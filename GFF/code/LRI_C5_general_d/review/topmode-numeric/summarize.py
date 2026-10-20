#!/usr/bin/env python3
"""Collect probe_*.json into markdown tables (review key topmode-numeric)."""
import json, glob, os, sys
import mpmath as mp
mp.mp.dps = 60
here = os.path.dirname(os.path.abspath(__file__))
files = sys.argv[1:] or sorted(glob.glob(os.path.join(here, 'results', 'probe_*.json')))
rows = {}
# entries computed before the LGR early-termination fix at d=2.5 (multiplicity Gamma ratio with a=1/2, b=1);
# they are superseded by probe_mainD2fix.json and listed separately in the report
SUPERSEDED = {('probe_mainG1.json', 'D2r3'), ('probe_mainG2.json', 'D2r4'),
              ('probe_extra1.json', 'A4r3'), ('probe_extra1.json', 'A1r2')}   # h=1/16 runs limited by complex-exponent quadrature
for f in files:
    d = json.load(open(f))
    st = d['settings']
    for k, v in d['configs'].items():
        if (os.path.basename(f), k) in SUPERSEDED:
            continue
        v['_settings'] = st
        v['_file'] = os.path.basename(f)
        rows[k] = v


def e(x):
    return '%.1e' % float(mp.mpf(x))


def bstr(b):
    re_, im_ = b
    return re_ if mp.mpf(im_) == 0 else '%s%s%si' % (re_, '+' if mp.mpf(im_) > 0 else '', im_)


order = sorted(rows, key=lambda k: (k[0] != 'A', k[0] != 'D', k))
print('### Mode magnitudes |gamma_m| / max_m |gamma_m|\n')
print('| key | d | b | r | kernel | dps,K,P,h,M | ' + ' | '.join('m=%d' % m for m in range(0, 7)) + ' | top (m=+-(r-1)) | boundary (m=+-r) |')
print('|' + '---|' * 15)
for k in order:
    v = rows[k]
    r = v['r']
    st = v['_settings']
    kern = 'balanced' if v['g'] is None and v['mult'] == 'so' else (
        'g=%s' % bstr(v['g']) if v['g'] is not None else 'mult (1-z)^{1-d}')
    cells = []
    for m in range(0, 7):
        if m <= r:
            a = float(mp.mpf(v['rel'][str(m)]))
            b = float(mp.mpf(v['rel'][str(-m)]))
            cells.append('%.2g / %.2g' % (a, b) if m else '%.2g' % a)
        else:
            cells.append('')
    print('| %s | %s | %s | %d | %s | %d,%d,%d,%s,%d | %s | %s | %s |' % (
        k, v['d'], bstr(v['b']), r, kern, st['dps'], st['K'], st['P'], st['h'], st['M'], ' | '.join(cells),
        e(v['top_rel']), e(v['boundary_rel'])))

print('\n### Symmetry checks (relative deviations)\n')
print('| key | gamma_m vs gamma_{-m} e^{2 pi i m sigma} | off-grid Xi(t*) vs modes | S(t*+1) vs S(t*) | S(-sigma-t*) vs S(t*) | S(-sigma-t*) vs S(t*+1) |')
print('|---|---|---|---|---|---|')
for k in order:
    v = rows[k]
    print('| %s | %s | %s | %s | %s | %s |' % (k, e(v['refl_modes']), e(v['offgrid']), e(v['periodicity']),
                                              e(v['reflection']), e(v['refl_vs_per'])))

print('\n### Residue functional\n')
print('| key | d | b | r | W_r (own residue series, all modes |m|<=r) | Bell weights vs series | explicit (eq. explicit) vs series | modes |m|<=r-2 only vs all | reference | rel. dev (series) | rel. dev (explicit) |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for k in order:
    v = rows[k]
    if 'W_residue' not in v:
        continue
    W = mp.mpc(*v['W_residue'])
    ex = ''
    if 'W_explicit' in v:
        ex = e(abs(mp.mpc(*v['W_explicit']) - W) / abs(W))
    ref = v.get('ref', '')
    print('| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
        k, v['d'], bstr(v['b']), v['r'], mp.nstr(W.real, 30) + ('' if abs(W.imag) < 1e-30 * abs(W) else ' %+.3gi' % float(W.imag)),
        e(v['bell_vs_residue']), ex, e(v['W_trunc_vs_full']), (ref[:32] + '...') if ref else '-',
        e(v['dev_residue']) if 'dev_residue' in v else '-', e(v['dev_explicit']) if 'dev_explicit' in v else '-'))

