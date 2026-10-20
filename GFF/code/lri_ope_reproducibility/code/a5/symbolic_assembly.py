import sympy as s
import json
A,R,M,N,U,V,T,P=s.symbols('A R M N U V T P')
e=s.symbols('e')
b3=T+s.Rational(87,4)*A**2-s.Rational(9,4)*R+M
b4=-s.Rational(393,4)*A**3-s.Rational(11,2)*A*M-9*A*T+s.Rational(117,4)*A*R-s.Rational(3,2)*M*N-6*P-s.Rational(165,8)*U+s.Rational(9,4)*V
g=e/3+2*A*e**2/9+(8*A**2/27-b3/81)*e**3+(40*A**3/81-(10*A*b3+b4)/243)*e**4
h=4/e+R*e-V*e**2/2
s40=A**2/8+3*R+M/9
s41=M*(A+N)/18+A*R+U/8-9*V/4
s51=b3/9+s.Rational(3,2)*A**2+s.Rational(45,2)*R+s.Rational(4,3)*M
s50=s.Rational(7,8)*A**3+M*(A+N)+s.Rational(145,8)*A*R+s.Rational(43,16)*U-s.Rational(181,8)*V
S4=s.Rational(9,2)/e**2+A/e+s40+s41*e
S5=18/e**3+11*A/e**2+s51/e+s50
# Independent formal derivatives of the outer convolution master, normalized by J0.
j={}
for n in range(4):
 for k in range(n+1):j[k,n-k]=s.symbols(f'j{k}{n-k}') if n else s.Integer(1)
def J(n):
 return sum((-e/4)**k/s.factorial(k)*sum(s.binomial(k,r)*(2*n-1)**r*j[k-r,r] for r in range(k+1)) for k in range(4))
f2=J(2)/6
f3=J(2)/e-h*J(3)/4
f4=(s.Rational(9,2)/e**2-A/e)*J(2)-9*h*J(3)/(4*e)+S4*J(4)
f5=(18/e**3-10*A/e**2+b3/(9*e))*J(2)+(-s.Rational(27,2)/e**2+9*A/(4*e))*h*J(3)+12*S4*J(4)/e-S5*J(5)
def cf(expr,k):return s.expand(expr).coeff(e,k)
# Use only the finite pieces required by the order being assembled.
result=0
for n,f in ((2,f2),(3,f3),(4,f4),(5,f5)):
 gp=s.Poly(g,e)**n
 for k in range(6-n):result+=cf(f,k)*gp.coeff_monomial(e**(5-k))
result=s.expand(54*result)
pure=s.expand(result.subs({v:0 for key,v in j.items() if key!=(0,0)}))
print('pure c3 =',pure)
print('FULL /a2 =',s.collect(result,list(j.values())[1:]))
c1=4*A/3;c2=s.Rational(25,36)*A**2+R/6-2*T/27
expected=pure-c2*(j[1,0]-j[0,1])/4+c1*(j[2,0]-2*j[1,1]+j[0,2])/32-(j[3,0]-3*j[2,1]+3*j[1,2]-j[0,3])/384
print('factorization remainder',s.expand(result-expected))
assert s.expand(result-expected)==0
B,S,D2=s.symbols('B S D2')
final=s.expand(pure-B*c2/4+(B**2+S)*c1/32-(B**3+3*B*S+D2)/384)
print('FINAL',final)
# Eliminate the primitive four-wheel using C4 from the uploaded note.
C4=s.symbols('C4')
PfromC4=(648*C4+A**3+s.Rational(4,3)*A*T+3*A*R-s.Rational(53,2)*U+3*V)/16
alternative=s.expand(final.subs(P,PfromC4))
print('C4 VERSION',alternative)
json.dump({'scalar_c3':str(pure),'a5_over_a2':str(final),'C4_version':str(alternative),'outer_derivative_factorization_verified':True},open('symbolic_a5.json','w'),indent=2)
