#!/usr/bin/env python3
"""
vixfinal.py

Writes/refreshes vix_open_clean.csv with Date,Open.

Before the US cash open (14:30 UK), if today's official Open isn't available:
  1) use live ^VIX last price
  2) else use yesterday's Close

After 14:30 UK:
  - Only record today's official Open (no fallback).

Merging is stable and version-proof (outer-join with suffixes; "your" updated value wins).
Verbose logs show exactly what happened.
"""

from __future__ import annotations

import sys
import time
import math
import argparse
from datetime import datetime, timedelta

import pandas as pd
import pytz

try:
    import yfinance as yf
except Exception:
    print("This script requires 'yfinance'. Install: pip install yfinance pandas pytz")
    raise

# ---------------------------- Config ---------------------------------

OUTPUT_CSV_DEFAULT = "vix_open_clean.csv"
DOWNLOAD_LOOKBACK_DAYS = 14
RETRIES = 3
RETRY_SLEEP_SEC = 2.0

LONDON_TZ = pytz.timezone("Europe/London")
UK_OPEN_HOUR = 14
UK_OPEN_MINUTE = 30


# ---------------------------- Helpers --------------------------------

def now_london() -> datetime:
    return datetime.now(tz=LONDON_TZ)


def uk_open_dt_on(date_: datetime) -> datetime:
    return LONDON_TZ.localize(datetime(date_.year, date_.month, date_.day, UK_OPEN_HOUR, UK_OPEN_MINUTE))


def is_before_uk_open(now_: datetime) -> bool:
    return now_ < uk_open_dt_on(now_)


def download_vix_history(start: datetime, end: datetime) -> pd.DataFrame:
    """
    Download recent VIX daily candles with retries.
    Returns DataFrame indexed by date (tz-naive) with columns incl. Open, Close.
    """
    last_err = None
    for _ in range(RETRIES):
        try:
            df = yf.download(
                "^VIX",
                start=start.date(),
                end=(end + timedelta(days=1)).date(),  # inclusive end
                interval="1d",
                auto_adjust=False,
                progress=False,
            )
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
                return df
            last_err = RuntimeError("Empty dataframe returned from yfinance.")
        except Exception as e:
            last_err = e
        time.sleep(RETRY_SLEEP_SEC)
    raise last_err


def get_live_last_price() -> float | None:
    """
    Try to get a live last price for ^VIX. Returns None if unavailable.
    """
    for _ in range(RETRIES):
        try:
            t = yf.Ticker("^VIX")
            fi = getattr(t, "fast_info", None)
            if fi and "last_price" in fi and fi["last_price"] is not None and not math.isnan(fi["last_price"]):
                return float(fi["last_price"])
            hist = t.history(period="1d", interval="1m")
            if isinstance(hist, pd.DataFrame) and not hist.empty and "Close" in hist:
                last = hist["Close"].dropna()
                if not last.empty:
                    return float(last.iloc[-1])
        except Exception:
            pass
        time.sleep(RETRY_SLEEP_SEC)
    return None


def load_existing_csv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        if "Date" not in df.columns or "Open" not in df.columns:
            raise ValueError("CSV must contain 'Date' and 'Open' columns.")
        df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
        df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Open"])
    except Exception:
        return pd.DataFrame(columns=["Date", "Open"])


def save_csv(df: pd.DataFrame, path: str) -> None:
    out = df.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out = out.sort_values("Date")
    out.to_csv(path, index=False)


# ---------------------------- Core Logic ------------------------------

def compute_today_open_value(daily: pd.DataFrame, now_dt: datetime, before_open: bool) -> tuple[float | None, str]:
    """
    Decide the value to store for today's 'Open' and return (value, source_label).
    """
    today_key = pd.Timestamp(now_dt.date())
    yday_key = today_key - pd.Timedelta(days=1)

    has_today = today_key in daily.index
    has_yday = yday_key in daily.index

    todays_open = None
    if has_today and "Open" in daily:
        v = daily.loc[today_key, "Open"]
        if pd.notna(v):
            todays_open = float(v)

    if not before_open:
        # After 14:30 UK: only accept true Open if present
        return (todays_open, "official_open" if todays_open is not None else "none_after_open")

    # Before open: try Open, then live, then yesterday close
    if todays_open is not None:
        return (todays_open, "official_open_preopen")

    live = get_live_last_price()
    if live is not None and not math.isnan(live) and live > 0:
        return (float(live), "live_last_price")

    if has_yday and "Close" in daily:
        yclose = daily.loc[yday_key, "Close"]
        if pd.notna(yclose):
            return (float(yclose), "yesterday_close")

    return (None, "none_preopen")


