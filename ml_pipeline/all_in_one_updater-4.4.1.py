#!/usr/bin/env python3
# comprehensive_updater.py
# Updates ALL your CSV files and fixes the Jan 4 - Feb 19, 2021 data quality issue

import os, shutil, time, requests
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict
import pandas as pd
import numpy as np

API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"
API_KEY = os.getenv("POLYGON_API_KEY", API_KEY)

UPDATE_WHAT = os.getenv("UPDATE_WHAT", "CLOSES,VIX,0900,1030,SPY915,PREOPEN,GARCH,TA").upper().split(",")
FIXED_DELAY = float(os.getenv("POLYGON_FIXED_DELAY", "0.15"))
MIN_COMPLETENESS = float(os.getenv("MIN_COMPLETENESS", "0.5"))
FILL_GAPS = os.getenv("FILL_GAPS", "1").lower() in ("1","true","yes")

# Your file mappings
FILE_MAPPINGS = {
    "CLOSES": "historical_closing_prices_old.csv",
    "VIX": "vix_open_clean.csv", 
    "0900": "stock_prices_0900_wide_format.csv",
    "1030": "stock_prices_1030_wide_format.csv",
    "SPY915": "spy_premarket_0915_prices.csv",
    "PREOPEN": "stock_open_prices_wide_format.csv",
    "GARCH": "garch.csv",
    "TA": "final_lstm_features.csv"
}

# Also check for the duplicate file
DUPLICATE_FILES = [
    "stock_prices_0900_wide_format 2.csv",
    "spy_prev_close_4pm.csv"
]

def poly_daily_bars(ticker: str, start: str, end: str):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
    r = requests.get(url, params={"apiKey": API_KEY})
    if r.status_code != 200:
        print(f"⚠️ API error for {ticker}: {r.status_code}")
        return []
    return r.json().get("results", [])

def poly_minute_bars(ticker: str, day: date, time_filter=None):
    """Get minute bars for a specific day, optionally filtered by time"""
    ds = pd.Timestamp(day).strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{ds}/{ds}"
    r = requests.get(url, params={"apiKey": API_KEY})
    if r.status_code != 200:
        return []
    
    bars = r.json().get("results", [])
    
    if time_filter:
        # Filter to specific time (like 9:00 AM, 10:30 AM, etc.)
        filtered_bars = []
        for bar in bars:
            bar_time = datetime.fromtimestamp(bar["t"]/1000)
            if time_filter(bar_time):
                filtered_bars.append(bar)
        return filtered_bars
    
    return bars

def extract_tickers_from_file(filepath: str) -> List[str]:
    """Extract ticker symbols from any CSV file"""
    if not os.path.exists(filepath):
        return []
    
    try:
        df = pd.read_csv(filepath, nrows=1)
        tickers = []
        
        for col in df.columns:
            if col.upper() not in ['DATE', 'TIME', 'TIMESTAMP']:
                # Handle different naming patterns
                if '_' in col:
                    ticker = col.split('_')[0]
                else:
                    ticker = col
                
                # Clean up ticker
                ticker = ticker.replace('.', '-').upper()
                if ticker and ticker not in ['VIX', 'SPY'] and len(ticker) <= 5:
                    tickers.append(ticker)
        
        return sorted(list(set(tickers)))
    except Exception as e:
        print(f"⚠️ Error reading {filepath}: {e}")
        return []

def find_quality_gaps(df: pd.DataFrame, min_completeness: float = 0.5) -> List[Tuple[date, date]]:
    """Find periods where data quality is poor"""
    if df.empty or 'Date' not in df.columns:
        return []
    
    df_sorted = df.sort_values('Date').copy()
    df_sorted['Date'] = pd.to_datetime(df_sorted['Date'], errors='coerce')
    df_sorted = df_sorted.dropna(subset=['Date'])
    
    data_cols = [col for col in df_sorted.columns if col != 'Date']
    if not data_cols:
        return []
    
    gaps = []
    consecutive_bad_days = []
    
    for _, row in df_sorted.iterrows():
        valid_count = row[data_cols].notna().sum()
        completeness = valid_count / len(data_cols)
        
        if completeness < min_completeness:
            consecutive_bad_days.append((row['Date'].date(), completeness))
        else:
            if len(consecutive_bad_days) >= 3:
                gap_start = consecutive_bad_days[0][0]
                gap_end = consecutive_bad_days[-1][0]
                avg_quality = sum(x[1] for x in consecutive_bad_days) / len(consecutive_bad_days)
                gaps.append((gap_start, gap_end))
                print(f"🚨 Quality gap: {gap_start} to {gap_end} ({len(consecutive_bad_days)} days, {avg_quality*100:.1f}% avg)")
            consecutive_bad_days = []
    
    if len(consecutive_bad_days) >= 3:
        gap_start = consecutive_bad_days[0][0]
        gap_end = consecutive_bad_days[-1][0] 
        avg_quality = sum(x[1] for x in consecutive_bad_days) / len(consecutive_bad_days)
        gaps.append((gap_start, gap_end))
        print(f"🚨 Quality gap: {gap_start} to {gap_end} ({len(consecutive_bad_days)} days, {avg_quality*100:.1f}% avg)")
    
    return gaps

