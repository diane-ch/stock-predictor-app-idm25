import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# === Configuration ===
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'UNH', 'V']
CSV_FILE = 'stock_data_v2.csv'
START_DATE = '2020-01-01'
END_DATE = datetime.today().strftime('%Y-%m-%d')


def fetch_data(tickers, start, end):
    print(f"Fetching from {start} to {end}...")
    data = yf.download(tickers, start=start, end=end, group_by='ticker', progress=False)

    # Create multi-index DataFrame: Date x Ticker, Columns: Open, High, Low, Close
    records = []
    for ticker in tickers:
        df = data[ticker][['Open', 'High', 'Low', 'Close']].copy()
        df['Ticker'] = ticker
        df = df.reset_index()
        records.append(df)

    combined_df = pd.concat(records)
    combined_df.set_index(['Date', 'Ticker'], inplace=True)
    combined_df.sort_index(inplace=True)
    return combined_df



if __name__ == '__main__':
    if os.path.exists(CSV_FILE):
        print(f"Found existing {CSV_FILE}")
        existing_df = pd.read_csv(CSV_FILE, parse_dates=['Date'])
        existing_df.set_index(['Date', 'Ticker'], inplace=True)
        last_date = existing_df.index.get_level_values('Date').max()
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Last saved date: {last_date.date()}")
    else:
        print("No existing data — starting fresh")
        existing_df = pd.DataFrame()
        start_date = START_DATE

    # Fetch new data
    new_data = fetch_data(TICKERS, start=start_date, end=END_DATE)

    if not new_data.empty:
        # Drop overlapping rows if any
        new_data = new_data[~new_data.index.isin(existing_df.index)]

        if not new_data.empty:
            combined = pd.concat([existing_df, new_data])
            combined.sort_index(inplace=True)
            combined.reset_index().to_csv(CSV_FILE, index=False)
            print(f"Appended {len(new_data)} new rows — saved to {CSV_FILE}")
        else:
            print("No new rows to append.")
    else:
        print("No new data to append.")
