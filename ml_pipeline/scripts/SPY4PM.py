#!/usr/bin/env python3
"""
SPY4PM.py — Build previous TRADING-DAY 4:00 PM close for SPY.

Output CSV:
  Date, SPY_close, SPY_prev_close, spy_prev_cc_ret

Default range:
  --start 2021-01-01  --end <today in America/New_York>

Fixes / improvements:
  - Includes the newest available close by patching the last trading day with
    intraday (1m) data if Yahoo's daily bar hasn't updated yet.
  - Detects early-close days by using the last intraday bar of the session.
  - Robust handling of timezones and MultiIndex columns from yfinance.
"""

import argparse
from datetime import datetime, date, time
from typing import Optional

import pandas as pd
import yfinance as yf
import sys
import os
# Force UTF-8 sur Windows
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')
try:
    from zoneinfo import ZoneInfo  # py>=3.9
    NY = ZoneInfo("America/New_York")
except Exception:
    import pytz
    NY = pytz.timezone("America/New_York")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=str, default="2021-01-01",
                   help="Start date (YYYY-MM-DD)")
    p.add_argument("--end",   type=str, default=None,
                   help="End date inclusive (YYYY-MM-DD). Default = today in New York.")
    p.add_argument("--out",   type=str, default="spy_prev_close_4pm.csv",
                   help="Output CSV path")
    return p.parse_args()


def ny_now() -> datetime:
    """Current wall-clock time in New York."""
    return datetime.now(NY)


def today_ny_yyyy_mm_dd() -> str:
    # “Today” in New York (handles UTC offset & DST)
    return ny_now().date().isoformat()


def _extract_close_series(df: pd.DataFrame) -> pd.Series:
    """Return a 1-D Series of closes from a yfinance DataFrame (handles MultiIndex)."""
    df = df.copy()
    df.index = pd.DatetimeIndex(df.index).tz_localize(None)

    if isinstance(df.columns, pd.MultiIndex):
        # common patterns
        if ('Close', 'SPY') in df.columns:
            s = df[('Close', 'SPY')]
        elif ('SPY', 'Close') in df.columns:
            s = df[('SPY', 'Close')]
        else:
            close_cols = [c for c in df.columns if isinstance(c, tuple) and 'Close' in c]
            if not close_cols:
                raise KeyError("Could not locate 'Close' in MultiIndex columns.")
            s = df[close_cols[0]]
    else:
        if 'Close' not in df.columns:
            raise KeyError("Column 'Close' not found in downloaded DataFrame.")
        s = df['Close']

    if isinstance(s, pd.DataFrame):
        if s.shape[1] == 1:
            s = s.iloc[:, 0]
        else:
            s = s.squeeze()

    if not isinstance(s, pd.Series):
        raise TypeError("Could not coerce Close data to a 1-D Series.")
    return s.astype(float)


def _get_intraday_close_for(target_date: date) -> Optional[float]:
    """
    Return the regular-session close for target_date using 1-minute data if available.
    - Prefers 16:00 NY bar.
    - If not present (e.g., early close), uses the last intraday bar of that date
      provided that at least 5 minutes have elapsed since that bar.
    Returns None if not determinable.
    """
    try:
        # 1-minute data is only available for ~7 days; 2d is enough for 'today'.
        intraday = yf.download(
            "SPY", period="5d", interval="1m", progress=False, auto_adjust=False, prepost=False
        )
    except Exception:
        return None

    if intraday is None or intraday.empty:
        return None

    # yfinance intraday index is timezone-aware (UTC). Convert to NY.
    idx = pd.DatetimeIndex(intraday.index)
    if idx.tz is None:
        intraday.index = idx.tz_localize("UTC").tz_convert(NY)
    else:
        intraday.index = idx.tz_convert(NY)

    day = intraday.loc[intraday.index.date == target_date]
    if day.empty:
        return None

    four_pm = pd.Timestamp.combine(target_date, time(16, 0)).replace(tzinfo=NY)

    # Exact 16:00 bar preferred when present (normal full session)
    if four_pm in day.index:
        val = day.loc[four_pm]
        try:
            return float(val["Close"])  # typical yfinance columns
        except Exception:
            # In rare cases, yfinance returns MultiIndex columns; fallback safely
            if isinstance(val, pd.Series) and "Close" in val.index:
                return float(val["Close"])  # type: ignore[index]
            return None

    # Early close (e.g., 13:00) or slight bar timing variations.
    last_ts = day.index.max()
    # Only trust if we're at least 5 minutes beyond the last bar (session closed)
    if ny_now() > (last_ts + pd.Timedelta(minutes=5)):
        try:
            return float(day.loc[last_ts, "Close"])  # last intraday bar's close
        except Exception:
            val = day.loc[last_ts]
            if isinstance(val, pd.Series) and "Close" in val.index:
                return float(val["Close"])  # type: ignore[index]
            return None

    return None


