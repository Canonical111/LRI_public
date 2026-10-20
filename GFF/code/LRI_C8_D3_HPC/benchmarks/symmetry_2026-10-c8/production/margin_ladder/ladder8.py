"""Fine depth ladder for the levels the L8 margin probe flagged as deficits (probe 571479). For each such level, the
local exponent |S_k| + d ln|f| / d ln t_k over windows [lo+s, hi+s] decades, s = 0, 5, ..., 400 and 480, 640, 800,
the other levels fixed at margin_probe8's scales (two-scale 9/13/11, chain 6/8/4), with the sign of f at both ends.
A dip below the proposal rate that sits between two plateaus and coincides with a sign change of f is a zero of f at
a crossover between two powers of t_k (a small |f|, never a large one); the tail is set by the deepest plateau.
Usage (package root): python3 -B ladder8.py PROBE_DIR OUT.json [workers]"""
import json, math, multiprocessing as mpc, os, re, sys, time
from pathlib import Path
sys.path.insert(0, 'tools')
import margin_probe8 as mp
import members
SHIFTS = list(range(0, 401, 5)) + [480, 560, 640, 800]
SCALES = {'two': (9, 13, 11), 'chain': (6, 8, 4)}
def parse(where):
    m = re.match(r'(two-scale flag|\d+-scale chain) ([0-9a-fx< ]+), level (\d+) = ', where)
    cls = 'two' if m.group(1) == 'two-scale flag' else 'chain'
    return cls, tuple(int(h, 16) for h in m.group(2).split(' < ')), int(m.group(3)) - 1
_F = {}
def work(t):
    key, path, sha, cls, sets, k = t
    if key not in _F:
        data = Path(path).read_bytes()
        assert mp.hashlib.sha256(data).hexdigest() == sha
        g = mp.Graph(data, key.split(':')[0], path)
        _F.clear(); _F[key] = mp.Forest(g, 3, 60)
    F = _F[key]; prep = F.prepare(sets); lo, hi, fix = SCALES[cls]
    rows = []
    for s in SHIFTS:
        a = [fix] * len(sets); a[k] = lo + s
        f1, s1, b1 = F.lnf(prep, a); a[k] = hi + s
        f2, s2, b2 = F.lnf(prep, a)
        e = None if f1 is None or f2 is None else prep.size[k] + (f2 - f1) / (-(hi - lo) * mp.LN10)
        rows.append(dict(shift=s, exponent=e, sign_lo=s1, sign_hi=s2, bits=min(b1, b2)))
    return dict(key=key, cls=cls, sets=[f'{S:#06x}' for S in sets], level=k + 1, ladder=rows)
def main():
    pdir, out = Path(sys.argv[1]), Path(sys.argv[2]); W = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
    keys = []
    for f in sorted(pdir.glob('*_L*_G*.json')):
        d = json.loads(f.read_text())
        if d['verdict']['status'] != 'deficit':
            continue
        for cls in ('two', 'chain'):
            for w in d['c_multi_scale'][cls]['worst']:
                if w['margin_a'] < -0.02:
                    keys.append((d, cls) + parse(w['where'])[1:])
    todo = []
    inputs = members.inputs_dir(None)
    gl = sorted({(d['graph']['sector'], int(d['graph']['L']), int(d['graph']['id'])) for d, *_ in keys})
    with members.extracted(gl, inputs, base=Path(os.environ['C8_SCRATCH']) if os.environ.get('C8_SCRATCH') else None) as root:
        for d, cls, sets, k in keys:
            s, L, g = d['graph']['sector'], int(d['graph']['L']), int(d['graph']['id'])
            p = root / s / f'L{L}' / f'G{g}.txt'
            todo.append((f'{s}:{L}:{g}', str(p), mp.sha256_file(p), cls, sets, k))
        t0 = time.time()
        with mpc.Pool(W) as pool:
            res = pool.map(work, todo, chunksize=1)
    doc = dict(schema='c8-d3-margin-ladder-1', probe_dir=str(pdir), shifts=SHIFTS, scales=SCALES, seconds=time.time() - t0,
               levels=res)
    assert not out.exists()
    out.write_text(json.dumps(doc, indent=1))
    for r in res:
        ex = [x['exponent'] for x in r['ladder']]
        flips = [x['shift'] for x in r['ladder'] if x['sign_lo'] != x['sign_hi']]
        tail = [e for e in ex[-8:] if e is not None]
        print(r['key'], r['cls'], ' < '.join(r['sets']), 'level', r['level'],
              'min %.3f' % min(e for e in ex if e is not None), 'deep', ' '.join('%.3f' % e for e in tail),
              'flips at', flips)
main()
