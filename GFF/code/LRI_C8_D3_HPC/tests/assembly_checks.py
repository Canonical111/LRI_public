#!/usr/bin/env python3
"""Assembly checks (PLAN A-ASM-2, A-ASM-4, A-ASM-5; component F). Pure Python on the Mac; also run on Expanse (J-VAL-1).

  python3 -B tests/assembly_checks.py [--exact]

A-ASM-2  the vendored coefficients(vals, B2, 7, 1.5) and jacobians equal (np.array_equal) a6ce987's tools/assemble.py
         (tests/fixtures/c7_tools/assemble_a6ce987.py, a byte copy pinned below) and reference/code/analyze.py on 96
         synthetic jet sets (seed 51892) and on run1's means, with B2 given as 6 (order-7) or 7 (order-8) entries.
A-ASM-4  on run1's means extended by synthetic new slots and at 16 random points: top_slot_gate J_L 3^(L+1) = (-1, +3)
         to 1e-12 for L = 3..8; loop7_gate (-16A, 42A)/19683 with A = -B2[0]/6; the float affinity_gate over loops 5..8
         (loops [4, 5] fails); Fraction mode: every exact second difference over loops 5..8 vanishes; coefficients equals
         ms8_value in 16 random constant-coefficient cases; ms8_rows equals RECON:620-625; --exact runs exact_check.py on
         the classified keys; a monkeypatched coefficients makes assemble exit nonzero. Coverage: means missing any one
         loop 3..8 make combine fail before any gate (test data too); a top_slot_gate that drops a row or an
         affinity_gate that reports [5, 6, 7] is caught; combine(order=7) never calls loop7_gate.
A-ASM-5  on synthetic data: lower-order pulls C3..C7 with both SEs; the null rows 3..7 (order 3 rounding level, |pull| > 3
         flagged) and the order-8 row (diagnostic, no flag); PP1-PP10 each with a test (PP6 by forcing every flag and
         identical numbers); PP8; the power_null_rows guards; the consistency flags (3.5 vs 2.5 combined SE; ratios 0.75,
         1.25, 0.9); error_by_loop sums to Var(C8); half streams and the bootstrap; the tail monitor; a 4-sigma C7
         deviation prints a FLAG line; test, partial and pilot results hold no physical number.
"""
from __future__ import annotations
import copy,hashlib,importlib.util,io,json,math,os,subprocess,sys,tempfile,contextlib
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import assemble as asm
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
A6CE987=ROOT/'tests/fixtures/c7_tools/assemble_a6ce987.py';A6CE987_SHA256='f11cdfcb2ba4e6989a6d8681292a924fe1a5b839398d38624211978770163f98'
RUN1=ROOT/'reference/c7d3_run1_results'
OA=asm.vendored()

def b2(order):return asm.two_loop(order)[0]
def module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def run1_arrays()->dict:
    ar={s:{t:{}for t in 'ab'}for s in ('free','power')}
    for p in sorted(RUN1.glob('groups/*/merged.json')):
        d=json.loads(p.read_text());t,s,L=p.parent.name.split('_');ar[s][t][int(L[1:])]=np.asarray(d['batches'],float)
    return ar

def run1_means()->dict:
    ar=run1_arrays();return {L:sum(ar[s][t][L].mean(0)for s in ('free','power')for t in 'ab')/2 for L in range(3,8)}

def extend(means7:dict,rng)->dict:
    """run1's order-7 means (2(8-L) entries) extended to order 8 (2(9-L)) by a synthetic new top slot per jet, and L8."""
    out={}
    for L in range(3,8):
        k=8-L;v=np.asarray(means7[L]);b,c=v[:k],v[k:];sc=float(np.max(np.abs(v)))or 1.
        out[L]=np.concatenate([b,[sc*rng.normal()],c,[sc*rng.normal()]])
    out[8]=rng.normal(size=2)*1e3;return out

