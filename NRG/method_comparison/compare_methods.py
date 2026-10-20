"""Method-independent comparison of the NRG Delta_eps(Delta_sigma) table.

References (none uses NRG):
  * 1D LRI cluster Monte Carlo (MC/data/1d/scan_data/FIT_V3_SCAN.json of this repository): Fukui-Todo cluster MC +
    finite-size scaling; value with sigma_stat and sigma_sys and its decision label, plus the crossing extrapolation
    Delta_inf(sigma_inf)(Delta_omega') where it exists. sigma_sys and Delta_omega' are sensitivity scales, not standard
    deviations: differences are compared with linear sums only (no quadrature, no "sigma" pulls).
  * epsilon expansion of Delta_E = sum_n C_n eps^n, eps = 2s - 1, C_0..C_8 for d = 1 (the coefficients of the
    accompanying paper): direct partial sums (only where the terms still decrease) and Borel-Pade resummation with the
    spread over approximants as its uncertainty. Borel-Pade: approximants [L/M] with L+M = 6, 7, 8, dropped if the Borel
    denominator has a positive real root or the value lies outside (0.3, 1.2); central value = the upper of the two middle
    values of the L+M = 8 approximants (four at Delta_sigma = 0.2-0.24), not their mean; spread = half the range of the
    approximants with L+M >= 7. The L+M = 6 approximants are computed but enter neither.
NRG points that are not converged in chain depth (results/ds13_final.json, status) carry no total error; their rows are
written for completeness and are not used in any comparison.
Writes comparison.json and comparison.md.

Usage (from the NRG folder): python method_comparison/compare_methods.py [--root DIR] [--mc FILE] [--out DIR]
  --root  folder holding results/ds13_final.json (default: the NRG folder above this script)
  --mc    the 1D Monte Carlo scan table (default: <NRG>/../MC/data/1d/scan_data/FIT_V3_SCAN.json)
  --out   where comparison.json and comparison.md are written (default: <NRG>/.work/method_comparison; the released files are never overwritten)
"""
import argparse,json,math
from pathlib import Path
import mpmath as mp

HERE=Path(__file__).resolve().parent

# d = 1 coefficients C_0..C_8. C_0..C_6 are exact to the digits shown; C_7 = -322550 +- 41; C_8 = (8.060 +- 0.017)e6.
C=[mp.mpf(1)/2,-mp.mpf(1)/6,mp.mpf('0.657131263981'),mp.mpf('-3.719856322902'),mp.mpf('45.42488010356'),
   mp.mpf('-731.13947662454'),mp.mpf('14331.6870328'),mp.mpf('-322550'),mp.mpf('8.060e6')]
dC={7:41,8:0.017e6}


def partial_sums(eps,coef):
    terms=[c*eps**n for n,c in enumerate(coef)];sums=[];acc=0
    for t in terms:acc+=t;sums.append(acc)
    return terms,sums


def optimal_truncation(eps,coef):
    """Sum up to (and excluding) the smallest term; error ~ smallest term."""
    terms,_=partial_sums(eps,coef);mags=[abs(t) for t in terms]
    k=min(range(2,len(terms)),key=lambda i:mags[i])
    return float(sum(terms[:k])),float(mags[k]),k


def borel_pade(eps,coef,L,M):
    b=[c/mp.factorial(n) for n,c in enumerate(coef[:L+M+1])]
    p,q=mp.pade(b,L,M)
    # reject approximants with a Borel-plane pole on the positive real axis (or near it)
    roots=mp.polyroots(q[::-1],maxsteps=200,extraprec=60) if M>0 else []
    for r in roots:
        if abs(mp.im(r))<1e-8 and mp.re(r)>0:return None
    f=lambda t:mp.polyval(p[::-1],eps*t)/mp.polyval(q[::-1],eps*t)*mp.exp(-t)
    return float(mp.quad(f,[0,1,10,mp.inf]))


