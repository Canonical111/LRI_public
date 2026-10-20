"""gdk:Delta and gdk:JGamma: Laurent coefficients of Delta = J^Gamma_{2tau} - C^2 X^2 on a circle (80 digits)."""
import mpmath as mp
mp.mp.dps = 80
def coeffs(q, r=mp.mpf('0.05'), N=64):
    C = lambda t: mp.gamma(2*q)*mp.gamma(t)/mp.gamma(2*q-t)
    Xd = lambda t: (mp.gamma(q-t/2)/mp.gamma(q+t/2))**2
    JG = lambda t: C(t)**2*mp.gamma(q-t)**2/mp.gamma(q+t)**2 + C(t)/t*(mp.gamma(q-t)/mp.gamma(q+t) - mp.gamma(q-2*t)*mp.gamma(q+t)/(mp.gamma(q+2*t)*mp.gamma(q-t)))
    D = lambda t: JG(t) - C(t)**2*Xd(t)**2
    vals = [D(r*mp.expjpi(2*mp.mpf(j)/N)) for j in range(N)]
    return {k: mp.fsum(vals[j]*mp.expjpi(-2*mp.mpf(j)*k/N) for j in range(N))/(N*r**k) for k in range(-3, 4)}
for d in ['0.8', '1', '1.25', '2', '2.75', '3', '3.6']:
    q = mp.mpf(d)/4
    A = mp.psi(0,2*q)+mp.psi(0,1)-2*mp.psi(0,q); U = mp.psi(2,q)
    c = coeffs(q)
    print(d, 'tau^-3..0:', [mp.nstr(abs(c[k]), 3) for k in (-3,-2,-1,0)], ' [tau]-3U/2:', mp.nstr(abs(c[1]-1.5*U)/abs(U), 3),
          ' [tau^2]-AU:', mp.nstr(abs(c[2]-A*U)/abs(A*U), 3))
