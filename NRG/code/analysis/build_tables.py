"""Stage D: final Delta_E(Delta_sigma) with error budget, plus the LaTeX tables of the note that describe the runs.

Reads   data/summaries/*_summary.json, *_details.json, data/summaries/resources.json, data/job_accounting.txt
Writes  results/ds13_final.json, results/ds13_final_table.md, results/lambda_study.json
        note/tables/{example,keep_nb,lambda,lambda_shift,resources}_table.tex, note/tables/all_items.tex

Estimator (estimator.py; note Sec. 3.7). Each item gives a settled value (the window with the smallest residual +
variation) and a plateau drift. A point has a plateau if the drift of its central item is <= estimator.TAU; its value is
then the settled value. Without a plateau the value is the extrapolation of the local exponent (estimator.extrapolate).
Delta_sigma = 0.249, 0.24 and 0.225 are not converged in chain depth (author's decision of 13 October 2026): their
settled values are shown, but not used in any comparison, and no total error is quoted for them.

Error budget of a point (all from the same estimator, all at Lambda = 3 unless stated; added linearly):
  depth     plateau drift of the central item (Lambda=3, K=128, n_b=16); for an extrapolated point the larger of
            |extrapolated - settled| and the spread of the fits
  keep/nb   max - min over the Lambda=3 items with K >= 64 and n_b >= 10 (n_b = 10 excluded for Delta_sigma >= 0.2)
  Lambda    the larger of (a) max - min over the Lambda items at the largest K run, same n_b (Lambda = 2.5 and 3 at K=128;
            for Delta_sigma < 0.2 also Lambda = 4 at K = 64, assumed converged in K, and, where run, Lambda = 2 at K = 256; n_b = 16 for
            Delta_sigma >= 0.2, else 10) and (b) the shift of the Lambda = 2.5 value under its one K doubling (64 -> 128),
            always at n_b = 10, the only n_b run at Lambda = 2.5, K = 64
  total     depth + keep/nb + Lambda
The superseded quality-range midpoint and its budget (used until 13 October 2026) are kept under "midpoint".
The cross-check fits of crosscheck.py (not adopted) are kept under "crosschecks" for the central item.
Extrapolations that are not determined (estimator.OMEGA_MIN) are written as null.
"""
import json,math
from pathlib import Path
from estimator import TAU,estimate,value,depth_error
import crosscheck

ROOT=Path(__file__).resolve().parents[2]
SUM=ROOT/'data'/'summaries';RES=ROOT/'results';TAB=ROOT/'note'/'tables'
DS=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]
NOT_CONVERGED=(0.249,0.24,0.225)
PILOT=[0.2,0.1,0.05]


def load(name,kind='summary'):
    return json.loads((SUM/f'{name}_{kind}.json').read_text())


rows={c:load(c) for c in ('example_K64_B10','ds13','lambda_pilot','lambda_followup')}
ALL=[dict(r,campaign=c) for c,rs in rows.items() for r in rs if c!='example_K64_B10']
EST={};DET={}
for c in ('ds13','lambda_pilot','lambda_followup'):
    lam={r['id']:r['Lambda'] for r in rows[c]}
    for d in load(c,'details'):EST[d['id']]=estimate(d,lam[d['id']]);DET[d['id']]=d
for r in ALL:   # the settled window is the analyzer's selected window stored in every record
    if EST[r['id']]['settled_start']!=r['sel_start'] or EST[r['id']]['settled']!=r['sel']:raise SystemExit(f"{r['id']}: settled != selected")


def get(ds,L,K,B):
    m=[r for r in ALL if r['ds']==ds and r['Lambda']==L and r['keep']==K and r['nb']==B]
    if len(m)>1:raise SystemExit(f'duplicate item for {ds,L,K,B}')
    return m[0] if m else None


def mid(r):
    return None if r is None else r['q_mid']


def hw(r):
    return None if r is None or r['q_mid'] is None else (r['q_hi']-r['q_lo'])/2


def is_extrapolated(ds):
    return ds not in NOT_CONVERGED and not EST[get(ds,3,128,16)['id']]['plateau']


def val(r,ds):
    return None if r is None else value(EST[r['id']],is_extrapolated(ds))


def lambda_items(ds):
    B=16 if ds>=0.2 else 10
    cand=[('2.5',get(ds,2.5,128,B)),('3',get(ds,3,128,B))]
    if ds<0.2:cand+=[('4',get(ds,4,64,10)),('2',get(ds,2,256,10))]
    return {k:r for k,r in cand if r is not None}


