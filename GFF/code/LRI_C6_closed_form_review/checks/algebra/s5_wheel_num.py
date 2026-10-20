from common import *
import time
mp.dps = 30
t0 = time.time()
ell = log(2)
A_ = lambda n: 4*Hc(2*n)-3*Hc(n)-2*ell+1/(4*n+1)
R_ = lambda n: 4*H2c(2*n)-H2c(n)+2/(4*n+1)**2
q_ = lambda n: (4*n+1)*a_(n)**6
print('sum q A =', S(lambda n: q_(n)*A_(n), 40))
print('sum q (A^2-R/2) =', S(lambda n: q_(n)*(A_(n)**2-R_(n)/2), 40), time.time()-t0)
# derivative formulas of log l_n at x=0
w = exp(1j*pi/4); vr = 1-w+w**3
p0 = [mpf(1)/2]*4+[1,1,1]
vv = [w**2, w, 1, 1-w+w**2, 1+w**2, w**2-w**3, 1+w**3]
def logl(n, x):
    a,b,c,d,e,f,g = [p0[i]+x*vv[i] for i in range(7)]
    al = d+g-e
    num = [1+al] + [h+n for h in [al, g-a, g-b, g-c, d, 1+d-e]]
    den = [g, 1+g-e, f-d, 1+a+d-e, 1+b+d-e, 1+c+d-e] + [h for h in [al, g-a, g-b, g-c, d, 1+d-e]] + [n+1] + [u+n for u in [1+a+d-e,1+b+d-e,1+c+d-e,1+g-e,g]] 
    # careful: (u)_n = Gamma(u+n)/Gamma(u); prefactor already has 1/Gamma(u) for u in {g,1+g-e,1+a+d-e,1+b+d-e,1+c+d-e}
    # so denominator: Gamma(u+n) only, and prefactor Gamma(u) cancels with Pochhammer's 1/Gamma(u)^{-1}: (u)_n in denominator = Gamma(u+n)/Gamma(u)
    # => 1/(Gamma(u) (u)_n) = 1/Gamma(u+n)
    den = [f-d] + [h for h in [al, g-a, g-b, g-c, d, 1+d-e]] + [n+1] + [u+n for u in [1+a+d-e,1+b+d-e,1+c+d-e,1+g-e,g]]
    return sum(LG(z) for z in num) - sum(LG(z) for z in den) - log(pi) + log((al+2*n)/al)
for n in [0,1,2,5]:
    l0 = exp(logl(n,0))
    d1 = mp.diff(lambda x: logl(n,x), 0, 1); d2 = mp.diff(lambda x: logl(n,x), 0, 2)
    print('n',n,' l_n(0)-q/(2pi)', l0-q_(n)/(2*pi), ' dlog-2vr A', d1-2*vr*A_(n), ' d2log+2vr^2 R', d2+2*vr**2*R_(n))
# input symmetry numerically: L(p0+xv) vs L(p0+omega xv), x small
def Lfun(x):
    a,b,c,d,e,f,g = [p0[i]+x*vv[i] for i in range(7)]
    al = d+g-e
    pre = gamma(1+al)/(pi*gamma(g)*gamma(1+g-e)*gamma(f-d)*gamma(1+a+d-e)*gamma(1+b+d-e)*gamma(1+c+d-e))
    return pre*mp.hyper([al,1+al/2,g-a,g-b,g-c,d,1+d-e],[al/2,1+a+d-e,1+b+d-e,1+c+d-e,1+g-e,g],1)
mp.dps = 20
for xx in [mpf('0.1'), mpc('0.05','0.03')]:
    try:
        L1 = Lfun(xx); L2 = Lfun(w*xx)
        print('L symmetry x=',xx,':', L1, L2, abs(L1-L2), time.time()-t0)
    except Exception as ex:
        print('hyper failed', ex)
