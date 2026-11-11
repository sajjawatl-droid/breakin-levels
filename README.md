# Daily ES/NQ levels for BreakIn_EA

Every weekday after the CME session ends (17:00 New York), GitHub Actions runs `levels_feed.py`:
it downloads the session's ES and NQ 1-minute bars from Databento (CME Globex), builds the 70% value
area the same way the backtest does, and appends one line per market to `levels.csv`:

    yyyy.mm.dd,SYM,VAH,VAL,POC,close_at_15:59_NY

The EA reads the file from
`https://raw.githubusercontent.com/<user>/<repo>/main/levels.csv` (set as its LevelsURL input).

Setup: add the Databento API key as the repository secret `DATABENTO_API_KEY`, then run the
workflow once by hand from the Actions tab (it backfills the last 7 days).
