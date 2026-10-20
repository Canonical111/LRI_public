"""Stage G: the tables and in-text numbers of the public note that build_tables.py does not write.

Reads   results/ds13_final.json, data/summaries/*_summary.json, *_details.json, resources.json, data/job_accounting.txt
        independent_check_compare/compare.json, trusted_windows.json                             (independent solver)
        method_comparison/comparison.json                                                        (MC and epsilon series)
Writes  note/tables/numbers.tex        one \\newcommand per number quoted in the running text of the note
        note/tables/headline_table.tex final values with status and the external test of each point (Sec. 1)
        note/tables/budget_table.tex   error budget per point (Sec. 4)
        note/tables/extrap_table.tex   settled value, extrapolation and fits of the points without a plateau (Sec. 7)
        note/tables/indep_table.tex    second implementation against production (Sec. 8.1)
        note/tables/series_table.tex   epsilon expansion near s = 1/2 (Sec. 8.2)
        note/tables/mc_table.tex       1D cluster Monte Carlo (Sec. 8.3)
        note/tables/s1_table.tex       y_t near s = 1 against the leading and next-to-leading forms (Sec. 7)
        note/tables/midpoint_table.tex the superseded midpoint estimator against the present one (App. E)

Usage   python code/analysis/note_numbers.py [--root DIR] [--check]
        --root   folder with the layout above (default: two levels above this script)
        --check  regenerate in memory and compare with the files in note/tables/; also check that every \\nrg macro
                 used in note/lri_nrg_1d_note.tex is defined and every \\input{tables/...} exists. Exit 1 on any difference.

Status of the points (author's decision, 13 October 2026): Delta_sigma = 0.249, 0.24 and 0.225 are not converged in
chain depth; their settled values are shown, carry no total error and are used in no comparison. Rounding of value(error):
the error with two significant digits if its three leading digits are 100-354, else one; 950-999 is rounded up to the next
power of ten with two digits (PDG convention); ROUND_HALF_UP on the decimal representation. Numbers quoted in the note as
bounds ("at most", "agree to") are rounded up (sci_up), lower bounds down (sci_dn), so the statements stay true.
"""
import argparse,json,math,re,statistics,sys
import numpy as np
from decimal import Decimal,ROUND_HALF_UP,ROUND_CEILING,ROUND_FLOOR
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from estimator import TAU,SPANS,estimate,value,local_exponent   # noqa: E402

DS=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]
PILOT=[0.2,0.1,0.05]
# Published 1D LRI Monte Carlo values of Delta_eps on the grid of this study: Uzelac, Glumac and Anicic, PRE 63, 037101
# (2001), as tabulated in the MC note of this repository (Table "d = 1 results", column "published MC").
UGA={0.05:(0.60,0.01),0.1:(0.53,0.02),0.15:(0.49,0.02),0.2:(0.50,0.02)}


# ---------------------------------------------------------------- formatting
def q(x,nd):return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd),rounding=ROUND_HALF_UP)


def paren(val,err):
    """val(err), PDG rounding of err."""
    e=Decimal(repr(float(err)));lead=int(f'{e:.2e}'.replace('.','')[:3])
    if lead>=950:e=Decimal(1).scaleb(e.adjusted()+1);sig=2   # 0.00096 -> 0.0010
    else:sig=2 if lead<355 else 1
    nd=-(e.adjusted()-sig+1);eq=q(e,nd)
    return f'{q(val,nd)}({int(eq.scaleb(nd))})'


def paren2(val,err):
    """val(err) with two significant digits of err (the rounding used until 13 October 2026)."""
    e=Decimal(repr(float(err)));nd=-(e.adjusted()-1)
    return f'{q(val,nd)}({int(q(err,nd).scaleb(nd))})'


def sci(x,sig=2,sign=False):
    """x as a\\times10^{b} with sig significant digits (plain decimal for 1e-2 <= |x| < 10)."""
    if x==0:return '0'
    s=f'{x:+.{sig-1}e}' if sign else f'{x:.{sig-1}e}'
    m,e=s.split('e');e=int(e)
    if -2<=e<=0:return f'{x:+.{sig-1-e}f}' if sign else f'{x:.{sig-1-e}f}'
    return f'{m}\\times10^{{{e}}}'


def _directed(x,sig,mode):
    d=Decimal(repr(float(x)));return float(d.quantize(Decimal(1).scaleb(d.adjusted()-sig+1),rounding=mode))


def sci_up(x,sig=2):
    """An upper bound: x > 0 rounded up to sig significant digits."""
    return sci(_directed(x,sig,ROUND_CEILING),sig)


def sci_dn(x,sig=2):
    """A lower bound: x > 0 rounded down to sig significant digits."""
    return sci(_directed(x,sig,ROUND_FLOOR),sig)


def up2(x):return f'{math.ceil(x*100-1e-9)/100:.2f}'


def e4(x,nd=1,sign=False):
    v=q(x*1e4,nd);return f'{v:+}' if sign else f'{v}'


def fx(x,nd):return f'{q(x,nd)}'


def rng(lo,hi,sig=2):
    """(a--b)\\times10^{e} with the exponent of hi."""
    e=Decimal(repr(float(hi))).adjusted();k=sig-1
    return f'({q(lo*10**-e,k)}\\text{{--}}{q(hi*10**-e,k)})\\times10^{{{e}}}'


def name(ds):
    return {0.249:'TwoFortyNine',0.24:'TwoForty',0.225:'TwoTwentyFive',0.2:'TwoHundred',0.175:'OneSeventyFive',
            0.15:'OneFifty',0.125:'OneTwentyFive',0.1:'OneHundred',0.075:'SeventyFive',0.05:'Fifty',
            0.025:'TwentyFive',0.01:'Ten',0.001:'One'}[ds]


# ---------------------------------------------------------------- data
class Data:
    def __init__(s,root):
        s.root=root
        s.F={x['ds']:x for x in json.loads((root/'results'/'ds13_final.json').read_text())}
        S=lambda c,k='summary':json.loads((root/'data'/'summaries'/f'{c}_{k}.json').read_text())
        s.example=S('example_K64_B10')
        s.all=[dict(r,campaign=c) for c in ('ds13','lambda_pilot','lambda_followup') for r in S(c)]
        lam={r['id']:r['Lambda'] for r in s.all}
        s.det={d['id']:d for c in ('ds13','lambda_pilot','lambda_followup') for d in S(c,'details')}
        s.est={i:estimate(d,lam[i]) for i,d in s.det.items()}
        s.res=json.loads((root/'data'/'summaries'/'resources.json').read_text())
        s.cfg={it['id']:it['config'] for f in sorted((root/'inputs'/'manifests').glob('*.json')) for it in json.loads(f.read_text())['items']}
        s.events=[e for f in sorted((root/'data'/'lane_logs').glob('*/events.jsonl')) for e in map(json.loads,f.read_text().splitlines())
                  if e.get('event')=='end' and e.get('rc')==0 and e['id'] in s.cfg]
        s.acct=[l.split() for l in (root/'data'/'job_accounting.txt').read_text().splitlines()[2:] if l.strip()]
        s.cmp={r['id']:r for r in json.loads((root/'independent_check_compare'/'compare.json').read_text())}
        s.tw={r['id']:r for r in json.loads((root/'independent_check_compare'/'trusted_windows.json').read_text())}
        s.mc={r['ds']:r for r in json.loads((root/'method_comparison'/'comparison.json').read_text())}

    def final(s,ds):return s.F[ds]['status']=='final'

    def get(s,ds,L,K,B):
        m=[r for r in s.all if r['ds']==ds and r['Lambda']==L and r['keep']==K and r['nb']==B]
        if len(m)>1:raise SystemExit(f'duplicate item {ds,L,K,B}')
        return m[0] if m else None

    def val(s,ds,L,K,B):
        """The estimator of point ds applied to one item (None if not run)."""
        r=s.get(ds,L,K,B);return None if r is None else value(s.est[r['id']],s.F[ds]['estimator']=='extrapolated')

    def mid(s,ds,L,K,B):
        r=s.get(ds,L,K,B);return None if r is None else r['q_mid']


