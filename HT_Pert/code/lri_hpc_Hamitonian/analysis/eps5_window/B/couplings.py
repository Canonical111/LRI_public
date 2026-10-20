"""Raw couplings r_k, g_k (k<=3 exact from the capped space P<=7,Q<=4: E^(3) needs only distance-1 states).
raw_couplings(L, cut4=None) -> (r[0..5], g[0..5]) with r4,g4,r5,g5 = NaN (not computable in the capped space)."""
import numpy as np, json, os
from htb5 import Space, St, run_orders
K = 5
_cache = {}
def raw_couplings(L, cut4=None):
    cut4 = 4 * L if cut4 is None else cut4
    if cut4 in _cache: return _cache[cut4]
    sp = Space(cut4, 7, 4, K, keep_modes=False)
    refs = {p: St(sp, sp.index([0] * p), K) for p in (0, 1, 3)}
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    r, g = run_orders(refs, r, g, None, 1, K, tune=(0, 1, 3), n_to=3)
    r[4:] = np.nan; g[4:] = np.nan
    _cache[cut4] = (r, g)
    return r, g
