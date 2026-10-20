#!/usr/bin/env python3
"""v3 evaluator (FIT_MODEL_V3.md §4): uniform scaling-variable windows, coverage guard, ratio label for sigma_sys,
population equilibration rule, in-window crossing family with deduplication, standalone crossing aggregation, complete
decision table with reblocking as a prerequisite, multi-campaign (union) inputs. Reuses the v2 machinery (fit_fss,
quotients, select_model) for fits, bootstrap schedule, residual-gate calibration and provenance.

Usage: select_model_v3.py --merged CAMP/merged_b4096_T --reblock CAMP/merged_b2048_T CAMP/merged_b8192_T --out OUT
       (--pre pre.json | --pre-from-v2 FITS_V2_DIR) [--s ...] [--legacy-windows] [--diagnostic] [--bootstrap 300]
       [--calibration 500] [--schedule 20260916] [--workers W] [--analysis-manifest PATH]

pre.json (frozen before any v3 fit; written to OUT/pre.json): {"<s>": {"beta_c": ..., "Delta_epsilon": ..., "source": ...}}.
--legacy-windows reproduces the v2 full/c3 windows (two-point re-derivation only). --diagnostic disables the coverage
guard and marks the run NON-PRODUCTION (what-if reproduction, FIT_MODEL_V3 §2.2).
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, os, re, sys, time, traceback, secrets
from collections import defaultdict, Counter
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from scipy.stats import f as f_dist
import fit_fss, quotients
import select_model as v2
from equilibration import check_population

# ---------------------------------------------------------------- v3 protocol constants (FIT_MODEL_V3.md)
XWINDOWS=[0.45,0.6,0.35]              # quotation preference order x0.45 < x0.6 < x0.35 (§4.2)
LEGACY_WINDOWS={'full':'summary.json','c3':'summary_c3.json'}
VARIANTS=['leading','background','second']; LOG_VARIANT_MAX_DS=0.05
NMINS=[4096,8192,16384]; FIELD_ORDERS=[1,2]; DEGREES=[3,4,5,6,7]; CDEG=2
COVERAGE_MIN_SIZES=4; COVERAGE_MIN_TEMPS=3; BETA_TOL=1e-9   # coincident betas (several campaigns) count as one temperature (R2-004)
RATIO_LABEL=3.0                        # sigma_sys <= 3 x median sigma_stat -> ACCEPTED, else ACCEPTED (sigma_sys-dominated)
XC_WINDOWS=[0.45,0.6]; LOCAL_CHI2_MAX=2.0
def local_degrees(m):return [d for d in range(2,3*m-1) if 6*m-2*(d+1)>=2]   # §4.5: 2 <= d <= 3m-2 (residual dof >= 2 for fit and comparator)
XC_PREFERENCE=['xc0.45_star','xc0.45_plus','xc0.6_star','xc0.6_plus']
IMPLEMENTATION_V3=['FIT_MODEL_V3.md','select_model_v3.py','select_model.py','fit_fss.py','quotients.py','bootstrap_schedule.py','equilibration.py','analyze.py','n0_diagnostic.py','scan_v3_report.py','run_fits_v3.sh',
                   'independence.py','union_check.py','merge_summaries.py','registry.py','completion_check.py','window_filter.py','run_point_v3.sh']   # complete dependency set (IR6-003)
VARIANT_RANK={'leading':0,'background':1,'second':2,'log':3}; WINDOW_RANK={'x0.45':0,'x0.6':1,'x0.35':2,'full':0,'c3':1}

def xpre(e,pre):return 100*(e['beta']-pre['beta_c'])*(e['N']/1024)**(1-pre['Delta_epsilon'])
X_TOL=1e-9   # relative tolerance of the inclusive window boundary (IR7-001): N2 places temperatures exactly at |x_pre| = x_max
def in_window(e,pre,xmax):
    """|x_pre(e)| <= xmax, inclusive up to floating-point reconstruction error (shared by the global-fit and crossing selections)."""
    return abs(xpre(e,pre))<=xmax*(1+X_TOL)+1e-12

def select_window(entries,window,pre,nmin):
    """Entries of one s for a window spec ('x<max>' or legacy name) after the Nmin cut."""
    if window.startswith('x'):
        xmax=float(window[1:]);sub=[e for e in entries if in_window(e,pre,xmax) and e['N']>=nmin]
    else:sub=[e for e in entries if e['N']>=nmin]
    return sub

def distinct_temperatures(betas):
    """Number of distinct simulated temperatures by tolerance clustering of the sorted values (REV-002 / RV3-002): a new temperature starts
    when the gap to the current cluster's start exceeds BETA_TOL. Shared by the coverage guard and the local-degree admissibility."""
    n=0;start=None
    for b in sorted(float(x) for x in betas):
        if start is None or b-start>BETA_TOL:n+=1;start=b
    return n

def coverage_ok(sub):
    """Coverage guard (§4.1): per size the number of DISTINCT simulated temperatures (tolerance BETA_TOL; coincident betas of
    several campaigns count once, R2-004); at least COVERAGE_MIN_SIZES sizes with >= COVERAGE_MIN_TEMPS temperatures."""
    per=defaultdict(list)
    for e in sub:per[e['N']].append(float(e['beta']))
    cnt={int(k):distinct_temperatures(bs) for k,bs in sorted(per.items())}
    return sum(1 for v in cnt.values() if v>=COVERAGE_MIN_TEMPS)>=COVERAGE_MIN_SIZES and len(cnt)>=4, cnt

def freeze_pre(fits_dir):
    """Frozen (beta_c, Delta_eps) per s from the least-bad PRODUCTION-FAMILY central fit of a fits_v2/fits_v3 directory (R2-005):
    fits/<key>.json on the block-4096 input only — never reblock_* records, comparators or failed fits. Records the source."""
    pre={}
    for f in sorted(Path(fits_dir).glob('fits/*.json')):
        if f.name.startswith('reblock_'):continue
        x=json.loads(f.read_text())
        if 'chi2' not in x or x.get('dof',0)<=0 or x.get('comparator_only') or 'error' in x or 'merged_b4096' not in str(x.get('summary_file','')):continue
        s=round(1-2*x['Delta_sigma'],12);c=x['chi2']/x['dof']
        if s not in pre or c<pre[s]['chi2_dof']:pre[s]=dict(beta_c=x['beta_c'],Delta_epsilon=x['Delta_epsilon'],chi2_dof=c,source=f.name,summary_file=x.get('summary_file'),source_sha256=v2.sha256(f))
    if not pre:raise SystemExit(f'{fits_dir}: no production-family central fit on a block-4096 input to freeze the pre-fit from')
    return pre

