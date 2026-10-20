"""Window-by-window Delta_E comparison restricted to windows where the finite-difference derivative is trustworthy.

A window's finite-difference Delta_E is trusted when two neighbouring step sizes h agree to < 1e-6 (early windows:
h = 1e-9 vs 1e-10 limited by rounding; late windows: 1e-10 vs 1e-11 before nonlinearity). Its value is the mean of
the best-agreeing pair. Writes trusted_windows.json / .md.

Usage (from the NRG folder): python independent_check_compare/trusted_windows.py [--root DIR] [--ind DIR] [--out DIR]
(same options as compare.py).
"""
import argparse,json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
CFG={'c1':'ds13/ds0.1_L3_K64_B10_N65','c2':'ds13/ds0.05_L3_K64_B10_N80','c3':'ds13/ds0.01_L3_K64_B10_N105',
     'c4':'ds13/ds0.2_L3_K64_B12_N65','c5':'ds13/ds0.249_L3_K64_B16_N65','c6':'ds13/ds0.001_L3_K48_B10_N250',
     'c7':'ds13/ds0.1_L2_K64_B10_N103','c8':'lambda_followup/ds0.15_L2.5_K64_B10_N78'}
def wde(w):return w['Delta_E'] if 'Delta_E' in w else w.get('delta_E',1-w['y_t'])
ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
ap.add_argument('--root',type=Path,default=HERE.parent);ap.add_argument('--ind',type=Path,default=HERE.parent/'independent_check'/'out')
ap.add_argument('--out',type=Path,default=HERE.parent/'.work'/'independent_check_compare');A=ap.parse_args()
PKG=A.root;IND=A.ind
rows=[];md=['| id | production windows | trusted FD windows | production quality windows covered | max \\|ΔΔ_E\\| (trusted) | median \\|ΔΔ_E\\| | quality range, production | quality range, independent (trusted windows) |','|---|---|---|---|---|---|---|---|']
for cid,rec in CFG.items():
    ind=json.loads((IND/f'{cid}.json').read_text());prod=json.loads((PKG/'data'/'records'/f'{rec}.json').read_text())['payload']
    pw={w['start']:w for w in prod['analysis']['windows']}
    hs=['1e-09','1e-10','1e-11'];iw={h:{w['start']:w for w in ind['window_audit'][h]['windows'] if not w.get('skipped')} for h in hs}
    out=[]
    for st,p in sorted(pw.items()):
        vals=[iw[h][st] for h in hs if st in iw[h]]
        if len(vals)<3:continue
        d=[wde(v) for v in vals];pairs=[(abs(d[0]-d[1]),(d[0]+d[1])/2,0),(abs(d[1]-d[2]),(d[1]+d[2])/2,1)]
        best=min(pairs)
        if best[0]<1e-6:
            q_p=p['gap_relative_variation']<.005 and p['log_response_residual']<.003
            w=vals[best[2]];q_i=w.get('variation',w.get('gap_relative_variation',1))<.005 and max(vals[best[2]].get('residual',vals[best[2]].get('log_response_residual',1)),vals[best[2]+1].get('residual',vals[best[2]+1].get('log_response_residual',1)))<.003
            out.append({'start':st,'prod':p['Delta_E'],'ind':best[1],'diff':best[1]-p['Delta_E'],'prod_quality':q_p,'ind_quality':q_i})
    qp=[w for w in pw.values() if w['gap_relative_variation']<.005 and w['log_response_residual']<.003]
    covered=sum(1 for o in out if o['prod_quality'])
    qi=[o['ind'] for o in out if o['ind_quality']]
    diffs=[abs(o['diff']) for o in out]
    r={'id':cid,'n_prod_windows':len(pw),'n_trusted':len(out),'prod_quality':len(qp),'covered':covered,
       'max_diff':max(diffs) if diffs else None,'median_diff':float(np.median(diffs)) if diffs else None,
       'prod_range':prod['analysis']['quality_window_range'],'ind_range':[min(qi),max(qi)] if qi else None,'windows':out}
    rows.append(r)
    f=lambda x:'—' if x is None else f'[{x[0]:.6f}, {x[1]:.6f}]'
    md.append(f"| {cid} | {len(pw)} | {len(out)} | {covered}/{len(qp)} | {'—' if r['max_diff'] is None else format(r['max_diff'],'.1e')} | "
              f"{'—' if r['median_diff'] is None else format(r['median_diff'],'.1e')} | {f(r['prod_range'])} | {f(r['ind_range'])} |")
A.out.mkdir(parents=True,exist_ok=True)
(A.out/'trusted_windows.json').write_text(json.dumps(rows,indent=1)+'\n');(A.out/'trusted_windows.md').write_text('\n'.join(md)+'\n');print('\n'.join(md))
