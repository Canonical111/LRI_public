# Test 4: second top mode gamma_{r-1} = kappa_- s1^- ; check (i) Step 6 conjugation s1^-(p) = conj(s1^+(conj p))
# and (ii) the direct lower-half-plane formula s1^- = 2pi kG int e^{-i sigma V} D(e^{-iV}) at(V) at'(2pi-V) dV,
# at - = conv of e^{-i al v}(1-e^{-iv})^{g-1}, at' = conv of e^{i be v}(1-e^{iv})^{g-1}; UNBALANCED complex, r=2.
import mpmath as mp, sys
sys.path.insert(0,'.')
from t2_s1formula import lattice_modes, s1_formula, kappa_plus
mp.mp.dps = 22
def s1_lower_direct(d,sig,al,be,g):
    h  = [ (lambda v,i=i: mp.expj(-al[i]*v)*mp.power(1-mp.expj(-v), g[i]-1)) for i in range(2)]
    hp = [ (lambda v,i=i: mp.expj(be[i]*v)*mp.power(1-mp.expj(v), g[i]-1)) for i in range(2)]
    def conv(F,V): return mp.quad(lambda v: F[0](v)*F[1](V-v), [0, V/2, V])
    def Dfun(V): return (1+mp.expj(-V))*mp.power(1-mp.expj(-V), 1-d)
    I = mp.quad(lambda V: mp.expj(-sig*V)*Dfun(V)*conv(h,V)*conv(hp,2*mp.pi-V), [0, mp.pi/2, mp.pi, 3*mp.pi/2, 2*mp.pi])
    kG = mp.fprod(mp.gamma(gi)**-2 for gi in g)
    return 2*mp.pi*kG*I
def kappa_minus(sig,al,be):
    r=len(al); cs=[sig+a for a in al]+[-b for b in be]
    return mp.mpf(-0.25)**r*mp.expjpi(mp.fsum(cs))
d=mp.mpf('1.5'); sig=mp.mpc('0.2','0.1'); al=[mp.mpc('0.1','-0.15'),mp.mpc('-0.2','0.05')]; g=[mp.mpc('1.9','0.3'),mp.mpc('2.4','-0.2')]
eps=[mp.mpc('0.12','0.05'),mp.mpc('-0.07','0.0')]
be=[d/2-sig-al[i]-g[i]+eps[i] for i in range(2)]
gm=lattice_modes(d,sig,al,be,g,200,200)
mx=max(abs(v) for v in gm.values())
s1m_direct=s1_lower_direct(d,sig,al,be,g)
# conjugate parameter point
cs=lambda L:[mp.conj(x) for x in L]
s1m_conj=mp.conj(s1_formula(d,mp.conj(sig),cs(al),cs(be),cs(g)))
print('lattice gamma_+1           =', mp.nstr(gm[1],14))
print('kappa_- * s1^- (direct)    =', mp.nstr(kappa_minus(sig,al,be)*s1m_direct,14))
print('kappa_- * conj s1^+(pbar)  =', mp.nstr(kappa_minus(sig,al,be)*s1m_conj,14))
print('lattice gamma_-1           =', mp.nstr(gm[-1],14), ' vs kappa_+ s1^+ =', mp.nstr(kappa_plus(sig,al,be)*s1_formula(d,sig,al,be,g),14))
print('rel diffs (to max|gamma|): direct %.2e, conj %.2e ; |gamma_+1|/max=%.2e, |gamma_-1|/max=%.2e' % (abs(kappa_minus(sig,al,be)*s1m_direct-gm[1])/mx, abs(kappa_minus(sig,al,be)*s1m_conj-gm[1])/mx, abs(gm[1])/mx, abs(gm[-1])/mx))