# C^SR_1(1) .. C^SR_6(1) of the short-range dual series Delta_E = 1 + sum_n C^SR_n(1) Delta_sigma^(n/2) (closed forms of the
# accompanying paper; the same as in verify/verify.py)
Z2,Z3,Z4,Z5=math.pi**2/6,1.2020569031595942,math.pi**4/90,1.0369277551433699
SR_C=(-2.,.5,39/16+2*Z2,4-4*Z2-8*Z3,11249/1024-361/16*Z2+24*Z3+49/2*Z4,26-38*Z2+104*Z3-80*Z4-272*Z5+112*Z2*Z3)


def sr_diff(v,ds,n):
    """Delta_E minus the dual series through C^SR_n(1)."""
    return v-1-sum(c*ds**((k+1)/2) for k,c in enumerate(SR_C[:n]))


def plateau_variant(detail,hfac,width):
    """Plateau drift (and settled value) with h = ceil(hfac w) and, if width is given, windows of that many sites refitted
    from the per-site data with the window rule of the analyzer (Sec. 3.6). Used only to report the sensitivity."""
    if width is None:
        W=detail['windows']
    else:
        lg=np.asarray(detail['log_abs_d_alpha_odd_gap'],float);g=np.asarray(detail['odd_gap'],float);N=len(lg);W=[]
        for st in range(max(8,int(0.13*N)),int(0.76*N)-width):
            n=np.arange(st,st+width);y=lg[st:st+width];gg=g[st:st+width]
            if np.any(gg<=0) or not np.all(np.isfinite(y)):continue
            p=np.polyfit(n,y,1)
            W.append({'start':st,'stop':st+width,'Delta_E':1-p[0]/math.log(3.0),'log_response_residual':float(np.max(np.abs(np.polyval(p,n)-y))),
                      'gap_relative_variation':float((gg.max()-gg.min())/abs(gg.mean()))})
    sel=min(W,key=lambda w:w['log_response_residual']+w['gap_relative_variation']);h=math.ceil((sel['stop']-sel['start'])*hfac)
    return max(abs(w['Delta_E']-sel['Delta_E']) for w in W if abs(w['start']-sel['start'])<=h),sel['Delta_E']


def ref_series(r):
    """The epsilon-series reference: partial sum at eps <= 0.02, Borel-Pade beyond; with its error."""
    return (r['series_bp'],r['series_bp_spread']) if r['eps']>0.02 else (r['series_opt'],r['series_opt_err'])


def accepted(r):return r.get('mc') is not None and r['mc_status'].startswith('ACCEPTED')


def hours(t):
    d,_,t=t.rpartition('-');h,m,sec=(int(x) for x in t.split(':'));return (int(d) if d else 0)*24+h+m/60+sec/3600


