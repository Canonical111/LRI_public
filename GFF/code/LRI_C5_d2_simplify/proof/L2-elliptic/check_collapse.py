# (1) both collapse forms against the 70-digit L2; (2) the general-x two-mode theorem at x != 1/2.
import mpmath as mp
mp.mp.dps = 70
pi, l = mp.pi, mp.log(2)
a = mp.mpf('1.118636387164187068349619257525640916794857551529361191480618646924046')
b = mp.mpf('0.9027285783238348241903933987727629850304635036014195522559185553239932')
Sy = mp.mpf('0.321311538544619606853604164437241038370829048911')            # 48 digits stored
Sxy = 4*mp.mpf('-0.07096629825322418433412296948435087373037822033') + mp.mpf('5.009759040984015386070483995287017465707352402263')
L2 = mp.mpf('-347.2491531232011310584767830752231692081676019948742708342016243405788')
mine = 2*pi**4*a**2 - 4*pi**4*b**2 + 16*pi**3*b*Sy - 8*pi**2*a*Sxy
finder = 3*pi**4*a**2 - 2*pi**4*b**2 + 8*pi**3*b*Sy - 12*pi**2*a*Sxy
print('mine   - L2 :', mp.nstr(mine - L2, 5))
print('finder - L2 :', mp.nstr(finder - L2, 5))
print('-16 pi^3 a b log2 - L2 :', mp.nstr(-16*pi**3*a*b*l - L2, 5))

# (2) two-mode theorem at general x:  sin^4(pi(u+x)) Phi(u;x) + sin^4(pi u) Phi(1-x-u;x) = A + B cos(2 pi u + pi x)
mp.mp.dps = 20
def Phi(u, x):
    return mp.nsum(lambda k: (mp.gamma(k+u+x)/mp.gamma(k+u+1))**4, [0, mp.inf], method='e')
def Omega(u, x):
    return mp.sin(pi*(u+x))**4*Phi(u, x) + mp.sin(pi*u)**4*Phi(1-x-u, x)
for x in [mp.mpf('0.45'), mp.mpf('0.3')]:
    # fit A,B from two points, test at a third and a complex point
    u1, u2 = mp.mpf('0.11'), mp.mpf('0.27')
    O1, O2 = Omega(u1, x), Omega(u2, x)
    c1, c2 = mp.cos(2*pi*u1 + pi*x), mp.cos(2*pi*u2 + pi*x)
    B = (O1 - O2)/(c1 - c2); A = O1 - B*c1
    for u3 in [mp.mpf('0.63'), mp.mpc('0.2', '0.3')]:
        print('x=%s u=%s  two-mode residual %s' % (x, u3, mp.nstr(Omega(u3, x) - (A + B*mp.cos(2*pi*u3 + pi*x)), 5)))
    # and A,B from the t=0 single sums
    P11 = mp.nsum(lambda n: (mp.rf(x, n)/mp.factorial(n))**4, [0, mp.inf], method='e')
    S1 = mp.nsum(lambda n: (mp.rf(x, n)/mp.factorial(n))**4*(mp.psi(0, n+x) - mp.psi(0, n+1)), [0, mp.inf], method='e')
    s, c = mp.sin(pi*x), mp.cos(pi*x)
    Bs = -(4*pi*s**3*c*mp.gamma(x)**4*P11 + 4*s**4*mp.gamma(x)**4*S1)/(2*pi*s)
    As = s**4*mp.gamma(x)**4*P11 - Bs*c
    print('   A,B from single sums vs fit:', mp.nstr(As - A, 5), mp.nstr(Bs - B, 5))
