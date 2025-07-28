import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

def force_add_asian_july_28():
    """
    Force add July 28th Asian market data using individual downloads
    """
    
    print("🎯 ASIAN MARKETS JULY 28TH FIX")
    print("=" * 40)
    
    # Asian market tickers
    tickers = {
        "HSI": "^HSI",   # Hang Seng Index
        "N225": "^N225"  # Nikkei 225
    }
    
    csv_file = "asian_market_avg_pct_change.csv"
    
    # Load existing data
    try:
        existing_df = pd.read_csv(csv_file)
        print(f"📊 Loaded existing Asian data: {len(existing_df)} rows")
        print(f"📅 Current range: {existing_df['Date'].min()} to {existing_df['Date'].max()}")
    except Exception as e:
        print(f"❌ Could not load existing data: {e}")
        return None
    
    # Check if July 28th already exists
    if "2025-07-28" in existing_df['Date'].values:
        print("ℹ️  July 28th already exists in Asian data")
        return existing_df
    
    print("\n🔄 Getting July 28th Asian market data...")
    
    # Get individual data for each market
    july_28_data = {}
    
    for market, ticker in tickers.items():
        print(f"\n📊 Fetching {market} ({ticker}) for July 28th...")
        
        try:
            # Use the proven single-day method
            data = yf.download(ticker, start="2025-07-28", end="2025-07-29", progress=False)
            
            if not data.empty:
                # Handle multi-level columns
                if hasattr(data.columns, 'levels') or isinstance(data.columns[0], tuple):
                    data.columns = [col[0] if isinstance(col, tuple) else str(col) for col in data.columns]
                
                close_price = data['Close'].iloc[0]
                print(f"   ✅ {market} July 28th Close: {close_price:.2f}")
                
                # Calculate percentage change from July 25th
                july_25_data = existing_df[existing_df['Date'] == '2025-07-25']
                if not july_25_data.empty:
                    if f'{market}_Pct_Change' in july_25_data.columns:
                        # Get July 25th close price to calculate % change
                        july_25_close_col = f'Close_{market}' if f'Close_{market}' in july_25_data.columns else f'Close_{market}_Hang_Seng'
                        
                        if july_25_close_col in july_25_data.columns:
                            july_25_close = july_25_data[july_25_close_col].iloc[0]
                            pct_change = ((close_price - july_25_close) / july_25_close) * 100
                            print(f"   📈 {market} % Change: {pct_change:.4f}%")
                            
                            july_28_data[market] = {
                                'close': close_price,
                                'pct_change': pct_change
                            }
                        else:
                            print(f"   ⚠️  Could not find July 25th close for {market}")
                else:
                    print(f"   ⚠️  No July 25th data found for percentage calculation")
            else:
                print(f"   ❌ No data available for {market}")
                
        except Exception as e:
            print(f"   ❌ Error getting {market}: {e}")
    
    # Create July 28th row if we got data
    if july_28_data:
        print(f"\n📈 Creating July 28th row with {len(july_28_data)} markets...")
        
        # Calculate Asian average
        pct_changes = [data['pct_change'] for data in july_28_data.values()]
        asian_avg = sum(pct_changes) / len(pct_changes)
        
        print(f"📊 Asian Average % Change for July 28th: {asian_avg:.4f}%")
        
        # Create new row matching existing structure
        new_row = {
            'Date': '2025-07-28',
            'Asian_Avg_Pct_Change': asian_avg
        }
        
        # Add individual market data to match existing columns
        for market, data in july_28_data.items():
            new_row[f'{market}_Pct_Change'] = data['pct_change']
            
            # Add close price columns to match existing structure
            for col in existing_df.columns:
                if col.startswith(f'Close_{market}'):
                    new_row[col] = data['close']
        
        # Fill any missing columns with NaN
        for col in existing_df.columns:
            if col not in new_row:
                new_row[col] = float('nan')
        
        # Create DataFrame and append
        new_row_df = pd.DataFrame([new_row])
        
        # Ensure same column order
        new_row_df = new_row_df.reindex(columns=existing_df.columns)
        
        # Combine data
        complete_df = pd.concat([existing_df, new_row_df], ignore_index=True)
        complete_df = complete_df.sort_values('Date').reset_index(drop=True)
        
        # Save updated data (FIX: Don't create backup, just save directly)
        print(f"💾 Saving updated data to {csv_file}...")
        complete_df.to_csv(csv_file, index=False, float_format='%.4f')
        
        print(f"✅ Updated Asian market data!")
        print(f"📊 Total records: {len(complete_df)}")
        print(f"📅 Range: {complete_df['Date'].min()} to {complete_df['Date'].max()}")
        
        # Verify the save worked
        try:
            verify_df = pd.read_csv(csv_file)
            if "2025-07-28" in verify_df['Date'].values:
                print(f"🎯 VERIFIED: July 28th data successfully saved!")
            else:
                print(f"❌ Verification failed - July 28th missing from saved file")
        except Exception as e:
            print(f"⚠️  Could not verify saved file: {e}")
        
        # Show the new July 28th data
        july_28_row = complete_df[complete_df['Date'] == '2025-07-28']
        if not july_28_row.empty:
            print(f"\n🎯 July 28th Asian Data:")
            row = july_28_row.iloc[0]
            for market in july_28_data.keys():
                pct_col = f'{market}_Pct_Change'
                if pct_col in row:
                    print(f"   {market}: {row[pct_col]:.4f}%")
            print(f"   Asian Average: {row['Asian_Avg_Pct_Change']:.4f}%")
        
        return complete_df
    else:
        print(f"\n❌ Could not get July 28th data for any Asian markets")
        return existing_df

def verify_asian_data():
    """
    Verify the updated Asian market data
    """
    
    try:
        df = pd.read_csv("asian_market_avg_pct_change.csv")
        
        print(f"\n🔍 ASIAN MARKET DATA VERIFICATION")
        print(f"📊 Total records: {len(df)}")
        print(f"📅 Date range: {df['Date'].min()} to {df['Date'].max()}")
        
        # Check for July 28th
        july_28 = df[df['Date'] == '2025-07-28']
        if not july_28.empty:
            avg_change = july_28['Asian_Avg_Pct_Change'].iloc[0]
            print(f"🎯 July 28th Asian Average: {avg_change:.4f}%")
            print(f"✅ READY FOR 9:15 AM MODEL ACTIVATION!")
        else:
            print(f"❌ July 28th still missing from Asian data")
        
        # Show last 5 entries
        print(f"\n📋 Last 5 Asian market entries:")
        last_5 = df.tail()
        for _, row in last_5.iterrows():
            print(f"   {row['Date']}: {row['Asian_Avg_Pct_Change']:.4f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ASIAN MARKETS JULY 28TH FIX")
    print("🎯 Getting that missing July 28th data!")
    
    result = force_add_asian_july_28()
    
    if result is not None:
        verify_asian_data()
        print(f"\n🎉 SUCCESS! Asian market data is now complete!")
    else:
        print(f"\n❌ Failed to update Asian market data")