def midpoint_budget(ds):
    """The superseded estimator (until 13 October 2026), recomputed exactly as it was published."""
    c=get(ds,3,128,16);B=16 if ds>=0.2 else 10
    conv=[r for r in ALL if r['ds']==ds and r['Lambda']==3 and r['keep']>=64 and r['nb']>=10 and r['q_mid'] is not None
          and not (r['nb']==10 and ds>=0.2) and r['campaign']=='ds13']
    spread=max(mid(r) for r in conv)-min(mid(r) for r in conv);sh25=mid(get(ds,2.5,128,B))-mid(get(ds,3,128,B))
    return {'Delta_E':mid(c),'window_halfwidth':hw(c),'keep_nb_spread':spread,'Lambda25_shift':sh25,
            'total_uncertainty':math.sqrt(hw(c)**2+spread**2+(2*sh25)**2)}


def final_table():
    out=[]
    for ds in DS:
        c=get(ds,3,128,16);e=EST[c['id']];nc=ds in NOT_CONVERGED;ext=is_extrapolated(ds)
        conv=[r for r in ALL if r['ds']==ds and r['Lambda']==3 and r['keep']>=64 and r['nb']>=10
              and not (r['nb']==10 and ds>=0.2) and r['campaign']=='ds13']
        dK=max(val(r,ds) for r in conv)-min(val(r,ds) for r in conv)
        lam={k:val(r,ds) for k,r in lambda_items(ds).items()}
        spreadL=max(lam.values())-min(lam.values())
        kd=abs(val(get(ds,2.5,64,10),ds)-val(get(ds,2.5,128,10),ds))
        dL=max(spreadL,kd);depth=None if nc else depth_error(e,ext);central=val(c,ds)
        x=e['extrapolation'];d=DET[c['id']]
        cc={'late':crosscheck.late(d,3.0,c['nsites'],e['settled'],ds),
            'crossover':crosscheck.crossover(d,3.0,c['nsites'],e['settled']) if ds>=0.2 else None}
        out.append({'ds':ds,'s':c['s'],'eps':round(2*c['s']-1,6),
                    'status':'not converged' if nc else 'final',
                    'estimator':'settled (not converged)' if nc else ('extrapolated' if ext else 'plateau'),
                    'Delta_E':central,'depth':depth,'keep_nb':dK,'Lambda':dL,'Lambda_spread':spreadL,'Lambda25_K_doubling':kd,
                    'Lambda_values':lam,'total':None if nc else depth+dK+dL,
                    'settled':e['settled'],'settled_window':[e['settled_start'],e['settled_stop']],'plateau_drift':e['plateau_drift'],
                    'plateau':e['plateau'],'drift_per_site':e['drift_per_site'],
                    'extrapolated':x['value'],'extrapolation_spread':x['spread'],'extrapolation_fits':x['fits'],
                    'extrapolation_status':x['status'],'crosschecks':cc,
                    'Lambda2_shift_K64':None if get(ds,2,64,10) is None else val(get(ds,2,64,10),ds)-val(get(ds,3,64,10),ds),
                    'Lambda4_shift_K64':None if get(ds,4,64,10) is None else val(get(ds,4,64,10),ds)-val(get(ds,3,64,10),ds),
                    'n_quality':c['n_quality'],'alpha_c':c['alpha_c'],'y_t':1-central,
                    'one_loop':(2-c['s'])/3,'kosterlitz_y_t':math.sqrt(2*(1-c['s'])),'midpoint':midpoint_budget(ds)})
    return out


def lambda_study():
    out=[]
    for ds in PILOT:
        for L in (1.5,2,2.5,3,4):
            for K in (64,128,192,256):
                for B in (10,16):
                    r=get(ds,L,K,B)
                    if r is None or (B==16 and L!=1.5):continue
                    e=EST[r['id']]
                    out.append({'ds':ds,'Lambda':L,'keep':K,'nb':B,'nsites':r['nsites'],'value':val(r,ds),'settled':e['settled'],
                                'plateau_drift':e['plateau_drift'],'extrapolated':e['extrapolation']['value'],'mid':mid(r),'hw':hw(r),
                                'n_quality':r['n_quality'],'alpha_c':r['alpha_c'],'campaign':r['campaign']})
    return out


def f5(x):return '--' if x is None else f'{x:.5f}'
def f6(x):return '--' if x is None else f'{x:.6f}'
def sgn(x,n=4):return '--' if x is None else (f'{x:+.{n}f}'.replace('+','$+$').replace('-','$-$'))
def tt(s):return r'\texttt{'+s.replace('_',r'\_')+'}'
def e4(x):return '--' if x is None else f'{x*1e4:+.2f}'.replace('+','$+$').replace('-','$-$')