def atomic_write(df: pd.DataFrame, path: str):
    """Safely write DataFrame to CSV with backup"""
    df_out = df.copy()
    if 'Date' in df_out.columns:
        df_out["Date"] = pd.to_datetime(df_out["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    
    tmp = path + ".tmp"
    df_out.to_csv(tmp, index=False)
    
    if os.path.exists(path):
        try:
            shutil.copy2(path, path + ".bak")
        except Exception:
            pass
    
    os.replace(tmp, path)
    
    try:
        chk = pd.read_csv(path)
        nrows = len(chk)
        pct_nan = (chk.isna().sum().sum() / (chk.shape[0]*chk.shape[1]) * 100) if nrows else 0.0
        print(f"📊 Saved {path} — rows={nrows}, cols={chk.shape[1]}, NaNs={pct_nan:.1f}%")
    except Exception:
        pass

def update_closing_prices(filepath: str):
    """Update historical closing prices"""
    print(f"\n🧰 Updating {filepath}...")
    
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        print(f"📝 Creating new file: {filepath}")
        df = pd.DataFrame(columns=['Date'])
    
    # Get tickers from file or use common ones
    tickers = extract_tickers_from_file(filepath)
    if not tickers:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "SPY", "NVDA"]
    
    print(f"🎯 Working with {len(tickers)} tickers")
    
    # Check for gaps
    if FILL_GAPS and not df.empty:
        gaps = find_quality_gaps(df, MIN_COMPLETENESS)
        for gap_start, gap_end in gaps:
            print(f"🔧 Filling gap: {gap_start} to {gap_end}")
            fill_gap_with_closes(df, tickers, gap_start, gap_end)
    
    # Update recent data
    last_date = df['Date'].max() if not df.empty else pd.Timestamp("2020-01-01")
    if pd.isna(last_date):
        last_date = pd.Timestamp("2020-01-01")
    
    start_date = (last_date + timedelta(days=1)).date()
    end_date = datetime.now().date()
    
    if start_date <= end_date:
        print(f"📅 Updating recent data: {start_date} to {end_date}")
        fill_gap_with_closes(df, tickers, start_date, end_date)
    
    atomic_write(df.sort_values('Date'), filepath)

def fill_gap_with_closes(df: pd.DataFrame, tickers: List[str], start_date: date, end_date: date):
    """Fill a gap with closing price data"""
    for ticker in tickers:
        bars = poly_daily_bars(ticker, start_date.isoformat(), end_date.isoformat())
        for bar in bars:
            bar_date = pd.to_datetime(bar["t"], unit="ms").date()
            
            # Ensure ticker column exists
            if ticker not in df.columns:
                df[ticker] = np.nan
            
            # Find or create row for this date
            mask = df['Date'].dt.date == bar_date
            if not mask.any():
                new_row = {col: np.nan for col in df.columns}
                new_row['Date'] = pd.Timestamp(bar_date)
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                mask = df['Date'].dt.date == bar_date
            
            df.loc[mask, ticker] = float(bar.get("c", np.nan))
        
        time.sleep(FIXED_DELAY)

def update_time_specific_prices(filepath: str, target_time: str):
    """Update files with specific time prices (9:00 AM, 10:30 AM, etc.)"""
    print(f"\n🧰 Updating {filepath} for {target_time}...")
    
    if os.path.exists(filepath):
        df = pd.read_csv(filepath) 
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        df = pd.DataFrame(columns=['Date'])
    
    tickers = extract_tickers_from_file(filepath)
    if not tickers:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "SPY"]
    
    # Time filter function
    if target_time == "0900":
        time_filter = lambda dt: dt.hour == 9 and dt.minute == 0
    elif target_time == "1030":
        time_filter = lambda dt: dt.hour == 10 and dt.minute == 30
    elif target_time == "0915":
        time_filter = lambda dt: dt.hour == 9 and dt.minute == 15
    else:
        time_filter = None
    
    # Check for gaps and update
    if FILL_GAPS and not df.empty:
        gaps = find_quality_gaps(df, MIN_COMPLETENESS)
        for gap_start, gap_end in gaps:
            fill_gap_with_intraday(df, tickers, gap_start, gap_end, time_filter)
    
    atomic_write(df.sort_values('Date'), filepath)