# ---------------------------------------------------------------- macros
def macros(D):
    M=[]
    def add(n,v,src):M.append((n,v,src))
    F=D.F;FIN=[d for d in DS if D.final(d)];NC=[d for d in DS if not D.final(d)]
    PL=[d for d in FIN if F[d]['estimator']=='plateau'];EX=[d for d in FIN if F[d]['estimator']=='extrapolated']
    # campaign size and cost
    n={c:sum(1 for r in D.all if r['campaign']==c) for c in ('ds13','lambda_pilot','lambda_followup')}
    add('nItems',str(len(D.example)+sum(n.values())),'number of production records (all campaigns)')
    add('nItemsDs',str(n['ds13']),'ds13 items');add('nItemsPilot',str(n['lambda_pilot']),'Lambda pilot items')
    add('nItemsFollowup',str(n['lambda_followup']),'Lambda follow-up items');add('nItemsExample',str(len(D.example)),'example items')
    add('nItemsAll',str(sum(n.values())),'records listed in App. D (all but the example items)')
    add('threadHours',f"{sum(r['core_hours'] for r in D.res):.0f}",'sum of item wall time x threads, resources.json')
    nh=sum(hours(a[5]) for a in D.acct)
    add('nodeHours',f'{nh:.0f}','sum of the elapsed times of all jobs (one whole node each), job_accounting.txt')
    add('coreHoursCharged',f'{round(64*nh,-1):.0f}','64 cores x node-hours')
    add('longestItem',f"{max(r['longest_item_hours'] for r in D.res):.1f}",'longest single item [h], resources.json')
    add('peakRSS',f"{max(r['max_peak_rss_mib'] for r in D.res):.0f}",'largest per-item peak RSS [MiB], resources.json')
    rows=D.example+D.all
    add('maxEigRes',sci_up(max(r['max_eigen_residual'] for r in rows)),'largest checked eigen-residual over all records')
    add('maxOrth',sci_up(max(r['max_orthogonality'] for r in rows)),'largest checked orthogonality error over all records')
    # final table: per point and ranges
    for ds in DS:
        x=F[ds];nm=name(ds)
        add(f'DE{nm}',paren(x['Delta_E'],x['total']) if x['total'] is not None else fx(x['Delta_E'],4),f'Delta_E (total) at Ds={ds}')
        add(f'nq{nm}',str(x['n_quality']),f'quality windows of the central item at Ds={ds}')
    low=[F[d]['total'] for d in FIN if 0.01<=d<=0.125]
    add('errLow',rng(min(low),max(low)),'range of total errors for 0.01 <= Ds <= 0.125')
    for d in (0.15,0.001,0.175,0.2):add(f'err{name(d)}',sci(F[d]['total'],2),f'total error at Ds={d}')
    m=min(FIN,key=lambda d:F[d]['Delta_E'])
    add('DEmin',fx(F[m]['Delta_E'],4),f'smallest final Delta_E (at Ds={m})')
    add('DEminAt',f'{m:g}','where')
    # estimator
    add('tau',sci(TAU,1),'plateau threshold');add('spans',', '.join(f'{s:g}' for s in SPANS),'fit ranges in l')
    add('nPlateau',str(len(PL)),'final points with a plateau');add('nExtrap',str(len(EX)),'final points extrapolated')
    drift_pl=max(F[d]['plateau_drift'] for d in PL);drift_no=min(F[d]['plateau_drift'] for d in DS if not F[d]['plateau'])
    add('driftMaxPlateau',sci_up(drift_pl,3),'largest plateau drift among plateau points')
    add('driftMaxPlateauAt',f"{max(PL,key=lambda d:F[d]['plateau_drift']):g}",'where')
    add('driftMinNoPlateau',sci_dn(drift_no,3),'smallest plateau drift among points without a plateau')
    add('driftMinNoPlateauAt',f"{min([d for d in DS if not F[d]['plateau']],key=lambda d:F[d]['plateau_drift']):g}",'where')
    small=[d for d in PL if d<=0.125];add('driftMaxLow',sci_up(max(F[d]['plateau_drift'] for d in small),2),'largest plateau drift, Ds<=0.125')
    late=lambda d:F[d]['crosschecks']['late']['value']-F[d]['Delta_E']
    low=[d for d in PL if d<=0.125]
    add('lateMaxLow',sci_up(max(abs(late(d)) for d in low),1),'max |late fit - value|, plateau points Ds<=0.125')
    for d in (0.15,0.175,0.2,0.001):add(f'late{name(d)}',sci(late(d),2,sign=True),f'late fit - value at Ds={d}')
    add('depthOne',sci(F[0.001]['depth'],2),'delta_depth at Ds=0.001')
    add('lateOutside',', '.join(f'{d:g}' for d in FIN if abs(late(d))>F[d]['depth']),'final points where |late fit - value| > delta_depth')
    add('lateOmTen',fx(F[0.01]['crosschecks']['late']['omega'],3),'omega of the late fit at Ds=0.01')
    add('nloOmTen',fx(math.sqrt(0.04)+0.02/4,3),'sqrt(2 delta) + delta/4 at delta = 0.02')
    for d in (0.249,0.24,0.225,0.2):
        c=F[d]['crosschecks']['crossover'];nm=name(d);ref=ref_series(D.mc[d])[0]
        add(f'cross{nm}',fx(c['value'],5),f'crossover fit (median) at Ds={d}')
        add(f'crossLo{nm}',fx(c['min'],5),'smallest accepted fit');add(f'crossHi{nm}',fx(c['max'],5),'largest');add(f'crossN{nm}',str(c['n']),'accepted fits')
        add(f'crossExc{nm}',sci(c['value']-ref,1,sign=True),'median - series')
        add(f'crossExcLo{nm}',sci(c['min']-ref,1,sign=True),'smallest accepted fit - series');add(f'crossExcHi{nm}',sci(c['max']-ref,1,sign=True),'largest - series')
    om=lambda d:statistics.median(f['omega'] for f in F[d]['extrapolation_fits'])
    for d in EX+NC:
        nm=name(d)
        add(f'om{nm}',fx(om(d),3),f'median fitted omega at Ds={d}')
        add(f'set{nm}',fx(F[d]['settled'],6),f'settled value at Ds={d}');add(f'ext{nm}',fx(F[d]['extrapolated'],6),f'extrapolated at Ds={d}')
        add(f'extShift{nm}',sci(F[d]['extrapolated']-F[d]['settled'],2,sign=True),f'extrapolated - settled at Ds={d}')
        add(f'extSpread{nm}',sci(F[d]['extrapolation_spread'],1),f'spread of the three fits at Ds={d}')
    for d in NC:
        add(f'driftSite{name(d)}',sci(F[d]['drift_per_site'],2,sign=True),f'change of Delta_E per site at the settled window, Ds={d}')
    for d in EX:
        e25=D.est[D.get(d,2.5,128,16 if d>=0.2 else 10)['id']]['extrapolation']['value']
        add(f'extLam{name(d)}',sci_up(abs(e25-F[d]['extrapolated']),1),f'|extrapolated Lambda=2.5 - Lambda=3 (central)| at Ds={d}')
    for d in (0.1,0.05,0.01,0.025):add(f'om{name(d)}',fx(om(d),3),f'median fitted omega at Ds={d}')
    x=F[0.225];om225=[f['omega'] for f in x['extrapolation_fits']]
    add('ruleTwoTwentyFive',fx(x['extrapolated'],6),'the rule alone at Ds=0.225: its extrapolation (all three fits converge)')
    add('ruleDepthTwoTwentyFive',sci(max(abs(x['extrapolated']-x['settled']),x['extrapolation_spread']),2),'its chain-depth error')
    add('ruleOmTwoTwentyFive',f'{fx(min(om225),3)}\\text{{--}}{fx(max(om225),3)}','fitted omega of the three fits at Ds=0.225')
    add('reclassOneFifty',sci(F[0.15]['extrapolated']-F[0.15]['settled'],2,sign=True),'value change if Ds=0.15 were extrapolated')
    add('reclassOneSeventyFive',sci(F[0.175]['settled']-F[0.175]['extrapolated'],2,sign=True),'value change if Ds=0.175 had a plateau')
    # sensitivity of the plateau test to h and to the window width (Ds = 0.15 and the plateau points below)
    dh={d:plateau_variant(D.det[D.get(d,3,128,16)['id']],0.5,None)[0] for d in PL}
    d20={d:plateau_variant(D.det[D.get(d,3,128,16)['id']],0.25,20) for d in PL}
    add('driftHalfOneFifty',sci(dh[0.15],2),'plateau drift at Ds=0.15 with h = w/2')
    add('driftHalfLow',sci_up(max(v for d,v in dh.items() if d<=0.125),2),'largest plateau drift with h = w/2, Ds<=0.125')
    add('driftTwentyOneFifty',sci(d20[0.15][0],2),'plateau drift at Ds=0.15 with windows of 20 sites')
    add('driftTwentyLow',sci_up(max(v[0] for d,v in d20.items() if d<=0.125),2),'largest plateau drift with windows of 20 sites, Ds<=0.125')
    add('settledTwentyShiftOneFifty',sci(d20[0.15][1]-F[0.15]['settled'],2,sign=True),'settled value with windows of 20 sites - settled, Ds=0.15')
    # budget pieces
    add('KdblMin',sci(min(F[d]['Lambda25_K_doubling'] for d in PL),2),'smallest K-doubling shift at Lambda=2.5 (plateau points)')
    add('KdblMax',sci(max(F[d]['Lambda25_K_doubling'] for d in PL),2),'largest (at Ds=0.001)')
    add('LspreadPilot',sci_up(max(F[d]['Lambda_spread'] for d in (0.1,0.05)),2),'Lambda spread over 2..4 at Ds=0.1, 0.05')
    add('LspreadMax',sci_up(max(F[d]['Lambda_spread'] for d in PL),2),'largest Lambda spread among the plateau points')
    add('LspreadMaxAt',f"{max(PL,key=lambda d:F[d]['Lambda_spread']):g}",'where')
    add('nLambdaKdbl',str(sum(1 for d in FIN if F[d]['Lambda25_K_doubling']>F[d]['Lambda_spread'])),
        'final points where the K-doubling allowance exceeds the measured Lambda spread')
    for d in PILOT[1:]:
        add(f'Ltwo{name(d)}',sci(D.val(d,2,256,10)-D.val(d,3,128,10),1,sign=True),f'Lambda=2 (K=256) - Lambda=3 (K=128), nb=10, Ds={d}')
        add(f'Lfour{name(d)}',sci(D.val(d,4,64,10)-D.val(d,3,128,10),1,sign=True),f'Lambda=4 (K=64) - Lambda=3 (K=128), nb=10, Ds={d}')
        add(f'Ltwofive{name(d)}',sci(D.val(d,2.5,128,10)-D.val(d,3,128,10),1,sign=True),f'Lambda=2.5 (K=128) - Lambda=3, nb=10, Ds={d}')
    for d in (0.001,):
        add(f'Ltwofive{name(d)}',sci(D.val(d,2.5,128,10)-D.val(d,3,128,10),1,sign=True),f'Lambda=2.5 - 3 (K=128), Ds={d}')
        add(f'Lfour{name(d)}',sci(D.val(d,4,64,10)-D.val(d,3,128,10),2,sign=True),f'Lambda=4 (K=64) - Lambda=3, Ds={d}')
        add(f'Ltwo{name(d)}',sci(D.val(d,2,64,10)-D.val(d,3,64,10),2,sign=True),f'Lambda=2 - 3 at K=64, Ds={d}')
        add(f'Kthree{name(d)}',sci(F[d]['keep_nb'],1),f'K/nb spread at Lambda=3, Ds={d}')
        add(f'Lspread{name(d)}',sci_up(F[d]['Lambda_spread'],2),f'spread over Lambda=2.5, 3, 4 (K-converged), Ds={d}')
    v10=[D.val(0.2,L,K,10) for L,K in ((2,256),(2.5,128),(3,128),(4,64))]
    add('LtenSpreadTwoHundred',sci(max(v10)-min(v10),1),'Ds=0.2, nb=10: spread of the extrapolated values over Lambda=2..4 (K-converged)')
    add('Kdbl'+name(0.001),sci(F[0.001]['Lambda25_K_doubling'],3),'K doubling at Lambda=2.5, Ds=0.001')
    # midpoint artefacts (App. E)
    off=[F[d]['midpoint']['Delta_E']-F[d]['Delta_E'] for d in PL if d>=0.025]
    add('midOffLo',e4(min(off)),'smallest old midpoint - new value over 0.025<=Ds<=0.15 [1e-4]');add('midOffHi',e4(max(off)),'largest')
    add('midOffOne',sci(F[0.001]['midpoint']['Delta_E']-F[0.001]['Delta_E'],2,sign=True),'old midpoint - new at Ds=0.001')
    oldL=[(F[d]['midpoint']['Lambda25_shift']) for d in PL]
    add('midLmax',sci(max(abs(x) for x in oldL),2),'largest |old Lambda=2.5 shift| over the plateau points (midpoints)')
    for d in (0.1,0.05):
        add(f'midLtwo{name(d)}',sci(D.mid(d,2,256,10)-D.mid(d,3,128,10),2,sign=True),f'old midpoint Lambda=2 (K=256) - Lambda=3, Ds={d}')
    add('midWithin',str(sum(1 for d in DS if abs(F[d]['midpoint']['Delta_E']-F[d]['Delta_E'])<=F[d]['midpoint']['total_uncertainty'])),
        'points whose old midpoint lies within its old total of the new value')
    mono=0
    for ds in DS:
        r=D.get(ds,3,128,16);W=[w for w in D.det[r['id']]['windows'] if w['gap_relative_variation']<.005 and w['log_response_residual']<.003]
        v=[w['Delta_E'] for w in sorted(W,key=lambda w:w['start'])];mono+=all(b<=a for a,b in zip(v,v[1:]))
    add('nMonoDec',str(mono),'central items whose quality-window Delta_E falls monotonically with the first site')
    ratio=[F[d]['midpoint']['total_uncertainty']/F[d]['total'] for d in FIN if 0.01<=d<=0.15]
    add('errShrink',f'{min(ratio):.0f}\\text{{--}}{max(ratio):.0f}','old total / new total, final points 0.01<=Ds<=0.15')
    # keep / nb convergence at Lambda = 3 (present estimator)
    ks=[]
    for ds in FIN:
        if ds>0.125:continue
        v=[D.val(ds,3,k,10) for k in (48,64,96,128,160,192) if D.get(ds,3,k,10)];ks.append(max(v)-min(v))
    add('keepSpread',sci_up(max(ks)),'max over Ds<=0.125 of the spread over K at nb=10, Lambda=3')
    c=lambda ds:F[ds]['Delta_E']
    add('nbEight',sci_up(max(abs(D.val(ds,3,64,8)-c(ds)) for ds in DS)),'max |nb=8 - central| (K=64), all points')
    add('nbTen',sci_up(max(abs(D.val(ds,3,64,10)-c(ds)) for ds in DS if ds>=0.2)),'max |nb=10 - central| (K=64) at Ds>=0.2')
    v=[abs(D.val(r['ds'],3,r['keep'],r['nb'])-c(r['ds'])) for r in D.all if r['Lambda']==3 and r['keep']>=64 and r['nb']>=12
       and r['campaign']=='ds13' and D.final(r['ds'])]
    add('nbTwelve',sci_up(max(v)),'max |nb>=12 - central| over Lambda=3, K>=64 items, final points')
    add('edgeMax',sci_up(max(r['max_edge'] for r in D.all if r['nb']>=12)),'largest top-level occupation, items with nb>=12')
    add('edgeMaxLow',sci_up(max(r['max_edge'] for r in D.all if r['nb']>=12 and r['ds']<=0.15)),'same, Ds<=0.15')
    neg=sorted(r['max_edge'] for r in D.all if r['nb']>=12 and r['terminal_residual']<0)
    pos=sorted(r['max_edge'] for r in D.all if r['nb']>=12 and r['terminal_residual']>0)
    add('edgeNegMed',sci(statistics.median(neg),1),'median max p_edge, nb>=12, flows leaving to the localized side (f<0)')
    add('edgePosMed',sci(statistics.median(pos),1),'same, flows leaving to the delocalized side (f>0)')
    add('edgeCentralMax',sci_up(max(r['max_edge'] for r in D.all if r['nb']==16 and r['keep']==128 and r['Lambda']==3)),'same, central items')
    # Lambda study
    mv=[abs(D.val(ds,1.5,128,10)-D.val(ds,1.5,64,10)) for ds in PILOT]
    add('LonefiveMove',f'{fx(min(mv),3)}\\text{{--}}{fx(max(mv),3)}','Lambda=1.5: |K=128 - K=64|')
    off=[abs(D.val(ds,1.5,128,10)-D.val(ds,2,256,10)) for ds in PILOT]
    add('LonefiveOff',f'{fx(min(off),3)}\\text{{--}}{fx(max(off),3)}','Lambda=1.5, K=128 against Lambda=2, K=256')
    nb16=[abs(D.val(ds,1.5,K,16)-D.val(ds,1.5,K,10)) for ds in PILOT for K in (64,128) if D.get(ds,1.5,K,16)]
    add('LonefiveNb',sci_up(max(nb16),2),'Lambda=1.5: |nb=16 - nb=10|')
    add('LtwoKconv',sci_up(max(abs(D.val(ds,2,256,10)-D.val(ds,2,192,10)) for ds in PILOT)),'Lambda=2: |K=256 - K=192|')
    k25={ds:abs(D.val(ds,2.5,64,10)-D.val(ds,2.5,128,10)) for ds in DS}
    add('LtwofiveKconv',sci_up(max(v for d,v in k25.items() if d<=0.15 and d>0.001)),'Lambda=2.5: |K=64 - K=128| (nb=10), 0.01<=Ds<=0.15')
    add('LtwofiveKconvHigh',sci_up(max(v for d,v in k25.items() if d>0.15 and D.final(d))),'same, final points with Ds>=0.175')
    add('LtwofiveKconvNc',sci_up(max(v for d,v in k25.items() if not D.final(d))),'same, the points not converged in chain depth')
    sm=[F[d]['Lambda2_shift_K64'] for d in DS if d<=0.05]
    add('LtwoKsixfourSmall',f'{sci(min(sm),1,sign=True)}\\text{{ to }}{sci(max(sm),1,sign=True)}','Lambda=2 - 3 at K=64, range over Ds<=0.05')
    # s -> 1
    for ds in (0.001,0.01,0.025):
        x=F[ds];nm=name(ds);dl=2*ds;nlo=math.sqrt(2*dl)-dl/4
        add(f'yt{nm}',fx(x['y_t'],5),f'y_t at Ds={ds}');add(f'kt{nm}',fx(x['kosterlitz_y_t'],5),f'2 sqrt(Ds) at Ds={ds}')
        add(f'ktPct{nm}',f"{100*abs(x['y_t']/x['kosterlitz_y_t']-1):.1f}",f'|y_t/(2 sqrt Ds) - 1| in % at Ds={ds}')
        add(f'nlo{nm}',fx(nlo,5),f'sqrt(2 delta) - delta/4 at Ds={ds}')
        add(f'nloDiff{nm}',sci(x['y_t']-nlo,2,sign=True),f'y_t - NLO at Ds={ds}')
    add('ytFig',', '.join(fx(F[d]['y_t'],3) for d in (0.2,0.15,0.1,0.05))+'\\text{ and }'+fx(F[0.025]['y_t'],3),'y_t at s = 0.6, 0.7, 0.8, 0.9, 0.95')
    r3=[(F[d]['y_t']-(math.sqrt(4*d)-d/2))/(2*d)**1.5 for d in (0.075,0.05,0.025,0.01,0.001)]
    add('nloRatioRange',f'{fx(min(r3),2)}\\text{{ to }}{fx(max(r3),2)}','(y_t - NLO)/delta^{3/2} over 0.001..0.075')
    add('nloThreeCoef',fx(-SR_C[2]/2**1.5,3),'coefficient of delta^{3/2} in y_t from the dual series: -C^SR_3(1)/2^{3/2}')
    add('nloRatioTen',fx(r3[3],2),'(y_t - NLO)/delta^{3/2} at Ds=0.01');add('nloRatioErrTen',sci(F[0.01]['total']/0.02**1.5,1),'delta_tot/delta^{3/2} at Ds=0.01')
    add('nloRatioOne',fx(r3[4],2),'(y_t - NLO)/delta^{3/2} at Ds=0.001')
    add('nloRatioErrOne',fx(F[0.001]['total']/0.002**1.5,1),'delta_tot/delta^{3/2} at Ds=0.001')
    for n_ in (2,3,4,5,6):
        add(f'srDiff{["","","Two","Three","Four","Five","Six"][n_]}',sci(sr_diff(F[0.01]['Delta_E'],0.01,n_),2,sign=True),
            f'Delta_E - dual series through C^SR_{n_}(1) at Ds=0.01')
    add('srTermSix',sci(abs(SR_C[5])*0.01**3,2),'|C^SR_6(1)| Ds^3 at Ds=0.01')
    add('errTen',sci(F[0.01]['total'],2),'total error at Ds=0.01')
    # the original study's archived critical couplings (code/lri_spin_boson_hpc/inputs/x*.json) against the same ds13 items
    rel=[]
    for f,iid in (('x0.1_L3_K48_B10.json','ds0.1_L3_K48_B10_N65'),('x0.24_L3_K64_B10.json','ds0.24_L3_K64_B10_N65'),
                  ('x0.01_L3_K64_B10.json','ds0.01_L3_K64_B10_N105')):
        arch=json.loads((D.root/'code'/'lri_spin_boson_hpc'/'inputs'/f).read_text())['alpha']
        r=[x for x in D.all if x['id']==iid and x['campaign']=='ds13'][0];rel.append(abs(r['alpha_c']/arch-1))
    add('archRel',sci_up(max(rel),2),'max relative difference, production alpha_c vs the original study (3 items)')
    ex={r['id']:r for r in D.example};ds13={r['id']:r for r in D.all if r['campaign']=='ds13'}
    exrel=[]
    for r in D.example:
        twin=[x for x in ds13.values() if abs(x['s']-r['s'])<1e-12 and x['Lambda']==r['Lambda'] and x['keep']==r['keep'] and x['nb']==r['nb']][0]
        exrel.append(abs(r['alpha_c']/twin['alpha_c']-1))
    add('exBitwise',str(sum(1 for x in exrel if x==0)),'example items whose alpha_c equals the 1-thread ds13 twin bitwise')
    add('exRel',sci_up(max(exrel),2),'largest relative alpha_c difference example (2 threads) vs ds13 (1 thread)')
    # independent implementation
    C=D.cmp;T=D.tw
    # The chain comparison is recomputed at replay time with the production closed form, whose last bits depend on the
    # platform's libm (a few 1e-16): it is quoted as a bound so that the printed number does not depend on the platform.
    cm=max(max(r['chain_eps_maxrel'],r['chain_t_maxrel']) for r in C.values())
    add('indChain','10^{-15}' if cm<1e-15 else sci_up(cm,2),'bound on the max relative chain-coefficient difference (rounding level)')
    add('indAlphaBitwise',str(sum(1 for r in C.values() if r['alpha_reldiff']==0)),'configurations with bitwise alpha_c')
    add('indAlpha',sci_up(max(r['alpha_reldiff'] for r in C.values()),2),'max relative alpha_c difference')
    add('indFlow',sci_up(max(r['flow_maxdiff_n_le_10'] for r in C.values()),2),'max |g_n| difference for n<=10')
    allw=[abs(w['diff']) for r in T.values() for w in r['windows']]
    add('indDE',sci_up(max(allw),2),'max window-by-window Delta_E difference (trusted windows)')
    add('indDEmedian',sci(statistics.median(allw),1),'median of the same')
    add('indTrusted',str(len(allw)),'number of trusted windows (all configurations)')
    add('indTrustedMin',str(min(r['n_trusted'] for r in T.values())),'fewest trusted windows in a configuration')
    add('indTrustedMax',str(max(r['n_trusted'] for r in T.values())),'most trusted windows in a configuration')
    add('indCovered',str(sum(r['covered'] for r in T.values())),'production quality windows within finite-difference reach')
    add('indQuality',str(sum(r['prod_quality'] for r in T.values())),'production quality windows (8 configurations)')
    add('indN',str(len(C)),'number of configurations')
    add('indWall',f"{max(r['wall_seconds'] for r in C.values())/60:.0f}",'longest single-core run of the independent solver [min]')
    add('indDivCone',str(C['c1']['flow_first_site_diff_gt_1e-8']),'c1: first site where the critical flows differ by > 1e-8')
    full=[k for k,r in T.items() if r['covered']==r['prod_quality'] and r['ind_range'] is not None]
    add('indFullN',str(len(full)),'configurations whose production quality windows are all within finite-difference reach')
    add('indFullList','\\text{ and }'.join(sorted(full)),'which')
    sw=[]
    for k,r in C.items():
        iid=r['record'].split('/')[-1];st=[x for x in D.all if x['id']==iid][0]['sel_start']
        w=[x for x in T[k]['windows'] if x['start']==st]
        if w:sw.append(abs(w[0]['diff']))
    add('indSettledN',str(len(sw)),'configurations whose settled window is a trusted window')
    add('indSettled',sci_up(max(sw),2),'max |difference| at the settled window over those')
    # one-loop test at Ds=0.249: slope of 1/(Delta_loc - series) against l, central item
    r=D.get(0.249,3,128,16);n_,l_,d_=local_exponent(D.det[r['id']],3.0);ser=D.mc[0.249]['series_opt']
    def slope(lo,hi):
        import numpy as np
        m=(l_>=lo)&(l_<=hi);return float(np.polyfit(l_[m],1/(d_[m]-ser),1)[0])
    add('slopeEarly',fx(slope(15,25),2),'slope of 1/(Delta_loc - series) on 15<=l<=25, Ds=0.249')
    add('slopeLate',fx(slope(38,48),2),'same on 38<=l<=48')
    add('slopeMid',fx(slope(20,45),2),'same on 20<=l<=45')
    # one loop: 1/(Delta_loc - Delta*) = (3/eps)(exp(eps(l - l0)) - 1), local slope 3 exp(eps(l - l0)); l0 from the data at 20<=l<=40
    eps=1-4*0.249;import numpy as np
    m=(l_>=20)&(l_<=40);l0=l_[m]-np.log1p(eps/(3*(d_[m]-ser)))/eps
    add('lzeroLo',f'{l0.min():.0f}','l0 of the one-loop form from the inverse excess at 20<=l<=40, smallest');add('lzeroHi',f'{l0.max():.0f}','largest')
    pr=lambda lc:f'{3*math.exp(eps*(lc-l0.max())):.2f}\\text{{--}}{3*math.exp(eps*(lc-l0.min())):.2f}'
    add('slopePredEarly',pr(20),'one-loop local slope at l=20 for that l0 range');add('slopePredLate',pr(43),'same at l=43')
    # terminal residuals near s = 1 (all items of the point)
    tr=lambda ds:[abs(x['terminal_residual']) for x in D.all if x['ds']==ds]
    add('termTenMax',sci_up(max(tr(0.01)),1),'largest |f(alpha_c)| at Ds=0.01');add('termOneMax',sci_up(max(tr(0.001)),1),'same at Ds=0.001')
    add('termTwentyFiveLo',sci_dn(min(tr(0.025)),1),'smallest |f| at Ds=0.025');add('termTwentyFiveHi',sci_up(max(tr(0.025)),1),'largest')
    add('nmaxTwentyFive',f"{30.6/(F[0.025]['y_t']*math.log(3)):.0f}",'n_max at Ds=0.025, Lambda=3')
    # memory planner (lri_spin.workflow.plan, one sector worker) against the lane-log peaks
    ratio=[]
    for e in D.events:
        c=D.cfg[e['id']];dd=c['keep']*c['nb'];k=c['keep'];work=8*(6*dd*dd+24*dd*k+32*k*k)
        ratio.append(((1.35*work+256*2**20)/2**30)/(e['peak_rss_kib']/2**20))
    add('planLo',f'{min(ratio):.1f}','smallest planner estimate / peak RSS');add('planHi',f'{max(ratio):.1f}','largest')
    add('planMed',f'{statistics.median(ratio):.1f}','median')
    # Angelini et al. (Ds = 0.0625, 1/nu = 0.4124(13)): NRG interpolated
    import numpy as np
    from scipy.interpolate import CubicSpline
    xs=[d for d in DS if D.final(d) and 0.01<=d<=0.15][::-1];ys=[F[d]['Delta_E'] for d in xs]
    vals=[float(CubicSpline(xs,ys)(0.0625))]
    for sub in ((0.025,0.05,0.075),(0.05,0.075,0.1),(0.025,0.05,0.075,0.1)):
        vals.append(float(np.polyval(np.polyfit(sub,[F[d]['Delta_E'] for d in sub],len(sub)-1),0.0625)))
    add('aprLo',fx(min(vals),4),'NRG interpolated to Ds=0.0625: smallest of four interpolants');add('aprHi',fx(max(vals),4),'largest')
    add('aprSigLo',fx((min(vals)-0.5876)/0.0013,1),'(interpolant - 0.5876)/0.0013, smallest');add('aprSigHi',fx((max(vals)-0.5876)/0.0013,1),'largest')
    # epsilon series
    S=D.mc
    for ds in (0.249,0.24,0.225,0.2):
        r=S[ds];nm=name(ds);ref,_=ref_series(r)
        add(f'ser{nm}',fx(ref,5 if ds!=0.249 else 6),f'series reference at Ds={ds}')
        add(f'exc{nm}',sci(F[ds]['settled']-ref,2,sign=True),f'settled - series at Ds={ds}')
    for ds in (0.249,0.24,0.225):
        nm=name(ds);r=S[ds];ref,_=ref_series(r)
        ext=[f['Delta_inf'] for B in (16,) for L in (3,2.5) for f in D.est[D.get(ds,L,128,B)['id']]['extrapolation']['fits']]
        add(f'extLo{nm}',fx(min(ext),4),f'smallest extrapolation (3 spans, Lambda=2.5 and 3, K=128, nb=16) at Ds={ds}')
        add(f'extHi{nm}',fx(max(ext),4),'largest')
        add(f'extExcLo{nm}',sci(min(ext)-ref,1,sign=True),'smallest extrapolation - series');add(f'extExcHi{nm}',sci(max(ext)-ref,1,sign=True),'largest')
    r=S[0.2];ref,sp=ref_series(r)
    add('diffTwoHundred',sci(F[0.2]['Delta_E']-ref,1,sign=True),'NRG - series (upper-middle approximant) at Ds=0.2')
    top=sorted(v for k,v in r['series_bp_approximants'].items() if sum(map(int,k.strip('[]').split('/')))==8)
    add('bpNTwoHundred',str(len(top)),'Borel-Pade approximants with L+M=8 at Ds=0.2')
    add('bpLoTwoHundred',fx(top[0],3),'smallest of them');add('bpHiTwoHundred',fx(top[-1],3),'largest')
    add('bpMedTwoHundred',fx(statistics.median(top),4),'their true median')
    add('diffMedTwoHundred',sci(F[0.2]['Delta_E']-statistics.median(top),2,sign=True),'NRG - true median at Ds=0.2')
    add('serOptErrTwoFortyNine',sci(S[0.249]['series_opt_err'],1),'smallest term at Ds=0.249')
    add('serBpTwoFortyNine',fx(S[0.249]['series_bp'],6),'Borel-Pade at Ds=0.249')
    add('serOptTwoForty',fx(S[0.24]['series_opt'],6),'optimal truncation at Ds=0.24')
    add('serOptErrTwoForty',sci(S[0.24]['series_opt_err'],1),'its smallest term')
    add('serAgreeTwoForty',sci(abs(S[0.24]['series_opt']-S[0.24]['series_bp']),1),'|optimal truncation - Borel-Pade| at Ds=0.24')
    add('serOptTwoTwentyFive',paren(S[0.225]['series_opt'],S[0.225]['series_opt_err']),'optimal truncation at Ds=0.225')
    add('serSpreadTwoHundred',sci(S[0.2]['series_bp_spread'],1),'Borel-Pade spread at Ds=0.2')
    for d in (0.225,0.2):
        add(f'serSens{name(d)}',sci_up(S[d]['series_bp_sens'],2),f'largest change of the [4/4] approximant when C7 or C8 moves by its allowance, Ds={d}')
    # Monte Carlo: ACCEPTED points, CROSS-CHECK FAILED points
    acc=[d for d in DS if accepted(S[d]) and D.final(d)]
    ccf=[d for d in DS if S[d].get('mc') is not None and S[d]['mc_status']=='CROSS-CHECK FAILED' and D.final(d)]
    lin=lambda r:r['mc_stat']+r['mc_sys']+r['nrg_err']
    add('mcAccN',str(len(acc)),'ACCEPTED MC points with a final NRG value');add('mcCcfN',str(len(ccf)),'CROSS-CHECK FAILED points')
    add('mcAccList',', '.join(f'{d:g}' for d in acc),'which');add('mcCcfList','\\text{ and }'.join(f'{d:g}' for d in ccf),'which')
    add('mcAccDiffMax',sci_up(max(abs(S[d]['nrg']-S[d]['mc']) for d in acc),2),'max |NRG - MC| over ACCEPTED')
    add('mcAccDiffMaxAt',f"{max(acc,key=lambda d:abs(S[d]['nrg']-S[d]['mc'])):g}",'where')
    add('mcAccRatioMax',f"{max(abs(S[d]['nrg']-S[d]['mc'])/lin(S[d]) for d in acc):.2f}",'max |NRG - MC|/(stat + sys + delta_tot), ACCEPTED')
    add('mcAccWithinLin',str(sum(1 for d in acc if abs(S[d]['nrg']-S[d]['mc'])<=lin(S[d]))),'ACCEPTED points within stat + sys + delta_tot')
    add('mcAccWithinSys',str(sum(1 for d in acc if abs(S[d]['nrg']-S[d]['mc'])<=S[d]['mc_sys'])),'ACCEPTED points with |NRG - MC| <= sigma_sys')
    add('mcAccStatRatioMax',f"{max(abs(S[d]['nrg']-S[d]['mc'])/S[d]['mc_stat'] for d in acc):.0f}",'max |NRG - MC|/sigma_stat, ACCEPTED')
    add('mcAccSysRatio',f"{min(S[d]['mc_sys']/S[d]['nrg_err'] for d in acc):.0f}\\text{{--}}{max(S[d]['mc_sys']/S[d]['nrg_err'] for d in acc):.0f}",
        'sigma_sys / delta_tot over ACCEPTED')
    both=[d for d in DS if S[d].get('mc') is not None and S[d]['mc_status']!='CONDITIONAL (sigma_sys coverage absent)' and D.final(d)]
    add('mcNeg',str(sum(1 for d in both if S[d]['nrg']<S[d]['mc'])),'points (ACCEPTED or CROSS-CHECK FAILED) with NRG below MC')
    add('mcBoth',str(len(both)),'those points')
    cr=lambda d:abs(S[d]['nrg']-S[d]['mc_cross'])/(S[d]['mc_cross_err']+S[d]['mc_cross_domega']+S[d]['nrg_err'])
    add('mcCrossRatioMax',up2(max(cr(d) for d in acc)),'max |NRG - crossing|/(sigma_inf + Delta_omega + delta_tot), ACCEPTED')
    allc=[d for d in DS if S[d].get('mc_cross') is not None and D.final(d)]
    add('mcCrossAllMax',up2(max(abs(S[d]['nrg']-S[d]['mc_cross'])/S[d]['mc_cross_err'] for d in allc)),'max |NRG - crossing|/sigma_inf, all points with a crossing')
    add('mcCrossAllN',str(len(allc)),'those points')
    add('mcCrossOneHundred',fx(abs(S[0.1]['nrg']-S[0.1]['mc_cross'])/S[0.1]['mc_cross_err'],2),'|NRG - crossing|/sigma_inf at Ds=0.1')
    add('mcCrossStatMax',up2(max(abs(S[d]['nrg']-S[d]['mc_cross'])/S[d]['mc_cross_err'] for d in acc)),'max |NRG - crossing|/sigma_inf, ACCEPTED')
    for d in ccf:
        nm=name(d);r=S[d]
        add(f'mcFit{nm}',sci(r['nrg']-r['mc'],2,sign=True),f'NRG - MC fit at Ds={d}');add(f'mcCross{nm}',sci(r['nrg']-r['mc_cross'],2,sign=True),f'NRG - MC crossing at Ds={d}')
    r=S[0.225]
    add('mcTwoTwentyFiveSer',sci(r['mc']-ref_series(r)[0],2,sign=True),'MC - series at Ds=0.225 (MC CONDITIONAL)')
    # published Monte Carlo (Uzelac et al. 2001)
    for d,(v,e) in UGA.items():
        add(f'uga{name(d)}',sci((F[d]['Delta_E']-v)/e,2,sign=True),f'(NRG - UGA)/sigma_UGA at Ds={d}')
    return M


