from mpmath import mp, mpf, quad, exp, sqrt, pi, inf, mpc, expj
mp.dps=20
# Z(g)=int dphi exp(-phi^2/2 - g phi^4/24), continue g=h e^{i th} by rotating phi=e^{-i th/4} x
def Z(h,th):
    w=expj(-th/4)
    return w*quad(lambda x: exp(-w**2*x**2/2 - h*x**4/24),[-inf,0,inf])
for h in [mpf('0.2'),mpf('0.1')]:
    z=Z(h,pi*(1-mpf('1e-12')))/sqrt(2*pi)
    print("h",h,"ImZ/Z0",z.imag,"pred -|l0|^-1/2 e^-S",-exp(-mpf(3)/(2*h))/sqrt(2), "ratio",z.imag/(-exp(-mpf(3)/(2*h))/sqrt(2)))