def fill_gap_with_intraday(df: pd.DataFrame, tickers: List[str], start_date: date, end_date: date, time_filter):
    """Fill gap with intraday price data"""
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Business days only
            for ticker in tickers:
                bars = poly_minute_bars(ticker, current_date, time_filter)
                if bars:
                    price = bars[0].get("c", np.nan)
                    
                    if ticker not in df.columns:
                        df[ticker] = np.nan
                    
                    mask = df['Date'].dt.date == current_date
                    if not mask.any():
                        new_row = {col: np.nan for col in df.columns}
                        new_row['Date'] = pd.Timestamp(current_date)
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        mask = df['Date'].dt.date == current_date
                    
                    df.loc[mask, ticker] = float(price)
                
                time.sleep(FIXED_DELAY)
        
        current_date += timedelta(days=1)

def update_vix(filepath: str):
    """Update VIX data"""
    print(f"\n🧰 Updating {filepath}...")
    
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        df = pd.DataFrame(columns=['Date', 'VIX'])
    
    if FILL_GAPS and not df.empty:
        gaps = find_quality_gaps(df, MIN_COMPLETENESS)
        for gap_start, gap_end in gaps:
            fill_gap_with_vix(df, gap_start, gap_end)
    
    # Update recent VIX
    last_date = df['Date'].max() if not df.empty else pd.Timestamp("2020-01-01") 
    start_date = (last_date + timedelta(days=1)).date()
    end_date = datetime.now().date()
    
    if start_date <= end_date:
        fill_gap_with_vix(df, start_date, end_date)
    
    atomic_write(df.sort_values('Date'), filepath)

def fill_gap_with_vix(df: pd.DataFrame, start_date: date, end_date: date):
    """Fill VIX data gap"""
    bars = poly_daily_bars("I:VIX", start_date.isoformat(), end_date.isoformat())
    for bar in bars:
        bar_date = pd.to_datetime(bar["t"], unit="ms").date()
        
        mask = df['Date'].dt.date == bar_date
        if not mask.any():
            new_row = {'Date': pd.Timestamp(bar_date), 'VIX': np.nan}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            mask = df['Date'].dt.date == bar_date
        
        df.loc[mask, 'VIX'] = float(bar.get("c", np.nan))

def update_technical_analysis():
    """Recompute technical analysis in final_lstm_features.csv"""
    filepath = FILE_MAPPINGS["TA"]
    closes_file = FILE_MAPPINGS["CLOSES"]
    
    print(f"\n🧮 Updating technical analysis in {filepath}...")
    
    if not os.path.exists(closes_file):
        print(f"⚠️ No closes file found at {closes_file}")
        return
    
    closes = pd.read_csv(closes_file)
    closes['Date'] = pd.to_datetime(closes['Date'], errors='coerce')
    closes = closes.dropna(subset=['Date']).sort_values('Date')
    
    # Compute TA for each ticker
    ta_frames = []
    for ticker in [col for col in closes.columns if col != 'Date']:
        prices = pd.to_numeric(closes[ticker], errors='coerce')
        if prices.isna().all():
            continue
        
        df_ta = pd.DataFrame({'Date': closes['Date']})
        
        # RSI 14
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_ta[f"{ticker}_rsi14"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        df_ta[f"{ticker}_macd"] = ema12 - ema26
        
        # Bollinger Band Position
        sma20 = prices.rolling(20).mean()
        std20 = prices.rolling(20).std()
        df_ta[f"{ticker}_bbp"] = (prices - sma20) / (2 * std20)
        
        ta_frames.append(df_ta)
    
    if not ta_frames:
        print("⚠️ No TA computed")
        return
    
    # Merge all TA data
    df_ta = ta_frames[0]
    for df in ta_frames[1:]:
        df_ta = df_ta.merge(df, on='Date', how='outer')
    
    atomic_write(df_ta, filepath)

def run_comprehensive_update():
    """Run updates for all specified file types"""
    print("🏁 Starting comprehensive update...")
    
    for update_type in UPDATE_WHAT:
        if update_type == "CLOSES":
            update_closing_prices(FILE_MAPPINGS["CLOSES"])
        elif update_type == "VIX":
            update_vix(FILE_MAPPINGS["VIX"])
        elif update_type == "0900":
            update_time_specific_prices(FILE_MAPPINGS["0900"], "0900")
        elif update_type == "1030":
            update_time_specific_prices(FILE_MAPPINGS["1030"], "1030")
        elif update_type == "SPY915":
            update_time_specific_prices(FILE_MAPPINGS["SPY915"], "0915")
        elif update_type == "PREOPEN":
            update_closing_prices(FILE_MAPPINGS["PREOPEN"])  # Use closes method for opens
        elif update_type == "TA":
            update_technical_analysis()
        else:
            print(f"⚠️ Unknown update type: {update_type}")

if __name__ == "__main__":
    print("🧩 Comprehensive Multi-File Updater")
    print("🕐", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("📂 Target files:", list(FILE_MAPPINGS.values()))
    print("🔧 Updates:", UPDATE_WHAT)
    print("=" * 60)
    
    run_comprehensive_update()
    
    print("\n✅ Comprehensive update complete!")