import os
import time as _time
from datetime import datetime, timedelta

import pandas as pd
import pytz
import yfinance as yf

"""
Bullet‑proof VIX downloader – *fixed*
====================================

Key fixes versus original script
--------------------------------
1. **Inclusive today** – yfinance’s `end` argument is *exclusive*. We therefore
   ask for *tomorrow* so that today’s bar is included.
2. **Don’t drop today** – We only drop rows whose **Open** is NaN *and* whose
   date is **older than today**. This keeps today’s row even before the market
   opens.
3. **Optional wait for market open** – If you launch the script before
   09:35 ET, it can automatically wait until the market is open so that the
   opening price is available.
"""

def wait_for_market_open(wait: bool = True):
    """Block until 09:35 America/New_York so that the VIX open is published."""

    if not wait:
        return

    ny = pytz.timezone("America/New_York")
    now_ny = datetime.now(tz=ny)
    open_ny = now_ny.replace(hour=9, minute=35, second=0, microsecond=0)

    if now_ny < open_ny:
        secs = int((open_ny - now_ny).total_seconds())
        mins, secs = divmod(secs, 60)
        print(f"⏳ Market not open yet – waiting {mins} min {secs} s…")
        _time.sleep((open_ny - now_ny).total_seconds())


def bulletproof_vix_download(
    start_date: str = "2021-01-01",
    output_file: str = "vix_open_clean.csv",
    keep_today_even_if_nan: bool = True,
    wait_until_market_open: bool = False,
):
    """Download ^VIX daily data and save a clean Date/Open CSV.

    Parameters
    ----------
    start_date : str
        First day to request (inclusive).
    output_file : str
        Destination CSV file.
    keep_today_even_if_nan : bool
        Keep today’s row even when the "Open" is NaN (before the market opens).
    wait_until_market_open : bool
        If *True* and script is executed before 09:35 ET, wait so that the
        opening price for today is published before downloading.
    """

    print("🛡️  BULLETPROOF VIX DOWNLOADER 2.0")

    # Optional blocking until the market is open
    wait_for_market_open(wait_until_market_open)

    today = datetime.utcnow().date()
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📊 Downloading VIX from {start_date} to {tomorrow_str} (exclusive)…")

    vix = yf.download("^VIX", start=start_date, end=tomorrow_str, progress=True)
    if vix.empty:
        raise RuntimeError("No data returned from Yahoo Finance.")

    # Flatten the DataFrame, keep only Date/Open
    df = vix.reset_index()
    if isinstance(df.columns[0], tuple):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df[["Date", "Open"]]

    # Drop NaNs, but keep today if requested
    if keep_today_even_if_nan:
        mask_old_nan = df["Open"].isna() & (df["Date"] < today.strftime("%Y-%m-%d"))
        df = df[~mask_old_nan]
    else:
        df = df.dropna(subset=["Open"])

    # Ensure numeric Open and final ordering
    df["Open"] = pd.to_numeric(df["Open"], errors="coerce").round(2)
    df = df.sort_values("Date").reset_index(drop=True)

    # Back‑up any existing file
    if os.path.exists(output_file):
        os.rename(output_file, output_file + ".backup")
        print(f"📦 Existing {output_file} backed‑up → {output_file}.backup")

    # Save clean CSV
    df.to_csv(
        output_file,
        index=False,
        float_format="%.2f",
        date_format="%Y-%m-%d",
        encoding="utf-8",
    )

    latest_date = df["Date"].max()
    latest_open = df.loc[df["Date"] == latest_date, "Open"].iloc[0]
    print(f"✅ Saved {len(df)} rows. Latest bar: {latest_date} · Open={latest_open}")

    return df


def emergency_vix_fix():
    """Attempt to salvage VIX data from previously saved CSVs."""

    print("\n🚨 EMERGENCY VIX REPAIR MODE")
    candidates = [
        "vix_open_prices.csv",
        "vix_open_prices_fixed.csv",
        "vix_daily_data.csv",
    ]

    for file in candidates:
        if not os.path.exists(file):
            continue

        print(f"🔧 Attempting to repair {file}…")
        for kwargs in (dict(), dict(engine="python"), dict(header=None)):
            try:
                df = pd.read_csv(file, **kwargs)
                if kwargs.get("header") is None:
                    df.columns = ["Date", "Open"]

                if df.empty:
                    continue

                df["Open"] = pd.to_numeric(df["Open"], errors="coerce")
                df = df.dropna()
                if len(df) > 100:
                    print(f"  🎯 Salvaged {len(df)} rows → returning repaired DataFrame")
                    return df
            except Exception as e:
                print("  ❌ Read attempt failed:", e)

    print("  ❌ No salvageable data found.")
    return None


if __name__ == "__main__":
    print("🛡️  BULLET‑PROOF VIX DATA DOWNLOAD (fixed)")

    # First try to repair old files
    repaired = emergency_vix_fix()
    if repaired is not None:
        print(f"🎯 Recovered {len(repaired)} historical rows from old file(s).")

    # Then perform a fresh download
    df = bulletproof_vix_download(wait_until_market_open=False)
    print(
        f"\n🎉 SUCCESS – clean data saved to 'vix_open_clean.csv' ({len(df)} rows, "
        f"{df['Date'].min()} → {df['Date'].max()})"
    )