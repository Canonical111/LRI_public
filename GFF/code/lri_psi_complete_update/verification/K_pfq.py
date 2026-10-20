"""Original six-3F2 numerical master formula; historical CLI omitted."""
import mpmath as mp,json,sys,time
from pathlib import Path
ROOT=Path(__file__).parent
half=mp.mpf('.5')
from hyp3_asym import hyp3
def h3(a,b):return hyp3(a,b)
def jhat(t):
 h=mp.mpf('.5')
 f1=h3([t,t,h],[h+t,h+t]);f2=h3([t,t,t],[h+t,h+t])
 f3=h3([h,h,t],[1,h+t]);f4=h3([h,h,t],[1,1])
 f5=h3([h,h,h],[1,mp.mpf('1.5')-t]);f6=h3([h,h,1-t],[1,mp.mpf('1.5')-t])
 a=mp.gamma(1+t)**2/mp.gamma(h+t)**2
 b=t*mp.gamma(1+t)*mp.gamma(h)/mp.gamma(h+t)
 c=t*mp.gamma(1+t)*mp.gamma(1-t)
 d=t*t*mp.gamma(h)*mp.gamma(1-t)/mp.gamma(mp.mpf('1.5')-t)
 return 2*mp.pi*(a*(f1+f2)+b*f3+c*f4+d*(f5+f6))
def v(t,ss):
 q=mp.mpf('.25');h=mp.mpf('.5')
 return 2*mp.sqrt(mp.pi)*mp.gamma(q-ss*t/2)*mp.gamma(1+t/2)*mp.gamma(q+(ss-1)*t/2)/(mp.gamma(q+ss*t/2)*mp.gamma(h-t/2)*mp.gamma(q+(1-ss)*t/2))
def phi(t):return jhat(t)-v(t,0)**2-2*(v(t,0)-v(t,2))

