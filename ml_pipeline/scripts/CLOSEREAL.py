import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
def complete_stock_rebuild():
    """
    Complete rebuild of stock closing prices from Jan 1 2021 to today
    """
    
    print("🎯 COMPLETE STOCK DATA REBUILD")
    print("📅 From January 1, 2021 to TODAY")
    print("=" * 60)
    
    # All your stock tickers
    tickers = [
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
    
    output_file = "historical_closing_prices.csv"
    backup_file = "historical_closing_prices_old.csv"
    
    # Date range - SAME AS YOUR OTHER DATASETS
    start_date = "2021-01-01"
    today = datetime.now().date()
    end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # Tomorrow to include today
    
    print(f"📊 Downloading {len(tickers)} stocks")
    print(f"📅 From: {start_date}")
    print(f"📅 To: {end_date} (exclusive - includes today)")
    print(f"⏳ This will take a few minutes...")
    
    # Backup existing file
    if os.path.exists(output_file):
        os.rename(output_file, backup_file)
        print(f"📦 Backed up existing file to: {backup_file}")
    
    try:
        print("\n🚀 Starting bulk download...")
        
        # Download all stock data
        stock_data = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            auto_adjust=True,  # Get adjusted close prices
            progress=True,
            threads=True,
            group_by='ticker'
        )
        
        if stock_data.empty:
            print("❌ No data returned from Yahoo Finance")
            return None
        
        print(f"✅ Downloaded data successfully!")
        print(f"📊 Data shape: {stock_data.shape}")
        
        # Process the data
        print("🔧 Processing stock data...")
        
        # Reset index to get Date as column
        stock_data.reset_index(inplace=True)
        
        # Handle multi-level columns
        if isinstance(stock_data.columns, pd.MultiIndex):
            print("   🔧 Processing multi-level columns...")
            
            # Create clean DataFrame
            clean_data = pd.DataFrame()
            clean_data['Date'] = pd.to_datetime(stock_data['Date']).dt.strftime('%Y-%m-%d')
            
            # Extract Close prices for each ticker
            for ticker in tickers:
                if ('Close', ticker) in stock_data.columns:
                    clean_data[ticker] = stock_data[('Close', ticker)].round(2)
                elif ticker in stock_data.columns:
                    # Handle case where ticker might be top level
                    if hasattr(stock_data[ticker], 'Close'):
                        clean_data[ticker] = stock_data[ticker]['Close'].round(2)
                    else:
                        clean_data[ticker] = stock_data[ticker].round(2)
                else:
                    # Add missing ticker as NaN
                    clean_data[ticker] = float('nan')
                    print(f"   ⚠️  Missing data for {ticker}")
        else:
            print("   🔧 Processing single-level data...")
            clean_data = stock_data.copy()
            clean_data['Date'] = pd.to_datetime(clean_data['Date']).dt.strftime('%Y-%m-%d')
            
            # Ensure we have all tickers
            for ticker in tickers:
                if ticker not in clean_data.columns:
                    clean_data[ticker] = float('nan')
                    print(f"   ⚠️  Missing data for {ticker}")
        
        # Clean up the data
        print("🧹 Cleaning data...")
        
        # Remove rows where ALL stock prices are NaN
        stock_columns = [col for col in clean_data.columns if col != 'Date']
        clean_data = clean_data.dropna(subset=stock_columns, how='all')
        
        # Sort by date
        clean_data = clean_data.sort_values('Date').reset_index(drop=True)
        
        # Ensure correct column order (Date first, then tickers in original order)
        column_order = ['Date'] + [ticker for ticker in tickers if ticker in clean_data.columns]
        clean_data = clean_data[column_order]
        
        print(f"✅ Processed data:")
        print(f"   📊 Shape: {clean_data.shape}")
        print(f"   📅 Date range: {clean_data['Date'].min()} to {clean_data['Date'].max()}")
        print(f"   📈 Stocks: {len(clean_data.columns) - 1}")
        
        # Save to CSV
        print(f"💾 Saving to {output_file}...")
        clean_data.to_csv(output_file, index=False, float_format='%.2f')
        
        print(f"✅ Stock data rebuild complete!")
        
        # Verify the results
        print(f"\n🔍 VERIFICATION:")
        print(f"📊 Total records: {len(clean_data)}")
        print(f"📅 Complete range: {clean_data['Date'].min()} to {clean_data['Date'].max()}")
        
        # Check if we got today's data
        today_str = today.strftime('%Y-%m-%d')
        if today_str in clean_data['Date'].values:
            print(f"🎉 SUCCESS! Got today's data ({today_str})")
            
            # Show today's prices for key stocks
            today_row = clean_data[clean_data['Date'] == today_str].iloc[0]
            print(f"📈 Today's stock prices:")
            
            key_stocks = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL']
            for stock in key_stocks:
                if stock in today_row and pd.notna(today_row[stock]):
                    print(f"   {stock}: ${today_row[stock]:.2f}")
                else:
                    print(f"   {stock}: No data")
        else:
            latest_date = clean_data['Date'].max()
            print(f"📅 Latest data: {latest_date}")
        
        # Data quality summary
        latest_row = clean_data.tail(1).iloc[0]
        valid_count = latest_row.drop('Date').notna().sum()
        total_count = len(latest_row) - 1
        print(f"📊 Data quality: {valid_count}/{total_count} stocks ({valid_count/total_count*100:.1f}%)")
        
        # Show sample of recent data
        print(f"\n📋 Last 3 trading days:")
        sample_stocks = ['AAPL', 'MSFT', 'NVDA']
        recent_data = clean_data.tail(3)
        for _, row in recent_data.iterrows():
            print(f"📅 {row['Date']}:")
            for stock in sample_stocks:
                if stock in row and pd.notna(row[stock]):
                    print(f"   {stock}: ${row[stock]:.2f}")
        
        return clean_data
        
    except Exception as e:
        print(f"❌ Error during rebuild: {e}")
        import traceback
        traceback.print_exc()
        
        # Restore backup if it exists
        if os.path.exists(backup_file):
            os.rename(backup_file, output_file)
            print(f"🔄 Restored backup file")
        
        return None

if __name__ == "__main__":
    print("🚀 COMPLETE STOCK DATA REBUILD")
    print("🎯 Matching your VIX and Asian market datasets")
    
    result = complete_stock_rebuild()
    
    if result is not None:
        print(f"\n🎉 SUCCESS! Complete stock dataset ready!")
        print(f"📁 File: historical_closing_prices.csv")
        print(f"📅 Range: Jan 1 2021 to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"✅ READY FOR 9:15 AM MODEL ACTIVATION!")
    else:
        print(f"\n❌ Stock data rebuild failed")