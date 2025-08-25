#!/usr/bin/env python3
"""
EVERYTHING-BUT-TA-&-VIX MASTER UPDATER (Polygon REST, no SDK)
-------------------------------------------------------------
Maintains:
  • SPY premarket 09:15 snapshot
  • 09:00 and 10:30 ticker snapshots (minute bars, nearest bar)
  • Daily opens (wide format)
  • Historical closes (wide format)
  • SPY previous close (4pm)
  • Simple GARCH-like daily vol via EWMA (from local closes; fallback to Polygon)

Removed:
  • All TA indicator logic (RSI/MACD/BB)
  • All VIX logic

Hardcoded API key is overrideable via POLYGON_API_KEY env var.
"""

# Silence urllib3 LibreSSL warning on macOS Python 3.9
try:
    from urllib3.exceptions import NotOpenSSLWarning
    import warnings as _warnings
    _warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

import os
import sys
import time
import shutil
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, time as dt_time, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Tuple

# ====================== CONFIG ======================
API_KEY = os.getenv("POLYGON_API_KEY", "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l")
SLEEP_SEC = 0.15
NY = ZoneInfo("America/New_York")

TICKERS: List[str] = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK.B","UNH","JPM",
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

FILES = {
    "garch": "garch.csv",
    "hist_close": "historical_closing_prices_old.csv",
    "open_wide": "stock_open_prices_wide_format.csv",
    "snap_0900": "stock_prices_0900_wide_format.csv",
    "snap_1030": "stock_prices_1030_wide_format.csv",
    "spy_0915": "spy_premarket_0915_prices.csv",
    "spy_prev_close": "spy_prev_close_4pm.csv",
}

# ====================== SUMMARY LOG ======================
UPDATE_LOG: List[Dict] = []

def log_update(filename: str, rows_added: int = 0, status: str = "updated", extra: str = "") -> None:
    UPDATE_LOG.append({"file": filename, "rows_added": int(rows_added or 0), "status": status, "extra": extra})

def print_final_summary() -> None:
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    if not UPDATE_LOG:
        print("No actions recorded.")
    else:
        for x in UPDATE_LOG:
            if x["rows_added"] > 0:
                print(f"✅ {x['file']} (+{x['rows_added']} rows){' · ' + x['extra'] if x['extra'] else ''}")
            else:
                print(f"🟢 {x['file']} (already up to date){' · ' + x['extra'] if x['extra'] else ''}")
    print("="*60 + "\n")

def print_status_only():
    for k, v in FILES.items():
        if os.path.exists(v):
            try:
                df = pd.read_csv(v)
                if "Date" in df.columns:
                    print(f"{v}: rows={len(df)}  {df['Date'].min()} → {df['Date'].max()}")
                else:
                    print(f"{v}: rows={len(df)}")
            except Exception as e:
                print(f"{v}: <error reading> {e}")
        else:
            print(f"{v}: <missing>")