def resum(eps):
    vals={}
    for N in (6,7,8):
        for M in range(1,N):
            L=N-M;v=borel_pade(mp.mpf(eps),C,L,M)
            if v is not None and 0.3<v<1.2:vals[f'[{L}/{M}]']=v
    if not vals:return None
    top=[v for k,v in vals.items() if sum(map(int,k.strip('[]').split('/')))==8]
    lo=[v for k,v in vals.items() if sum(map(int,k.strip('[]').split('/')))>=7]
    # central value: the upper of the two middle values when there is an even number (not the mean of the two)
    central=sorted(top)[len(top)//2] if top else sorted(lo)[len(lo)//2]
    spread=(max(lo)-min(lo))/2 if len(lo)>1 else float('nan')
    # sensitivity to the C7, C8 allowances
    sens=0.
    for n in (7,8):
        Cp=list(C);Cp[n]+=dC[n]
        b=[c/mp.factorial(k) for k,c in enumerate(Cp)];
        try:
            p,q=mp.pade(b,4,4)
            f=lambda t:mp.polyval(p[::-1],mp.mpf(eps)*t)/mp.polyval(q[::-1],mp.mpf(eps)*t)*mp.exp(-t)
            sens=max(sens,abs(float(mp.quad(f,[0,1,10,mp.inf]))-vals.get('[4/4]',central)))
        except Exception:
            pass
    return {'central':central,'spread':spread,'coef_sensitivity':sens,'approximants':vals}


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root',type=Path,default=HERE.parent)
    ap.add_argument('--mc',type=Path,default=HERE.parent.parent/'MC'/'data'/'1d'/'scan_data'/'FIT_V3_SCAN.json')
    ap.add_argument('--out',type=Path,default=HERE.parent/'.work'/'method_comparison');a=ap.parse_args()
    NRG=json.loads((a.root/'results'/'ds13_final.json').read_text())
    MC={round(p['ds'],7):p for p in json.loads(a.mc.read_text())}
    mp.mp.dps=40;rows=[]
    for x in NRG:
        ds=x['ds'];s=x['s'];eps=1-4*ds
        row={'ds':ds,'s':s,'eps':eps,'nrg':x['Delta_E'],'nrg_err':x['total'],'nrg_status':x['status'],'nrg_estimator':x['estimator']}
        m=MC.get(round(ds,7))
        if m and m.get('Delta_epsilon') is not None:
            sys=m['sigma_sys'] if m['sigma_sys'] is not None else float('nan')
            row.update(mc=m['Delta_epsilon'],mc_stat=m['sigma_stat'],mc_sys=sys,mc_status=m['status'],
                       mc_cross=m.get('Delta_inf'),mc_cross_err=m.get('sigma_inf'),mc_cross_domega=m.get('Delta_omega'))
        elif m:
            row.update(mc=None,mc_status=m['status'])
        ot=optimal_truncation(mp.mpf(eps),C);row.update(series_opt=ot[0],series_opt_err=ot[1],series_opt_order=ot[2])
        r=resum(eps)
        if r:row.update(series_bp=r['central'],series_bp_spread=r['spread'],series_bp_sens=r['coef_sensitivity'],
                        series_bp_approximants=r['approximants'])
        rows.append(row)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'comparison.json').write_text(json.dumps(rows,indent=1)+'\n')
    f=lambda v,n=5:'—' if v is None or (isinstance(v,float) and math.isnan(v)) else f'{v:.{n}f}'
    md=['NRG − MC is compared with the linear sum σ_stat + σ_sys + δ_tot ("lin. ratio"); "—" where σ_sys is absent or the NRG point is',
        'not converged (the difference is then shown for information only). A CROSS-CHECK FAILED or CONDITIONAL MC value is not',
        'an infinite-size value (MC/REPRODUCE.md). Borel–Padé: the upper-middle of the L+M = 8 approximants; spread: half-range over L+M ≥ 7.','',
        '| Δσ | ε | NRG | MC (stat)(sys) [label] | MC crossing (σ_∞)(Δω′) | NRG−MC (lin. ratio) | ε-series, optimal truncation | ε-series, Borel–Padé (spread) | NRG−series |',
        '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        mc='—' if r.get('mc') is None else f"{r['mc']:.5f}({r['mc_stat']*1e5:.0f})({'†' if math.isnan(r['mc_sys']) else round(r['mc_sys']*1e5)}) [{r['mc_status']}]"
        if r.get('mc') is None and r.get('mc_status'):mc=f"— [{r['mc_status']}]"
        cr='—' if r.get('mc_cross') is None else f"{r['mc_cross']:.5f}({r['mc_cross_err']*1e5:.0f})({r['mc_cross_domega']*1e5:.0f})"
        if r.get('mc') is None:diff='—'
        else:
            ok=r['nrg_err'] is not None and not math.isnan(r['mc_sys'])
            diff=f"{r['nrg']-r['mc']:+.5f} ("+(f"{abs(r['nrg']-r['mc'])/(r['mc_stat']+r['mc_sys']+r['nrg_err']):.2f}" if ok else '—')+')'
        bp='—' if r.get('series_bp') is None else f"{r['series_bp']:.5f} ({r['series_bp_spread']:.5f})"
        ref=r.get('series_bp') if r['eps']>0.02 else r['series_opt']
        nrg=f"{r['nrg']:.6f} ± {r['nrg_err']:.1e}" if r['nrg_err'] is not None else f"{r['nrg']:.6f} (not converged)"
        md.append(f"| {r['ds']:g} | {r['eps']:g} | {nrg} | {mc} | {cr} | {diff} | "
                  f"{r['series_opt']:.6f} ± {r['series_opt_err']:.1e} (to order {r['series_opt_order']-1}) | {bp} | "
                  f"{'—' if ref is None else format(r['nrg']-ref,'+.5f')} |")
    (a.out/'comparison.md').write_text('\n'.join(md)+'\n');print('\n'.join(md))


if __name__=='__main__':
    main()
