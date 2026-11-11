"""Compare levels built from Yahoo 1-minute bars with levels.csv (Databento) for recent sessions."""
import pandas as pd, numpy as np, yfinance as yf
import sys; sys.path.insert(0, ".")
from levels_lib import SPEC, profile, value_area
NY = "America/New_York"
ref = {}
for line in open("levels.csv"):
    f = line.strip().split(",")
    if len(f) >= 6: ref[(f[0], f[1])] = [float(x) for x in f[2:6]]
for sym, tk in [("ES", "ES=F"), ("NQ", "NQ=F")]:
    df = yf.download(tk, period="8d", interval="1m", progress=False, auto_adjust=False, prepost=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower).rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
    print(sym, "bars", len(df), "from", df.index[0], "to", df.index[-1], "now", pd.Timestamp.now(tz=NY))
    sess = (df.index + pd.Timedelta(hours=6)).date
    for d, b in df.groupby(sess):
        if pd.Timestamp(d).weekday() >= 5: continue
        s = SPEC[sym]
        base, prof = profile(b.l.values, b.h.values, b.v.values.astype(float), s["T"])
        vah, poc, val = value_area(base, prof, s["T"], s["vb"], s["rows"])
        u = b[(b.index.strftime("%H:%M") <= "15:59") & (b.index.hour >= 9)]
        cl = float(u.c.iloc[-1]) if len(u) else float("nan")
        r = ref.get((pd.Timestamp(d).strftime("%Y.%m.%d"), sym))
        print(f"  {d} bars {len(b):4d} last {b.index.max().strftime('%H:%M')} vol {int(b.v.sum()):>8d} | yahoo {vah:.2f}/{val:.2f}/{poc:.2f}/{cl:.2f} | databento {r}")
print("--- detail")
df = yf.download("NQ=F", period="8d", interval="1m", progress=False, auto_adjust=False, prepost=True)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
b = df[(df.index + pd.Timedelta(hours=6)).date == pd.Timestamp("2026-11-09").date()]
print(b.head(12)[["Open","High","Low","Close","Volume"]].to_string())
print(b[b.Low < 27200][["Open","High","Low","Close","Volume"]].head(15).to_string(), len(b[b.Low<27200]))
