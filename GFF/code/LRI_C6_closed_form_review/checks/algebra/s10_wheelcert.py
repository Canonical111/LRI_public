import sympy as sp
from mpmath import mp, mpf
import mpmath
t, X, y = sp.symbols('t x y', positive=True)
Q4 = sp.Rational(1,4); Q2 = sp.Rational(1,2)
def phi4(j, tt):
    if j == -1: return (tt-Q4)**3/(tt-Q2)**4
    return (tt-Q4)/(tt**j*(tt-Q2)**(j+4))
def phi6(j, tt): return (tt-Q4)**6/(tt**j*(tt-Q2)**(j+6))
def Delta(r, f):  # f: function of t
    return f(t) - ((t+Q2)/(t+1))**r*f(t+1)
E = [sp.euler(2*j) for j in range(12)]
d = [sp.Rational(E[j]*(2*j+1), 2*16**j) for j in range(12)]
print('d_j:', d[:5])
def build(M):
    L = M+1
    al = sp.symbols('al_m1 '+' '.join('al%d'%j for j in range(M+1)))
    be = sp.symbols(' '.join('be%d'%j for j in range(L+1)))
    js4 = list(range(-1,M+1))
    D4 = sum(al[i]*Delta(4, lambda tt, j=j: phi4(j,tt)) for i,j in enumerate(js4))
    D6 = sum(be[j]*Delta(6, lambda tt, j=j: phi6(j,tt)) for j in range(L+1))
    # substitute t = x - 1/4, expand in 1/x
    u = sp.Symbol('u', positive=True)  # u = 1/x
    D4u = sp.series(sp.together(D4.subs(t, 1/u-Q4)), u, 0, 2*M+5).removeO()
    D6u = sp.series(sp.together(D6.subs(t, 1/u-Q4)), u, 0, 2*L+3).removeO()
    tgt4 = sum(d[k]*u**(2*k+2) for k in range(M+2))
    tgt6 = 4*sum(d[k]*u**(2*k+1) for k in range(L+1))
    eq4 = sp.Poly(sp.expand(D4u-tgt4), u).all_coeffs()
    eq6 = sp.Poly(sp.expand(D6u-tgt6), u).all_coeffs()
    s4 = sp.solve(eq4, al, dict=True); s6 = sp.solve(eq6, be, dict=True)
    return al, be, s4, s6, js4
for M in [0,1,2]:
    al, be, s4, s6, js4 = build(M)
    print('M=%d'%M, 'alpha:', [s4[0][a] for a in al] if s4 else s4, ' beta:', [s6[0][b] for b in be] if s6 else s6)
# evenness / denominators check
for j in [-1,0,1,2]:
    expr = sp.together(Delta(4, lambda tt: phi4(j,tt)).subs(t, X-Q4))
    print('Delta4 phi4_%d even in x:'%j, sp.simplify(expr - expr.subs(X,-X)) == 0, ' denom:', sp.factor(sp.denom(sp.factor(expr))))
for j in [0,1,2]:
    expr = sp.together(Delta(6, lambda tt: phi6(j,tt)).subs(t, X-Q4))
    print('Delta6 phi6_%d odd in x:'%j, sp.simplify(expr + expr.subs(X,-X)) == 0, ' denom:', sp.factor(sp.denom(sp.factor(expr))))
# numerical certificate test
mp.dps = 40
def certificate(N, M):
    al, be, s4, s6, js4 = build(M)
    s4 = s4[0]; s6 = s6[0]; L = M+1
    q4 = sum(s4[al[i]]*phi4(j, t) for i,j in enumerate(js4))
    q6 = sum(s6[be[j]]*phi6(j, t) for j in range(L+1))
    D4e = sp.together(Delta(4, sp.Lambda(t, q4)).subs(t, 1/sp.sqrt(y)-Q4))
    D6e = sp.together(Delta(6, sp.Lambda(t, q6)).subs(t, 1/sp.sqrt(y)-Q4))
    Den4 = (1-y/16)**M*(1-9*y/16)**(M+4); Den6 = (1-y/16)**L*(1-9*y/16)**(L+6)
    P4 = sp.simplify(D4e*Den4); P6 = sp.simplify(D6e*Den6/sp.sqrt(y))
    P4 = sp.Poly(sp.expand(P4), y); P6 = sp.Poly(sp.expand(P6), y)
    U4 = sum(d[k]*y**(k+1) for k in range(M+2)); U6 = 4*sum(d[k]*y**k for k in range(L+1))
    E4n = sp.Poly(sp.expand(P4.as_expr()-Den4*U4), y); E6n = sp.Poly(sp.expand(P6.as_expr()-Den6*U6), y)
    # divisibility
    E4q, E4r = sp.div(E4n, sp.Poly(y**(M+3), y)); E6q, E6r = sp.div(E6n, sp.Poly(y**(L+1), y))
    Yv = sp.Rational(1,1)/(N+Q4)**2
    K4 = abs(d[M+2]) + sum(abs(c)*Yv**k for (k,), c in E4q.terms())/Den4.subs(y,Yv)
    K6 = 4*abs(d[L+1]) + sum(abs(c)*Yv**k for (k,), c in E6q.terms())/Den6.subs(y,Yv)
    bound = (sp.Rational(8,9)*K4+sp.Rational(110,189)*K6)/((2*M+7)*(N-sp.Rational(3,4))**(2*M+7))
    q4N = sp.N(q4.subs(t,N), 45); q6N = sp.N(q6.subs(t,N), 45)
    return E4r.is_zero, E6r.is_zero, sp.N(K4,10), sp.N(K6,10), mpf(str(sp.N(bound,30))), mpf(str(q4N)), mpf(str(q6N))
from mpmath import binomial, pi, psi, nsum, inf
def a(n): return mpmath.exp(mpmath.loggamma(n+0.5)-mpmath.loggamma(n+1))/mpmath.sqrt(pi)
dl = lambda n: psi(1,n+0.5)-psi(1,n+1)
Wc = 8*nsum(lambda n: a(n)**4*dl(n),[1,inf],method='e') + 5*pi*nsum(lambda n:(4*n+1)*a(n)**6*dl(n),[1,inf],method='e')
print('Wc', Wc, ' W0-Wc-(8+5pi)pi^2/3', mpf('78.57031213654711716068274888671985244')-Wc-(8+5*pi)*pi**2/3)
for (N,M) in [(4,0),(6,1),(10,2),(20,2)]:
    r4, r6, K4, K6, bound, q4N, q6N = certificate(N,M)
    WNM = sum(a(n)**4*(8+5*pi*(4*n+1)*a(n)**2)*dl(n) for n in range(1,N)) + 8*a(N)**4*q4N + 5*pi*a(N)**6*q6N
    err = abs(Wc-WNM)
    print('N=%d M=%d'%(N,M), 'exact div', r4, r6, ' K4',K4,' K6',K6, ' |Wc-WNM|', mpmath.nstr(err,6), ' bound', mpmath.nstr(bound,6), ' ok', err<=bound)
