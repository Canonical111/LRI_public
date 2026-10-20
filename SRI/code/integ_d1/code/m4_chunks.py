"""Task files for the n = 4 runs: the mirror-reduced sectors (n4.mirror.json weight > 0) split into contiguous runs and
balanced over NCHUNKS node jobs with the node-count cost model
  ser (conjugate symmetry halves the outermost circle): nterm * ((nseg + m)^k + nseg^k) / 2 * nplain^(6 - k)
  cx:                                                    nterm * (nseg + m)^k * nplain^(6 - k)
where k counts the variables the engine splits under -radii rouche (plain flag and Rouche radius R1 >= plainR, replicated
here from the input; identical to the engine's classification for all 4777 sectors). Pilot: time/model within ~3x.
usage: python m4_chunks.py [--only SECTORS.json] NCHUNKS NAME ENGINE_ARGS...   (e.g. 16 prod/G3 -mode ser -k 1 -nseg 10 -m 14 -nplain 12)
  --only: a JSON list of sector indices (a subset of the mirror-reduced set, e.g. the double-double overrides)
writes NAME_c<i>.tasks (NAME with '/' -> '_') in the current directory; lines 'NAME/c<i>_<s0> -i n4.txt ... -sec s0 s1'"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import provenance as pv

argv = sys.argv[1:]
only = None
if argv and argv[0] == '--only':
    only = set(json.load(open(argv[1]))); argv = argv[2:]
nch, name, eargs = int(argv[0]), argv[1], argv[2:]
def arg(flag, default):
    return float(eargs[eargs.index(flag) + 1]) if flag in eargs else default
nseg, m, npl, plainR = arg('-nseg', 24), arg('-m', 32), arg('-nplain', 30), arg('-plainR', 0.3)
kmax = int(arg('-k', 1))
inp = os.path.join(pv.RES, 'm4_inputs', 'n4.txt')
w = json.load(open(os.path.join(pv.RES, 'm4_inputs', 'n4.mirror.json')))['weights']
# parse the engine input: per sector plain flags, interval regular parts and s
secs = []
with open(inp) as f:
    head = f.readline().split(); n = int(head[1]); nint = int(head[3]); D = 2 * n - 2
    for line in f:
        p = line.split()
        if not p: continue
        if p[0] == 'sector':
            i0 = p.index('plain0'); i1 = p.index('plain1'); ir = p.index('R')
            secs.append(dict(plain0=list(map(int, p[i0 + 1:i1])), plain1=list(map(int, p[i1 + 1:ir])), polys=[], nterm=0))
        elif p[0] == 'int':
            nr = int(p[1 + D]); rows = [tuple(map(int, p[2 + D + r * D:2 + D + (r + 1) * D])) for r in range(nr)]
            secs[-1]['polys'].append([(r, 1.0) for r in rows])
        elif p[0] == 's':
            nr = int(p[1 + D]); rows = []
            for r in range(nr):
                q = p[2 + D + r * (D + 1):2 + D + (r + 1) * (D + 1)]
                rows.append((tuple(map(int, q[:D])), float(q[D])))
            secs[-1]['polys'].append(rows)
        elif p[0] == 'nterm':
            secs[-1]['nterm'] = int(p[1])
def r1(polys, k):
    best = 1e9
    for P in polys:
        c0 = sum(c for e, c in P if not any(e)); ad = {}
        for e, c in P:
            if any(e) and e[k] > 0: ad[e[k]] = ad.get(e[k], 0) + c
        if not ad: continue
        lo, hi = 0.0, 1e9
        for _ in range(200):
            r = 0.5 * (lo + hi)
            if sum(c * r ** d for d, c in ad.items()) < c0: lo = r
            else: hi = r
        best = min(best, lo)
    return best
cost = []
for s in secs:
    flags = s['plain0'] if kmax == 0 else s['plain1']
    ns = sum(1 for k in range(D) if not (flags[k] and r1(s['polys'], k) >= plainR))
    cx = '-mode' in eargs and eargs[eargs.index('-mode') + 1] == 'cx'
    circ = (nseg + m) ** ns if cx else ((nseg + m) ** ns + nseg ** ns) / 2
    cost.append(s['nterm'] * circ * npl ** (D - ns))
todo = [i for i in range(len(secs)) if w[i] > 0 and (only is None or i in only)]
if only is not None and len(todo) != len(only):
    sys.exit('--only lists sectors outside the mirror-reduced set')
tot = sum(cost[i] for i in todo); target = tot / nch
chunks, cur, acc = [], [], 0.0
for i in todo:
    cur.append(i); acc += cost[i]
    if acc >= target * (len(chunks) + 1) and len(chunks) < nch - 1:
        chunks.append(cur); cur = []
chunks.append(cur)
base = ' '.join(eargs)
for ci, ch in enumerate(chunks):
    runs, a = [], None
    for i in ch:
        if a is None: a = b = i
        elif i == b + 1: b = i
        else: runs.append((a, b + 1)); a = b = i
    runs.append((a, b + 1))
    fn = f'{name.replace("/", "_")}_c{ci}.tasks'
    with open(fn, 'w') as f:
        for a, b in runs:
            f.write(f'{name}/c{ci}_{a} -i n4.txt {base} -sec {a} {b}\n')
    print(fn, len(ch), 'sectors', len(runs), 'runs', f'model cost share {sum(cost[i] for i in ch) / tot:.3f}')
