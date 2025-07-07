"""
This .py script incrementally fetches data from Yahoo Finance and saves it into the CSV file "stock_data.csv".

Step-by-step:
Loads the existing CSV if any.
Fetches new stock data from Yahoo Finance incrementally.
Appends only new rows to the CSV file locally.
Then uploads the updated CSV to your specified S3 bucket/key with upload_to_s3()

To keep in mind: Yahoo Finance’s API does not provide intraday or today’s real-time data,
and it also often lags by 1–2 trading days. So do not panick it the last fetched data is not the current day.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# === Configuration ===
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'UNH', 'V']
CSV_FILE = 'stock_data.csv'
START_DATE = '2020-01-01'  # Used only if no existing file
END_DATE = datetime.today().strftime('%Y-%m-%d')

# AWS S3 config
BUCKET_NAME = 'stock-data-app-idm25'
S3_KEY = 'stock_data.csv'

def fetch_data(tickers, start, end):
    print(f"Fetching from {start} to {end}...")
    data = yf.download(tickers, start=start, end=end, group_by='ticker', progress=False)
    close_prices = pd.DataFrame()

    for ticker in tickers:
        close_prices[ticker] = data[ticker]['Close']

    # This line acts as a safeguard in case there are NaN values, but it shouldnt be the case
    close_prices.dropna(inplace=True)
    return close_prices

def upload_to_s3(file_name, bucket, s3_key):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_name, bucket, s3_key)
        print(f"Uploaded '{file_name}' to S3 bucket '{bucket}' as '{s3_key}'")
    except FileNotFoundError:
        print(f"File {file_name} not found.")
    except NoCredentialsError:
        print("AWS credentials not found. Please configure them.")
    except ClientError as e:
        print(f"Failed to upload: {e}")

if __name__ == '__main__':
    if os.path.exists(CSV_FILE):
        print(f"Found existing {CSV_FILE}")
        existing_df = pd.read_csv(CSV_FILE, index_col=0, parse_dates=True)
        last_date = existing_df.index[-1]
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Last saved date: {last_date.date()}")
    else:
        print("No existing data — starting fresh")
        existing_df = pd.DataFrame()
        start_date = START_DATE

    # Fetch new data
    new_data = fetch_data(TICKERS, start=start_date, end=END_DATE)

    if not new_data.empty:
        # Remove any overlapping dates (already in existing_df)
        # Needed because the last day of the CSV may still appear in new_data due to internal caching or timezone quirks in yfinance.
        new_data = new_data[~new_data.index.isin(existing_df.index)]

        if not new_data.empty:
            combined = pd.concat([existing_df, new_data])
            combined.sort_index(inplace=True)
            combined.to_csv(CSV_FILE)
            print(f"Appended {len(new_data)} new rows — saved to {CSV_FILE}")
        else:
            print("No new rows to append.")
    else:
        print("No new data to append.")

# Upload CSV to S3
upload_to_s3(CSV_FILE, BUCKET_NAME, S3_KEY)