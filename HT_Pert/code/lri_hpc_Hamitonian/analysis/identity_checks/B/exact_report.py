import json
from fractions import Fraction as F
import mpmath as mp
mp.mp.dps=30
def dec(s,n=20):
    f=F(s); return mp.nstr(mp.mpf(f.numerator)/f.denominator,n)
for L in [8,12,16]:
    d=json.load(open(f'exact_L{L}.json')); big=json.load(open(f'big_L{L}.json'))
    print(f'==== L={L} dim={d["dim"]}  raw r=',[dec(x) for x in d['r'][2:]],' g=',[dec(x) for x in d['g'][1:]])
    for v,o in d['variants'].items():
        fl=big['variants'][v]
        dif=max(abs(float(F(o['C'][4]))-fl['C'][4]), abs(float(F(o['spacing_d1'][4]))-fl['spacing_d1'][4]))
        print(f"  {v:10s} r4={dec(o['r4'])} g4={dec(o['g4'])} C4={dec(o['C'][4])}  |exact-float|<={dif:.1e}")
        for p in (1,2,3):
            print(f"      d{p}: e2={dec(o['spacing_d%d'%p][2])} e3={dec(o['spacing_d%d'%p][3])} e4={dec(o['spacing_d%d'%p][4])}")
    print('  C4 shift Dfull_c-g2D exact =',dec(str(F(d['variants']['Dfull_c']['C'][4])-F(d['variants']['g2D']['C'][4]))),
          ' Dfull_raw-g2D =',dec(str(F(d['variants']['Dfull_raw']['C'][4])-F(d['variants']['g2D']['C'][4]))))
    print('  C2,C3 raw exact:',dec(d['variants']['raw']['C'][2]),dec(d['variants']['raw']['C'][3]), ' rational C2 =',d['variants']['raw']['C'][2] if len(d['variants']['raw']['C'][2])<80 else '(long)')
