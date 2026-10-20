import mpmath as mp, sys
sys.argv=['x']
import hp_general_d as H
mp.mp.dps=30; d=mp.mpf('0.8')
for br,lab in (([0,mp.mpf('0.3'),mp.mpf('1.5'),6,40,mp.inf],'default'),([0,mp.mpf('0.3'),mp.mpf('1.5'),6,40,400,4000,40000,4e5,4e6,mp.inf],'extended breaks')):
    for L,K in ((24,30),(36,40)):
        print(lab,L,K, mp.nstr(mp.re(H.wheel(3,d/2,d,L,K,br))/3,28), flush=True)
