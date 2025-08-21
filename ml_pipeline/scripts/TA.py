import pandas as pd
import numpy as np
import requests
import ta
from datetime import datetime, timedelta
import time
import os
import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURATION ===
API_KEY = "pzHOyL8BbwwwdwVcBxSP3rXCwKTtHB3l"
TA_CSV_FILE = "final_lstm_features.csv"

# Same tickers as in your TA.py but with Polygon format
TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK/B", "UNH", "JPM",
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

# Map yfinance names to Polygon names
TICKER_MAP = {
    "BRK-B": "BRK/B"
}

def get_polygon_ticker(ticker):
    return TICKER_MAP.get(ticker, ticker)

def fetch_daily_ohlc(ticker, date_str):
    """Fetch OHLC data for a single day from Polygon"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{date_str}/{date_str}"
    params = {
        "adjusted": "true",
        "apiKey": API_KEY
    }
    
    try:
        res = requests.get(url, params=params)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"
        
        data = res.json().get("results", [])
        if not data:
            return None, "No data"
        
        bar = data[0]
        return {
            'open': bar['o'],
            'high': bar['h'],
            'low': bar['l'],
            'close': bar['c'],
            'volume': bar['v']
        }, None
        
    except Exception as e:
        return None, str(e)

def fetch_spy_vix_data(date_str):
    """Fetch SPY and VIX data for benchmarks"""
    spy_data, spy_error = fetch_daily_ohlc("SPY", date_str)
    vix_data, vix_error = fetch_daily_ohlc("VIX", date_str)
    
    result = {}
    if spy_data:
        result['SPY'] = spy_data['close']
    if vix_data:
        result['VIX'] = vix_data['close']
    
    return result

def calculate_technical_indicators(ticker, price_series):
    """Calculate TA indicators for a single ticker"""
    if len(price_series) < 26:  # MACD needs at least 26 periods
        print(f"    ⚠️  {ticker}: Not enough data ({len(price_series)} periods) for MACD")
        return {}
    
    try:
        # Clean the price series first
        clean_prices = price_series.dropna()
        if len(clean_prices) < 26:
            print(f"    ⚠️  {ticker}: Not enough clean data ({len(clean_prices)} periods) after dropna")
            return {}
        
        # Calculate indicators
        indicators = {}
        
        # Volatility (5-day rolling std of returns)
        returns = clean_prices.pct_change(fill_method=None)
        vol5 = returns.rolling(5).std().iloc[-1]
        indicators[f"{ticker}_vol5"] = vol5
        
        # Returns
        ret1 = returns.iloc[-1]
        ret5 = clean_prices.pct_change(5, fill_method=None).iloc[-1]
        indicators[f"{ticker}_ret1"] = ret1
        indicators[f"{ticker}_ret5"] = ret5
        
        # RSI (14-period)
        try:
            rsi14 = ta.momentum.rsi(clean_prices, window=14).iloc[-1]
            indicators[f"{ticker}_rsi14"] = rsi14
        except Exception as e:
            print(f"    ⚠️  {ticker} RSI error: {e}")
            indicators[f"{ticker}_rsi14"] = np.nan
        
        # MACD (requires 26+ periods)
        try:
            macd_line = ta.trend.macd_diff(clean_prices)
            if not macd_line.empty and not pd.isna(macd_line.iloc[-1]):
                indicators[f"{ticker}_macd"] = macd_line.iloc[-1]
                print(f"    📊 {ticker} MACD: {macd_line.iloc[-1]:.6f}")
            else:
                print(f"    ⚠️  {ticker} MACD returned NaN or empty")
                indicators[f"{ticker}_macd"] = np.nan
        except Exception as e:
            print(f"    ⚠️  {ticker} MACD error: {e}")
            indicators[f"{ticker}_macd"] = np.nan
        
        # Bollinger Band Position
        try:
            bbp = ta.volatility.bollinger_pband(clean_prices).iloc[-1]
            indicators[f"{ticker}_bbp"] = bbp
        except Exception as e:
            print(f"    ⚠️  {ticker} BBP error: {e}")
            indicators[f"{ticker}_bbp"] = np.nan
        
        return indicators
        
    except Exception as e:
        print(f"    ❌ Error calculating indicators for {ticker}: {e}")
        return {}

def update_ta_features():
    """Update TA features CSV with missing dates from Polygon"""
    
    print("🔄 UPDATING TA FEATURES WITH POLYGON DATA")
    print("=" * 50)
    
    # Load existing TA data
    try:
        existing_df = pd.read_csv(TA_CSV_FILE, index_col=0, parse_dates=True)
        print(f"📊 Loaded existing TA data: {len(existing_df)} rows")
        print(f"📅 Current range: {existing_df.index.min().date()} to {existing_df.index.max().date()}")
    except Exception as e:
        print(f"❌ Could not load TA features: {e}")
        return
    
    # Find missing dates (July 30-31, 2025)
    last_date = existing_df.index.max().date()
    today = datetime.today().date()
    
    missing_dates = []
    current_date = last_date + timedelta(days=1)
    
    while current_date <= today:
        if current_date.weekday() < 5:  # Business days only
            missing_dates.append(current_date)
        current_date += timedelta(days=1)
    
    if not missing_dates:
        print("✅ TA features are already up to date!")
        return
    
    print(f"📅 Missing dates to add: {[str(d) for d in missing_dates]}")
    
    # We need historical price data to calculate indicators
    # Load the last 60 days of price data for calculations (increased for MACD)
    lookback_date = last_date - timedelta(days=60)
    print(f"🔍 Loading price history from {lookback_date} for indicator calculations...")
    
    # Get historical prices for each ticker (last 30 days)
    historical_prices = {}
    for ticker in TICKERS:
        yf_ticker = ticker.replace("/", "-")  # Convert back to yfinance format
        polygon_ticker = get_polygon_ticker(yf_ticker)
        
        print(f"   📊 Getting history for {yf_ticker}...")
        
        # Get daily data for last 30 days
        date_range = pd.date_range(start=lookback_date, end=last_date, freq='B')  # Business days
        prices = []
        
        for hist_date in date_range:
            date_str = hist_date.strftime("%Y-%m-%d")
            data, error = fetch_daily_ohlc(polygon_ticker, date_str)
            if data:
                prices.append(data['close'])
            else:
                prices.append(np.nan)
            time.sleep(0.1)  # Rate limiting
        
        historical_prices[yf_ticker] = pd.Series(prices, index=date_range)
    
    # Process each missing date
    new_rows = []
    for date in missing_dates:
        date_str = date.strftime("%Y-%m-%d")
        print(f"\n📅 Processing {date_str}...")
        
        daily_features = {}
        
        # Get new price data for this date
        for ticker in TICKERS:
            yf_ticker = ticker.replace("/", "-")
            polygon_ticker = get_polygon_ticker(yf_ticker)
            
            data, error = fetch_daily_ohlc(polygon_ticker, date_str)
            if data:
                # Add new price to historical series
                extended_series = historical_prices[yf_ticker].copy()
                extended_series.loc[pd.Timestamp(date)] = data['close']
                
                # Calculate indicators with extended series
                indicators = calculate_technical_indicators(yf_ticker, extended_series)
                daily_features.update(indicators)
                
                print(f"    ✅ {yf_ticker}: {data['close']:.2f}")
            else:
                print(f"    ❌ {yf_ticker}: {error}")
            
            time.sleep(0.15)  # Rate limiting
        
        # Get SPY and VIX data
        bench_data = fetch_spy_vix_data(date_str)
        daily_features.update(bench_data)
        
        # Calculate VIX indicators if we have data
        if 'VIX' in daily_features and len(existing_df) > 0:
            # Get last few VIX values to calculate delta and MA
            recent_vix = existing_df['VIX'].tail(5).tolist() + [daily_features['VIX']]
            daily_features['VIX_delta1'] = recent_vix[-1] - recent_vix[-2] if len(recent_vix) >= 2 else 0
            daily_features['VIX_MA5'] = np.mean(recent_vix[-5:]) if len(recent_vix) >= 5 else recent_vix[-1]
        
        # Calculate SPY_ret1 (next day return - will be NaN for now)
        daily_features['SPY_ret1'] = np.nan
        
        new_rows.append(pd.Series(daily_features, name=pd.Timestamp(date)))
        print(f"    📊 Calculated {len(daily_features)} features")
    
    if new_rows:
        # Create DataFrame for new rows
        new_df = pd.DataFrame(new_rows)
        
        # Ensure same columns as existing data
        for col in existing_df.columns:
            if col not in new_df.columns:
                new_df[col] = np.nan
        
        new_df = new_df.reindex(columns=existing_df.columns)
        
        # Combine with existing data
        updated_df = pd.concat([existing_df, new_df])
        
        # Update SPY_ret1 for previous day (now that we have new SPY data)
        if 'SPY' in updated_df.columns:
            updated_df['SPY_ret1'] = updated_df['SPY'].pct_change().shift(-1)
        
        # Apply same standardization as original (approximately)
        feature_cols = [c for c in updated_df.columns if c not in ['SPY_ret1']]
        
        # Re-standardize only the new rows to match existing distribution
        if len(new_rows) > 0:
            print("🔧 Applying standardization to new features...")
            # Use existing mean/std for consistency
            for col in feature_cols:
                if col in existing_df.columns:
                    existing_mean = existing_df[col].mean()
                    existing_std = existing_df[col].std()
                    if existing_std > 0:
                        # Standardize new values using existing parameters
                        new_mask = updated_df.index.isin([row.name for row in new_rows])
                        updated_df.loc[new_mask, col] = (updated_df.loc[new_mask, col] - existing_mean) / existing_std
        
        # Save updated data
        updated_df.to_csv(TA_CSV_FILE)
        print(f"\n✅ Updated TA features saved!")
        print(f"📊 Total records: {len(updated_df)}")
        print(f"📅 New range: {updated_df.index.min().date()} to {updated_df.index.max().date()}")
        
        # Show what was added
        print(f"\n🎯 Added data for:")
        for row in new_rows:
            date_str = row.name.strftime('%Y-%m-%d')
            non_nan_features = sum(1 for val in row.values if not pd.isna(val))
            print(f"   {date_str}: {non_nan_features} features")
    
    else:
        print("❌ No new data could be retrieved")

if __name__ == "__main__":
    update_ta_features()
    print("\n🎉 TA features update complete!")