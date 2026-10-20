import mpmath as mp, sys, json
from load import load
from lllrel import relation, tens, LOG
dig=int(sys.argv[1]) if len(sys.argv)>1 else 155
fn=sys.argv[2] if len(sys.argv)>2 else 'pA_dps170.json'
d,V,D,D2,cen=load(fn,0)
mp.mp.dps=dig+20
pi=mp.pi;r2=mp.sqrt(2);l2=mp.log(2);ls=mp.log(1+r2);G=mp.catalan
H0,Hh,A,B,C,V0q,V1q,V0p,V1p=[V[k] for k in ['H0','Hh','A','B','C','V0q','V1q','V0p','V1p']]
AB=A*B;VV=V0q*V1q
L3=-D['W']/2;P4=V['W']
k1=224*r2-320;k2=120*r2-170
Pt=2*D['H0']-5*D['Hh']+k1*(D['A']*B+A*D['B'])+k2*(D['V0q']*V1q+V0q*D['V1q'])
P=[('H0',H0),('Hh',Hh),('AB',AB),('VV',VV)]
W1=[('pi',pi),('pir2',pi*r2),('l2',l2),('l2r2',l2*r2),('ls',ls),('lsr2',ls*r2)]
Eq=[('1',1),('r2',r2)]
Einv=[(n+'/pi',e/pi) for n,e in [('1',1),('r2',r2),('l2',l2),('l2r2',l2*r2),('ls',ls),('lsr2',ls*r2)]]
tests=[]
tests.append(('L3 ~ P x {1,r2, (1,r2,l2,l2r2,ls,lsr2)/pi}',L3,*tens(P,Eq+Einv)))
tests.append(('L3 ~ P x {1,r2,W1, (1,r2,l2,l2r2,ls,lsr2)/pi}',L3,*tens(P,Eq+W1+Einv)))
tests.append(('L3 ~ P x {1,r2,pi,pir2,1/pi,r2/pi}',L3,*tens(P,Eq+W1[:2]+Einv[:2])))
tests.append(('L3 ~ P x {1,r2,pi,pir2,l2,l2r2,G,Gr2,pi^2,pi^2r2}',L3,*tens(P,Eq+W1[:4]+[('G',G),('Gr2',G*r2),('pi2',pi**2),('pi2r2',pi**2*r2)])))
tests.append(('Pt ~ P x {1,r2,W1,pi^2,pi^2r2,G,Gr2,pil2,pil2r2}',Pt,*tens(P,Eq+W1+[('pi2',pi**2),('pi2r2',pi**2*r2),('G',G),('Gr2',G*r2),('pil2',pi*l2),('pil2r2',pi*l2*r2)])))
out=[]
for name,t,b,nm in tests:
    rel,bound=relation(name,t,b,nm,dig)
    out.append(dict(name=name,n=len(b)+1,relation=rel,bound=str(mp.nstr(bound,4))))
json.dump(dict(dig=dig,source=fn,results=out,log=LOG),open('battery2_dig%d.json'%dig,'w'),indent=1)
