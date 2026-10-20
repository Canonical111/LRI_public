import json
from fractions import Fraction as F
import mpmath as mp
mp.mp.dps=30
for c in (8,16,24):
    o=json.load(open(f'exact5_c{c}.json')); V=o['variants']
    C={k:[F(x) for x in V[k]['C']] for k in V}
    out={}
    for k in V:
        if k=='raw': continue
        d4=C[k][4]-C['raw'][4]; d5=C[k][5]-C['raw'][5]
        out[k]=(mp.mpf(d4.numerator)/d4.denominator, mp.mpf(d5.numerator)/d5.denominator)
    print('L=',c//4,'raw C4,C5', float(C['raw'][4]), float(C['raw'][5]))
    for k,(a,b) in out.items(): print('   ',k,'dC4=',mp.nstr(a,20),'dC5=',mp.nstr(b,20))
