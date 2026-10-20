import mpmath as mp, sys, json
from load import load
from lllrel import relation, tens, LOG
dig=int(sys.argv[1]) if len(sys.argv)>1 else 155
fn=sys.argv[2] if len(sys.argv)>2 else 'pA_dps170.json'
d,V,D,D2,cen=load(fn,0)
mp.mp.dps=dig+20
pi=mp.pi;r2=mp.sqrt(2);l2=mp.log(2);ls=mp.log(1+r2);G=mp.catalan
A3=2+4*l2-pi
H0,Hh,A,B,C,V0q,V1q,V0p,V1p=[V[k] for k in ['H0','Hh','A','B','C','V0q','V1q','V0p','V1p']]
AB=A*B;VV=V0q*V1q
k1=224*r2-320;k2=120*r2-170
L3=-D['W']/2;P4=V['W']
Pt=2*D['H0']-5*D['Hh']+k1*(D['A']*B+A*D['B'])+k2*(D['V0q']*V1q+V0q*D['V1q'])   # = pi * d/dgamma(frozen-weight P4)
Hd=2*D['H0']-5*D['Hh']
E8=[('1',1),('r2',r2),('pi',pi),('pir2',pi*r2),('l2',l2),('l2r2',l2*r2),('ls',ls),('lsr2',ls*r2)]
P=[('H0',H0),('Hh',Hh),('AB',AB),('VV',VV)]
tests=[]
# L3 directly
tests.append(('L3 ~ P x {1,r2} + P x {1,r2,l2,l2r2,ls,lsr2}/pi',L3,*tens(P,[('1',1),('r2',r2)]+[(n+'/pi',e/pi) for n,e in E8 if 'pi' not in n])))
tests.append(('L3 ~ P x {1,r2,pi,pir2,l2,l2r2}',L3,*tens(P,E8[:6])))
tests.append(('L3 ~ P x E8',L3,*tens(P,E8)))
# derivative combinations
tests.append(("Pt=pi dP4frozen/dgamma ~ P x E8",Pt,*tens(P,E8)))
tests.append(("2H0'-5Hh' ~ P x E8",Hd,*tens(P,E8)))
tests.append(("H0' ~ P x E8",D['H0'],*tens(P,E8)))
tests.append(("Hh' ~ P x E8",D['Hh'],*tens(P,E8)))
O=[('A',A),('B',B),('C',C)]
tests.append(("A' ~ {A,B,C} x E8",D['A'],*tens(O,E8)))
tests.append(("C' ~ {A,B,C} x E8",D['C'],*tens(O,E8)))
O2=[('V0q',V0q),('V1q',V1q),('V0p',V0p),('V1p',V1p),('C',C)]
for k in ['V0q','V1q','V0p','V1p']:
    tests.append((k+"' ~ {V0q,V1q,V0p,V1p,C} x E8",D[k],*tens(O2,E8)))
# Horn derivative allowing ordinary-derivative products
extra=[("A'B",D['A']*B),("V0q'V1q",D['V0q']*V1q),("V0qV1q'",V0q*D['V1q'])]
b,nm=tens(P,E8); b+= [e for _,e in extra]; nm+=[n for n,_ in extra]
tests.append(("2H0'-5Hh' ~ P x E8 + ordinary derivative products",Hd,b,nm))
# L3 with ordinary-derivative products allowed
b,nm=tens(P,[('1',1),('r2',r2)]+[(n+'/pi',e/pi) for n,e in E8[:6] if 'pi' not in n]); b+=[e/pi for _,e in extra]+[r2*e/pi for _,e in extra]; nm+=[n+'/pi' for n,_ in extra]+[n+'r2/pi' for n,_ in extra]
tests.append(("L3 ~ P x{1,r2,(1,r2,l2,l2r2)/pi} + {A'B,V0q'V1q,V0qV1q'} x{1,r2}/pi",L3,b,nm))
out=[]
for name,t,b,nm in tests:
    rel,bound=relation(name,t,b,nm,dig)
    out.append(dict(name=name,n=len(b)+1,relation=rel,bound=str(mp.nstr(bound,4))))
json.dump(dict(dig=dig,source=fn,results=out,log=LOG),open('battery_dig%d.json'%dig,'w'),indent=1)