# ---------------------------------------------------------------- tables
def status_cell(D,ds):
    x=D.F[ds]
    if x['status']!='final':return 'not converged'
    return 'final, extrapolated' if x['estimator']=='extrapolated' else 'final'


def check_cell(D,ds):
    r=D.mc[ds];bits=[]
    if ds>=0.2:
        ref,err=ref_series(r);bits.append(f"series {fx(ref,5 if ds!=0.249 else 6)}"+(' (spread $'+sci(err,1)+'$: no test)' if ds==0.2 else ''))
        if D.F[ds]['status']!='final':bits[-1]+=' (excess $'+sci(D.F[ds]['settled']-ref,2,sign=True)+'$)'
    if r.get('mc') is not None:
        lab={'ACCEPTED':'MC label: accepted','ACCEPTED (sigma_sys-dominated)':'MC label: accepted',
             'CROSS-CHECK FAILED':'MC label: cross-check failed (not used)',
             'CONDITIONAL (sigma_sys coverage absent)':'MC label: conditional'}[r['mc_status']]
        if D.final(ds) and accepted(r):
            lab+=f"; NRG$-$MC ${sci(r['nrg']-r['mc'],2,sign=True)}$ (ratio {abs(r['nrg']-r['mc'])/(r['mc_stat']+r['mc_sys']+r['nrg_err']):.2f})"
        bits.append(lab)
    if ds in (0.01,0.001):bits.append('$s\\to1$ expansion only')
    return '; '.join(bits) if bits else '--'


