"""Value-area levels exactly as the backtest engine builds them.
Input: 1-minute bars of ONE CME session (columns h, l, c, v; index = bar start, America/New_York)."""
import numpy as np

SPEC = {  # tick size, profile row size, rows added per expansion step
    "ES": dict(T=0.25, vb=0.5, rows=2),   # MotiveWave-style 0.5-pt rows (matched Charlie's charts)
    "NQ": dict(T=0.25, vb=None, rows=2),
}

def profile(l, h, v, T):
    lo = np.round(l / T).astype(int); hi = np.round(h / T).astype(int)
    base = lo.min(); prof = np.zeros(hi.max() - base + 1)
    for a, b, x in zip(lo - base, hi - base, v):
        prof[a:b + 1] += x / (b - a + 1)
    return base, prof

def value_area(base, prof, T, vb, rows, pct=0.70):
    if vb:
        k = int(round(vb / T)); off = base % k
        pr = np.concatenate([np.zeros(off), prof]); pr = np.concatenate([pr, np.zeros((-len(pr)) % k)])
        b = pr.reshape(-1, k).sum(1); b0 = base - off
    else:
        k = 1; b = prof; b0 = base
    p = int(np.argmax(b)); lo = hi = p; acc = b[p]; tot = b.sum(); n = len(b)
    while acc < pct * tot and (lo > 0 or hi < n - 1):
        up = b[hi + 1:hi + 1 + rows].sum() if hi < n - 1 else -1
        dn = b[max(lo - rows, 0):lo].sum() if lo > 0 else -1
        if up >= dn: s = min(rows, n - 1 - hi); acc += b[hi + 1:hi + 1 + s].sum(); hi += s
        else:        s = min(rows, lo);         acc += b[lo - s:lo].sum();         lo -= s
    if vb:
        return (b0 + hi * k) * T + vb, (b0 + p * k) * T + vb / 2, (b0 + lo * k) * T
    return (b0 + hi) * T, (b0 + p) * T, (b0 + lo) * T

def session_levels(bars, sym):
    """bars: DataFrame of one session (NY-time index). Returns (vah, val, poc, close_1559) or None."""
    if len(bars) < 1300: return None          # holiday short session -> no levels (EA skips it too)
    last = bars.index.max()
    if last.hour < 16 or (last.hour == 16 and last.minute < 45): return None   # session not finished yet
    s = SPEC[sym]
    base, prof = profile(bars.l.values, bars.h.values, bars.v.values.astype(float), s["T"])
    vah, poc, val = value_area(base, prof, s["T"], s["vb"], s["rows"])
    upto = bars[bars.index.strftime("%H:%M") <= "15:59"]
    upto = upto[upto.index.hour >= 9]          # same calendar day's RTH part
    if not len(upto): return None
    return vah, val, poc, float(upto.c.iloc[-1])