def verify_coverage(merged,registry,evidences=()):
    """RV3-001 / R11-001: the summary must contain EXACTLY the active union of the registry — for every expected pair and every active campaign
    of that pair, the entries at that (s, N) carry the campaign's complete manifest task set (task ids from the chain diagnostics), the merged
    summary declares coverage 'all', AND the campaign definitions are the ones the completion evidence authenticated: every active campaign's
    manifest hash equals the evidence's manifest_sha256, and the supplied registry is authenticated (its hash, or that of a registry snapshot
    registry_<T>_<host>.json next to the summary's point directory, is a registry_sha256 of the evidence) with an identical portable view."""
    import registry as regmod
    notes=[];rec={}
    if registry is None or not Path(registry).exists():return False,['registry not supplied or missing (--registry)'],rec
    r=regmod.load(Path(registry));root=Path(r['root'])
    S=json.loads((merged/'summary.json').read_text())
    if S.get('coverage') not in (None,'all'):notes.append(f"merged summary coverage {S.get('coverage')!r} != 'all'")
    try:pairs=regmod.validate(r,root,'all')
    except SystemExit as ex:
        # the registry root may point to another host: fall back to the manifests next to the merged summary's point directory
        alt=Path(merged).resolve().parent
        try:r2=dict(r,root=str(alt));pairs=regmod.validate(r2,alt,'all');rec['registry_root_used']=str(alt);root=alt
        except SystemExit as ex2:return False,[f'registry validation failed: {ex2}'],rec
    # R11-001: bind to the evidence — manifest hashes and an authenticated registry
    ev_manifest={};ev_registry=set()
    for ev in [Path(x) for x in (evidences or []) if x is not None and Path(x).exists()]:
        E=json.loads(ev.read_text());ev_registry.add(E.get('registry_sha256'))
        for name,c in (E.get('campaigns') or {}).items():ev_manifest[name]=c.get('manifest_sha256')
    if not ev_manifest:notes.append('no completion evidence supplied: campaign definitions cannot be authenticated')
    for pair,lst in pairs.items():
        for c,_ in lst:
            h=v2.sha256(root/c['dir']/'manifest.json')
            if ev_manifest and ev_manifest.get(c['name'])!=h:notes.append(f"{c['name']}: manifest hash {h[:12]} != evidence {str(ev_manifest.get(c['name']))[:12]}")
    supplied_sha=v2.sha256(registry);auth=None
    if supplied_sha in ev_registry:auth=Path(registry)
    else:
        pt=Path(merged).resolve().parent
        for cand in sorted(pt.glob('registry_*_*.json')):
            if v2.sha256(cand) in ev_registry:auth=cand;break
    if auth is None:notes.append('supplied registry not authenticated by the completion evidence (no matching registry hash or snapshot)')
    else:
        pv=regmod.portable_view(regmod.load(auth));ps=regmod.portable_view(r)
        if pv!=ps:notes.append(f'supplied registry differs from the authenticated snapshot {auth.name} in portable fields {[k for k in ps if ps[k]!=pv.get(k)]}')
        rec['registry_authenticated_by']=str(auth)
    rec['registry_portable_sha256']=hashlib.sha256(json.dumps(regmod.portable_view(r),sort_keys=True).encode()).hexdigest()
    have=defaultdict(set)
    for e in S['entries']:
        for d in e.get('replica_diagnostics',[]):
            if 'task_id' in d:have[(e.get('campaign',''),regmod.key(e['s'],e['N']))].add(int(d['task_id']))
    missing=[];extra=[]
    for pair,lst in pairs.items():
        for c,tasks in lst:
            want={t['id'] for t in tasks};got=have.pop((c['name'],pair),set())
            if got!=want:missing.append((c['name'],pair,len(want-got),len(got-want)))
    extra=[k for k in have]
    if missing:notes.append(f'{len(missing)} (campaign, pair) with incomplete or foreign task sets (campaign, pair, missing, unexpected): {missing[:4]}')
    if extra:notes.append(f'{len(extra)} (campaign, pair) in the summary that are not active in the registry: {extra[:4]}')
    rec.update(registry=str(Path(registry).resolve()),registry_sha256=v2.sha256(registry),expected_pairs=len(pairs),campaign_pairs_checked=sum(len(l) for l in pairs.values()))
    return (not notes),notes,rec

def multi_campaign_pairs(merged):
    """(s, N) pairs measured by more than one campaign: need the §4.7 union schema (FITV3-002 / R2-003), not implemented yet."""
    by=defaultdict(set)
    for e in json.loads((merged/'summary.json').read_text())['entries']:by[(round(float(e['s']),9),int(e['N']))].add(e.get('campaign',''))
    return sorted(k for k,v in by.items() if len(v)>1)

def verify_lineage(merged,reblock_dirs,manifest,evidences,legacy):
    """§4.7 / R2-002 / IR14-002..004: the snapshot manifest must list the SHA-256 of every consumed summary AND of every block archive
    referenced by every consumed summary (all three block sizes); every completion-evidence record (one per host) must itself be
    listed in the manifest, be a PASS record whose registry hash is in the manifest, and the union of the records must cover every
    campaign of the summary without duplicate (campaign, task) entries; for every summary entry the set of chain task ids
    (replica_diagnostics) must equal the evidence's task ids at that (campaign, N, beta). Returns (ok, notes, record)."""
    notes=[];rec={}
    if manifest is None or not Path(manifest).exists():return False,['analysis manifest not supplied or missing'],rec
    H={l.split()[0] for l in Path(manifest).read_text().splitlines() if re.match(r'^[0-9a-f]{64}\s',l)}
    dirs=[merged]+list(reblock_dirs)
    files=[d/w for d in dirs for w in (['summary.json','summary_c3.json'] if legacy else ['summary.json'])]
    missing=[str(f) for f in files if not f.exists() or v2.sha256(f) not in H]
    if missing:notes.append(f'{len(missing)} consumed summaries not listed in the manifest: {missing[:3]}')
    arch=set()
    for d in dirs:
        f=d/'summary.json'
        if f.exists():arch|={str((d/e['blocks_file']).resolve()) for e in json.loads(f.read_text())['entries']}
    inman=sum(1 for q in arch if Path(q).exists() and v2.sha256(Path(q)) in H)
    rec['manifest']=dict(path=str(Path(manifest).resolve()),sha256=v2.sha256(manifest),summaries_verified=len(files)-len(missing),summaries_total=len(files),block_archives_in_manifest=f'{inman}/{len(arch)}')
    if inman<len(arch):notes.append(f'{len(arch)-inman} consumed block archives (all block sizes) not listed in the manifest')
    S=json.loads((merged/'summary.json').read_text())['entries']
    evidences=[Path(x) for x in (evidences or []) if x is not None]
    if not evidences:notes.append('completion evidence not supplied');return False,notes,rec
    recs=[];tasks={};ecamps=set();dups=[]
    for ev in evidences:
        if not ev.exists():notes.append(f'completion evidence {ev} missing');continue
        h=v2.sha256(ev);E=json.loads(ev.read_text());r=dict(path=str(ev.resolve()),sha256=h,result=E.get('result'),host=E.get('host'),listed_in_manifest=h in H);recs.append(r)
        if h not in H:notes.append(f'completion evidence {ev.name} not listed in the manifest')
        if E.get('result')!='PASS':notes.append(f"completion evidence {ev.name} result {E.get('result')!r} != 'PASS'")
        if E.get('registry_sha256') not in H:notes.append(f'{ev.name}: registry hash not in the manifest (different snapshot?)')
        ecamps|=set(E['campaigns'].keys()) if isinstance(E.get('campaigns'),dict) else set(E.get('campaigns') or [])
        for t in E.get('tasks',[]):
            k=(t['campaign'],int(t['task']))
            if k in tasks:dups.append(k)
            tasks[k]=(round(float(t['s']),9) if 's' in t else None,int(t['N']),round(float(t['beta']),12),t.get('seed'),t.get('samples_sha256'))
    rec['completion_evidence']=recs
    if dups:notes.append(f'{len(dups)} (campaign, task) entries duplicated across evidence records, e.g. {dups[:3]}')
    # IR5-001: cross-campaign independence of every chain in the evidence union (shared validator, also used by union_check.py)
    from independence import check_independence
    indep=check_independence([dict(campaign=c,task=tid,s=sv,N=N,beta=b,seed=sd,samples_sha256=h) if sv is not None else dict(campaign=c,task=tid,N=N,beta=b,seed=sd,samples_sha256=h) for (c,tid),(sv,N,b,sd,h) in tasks.items()])
    rec['independence_problems']=indep
    if indep:notes.append('independence: '+'; '.join(indep))
    camps={e.get('campaign','') for e in S}
    if not camps<=ecamps:notes.append(f'campaigns {sorted(camps-ecamps)} absent from the completion evidence')
    # match by (campaign, s, N, beta) (AUDIT-004); legacy evidence without s falls back to (campaign, N, beta) only when the campaign's
    # evidence carries a single s-less task set per (N, beta) — recorded as a fallback
    by=defaultdict(set);legacy=False
    for (c,tid),(sv,N,b,_,_) in tasks.items():
        if sv is None:legacy=True;by[(c,None,N,b)].add(tid)
        else:by[(c,sv,N,b)].add(tid)
    rec['legacy_evidence_without_s']=legacy
    bad=[]
    for e in S:
        ids={int(r['task_id']) for r in e.get('replica_diagnostics',[]) if 'task_id' in r};c=e.get('campaign','');N=int(e['N']);b=round(float(e['beta']),12);sv=round(float(e['s']),9)
        want=by.get((c,sv,N,b)) if (c,sv,N,b) in by else by.get((c,None,N,b))
        if not ids or ids!=(want or set()):bad.append((c,e['s'],N,e['beta']))
    if bad:notes.append(f'{len(bad)} summary entries whose chain task identities differ from the completion evidence, e.g. {bad[:2]}')
    rec['entries_matched']=len(S)-len(bad);rec['evidence_tasks']=len(tasks)
    return (not notes),notes,rec

