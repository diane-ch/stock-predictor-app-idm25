#!/usr/bin/env python3
"""
All-in-One Market Data Updater — Polygon-only, append-only + REPAIR INCOMPLETE ROWS

What it updates (appends/repairs):
- stock_prices_1030_wide_format.csv   (10:30 ET minute-bar snapshot per ticker, Polygon)
- stock_prices_0900_wide_format.csv   (09:00 ET minute-bar snapshot per ticker, Polygon)
- spy_premarket_0915_prices.csv       (SPY ~09:15 ET minute close, Polygon; column 'SPY')
- vix_open_clean.csv                  (VIX latest available value per day, column 'VIX')
- historical_closing_prices.csv       (wide daily CLOSES via Polygon /v2/aggs/grouped …)
- spy_prev_close.csv                  (SPY close + prev close + return, derived from closes)
- final_lstm_features.csv             (optional TA for new dates only, from closes + SPY + VIX)
- stock_open_prices_wide_format.csv   (daily OPEN prices wide format, via yfinance)
- spy_prev_close_4pm.csv              (SPY close & prev close at 4pm NY, via yfinance)
- garch.csv                           (per-ticker daily GARCH(1,1) volatility estimates)

Environment (optional):
- POLYGON_API_KEY
- START_DATE_YYYY_MM_DD               (default: 2021-01-04)
- UPDATE_WHAT                         (default: ALL) any of: 1030,0900,SPY915,VIX,CLOSES,SPY4PM,TA,OPEN,SPY4PM_EXT,GARCH,ALL
- DATA_DIR
- POLYGON_FIXED_DELAY_SECONDS         (default: 0.15)
- POLYGON_ADJUSTED_MINUTE             (default: false)
- POLYGON_ADJUSTED_DAILY              (default: true)
- POLYGON_MAX_RETRIES                 (default: 6)
- REPAIR_LOOKBACK_DAYS                (default: 3)    ← only re-fetch incomplete rows within last N days (0 = repair all)
- INTRADAY_MAX_GAP_SEC                (default: 2000) ← accept nearest minute bar within this many seconds

Notes:
- Adds REPAIR mode: fills NaNs for existing dates by re-querying Polygon for those dates.
- Uses nearest minute bar (prefers <= target) with a configurable time-gap tolerance.
"""

import os
import subprocess
import sys
import shutil
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date, time as dt_time, timezone
from typing import Dict, List, Optional, Tuple

# ---------- Timezones ----------
try:
    from zoneinfo import ZoneInfo
    NY_TZ = ZoneInfo("America/New_York")
except Exception:
    import pytz
    NY_TZ = pytz.timezone("America/New_York")
UTC = timezone.utc

# ---------- Config ----------
API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
if not API_KEY:
    # Embedded fallback (per your request). ENV var still overrides.
    API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"
    print("🔐 Using embedded Polygon API key from script (override with $POLYGON_API_KEY).")

DEFAULT_START = os.getenv("START_DATE_YYYY_MM_DD", "2021-01-04")
WHAT = os.getenv("UPDATE_WHAT", "ALL").upper().split(",")
DATA_DIR = os.getenv("DATA_DIR", "ml_pipeline/data").strip()
FIXED_DELAY = float(os.getenv("POLYGON_FIXED_DELAY_SECONDS", "0.15"))
MAX_RETRIES = int(os.getenv("POLYGON_MAX_RETRIES", "6"))
ADJ_MINUTE = os.getenv("POLYGON_ADJUSTED_MINUTE", "false").strip().lower() in ("1","true","yes")
ADJ_DAILY  = os.getenv("POLYGON_ADJUSTED_DAILY", "true").strip().lower() in ("1","true","yes")
REPAIR_LOOKBACK_DAYS = int(os.getenv("REPAIR_LOOKBACK_DAYS", "3"))
INTRADAY_MAX_GAP_SEC = int(os.getenv("INTRADAY_MAX_GAP_SEC", "2000"))  # ~33 minutes

def outpath(name: str) -> str:
    return os.path.join(DATA_DIR, name) if DATA_DIR else name

