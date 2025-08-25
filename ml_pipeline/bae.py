#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
bae_patched_all_FIXED-2.py  (hybrid: close-first features + BAE-1 confidence 0–10)

What you get:
- Rolling features computed from FULL close history first (ret1/ma5/ma20/vol5/garch_vol).
- Intraday panel built from 09:00 + 10:30 + daily close (with 09:00 imputed from prev close).
- Optional TA merge (final_lstm_features.csv in long or recognizable wide format) with per-ticker ffill.
- Per-ticker models (GBR for regression; LR or constant-proba for direction).
- BAE-1 style weighted confidence normalized to **0–10** using FEATURE_WEIGHTS (never exceeds 10).
- Predictions appended to predictions_history.csv with columns:
  [date, ticker, name, price, change, confidence, feature1..feature4]
"""

import os
import sys
import math
import warnings
from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------- Pretty names ----------------
_PRETTY_FEATURE = {
    "overnight_drift": "Overnight drift",
    "ret_0900_1030_prev": "Prev intraday ret",
    "ret_0900_1030_prev_sign": "Prev intraday sign",
    "VIX_delta": "ΔVIX",
    "ret1": "Ret(1d)",
    "vol5": "Vol(5)",
    "ma5": "MA(5)",
    "ma20": "MA(20)",
    "garch_vol": "GARCH vol",
    "RSI_14": "RSI(14)",
    "MACD_line": "MACD line",
    "BB_pos": "BB pos",
}
def _pretty_feat(name: str) -> str:
    return _PRETTY_FEATURE.get(name, name)

# --------------- Logging helpers ---------------
def _print_ok(msg: str):   print(f"✅ {msg}")
def _print_warn(msg: str): print(f"⚠️ {msg}")
def _print_err(msg: str):  print(f"❌ {msg}")

# --------------- Name utilities ----------------
def _norm(s) -> str: return str(s).strip().lower()
def _canon_tkr(s: str) -> str: return str(s).replace(".", "-").strip().upper()

def _find_ci_column(df: pd.DataFrame, target_lc: str):
    for c in df.columns:
        if _norm(c) == target_lc:
            return c
    return None

def _find_first_of(df: pd.DataFrame, targets_lc):
    targets = {t.lower() for t in targets_lc}
    for c in df.columns:
        if _norm(c) in targets:
            return c
    return None

# --------------- Date parsing ------------------
def _smart_parse_dates(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    def try_parse(dayfirst=None, fmt=None):
        try:
            return pd.to_datetime(s, dayfirst=dayfirst, format=fmt, errors="coerce")
        except Exception:
            return pd.Series([pd.NaT] * len(s))
    candidates = [
        try_parse(dayfirst=False),
        try_parse(dayfirst=True),
        try_parse(fmt="%d/%m/%Y"),
        try_parse(fmt="%m/%d/%Y"),
        try_parse(fmt="%Y-%m-%d"),
    ]
    best = min(candidates, key=lambda ser: ser.isna().sum())
    if best.isna().mean() > 0.5:
        return try_parse(dayfirst=True)
    return best

def read_csv_or_fail(path: str, label: str) -> pd.DataFrame:
    if not path or not os.path.exists(path):
        _print_err(f"{label} missing at path: {path}"); sys.exit(2)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        _print_err(f"Could not read {label} ({path}): {e}"); sys.exit(2)

    date_col = _find_ci_column(df, "date")
    if date_col is None:
        date_col = _find_first_of(df, ["Date","DATE","trade_date","day","dt","Unnamed: 0","index"])
    if date_col is None:
        _print_err(f"{label}: 'Date' column not found.")
        print("  Available columns:", list(df.columns))
        sys.exit(2)

    parsed = _smart_parse_dates(df[date_col])
    if parsed.isna().all():
        _print_err(
            f"{label}: failed to parse any dates in column '{date_col}'. "
            f"Example values: {df[date_col].head(5).tolist()}"
        ); sys.exit(2)

    df["Date"] = parsed
    if date_col != "Date":
        try: df.drop(columns=[date_col], inplace=True)
        except Exception: pass
    return df

def find_first_existing(base_dir, candidates):
    for name in candidates:
        p = os.path.join(base_dir, name)
        if os.path.exists(p):
            return p
    return None

# --------------- Modeling helpers --------------
def _align_to_estimator_features(X: pd.DataFrame, estimator):
    X = X.copy()
    if hasattr(estimator, "feature_names_in_"):
        cols = list(estimator.feature_names_in_)
        for c in cols:
            if c not in X.columns:
                X[c] = np.nan
        return X[cols]
    n = getattr(estimator, "n_features_in_", X.shape[1])
    return X.iloc[:, :n]

def _post_impute(df_imp: pd.DataFrame) -> pd.DataFrame:
    return df_imp.fillna(0.0)

# === BAE-1 style feature weights (used for 0–10 confidence) ===
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

def _weighted_confidence_from_scaled(X_scaled: np.ndarray, cols_in_order: list, weights: dict) -> np.ndarray:
    """
    Turn z-scored features into a 0–10 weighted confidence.
    Faster-rising curve so good signals land 6–8 more often. Hard cap at 10.
    """
    if X_scaled.size == 0:
        return np.zeros((0,), dtype=float)

    w_vec = np.array([weights.get(c, 0.0) for c in cols_in_order], dtype=float)
    w_sum = w_vec.sum()
    if w_sum <= 0:
        return np.zeros((X_scaled.shape[0],), dtype=float)

    # Contribution per feature from its |z|:
    # - Divisor 1.2 (vs 2.0) makes moderate z matter more
    # - Power 0.7 softens small z penalty
    contrib = np.minimum(1.0, (np.abs(X_scaled) / 1.2)) ** 0.7  # shape (n_rows, n_feat)

    raw = np.dot(contrib, w_vec)        # (n_rows,)
    conf = 10.0 * raw / w_sum           # scale to 0–10
    return np.clip(conf, 0.0, 10.0)

# --------------- Daily (close) features --------
def compute_daily_close_features(dfclose_wide: pd.DataFrame) -> pd.DataFrame:
    """Return long table with Date, ticker, Close_t, Close_t_minus_1, ret1, ma5, ma20, vol5, garch_vol."""
    def _ewma_abs_ret(s, alpha=0.2):
        out, prev = [], np.nan
        for x in s.fillna(0.0):
            val = (alpha * abs(x)) + ((1 - alpha) * (prev if not np.isnan(prev) else abs(x)))
            out.append(val); prev = val
        return pd.Series(out, index=s.index)

    # melt to long
    long = dfclose_wide.melt(id_vars=["Date"], var_name="ticker", value_name="Close_t")
    long["ticker"] = long["ticker"].map(_canon_tkr)
    long = long.sort_values(["ticker","Date"]).reset_index(drop=True)

    # prev close and daily return
    long["Close_t_minus_1"] = long.groupby("ticker")["Close_t"].shift(1)
    long["ret1"] = (long["Close_t"] - long["Close_t_minus_1"]) / long["Close_t_minus_1"]

    # rolling features computed on the FULL daily history
    long["ma5"]  = long.groupby("ticker")["Close_t"].transform(lambda s: s.rolling(5,  min_periods=5).mean())
    long["ma20"] = long.groupby("ticker")["Close_t"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    long["vol5"] = long.groupby("ticker")["ret1"].transform(lambda s: s.rolling(5,  min_periods=5).std())
    long["garch_vol"] = long.groupby("ticker")["ret1"].transform(lambda s: _ewma_abs_ret(s))

    return long  # NaNs only on earliest daily rows per ticker (dropped after merge)

# --------------- Intraday merge ----------------
def build_intraday_feature_table(df1030_wide, df0900_wide, daily_close_long):
    # intraday long
    L1030 = df1030_wide.melt(id_vars=["Date"], var_name="ticker", value_name="P1030")
    L0900 = df0900_wide.melt(id_vars=["Date"], var_name="ticker", value_name="P0900")
    for L in (L1030, L0900):
        L["ticker"] = L["ticker"].map(_canon_tkr)

    # merge intraday with daily close features
    df = L1030.merge(L0900, on=["Date","ticker"], how="outer")
    df = df.merge(daily_close_long, on=["Date","ticker"], how="left")

    # Impute 09:00 with previous close if missing
    df = df.sort_values(["ticker","Date"]).reset_index(drop=True)
    df["P0900_imputed"] = df["P0900"]
    m = df["P0900_imputed"].isna() & df["Close_t_minus_1"].notna()
    df.loc[m, "P0900_imputed"] = df.loc[m, "Close_t_minus_1"]

    # Target & overnight drift
    df["ret_0900_1030"] = (df["P1030"] - df["P0900_imputed"]) / df["P0900_imputed"]
    df["overnight_drift"] = (df["P0900_imputed"] - df["Close_t_minus_1"]) / df["Close_t_minus_1"]

    return df

# --------------- TA merge (wide/long) ----------
def _melt_wide_ta(ta: pd.DataFrame):
    cols = [c for c in ta.columns if c != "Date"]
    suffix_map = {"rsi14": "RSI_14", "macd": "MACD_line", "bbp": "BB_pos"}
    out = {"RSI_14": None, "MACD_line": None, "BB_pos": None}

    for suf_lc, canon in suffix_map.items():
        match_cols = [c for c in cols if _norm(c).endswith("_" + suf_lc)]
        if not match_cols:
            continue
        tmp = ta[["Date"] + match_cols].copy()
        rename_map = {}
        for c in match_cols:
            pos = c.lower().rfind("_")
            ticker = _canon_tkr(c[:pos])
            rename_map[c] = ticker
        tmp.rename(columns=rename_map, inplace=True)
        long = tmp.melt(id_vars=["Date"], var_name="ticker", value_name=canon)
        out[canon] = long

    frames = [df for df in out.values() if df is not None]
    if not frames:
        return None
    merged = frames[0]
    for df in frames[1:]:
        merged = merged.merge(df, on=["Date","ticker"], how="outer")
    return merged

def merge_optional_ta(df_feat, base_dir, ffill_ta=True):
    ta_path = find_first_existing(base_dir, ["final_lstm_features.csv"])
    if not ta_path:
        _print_warn("final_lstm_features.csv not found; skipping TA merge.")
        return df_feat, []

    ta = read_csv_or_fail(ta_path, "final_lstm_features.csv")

    # try long format first
    ticker_col = _find_first_of(ta, ["ticker","symbol","ric","secid","security","Ticker","Symbol"])
    if ticker_col is not None:
        if ticker_col != "ticker":
            ta.rename(columns={ticker_col: "ticker"}, inplace=True)
        ta["ticker"] = ta["ticker"].map(_canon_tkr)

        lc_map = { _norm(c): c for c in ta.columns }
        ren = {}
        for alt, canon in [("rsi_14","RSI_14"), ("rsi14","RSI_14"),
                           ("macd_line","MACD_line"), ("macd","MACD_line"),
                           ("bb_pos","BB_pos"), ("bbp","BB_pos")]:
            if alt in lc_map: ren[lc_map[alt]] = canon
        if ren: ta.rename(columns=ren, inplace=True)

        ta_cols = [c for c in ["RSI_14","MACD_line","BB_pos"] if c in ta.columns]
        if not ta_cols:
            _print_warn("No known TA columns in final_lstm_features.csv; skipping TA merge.")
            return df_feat, []
        keep = ["Date","ticker"] + ta_cols
        ta_small = ta[keep].copy()
        merged = df_feat.merge(ta_small, on=["Date","ticker"], how="left")
    else:
        ta_wide_long = _melt_wide_ta(ta)
        if ta_wide_long is None:
            _print_warn("TA file present but neither long nor recognizable wide format; skipping TA merge.")
            return df_feat, []
        merged = df_feat.merge(ta_wide_long, on=["Date","ticker"], how="left")

    # optional TA forward-fill per ticker
    ta_cols = [c for c in ["RSI_14","MACD_line","BB_pos"] if c in merged.columns]
    if ffill_ta and ta_cols:
        merged.sort_values(["ticker","Date"], inplace=True)
        merged[ta_cols] = merged.groupby("ticker")[ta_cols].ffill()

    _print_ok(f"Merged TA (wide or long)")
    print("   Added features:", ta_cols)
    print(merged[["Date","ticker"] + ta_cols].head(10).to_string(index=False))
    return merged, ta_cols

# --------------- Models ------------------------
@dataclass
class TickerModels:
    imputer: SimpleImputer
    reg: Pipeline
    clf: object
    feature_names_: list

class ConstantProba:
    def __init__(self, p_up: float): self.p_up = float(max(0.0, min(1.0, p_up)))
    def predict_proba(self, X):
        n = len(X); p1 = np.full(n, self.p_up, dtype=float); p0 = 1.0 - p1
        return np.column_stack([p0, p1])
    def decision_function(self, X):
        p = min(max(self.p_up, 1e-12), 1.0 - 1e-12)
        return np.full(len(X), math.log(p / (1.0 - p)), dtype=float)

def build_models_for_ticker(df_tkr: pd.DataFrame, feat_cols):
    df_tkr = df_tkr.sort_values("Date").reset_index(drop=True)
    y_full = df_tkr["ret_0900_1030"].astype(float)
    X_full = df_tkr[feat_cols].copy()
    mask = y_full.notna() & X_full.notna().any(axis=1)
    y = y_full[mask]; X = X_full[mask]
    if len(X) < 10: return None, (0, 0, np.nan, np.nan)

    n = len(X); n_valid = min(48, max(1, n // 5)); n_train = n - n_valid if n > n_valid else max(1, n - 1)
    X_train, X_val = X.iloc[:n_train], X.iloc[n_train:]
    y_train, y_val = y.iloc[:n_train], y.iloc[n_train:]

    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    X_train_imp = pd.DataFrame(imputer.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_train_imp = _post_impute(X_train_imp)

    reg = Pipeline([("scaler", StandardScaler()), ("gb", GradientBoostingRegressor(random_state=42))])
    reg.fit(X_train_imp, y_train)

    y_cls = (y_train > 0).astype(int)
    if y_cls.nunique() >= 2:
        clf = Pipeline([("scaler", StandardScaler(with_mean=True, with_std=True)),
                        ("lr", LogisticRegression(max_iter=200))])
        clf.fit(X_train_imp, y_cls)
    else:
        clf = ConstantProba(0.99 if (len(y_cls)>0 and y_cls.iloc[0]==1) else 0.01)

    if len(X_val) > 0:
        Xv = _align_to_estimator_features(X_val, imputer)
        Xv_imp = pd.DataFrame(imputer.transform(Xv), columns=X_train.columns, index=Xv.index)
        Xv_imp = _post_impute(Xv_imp)
        y_pred = reg.predict(Xv_imp)
        mae = mean_absolute_error(y_val, y_pred); rmse = math.sqrt(mean_squared_error(y_val, y_pred))
    else:
        mae = np.nan; rmse = np.nan

    return TickerModels(imputer=imputer, reg=reg, clf=clf, feature_names_=list(X_train.columns)), (n_train, len(X_val), mae, rmse)

# --------- Confidence (0–10) from weights ----------
def _compute_confidence10(model: "TickerModels", X_one_imp: pd.DataFrame) -> float:
    """
    Use the regression pipeline's scaler to z-score the same feature space,
    then map to a 0–10 weighted confidence via FEATURE_WEIGHTS.
    """
    try:
        scaler = model.reg.named_steps.get("scaler", None)
        if scaler is None:
            return 0.0

        X_for_scaler = X_one_imp.copy()

        # Ensure same column order/coverage the scaler was fit on:
        if hasattr(scaler, "feature_names_in_"):
            needed = list(scaler.feature_names_in_)
            for c in needed:
                if c not in X_for_scaler.columns:
                    X_for_scaler[c] = 0.0
            X_for_scaler = X_for_scaler[needed]

        X_scaled = scaler.transform(X_for_scaler)
        conf_arr = _weighted_confidence_from_scaled(X_scaled, list(X_for_scaler.columns), FEATURE_WEIGHTS)
        return float(conf_arr[0])
    except Exception:
        return 0.0

# --------------- Predict for a date -------------
def predict_for_date(df_feat, tickers, feat_cols, models_dict, pred_date):
    rows = []
    for tkr in tickers:
        m = models_dict.get(tkr)
        if m is None: continue
        df_tkr = df_feat[(df_feat["ticker"] == tkr) & (df_feat["Date"].dt.date == pred_date)]
        if df_tkr.empty: continue
        row = df_tkr.iloc[-1]
        X_one = pd.DataFrame([row[feat_cols].values], columns=feat_cols)

        # align to imputer's features
        X_one_aligned = _align_to_estimator_features(X_one, m.imputer)
        X_one_imp = pd.DataFrame(m.imputer.transform(X_one_aligned), columns=X_one_aligned.columns)
        X_one_imp = _post_impute(X_one_imp)

        # regression prediction
        pred_ret = float(m.reg.predict(X_one_imp)[0])

        # probability (optional)
        try:
            prob_up = float(m.clf.predict_proba(X_one_imp)[0, 1])
        except Exception:
            z = float(m.clf.decision_function(X_one_imp)[0])
            prob_up = 1.0 / (1.0 + math.exp(-z))
        prob_down = 1.0 - prob_up
        prob_margin = abs(prob_up - prob_down)

        # NEW: 0–10 confidence based on bae-1 weights (never exceeds 10)
        conf10 = _compute_confidence10(m, X_one_imp)

        p0900 = float(row["P0900_imputed"]) if not pd.isna(row["P0900_imputed"]) else np.nan
        pred_1030_price = p0900 * (1.0 + pred_ret) if not pd.isna(p0900) else np.nan

        # Use confidence directly for capital (0–10)
        cap_used = int(round(max(0.0, min(10.0, conf10))))

        red_flag = bool(pd.isna(p0900) or pd.isna(pred_ret))

        rows.append([
            tkr, pred_date.isoformat(), red_flag, p0900, pred_ret, pred_1030_price,
            prob_up, prob_down, prob_margin, cap_used, conf10
        ])
    if not rows:
        _print_warn(f"No tickers had rows for {pred_date}.")
        return pd.DataFrame(columns=[
            "ticker","date_used_for_features","red_flag","p0900_imputed",
            "pred_ret(10:30 vs 09:00)","pred_1030_price","prob_up","prob_down",
            "prob_margin","cap_used_%","confidence"
        ])
    return pd.DataFrame(rows, columns=[
        "ticker","date_used_for_features","red_flag","p0900_imputed",
        "pred_ret(10:30 vs 09:00)","pred_1030_price","prob_up","prob_down",
        "prob_margin","cap_used_%","confidence"
    ])

# --------------- Top features helper -----------
def _top4_features_for_ticker(model: "TickerModels") -> list:
    feat_names = getattr(model, "feature_names_", None)
    if feat_names is None: return []
    try:
        gb = model.reg.named_steps.get("gb", None)
        if gb is not None and hasattr(gb, "feature_importances_"):
            imps = gb.feature_importances_
            order = list(np.argsort(imps)[::-1])
            names_sorted = [feat_names[i] for i in order]
            return [_pretty_feat(n) for n in names_sorted[:4]]
    except Exception:
        pass
    return [_pretty_feat(n) for n in feat_names[:4]]

# --------------- Save predictions CSV ----------
def save_predictions_csv(base_dir, df_preds, models_dict, pred_date):
    out_path = os.path.join(base_dir, "predictions_history.csv")
    rows = []
    for _, r in df_preds.iterrows():
        tkr = r["ticker"]
        price = r["pred_1030_price"]
        change = r["pred_ret(10:30 vs 09:00)"] * 100.0

        # prefer model-based 0–10 confidence; fall back to prob_margin*10 if needed
        if "confidence" in r.index and pd.notna(r["confidence"]):
            confidence = float(max(0.0, min(10.0, r["confidence"])))
        else:
            confidence = float(max(0.0, min(10.0, (r["prob_margin"] * 10.0) if "prob_margin" in r.index else 0.0)))

        top_feats = _top4_features_for_ticker(models_dict.get(tkr))
        while len(top_feats) < 4: top_feats.append("")
        rows.append([pred_date.isoformat(), tkr, tkr,
                     round(price, 2) if pd.notna(price) else "",
                     round(change, 1) if pd.notna(change) else "",
                     round(confidence, 1),
                     top_feats[0], top_feats[1], top_feats[2], top_feats[3]])
    df_out = pd.DataFrame(rows, columns=[
        "date","ticker","name","price","change","confidence","feature1","feature2","feature3","feature4"
    ])
    if os.path.exists(out_path):
        try:
            old = pd.read_csv(out_path)
            merged = pd.concat([old, df_out], ignore_index=True)
            merged = merged.drop_duplicates(subset=["date","ticker"], keep="last")
            merged = merged.sort_values(["date","ticker"])
            merged.to_csv(out_path, index=False)
        except Exception:
            df_out.to_csv(out_path, index=False)
    else:
        df_out.to_csv(out_path, index=False)
    _print_ok(f"Predictions appended to {os.path.abspath(out_path)}")

# --------------- Date chooser ------------------
def choose_prediction_date(available_dates, today=None, max_lookahead_days=1):
    if today is None:
        today = date.today()
    def _as_date(d):
        if isinstance(d, datetime): return d.date()
        if isinstance(d, (np.datetime64, pd.Timestamp)): return pd.to_datetime(d).date()
        return d
    avail = sorted({_as_date(d) for d in available_dates if not pd.isna(d)})
    if not avail: return None, "No available dates found."
    if today in avail and today.weekday() < 5: return today, None
    for d in avail:
        if d >= today and (d - today).days <= max_lookahead_days: return d, None
    past = [d for d in avail if d <= today]
    if past: return past[-1], None
    return avail[-1], f"Using {avail[-1]} from data because we found no usable date near {today}."

# --------------- Main --------------------------
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Locate inputs (prefer your new closing file)
    p1030_path = find_first_existing(base_dir, ["stock_prices_1030_wide_format.csv"])
    p0900_path = find_first_existing(base_dir, ["stock_prices_0900_wide_format.csv"])
    close_path = find_first_existing(base_dir, [
        "historical_closing_prices.csv",                    # preferred
        "stock_prices_close_wide_format.csv",
        "historical_closing_prices_wide_format.csv",
        "historical_closing_prices_old.csv"
    ])

    if not p1030_path or not close_path:
        _print_err("Required files missing. Ensure 10:30 and Close price CSVs exist in this folder.")
        print("Expected:\n  - stock_prices_1030_wide_format.csv\n  - one of: historical_closing_prices.csv | stock_prices_close_wide_format.csv | historical_closing_prices_wide_format.csv | historical_closing_prices_old.csv")
        sys.exit(2)

    # Read with robust parsers
    df1030 = read_csv_or_fail(p1030_path, "10:30 prices")
    dfclose = read_csv_or_fail(close_path, "Close prices")
    if p0900_path:
        df0900 = read_csv_or_fail(p0900_path, "09:00 prices")
    else:
        df0900 = dfclose.copy()
        for c in df0900.columns:
            if c != "Date": df0900[c] = np.nan
        _print_warn("09:00 file not found; using NaN 09:00 prices (will be imputed).")

    # Canonicalize ticker columns across inputs (UPPERCASE + '.' -> '-')
    def _canon_cols(df):
        df = df.copy()
        df.columns = ["Date" if _norm(c) == "date" else _canon_tkr(c) for c in df.columns]
        return df
    df1030 = _canon_cols(df1030)
    df0900 = _canon_cols(df0900)
    dfclose = _canon_cols(dfclose)

    _print_ok(f"Using 10:30 prices: {p1030_path}")
    _print_ok(f"Using 09:00 prices: {p0900_path if p0900_path else '(missing -> impute)'}")
    _print_ok(f"Using Close prices: {close_path}")

    # --- Compute daily features from FULL close history first
    daily_close_long = compute_daily_close_features(dfclose)

    # Build intraday feature table by merging with daily features
    df_feat = build_intraday_feature_table(df1030, df0900, daily_close_long)

    # --------- FILTERS ----------
    df_feat = df_feat[df_feat["Date"].dt.weekday < 5].copy()
    valid_close_dates = set(dfclose["Date"].dt.date.unique())
    df_feat = df_feat[df_feat["Date"].dt.date.isin(valid_close_dates)].copy()
    df_feat = df_feat[df_feat["P1030"].notna() & df_feat["P0900_imputed"].notna()].copy()

    # Lags within the intraday set
    df_feat = df_feat.sort_values(["ticker","Date"]).reset_index(drop=True)
    df_feat["ret_0900_1030_prev"] = df_feat.groupby("ticker")["ret_0900_1030"].shift(1)
    df_feat["ret_0900_1030_prev_sign"] = np.sign(df_feat["ret_0900_1030_prev"]).astype(float)
    df_feat = df_feat[df_feat["ret_0900_1030_prev"].notna()].copy()

    # Optional VIX
    vix_path = find_first_existing(base_dir, ["vix_prices.csv", "vix_open_clean.csv"])
    if vix_path:
        vix = read_csv_or_fail(vix_path, "VIX")
        vix_close_col = None
        for c in ["Close","close","VIX","vix","price","Price"]:
            if c in vix.columns:
                vix_close_col = c; break
        if vix_close_col:
            vix_small = vix[["Date", vix_close_col]].copy().rename(columns={vix_close_col: "VIX"})
            vix_small = vix_small.sort_values("Date")
            vix_small["VIX_prev"] = vix_small["VIX"].shift(1)
            vix_small["VIX_delta"] = vix_small["VIX"] - vix_small["VIX_prev"]
            df_feat = df_feat.merge(vix_small[["Date","VIX_delta"]], on="Date", how="left")
        else:
            df_feat["VIX_delta"] = np.nan
    else:
        df_feat["VIX_delta"] = np.nan

    base_feats = ['overnight_drift','ret_0900_1030_prev','ret_0900_1030_prev_sign',
                  'ret1','vol5','ma5','ma20','garch_vol']
    if "VIX_delta" in df_feat.columns and df_feat["VIX_delta"].notna().any():
        base_feats.insert(3, "VIX_delta")
    else:
        _print_warn("VIX_delta is empty in this dataset; excluding it from features.")

    # Optional TA merge (forward-fill to avoid TA warm-up NaNs)
    df_feat, ta_cols = merge_optional_ta(df_feat, base_dir, ffill_ta=True)
    ta_feats = [c for c in ["RSI_14","MACD_line","BB_pos"] if c in df_feat.columns]
    feat_cols = base_feats + ta_feats

    # Final sanity: drop any lingering NaNs in required features
    must_have = ['ret_0900_1030'] + feat_cols
    missing = df_feat[must_have].isna().sum().sort_values(ascending=False)
    if missing.sum() > 0:
        _print_warn(f"Residual NaNs found in features/target; dropping those rows:\n{missing[missing>0]}")
        df_feat = df_feat.dropna(subset=must_have).copy()

    _print_ok(f"Feature table ready | rows: {len(df_feat):,} | features: {len(feat_cols)}")
    print("Features:", feat_cols)

    # Preview
    preview_cols = ["Date","ticker","P1030","P0900","Close_t","Close_t_minus_1",
                    "P0900_imputed","ret_0900_1030"] + feat_cols
    preview_cols = [c for c in preview_cols if c in df_feat.columns]
    print(df_feat[preview_cols].head(10).to_string(index=False))

    # Train per-ticker models
    tickers = sorted([c for c in df1030.columns if c != "Date"])
    models, perf_rows = {}, []
    for tkr in tickers:
        df_tkr = df_feat[df_feat["ticker"] == tkr].copy()
        if df_tkr.empty: continue
        tm, (n_train, n_val, mae, rmse) = build_models_for_ticker(df_tkr, feat_cols)
        if tm is None:
            _print_warn(f"Skipping {tkr}: not enough clean rows after dropping NaN targets.")
            continue
        models[tkr] = tm
        perf_rows.append((tkr, mae, rmse, n_train, n_val))

    if perf_rows:
        df_perf = pd.DataFrame(perf_rows, columns=["ticker","MAE","RMSE","n_train","n_test"]).sort_values("ticker")
        print("✅ Trained models per ticker (validation performance):")
        with pd.option_context("display.max_rows", None):
            print(df_perf.to_string(index=False, justify="right",
                                    float_format=lambda x: f"{x:10.6f}" if pd.notna(x) else "        NaN"))
    else:
        _print_warn("No models trained (empty perf).")

    # Choose prediction date
    pred_date, note = choose_prediction_date(df_feat["Date"].dt.date.unique(), today=date.today(), max_lookahead_days=1)
    if note: _print_warn(note)
    print(f"✅ Predictions for {pred_date}:")

    df_preds = predict_for_date(df_feat, tickers, feat_cols, models, pred_date)

    if not df_preds.empty:
        cols_order = ["ticker","date_used_for_features","red_flag","p0900_imputed",
                      "pred_ret(10:30 vs 09:00)","pred_1030_price","prob_up","prob_down",
                      "prob_margin","cap_used_%","confidence"]
        df_preds = df_preds[cols_order]
        with pd.option_context("display.max_rows", None):
            print(df_preds.to_string(index=False,
                                     float_format=lambda x: f"{x:0.6f}",
                                     justify="right"))
    else:
        _print_warn("No predictions to display.")

    try:
        save_predictions_csv(base_dir, df_preds, models, pred_date)
    except Exception as e:
        _print_warn(f"Could not save predictions_history.csv: {e}")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        raise e
    except Exception as e:
        _print_err(f"Unhandled exception: {e}")
        sys.exit(1)
