"""Exact two-dimensional reduction of the six-kink angular current integral."""
import sympy as s
x,z,t,y,w=s.symbols('x z t y w', real=True)
f=(1-t)**2/(t**2*(t-x)**2*(t-z)**2)
D={};C={}
for j in range(4):
    D[j,0]=1/(x*x*z*z) if j==0 else s.S(0)
    C[j,0]=(-2+2/x+2/z)/(x*x*z*z) if j==0 else (1/(x*x*z*z) if j==1 else s.S(0))
    for r,other in [(x,z),(z,x)]:
        D[j,r]=r**(j-2)*(1-r)**2/(r-other)**2
        C[j,r]=D[j,r]*((j-2)/r-2/(1-r)-2/(r-other))
    recon=sum(C[j,r]/(t-r)+D[j,r]/(t-r)**2 for r in [0,x,z])
    assert s.cancel(t**j*f-recon)==0
print('All four rational-moment decompositions: EXACT PASS')
q=s.expand((w-y)**2*(1-x-z+y+w))
check=w**3+y**3-w*w*y-w*y*y+(1-x-z)*(w*w+y*y-2*w*y)
assert s.expand(q-check)==0
pref=x*x*z*z*(z-x)**2/((1-x)**2*(1-z)**2)
X=[0,y,x,w,z,1]
W=s.prod((X[j]-X[i])**(2*(-1)**(i+j)) for i in range(6) for j in range(i+1,6))
Dip=y+w+1-x-z
assert s.cancel(Dip*W-pref*f.subs(t,y)*f.subs(t,w)*q)==0
print('Six-vertex factorization with dipole: EXACT PASS')
# Matrix form of the polynomial coupling.
Q=s.zeros(4)
for (j,k),c in s.Poly(q,y,w).terms():Q[j,k]=c
assert s.expand((s.Matrix([[y**j for j in range(4)]])*Q*s.Matrix([w**k for k in range(4)]))[0]-q)==0
print('Bilinear moment matrix: EXACT PASS')
if __name__=='__main__':
 print('Moment coupling matrix:',Q)