def ident_of(e):
    """Measurement identity (§4.7): campaign, s, N, beta and the task ids of the chains behind the entry (analyze.py replica
    diagnostics), so that two analyses of the same coordinates from different chains never pass as the same measurement."""
    tasks=tuple(sorted(int(r['task_id']) for r in e.get('replica_diagnostics',[]) if 'task_id' in r))
    return (e.get('campaign',''),round(float(e['s']),9),int(e['N']),round(float(e['beta']),12),tasks)

def load_all(summary,s):
    """Entries of one s with the shared ingestion validation (FITV3-012): no reweighted points (beta != beta_simulated) and
    no repeated measurement identity may enter a global fit or a crossing series."""
    ent=[e for e in json.loads(Path(summary).read_text())['entries'] if abs(e['s']-s)<1e-12]
    bad=[e for e in ent if abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14]
    if bad:raise ValueError(f'{len(bad)} reweighted points (beta != beta_simulated) are not independent FSS data')
    ids=[ident_of(e) for e in ent]
    if len(set(ids))!=len(ids):raise ValueError('repeated measurement identities in the summary')
    return ent

def series_signature(ident_by_n,degrees,pairs):
    """§4.5 deduplication key of a crossing series: the measurement identities and local degree of every size that enters
    the selected pair set (both ends of each doubling pair), plus the pair set itself. Sizes outside the pairs do not enter
    (FITV3-005), so two windows differing only at an unused size are one configuration."""
    used=sorted({m for N in pairs for m in (int(N),2*int(N))})
    return (tuple((m,tuple(ident_by_n.get(m,())),degrees.get(m,degrees.get(str(m)))) for m in used),tuple(int(N) for N in pairs))

# ---------------------------------------------------------------- workers
def w_fit(job):
    """central fit (bootstrap=0) or bootstrapped fit of one configuration on its window-selected entries."""
    try:
        entries=select_window(load_all(job['summary'],job['s']),job['window'],job['pre'],job['Nmin'])
        if len({e['N'] for e in entries})<4:raise ValueError('fewer than four sizes after window selection')
        r=fit_fss.run_fit(job['summary'],entries,job['degree'],CDEG,job['variant'],field_order=job['K'],
                          bootstrap=job.get('bootstrap',0),schedule=job.get('schedule'),tag=job['window'])
        r['config']=v2.cfg_of(job);r['window']=job['window'];r['K']=job['K'];r['points_per_size']=coverage_ok(entries)[1]
        return job,r
    except v2.NUMERICAL_ERRORS as ex:
        return job,dict(error=f'{type(ex).__name__}: {ex}',config=v2.cfg_of(job),window=job['window'],K=job['K'],degree=job['degree'],variant=job['variant'],Nmin=job['Nmin'])

def w_calibration(job):
    entries=select_window(load_all(job['summary'],job['s']),job['window'],job['pre'],job['Nmin'])
    model=fit_fss.ProfileFit(entries,job['degree'],CDEG,job['variant'],field_order=job['K'])
    p0=np.array(job['parameters']);pred=np.array(job['predictions']);rng=np.random.default_rng(np.random.SeedSequence(job['seed']));out=[]
    for _ in range(job['n']):
        pseudo=pred+model.colour(rng.standard_normal(pred.size))
        try:
            f=model.fit(pseudo,initial=p0,multistart=False);ok=bool(f['success'] and not f['flags'])
            T,R,_=v2.residual_stats(f['pulls']);out.append((T,R,ok))
        except v2.NUMERICAL_ERRORS:out.append((np.nan,np.nan,False))
    return job['key'],out

def local_ladder(entries_by_n,ref):
    """Per size: admissible local degrees (dof >= 2 for fit and comparator), F-test ladder p<0.01 -> d*, plus d*+1 if admissible."""
    out={}
    for n,ee in sorted(entries_by_n.items()):
        m=distinct_temperatures(e['beta'] for e in ee)   # RV3-002: admissibility from DISTINCT temperatures; all independent observations stay in the fit
        if m<COVERAGE_MIN_TEMPS:out[n]=dict(usable=False,reason=f'{m} in-window temperatures');continue
        adm=local_degrees(m)
        fits={}
        for d in adm:
            try:
                c=quotients.LocalCurve(ee,ref,d);coef,chi,dof=c.fit();fits[d]=(chi,dof)
            except (ValueError,np.linalg.LinAlgError):break
        if not fits:out[n]=dict(usable=False,reason='no admissible local fit');continue
        degs=sorted(fits);dstar=degs[0]
        for a,b in zip(degs,degs[1:]):
            (c1,d1),(c2,d2)=fits[a],fits[b];q=2*(b-a);F=((c1-c2)/q)/(c2/d2) if c2>0 else np.inf
            pv=float(f_dist.sf(F,q,d2)) if np.isfinite(F) else 0.
            if pv<0.01:dstar=b
            else:break
        chi,dof=fits[dstar];rec=dict(usable=chi/dof<=LOCAL_CHI2_MAX and dof>=2,d_star=dstar,chi2_dof=chi/dof,n_temps=m,admissible=adm)
        nxt=dstar+1
        if nxt in fits:
            c,d=fits[nxt];rec['d_plus']=nxt;rec['plus_usable']=bool(c/d<=LOCAL_CHI2_MAX and d>=2);rec['plus_chi2_dof']=c/d
        else:rec['d_plus']=None;rec['plus_usable']=False
        out[n]=rec
    return out

