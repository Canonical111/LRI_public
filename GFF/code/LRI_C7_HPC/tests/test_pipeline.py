#!/usr/bin/env python3
"""Pipeline logic tests with a fake integrator: plan/run/merge/verify/combine, restart and guards.

Runs anywhere Python and NumPy/SciPy run (no C++ build). The fake executable writes the
real output schema with values that are exactly additive over sample chunks, so every
bookkeeping property can be checked without integrating a graph.
"""
from __future__ import annotations
import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import campaign as C
from assemble import assemble
PY=sys.executable;CAMP=[PY,str(ROOT/'tools/campaign.py')];PROD=[PY,str(ROOT/'tools/production.py')]
FAKE=r'''#!PYTHON
import hashlib,json,os,signal,sys,time
from decimal import Decimal as D,getcontext
getcontext().prec=40;a=sys.argv[1:];o=dict(zip(a[::2],a[1::2]))
def h(*k):return int.from_bytes(hashlib.sha256(repr(k).encode()).digest()[:6],'little')/2**48-.5
act=os.environ.get('C7_FAKE_ACTION','');deg=int(o.get('--degree','0'))
if act=='die' and int(os.environ.get('C7_FAKE_ON_DEGREE',deg))==deg:sys.exit(3)
if act=='sleep':time.sleep(60)
lines=open(o['--tasks']).read().split('\n');ng=int(lines[0].split()[1]);rows=[]
for line in lines[1:]:
    if not line.strip():continue
    uid,rep,g,b,e,t=map(int,line.split());n=e-b;s=o['--seed']
    # Per-sample value alpha+beta*i: chunk sums are exact, so any split reproduces the whole stream.
    v=[(D(repr(h(s,rep,g,deg,j)))*n+D(repr(h(s,g,deg,j,'b')))*D((b+e-1)*n)/2/t)/t for j in range(14)]
    rows.append('{"uid":%d,"replicate":%d,"graph":%d,"begin":%d,"end":%d,"total":%d,"quad_calls":%d,"mp_calls":0,"seconds":%r,"value":[%s]}'%(uid,rep,g,b,e,t,n%3,time.time()%1,','.join(format(x,'.25g') for x in v)))
txt='{"schema":"c7-hpc-1","build":{"compiler":"fake","boost":"none"},"mode":"%s","L":%s,"degree":%d,"seed":%s,"rate":%s,"inventory_count":%d,"threads":1,"long_double_bits":64,"long_double_bytes":16,"tile":1,"scratch_mib":1,"oracle_point":false,"preparation_seconds":%r,"integration_seconds":0.1,"rows":[%s],"profile":[]}\n'%(o['--mode'],o['--L'],deg,o['--seed'],o['--rate'],ng,time.time()%1,','.join(rows))
tmp=o['--output']+'.part';open(tmp,'w').write(txt);os.rename(tmp,o['--output'])
if act=='killparent' and int(os.environ.get('C7_FAKE_ON_DEGREE',deg))==deg:os.kill(os.getppid(),signal.SIGKILL)
'''
REPORT=[]
def ok(name,**kw):REPORT.append(dict(name=name,**kw));print('PASS',name,flush=True)
def sh(cmd,env=None,fail=False):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env={**os.environ,'OMP_NUM_THREADS':'1',**(env or {})})
    if (p.returncode==0)==fail:raise AssertionError(f'unexpected exit {p.returncode}: {" ".join(map(str,cmd))}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}')
    return p
def expect_error(f,text):
    try:f()
    except Exception as e:
        assert text in str(e),(text,str(e));return
    raise AssertionError('expected failure: '+text)
