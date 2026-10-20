# Numerical checks (NOT proof steps) of the boundary-value table used in Lemmas 2 and 3
# of proof_v2.md, of the moment relations (N2) and of the two Stokes evaluations.
#   K(m) = (pi/2) 2F1(1/2,1/2;1;m), principal branch (cut [1,oo)).
#   phi(y) = y^(-1/2) (1-y)^(tau-1), u = phi K(y), v = phi K(1-y)   on D = C \ ((-oo,0] U [1,oo)).
import mpmath as mp

mp.mp.dps = 40
EPS = mp.mpf(10) ** -30          # distance to the cut used for the one-sided limits


def K(m):
    return mp.pi / 2 * mp.hyp2f1(0.5, 0.5, 1, m)


def phi(y, tau):
    return mp.power(y, -0.5) * mp.power(1 - y, tau - 1)


def u(y, tau):
    return phi(y, tau) * K(y)


def v(y, tau):
    return phi(y, tau) * K(1 - y)


def E(a, b):
    """Euler moment int_0^1 x^(a-1)(1-x)^(b-1) K(x) dx via N1."""
    return mp.pi / 2 * mp.beta(a, b) * mp.hyp3f2(0.5, 0.5, a, 1, a + b, 1)


def report(name, val):
    print(f"  {name:58s} {mp.nstr(abs(val), 3)}")


for tau in [mp.mpf(3) / 10, mp.mpf(3) / 5, mp.mpf(9) / 20]:
    s, c = mp.sin(mp.pi * tau), mp.cos(mp.pi * tau)
    print(f"tau = {mp.nstr(tau, 6)}")
    # --- boundary values of K across [1,oo)
    for x in [mp.mpf('1.3'), mp.mpf('4.7')]:
        for sgn in (+1, -1):
            lhs = K(x + sgn * 1j * EPS)
            rhs = x ** -0.5 * (K(1 / x) + sgn * 1j * K(1 - 1 / x))
            report(f"K(x{'+' if sgn > 0 else '-'}i0) - x^-1/2[K(1/x) +- i K(1-1/x)], x={x}", lhs - rhs)
    # --- edge values on (-oo,0)
    for x in [mp.mpf('-0.4'), mp.mpf('-3.2')]:
        p = abs(x) ** -0.5 * (1 - x) ** (tau - 1) * K(x)
        q = abs(x) ** -0.5 * (1 - x) ** (tau - 1.5) * K(1 / (1 - x))
        for sgn in (+1, -1):
            y = x + sgn * 1j * EPS
            report(f"u(x{'+' if sgn > 0 else '-'}i0) - (-+ i p), x={x}", u(y, tau) - (-sgn * 1j * p))
            report(f"v(x{'+' if sgn > 0 else '-'}i0) - (-p -+ i q), x={x}", v(y, tau) - (-p - sgn * 1j * q))
    # --- edge values on (1,oo)
    for x in [mp.mpf('1.6'), mp.mpf('7.5')]:
        r = x ** -1 * (x - 1) ** (tau - 1) * K(1 / x)
        ss = x ** -1 * (x - 1) ** (tau - 1) * K(1 - 1 / x)
        for sgn in (+1, -1):
            y = x + sgn * 1j * EPS
            ph = -mp.exp(-sgn * 1j * mp.pi * tau)
            report(f"u(x{'+' if sgn > 0 else '-'}i0) - (-e^(-+i pi tau)(r +- i s)), x={x}", u(y, tau) - ph * (r + sgn * 1j * ss))
            report(f"v(x{'+' if sgn > 0 else '-'}i0) - (-e^(-+i pi tau) s), x={x}", v(y, tau) - ph * ss)
    # --- the four edge integrals equal Euler moments
    I1, I2, I3 = E(0.5, tau), E(tau, 0.5), E(1 - tau, tau)
    I4, I5, I6 = E(tau, 1 - tau), E(0.5, 1 - tau), E(1 - tau, 0.5)
    P = mp.quad(lambda x: abs(x) ** -0.5 * (1 - x) ** (tau - 1) * K(x), [-mp.inf, -256, -16, -4, -1, -0.25, 0])
    Q = mp.quad(lambda x: abs(x) ** -0.5 * (1 - x) ** (tau - 1.5) * K(1 / (1 - x)), [-mp.inf, -256, -16, -4, -1, -0.25, 0])
    R = mp.quad(lambda x: x ** -1 * (x - 1) ** (tau - 1) * K(1 / x), [1, 1.25, 2, 4, 16, 256, mp.inf])
    S = mp.quad(lambda x: x ** -1 * (x - 1) ** (tau - 1) * K(1 - 1 / x), [1, 1.25, 2, 4, 16, 256, mp.inf])
    report("int_{-oo}^0 p - I5", P - I5)
    report("int_{-oo}^0 q - I6", Q - I6)
    report("int_1^oo r - I3", R - I3)
    report("int_1^oo s - I4", S - I4)
    # --- moment relations N2 at t = tau
    report("I1 - (c I3 + s I4)", I1 - (c * I3 + s * I4))
    report("I5 - (s I3 - c I4)", I5 - (s * I3 - c * I4))
    report("I2 - s I3", I2 - s * I3)
    report("I6 - s I4", I6 - s * I4)
    # --- Euler moments vs F
    F = lambda t: mp.hyp3f2(0.5, 0.5, t, 1, 1, 1)
    report("I3 - pi^2 F(1-tau)/(2s)", I3 - mp.pi ** 2 * F(1 - tau) / (2 * s))
    report("I4 - pi^2 F(tau)/(2s)", I4 - mp.pi ** 2 * F(tau) / (2 * s))
    # --- the Stokes evaluations
    X1 = I5 ** 2 + 2 * s * I1 * I4 - I4 ** 2       # U based at 0
    X2 = I4 ** 2 + 2 * I2 * I5 - I5 ** 2           # V based at 1
    X3 = I5 ** 2 + 2 * I1 * I6 - I4 ** 2           # U based at 1
    X4 = 2 * (s * I1 * I4 + I2 * I5)                # average = KLT form (N6)
    target = 4 * mp.pi ** -2 * 0 + s ** 2 * (I3 ** 2 + I4 ** 2)
    report("X1 - s^2(I3^2+I4^2)", X1 - target)
    report("X2 - s^2(I3^2+I4^2)", X2 - target)
    report("X3 - s^2(I3^2+I4^2)", X3 - target)
    report("X4/2 - s^2(I3^2+I4^2)", X4 / 2 - target)
    J = 4 / mp.pi ** 2 * X1
    report("(4/pi^2) X1 - pi^2 (F(tau)^2 + F(1-tau)^2)", J - mp.pi ** 2 * (F(tau) ** 2 + F(1 - tau) ** 2))
    print(f"  J_(2tau) = {mp.nstr(J, 30)}")