def w_crossing_series(job):
    """One member of the crossing family: window x_c, degree rule ('star'|'plus'); returns quotients result + samples."""
    ent=[e for e in load_all(job['summary'],job['s']) if in_window(e,job['pre'],job['xc'])]
    byn=defaultdict(list)
    for e in ent:byn[e['N']].append(e)
    ref=float(np.median([e['beta'] for e in ent])) if ent else 0.
    lad=local_ladder(byn,ref);degrees={}
    for n,rec in lad.items():
        # usability is judged per degree rule (§4.5): the d* gate for 'star', the d*+1 gate alone for 'plus' (FITV3-008)
        if job['rule']=='star':
            if rec.get('usable'):degrees[n]=rec['d_star']
        elif rec.get('plus_usable'):degrees[n]=rec['d_plus']
    used=[e for e in ent if e['N'] in degrees]
    ident={int(n):tuple(sorted(ident_of(e) for e in used if e['N']==n)) for n in degrees}
    if len(degrees)<2:return job,dict(crossings=[],local_fit_diagnostics={},warnings=['fewer than two usable sizes'],ladder=lad,degrees={}),np.zeros((job['bootstrap'],0,3)),ident
    qr,smp=quotients.process(used,Path(job['summary']).parent,degrees,job['bootstrap'],np.random.default_rng(1348772),job['schedule'])
    qr['ladder']={str(k):v for k,v in lad.items()};qr['degrees']={str(k):v for k,v in degrees.items()}
    return job,qr,smp,ident

def four_largest_pairs(qr):
    Ns=sorted({r['N'] for r in qr['crossings'] if r['crossing_observable']=='U'})
    return Ns[-4:] if len(Ns)>=4 else []

def series_eval(qr,samples,pairs):
    """crosscheck_series of v2 with the pair set chosen here (four largest usable pairs)."""
    if len(pairs)<4:return dict(eligible=False,reason=f'only {len(pairs)} usable doubling pairs')
    saved=v2.XCHECK_PAIRS;v2.XCHECK_PAIRS=pairs
    try:out=v2.crosscheck_series(qr,samples)
    finally:v2.XCHECK_PAIRS=saved
    out['pairs']=pairs;return out

def standalone_aggregate(series,E,nd):
    """§4.6 standalone crossing aggregation (no global fit): median over E per draw on common-valid draws."""
    if len(E)<2:return dict(status='EXTRAPOLATION UNAVAILABLE (fewer than 2 distinct eligible series)')
    central=np.array([series[n]['central']['Delta_inf'] for n in E]);Dinf=float(np.median(central));spread=float((central.max()-central.min())/2)
    common=np.ones(nd,bool)
    for n in E:common&=np.array(series[n]['draw_converged'],bool)
    need=int(np.ceil(v2.COMMON_VALID_FRAC*nd))
    if common.sum()<need:return dict(status=f'EXTRAPOLATION UNAVAILABLE (common-valid {int(common.sum())} < {need})',Delta_inf_central=Dinf,model_spread=spread)
    per=np.array([series[n]['per_draw_Delta_inf'] for n in E]);Dk=np.median(per[:,common],axis=0);q16,q84=np.percentile(Dk,[16,84])
    grid=[series[n]['central']['omega'] for n in E]
    # Delta_omega' = half-range of the central extrapolations over E, enlarged by the half-range of Delta_inf over the omega'
    # grid points with Delta chi2 <= 1 of every member (§4.6; FITV3-010)
    prof=[series[n]['central'].get('profile_Delta_inf_range') for n in E];prof=[p for p in prof if p]
    omega_half=float((max(p[1] for p in prof)-min(p[0] for p in prof))/2) if prof else None
    return dict(status='ok',Delta_inf=Dinf,sigma_inf=float((q84-q16)/2),model_spread=spread,omega_profile_half_range=omega_half,
                Delta_omega_prime=(spread+omega_half if omega_half is not None else None),omega_range=[min(grid),max(grid)],common_valid=int(common.sum()))

def atomic_write_json(path,obj):
    """Write JSON to a temporary file in the same directory and rename it into place (REV-007)."""
    tmp=Path(f'{path}.tmp.{os.getpid()}.{secrets.token_hex(3)}');tmp.write_text(json.dumps(obj,indent=1,default=float)+'\n');os.replace(tmp,path)   # IR18-003: unique temp name

def suppress_quotation(P):
    """§4.6 row 1 (EQUILIBRATION FAILED): the formal quotation and its uncertainties are withdrawn; the fit that would have been
    quoted is kept only as a labelled diagnostic candidate (IR14-007)."""
    if P.get('quoted') is not None:P['quoted_diagnostic_not_quoted']=P['quoted']
    P['quoted']=None
    if P.get('sigma_sys'):P['sigma_sys']=dict(P['sigma_sys'],value=None,ratio=None,suppressed='EQUILIBRATION FAILED')
    P['crossing_value']=None
    return P

def pair_fallback(raw):
    """§4.6 rows 2, 4 and 7: the two LARGEST usable doubling pairs across the whole crossing family (R2-006), each taken from the
    first series in XC_PREFERENCE that holds it; Δ_eff(U), Δ_eff(Y) with bootstrap errors and the series/degrees provenance."""
    avail={}
    for name in XC_PREFERENCE+[n for n in raw if n not in XC_PREFERENCE]:
        qr=raw.get(name)
        if not qr or not qr.get('crossings'):continue
        need=int(np.ceil(v2.COMMON_VALID_FRAC*int(qr.get('bootstrap_requested') or 0)))   # R17-002: the §4.6 common-valid threshold (90 % of the requested draws)
        for r in qr['crossings']:
            # R17-002: a pair is usable only with a bootstrap error from >= `need` valid draws
            if r['crossing_observable']=='U' and r.get('bootstrap_standard_error') is not None and (r.get('valid_bootstrap_draws') or 0)>=max(need,2):avail.setdefault(int(r['N']),[]).append((name,r))
    if not avail:return dict(status='no usable doubling pair (no U crossing with a bootstrap error from >= %.0f %% of the requested draws)'%(100*v2.COMMON_VALID_FRAC),pairs=[])
    out=[]
    for N in sorted(avail)[-2:]:
        name,r=avail[N][0];se=r.get('bootstrap_standard_error') or [None,None,None]
        out.append(dict(N=int(N),N2=int(r['N2']),series=name,degrees=raw[name].get('degrees',raw[name].get('local_polynomial_degree')),beta_crossing=r['beta_crossing'],
                        Delta_eff_U=r['Delta_epsilon_eff_from_U'],sigma_U=se[2],Delta_eff_Y=r['Delta_epsilon_eff_from_Y'],sigma_Y=se[1],valid_draws=r['valid_bootstrap_draws']))
    return dict(status='ok',pairs=out)

