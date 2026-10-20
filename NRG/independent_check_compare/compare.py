"""Compare the independent NRG implementation (independent_check/out/c*.json) with the production records.

What is compared, per configuration:
  chain   rescaled on-site and hopping coefficients: independent (mpmath Lanczos with reorthogonalization of the
          discretized star) vs production (closed-form little q-Jacobi, lri_spin.config.chain_coefficients)
  alpha_c the critical coupling from the same bisection convention
  flow    the critical parity-gap flow g_n (early sites; late sites diverge by design when inputs differ by rounding)
  y_t     production: analytic alpha-tangent + window audit; independent: finite differences in alpha (three h)
          + independently written window audit; quality range and window-by-window Delta_E

Usage (from the NRG folder): python independent_check_compare/compare.py [--root DIR] [--ind DIR] [--out DIR]
  --root  folder holding data/records and code/lri_spin_boson_hpc/src (default: the NRG folder above this script)
  --ind   folder holding the independent outputs c1.json ... c8.json (default: <NRG>/independent_check/out)
  --out   where compare.json and compare.md are written (default: <NRG>/.work/independent_check_compare; the released files are never overwritten)
"""
import argparse,json,sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
CFG={'c1':'ds13/ds0.1_L3_K64_B10_N65','c2':'ds13/ds0.05_L3_K64_B10_N80','c3':'ds13/ds0.01_L3_K64_B10_N105',
     'c4':'ds13/ds0.2_L3_K64_B12_N65','c5':'ds13/ds0.249_L3_K64_B16_N65','c6':'ds13/ds0.001_L3_K48_B10_N250',
     'c7':'ds13/ds0.1_L2_K64_B10_N103','c8':'lambda_followup/ds0.15_L2.5_K64_B10_N78'}


def wde(w):
    for k in ('Delta_E','delta_E','DeltaE'):
        if k in w:return w[k]
    return 1-w['y_t']


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root',type=Path,default=HERE.parent);ap.add_argument('--ind',type=Path,default=HERE.parent/'independent_check'/'out')
    ap.add_argument('--out',type=Path,default=HERE.parent/'.work'/'independent_check_compare');a=ap.parse_args()
    sys.path.insert(0,str(a.root/'code'/'lri_spin_boson_hpc'/'src'))
    from lri_spin.config import chain_coefficients   # noqa: E402
    rows=[]
    for cid,rec in CFG.items():
        f=a.ind/f'{cid}.json'
        if not f.exists():rows.append({'id':cid,'missing':True});continue
        ind=json.loads(f.read_text());prod=json.loads((a.root/'data'/'records'/f'{rec}.json').read_text())['payload']
        c=prod['critical_flow']['config'];N=c['nsites']
        on,hop=chain_coefficients(c['s'],c['Lambda'],N)
        ie=np.array(ind['chain']['eps_rescaled'][:N],float);it=np.array([x if x is not None else 0. for x in ind['chain']['t_rescaled'][:N]])
        chain_eps=float(np.max(np.abs(ie-on)/np.abs(on)));chain_t=float(np.max(np.abs(it[1:]-hop[1:])/np.abs(hop[1:])))
        a_p=prod['critical_flow']['alpha'];a_i=ind['critical_search']['alpha_c']
        gp=np.array([r['odd_gap'] for r in prod['critical_flow']['records']]);gi=np.array(ind['critical_flow']['g'])
        dg=np.abs(gp-gi)
        first_div=int(np.argmax(dg>1e-8)) if np.any(dg>1e-8) else None
        q=prod['analysis']['quality_window_range'];pmid=None if q is None else (q[0]+q[1])/2
        pw={w['start']:w['Delta_E'] for w in prod['analysis']['windows']}
        per_h={}
        for h,wa in ind['window_audit'].items():
            s=wa['summary'];imid=s.get('delta_E_mid')
            common=[(st,pw[st],wde(w)) for w in wa['windows'] if not w.get('skipped') and (st:=w['start']) in pw]
            diffs=[abs(x-y) for _,x,y in common]
            per_h[h]={'n_quality':s['n_quality'],'range':[s.get('delta_E_min'),s.get('delta_E_max')],'mid':imid,
                      'mid_minus_production':None if imid is None or pmid is None else imid-pmid,
                      'windows_compared':len(common),'max_window_diff':max(diffs) if diffs else None,
                      'median_window_diff':float(np.median(diffs)) if diffs else None}
        rows.append({'id':cid,'record':rec,'s':c['s'],'Lambda':c['Lambda'],'keep':c['keep'],'nb':c['nb'],'N':N,
                     'chain_eps_maxrel':chain_eps,'chain_t_maxrel':chain_t,'chain_convergence':ind['chain'].get('convergence_max_rel_change'),
                     'alpha_prod':a_p,'alpha_ind':a_i,'alpha_reldiff':abs(a_i/a_p-1),
                     'flow_maxdiff_n_le_10':float(dg[:11].max()),'flow_first_site_diff_gt_1e-8':first_div,
                     'prod_n_quality':prod['analysis']['number_of_quality_windows'],'prod_range':q,'prod_mid':pmid,'ind':per_h,
                     'ind_status':ind.get('status'),'wall_seconds':ind.get('wall_seconds')})
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'compare.json').write_text(json.dumps(rows,indent=1)+'\n')
    md=['| id | config | chain ε̄ / t̄ max rel. diff | α_c production | α_c independent | rel. diff | g_n diff (n ≤ 10) | first n with |Δg| > 1e-8 | Δ_E production (n_q) | Δ_E independent, h = 1e-10 (n_q) | mid diff | max window diff (h = 1e-10) |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r.get('missing'):md.append(f"| {r['id']} | missing | | | | | | | | | | |");continue
        h=r['ind'].get('1e-10') or next(iter(r['ind'].values()))
        pr='—' if r['prod_mid'] is None else f"{r['prod_mid']:.6f} ({r['prod_n_quality']})"
        ir='—' if h['mid'] is None else f"{h['mid']:.6f} ({h['n_quality']})"
        md.append(f"| {r['id']} | s={r['s']:g}, Λ={r['Lambda']:g}, K={r['keep']}, n_b={r['nb']}, N={r['N']} | {r['chain_eps_maxrel']:.1e} / {r['chain_t_maxrel']:.1e} | "
                  f"{r['alpha_prod']:.15f} | {r['alpha_ind']:.15f} | {r['alpha_reldiff']:.1e} | {r['flow_maxdiff_n_le_10']:.1e} | {r['flow_first_site_diff_gt_1e-8']} | "
                  f"{pr} | {ir} | {'—' if h['mid_minus_production'] is None else format(h['mid_minus_production'],'+.1e')} | "
                  f"{'—' if h['max_window_diff'] is None else format(h['max_window_diff'],'.1e')} |")
    (a.out/'compare.md').write_text('\n'.join(md)+'\n');print('\n'.join(md))


if __name__=='__main__':
    main()
