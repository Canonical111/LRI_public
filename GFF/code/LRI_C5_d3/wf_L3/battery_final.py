"""Final integer-relation battery (FLINT LLL + Gram-Schmidt bound) on the intrinsic L3 constants. session L3."""
import mpmath as mp, sys, json
from lllrel import relation, tens, LOG
dig = int(sys.argv[1]); fn = sys.argv[2] if len(sys.argv) > 2 else 'L3_final_values.json'
mp.mp.dps = dig + 20
v = {k: mp.mpf(x) for k, x in json.load(open(fn))['values'].items()}
pi = mp.pi; r2 = mp.sqrt(2); l2 = mp.log(2); ls = mp.log(1 + r2); G = mp.catalan
Ups = v['U40_34'] * v['U41_34']
blocks = [('X0', v['X0']), ('Xh', v['Xh']), ('a4b4', v['a4'] * v['b4']), ('Ups', Ups)]
E8 = [('1', 1), ('r2', r2), ('pi', pi), ('pir2', pi * r2), ('l2', l2), ('l2r2', l2 * r2), ('ls', ls), ('lsr2', ls * r2)]
E4 = E8[:4]
ordv = [('a4', v['a4']), ('b4', v['b4']), ('c4', v['c4'])]
ordU = [('U40_14', v['U40_14']), ('U40_34', v['U40_34']), ('U41_34', v['U41_34']), ('c4', v['c4']), ('b4', v['b4'])]
extra_prod = [('a4c4', v['a4'] * v['c4']), ('b4c4', v['b4'] * v['c4']), ('a4^2', v['a4'] ** 2), ('b4^2', v['b4'] ** 2), ('c4^2', v['c4'] ** 2),
              ('U40_14*U41_34', v['U40_14'] * v['U41_34']), ('U40_14*U40_34', v['U40_14'] * v['U40_34']), ('U41_34^2', v['U41_34'] ** 2), ('U40_34^2', v['U40_34'] ** 2)]
T = []
T.append(("dH = d/db[N(4c0+5c2)] ~ {X0,Xh,a4b4,Ups} x E8", v['dH'], *tens(blocks, E8)))
T.append(("dH ~ {X0,Xh,a4b4,Ups} x E8 + {a4,b4,c4}-products x E4", v['dH'], *[x + y for x, y in zip(tens(blocks, E8), tens(extra_prod, E4))]))
T.append(("da = d/db[N^(1/2) a4] ~ {a4,b4,c4} x E8", v['da'], *tens(ordv, E8)))
T.append(("da ~ {U40(1/4),U40(3/4),U41(3/4),c4,b4} x E8", v['da'], *tens(ordU, E8)))
T.append(("Phat' ~ {X0,Xh,a4b4,Ups} x E8", v['Phat_prime'], *tens(blocks, E8)))
T.append(("L3 ~ {X0,Xh,a4b4,Ups} x pi x E8", v['L3'], *tens(blocks, [(n + '*pi', e * pi) for n, e in E8])))
T.append(("L3 ~ {X0,Xh,a4b4,Ups} x {1,r2,pi,pir2,pi^2,pi^2r2,pil2,pil2r2}", v['L3'], *tens(blocks, E4 + [('pi2', pi ** 2), ('pi2r2', pi ** 2 * r2), ('pil2', pi * l2), ('pil2r2', pi * l2 * r2)])))
T.append(("L3 ~ {X0,Xh,a4b4,Ups} x {1,r2,pi,pir2,pi^2,pi^2r2,pil2,pil2r2,pils,pilsr2,G,Gr2}", v['L3'], *tens(blocks, E4 + [('pi2', pi ** 2), ('pi2r2', pi ** 2 * r2), ('pil2', pi * l2), ('pil2r2', pi * l2 * r2), ('pils', pi * ls), ('pilsr2', pi * ls * r2), ('G', G), ('Gr2', G * r2)])))
T.append(("L3 - 4pi P4 + 2pi^2 X0 - 6r2 pi(pi-2l2) a4b4 ~ {pi dH, pi b4 da, pi X0, pi Xh, pi a4b4, pi Ups} x {1,r2}", v['L3'] - 4 * pi * v['P4'] + 2 * pi ** 2 * v['X0'] - 6 * r2 * pi * (pi - 2 * l2) * v['a4'] * v['b4'],
          *tens([('pi dH', pi * v['dH']), ('pi b4 da', pi * v['b4'] * v['da']), ('pi X0', pi * v['X0']), ('pi Xh', pi * v['Xh']), ('pi a4b4', pi * v['a4'] * v['b4']), ('pi Ups', pi * Ups)], [('1', 1), ('r2', r2)])))
out = []
for name, t, b, nm in T:
    rel, bound = relation(name, t, b, nm, dig)
    out.append(dict(name=name, n=len(b) + 1, relation=rel, bound=mp.nstr(bound, 4)))
json.dump(dict(dig=dig, source=fn, results=out, log=LOG), open('battery_final_dig%d.json' % dig, 'w'), indent=1)
# are the two derivative constants related?
bb, nn = tens(blocks + [('b4*da', v['b4'] * v['da'])], E8)
relation("dH ~ ({X0,Xh,a4b4,Ups} + b4*da) x E8", v['dH'], bb, nn, dig)
relation("ds ~ ({X0,Xh,a4b4,Ups} + b4*da) x E8", v['ds'], bb, nn, dig)
bb, nn = tens(blocks + [('b4*da', v['b4'] * v['da'])], [('1', 1), ('r2', r2), ('pi', pi), ('pir2', pi * r2)])
relation("m0 ~ ({X0,Xh,a4b4,Ups} + b4*da) x {1,r2,pi,pir2}", v['m0_mu1_weighted_h4_0'], bb, nn, dig)
json.dump(dict(dig=dig, source=fn, results=out, log=LOG), open('battery_final_dig%d.json' % dig, 'w'), indent=1)
