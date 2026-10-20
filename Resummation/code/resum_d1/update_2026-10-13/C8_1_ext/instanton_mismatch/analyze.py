"""Reproducible diagnostics; run through Slurm, not on the laptop.

Finite-order fits are diagnostics, not estimates with statistical confidence.
The supplied high-loop error allowances do not include common theory errors.

2026-10-13 (C8(1) final): copy of reproduction/instanton_mismatch/analyze.py (unchanged there) in which C8 and its
allowance come from update_2026-10-13/C8_1_ext/c8_1_switch.py: LRI_C8_1=final (default) 8059766.723129955 +- 17000,
LRI_C8_1=previous 8066723.342964563 +- 33000 (reproduces reproduction/instanton_mismatch/analysis.json and
ratio_table.csv). C0..C7 unchanged. Output: ANALYSIS_OUTPUT if set, else <switch output root>/instanton_mismatch/.
Also writes ratio_table_KI.csv: C_n / [K_I (-1/A_eps)^n Gamma(n+4)] with the preferred K_I = 0.006246637286122374.
The whole run takes a few seconds (local run allowed).
"""
import json, math, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import c8_1_switch as SW
C8IN = SW.c8_inputs()
import mpmath as mp
import numpy as np
from scipy.special import gammaln
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = Path(os.environ.get('ANALYSIS_OUTPUT') or SW.out_root()/'instanton_mismatch')
out.mkdir(parents=True, exist_ok=True)
mp.mp.dps = 65
p = mp.pi
A = p + 4*mp.log(2)
Q = mp.gamma(mp.mpf('0.25'))**4/p
Ag = 3*p**2/mp.gamma(mp.mpf('0.25'))**4
Ae = 3*Ag
a = float(1/Ae)
C = np.array([.5, -1/6, .657131263981, -3.719856322902,
              45.42488010356, -731.13947662454, 14331.68703276838,
              -322549.8888129889, float(C8IN['C8'])])
allow = np.array([0., 0., 0., 0., 0., 0., 4.9e-7, 41., float(C8IN['allowance'])])
ns = np.arange(2,9)
ratios = -C[2:]/(ns*C[1:-1])
report = {'inputs': {'C': C.tolist(), 'allowances': allow.tolist(),
                     'source': 'long_range_ising_condensed.tex, 3 October 2026' if C8IN['mode'] == 'previous' else
                               'long_range_ising_condensed.tex, 3 October 2026; C8(1) final of 13 October 2026 (note fa71533, c8_1_final.json)'},
          'constants': {k: str(v) for k,v in dict(Ag=Ag,Aepsilon=Ae,a=1/Ae,A=A,Q=Q).items()},
          'ratios': []}
for n,r in zip(ns,ratios):
    report['ratios'].append(dict(n=int(n),r=float(r),
        b_effective=float(n*(r/a-1)), corrected_b3=float(r/(1+3/n)),
        normalized_b3=float(abs(C[n])/(a**n*math.gamma(n+4)))))
print('Constants', report['constants'], flush=True)

# Independent direct quadrature of the inverse-kernel equation.
# y=x+/-t^2 removes its integrable |x-y|^{-1/2} singularity.
checks=[]
for dps in (40,65):
    mp.mp.dps=dps
    const=mp.sqrt(mp.pi)*mp.gamma(mp.mpf('.25'))/mp.gamma(mp.mpf('.75'))
    for xv,rv in (('0','1'),('.7','1'),('3','1'),('.7','2')):
        x,R=mp.mpf(xv),mp.mpf(rv)
        f=lambda y: (R/(R*R+y*y))**mp.mpf('.25')
        integ=mp.quad(lambda t: 2*(f(x+t*t)**3+f(x-t*t)**3),
                      [0,mp.mpf('.5'),1,2,4,mp.inf])
        err=abs(integ/(const*f(x))-1)
        checks.append(dict(dps=dps,x=xv,R=rv,relative_error=str(err)))
        assert err < mp.mpf('1e-25')
report['bubble_integral_checks']=checks
mp.mp.dps=65
report['dimensional_check']={str(d):str(mp.mpf('4.5')*mp.gamma(3*mp.mpf(d)/4)**2/
                                    (mp.gamma(mp.mpf(d)/4)**2*mp.gamma(d))) for d in (1,2,3,4)}

