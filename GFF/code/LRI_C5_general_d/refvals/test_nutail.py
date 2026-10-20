import os, sys, mpmath as mp
os.environ['HPG_NUTAIL']='1'
sys.argv=['x']
import hp_general_d as H
mp.mp.dps=30
br=[0,mp.mpf('0.3'),mp.mpf('1.5'),6,40,mp.inf]
for dd,L,K in (('1.25',24,30),('3',24,30),('0.8',24,30),('0.8',36,40)):
    d=mp.mpf(dd); print(dd,L,K,'W3/3 =',mp.nstr(mp.re(H.wheel(3,d/2,d,L,K,br))/3,28),flush=True)
