#!/usr/bin/env python3
"""End-to-end regression of the C8 batch tooling with a fake integrator (no numerics; runs in seconds).

Builds a tiny synthetic inventory (loops 5..8), a synthetic affine/control map and a frozen design bundle, then runs
the real tools: campaign.py (plan/run/merge through production8.py), the exact loop-5 campaign, production8 plan with
--design-meta, assemble8 (preview), combine8 (full, partial, rejected counts) and the frozen loop-5 check.
Requires numpy and scipy (Sobol nets). Usage: python tests/test_pipeline8.py
"""
from __future__ import annotations
import hashlib, json, os, shutil, stat, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable;T=ROOT/'tools'
sys.path.insert(0,str(T))
import numpy as np
from c8lib import LEVEL_SPEC,NW,NV
from campaign import tree_count

FAKE='''#!PYTHON
import json,sys,hashlib
a=dict(zip(sys.argv[1::2],sys.argv[2::2]));lines=open(a['--tasks']).read().split('\\n');magic,ng,n=lines[0].split()
assert magic=='C8TASKS1'
rows=[]
for ln in lines[1:]:
    if not ln.strip():continue
    uid,rep,g,b,e,tot=map(int,ln.split())
    h=hashlib.sha256(f"{a['--seed']}:{rep}:{g}:{b}:{a.get('--degree','0')}".encode()).digest()
    val=[(int.from_bytes(h[2*i:2*i+2],'little')/65536-.5)*(e-b)/tot for i in range(16)]
    rows.append({'uid':uid,'replicate':rep,'graph':g,'begin':b,'end':e,'total':tot,'quad_calls':0,'mp_calls':0,'seconds':0.001*(e-b),'value':val})
out={'schema':'c8-hpc-1','slots':8,'mode':a['--mode'],'L':int(a['--L']),'degree':int(a.get('--degree','0')),'seed':int(a['--seed']),'rate':float(a['--rate']),
     'inventory_count':int(ng),'long_double_bits':64,'rows':rows}
open(a['--output'],'w').write(json.dumps(out))
'''

def run(*cmd,ok=True):
    r=subprocess.run([str(c) for c in cmd],capture_output=True,text=True)
    if ok and r.returncode:raise RuntimeError(' '.join(map(str,cmd))+'\n'+r.stdout[-1500:]+r.stderr[-1500:])
    if not ok and not r.returncode:raise AssertionError('expected failure: '+' '.join(map(str,cmd)))
    return r

