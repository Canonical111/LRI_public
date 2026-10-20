import sympy as sp
t,tau=sp.symbols('t tau')
pi=sp.pi
D=sp.sin(pi*t)**2*sp.sin(pi*(t-sp.Rational(1,4)))**3*sp.sin(pi*(t-sp.Rational(3,4)+tau))
def R_func(k):
    phi=sp.exp(2*pi*sp.I*k*t)
    ts=sp.Rational(3,4)-tau
    r1=phi.subs(t,ts)/(pi*sp.sin(pi*ts)**2*sp.sin(pi*(ts-sp.Rational(1,4)))**3)
    f=t**2*phi/D
    r0=sp.diff(sp.series(f,t,0,2).removeO(),t).subs(t,0)
    return sp.simplify(r0+r1)
for k in (-2,-1,0,1,2):
    e=R_func(k)
    print(k, sp.nsimplify(sp.simplify(sp.series(e,tau,0,4).removeO())) )