def upsert_today_row(existing: pd.DataFrame, date_: datetime, value: float | None) -> pd.DataFrame:
    """
    Prefer updating today's value if present; insert if missing and we have a value.
    """
    df = existing.copy()
    date_key = pd.Timestamp(date_.date())
    mask = (df["Date"] == date_key)

    if mask.any():
        if value is not None:
            df.loc[mask, "Open"] = value
    else:
        if value is not None:
            df = pd.concat([df, pd.DataFrame([{"Date": date_key, "Open": value}])], ignore_index=True)
    return df


def merge_recent_with_updated(daily: pd.DataFrame, updated: pd.DataFrame) -> pd.DataFrame:
    """
    Version-proof merge:
      - Build 'recent' from daily (Date index → column)
      - Outer-join on Date with suffixes
      - Take updated's Open when present; else recent's Open
    """
    recent = (
        daily[["Open"]]
        .rename_axis("Date")
        .reset_index()
    )
    recent["Date"] = pd.to_datetime(recent["Date"]).dt.normalize()

    # Ensure types align
    updated2 = updated.copy()
    updated2["Date"] = pd.to_datetime(updated2["Date"]).dt.normalize()

    # Outer join on Date; suffixes so both Open columns survive
    merged = recent.merge(updated2, on="Date", how="outer", suffixes=("_r", "_u"))

    # Prefer user's updated value
    merged["Open"] = merged["Open_u"].combine_first(merged["Open_r"])

    # Keep only Date, Open
    merged = merged[["Date", "Open"]].sort_values("Date").reset_index(drop=True)
    return merged


def main():
    parser = argparse.ArgumentParser(description="Build/refresh VIX Open CSV with smart pre-open fallback.")
    parser.add_argument("--out", default=OUTPUT_CSV_DEFAULT, help="Output CSV path (default: vix_open_clean.csv)")
    parser.add_argument("--lookback", type=int, default=DOWNLOAD_LOOKBACK_DAYS, help="Download lookback days (default: 14)")
    args = parser.parse_args()

    now = now_london()
    before_open = is_before_uk_open(now)

    print("=== VIX Open CSV Refresher ===")
    print(f"Now (Europe/London): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Before 14:30 UK open? {before_open}")
    print(f"Target CSV path: {args.out}")

    # 1) Load existing CSV (if present)
    existing = load_existing_csv(args.out)
    print(f"Loaded existing rows: {len(existing)}")

    # 2) Download fresh daily data for a window around today
    start = now - timedelta(days=max(5, args.lookback))
    end = now
    daily = download_vix_history(start, end)
    print(f"Downloaded daily rows: {len(daily)} (from {daily.index.min().date() if not daily.empty else 'n/a'} to {daily.index.max().date() if not daily.empty else 'n/a'})")

    # 3) Decide today's value
    value, source = compute_today_open_value(daily, now, before_open)
    print(f"Decision for today: source={source}, value={value}")

    # 4) Upsert into existing
    updated = upsert_today_row(existing, now, value)
    print(f"Rows after upsert: {len(updated)}")

    # 5) Merge with recent download (UPDATED wins)
    merged = merge_recent_with_updated(daily, updated)
    print(f"Rows after merge: {len(merged)}  |  Last date in file: {merged['Date'].max().date() if not merged.empty else 'n/a'}")

    # 6) Save
    save_csv(merged, args.out)
    print(f"Saved CSV to: {args.out}")

    # 7) Notes if unchanged
    if value is None and not before_open:
        print("Note: After 14:30 UK we only record the official Open. If Yahoo hasn't published today's Open (e.g., weekend/holiday), the file may remain unchanged.")
    elif value is None and before_open:
        print("Note: No live/yesterday close available (rare). File may be unchanged.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
