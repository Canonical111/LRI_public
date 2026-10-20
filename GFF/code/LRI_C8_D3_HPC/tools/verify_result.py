#!/usr/bin/env python3
"""Re-verify a C8(3) result file (PLAN E.3; C7I-02/11): every stored gate block and every derived number is recomputed
from the result's own fields and compared; floats to 1e-10 of their sibling scale (the largest magnitude in the same
list, else the value), non-float leaves identically; an added or a deleted key fails.

Recomputed: the coefficients, power-free coefficients and power differences from the stored means (the vendored
coefficients); C_n, the top SEs and the power correction from their vectors; the hard gates (top_slot, loop7 at order
8, affinity) from the means; the power null rows (with the PP8 marker) from the stored differences and errors; the
lower-order pulls from the coefficients, SEs and references/lower_order_d3.json; the b_3^p(0) control pull; the
power_protocol and assembly blocks (the vendored pins); the
consistency flags (a/b pull, bootstrap/covariance ratio) and the coverage records of the gates block, the campaign
record included (assemble.evaluate's: null for a test campaign; 24 groups, twice the tail monitor's graphs and the
campaign role as its source for production and pilot_full); error_by_loop summing to Var(C_order), its schema (sectors
free and power, loops 3..order, rows {variance, share, se}) and every share = variance/Var(C_order) and se =
sqrt(variance) recomputed (S3-008); every number finite (a NaN, an infinity or an overflowing literal such as 1e309 is
rejected, also when the file is read: S3-R2-003); the variance
identities SE_i = sqrt(V_ii) and V_nn = power_free_se^2 + power_correction_se^2 + 2 power_free_correction_covariance;
the tail monitor's flags from its listed rows. The provenance its writer always records is required: assemble.evaluate's
keys (EVAL_PROV, the tail monitor, a campaign role matching the label, 24 merged groups, each with its scientific
identity, science_sha256, S3-R2-007) or combine.py's (batches, combined_from). A combined result carries its design
identity and every batch's role and scientific identities, and its batch counts are consistent (combined_check, S3-007):
count = per_batch = combined_from >= 1, dof = count - 1, count <= planned, one design and one role, every per-batch C8
finite and its sampling SE positive and finite, the chi-square recomputed from per_batch and both it and the stored one
finite (S3-R2-003); a final result needs exactly the planned count of production batches. In directory mode the result
must also belong to the campaign (bind, S3-006): its source manifest, merged files, scientific identities, role,
test_only flag, backend, build, numerics, MP mode, allocation and two-loop pin equal the campaign's current ones. A
pilot_subset campaign has no result: `verify_result.py RUN` refuses it (65).

  verify_result.py RESULT.json            exit 0 verified, 1 a difference (named), 65 a pilot_subset campaign directory
  verify_result.py RUN                    the default result file of a campaign directory, bound to that campaign
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,canon,digest
import assemble as asm

PHYS=('coefficients','standard_errors','covariance','power_free_se','power_free_coefficients','power_correction','power_correction_se',
      'power_free_correction_covariance','power_differences','power_difference_errors','means','error_by_loop','campaigns','half_streams','bootstrap',
      'lower_order_checks','power_null_checks','b3p_control','hard_gates','power_protocol','assembly','gates','sampling_standard_error')
META=('schema','dimension','order','epsilon','label','scope','final')
PROV=('source_manifest_sha256','merged_sha256','science_sha256','backend','build','numerics','mp_check','campaign_role','test_only','allocation',
      'two_loop_sha256','references_sha256','tool_sha256','accepted_tool_changes','tail_monitor','batches','combined_from')
HIDDEN=('test_partial','sizing_only','partial_values')
# Provenance that assemble.evaluate always writes (top level), and that combine.py always writes (beside the values).
EVAL_PROV=('source_manifest_sha256','merged_sha256','science_sha256','backend','build','numerics','mp_check','campaign_role','test_only','allocation',
           'two_loop_sha256','references_sha256','tool_sha256')
COMBINE_PROV=('batches','combined_from')
ROLE_OF_LABEL={'production':'production','pilot':'pilot_full','test':'test'}   # assemble.evaluate's view per campaign role
REL=1e-10

class Mismatch(ValueError):pass

def _num(x)->bool:return isinstance(x,(int,float))and not isinstance(x,bool)
def _fin(x)->bool:return _num(x)and math.isfinite(x)

def _bad_constant(name:str):raise Mismatch(f'non-finite JSON constant {name} (S3-R2-003)')
def _strict_float(text:str)->float:
    v=float(text)
    if not math.isfinite(v):raise Mismatch(f'number {text} overflows to a non-finite float (S3-R2-003)')
    return v
def strict_load(path:Path):
    """A result file as JSON with every number finite: NaN, Infinity and -Infinity, and literals that overflow a float
    (1e309), are rejected (S3-R2-003)."""
    return json.loads(Path(path).read_text(),parse_constant=_bad_constant,parse_float=_strict_float)

def nonfinite(x,where:str='result')->None:
    """Every number of x is finite (results are written with allow_nan=False, so a non-finite value is tampering)."""
    if isinstance(x,dict):
        for k,v in x.items():nonfinite(v,f'{where}.{k}')
    elif isinstance(x,(list,tuple)):
        for i,v in enumerate(x):nonfinite(v,f'{where}[{i}]')
    elif isinstance(x,float)and not math.isfinite(x):raise Mismatch(f'{where}: {x!r} is not finite (S3-R2-003)')

def compare(a,b,where:str,scale:float=0.)->None:
    if _num(a)and _num(b):
        if type(a)is int and type(b)is int:
            if a!=b:raise Mismatch(f'{where}: {a} != {b}')
            return
        if a==b:return
        if not(math.isfinite(a)and math.isfinite(b)):raise Mismatch(f'{where}: {a} != {b}')
        if abs(a-b)>REL*max(abs(a),abs(b),scale):raise Mismatch(f'{where}: {a!r} differs from the recomputed {b!r}')
        return
    if isinstance(a,dict)and isinstance(b,dict):
        if set(a)!=set(b):raise Mismatch(f'{where}: keys differ (stored extra {sorted(set(a)-set(b))[:4]}, missing {sorted(set(b)-set(a))[:4]})')
        for k in a:compare(a[k],b[k],f'{where}.{k}')
        return
    if isinstance(a,(list,tuple))and isinstance(b,(list,tuple)):
        if len(a)!=len(b):raise Mismatch(f'{where}: length {len(a)} != {len(b)}')
        sc=max([abs(x)for x in [*a,*b]if _num(x)and math.isfinite(x)],default=0.)
        for i,(x,y)in enumerate(zip(a,b)):compare(x,y,f'{where}[{i}]',sc)
        return
    if a!=b:raise Mismatch(f'{where}: {a!r} != {b!r}')

def jsonable(x):return json.loads(json.dumps(x,allow_nan=False,default=lambda o:o.tolist()if hasattr(o,'tolist')else float(o)))

def check_keys(r:dict)->dict:
    """The key set of a result: META, then either the physical fields (production) or None at the top and the fields
    under exactly one hidden key (test, pilot, partial), then provenance keys only."""
    if r.get('schema')!=asm.RESULT_SCHEMA or r.get('dimension')!=3:raise Mismatch(f'schema {r.get("schema")!r} is not {asm.RESULT_SCHEMA}')
    order=r.get('order');n=order
    missing=[k for k in META if k not in r]
    if missing:raise Mismatch(f'deleted keys {missing}')
    top=(f'C{n}_full',f'power_free_C{n}')
    hidden=[k for k in HIDDEN if k in r]
    if r['label']=='production':
        if hidden:raise Mismatch(f'a production result holds hidden values {hidden}')
        v=r
    else:
        if len(hidden)!=1:raise Mismatch(f'a {r["label"]} result needs exactly one of {HIDDEN}, has {hidden}')
        v=r[hidden[0]]
        bad=[k for k in (*PHYS,*top)if r.get(k)is not None]
        if bad:raise Mismatch(f'a {r["label"]} result holds a physical number at the top level: {bad} (A-ASM-5)')
        if r['final']:raise Mismatch(f'a {r["label"]} result is never final')
    want=set(PHYS)|set(top)
    have={k for k in v if k not in META}
    if r['label']=='production':have-=set(PROV)
    else:
        have-=set(PROV)
        extra_top={k for k in r if k not in META and k not in PHYS and k not in top and k not in PROV and k not in HIDDEN}
        if extra_top:raise Mismatch(f'added keys {sorted(extra_top)}')
    if have!=want:raise Mismatch(f'added keys {sorted(have-want)}; deleted keys {sorted(want-have)}')
    # The provenance its writer always records (Stage 3a repair round 1): a combined result (combine.py) carries batches
    # and combined_from beside its values; any other result is assemble.evaluate's and carries EVAL_PROV at the top, the
    # tail monitor beside its values, and a campaign role that matches its label.
    if any(k in v for k in COMBINE_PROV):
        gone=[k for k in COMBINE_PROV if k not in v]
        if gone:raise Mismatch(f'deleted keys {gone} (combine.py writes both)')
        if r['label']not in('production','partial'):raise Mismatch(f'a combined result is labelled {r["label"]!r}')
        if 'campaign_role'in r or 'campaign_role'in v:raise Mismatch('added key campaign_role: a combined result has no single campaign')
        combined_check(r,v)
    else:
        gone=[k for k in EVAL_PROV if k not in r]+(['tail_monitor']if 'tail_monitor'not in v else[])
        if gone:raise Mismatch(f'deleted keys {gone} (assemble.evaluate always writes them)')
        if ROLE_OF_LABEL.get(r['label'])!=r['campaign_role']:raise Mismatch(f'label {r["label"]!r} does not match campaign_role {r["campaign_role"]!r}')
        if not isinstance(r['merged_sha256'],dict)or len(r['merged_sha256'])!=24:raise Mismatch('merged_sha256 does not name the 24 merged groups')
        science_check(r['science_sha256'],r['merged_sha256'],'science_sha256')
    return v

def science_check(sc,merged,where:str)->None:
    """S3-R2-007: a scientific identity (assemble.group_science) for exactly the groups of the merged_sha256 map."""
    if not isinstance(sc,dict)or not isinstance(merged,dict)or set(sc)!=set(merged):raise Mismatch(f'{where} does not name the groups of merged_sha256')
    bad=[g for g,x in sc.items()if not asm.science_ok(x)]
    if bad:raise Mismatch(f'{where}: {bad[:4]} hold no scientific identity {{{", ".join(asm.SCIENCE_KEYS)}}}')

COMBINED_BATCHES=('count','planned','per_batch','chi2_about_combined','dof','design_meta_sha256')
COMBINED_ROLES=(('production',False),('test',True))
def combined_check(r:dict,v:dict)->None:
    """S3-007: a combined result (combine.py) carries its design identity (batches.design_meta_sha256) and every batch's role
    (combined_from: run, merged_sha256, campaign_role, test_only), and its batch counts hold: count = len(per_batch) =
    len(combined_from) >= 1, dof = count - 1, count <= planned; distinct batch labels and runs; one role over all
    batches, production (test_only false) or test (test_only true); the chi-square about the combination recomputed from
    per_batch and C_order (null for one batch). Final (label production, final true) needs exactly the planned count of
    production batches; a partial result (final false) has fewer, or test-only batches."""
    b,cf,n=v['batches'],v['combined_from'],r['order']
    if not isinstance(b,dict)or set(b)!=set(COMBINED_BATCHES):raise Mismatch(f'batches: keys {sorted(b)if isinstance(b,dict)else b!r}, need {list(COMBINED_BATCHES)}')
    K,Pl=b['count'],b['planned']
    if type(K)is not int or type(Pl)is not int or not 1<=K<=Pl:raise Mismatch(f'batches: count {K!r} and planned {Pl!r} need 1 <= count <= planned')
    if b['dof']!=K-1:raise Mismatch(f'batches: dof {b["dof"]!r} is not count - 1 = {K-1}')
    if not isinstance(b['design_meta_sha256'],str)or len(b['design_meta_sha256'])!=64:raise Mismatch('batches.design_meta_sha256 does not name the design bundle')
    pb=b['per_batch']
    if not isinstance(pb,list)or len(pb)!=K or not isinstance(cf,list)or len(cf)!=K:raise Mismatch(f'{K} batches, but per_batch and combined_from hold {len(pb)if isinstance(pb,list)else pb!r} and {len(cf)if isinstance(cf,list)else cf!r}')
    for x in pb:   # S3-R2-003: a finite C8 and a positive finite SE (an infinity or a NaN would make the chi-square check vacuous)
        if not isinstance(x,dict)or set(x)!={'label','C8','sampling_se'}or not _fin(x['C8'])or not _fin(x['sampling_se'])or not x['sampling_se']>0:raise Mismatch(f'batches.per_batch row {x!r}')
    for i,x in enumerate(cf):
        if not isinstance(x,dict)or set(x)!={'run','merged_sha256','science_sha256','campaign_role','test_only'}:
            raise Mismatch(f'combined_from row keys {sorted(x)if isinstance(x,dict)else x!r} (run, merged_sha256, science_sha256, campaign_role, test_only)')
        science_check(x['science_sha256'],x['merged_sha256'],f'combined_from[{i}].science_sha256')
    if len({x['label']for x in pb})!=K or len({x['run']for x in cf})!=K:raise Mismatch('the batches are not distinct (labels or runs repeat)')
    roles={(x['campaign_role'],x['test_only'])for x in cf}
    if len(roles)!=1 or next(iter(roles))not in COMBINED_ROLES:raise Mismatch(f'combined_from roles {sorted(map(str,roles))}: one role, production or test-only, over all batches')
    c=v[f'C{n}_full']
    if not _fin(c):raise Mismatch(f'C{n}_full {c!r} is not finite')
    chi=sum((x['C8']-c)**2/x['sampling_se']**2 for x in pb)if K>1 else None
    if K>1:   # S3-R2-003: both chi-squares finite before they are compared (abs(inf - inf) is NaN, and NaN > tol is false)
        if not _fin(chi):raise Mismatch(f'the chi-square recomputed from per_batch is not finite ({chi!r})')
        if not _fin(b['chi2_about_combined'])or abs(b['chi2_about_combined']-chi)>REL*max(abs(chi),1.):raise Mismatch(f'batches.chi2_about_combined {b["chi2_about_combined"]!r} is not the recomputed {chi!r}')
    elif b['chi2_about_combined']is not None:raise Mismatch('batches.chi2_about_combined of one batch must be null')
    final=roles=={('production',False)}and K==Pl
    if r['label']=='production'and not(final and r['final']is True):raise Mismatch(f'a final combined result needs the {Pl} planned production batches (has {K}, roles {sorted(map(str,roles))})')
    if r['label']=='partial'and (r['final']is not False or final):raise Mismatch('a partial combined result is never final and has fewer than the planned batches or test-only batches')

def error_by_loop_of(v:dict,order:int)->dict:
    """S3-008 (E.3, A-ASM-7): error_by_loop recomputed from its own variances: sectors free and power, loops 3..order, rows
    {variance, share, se} with share = variance / Var(C_order) (null when Var is 0, as assemble.combine) and se =
    sqrt(max(0, variance)); compared key by key, so a changed share or se and an added or deleted key fail."""
    e=v['error_by_loop'];var=float(v['covariance'][order][order]);loops={str(L)for L in range(3,order+1)}
    if not isinstance(e,dict)or set(e)!={'free','power'}or any(not isinstance(e[s],dict)or set(e[s])!=loops for s in e):raise Mismatch(f'error_by_loop: sectors free and power, loops 3..{order}')
    out={}
    for s in ('free','power'):
        out[s]={}
        for L in sorted(loops,key=int):
            x=e[s][L]
            if not isinstance(x,dict)or set(x)!={'variance','share','se'}or not _num(x['variance']):raise Mismatch(f'error_by_loop.{s}.{L}: a row {{variance, share, se}} with a numeric variance')
            w=float(x['variance']);out[s][L]={'variance':w,'share':w/var if var>0 else None,'se':math.sqrt(max(0.,w))}
    return out

def bind(r:dict,m:dict,mh:str,I,merged:dict,science:dict)->None:
    """S3-006: the result of a campaign belongs to it: source_manifest_sha256, merged_sha256 (every group's merged.json),
    science_sha256 (every group's scientific identity, S3-R2-007), campaign_role, test_only, backend, build, numerics,
    mp_check and allocation equal the campaign's current manifest and merged files, and two_loop_sha256 its inputs
    manifest's pin."""
    want={'source_manifest_sha256':mh,'merged_sha256':merged,'science_sha256':science,'campaign_role':m['campaign_role'],'test_only':m['test_only'],'backend':m['backend'],'build':m['build'],
          'numerics':m['numerics'],'mp_check':m['mp_check'],'allocation':m.get('allocation'),'two_loop_sha256':I.sha('two_loop.json')}
    bad=[k for k,x in want.items()if k not in r or canon(r[k])!=canon(x)]
    if bad:raise Mismatch(f'the result does not belong to this campaign: {", ".join(bad)} differ from its current manifest, merged files or input pins')

def bind_directory(r:dict,run:Path,m=None,I=None,mh=None)->None:
    """bind against a campaign directory (every group's merged.json validated and hashed)."""
    import production as prod
    if m is None:m,I,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    merged={};science={}
    for gr in m['groups']:
        p,cfg=prod.group_of(run,m,gr['name']);d=prod.validate_merged(p,cfg,m,mh);merged[gr['name']]=digest(p/'merged.json');science[gr['name']]=asm.group_science(d)
    bind(r,m,mh,I,merged,science)

def tail_monitor_check(tm:dict)->None:
    """The tail monitor's flags follow from its listed rows (E.2: a listed L8 graph with a share above 3% in a campaign)."""
    if not isinstance(tm,dict)or not all(isinstance(tm.get(k),list)for k in ('listed','flags','undefined')):raise Mismatch('tail_monitor is not a tail-monitor record')
    want=[{**x,'flag':'more than 3% of its group variance: for the results review'}for x in tm['listed']
          if any(s is not None and s>asm.TAIL_SHARE for s in (x.get('share')or{}).values())]
    if [x.get('graph')for x in tm['flags']]!=[x['graph']for x in want]or tm['flags']!=want:raise Mismatch('tail_monitor.flags do not follow from its listed rows and shares')
    if any(x.get('L')!=8 or not x.get('xi_mean',0)>asm.TAIL_XI for x in tm['listed']):raise Mismatch('tail_monitor.listed holds a row that is not an L8 graph above the threshold')

def campaign_coverage(r:dict,v:dict)->dict|None:
    """assemble.evaluate's gates.coverage.campaign from the result's own fields: None for a test campaign; else the
    coverage guard's record, 24 groups, every graph of both campaigns (twice the tail monitor's distinct graphs) and the
    source equal to the campaign role (production or pilot_full, never null)."""
    role=r['campaign_role']
    if role=='test':return None
    if role not in('production','pilot_full'):raise Mismatch(f'campaign_role {role!r} has no result')
    return {'groups':24,'graphs':2*int(v['tail_monitor']['graphs']),'source':role}

def recompute(v:dict,order:int,r:dict|None=None)->dict:
    oa=asm.vendored();n=order;B2,_=asm.two_loop(order)
    means={s:{int(L):np.asarray(x,float)for L,x in v['means'][s].items()}for s in asm.SECTORS}
    loops=sorted(means['free'])
    if loops!=list(range(3,order+1)):raise Mismatch(f'means hold loops {loops}, need 3..{order}')
    tot={L:means['free'][L]+means['power'][L]for L in loops}
    mu=oa.coefficients(tot,B2,order,asm.HALF_D);pf=oa.coefficients(means['free'],B2,order,asm.HALF_D);delta=mu-pf
    J=oa.jacobians(tot,B2,order,asm.HALF_D);refs,_=asm.references()
    out={'coefficients':mu.tolist(),'power_free_coefficients':pf.tolist(),'power_differences':delta.tolist(),
         f'C{n}_full':float(mu[n]),f'power_free_C{n}':float(pf[n]),'power_correction':float(delta[n]),
         'sampling_standard_error':float(v['standard_errors'][n]),'power_correction_se':float(v['power_difference_errors'][n]),
         'hard_gates':jsonable(asm.hard_gates(tot,J,B2,order,asm.HALF_D)),
         'power_null_checks':jsonable(asm.power_null_checks(np.asarray(v['power_differences'],float),np.asarray(v['power_difference_errors'],float),order)),
         'lower_order_checks':jsonable(asm.lower_order_checks(v['coefficients'],v['standard_errors'],order,refs))}
    out['power_protocol']=asm.protocol_block();out['assembly']=jsonable(asm.assembly_block(v['assembly'].get('half_d')if isinstance(v.get('assembly'),dict)else asm.HALF_D))
    if out['assembly']['half_d']!=asm.HALF_D:raise Mismatch(f'assembly.half_d {out["assembly"]["half_d"]} is not {asm.HALF_D}')
    c=v['b3p_control'];p=asm.pull(c['estimate'],c['se'],asm.B3P0,0.)
    out['b3p_control']={'estimate':c['estimate'],'se':c['se'],'reference':asm.B3P0,'reference_text':'-16 pi/15','pull':p,'flag':p is not None and abs(p)>asm.CONTROL_FLAG}
    g=jsonable(asm.gates_block({**v,'hard_gates':out['hard_gates'],'power_null_checks':out['power_null_checks'],'lower_order_checks':out['lower_order_checks'],
                                 'b3p_control':out['b3p_control']},order))
    stored_cov=(v.get('gates')or{}).get('coverage')or{}
    if r is not None and not any(k in v for k in COMBINE_PROV):   # assemble.evaluate's result: the campaign record is recomputed
        if 'campaign'not in stored_cov:raise Mismatch('deleted key gates.coverage.campaign (assemble.evaluate always writes it)')
        g['coverage']['campaign']=campaign_coverage(r,v);tail_monitor_check(v['tail_monitor'])
    out['gates']=g;out['error_by_loop']=error_by_loop_of(v,order)
    var=v['covariance'][n][n];s=sum(x['variance']for sec in v['error_by_loop'].values()for x in sec.values())
    if not abs(s-var)<=1e-10*max(abs(var),1e-300):raise Mismatch(f'error_by_loop sums to {s}, not Var(C{n}) = {var}')
    # the variance identities (fields the result holds no statistics to recompute): SE_i = sqrt(V_ii);
    # V_nn = power_free_se^2 + power_correction_se^2 + 2 power_free_correction_covariance (V = V_pf + V_Delta + cross + cross^T)
    for i,se in enumerate(v['standard_errors']):
        w=math.sqrt(max(0.,v['covariance'][i][i]))
        if abs(se-w)>REL*max(abs(w),max(math.sqrt(max(0.,v['covariance'][j][j]))for j in range(len(v['standard_errors'])))):raise Mismatch(f'standard_errors[{i}] = {se!r} is not sqrt(covariance[{i}][{i}]) = {w!r}')
    ident=v['power_free_se']**2+v['power_correction_se']**2+2*v['power_free_correction_covariance']
    if not abs(ident-var)<=1e-8*max(abs(var),v['power_free_se']**2,v['power_correction_se']**2,1e-300):
        raise Mismatch(f'variance identity: power_free_se^2 + power_correction_se^2 + 2 cross = {ident!r}, not Var(C{n}) = {var!r}')
    if v['power_difference_errors'][n]!=v['power_correction_se']:raise Mismatch('power_correction_se is not power_difference_errors[order]')
    return out

def verify(r:dict)->dict:
    nonfinite(r);v=check_keys(r);order=r['order']
    if order not in(7,8):raise Mismatch(f'order {order}')
    rec=recompute(v,order,r)
    for k,x in rec.items():compare(jsonable(v[k]),x,k)
    return {'verified':True,'label':r['label'],'order':order,'checked':sorted(rec)}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('target',type=Path);a=p.parse_args(argv)
    try:
        t=a.target.resolve();run=m=I=mh=None
        if t.is_dir():
            import production as prod
            run=t;m,I,mh,_=prod.verify_base(t,check_executable=False,accept_tool_change=True,scheduling_copies=False);asm.refuse_subset(m,'verify_result.py')
            name={'test':'C8_test_result.json','pilot_full':'C8_pilot_result.json','production':'C8_result.json'}[m['campaign_role']];t=t/name
        r=strict_load(t);out=verify(r)
        if run is not None:bind_directory(r,run,m,I,mh);out['bound_to_campaign']=str(run)   # S3-006
        print(json.dumps(out));return 0
    except Refuse as e:print(f'verify_result: {e}',file=sys.stderr);return e.code
    except (Mismatch,ValueError,KeyError,TypeError,ArithmeticError)as e:print(f'verify_result: REJECTED: {e}',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
