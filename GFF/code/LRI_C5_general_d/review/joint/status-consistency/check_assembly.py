# status-consistency joint review, 2026-10-03: quick checks of the combined C5(d) statement.
# (1) gdr:C5reduced == gs:C5 after inserting gdr:P4, gdr:L, gdr:Q, gdr:Z (symbolic, sympy).
# (2) gdk:Kr3 with the printed r3 column reproduces the printed K_d column and the independent
#     spectral references K (reference_values.json); closed forms r3(1), r3(2); gdk:E2 dictionary.
# (3) C5 with K_d substituted by gdk:Kr3: the K_d-dependent part -1536 K_d rewritten.
import json, sympy as sp, mpmath as mp

# ---------- (1) symbolic assembly ----------
A,R,U,V,X,C,S,pi = sp.symbols('A R U V X C S pi', real=True)
X0,Xh,XT,DL,T3,T3pp,c0,c0p,c0pp,P5,K,cosd = sp.symbols('X0 Xh XT DL T3 T3pp c0 c0p c0pp P5 K cosd')
P4 = 2/(pi*S**7)*((1+C)**2*(1+2*C)*X0-(1-C)**2*(1-2*C)*Xh-2*C*XT)
L  = -1/S**8*((1+C)**2*(4+9*C+8*C**2)*X0+(1-C)**2*(4-9*C+8*C**2)*Xh-2*(1+6*C**2)*XT)+2/(pi*S**7)*DL
Q  = (6*pi**2/S**2*T3+4/(pi*S**3)*c0)/3
Z  = 2*pi**2/(3*S**2)*T3pp - pi**2*cosd/(6*S**2)*Q + sp.Rational(1,9)*(pi*(1+C**2)/S**5*c0-4*C/S**4*c0p+4/(pi*S**3)*c0pp)
gsC5 = (-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+720*A**2*Q+1008*Q*R+7152*Z
        -15*A**4-90*A**2*R+414*A*U-108*A*V-117*R**2-75*X)
k0 = (1+C)**2*(768*A*(1+2*C)/(pi*S**7)+576*(4+9*C+8*C**2)/S**8)
kh = (1-C)**2*(-768*A*(1-2*C)/(pi*S**7)+576*(4-9*C+8*C**2)/S**8)
kT = -1536*A*C/(pi*S**7)-1152*(1+6*C**2)/S**8
Qd = 2*pi**2/S**2*T3+4/(3*pi*S**3)*c0
red = (-1536*(P5+K)-1728*Qd**2+(720*A**2+1008*R-1192*pi**2*cosd/S**2)*Qd
       +k0*X0+kh*Xh+kT*XT-1152/(pi*S**7)*DL+4768*pi**2/S**2*T3pp
       +sp.Rational(2384,3)*(pi*(1+C**2)/S**5*c0-4*C/S**4*c0p+4/(pi*S**3)*c0pp)
       -15*A**4-90*A**2*R+414*A*U-108*A*V-117*R**2-75*X)
print('(1) gs:C5 - gdr:C5reduced =', sp.simplify(sp.expand(gsC5-red)))

# ---------- (2) gdk:Kr3 against the printed tables and the spectral references ----------
mp.mp.dps = 60
def basis(d):
    q = mp.mpf(d)/4
    A_ = mp.psi(0,2*q)+mp.psi(0,1)-2*mp.psi(0,q); R_ = mp.psi(1,2*q)-mp.psi(1,1)
    U_ = mp.psi(2,q); V_ = mp.psi(2,1)+mp.psi(2,2*q); X_ = mp.psi(3,2*q)-mp.psi(3,1)
    cs = mp.psi(0,1)+mp.psi(0,2*q)
    return q,A_,R_,U_,V_,X_,cs
def s3(d):
    q,A_,R_,U_,V_,X_,cs = basis(d)
    x1 = cs-4*mp.psi(0,q); x2 = -R_; x3 = V_-U_; x4 = -X_
    # check (x1..x4) of gdk:xh against the general formula
    xh = lambda h: mp.psi(h-1,1)-(-1)**h*mp.psi(h-1,2*q)-(2**(3-h)*mp.psi(h-1,q) if h%2 else 0)
    assert all(abs(a-b)<mp.mpf(10)**-50 for a,b in zip((x1,x2,x3,x4),(xh(1),xh(2),xh(3),xh(4))))
    return (x1**4+6*x1**2*x2+4*x1*x3+3*x2**2+x4)/24