# ---------------------------------------------------------------- main
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--merged',type=Path,required=True);p.add_argument('--reblock',type=Path,nargs='*',default=[])
    p.add_argument('--out',type=Path,required=True);p.add_argument('--s',type=float,nargs='*')
    p.add_argument('--pre',type=Path);p.add_argument('--pre-from-v2',type=Path,help='fits_v2 directory: freeze (beta_c, Delta_eps) from its least-bad fit')
    p.add_argument('--legacy-windows',action='store_true');p.add_argument('--diagnostic',action='store_true')
    p.add_argument('--bootstrap',type=int,default=v2.PROTOCOL_BOOTSTRAP);p.add_argument('--calibration',type=int,default=v2.PROTOCOL_CALIBRATION)
    p.add_argument('--schedule',type=int,default=20260916);p.add_argument('--workers',type=int)
    p.add_argument('--analysis-manifest',type=Path,help='snapshot manifest of the analysed data (required for a production run)')
    p.add_argument('--completion-evidence',type=Path,nargs='*',default=[],help='completion_check --evidence records (one per host) of the campaigns behind the snapshot')
    p.add_argument('--registry',type=Path,help='point registry (campaigns.json or its snapshot) that defines the active union the inputs must cover exactly (RV3-001)')
    a=p.parse_args();t0=time.time()
    # IR18-003: refuse an output directory that already holds a run's artefacts (the driver's MANIFEST.txt and the tee'd select_model_v3.log
    # are created before this process starts and are therefore not evidence of a previous run)
    if a.out.exists() and any((a.out/x).exists() for x in ('fit_v3.json','pre.json','fits','FIT_V3_RESULTS.md')):p.error(f'--out {a.out} already holds a run (IR18-003): use a fresh directory')
    a.out.mkdir(parents=True,exist_ok=True);fitdir=a.out/'fits';fitdir.mkdir(exist_ok=True)
    workers=a.workers or (len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count())
    prov=v2.provenance(a.out,a.merged,a.reblock,sys.argv);here=Path(__file__).resolve().parent
    prov['implementation_v3']={f:v2.sha256(here/f) for f in IMPLEMENTATION_V3 if (here/f).exists()}   # FITV3-014: v3-aware inside the evaluator
    if a.analysis_manifest and a.analysis_manifest.exists():prov['analysis_manifest']=dict(path=str(a.analysis_manifest.resolve()),sha256=v2.sha256(a.analysis_manifest))
    prov['completion_evidence']=[dict(path=str(x.resolve()),sha256=v2.sha256(x)) for x in a.completion_evidence if x.exists()]
    svals=a.s or sorted({e['s'] for e in json.loads((a.merged/'summary.json').read_text())['entries']})
    # frozen pre-fit (beta_c, Delta_eps) per s
    pre={}
    if a.pre:pre={float(k):v for k,v in json.loads(a.pre.read_text()).items()}
    elif a.pre_from_v2:pre=freeze_pre(a.pre_from_v2)
    elif not a.legacy_windows:p.error('--pre or --pre-from-v2 required for x-windows')
    (a.out/'pre.json').write_text(json.dumps({str(k):v for k,v in pre.items()},indent=1)+'\n')
    prov['pre_source']=(dict(kind='pre.json',path=str(a.pre.resolve()),sha256=v2.sha256(a.pre)) if a.pre else
                        dict(kind='fits_v2',path=str(a.pre_from_v2.resolve()),files={f.name:v2.sha256(f) for f in sorted(a.pre_from_v2.glob('fits/*.json'))}) if a.pre_from_v2 else dict(kind='legacy windows'))
    reblock_ok,reblock_notes,reblock_dirs=v2.validate_reblock(a.merged,a.reblock) if a.legacy_windows else validate_inputs(a.merged,a.reblock)
    nonprod=[]
    if a.diagnostic:nonprod.append('diagnostic mode (coverage guard off)')
    if a.bootstrap!=v2.PROTOCOL_BOOTSTRAP:nonprod.append(f'bootstrap {a.bootstrap} != {v2.PROTOCOL_BOOTSTRAP}')
    if a.calibration!=v2.PROTOCOL_CALIBRATION:nonprod.append(f'calibration {a.calibration} != {v2.PROTOCOL_CALIBRATION}')
    if not reblock_ok:nonprod.append('reblocking inputs invalid: '+'; '.join(reblock_notes))
    lin_ok,lin_notes,lin_rec=verify_lineage(a.merged,list(reblock_dirs.values()),a.analysis_manifest,a.completion_evidence,a.legacy_windows)
    prov['lineage']=dict(verified=lin_ok,notes=lin_notes,**lin_rec)
    if not lin_ok:nonprod.append('snapshot lineage not verified: '+'; '.join(lin_notes))
    cov_ok,cov_notes,cov_rec=verify_coverage(a.merged,a.registry,a.completion_evidence)   # RV3-001 / R11-001: exact, authenticated coverage
    prov['coverage']=dict(verified=cov_ok,notes=cov_notes,**cov_rec)
    if not cov_ok:nonprod.append('registry coverage not verified: '+'; '.join(cov_notes))
    multi=multi_campaign_pairs(a.merged);prov['multi_campaign_pairs']=[list(k) for k in multi]
    if multi:   # §4.7 union: every entry of a multi-campaign summary must carry its campaign stamp and chain task ids (merge_summaries.py)
        S=json.loads((a.merged/'summary.json').read_text())
        if not S.get('union') or any(not e.get('campaign') or not e.get('task_ids') for e in S['entries']):nonprod.append('multi-campaign summary without union stamps (campaign, task_ids) — merge with merge_summaries.py (§4.7)')
    production=not nonprod
    report={'protocol':'FIT_MODEL_V3.md','production':production,'non_production_reasons':nonprod,'legacy_windows':a.legacy_windows,
            'schedule':a.schedule,'bootstrap':a.bootstrap,'calibration':a.calibration,'pre':{str(k):v for k,v in pre.items()},
            'reblock_inputs':{str(b):str(d) for b,d in reblock_dirs.items()},'provenance':prov,'points':{},'errors':[]}
    print(f'production={production} {nonprod} legacy={a.legacy_windows}',flush=True)
    pool=Pool(workers)
    try:
        for s in svals:
            try:run_point(a,s,pool,fitdir,report,reblock_dirs,production,pre.get(round(s,12)),t0)
            except Exception as ex:
                report['errors'].append(dict(s=s,error=f'{type(ex).__name__}: {ex}',traceback=traceback.format_exc()));print(f'  point s={s} FAILED: {ex}',flush=True)
    finally:
        pool.close();pool.join()
        atomic_write_json(a.out/'fit_v3.json',report)   # REV-007: never leave a half-written result behind
        try:write_report(report,a.out/'FIT_V3_RESULTS.md')
        except Exception as ex:report['errors'].append(dict(error=f'report: {ex}'));atomic_write_json(a.out/'fit_v3.json',report)
        with (a.out/'MANIFEST.txt').open('a') as m:
            for f in sorted(a.out.glob('xcheck_*'))+[a.out/'fit_v3.json',a.out/'pre.json']:
                if f.exists():m.write(f'{v2.sha256(f)}  {f}\n')
            m.write(f"{time.strftime('%F_%T')} done in {time.time()-t0:.0f}s; errors {len(report['errors'])}\n")
    print(a.out/'FIT_V3_RESULTS.md')
    if report['errors']:sys.exit(1)

def validate_inputs(merged,reblock):
    """§4.7 input validation for x-window mode: uniform block size per input, sizes exactly 2048/4096/8192, identical
    measurement identities (campaign, s, N, beta, chain task ids; FITV3-011) across the three inputs, unique within each,
    and no reweighted entries."""
    notes=[];byblock={}
    def ids(d):
        S=json.loads((d/'summary.json').read_text())['entries'];bs={e['block_size'] for e in S}
        idn=[ident_of(e) for e in S]
        if len(set(idn))!=len(idn):notes.append(f'{d}: duplicate measurement identities')
        if any(abs(e['beta']-e.get('beta_simulated',e['beta']))>1e-14 for e in S):notes.append(f'{d}: reweighted entries present')
        return bs,set(idn)
    bs0,id0=ids(merged)
    if bs0!={4096}:notes.append(f'block-4096 input has block sizes {sorted(bs0)}')
    for d in reblock:
        if not (d/'summary.json').exists():notes.append(f'{d}: missing summary.json');continue
        bs,idn=ids(d)
        if len(bs)!=1:notes.append(f'{d}: mixed block sizes {sorted(bs)}');continue
        b=bs.pop()
        if b not in v2.REBLOCK_BLOCKS:notes.append(f'{d}: block size {b} not in {v2.REBLOCK_BLOCKS}');continue
        if b in byblock:notes.append(f'{d}: duplicate block size {b}');continue
        if idn!=id0:notes.append(f'{d}: measurement identities differ from the block-4096 input');continue
        byblock[b]=d
    missing=[b for b in v2.REBLOCK_BLOCKS if b not in byblock]
    if missing:notes.append(f'reblocking inputs missing for block sizes {missing}')
    return (not notes),notes,byblock

