#!/usr/bin/env python3
"""Assemble C0..C8(3) from complete independent finite-scheme RG-jet campaigns (PLAN component E.2).

The arithmetic is the vendored order-8 assembly vendor/c8_assembly/order8_assembly.py (HANDOFF f5ff6a35), imported
only after its sha256 equals the pin of tools/VENDORED.json: campaign_moments (equal campaign weights 1/2),
sector_assembly (C = F(f+p), C_pf = F(f), Delta_p = F(f+p) - F(f) and their propagated covariances) and
power_null_rows. Nothing of it is reimplemented here. This file adds:
  * gate coverage asserts (the vendored gates skip absent loops, F12): combine refuses, before any gate, unless the
    data hold every loop 3..order in both sectors and campaigns; after the gates it asserts one top_slot_gate row per
    L = 3..order and affinity loops == [5..order];
  * hard gates at the data means (ArithmeticError, exit 3): top_slot_gate, the float affinity_gate (loops 5..order)
    and, at order 8 only, loop7_gate (combine(order=7) records "not applicable at order 7");
  * input guards around power_null_rows (delta and dse of length >= order+1; finite Delta_p[k] and SE[k], k = 3..order;
    SE[k] > 0 wherever a pull is computed); a None or non-finite pull at orders 4..order is an error naming the row;
  * the PP8 marker (POWER_PROTOCOL.md:96-98): a flagged order-6 null row gets "pp8" and prints a FLAG line;
  * the consistency flags (results review, never constraints): the a/b campaign pull on C_order (|pull| > 3) and the
    bootstrap/covariance SE ratio (outside [0.8, 1.2]);
  * lower-order pulls C3..C(order-1) against references/lower_order_d3.json (HD8; both SEs; |pull| > 3 flagged);
    the b_3^p(0) control pull against -16 pi/15 (|pull| > 4 flagged); error_by_loop (sums to Var(C_order)); the two
    campaigns, the half streams and a bootstrap (seed 70530413);
  * for a campaign directory: the role (D.3a; a pilot_subset campaign is refused with 65 before any group data is
    read: its merge ends in `pilot_report.py subset-check`), the coverage guard of a non-test campaign (all 24 groups;
    graph sets equal to the inventory's; counts equal to the allocation source's) and the tail monitor (RECON action
    6; L8 thresholds, L <= 7 diagnostics).
Results: test -> C8_test_result.json (every physical field under test_partial), pilot_full -> C8_pilot_result.json
(label pilot, "for sizing only, never an estimate", values under sizing_only), production -> C8_result.json (final).
Publication (publish_result) is no-clobber: an identical result is kept, one whose only change is merged_sha256 (a
group re-merged after a recovered index) is superseded and kept as <name>.superseded.<sha12>.json (F8-d3), anything
else is refused. A result records each group's scientific identity apart from its timing (science_sha256, S3-R2-007:
the sha256 of every scientific table and a canonical digest of merged.json without its timing fields); a supersede
needs those identities recorded and equal, so a recomputed table whose rows changed (a recovered checkpoint with
another tail_sum, say) is refused even when every assembled value is unchanged.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,canon,digest,dump_point,load,object_hash,supersede

RESULT_SCHEMA='c8-d3-hpc-result-1'
HALF_D=1.5
VENDOR=ROOT/'vendor/c8_assembly'
SECTORS,CAMPAIGNS=('free','power'),('a','b')
FLAG_PULL=3.0;CONTROL_FLAG=4.0;RATIO_BAND=(0.8,1.2)
BOOTSTRAP_SEED=70530413
B3P0=-16*math.pi/15   # the b_3^p(0) control value (E.2)
REFERENCES=ROOT/'references/lower_order_d3.json'
PP8_ORDER=6
PP8_TEXT='must be investigated: a flag at order 6 contradicts an MS numerical zero (POWER_PROTOCOL.md:96-98)'
TAIL_XI=0.44;TAIL_SHARE=0.03;TAIL_K=16
META=('schema','dimension','order','epsilon','label','scope','final')

_OA=None
def vendored():
    """order8_assembly.py from vendor/, imported once, after its sha256 equals the VENDORED.json pin (E.1)."""
    global _OA
    if _OA is None:
        v=json.loads((ROOT/'tools/VENDORED.json').read_bytes())
        pin=next(f['sha256']for f in v['files']if f['path']=='order8_assembly.py');path=VENDOR/'order8_assembly.py';data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=pin:raise ValueError(f'{path} is not at its pinned sha256 {pin} (tools/VENDORED.json)')
        sys.dont_write_bytecode=True
        spec=importlib.util.spec_from_file_location('c8d3_order8_assembly',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);_OA=mod
    return _OA

def power_protocol_sha256()->str:return json.loads((ROOT/'tools/VENDORED.json').read_bytes())['power_protocol']['sha256']

def two_loop(order:int=8,inputs:Path|None=None,expected:dict|None=None)->tuple[np.ndarray,str]:
    """B2 of order 8 (inputs/two_loop.json, 7 strings) or order 7 (inputs/order7/two_loop.json), read from exactly the
    bytes whose sha256 matches `expected` (the campaign's inputs manifest pins) when given."""
    d=Path(inputs)if inputs is not None else ROOT/'inputs'
    rel='two_loop.json'if order==8 else'order7/two_loop.json';data=(d/rel).read_bytes();h=hashlib.sha256(data).hexdigest()
    if expected is not None and expected.get(rel)!=h:raise ValueError(f'Checksum mismatch: {d/rel} is not the file the campaign\'s inputs manifest pins')
    doc=json.loads(data)
    if doc.get('dimension')!=3 or doc.get('order')!=order:raise ValueError(f'{d/rel}: not the d=3 order-{order} two-loop data')
    return np.asarray(doc['B2'],float),h

def references()->tuple[dict,str]:
    data=REFERENCES.read_bytes();refs=json.loads(data)
    if refs.get('schema')!='c8-d3-references-1'or refs.get('dimension')!=3:raise ValueError('wrong references file')
    return refs,hashlib.sha256(data).hexdigest()

def pull(est,se,ref,rse):
    s=math.hypot(se,rse);return (est-ref)/s if s>0 else None

# ---------------------------------------------------------------- pieces of the result
def lower_order_checks(mu,se,order:int,refs:dict)->list:
    out=[];prim={e['order']:e for e in refs['coefficients']};sec={e['order']:e for e in refs.get('secondary',[])}
    for k in range(3,order):
        if k not in prim:continue
        e=prim[k];p=pull(float(mu[k]),float(se[k]),e['value'],e['se'])
        row=dict(order=k,estimate=float(mu[k]),sampling_se=float(se[k]),reference=e['value'],reference_se=e['se'],reference_source=e['source'],pull=p,
                 flag=p is not None and abs(p)>FLAG_PULL)
        if k in sec:
            q=pull(float(mu[k]),float(se[k]),sec[k]['value'],sec[k]['se']);row['secondary']=dict(reference=sec[k]['value'],reference_se=sec[k]['se'],pull=q,flag=q is not None and abs(q)>FLAG_PULL)
        out.append(row)
    return out

def power_null_checks(delta,dse,order:int)->dict:
    """The vendored null rows with the input guards of E.2 and the PP8 marker; no guard changes a reported number."""
    if delta is None or dse is None or len(delta)<order+1 or len(dse)<order+1:
        raise ValueError(f'power_null_rows: delta and dse need length >= {order+1} (got {None if delta is None else len(delta)}, {None if dse is None else len(dse)})')
    for k in range(3,order+1):
        if not(math.isfinite(float(delta[k]))and math.isfinite(float(dse[k]))):raise ValueError(f'power_null_rows: order {k}: Delta_p or its SE is not finite')
        if (k>=4 or abs(float(delta[k]))>=1e-12)and not float(dse[k])>0:raise ValueError(f'power_null_rows: order {k}: SE {float(dse[k])} must be positive where a pull is computed')
    rows=vendored().power_null_rows(delta,dse,order)
    for r in rows['null_rows']+[rows['top']]:
        if r['order']>=4 and(r['pull']is None or not math.isfinite(r['pull'])):raise ValueError(f'power_null_rows: the order-{r["order"]} row has no finite pull ({r["pull"]})')
    for r in rows['null_rows']:
        r['pp8']=PP8_TEXT if(r['order']==PP8_ORDER and r['flag'])else None
    rows['flags']=[r for r in rows['null_rows']if r['flag']]
    rows['rule']=('POWER_PROTOCOL.md (vendored; sha256 in power_protocol.sha256): rows 3..order-1 are null rows, |pull| > 3 flagged "not proved zero"; '
                  'the top order is the reported correction with a diagnostic pull and no flag; flags never change an estimate (PP6)')
    return rows

def coverage(ar:dict,order:int)->None:
    """E.2's coverage asserts before any gate: every loop 3..order in both sectors and both campaigns (any label)."""
    if set(ar)!=set(SECTORS):raise ValueError('combine: both sectors are required')
    for s in SECTORS:
        if set(ar[s])!=set(CAMPAIGNS):raise ValueError('combine: the two independent campaigns a and b are required')
        for t in CAMPAIGNS:
            missing=sorted(set(range(3,order+1))-set(ar[s][t]));extra=sorted(set(ar[s][t])-set(range(3,order+1)))
            if missing or extra:raise ValueError(f'combine: {s}/{t} lacks loops {missing} (extra {extra}); every loop 3..{order} is required before any gate (E.2)')
            for L,x in ar[s][t].items():
                x=np.asarray(x)
                if x.ndim!=2 or x.shape[1]!=2*(order+1-L)or len(x)<2 or not np.isfinite(x).all():raise ValueError(f'combine: invalid replicate data in {s}/{t}/L{L}')

def hard_gates(means_total:dict,J:dict,B2,order:int,half_d)->dict:
    oa=vendored();want=list(range(3,order+1))
    out=dict(top_slot=oa.top_slot_gate(J,order))
    if [r['L']for r in out['top_slot']['rows']]!=want:raise ArithmeticError(f'top_slot_gate returned rows for loops {[r["L"]for r in out["top_slot"]["rows"]]}, need exactly {want} (E.2)')
    out['loop7']=oa.loop7_gate(J,B2,order)if order==8 else 'not applicable at order 7'
    aff=oa.affinity_gate(means_total,B2,order,half_d,loops=list(range(5,order+1)))
    if aff['loops']!=list(range(5,order+1)):raise ArithmeticError(f'affinity_gate reports loops {aff["loops"]}, need {list(range(5,order+1))} (E.2)')
    out['affinity']=aff
    return out

def consistency(r:dict,order:int)->dict:
    """The a/b campaign pull on C_order and the bootstrap/covariance ratio: flags for the results review (E.2)."""
    a,b=r['campaigns']['a'],r['campaigns']['b'];key=f'C{order}'
    p=pull(a[key],a['sampling_se'],b[key],b['sampling_se'])
    out={'campaign_pull':{'a':a[key],'a_se':a['sampling_se'],'b':b[key],'b_se':b['sampling_se'],'pull':p,'flag':p is not None and abs(p)>FLAG_PULL},'bootstrap_ratio':None}
    if r.get('bootstrap'):
        ratio=r['bootstrap']['full_se'][order]/r['sampling_standard_error']if r['sampling_standard_error']>0 else None
        out['bootstrap_ratio']={'bootstrap_se':r['bootstrap']['full_se'][order],'covariance_se':r['sampling_standard_error'],'ratio':ratio,
                                'flag':ratio is None or not RATIO_BAND[0]<=ratio<=RATIO_BAND[1]}
    return out

def control_b3p(means:dict,vc:dict)->dict:
    """b_3^p(0) (the z^0 b-jet entry of the power loop-3 mean) against -16 pi/15; |pull| > 4 flagged (E.2)."""
    v=float(np.asarray(means['power'][3])[0]);se=float(max(0.,np.asarray(vc['power'][3])[0,0])**.5);p=pull(v,se,B3P0,0.)
    return {'estimate':v,'se':se,'reference':B3P0,'reference_text':'-16 pi/15','pull':p,'flag':p is not None and abs(p)>CONTROL_FLAG}

def gates_block(r:dict,order:int)->dict:
    """Every stored gate record recomputable from the result's own fields (E.3, verify_result.py)."""
    pn=r['power_null_checks']
    return {'hard':{k:r['hard_gates'][k]for k in('top_slot','loop7','affinity')},
            'coverage':{'loops':sorted(int(L)for L in r['means']['free']),'top_slot_rows':[x['L']for x in r['hard_gates']['top_slot']['rows']],
                        'affinity_loops':r['hard_gates']['affinity']['loops'],'complete':sorted(int(L)for L in r['means']['free'])==list(range(3,order+1))},
            'consistency':consistency(r,order),
            'pp8':[{'order':x['order'],'pp8':x['pp8']}for x in pn['null_rows']if x.get('pp8')],
            'power_null_flags':[x['order']for x in pn['flags']],
            'lower_order_flags':[x['order']for x in r['lower_order_checks']if x['flag']],
            'control_flag':r['b3p_control']['flag']}

def protocol_block()->dict:
    return dict(sha256=power_protocol_sha256(),path='vendor/c8_assembly/POWER_PROTOCOL.md',requirements='PP1-PP10 of the H2 review record (step 6), all reported here')

def assembly_block(half_d=HALF_D)->dict:
    return dict(module='vendor/c8_assembly/order8_assembly.py',module_sha256=digest(VENDOR/'order8_assembly.py'),handoff_sha256=digest(VENDOR/'HANDOFF_assembly.json'),half_d=half_d)

def combine(ar:dict,order:int=8,half_d=HALF_D,bootstrap:int=1024,B2=None,refs:dict|None=None)->dict:
    """The pure assembly of ar[sector][campaign][L] (replicates x 2(order+1-L): the b jet, then the c jet). order 8 is
    production; order 7 is kept for A-ASM-3 (the C7(3) run1 reassembly)."""
    oa=vendored();coverage(ar,order)
    if B2 is None:B2,_=two_loop(order)
    refs=refs if refs is not None else references()[0]
    loops=range(3,order+1);ar={s:{t:{L:np.asarray(ar[s][t][L],float)for L in loops}for t in CAMPAIGNS}for s in SECTORS}
    means,vc=oa.campaign_moments(ar,loops)
    r=oa.sector_assembly(means,vc,B2,order,half_d)
    if r['max_order']!=order:raise ValueError(f'sector_assembly reported max_order {r["max_order"]}, not {order}')
    mu,pf,delta=r['coefficients'],r['power_free_coefficients'],r['power_differences']
    cov,dcov,pcov,cross=r['covariance'],r['power_difference_covariance'],r['power_free_covariance'],r['cross']
    se,dse=r['standard_errors'],r['power_difference_errors']
    m={L:means['free'][L]+means['power'][L]for L in loops}
    g=hard_gates(m,r['J'],B2,order,half_d)
    var=float(cov[order,order])
    ebl={s:{str(L):dict(variance=float(r['contributions'][s][L][order,order]),share=float(r['contributions'][s][L][order,order])/var if var>0 else None,
                        se=math.sqrt(max(0.,float(r['contributions'][s][L][order,order]))))for L in loops}for s in SECTORS}
    camps={}
    for t in CAMPAIGNS:
        mm={L:ar['free'][t][L].mean(0)+ar['power'][t][L].mean(0)for L in loops};jj=oa.jacobians(mm,B2,order,half_d);cc=oa.coefficients(mm,B2,order,half_d)
        cv=sum(jj[L]@(np.cov(ar['free'][t][L],rowvar=False)/len(ar['free'][t][L])+np.cov(ar['power'][t][L],rowvar=False)/len(ar['power'][t][L]))@jj[L].T for L in loops)
        camps[t]={f'C{order}':float(cc[order]),'sampling_se':float(max(0,cv[order,order])**.5)}
    halves=[]
    for h in (0,1):
        mm={L:sum(ar[s][t][L][h*len(ar[s][t][L])//2:(h+1)*len(ar[s][t][L])//2].mean(0)for s in SECTORS for t in CAMPAIGNS)/2 for L in loops}
        halves.append(oa.coefficients(mm,B2,order,half_d).tolist())
    boot=None
    if bootstrap:
        rng=np.random.default_rng(BOOTSTRAP_SEED);xs=np.empty((bootstrap,order+1));dx=np.empty((bootstrap,order+1))
        for i in range(bootstrap):
            mm={s:{L:sum(ar[s][t][L][rng.integers(len(ar[s][t][L]),size=len(ar[s][t][L]))].mean(0)for t in CAMPAIGNS)/2 for L in loops}for s in SECTORS}
            f=oa.coefficients({L:mm['free'][L]+mm['power'][L]for L in loops},B2,order,half_d);xs[i]=f;dx[i]=f-oa.coefficients(mm['free'],B2,order,half_d)
        boot=dict(replicates=bootstrap,seed=BOOTSTRAP_SEED,full_se=xs.std(0,ddof=1).tolist(),correction_se=dx.std(0,ddof=1).tolist(),bias=(xs.mean(0)-mu).tolist(),diagnostic_only=True)
    n=order
    out={'schema':RESULT_SCHEMA,'dimension':3,'order':order,'epsilon':'2s-3',
         f'C{n}_full':float(mu[n]),'sampling_standard_error':float(se[n]),'coefficients':mu.tolist(),'standard_errors':se.tolist(),'covariance':cov.tolist(),
         f'power_free_C{n}':float(pf[n]),'power_free_se':float(max(0,pcov[n,n])**.5),'power_free_coefficients':pf.tolist(),
         'power_correction':float(delta[n]),'power_correction_se':float(dse[n]),'power_free_correction_covariance':float(cross[n,n]),
         'power_differences':delta.tolist(),'power_difference_errors':dse.tolist(),
         'means':{s:{str(L):np.asarray(v).tolist()for L,v in means[s].items()}for s in SECTORS},
         'error_by_loop':ebl,'campaigns':camps,'half_streams':halves,'bootstrap':boot,
         'lower_order_checks':lower_order_checks(mu,se,order,refs),'power_null_checks':power_null_checks(delta,dse,order),
         'b3p_control':control_b3p(means,vc),'hard_gates':g,
         'power_protocol':protocol_block(),'assembly':assembly_block(half_d),
         'scope':('Sampling precision only. Both sectors are integrated explicitly; C = F(f+p) is reported with the power-free part and the measured power '
                  'correction, which is never assumed zero and never a gate. Lower-order pulls, power null rows and the consistency flags are diagnostics; '
                  'the top-slot, loop-7 (order 8) and affinity gates are hard.')}
    tot=sum(v['variance']for s in ebl.values()for v in s.values())
    if not abs(tot-var)<=1e-10*max(abs(var),1e-300):raise ArithmeticError(f'error_by_loop sums to {tot}, not Var(C{n}) = {var}')
    out['gates']=gates_block(out,order)
    for x in out['power_null_checks']['null_rows']:
        if x.get('pp8'):print(f'FLAG pp8: power_differences[{x["order"]}] is flagged "{x["flag"]}": {x["pp8"]}',file=sys.stderr)
    return out

# ---------------------------------------------------------------- views (A-ASM-5: test, partial and pilot results hold no physical number)
def hidden_view(r:dict,key:str,label:str,scope:str)->dict:
    r=dict(r);part={k:r.pop(k)for k in list(r)if k not in META}
    r.update({k:None for k in part});r[key]=part;r['label']=label;r['scope']=scope;r['final']=False
    return r

def test_only_view(r:dict)->dict:
    return hidden_view(r,'test_partial','test','INCOMPLETE workflow test (a test-only plan). Not a physical coefficient; partial values only under test_partial.')

def pilot_view(r:dict)->dict:
    return hidden_view(r,'sizing_only','pilot','PILOT (pilot_full campaign): for sizing only, never an estimate; values only under sizing_only (E.2, A-PIL-3).')

def values_of(r:dict)->dict:
    """The physical fields of a result, whichever view holds them."""
    return r.get('test_partial')or r.get('sizing_only')or r.get('partial_values')or r

# ---------------------------------------------------------------- campaigns
def refuse_subset(m:dict,tool:str)->None:
    if m.get('campaign_role')=='pilot_subset':
        raise Refuse(65,f'{tool}: a pilot_subset campaign (PA or PC) has no result; its merge ends in `tools/pilot_report.py subset-check` (D.3a, D.13, R01)')

def coverage_guard(m:dict,cfgs:dict,inventory:dict)->dict:
    """A non-test assemble (production, pilot_full) refuses unless all 24 groups exist, each graph set equals the
    inventory's (L8: the to-integrate set of selection.json, which the inventory rows are), and the counts equal the
    allocation source's: the bundle's counts x s (production); the manifest's --points and replicate counts (pilot_full)."""
    want={(c,s,L)for c in CAMPAIGNS for s in SECTORS for L in range(3,9)}
    if set(cfgs)!=want:raise ValueError(f'coverage: groups missing {sorted(want-set(cfgs))[:4]}, unexpected {sorted(set(cfgs)-want)[:4]}')
    bundle=None;meta=None
    if m['campaign_role']=='production':
        bundle=Path(m['design']['bundle'])
        if digest(bundle/'design_meta.json')!=m['design']['meta_sha256']:raise ValueError(f'coverage: {bundle}/design_meta.json differs from the bundle the campaign was planned with')
        meta=json.loads((bundle/'design_meta.json').read_bytes())
    for (c,s,L),cfg in sorted(cfgs.items()):
        rows={int(r['id']):r for r in inventory[s][str(L)]};counts={int(k):int(v)for k,v in cfg['counts'].items()}
        if set(counts)!=set(rows):raise ValueError(f'coverage: group {c}_{s}_L{L} has {len(counts)} graphs, the inventory {len(rows)}')
        if m['campaign_role']=='pilot_full':
            P=m['allocation']['points'];R=m['allocation']['group_replicates'].get(f'{s}:{L}',m['allocation']['replicates'])
            if any(v!=P for v in counts.values()):raise ValueError(f'coverage: group {c}_{s}_L{L} has a graph at other than --points {P}')
            if cfg['replicates']!=R:raise ValueError(f'coverage: group {c}_{s}_L{L} has {cfg["replicates"]} replicates, the plan {R}')
        else:
            name=f'counts/{c}_{s}_L{L}.txt'
            if bundle is None or meta is None:raise ValueError(f'coverage: campaign role {m["campaign_role"]!r} has no design bundle to check counts against')
            if not(bundle/name).is_file()or name not in meta['counts_sha256']:raise ValueError(f'coverage: {name} is missing from the bundle {bundle}')
            data=(bundle/name).read_bytes()
            if hashlib.sha256(data).hexdigest()!=meta['counts_sha256'][name]:raise ValueError(f'coverage: {name} differs from the digest in design_meta.json')
            frozen={int(a):int(b)for a,b in (ln.split()for ln in data.decode().splitlines()if ln.strip())}
            st=m['design']['s']
            def mult(g):return int(st['free_L8_primitive'if(s=='free'and L==8 and rows[g].get('primitive'))else f'{s}_L{L}'])
            if counts!={k:v*mult(k)for k,v in frozen.items()}:raise ValueError(f'coverage: group {c}_{s}_L{L} counts differ from the bundle counts x s')
            if cfg['replicates']!=int(m['design']['r'][f'{s}_L{L}']):raise ValueError(f'coverage: group {c}_{s}_L{L} replicates differ from the bundle')
    return dict(groups=len(cfgs),graphs=sum(len(v['counts'])for v in cfgs.values()),source=m['campaign_role'])

def hill(top:list)->float|None:
    """Hill estimate of xi from the 16 largest |t| (15 log-spacings above the 16th); None if undefined."""
    if len(top)<TAIL_K:return None
    x=[float(v)for v in top]
    if x[-1]<=0 or not all(math.isfinite(v)for v in x):return None
    return sum(math.log(v/x[-1])for v in x[:-1])/(TAIL_K-1)

def read_csv(path:Path)->list[dict]:
    lines=Path(path).read_text().splitlines();head=lines[0].split(',')
    return [dict(zip(head,l.split(',')))for l in lines[1:]]

def tail_monitor(directory:Path,m:dict,cfgs:dict,J:dict|None)->dict:
    """RECON action 6 (E.2): per L8 graph and campaign the replicate-mean Hill index of the merged top 16
    (graph_tails.csv); two-campaign mean > 0.44 lists the graph as "possible infinite variance (production)" with its
    share of the group variance (C8 Jacobian combination); > 3% flags. L <= 7: the same statistics as diagnostics.
    A zero tail_sum or a non-finite statistic is "tail statistic undefined", never compared. No value changes."""
    per={};undefined=[];listed=[];flags=[]
    for (c,s,L),cfg in sorted(cfgs.items()):
        p=Path(directory)/'groups'/f'{c}_{s}_L{L}';rows=read_csv(p/'graph_tails.csv');hs={}
        for r in rows:
            g=int(r['graph']);top=[r[f'tail_top_{i+1}']for i in range(TAIL_K)if r.get(f'tail_top_{i+1}')]
            h=None if float(r['tail_sum'])==0 else hill(top)
            hs.setdefault(g,[]).append(h)
        for g,v in hs.items():
            e=per.setdefault((s,L,g),{})
            e[c]=None if any(x is None for x in v)else sum(v)/len(v)
    shares={}
    if J is not None:
        for (c,s,L),cfg in cfgs.items():
            if L!=8:continue
            reps=read_csv(Path(directory)/'groups'/f'{c}_{s}_L{L}'/'graph_replicates.csv');k=2*(9-L);vals={}
            j=np.asarray(J[L])[8]
            for r in reps:vals.setdefault(int(r['graph']),[]).append(float(np.dot(j,[float(r[f'jet_{i}'])for i in range(k)])))
            var={g:float(np.var(v,ddof=1))if len(v)>1 else 0. for g,v in vals.items()};tot=sum(var.values())
            for g,v in var.items():shares[(c,s,g)]=v/tot if tot>0 else None
    out=[]
    for (s,L,g),e in sorted(per.items()):
        if any(e.get(c)is None for c in CAMPAIGNS):
            undefined.append({'sector':s,'L':L,'graph':g,'reason':'tail statistic undefined (a zero tail_sum or a non-finite Hill index in some replicate)'});continue
        mean=(e['a']+e['b'])/2;row={'sector':s,'L':L,'graph':g,'xi_a':e['a'],'xi_b':e['b'],'xi_mean':mean}
        if L==8 and mean>TAIL_XI:
            sh={c:shares.get((c,s,g))for c in CAMPAIGNS};row.update(listed='possible infinite variance (production)',share=sh);listed.append(row)
            if any(x is not None and x>TAIL_SHARE for x in sh.values()):flags.append({**row,'flag':'more than 3% of its group variance: for the results review'})
        out.append(row)
    return {'rule':'L8: replicate-mean Hill index of the merged top 16, two-campaign mean > 0.44 listed with its variance share, > 3% flagged; '
                   'L <= 7: diagnostics, no threshold; nothing changes a value','listed':listed,'flags':flags,'undefined':undefined,
            'diagnostics_L_le_7':[r for r in out if r['L']<8],'graphs':len(per)}

# S3-R2-007: a merged group's scientific identity, apart from its timing. merged.json's timing and provenance fields
# (lane and thread seconds, row seconds, max_rss_kb, the graph_costs.csv digest, its own payload digest, the units text
# and accepted tool changes) are left out; every other field (batches, fallbacks, counts, the digests of the scientific
# tables) enters merged_science, and each scientific table's sha256 is recorded by name (validate_merged has checked
# every table against merged.json). A recomputed index with other timings keeps it; any changed row changes it.
MERGED_TIMING=('integration_seconds_sum','thread_seconds_sum','integration_core_seconds','max_rss_kb','graph_costs_sha256','payload_sha256','units',
               'accepted_tool_changes')
SCIENCE_TABLES=('graph_replicates','graph_tails','graph_promotions','graph_prefixes')
SCIENCE_KEYS=tuple(f'{t}.csv'for t in SCIENCE_TABLES)+('merged_science',)
def group_science(d:dict)->dict:
    """The scientific identity of a validated merged.json d: {table.csv: sha256 (graph_prefixes.csv None without nested
    graphs), 'merged_science': the canonical digest of d without MERGED_TIMING}."""
    out={f'{t}.csv':d.get(f'{t}_sha256')for t in SCIENCE_TABLES}
    out['merged_science']=object_hash({k:v for k,v in d.items()if k not in MERGED_TIMING});return out

def science_ok(x)->bool:
    """x is a group_science record: exactly SCIENCE_KEYS, each a sha256 (graph_prefixes.csv may be null)."""
    h=lambda v:isinstance(v,str)and len(v)==64 and all(c in '0123456789abcdef'for c in v)  # noqa: E731
    return isinstance(x,dict)and set(x)==set(SCIENCE_KEYS)and all(h(v)or(k=='graph_prefixes.csv'and v is None)for k,v in x.items())

def load_campaign(directory:Path,accept_tool_change:bool=False):
    """(manifest, Inputs, manifest sha256, replicate data, merged.json sha256 per group, accepted tool changes, configs,
    the scientific identity per group (group_science))."""
    from production import group_of,validate_merged,verify_base
    m,I,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=accept_tool_change,vendored=True)
    refuse_subset(m,'assemble.py')
    if m['campaign_weights']!={'a':.5,'b':.5}:raise ValueError('changed campaign weights')
    ar={s:{t:{}for t in CAMPAIGNS}for s in SECTORS};hashes={};cfgs={};science={}
    for gr in m['groups']:
        p,cfg=group_of(directory,m,gr['name']);d=validate_merged(p,cfg,m,mh);key=(cfg['campaign'],cfg['sector'],cfg['L'])
        if key in cfgs:raise ValueError('duplicate group')
        x=np.asarray(d['batches'],float)
        if x.shape!=(cfg['replicates'],2*(9-cfg['L'])):raise ValueError('wrong data shape')
        ar[cfg['sector']][cfg['campaign']][cfg['L']]=x;hashes[gr['name']]=digest(p/'merged.json');cfgs[key]=cfg;science[gr['name']]=group_science(d)
    return m,I,mh,ar,hashes,changes,cfgs,science

def evaluate(directory:Path,bootstrap:int=1024,accept_tool_change:bool=False)->dict:
    m,I,mh,ar,hashes,changes,cfgs,science=load_campaign(directory,accept_tool_change)
    role=m['campaign_role'];cov=None
    if role in('production','pilot_full'):cov=coverage_guard(m,cfgs,load(I.where('inventory.json')))
    B2,b2sha=two_loop(8,I.dir,I.m['sha256'])
    r=combine(ar,8,HALF_D,bootstrap,B2)
    J={L:np.asarray(v)for L,v in vendored().jacobians({L:np.asarray(r['means']['free'][str(L)])+np.asarray(r['means']['power'][str(L)])for L in range(3,9)},B2,8,HALF_D).items()}
    r['tail_monitor']=tail_monitor(directory,m,cfgs,J)
    r['gates']['coverage']['campaign']=cov
    _,rsha=references()
    prov=dict(source_manifest_sha256=mh,merged_sha256=hashes,science_sha256=science,backend=m['backend'],build=m['build'],numerics=m['numerics'],mp_check=m['mp_check'],
              campaign_role=role,test_only=m['test_only'],allocation=m.get('allocation'),two_loop_sha256=b2sha,references_sha256=rsha,
              tool_sha256={n:digest(ROOT/'tools'/n)for n in ('assemble.py','report.py','production.py','common.py')if (ROOT/'tools'/n).exists()})
    if changes:prov['accepted_tool_changes']=changes
    if role=='test':r=test_only_view(r)
    elif role=='pilot_full':r=pilot_view(r)
    else:r['label']='production';r['final']=True
    r.update(prov);return r

def default_output(directory:Path,r:dict)->Path:
    return Path(directory)/{'test':'C8_test_result.json','pilot':'C8_pilot_result.json','production':'C8_result.json'}[r['label']]

# Provenance a recomputed result may change while its scientific content stays the same (F8-d3, C62d's F8): every
# 'merged_sha256' (assemble: the sha256 of each group's merged.json; combine.py: the same per batch, in combined_from).
# merged.json also records timing (lane and row seconds, max_rss_kb, the graph_costs.csv digest), which changes
# whenever a block is recomputed. Its scientific content is bound apart, by 'science_sha256' (group_science; S3-R2-007),
# which is never supersedable.
SUPERSEDABLE=('merged_sha256',)
SCIENCE='science_sha256'

def science_of(x):
    """x without its SUPERSEDABLE fields, at any depth (what must be equal for a result to be superseded)."""
    if isinstance(x,dict):return {k:science_of(v)for k,v in x.items()if k not in SUPERSEDABLE}
    if isinstance(x,list):return [science_of(v)for v in x]
    return x

def merged_maps(x,at:str='',key:str='merged_sha256')->dict:
    """{label: value} over every `key` map of a result (merged_sha256, or science_sha256): 'group' (assemble),
    'combined_from[i]:group' (combine)."""
    out={}
    for k,v in (x.items()if isinstance(x,dict)else()):
        if k==key and isinstance(v,dict):out.update({f'{at}{g}':s for g,s in v.items()})
        elif isinstance(v,list):
            for i,y in enumerate(v):out.update(merged_maps(y,f'{at}{k}[{i}]:',key))
        else:out.update(merged_maps(v,at,key))
    return out

def supersede_refusal(old,new)->str|None:
    """Why `new` may not supersede `old` (None: it may). It may only when everything but the merged_sha256 maps is
    equal, the scientific identities included, and every group whose merged_sha256 changed carries a recorded
    scientific identity (S3-R2-007): equal assembled values alone do not show that no scientific table changed."""
    if not isinstance(old,dict):return 'the existing file is not a result'
    so,sn=merged_maps(old,key=SCIENCE),merged_maps(new,key=SCIENCE)
    if sn and not so:return 'the existing result records no scientific identity (written before S3-R2-007): its science cannot be compared'
    diff=sorted(g for g in set(so)|set(sn)if canon(so.get(g))!=canon(sn.get(g)))
    if diff:
        tabs=lambda g:[k for k in SCIENCE_KEYS if (so.get(g)or{}).get(k)!=(sn.get(g)or{}).get(k)]if isinstance(so.get(g),dict)and isinstance(sn.get(g),dict)else['recorded identity']  # noqa: E731
        return 'the scientific identity changed for '+'; '.join(f'{g} ({", ".join(tabs(g))})'for g in diff[:6])+(f' and {len(diff)-6} more'if len(diff)>6 else'')
    if canon(science_of(old))!=canon(science_of(new)):return 'its assembled content differs'
    mo,mn=merged_maps(old),merged_maps(new);changed=sorted(g for g in set(mo)|set(mn)if mo.get(g)!=mn.get(g))
    bare=[g for g in changed if not science_ok(sn.get(g))]
    if bare:return f'no scientific identity is recorded for {", ".join(bare[:6])}: a change of its merged.json is not shown to be timing only'
    return None

def publish_result(dest:Path,result:dict)->str:
    """No-clobber and idempotent: an existing identical result is kept. An existing result that differs only in its
    SUPERSEDABLE fields, its scientific content unchanged (a group re-merged after the recovery of a completed index:
    the same batches, other timings), is superseded: the old bytes are kept as <name>.superseded.<sha256[:12]>.json
    (a hard link) and the new result replaces the file atomically (F8-d3). The scientific content includes every
    group's scientific identity (science_sha256; supersede_refusal, S3-R2-007). Any other difference is a real conflict
    and an error, never overwritten. Also behind combine.py (C8_partial.json, C8_final.json)."""
    new=json.loads(json.dumps(result,allow_nan=False))
    if dest.exists():
        data=dest.read_bytes();old=json.loads(data)
        if canon(old)==canon(new):return 'identical result already present; kept'
        why=supersede_refusal(old,new)
        if why:raise ValueError(f'{dest} exists and differs from the recomputed result ({why}); not overwritten')
        keep=supersede(dest,(json.dumps(result,indent=2,allow_nan=False)+'\n').encode(),data,'result_publish')
        if keep is None:return publish_result(dest,result)   # dest changed between the read and the link: decide again
        mo,mn=merged_maps(old),merged_maps(new);changed=sorted(g for g in set(mo)|set(mn)if mo.get(g)!=mn.get(g))
        return f'superseded: scientific content unchanged, merged_sha256 changed for {", ".join(changed)or "no group"}; previous result kept as {keep}'
    try:dump_point(dest,result,'result_publish');return 'written'
    except FileExistsError:return publish_result(dest,result)

def summary_lines(r:dict)->list[str]:
    src=values_of(r);out=[];f=lambda p:'n/a'if p is None else f'{p:+.2f}'
    for c in src.get('lower_order_checks')or[]:
        out.append(('FLAG |pull|>3 (diagnostic) 'if c['flag']else'')+f"C{c['order']}: {c['estimate']:.12g} +/- {c['sampling_se']:.3g} vs {c['reference']:.12g} +/- {c['reference_se']:.3g}  pull {f(c['pull'])}")
    pn=src.get('power_null_checks')or{}
    for c in pn.get('null_rows',[]):
        out.append((f'FLAG {c["flag"]} 'if c['flag']else'')+f"power_differences[{c['order']}]: {c['delta']:.3g} +/- {c['se']:.3g}  "+(c.get('note')or f"pull {f(c['pull'])}")+
                   (f'  [pp8: {c["pp8"]}]'if c.get('pp8')else''))
    if pn.get('top'):t=pn['top'];out.append(f"power correction (order {t['order']}): {t['delta']:.6g} +/- {t['se']:.3g}  diagnostic pull {f(t['pull'])}")
    g=(src.get('gates')or{}).get('consistency')or{}
    if g.get('campaign_pull'):out.append(('FLAG 'if g['campaign_pull']['flag']else'')+f"a/b campaigns: pull {f(g['campaign_pull']['pull'])}")
    if g.get('bootstrap_ratio'):out.append(('FLAG 'if g['bootstrap_ratio']['flag']else'')+f"bootstrap/covariance SE ratio: {g['bootstrap_ratio']['ratio']}")
    c=src.get('b3p_control')
    if c:out.append(('FLAG |pull|>4 'if c['flag']else'')+f"b_3^p(0) control: {c['estimate']:.10g} +/- {c['se']:.3g} vs -16pi/15: pull {f(c['pull'])}")
    tm=src.get('tail_monitor')or{}
    for x in tm.get('flags',[]):out.append(f"FLAG tail monitor: {x['sector']} L{x['L']} graph {x['graph']}: xi {x['xi_mean']:.3f}, share {x['share']}")
    if r.get('label')in('test','pilot'):out=[f'({r["label"]} result: no physical number)']+out
    return out

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__.split('\n')[0]);p.add_argument('directory',type=Path);p.add_argument('--bootstrap',type=int,default=1024)
    p.add_argument('--output',type=Path);p.add_argument('--accept-tool-change',action='store_true');a=p.parse_args(argv)
    try:
        if a.bootstrap<0 or a.bootstrap==1:raise ValueError('bootstrap must be zero or >= 2')
        r=evaluate(a.directory.resolve(),a.bootstrap,a.accept_tool_change)
        import verify_result as vr
        vr.verify(r)
        dest=a.output or default_output(a.directory,r);state=publish_result(dest,r)
    except Refuse as e:print(f'assemble: {e}',file=sys.stderr);return e.code
    except ArithmeticError as e:print(f'assemble: hard gate failed: {e}',file=sys.stderr);return 3
    except (ValueError,OSError)as e:print(f'assemble: {e}',file=sys.stderr);return 1
    print(json.dumps({'C8_full':r.get('C8_full'),'label':r['label'],'final':r['final'],'output':str(dest),'state':state}))
    for line in summary_lines(r):print(line)
    return 0
if __name__=='__main__':sys.exit(main())