def Kr3(d, r3):
    q,A_,R_,U_,V_,X_,cs = basis(d)
    return U_/8*(mp.psi(0,1)+mp.psi(0,2*q)+4*mp.psi(0,q)) + (r3-s3(d))/4
tableK = {'0.8':'92.372770239922771632645391899036','1':'39.331569128259039057503187151598','1.25':'17.203345729921688327085720106549',
 '1.5':'9.0182974015948205470847431046793','2':'3.5181091385902522416490901703077','2.5':'1.8405012954285880307301818602723',
 '2.75':'1.4292491886603120000991755368839','3':'1.1485946495271793365566463108107'}
tabler3 = {'0.8':'1894.360867513991151448939858','1':'767.2452094446567860904798157','1.25':'302.1379775430212297584696879',
 '1.5':'136.5685443212260369206603723','2':'35.63714944308140680727039972','2.5':'11.46731776044183878576775169',
 '2.75':'6.984719816576732523926795216','3':'4.511759358236005780256620898'}
ref = json.load(open('<PROJECT>/LRI_C5_general_d/references/reference_values.json'))['values']
print('(2) gdk:Kr3(r3 column) vs K column, and vs spectral reference K:')
for dd in tableK:
    k1 = Kr3(mp.mpf(dd), mp.mpf(tabler3[dd])); kt = mp.mpf(tableK[dd])
    line = f'  d={dd:5s} Kr3-Ktable rel {mp.nstr((k1-kt)/kt,3):>10s}'
    if f'd={dd}' in ref:
        kr = mp.mpf(ref[f'd={dd}']['K']['value']); line += f'   Ktable-Kref rel {mp.nstr((kt-kr)/kr,3)}'
    print(line)
# closed forms
G = mp.catalan; z3 = mp.zeta(3); gE = mp.euler; l2 = mp.log(2); P = mp.pi
K1 = 128*G**2+24*P**2*G-4*P**3*l2-28*(P+4*l2)*z3
r31 = s3(1)+4*K1-2*(P**3+28*z3)*(3*gE+7*l2+P)
K2 = 32*G**2-28*z3*l2
r32 = s3(2)+128*G**2-168*z3*l2-42*gE*z3
print('(2b) r3(1) closed form', mp.nstr(r31,32), ' printed 767.24520944465678609047981573762')
print('     r3(2) closed form', mp.nstr(r32,32), ' printed 35.637149443081406807270399721681')
print('     Kr3(1, r3(1)) - K1 =', mp.nstr(Kr3(1,r31)-K1,3), '; Kr3(2, r3(2)) - K2 =', mp.nstr(Kr3(2,r32)-K2,3))
q,A_,R_,U_,V_,X_,cs = basis(1)
print('     U/8[psi(1)+psi(1/2)+4psi(1/4)] - (pi^3+28z3)(3gE+7l2+pi)/2 =',
      mp.nstr(U_/8*(mp.psi(0,1)+mp.psi(0,0.5)+4*mp.psi(0,0.25))-(P**3+28*z3)*(3*gE+7*l2+P)/2,3))
# gdk:E2 dictionary
print('(2c) E2: d=1', mp.nstr(1.5*mp.psi(2,0.25)-(-3*P**3-84*z3),3), ' d=2', mp.nstr(1.5*mp.psi(2,0.5)+21*z3,3),
      ' d=3', mp.nstr(1.5*mp.psi(2,0.75)-(3*P**3-84*z3),3))
# A = c* - 2 psi(q) used in the proof of gdk:Kr3
print('(2d) A - (c* - 2psi(q)) at d=1.3:', mp.nstr(basis(1.3)[1]-(basis(1.3)[6]-2*mp.psi(0,1.3/4)),3))

# ---------- (3) substituted form of the K_d term ----------
psi0q, psi02q, psi01, r3s, s3s = sp.symbols('psi0q psi02q psi01 r3 s3')
Ksub = U/8*(psi01+psi02q+4*psi0q)+(r3s-s3s)/4
print('(3) -1536*K_d after gdk:Kr3 =', sp.expand(-1536*Ksub))