# ---------------------------------------------------------------- A-ASM-2
def a_asm_2():
    assert hashlib.sha256(A6CE987.read_bytes()).hexdigest()==A6CE987_SHA256,'the a6ce987 assemble.py fixture is not the pinned byte copy'
    old=module(A6CE987,'assemble_a6ce987');an=module(ROOT/'reference/code/analyze.py','original_d3_analysis')
    B6,B7=b2(7),b2(8);assert len(B6)==6 and len(B7)==7 and np.array_equal(B7[:6],B6)
    rng=np.random.default_rng(51892);cases=[{L:rng.normal(size=2*(8-L))*10.**rng.integers(-3,4)for L in range(3,8)}for _ in range(96)]+[run1_means()]
    for vals in cases:
        want=old.coefficients(vals,B6);wantJ=old.jacobians(vals,B6)
        for B in (B6,B7):
            got=OA.coefficients(vals,B,7,1.5);gotJ=OA.jacobians(vals,B,7,1.5)
            assert np.array_equal(got,want),(got,want)
            assert all(np.array_equal(gotJ[L],wantJ[L])for L in vals)
        assert np.array_equal(an.coefficients(vals),want)
    ok('A-ASM-2: the vendored coefficients(vals, B2, 7, 1.5) and jacobians equal a6ce987\'s assemble.py (pinned byte copy) and '
       'reference/code/analyze.py exactly on 96 synthetic jet sets (seed 51892) and on run1\'s means, with B2 of 6 and of 7 entries',cases=len(cases))

# ---------------------------------------------------------------- A-ASM-4
RECON_MS8=('82368A^7 − 25344A^5 b3 + 28512A^5 c3 − 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2 − 3960A^3 b3c3 − 960A^3 b5 + 1800A^3 c5 + '
           '540A^2 b3b4 − 720A^2 b3c4 − 540A^2 b4c3 − 144A^2 b6 + 324A^2 c6 − (100/3)A b3^3 + 90A b3^2 c3 + 54A b3b5 − 90A b3c5 + 27A b4^2 − '
           '72A b4c4 − 54A b5c3 − 16A b7 + 42A c7 − 5b3^2 b4 + 6b3^2 c4 + 9b3b4c3 + 3b3b6 − 6b3c6 + 3b4b5 − 5b4c5 − 4b5c4 − 3b6c3 + (3c8 − b8)')

def parse_recon(text:str)->dict:
    """RECON:620-625 (3^9 C8 as a sum of monomials) -> {frozenset of (symbol, power): Fraction}."""
    import re
    t=text.replace('−','-').replace('(3c8 - b8)','3c8 - b8');out={}
    for sign,term in re.findall(r'([+-]?)\s*((?:\(\d+/\d+\)|\d+)?[A-Za-z0-9^ ]+?)(?=\s[+-]\s|$)',t):
        term=term.strip();m=re.match(r'(\(\d+/\d+\)|\d+)?(.*)',term);co=Fraction(m.group(1).strip('()')if m.group(1)else 1);rest=m.group(2).replace(' ','')
        mono={}
        for sym,pw in re.findall(r'(A|[bc]\d)(?:\^(\d))?',rest):mono[sym]=mono.get(sym,0)+int(pw or 1)
        out[frozenset(mono.items())]=co*(-1 if sign=='-'else 1)
    return out

