import json, mpmath as mp, itertools
mp.mp.dps=72
d=json.load(open('<PROJECT>/LRI_C5_d2_simplify/confirm_dps70.json'))
S={}
for k,v in d['singles'].items():
    kk=eval(k)
    if kk[0]=='K': S[(kk[1],kk[2])]=mp.mpf(v)
pi,l2,G,z3=mp.pi,mp.log(2),mp.catalan,mp.zeta(3)
T3=mp.im(mp.polylog(3,(1+1j)/2))
L4=mp.polylog(4,0.5); b4=(mp.zeta(4,0.25)-mp.zeta(4,0.75))/256; z5=mp.zeta(5)
names=['x1','x2','x3','x4','w0','w1','w2','w3']
def weight(e): return sum(p*(i+1) for i,p in enumerate(e[:4]))+sum(p*(i+1) for i,p in enumerate(e[4:]))
# basis by weight
B={1:[('pi',pi),('l2',l2)],
   2:[('pi2',pi**2),('pil2',pi*l2),('l22',l2**2),('G',G)],
   3:[('pi3',pi**3),('pi2l2',pi**2*l2),('pil22',pi*l2**2),('l23',l2**3),('piG',pi*G),('Gl2',G*l2),('z3',z3),('T3',T3)],
}
B[4]=[('pi4',pi**4),('pi3l2',pi**3*l2),('pi2l22',pi**2*l2**2),('pil23',pi*l2**3),('l24',l2**4),('pi2G',pi**2*G),('piGl2',pi*G*l2),('Gl22',G*l2**2),('G2',G**2),('piz3',pi*z3),('z3l2',z3*l2),('piT3',pi*T3),('T3l2',T3*l2),('L4',L4),('b4',b4)]
for key,val in sorted(S.items()):
    wt,e=key
    if wt!='C': continue
    w=weight(e)
    pure=all(p==0 for i,p in enumerate(e) if i!=4)
    tgt=pi*val
    for W in [w+1]:
        if W>4: 
            print(key,'w=',w,'skip (weight',W,')'); continue
        bas=B[W]
        rel=mp.pslq([tgt]+[x for _,x in bas],maxcoeff=10**6,maxsteps=10**6)
        print(key,'w=',w,'pure' if pure else '', rel and dict(zip(['S']+[n for n,_ in bas],rel)))
