#!/usr/bin/env python3
"""From a Y(b) Cauchy circle (zcircle.py) build S(b) = Horn function, its first two b-derivatives at 3/2, and Z3:
   W_3(3;b) = 6 pi^2 S(b)/sin^2(pi b/2) - pi^(11/2) Gamma((5-3b)/2) / [2 sin^3(pi b/2) Gamma((3-b)/2)^6 Gamma(b/2)^3]
   S(b)     = sum_{l,n>=0} (2l+1) [ (b/2)_{l+n} ((b-1)/2)_n / ((3/2)_{l+n} n!) ]^3 = Y(b) Gamma(3/2)^3/(Gamma(b/2)Gamma((b-1)/2))^3
   Z3       = (4 pi^2/3) S''(3/2) - (4G + pi^2/2) Gamma(1/4)^10/(16 pi^(7/2))
usage: derive.py circ.json [out.json]"""
import sys, json
import mpmath as mp
d = json.load(open(sys.argv[1]))
mp.mp.dps = d['dps']
a = [mp.mpmathify(s.replace(' ', '')) for s in d['taylor']]
Y0, Y1, Y2 = mp.re(a[0]), mp.re(a[1]), 2 * mp.re(a[2])
imag = max(abs(mp.im(x)) for x in a[:3])
q, h = mp.mpf(1) / 4, mp.mpf(3) / 4
phi = mp.gamma(mp.mpf(3) / 2) ** 3 / (mp.gamma(h) * mp.gamma(q)) ** 3
L1 = -mp.mpf(3) / 2 * (mp.digamma(h) + mp.digamma(q))
L2 = -mp.mpf(3) / 4 * (mp.psi(1, h) + mp.psi(1, q))
S0 = phi * Y0
S1 = phi * (Y1 + Y0 * L1)
S2 = phi * (Y2 + 2 * Y1 * L1 + Y0 * (L2 + L1 ** 2))
pi, G = mp.pi, mp.catalan
g = mp.gamma(q) ** 10 / (48 * pi ** mp.mpf(3.5))        # Gamma piece of Q3:  Q3 = 4 pi^2 H3(0) - g
Q3 = 4 * pi ** 2 * S0 - g
Z3 = 4 * pi ** 2 / 3 * S2 - 3 * g * (4 * G + pi ** 2 / 2)
chk1 = S1 - (3 * g / (4 * pi) - pi * S0)                  # W'(3/2) = 0
Q3ref = mp.mpf('5.01710256455385536959085484569018369956449159350050897829591891338076076609203484012550649')
Z3ref = mp.mpf('8.82092489306009248553686732817408087436490074')
print('max |Im| of Taylor coeffs', mp.nstr(imag, 3))
print('H3(0) = S(3/2) =', mp.nstr(S0, 60))
print("S'(3/2) check (W'=0):", mp.nstr(chk1, 3))
print("S''(3/2) =", mp.nstr(S2, 60))
print('Q3 - Q3(90-digit formula run):', mp.nstr(Q3 - Q3ref, 3))
print('Z3 =', mp.nstr(Z3, 80))
print('Z3 - spectral 43-digit value:', mp.nstr(Z3 - Z3ref, 3))
if len(sys.argv) > 2:
    json.dump(dict(src=sys.argv[1], dps=d['dps'], H30=str(S0), S1=str(S1), S2=str(S2), Q3=str(Q3), Z3=str(Z3),
                   check_W1=str(chk1), imag=str(imag)), open(sys.argv[2], 'w'), indent=1)
