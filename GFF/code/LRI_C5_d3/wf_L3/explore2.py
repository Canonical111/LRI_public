import mpmath as mp, sys
from load import load
fn=sys.argv[1] if len(sys.argv)>1 else 'pieces_dps50.json'
dig=int(sys.argv[2]) if len(sys.argv)>2 else 45
d,V,D,D2,cen=load(fn,0)
mp.mp.dps=dig+5
pi=mp.pi;r2=mp.sqrt(2);l2=mp.log(2);ls=mp.log(1+r2);G=mp.catalan
A3=2+4*l2-pi
H0,Hh,A,B,V0q,V1q=[V[k] for k in ['H0','Hh','A','B','V0q','V1q']]
AB=A*B;VV=V0q*V1q
L3=-D['W']/2;P4=V['W']
def test(name,target,basis,names):
    vec=[target]+basis;n=len(vec)
    mc=int(10**((dig-10)/n))
    rel=mp.pslq(vec,tol=mp.mpf(10)**(-(dig-3)),maxcoeff=mc,maxsteps=2*10**6)
    if rel and rel[0]!=0:
        res=abs(mp.fsum(a*b for a,b in zip(rel,vec)))/max(abs(a*b) for a,b in zip(rel,vec))
        print(name,'RELATION res %s:'%mp.nstr(res,3),[(c,nm) for c,nm in zip(rel,['T']+names) if c])
    else: print(name,'none  n=%d |c|<=%d'%(n,mc))
def tens(objs,els):
    b=[];nm=[]
    for on,o in objs:
        for en,e in els: b.append(o*e);nm.append(on+'*'+en)
    return b,nm
objs=[('H0',H0),('Hh',Hh),('AB',AB),('VV',VV)]
for els in [[('1',1),('r2',r2)],[('1',1),('r2',r2),('pi',pi),('pir2',pi*r2)],[('1',1),('r2',r2),('l2',l2),('l2r2',l2*r2)],
            [('1',1),('r2',r2),('1/pi',1/pi),('r2/pi',r2/pi)], [('1',1),('r2',r2),('l2/pi',l2/pi),('l2r2/pi',l2*r2/pi)]]:
    b,nm=tens(objs,els)
    test('L3+A3/2 P4 ~ '+','.join(e for e,_ in els),L3+A3/2*P4,b,nm)
    test('L3 ~ P4,A3P4 + '+','.join(e for e,_ in els),L3,[P4,A3*P4]+b,['P4','A3P4']+nm)
