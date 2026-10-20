import math, json, mpmath as mp
from pathlib import Path
mp.mp.dps=80
pi=mp.pi;l=mp.log(2);A=pi+4*l
c7=mp.cos(pi/8)**7;s7=mp.sin(pi/8)**7;Rplus=13+22*mp.sqrt(2);Rminus=22*mp.sqrt(2)-13
p=[c7*Rplus,-35,c7*Rminus,-s7*Rminus,s7*Rplus]
xiPlus=-55*A/98+(401+735*mp.sqrt(2))*pi/1598
xiMinus=-55*A/98+(401-735*mp.sqrt(2))*pi/1598
xis=[xiPlus,37*A/196-67*pi/140,xiMinus+4,xiMinus+mp.mpf(4)/3,xiPlus+mp.mpf(24)/5]
N=420;den=1<<N;cum=0;weights=[]
for n in range(N):
 cum+=math.comb(N,n);weights.append(mp.mpf(den-cum)/den)
targets=[]
for r,xi in zip([1,2,3,5,7],xis):
 t=mp.mpf(r)/8;a=t+mp.mpf(1)/4;b=t+mp.mpf(3)/4
 u=t*(mp.gamma(a)/mp.gamma(b))**7;H=mp.mpf(0);terms=[]
 for n in range(N):
  terms.append(weights[n]*u*(H+xi))
  H+=(1/(n+a)+1/(n+b))/2
  u*=-(n+t+1)/(n+t)*((n+a)/(n+b))**7
 targets.append(mp.fsum(terms))
B=9408*pi**mp.mpf('1.5')*mp.fsum(w*v for w,v in zip(p,targets))
new=json.loads((Path(__file__).resolve().parent/'results'/'numerical_80.json').read_text())
err=abs(B-mp.mpf(new['B7_new']))
print('oldfive',mp.nstr(B,80));print('diff',mp.nstr(err,15))
(Path(__file__).resolve().parent/'results'/'shifted_check.json').write_text(json.dumps({'working_decimal_digits':80,'Euler_N':N,'shifted_targets':[str(x) for x in targets],'B7_original_five_shift':str(B),'absolute_difference_from_new_Barnes_form':str(err),'rigorous_interval':False},indent=2))
