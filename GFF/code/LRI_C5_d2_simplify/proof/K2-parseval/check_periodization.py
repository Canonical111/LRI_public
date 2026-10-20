# Numerical check of the two-mode periodization lemma and of the closed form of the tau>0 factorized spectral sums.
# Quantities (0<tau<1/2), G = Gamma:
#   frak_a(x) = G(x+1/2)^3/(G(x+1)^2 G(x+1/2+tau))      S_a  = sum_{m>=0} frak_a(m),  S_a' = sum_m frak_a'(m)
#   g(x)      = G(x+1/2)^2 G(x+1-tau)/G(x+1)^3          F0   = sum_k g(k)  ( = pi G(1-tau) FF(1-tau) )
#   frak_c(x) = G(x+1-tau)^3/(G(x+3/2-tau)^2 G(x+1))    S_c  = sum_k frak_c(k)
#   FF(t) = 3F2(1/2,1/2,t;1,1;1),  GG(t) = 3F2(t,t,t;1/2+t,1/2+t;1)
# Claims (Lemma D):  S_a' = -pi sin(pi tau) F0 ;  S_a = cos(pi tau) F0 + sin(pi tau)^2 S_c
# Thomae (note eq:KproofThomae at t=1-tau):  sin(pi tau) S_c = pi G(1-tau) FF(tau)
# Proposition:  <t^2 R_tau> = (a-family)+(b-family) = pi sin(pi tau) G(1-tau)^2 [FF(tau)^2 + FF(1-tau)^2]
# Two-wheel family (Lemma E): frak_s(x) = [G(x+2al)/G(x+1)]^2, 2al=(1-tau)/2:
#   sum frak_s = Gauss = G(2al)^2 G(tau)/G(1-2al)^2 ,  sum frak_s' = -2 pi tan(pi tau/2) sum frak_s,
#   <t^2 S_tau> = C(tau) X(tau)^2 , C = G(tau)/G(1-tau), X = [G(1/2-tau/2)/G(1/2+tau/2)]^2
import sys, mpmath as mp
from rsum import rsum
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 40
h = mp.mpf(1)/2
lg = mp.loggamma

def run(tau):
    tau = mp.mpf(tau)
    a  = lambda x: mp.exp(3*lg(x+h)-2*lg(x+1)-lg(x+h+tau))
    ap = lambda x: a(x)*(3*mp.psi(0,x+h)-2*mp.psi(0,x+1)-mp.psi(0,x+h+tau))
    g  = lambda x: mp.exp(2*lg(x+h)+lg(x+1-tau)-3*lg(x+1))
    c  = lambda x: mp.exp(3*lg(x+1-tau)-2*lg(x+mp.mpf(3)/2-tau)-lg(x+1))
    FFt  = rsum(lambda k: mp.exp(2*lg(k+h)+lg(k+tau)-3*lg(k+1))/(mp.pi*mp.gamma(tau)), 1-tau)   # FF(tau)
    FF1t = rsum(lambda k: mp.exp(2*lg(k+h)+lg(k+1-tau)-3*lg(k+1))/(mp.pi*mp.gamma(1-tau)), tau) # FF(1-tau)
    Sa, F0, Sc = rsum(a, tau), rsum(g, tau), rsum(c, tau)
    Sap = rsum(ap, 1+tau)
    s, co = mp.sinpi(tau), mp.cospi(tau)
    print('tau =', tau)
    print("  S_a' + pi sin F0                 =", mp.nstr(Sap + mp.pi*s*F0, 5), '   (S_a\' =', mp.nstr(Sap, 15), ')')
    print('  S_a - cos F0 - sin^2 S_c          =', mp.nstr(Sa - co*F0 - s**2*Sc, 5))
    print('  F0 - pi G(1-tau) FF(1-tau)        =', mp.nstr(F0 - mp.pi*mp.gamma(1-tau)*FF1t, 5))
    print('  sin S_c - pi G(1-tau) FF(tau)     =', mp.nstr(s*Sc - mp.pi*mp.gamma(1-tau)*FFt, 5))
    afam = (-2*Sa*Sap - mp.pi*(s/co)*Sa**2)/(mp.pi**2*co)
    bfam = s**3/(mp.pi*co**2)*Sc**2
    closed = mp.pi*s*mp.gamma(1-tau)**2*(FFt**2 + FF1t**2)
    print('  <t^2 R_tau>: families =', mp.nstr(afam+bfam, 25), ' closed =', mp.nstr(closed, 25), ' diff =', mp.nstr(afam+bfam-closed, 5))
    al2 = (1-tau)/2
    sf  = lambda x: mp.exp(2*lg(x+al2)-2*lg(x+1))
    sfp = lambda x: sf(x)*2*(mp.psi(0,x+al2)-mp.psi(0,x+1))
    Ss, Ssp = rsum(sf, tau), rsum(sfp, 1+tau)
    gauss = mp.gamma(al2)**2*mp.gamma(tau)/mp.gamma(1-al2)**2
    print('  sum s - Gauss                     =', mp.nstr(Ss-gauss, 5))
    print("  sum s' + 2 pi tan(pi tau/2) sum s =", mp.nstr(Ssp + 2*mp.pi*mp.tan(mp.pi*tau/2)*Ss, 5))
    X = (mp.gamma(h-tau/2)/mp.gamma(h+tau/2))**2
    C = mp.gamma(tau)/mp.gamma(1-tau)
    sfam = (-2*mp.cos(mp.pi*tau/2)**2*Ss*Ssp - mp.pi*s*Ss**2)/mp.pi**2
    print('  <t^2 S_tau>: family - C X^2       =', mp.nstr(sfam - C*X**2, 5))
    return afam+bfam, sfam

if __name__ == '__main__':
    for tau in ['0.3', '0.13', '0.41']:
        run(tau)