def write(name,text):
    TAB.mkdir(parents=True,exist_ok=True);(TAB/name).write_text(text)


def tex_example():
    L=[r'\begin{tabular}{llllll}',r'\toprule',r'item & $\alpha_c$ & bisection & terminal residual & quality windows & $\Delta_E$ range (settled) \\',r'\midrule']
    for r in rows['example_K64_B10']:
        L.append(f"{tt(r['id'])} & {r['alpha_c']:.14f} & {r['bisect']} & {sgn(r['terminal_residual'],3)} & {r['n_quality']} & "
                 f"[{r['q_lo']:.5f}, {r['q_hi']:.5f}] ({r['sel']:.5f})\\\\")
    L+=[r'\bottomrule',r'\end{tabular}']
    write('example_table.tex','\n'.join(L)+'\n')


def tex_keep_nb(F):
    cen={x['ds']:x['Delta_E'] for x in F}
    keeps=(48,64,96,128,160,192);nbs=(8,10,12,16,20,24)
    head=' & '.join([f'$K{{=}}{k}$' for k in keeps]+[f'$n_b{{=}}{b}$' for b in nbs])
    L=[r'\begin{tabular}{l'+'r'*(len(keeps)+len(nbs))+'}',r'\toprule',
       r' & \multicolumn{6}{c}{$K$ scan ($n_b=10$)} & \multicolumn{6}{c}{$n_b$ scan ($K=64$)}\\',
       r'\cmidrule(lr){2-7}\cmidrule(lr){8-13}',r'$\Delta_\sigma$ & '+head+r'\\',r'\midrule']
    for ds in DS:
        cells=[]
        for r in [get(ds,3,k,10) for k in keeps]+[get(ds,3,64,b) for b in nbs]:
            cells.append('' if r is None else e4(val(r,ds)-cen[ds]))
        L.append(f'{ds:g} & '+' & '.join(cells)+r'\\')
    L+=[r'\bottomrule',r'\end{tabular}']
    write('keep_nb_table.tex','\n'.join(L)+'\n')


def tex_lambda(LS):
    L=[r'\begin{tabular}{llllllll}',r'\toprule',
       r'$\Delta_\sigma$ & $\Lambda$ & $K$ & $n_b$ & $N$ & $\Delta_E$ (this note) & old midpoint (half-width) & $\alpha_c$ \\',r'\midrule']
    last=None
    for x in LS:
        if last is not None and x['ds']!=last:L.append(r'\midrule')
        last=x['ds']
        L.append(f"{x['ds']:g} & {x['Lambda']:g} & {x['keep']} & {x['nb']} & {x['nsites']} & {f6(x['value'])} & {f5(x['mid'])} ({f5(x['hw'])}) & "
                 f"{x['alpha_c']:.10f}\\\\")
    L+=[r'\bottomrule',r'\end{tabular}']
    write('lambda_table.tex','\n'.join(L)+'\n')


def tex_lambda_all(F):
    L=[r'\begin{tabular}{llllll}',r'\toprule',
       r' & \multicolumn{3}{c}{$10^4\times$ shift relative to $\Lambda=3$} & \multicolumn{2}{c}{at $\Lambda=2.5$}\\',r'\cmidrule(lr){2-4}\cmidrule(lr){5-6}',
       r'$\Delta_\sigma$ & $\Lambda{=}2$, $K{=}64$ & $\Lambda{=}2.5$, $K{=}128$ & $\Lambda{=}4$, $K{=}64$ & $10^4\times(K{=}64$ minus $K{=}128)$ & $n_q$\\',r'\midrule']
    for x in F:
        ds=x['ds'];B=16 if ds>=0.2 else 10;a64=get(ds,2.5,64,10);a=get(ds,2.5,128,10)
        sh25=val(get(ds,2.5,128,B),ds)-val(get(ds,3,128,B),ds)
        L.append(f"{ds:g} & {e4(x['Lambda2_shift_K64'])} & {e4(sh25)} & {e4(x['Lambda4_shift_K64'])} & {e4(val(a64,ds)-val(a,ds))} & {a['n_quality']}\\\\")
    L+=[r'\bottomrule',r'\end{tabular}']
    write('lambda_shift_table.tex','\n'.join(L)+'\n')


