import time,json,mpmath as m
from pathlib import Path
from kite_klt_fast import kite
from hyper3_fast import hyper3_direct
from master_symmetry import complete,perms
from fractions import Fraction as F
m.mp.dps=45;out=[];t=time.time()
g=lambda x:m.gamma(x)/m.gamma(1-x)
for a,b,c in [('.5','.5','-.25'),('.65','.45','-.18'),('.43','.62','-.17')]:
 a,b,c=map(m.mpf,[a,b,c]);p=[2*(1-a),2*(1-b),2*(1-a),2*(1-b),-4*c]
 exact=2*g(2*c)/g(c)*g(a)*g(b)/g(a+b+c)*g(a+c)*g(b+c)/g(a+b+2*c)
 v=kite(p);err=v-exact;print('Selberg',p,'value',m.nstr(v,25),'err',m.nstr(err,5),flush=True);out.append({'kind':'Selberg','p':list(map(str,p)),'value':str(v),'reference':str(exact),'error':str(err)})
p=list(map(m.mpf,['.9','1.2','.8','1.15','.95']));v=kite(p)
# Exact S5-completion tests, implemented independently at actual powers.
a,b,c,d,e=p;lam=[6-sum(p),a,c,b+d+e-2,b,d,a+c+e-2,e,4-a-b-e,4-c-d-e]
for idx in [1,8,25,57,100]:
 pp=perms[idx];ps=[lam[pp[i]]for i in[1,4,2,5,7]]
 try:w=kite(ps);err=w-v
 except Exception as ex:out.append({'kind':'S5','p':list(map(str,ps)),'failure':str(ex)});continue
 print('S5',idx,'err',m.nstr(err,8),flush=True);out.append({'kind':'S5','p':list(map(str,ps)),'value':str(w),'reference':str(v),'error':str(err)})
for a,b in [([.5,.5,.5],[1,1]),([m.mpf('.5')+.012j,m.mpf('.5')-.034j,m.mpf('.1')+.001j],[1+.009j,m.mpf('.3')-.005j])]:
 u=hyper3_direct(a,b);w=hyper3_direct(a,b,256,38,24);print('tail',m.nstr(u-w,10),flush=True);out.append({'kind':'tail','difference':str(u-w)})
Path(__file__).with_name('klt_checks.json').write_text(json.dumps({'dps':m.mp.dps,'checks':out,'seconds':time.time()-t},indent=2))
