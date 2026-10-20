import sys, json, time; sys.dont_write_bytecode=True
from ht5 import Engine
out = {}
for L in [int(a) for a in sys.argv[1:]]:
    t0 = time.time()
    e = Engine(L, 10, 11)
    R = {v: e.run(v) for v in ('raw', 'g2D3W', 'Dconn', 'Dfull')}
    out[L] = dict(dims=(e.Se.dim, e.So.dim, e.Sv.dim), sec=time.time() - t0, **R)
    print(L, out[L]['dims'], '%.1fs' % out[L]['sec'], 'rawC4 %.13f rawC5 %.13f dC4 %.13f dC5 %.13f g2D3W dC5 %.13f Dfull dC5 %.13f' % (
        R['raw']['C'][4], R['raw']['C'][5], R['Dconn']['C'][4] - R['raw']['C'][4], R['Dconn']['C'][5] - R['raw']['C'][5],
        R['g2D3W']['C'][5] - R['raw']['C'][5], R['Dfull']['C'][5] - R['raw']['C'][5]), flush=True)
    json.dump({str(k): v for k, v in out.items()}, open('big_%s.json' % '_'.join(sys.argv[1:]), 'w'), default=float, indent=1)
