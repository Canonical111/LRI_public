#!/usr/bin/env python3
"""Figure fig_d1_cutoff.pdf: Delta_eps(N) at strong coupling and the local exponent omega_eff(N) (d = 1, dens_v1).
Input: data/dens_v1_series.json. Requires matplotlib."""
import json, math
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
H = Path(__file__).resolve().parents[1]
S = {s['delta']: s for s in json.loads((H / 'data/dens_v1_series.json').read_text())['series']}
fig, ax = plt.subplots(1, 3, figsize=(11, 3.4))
cols = {0.125: 'C0', 0.1: 'C1', 0.075: 'C2', 0.05: 'C3', 0.025: 'C4', 0.01: 'C5'}
for d, c in cols.items():
    s = S[d]; N = s['cuts']; y = s['values']
    if d >= 0.05:
        ax[0].plot(N, y, 'o-', ms=3, color=c, label=r'$\Delta_\sigma=%g$' % d)
        if s['stable']: ax[0].axhline(s['D_inf'], color=c, ls=':', lw=1)
    else:  # no limit: change from N = 12, so that the maximum at 0.025 and the steady fall at 0.01 are visible
        ax[1].plot(N, [1e3 * (v - y[0]) for v in y], 'o-', ms=3, color=c, label=r'$\Delta_\sigma=%g$' % d)
    sl = [(math.sqrt(N[i] * N[i + 1]), (y[i + 1] - y[i]) / math.log(N[i + 1] / N[i])) for i in range(len(N) - 1)]
    om = [(sl[i + 1][0], -math.log(sl[i + 2][1] / sl[i][1]) / math.log(sl[i + 2][0] / sl[i][0])) for i in range(0, len(sl) - 2, 2) if sl[i][1] * sl[i + 2][1] > 0]
    if d >= 0.05: ax[2].plot(*zip(*om), 'o-', ms=3, color=c, label=r'$\Delta_\sigma=%g$' % d)
for a in ax[:2]: a.set_xlabel('$N$'); a.legend(fontsize=7)
ax[0].set_ylabel(r'$\Delta_\varepsilon(N)$'); ax[1].set_ylabel(r'$10^3\,[\Delta_\varepsilon(N)-\Delta_\varepsilon(12)]$')
ax[0].set_title('rising; dotted: extrapolation', fontsize=9); ax[1].set_title('no limit', fontsize=9)
ax[2].set_xlabel('$N$'); ax[2].set_ylabel(r'$\omega_{\rm eff}(N)$'); ax[2].legend(fontsize=7); ax[2].set_title('local exponent', fontsize=9)
fig.tight_layout(); fig.savefig(H / 'figures/fig_d1_cutoff.pdf'); print('wrote figures/fig_d1_cutoff.pdf')
