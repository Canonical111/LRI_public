"""Independent one-dimensional evaluation of P=[q] A_Q4(q).
It uses an exact angular hard-core integral, rather than Hepp sectors.
"""
import mpmath as m
m.mp.dps = 90
z2 = m.zeta(2)
c0 = -6-4*z2
upper = m.mpf(1)/3
lower = m.mpf('1e-30')

def H(eta):
    L = m.log((1-2*eta)/eta)
    z = eta/(1-eta)
    return ((2*L+1)/eta - 4*L/(1-eta) - 2*(1-eta)*L
            - 2-3*eta + 4*m.log(z)**2-4*z2+8*m.polylog(2,z))

def remainder_over_eta(eta):
    l = m.log(eta)
    return (H(eta)-(-2*l+1)/eta-4*l*l-6*l-c0)/eta

l=m.log(upper)
analytic = (1+2*l)/upper + m.mpf(4)/3*l**3+3*l*l+c0*l
finite = m.quad(remainder_over_eta,
                [lower,m.mpf('1e-8'),m.mpf('.001'),m.mpf('.05'),upper])
P=analytic+finite
print('P, independent 1D integral =',m.nstr(P,40))
print('The omitted interval [0,1e-30] has size O(1e-28); no rigorous bound is claimed.')
print('This evaluation does not assume the five-vertex period identity.')
