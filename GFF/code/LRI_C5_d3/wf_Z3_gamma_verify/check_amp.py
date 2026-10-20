"""Adversarial check of a3(b) b3(b) = pi^5 Gamma(1-3beta)/Gamma(1-beta)^9, beta=(b-1)/2.
a3 = Psi30(u)/cos(pi u), b3 = Psi31(u)/sin(pi u), Psi_{3,m}(u) = sin^3(pi(u+c)) U_m(u) + (-1)^m sin^3(pi(c-u)) U_m(1-u),
U_m(u) = sum_n (n+u)^m [Gamma(n+u+c)/Gamma(n+u+1-c)]^3,  c=(b-1)/4.
Two independent evaluators for U: (i) mpmath hyper literal pFq(1), (ii) zb.gamma_moment (author's Euler-Maclaurin tail)."""
import sys, mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_d3/wf_Z3')
import zb
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 30

def U_lit(m, u, c):
    u = mp.mpc(u)
    pre = u**m * (mp.gamma(u+c)/mp.gamma(u+1-c))**3
    return pre * mp.hyper([1]+[u+c]*3+[u+1]*m, [u+1-c]*3+[u]*m, 1)

def U_em(m, u, c):
    return zb.gamma_moment(u+c, u+1-c, 3, u, m, 120, 48)

def Psi(m, u, c, U):
    s1 = mp.sin(mp.pi*(u+c))**3
    s2 = (-1)**m * mp.sin(mp.pi*(c-u))**3
    return s1*U(m, u, c) + (s2*U(m, 1-u, c) if abs(s2) > mp.eps**0.75 else 0)

def closed(b):
    be = (mp.mpc(b)-1)/2
    return mp.pi**5*mp.gamma(1-3*be)/mp.gamma(1-be)**9

def closed_sin(b):
    be = (mp.mpc(b)-1)/2
    return mp.sin(mp.pi*be)**5*mp.gamma(be)**5*mp.gamma(1-3*be)/mp.gamma(1-be)**4

for b in [mp.mpf('1.1'), mp.mpf('1.25'), mp.mpf('1.4'), mp.mpf(3)/2, mp.mpf('1.6'), mp.mpc('1.3','0.2')]:
    c = (b-1)/4
    rows = []
    for U, name in [(U_em, 'EM'), (U_lit, 'hyper')]:
        if name == 'hyper' and (mp.mp.dps > 40 or mp.re(b) > 1.55): continue
        a3s = [Psi(0, u, c, U)/mp.cos(mp.pi*u) for u in [c, mp.mpf('0.31'), mp.mpf('0.17')]]
        b3s = [Psi(1, u, c, U)/mp.sin(mp.pi*u) for u in [c, mp.mpf('0.31'), mp.mpf('0.17')]]
        prod = a3s[0]*b3s[0]
        rows.append((name, prod, max(abs(x/a3s[0]-1) for x in a3s), max(abs(x/b3s[0]-1) for x in b3s)))
    A3, B3 = zb.a3b3(b)
    cf = closed(b)
    print('b =', mp.nstr(b, 6))
    for name, prod, da, db in rows:
        print('  %-5s prod=%s  rel(prod/closed-1)=%s  u-indep a3 %s b3 %s' % (name, mp.nstr(prod, 20), mp.nstr(abs(prod/cf-1), 3), mp.nstr(da, 3), mp.nstr(db, 3)))
    print('  zb.a3b3 vs closed:', mp.nstr(abs(A3*B3/cf-1), 3), ' sin-form vs closed:', mp.nstr(abs(closed_sin(b)/cf-1), 3))
print('b=3/2 vs td:gammaAmplitudes:', mp.nstr(abs(closed(mp.mpf(3)/2)/(mp.gamma(0.25)**10/(16*mp.sqrt(2)*mp.pi**4))-1), 3))
print('c0 form check:', mp.nstr(abs(closed(mp.mpf('1.37')) - mp.pi**5*mp.gamma((5-3*mp.mpf('1.37'))/2)/mp.gamma((3-mp.mpf('1.37'))/2)**9), 3))
