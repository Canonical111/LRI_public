#!/usr/bin/env python3
"""First-order jets (dual numbers) over mpmath, for exact parameter derivatives of the accelerated
hypergeometric sums (session L, LRI_C5_general_d/L).

A jet J(v, d) represents v + d*eps with eps^2 = 0.  Every operation used by hypsums_jet.py is overloaded, so
running the series code with the rim exponent b = J(b0, 1) returns J(F(b0), F'(b0)) for each sum F: the
derivative is the exact derivative of the evaluated expression (finite part + truncated asymptotic tail),
i.e. the polygamma-weighted series with its tail accelerated in the same way.  It is not a finite difference.
"""
import mpmath as mp


class J:
    __slots__ = ('v', 'd')

    def __init__(self, v, d=0):
        # always store mpmath numbers: a Python int/float seed (e.g. d=1) would otherwise turn
        # d/3 into a double-precision float
        self.v = v if isinstance(v, (mp.mpf, mp.mpc)) else mp.mpmathify(v)
        self.d = d if isinstance(d, (mp.mpf, mp.mpc)) else mp.mpmathify(d)

    # ---------------------------------------------------------------- arithmetic
    def __add__(self, o):
        if isinstance(o, J):
            return J(self.v + o.v, self.d + o.d)
        return J(self.v + o, self.d)

    __radd__ = __add__

    def __sub__(self, o):
        if isinstance(o, J):
            return J(self.v - o.v, self.d - o.d)
        return J(self.v - o, self.d)

    def __rsub__(self, o):
        return J(o - self.v, -self.d)

    def __neg__(self):
        return J(-self.v, -self.d)

    def __pos__(self):
        return J(+self.v, +self.d)

    def __mul__(self, o):
        if isinstance(o, J):
            return J(self.v * o.v, self.v * o.d + self.d * o.v)
        return J(self.v * o, self.d * o)

    __rmul__ = __mul__

    def __truediv__(self, o):
        if isinstance(o, J):
            iv = 1 / o.v
            return J(self.v * iv, (self.d - self.v * o.d * iv) * iv)
        return J(self.v / o, self.d / o)

    def __rtruediv__(self, o):
        iv = 1 / self.v
        return J(o * iv, -o * self.d * iv * iv)

    def __pow__(self, n):
        if isinstance(n, int):
            if n == 0:
                return J(mp.mpf(1) if not isinstance(self.v, mp.mpc) else mp.mpc(1), 0)
            p = self.v ** (n - 1)
            return J(p * self.v, n * p * self.d)
        return jexp(n * jlog(self))

    def __rpow__(self, base):
        return jpow(base, self)

    # ---------------------------------------------------------------- comparisons used by the series code
    def __eq__(self, o):
        if isinstance(o, J):
            return self.v == o.v and self.d == o.d
        return self.v == o and self.d == 0

    def __ne__(self, o):
        return not self.__eq__(o)

    __hash__ = None

    def __abs__(self):
        return abs(self.v)

    def __repr__(self):
        return 'J(%s, %s)' % (mp.nstr(self.v, 15), mp.nstr(self.d, 15))


def isjet(x):
    return isinstance(x, J)


def val(x):
    return x.v if isinstance(x, J) else x


def der(x):
    return x.d if isinstance(x, J) else 0


def cnum(x):
    """complex mpmath number, jets left untouched"""
    return x if isinstance(x, J) else mp.mpc(x)


def num(x):
    return x if isinstance(x, J) else mp.mpmathify(x)


def jsum(xs):
    xs = list(xs)
    if not any(isinstance(x, J) for x in xs):
        return mp.fsum(xs)
    return J(mp.fsum(val(x) for x in xs), mp.fsum(der(x) for x in xs))


def jexp(x):
    if isinstance(x, J):
        e = mp.exp(x.v)
        return J(e, e * x.d)
    return mp.exp(x)


def jlog(x):
    if isinstance(x, J):
        return J(mp.log(x.v), x.d / x.v)
    return mp.log(x)


def jpow(base, e):
    """base**e for jets or numbers (principal branch)."""
    if not isinstance(base, J) and not isinstance(e, J):
        return mp.power(base, e)
    if isinstance(e, int) and isinstance(base, J):
        return base ** e
    if not isinstance(base, J):           # constant base, jet exponent
        p = mp.power(base, e.v)
        return J(p, p * mp.log(base) * e.d)
    if not isinstance(e, J):              # jet base, constant exponent
        p = mp.power(base.v, e - 1)
        return J(p * base.v, e * p * base.d)
    return jexp(e * jlog(base))


def jgamma(x):
    if isinstance(x, J):
        g = mp.gamma(x.v)
        return J(g, g * mp.psi(0, x.v) * x.d)
    return mp.gamma(x)


def jrgamma(x):
    if isinstance(x, J):
        r = mp.rgamma(x.v)
        if r == 0:   # 1/Gamma at a nonpositive integer -n: derivative (-1)^n n!
            n = int(mp.nint(-mp.re(x.v)))
            return J(r, (-1) ** n * mp.factorial(n) * x.d)
        return J(r, -r * mp.psi(0, x.v) * x.d)
    return mp.rgamma(x)


def jpsi(x):
    if isinstance(x, J):
        return J(mp.psi(0, x.v), mp.psi(1, x.v) * x.d)
    return mp.psi(0, x)


def jsin(x):
    if isinstance(x, J):
        return J(mp.sin(x.v), mp.cos(x.v) * x.d)
    return mp.sin(x)


def jcos(x):
    if isinstance(x, J):
        return J(mp.cos(x.v), -mp.sin(x.v) * x.d)
    return mp.cos(x)


def jsinpi(x):
    if isinstance(x, J):
        return J(mp.sinpi(x.v), mp.pi * mp.cospi(x.v) * x.d)
    return mp.sinpi(x)


def jcospi(x):
    if isinstance(x, J):
        return J(mp.cospi(x.v), -mp.pi * mp.sinpi(x.v) * x.d)
    return mp.cospi(x)


def jbernpoly(n, x):
    if isinstance(x, J):
        if n == 0:
            return J(mp.mpf(1), 0)
        return J(mp.bernpoly(n, x.v), n * mp.bernpoly(n - 1, x.v) * x.d)
    return mp.bernpoly(n, x)


def jre(x):
    if isinstance(x, J):
        return J(mp.re(x.v), mp.re(x.d))
    return mp.re(x)


def jnstr(x, n=20):
    if isinstance(x, J):
        return '(%s ; d=%s)' % (mp.nstr(x.v, n), mp.nstr(x.d, n))
    return mp.nstr(x, n)
