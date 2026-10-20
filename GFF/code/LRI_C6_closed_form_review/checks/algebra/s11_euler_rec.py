from mpmath import mp, mpf, pi, log, sqrt, zeta, binomial, gamma, matrix, lu_solve, nstr
import time
mp.dps = 80
t0 = time.time()
ell = log(2)
# exact-ish harmonic accumulators
NMAX = 400
H1=[mpf(0)];H2=[mpf(0)];H3=[mpf(0)]
for k in range(1,2*NMAX+2):
    H1.append(H1[-1]+mpf(1)/k); H2.append(H2[-1]+mpf(1)/k**2); H3.append(H3[-1]+mpf(1)/k**3)
a=[mpf(1)]
for n in range(1,NMAX+1): a.append(a[-1]*(2*n-1)/(2*n))
def Fn(n):
    y = n+mpf(1)/4; h = ell+H1[n]-H1[2*n]; dl = pi**2/3-4*H2[2*n]+2*H2[n]
    u = 1-14*y*h; v = 196*y*h**2-28*h+7*y*(dl-pi**2)
    T = 80*pi**2*y-26*pi*u+11*v; K = 28*pi**2*y-10*pi*u+3*v
    return (98*H1[2*n]+74*ell-6*pi)*T-98*pi*K-98*(11*u-13*pi*y)*(pi**2/3+4*H2[2*n])-8624*y*(zeta(3)-H3[2*n])
b = [a[n]**7*Fn(n) for n in range(NMAX)]
def EN(N):
    s = mpf(0); cum = mpf(0)
    for n in range(N):
        cum += binomial(N,n); w = 1-cum/mpf(2)**N
        s += (-1)**n*w*b[n]
    return s
ref = EN(360)
print('E_360 =', nstr(ref,45), ' table M7 -15332.55419477457527697894653409303157')
for N in [10,20,40,60,80,100,150,200,250,300]:
    e = EN(N)-ref
    print('N',N,' err',nstr(e,5),' err*2^N',nstr(e*mpf(2)**N,6), ' allowance 2^(100-N)', nstr(mpf(2)**(100-N),3))
print('sum |b_n| n<400:', nstr(sum(abs(x) for x in b),8), ' b0', nstr(b[0],8), time.time()-t0)
# -------- Appendix A recurrence
mp.dps = 50
A = pi+4*ell; Q = gamma(mpf(1)/4)**4/pi
F = lambda s: mpf(s) if not isinstance(s,str) else mpf(s)
from fractions import Fraction as Fr
A0r = [[0,2,0,2,0,0,0,0,0],[0,Fr(1,2),1,0,2,0,0,0,0],[0,0,1,0,0,2,0,0,0],[0,0,0,0,2,0,1,0,0],[0,0,0,0,Fr(1,2),1,0,1,0],[0,0,0,0,0,1,0,0,1],[0,0,0,0,0,0,0,2,0],[0,0,0,0,0,0,0,Fr(1,2),1],[0,0,0,0,0,0,0,0,1]]
C0r = [[-1,-4,0,-4,0,0,0,0,0],[Fr(1,4),2,-2,0,-4,0,0,0,0],[0,Fr(1,2),5,0,0,-4,0,0,0],[Fr(1,4),0,0,1,-4,0,-2,0,0],[0,Fr(1,4),0,Fr(1,4),4,-2,0,-2,0],[0,0,Fr(1,4),0,Fr(1,2),7,0,0,-2],[0,0,0,Fr(1,2),0,0,3,-4,0],[0,0,0,0,Fr(1,2),0,Fr(1,4),6,-2],[0,0,0,0,0,Fr(1,2),0,Fr(1,2),9]]
print('||A0||inf', max(sum(abs(x) for x in r) for r in A0r), ' ||C0||inf', max(sum(abs(x) for x in r) for r in C0r))
A0 = [[mpf(x.numerator)/x.denominator if isinstance(x,Fr) else mpf(x) for x in r] for r in A0r]
C0 = [[mpf(x.numerator)/x.denominator if isinstance(x,Fr) else mpf(x) for x in r] for r in C0r]
# polynomials in L represented as coefficient lists [c0,c1,c2]; x = L - A
def P(*c): return list(c)+[mpf(0)]*(3-len(c))
def padd(p,q): return [p[i]+q[i] for i in range(3)]
def pscal(c,p): return [c*x for x in p]
def pmul(p,q):
    r=[mpf(0)]*5
    for i in range(3):
        for j in range(3): r[i+j]+=p[i]*q[j]
    assert all(abs(x)<mpf(10)**-40 for x in r[3:]); return r[:3]
X = P(-A, 1)   # x = L - A
one = P(1); pi_ = P(pi)
def lin(*terms):  # sum coeff*poly
    r = P(0)
    for c,p in terms: r = padd(r, pscal(c,p))
    return r
X2 = pmul(X,X)
avec = [lin((15,X2),(-12*pi,X),(-pi**2,one)), lin((15,X),(-6*pi,one)), P(15)]
bvec = [pscal(mpf(1)/8, lin((15,X2),(90,X),(-12*pi,X),(-36*pi,one),(-pi**2,one))),
        pscal(mpf(1)/16, lin((15,X2),(120,X),(90,one),(-12*pi,X),(-48*pi,one),(-pi**2,one))),
        pscal(mpf(1)/8, lin((15,X),(105,one),(-6*pi,one)))]
