import sys, json, numpy as np
sys.path.insert(0, '.')
from indep_ht3d import Model
from indep_spin import SpinModel
ext = json.load(open('indep_extract.json'))
L = int(sys.argv[1]); xs = [float(v) for v in sys.argv[2].split(',')]
for x in xs:
    e = next(e for e in ext if e['camp'] in ('grid18','grid18sri') and abs(e['delta']-x) < 1e-9 and e['bath_cut'] == L and e['window'] == 'vacuum' and e['angular_spectra'])
    m0 = Model(L, x); s0 = m0.solve(e['r'], e['g'], K=16, window=True, nroots=2)
    D = np.zeros(L + 1)
    for N in range(1, L + 1): D[N] = s0['Ev'][L] - s0['Ev'][2 * ((L - N) // 2)]
    E0 = s0['E0']
    for J, inv in ((1, 1), (2, 0)):
        sm = SpinModel(L, x, J, inv)
        for f in (0, 1):
            ev = sm.spectrum(e['r'], e['g'], 16, D, f, 6) - E0
            pk = e['angular_spectra'][str(J)][str(f)]
            print(f'x={x} L={L} J={J} field={f} states={sm.checks["states"]} imag={sm.checks["imag_max"]:.1e} | indep {np.round(ev,9)} | pkg {np.round(pk,9)} | maxdiff {np.max(np.abs(ev-np.array(pk))):.1e}', flush=True)