# Vary inverse-order ansatz and fitting window. No weighting by tiny integration
# errors: unknown asymptotic corrections, not integration errors, dominate.
fits=[]
for lo in (4,5,6):
    for degree in (1,2):
        n=np.arange(lo,9,dtype=float); y=ratios[lo-2:]
        X=np.array([n**(-j) for j in range(degree+1)]).T
        coef=np.linalg.lstsq(X,y,rcond=None)[0]
        fits.append(dict(window=[lo,8],degree=degree,coefficients=coef.tolist(),
                         rms=float(np.sqrt(np.mean((X@coef-y)**2)))))
report['unconstrained_ratio_fits']=fits
fixed=[]
for lo in (4,5,6):
    n=np.arange(lo,9,dtype=float); y=ratios[lo-2:]-a
    X=np.array([1/n,1/n**2]).T
    coef=np.linalg.lstsq(X,y,rcond=None)[0]
    fixed.append(dict(window=[lo,8],b=float(coef[0]/a),d=float(coef[1]),
                      rms=float(np.sqrt(np.mean((X@coef-y)**2)))))
report['fixed_a_ratio_fits']=fixed

# Coefficient-level inverse-factorial expansions with fixed candidate b=3.
# F_n=K0+K1/(n+3)+K2/[(n+3)(n+2)]+... corresponds to an analytic
# fluctuation series multiplying h^{-4} exp(-Ae/h), if that semiclassical
# counting survives MS renormalization. This condition is not proven here.
def basis(n,degree,b=3):
    cols=[np.ones_like(n,dtype=float)]
    for j in range(1,degree+1):
        cols.append(cols[-1]/(n+b-j+1))
    return np.array(cols).T

models=[]
for av in (1.3,a,2.5,3.2):
    for end in (6,7,8):
        for degree in (1,2):
            n=np.arange(4,end+1)
            if len(n)<degree+1: continue
            base=np.exp(n*np.log(av)+gammaln(n+4))
            y=np.abs(C[n])/base
            X=basis(n,degree)
            k=np.linalg.lstsq(X,y,rcond=None)[0]
            pred=[]
            for nxt in range(end+1,10):
                value=float((-1)**nxt*np.exp(nxt*np.log(av)+gammaln(nxt+4))*(basis(np.array([nxt]),degree)@k)[0])
                pred.append(dict(n=nxt,value=value,relative_error=(value/C[nxt]-1) if nxt<=8 else None))
            models.append(dict(a=av,b=3,degree=degree,training=[4,end],
                k=k.tolist(),relative_corrections=(k[1:]/k[0]).tolist(),
                rms_relative=float(np.sqrt(np.mean(((X@k)/y-1)**2))), predictions=pred))
report['coefficient_models']=models

# Sensitivity of the ill-conditioned three-point extrapolation to the supplied
# *allowances*. Corners are bounds for a diagnostic, not confidence intervals.
corners=[]
for s6 in (-1,1):
 for s7 in (-1,1):
  for s8 in (-1,1):
   cc=C.copy(); cc[6:9]+=allow[6:9]*np.array([s6,s7,s8])
   n=np.arange(6,9,dtype=float)
   rr=-cc[6:9]/(n*cc[5:8])
   est=np.linalg.solve(np.array([np.ones(3),1/n,1/n**2]).T,rr)[0]
   corners.append(float(est))
report['last_three_quadratic_allowance_range']=[min(corners),max(corners)]

# Dlog-Pade diagnostic for B_L(z)/z^2 after removing C0,C1.
# Each Pade uses all available six coefficients of the logarithmic derivative.
pades=[]
for leroy in (0,3,5):
    f=[mp.mpf(str(C[n]))/mp.gamma(n+leroy+1) for n in range(2,9)]
    dlog=[]
    for k in range(6):
        dlog.append(((k+1)*f[k+1]-sum(f[j]*dlog[k-j] for j in range(1,k+1)))/f[0])
    for den in (1,2,3,4):
        num=5-den
        pp,qq=mp.pade(dlog,num,den)
        poles=np.roots([float(z) for z in reversed(qq)])
        zeros=np.roots([float(z) for z in reversed(pp)])
        pades.append(dict(leroy=leroy,order=[num,den],poles=[
            dict(real=float(z.real),imag=float(z.imag),distance_to_numerator_zero=float(min(abs(z-zz) for zz in zeros)) if len(zeros) else None)
            for z in poles]))
report['dlog_pade']=pades

# Reexpand the known truncated MS RG functions. Higher coefficients obtained
# this way are explicitly diagnostic truncations, not new loop results.
b2=-6*A
b3=6*Q+mp.mpf(87)/4*A*A-mp.mpf(3)/4*p*p-4*p
c2=-A
c3=mp.mpf(7)/2*A*A-p*p/6-4*p/3
def mul(x,y,N):
    return [sum(x[j]*y[k-j] for j in range(k+1)) for k in range(N+1)]