def tex_resources():
    acct={}
    for line in (ROOT/'data'/'job_accounting.txt').read_text().splitlines()[2:]:
        p=line.split()
        if p:acct[p[0]]={'name':p[1],'state':p[3],'start':p[4],'elapsed':p[5],'node':p[7]}
    purpose={'569091':'validation (build)','569093':'smoke lane','569096':'USR1 drill, gen.~1','569097':'cross-node ownership drill',
             '569098':'USR1 drill, gen.~2 (resumed)','569134':'re-validation (fix round 1)','569135':'second smoke',
             '569161':'validation of final code','569565':'example manifest','569572':'ds13 lane 0','569573':'ds13 lane 1',
             '569574':'ds13 lane 2','569575':'ds13 lane 3','569576':'ds13 lane 4','569602':'$\\Lambda$ pilot',
             '569626':'$\\Lambda$ follow-up lane 0','569627':'$\\Lambda$ follow-up lane 1','569640':'follow-up lane 0, gen.~2',
             '569641':'follow-up lane 1, gen.~2'}
    res={r['job']:r for r in json.loads((SUM/'resources.json').read_text())}
    L=[r'\begin{tabular}{llllllll}',r'\toprule',r'job & purpose & state & start & elapsed & node & items & thread-h\\',r'\midrule']
    for j,a in acct.items():
        r=res.get(j)
        items='' if r is None else f"{r['items_ended']}/{r['items_started']}"
        th='' if r is None else f"{r['core_hours']:.1f}"
        state=a['state'].replace('_',r'\_')   # outside the f-string: Python < 3.12 forbids backslashes there
        L.append(f"{j} & {purpose.get(j,a['name'])} & {state} & {a['start'].replace('T',' ')} & {a['elapsed']} & {a['node']} & {items} & {th}\\\\")
    L+=[r'\bottomrule',r'\end{tabular}']
    write('resources_table.tex','\n'.join(L)+'\n')


def tex_all_items():
    L=[r'\begin{longtable}{@{}llrllllr@{}}',r'\toprule',
       r'campaign & item & $\alpha_c$ & $n_q$ & $\Delta_E$ quality range & settled & plateau drift & $\max p_{\rm edge}$\\',r'\midrule',r'\endhead']
    tag={'ds13':'D','lambda_pilot':'P','lambda_followup':'F'}
    for r in sorted(ALL,key=lambda r:(-r['ds'],r['Lambda'],r['nb'],r['keep'])):
        rng='--' if r['q_lo'] is None else f"[{r['q_lo']:.5f}, {r['q_hi']:.5f}]"
        L.append(f"{tag[r['campaign']]} & {tt(r['id'])} & {r['alpha_c']:.10f} & {r['n_quality']} & {rng} & {f6(EST[r['id']]['settled'])} & "
                 f"{EST[r['id']]['plateau_drift']:.0e} & {r['max_edge']:.0e}\\\\")
    L+=[r'\bottomrule',r'\end{longtable}']
    write('all_items.tex','\n'.join(L)+'\n')


def main():
    RES.mkdir(parents=True,exist_ok=True)
    F=final_table();LS=lambda_study()
    (RES/'ds13_final.json').write_text(json.dumps(F,indent=1)+'\n')
    (RES/'lambda_study.json').write_text(json.dumps(LS,indent=1)+'\n')
    g=lambda v:'n.d.' if v is None else f'{v:.6f}'
    md=[f'Estimator: settled window; plateau if the plateau drift is <= {TAU:g}; otherwise extrapolated (see code/analysis/estimator.py).',
        'Errors are added linearly. Not-converged points: settled value shown, no total error, not used in any comparison.','',
        '| Δσ | s | estimator | Δ_E | depth | keep/nb | Λ | total | settled | extrapolated | old midpoint (old total) |',
        '|---|---|---|---|---|---|---|---|---|---|---|']
    for x in F:
        m=x['midpoint']
        md.append(f"| {x['ds']:g} | {x['s']:g} | {x['estimator']} | {x['Delta_E']:.6f} | {'—' if x['depth'] is None else format(x['depth'],'.1e')} | "
                  f"{x['keep_nb']:.1e} | {x['Lambda']:.1e} | {'—' if x['total'] is None else format(x['total'],'.1e')} | {g(x['settled'])} | "
                  f"{g(x['extrapolated'])} | {m['Delta_E']:.6f} ({m['total_uncertainty']:.1e}) |")
    (RES/'ds13_final_table.md').write_text('\n'.join(md)+'\n')
    tex_example();tex_keep_nb(F);tex_lambda(LS);tex_lambda_all(F);tex_resources();tex_all_items()
    print('\n'.join(md))


if __name__=='__main__':
    main()
