"""Independent Barnes-kernel versus ordinary hypergeometric comparison.
This script uses numerical integrals as tests, not in the proposed Wolfram formula.
It supplies no rigorous bound for the Barnes numerical quadrature and does not
execute a Wolfram kernel or recompute the full C6 coefficient.
"""
import mpmath as mp, sys, time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'legacy'))
from rational_tails import enclosure
mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 40
D=mp.mp.dps; st=time.time(); N=int(sys.argv[2]) if len(sys.argv)>2 else 128; order=int(sys.argv[3]) if len(sys.argv)>3 else 40
def mf(q):return mp.mpf(q.numerator)/q.denominator
pars=[('U8',['5/4']+['1/2']*8,['1/4']+['1']*8),('Y1',['9/8']+['3/8']*8,['1/8']+['7/8']*8),('Y7',['15/8']+['9/8']*8,['7/8']+['13/8']*8)]
v={};width={}
for name,up,dn in pars:
 iv,info=enclosure(tuple(up),tuple(dn),N,order)
 v[name]=mf((iv[0]+iv[1])/2);width[name]=mp.nstr(mf(iv[1]-iv[0]),8)
 if name.startswith('Y'):
  t=mp.mpf(name[1:])/8;v[name]*=t*(mp.gamma(t+mp.mpf('.25'))/mp.gamma(t+mp.mpf('.75')))**8
 print(name,mp.nstr(v[name],D), 'sec',time.time()-st,flush=True)
r2=mp.sqrt(2);pi=mp.pi
old=pi**6*(4932-5004*r2)*v['U8']+556*pi**2*((17+12*r2)*v['Y1']-(17-12*r2)*v['Y7'])
a=1233-278*r2;b=mp.mpf(556);c=139*r2
R=mp.sqrt((a-c)**2+b*b)
delta=mp.atan(b/(a-c))/(2*pi);eta=mp.acosh((a+c)/R)/(2*pi)
ap=delta+1j*eta;am=delta-1j*eta
print('parameters',ap,am,'R',R,'old',old,flush=True)
segs=[0,mp.mpf('.125'),mp.mpf('.25'),mp.mpf('.5'),1,2,4,8,16,mp.inf]
def raw(s):
 exp=(3*mp.loggamma(s)+7*mp.loggamma(mp.mpf('.5')-s)
      +mp.loggamma(mp.mpf('1.25')-s)-5*mp.loggamma(1-s)
      -mp.loggamma(mp.mpf('.5')+s)-mp.loggamma(mp.mpf('.25')-s)
      -mp.loggamma(s+ap)-mp.loggamma(1-s-ap)
      -mp.loggamma(s+am)-mp.loggamma(1-s-am))
 return mp.exp(exp)
def ker(u):
 if u==0:return mp.mpf(0)
 return mp.re(raw(mp.mpf('.25')+1j*u))
g=mp.quad(ker,segs)/pi
new=16*pi**3*R*g
print('G',mp.nstr(g,D),'new',mp.nstr(new,D),'diff',mp.nstr(new-old,8),'secs',time.time()-st,flush=True)
def jker(u,j):
 if u==0:return mp.mpf(0)
 s=mp.mpf('.25')+1j*u
 ex=j*mp.loggamma(s)+(10-j)*mp.loggamma(mp.mpf('.5')-s)-(8-j)*mp.loggamma(1-s)-(j-2)*mp.loggamma(mp.mpf('.5')+s)
 return mp.re((-1j*u)*mp.exp(ex))
j37=mp.quad(lambda u:jker(u,3),segs)/pi
j46=mp.quad(lambda u:jker(u,4),segs)/pi
alt=pi**6*(4932-1668*r2)*v['U8']+pi*(8896*j46+2224*r2*j37)
print('J37',mp.nstr(j37,D),'J46',mp.nstr(j46,D),'alt_diff',mp.nstr(alt-old,8),'sec',time.time()-st,flush=True)
report={'working_digits':D,'ordinary_cutoff':N,'ordinary_tail_order':order,'U8':mp.nstr(v['U8'],D),'Y1':mp.nstr(v['Y1'],D),'Y7':mp.nstr(v['Y7'],D),'ordinary_widths':width,'R':mp.nstr(R,D),'alpha_plus':mp.nstr(ap,D),'alpha_minus':mp.nstr(am,D),'G':mp.nstr(g,D),'old_block_r6':mp.nstr(old,D),'new_block_r6':mp.nstr(new,D),'absolute_difference':mp.nstr(abs(new-old),10),'difference_in_C6_units':mp.nstr(abs(new-old)/2187,10),'J37':mp.nstr(j37,D),'J46':mp.nstr(j46,D),'rational_alternative_difference':mp.nstr(abs(alt-old),10),'seconds':time.time()-st}
(Path(__file__).parent/'results'/f'numerical_{D}.json').write_text(json.dumps(report,indent=2)+'\n')
