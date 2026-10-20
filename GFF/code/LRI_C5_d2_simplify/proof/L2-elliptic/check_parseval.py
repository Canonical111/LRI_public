# Checks of every ingredient of the Parseval/Landen proof of (L-a) and (L-b).  30 digits, < 1 min.
import mpmath as mp
mp.mp.dps = 30
pi, l = mp.pi, mp.log(2)
h = mp.mpf(1)/2
K = lambda k: mp.ellipk(k*k)            # modulus convention, valid for complex k off the cuts
kp = lambda k: mp.sqrt((1-k)*(1+k))
f = lambda k: mp.pi/(2*mp.agm(1, kp(k)))
g = lambda k: mp.pi/(2*mp.agm(1, k))
y1 = lambda z, x=h: mp.hyp2f1(x, x, 1, z)
y3 = lambda z, x=h: mp.hyp2f1(x, x, 2*x, 1-z)
c2 = lambda n, x=h: mp.rf(x, n)**2/mp.factorial(n)**2
ok = lambda name, v: print('%-60s %s' % (name, mp.nstr(v, 5)))

# (E) Euler: D y1 = -log(1-z) y1
for z in [mp.mpf('0.3'), mp.mpc('-0.4', '0.5')]:
    ok('Euler  D y1 + log(1-z) y1', mp.diff(lambda x: y1(z, x), h) + mp.log(1-z)*y1(z))
# (F) DLMF 15.8.10 at general x: G_x(z) = sum c_n(x)^2 [psi(n+x)-psi(n+1)] z^n = -(1/2) G(x)^2/G(2x) y3 - (1/2) log z y1
for x in [h, mp.mpf('0.37')]:
    for z in [mp.mpf('0.3'), mp.mpc('-0.2', '0.45')]:
        G = mp.nsum(lambda n: c2(int(n), x)*(mp.psi(0, n+x)-mp.psi(0, n+1))*z**n, [0, mp.inf])
        ok('Frobenius G_x  x=%s z=%s' % (mp.nstr(x, 3), mp.nstr(z, 3)),
           G + mp.gamma(x)**2/mp.gamma(2*x)*y3(z, x)/2 + mp.log(z)*y1(z, x)/2)
# (C) connection-formula limit: D y3 = (4 l - log(1-z)) y3 - pi y1
for z in [mp.mpf('0.3'), mp.mpc('0.2', '0.7'), mp.mpc('-0.5', '0.3')]:
    ok('D y3 formula z=%s' % mp.nstr(z, 3), mp.diff(lambda x: y3(z, x), h) - ((4*l - mp.log(1-z))*y3(z) - pi*y1(z)))
# (B1),(B2) boundary values on the unit circle, 0<theta<pi, phi=theta/4
for th in [mp.mpf('0.3'), mp.mpf('1.7'), mp.mpf('3.0')]:
    ph = th/4; z = mp.expj(th)
    ok('B1 y1(e^{i th}) th=%s' % th, y1(z) - mp.expj(-ph)*(g(mp.sin(ph)) + 1j*f(mp.sin(ph)))/pi)
    ok('B2 y3(e^{-i th}) th=%s' % th, y3(mp.conj(z)) - 2/pi*mp.expj(ph)*f(mp.sin(ph)))
