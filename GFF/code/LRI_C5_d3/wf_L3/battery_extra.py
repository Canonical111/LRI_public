import mpmath as mp, json, sys
from lllrel import relation, tens, LOG
dig = int(sys.argv[1]) if len(sys.argv) > 1 else 155
mp.mp.dps = dig + 20
v = {k: mp.mpf(x) for k, x in json.load(open('L3_final_values.json'))['values'].items()}
x = {k: mp.mpf(s) for k, s in json.load(open('extra_nodes_dps170.json')).items()}
pi = mp.pi; r2 = mp.sqrt(2); l2 = mp.log(2); ls = mp.log(1 + r2)
Ups = v['U40_34'] * v['U41_34']
E4 = [('1', 1), ('r2', r2), ('pi', pi), ('pir2', pi * r2)]
blocks = [('X0', v['X0']), ('Xh', v['Xh']), ('a4b4', v['a4'] * v['b4']), ('Ups', Ups)]
horn = [(k, x[k]) for k in ['Tp(0)', 'Tp(1/16)', 'Tp(3/16)', 'Tp(3/8)', 'Tp(1/2)', 'Tp(5/8)', 'Tp(3/4)', 'Tp(7/8)']]
b1, n1 = tens(blocks + horn, E4)
relation("dH ~ ({X0,Xh,a4b4,Ups} + Tp at 8 extra nodes) x {1,r2,pi,pir2}", v['dH'], b1, n1, dig)
b2, n2 = tens(blocks + horn, [('1', 1), ('r2', r2)])
relation("dH ~ ({X0,Xh,a4b4,Ups} + Tp at 8 extra nodes) x {1,r2}", v['dH'], b2, n2, dig)
relation("Phat' ~ ({X0,Xh,a4b4,Ups} + Tp at 8 extra nodes) x {1,r2,pi,pir2}", v['Phat_prime'], b1, n1, dig)
ordn = [('a4', v['a4']), ('b4', v['b4']), ('c4', v['c4']), ('U40(1/4)', v['U40_14']), ('U40(3/4)', v['U40_34']), ('U41(3/4)', v['U41_34'])] + \
       [(k, x[k]) for k in ['U0(1/8)', 'U0(3/8)', 'U0(5/8)', 'U0(7/8)', 'U1(1/8)', 'U1(3/8)', 'U1(5/8)', 'U1(7/8)']]
b3, n3 = tens(ordn, E4)
relation("da ~ (a4,b4,c4,U at 1/8..7/8) x {1,r2,pi,pir2}", v['da'], b3, n3, dig)
b4_, n4 = tens(ordn, [('1', 1), ('r2', r2), ('l2', l2), ('ls', ls)])
relation("da ~ (a4,b4,c4,U at 1/8..7/8) x {1,r2,l2,ls}", v['da'], b4_, n4, dig)
json.dump(dict(dig=dig, log=LOG), open('battery_extra_dig%d.json' % dig, 'w'), indent=1)
# independent ordinary basis (finite-mode identities remove U0(1/8),U0(5/8),U0(3/4),U1(1/8),U1(5/8),U1(1/4))
ordi = [('a4', v['a4']), ('b4', v['b4']), ('c4', v['c4']), ('U40(1/4)', v['U40_14']), ('U41(3/4)', v['U41_34'])] + \
       [(k, x[k]) for k in ['U0(3/8)', 'U1(3/8)', 'U0(7/8)', 'U1(7/8)']]
b5, n5 = tens(ordi, E4)
relation("da ~ independent ordinary basis(9) x {1,r2,pi,pir2}", v['da'], b5, n5, dig)
b6, n6 = tens(ordi, [('1', 1), ('r2', r2), ('l2', l2), ('ls', ls)])
relation("da ~ independent ordinary basis(9) x {1,r2,l2,ls}", v['da'], b6, n6, dig)
json.dump(dict(dig=dig, log=LOG), open('battery_extra_dig%d.json' % dig, 'w'), indent=1)
# by-product found: 4 b4 + (1-r2) U41(3/4) - 2(1+r2) U1(3/8) = 0 numerically (res ~1e-166); drop U1(3/8)
ordi2 = [('a4', v['a4']), ('b4', v['b4']), ('c4', v['c4']), ('U40(1/4)', v['U40_14']), ('U41(3/4)', v['U41_34'])] + \
        [(k, x[k]) for k in ['U0(3/8)', 'U0(7/8)', 'U1(7/8)']]
for nm, vv in ordi2:
    rest = [(a, b) for a, b in ordi2 if a != nm]
    bb, nn = tens(rest, E4)
    relation("basis check: %s ~ rest x E4" % nm, vv, bb, nn, dig)
b7, n7 = tens(ordi2, E4)
relation("da ~ independent ordinary basis(8) x {1,r2,pi,pir2}", v['da'], b7, n7, dig)
b8, n8 = tens(ordi2, [('1', 1), ('r2', r2), ('l2', l2), ('ls', ls)])
relation("da ~ independent ordinary basis(8) x {1,r2,l2,ls}", v['da'], b8, n8, dig)
r = mp.mpf(4) * v['b4'] + (1 - r2) * v['U41_34'] - 2 * (1 + r2) * x['U1(3/8)']
print('by-product identity residual', mp.nstr(r, 3))
LOG.append('by-product identity 4 b4 + (1-r2) U41(3/4) - 2(1+r2) U1(3/8) residual %s' % mp.nstr(r, 3))
json.dump(dict(dig=dig, log=LOG), open('battery_extra_dig%d.json' % dig, 'w'), indent=1)
