"""Endpoint-subtracted original Kappa integral, from the preceding revision.
Only the numerical evaluator is retained; proof status is in the new note.
"""
import mpmath as m

def elliptic_star(x):
    A=m.pi+4*m.log(2); lx=m.log(x); f0=2*(A-lx)
    if x<m.mpf('.125'):
        a=xp=m.mpf(1); h=h2=rem=m.mpf(0)
        for n in range(1,3*m.mp.dps+100):
            a*=((m.mpf(n)-m.mpf('.5'))/n)**2; xp*=x
            h+=m.mpf(1)/n; h2+=m.mpf(1)/(2*n-1)+m.mpf(1)/(2*n)
            term=2*a*xp*(A-lx+4*(h-h2)); rem+=term
            if abs(term)<m.eps*max(1,abs(rem))/100: return f0+rem,rem
        raise ArithmeticError('Endpoint series did not converge.')
    f=4*(m.ellipk(x)+m.ellipk(1-x)); return f,f-f0

def integrand(u):
    if not u: return m.mpf(0)
    x=u*u/2; lx=m.log(x); ly=m.log1p(-x); r=m.sqrt(x); c=m.sqrt(1-x)
    F,rem=elliptic_star(x)
    edge=(2*rem*lx**2+F*(x/(c*(1+c))*lx**2-2*lx*ly+ly**2))/(2*x)
    regular=F/2*(ly**2/(r*(1-x))+(ly-lx)**2/(1-x)+ly**2/r+lx**2/c)
    return u*(edge+regular)

def integral_kappa():
    l=m.log(2); A=m.pi+4*l
    # Breakpoints and small-x threshold differ from the supplied evaluator.
    I=m.quad(integrand,[0,m.mpf('.0625'),m.mpf('.25'),m.mpf('.75'),1])
    j2=I-m.mpf(2)/3*A*l**3-l**4/2
    g2=A**4/6-A*A*m.pi**2/6-A*m.pi**3/3-12*A*m.zeta(3)-m.pi**4/180
    return j2-g2,I,j2,g2

