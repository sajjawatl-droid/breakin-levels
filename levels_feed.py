"""Nightly job: build yesterday's ES/NQ levels from Yahoo 1-minute bars right after the close, then
correct them with Databento (CME Globex) data once it is published (~8h later);
compute the 70% value area of each full CME session and append it to levels.csv.
Line format (read by BreakIn_EA): yyyy.mm.dd,SYM,VAH,VAL,POC,close_at_15:59_NY
The date is the session's end date (the day it closes at 16:00 New York)."""
import os, sys, datetime as dt
import pandas as pd
import databento as db
from levels_lib import session_levels

NY = "America/New_York"
OUT = "levels.csv"
SYMS = {"ES": "ES.v.0", "NQ": "NQ.v.0"}   # front month by volume (handles quarterly rolls)
DAYS_BACK = int(os.environ.get("DAYS_BACK", "7"))

def load(path):
    if not os.path.exists(path): return {}
    rows = {}
    for line in open(path):
        f = line.strip().split(",")
        if len(f) >= 6: rows[(f[0], f[1])] = line.strip()
    return rows

def yahoo(rows):
    """Fast path: Yahoo 1-minute bars (about 10 minutes delayed) so the levels exist before the next
    session opens. Databento (about 8 hours delayed) later overwrites them with exchange data."""
    import yfinance as yf
    added = 0
    for sym, tk in {"ES": "ES=F", "NQ": "NQ=F"}.items():
        try:
            df = yf.download(tk, period="5d", interval="1m", progress=False, auto_adjust=False, prepost=True)
        except Exception as e:
            print("yahoo", sym, "failed:", e); continue
        if df is None or df.empty: print("yahoo", sym, "no data"); continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "c", "Volume": "v"})
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
        sess = (df.index + pd.Timedelta(hours=6)).date
        for d, bars in df.groupby(sess):
            if pd.Timestamp(d).weekday() >= 5: continue
            key = (pd.Timestamp(d).strftime("%Y.%m.%d"), sym)
            if key in rows: continue
            med = bars.v[bars.v > 0].median()
            bars = bars[bars.v <= 50 * med]          # Yahoo sometimes dumps the day's volume into one bar
            lv = session_levels(bars, sym)
            if lv is None: continue
            rows[key] = f"{key[0]},{sym},{lv[0]:.2f},{lv[1]:.2f},{lv[2]:.2f},{lv[3]:.2f}"
            print("yahoo added", rows[key]); added += 1
    return added

def main():
    rows0 = load(OUT)
    n = yahoo(rows0) if os.environ.get("YAHOO", "1") == "1" else 0
    if n:
        with open(OUT, "w") as fh:
            for k in sorted(rows0): fh.write(rows0[k] + "\n")
    client = db.Historical(os.environ["DATABENTO_API_KEY"])
    rows = load(OUT)
    now_ny = pd.Timestamp.now(tz=NY)
    start = (now_ny - pd.Timedelta(days=DAYS_BACK)).normalize() - pd.Timedelta(hours=6)  # 18:00 NY the day before
    avail = pd.Timestamp(client.metadata.get_dataset_range(dataset="GLBX.MDP3")["end"])
    end = min(now_ny.tz_convert("UTC"), avail.tz_convert("UTC") if avail.tzinfo else avail.tz_localize("UTC"))
    print("data available until", end.tz_convert(NY))
    added = 0
    for sym, code in SYMS.items():
        data = client.timeseries.get_range(dataset="GLBX.MDP3", symbols=[code], stype_in="continuous",
                                           schema="ohlcv-1m", start=start.tz_convert("UTC").isoformat(),
                                           end=end.isoformat())
        df = data.to_df()
        if df.empty: print(sym, "no data returned"); continue
        df = df.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
        # session date = NY date of the bar shifted forward 6h (18:00 NY belongs to the next day's session)
        sess = (df.index + pd.Timedelta(hours=6)).date
        for d, bars in df.groupby(sess):
            if pd.Timestamp(d).weekday() >= 5: continue
            key = (pd.Timestamp(d).strftime("%Y.%m.%d"), sym)
            lv = session_levels(bars, sym)
            if lv is None: print(sym, d, "skipped (short or incomplete session)"); continue
            new = f"{key[0]},{sym},{lv[0]:.2f},{lv[1]:.2f},{lv[2]:.2f},{lv[3]:.2f}"
            if rows.get(key) == new: continue
            print(("replaced " + rows[key] + " ->" if key in rows else "added"), new); rows[key] = new; added += 1
    with open(OUT, "w") as fh:
        for k in sorted(rows): fh.write(rows[k] + "\n")
    print(f"{added} new lines, {len(rows)} total")

if __name__ == "__main__":
    main()
