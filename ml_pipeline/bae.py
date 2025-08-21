# -*- coding: utf-8 -*-
"""
bae.py — intraday (09:00 -> 10:30) prediction pipeline
- Robust path handling and file checks
- Feature engineering (overnight drift, prev intraday return + sign, ΔVIX, TA, GARCH proxy)
- Model training per ticker (Ridge magnitude + Logistic direction) with manual weights
- Predictions for TARGET_DATES (multi-date)
- Terminal-friendly printing (no Jupyter display)
- Final "newswire-style" CSV export (one per target date):
  date,ticker,name,price,change,confidence,feature1,feature2,feature3,feature4

Now: feature1..feature4 are the TOP CONTRIBUTING FEATURES for that prediction
(e.g., "RSI", "GARCH vol", "ΔVIX", "Prev intraday", "Overnight drift", etc.)

Requires: pandas, numpy, scikit-learn
Optional: arch (for GARCH), tabulate (for nicer tables)
"""

import os
import re
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

# -----------------------------------------------------------------------------
# 1) SETUP & FILE CHECKS
# -----------------------------------------------------------------------------
OG_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(OG_BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(OG_BASE_DIR, 'output')

P1030_FILE = "stock_prices_1030_wide_format.csv"
P0900_FILE = "stock_prices_0900_wide_format.csv"
CLOSE_FILE_CANDIDATES = [
    "stock_prices_close_wide_format.csv",
    "historical_closing_prices_wide_format.csv",
    "historical_closing_prices_old.csv",
]

def load_csv_safe(path, **kwargs):
    try:
        if not os.path.exists(path):
            return None
        return pd.read_csv(path, **kwargs)
    except Exception:
        return None

def parse_date_col(df, col="Date", dayfirst=False):
    if df is None: return None
    out = df.copy()
    out[col] = pd.to_datetime(out[col], dayfirst=dayfirst, errors="coerce")
    out = out.sort_values(col).reset_index(drop=True)
    return out

def unify_ticker_cols(df, date_col="Date"):
    if df is None: return None
    cols = [c for c in df.columns if c != date_col and "unnamed" not in str(c).lower()]
    return df[[date_col] + cols]

def melt_long(df, value_name):
    cols = [c for c in df.columns if c != "Date"]
    return df.melt(id_vars=["Date"], value_vars=cols, var_name="ticker", value_name=value_name)

missing = []

p1030_path = os.path.join(BASE_DIR, P1030_FILE)
if not os.path.exists(p1030_path):
    missing.append(P1030_FILE)

p0900_path = os.path.join(BASE_DIR, P0900_FILE)
if not os.path.exists(p0900_path):
    print("⚠️ No 09:00 premarket file found, continuing without it.")
    p0900_path = None

close_path = None
for cand in CLOSE_FILE_CANDIDATES:
    cand_path = os.path.join(BASE_DIR, cand)
    if os.path.exists(cand_path):
        close_path = cand_path
        break
if close_path is None:
    missing.append("Close price file (one of: " + ", ".join(CLOSE_FILE_CANDIDATES) + ")")

if missing:
    raise RuntimeError("❌ Required file(s) not found:\n  - " + "\n  - ".join(missing) + f"\nCheck folder: {BASE_DIR}")

print(f"✅ Using 10:30 prices: {p1030_path}")
if p0900_path:
    print(f"✅ Using 09:00 prices: {p0900_path}")
print(f"✅ Using Close prices: {close_path}")

# -----------------------------------------------------------------------------
# 2) LOAD & FEATURE ENGINEERING
# -----------------------------------------------------------------------------
vix = parse_date_col(load_csv_safe(os.path.join(BASE_DIR, "vix_prices.csv")), "Date")
if vix is None:
    vix_alt = parse_date_col(load_csv_safe(os.path.join(BASE_DIR, "vix_open_clean.csv")), "Date")
    if vix_alt is not None:
        if "Open" in vix_alt.columns:
            vix_alt = vix_alt.rename(columns={"Open": "VIX"})
        elif "VIX_open" in vix_alt.columns:
            vix_alt = vix_alt.rename(columns={"VIX_open": "VIX"})
        vix = vix_alt

p1030 = unify_ticker_cols(parse_date_col(load_csv_safe(p1030_path), "Date"))
p0900 = unify_ticker_cols(parse_date_col(load_csv_safe(p0900_path), "Date")) if p0900_path else None
close = unify_ticker_cols(parse_date_col(load_csv_safe(close_path), "Date"))

m1030 = melt_long(p1030, "P1030")
if p0900 is not None:
    m0900 = melt_long(p0900, "P0900")
else:
    print("⚠️ 09:00 file missing — will impute P0900 from yesterday's Close as needed.")
    m0900 = m1030[["Date", "ticker"]].copy()
    m0900["P0900"] = np.nan
mclose = melt_long(close, "Close")

df = (
    m1030
    .merge(m0900, on=["Date","ticker"], how="outer")
    .merge(mclose.rename(columns={"Close":"Close_t"}), on=["Date","ticker"], how="left")
    .sort_values(["ticker","Date"])
    .reset_index(drop=True)
)

df["Close_t_minus_1"] = df.groupby("ticker")["Close_t"].shift(1)
df["P0900_imputed"] = df["P0900"].where(df["P0900"].notna(), df["Close_t_minus_1"])

df = df[df["P1030"].notna()].copy()
df = df[df["P0900_imputed"].notna()].copy()

df["ret_0900_1030"] = (df["P1030"] / df["P0900_imputed"]) - 1.0
df["overnight_drift"] = (df["P0900_imputed"] / df["Close_t_minus_1"]) - 1.0

df["ret_0900_1030_prev"] = df.groupby("ticker")["ret_0900_1030"].shift(1)
df["ret_0900_1030_prev_sign"] = np.sign(df["ret_0900_1030_prev"])

if vix is not None:
    vix_cols = [c for c in vix.columns if c.lower() != "date"]
    if vix_cols:
        col = vix_cols[0]
        vix_simple = vix[["Date", col]].rename(columns={col: "VIX"}).dropna()
        vix_simple["VIX_delta"] = vix_simple["VIX"].diff()
        # FIXED: use list (not set) for column selection
        df = df.merge(vix_simple[["Date","VIX_delta"]], on="Date", how="left")
    else:
        df["VIX_delta"] = np.nan
else:
    df["VIX_delta"] = np.nan

# TA
df["ret1"] = df.groupby("ticker")["Close_t"].pct_change(fill_method=None)
df["vol5"] = df.groupby("ticker")["Close_t"].rolling(5).std(ddof=0).reset_index(level=0, drop=True)
df["ma5"]  = df.groupby("ticker")["Close_t"].rolling(5).mean().reset_index(level=0, drop=True)
df["ma20"] = df.groupby("ticker")["Close_t"].rolling(20).mean().reset_index(level=0, drop=True)
for c in ["ret1","vol5","ma5","ma20"]:
    df[c] = df[c] * 0.1

def compute_garch_series(ret_series):
    try:
        from arch import arch_model
        s = ret_series.dropna() * 100.0
        if len(s) < 60:
            raise ValueError("Not enough data for GARCH; using fallback.")
        am = arch_model(s, vol="Garch", p=1, q=1, dist="normal")
        res = am.fit(disp="off")
        vol = res.conditional_volatility / 100.0
        vol = vol.reindex(ret_series.index)
        return vol
    except Exception:
        r = ret_series.abs()
        vol = r.ewm(alpha=0.06, adjust=False, min_periods=10).mean()
        return vol

df["garch_vol"] = df.groupby("ticker")["ret1"].apply(lambda s: compute_garch_series(s)).reset_index(level=0, drop=True)

df_feat = df.dropna(subset=["P0900_imputed","P1030","Close_t_minus_1","ret_0900_1030_prev"]).copy()

FEAT_COLS = [
    "overnight_drift",
    "ret_0900_1030_prev",
    "ret_0900_1030_prev_sign",
    "VIX_delta",
    "ret1", "vol5", "ma5", "ma20",
    "garch_vol"
]

print(f"✅ Feature table ready | rows: {len(df_feat):,} | features: {len(FEAT_COLS)}")
print("Features:", FEAT_COLS)
try:
    from tabulate import tabulate
    print(tabulate(df_feat.head(10), headers="keys", tablefmt="psql", showindex=False))
except Exception:
    print(df_feat.head(10).to_string(index=False))

# ---- Optional TA from final_lstm_features.csv (RSI_14, MACD_line, BB_pos) ----
POSSIBLE_PATHS = [
    os.path.join(BASE_DIR, "final_lstm_features.csv"),
    "final_lstm_features.csv",
    "/mnt/data/final_lstm_features.csv",
]
csv_path = next((p for p in POSSIBLE_PATHS if os.path.exists(p)), None)

if csv_path:
    raw = pd.read_csv(csv_path)
    if "Date" not in raw.columns:
        cand = [c for c in raw.columns if str(c).strip().lower() in ("date","dt","time","timestamp")]
        if not cand:
            u = [c for c in raw.columns if str(c).lower().startswith("unnamed")]
            if u:
                cand = [u[0]]
        if not cand:
            raise RuntimeError("❌ final_lstm_features.csv present but no date-like column was found.")
        raw = raw.rename(columns={cand[0]:"Date"})
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw = raw.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    date_only = raw[["Date"]]
    feat_cols = [c for c in raw.columns if c != "Date"]

    triples = []
    pat = re.compile(r"^([A-Za-z0-9.\-]+)_(rsi14|macd|bbp)$", flags=re.IGNORECASE)
    for c in feat_cols:
        m = pat.match(c)
        if m:
            tkr, fraw = m.group(1), m.group(2).lower()
            canon = {"rsi14":"RSI_14", "macd":"MACD_line", "bbp":"BB_pos"}[fraw]
            triples.append((c, tkr, canon))

    if triples:
        feat_tables = {}
        for feat_name in ["RSI_14","MACD_line","BB_pos"]:
            sub_frames = []
            for col, tkr, canon in triples:
                if canon != feat_name: continue
                tmp = date_only.copy()
                tmp["ticker"] = tkr
                tmp[feat_name] = pd.to_numeric(raw[col], errors="coerce")
                sub_frames.append(tmp)
            if sub_frames:
                cat = pd.concat(sub_frames, axis=0, ignore_index=True)
                cat = (cat.sort_values(["Date","ticker"])
                         .groupby(["Date","ticker"], as_index=False)[feat_name].first())
                feat_tables[feat_name] = cat

        base_pairs = df_feat[["Date","ticker"]].drop_duplicates()
        for feat_name, table in feat_tables.items():
            base_pairs = base_pairs.merge(table, on=["Date","ticker"], how="left")

        for c in [k for k in ["RSI_14","MACD_line","BB_pos"] if k in base_pairs.columns]:
            q1, q99 = base_pairs[c].quantile(0.01), base_pairs[c].quantile(0.99)
            base_pairs[c] = base_pairs[c].clip(lower=q1, upper=q99)

        df_feat = df_feat.merge(base_pairs, on=["Date","ticker"], how="left")
        new_feats = [c for c in ["RSI_14","MACD_line","BB_pos"] if c in df_feat.columns and c not in FEAT_COLS]
        FEAT_COLS = FEAT_COLS + new_feats

        print(f"✅ Merged TA (RSI_14, MACD_line, BB_pos) from {os.path.basename(csv_path)} into df_feat")
        print("   Added features:", new_feats)
        try:
            from tabulate import tabulate
            print(tabulate(df_feat[["Date","ticker"] + new_feats].head(10), headers="keys", tablefmt="psql", showindex=False))
        except Exception:
            print(df_feat[["Date","ticker"] + new_feats].head(10).to_string(index=False))
    else:
        print("ℹ️ final_lstm_features.csv present but no columns matched '<TICKER>_(rsi14|macd|bbp)'. Skipping.")
else:
    print("ℹ️ final_lstm_features.csv not found. Continuing without RSI/MACD/BB% extras.")

# -----------------------------------------------------------------------------
# 3) TRAINING (per ticker)
# -----------------------------------------------------------------------------
FEATURE_WEIGHTS = {
    "overnight_drift":         8,
    "ret_0900_1030_prev":      7,
    "ret_0900_1030_prev_sign": 4,
    "VIX_delta":               9,
    "ret1":                    6,
    "vol5":                    5,
    "ma5":                     3,
    "ma20":                    3,
    "garch_vol":               8,
    "RSI_14":                  6,
    "MACD_line":               7,
    "BB_pos":                  5,
}
WEIGHTS_VEC = np.array([FEATURE_WEIGHTS.get(f, 5) for f in FEAT_COLS], dtype=float)

BASE_CAP = 0.02
RED_CAP  = 0.08
VIX_DELTA_RED    = 5.0
GARCH_FACTOR_RED = 2.0
MARGIN_BLEND = 0.6

def soft_cap(x, cap):
    return float(np.tanh(x / cap) * cap)

def compute_red_flags(df_in: pd.DataFrame) -> pd.Series:
    df2 = df_in.copy()
    vix_spike = (df2["VIX_delta"].abs() >= VIX_DELTA_RED).fillna(False) if "VIX_delta" in df2 else False
    if "garch_vol" in df2:
        med_per_tkr = df2.groupby("ticker")["garch_vol"].transform(lambda s: s.median(skipna=True))
        garch_spike = (df2["garch_vol"] > (GARCH_FACTOR_RED * med_per_tkr)).fillna(False)
    else:
        garch_spike = False
    return (vix_spike | garch_spike)

df_feat = df_feat.copy()
df_feat["is_red_flag"] = compute_red_flags(df_feat)

def split_chrono(n, frac_test=1/7, frac_val=1/7, min_train=60):
    n_test  = max(1, int(round(n * frac_test)))
    n_val   = max(1, int(round(n * frac_val)))
    n_train = n - n_val - n_test
    if n_train < min_train:
        need = min_train - n_train
        take_val = min(need // 2, max(0, n_val - 1))
        take_tst = min(need - take_val, max(0, n_test - 1))
        n_val  -= take_val
        n_test -= take_tst
        n_train = n - n_val - n_test
        if n_train < min_train:
            n_train = min_train
            leftover = n - n_train
            n_val  = max(1, leftover // 2)
            n_test = max(1, leftover - n_val)
    return n_train, n_val, n_test

models_reg, models_clf, scalers, imputers = {}, {}, {}, {}
summ_rows = []
tickers = tuple(sorted(df_feat["ticker"].unique()))

for tkr in tickers:
    d = df_feat[df_feat["ticker"] == tkr].sort_values("Date").reset_index(drop=True)
    n = len(d)
    if n < 80:
        print(f"⚠️ {tkr}: only {n} rows; results may be noisy.")

    X = d[FEAT_COLS].to_numpy(dtype=float)
    y = d["ret_0900_1030"].to_numpy(dtype=float)
    y_dir = (y > 0).astype(int)
    p0900 = d["P0900_imputed"].to_numpy(dtype=float)
    redf  = d.get("is_red_flag", pd.Series(False, index=d.index)).to_numpy(dtype=bool)

    X[~np.isfinite(X)] = np.nan

    n_train, n_val, n_test = split_chrono(n)
    X_train, X_val, X_test = X[:n_train], X[n_train:n_train+n_val], X[n_train+n_val:]
    y_train, y_val, y_test = y[:n_train], y[n_train:n_train+n_val], y[n_train+n_val:]
    y_train_dir, y_val_dir, y_test_dir = y_dir[:n_train], y_dir[n_train:n_train+n_val], y_dir[n_train+n_val:]
    p0900_train, p0900_val, p0900_test = p0900[:n_train], p0900[n_train:n_train+n_val], p0900[n_train+n_val:]
    red_val, red_test = redf[n_train:n_train+n_val], redf[n_train+n_val:]

    imputer = SimpleImputer(strategy="median")
    X_train_i = imputer.fit_transform(X_train)
    X_val_i   = imputer.transform(X_val)

    scaler = StandardScaler().fit(X_train_i)
    X_train_s = np.clip(scaler.transform(X_train_i), -5, 5) * WEIGHTS_VEC
    X_val_s   = np.clip(scaler.transform(X_val_i),   -5, 5) * WEIGHTS_VEC

    reg = Ridge(alpha=0.1, fit_intercept=True).fit(X_train_s, y_train)
    clf = LogisticRegression(max_iter=500, solver="lbfgs").fit(X_train_s, y_train_dir)

    # Validation metrics in PRICE space
    y_val_mag = reg.predict(X_val_s)
    prob_val  = clf.predict_proba(X_val_s)[:, 1]
    dir_val   = (prob_val >= 0.5).astype(int)
    margin    = np.abs(prob_val - 0.5) * 2.0
    mag_blend = (1.0 - MARGIN_BLEND) + (MARGIN_BLEND * margin)
    y_val_pred = np.where(dir_val == 1, np.abs(y_val_mag), -np.abs(y_val_mag)) * mag_blend
    y_val_pred_capped = np.array([soft_cap(v, RED_CAP if red_val[i] else BASE_CAP) for i, v in enumerate(y_val_pred)])

    y_val_px   = p0900_val * (1.0 + y_val)
    y_pred_px  = p0900_val * (1.0 + y_val_pred_capped)
    mae_val    = mean_absolute_error(y_val_px, y_pred_px) if len(y_val) else np.nan
    rmse_val   = float(np.sqrt(mean_squared_error(y_val_px, y_pred_px))) if len(y_val) else np.nan

    models_reg[tkr] = reg
    models_clf[tkr] = clf
    scalers[tkr]    = scaler
    imputers[tkr]   = imputer

    summ_rows.append({
        "ticker": tkr,
        "MAE": None if pd.isna(mae_val) else round(mae_val, 8),
        "RMSE": None if pd.isna(rmse_val) else round(rmse_val, 8),
        "n_train": int(n_train),
        "n_test": int(n_test),
    })

perf_df = pd.DataFrame(summ_rows).sort_values("ticker").reset_index(drop=True)
print("✅ Trained models per ticker (validation performance):")
try:
    from tabulate import tabulate
    print(tabulate(perf_df.rename(columns={"MAE":"MAE","RMSE":"RMSE"}), headers="keys", tablefmt="psql", showindex=False))
except Exception:
    print(perf_df.to_string(index=False))

# -----------------------------------------------------------------------------
# 4) PREDICT FOR TARGET_DATE(S)
# -----------------------------------------------------------------------------
# Run two explicit dates: yesterday (2025-08-20) and today (2025-08-21)
TARGET_DATES = [
    pd.to_datetime("2025-08-20"),
    pd.to_datetime("2025-08-21"),
]

def row_cap(is_red):
    return RED_CAP if bool(is_red) else BASE_CAP

# Pretty labels for features -> what you’ll see in feature1..4
PRETTY_LABELS = {
    "overnight_drift": "Overnight drift",
    "ret_0900_1030_prev": "Prev intraday",
    "ret_0900_1030_prev_sign": "Prev sign",
    "VIX_delta": "ΔVIX",
    "ret1": "Daily return (lag1)",
    "vol5": "Vol(5)",
    "ma5": "MA(5)",
    "ma20": "MA(20)",
    "garch_vol": "GARCH vol",
    "RSI_14": "RSI",
    "MACD_line": "MACD",
    "BB_pos": "Bollinger %B",
}

def make_predictions_for_date(tdate: pd.Timestamp) -> pd.DataFrame:
    rows_pred = []
    for tkr in sorted(df_feat["ticker"].unique()):
        if tkr not in models_reg or tkr not in models_clf:
            continue

        d = df_feat[df_feat["ticker"] == tkr].sort_values("Date").reset_index(drop=True)
        row = d[d["Date"] == tdate]
        if row.empty:
            continue  # no data for that ticker on this date

        X_now = row[FEAT_COLS].to_numpy(dtype=float)
        Xi = imputers[tkr].transform(X_now)
        Xs = np.clip(scalers[tkr].transform(Xi), -5, 5) * WEIGHTS_VEC

        reg, clf = models_reg[tkr], models_clf[tkr]
        mag  = float(reg.predict(Xs).squeeze())
        prob = clf.predict_proba(Xs).squeeze()
        prob_up = float(prob[1]) if np.ndim(prob) == 1 else float(prob[0,1])
        prob_dn = 1.0 - prob_up
        margin  = abs(prob_up - 0.5) * 2.0

        pred_ret_dir = abs(mag) if prob_up >= 0.5 else -abs(mag)
        mag_blended  = (1.0 - MARGIN_BLEND) + (MARGIN_BLEND * margin)
        pred_ret_raw = pred_ret_dir * mag_blended

        is_red = bool(row["is_red_flag"].iloc[0]) if "is_red_flag" in row.columns else False
        cap = row_cap(is_red)
        pred_ret = soft_cap(pred_ret_raw, cap)

        p0900_now = float(row["P0900_imputed"].iloc[0])
        pred_1030 = p0900_now * (1.0 + pred_ret)

        # Per-feature contributions -> top 4 labels
        coefs = reg.coef_.reshape(-1)
        xvec  = Xs.reshape(-1)
        contrib = coefs * xvec
        order = np.argsort(-np.abs(contrib))
        top_labels = []
        for idx in order:
            fname = FEAT_COLS[idx]
            label = PRETTY_LABELS.get(fname, fname)
            if label not in top_labels:
                top_labels.append(label)
            if len(top_labels) == 4:
                break
        while len(top_labels) < 4:
            top_labels.append("—")

        rows_pred.append({
            "ticker": tkr,
            "date_used_for_features": str(pd.to_datetime(tdate).date()),
            "red_flag": is_red,
            "p0900_imputed": round(p0900_now, 6),
            "pred_ret(10:30 vs 09:00)": round(pred_ret, 6),
            "pred_1030_price": round(pred_1030, 6),
            "prob_up": round(prob_up, 6),
            "prob_down": round(prob_dn, 6),
            "prob_margin": round(margin, 6),
            "cap_used_%": int(cap * 100),
            "feat_top1": top_labels[0],
            "feat_top2": top_labels[1],
            "feat_top3": top_labels[2],
            "feat_top4": top_labels[3],
        })

    pred_df = pd.DataFrame(rows_pred)
    if pred_df.empty:
        print(f"ℹ️ No predictions available for {pd.to_datetime(tdate).date()} (no tickers with data on this date).")
        return pred_df

    pred_df = pred_df.sort_values(["ticker"]).reset_index(drop=True)
    print(f"✅ Predictions for {pd.to_datetime(tdate).date()}:")
    try:
        from tabulate import tabulate
        print(tabulate(pred_df.drop(columns=["feat_top1","feat_top2","feat_top3","feat_top4"]),
                       headers="keys", tablefmt="psql", showindex=False))
    except Exception:
        print(pred_df.drop(columns=["feat_top1","feat_top2","feat_top3","feat_top4"]).to_string(index=False))
    return pred_df

# Run for both dates and keep in a dict
pred_by_date = {tdate.date(): make_predictions_for_date(tdate) for tdate in TARGET_DATES}

# -----------------------------------------------------------------------------
# 5) CONFIDENCE SUMMARY
# -----------------------------------------------------------------------------
rows_conf = []
for tkr in sorted(df_feat["ticker"].unique()):
    if tkr not in models_reg or tkr not in models_clf:
        continue

    d = df_feat[df_feat["ticker"] == tkr].sort_values("Date").reset_index(drop=True)
    n = len(d)
    if n < 80:
        continue

    X = d[FEAT_COLS].to_numpy(dtype=float)
    y = d["ret_0900_1030"].to_numpy(dtype=float)
    p0900 = d["P0900_imputed"].to_numpy(dtype=float)
    redf  = d.get("is_red_flag", pd.Series(False, index=d.index)).to_numpy(dtype=bool)
    y_dir = (y > 0).astype(int)

    n_train, n_val, n_test = split_chrono(n)
    X_val = X[n_train:n_train+n_val]
    y_val = y[n_train:n_train+n_val]
    p0900_v = p0900[n_train:n_train+n_val]
    red_v = redf[n_train:n_train+n_val]

    Xi = imputers[tkr].transform(X_val)
    Xs = np.clip(scalers[tkr].transform(Xi), -5, 5) * 1.0  # ignore manual weights for conf

    mag_v = models_reg[tkr].predict(Xs)
    prob_v = models_clf[tkr].predict_proba(Xs)[:,1]
    dir_v = (prob_v >= 0.5).astype(int)
    pred_ret_raw = np.where(dir_v == 1, np.abs(mag_v), -np.abs(mag_v))
    pred_ret_cap = np.array([soft_cap(v, RED_CAP if red_v[i] else BASE_CAP) for i, v in enumerate(pred_ret_raw)])

    y_val_px  = p0900_v * (1.0 + y_val)
    y_pred_px = p0900_v * (1.0 + pred_ret_cap)

    mae_val  = mean_absolute_error(y_val_px, y_pred_px) if len(y_val_px) else np.nan
    rmse_val = float(np.sqrt(mean_squared_error(y_val_px, y_pred_px)) ) if len(y_val_px) else np.nan
    avg_px   = float(np.nanmean(p0900_v)) if len(p0900_v) else np.nan
    err_pct  = (rmse_val / avg_px * 100.0) if (avg_px and not np.isnan(avg_px)) else np.nan

    if np.isnan(err_pct):
        conf_cat = "Unknown"
    elif err_pct <= 0.5:
        conf_cat = "High"
    elif err_pct <= 1.5:
        conf_cat = "Medium"
    else:
        conf_cat = "Low"

    rows_conf.append({
        "ticker": tkr,
        "val_MAE_$": None if pd.isna(mae_val) else round(float(mae_val), 4),
        "val_RMSE_$": None if pd.isna(rmse_val) else round(float(rmse_val), 4),
        "avg_val_price": None if pd.isna(avg_px) else round(float(avg_px), 2),
        "error_%": None if pd.isna(err_pct) else round(float(err_pct), 3),
        "confidence": conf_cat
    })

conf_df = pd.DataFrame(rows_conf).sort_values("ticker").reset_index(drop=True)
print("✅ Model confidence:")
try:
    from tabulate import tabulate
    print(tabulate(conf_df, headers="keys", tablefmt="psql", showindex=False))
except Exception:
    print(conf_df.to_string(index=False))

# -----------------------------------------------------------------------------
# 6) FINAL NEWSWIRE CSV (TOP FEATURES INCLUDED) — for each requested date
# -----------------------------------------------------------------------------
# Build name map file if available
name_map = {}
nm1 = os.path.join(BASE_DIR, "ticker_to_name.csv")             # cols: ticker,name
nm2 = os.path.join(BASE_DIR, "sp500_constituents.csv")         # cols: Symbol,Security
if os.path.exists(nm1):
    try:
        tmp = pd.read_csv(nm1).rename(columns={"Ticker":"ticker","Name":"name"})
        if "ticker" in tmp.columns and "name" in tmp.columns:
            name_map = dict(zip(tmp["ticker"].astype(str), tmp["name"].astype(str)))
    except Exception:
        pass
elif os.path.exists(nm2):
    try:
        tmp = pd.read_csv(nm2)
        if "Symbol" in tmp.columns and "Security" in tmp.columns:
            name_map = dict(zip(tmp["Symbol"].astype(str), tmp["Security"].astype(str)))
    except Exception:
        pass

def confidence_score(row):
    base = {"High":3.0, "Medium":2.0, "Low":1.0}.get(str(row.get("confidence", "Unknown")), 1.5)
    pm = float(row.get("prob_margin", 0.0))
    return round(base + 0.5 * max(0.0, min(1.0, pm)), 1)

for dte, pred_today_df in pred_by_date.items():
    if pred_today_df is None or pred_today_df.empty:
        print(f"ℹ️ No predictions to export for {dte}.")
        continue

    today_date = pd.to_datetime(dte)
    out = pred_today_df.merge(conf_df[["ticker","confidence"]], on="ticker", how="left")

    rows_news = []
    for _, r in out.iterrows():
        price_1030 = float(r["pred_1030_price"])
        p0900_now  = float(r["p0900_imputed"])
        change_pct = (price_1030 / p0900_now - 1.0) * 100.0

        nm = name_map.get(r["ticker"], r["ticker"])
        cnum = confidence_score(r)

        rows_news.append({
            "date": today_date.date().isoformat(),
            "ticker": r["ticker"],
            "name": nm,
            "price": round(price_1030, 2),
            "change": round(change_pct, 1),
            "confidence": cnum,
            "feature1": r.get("feat_top1", "—"),
            "feature2": r.get("feat_top2", "—"),
            "feature3": r.get("feat_top3", "—"),
            "feature4": r.get("feat_top4", "—"),
        })

    news_df = pd.DataFrame(rows_news)
    if not news_df.empty:
        news_df = news_df.sort_values(by=["confidence","change"], ascending=[False, False]).reset_index(drop=True)

    print(f"✅ Newswire-style rows for {today_date.date()}:")
    print(",".join(news_df.columns))
    for _, r in news_df.head(20).iterrows():
        print(f"{r['date']},{r['ticker']},{r['name']},{r['price']},{r['change']},{r['confidence']},{r['feature1']},{r['feature2']},{r['feature3']},{r['feature4']}")

    out_csv_path = os.path.join(OUTPUT_DIR, f"predictions_newswire_{today_date.date().isoformat()}.csv")
    news_df.to_csv(out_csv_path, index=False)
    print(f"💾 Saved: {out_csv_path}")