def a_asm_4(exact:bool):
    rng=np.random.default_rng(20261004);B2=b2(8);A=-B2[0]/6;m7=run1_means();pts=[extend(m7,rng)]
    for _ in range(16):pts.append({L:rng.normal(size=2*(9-L))*10.**rng.integers(-2,3)for L in range(3,9)})
    for m in pts:
        J=OA.jacobians(m,B2,8,1.5)
        for L in range(3,9):
            k=9-L;jb,jc=J[L][8,k-1]*3**(L+1),J[L][8,2*k-1]*3**(L+1)
            assert abs(jb+1)<=1e-12 and abs(jc-3)<=1e-12*3,(L,jb,jc)
        g=OA.loop7_gate(J,B2,8);assert abs(g['dC8_db70']-(-16*A/19683))<=1e-12*abs(16*A/19683)and abs(g['dC8_dc70']-42*A/19683)<=1e-12*abs(42*A/19683)
        OA.top_slot_gate(J,8);aff=OA.affinity_gate(m,B2,8,1.5,loops=[5,6,7,8]);assert aff['loops']==[5,6,7,8]
    try:OA.affinity_gate(pts[0],B2,8,1.5,loops=[4,5]);raise AssertionError('affinity over loops [4, 5] passed')
    except ArithmeticError:pass
    # Fraction mode: exact second differences over loops 5..8 vanish; ms8 constant-coefficient cases; ms8_rows = RECON:620-625
    fr={L:np.array([Fraction(int(x*1000),1000)for x in pts[1][L]],dtype=object)for L in range(3,9)}
    ex=OA.affinity_gate(fr,B2,8,1.5,loops=[5,6,7,8]);assert ex['mode']=='exact'and ex['all_second_differences_zero']and ex['pairs']==210
    rr=np.random.default_rng(7)
    for _ in range(16):
        Af=Fraction(int(rr.integers(-50,50)),7);syms={'A':Af};vals={}
        B2x=np.array([Fraction(-6)*Af]+[Fraction(0)]*6,dtype=object)
        for L in range(3,9):
            bL=Fraction(int(rr.integers(-90,90)),11);cL=Fraction(int(rr.integers(-90,90)),13);syms[f'b{L}']=bL;syms[f'c{L}']=cL;k=9-L
            vals[L]=np.array([bL]+[Fraction(0)]*(k-1)+[cL]+[Fraction(0)]*(k-1),dtype=object)
        c=OA.coefficients(vals,B2x,8,Fraction(3,2));assert c[8]==OA.ms8_value(syms),(c[8],OA.ms8_value(syms))
    rows={frozenset(m.items()):co for co,m in OA.ms8_rows()};assert rows==parse_recon(RECON_MS8),'ms8_rows differ from RECON:620-625'
    # coverage: any missing loop refuses before any gate; a dropped top-slot row or affinity loops [5, 6, 7] are caught
    ar=run1_arrays();rng2=np.random.default_rng(3)
    ar8={s:{t:{L:np.concatenate([x,rng2.normal(size=(len(x),2))*1e-3],axis=1)[:, [*range(8-L),2*(8-L),*range(8-L,2*(8-L)),2*(8-L)+1]]if L<8 else x for L,x in v.items()}for t,v in ar[s].items()}for s in ar}
    for s in ar8:
        for t in ar8[s]:ar8[s][t][8]=rng2.normal(size=(len(ar8[s][t][3]),2))
    r=asm.combine(ar8,8,1.5,0,B2);assert r['gates']['coverage']['complete']and r['hard_gates']['loop7']!='not applicable at order 7'
    for L in range(3,9):
        bad=copy.deepcopy(ar8);del bad['power']['b'][L]
        try:asm.combine(bad,8,1.5,0,B2);raise AssertionError(f'missing loop {L} accepted')
        except ValueError as e:assert 'every loop 3..8'in str(e)
    real_top,real_aff=OA.top_slot_gate,OA.affinity_gate
    try:
        OA.top_slot_gate=lambda J,order,rtol=1e-12:(lambda d:{**d,'rows':d['rows'][1:]})(real_top(J,order,rtol))
        try:asm.combine(ar8,8,1.5,0,B2);raise AssertionError('a dropped top-slot row passed')
        except ArithmeticError as e:assert 'top_slot_gate returned rows'in str(e)
        OA.top_slot_gate=real_top;OA.affinity_gate=lambda *a,**k:{**real_aff(*a,**k),'loops':[5,6,7]}
        try:asm.combine(ar8,8,1.5,0,B2);raise AssertionError('affinity loops [5, 6, 7] passed')
        except ArithmeticError as e:assert 'affinity_gate reports loops'in str(e)
    finally:OA.top_slot_gate,OA.affinity_gate=real_top,real_aff
    called=[];real7=OA.loop7_gate
    try:
        OA.loop7_gate=lambda *a,**k:called.append(1)or real7(*a,**k)
        r7=asm.combine(run1_arrays(),7,1.5,0,b2(7));assert not called and r7['hard_gates']['loop7']=='not applicable at order 7'
    finally:OA.loop7_gate=real7
    # an injected violation (monkeypatched coefficients) makes the assemble CLI exit nonzero (hard gate)
    real_c=OA.coefficients
    try:
        OA.coefficients=lambda vals,B,order,hd:real_c(vals,B,order,hd)*(1+1e-6)
        try:asm.combine(ar8,8,1.5,0,B2);raise AssertionError('an injected coefficient violation passed')
        except (ArithmeticError,ValueError):pass
    finally:OA.coefficients=real_c
    extra={}
    if exact:
        import exact_keys as ek
        cp=subprocess.run([sys.executable,'-B',str(ROOT/'vendor/c8_assembly/exact_check.py')],capture_output=True,text=True,
                          env={**{k:v for k,v in os.environ.items()if k!='PYTHONPYCACHEPREFIX'},'LRI_ROOT':str(ROOT/'vendor/c8_assembly_fixtures'),'PYTHONDONTWRITEBYTECODE':'1'})
        classes=json.loads(ek.KEYS.read_bytes());ref=json.loads((ROOT/'vendor/c8_assembly/exact_check_results.json').read_bytes())
        g=ek.gate(classes,ref,json.loads(cp.stdout),lri_root=True);assert cp.returncode==0 and g['passed'],g.get('errors')
        extra['exact_check']='passed on the classified keys'
    ok('A-ASM-4: top_slot (J_L 3^(L+1) = (-1, +3) to 1e-12, L = 3..8), loop7 ((-16A, 42A)/19683) and the float affinity gate (loops 5..8; [4, 5] '
       'fails) on run1\'s means with synthetic new slots and 16 random points; Fraction mode: 210 exact second differences vanish; coefficients = '
       'ms8_value in 16 constant-coefficient cases; ms8_rows = RECON:620-625; coverage: every missing loop refuses before any gate, a dropped '
       'top-slot row and affinity loops [5, 6, 7] are caught; combine(order=7) never calls loop7_gate; an injected coefficient violation fails',**extra)

