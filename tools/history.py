"""One-off: download 1-minute OHLCV history for backtests (not used by the EA).
Env: DATASET, SYMBOL (continuous, e.g. NKD.v.0), START (YYYY-MM-DD), END (optional),
MAXCOST (USD, abort above it), DRY=1 to print cost/availability only."""
import os, sys, pandas as pd, databento as db
c = db.Historical(os.environ["DATABENTO_API_KEY"])
ds, sym = os.environ["DATASET"], os.environ["SYMBOL"]
rng = c.metadata.get_dataset_range(dataset=ds)
print("dataset range", rng["start"], "->", rng["end"])
start = max(pd.Timestamp(os.environ["START"], tz="UTC"), pd.Timestamp(rng["start"]))
end = pd.Timestamp(os.environ.get("END") or rng["end"])
if end.tzinfo is None: end = end.tz_localize("UTC")
kw = dict(dataset=ds, symbols=[sym], stype_in="continuous", schema="ohlcv-1m", start=start.isoformat(), end=end.isoformat())
cost = c.metadata.get_cost(**kw)
print(f"{sym} {start.date()} -> {end.date()} cost ${cost:.2f}")
if os.environ.get("DRY") == "1": sys.exit(0)
if cost > float(os.environ.get("MAXCOST", "10")): sys.exit(f"cost ${cost:.2f} above MAXCOST, stopping")
df = c.timeseries.get_range(**kw).to_df()
out = f"hist_{sym.replace('.', '_')}.csv.gz"
df[["open", "high", "low", "close", "volume"]].to_csv(out)
print("rows", len(df), "first", df.index[0], "last", df.index[-1], "->", out)