def run_point(a,s,pool,fitdir,report,reblock_dirs,production,pre,t0):
    ds,dsl=v2.ds_of(s);P={'Delta_sigma':ds,'s':s,'pre':pre};print(f'=== s={s} (Delta_sigma={dsl}) ===',flush=True)
    entries_all=load_all(a.merged/'summary.json',s)
    # ---- equilibration (population rule, §4.4)
    eq=check_population(entries_all);P['equilibration']=eq
    print(f"  equilibration (population): {'PASS' if eq['passed'] else 'FAIL'} groups {eq['groups']} hot/cold>3: {eq['groups_hotcold_over_3']} half>3: {eq['replicas_half_z_over_3']}",flush=True)
    # ---- family
    if a.legacy_windows:windows={w:str(a.merged/f) for w,f in LEGACY_WINDOWS.items()}
    else:
        if pre is None:raise ValueError('no frozen (beta_c, Delta_eps) for this s')
        windows={f'x{x}':str(a.merged/'summary.json') for x in XWINDOWS}
    variants=VARIANTS+(['log'] if (ds<=LOG_VARIANT_MAX_DS and not a.legacy_windows) else [])
    configs=[dict(summary=windows[w],s=s,ds=dsl,window=w,variant=v,Nmin=n,K=K,pre=pre) for w,v,n,K in itertools.product(windows,variants,NMINS,FIELD_ORDERS)]
    # coverage guard per configuration (after window and Nmin selection)
    admissible=[];coverage={}
    for c in configs:
        sub=select_window(load_all(c['summary'],s),c['window'],pre,c['Nmin']);ok,per=coverage_ok(sub)
        coverage[v2.cfg_of(c)]=dict(admissible=bool(ok or a.diagnostic),points_per_size=per)
        if ok or a.diagnostic:admissible.append(c)
    P['coverage']=coverage;print(f'  configurations: {len(configs)}, admissible after coverage guard: {len(admissible)}',flush=True)
    jobs=[{**c,'degree':d} for c in admissible for d in DEGREES];fits={}
    for job,r in pool.imap_unordered(w_fit,jobs):
        fits[v2.key_of(job)]=r;(fitdir/(v2.key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    # ---- ladder, comparator, gates (v2 logic)
    selection={};comp_jobs=[]
    for ci,c in enumerate(admissible):
        get=lambda d:fits.get(v2.key_of({**c,'degree':d}));dstar=DEGREES[0];steps=[]
        for d in DEGREES[:-1]:
            lo,hi=get(d),get(d+1)
            if lo is None or hi is None or 'error' in lo or 'error' in hi or hi['flags'] or lo['flags'] or hi['dof']<=0:steps.append(dict(from_degree=d,to_degree=d+1,p=None,note='fit missing or flagged: ladder stops'));break
            q=hi['nlinear']-lo['nlinear'];F=((lo['chi2']-hi['chi2'])/q)/(hi['chi2']/hi['dof']) if hi['chi2']>0 else np.inf
            pv=float(f_dist.sf(F,q,hi['dof'])) if np.isfinite(F) else 0.;steps.append(dict(from_degree=d,to_degree=d+1,F=float(F),p=pv,significant=bool(pv<v2.LADDER_P)))
            if pv<v2.LADDER_P:dstar=d+1
            else:break
        selection[v2.cfg_of(c)]=dict(config={k:v for k,v in c.items() if k!='pre'},config_index=ci,d_star=dstar,ladder=steps)
        if dstar==DEGREES[-1]:comp_jobs.append({**c,'degree':DEGREES[-1]+1})
    for job,r in pool.imap_unordered(w_fit,comp_jobs):
        r['comparator_only']=True;fits[v2.key_of(job)]=r;(fitdir/(v2.key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    boot_jobs=[]
    for cfg,sel in selection.items():
        c=next(x for x in admissible if v2.cfg_of(x)==cfg);r=fits.get(v2.key_of({**c,'degree':sel['d_star']}));reasons=[]
        if r is None or 'error' in r:reasons.append('fit at d* missing')
        else:
            if r['chi2']/r['dof']>v2.CHI2_DOF_MAX:reasons.append(f"chi2/dof {r['chi2']/r['dof']:.2f} > {v2.CHI2_DOF_MAX}")
            if r['flags']:reasons.append('flags: '+'; '.join(r['flags']))
            bad=[q for q,v in r['mean_abs_pull'].items() if v>v2.PULL_MAX]
            if bad:reasons.append(f'mean |pull| > {v2.PULL_MAX} for {bad}')
        sel['cheap_gate_failures']=reasons
        if not reasons:boot_jobs.append({**c,'degree':sel['d_star'],'bootstrap':a.bootstrap,'schedule':a.schedule})
    print(f'  ladder done; {len(boot_jobs)} candidates; bootstrapping ({time.time()-t0:.0f}s)',flush=True)
    for job,r in pool.imap_unordered(w_fit,boot_jobs):
        fits[v2.key_of(job)]=r;(fitdir/(v2.key_of(job)+'.json')).write_text(json.dumps(r,indent=1)+'\n')
    need_valid=int(np.ceil(v2.BOOT_VALID_FRAC*a.bootstrap));calib=[]
    for cfg,sel in selection.items():
        if sel['cheap_gate_failures']:sel['quotable']=False;sel['reasons']=sel['cheap_gate_failures'];continue
        c=next(x for x in admissible if v2.cfg_of(x)==cfg);r=fits[v2.key_of({**c,'degree':sel['d_star']})];reasons=[]
        if 'error' in r or 'bootstrap' not in r:sel['quotable']=False;sel['reasons']=['bootstrap failed'];continue
        b=r['bootstrap'];sel['bootstrap_valid']=b['valid']
        if b['valid']<need_valid:reasons.append(f"bootstrap valid {b['valid']} < {need_valid}")
        sigma=(b['percentile_16_50_84'][2]-b['percentile_16_50_84'][0])/2 if b['percentile_16_50_84'] else None;sel['sigma_stat']=sigma
        comp=fits.get(v2.key_of({**c,'degree':sel['d_star']+1}))
        if comp is None or 'error' in comp or comp['flags'] or not comp['success']:reasons.append('stability-unresolved: comparator missing, non-converged or flagged')
        elif sigma is None or abs(comp['Delta_epsilon']-r['Delta_epsilon'])>v2.STABILITY_SIGMAS*sigma:reasons.append('order-unstable')
        sel['comparator_Delta_epsilon']=None if comp is None or 'error' in comp else comp['Delta_epsilon'];sel['reasons']=reasons
        if not reasons:calib.append(cfg)
    cjobs=[];chunk=25
    for cfg in calib:
        sel=selection[cfg];c=next(x for x in admissible if v2.cfg_of(x)==cfg);r=fits[v2.key_of({**c,'degree':sel['d_star']})]
        T,R,per=v2.residual_stats(r['pulls']);sel['residual_gate']=dict(T_observed=T,R_observed=R,per_observable=per)
        for i in range(0,a.calibration,chunk):
            cjobs.append({**c,'degree':sel['d_star'],'key':cfg,'parameters':r['parameters'],'predictions':r['predictions'],'seed':v2.calibration_seed(a.schedule,s,sel['config_index'],i//chunk),'n':min(chunk,a.calibration-i)})
    print(f'  residual-gate calibration: {len(calib)} candidates ({time.time()-t0:.0f}s)',flush=True)
    null=defaultdict(list)
    for key,out in pool.imap_unordered(w_calibration,cjobs):null[key].extend(out)
    for cfg in calib:
        sel=selection[cfg];g=sel['residual_gate'];arr=np.array(null[cfg],float);ok=arr[:,2]>0.5
        g['null_replicates']=int(len(arr));g['null_nonconverged']=int((~ok).sum())
        if (~ok).mean()>v2.CALIB_FAIL_MAX:g['decision']='not evaluable';sel['reasons'].append('residual gate not evaluable')
        else:
            g['T_q01']=float(np.quantile(arr[ok,0],0.01));g['R_q99']=float(np.quantile(arr[ok,1],0.99))
            rej=g['T_observed']<g['T_q01'] or g['R_observed']>g['R_q99'];g['decision']='structured residuals' if rej else 'pass'
            if rej:sel['reasons'].append('structured residuals')
        sel['quotable']=not sel['reasons']
    for sel in selection.values():sel.setdefault('quotable',False)
    quotable=[]
    for cfg,sel in selection.items():
        if sel['quotable']:
            c=sel['config'];r=fits[v2.key_of({**c,'degree':sel['d_star']})]
            quotable.append(dict(config=cfg,degree=sel['d_star'],Nmin=c['Nmin'],window=c['window'],variant=c['variant'],K=c['K'],Delta_epsilon=r['Delta_epsilon'],
                                 sigma_stat=sel['sigma_stat'],chi2=r['chi2'],dof=r['dof'],nparams=r['nlinear']+r['nonlinear_parameters'],key=v2.key_of({**c,'degree':sel['d_star']})))
    P['selection']=selection;P['quotable']=quotable
    # ---- crossing family (in-window; legacy mode uses the v2 windows/degrees)
    series={};idents={};npz={};raw={}
    if a.legacy_windows:
        qjobs=[dict(summary=windows[w],s=s,degree=d,window=w,bootstrap=a.bootstrap,schedule=a.schedule) for d in v2.XCHECK_DEGREES for w in LEGACY_WINDOWS]
        for job,qr,smp in pool.imap_unordered(v2.w_quotients,qjobs):
            name=f"deg{job['degree']}_{job['window']}";series[name]=v2.crosscheck_series(qr,smp);series[name]['pairs']=list(v2.XCHECK_PAIRS);idents[name]=(name,);npz[name]=np.asarray(smp);raw[name]=qr
    else:
        qjobs=[dict(summary=str(a.merged/'summary.json'),s=s,pre=pre,xc=xc,rule=rule,bootstrap=a.bootstrap,schedule=a.schedule) for xc in XC_WINDOWS for rule in ('star','plus')]
        for job,qr,smp,ident in pool.imap_unordered(w_crossing_series,qjobs):
            name=f"xc{job['xc']}_{job['rule']}";pairs=four_largest_pairs(qr);raw[name]=qr
            series[name]=series_eval(qr,smp,pairs) if qr['crossings'] else dict(eligible=False,reason='; '.join(qr.get('warnings',[])) or 'no crossings')
            series[name]['degrees']=qr.get('degrees',{});series[name]['ladder']=qr.get('ladder',{});series[name]['warnings']=qr.get('warnings',[])
            idents[name]=series_signature(ident,qr.get('degrees',{}),pairs);npz[name]=np.asarray(smp)   # FITV3-005: used sizes only
            (a.out/f'quot_{name}_ds{dsl}.json').write_text(json.dumps(qr,indent=1,default=float)+'\n')
    # deduplicate eligible series by identity (measurements, degrees, pairs)
    E=[];seen=set()
    for n,sr in series.items():
        if sr.get('eligible') and idents[n] not in seen:E.append(n);seen.add(idents[n])
    dup=[n for n,sr in series.items() if sr.get('eligible') and n not in E]
    X={'eligible_distinct':E,'duplicates_removed':dup}
    np.savez_compressed(a.out/f'xcheck_ds{dsl}.samples.npz',**npz)
    # ---- reblocking (only with a quoted fit)
    quoted=None;rb={}
    if quotable:
        nmin=min(q['Nmin'] for q in quotable)
        quoted=min([q for q in quotable if q['Nmin']==nmin],key=lambda q:(q['nparams'],WINDOW_RANK[q['window']],VARIANT_RANK[q['variant']],q['K'],q['degree'],q['config']))
        for b,d in sorted(reblock_dirs.items()):
            job=dict(summary=str(d/'summary.json'),s=s,ds=dsl,window=quoted['window'],variant=quoted['variant'],Nmin=quoted['Nmin'],K=quoted['K'],degree=quoted['degree'],pre=pre,bootstrap=a.bootstrap,schedule=a.schedule)
            if a.legacy_windows:job['summary']=str(d/LEGACY_WINDOWS[quoted['window']])
            _,r=w_fit(job)
            if 'error' in r:rb[str(b)]=dict(sigma_stat=None,within_tol=False,note='fit failed: '+r['error']);continue
            pc=r['bootstrap']['percentile_16_50_84'];sig=(pc[2]-pc[0])/2 if pc else None;problems=[]
            if not r['success'] or r['flags']:problems.append('central fit not converged/unflagged')
            if r['bootstrap']['valid']<need_valid:problems.append(f"bootstrap valid {r['bootstrap']['valid']} < {need_valid}")
            if sig is None:problems.append('no valid draws')
            rb[str(b)]=dict(Delta_epsilon=r['Delta_epsilon'],sigma_stat=sig,valid=r['bootstrap']['valid'],within_tol=(False if problems or not quoted['sigma_stat'] else bool(abs(sig-quoted['sigma_stat'])<=v2.REBLOCK_TOL*quoted['sigma_stat'])),note='; '.join(problems) or None)
            (fitdir/f"reblock_b{b}_{quoted['key']}.json").write_text(json.dumps(r,indent=1)+'\n')
    P['quoted']=quoted;P['reblocking']=rb
    # ---- sigma_sys, cross-check, decision table (§4.6)
    vals=[q['Delta_epsilon'] for q in quotable]
    cov_ok=len(quotable)>=v2.SYS_MIN_FITS and len({q['Nmin'] for q in quotable})>=v2.SYS_MIN_NMIN and len({q['variant'] for q in quotable})>=v2.SYS_MIN_VARIANTS
    sig_sys=(max(vals)-min(vals))/2 if cov_ok else None;med_stat=float(np.median([q['sigma_stat'] for q in quotable])) if quotable else None
    P['sigma_sys']=dict(value=sig_sys,coverage_ok=cov_ok,n_quotable=len(quotable),range=[min(vals),max(vals)] if vals else None,median_sigma_stat=med_stat,
                        ratio=(sig_sys/med_stat if sig_sys is not None and med_stat else None))
    audit={}
    if quoted:
        qfit=fits[quoted['key']];Xp=v2.paired_comparison(series,E,qfit['bootstrap']['draws'],a.bootstrap,quoted['Delta_epsilon'])
        # R16-004: the paired selection and differences behind the decision stay in the xcheck audit file (as in v2); only the in-report summary is trimmed
        audit={k:(v.tolist() if hasattr(v,'tolist') else v) for k in ('global_valid_mask','common_valid_mask','per_draw_Delta_inf_median','paired_differences') if (v:=Xp.pop(k,None)) is not None}
        X.update(Xp)
    SA=standalone_aggregate(series,E,a.bootstrap);X['standalone']=SA
    # §4.6 numerical fallbacks (FITV3-013): the crossing value with both uncertainties, and the two largest usable pairs' estimates
    P['crossing_value']=(dict(Delta_inf=SA['Delta_inf'],sigma_inf=SA['sigma_inf'],Delta_omega_prime=SA['Delta_omega_prime'],series=list(E)) if SA['status']=='ok' else None)
    P['fallback_pairs']=pair_fallback(raw)
    X['series']={n:{k:v for k,v in sr.items() if k not in ('per_draw_Delta_inf','draw_valid','draw_converged','ladder')} for n,sr in series.items()}
    P['crosscheck']=X
    rb_ok=len(rb)==len(v2.REBLOCK_BLOCKS) and all(v['within_tol'] for v in rb.values())
    n_adm=len(admissible)
    if not eq['passed']:dec='EQUILIBRATION FAILED'
    elif n_adm==0:dec='COVERAGE-LIMITED'+(' (crossing value)' if SA['status']=='ok' else ' (finite-size estimates)')
    elif not quotable:dec='MODEL-LIMITED (crossing value)' if SA['status']=='ok' else 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE'
    elif not cov_ok:dec='CONDITIONAL (sigma_sys coverage absent)'
    elif len(rb)<len(v2.REBLOCK_BLOCKS):dec='REBLOCKING UNAVAILABLE'
    elif not rb_ok:dec='REBLOCKING FAILED'
    elif X.get('status','')!='pass':dec='CROSS-CHECK UNAVAILABLE' if 'UNAVAILABLE' in X.get('status','UNAVAILABLE') else 'CROSS-CHECK FAILED'
    elif sig_sys<=RATIO_LABEL*med_stat:dec='ACCEPTED'
    else:dec='ACCEPTED (sigma_sys-dominated)'
    if dec=='EQUILIBRATION FAILED':suppress_quotation(P)   # §4.6 row 1: no quoted number (IR14-007)
    P['decision']=dec if production else f'NON-PRODUCTION ({"; ".join(report["non_production_reasons"])}); would be: {dec}'
    report['points'][dsl]=P
    (a.out/f'xcheck_ds{dsl}.json').write_text(json.dumps(dict(eligible_distinct=E,duplicates=dup,series=series,standalone=SA,paired={**{k:v for k,v in X.items() if k!='series'},**audit}),indent=1,default=float)+'\n')
    qd=f"{quoted['config']} d{quoted['degree']}: {quoted['Delta_epsilon']:.5f} +- {v2.f5(quoted['sigma_stat'])}" if quoted else 'none'
    print(f"  quoted {qd} | sigma_sys={v2.f5(sig_sys)} ratio={v2.f5(P['sigma_sys']['ratio'],'%.1f')} | E={E} | xcheck={X.get('status','-')} | decision={P['decision']} ({time.time()-t0:.0f}s)",flush=True)

def write_report(rep,path):
    L=[f"# FIT v3 results ({'production' if rep['production'] else 'NON-PRODUCTION: '+'; '.join(rep['non_production_reasons'])}; {'legacy windows' if rep['legacy_windows'] else 'x-windows'}; schedule {rep['schedule']}, bootstrap {rep['bootstrap']}, calibration {rep['calibration']})",'',
       'Protocol: FIT_MODEL_V3.md §4 (decision table §4.6). Selection blind to Delta_epsilon; (beta_c, Delta_eps) for the windows frozen in pre.json.','']
    if rep.get('errors'):L+=['**Errors:** '+'; '.join(e['error'] for e in rep['errors']),'']
    for ds,P in rep['points'].items():
        L+=[f"## Delta_sigma = {ds} (s = {P['s']})",'',f"**Decision: {P['decision']}**",'']
        q=P.get('quoted');ss=P['sigma_sys']
        if P.get('quoted_diagnostic_not_quoted'):
            qd=P['quoted_diagnostic_not_quoted'];L+=[f"NOT QUOTED (equilibration failed): diagnostic candidate {qd['config']} degree {qd['degree']} gave Delta_epsilon {qd['Delta_epsilon']:.5f} ± {v2.f5(qd['sigma_stat'])}; no value is quoted for this point.",'']
        if q:L+=[f"Quoted: Delta_epsilon = {q['Delta_epsilon']:.5f} ± {v2.f5(q['sigma_stat'])} (stat)"+(f" ± {ss['value']:.5f} (sys; ratio to median sigma_stat {ss['ratio']:.1f})" if ss['value'] is not None else ' (sigma_sys unresolved)'),f"from {q['config']} degree {q['degree']} (chi2/dof {q['chi2']:.1f}/{q['dof']}); quotable {ss['n_quotable']}; range {ss['range']}",'']
        eq=P['equilibration'];L.append(f"Equilibration (population rule): {'PASS' if eq['passed'] else 'FAIL'} — groups {eq['groups']}, hot/cold |z|>3: {eq['groups_hotcold_over_3']} ({eq['fraction_hotcold_over_3']:.1%}), half-chain |z|>3: {eq['replicas_half_z_over_3']} ({eq['fraction_half_over_3']:.1%})")
        cov=P['coverage'];L.append(f"Coverage guard: {sum(1 for v in cov.values() if v['admissible'])}/{len(cov)} configurations admissible")
        L+=['','| configuration | d* | chi2/dof | Delta_eps | sigma_stat | quotable | reasons |','|---|---|---|---|---|---|---|']
        for cfg,sel in P['selection'].items():
            fitkey=f"ds{ds}_{cfg}_deg{sel['d_star']}";r=None
            try:r=json.load(open(Path(path).parent/'fits'/(fitkey+'.json')))
            except Exception:pass
            L.append(f"| {cfg} | {sel['d_star']} | {(('%.2f'%(r['chi2']/r['dof'])) if r and 'chi2' in r else '—')} | {v2.f5(r.get('Delta_epsilon') if r else None)} | {v2.f5(sel.get('sigma_stat'))} | {'yes' if sel['quotable'] else 'no'} | {'; '.join(sel.get('reasons',[]))[:140]} |")
        X=P['crosscheck'];L+=['',f"Cross-check: {X.get('status','-')}; distinct eligible series {X['eligible_distinct']} (duplicates removed: {X['duplicates_removed']}); standalone: {X['standalone']}"]
        cv=P.get('crossing_value');fb=P.get('fallback_pairs') or {}
        L.append('Crossing value: '+(f"Delta_inf = {cv['Delta_inf']:.5f} ± {v2.f5(cv['sigma_inf'])} (sigma_inf) ± {v2.f5(cv['Delta_omega_prime'])} (Delta_omega') from {cv['series']}" if cv else 'unavailable'))
        L.append('Largest usable pairs: '+(', '.join(f"{q['N']}-{q['N2']}: Delta_eff(U) = {q['Delta_eff_U']:.5f} ± {v2.f5(q['sigma_U'])}, Delta_eff(Y) = {q['Delta_eff_Y']:.5f} ± {v2.f5(q['sigma_Y'])} ({q['valid_draws']} valid draws; series {q['series']})" for q in fb.get('pairs',[])) if fb.get('pairs') else fb.get('status','—')))
        for n,sr in X['series'].items():
            c=sr.get('central') or {};L.append(f"- {n}: "+(f"Delta_inf {c['Delta_inf']:.5f} omega' {c['omega']:.2f} chi2/dof {c['chi2']:.2f}/{c['dof']} pairs {sr.get('pairs')}" if 'Delta_inf' in c else '')+(f" — {sr.get('reason')}" if not sr.get('eligible') else ' — eligible'))
        if P.get('reblocking'):L.append('Reblocking: '+'; '.join(f"block {k}: sigma_stat {v2.f5(v['sigma_stat'])} ({'ok' if v['within_tol'] else 'FAIL'}{'; '+v['note'] if v.get('note') else ''})" for k,v in P['reblocking'].items()))
        L.append('')
    Path(path).write_text('\n'.join(L)+'\n')

if __name__=='__main__':main()