pvec = [lin((pi,one),(6,X)), P(3), P(0)]
qvec = [pscal(mpf(1)/8, lin((pi,one),(6,X),(18,one))), pscal(mpf(1)/16, lin((pi,one),(6,X),(24,one))), P(mpf(3)/8)]
def kron(u, w):  # u: list of polys (3), w: list of numbers (3) -> 9 polys
    return [pscal(w[k], u[i]) for i in range(3) for k in range(3)]
def kron_e(u_nums, w):  # e (numbers) outer, w polys
    return [pscal(u_nums[i], w[k]) if False else None for i in range(3) for k in range(3)]
e = [mpf(1),mpf(0),mpf(0)]
def vadd(U,V): return [padd(U[i],V[i]) for i in range(9)]
def vsc(c,U): return [pscal(c,U[i]) for i in range(9)]
def vder(U): return [[U[i][1], 2*U[i][2], mpf(0)] for i in range(9)]
U0 = vsc(Q, kron(avec, e))
eKr = [P(e[i]*w) for i in range(3) for w in [mpf(1),mpf(1)/2,mpf(1)/4]]
U1 = vadd(vsc(Q, vadd(kron(bvec,e), kron(avec,[mpf(3)/4,mpf(1)/8,mpf(0)]))), vsc(-16*pi**4/Q, eKr))
V0 = vsc(8*pi**2, kron(pvec,[mpf(1),mpf(1)/4,mpf(0)]))
V1 = vsc(8*pi**2, vadd(kron(qvec,[mpf(1),mpf(1)/4,mpf(0)]), kron(pvec,[mpf(1),mpf(1)/2,mpf(1)/16])))
def coeffs(U, j): return [U[i][j] for i in range(9)]
seed0 = [[coeffs(U0,j) for j in range(3)], [coeffs(vadd(vadd(vsc(4,U1),vsc(-3,U0)),vsc(-2,vder(U0))),j) for j in range(3)]]
seedh = [[coeffs(vsc(2,V0),j) for j in range(3)], [coeffs(vadd(vadd(vsc(8,V1),vsc(-8,V0)),vsc(-4,vder(V0))),j) for j in range(3)]]
print('half-branch degree-2 channel zero:', max(abs(x) for x in seedh[0][2]+seedh[1][2]))
def matvec(Mx, v): return [sum(Mx[i][k]*v[k] for k in range(9)) for i in range(9)]
def backsolve(lam_n, rhs):  # [(lam_n) I - A0] z = rhs, upper triangular
    z = [mpf(0)]*9
    for i in range(8,-1,-1):
        s = rhs[i] + sum(A0[i][k]*z[k] for k in range(i+1,9))
        z[i] = s/(lam_n - A0[i][i])
    return z
def run(lam, seeds, N):
    zs = [seeds[0], seeds[1]]
    for n in range(2, N+2):
        zn = [None,None,None]; z3 = [mpf(0)]*9
        for j in [2,1,0]:
            znext = z3 if j==2 else zn[j+1]
            zm2next = z3 if j==2 else zs[n-2][j+1]
            rhs = [matvec(C0, zs[n-1][j])[i] + ((n-1+lam)*zs[n-2][j][i] + matvec(A0, zs[n-2][j])[i]) + (j+1)*(zm2next[i]-znext[i]) for i in range(9)]
            zn[j] = backsolve(n+lam, rhs)
        zs.append(zn)
    return zs
rho = 3-2*sqrt(2)
def J(j, s):
    return rho**s*sum(binomial(j,r)*(-1)**r*gamma(r+1)*log(rho)**(j-r)/s**(r+1) for r in range(j+1))
Nn = 110
z0 = run(mpf(0), seed0, Nn); zh = run(mpf(1)/2, seedh, Nn)
def PaN(N):
    return 4*sum(sum(z0[n][j][0]*J(j, n+mpf(1)/2) for j in range(3)) + sum(zh[n][j][0]*J(j, n+1) for j in range(2)) for n in range(N))
Pref = mpf('334926.04524805183788322200124007778661')
for N in [10,20,40,48,60,80,100]:
    print('P_a,N', N, nstr(PaN(N),40), ' diff from table', nstr(PaN(N)-Pref,5))
def nrm(z): return max(abs(x) for j in range(3) for x in z[j])
for N in [48,60,80]:
    K0 = max(rho**(N-1)*nrm(z0[N-1]), rho**(N-2)*nrm(z0[N-2])/4); Kh = max(rho**(N-1)*nrm(zh[N-1]), rho**(N-2)*nrm(zh[N-2])/4)
    bound = 32/(3*mpf(N))*(sqrt(rho)*K0+rho*Kh)
    print('N',N,' tail bound', nstr(bound,5), ' actual |P_a - P_aN|', nstr(abs(PaN(N)-PaN(Nn)),5))
# check Neumann inequality empirically and the U_n decay
print('rho<1/5', rho<mpf(1)/5, ' |log rho|', -log(rho))
print('time', time.time()-t0)