def inventory(d:Path,L:int):
    NE=L*(L+1)//2;lines=[f'{L} 4']
    for g,(wa,wb,pw) in enumerate([(1.,.2,0),(2.,.1,1),(.5,.3,1),(1.5,.45,0)]):
        lines.append(f'{g} {wa} {wb} {pw} 0 1');lines.append('1 '+' '.join(['1']+['0']*(NE-1)))
    (d/f'L{L}_coord.txt').write_text('\n'.join(lines)+'\n');(d/f'cgamma_L{L}.txt').write_text(' '.join(['1']+['0']*(NW-1))+'\n')
    for N in range(1,15):(d/f'cw_L{L}_N{N}.txt').write_text(f'C8WEIGHTS1 1\n0\n')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    tmp=Path(tempfile.mkdtemp(prefix='c8pipe_'));print('workdir',tmp)
    fb=tmp/'bin';fb.mkdir();(fb/'squeue').write_text('#!/bin/sh\n[ -n "$FAKE_SQUEUE_SLEEP" ] && sleep "$FAKE_SQUEUE_SLEEP"\n[ -n "$SQUEUE_PARTITION" ] && exit 0\nprintf "%s" "$FAKE_SQUEUE_OUT"\nexit 0\n');(fb/'squeue').chmod(0o755) # scheduler with no jobs; a partition filter would hide jobs
    os.environ['PATH']=str(fb)+os.pathsep+os.environ['PATH']
    exe=tmp/'fake_integrate';exe.write_text(FAKE.replace('PYTHON',PY));exe.chmod(exe.stat().st_mode|stat.S_IEXEC)
    inp=tmp/'inputs';inp.mkdir()
    for L in (5,6,7,8):inventory(inp,L)
    run(PY,T/'prepare_inputs.py',inp) # C7IDX1 byte indices, as for the real inventory
    # 1. exact loop 5 (two degrees), merged
    unit5=tmp/'u5.json';unit5.write_text(json.dumps({'campaigns':[{'name':'exact_L5','L':5,'mode':'exact','B':1,'n':0,'degrees':[12,14],'rate':'.8','weight':1,'level':'exact','role':'input'}]}))
    run(PY,T/'production8.py','plan',tmp/'ex5','--unit',unit5,'--seed',1,'--inputs',inp,'--executable',exe,'--threads',1)
    jobs=json.loads((tmp/'ex5/production.json').read_text())['jobs']
    for i in range(len(jobs)):run(PY,T/'production8.py','run',tmp/'ex5','--index',i,'--threads',1,'--allow-oversubscribe')
    run(PY,T/'production8.py','merge',tmp/'ex5')
    m5=json.loads((tmp/'ex5/exact_L5/manifest.json').read_text());assert m5['counts']==[tree_count(5)]*4
    # 1b. symmetry smoke comparator on a campaign with two checkpoint parts and two degrees
    sb=tmp/'smk_ref';smk=tmp/'smk'
    run(PY,T/'production8.py','plan',sb,'--unit',unit5,'--seed',3,'--inputs',inp,'--executable',exe,'--threads',1,'--shards-per-stream',1,'--checkpoint-tasks',2)
    run(PY,T/'production8.py','run',sb,'--index',0,'--threads',1,'--allow-oversubscribe')
    refs=sorted((sb/'exact_L5/checkpoints').glob('*.json'));assert len(refs)==4
    def smoke_copy(mode,edit=None):
        d=smk/mode/'b1'/'exact_L5'/'checkpoints';d.mkdir(parents=True,exist_ok=True)
        for f in refs:
            j=json.loads(f.read_text())
            for r in j['rows']:r['seconds']=r.get('seconds',0)+(1 if mode=='ht' else 2) # timings differ between modes
            if edit:edit(f.name,j)
            (d/f.name).write_text(json.dumps(j))
    sa=tmp/'smk_affine.json';sa.write_text(json.dumps({'loops':{'5':{'J':np.random.default_rng(2).normal(size=(NW+1,NV)).tolist()}}}))
    def base_result(se):
        f=tmp/f'smk_base_{se}.json';f.write_text(json.dumps({'campaign_aggregates':{'exact_L5':{'sampling_se_C8':se}}}));return f
    cmp=lambda se:[PY,ROOT/'cluster/symmetry/smoke_compare.py',smk,sb,'1e-10','1e-6',sa,base_result(se),'phys,ht','0']
    env_ok=os.environ.get('C8_ROOT');os.environ['C8_ROOT']=str(ROOT)
    smoke_copy('phys');smoke_copy('ht')
    run(*cmp(1.0)[:-1],ok=False) # no element: rejected
    assert run(*cmp(1.0),ok=False).returncode==3 # element 0 is not the qualifying set: a gate failure without the switch
    os.environ['C8X_SMOKE_DIAGNOSTIC']='1';assert run(*cmp(1.0),ok=False).returncode==3;del os.environ['C8X_SMOKE_DIAGNOSTIC'] # an inherited variable is no bypass
    cmp0=cmp;cmp=lambda se:[cmp0(se)[0],cmp0(se)[1],'--diagnostic',*cmp0(se)[2:]] # explicit reduced (diagnostic) comparisons from here on
    run(*cmp(1.0)) # equal values, different timings: pass (diagnostic element set)
    def bump(name,j):
        if name==refs[1].name:j['rows'][0]['value'][2]*=1+1e-9
    smoke_copy('phys',bump);smoke_copy('ht',bump);run(*cmp(1e30),ok=False) # beyond the row bound
    def offset(name,j):
        for r in j['rows']:r['value'][3]+=1e-12*max(abs(v) for v in r['value'])
    smoke_copy('phys',offset);smoke_copy('ht',offset);run(*cmp(1e30)) # within the row bound, negligible on the estimator scale
    run(*cmp(1e-30),ok=False) # the same offset fails against a tiny sampling SE
    smoke_copy('phys');smoke_copy('ht',offset);run(*cmp(1e30),ok=False) # modes disagree
    if env_ok is None:del os.environ['C8_ROOT']
    else:os.environ['C8_ROOT']=env_ok
    # 2. synthetic full affine map with loop-5 provenance and controls (adjusted = J; training seed 99)
    rng=np.random.default_rng(1);mh5=sha(tmp/'ex5/exact_L5/manifest.json')
    loops={str(L):{'J':(J:=rng.normal(size=(NW+1,NV))).tolist(),'control':np.zeros((NW+1,NV)).tolist(),'adjusted':J.tolist(),'training':[{'seed':99}]} for L in (5,6,7,8)}
    aff=tmp/'full_affine.json';aff.write_text(json.dumps({'schema':'c8-full-affine-1','K':[0.]*(NW+1),'loops':loops,'sources':{'5':{'manifest_sha256':mh5,'degrees':[12,14]}}}))
    # 3. production unit with every canonical level at loops 6..8, counts files, frozen bundle (as design8 writes it)
    bundle=tmp/'bundle';bundle.mkdir();camps=[];design={}
    for L in (6,7,8):
        for lev,(mode,role,degs) in LEVEL_SPEC.items():
            pairs=[('A',.5),('B',.5)] if lev=='free' else [('A',2/3),('B',1/3)] if lev=='coarse' else [('',1)]
            for tag,w in pairs:
                name=f'{lev}{tag}_L{L}';cf=f'counts_{lev}_L{L}.txt';power=mode=='power'
                act=[g for g,pw in enumerate([0,1,1,0]) if bool(pw)==power]
                (bundle/cf).write_text('4\n'+''.join(f'{g} {(2 if g in act else 0)}\n' for g in range(4)))
                s={'name':name,'L':L,'mode':mode,'B':2,'n':0,'degrees':degs,'rate':'.8','weight':w,'level':lev,'role':role,'counts':cf}
                if tag:s['pair']=f"{lev}{'B' if tag=='A' else 'A'}_L{L}"
                camps.append(s);design[name]={'multiplier':1,'replicate_multiplier':1,'shards':1,'checkpoint_tasks':64,'chunk_points':0 if power else 65536}
    (bundle/'unit_production.json').write_text(json.dumps({'campaigns':camps},indent=1));(bundle/'design.json').write_text(json.dumps(design,indent=1))
    exp={}
    for L in (6,7,8):
        for n in (f'L{L}_coord.txt',f'L{L}_coord.txt.idx',f'cgamma_L{L}.txt'):exp[n]=sha(inp/n)
        exp[f'exact_zero_L{L}.txt']='absent'
        for N in range(1,10):exp[f'cw_L{L}_N{N}.txt']=sha(inp/f'cw_L{L}_N{N}.txt')
    meta={'batches':2,'affine_sha256':sha(aff),'design_sha256':sha(bundle/'design.json'),'unit_sha256':sha(bundle/'unit_production.json'),
          'counts_sha256':{f.name:sha(f) for f in sorted(bundle.glob('counts_*.txt'))},'forbidden_seeds':[99],'forbidden_batch_seeds':[7],'expected_input_sha256':exp,
          'exact_loop5':{'manifest_sha256':mh5,'chosen_degree':14,'previous_degree':12}}
    (bundle/'design_meta.json').write_text(json.dumps(meta))
    # 4. two production batches
    batches=[]
    for k,seed in enumerate((101,102)):
        b=tmp/f'batch{k}'
        run(PY,T/'production8.py','plan',b,'--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',seed,'--inputs',inp,'--executable',exe,'--threads',1,'--label',f'b{k}')
        for i in range(len(json.loads((b/'production.json').read_text())['jobs'])):run(PY,T/'production8.py','run',b,'--index',i,'--threads',1,'--allow-oversubscribe')
        run(PY,T/'production8.py','merge',b);batches.append(b)
    run(PY,T/'production8.py','plan',tmp/'bad','--unit',bundle/'unit_production.json','--design',bundle/'design.json','--seed',103,'--inputs',inp,'--executable',exe,ok=False) # no --design-meta
    run(PY,T/'production8.py','plan',tmp/'bad2','--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',7,'--inputs',inp,'--executable',exe,ok=False) # pilot batch seed
    ex=[tmp/'ex5/exact_L5/merged/N14.json',tmp/'ex5/exact_L5/merged/N12.json']
    common=['--affine',aff,'--exact5',*ex,'--design-meta',bundle/'design_meta.json']
    r=run(PY,T/'combine8.py',*batches,'--output',tmp/'final',*common);res=json.loads((tmp/'final/C8_final.json').read_text())
    assert res['final'] is True and res['batches']['count']==2 and not res['preview'] and res['frozen_design'] and np.isfinite(res['C8_full']) and res['coverage']['8']['active']>0
    run(PY,T/'combine8.py',batches[0],'--output',tmp/'partial','--partial',*common);pres=json.loads((tmp/'partial/C8_partial.json').read_text())
    assert pres['final'] is False and 'PARTIAL' in pres['status'] and not (tmp/'partial/C8_final.json').exists()
    run(PY,T/'combine8.py',batches[0],'--output',tmp/'rej1',*common,ok=False) # one of two batches without --partial
    run(PY,T/'combine8.py',*batches,'--output',tmp/'rej2','--partial',*common,ok=False) # --partial with the full set
    run(PY,T/'combine8.py',*batches,'--output',tmp/'rej3','--affine',aff,'--exact5',ex[0],ex[0],'--design-meta',bundle/'design_meta.json',ok=False) # loop-5 degrees not frozen
    # 4b. amendment A1: extension batches x1 (complete, merged), x2 (incomplete), x3 (complete checkpoints, not merged)
    ext_dir=tmp/'ext';ext_dir.mkdir();xb={}
    for lab,seed in (('x1',201),('x2',202),('x3',203)):
        b=ext_dir/lab;xb[lab]=b
        run(PY,T/'production8.py','plan',b,'--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',seed,'--inputs',inp,'--executable',exe,'--threads',1,'--label',lab)
        n=len(json.loads((b/'production.json').read_text())['jobs'])
        for i in range(n if lab!='x2' else 1):run(PY,T/'production8.py','run',b,'--index',i,'--threads',1,'--allow-oversubscribe')
    run(PY,T/'production8.py','merge',xb['x1'])
    extf=ext_dir/'extension.json'
    basel=[{'label':f'b{k}','seed':s,'production_sha256':sha(batches[k]/'production.json')} for k,s in enumerate((101,102))]
    xlist=[{'label':lab,'seed':s,'path':lab} for lab,s in (('x1',201),('x2',202),('x3',203))]
    extdoc=lambda base,ext:json.dumps({'schema':'c8-extension-1','design_meta_sha256':sha(bundle/'design_meta.json'),'base':base,'extension':ext})
    extf.write_text(extdoc(basel,xlist))
    xc=['--extension',extf,*common]
    for name,doc in (('nometa',extdoc(basel,xlist+[{'label':'x5','seed':205,'path':'x5'}])),('count',extdoc(basel[:1],xlist)),('dup',extdoc(basel,xlist+[{'label':'x1','seed':204,'path':'x4'}])),('sha',extdoc([basel[0],{**basel[1],'production_sha256':'0'*64}],xlist))):
        bad=ext_dir/f'bad_{name}.json';bad.write_text(doc) # declared but never planned / one base batch only / duplicate extension label / wrong base record
        run(PY,T/'combine8.py',*batches,xb['x1'],'--output',tmp/f'xbad_{name}','--extension',bad,*common,ok=False)
    run(PY,T/'combine8.py',*batches,xb['x1'],'--output',tmp/'xrej1',*xc,ok=False) # x3 has every checkpoint but is left out
    run(PY,T/'production8.py','merge',xb['x3'])
    run(PY,T/'combine8.py',batches[0],xb['x1'],xb['x3'],'--output',tmp/'xrej2',*xc,ok=False) # base batch b1 missing
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x2'],xb['x3'],'--output',tmp/'xrej3',*xc,ok=False) # x2 not merged (incomplete)
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],'--output',tmp/'xrej4','--partial',*xc,ok=False) # --partial with --extension
    run(PY,T/'combine8.py',*batches,'--output',tmp/'xrej5','--closed',*common,ok=False) # --closed without --extension
    run(PY,T/'production8.py','plan',ext_dir/'x9','--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',209,'--inputs',inp,'--executable',exe,'--threads',1,'--label','x9')
    for i in range(len(json.loads((ext_dir/'x9/production.json').read_text())['jobs'])):run(PY,T/'production8.py','run',ext_dir/'x9','--index',i,'--threads',1,'--allow-oversubscribe')
    run(PY,T/'production8.py','merge',ext_dir/'x9')
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],ext_dir/'x9','--output',tmp/'xrej6',*xc,ok=False) # x9 is not a planned extension batch
    pj=ext_dir/'x9/production.json';pd=json.loads(pj.read_text());pd['seed']=210;pj.write_text(json.dumps(pd)) # relabelled streams of another seed
    bad=ext_dir/'bad_seed.json';bad.write_text(extdoc(basel,xlist+[{'label':'x9','seed':210,'path':'x9'}]))
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],ext_dir/'x9','--output',tmp/'xbad_seed','--extension',bad,*common,ok=False)
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],'--output',tmp/'xint',*xc)
    xi=json.loads((tmp/'xint/C8_interim.json').read_text())
    assert xi['final'] is False and 'INTERIM' in xi['status'] and [x['label'] for x in xi['extension']['omitted_incomplete']]==['x2'] and 0<xi['extension']['omitted_incomplete'][0]['completed_fraction']<1 and xi['batches']['count']==4 and not (tmp/'xint/C8_final.json').exists()
    # an omitted batch with inconsistent planning metadata (an unplanned degree in one manifest) is rejected, not omitted
    x6=ext_dir/'x6'
    run(PY,T/'production8.py','plan',x6,'--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',206,'--inputs',inp,'--executable',exe,'--threads',1,'--label','x6')
    pc=next(c for c in json.loads((x6/'production.json').read_text())['campaigns'] if c.startswith('refine3'));mp=x6/pc/'manifest.json';mm=json.loads(mp.read_text());mm['degrees'].append(9);mp.write_text(json.dumps(mm))
    bad=ext_dir/'bad_tamper.json';bad.write_text(extdoc(basel,xlist+[{'label':'x6','seed':206,'path':'x6'}]))
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],'--output',tmp/'xbad_tamper','--extension',bad,*common,ok=False)
    x7=ext_dir/'x7' # a regrouped checkpoint layout (checkpoint_tasks) of an omitted batch is rejected too
    run(PY,T/'production8.py','plan',x7,'--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',207,'--inputs',inp,'--executable',exe,'--threads',1,'--label','x7')
    mp=x7/pc/'manifest.json';mm=json.loads(mp.read_text());mm['checkpoint_tasks']=1;mp.write_text(json.dumps(mm))
    bad=ext_dir/'bad_regroup.json';bad.write_text(extdoc(basel,xlist+[{'label':'x7','seed':207,'path':'x7'}]))
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],'--output',tmp/'xbad_regroup','--extension',bad,*common,ok=False)
    # lane runner: queue the incomplete x2, one worker finishes it and merges it; then the closed combination of all five
    costs=tmp/'costs.json';costs.write_text(json.dumps({str(i):float(i) for i in range(len(json.loads((xb['x2']/'production.json').read_text())['jobs']))}))
    run(PY,T/'lane8.py','queue','--queue',tmp/'q','--costs',costs,xb['x2'])
    order=[f"{e['label']}_{int(e['index']):04d}" for e in json.loads((tmp/'q/order.json').read_text())['elements']]
    old=os.path.getmtime(tmp/'q/order.json')-7200 # attempts and a merge claim of another job without heartbeat, and an own attempt
    (tmp/'q/claims'/f'{order[0]}.0').write_text(json.dumps({'job':'99999','slot':0}));os.utime(tmp/'q/claims'/f'{order[0]}.0',(old,old))
    (tmp/'q/claims'/f'{order[1]}.0').write_text(json.dumps({'job':'local','slot':0}))
    (tmp/'q/claims'/f'{order[2]}.0').write_text('');os.utime(tmp/'q/claims'/f'{order[2]}.0',(old,old)) # unreadable leftover
    (tmp/'q/merge/x2.0').write_text(json.dumps({'job':'99999','slot':1}));os.utime(tmp/'q/merge/x2.0',(old,old))
    run(PY,T/'lane8.py','run','--queue',tmp/'q','--slot',0,'--threads',1,'--c8-root',ROOT,'--executable',exe)
    assert (tmp/'q/merge/x2.ok').exists() and not list((tmp/'q/failed').iterdir()) and len(list((tmp/'q/done').iterdir()))==len(order)
    d0,d1,d2=(json.loads((tmp/'q/done'/k).read_text()) for k in order[:3]);mok=json.loads((tmp/'q/merge/x2.ok').read_text())
    assert (d0['how'],d0['attempt'])==('takeover',1) and (d1['how'],d1['attempt'])==('resume',0) and (d2['how'],d2['attempt'])==('takeover',1) and mok['attempt']==1
    run(PY,T/'lane8.py','status','--queue',tmp/'q')
    # queue-aware quarantine: the checkpoint is recomputed by the lane and the batch re-merged with an identical audit
    camp=json.loads((xb['x2']/'production.json').read_text())['campaigns'][0];ck=sorted((xb['x2']/camp/'checkpoints').glob('*.json'))[0]
    run(PY,T/'lane8.py','quarantine','--queue',tmp/'q','--c8-root',ROOT,'--label','x2','--campaign',camp,'--identity',ck.stem,'--reason','test')
    run(PY,T/'lane8.py','quarantine','--queue',tmp/'q','--c8-root',ROOT,'--label','x2','--campaign',camp,'--identity',ck.stem,'--reason','test rerun') # restartable
    assert not ck.exists() and not (tmp/'q/merge/x2.ok').exists() and len(list((tmp/'q/done').iterdir()))==len(order)-1
    run(PY,T/'lane8.py','run','--queue',tmp/'q','--slot',0,'--threads',1,'--c8-root',ROOT,'--executable',exe)
    assert ck.exists() and (tmp/'q/merge/x2.ok').exists() and (xb['x2']/camp/'merged/audit.json').exists() and len(list((tmp/'q/done').iterdir()))==len(order)
    # an abandoned element (MAX_FAILURES failed attempts) makes the worker exit nonzero; explicit recovery resets the budget
    k3=order[3];idx3=int(k3.split('_')[1])
    (tmp/'q/done'/k3).unlink()
    for n in (1,2):(tmp/'q/claims'/f'{k3}.{n}').write_text(json.dumps({'job':'99999','slot':0}));os.utime(tmp/'q/claims'/f'{k3}.{n}',(old,old))
    for n in (0,1,2):(tmp/'q/failed'/f'{k3}.{n}').write_text('{}')
    lane=[PY,T/'lane8.py','run','--queue',tmp/'q','--slot',0,'--threads',1,'--c8-root',ROOT,'--executable',exe]
    assert run(*lane,ok=False).returncode==1 and not (tmp/'q/done'/k3).exists()
    (tmp/'q/MAINTENANCE').write_text('{}') # a worker that starts during recovery waits and claims nothing
    before=sorted(os.listdir(tmp/'q/claims'));w=subprocess.Popen([str(x) for x in lane]);import time as _t;_t.sleep(5);w.terminate();w.wait(60)
    assert sorted(os.listdir(tmp/'q/claims'))==before and not (tmp/'q/done'/k3).exists()
    run(PY,T/'lane8.py','invalidate','--queue',tmp/'q','--label','x2','--index',idx3,'--reason','test',ok=False) # marker exists: refused
    (tmp/'q/MAINTENANCE').unlink()
    os.environ['FAKE_SQUEUE_OUT']='123|c8x-smoke|RUNNING\n' # another job of this package exists: recovery refused, no marker left
    run(PY,T/'lane8.py','invalidate','--queue',tmp/'q','--label','x2','--index',idx3,'--reason','test',ok=False);del os.environ['FAKE_SQUEUE_OUT']
    assert not (tmp/'q/MAINTENANCE').exists()
    run(PY,T/'lane8.py','invalidate','--queue',tmp/'q','--label','x2','--index',idx3,'--reason','test')
    assert not (tmp/'q/MAINTENANCE').exists()
    run(*lane);d3=json.loads((tmp/'q/done'/k3).read_text())
    assert (d3['how'],d3['attempt'])==('claim',4) and (tmp/'q/merge/x2.ok').exists() and not list((tmp/'q/failed').iterdir())
    # finalize after the wave: x8 has every checkpoint but no done markers (cut off) and one campaign merged before the
    # cut; x10 is incomplete. finalize merges x8 (resuming), leaves x10, and refuses while another C8 job exists.
    for lab,seed in (('x8',208),('x10',210)):
        run(PY,T/'production8.py','plan',ext_dir/lab,'--unit',bundle/'unit_production.json','--design',bundle/'design.json','--design-meta',bundle/'design_meta.json','--seed',seed,'--inputs',inp,'--executable',exe,'--threads',1,'--label',lab)
        n=len(json.loads((ext_dir/lab/'production.json').read_text())['jobs'])
        for i in range(n if lab=='x8' else 2):run(PY,T/'production8.py','run',ext_dir/lab,'--index',i,'--threads',1,'--allow-oversubscribe')
    c0=json.loads((ext_dir/'x8/production.json').read_text())['campaigns'][0];run(PY,T/'campaign.py','merge',ext_dir/'x8'/c0)
    run(PY,T/'lane8.py','queue','--queue',tmp/'qf','--costs',costs,ext_dir/'x8',ext_dir/'x10')
    fin=[PY,T/'lane8.py','finalize','--queue',tmp/'qf','--c8-root',ROOT]
    os.environ['FAKE_SQUEUE_OUT']='77|c8x-lane|PENDING\n';os.environ['SQUEUE_PARTITION']='defq';run(*fin,ok=False);del os.environ['SQUEUE_PARTITION'] # an inherited filter cannot hide the lane
    os.environ['FAKE_SQUEUE_OUT']='not a squeue line\n';run(*fin,ok=False) # malformed answer
    assert not (tmp/'qf/MAINTENANCE').exists()
    os.environ['FAKE_SQUEUE_OUT']='78|c8x-lane|COMPLETED\n79|c8d3-prod_lane-abc|RUNNING\n80|c8x-stop|PENDING\n';r0=run(*fin);del os.environ['FAKE_SQUEUE_OUT'] # finished jobs, other packages and the stop job do not block
    r=r0;assert (tmp/'qf/merge/x8.ok').exists() and not (tmp/'qf/merge/x10.ok').exists() and 'x10: incomplete' in r.stdout and not (tmp/'qf/MAINTENANCE').exists()
    # a passed wave deadline: a worker (also a restarted one) claims nothing; the deadline is immutable
    run(PY,T/'lane8.py','queue','--queue',tmp/'qd','--costs',costs,ext_dir/'x10')
    run(PY,T/'lane8.py','deadline','--queue',tmp/'qd','--epoch',1.0);run(PY,T/'lane8.py','deadline','--queue',tmp/'qd','--epoch',9e9,ok=False)
    run(PY,T/'lane8.py','run','--queue',tmp/'qd','--slot',0,'--threads',1,'--c8-root',ROOT,'--executable',exe);assert not os.listdir(tmp/'qd/claims')
    # the deadline passes while the scheduler query runs: no claim is published and nothing starts
    import time as _t
    run(PY,T/'lane8.py','queue','--queue',tmp/'qs','--costs',costs,ext_dir/'x10');run(PY,T/'lane8.py','deadline','--queue',tmp/'qs','--epoch',_t.time()+2)
    os.environ['FAKE_SQUEUE_SLEEP']='4';run(PY,T/'lane8.py','run','--queue',tmp/'qs','--slot',0,'--threads',1,'--c8-root',ROOT,'--executable',exe);del os.environ['FAKE_SQUEUE_SLEEP']
    assert not os.listdir(tmp/'qs/claims') and not os.listdir(tmp/'qs/logs')
    assert all((ext_dir/'x8'/c/'merged/audit.json').exists() for c in json.loads((ext_dir/'x8/production.json').read_text())['campaigns'])
    assert not any((ext_dir/'x10'/c/'merged').exists() for c in json.loads((ext_dir/'x10/production.json').read_text())['campaigns'])
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x3'],'--output',tmp/'xrej7','--closed',*xc,ok=False) # x2 now complete: must be included
    run(PY,T/'combine8.py',*batches,xb['x1'],xb['x2'],xb['x3'],'--output',tmp/'xfin','--closed',*xc)
    xf=json.loads((tmp/'xfin/C8_final.json').read_text())
    assert xf['final'] is True and xf['batches']['count']==5 and xf['extension']['omitted_incomplete']==[] and xf['extension']['closed'] is True
    # 5. preview of one batch (no bundle)
    run(PY,T/'preview8.py',batches[0],'--affine',aff,'--exact5',*ex,'--output',tmp/'preview')
    assert json.loads((tmp/'preview/C8_preview.json').read_text())['preview'] is True
    shutil.rmtree(tmp);print('test_pipeline8: all checks passed')
if __name__=='__main__':main()
