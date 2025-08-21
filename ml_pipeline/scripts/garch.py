import pandas as pd
import numpy as np
from arch import arch_model
import yfinance as yf
import os
from datetime import datetime, date
import sys
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
# Define your ticker list manually
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

print("📊 Starting GARCH Volatility Analysis...")
print(f"📅 Date range: 2021-01-01 to {date.today()}")

# Download stock data from Yahoo Finance
print("📥 Downloading stock price data...")
start_date = "2021-01-01"
end_date = datetime.now().strftime("%Y-%m-%d")

# Download data for all tickers
data = yf.download(tickers, start=start_date, end=end_date, progress=True)

# Extract Open prices (or Adj Close if Open not available)
if 'Open' in data.columns.levels[0]:
    prices_df = data['Open'].copy()
    print("✅ Using Open prices")
else:
    prices_df = data['Adj Close'].copy()
    print("✅ Using Adjusted Close prices")

# Handle single ticker case
if len(tickers) == 1:
    prices_df = pd.DataFrame(prices_df, columns=[tickers[0]])

# Clean up column names and remove any tickers with insufficient data
prices_df = prices_df.dropna(how='all')  # Remove dates with no data
min_data_points = 100

# Create output directory
os.makedirs("garch_outputs", exist_ok=True)

# Output container for GARCH volatilities
garch_vols = pd.DataFrame(index=prices_df.index)

print(f"\n🔄 Processing {len(tickers)} tickers for GARCH volatility...")

# Loop through all tickers
successful_tickers = 0
for i, ticker in enumerate(tickers):
    print(f"[{i+1}/{len(tickers)}] Processing {ticker}...", end=" ")
    
    if ticker not in prices_df.columns:
        print(f"❌ Not found in data")
        garch_vols[ticker] = np.nan
        continue

    prices = prices_df[ticker].dropna()
    
    if len(prices) < min_data_points:
        print(f"⏭️ Insufficient data ({len(prices)} points)")
        garch_vols[ticker] = np.nan
        continue

    # Calculate returns (percentage)
    returns = 100 * prices.pct_change().dropna()
    
    try:
        # Fit GARCH(1,1) model
        model = arch_model(returns, vol='Garch', p=1, q=1, mean='Zero')
        res = model.fit(disp='off', show_warning=False)
        
        # Get conditional volatility (fitted values)
        conditional_vol = res.conditional_volatility
        
        # Align to full price index
        vol_series = pd.Series(index=prices.index, dtype=float)
        vol_series.loc[conditional_vol.index] = conditional_vol.values
        
        # Reindex to match the full DataFrame index
        aligned_vol = vol_series.reindex(garch_vols.index)
        garch_vols[ticker] = aligned_vol
        
        successful_tickers += 1
        print(f"✅ Success")

    except Exception as e:
        print(f"⚠️ GARCH failed: {str(e)[:50]}...")
        garch_vols[ticker] = np.nan

print(f"\n📊 Successfully processed {successful_tickers}/{len(tickers)} tickers")

# Save the main GARCH results
output_file = "garch.csv"
garch_vols.to_csv(output_file)
print(f"💾 Main output saved: {output_file}")

# Also save to the garch_outputs directory with more descriptive name
detailed_output = "garch_outputs/garch_volatility_all_tickers_detailed.csv"
garch_vols.to_csv(detailed_output)
print(f"💾 Detailed output saved: {detailed_output}")

# Create a summary statistics file
summary_stats = pd.DataFrame({
    'Ticker': garch_vols.columns,
    'Mean_Volatility': garch_vols.mean(),
    'Std_Volatility': garch_vols.std(),
    'Min_Volatility': garch_vols.min(),
    'Max_Volatility': garch_vols.max(),
    'Data_Points': garch_vols.count()
})

summary_file = "garch_outputs/garch_summary_statistics.csv"
summary_stats.to_csv(summary_file, index=False)
print(f"📈 Summary statistics saved: {summary_file}")

print(f"\n🎉 Analysis complete!")
print(f"📋 Files created:")
print(f"   • {output_file} (main output)")
print(f"   • {detailed_output} (detailed copy)")
print(f"   • {summary_file} (summary stats)")
print(f"\n📊 Data shape: {garch_vols.shape[0]} dates × {garch_vols.shape[1]} tickers")
print(f"📅 Date range: {garch_vols.index[0].strftime('%Y-%m-%d')} to {garch_vols.index[-1].strftime('%Y-%m-%d')}")