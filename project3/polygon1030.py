import requests
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
import time
import os

# === CONFIGURATION ===
API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"
TARGET_TIME = dt_time(10, 30)
OUTPUT_FILE = "stock_prices_1030_wide_format.csv"

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

def get_polygon_ticker(ticker, date):
    if ticker == "META" and date < datetime(2022, 6, 9):
        return "FB"
    elif ticker == "BRK.B":
        return "BRK/B"
    else:
        return ticker

def fetch_closest_1030_price(ticker, date_str):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{date_str}/{date_str}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
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
            return closest_bar["o"], None
        return None, "Closest to 10:30 not found"
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    # Determine start date from existing CSV if available
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        # Clean the dataframe - remove any rows with missing dates
        existing_df = existing_df.dropna(subset=['Date'])
        # Convert Date column to string to handle mixed types
        existing_df['Date'] = existing_df['Date'].astype(str)
        # Filter out any invalid date formats (keep only YYYY-MM-DD format)
        existing_df = existing_df[existing_df['Date'].str.match(r'^\d{4}-\d{2}-\d{2}$')]
        
        # IMPORTANT: Only consider dates up to today to avoid future date corruption
        today_str = datetime.today().strftime("%Y-%m-%d")
        existing_df = existing_df[existing_df['Date'] <= today_str]
        
        if len(existing_df) > 0:
            last_date_str = existing_df["Date"].max()
            START_DATE = datetime.strptime(last_date_str, "%Y-%m-%d") + timedelta(days=1)
            print(f"🔄 Found {len(existing_df)} valid records. Resuming from {START_DATE.date()}...")
        else:
            START_DATE = datetime(2021, 1, 4)
            print("🔄 No valid dates found, starting fresh...")
    else:
        START_DATE = datetime(2021, 1, 4)

    END_DATE = datetime.today()
    total_days = (END_DATE - START_DATE).days

    print(f"📊 Fetching 10:30 AM prices from {START_DATE.date()} to {END_DATE.date()}...")

    for day_offset in range(total_days + 1):
        date = START_DATE + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        if date.weekday() >= 5:
            continue

        print(f"\n📅 {date_str}")
        
        # Collect all prices for this date in wide format
        daily_data = {"Date": date_str}
        
        for ticker in TICKERS:
            polygon_ticker = get_polygon_ticker(ticker, date)
            price, error = fetch_closest_1030_price(polygon_ticker, date_str)

            if price is not None:
                daily_data[ticker] = price
                print(f"  ✅ {ticker}: {price}")
            else:
                daily_data[ticker] = None  # or pd.NA
                print(f"  ❌ {ticker}: {error}")

            time.sleep(0.15)
        
        # Save the entire day's data as one row
        new_row = pd.DataFrame([daily_data])
        if os.path.exists(OUTPUT_FILE):
            new_row.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
        else:
            new_row.to_csv(OUTPUT_FILE, mode='w', header=True, index=False)

    print(f"\n✅ All done! Data saved to {OUTPUT_FILE}")