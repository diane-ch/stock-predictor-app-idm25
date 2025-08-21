import requests
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
import time
import os

import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURATION ===
API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"
TARGET_TIME = dt_time(9, 15)
OUTPUT_FILE = "spy_premarket_0915_prices.csv"
TICKER = "SPY"

def fetch_closest_915_price(ticker, date_str):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date_str}/{date_str}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "includeOutsideHours": "true",
        "apiKey": API_KEY
    }

    try:
        res = requests.get(url, params=params)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"

        data = res.json().get("results", [])
        if not data:
            return None, "No data (holiday or no trading)"

        closest_bar = None
        min_diff = float("inf")
        for bar in data:
            ts = datetime.fromtimestamp(bar["t"] / 1000)
            diff = abs((datetime.combine(ts.date(), ts.time()) - datetime.combine(ts.date(), TARGET_TIME)).total_seconds())

            if diff < min_diff:
                min_diff = diff
                closest_bar = bar

        if closest_bar:
            return closest_bar["c"], None
        return None, "Closest to 9:15 not found"
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    # Read existing CSV to find where to resume
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            existing_df.columns = existing_df.columns.str.strip()
            
            # Fix case sensitivity - handle both 'Date' and 'date'
            if 'date' in existing_df.columns:
                existing_df = existing_df.rename(columns={'date': 'Date'})
                print("🔧 Renamed 'date' column to 'Date'")
            elif 'Date' not in existing_df.columns:
                print(f"❌ Column names found: {list(existing_df.columns)}")
                print("❌ Neither 'Date' nor 'date' column found. Please check your CSV file.")
                exit(1)
            
            print(f"📊 Found existing CSV with {len(existing_df)} records")
            
            last_date_str = existing_df['Date'].max()
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            START_DATE = last_date + timedelta(days=1)
            
            print(f"📅 Last date in CSV: {last_date_str}")
            print(f"▶️  Resuming from: {START_DATE.date()}")
            
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            print("💡 Try cleaning your CSV file or check for formatting issues")
            exit(1)
    else:
        print("❌ No existing CSV found!")
        exit(1)

    END_DATE = datetime.today()
    
    business_days_to_fetch = 0
    current_date = START_DATE
    while current_date <= END_DATE:
        if current_date.weekday() < 5:
            business_days_to_fetch += 1
        current_date += timedelta(days=1)
    
    if business_days_to_fetch == 0:
        print("✅ CSV is already up to date! No new data to fetch.")
        exit()
    
    print(f"🎯 Need to fetch {business_days_to_fetch} business days")
    print(f"⏱️  Estimated time: {business_days_to_fetch * 0.15 / 60:.1f} minutes")
    print(f"🚀 Starting data fetch...\n")

    fetched_count = 0
    for day_offset in range((END_DATE - START_DATE).days + 1):
        date = START_DATE + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        if date.weekday() >= 5:
            continue

        print(f"📅 {date_str} ({fetched_count + 1}/{business_days_to_fetch})")
        
        price, error = fetch_closest_915_price(TICKER, date_str)

        if price is not None:
            new_row = pd.DataFrame([{"Date": date_str, "spy_0915_price": price}])
            file_exists = os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0
            new_row.to_csv(OUTPUT_FILE, mode='a', header=not file_exists, index=False)
            print(f"  ✅ SPY: {price} - SAVED")
        else:
            print(f"  ❌ SPY: {error}")

        fetched_count += 1
        time.sleep(0.15)

    print(f"\n🎉 COMPLETE! Fetched {fetched_count} new records")
    
    final_df = pd.read_csv(OUTPUT_FILE)
    final_df.columns = final_df.columns.str.strip()
    print(f"📈 Total records in CSV: {len(final_df)}")
    print(f"📅 Full date range: {final_df['Date'].min()} to {final_df['Date'].max()}")