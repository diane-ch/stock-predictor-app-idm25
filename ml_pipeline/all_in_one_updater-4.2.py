#!/usr/bin/env python3
# all_in_one_updater-4.2.py
#
# Polygon-only append/repair updater for:
#   - Intraday 09:00 & 10:30 snapshots
#   - SPY 09:15
#   - Daily closes
#   - VIX (daily)
#   - TA cleaner for final_lstm_features.csv
#
# Env vars still supported for flexibility, but API key is baked in.

import os, shutil, time, requests
from datetime import datetime, timedelta, date
from typing import List
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------
# ENV CONFIG
# ---------------------------------------------------------------------
# 🔐 Your Polygon API key baked in:
API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"

# Allow env var override
API_KEY = os.getenv("POLYGON_API_KEY", API_KEY)

UPDATE_WHAT = os.getenv("UPDATE_WHAT", "1030,0900,CLOSES,VIX,SPY915,TA").upper().split(",")
REPAIR_LOOKBACK_DAYS = int(os.getenv("REPAIR_LOOKBACK_DAYS", "5"))
INTRADAY_MAX_GAP_SEC = int(os.getenv("INTRADAY_MAX_GAP_SEC", "2000"))
REPAIR_FROM = os.getenv("REPAIR_FROM_YYYY_MM_DD", "").strip() or None
REPAIR_TO   = os.getenv("REPAIR_TO_YYYY_MM_DD", "").strip() or None
FIXED_DELAY = float(os.getenv("POLYGON_FIXED_DELAY", "0.15"))
OVERWRITE_FORCED = os.getenv("OVERWRITE_FORCED", "1").lower() in ("1","true","yes")
ACCEPT_ANY = os.getenv("INTRADAY_ACCEPT_ANY", "1").lower() in ("1","true","yes")

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def business_days(start: datetime, end: datetime) -> List[datetime]:
    return list(pd.date_range(start=start, end=end, freq="B").to_pydatetime())

def poly_minute_bars(ticker: str, day: date):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{day}/{day}"
    r = requests.get(url, params={"apiKey": API_KEY})
    if r.status_code != 200:
        return []
    return r.json().get("results", [])

def poly_daily_bars(ticker: str, start: str, end: str):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
    r = requests.get(url, params={"apiKey": API_KEY})
    if r.status_code != 200:
        return []
    return r.json().get("results", [])

def nearest_bar(bars, target: datetime):
    if not bars:
        return None, None
    times = [datetime.fromtimestamp(b["t"]/1000) for b in bars]
    gaps = [abs((t - target).total_seconds()) for t in times]
    idx = int(np.argmin(gaps))
    return bars[idx], gaps[idx]

def atomic_write(df: pd.DataFrame, path: str):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    os.replace(tmp, path)
    print(f"📊 Saved {path} — rows={len(df)}, cols={df.shape[1]}, overall NaNs={df.isna().mean().mean()*100:.2f}%")

# ---------------------------------------------------------------------
# CORE: Update intraday at a given time
# ---------------------------------------------------------------------
def update_intraday_at_time(path: str, tickers: List[str], target_time: datetime):
    print(f"🧰 {path}: updating…")
    exist = pd.read_csv(path, parse_dates=["Date"]) if os.path.exists(path) else pd.DataFrame(columns=["Date"]+tickers)

    # --- determine dates to repair ---
    repair_dates: List[date] = []

    if REPAIR_FROM and REPAIR_TO:
        rf = datetime.fromisoformat(REPAIR_FROM)
        rt = datetime.fromisoformat(REPAIR_TO)
        if rf > rt: rf, rt = rt, rf
        forced_days = business_days(rf, rt)
        repair_dates = [d.date() for d in forced_days]

    if not repair_dates and not exist.empty:
        mask_incomplete = exist[tickers].isna().any(axis=1)
        repair_dates = sorted(set(exist.loc[mask_incomplete, "Date"].dt.date.tolist()))
        if REPAIR_LOOKBACK_DAYS > 0 and repair_dates:
            cutoff = (datetime.now().date() - timedelta(days=REPAIR_LOOKBACK_DAYS-1))
            repair_dates = [d for d in repair_dates if d >= cutoff]

    print(f"🔧 Will repair {len(repair_dates)} date(s).")

    for d in repair_dates:
        for tkr in tickers:
            bars = poly_minute_bars(tkr, d)
            if not bars: continue
            bar, gap = nearest_bar(bars, datetime.combine(d, target_time.time()))
            if bar and (ACCEPT_ANY or gap <= INTRADAY_MAX_GAP_SEC):
                val = bar.get("o") or bar.get("c")
                if OVERWRITE_FORCED:
                    exist.loc[exist["Date"].dt.date==d, tkr] = val
                else:
                    if exist.loc[exist["Date"].dt.date==d, tkr].isna().any():
                        exist.loc[exist["Date"].dt.date==d, tkr] = val
                print(f"  ✅ {tkr:<5} : {val} (gap={gap:.0f}s)")
            else:
                print(f"  ❔ {tkr:<5} : NaN (gap={gap}s)")
            time.sleep(FIXED_DELAY)

    atomic_write(exist, path)

