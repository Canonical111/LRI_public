# Test 5: Steps 1-4 formula at r=3,4 with integer g_i (exact exponential-sum convolutions), unbalanced and balanced,
# complex sigma, alpha_i, beta_i. gamma_{1-r} (lattice) vs kappa_+ s1^+.
import mpmath as mp, itertools
mp.mp.dps = 25
def fg(g,w): return mp.gamma(w)*mp.rgamma(w+g)
def dl_list(d,M):
    c=[mp.mpf(1)]
    for k in range(1,M+1): c.append(c[-1]*(d-1+k-1)/k)
    return [c[0]]+[c[l]+c[l-1] for l in range(1,M+1)]
def lattice_modes(d,sig,al,be,g,N,M,t0=mp.mpf('0.0731')):
    r=len(g); dl=dl_list(d,N+M+2); K=2*r+1
    ts=[t0+mp.mpf(j)/K for j in range(K)]; X=[]
    for t in ts:
        L={m: mp.fprod(fg(g[i], m+t+sig+al[i]) for i in range(r)) for m in range(-N,M+1)}
        R={n: mp.fprod(fg(g[i], be[i]-n-t) for i in range(r)) for n in range(-N,N+1)}
        S=mp.fsum(R[n]*mp.fsum(dl[m-n]*L[m] for m in range(n,M+1)) for n in range(-N,N+1))
        D=mp.fprod(mp.sin(mp.pi*(t+sig+al[i]))*mp.sin(mp.pi*(t-be[i])) for i in range(r))
        X.append(D*S)
    return {m: mp.fsum(X[j]*mp.expjpi(-2*m*ts[j]) for j in range(K))/K for m in range(-r,r+1)}
def expsum(shift, sgn, g):
    # e^{i shift v} (1 - e^{i sgn v})^{g-1} as list of (coef, exponent a) meaning coef*e^{i a v}
    n=int(g)-1
    return [(mp.binomial(n,k)*(-1)**k, shift+sgn*k) for k in range(n+1)]
def conv_eval(factors, V):
  with mp.workdps(120):
    return +conv_eval_raw(factors, V)
def conv_eval_raw(factors, V):
    # r-fold convolution on [0,inf) of sums of exponentials, evaluated at V (divided differences)
    tot=0
    for combo in itertools.product(*factors):
        c=mp.fprod(x[0] for x in combo); a=[x[1] for x in combo]
        s=0
        for k in range(len(a)):
            den=mp.fprod(1j*(a[k]-a[j]) for j in range(len(a)) if j!=k)
            s+=mp.expj(a[k]*V)/den
        tot+=c*s
    return tot
def s1_formula(d,sig,al,be,g):
    r=len(g)
    F =[expsum(al[i], +1, g[i]) for i in range(r)]
    Fp=[expsum(-be[i], -1, g[i]) for i in range(r)]
    Dfun=lambda V: (1+mp.expj(V))*mp.power(1-mp.expj(V),1-d)
    I=mp.quad(lambda V: mp.expj(sig*V)*Dfun(V)*conv_eval(F,V)*conv_eval(Fp,2*mp.pi-V), [0,mp.pi/2,mp.pi,3*mp.pi/2,2*mp.pi])
    return 2*mp.pi*mp.fprod(mp.gamma(gi)**-2 for gi in g)*I
def kappa_plus(sig,al,be):
    r=len(al); cs=[sig+a for a in al]+[-b for b in be]
    return mp.mpf(-0.25)**r*mp.expjpi(-mp.fsum(cs))
C=mp.mpc
cases=[]
_unused=[('r=3 g=(1,2,3) d=1.7 unbalanced', mp.mpf('1.7'), C('0.21','0.13'), [C('0.17','-0.11'),C('-0.33','0.07'),C('0.41','0.19')], [1,2,3], [C('0.13','0.04'),C('-0.05','0.02'),C('0.09','-0.06')]),
       ('r=3 g=(1,2,3) d=1.7 BALANCED',   mp.mpf('1.7'), C('0.21','0.13'), [C('0.17','-0.11'),C('-0.33','0.07'),C('0.41','0.19')], [1,2,3], [0,0,0]),
       ]
cases=[('r=4 g=(1,1,2,2) d=2.9 unbalanced (total balance kept)', mp.mpf('2.9'), C('-0.12','0.08'), [C('0.27','0.05'),C('-0.18','-0.09'),C('0.33','0.12'),C('0.06','-0.14')], [1,1,2,2], [C('0.1','0.02'),C('-0.1','-0.02'),C('0.05','0'),C('-0.05','0')]),
       ('r=4 g=(1,1,2,2) d=2.9 BALANCED', mp.mpf('2.9'), C('-0.12','0.08'), [C('0.27','0.05'),C('-0.18','-0.09'),C('0.33','0.12'),C('0.06','-0.14')], [1,1,2,2], [0,0,0,0]),
]
for name,d,sig,al,g,eps in cases:
    r=len(g); be=[d/2-sig-al[i]-g[i]+eps[i] for i in range(r)]
    gm1=lattice_modes(d,sig,al,be,g,50,50); gm=lattice_modes(d,sig,al,be,g,90,90)
    mx=max(abs(v) for v in gm.values())
    pred=kappa_plus(sig,al,be)*s1_formula(d,sig,al,be,g)
    print(name)
    print('   lattice gamma_{1-r}: N=50 %s  N=90 %s' % (mp.nstr(gm1[1-r],12), mp.nstr(gm[1-r],12)))
    print('   kappa_+ s1^+       : %s' % mp.nstr(pred,12))
    print('   rel(to max): |formula-lattice| %.1e ; |gamma_{1-r}| %.1e ; |gamma_{r-1}| %.1e ; boundary |gamma_{+-r}| %.1e %.1e' % (abs(pred-gm[1-r])/mx, abs(gm[1-r])/mx, abs(gm[r-1])/mx, abs(gm[-r])/mx, abs(gm[r])/mx))