# ---------------------------------------------------------------- A-ASM-5
def synthetic_ar(rng,R=16,scale=1e-3)->dict:
    return {s:{t:{L:rng.normal(size=(R,2*(9-L)))*scale+(1. if s=='free'else .1)for L in range(3,9)}for t in 'ab'}for s in ('free','power')}

def a_asm_5():
    rng=np.random.default_rng(11);B2=b2(8);refs,_=asm.references()
    r=asm.combine(synthetic_ar(rng),8,1.5,64,B2)
    lo=r['lower_order_checks'];assert [x['order']for x in lo]==[3,4,5,6,7]
    for x in lo:
        e=next(e for e in refs['coefficients']if e['order']==x['order'])
        assert x['reference']==e['value']and x['reference_se']==e['se']and abs(x['pull']-(x['estimate']-e['value'])/math.hypot(x['sampling_se'],e['se']))<1e-12
    # the null rows (PP3-PP5, PP7) on injected differences; PP6: forcing every flag changes no number
    delta=np.array([0,0,0,1e-13,5.,0.1,2.,-1.,7.]);dse=np.array([0,0,0,1.,1.,1.,0.5,0.1,1.])
    pn=asm.power_null_checks(delta,dse,8);rows={x['order']:x for x in pn['null_rows']}
    assert rows[3]['pull']is None and 'rounding level'in rows[3]['note']and rows[4]['flag']=='not proved zero'and rows[5]['flag']is None
    assert rows[6]['flag']and rows[6]['pp8']and rows[7]['flag']and rows[7]['pp8']is None and pn['top']['order']==8 and 'flag'not in pn['top']
    d5=delta.copy();d5[5]=10.;assert asm.power_null_checks(d5,dse,8)['null_rows'][2]['pp8']is None   # an order-5 flag: no PP8 marker
    for bad,name in ((delta[:8],'length'),(np.where(np.arange(9)==4,np.nan,delta),'not finite')):
        try:asm.power_null_checks(bad,dse[:len(bad)],8);raise AssertionError(name)
        except ValueError:pass
    z=dse.copy();z[5]=0
    try:asm.power_null_checks(delta,z,8);raise AssertionError('SE 0 at order 5')
    except ValueError as e:assert 'order 5'in str(e)
    real=OA.power_null_rows
    try:
        for k in range(4,9):
            for bad in (None,float('nan')):
                def fake(d,s,o,k=k,bad=bad):
                    x=real(d,s,o);(x['top']if k==8 else x['null_rows'][k-3]).update(pull=bad);return x
                OA.power_null_rows=fake
                try:asm.power_null_checks(delta,dse,8);raise AssertionError(f'a {bad} pull at order {k}')
                except ValueError as e:assert f'order-{k} row'in str(e)
    finally:OA.power_null_rows=real
    # PP1-PP10 (C62d's H2 review record, step 6), one check each, on the synthetic result r
    oa=OA;arx=synthetic_ar(np.random.default_rng(11));tot={L:sum(arx[s][t][L].mean(0)for t in 'ab')/2 for s in ('free',)for L in range(3,9)}
    tot={L:tot[L]+sum(arx['power'][t][L].mean(0)for t in 'ab')/2 for L in range(3,9)}
    means,vc=oa.campaign_moments({s:{t:{L:arx[s][t][L]for L in range(3,9)}for t in 'ab'}for s in arx},range(3,9));sa=oa.sector_assembly(means,vc,B2,8,1.5)
    assert r['C8_full']==float(oa.coefficients(tot,B2,8,1.5)[8]),'PP1'
    assert r['power_free_C8']==float(sa['power_free_coefficients'][8])and r['power_correction']==float(sa['power_differences'][8])and \
        abs(r['power_correction']-(r['C8_full']-r['power_free_C8']))<=1e-12*abs(r['C8_full'])and r['power_correction_se']==float(sa['power_difference_errors'][8])and \
        r['power_free_correction_covariance']==float(sa['cross'][8,8]),'PP2'
    hv=asm.power_null_checks(np.array([0,0,0,5e-13,2e-6,9e-5,1e-3,0.2,3.]),np.array([0,0,0,1e-14,1e-6,2e-5,2e-3,0.05,1.]),8);nh={x['order']:x for x in hv['null_rows']}
    assert [x['order']for x in hv['null_rows']]==[3,4,5,6,7]and nh[4]['pull']==2.and abs(nh[5]['pull']-4.5)<1e-12 and abs(nh[6]['pull']-.5)<1e-12 and nh[7]['pull']==4.,'PP3'
    assert nh[5]['flag']=='not proved zero'and nh[7]['flag']=='not proved zero'and nh[4]['flag']is None and nh[6]['flag']is None and [x['order']for x in hv['flags']]==[5,7],'PP4'
    assert nh[3]['pull']is None and 'rounding'in nh[3]['note'],'PP5'
    assert hv['top']['order']==8 and hv['top']['pull']==3. and 'flag'not in hv['top'],'PP7'
    assert nh[5]['pp8']is None and nh[7]['pp8']is None,'PP8 (orders 5 and 7 carry no marker)'
    Vh=sum(sa['J'][L]@(vc['free'][L]+vc['power'][L])@sa['J'][L].T for L in range(3,9))
    assert np.allclose(np.asarray(r['covariance']),Vh,rtol=1e-12,atol=1e-12*np.max(np.abs(Vh)))and np.allclose(sa['covariance'],
        sa['power_free_covariance']+sa['power_difference_covariance']+sa['cross']+sa['cross'].T,rtol=1e-10,atol=1e-12*np.max(np.abs(Vh))),'PP9'
    pp=json.loads((ROOT/'tools/VENDORED.json').read_bytes())['power_protocol']['sha256'];hand=json.loads((ROOT/'vendor/c8_assembly/HANDOFF_assembly.json').read_bytes())
    assert r['power_protocol']['sha256']==pp==next(f['sha256']for f in hand['files']if f['path']=='POWER_PROTOCOL.md')and pp in (ROOT/'docs/NUMERICS.md').read_text(),'PP10'
    # PP8 FLAG line printed; PP6 numbers unchanged with every flag forced
    ar=synthetic_ar(rng);r1=asm.combine(ar,8,1.5,0,B2);real=OA.power_null_rows
    try:
        OA.power_null_rows=lambda d,s,o:(lambda x:([y.update(flag='not proved zero')for y in x['null_rows']],x)[1])(real(d,s,o))
        err=io.StringIO()
        with contextlib.redirect_stderr(err):r2=asm.combine(ar,8,1.5,0,B2)
    finally:OA.power_null_rows=real
    assert 'FLAG pp8'in err.getvalue()and all(r1[k]==r2[k]for k in ('coefficients','standard_errors','power_differences','covariance'))
    # the consistency flags: a/b pull 3.5 flagged, 2.5 not; ratio 0.75 and 1.25 flagged, 0.9 not; no number changes
    def cons(pull,ratio):
        x=copy.deepcopy(r);x['campaigns']={'a':{'C8':0.,'sampling_se':1.},'b':{'C8':pull*math.sqrt(2),'sampling_se':1.}}
        x['bootstrap']={'full_se':[ratio*x['sampling_standard_error']]*9};return asm.consistency(x,8)
    assert cons(3.5,1.)['campaign_pull']['flag']and not cons(2.5,1.)['campaign_pull']['flag']
    assert cons(0,.75)['bootstrap_ratio']['flag']and cons(0,1.25)['bootstrap_ratio']['flag']and not cons(0,.9)['bootstrap_ratio']['flag']
    tot=sum(v['variance']for s in r['error_by_loop'].values()for v in s.values());assert abs(tot-r['covariance'][8][8])<=1e-10*abs(r['covariance'][8][8])
    assert len(r['half_streams'])==2 and r['bootstrap']['replicates']==64 and r['bootstrap']['seed']==70530413
    # a 4-sigma C7 deviation prints a FLAG line; test, partial and pilot views hold no physical number
    x=copy.deepcopy(r);x['lower_order_checks'][-1].update(pull=4.,flag=True);lines=asm.summary_lines(x)
    assert any(l.startswith('FLAG |pull|>3')and l.split(':')[0].endswith('C7')for l in lines)
    for view,key in ((asm.test_only_view,'test_partial'),(asm.pilot_view,'sizing_only'),(lambda v:asm.hidden_view(v,'partial_values','partial','p'),'partial_values')):
        v=view(copy.deepcopy(r));assert v['final']is False and v['C8_full']is None and v['coefficients']is None and v[key]['C8_full']==r['C8_full']
    # the tail monitor: an injected heavy L8 graph is listed, a zero tail_sum replicate is undefined, no value changes
    td=Path(tempfile.mkdtemp(prefix='c8d3_tm_'))
    try:
        cfgs={};k=16
        for c in 'ab':
            for s in ('free','power'):
                for L in (7,8):
                    p=td/'groups'/f'{c}_{s}_L{L}';p.mkdir(parents=True);cfgs[(c,s,L)]={'replicates':4}
                    tails=['replicate,graph,points,tail_sum,tail_argmax,tail_n,'+','.join(f'tail_top_{i+1}'for i in range(k))]
                    reps=['replicate,graph,'+','.join(f'jet_{i}'for i in range(2*(9-L)))]
                    for rep in range(4):
                        for g in range(3):
                            top=[(1+i)**-1. for i in range(k)]if (g==1 and L==8)else[1-0.001*i for i in range(k)]
                            ts=0. if (g==2 and rep==0 and s=='free')else sum(top)+100
                            tails.append(f'{rep},{g},4096,{ts},{g},16,'+','.join(map(str,sorted(top,reverse=True))))
                            jet=rng.normal(size=2*(9-L))*(10 if g==1 else 1);reps.append(f'{rep},{g},'+','.join(map(str,jet)))
                    (p/'graph_tails.csv').write_text('\n'.join(tails)+'\n');(p/'graph_replicates.csv').write_text('\n'.join(reps)+'\n')
        J={8:np.zeros((9,2))};J[8][8]=[-1/3**9,3/3**9]
        tm=asm.tail_monitor(td,{},cfgs,J)
        assert [(x['sector'],x['graph'])for x in tm['listed']]==[('free',1),('power',1)]and tm['flags']
        assert any(u['sector']=='free'and u['graph']==2 for u in tm['undefined'])and all(math.isfinite(x['xi_mean'])for x in tm['listed'])
    finally:
        import shutil;shutil.rmtree(td,ignore_errors=True)
    ok('A-ASM-5: lower-order pulls C3..C7 with both SEs; null rows 3..7 (order 3 at rounding level without pull, |pull| > 3 "not proved zero") and '
       'the order-8 diagnostic row without flag; PP8 marks an order-6 flag only (FLAG line), PP6 (every flag forced, identical numbers); the '
       'power_null_rows guards (short vectors, NaN, SE 0 at order >= 4, a None or NaN pull at each order 4..8 naming the row); PP1-PP5, PP7, PP9, PP10 one check each; the a/b pull (3.5 flagged, 2.5 not) and the '
       'bootstrap ratio (0.75, 1.25 flagged, 0.9 not); error_by_loop sums to Var(C8); half streams and the bootstrap; a 4-sigma C7 FLAG line; '
       'test, pilot and partial views hold no physical number; the tail monitor lists an injected heavy L8 graph and an undefined entry')

def run(exact=False)->dict:
    a_asm_2();a_asm_4(exact);a_asm_5()
    return {'status':'passed','tests':len(RESULTS),'results':RESULTS,'numpy':np.__version__,'python':sys.version.split()[0]}
if __name__=='__main__':print(json.dumps(run('--exact'in sys.argv),indent=1))
