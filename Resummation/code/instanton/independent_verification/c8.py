import sympy as sp
u,g,cA,b3,Ag=sp.symbols('u g calA b3 A_g',positive=True)
eps=-u
beta=-eps*g+3*g**2-6*cA*g**3+b3*g**4
gam=g-cA*g**2+sp.Symbol('c3')*g**3
# fixed point series g*=sum
c1,c2,c3=sp.symbols('c1:4')
gs=c1*u+c2*u**2+c3*u**3
eq=sp.expand(sp.series(beta.subs(g,gs),u,0,5).removeO())
sol=sp.solve([eq.coeff(u,k) for k in (2,3,4)],[c1,c2,c3],dict=True)
sol=[s for s in sol if s[c1]!=0][0]; gstar=gs.subs(sol)
print("g*(eps=-u) =",sp.simplify(gstar))
hstar=-gstar
ratio=sp.series((sp.diff(gam,g)/sp.diff(beta,g)).subs(g,gstar),u,0,2)
print("gamma'/beta' =",sp.simplify(ratio))
# Im Delta ∝ -(gam'/bet') * (Ag/h*)^3 exp(-Ag/h*)
pref=sp.series(-(sp.diff(gam,g)/sp.diff(beta,g)).subs(g,gstar)*u*(Ag/hstar)**3*u**3/(3*Ag)**3,u,0,2).removeO()
expo=sp.series(Ag/hstar,u,0,2).removeO()   # = 3Ag/u + 2 cA Ag + k1 u
print("A_g/h* =",sp.expand(expo))
k1=sp.expand(pref).coeff(u,1)-sp.expand(expo).coeff(u,1)
print("O(u) coeff:",sp.simplify(k1), " claim-diff:",sp.simplify(k1-(2*cA-Ag*(b3-12*cA**2)/9)))
num={cA:sp.pi+4*sp.log(2),Ag:3*sp.pi**2/sp.gamma(sp.Rational(1,4))**4}
num[b3]=6*sp.gamma(sp.Rational(1,4))**4/sp.pi+sp.Rational(87,4)*num[cA]**2-sp.Rational(3,4)*sp.pi**2-4*sp.pi
print("numeric:",sp.N(k1.subs(num)), " extra -3h/A_g and +2h/A_g pieces (u-coeff):",sp.N((-1/(3*Ag)).subs(num)))
