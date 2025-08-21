#!/usr/bin/env python3
"""
Update missing dates in stock_prices_1030_wide_format.csv
Fills in missing data from August 4th, 2025 onwards using Polygon API
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, time as dt_time, date
import time
import os
from zoneinfo import ZoneInfo
from datetime import timezone
import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
# ================== CONFIG ==================
API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"  # Your working API key
TARGET_TIME = dt_time(10, 30)  # 10:30 ET
CSV_FILE = "stock_prices_1030_wide_format.csv"

# Missing data starts from August 4th, 2025
MISSING_START_DATE = date(2025, 8, 4)

TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "UNH", "JPM",
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

NY = ZoneInfo("America/New_York")

def get_polygon_ticker(ticker: str) -> str:
    """Symbol mapping for Polygon."""
    if ticker == "BRK.B":
        return "BRK/B"
    else:
        return ticker

def fetch_closest_1030_price(ticker: str, target_date: date) -> tuple:
    """
    Fetch the minute bar closest to 10:30 ET for a given ticker and date.
    Returns (price, error). Price is the minute OPEN nearest to 10:30 ET.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    polygon_ticker = get_polygon_ticker(ticker)
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{polygon_ticker}/range/1/minute/{date_str}/{date_str}"
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY}

    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"

        data = res.json().get("results", [])
        if not data:
            return None, "No data (holiday/no trading)"

        # Target timestamp in New York time
        target_ny = datetime.combine(target_date, TARGET_TIME, tzinfo=NY)

        closest_bar = None
        closest_diff = float("inf")
        chosen_pref = None  # 0 if <= target, 1 if > target (prefer <=)

        for bar in data:
            # Polygon 't' is epoch ms UTC
            ts_utc = datetime.fromtimestamp(bar["t"] / 1000, tz=timezone.utc)
            ts_ny = ts_utc.astimezone(NY)

            diff = abs((ts_ny - target_ny).total_seconds())
            # prefer bars at or before the target when distances tie
            pref = 0 if ts_ny <= target_ny else 1

            if (diff < closest_diff) or (diff == closest_diff and pref < chosen_pref):
                closest_diff = diff
                closest_bar = bar
                chosen_pref = pref

        if closest_bar:
            return float(closest_bar["o"]), None  # minute OPEN at ~10:30
        return None, "No data near 10:30"
        
    except Exception as e:
        return None, f"Exception: {e}"