def get_trading_days(start_str: str, end_str: str) -> pd.DatetimeIndex:
    """US trading-day calendar via ^GSPC (handles weekends/holidays).
    Will **append today** if intraday data indicates a completed session but the
    daily ^GSPC bar hasn't posted yet.
    """
    # +1 day so end date appears in index
    end_plus = (pd.to_datetime(end_str) + pd.Timedelta(days=1)).date().isoformat()
    cal = yf.download("^GSPC", start=start_str, end=end_plus, progress=False, auto_adjust=False)

    if cal.empty:
        idx = pd.bdate_range(start=start_str, end=end_str)
    else:
        idx = pd.DatetimeIndex(cal.index).tz_localize(None)

    # If end_str is "today" in NY and the GSPC daily hasn't landed yet, but intraday
    # shows we've closed, include today.
    end_dt = pd.to_datetime(end_str).date()
    today_ny = ny_now().date()
    if end_dt == today_ny:
        if pd.Timestamp(end_dt) not in idx:
            intraday_close = _get_intraday_close_for(end_dt)
            if intraday_close is not None:
                idx = idx.append(pd.DatetimeIndex([pd.Timestamp(end_dt)]))

    # Ensure we only keep the requested range (inclusive)
    idx = idx[(idx >= pd.to_datetime(start_str)) & (idx <= pd.to_datetime(end_str))]
    return pd.DatetimeIndex(idx.unique().sort_values())


def build_spy_prev_close(trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Download SPY daily, align to trading_days, compute prev close + cc return.
    If the last trading day is missing a daily close, we patch it with intraday.
    """
    start = trading_days.min().date()
    end   = trading_days.max().date()
    start_dl = (pd.to_datetime(start) - pd.Timedelta(days=10)).date().isoformat()
    end_dl   = (pd.to_datetime(end) + pd.Timedelta(days=1)).date().isoformat()

    spy_raw = yf.download("SPY", start=start_dl, end=end_dl, progress=False, auto_adjust=False)
    if spy_raw.empty:
        raise RuntimeError("Could not download SPY daily data from Yahoo.")

    spy_close = _extract_close_series(spy_raw)

    out = pd.DataFrame(index=trading_days)
    out.index.name = "Date"
    out["SPY_close"] = spy_close.reindex(trading_days)

    # Patch the last day with intraday close if daily bar hasn't arrived yet.
    last_day = trading_days.max().date()
    last_idx = pd.Timestamp(last_day)
    if pd.isna(out.loc[last_idx, "SPY_close"]):
        patched = _get_intraday_close_for(last_day)
        if patched is not None:
            out.loc[last_idx, "SPY_close"] = patched

    out["SPY_prev_close"] = out["SPY_close"].shift(1)
    out["spy_prev_cc_ret"] = out["SPY_close"] / out["SPY_prev_close"] - 1.0

    return out.reset_index()


def main():
    args = parse_args()
    end_str = args.end or today_ny_yyyy_mm_dd()
    trading_days = get_trading_days(args.start, end_str)
    out = build_spy_prev_close(trading_days)
    out.to_csv(args.out, index=False)
    print(f"[DONE] Wrote {len(out):,} rows → {args.out}")
    print(out.tail(3))


if __name__ == "__main__":
    main()
