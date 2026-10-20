# Test 2: Steps 1-4 machinery. gamma_{1-r} (lattice) vs kappa_+ * s1+ with
#   s1+ = 2 pi kappa_Gamma int_0^{2pi} e^{i sigma V} D(e^{iV}) a(V) a'(2pi-V) dV
# for r=2, in UNBALANCED cases (top mode nonzero), and a balanced case (should vanish).
import mpmath as mp, sys
mp.mp.dps = 22
def fg(g,w): return mp.gamma(w)*mp.rgamma(w+g)
def dl_list(d,M):
    c=[mp.mpf(1)]
    for k in range(1,M+1): c.append(c[-1]*(d-1+k-1)/k)
    return [c[0]]+[c[l]+c[l-1] for l in range(1,M+1)]
def xi(t,d,sig,al,be,g,N,M,dl):
    r=len(g)
    L={m: mp.fprod(fg(g[i], m+t+sig+al[i]) for i in range(r)) for m in range(-N,M+1)}
    R={n: mp.fprod(fg(g[i], be[i]-n-t) for i in range(r)) for n in range(-N,N+1)}
    S=mp.fsum(R[n]*mp.fsum(dl[m-n]*L[m] for m in range(n,M+1)) for n in range(-N,N+1))
    D=mp.fprod(mp.sin(mp.pi*(t+sig+al[i]))*mp.sin(mp.pi*(t-be[i])) for i in range(r))
    return D*S
def lattice_modes(d,sig,al,be,g,N,M,t0=mp.mpf('0.0731')):
    r=len(g); dl=dl_list(d,N+M+2); K=2*r+1
    ts=[t0+mp.mpf(j)/K for j in range(K)]
    X=[xi(t,d,sig,al,be,g,N,M,dl) for t in ts]
    return {m: mp.fsum(X[j]*mp.expjpi(-2*m*ts[j]) for j in range(K))/K for m in range(-r,r+1)}
def s1_formula(d,sig,al,be,g):
    # r = 2 only: a = h1*h2, a' = h1'*h2'
    h  = [ (lambda v,i=i: mp.expj(al[i]*v)*mp.power(1-mp.expj(v), g[i]-1)) for i in range(2)]
    hp = [ (lambda v,i=i: mp.expj(-be[i]*v)*mp.power(1-mp.expj(-v), g[i]-1)) for i in range(2)]
    def conv(F,V): return mp.quad(lambda v: F[0](v)*F[1](V-v), [0, V/2, V])
    def Dfun(V): return (1+mp.expj(V))*mp.power(1-mp.expj(V), 1-d)
    I = mp.quad(lambda V: mp.expj(sig*V)*Dfun(V)*conv(h,V)*conv(hp,2*mp.pi-V), [0, mp.pi/2, mp.pi, 3*mp.pi/2, 2*mp.pi])
    kG = mp.fprod(mp.gamma(gi)**-2 for gi in g)
    return 2*mp.pi*kG*I
def kappa_plus(sig,al,be):
    r=len(al); cs=[sig+a for a in al]+[-b for b in be]
    return mp.mpf(-0.25)**r*mp.expjpi(-mp.fsum(cs))
cases = [
 ('real, unbalanced eps=(0.15,0.10)', mp.mpf('1.5'), mp.mpf('0.3'), [mp.mpf('0.1'),mp.mpf('-0.2')], [mp.mpf('1.8'),mp.mpf('2.2')], [mp.mpf('0.15'),mp.mpf('0.10')]),
 ('complex, unbalanced',              mp.mpf('2.6'), mp.mpc('0.2','0.1'), [mp.mpc('0.1','-0.15'),mp.mpc('-0.2','0.05')], [mp.mpc('1.9','0.3'),mp.mpc('2.4','-0.2')], [mp.mpc('0.12','0.05'),mp.mpc('-0.07','0.0')]),
 ('complex, total balance only',      mp.mpf('0.8'), mp.mpc('0.2','-0.1'), [mp.mpc('0.3','0.1'),mp.mpc('-0.1','0.2')], [mp.mpc('1.7','-0.3'),mp.mpc('2.1','0.25')], [mp.mpc('0.1','0.03'),mp.mpc('-0.1','-0.03')]),
 ('complex, BALANCED',                mp.mpf('2.6'), mp.mpc('0.2','0.1'), [mp.mpc('0.1','-0.15'),mp.mpc('-0.2','0.05')], [mp.mpc('1.9','0.3'),mp.mpc('2.4','-0.2')], [0,0]),
]
if __name__=="__main__":
  for name,d,sig,al,g,eps in cases:
      be=[d/2-sig-al[i]-g[i]+eps[i] for i in range(2)]
      gm=lattice_modes(d,sig,al,be,g,140,140)
      gm2=lattice_modes(d,sig,al,be,g,200,200)
      s1=s1_formula(d,sig,al,be,g)
      pred=kappa_plus(sig,al,be)*s1
      mx=max(abs(v) for v in gm2.values())
      print(name)
      print('   lattice gamma_-1 (N=140) = %s' % mp.nstr(gm[-1],14))
      print('   lattice gamma_-1 (N=200) = %s' % mp.nstr(gm2[-1],14))
      print('   kappa_+ * s1+ (formula)  = %s' % mp.nstr(pred,14))
      print('   rel diff formula vs N=200: %.2e ; |gamma_-1|/max = %.2e ; |gamma_+-2|/max = %.1e,%.1e' % (abs(pred-gm2[-1])/mx, abs(gm2[-1])/mx, abs(gm2[-2])/mx, abs(gm2[2])/mx))
      sys.stdout.flush()