# ====================== HELPERS ======================
def atomic_write(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    if os.path.exists(path):
        try: shutil.copy2(path, path + ".bak")
        except Exception: pass
    os.replace(tmp, path)
    try:
        chk = pd.read_csv(path)
        print(f"📊 Saved {path} — rows={len(chk)}, cols={chk.shape[1]}")
    except Exception:
        print(f"📊 Saved {path}")

def prune_future_rows(path: str):
    """Remove rows with Date > today from a CSV in place."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    try:
        df = pd.read_csv(path)
        if "Date" not in df.columns:
            return
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        today = pd.Timestamp(datetime.utcnow().date())
        before = len(df)
        df = df[df["Date"] <= today].copy()
        if len(df) < before:
            df = df.sort_values("Date").reset_index(drop=True)
            atomic_write(df, path)
            print(f"🧹 Pruned future rows from {path}: {before - len(df)} removed")
    except Exception as e:
        print(f"⚠️ Could not prune {path}: {e}")

def business_days(start: date, end: date) -> List[date]:
    """Strict business-day generator. No start/end swap. Clamps end to today."""
    today = datetime.utcnow().date()
    if end > today:
        end = today
    if start > end:
        return []
    return [d.date() for d in pd.date_range(start, end, freq="B")]

def _load_or_init(path: str, tickers: List[str]) -> pd.DataFrame:
    if os.path.exists(path) and os.path.getsize(path)>0:
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame(columns=["Date"]+tickers)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for t in tickers:
        if t not in df.columns:
            df[t] = np.nan
    return df.sort_values("Date").reset_index(drop=True)

def _poly_symbol(yahoo_ticker: str) -> str:
    # Polygon uses dot for class (BRK.B). List already uses BRK.B; keep as-is.
    return yahoo_ticker.replace("-", ".")

# ====================== POLYGON CALLS ======================
def poly_minute_bars(ticker: str, day: date) -> List[Dict]:
    ds = pd.Timestamp(day).strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/{_poly_symbol(ticker)}/range/1/minute/{ds}/{ds}"
    r = requests.get(url, params={"apiKey": API_KEY, "sort":"asc", "limit":50000})
    if r.status_code != 200:
        return []
    return r.json().get("results", [])

def poly_daily_bars(ticker: str, start: date, end: date) -> List[Dict]:
    url = f"https://api.polygon.io/v2/aggs/ticker/{_poly_symbol(ticker)}/range/1/day/{start}/{end}"
    r = requests.get(url, params={"apiKey": API_KEY, "sort":"asc", "adjusted":"true"})
    if r.status_code != 200:
        return []
    return r.json().get("results", [])

def nearest_bar(bars: List[Dict], target_dt: datetime) -> Tuple[Optional[Dict], float]:
    if not bars:
        return None, float("inf")
    gaps = []
    for b in bars:
        ts = datetime.fromtimestamp(b["t"]/1000, tz=timezone.utc).astimezone(NY)
        gaps.append(abs((ts.replace(tzinfo=None) - target_dt).total_seconds()))
    idx = int(np.argmin(gaps))
    return bars[idx], float(gaps[idx])

# ====================== FEATURES ======================
def update_spy_0915(path: str):
    tkr = "SPY"
    prune_future_rows(path)  # NEW
    df = _load_or_init(path, [tkr])

    last_dt = df["Date"].max() if "Date" in df.columns else pd.NaT
    today = datetime.utcnow().date()
    start_day = (last_dt.date() + timedelta(days=1)) if pd.notna(last_dt) else (today - timedelta(days=5))
    end_day = today

    to_fetch = business_days(start_day, end_day)
    if not to_fetch:
        log_update(path, 0, "ok", "already up to date")
        return

    added = 0
    for d in to_fetch:
        bars = poly_minute_bars(tkr, d)
        target_dt = datetime.combine(d, dt_time(hour=9, minute=15))
        bar, gap = nearest_bar(bars, target_dt)
        if bar:
            val = bar.get("c") or bar.get("o")
            newrow = {"Date": pd.Timestamp(d), tkr: float(val) if val is not None else np.nan}
            df = pd.concat([df, pd.DataFrame([newrow])], ignore_index=True)
            added += 1
            print(f"  SPY {d}: {val} (gap={int(gap)}s)")
        time.sleep(SLEEP_SEC)

    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    atomic_write(df, path)
    log_update(path, added, "updated", "SPY 09:15")

def update_snapshot_wide(target_time: dt_time, path: str, tickers: List[str], prefer_past: bool = True):
    prune_future_rows(path)  # NEW
    df = _load_or_init(path, tickers)

    last_dt = df["Date"].max() if "Date" in df.columns else pd.NaT
    today = datetime.utcnow().date()
    start_day = (last_dt.date() + timedelta(days=1)) if pd.notna(last_dt) else (today - timedelta(days=5))
    end_day = today

    to_fetch = business_days(start_day, end_day)
    if not to_fetch:
        log_update(path, 0, "ok", "already up to date")
        return

    added = 0
    for d in to_fetch:
        row = {"Date": pd.Timestamp(d)}
        for t in tickers:
            bars = poly_minute_bars(t, d)
            target_dt = datetime.combine(d, target_time)
            bar, gap = nearest_bar(bars, target_dt)
            if not bar:
                continue
            val = bar.get("o") if prefer_past else (bar.get("c") or bar.get("o"))
            row[t] = float(val) if val is not None else np.nan
            time.sleep(SLEEP_SEC)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        added += 1
        print(f"  {path}: added {d}")

    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    atomic_write(df, path)
    log_update(path, added, "updated", f"snapshot {target_time.strftime('%H:%M')}")

def update_daily_opens(path: str, tickers: List[str], start_back_days: int = 5):
    prune_future_rows(path)  # NEW
    df = _load_or_init(path, tickers)

    last_dt = df["Date"].max() if "Date" in df.columns else pd.NaT
    today = datetime.utcnow().date()
    start_day = (last_dt.date() + timedelta(days=1)) if pd.notna(last_dt) else (today - timedelta(days=start_back_days))
    end_day = today

    to_fetch = business_days(start_day, end_day)
    if not to_fetch:
        log_update(path, 0, "ok", "already up to date")
        return

    added = 0
    for d in to_fetch:
        row = {"Date": pd.Timestamp(d)}
        for t in tickers:
            bars = poly_daily_bars(t, d, d)
            if not bars:
                continue
            row[t] = float(bars[0].get("o"))
            time.sleep(SLEEP_SEC)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        added += 1
        print(f"  {path}: added {d}")

    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    atomic_write(df, path)
    log_update(path, added, "updated", "daily opens")

def update_hist_closes(path: str, tickers: List[str], start_back_days: int = 30):
    prune_future_rows(path)  # NEW
    df = _load_or_init(path, tickers)

    last_dt = df["Date"].max() if "Date" in df.columns else pd.NaT
    today = datetime.utcnow().date()
    start_day = (last_dt.date() + timedelta(days=1)) if pd.notna(last_dt) else (today - timedelta(days=start_back_days))
    end_day = today

    if start_day > end_day:
        log_update(path, 0, "ok", "already up to date")
        return

    start_s = start_day.isoformat()
    end_s = end_day.isoformat()
    work = []
    for t in tickers:
        bars = poly_daily_bars(t, start_s, end_s)
        for b in bars:
            d = pd.to_datetime(b["t"], unit="ms").date()
            work.append((d, t, float(b.get("c"))))
        time.sleep(SLEEP_SEC)

    if not work:
        log_update(path, 0, "ok", "no new closes from polygon")
        return

    add_df = pd.DataFrame(work, columns=["Date","Ticker","Close"])
    wide = add_df.pivot_table(index="Date", columns="Ticker", values="Close", aggfunc="last").reset_index()
    wide["Date"] = pd.to_datetime(wide["Date"])
    df = pd.concat([df, wide], ignore_index=True)
    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    atomic_write(df, path)
    rows_added = len(wide)
    log_update(path, rows_added, "updated", "closes (wide)")

def update_spy_prev_close(path: str):
    # CSV schema: Date, SPY_close, SPY_return
    prune_future_rows(path)  # NEW

    if os.path.exists(path) and os.path.getsize(path)>0:
        base = pd.read_csv(path, parse_dates=["Date"])
        last = base["Date"].max().date()
        start = last + timedelta(days=1)
    else:
        base = pd.DataFrame(columns=["Date","SPY_close","SPY_return"])
        start = datetime.utcnow().date() - timedelta(days=5)

    end = datetime.utcnow().date()
    days = business_days(start, end)
    if not days:
        log_update(path, 0, "ok", "already up to date")
        return

    added = 0
    for d in days:
        bars = poly_daily_bars("SPY", d, d)
        if not bars:
            continue
        close = float(bars[0].get("c"))
        prev = base["SPY_close"].iloc[-1] if not base.empty else np.nan
        ret = (close/prev - 1.0) if prev == prev else np.nan
        base = pd.concat([base, pd.DataFrame([{"Date": pd.Timestamp(d), "SPY_close": close, "SPY_return": ret}])], ignore_index=True)
        added += 1
        time.sleep(SLEEP_SEC)

    if added > 0:
        base = base.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
        atomic_write(base, path)
    log_update(path, added, "updated" if added>0 else "ok", "SPY prev close")

# ====================== GARCH (EWMA fallback) ======================
def compute_garch_from_local_closes(out_csv: str, closes_csv: str, lam: float = 0.94):
    if not os.path.exists(closes_csv) or os.path.getsize(closes_csv) == 0:
        log_update(out_csv, 0, "skipped", "no local closes")
        return
    closes = pd.read_csv(closes_csv, parse_dates=["Date"]).sort_values("Date")
    tickers = [c for c in closes.columns if c != "Date"]
    vols = pd.DataFrame({"Date": closes["Date"]})
    for t in tickers:
        s = pd.to_numeric(closes[t], errors="coerce")
        r = s.pct_change()
        ewvar = r.pow(2).ewm(alpha=(1-lam), adjust=False).mean()
        vols[t] = np.sqrt(ewvar)  # daily sigma
    before = len(pd.read_csv(out_csv)) if os.path.exists(out_csv) else 0
    atomic_write(vols, out_csv)
    after = len(vols)
    log_update(out_csv, max(0, after-before), "updated", "EWMA from local")

def compute_garch_from_polygon_closes(out_csv: str, tickers: List[str], start: str = "2021-01-01", lam: float = 0.94):
    start_d = datetime.fromisoformat(start).date()
    end_d = datetime.utcnow().date()
    rows = []
    for t in tickers:
        bars = poly_daily_bars(t, start_d, end_d)
        for b in bars:
            d = pd.to_datetime(b["t"], unit="ms").date()
            rows.append((d, t, float(b.get("c"))))
        time.sleep(SLEEP_SEC)
    if not rows:
        log_update(out_csv, 0, "skipped", "no polygon closes")
        return
    wide = pd.DataFrame(rows, columns=["Date","Ticker","Close"]).pivot_table(index="Date", columns="Ticker", values="Close", aggfunc="last").reset_index()
    wide["Date"] = pd.to_datetime(wide["Date"])
    tickers2 = [c for c in wide.columns if c != "Date"]
    vols = pd.DataFrame({"Date": wide["Date"]})
    for t in tickers2:
        s = pd.to_numeric(wide[t], errors="coerce")
        r = s.pct_change()
        ewvar = r.pow(2).ewm(alpha=(1-lam), adjust=False).mean()
        vols[t] = np.sqrt(ewvar)
    before = len(pd.read_csv(out_csv)) if os.path.exists(out_csv) else 0
    atomic_write(vols, out_csv)
    after = len(vols)
    log_update(out_csv, max(0, after-before), "updated", "EWMA from polygon")

# ====================== MAIN ======================
def main() -> None:
    print("🔧 ONE-BUTTON MASTER UPDATER (Py3.9, API key hardcoded)")
    print(f"⏱  Rate limit: {SLEEP_SEC:.2f}s/call · 🧮 {len(TICKERS)} tickers")
    print(f"🕒 NY Now: {datetime.now(NY).strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Minute snapshots
    update_spy_0915(FILES["spy_0915"])
    update_snapshot_wide(dt_time(9,0),   FILES["snap_0900"], TICKERS, prefer_past=True)
    update_snapshot_wide(dt_time(10,30), FILES["snap_1030"], TICKERS, prefer_past=True)

    # Daily opens & closes
    update_daily_opens(FILES["open_wide"], TICKERS)
    update_hist_closes(FILES["hist_close"], TICKERS)

    # SPY prev close + return
    update_spy_prev_close(FILES["spy_prev_close"])

    # GARCH vols
    before_len = len(pd.read_csv(FILES["garch"])) if os.path.exists(FILES["garch"]) else 0
    compute_garch_from_local_closes(FILES["garch"], FILES["hist_close"])
    after_len = len(pd.read_csv(FILES["garch"])) if os.path.exists(FILES["garch"]) else 0
    if after_len <= before_len:
        compute_garch_from_polygon_closes(FILES["garch"], TICKERS, start="2021-01-01")

    print_final_summary()

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] in {"--summary-only","--status"}:
            print("🔎 Running in --summary-only mode")
            print_status_only()
        else:
            main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        print_final_summary()
