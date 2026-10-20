"""The inherited primitive recurrence, with a newly derived a posteriori tail.

The tail proof uses ||A||_inf=4, ||C||_inf=10, log-degree<=2, rho<1/5.
It does not use the inherited asymptotic or Cauchy tail allowance.
"""
from fractions import Fraction as F
from math import comb,factorial
import sympy as sp
from dyadic import I,log,evaluate

def seed_expressions():
    L,A,Q,p=sp.symbols('L A Q pi');x=L-A;R=sp.Rational
    e=[1,0,0]
    a=[15*x*x-12*p*x-p*p,15*x-6*p,15]
    b=[(15*(x*x+6*x)-12*p*(x+3)-p*p)/8,
       (15*(x*x+8*x+6)-12*p*(x+4)-p*p)/16,(15*(x+7)-6*p)/8]
    pp=[p+6*x,3,0];qq=[(p+6*x+18)/8,(p+6*x+24)/16,R(3,8)]
    def kron(a,b):return [sp.sympify(x)*sp.sympify(y) for x in a for y in b]
    def add(a,b):return [x+y for x,y in zip(a,b)]
    U0=[Q*v for v in kron(a,e)]
    U1=[Q*v-16*p**4/Q*w for v,w in zip(add(kron(b,e),kron(a,[R(3,4),R(1,8),0])),kron(e,[1,R(1,2),R(1,4)]))]
    V0=[8*p*p*v for v in kron(pp,[1,R(1,4),0])]
    V1=[8*p*p*v for v in add(kron(qq,[1,R(1,4),0]),kron(pp,[1,R(1,2),R(1,16)]))]
    z00=U0
    z01=[4*u1-3*u0-2*sp.diff(u0,L) for u0,u1 in zip(U0,U1)]
    z10=[2*v for v in V0]
    z11=[8*v1-8*v0-4*sp.diff(v0,L) for v0,v1 in zip(V0,V1)]
    return [[[[sp.expand(v).coeff(L,j) for v in zz] for j in range(3)] for zz in pair]
            for pair in [(z00,z01),(z10,z11)]]

def exact_seed_checks(obj):
    A=sp.Matrix(obj['A_matrix']);C=sp.Matrix(obj['C_matrix']);seeds=seed_expressions();checks=[]
    assert max(sum(abs(v) for v in A.row(i)) for i in range(9))==4
    assert max(sum(abs(v) for v in C.row(i)) for i in range(9))==10
    for branch,lam in enumerate([sp.Rational(0),sp.Rational(1,2)]):
        for n in range(2):
            for j in range(3):
                z=sp.Matrix(seeds[branch][n][j]);zp=sp.Matrix(seeds[branch][n][j+1]) if j<2 else sp.zeros(9,1)
                rhs=C*sp.Matrix(seeds[branch][0][j]) if n==1 else sp.zeros(9,1)
                residual=((n+lam)*sp.eye(9)-A)*z+(j+1)*zp-rhs
                assert all(sp.expand(v)==0 for v in residual),(branch,n,j,residual)
                checks.append(f'Frobenius seed equation branch={lam}, n={n}, logdegree={j}')
    assert all(v==0 for n in range(2) for v in seeds[1][n][2])
    return checks

def compute(obj,env,N=240):
    if N<48:raise ValueError('the recurrence-only tail proof requires N>=48')
    Am=[[F(x) for x in row] for row in obj['A_matrix']]
    Cm=[[F(x) for x in row] for row in obj['C_matrix']]
    assert all(Am[i][j]==0 for i in range(9) for j in range(i))
    assert max(sum(map(abs,r)) for r in Am)==4
    assert max(sum(map(abs,r)) for r in Cm)==10
    seeds=seed_expressions()
    rho=3-2*I(2).sqrt();rootrho=I(2).sqrt()-1;lr=log(rho)
    assert 0<rho.lo and rho.hi<I(F(1,5)).lo and lr.absolute_upper()<2
    allstates=[];total=I(0);bounds=[]
    def matvec(M,v):return [sum((a*x for a,x in zip(row,v) if a),I(0)) for row in M]
    def solve(rhs,n,lam):
        ans=[I(0)]*9
        for i in range(8,-1,-1):
            ans[i]=(rhs[i]+sum((Am[i][k]*ans[k] for k in range(i+1,9) if Am[i][k]),I(0)))/(F(n)+lam-Am[i][i])
        return ans
    for br,lam in enumerate([F(0),F(1,2)]):
        st=[[[evaluate(str(v),env) for v in row] for row in zz] for zz in seeds[br]]
        for n in range(2,N):
            new=[[I(0)]*9 for _ in range(3)]
            for j in [2,1,0]:
                one=matvec(Cm,st[n-1][j]);two=matvec(Am,st[n-2][j])
                rhs=[one[i]+two[i]+(F(n-1)+lam)*st[n-2][j][i] for i in range(9)]
                if j<2:rhs=[rhs[i]+(j+1)*(st[n-2][j+1][i]-new[j+1][i]) for i in range(9)]
                new[j]=solve(rhs,n,lam)
            st.append(new)
        powrho=I(1)
        sigma=F(1,2) if br==0 else F(1)
        factor=rootrho if br==0 else rho
        part=I(0)
        for n in range(N):
            s=F(n)+sigma
            for j in range(3 if br==0 else 2):
                weight=sum((comb(j,r)*(-1)**r*factorial(r)*lr**(j-r)/s**(r+1) for r in range(j+1)),I(0))
                part+=st[n][j][0]*powrho*factor*weight
            powrho*=rho
        total+=4*part
        def scaled_norm(n):
            un=max(v.absolute_upper() for channel in st[n] for v in channel)
            return (I(un)*rho**n).upper()
        k=max(scaled_norm(N-1),F(1,4)*scaled_norm(N-2))
        bounds.append(k);allstates.append(st)
    # For n>=48, w_n <= a*w_(n-1)+b*w_(n-2), a/r+b/r^2<=1, r=1/4.
    # All |J_j|/rho^(n+sigma), summed over j, are <8/N for n>=N.
    err=(F(32,3*N)*(rootrho*bounds[0]+rho*bounds[1])).upper()
    return total.inflate(err),{'N':N,'integer_scaled_K':str(bounds[0]),'half_scaled_K':str(bounds[1]),
        'tail_bound':str(err),'finite_arithmetic_width':str(total.width()),
        'norm_A':4,'norm_C':10,'log_derivative_norm_bound':2,'geometric_majorant_ratio':'1/4',
        'tail_uses_inherited_bound':False}
