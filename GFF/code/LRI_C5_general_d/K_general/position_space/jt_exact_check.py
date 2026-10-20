"""30-digit check of J_t (MB, pole split) against the exact finite-t closed forms at d=2 (gc:K2master) and d=1 (eq:Jhat)."""
import mpmath as mp
from mixed_trace_check import J_full
mp.mp.dps = 40
# d = 2, tau = 3/10: note value 47.790785413226103671 (pi^2 [F(tau)^2 + F(1-tau)^2]); recompute F by mpmath nsum with Richardson
def F(tau):
    return mp.hyp3f2(mp.mpf(1) / 2, mp.mpf(1) / 2, tau, 1, 1, 1, maxterms=10**6)
try:
    ex2 = mp.pi ** 2 * (F(mp.mpf('0.3')) ** 2 + F(mp.mpf('0.7')) ** 2)
except Exception as e:
    ex2 = mp.mpf('47.790785413226103671'); print('  (using the note value for d=2:', e, ')')
v2, N = J_full('2', mp.mpf('0.6'), 30, -0.35, -0.07)
print('d=2 t=0.6 : J_MB = %s   exact = %s   diff = %s' % (mp.nstr(v2.real, 28), mp.nstr(ex2, 28), mp.nstr(abs(v2 - ex2), 3)))
# d = 1, t = 3/10 : J_t = Jhat(t)/t^2 (eq:Jhat)
t = mp.mpf('0.3'); G = mp.gamma; h = mp.mpf(1) / 2
f = [mp.hyp3f2(t, t, h, h + t, h + t, 1), mp.hyp3f2(t, t, t, h + t, h + t, 1), mp.hyp3f2(h, h, t, 1, h + t, 1),
     mp.hyp3f2(h, h, t, 1, 1, 1), mp.hyp3f2(h, h, h, 1, 1.5 - t, 1), mp.hyp3f2(h, h, 1 - t, 1, 1.5 - t, 1)]
Jh = 2 * mp.pi * (G(1 + t) ** 2 / G(h + t) ** 2 * (f[0] + f[1]) + t * mp.sqrt(mp.pi) * G(1 + t) / G(h + t) * f[2]
                  + t * G(1 + t) * G(1 - t) * f[3] + t ** 2 * mp.sqrt(mp.pi) * G(1 - t) / G(1.5 - t) * (f[4] + f[5]))
ex1 = Jh / t ** 2
v1, N = J_full('1', t, 30, -0.17, -0.05)
print('d=1 t=0.3 : J_MB = %s   exact = %s   diff = %s' % (mp.nstr(v1.real, 28), mp.nstr(ex1, 28), mp.nstr(abs(v1 - ex1), 3)))