# ---------- Ticker universe (SPY included so 'closes' has SPY column) ----------
TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","SPY","BRK.B","UNH","JPM",
    "V","LLY","XOM","MA","AVGO","JNJ","HD","PG","MRK","COST",
    "ABBV","ADBE","PEP","CRM","NFLX","CVX","WMT","ACN","AMD","MCD",
    "KO","BAC","TMO","INTC","LIN","AMGN","TXN","NEE","PFE","HON",
    "MS","UNP","QCOM","PM","GS","NOW","VRTX","BKNG","LOW","RTX",
    "ISRG","LMT","IBM","SBUX","GE","CAT","BLK","DE","ADI","MDT",
    "ORCL","INTU","CSCO","MU","ADSK","PANW","SNPS","CDNS","FTNT","ZM",
    "REGN","BMY","GILD","BIIB","DHR","CI","ELV","ZBH","IDXX","HCA",
    "SCHW","AXP","C","TFC","SPGI","ICE","CB","AON","MMC","AMP",
    "SLB","COP","EOG","PSX","MPC","OKE","WMB","KMI","HAL","FANG",
    "TGT","DG","ROST","DLTR","KHC","SYY","KR","CL","MNST","CHD",
    "ETN","EMR","ROP","PH","ITW","ROK","FAST","PCAR","XYL","AOS",
    "SO","D","DUK","AEP","EXC","PEG","ED","WEC","EIX","XEL"
]

# ---------- Safe CSV writes / helpers ----------
def safe_write_csv(df: pd.DataFrame, path: str):
    """Atomic write with timestamped backup of the existing file (if any)."""
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(tmp, index=False)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        stamp = datetime.now(tz=NY_TZ).strftime("%Y%m%d-%H%M%S")
        backup = f"{path}.bak-{stamp}"
        try:
            shutil.copy2(path, backup)
            print(f"🛟 Backup → {backup}")
        except Exception as e:
            print(f"⚠️ Backup failed: {e}")
    os.replace(tmp, path)

