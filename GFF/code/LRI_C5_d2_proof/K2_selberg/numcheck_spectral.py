"""Independent finite-t check: J_{2tau} from the note's spectral subtraction identity gs:Ksubtraction at d=2,
   J_{2tau} = C(tau)^2 [Gamma(1/2-tau/2)/Gamma(1/2+tau/2)]^4 + C(tau) < t_l^2 (R_tau - S_tau) >_2,
computed with session C63d's spectral code (read-only import), versus the closed form proved here,
   J_{2tau} = (4/pi^2) sin^2(pi tau) (I_3^2 + I_4^2) = pi^2 F(tau)^2 + [sin(pi tau)Gamma(tau)^2/Gamma(1/2+tau)^2]^2 G(tau)^2."""
import sys, time
sys.path.insert(0, '<PROJECT>/LRI_C5_d3/wf_d2check')
import mpmath as mp
import hp_masters_d2 as H
from numcheck_moments2 import Is

H.setcfg(dict(dps=20, spins=16, kmax=20, rho='0.1', c0='0', breaks='0,0.3,1.5,6,inf', part='t'))
for tau in [mp.mpf('0.1'), mp.mpf('0.23')]:
    st = time.time()
    Fmix = H.Kmixed(tau)
    C = mp.gamma(tau)/mp.gamma(1-tau)
    Jspec = C**2*(mp.gamma(0.5-tau/2)/mp.gamma(0.5+tau/2))**4 + C*Fmix
    I = Is(tau)
    Jklt = 4/mp.pi**2*mp.sinpi(tau)**2*(I[3]**2+I[4]**2)
    print('tau =', tau, ' J_spectral =', mp.nstr(Jspec, 18), ' J_closed =', mp.nstr(Jklt, 18),
          ' rel diff =', mp.nstr(Jspec/Jklt-1, 3), ' (%.0f s)' % (time.time()-st), flush=True)