# ---------------------------------------------------------------------
# SPY 09:15 updater
# ---------------------------------------------------------------------
def update_spy_0915(path: str):
    tkr = "SPY"
    target = datetime(2021,1,1,9,15)  # time part only
    exist = pd.read_csv(path, parse_dates=["Date"]) if os.path.exists(path) else pd.DataFrame(columns=["Date",tkr])
    all_days = exist["Date"].dt.date.unique() if not exist.empty else []
    for d in all_days:
        bars = poly_minute_bars(tkr, d)
        bar, gap = nearest_bar(bars, datetime.combine(d, target.time()))
        if bar and (ACCEPT_ANY or gap <= INTRADAY_MAX_GAP_SEC):
            exist.loc[exist["Date"].dt.date==d, tkr] = bar["c"]
            print(f"  ✅ SPY {d} : {bar['c']} (gap={gap:.0f}s)")
        else:
            print(f"  ❔ SPY {d} : NaN (gap={gap}s)")
        time.sleep(FIXED_DELAY)
    atomic_write(exist, path)

# ---------------------------------------------------------------------
# Daily closes updater
# ---------------------------------------------------------------------
def update_daily_closes(path: str, tickers: List[str]):
    print(f"🧰 {path}: updating closes…")
    exist = pd.read_csv(path, parse_dates=["Date"]) if os.path.exists(path) else pd.DataFrame(columns=["Date"]+tickers)
    last_date = exist["Date"].max().date() if not exist.empty else datetime(2020,1,1).date()
    today = datetime.now().date()
    for tkr in tickers:
        bars = poly_daily_bars(tkr, last_date.isoformat(), today.isoformat())
        for b in bars:
            d = datetime.fromtimestamp(b["t"]/1000).date()
            exist.loc[exist["Date"].dt.date==d, tkr] = b["c"]
            if not (exist["Date"].dt.date==d).any():
                exist = pd.concat([exist, pd.DataFrame([{"Date":d, tkr:b["c"]}])])
        time.sleep(FIXED_DELAY)
    atomic_write(exist.sort_values("Date"), path)

# ---------------------------------------------------------------------
# VIX updater (daily)
# ---------------------------------------------------------------------
def update_vix(path="vix.csv"):
    print("🧰 Updating VIX…")
    exist = pd.read_csv(path, parse_dates=["Date"]) if os.path.exists(path) else pd.DataFrame(columns=["Date","VIX"])
    last_date = exist["Date"].max().date() if not exist.empty else datetime(2020,1,1).date()
    today = datetime.now().date()
    bars = poly_daily_bars("VIX", last_date.isoformat(), today.isoformat())
    for b in bars:
        d = datetime.fromtimestamp(b["t"]/1000).date()
        exist.loc[exist["Date"].dt.date==d, "VIX"] = b["c"]
        if not (exist["Date"].dt.date==d).any():
            exist = pd.concat([exist, pd.DataFrame([{"Date":d, "VIX":b["c"]}])])
        time.sleep(FIXED_DELAY)
    atomic_write(exist.sort_values("Date"), path)

# ---------------------------------------------------------------------
# TA Cleaner
# ---------------------------------------------------------------------
def repair_ta_file(path="final_lstm_features.csv"):
    if not os.path.exists(path) or os.path.getsize(path)==0:
        print("⚠️ No TA file found to repair.")
        return
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]:"Date"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    dropped = [c for c in df.columns if c!="Date" and df[c].isna().mean()>0.8]
    df = df.drop(columns=dropped)
    for c in [c for c in df.columns if c!="Date"]:
        s = pd.to_numeric(df[c], errors="coerce")
        q1,q99 = s.quantile(0.01), s.quantile(0.99)
        df[c] = s.clip(q1,q99)
    atomic_write(df, path)
    print(f"✅ Repaired TA file → {path}")

# ---------------------------------------------------------------------
# RUNNER
# ---------------------------------------------------------------------
def run_all():
    tickers = ["AAPL","MSFT","GOOGL","AMZN","META","TSLA","SPY"]
    if "1030" in UPDATE_WHAT:
        update_intraday_at_time("stock_prices_1030_wide_format.csv", tickers, datetime(2021,1,1,10,30))
    if "0900" in UPDATE_WHAT:
        update_intraday_at_time("stock_prices_0900_wide_format.csv", tickers, datetime(2021,1,1,9,0))
    if "SPY915" in UPDATE_WHAT:
        update_spy_0915("spy_0915.csv")
    if "CLOSES" in UPDATE_WHAT:
        update_daily_closes("daily_closes.csv", tickers)
    if "VIX" in UPDATE_WHAT:
        update_vix("vix.csv")
    if "TA" in UPDATE_WHAT:
        repair_ta_file()

if __name__ == "__main__":
    print("🧩 Polygon Append+Repair Updater (v4.2)")
    print("🕒", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    extra = ""
    if REPAIR_FROM and REPAIR_TO:
        extra = f"  |  Forced repair: {REPAIR_FROM} → {REPAIR_TO}"
    print(f"⏱️ delay={FIXED_DELAY:.2f}s | max_gap={INTRADAY_MAX_GAP_SEC}s | lookback={REPAIR_LOOKBACK_DAYS} | overwrite_forced={OVERWRITE_FORCED} | accept_any={ACCEPT_ANY}{extra}")
    run_all()