def last_date_in_csv(path: str, default_start: str) -> datetime:
    """Return next start date = (max Date + 1 day) or default_start if missing/empty."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return datetime.fromisoformat(default_start)
    try:
        df = pd.read_csv(path, usecols=["Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        if df.empty:
            return datetime.fromisoformat(default_start)
        last = df["Date"].max().to_pydatetime()
        return (last + timedelta(days=1)).replace(tzinfo=None)
    except Exception:
        return datetime.fromisoformat(default_start)

def business_days(start_dt: datetime, end_dt: datetime) -> List[datetime]:
    days, d = [], start_dt
    while d.date() <= end_dt.date():
        if d.weekday() < 5:
            days.append(d.replace(hour=0, minute=0, second=0, microsecond=0))
        d += timedelta(days=1)
    return days

# ---------- Polygon HTTP (fixed 0.15s delay only) ----------
def polygon_get(url: str, params: Dict) -> requests.Response:
    if "apiKey" not in params:
        params["apiKey"] = API_KEY
    attempt, backoff = 0, 1.0
    while True:
        attempt += 1
        if FIXED_DELAY > 0:
            time.sleep(FIXED_DELAY)
        r = requests.get(url, params=params, timeout=45)
        if 200 <= r.status_code < 300:
            return r
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            try:
                wait_s = float(ra) if ra is not None else backoff
            except Exception:
                wait_s = backoff
            time.sleep(wait_s)
            backoff = min(backoff * 2.0, 32.0)
        elif 500 <= r.status_code < 600:
            time.sleep(backoff); backoff = min(backoff * 2.0, 32.0)
        else:
            r.raise_for_status()
        if attempt >= MAX_RETRIES:
            r.raise_for_status()

def poly_symbol_for_date(sym: str, dt: datetime) -> str:
    """Handle renames/specials: META→FB pre-2022-06-09; BRK.B dot/slash tried in minute-bar helper."""
    if sym == "META" and dt.date() < date(2022, 6, 9):
        return "FB"
    return sym

# ---------- Polygon data helpers ----------
def polygon_day_bars_1m(ticker: str, d: datetime):
    """All 1-min bars for a ticker *or index* for date d (NY session day)."""
    ds = d.strftime("%Y-%m-%d")
    # Try both for BRK.B (dot and slash) — indices like I:VIX pass through unchanged
    for sym_try in [poly_symbol_for_date(ticker, d).replace("BRK.B","BRK.B"),
                    poly_symbol_for_date(ticker, d).replace("BRK.B","BRK/B")]:
        url = f"https://api.polygon.io/v2/aggs/ticker/{sym_try}/range/1/minute/{ds}/{ds}"
        try:
            r = polygon_get(url, {"adjusted": ("true" if ADJ_MINUTE else "false"),
                                  "sort":"asc", "limit":50000})
            js = r.json()
            res = js.get("results", [])
            if res: return res
        except Exception:
            continue
    return None

def polygon_daily_ohlc_stock(sym: str, d: datetime):
    """Daily OHLC for a stock for date d."""
    ds = d.strftime("%Y-%m-%d")
    sym = poly_symbol_for_date(sym, d)
    url = f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/{ds}/{ds}"
    try:
        r = polygon_get(url, {"adjusted": ("true" if ADJ_DAILY else "false")})
        arr = r.json().get("results", [])
        return arr[0] if arr else None
    except Exception:
        return None

def polygon_daily_grouped(d: datetime):
    """Grouped daily OHLC for ALL US stocks for date d (single call)."""
    ds = d.strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{ds}"
    try:
        r = polygon_get(url, {"adjusted": ("true" if ADJ_DAILY else "false")})
        return r.json().get("results", [])  # list of {T, o,h,l,c,v,...}
    except Exception:
        return []

def polygon_daily_ohlc_index(index_ticker: str, d: datetime):
    """Daily OHLC for an index (e.g., 'I:VIX') for date d."""
    ds = d.strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/{index_ticker}/range/1/day/{ds}/{ds}"
    try:
        r = polygon_get(url, {"sort": "asc", "limit": 5000})
        arr = r.json().get("results", [])
        return arr[0] if arr else None
    except Exception:
        return None

def pick_bar_near_time_minute(
    bars: List[dict],
    target_ny: datetime,
    prefer_le: bool = True
) -> Tuple[Optional[dict], float]:
    """
    Pick the 1-min bar closest to target (ties prefer <= when prefer_le=True).
    Returns (bar_or_None, abs_time_diff_seconds).
    """
    closest, best = None, float("inf")
    tie_pref_best = 1 if not prefer_le else 0
    for b in bars:
        ts_utc = datetime.fromtimestamp(b["t"]/1000, tz=UTC)
        ts_ny = ts_utc.astimezone(NY_TZ)
        diff = abs((ts_ny - target_ny).total_seconds())
        pref = 0 if ts_ny <= target_ny else 1
        if diff < best or (diff == best and pref < tie_pref_best):
            closest, best, tie_pref_best = b, diff, pref
    return closest, (best if closest is not None else float("inf"))

def get_bar_value_with_fallback(
    bars: Optional[List[dict]],
    target_ny: datetime,
    requested_field: str,
    max_allowed_gap_sec: int,
    ticker: str
) -> Tuple[Optional[float], str]:
    """
    Try to extract a value for requested_field ('o' or 'c') near target.
    Fallbacks:
      1) If chosen bar is too far, return None with reason.
      2) If requested_field missing on the chosen bar, try the bar's 'c'.
    Returns (value_or_None, reason_string).
    """
    if not bars:
        return None, "no-bars"
    bar, gap = pick_bar_near_time_minute(bars, target_ny, prefer_le=True)
    if bar is None:
        return None, "no-nearest"
    if gap > max_allowed_gap_sec:
        return None, f"gap>{max_allowed_gap_sec}s (actual {int(gap)}s)"
    val = bar.get(requested_field)
    if val is None and requested_field != "c":
        # try close as a reasonable fallback for intraday snapshots
        val = bar.get("c")
        if val is not None:
            return float(val), "fallback:bar.close"
        return None, "field-missing"
    return float(val), "ok"

# ---------- Updaters (append + repair) ----------
def update_intraday_at_time(output_csv: str, target_time: dt_time, price_field: str, tickers: List[str]):
    """
    Append missing business days AND repair incomplete rows by re-querying Polygon.
    - Uses nearest minute bar (prefers <= target); rejects bars too far away based on INTRADAY_MAX_GAP_SEC.
    - If 'o' missing for that bar, tries the bar's 'c'; then daily open as last resort (for 'o' requests).
    - For existing dates, only fills NaNs (never overwrites a non-NaN).
    - Repair scope limited by REPAIR_LOOKBACK_DAYS (0 = repair all).
    """
    if not API_KEY:
        print(f"⛔ Skipping {output_csv} — no POLYGON_API_KEY.")
        return

    tol_sec = INTRADAY_MAX_GAP_SEC

    # Ensure header
    if not os.path.exists(output_csv) or os.path.getsize(output_csv) == 0:
        safe_write_csv(pd.DataFrame(columns=["Date"] + tickers), output_csv)

    # Load existing & normalize
    exist = pd.read_csv(output_csv)
    if "Date" not in exist.columns:
        exist.insert(0, "Date", "")
    # Make sure all ticker columns exist
    for t in tickers:
        if t not in exist.columns:
            exist[t] = np.nan

    exist["Date"] = pd.to_datetime(exist["Date"], errors="coerce")
    exist = exist.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    # Determine dates to append (after last Date)
    start_dt = (exist["Date"].max() + pd.Timedelta(days=1)).to_pydatetime() if not exist.empty else datetime.fromisoformat(DEFAULT_START)
    end_dt = datetime.now(tz=NY_TZ)
    append_days = business_days(start_dt, end_dt)

    # Determine dates to repair (existing business days with any NaN among tracked tickers)
    if not exist.empty:
        mask_incomplete = exist[tickers].isna().any(axis=1)
        repair_dates = sorted(set(exist.loc[mask_incomplete, "Date"].dt.date.tolist()))
    else:
        repair_dates = []

    # Limit repair to most recent N days (0 => no limit, repair all)
    if REPAIR_LOOKBACK_DAYS > 0 and repair_dates:
        cutoff = (datetime.now(tz=NY_TZ).date() - timedelta(days=REPAIR_LOOKBACK_DAYS - 1))
        repair_dates = [d for d in repair_dates if d >= cutoff]

    # Prepare final date list (append + repair)
    dates_to_process = [*append_days] + [datetime.combine(d, dt_time(0,0)) for d in repair_dates]
    # De-duplicate and sort
    dates_to_process = sorted({d.date(): d for d in dates_to_process}.values())

    if not dates_to_process:
        print(f"✅ {output_csv} already up to date and complete.")
        return

    print(f"🧰 {output_csv}: processing {len(dates_to_process)} date(s) "
          f"({len(append_days)} append, {len(repair_dates)} repair).")

    # Collect fresh values per date
    new_rows = []
    for i, d in enumerate(dates_to_process, 1):
        ds = d.strftime("%Y-%m-%d")
        tlabel = target_time.strftime('%H:%M')
        print(f"\n📅 [{i}/{len(dates_to_process)}] {output_csv}: {ds} @ {tlabel} ET")
        row = {"Date": ds}
        target_ny = datetime.combine(d.date(), target_time, tzinfo=NY_TZ)

        for t in tickers:
            reason = ""
            try:
                bars = polygon_day_bars_1m(t, d)
                val, reason = get_bar_value_with_fallback(
                    bars=bars,
                    target_ny=target_ny,
                    requested_field=price_field,
                    max_allowed_gap_sec=tol_sec,
                    ticker=t
                )
                if val is None and price_field == "o":
                    # gentle fallback to daily open if the minute bar was missing or too far
                    ohlc = polygon_daily_ohlc_stock(t, d)
                    if ohlc and ohlc.get("o") is not None:
                        val = float(ohlc["o"])
                        reason = "fallback:daily.open" if reason else "fallback:daily.open"
                row[t] = float(val) if val is not None else np.nan
                print(f"  {'✅' if val is not None else '❔'} {t:6s}: {price_field}={row[t] if val is not None else 'NaN'}"
                      + (f"  ({reason})" if reason else ""))
            except Exception as e:
                row[t] = np.nan
                print(f"  ⚠️  {t:6s}: {e}")
        new_rows.append(row)

    add = pd.DataFrame.from_records(new_rows)
    add["Date"] = pd.to_datetime(add["Date"], errors="coerce")

    # Merge strategy:
    # - if Date not in existing: append full row
    # - if Date in existing: fill NaNs in existing with values from add (do not overwrite non-NaNs)
    exist_idxed = exist.set_index("Date")
    add_idxed = add.set_index("Date")

    # Ensure same set of columns
    for t in tickers:
        if t not in add_idxed.columns:
            add_idxed[t] = np.nan
        if t not in exist_idxed.columns:
            exist_idxed[t] = np.nan

    # Fill NaNs in existing with add values for overlapping dates
    overlap = exist_idxed.index.intersection(add_idxed.index)
    if len(overlap) > 0:
        merged_overlap = exist_idxed.loc[overlap, tickers].copy()
        for t in tickers:
            merged_overlap[t] = merged_overlap[t].where(merged_overlap[t].notna(), add_idxed.loc[overlap, t])
        exist_idxed.loc[overlap, tickers] = merged_overlap

    # Append any brand-new dates
    new_dates = add_idxed.index.difference(exist_idxed.index)
    if len(new_dates) > 0:
        exist_idxed = pd.concat([exist_idxed, add_idxed.loc[new_dates, tickers]], axis=0)

    # Write back
    out_df = exist_idxed.reset_index().sort_values("Date")
    out_df["Date"] = out_df["Date"].dt.strftime("%Y-%m-%d")
    out_df = out_df[["Date"] + TICKERS]  # keep only Date + tracked tickers
    safe_write_csv(out_df, output_csv)

    repaired = len(repair_dates)
    appended = len(new_dates)
    print(f"✅ Completed: repaired {repaired} date(s), appended {appended} new date(s) → {output_csv}")

def update_spy_0915(output_csv: str):
    """Append SPY 09:15 (close of that minute) → single column 'SPY'."""
    if not os.path.exists(output_csv) or os.path.getsize(output_csv) == 0:
        safe_write_csv(pd.DataFrame(columns=["Date","SPY"]), output_csv)
    start_dt = last_date_in_csv(output_csv, DEFAULT_START)
    end_dt = datetime.now(tz=NY_TZ)
    days = business_days(start_dt, end_dt)
    if not days:
        print(f"✅ {output_csv} already up to date."); return

    rows = []
    for i, d in enumerate(days, 1):
        ds = d.strftime("%Y-%m-%d")
        print(f"\n📅 [{i}/{len(days)}] {output_csv}: {ds} @ 09:15 ET")
        row = {"Date": ds}
        try:
            bars = polygon_day_bars_1m("SPY", d)
            val = None
            reason = ""
            if bars:
                target_ny = datetime.combine(d.date(), dt_time(9,15), tzinfo=NY_TZ)
                bar, gap = pick_bar_near_time_minute(bars, target_ny, prefer_le=True)
                if bar and gap <= INTRADAY_MAX_GAP_SEC and bar.get("c") is not None:
                    val, reason = float(bar.get("c")), "ok"
                else:
                    reason = f"gap>{INTRADAY_MAX_GAP_SEC}s or no-bar"
            row["SPY"] = float(val) if val is not None else np.nan
            print(f"  {'✅' if val is not None else '❔'} SPY: {row['SPY'] if val is not None else 'NaN'}"
                  + (f"  ({reason})" if reason else ""))
        except Exception as e:
            row["SPY"] = np.nan
            print(f"  ⚠️  SPY: {e}")
        rows.append(row)

    add = pd.DataFrame.from_records(rows).sort_values("Date")
    exist = pd.read_csv(output_csv)
    exist["Date"] = pd.to_datetime(exist["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    add["Date"] = pd.to_datetime(add["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    merged = pd.concat([exist, add[~add["Date"].isin(exist["Date"])]]).sort_values("Date")
    safe_write_csv(merged, output_csv)
    print(f"✅ Appended {len(add[~add['Date'].isin(exist['Date'])])} rows → {output_csv}")

def update_vix_latest(output_csv: str, start_date="2021-01-01"):
    """
    Append VIX (I:VIX) as the LATEST AVAILABLE value for each day.
    - Past days: daily close 'c'
    - Today: latest 1-min bar close up to now (fallback to today's daily 'c' if present)
    Writes a two-column CSV: Date,VIX   (auto-migrates old 'Open' column to 'VIX')
    """
    # Migrate old file (Open -> VIX) if needed
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        try:
            cur = pd.read_csv(output_csv)
            if "Open" in cur.columns and "VIX" not in cur.columns:
                cur = cur.rename(columns={"Open": "VIX"})
                safe_write_csv(cur, output_csv)
        except Exception:
            pass

    # Determine missing business days
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        start_dt = last_date_in_csv(output_csv, start_date)
    else:
        start_dt = datetime.fromisoformat(start_date)

    end_dt = datetime.now(tz=NY_TZ)
    days = business_days(start_dt, end_dt)
    if not days:
        print("✅ VIX up to date."); return

    rows = []
    today_ny = datetime.now(tz=NY_TZ).date()
    now_ny_dt = datetime.now(tz=NY_TZ)

    for i, d in enumerate(days, 1):
        ds = d.strftime("%Y-%m-%d")
        print(f"\n📅 [{i}/{len(days)}] VIX latest: {ds}")
        v = np.nan
        try:
            if d.date() < today_ny:
                # Past day: daily close
                ohlc = polygon_daily_ohlc_index("I:VIX", d)
                if ohlc and ohlc.get("c") is not None:
                    v = float(ohlc["c"])
            else:
                # Today: last available minute-bar close up to now
                bars = polygon_day_bars_1m("I:VIX", d)
                if bars:
                    bar, gap = pick_bar_near_time_minute(bars, now_ny_dt, prefer_le=True)
                    if bar is not None and bar.get("c") is not None:
                        v = float(bar["c"])
                if np.isnan(v):
                    # Fallback to today's daily close (if Polygon has populated it yet)
                    ohlc = polygon_daily_ohlc_index("I:VIX", d)
                    if ohlc and ohlc.get("c") is not None:
                        v = float(ohlc["c"])
        except Exception:
            pass

    rows.append({"Date": ds, "VIX": v})

    add = pd.DataFrame(rows).sort_values("Date")
    if os.path.exists(output_csv):
        exist = pd.read_csv(output_csv)
        # Normalize / migrate columns if needed
        if "Open" in exist.columns and "VIX" not in exist.columns:
            exist = exist.rename(columns={"Open": "VIX"})
        if "VIX" not in exist.columns:
            exist["VIX"] = np.nan
        exist["Date"] = pd.to_datetime(exist["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        add["Date"] = pd.to_datetime(add["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        merged = pd.concat([exist, add[~add["Date"].isin(exist["Date"])]]).sort_values("Date")
    else:
        merged = add
    safe_write_csv(merged, output_csv)
    print(f"✅ Appended {len(add)} rows → {output_csv}")

def update_daily_closes_polygon(output_csv: str, start_date: str):
    """Append daily CLOSES (wide) using ONE grouped call per missing date."""
    # determine missing business days
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        start_dt = last_date_in_csv(output_csv, start_date)
    else:
        start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.now(tz=NY_TZ)
    days = business_days(start_dt, end_dt)
    if not days:
        print("✅ Daily closes up to date."); return

    # ensure header exists
    if not os.path.exists(output_csv) or os.path.getsize(output_csv) == 0:
        safe_write_csv(pd.DataFrame(columns=["Date"] + TICKERS), output_csv)

    new_rows = []
    for i, d in enumerate(days, 1):
        ds = d.strftime("%Y-%m-%d")
        print(f"\n📅 [{i}/{len(days)}] closes: {ds}")
        res = polygon_daily_grouped(d)
        by_sym_close = {item["T"]: item.get("c") for item in res if isinstance(item.get("T"), str)}
        row = {"Date": ds}
        for t in TICKERS:
            row[t] = float(by_sym_close[t]) if t in by_sym_close and by_sym_close[t] is not None else np.nan
        new_rows.append(row)

    add = pd.DataFrame.from_records(new_rows).sort_values("Date")
    exist = pd.read_csv(output_csv)
    exist["Date"] = pd.to_datetime(exist["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    add["Date"] = pd.to_datetime(add["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    merged = pd.concat([exist, add[~add["Date"].isin(exist["Date"])]]).sort_values("Date")
    safe_write_csv(merged, output_csv)
    print(f"✅ Appended {len(add[~add['Date'].isin(exist['Date'])])} rows → {output_csv}")

def update_spy_4pm_from_closes(output_csv: str, closes_csv: str):
    """Build/append SPY 4pm file purely from the closes wide CSV (now includes SPY)."""
    if not os.path.exists(closes_csv) or os.path.getsize(closes_csv) == 0:
        print("⛔ Need historical_closing_prices.csv first."); return
    dc = pd.read_csv(closes_csv)
    if "SPY" not in dc.columns:
        print("⛔ SPY column missing in closes."); return
    dc["Date"] = pd.to_datetime(dc["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = pd.DataFrame({"Date": dc["Date"], "SPY_close": pd.to_numeric(dc["SPY"], errors="coerce").round(4)})
    out["SPY_prev_close"] = out["SPY_close"].shift(1)
    out["spy_prev_cc_ret"] = (out["SPY_close"] / out["SPY_prev_close"] - 1.0).round(6)

    if os.path.exists(output_csv):
        exist = pd.read_csv(output_csv)
        exist["Date"] = pd.to_datetime(exist["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        add = out[~out["Date"].isin(exist["Date"])]
        if add.empty:
            print("✅ SPY 4PM up to date."); return
        merged = pd.concat([exist, add]).sort_values("Date").reset_index(drop=True)
        # recompute prev close/returns across the whole set for correctness
        merged["SPY_prev_close"] = merged["SPY_close"].shift(1)
        merged["spy_prev_cc_ret"] = (merged["SPY_close"] / merged["SPY_prev_close"] - 1.0).round(6)
        safe_write_csv(merged, output_csv)
        print(f"✅ Appended {len(add)} rows → {output_csv}")
    else:
        safe_write_csv(out, output_csv)
        print(f"✅ Wrote {len(out)} rows → {output_csv}")

def update_ta_features(output_csv: str):
    """Compute TA for *new* dates only, using closes (Polygon-based)."""
    try:
        import ta
    except Exception:
        print("ℹ️  'ta' not installed — skipping TA."); return

    closes_csv = outpath("historical_closing_prices.csv")
    if not os.path.exists(closes_csv) or os.path.getsize(closes_csv) == 0:
        print("⛔ Need historical_closing_prices.csv first."); return

    dc = pd.read_csv(closes_csv)
    dc["Date"] = pd.to_datetime(dc["Date"])
    dc = dc.sort_values("Date").set_index("Date")

    done = set()
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        try:
            base = pd.read_csv(output_csv, usecols=["Date"])
            base["Date"] = pd.to_datetime(base["Date"], errors="coerce")
            done = set(base["Date"].dt.strftime("%Y-%m-%d").dropna())
        except Exception:
            pass

    frames = []
    for t in TICKERS:
        if t not in dc.columns: continue
        s = pd.to_numeric(dc[t], errors="coerce")
        if s.notna().sum() < 30: continue
        f = pd.DataFrame({
            f"{t}_sma10": ta.trend.sma_indicator(s, window=10),
            f"{t}_rsi14": ta.momentum.rsi(s, window=14),
            f"{t}_macd" : ta.trend.macd_diff(s, window_slow=26, window_fast=12, window_sign=9),
        }, index=s.index)
        frames.append(f)

    if not frames:
        print("⚠️  Not enough data for TA."); return

    feats = pd.concat(frames, axis=1)

    # Add SPY (from SPY 4pm) and VIX (from VIX file). Accept 'VIX' or legacy 'Open'.
    extras = []
    try:
        spy = pd.read_csv(outpath("spy_prev_close.csv"), parse_dates=["Date"]).set_index("Date")["SPY_close"].rename("SPY")
        extras.append(spy)
    except Exception:
        extras.append(pd.Series(dtype=float, name="SPY"))
    vix_csv = outpath("vix_open_clean.csv")
    try:
        vix_df = pd.read_csv(vix_csv, parse_dates=["Date"])
        v_col = "VIX" if "VIX" in vix_df.columns else ("Open" if "Open" in vix_df.columns else None)
        if v_col:
            vix_series = vix_df.set_index("Date")[v_col].rename("VIX")
            extras.append(vix_series)
        else:
            extras.append(pd.Series(dtype=float, name="VIX"))
    except Exception:
        extras.append(pd.Series(dtype=float, name="VIX"))

    if extras:
        for s in extras:
            feats = feats.join(s, how="left")

    feats = feats.reset_index().rename(columns={"index":"Date"})
    feats["Date"] = pd.to_datetime(feats["Date"]).dt.strftime("%Y-%m-%d")
    add = feats[~feats["Date"].isin(done)].sort_values("Date")
    if add.empty:
        print("✅ TA features up to date."); return

    if os.path.exists(output_csv):
        exist = pd.read_csv(output_csv)
        merged = pd.concat([exist, add]).sort_values("Date")
        safe_write_csv(merged, output_csv)
    else:
        safe_write_csv(add, output_csv)
    print(f"✅ Appended {len(add)} rows → {output_csv}")


# ---------- Extra helpers for external scripts ----------
def run_spy4pm_external(out_csv: str):
    """Run SPY4PM.py to produce spy_prev_close_4pm.csv (yfinance-based)."""
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__) or '.', 'SPY4PM.py'), '--out', out_csv]
    print("▶️ Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def run_garch_external():
    """Run garch.py which writes garch.csv and other outputs in ./garch_outputs."""
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__) or '.', 'garch.py')]
    print("▶️ Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    # Move main output garch.csv to DATA_DIR if needed
    src = 'garch.csv'
    dst = outpath(src)
    if dst != src and os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print(f"📦 Moved {src} → {dst}")

def update_opening_prices_file():
    """Call openpy.update_opening_prices() and ensure CSV ends up under DATA_DIR."""
    try:
        import openpy as _openpy
    except Exception as e:
        raise RuntimeError(f"Cannot import openpy.py: {e}")
    _openpy.update_opening_prices()
    src = 'stock_open_prices_wide_format.csv'
    dst = outpath(src)
    if dst != src and os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print(f"📦 Moved {src} → {dst}")

# ---------- Runner ----------
def run_all():
    targets = set([w.strip().upper() for w in WHAT])
    if "ALL" in targets:
        targets = {"1030","0900","SPY915","VIX","CLOSES","SPY4PM","TA","OPEN","SPY4PM_EXT","GARCH"}

    try:
        if "1030" in targets:
            update_intraday_at_time(outpath("stock_prices_1030_wide_format.csv"),
                                    dt_time(10,30), price_field="o", tickers=TICKERS)
    except Exception as e:
        print("❌ 10:30 updater failed:", e)

    try:
        if "0900" in targets:
            update_intraday_at_time(outpath("stock_prices_0900_wide_format.csv"),
                                    dt_time(9,0), price_field="c", tickers=TICKERS)
    except Exception as e:
        print("❌ 09:00 updater failed:", e)

    try:
        if "SPY915" in targets:
            update_spy_0915(outpath("spy_premarket_0915_prices.csv"))
    except Exception as e:
        print("❌ SPY 09:15 updater failed:", e)

    try:
        if "VIX" in targets:
            update_vix_latest(outpath("vix_open_clean.csv"))
    except Exception as e:
        print("❌ VIX updater failed:", e)

    try:
        if "CLOSES" in targets:
            update_daily_closes_polygon(outpath("historical_closing_prices.csv"), DEFAULT_START)
    except Exception as e:
        print("❌ Daily closes updater failed:", e)

    try:
        if "SPY4PM" in targets:
            update_spy_4pm_from_closes(outpath("spy_prev_close.csv"), outpath("historical_closing_prices.csv"))
    except Exception as e:
        print("❌ SPY 4PM updater failed:", e)


    try:
        if "OPEN" in targets:
            update_opening_prices_file()
    except Exception as e:
        print("❌ Opening prices updater failed:", e)

    try:
        if "SPY4PM_EXT" in targets:
            run_spy4pm_external(outpath("spy_prev_close_4pm.csv"))
    except Exception as e:
        print("❌ SPY4PM (external) updater failed:", e)

    try:
        if "GARCH" in targets:
            run_garch_external()
    except Exception as e:
        print("❌ GARCH updater failed:", e)

    try:
        if "TA" in targets:
            update_ta_features(outpath("final_lstm_features.csv"))
    except Exception as e:
        print("❌ TA features updater failed:", e)

if __name__ == "__main__":
    print("🧩 Polygon-only Append-Updater (+ repair)")
    print("🕒", datetime.now(tz=NY_TZ).strftime("%Y-%m-%d %H:%M:%S %Z"))
    print(f"⏱️ Fixed Polygon delay: {FIXED_DELAY:.2f}s  |  Max gap: {INTRADAY_MAX_GAP_SEC}s")
    run_all()
