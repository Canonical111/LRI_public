"""RR-001 propagation: R6 (C6_lower) from the saved degree-28 lower amplitudes, from the long-double rerun and from
the float64 rerun, with the production five-loop inputs (L5 long double, M = 40) held fixed."""
import sys, json, copy
from pathlib import Path
ref = Path(sys.argv[1]); rr = Path(sys.argv[2]); levels = Path(sys.argv[3])
sys.path.insert(0, str(ref)); sys.path.insert(0, str(ref / 'lri_numerical_resolution/verification'))
import assemble6 as A6
import mpmath as mp
mp.mp.dps = 70
H5 = json.loads((levels / 'L5_H_all_N40.ld.json').read_text())['totals']; J5 = json.loads((levels / 'L5_J_all_N40.ld.json').read_text())['totals']
runs = {m: json.loads((rr / f'lower28_{m}.json').read_text())['result'] for m in ('ld', 'f64')}
out = {}
for i, cut in enumerate(('maxgap', 'span')):
    base = A6.inputs(cut, 28)  # saved lower6_{cut}_28.json + retained five-loop poles
    for k in range(5):
        H = mp.mpf(H5[5 * i + k]); J = mp.mpf(J5[6 * i + k]); p = str(k - 5)
        base['5'][0][p] = mp.nstr(8 * H - 3 * J, 60); base['5'][1][p] = mp.nstr(3 * H - J, 60)
    R = {'saved': A6.assemble(base)['C'][-1]}
    maxrel = {}
    for m, res in runs.items():
        d = copy.deepcopy(base)
        for L in ('2', '3', '4'):
            d[L] = res[cut][L]
            for ab in (0, 1):
                for kk, v in res[cut][L][ab].items():
                    s = mp.mpf(base[L][ab][kk]); x = mp.mpf(v)
                    maxrel[m] = max(maxrel.get(m, 0), float(abs(x - s) / abs(s)) if s != 0 else float(abs(x)))
        R[m] = A6.assemble(d)['C'][-1]
    out[cut] = {'R6_saved': mp.nstr(R['saved'], 25), 'R6_ld_minus_saved': mp.nstr(R['ld'] - R['saved'], 6),
                'R6_f64_minus_ld': mp.nstr(R['f64'] - R['ld'], 6), 'max_rel_amplitude_diff': maxrel}
print(json.dumps(out, indent=1))
