import pandas as pd
import numpy as np
import yfinance as yf
import ta
from datetime import datetime

# === PARAMETERS ===
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

start_date = "2021-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

# === Download price data ===
price = yf.download(tickers, start=start_date, end=end_date)["Close"]
price = price.dropna(how="all")

# 1) TZ-naive index
price.index = price.index.tz_localize(None)

# 2) Start building the panel dataframe
dfp = price.copy()

# 3) Calculate Technical Indicators per ticker
tech = []
for t in tickers:
    s = price[t].dropna()
    tech_df = pd.DataFrame({
        f"{t}_vol5":   s.pct_change().rolling(5).std(),
        f"{t}_ret1":   s.pct_change(1),
        f"{t}_ret5":   s.pct_change(5),
        f"{t}_rsi14":  ta.momentum.rsi(s, window=14),
        f"{t}_macd":   ta.trend.macd_diff(s),
        f"{t}_bbp":    ta.volatility.bollinger_pband(s),
    }, index=s.index)
    tech.append(tech_df)

tech_df = pd.concat(tech, axis=1)
dfp = pd.concat([dfp, tech_df], axis=1)

# 4) Merge benchmarks (SPY & VIX)
bench = yf.download(["SPY", "^VIX"], start=start_date, end=end_date)["Close"]
bench.columns = ["SPY", "VIX"]
bench.index = bench.index.tz_localize(None)
dfp = dfp.join(bench, how="left")

# 5) Compute VIX delta and 5-day moving average
dfp["VIX_delta1"] = dfp["VIX"].diff().fillna(0)
dfp["VIX_MA5"] = dfp["VIX"].rolling(window=5).mean()

# 6) Drop raw stock prices (optional)
dfp.drop(columns=tickers, inplace=True, errors="ignore")

# 7) Define your label here (example: next-day SPY return)
dfp["SPY_ret1"] = dfp["SPY"].pct_change().shift(-1)
dfp.dropna(subset=["SPY_ret1"], inplace=True)

# 8) Define label_cols and feature_cols
label_cols = ["SPY_ret1"]
feature_cols = [c for c in dfp.columns if c not in label_cols]

# 9) Global Standardization of features
mu = dfp[feature_cols].mean()
sig = dfp[feature_cols].std(ddof=0)
dfp[feature_cols] = (dfp[feature_cols] - mu) / sig

# 10) Fill & clean NaNs
dfp[feature_cols] = dfp[feature_cols].ffill().bfill()
dfp.dropna(inplace=True)

# Final dataset ready for LSTM
dfp.to_csv("final_lstm_features.csv")
print("✅ Final dataset shape:", dfp.shape)
print("✅ Saved as final_lstm_features.csv")
