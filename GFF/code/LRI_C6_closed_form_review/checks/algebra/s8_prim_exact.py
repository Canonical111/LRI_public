import sympy as sp
I = sp.I
u,r,a,b = sp.symbols('u r a b', real=True)
def Nf(f,g,fs,gs):
    return sp.expand(g**2*gs**2+g**2*fs**2+f**2*gs**2-4*f*g*fs*gs-3*f**2*fs**2+4*I*(f*g*fs**2-f**2*fs*gs))
N1 = Nf(u, r-I*u, a-I*b, a+I*b)
N2 = Nf(a+I*b, a-I*b, u, r+I*u)
tgt = sp.expand(2*r*(a-b)*((a+b)*r-2*(a-b)*u))
print('row x<0: N - target =', sp.simplify(N1-tgt))
print('row x>1: N - target =', sp.simplify(N2-tgt))
# interior: express real numerator in P basis
f,F,fs,Fs = sp.symbols('f F fs Fs')  # F = f+g
g = F-f; gs = Fs-fs
real_num = sp.expand(g**2*gs**2+g**2*fs**2+f**2*gs**2-4*f*g*fs*gs-3*f**2*fs**2)
# write as sum c_ij P_i(x) P_j(1-x), P0=f^2,P1=fF,P2=F^2 ; P*_j similarly
c = sp.symbols('c0:9')
P = [f**2, f*F, F**2]; Ps = [fs**2, fs*Fs, Fs**2]
expr = sum(c[3*i+j]*P[i]*Ps[j] for i in range(3) for j in range(3))
sol = sp.solve(sp.Poly(sp.expand(expr-real_num), f,F,fs,Fs).coeffs(), c)
print('pointwise coefficient matrix c_ij (rows i for x, cols j for 1-x):')
M = sp.Matrix(3,3,lambda i,j: sol[c[3*i+j]]); sp.pprint(M)
Msym = (M+M.T)/2
print('symmetrized:'); sp.pprint(Msym)
# the claimed relation I22 - 4I12 + 4I02 - 4I00 = 0 corresponds to symmetric matrix:
Cl = sp.Matrix([[-4,0,2],[0,0,-2],[2,-2,1]])
print('ratio check (Msym vs claimed):', sp.simplify(Msym - Cl*sp.Rational(Msym[2,2],1)/Cl[2,2]))
# also imaginary part 4(fgf*^2 - f^2 f* g*) and the max log power near x=0: f~1, g~L, fs~L, gs~L
# primitive pairing algebra: P_a/pi^3 in g basis
H = sp.Matrix(3,3,lambda i,j: sp.Symbol('H%d%d'%(min(i,j)+1,max(i,j)+1)))
def pair(x,y):  # x,y coefficient vectors in g1,g2,g3
    return sp.expand((sp.Matrix(x).T*H*sp.Matrix(y))[0])
gh = [[1,0,0],[1,1,0],[2,2,2]]  # p_i/pi^i = gh_i/sqrt(pi) (times 1)
Iij = lambda i,j: pair(gh[i],gh[j])  # = pi * I_ij
Pa_over_pi3 = 60*(Iij(1,2)-Iij(0,2))+24*Iij(1,1)+56*Iij(0,0)
print('P_a/pi^3 =', sp.factor(Pa_over_pi3))
rel = Iij(2,2)-4*Iij(1,2)+4*Iij(0,2)-4*Iij(0,0)
print('relation in g basis =', sp.factor(rel))
# primitive-input substitution
print('15I22+24I11-4I00 - [60(I12-I02)+24I11+56I00] using relation:', sp.expand(15*Iij(2,2)+24*Iij(1,1)-4*Iij(0,0) - (60*(Iij(1,2)-Iij(0,2))+24*Iij(1,1)+56*Iij(0,0)) - 15*rel))
# matrices and cubic
lam = sp.Symbol('lam')
Mm = sp.Matrix([[10,sp.Rational(21,2),0],[sp.Rational(21,2),18,sp.Rational(15,2)],[0,sp.Rational(15,2),0]])
Nm = sp.Matrix([[0,0,1],[0,-1,0],[1,0,1]])
print('4det(M+lam N) =', sp.expand(4*(Mm+lam*Nm).det()))
cub = 4*lam**3-112*lam**2+909*lam-2250
print('real roots', [sp.N(x,20) for x in sp.real_roots(cub)])