def power(x,k,N):
    y=[mp.mpf(1)]+[mp.mpf(0)]*N
    for _ in range(k): y=mul(y,x,N)
    return y
trunc=[]
N=16
for loops,bb,cc in ((2,[0,3,b2],[0,1,c2]),(3,[0,3,b2,b3],[0,1,c2,c3])):
    g=[mp.mpf(0)]*(N+1)
    for n in range(1,N+1):
        g[n]=((1 if n==1 else 0)-sum(bb[k]*power(g,k,N)[n] for k in range(2,len(bb))))/3
    thermal=[mp.mpf('.5'),-mp.mpf('.5')]+[mp.mpf(0)]*(N-1)
    for k in range(1,len(cc)):
        gp=power(g,k,N)
        thermal=[v+cc[k]*w for v,w in zip(thermal,gp)]
    roots=np.roots([float(k*bb[k]) for k in range(len(bb)-1,0,-1)])
    branch=[]
    for rt in roots:
        ev=sum(float(bb[k])*rt**k for k in range(1,len(bb)))
        branch.append(dict(g_real=float(rt.real),g_imag=float(rt.imag),eps_real=float(ev.real),eps_imag=float(ev.imag),modulus=float(abs(ev))))
    trunc.append(dict(loops=loops,C=[str(z) for z in thermal],critical_values=branch))
report['truncated_RG']=trunc
for n in (1,2,3):
    assert abs(float(trunc[-1]['C'][n])-C[n])<1e-10
report['fixed_point_composition']={
 'exp_constant':str(mp.exp(-2*Ag*A)),
 'log_exp_linear_epsilon':str(Ag*(b3-12*A*A)/9),
 'disc_linear_h_from_composition_if_beta_power3':str(2*A-Ag*(b3-12*A*A)/9),
 'gamma_prime_over_beta_prime_linear_cancellation':str(2*c2/3-b2/9)}

with (out/'analysis.json').open('w') as fh: json.dump(report,fh,indent=2)
with (out/'ratio_table.csv').open('w') as fh:
    fh.write('n,C_n,ratio,b_effective,corrected_b3,normalized_b3\n')
    for row in report['ratios']:
        n=row['n']; fh.write(','.join(map(str,[n,C[n],row['r'],row['b_effective'],row['corrected_b3'],row['normalized_b3']]))+'\n')
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(10.4,4.0))
n=np.arange(4,9)
axs[0].plot(n,ratios[2:],'o-',label='supplied coefficients')
axs[0].axhline(a,color='black',ls='--',label=r'$a_\mathrm{inst}=1.94528$')
axs[0].plot(n,a*(1+3/n),'s:',label=r'$a_\mathrm{inst}(1+3/n)$')
axs[0].set(xlabel='order n',ylabel=r'$-C_n/(n C_{n-1})$',title='Raw ratio is not yet a limit')
axs[0].legend(fontsize=9)
f3=np.abs(C[n])/np.exp(n*np.log(a)+gammaln(n+4))
axs[1].plot(n,f3,'o-',label=r'$|C_n|/[a_\mathrm{inst}^n\Gamma(n+4)]$')
axs[1].set(xlabel='order n',ylabel='normalized amplitude',title='Conditional power b=3')
axs[1].legend(fontsize=9)
fig.tight_layout(); fig.savefig(out/'ratio_diagnostics.png',dpi=180)
print('Bubble checks passed; diagnostics written.',flush=True)
print('Ratios:',report['ratios'],flush=True)
print('Free extrapolations:',fits,flush=True)
print('Fixed-a fits:',fixed,flush=True)
print('COMPLETED',flush=True)

# 2026-10-13: ratio to the preferred one-loop sector prediction C_n ~ K_I (-1/A_eps)^n Gamma(n+4)
KI = 0.006246637286122374
with (out/'ratio_table_KI.csv').open('w') as fh:
    fh.write('n,C_n,C_n_over_KI_minus_a_pow_n_Gamma_n_plus_4\n')
    for n in range(2, 9):
        fh.write('%d,%r,%r\n' % (n, float(C[n]), float(C[n]/(KI*(-a)**n*math.gamma(n+4)))))
print('C_n/[K_I(-1/A)^n Gamma(n+4)]:', {n: round(float(C[n]/(KI*(-a)**n*math.gamma(n+4))), 6) for n in range(3, 9)},
      'C8 mode', C8IN['mode'], flush=True)
