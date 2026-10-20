import mpmath as mp, itertools
from load import load
d,V,D,D2,cen=load('pieces_dps50.json',0)
mp.mp.dps=46
pi=mp.pi;r2=mp.sqrt(2);l2=mp.log(2);ls=mp.log(1+r2)
def test(name,target,basis,names,dig=45):
    vec=[target]+basis
    n=len(vec)
    mc=int(10**((dig-10)/n))
    rel=mp.pslq(vec,maxcoeff=mc,maxsteps=10**6)
    if rel:
        res=mp.fsum(a*b for a,b in zip(rel,vec))
        print(name,'RELATION',rel,'res',mp.nstr(res,3),'(maxcoeff',mc,')')
        print('   ',[ (c,nm) for c,nm in zip(rel,['T']+names) if c])
    else: print(name,'none, n=%d, |c|<=%d'%(n,mc))
A,B,C=V['A'],V['B'],V['C']
el=[('1',1),('pi',pi),('l2',l2)]
for tg in ['A','C']:
  for E in [[('1',1),('pi',pi),('l2',l2)],[('1',1),('pi',pi),('l2',l2),('r2',r2),('ls',ls)]]:
    basis=[];names=[]
    for X,xn in [(A,'A'),(C,'C'),(B,'B')]:
        for en,e in E: basis.append(X*e);names.append(xn+'*'+en)
    test(tg+"'",D[tg],basis,names)
# V0q', V1q' against ordinary values
for tg in ['V0q','V1q','V0p','V1p']:
    basis=[];names=[]
    for X in ['V0q','V1q','V0p','V1p']:
        for en,e in [('1',1),('pi',pi),('l2',l2)]: basis.append(V[X]*e);names.append(X+'*'+en)
    test(tg+"'",D[tg],basis,names)
