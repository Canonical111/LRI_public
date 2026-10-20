"""Finite-tau check of the closed form against the note's spectral identity gs:Ksubtraction at higher precision,
using session C63d's independent spectral code (read-only import), closed form evaluated with mpmath hyp3f2."""
import sys, time
sys.path.insert(0, '<PROJECT>/LRI_C5_d3/wf_d2check')
import mpmath as mp
import hp_masters_d2 as H
dps, spins, kmax = int(sys.argv[1]), sys.argv[2], sys.argv[3]
H.setcfg(dict(dps=dps, spins=int(spins), kmax=int(kmax), rho='0.1', c0='0', breaks='0,0.3,1.5,6,inf', part='t'))
mp.mp.dps = dps
for tau in [mp.mpf(sys.argv[4]) if len(sys.argv) > 4 else mp.mpf('0.1')]:
    st = time.time()
    Fmix = H.Kmixed(tau)
    C = mp.gamma(tau)/mp.gamma(1-tau)
    Jspec = C**2*(mp.gamma(0.5-tau/2)/mp.gamma(0.5+tau/2))**4 + C*Fmix
    Jref = mp.pi**2*(mp.hyp3f2(0.5,0.5,tau,1,1,1)**2 + (mp.gamma(tau)/(mp.gamma(1-tau)*mp.gamma(0.5+tau)**2)*mp.hyp3f2(tau,tau,tau,0.5+tau,0.5+tau,1))**2)   # closed form (Thomae form)
    print(f'dps={dps} spins={spins} kmax={kmax} tau={tau}: J_spec = {mp.nstr(Jspec.real, dps)}  rel diff = {mp.nstr(abs(Jspec/Jref-1), 3)}  ({time.time()-st:.0f}s)', flush=True)