# moments of the note
Q = lambda F: mp.quad(F, [0, mp.mpf(1)/2, 1])
M = Q(lambda k: f(k)**2); N = Q(lambda k: f(k)*g(k))
U0 = Q(lambda k: f(k)**2/kp(k)); V0 = Q(lambda k: f(k)*g(k)/kp(k))
U = Q(lambda k: f(k)**2*mp.log(k*kp(k))/kp(k)); V = Q(lambda k: f(k)*g(k)*mp.log(k*kp(k))/kp(k))
ok('U0-2N', U0-2*N); ok('V0-2M', V0-2*M); ok('U+piM+2lN', U+pi*M+2*l*N); ok('V+piN/2+2lM', V+pi*N/2+2*l*M)
a = 8*N/pi**3; b = 8*M/pi**3
# Parseval forms directly on the circle (theta in (0,pi), doubled real part)
Lh = lambda th: mp.log(2*mp.sin(th/2))
P11 = mp.quad(lambda th: abs(y1(mp.expj(th)))**2, [0, pi])/pi
P13 = mp.quad(lambda th: mp.re(y1(mp.expj(th))*y3(mp.expj(-th))), [0, pi])/pi
ok('P11 - a', P11 - a); ok('P13 - b', P13 - b)
Sy_circ = -mp.quad(lambda th: Lh(th)*abs(y1(mp.expj(th)))**2, [0, pi])/(2*pi)
Sxy_circ = mp.quad(lambda th: Lh(th)*mp.re(y1(mp.expj(th))*y3(mp.expj(-th))), [0, pi]) + pi**2/2*a
Sy70 = mp.mpf('0.321311538544619606853604164437241038370829048911')
Sxy70 = 4*mp.mpf('-0.07096629825322418433412296948435087373037822033') + mp.mpf('5.009759040984015386070483995287017465707352402263')
ok('Sy  circle - 70-digit', Sy_circ - Sy70); ok('Sxy circle - 70-digit', Sxy_circ - Sxy70)
ok('Sy  closed 2M/pi^2-4lN/pi^3', 2*M/pi**2 - 4*l*N/pi**3 - Sy70)
ok('Sxy closed 2N/pi+8lM/pi^2', 2*N/pi + 8*l*M/pi**2 - Sxy70)

# --- extra checks: note moments in the theta variable (k = sin phi), and the closed form of H
fT = lambda ph: mp.pi/(2*mp.agm(1, mp.cos(ph)))   # K(sin phi)
gT = lambda ph: mp.pi/(2*mp.agm(1, mp.sin(ph)))   # K(cos phi)
QT = lambda F: mp.quad(F, [0, pi/4, pi/2])
U0t = QT(lambda ph: fT(ph)**2); V0t = QT(lambda ph: fT(ph)*gT(ph))
Ut = QT(lambda ph: fT(ph)**2*mp.log(mp.sin(ph)*mp.cos(ph))); Vt = QT(lambda ph: fT(ph)*gT(ph)*mp.log(mp.sin(ph)*mp.cos(ph)))
ok('theta: U0-2N', U0t-2*N); ok('theta: V0-2M', V0t-2*M); ok('theta: U+piM+2lN', Ut+pi*M+2*l*N); ok('theta: V+piN/2+2lM', Vt+pi*N/2+2*l*M)
# H(z) = sum c_n^2 {2[psi(n+1/2)-psi(1/2)][psi(n+1/2)-psi(n+1)] + psi_1(n+1/2)} z^n
for z in [mp.mpf('0.4'), mp.mpc('-0.3', '0.5')]:
    Hs = mp.nsum(lambda n: c2(int(n))*(2*(mp.psi(0, n+h)-mp.psi(0, h))*(mp.psi(0, n+h)-mp.psi(0, n+1)) + mp.psi(1, n+h))*z**n, [0, mp.inf])
    Hc = pi/2*mp.log(1-z)*y3(z) + pi**2/2*y1(z) + mp.log(z)*mp.log(1-z)*y1(z)/2
    ok('H closed form z=%s' % mp.nstr(z, 3), Hs - Hc)
# reciprocal-modulus boundary value used for (N5): y1(s+i0) = s^{-1/2}[y1(1/s) + i y1(1-1/s)], s>1
for s_ in [mp.mpf('1.3'), mp.mpf('4.0')]:
    up = mp.hyp2f1(h, h, 1, s_ + mp.mpc(0, mp.mpf(10)**-25))
    ok('reciprocal-modulus y1(s+i0) s=%s' % s_, up - (y1(1/s_) + 1j*y1(1-1/s_))/mp.sqrt(s_))
# direction of approach in the Landen argument: Im 4w/(1+w)^2 > 0 for w = r e^{2 i phi}, r<1
for ph in [mp.mpf('0.2'), mp.mpf('0.7')]:
    w = mp.mpf('0.999')*mp.expj(2*ph)
    print('Im 4w/(1+w)^2 at phi=%s: %s (positive expected)' % (ph, mp.nstr(mp.im(4*w/(1+w)**2), 5)))
