import os
import warnings
from datetime import datetime, timedelta
import argparse

import pandas as pd
import yfinance as yf

"""
Bullet‑proof Relative Volume (RVOL) Downloader – Full Tickers with Volume Pivot
==============================================================================
Fetches daily Volume for a comprehensive basket of tickers, calculates RVOL in long
format, and also saves a wide-format CSV of raw volumes (one column per ticker).
Key features:

1. **Batch download** in one yf.download call (optional threads).
2. Supports correct Yahoo tickers (e.g. BRK-B).
3. Explicit control of `auto_adjust`, suppress FutureWarnings.
4. Customizable start/end dates and rolling window size.
5. Outputs:
   - **Long**   CSV (`Date,Ticker,Volume,RVOL`)  
   - **Wide**   CSV (`Date,AAPL,MSFT,...`) of raw volumes.
6. Graceful handling of missing/delisted tickers.
"""

# Suppress warnings about auto_adjust default change
warnings.filterwarnings("ignore", category=FutureWarning)

# Full ticker list (dot -> dash for BRK-B)
TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "JPM",
    "V", "LLY", "XOM", "MA", "AVGO", "JNJ", "HD", "PG", "MRK", "COST",
    "ABBV", "ADBE", "PEP", "CRM", "NFLX", "CVX", "WMT", "ACN", "AMD", "MCD",
    "KO", "BAC", "TMO", "INTC", "LIN", "AMGN", "TXN", "NEE", "PFE", "HON",
    "MS", "UNP", "QCOM", "PM", "GS", "NOW", "VRTX", "BKNG", "LOW", "RTX",
    "ISRG", "LMT", "IBM", "SBUX", "GE", "CAT", "BLK", "DE", "ADI", "MDT",
    "ORCL", "INTU", "CSCO", "MU", "ADSK", "PANW", "SNPS", "CDNS", "FTNT", "ZM",
    "REGN", "BMY", "GILD", "BIIB", "DHR", "CI", "ELV", "ZBH", "IDXX", "HCA",
    "SCHW", "AXP", "C", "TFC", "SPGI", "ICE", "CB", "AON", "MMC", "AMP",
    "SLB", "COP", "EOG", "PSX", "MPC", "OKE", "WMB", "KMI", "HAL", "FANG",
    "TGT", "DG", "ROST", "DLTR", "KHC", "SYY", "KR", "CL", "MNST", "CHD",
    "ETN", "EMR", "ROP", "PH", "ITW", "ROK", "FAST", "PCAR", "XYL", "AOS",
    "SO", "D", "DUK", "AEP", "EXC", "PEG", "ED", "WEC", "EIX", "XEL"
]
DEFAULT_START = "2021-01-01"
DEFAULT_WINDOW = 10


def download_data(tickers, start, end, threads=True, auto_adjust=False):
    """Batch download raw data for provided tickers."""
    return yf.download(
        tickers=" ".join(tickers),
        start=start,
        end=end,
        group_by="ticker",
        threads=threads,
        auto_adjust=auto_adjust,
        progress=False,
    )


def compute_long_rvol(raw, tickers, window):
    """Compute RVOL and return long-format DataFrame (Date,Ticker,Volume,RVOL)."""
    rows = []
    for sym in tickers:
        try:
            df = raw[sym][["Volume"]].copy()
        except Exception:
            print(f"⚠️ {sym} missing/delisted, skipped")
            continue
        df["RVOL"] = df["Volume"] / df["Volume"].rolling(window).mean()
        out = (
            df.reset_index()
              .assign(Ticker=sym)
              [["Date", "Ticker", "Volume", "RVOL"]]
        )
        rows.append(out)
    if not rows:
        raise RuntimeError("No valid data for any ticker.")
    return pd.concat(rows, ignore_index=True)


def save_wide_volume(raw, tickers, out_file):
    """Save wide-format CSV of raw volumes: Date + one column per ticker."""
    # Extract volume level (handles MultiIndex columns)
    volumes = raw.xs('Volume', axis=1, level=1)
    # Ensure only requested tickers and order
    volumes = volumes[tickers]
    volumes.index.name = 'Date'
    vol_df = volumes.reset_index()
    vol_df.to_csv(out_file, index=False)
    print(f"✅ Saved wide-volume CSV: {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Download RVOL and wide volumes for tickers.")
    parser.add_argument("--start", type=str, default=DEFAULT_START, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end",   type=str, default=(datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
                        help="End date (YYYY-MM-DD, exclusive)")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="Window size for RVOL")
    parser.add_argument("--threads", action="store_true", help="Enable multithreaded download")
    parser.add_argument("--adjust",  action="store_true", help="Set auto_adjust=True for adjusted OHLC")
    parser.add_argument("--long-out", type=str, default="rvol_daily.csv",
                        help="Output file for long-format RVOL CSV")
    parser.add_argument("--wide-out", type=str, default="rvol_daily_cleaned.csv",
                        help="Output file for wide-format volume CSV")
    args = parser.parse_args()

    # Step 1: download raw
    raw = download_data(TICKERS, args.start, args.end, threads=args.threads, auto_adjust=args.adjust)

    # Step 2: compute long RVOL and save
    long_df = compute_long_rvol(raw, TICKERS, args.window)
    if os.path.exists(args.long_out):
        os.rename(args.long_out, args.long_out + ".backup")
    long_df.to_csv(args.long_out, index=False, float_format="%.4f")
    print(f"✅ Saved long RVOL CSV: {args.long_out}")

    # Step 3: save wide volume CSV
    if os.path.exists(args.wide_out):
        os.rename(args.wide_out, args.wide_out + ".backup")
    save_wide_volume(raw, TICKERS, args.wide_out)

if __name__ == "__main__":
    main()
