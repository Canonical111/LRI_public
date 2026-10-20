"""M4 part B cost pilot: per-sector contributions to f_3_0_1 (four bubbles, delta^1) on a sample of sectors.
f_3_0_1 = F3[d^1 w^0] = base + sum_e R_e c4(1, e) (m4_step0 map) is linear in the sector values, so every sector has a
contribution f_s = R . (weight_s * Gamma-convolved A_s^(1)). Differences of f_s between grids (and between the double
and double-double builds) estimate the quadrature (and roundoff) error of f_3_0_1; the sample is a stride-STRIDE subset
of all sectors, so sums are scaled by STRIDE. Production computes only sectors of nonzero mirror weight.
usage: python m4_pilot_analyze.py PILOT_DIR STRIDE   (PILOT_DIR/<grid>/s<sector>.out, timing from the 'time' field)"""
import sys, os, glob, json, re
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cluster_assemble import read_out, laurent_gamma_derivs, pattern_factors
import provenance as pv
mp.mp.dps = 30
pdir, stride = sys.argv[1], int(sys.argv[2])
resp_raw, _ = pv.load_step0('m4_step0_response.json')
R = {int(k.split(',')[1]): mp.mpf(d['1,0']) for k, d in resp_raw.items() if '1,0' in d}
mirror = json.load(open(os.path.join(pv.RES, 'm4_inputs', 'n4.mirror.json')))['weights']
fac = pattern_factors(4)
Lg = laurent_gamma_derivs(4, 2, -4, 8)
need_top = max(R)                      # highest J4^(1) exponent that enters f_3_0_1


def contrib(sec):
    """returns (f_s without the mirror weight, top resolved J exponent, J4^(0) and J4^(1) Laurent pieces)"""
    A = sec['S']; wt = fac[sec['pat']]
    tops = {}
    for (k, j, e) in A: tops[(k, j)] = max(tops.get((k, j), -99), e)
    jtop = min(tops[(1, j)] + min(Lg[j]) for j in range(3))
    f = mp.mpf(0)
    for e, r in R.items():
        c = mp.mpf(0)
        for (k, j, ea), v in A.items():
            if k == 1 and (e - ea) in Lg[j]: c += Lg[j][e - ea] * mp.re(v)
        f += r * wt * c
    return f, jtop


grids = sorted(d for d in os.listdir(pdir) if os.path.isdir(os.path.join(pdir, d)))
data = {}
for g in grids:
    for fn in glob.glob(os.path.join(pdir, g, 's*.out')):
        try:
            h, secs = read_out(fn)
        except Exception as ex:
            print('skip', fn, ex); continue
        for s, sec in secs.items():
            if h['mode'] == 'ser':
                f, jtop = contrib(sec)
                data.setdefault(g, {})[s] = dict(f=f, jtop=jtop, t=sec['time'], nterm=sec['nterm'])
            else:
                v = sec['A'][(0, 0)]
                data.setdefault(g, {})[s] = dict(v=v * fac[sec['pat']], t=sec['time'], nterm=sec['nterm'])
print('grids:', {g: len(v) for g, v in data.items()})
for g in grids:
    if g not in data: continue
    d = data[g]
    tall = sum(x['t'] for x in d.values()); tred = sum(x['t'] * (1 if mirror[s] > 0 else 0) for s, x in d.items())
    print(f'{g:6s}: {len(d)} sectors, node-s {tall:9.1f}; projected full set {tall * stride / 3600 * 40:9.0f} core-h, '
          f'mirror-reduced {tred * stride / 3600 * 40:9.0f} core-h' + (f'; min top exponent {min(x["jtop"] for x in d.values())} (need {need_top})' if 'jtop' in next(iter(d.values())) else ''))
ser = [g for g in grids if g in data and 'f' in next(iter(data[g].values()))]
print('\nper-sector f_3_0_1 contributions (mirror weight applied), sums scaled by stride:')
for a, b in [(x, y) for i, x in enumerate(ser) for y in ser[i + 1:]]:
    com = [s for s in data[a] if s in data[b] and mirror[s] > 0]
    if not com: continue
    diff = [mirror[s] * (data[a][s]['f'] - data[b][s]['f']) for s in com]
    mag = [mirror[s] * abs(data[b][s]['f']) for s in com]
    print(f'  {a} - {b}: {len(com)} sectors; signed sum x stride {mp.nstr(stride * sum(diff), 3)}; '
          f'abs sum x stride {mp.nstr(stride * sum(abs(x) for x in diff), 3)}; max |diff| {mp.nstr(max(abs(x) for x in diff), 3)} '
          f'(sector {com[max(range(len(diff)), key=lambda i: abs(diff[i]))]}); sum |f_s| x stride {mp.nstr(stride * sum(mag), 3)}')
cxg = [g for g in grids if g in data and 'v' in next(iter(data[g].values()))]
for a, b in [(x, y) for i, x in enumerate(cxg) for y in cxg[i + 1:]]:
    com = [s for s in data[a] if s in data[b]]
    rel = [abs(data[a][s]['v'] - data[b][s]['v']) / abs(data[b][s]['v']) for s in com if data[b][s]['v'] != 0]
    print(f'  cx delta^0 {a} vs {b}: {len(com)} sectors, max rel diff {mp.nstr(max(rel), 3)}, median {mp.nstr(sorted(rel)[len(rel) // 2], 3)}')
