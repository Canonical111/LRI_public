import mpmath as mp, json, time
import gen3 as G
mp.mp.dps = 170
d = G.D3(mp.mpf(3) / 4, 280, 116)
out = {}
t = time.time()
for u in ['0', '1/16', '3/16', '3/8', '1/2', '5/8', '3/4', '7/8']:
    out['Tp(%s)' % u] = d.Tp(mp.mpf(mp.fraction(*map(int, u.split('/'))) if '/' in u else 0))
for m in (0, 1):
    for v in ['1/8', '3/8', '5/8', '7/8']:
        out['U%d(%s)' % (m, v)] = d.U(m, mp.fraction(*map(int, v.split('/'))))
out['Tp(1/8)'] = d.Tp(mp.mpf(1) / 8); out['Tp(1/4)'] = d.Tp(mp.mpf(1) / 4)
print('seconds', time.time() - t)
json.dump({k: mp.nstr(mp.re(x), 165) for k, x in out.items()}, open('extra_nodes_dps170.json', 'w'), indent=1)