def tree_hashes(d:Path,pattern):return {str(p.relative_to(d)):C.digest(p) for p in sorted(d.glob(pattern))}
def payloads(d:Path):return {p.name:C.read(p)['provenance']['payload_sha256'] for p in sorted(d.glob('*/checkpoints/*.json'))}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--keep',type=Path,help='work directory to keep (must not exist)');a=ap.parse_args()
    work=Path(tempfile.mkdtemp(prefix='c7_pipeline_')) if not a.keep else a.keep.resolve()
    if a.keep:work.mkdir(parents=True)
    os.umask(0o022);fake=work/'fake_c7';fake.write_text(FAKE.replace('PYTHON',PY));fake.chmod(0o755)
    extra=work/'extra';extra.mkdir()
    for L in (5,6,7):(extra/f'cw_L{L}_N7.txt').write_text('C7WEIGHTS1 1\n0\n')
    srcin=work/'inputs_src';shutil.copytree(ROOT/'reference/inputs',srcin)
    # 1. Launch-policy decisions and the explicit-index rule.
    assert C.binding_policy(None,8)=='unknown' and C.binding_policy(4,8)=='oversubscribed' and C.binding_policy(8,8)=='confined' and C.binding_policy(32,8)=='unconfined'
    ok('binding_policy_all_branches')
    def plan(name,seed,*extra_args,inputs=srcin):
        d=work/name;sh(PROD+['plan',d,'--seed',seed,'--shards-per-stream',1,'--threads',1,'--checkpoint-tasks',100000,'--chunk-points',0,'--executable',fake,'--inputs',inputs,*extra_args]);return d
    def runall(d,env=None):
        for i in range(len(json.loads((d/'production.json').read_text())['jobs'])):sh(PROD+['run',d,'--index',i,'--threads',1],env)
    # 2. Design validation.
    bad=work/'design_bad.json';bad.write_text(json.dumps({'power_coarseA_L7':{'multiplier':2}}))
    sh(PROD+['plan',work/'rejected','--seed',1,'--design',bad,'--executable',fake,'--inputs',srcin],fail=True)
    bad.write_text(json.dumps({'tprodA_L5':{'multiplier':3},'tprodB_L5':{'multiplier':3}}))
    sh(PROD+['plan',work/'rejected2','--seed',1,'--design',bad,'--executable',fake,'--inputs',srcin],fail=True)
    ok('design_rejects_unequal_pairs_and_non_power_of_two_qmc')
    # 3. A complete fresh production (with the degree-7 check), idempotent merge and file modes.
    good=work/'design.json';good.write_text(json.dumps({'power_refine3B_L7':{'replicate_multiplier':2},'tprodA_L7':{'multiplier':2},'tprodB_L7':{'multiplier':2}}))
    p1=plan('b1',101,'--refine7','--extra-inputs',extra,'--design',good,'--label','b1')
    m=json.loads((p1/'power_refine7_L7/manifest.json').read_text());assert m['inputs']=='../inputs' and m['schema']=='c7-campaign-2' and m['degrees']==[6,7]
    mode=stat.S_IMODE((p1/'tprodA_L5/manifest.json').stat().st_mode);assert mode==0o644,oct(mode)
    sh(CAMP+['run',p1/'tprodA_L5'],env={'SLURM_ARRAY_TASK_ID':''},fail=True)
    e=dict(os.environ);e.pop('SLURM_ARRAY_TASK_ID',None);p=subprocess.run(CAMP+['run',str(p1/'tprodA_L5')],capture_output=True,text=True,env=e);assert p.returncode and 'give --index' in p.stderr
    runall(p1);sh(PROD+['merge',p1]);r1=json.loads((p1/'C7_result.json').read_text())
    assert 'refine7' in r1['check_levels'] and r1['allowance']['candidates'].get('refine7') is not None and not any(v['role']=='check' and k in r1['power_levels'] for k,v in r1['components'].items())
    before=tree_hashes(p1,'*/merged/*');sh(PROD+['merge',p1]);assert tree_hashes(p1,'*/merged/*')==before
    (p1/'tprodA_L6/merged/audit.json').unlink();sh(CAMP+['merge',p1/'tprodA_L6']);assert tree_hashes(p1,'*/merged/*')==before
    stale=p1/'C7_result.json.tmp.stale';stale.write_text('partial');sh(PROD+['merge',p1]);stale.unlink()
    assert stat.S_IMODE((p1/'tprodA_L6/merged/N0.json').stat().st_mode)==0o644
    ok('fresh_production_refine7_check_idempotent_merge_and_modes',C7=r1['C7_full'])
    # 4. Reconciliation of estimator components with the total (nonzero primitive and nonzero check level).
    est=[v for v in r1['components'].values() if v['role']=='estimator'];K=np.array(json.loads((p1/'full_affine_assembly.json').read_text())['K'])
    tot=K+sum(np.array(v['mean']) for v in est);tot[7]+=r1['retained_primitive']['mean'];assert np.allclose(tot,r1['coefficients'],rtol=1e-12,atol=1e-9)
    assert r1['retained_primitive']['sampling_se']>0 and abs(r1['check_levels']['refine7']['mean'][7])>0
    ok('component_reconciliation')
    # 5. Interruptions at each publication boundary, then resume.
    p2=plan('b2',202,'--label','b2');j=json.loads((p2/'production.json').read_text())['jobs'];idx=[i for i,x in enumerate(j) if x['campaign']=='power_refine5_L6'][0]
    sh(PROD+['run',p2,'--index',idx],env={'C7_FAKE_ACTION':'die','C7_FAKE_ON_DEGREE':'5'},fail=True)
    ck=p2/'power_refine5_L6/checkpoints';assert [x.name for x in ck.glob('*.json')]==['s000000_p000000_N3.json']
    keep=C.digest(ck/'s000000_p000000_N3.json')
    sh(CAMP+['run',p2/'power_refine5_L6','--index',0],env={'C7_FAKE_ACTION':'killparent','C7_FAKE_ON_DEGREE':'5'},fail=True)
    assert not (ck/'s000000_p000000_N5.json').exists()
    tmp=Path(tempfile.gettempdir());left=set(tmp.glob('c7_task_*'))
    proc=subprocess.Popen(CAMP+['run',str(p2/'power_refine5_L6'),'--index','0'],env={**os.environ,'C7_FAKE_ACTION':'sleep'});time.sleep(3);proc.send_signal(signal.SIGTERM);proc.wait(30)
    assert proc.returncode!=0 and set(tmp.glob('c7_task_*'))<=left,'SIGTERM left a temporary block directory'
    runall(p2);assert C.digest(ck/'s000000_p000000_N3.json')==keep
    ok('interruption_before_after_publish_and_sigterm_cleanup')
    # 6. Concurrent duplicate workers commit each checkpoint exactly once.
    q=work/'dup';shutil.copytree(p2/'power_refine3_L6',q/'power_refine3_L6',ignore=shutil.ignore_patterns('checkpoints','merged'));shutil.copytree(p2/'inputs',q/'inputs')
    ps=[subprocess.Popen(CAMP+['run',str(q/'power_refine3_L6'),'--index','0']) for _ in range(3)];assert all(x.wait(120)==0 for x in ps)
    sh(CAMP+['merge',q/'power_refine3_L6']);sh(CAMP+['merge',p2/'power_refine3_L6'])
    assert C.digest(q/'power_refine3_L6/merged/N3.json')==C.digest(p2/'power_refine3_L6/merged/N3.json')
    ok('concurrent_duplicate_workers')
    # 7. Tamper detection, quarantine and deterministic recomputation.
    sh(PROD+['merge',p2]);ref=C.digest(p2/'tprodB_L5/merged/N0.json');f=next((p2/'tprodB_L5/checkpoints').glob('*.json'));txt=f.read_text()
    i=txt.index('"value":[')+10;k=next(n for n in range(i,i+40) if txt[n].isdigit());f.write_text(txt[:k]+str((int(txt[k])+1)%10)+txt[k+1:])
    sh(CAMP+['verify',p2/'tprodB_L5'],fail=True);sh(CAMP+['run',p2/'tprodB_L5','--index',0],fail=True);sh(PROD+['merge',p2],fail=True)
    old=C.read(f) # the tampered file still carries the digest committed with the original content
    sh(CAMP+['quarantine',p2/'tprodB_L5',f.stem,'--reason','test']);sh(CAMP+['run',p2/'tprodB_L5','--index',0])
    assert C.read(f)['provenance']['payload_sha256']==old['provenance']['payload_sha256'] and list((p2/'tprodB_L5/merged').glob('audit.json.invalidated.*'))
    sh(PROD+['merge',p2]);assert C.digest(p2/'tprodB_L5/merged/N0.json')==ref and (p2/'tprodB_L5/merged/audit.json').exists() # no manual deletion needed
    ok('payload_digest_tamper_quarantine_recompute')
    # 8. Merge coverage is checked against manifest counts x replicates.
    c=work/'coverage';sh(CAMP+['plan','--out',c,'--mode','power','--L',5,'--inputs',srcin,'--executable',fake,'--seed',7,'--points',2,'--replicates',2,'--degrees',1,'--shards',1,'--threads',1])
    mp=json.loads((c/'manifest.json').read_text());tf=c/mp['shards'][0]['file'];lines=tf.read_text().splitlines();drop=lines[1].split()
    kept=[x for x in lines[1:] if x.split()[1:3]!=drop[1:3]];tf.write_text(f'C7TASKS1 {lines[0].split()[1]} {len(kept)}\n'+'\n'.join(kept)+'\n')
    mp['shards'][0].update(sha256=C.digest(tf),work_units=len(kept));mp['total_work_units']=len(kept);(c/'manifest.json').unlink();C.dump(c/'manifest.json',mp)
    sh(CAMP+['run',c,'--index',0]);p=sh(CAMP+['merge',c],fail=True);assert 'manifest streams' in p.stderr
    # An audited legacy-schema campaign that omits a stream must not pass verify (its audit is not trusted for coverage).
    lg=work/'legacy_cov';shutil.copytree(c,lg);ml=json.loads((lg/'manifest.json').read_text());ml['schema']='c7-campaign-1';(lg/'manifest.json').unlink();C.dump(lg/'manifest.json',ml)
    for f in (lg/'checkpoints').glob('*.json'):f.unlink()
    sh(CAMP+['run',lg,'--index',0]);(lg/'merged').mkdir(exist_ok=True);(lg/'merged/N1.json').write_text('{}\n');mh=C.digest(lg/'manifest.json')
    src=[{'file':str(f.relative_to(lg)),'sha256':C.digest(f)} for f in sorted((lg/'checkpoints').glob('*.json'))]
    (lg/'merged/audit.json').write_text(json.dumps({'manifest_sha256':mh,'complete':True,'work_units_per_degree':ml['total_work_units'],'sources':src,'outputs':[{'file':'merged/N1.json','sha256':C.digest(lg/'merged/N1.json')}]}))
    expect_error(lambda:C.verify_campaign(lg),'manifest streams')
    ok('merge_and_verify_coverage_against_manifest')
    # 9. Relocation with the original inputs unavailable: identical merged outputs and final result.
    ctl=plan('reloc_ctl',303);runall(ctl)
    # Kill between writing the final result's temporary file and linking it; the rerun must publish normally.
    die=f'import os,sys,pathlib;sys.path.insert(0,{str(ROOT/"tools")!r});import production;real=os.link\n'+\
        'def link(s,d,*a,**k):\n    if str(d).endswith("C7_result.json"):os._exit(9)\n    return real(s,d,*a,**k)\n'+f'os.link=link;production.assemble_production(pathlib.Path({str(ctl)!r}))\n'
    q=subprocess.run([PY,'-c',die],capture_output=True,text=True);assert q.returncode==9 and not (ctl/'C7_result.json').exists() and list(ctl.glob('C7_result.json.tmp.*')),q.stderr[-500:]
    sh(PROD+['merge',ctl]);assert (ctl/'C7_result.json').exists()
    src2=work/'inputs_gone';shutil.copytree(srcin,src2);mv=plan('reloc_src',303,inputs=src2);j=json.loads((mv/'production.json').read_text())['jobs']
    for i in range(len(j)//2):sh(PROD+['run',mv,'--index',i,'--threads',1])
    shutil.rmtree(src2);moved=work/'elsewhere'/'reloc';moved.parent.mkdir();shutil.move(str(mv),str(moved))
    for i in range(len(j)):sh(PROD+['run',moved,'--index',i,'--threads',1,'--executable',fake])
    sh(PROD+['merge',moved])
    assert tree_hashes(moved,'*/merged/N*.json')==tree_hashes(ctl,'*/merged/N*.json') and C.digest(moved/'C7_result.json')==C.digest(ctl/'C7_result.json') and payloads(moved)==payloads(ctl)
    ok('relocation_with_original_inputs_removed')
    # 10. Stream-overlap and legacy-archive guards.
    cf=json.loads((p1/'assembly.json').read_text());s3=[s for s in cf['sources'] if s['name']=='power_refine3_L6'][0]
    cf2={**cf,'sources':cf['sources']+[{**s3,'name':'overlap','subtract':'power_coarseA_L6/merged/N1.json','path':'power_coarseB_L6/merged/N1.json'}]}
    expect_error(lambda:assemble(cf2,p1),'stream used twice')
    from assemble import original_config
    oc=original_config(ROOT/'reference');bad=work/'tampered_record.json';rec=json.loads(Path(oc['sources'][-1]['path']).read_text());rec['seed']+=0;bad.write_text(json.dumps(rec)+' ')
    oc2={**oc,'sources':oc['sources'][:-1]+[{**oc['sources'][-1],'path':str(bad)}]};expect_error(lambda:assemble(oc2,ROOT),'reference archive')
    oc3={**oc,'sources':[{k:v for k,v in s.items() if k!='legacy_archive'} for s in oc['sources']]};expect_error(lambda:assemble(oc3,ROOT),'provenance-carrying')
    expect_error(lambda:assemble({k:v for k,v in cf.items() if k!='primitive_guard'},p1),'primitive_guard for L=7 is required')
    inv2=work/'inv_copy';inv2.mkdir();shutil.copy2(p1/'inputs/L7_coord.txt',inv2/'L7_coord.txt');(inv2/'L7_coord.txt').write_text((inv2/'L7_coord.txt').read_text()+'\n')
    expect_error(lambda:assemble({**cf,'primitive_guard':{'inventory':str(inv2/'L7_coord.txt'),'L':7}},p1),'differs from the inventory')
    ok('stream_overlap_primitive_and_legacy_archive_guards')
    # 11. Batch combination and its rejections.
    b3=plan('b3',404,'--refine7','--extra-inputs',extra,'--design',good,'--label','b3');runall(b3);sh(PROD+['merge',b3])
    out=work/'combined';sh([PY,ROOT/'tools/combine.py',p1,b3,'--output',out]);r=json.loads((out/'C7_final.json').read_text())
    assert r['batches']['count']==2 and abs(r['C7_full']-(r1['C7_full']+json.loads((b3/'C7_result.json').read_text())['C7_full'])/2)<1e-6*max(1,abs(r['C7_full']))
    names=list(r['components']);assert len(names)==len(set(names))==2*len(r1['components']) and all(n.split('/')[0] in ('b1','b3') for n in names)
    sh([PY,ROOT/'tools/combine.py',p1,b3,'--output',out])
    ch=work/'inputs_cgamma';shutil.copytree(srcin,ch);(ch/'cgamma_L5.txt').write_text((ch/'cgamma_L5.txt').read_text().replace('1','1',1)+' ')
    b4=plan('b4',505,'--refine7','--extra-inputs',extra,'--design',good,'--label','b4',inputs=ch);runall(b4)
    p_=sh(PROD+['merge',b4],fail=True);assert 'authenticated archive input' in p_.stderr,p_.stderr[-300:] # a non-archive Gamma file is rejected at assembly
    sh([PY,ROOT/'tools/combine.py',p1,b4,'--output',work/'c_bad1'],fail=True)
    for tag,edit in [('primitive',lambda c:c['retained_primitive'].update(mean=c['retained_primitive']['mean']+1)),('weight',lambda c:c['sources'][0].update(weight=.4)),
                     ('affine',None),('seed',None)]:
        t=work/f'b_{tag}';shutil.copytree(b3,t)
        if edit:c2=json.loads((t/'assembly.json').read_text());edit(c2);(t/'assembly.json').write_text(json.dumps(c2))
        elif tag=='affine':x=json.loads((t/'full_affine_assembly.json').read_text());x['K'][0]+=1e-9;(t/'full_affine_assembly.json').write_text(json.dumps(x))
        else:pr=json.loads((t/'production.json').read_text());pr['label']='bseed';(t/'production.json').write_text(json.dumps(pr))
        sh([PY,ROOT/'tools/combine.py',p1,t,'--output',work/f'c_{tag}'] if tag!='seed' else [PY,ROOT/'tools/combine.py',b3,t,'--output',work/'c_seed'],fail=True)
    ok('combine_two_batches_and_rejections',C7=r['C7_full'],chi2=r['batches']['chi2_about_combined'])
    # 11a. PLAN2: a direct primitive campaign replaces the retained primitive input; the sector is counted once.
    from campaign import inventory as inv7;rows7=inv7(srcin,7);G=sorted(r['id'] for r in rows7 if r['primitive'] and not r['power']);ng=len(rows7)
    assert len(G)==44 and any(r['primitive'] and r['power'] for r in rows7)
    def pcamp(name,counts=None,sel='primitive',inputs=srcin,seed=11):
        d=work/name;args=['--points',64] if counts is None else ['--counts',counts,'--points',0]
        sh(CAMP+['plan','--out',d,'--mode','qmc','--L',7,'--selection',sel,*args,'--replicates',4,'--seed',seed,'--shards',1,'--threads',1,'--executable',fake,'--inputs',inputs]);sh(CAMP+['run',d,'--index',0]);sh(CAMP+['merge',d]);return d
    def cfile(name,ids):f=work/name;f.write_text(f'{ng}\n'+''.join(f'{g} {64 if g in ids else 0}\n' for g in range(ng)));return f
    primP=pcamp('primP');primQ=pcamp('primQ',seed=12);primMiss=pcamp('primMiss',cfile('c_miss.txt',set(G[1:])),seed=13)
    freeX=pcamp('freeX',cfile('c_x.txt',{G[0]}),sel='free',seed=14);freeY=pcamp('freeY',cfile('c_y.txt',{G[0]}),sel='free',seed=15)
    invd=work/'inputs_inv';shutil.copytree(srcin,invd);(invd/'L7_coord.txt').write_text((invd/'L7_coord.txt').read_text()+'\n');primI=pcamp('primI',inputs=invd,seed=16)
    outp=work/'combined_prim';sh([PY,ROOT/'tools/combine.py',p1,b3,'--primitive',primP,'--output',outp]);rp=json.loads((outp/'C7_final.json').read_text())
    assert rp['retained_primitive'] is None and rp['primitive_source']['name']=='primitive/primP' and rp['retained_primitive_crosscheck']['retained']['mean']==r1['retained_primitive']['mean']
    assert abs(rp['batches']['chi2_about_combined']-r['batches']['chi2_about_combined'])<=1e-9*max(1,r['batches']['chi2_about_combined']) # invariant under the replacement
    assert any(json.loads((p1/'power_coarseA_L7/merged/N1.json').read_text())['counts'][g] for g in (x['id'] for x in rows7 if x['primitive'] and x['power'])) # power&&primitive support is legitimate
    outj=work/'combined_prim_j2';sh([PY,ROOT/'tools/combine.py',p1,b3,'--primitive',primP,'--output',outj,'--jobs',2]) # parallel verification: identical output
    assert (outj/'C7_final.json').read_bytes()==(outp/'C7_final.json').read_bytes()
    for d_,msg in [(primMiss,'exactly the L7 primitive classes'),(primI,'numerical inputs differ from the batches: L7_coord.txt')]:
        p_=sh([PY,ROOT/'tools/combine.py',p1,b3,'--primitive',d_,'--output',work/f'cp_{d_.name}'],fail=True);assert msg in p_.stderr,(d_.name,p_.stderr[-300:])
    cc=json.loads((outp/'combined_assembly.json').read_text())
    def src(d_,**kw):return {'name':kw.pop('name',d_.name),'campaign':d_.name,'level':'primitive','role':'estimator','L':7,'kind':'free','weight':1,'path':os.path.relpath(d_/'merged/N0.json',outp),**kw}
    cases=[({**cc,'retained_primitive':cc['retained_primitive_crosscheck']},'cannot be combined'),
           ({**cc,'sources':cc['sources']+[src(primQ)]},'exactly one primitive-level'),
           ({**cc,'sources':cc['sources']+[src(primQ,level='coarse',kind='power')]},'does not match its verified campaign'),
           ({**cc,'sources':cc['sources']+[src(freeX,level='free',weight=.5)]},'already covers'),
           ({**cc,'sources':[x for x in cc['sources'] if x['level']!='primitive']+[src(primMiss),src(freeX,level='free')]},'exactly the L7 primitive classes'),
           ({**cc,'retained_primitive':cc['retained_primitive_crosscheck'],'sources':[x for x in cc['sources'] if x['level']!='primitive']+[src(freeX,level='free'),src(freeY,level='free',weight=-1)]},'already covers'),
           ({**cc,'sources':[{**x,'kind':'free'} if x['name'].endswith('power_coarseA_L7') and x['name'].startswith('b1/') else x for x in cc['sources']]},'does not match its verified campaign')]
    for cfg,msg in cases:expect_error(lambda:assemble(cfg,outp),msg)
    # P2-R01: a primitive campaign with a different Gamma input is rejected (combine and standalone assembly).
    gd=work/'inputs_gamma7';shutil.copytree(srcin,gd);(gd/'cgamma_L7.txt').write_text((gd/'cgamma_L7.txt').read_text()+' ');primG=pcamp('primG',inputs=gd,seed=17)
    p_=sh([PY,ROOT/'tools/combine.py',p1,b3,'--primitive',primG,'--output',work/'cp_gamma'],fail=True);assert 'numerical inputs differ' in p_.stderr,p_.stderr[-300:]
    expect_error(lambda:assemble({**cc,'sources':[x for x in cc['sources'] if x['level']!='primitive']+[src(primG)]},outp),'cgamma_L7.txt differs')
    # P2-R04: mixed archived/direct assemblies bind new campaigns to the authenticated archive inputs.
    from assemble import original_config as ocfg
    oc=ocfg(ROOT/'reference');oc['retained_primitive']=None
    def osrc(d_):return {'name':d_.name,'campaign':d_.name,'level':'primitive','role':'estimator','L':7,'kind':'free','weight':1,'path':str(d_/'merged/N0.json')}
    rmix=assemble({**oc,'sources':oc['sources']+[osrc(primP)]},ROOT);assert rmix['retained_primitive'] is None and rmix['primitive_source']['name']=='primP'
    expect_error(lambda:assemble({**oc,'sources':oc['sources']+[osrc(primG)]},ROOT),'authenticated archive input')
    # P2-R02: support comes from the verified manifest; merged counts rewritten to claim a missing class are caught.
    tam=work/'primTam';shutil.copytree(primMiss,tam);mf=tam/'merged/N0.json';o=json.loads(mf.read_text());o['counts'][G[0]]=64;mf.write_text(json.dumps(o))
    au=json.loads((tam/'merged/audit.json').read_text());au['outputs']=[{'file':'merged/N0.json','sha256':C.digest(mf)}];(tam/'merged/audit.json').write_text(json.dumps(au))
    p_=sh([PY,ROOT/'tools/combine.py',p1,b3,'--primitive',tam,'--output',work/'cp_tam'],fail=True);assert 'does not match its manifest' in p_.stderr,p_.stderr[-300:]
    # --original is unchanged apart from the two new keys and the corrected guarded-class count (PLAN2 baseline).
    # The baseline is the committed fixture (tests/regenerate_original_baseline.py rebuilds it from commit 0227dc5).
    subprocess.run([PY,str(ROOT/'tools/assemble.py'),'--original','--output',str(work/'orig_now.json')],check=True,capture_output=True)
    o0=json.loads((ROOT/'tests/fixtures/assemble_original_0227dc5.json').read_text());o1=json.loads((work/'orig_now.json').read_text())
    assert o1.pop('primitive_source') is None and o1.pop('retained_primitive_crosscheck') is None and o0['primitive_guard'].pop('primitive_classes')==64 and o1['primitive_guard'].pop('primitive_classes')==44 and o0==o1
    ok('direct_primitive_replacement_guards_chi2_invariance_and_original_baseline',C7=rp['C7_full'],chi2=rp['batches']['chi2_about_combined'])
    # 11b. Pre-registered design: K_max from estimator campaigns only; the degree-7 check inherits the refine6 allocation.
    arch=work/'archive.json';from assemble import original_config as oc0,result_text;arch.write_text(result_text(assemble(oc0(ROOT/'reference'),ROOT)))
    rep=work/'design_rep.json';rep.write_text(json.dumps({'power_refine3B_L7':{'replicate_multiplier':2},'tprodA_L7':{'replicate_multiplier':2},'tprodB_L7':{'replicate_multiplier':2}}))
    pil=plan('pilot',707,'--refine7','--extra-inputs',extra,'--design',rep,'--label','pilot');runall(pil);sh(PROD+['merge',pil])
    sh([PY,ROOT/'tools/design.py','--pilot',pil,'--archive',arch,'--target-se',200,'--out',work/'design_v1.json','--meta',work/'design_meta.json'])
    dv=json.loads((work/'design_v1.json').read_text());dm=json.loads((work/'design_meta.json').read_text())
    est=[n for n in dv if 'refine7' not in n];pred=sum(dm['unit'][n]['variance']/(dv[n]['replicate_multiplier']*dv[n]['multiplier']) for n in est)**.5
    assert abs(pred-dm['predicted_se_per_batch'])<1e-9*pred and dm['K_max']==__import__('math').ceil((pred/30)**2)
    assert all((dv[f'power_refine7_L{L}']['multiplier'],dv[f'power_refine7_L{L}']['replicate_multiplier'])==(dv[f'power_refine6_L{L}']['multiplier'],dv[f'power_refine6_L{L}']['replicate_multiplier']) for L in (5,6,7))
    assert all((dv[x]['multiplier'],dv[x]['replicate_multiplier'])==(dv[y]['multiplier'],dv[y]['replicate_multiplier']) for x,y in __import__('production').PAIRS)
    p=sh([PY,ROOT/'tools/design.py','--pilot',p1,'--archive',arch,'--out',work/'d2.json','--meta',work/'d2m.json'],fail=True);assert 'multipliers must be 1' in p.stderr # b1 has sample multiplier 2
    for tag,edit_,msg in [('missing',lambda x:x['campaigns'].remove('power_refine3B_L7'),'missing: power_refine3B_L7'),('rep',lambda x:x['settings']['power_refine3B_L7'].update(replicate_multiplier=1),'replicate count inconsistent')]:
        q=work/f'pil_{tag}';shutil.copytree(pil,q);x=json.loads((q/'production.json').read_text());edit_(x);(q/'production.json').write_text(json.dumps(x))
        p=sh([PY,ROOT/'tools/design.py','--pilot',q,'--archive',arch,'--out',work/f'd_{tag}.json','--meta',work/f'dm_{tag}.json'],fail=True);assert msg in p.stderr,(tag,p.stderr[-400:])
    q=work/'pil_swap';shutil.copytree(pil,q);x=json.loads((q/'assembly.json').read_text());a_,b_=[s for s in x['sources'] if s['campaign'] in ('power_refine3B_L7','power_refine6_L7')];a_['campaign'],b_['campaign']=b_['campaign'],a_['campaign'];(q/'assembly.json').write_text(json.dumps(x))
    p=sh([PY,ROOT/'tools/design.py','--pilot',q,'--archive',arch,'--out',work/'d_sw.json','--meta',work/'dm_sw.json'],fail=True);assert 'does not match its campaign' in p.stderr,p.stderr[-400:]
    ar2=work/'archive_missing.json';y=json.loads(arch.read_text());y['components'].pop('power_refine3B_L7');ar2.write_text(json.dumps(y))
    p=sh([PY,ROOT/'tools/design.py','--pilot',pil,'--archive',ar2,'--out',work/'d_ar.json','--meta',work/'dm_ar.json'],fail=True);assert 'archived estimator variance missing' in p.stderr,p.stderr[-400:]
    zer=work/'inputs_zero';shutil.copytree(srcin,zer);tk=(zer/'tree_production_counts_L5.txt').read_text().split();act=next(i for i in range(len(tk[1::2])) if int(tk[2+2*i]));tk[2+2*act]='0'
    (zer/'tree_production_counts_L5.txt').write_text(tk[0]+'\n'+''.join(f'{g} {c}\n' for g,c in zip(tk[1::2],tk[2::2])))
    pz=plan('pilot_zero',909,'--refine7','--extra-inputs',extra,'--design',rep,'--label','pzero',inputs=zer);runall(pz);sh(PROD+['merge',pz])
    p=sh([PY,ROOT/'tools/design.py','--pilot',pz,'--archive',arch,'--out',work/'d_z.json','--meta',work/'dm_z.json'],fail=True);assert 'exact vector' in p.stderr,p.stderr[-400:]
    dbl=work/'inputs_dbl';shutil.copytree(srcin,dbl);tk=(dbl/'tree_production_counts_L5.txt').read_text().split();(dbl/'tree_production_counts_L5.txt').write_text(tk[0]+'\n'+''.join(f'{g} {2*int(c)}\n' for g,c in zip(tk[1::2],tk[2::2])))
    pd=plan('pilot_dbl',808,'--refine7','--extra-inputs',extra,'--design',rep,'--label','pdbl',inputs=dbl);runall(pd);sh(PROD+['merge',pd])
    p=sh([PY,ROOT/'tools/design.py','--pilot',pd,'--archive',arch,'--out',work/'d_dbl.json','--meta',work/'dm_dbl.json'],fail=True);assert 'frozen unit allocation' in p.stderr,p.stderr[-400:]
    ra=json.loads(arch.read_text());from campaign import inventory as inv0;assert ra['primitive_guard']['primitive_classes']==sum(1 for r in inv0(ROOT/'reference/inputs',7) if r['primitive'] and not r['power'])==44
    ok('design_estimator_only_prediction_check_allocation_and_pilot_guard',K_max=dm['K_max'],predicted_se=pred)
    # 11c. Replay accuracy is judged per element: a small-magnitude row cannot hide behind a large one (R3-01).
    sys.path.insert(0,str(ROOT/'tests'));from check_quad import accuracy;from decimal import Decimal as Dq
    z=lambda v:[str(v)]+['0']*13;Qm={(0,1):z(Dq('1e8')),(0,2):z(Dq(1))};Rm={k:list(v) for k,v in Qm.items()};Om={(0,1):z(Dq('1e8')),(0,2):z(Dq(1)+Dq('1e-10'))}
    v=accuracy(Qm,Om,Rm,list(Qm),'strict');w=accuracy(Qm,Om,Rm,list(Qm),'rounding-floor')
    assert not v['passed'] and not w['passed'] and v['strict']['failures']==w['rounding_floor']['failures']==1
    Om2={(0,1):z(Dq('1e8')+Dq('1e-12')),(0,2):z(Dq(1))};assert accuracy(Qm,Om2,Rm,list(Qm),'rounding-floor')['passed'] and not accuracy(Qm,Om2,Rm,list(Qm),'strict')['passed']
    ok('replay_accuracy_per_element_mixed_magnitudes')
    # 12. Slurm template: C7_INDEX_OFFSET and the srun line, with a pass-through srun.
    fb=work/'fakebin';fb.mkdir();(fb/'srun').write_text('#!/bin/bash\nwhile [[ "$1" == --* ]]; do echo "srun-opt $1" >&2; shift; done\nexec "$@"\n');(fb/'srun').chmod(0o755)
    t=plan('tmpl',606);jobs=json.loads((t/'production.json').read_text())['jobs'];target=5
    env={'PATH':f'{fb}:{os.environ["PATH"]}','C7_ROOT':str(ROOT),'C7_PRODUCTION':str(t),'SLURM_ARRAY_TASK_ID':'2','C7_INDEX_OFFSET':'3','SLURM_CPUS_PER_TASK':'1','C7_PYTHON':PY}
    p=sh(['bash',ROOT/'cluster/production.slurm'],env);jc=jobs[target]
    assert any((t/jc['campaign']/'checkpoints').glob(f's{jc["index"]:06d}_*.json')) and 'srun-opt --cpus-per-task=1' in p.stderr
    ok('slurm_template_index_offset_and_cpus_per_task')
    (work/'pipeline_tests.json').write_text(json.dumps({'passed':True,'checks':REPORT},indent=2)+'\n')
    print('ALL PIPELINE CHECKS PASSED:',work/'pipeline_tests.json')
    if not a.keep:shutil.rmtree(work)
if __name__=='__main__':main()
