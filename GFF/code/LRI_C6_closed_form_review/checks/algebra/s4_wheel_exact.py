import sympy as sp
w = sp.exp(sp.I*sp.pi/4)
x = sp.Symbol('x')
p0 = [sp.Rational(1,2)]*4+[1,1,1]
v = [w**2, w, 1, 1-w+w**2, 1+w**2, w**2-w**3, 1+w**3]
def C(p):
    a,b,c,d,e,f,g = p
    return [g-c, a, b, g-d, 1+a+b-f, g, 1+a+b-e]
P = [p0[i]+x*v[i] for i in range(7)]
CP = C(P)
print('C(p0+xv) - (p0+omega x v):', [sp.simplify(sp.expand(CP[i]-(p0[i]+w*x*v[i]))) for i in range(7)])
# balance e+f+g-a-b-c-d
print('balance slope:', sp.simplify(v[4]+v[5]+v[6]-v[0]-v[1]-v[2]-v[3]))
a,b,c,d,e,f,g = v
alpha = d+g-e
varrho = sp.nsimplify(sp.simplify(sp.expand(1-w+w**3)))
print('varrho=', sp.simplify(alpha), ' simplified', sp.radsimp(sp.expand_complex(alpha)))
half = [alpha, g-a, g-b, g-c, d, d-e]
unit = [1+a+d-e-1, 1+b+d-e-1, 1+c+d-e-1, 1+g-e-1, g-1+1]  # slopes (constants drop)
unit = [a+d-e, b+d-e, c+d-e, g-e, g]
r = 1-w+w**3
print('half slopes sum/varrho', sp.simplify(sp.expand_complex(sum(half)/r)), ' squares/varrho^2', sp.simplify(sp.expand_complex(sum(h**2 for h in half)/r**2)))
print('unit slopes sum/varrho', sp.simplify(sp.expand_complex(sum(unit)/r)), ' squares', sp.simplify(sp.expand_complex(sum(u**2 for u in unit))))
print('f-d slope', sp.simplify(sp.expand_complex((f-d)/r)), ' alpha slope', sp.simplify(sp.expand_complex(alpha/r)))
# pointwise identity
n = sp.Symbol('n')
H1,H2,Hn1,Hn2,l = sp.symbols('H2n Hn H2n2 Hn2 ell')  # H_{2n},H_n,H^{(2)}_{2n},H^{(2)}_n
An = 4*H1-3*H2-2*l+1/(4*n+1); Rn = 4*Hn1-Hn2+2/(4*n+1)**2
Ln = 8*H1-6*H2-4*l+2/(4*n+1); Mn = 5*sp.pi**2/3-16*Hn1+6*Hn2-4/(4*n+1)**2
dn = sp.pi**2/3-4*Hn1+2*Hn2
print('pointwise identity:', sp.simplify(Ln**2+Mn-(sp.pi**2+2*dn)-4*(An**2-Rn/2)))
# elimination
Bs,T,S7,Vw,D6 = sp.symbols('Bs T S7 Vw D6')
lhs = Bs/2-16*T
lhs = lhs.subs(T, (sp.Rational(3,2)*Bs/sp.pi**2 - S7)*sp.pi**2/32)
print('elimination:', sp.simplify(lhs.subs(S7, sp.pi**2*Vw+2*D6).subs(Bs,2*sp.pi**4*Vw) - sp.pi**2*D6))
