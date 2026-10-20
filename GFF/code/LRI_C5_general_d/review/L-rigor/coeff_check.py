#!/usr/bin/env python3
"""Review L-rigor: printed coefficients of Theorem 6 (my own transcription from L_general_d.tex) vs numerical
b-derivatives (mp.diff) of the b-dependent coefficient functions of eq:W4five (my own implementation)."""
import mpmath as mp
mp.mp.dps = 40
pi = mp.pi


def coef_funcs(d, b):
    q = mp.mpf(d) / 4
    x, y = b / 4, mp.mpf(d) / 2 - b / 4
    s, c = mp.sin(pi * b / 2), mp.cos(pi * b / 2)
    sig, g = b / 2, (mp.mpf(d) - b) / 2
    N = mp.gamma(2 * q) * mp.gamma(g) / mp.gamma(sig)
    phi = lambda z: mp.gamma(z + x) / mp.gamma(z + y)
    k0 = N * mp.sin(pi * x) ** 2 * phi(0) ** 2
    kh = N * mp.cos(pi * x) ** 2 * phi(mp.mpf(1) / 2) ** 2
    r0 = x * (1 - y) / (y * (1 - x))
    rh = (1 - 2 * y) / (1 - 2 * x)
    a_hx = -4 * pi ** 3 * c / s ** 3
    a_s0 = 2 * (1 + c) ** 2 * (1 + 2 * c) * k0 ** 4 / (pi * s ** 7)
    a_sh = -2 * (1 - c) ** 2 * (1 - 2 * c) * kh ** 4 / (pi * s ** 7)
    return dict(hx=a_hx, s0=a_s0, h1=a_s0 * 2 * r0 ** 4, s1=a_sh, hh=a_sh * 2 * rh ** 4)


def printed(d):
    q = mp.mpf(d) / 4
    S, C = mp.sin(pi * q), mp.cos(pi * q)
    G0 = mp.gamma(q / 2) / mp.gamma(3 * q / 2)
    Gh = mp.gamma((1 + q) / 2) / mp.gamma((1 + 3 * q) / 2)
    beta0 = mp.gamma(2 * q) ** 4 * G0 ** 8 * mp.tan(pi * q / 2) / (16 * pi * mp.cos(pi * q / 2) ** 2)
    betah = mp.gamma(2 * q) ** 4 * Gh ** 8 * mp.cot(pi * q / 2) / (16 * pi * mp.sin(pi * q / 2) ** 2)
    rho0 = (2 - 3 * q) / (3 * (2 - q))
    rhoh = (1 - 3 * q) / (1 - q)
    Lt0 = -4 * mp.digamma(q) + 2 * mp.digamma(q / 2) + 2 * mp.digamma(3 * q / 2) + pi * mp.cot(pi * q / 2) \
        - 3 * pi / 2 * mp.cot(pi * q)
    Lth = -4 * mp.digamma(q) + 2 * mp.digamma((1 + q) / 2) + 2 * mp.digamma((1 + 3 * q) / 2) - pi * mp.tan(pi * q / 2) \
        - 3 * pi / 2 * mp.cot(pi * q)
    nu0 = rho0 ** 4 / 2 * (4 / (3 * q) + 1 / (2 - q)) + rho0 ** 3 / (6 * (2 - q))
    nuh = (1 - 2 * q) * rhoh ** 3 / (1 - q) ** 2
    val = dict(hx=-4 * pi ** 3 * C / S ** 3, s0=(1 + 2 * C) * beta0, h1=(1 + 2 * C) * beta0 * 2 * rho0 ** 4,
               s1=(2 * C - 1) * betah, hh=(2 * C - 1) * betah * 2 * rhoh ** 4)
    der = dict(hx=2 * pi ** 4 * (1 + 2 * C ** 2) / S ** 4,
               s0=beta0 * ((1 + 2 * C) * Lt0 - pi * S),
               h1=beta0 * (((1 + 2 * C) * Lt0 - pi * S) * 2 * rho0 ** 4 + (1 + 2 * C) * 8 * nu0),
               s1=betah * ((2 * C - 1) * Lth - pi * S),
               hh=betah * (((2 * C - 1) * Lth - pi * S) * 2 * rhoh ** 4 + (2 * C - 1) * 8 * nuh))
    return val, der


if __name__ == '__main__':
  worst = 0
  for ds in ('0.55', '0.7', '1', '4/3', '1.7', '2', '2.6', '8/3', '3', '3.7', '3.95'):
      d = mp.mpf(mp.fraction(*map(int, ds.split('/')))) if '/' in ds else mp.mpf(ds)
      b0 = d / 2
      val, der = printed(d)
      cf0 = coef_funcs(d, b0)
      line = []
      for k in ('hx', 's0', 'h1', 's1', 'hh'):
          dn = mp.diff(lambda bb: coef_funcs(d, bb)[k], b0)
          ev = abs(cf0[k] - val[k]) / max(abs(cf0[k]), mp.mpf(1))
          ed = abs(dn - der[k]) / max(abs(dn), mp.mpf(1))
          worst = max(worst, ev, ed)
          line.append('%s:%s/%s' % (k, mp.nstr(ev, 2), mp.nstr(ed, 2)))
      print('d=%-5s' % ds, ' '.join(line))
  print('worst (value/derivative, relative or absolute if <1):', mp.nstr(worst, 3))