def T_headline(D):
    L=[r'\begin{tabular}{@{}lllll>{\raggedright\arraybackslash}p{6.4cm}@{}}',r'\toprule',
       r'$\Delta_\sigma$ & $s$ & $\varepsilon$ & $\Delta_E$ & status & external test (Sec.~\ref{sec:checks})\\',r'\midrule']
    for ds in DS:
        x=D.F[ds];v=paren(x['Delta_E'],x['total']) if x['total'] is not None else r'\textcolor{gray}{['+fx(x['Delta_E'],4)+']}'
        L.append(f"{ds:g} & {x['s']:g} & {x['eps']:g} & {v} & {status_cell(D,ds)} & {check_cell(D,ds)}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_budget(D):
    L=[r'\begin{tabular}{@{}lllrrrrrrl@{}}',r'\toprule',
       r'$\Delta_\sigma$ & estimator & $\Delta_E$ & $10^4\delta_{\rm depth}$ & $10^4\delta_K$ & $10^4\delta_\Lambda$ & $10^4\delta_{\rm tot}$ & '
       r'$n_q$ & $10^4\,$(late fit $-\Delta_E$) & status\\',r'\midrule']
    for ds in DS:
        x=D.F[ds];est={'plateau':'plateau','extrapolated':'extrapolated','settled (not converged)':'settled'}[x['estimator']]
        dep='n.c.' if x['depth'] is None else e4(x['depth'],2);tot='--' if x['total'] is None else e4(x['total'],2)
        lt=x['crosschecks']['late'];late='--' if lt is None or x['status']!='final' else e4(lt['value']-x['Delta_E'],2,sign=True)
        L.append(f"{ds:g} & {est} & {x['Delta_E']:.6f} & {dep} & {e4(x['keep_nb'],2)} & {e4(x['Lambda'],2)} & {tot} & {x['n_quality']} & "
                 f"${late}$ & {'final' if x['status']=='final' else 'not converged'}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_extrap(D):
    L=[r'\begin{tabular}{@{}llllllll@{}}',r'\toprule',
       r' & & & & \multicolumn{3}{c}{the rule (Sec.~\ref{sec:estimator})} & cross-check, not adopted\\',r'\cmidrule(lr){5-7}\cmidrule(lr){8-8}',
       r'$\Delta_\sigma$ & settled & drift & per site & fits $\Delta_\infty$ ($S=30,25,20$) & $\omega$ & median & '
       r'crossover fit ($n_{\rm fit}$)\\',r'\midrule']
    for ds in DS:
        x=D.F[ds]
        if x['plateau']:continue
        fits=', '.join(f"{f['Delta_inf']:.5f}" for f in x['extrapolation_fits']);om=', '.join(f"{f['omega']:.3f}" for f in x['extrapolation_fits'])
        tag='' if x['status']=='final' else r'$^\ast$'
        c=x['crosschecks']['crossover'];cs='--' if c is None else f"{c['value']:.5f} ({c['n']})"
        L.append(f"{ds:g}{tag} & {x['settled']:.6f} & ${sci(x['plateau_drift'],1)}$ & ${sci(x['drift_per_site'],1,sign=True)}$ & {fits} & {om} & "
                 f"{x['extrapolated']:.6f} & {cs}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_indep(D):
    L=[r'\begin{tabular}{@{}lllllrrl@{}}',r'\toprule',
       r'id & $(s,\Lambda,K,n_b,N)$ & chain & $\alpha_c$ & trusted & $\max|\delta\Delta_E|$ & covered & quality range (production)\\',r'\midrule']
    for k in sorted(D.cmp):
        c=D.cmp[k];t=D.tw[k]
        a='bitwise' if c['alpha_reldiff']==0 else sci(c['alpha_reldiff'],1)
        pr=t['prod_range'];prs='--' if pr is None else f'[{pr[0]:.6f}, {pr[1]:.6f}]'
        ch=max(c['chain_eps_maxrel'],c['chain_t_maxrel']);chs='<10^{-15}' if ch<1e-15 else sci(ch,1)
        L.append(f"{k} & $({c['s']:g},{c['Lambda']:g},{c['keep']},{c['nb']},{c['N']})$ & ${chs}$ & "
                 f"{a if a=='bitwise' else '$'+a+'$'} & {t['n_trusted']} & ${sci(t['max_diff'],1)}$ & {t['covered']}/{t['prod_quality']} & {prs}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_series(D):
    L=[r'\begin{tabular}{@{}llllllll@{}}',r'\toprule',
       r'$\Delta_\sigma$ & $\varepsilon$ & NRG $\Delta_E$ & optimal truncation & Borel--Pad\'e (spread) & NRG $-$ reference & '
       r"rule's extrapolation & crossover fit\\",r'\midrule']
    for ds in (0.249,0.24,0.225,0.2):
        r=D.mc[ds];x=D.F[ds];ref,_=ref_series(r)
        v=paren(x['Delta_E'],x['total']) if x['total'] is not None else f"[{x['Delta_E']:.6f}]"
        if x['status']=='final':ext='adopted'
        else:
            e=[f['Delta_inf'] for L_ in (3,2.5) for f in D.est[D.get(ds,L_,128,16)['id']]['extrapolation']['fits']]
            ext=f'{min(e):.4f}--{max(e):.4f}'
        c=x['crosschecks']['crossover'];ext+=f" & {c['value']:.5f}" 
        L.append(f"{ds:g} & {r['eps']:g} & {v} & {r['series_opt']:.6f} ($\\pm{sci(r['series_opt_err'],1)}$) & "
                 f"{r['series_bp']:.5f} (${sci(r['series_bp_spread'],1)}$) & ${sci(x['Delta_E']-ref,2,sign=True)}$ & {ext}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_mc(D):
    L=[r'\begin{tabular}{@{}lllllll@{}}',r'\toprule',
       r'$\Delta_\sigma$ & NRG $\Delta_E$ & MC $\Delta_\varepsilon$ ($\sigma_{\rm stat}$)($\sigma_{\rm sys}$) & MC label & NRG $-$ MC & ratio & '
       r'MC crossing ($\sigma_\infty$)($\Delta_{\omega^\prime}$)\\',r'\midrule']
    lab={'ACCEPTED':'accepted','ACCEPTED (sigma_sys-dominated)':r'accepted ($\sigma_{\rm sys}$-dom.)','CROSS-CHECK FAILED':'cross-check failed',
         'CONDITIONAL (sigma_sys coverage absent)':r'conditional (no $\sigma_{\rm sys}$)'}
    for ds in DS:
        r=D.mc[ds]
        if r.get('mc') is None:continue
        x=D.F[ds];nc=x['status']!='final';sys_=r['mc_sys']
        sysS='--' if math.isnan(sys_) else f'{round(sys_*1e5)}'
        ratio='--' if nc or math.isnan(sys_) else f"{abs(r['nrg']-r['mc'])/(r['mc_stat']+sys_+r['nrg_err']):.2f}"
        cr='--' if r.get('mc_cross') is None else f"{r['mc_cross']:.5f}({round(r['mc_cross_err']*1e5)})({round(r['mc_cross_domega']*1e5)})"
        v=f"[{r['nrg']:.4f}]" if nc else paren(r['nrg'],r['nrg_err'])
        tag=r'$^\ast$' if nc else ''   # outside the f-string: Python < 3.12 forbids backslashes there
        L.append(f"{ds:g}{tag} & {v} & {r['mc']:.5f}({round(r['mc_stat']*1e5)})({sysS}) & {lab[r['mc_status']]} & "
                 f"${sci(r['nrg']-r['mc'],2,sign=True)}$ & {ratio} & {cr}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_s1(D):
    L=[r'\begin{tabular}{@{}llllllrr@{}}',r'\toprule',
       r'$\Delta_\sigma$ & $\delta=1-s$ & $y_t=1-\Delta_E$ & $\sqrt{2\delta}=2\sqrt{\Delta_\sigma}$ & ratio & $\sqrt{2\delta}-\delta/4$ & '
       r'$(y_t-\sqrt{2\delta}+\delta/4)/\delta^{3/2}$ & $\delta_{\rm tot}/\delta^{3/2}$\\',r'\midrule']
    for ds in (0.075,0.05,0.025,0.01,0.001):
        x=D.F[ds];dl=2*ds;nlo=math.sqrt(2*dl)-dl/4
        L.append(f"{ds:g} & {dl:g} & {x['y_t']:.5f} & {x['kosterlitz_y_t']:.5f} & {x['y_t']/x['kosterlitz_y_t']:.3f} & {nlo:.5f} & "
                 f"{(x['y_t']-nlo)/dl**1.5:.2f} & {x['total']/dl**1.5:.2g}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def T_midpoint(D):
    L=[r'\begin{tabular}{@{}lllllrl@{}}',r'\toprule',
       r'$\Delta_\sigma$ & old: midpoint ($\delta_{\rm tot}^{\rm old}$) & $10^4\delta_{\rm w}$ & $10^4\cdot2\delta_\Lambda^{\rm old}$ & this note & '
       r'$10^4\times$(old $-$ this note) & old status\\',r'\midrule']
    old={0.249:'biased (a)',0.24:'biased (a)',0.225:'biased (b)',0.2:'final (c)'}
    for ds in DS:
        x=D.F[ds];m=x['midpoint'];v=paren(x['Delta_E'],x['total']) if x['total'] is not None else f"[{x['Delta_E']:.6f}]"
        L.append(f"{ds:g} & {paren2(m['Delta_E'],m['total_uncertainty'])} & {e4(m['window_halfwidth'])} & {e4(2*abs(m['Lambda25_shift']))} & "
                 f"{v} & {e4(m['Delta_E']-x['Delta_E'],1,sign=True)} & {old.get(ds,'final')}\\\\")
    return L+[r'\bottomrule',r'\end{tabular}']


def render(D):
    out={}
    M=macros(D)
    out['numbers.tex']='% generated by code/analysis/note_numbers.py -- do not edit\n'+''.join(
        f'\\newcommand{{\\nrg{n}}}{{{v}}}% {src}\n' for n,v,src in M)
    for fn,f in (('headline_table.tex',T_headline),('budget_table.tex',T_budget),('extrap_table.tex',T_extrap),
                 ('indep_table.tex',T_indep),('series_table.tex',T_series),('mc_table.tex',T_mc),('s1_table.tex',T_s1),
                 ('midpoint_table.tex',T_midpoint)):
        out[fn]='\n'.join(f(D))+'\n'
    return out


def check(root,out):
    tab=root/'note'/'tables';bad=[]
    for fn,text in out.items():
        p=tab/fn
        if not p.is_file():bad.append(f'missing {p}')
        elif p.read_text()!=text:bad.append(f'differs: {p}')
    tex=(root/'note'/'lri_nrg_1d_note.tex').read_text()
    defined=set(re.findall(r'\\newcommand\{\\(nrg[A-Za-z]+)\}',out['numbers.tex']))
    used=set(re.findall(r'\\(nrg[A-Za-z]+)',tex))
    for u in sorted(used-defined):bad.append(f'undefined macro \\{u} in the note')
    for u in sorted(defined-used):print(f'note: \\{u} defined but not used')
    for t in re.findall(r'\\input\{(tables/[^}]+)\}',tex):
        if not (root/'note'/t).is_file() and not (root/'note'/(t+'.tex')).is_file():bad.append(f'missing input {t}')
    for t in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',tex):
        if not (root/'note'/t).is_file():bad.append(f'missing figure {t}')
    print('\n'.join(bad) if bad else f'note numbers: {len(out)} files and {len(used)} macros consistent with the data')
    return not bad


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--check',action='store_true')
    a=ap.parse_args();out=render(Data(a.root))
    if a.check:sys.exit(0 if check(a.root,out) else 1)
    tab=a.root/'note'/'tables';tab.mkdir(parents=True,exist_ok=True)
    for fn,text in out.items():(tab/fn).write_text(text)
    print(f'wrote {len(out)} files to {tab}')


if __name__=='__main__':
    main()