print('\n### Coefficients c_{r,k} = 2 gamma_k e^{-i pi k sigma} (c_0 = gamma_0), 12 digits\n')
print('| key | ' + ' | '.join('c_%d' % kk for kk in range(0, 7)) + ' |')
print('|' + '---|' * 8)
for k in order:
    v = rows[k]
    r = v['r']
    cells = []
    for kk in range(0, 7):
        if kk <= r:
            c = mp.mpc(*v['c'][str(kk)])
            cells.append(mp.nstr(c.real, 12) + ('' if abs(c.imag) <= 1e-35 * max(1, abs(c)) else ' %+.6gi' % float(c.imag)))
        else:
            cells.append('')
    print('| %s | %s |' % (k, ' | '.join(cells)))

# comparison with the foundation's stored coefficients (results/val50.json, 'fixed' nodes, 65 digits)
VAL = '<PROJECT>/LRI_C5_general_d/foundation/results/val50.json'
if os.path.exists(VAL):
    val = json.load(open(VAL))
    found = {}
    for p in val['points']:
        pl = p['payload']
        if pl[3] == 'fixed' and 'c' in p['out']:
            # parse "(a + bj)" robustly
            cs = []
            for x in p['out']['c']:
                s = x.strip().strip('()')
                if 'j' in s:
                    s = s.replace('j', '')
                    # split at the sign of the imaginary part (last + or - not following 'e')
                    i = max(j for j in range(1, len(s)) if s[j] in '+-' and s[j - 1] not in 'eE')
                    cs.append(mp.mpc(mp.mpf(s[:i].strip()), mp.mpf(s[i:].replace(' ', ''))))
                else:
                    cs.append(mp.mpc(mp.mpf(s), 0))
            found[(pl[0], pl[1], pl[2])] = cs
    print('\n### Coefficients vs the foundation (val50.json, fixed nodes)\n')
    print('| key | k | c_k (this probe) | max_k rel. dev. vs foundation, k<=r-2 | top c_{r,r-1}: probe / foundation |')
    print('|---|---|---|---|---|')
    for k in order:
        v = rows[k]
        if v['g'] is not None or v['mult'] != 'so' or mp.mpf(v['b'][1]) != 0:
            continue
        key = (v['r'], v['d'], v['b'][0])
        if key not in found:
            continue
        fc = found[key]
        mine = [mp.mpc(*v['c'][str(kk)]) for kk in range(v['r'])]
        scale = max(abs(x) for x in mine)
        dev = max(abs(mine[kk] - fc[kk]) for kk in range(v['r'] - 1)) / scale
        print('| %s | 0..%d | %s | %s | %.1e / %.1e |' % (k, v['r'] - 2, ', '.join(mp.nstr(mine[kk].real, 15) for kk in range(v['r'] - 1)),
                                                        e(dev), float(abs(mine[v['r'] - 1]) / scale), float(abs(fc[v['r'] - 1]) / scale)))

# imbalance scan: top mode versus delta = g - (d/2 - b/2)
scan = [k for k in order if rows[k]['g'] is not None]
if scan:
    print('\n### Unbalanced kernels: top mode versus imbalance delta = g - (d - b)/2\n')
    print('| key | d | b | r | g | delta | top |gamma_{r-1}|/max (both signs) | top/|delta| | boundary |')
    print('|---|---|---|---|---|---|---|---|---|')
    for k in scan:
        v = rows[k]
        d_ = mp.mpf(v['d'])
        b_ = mp.mpc(*v['b'])
        g_ = mp.mpc(*v['g'])
        delta = g_ - (d_ - b_) / 2
        r = v['r']
        top = max(mp.mpf(v['rel'][str(r - 1)]), mp.mpf(v['rel'][str(1 - r)]))
        print('| %s | %s | %s | %d | %s | %s | %s / %s | %.3g | %s |' % (
            k, v['d'], bstr(v['b']), r, bstr(v['g']), (mp.nstr(delta.real, 3) if delta.imag == 0 else mp.nstr(delta, 3)), v['rel'][str(r - 1)], v['rel'][str(1 - r)],
            float(top / abs(delta)), e(v['boundary_rel'])))
