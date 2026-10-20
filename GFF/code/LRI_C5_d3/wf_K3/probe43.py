# quick PSLQ probes at 43 established digits (K3 from masters_d3.json)
import mpmath as mp
mp.mp.dps=60
K3=mp.mpf('1.1485946495271793365566463108106731876338481')
pi,G,z3,l2,s2=mp.pi,mp.catalan,mp.zeta(3),mp.log(2),mp.sqrt(2)
A=2+4*l2-pi; U=2*pi**3-56*z3
# check d=1, d=2 pattern
p11=mp.psi(1,mp.mpf(1)/4)
K1=128*G**2+24*pi**2*G-4*pi**3*l2-28*(pi+4*l2)*z3
A1=pi+4*l2;U1=mp.psi(2,mp.mpf(1)/4)
print('d1 check',mp.nstr(K1-(2*p11**2-pi**2*p11+A1/2*U1),5))
K2=32*G**2-28*z3*l2;A2=4*l2;U2=mp.psi(2,mp.mpf(1)/2)
print('d2 check',mp.nstr(K2-(p11**2/2-pi**2*p11+pi**4/2+A2/2*U2),5))
Kp=K3-A/2*U
print('K3 - A U/2 =',Kp)
L8=mp.nsum(lambda k: 1/(8*k+1)**2+1/(8*k+3)**2-1/(8*k+5)**2-1/(8*k+7)**2,[0,mp.inf])
digits=43
def test(name,target,basis):
    vec=[target]+[v for _,v in basis];n=len(vec)
    cmax=int(mp.floor(mp.mpf(10)**(mp.mpf(digits-10)/n)))
    with mp.workdps(digits):
        rel=mp.pslq(vec,tol=mp.mpf(10)**(-(digits-3)),maxcoeff=cmax,maxsteps=10**6)
    if rel is None: print(name,'none, bound',cmax,'n',n);return
    print(name,rel,[nm for nm,_ in basis])
w2=[('pi2',pi**2),('G',G),('s2pi2',s2*pi**2),('L8',L8),('s2G',s2*G),('s2L8',s2*L8)]
quad=[]
for i in range(len(w2)):
    for j in range(i,len(w2)):
        quad.append((w2[i][0]+'*'+w2[j][0],w2[i][1]*w2[j][1]))
# reduce: only products with at most one sqrt2 factor overall (s2*s2=2 rational)
quadr=[(n,v) for n,v in quad if n.count('s2')<=1]
test('Kp quad level8 (no sqrt2 dup)',Kp,quadr[:10])
test('Kp in pi4,pi2G,G2,pi2L8,GL8,L82',Kp,[('pi4',pi**4),('pi2G',pi**2*G),('G2',G**2),('pi2L8',pi**2*L8),('GL8',G*L8),('L82',L8**2)])
test('Kp + sqrt2',Kp,[('pi4',pi**4),('pi2G',pi**2*G),('G2',G**2),('s2pi4',s2*pi**4),('s2pi2G',s2*pi**2*G),('s2G2',s2*G**2)])
