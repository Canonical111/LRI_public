from mpmath import mp, mpf, mpc, gamma, psi, pi, log, zeta, sqrt, atan, cos, sin, tan, exp, quad, nsum, inf, euler, rgamma, loggamma
def a_(n): return exp(loggamma(n+mpf(1)/2)-loggamma(n+1))/sqrt(pi)
def Hc(n): return psi(0,n+1)+euler
def H2c(n): return zeta(2)-psi(1,n+1)
def H3c(n): return zeta(3)+psi(2,n+1)/2
def h_(n): return log(2)+psi(0,n+1)-psi(0,2*n+1)
def dl_(n): return psi(1,n+mpf(1)/2)-psi(1,n+1)
def tau_(n): return 12*zeta(3)-16*H3c(2*n)+4*H3c(n)
def S(f, N0=20):
    # sum_{n>=0} f(n) for smooth f: direct + Euler-Maclaurin tail
    s = sum(f(mpf(n)) for n in range(N0))
    return s + nsum(f, [N0, inf], method='euler-maclaurin')
def Salt(f, N0=20):
    # sum (-1)^n f(n)
    se = S(lambda m: f(2*m), N0); so = S(lambda m: f(2*m+1), N0)
    return se-so
def B(f, c, cut=None):
    # (1/2pi i) int_{c-i inf}^{c+i inf} f(s) ds = (1/2pi) int f(c+iu) du
    g = lambda u: f(mpc(c,u))
    pts = [-inf,-20,-5,-1,0,1,5,20,inf]
    return quad(g, pts)/(2*pi)
LG = loggamma
def GP(num, den):
    # product of gammas: num, den are lists of arguments
    return exp(sum(LG(x) for x in num) - sum(LG(x) for x in den))
def TAN(s):  # tan(pi s) as gamma ratio
    return GP([0.5+s, 0.5-s], [s, 1-s])
def RR(s, k):  # [Gamma(s)/Gamma(s+1/2)]^k
    return exp(k*(LG(s)-LG(s+0.5)))
