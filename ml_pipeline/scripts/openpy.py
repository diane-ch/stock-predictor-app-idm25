import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')
import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
def update_opening_prices():
    """Update opening prices CSV with only new data"""
    
    print("📊 OPENING PRICES UPDATER")
    print("=" * 40)
    
    output_file = "stock_open_prices_wide_format.csv"
    
    # All tickers
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
    
    # Check existing file
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            print(f"📊 Found existing file: {len(existing_df)} records")
            
            # Get last date
            last_date_str = existing_df['Date'].max()
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            start_date = last_date + timedelta(days=1)
            
            print(f"📅 Last date: {last_date_str}")
            print(f"▶️  Will update from: {start_date.strftime('%Y-%m-%d')}")
            
        except Exception as e:
            print(f"❌ Error reading existing file: {e}")
            return None
    else:
        print("❌ No existing file found! Run nuclear rebuild first.")
        return None
    
    # Check if update needed
    today = datetime.today()
    end_date = today + timedelta(days=1)  # Include today
    
    if start_date > today:
        print("✅ Opening prices are already up to date!")
        return existing_df
    
    # Calculate business days needed
    business_days = 0
    check_date = start_date
    while check_date <= today:
        if check_date.weekday() < 5:
            business_days += 1
        check_date += timedelta(days=1)
    
    if business_days == 0:
        print("✅ No new business days to update!")
        return existing_df
    
    print(f"🎯 Need to fetch {business_days} business days")
    print(f"📅 From: {start_date.strftime('%Y-%m-%d')} to: {today.strftime('%Y-%m-%d')}")
    
    try:
        # Download NEW data only
        print("⬇️  Downloading new opening prices...")
        
        new_data = yf.download(
            tickers, 
            start=start_date.strftime('%Y-%m-%d'), 
            end=end_date.strftime('%Y-%m-%d'), 
            progress=True
        )
        
        if new_data.empty:
            print("❌ No new data available")
            return existing_df
        
        print(f"✅ Downloaded new data: {new_data.shape}")
        
        # Process new data using the WORKING method
        new_data = new_data.reset_index()
        
        # Create clean new dataframe
        new_df = pd.DataFrame()
        new_df['Date'] = pd.to_datetime(new_data['Date']).dt.strftime('%Y-%m-%d')
        
        # Extract opens for all tickers
        missing_tickers = []
        for ticker in tickers:
            if ('Open', ticker) in new_data.columns:
                new_df[ticker] = new_data[('Open', ticker)].round(2)
            else:
                new_df[ticker] = float('nan')
                missing_tickers.append(ticker)
        
        if missing_tickers:
            print(f"⚠️  Missing data for: {missing_tickers[:5]}...")
        
        # Remove weekends
        new_df['Date_obj'] = pd.to_datetime(new_df['Date'])
        new_df = new_df[new_df['Date_obj'].dt.weekday < 5]
        new_df = new_df.drop('Date_obj', axis=1)
        
        # Sort by date
        new_df = new_df.sort_values('Date').reset_index(drop=True)
        
        print(f"🔧 Processed {len(new_df)} new trading days")
        
        if len(new_df) == 0:
            print("⚠️  No new trading days to add")
            return existing_df
        
        # Combine with existing data
        print("🔗 Combining with existing data...")
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Date'], keep='last')
        combined_df = combined_df.sort_values('Date').reset_index(drop=True)
        
        # Ensure same column order
        column_order = ['Date'] + [t for t in tickers if t in combined_df.columns]
        combined_df = combined_df[column_order]
        
        # Save updated file
        print("💾 Saving updated opening prices...")
        combined_df.to_csv(output_file, index=False, float_format='%.2f')
        
        print(f"✅ UPDATE COMPLETE!")
        print(f"📊 Total records: {len(combined_df)}")
        print(f"📅 Date range: {combined_df['Date'].min()} to {combined_df['Date'].max()}")
        print(f"📈 Added {len(new_df)} new trading days")
        
        # Show new data
        if len(new_df) > 0:
            print(f"\n📋 New opening prices added:")
            sample_stocks = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL']
            
            for _, row in new_df.iterrows():
                print(f"📅 {row['Date']}:")
                for stock in sample_stocks:
                    if stock in row and pd.notna(row[stock]):
                        print(f"   {stock}: ${row[stock]:.2f}")
        
        return combined_df
        
    except Exception as e:
        print(f"❌ Update failed: {e}")
        import traceback
        traceback.print_exc()
        return existing_df

if __name__ == "__main__":
    print("🚀 OPENING PRICES UPDATER")
    print("📊 Only downloads NEW data since last update")
    
    result = update_opening_prices()
    
    if result is not None:
        print(f"\n🎉 SUCCESS! Opening prices updated!")
        print(f"📁 File: stock_open_prices_wide_format.csv")
        print(f"✅ Run this anytime to get latest data!")
    else:
        print(f"\n❌ Update failed")