def load_existing_csv():
    """Load and analyze existing CSV"""
    print("📖 Loading existing CSV...")
    
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV file not found: {CSV_FILE}")
        return None
    
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"   📊 Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Convert Date column
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        # Show date range
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        print(f"   📅 Date range: {min_date} → {max_date}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None

def find_missing_dates(df):
    """Find missing business dates from August 4th onwards"""
    print(f"\n🔍 Finding missing dates from {MISSING_START_DATE}...")
    
    # Get today's date
    today = datetime.now(NY).date()
    
    # Create list of all business days from Aug 4th to today
    all_business_days = []
    current_date = MISSING_START_DATE
    
    while current_date <= today:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            all_business_days.append(current_date)
        current_date += timedelta(days=1)
    
    # Find which dates are missing from the CSV
    existing_dates = set(df['Date'].tolist())
    missing_dates = [d for d in all_business_days if d not in existing_dates]
    
    print(f"   📊 Total business days from {MISSING_START_DATE}: {len(all_business_days)}")
    print(f"   📊 Missing dates: {len(missing_dates)}")
    
    if missing_dates:
        print(f"   📅 Missing range: {missing_dates[0]} → {missing_dates[-1]}")
        
        # Show sample of missing dates
        sample_size = min(5, len(missing_dates))
        print(f"   📋 Sample missing dates: {missing_dates[:sample_size]}")
    
    return missing_dates

def fetch_missing_data(missing_dates):
    """Fetch data for missing dates"""
    print(f"\n🚀 FETCHING DATA for {len(missing_dates)} missing dates...")
    
    new_rows = []
    
    for i, target_date in enumerate(missing_dates, 1):
        date_str = target_date.strftime("%Y-%m-%d")
        print(f"\n📅 [{i}/{len(missing_dates)}] Fetching {date_str}...")
        
        daily_data = {"Date": date_str}
        successful = 0
        
        for ticker in TICKERS:
            price, error = fetch_closest_1030_price(ticker, target_date)
            
            if price is not None:
                daily_data[ticker] = price
                successful += 1
                print(f"  ✅ {ticker:6s}: ${price:.2f}")
            else:
                daily_data[ticker] = None
                print(f"  ❌ {ticker:6s}: {error}")
            
            # Rate limiting
            time.sleep(0.12)
        
        print(f"  📊 Success: {successful}/{len(TICKERS)} tickers")
        new_rows.append(daily_data)
        
        # Progress update every 5 dates
        if i % 5 == 0:
            print(f"  🚀 Progress: {i}/{len(missing_dates)} dates completed")
    
    return new_rows

def update_csv(df, new_rows):
    """Update the CSV with new data"""
    print(f"\n💾 UPDATING CSV with {len(new_rows)} new rows...")
    
    if not new_rows:
        print("   ⚠️  No new data to add")
        return False
    
    try:
        # Create DataFrame from new rows
        new_df = pd.DataFrame(new_rows)
        
        # Ensure all ticker columns exist in both DataFrames
        all_columns = set(df.columns) | set(new_df.columns)
        
        # Add missing columns with NaN values
        for col in all_columns:
            if col not in df.columns:
                df[col] = None
            if col not in new_df.columns:
                new_df[col] = None
        
        # Reorder columns to match
        column_order = ['Date'] + [col for col in sorted(all_columns) if col != 'Date']
        df = df[column_order]
        new_df = new_df[column_order]
        
        # Combine DataFrames
        combined_df = pd.concat([df, new_df], ignore_index=True)
        
        # Sort by date
        combined_df['Date'] = pd.to_datetime(combined_df['Date'])
        combined_df = combined_df.sort_values('Date')
        combined_df['Date'] = combined_df['Date'].dt.strftime('%Y-%m-%d')
        
        # Remove duplicates (keep last occurrence)
        combined_df = combined_df.drop_duplicates(subset=['Date'], keep='last')
        
        # Save updated CSV
        combined_df.to_csv(CSV_FILE, index=False)
        
        print(f"   ✅ Updated CSV saved")
        print(f"   📊 Final CSV: {len(combined_df)} rows")
        print(f"   📅 New date range: {combined_df['Date'].min()} → {combined_df['Date'].max()}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error updating CSV: {e}")
        return False

def verify_update():
    """Verify the update was successful"""
    print(f"\n🔍 VERIFYING UPDATE...")
    
    try:
        df = pd.read_csv(CSV_FILE)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        # Check if we have data for some of the dates we just added
        today = datetime.now(NY).date()
        recent_dates = [today - timedelta(days=i) for i in range(5) if (today - timedelta(days=i)).weekday() < 5]
        
        print("   📊 Recent data check:")
        for check_date in recent_dates[:3]:  # Check last 3 business days
            date_row = df[df['Date'] == check_date]
            if len(date_row) > 0:
                # Check AMZN price as example
                amzn_price = date_row['AMZN'].iloc[0]
                if pd.notna(amzn_price):
                    print(f"     ✅ {check_date}: AMZN = ${amzn_price:.2f}")
                else:
                    print(f"     ⚠️  {check_date}: AMZN = NaN")
            else:
                print(f"     ❌ {check_date}: Date not found")
        
        print(f"   ✅ Verification complete")
        return True
        
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        return False

def main():
    """Main function"""
    print("🔧 CSV UPDATER: Fill Missing Dates from August 4th Onwards")
    print("=" * 60)
    print(f"Target CSV: {CSV_FILE}")
    print(f"Missing data starts: {MISSING_START_DATE}")
    print(f"API Key configured: {'✅' if API_KEY else '❌'}")
    print()
    
    if not API_KEY:
        print("❌ No API key configured!")
        sys.exit(1)
    
    # Step 1: Load existing CSV
    df = load_existing_csv()
    if df is None:
        sys.exit(1)
    
    # Step 2: Find missing dates
    missing_dates = find_missing_dates(df)
    if not missing_dates:
        print("✅ No missing dates found - CSV is up to date!")
        return
    
    # Step 3: Fetch missing data
    new_rows = fetch_missing_data(missing_dates)
    
    # Step 4: Update CSV
    success = update_csv(df, new_rows)
    if not success:
        sys.exit(1)
    
    # Step 5: Verify update
    verify_update()
    
    print(f"\n🎉 UPDATE COMPLETE!")
    print(f"   ✅ Added {len(new_rows)} new dates")
    print(f"   ✅ CSV updated: {CSV_FILE}")
    print(f"   🎯 Ready for predictions!")

if __name__ == "__main__":
    main()