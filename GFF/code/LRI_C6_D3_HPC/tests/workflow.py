#!/usr/bin/env python3
"""Small complete distributed d=3 workflow with the REAL native worker, with and without the frozen grid; not physics.

Covers: full coverage and assembly; restart after a deleted checkpoint with a different thread count; concurrent
duplicate executions; a forced native failure; a foreign-plan checkpoint; an interrupted (--max-blocks) run versus an
uninterrupted one; resumable merge and idempotent assembly; status; the job-private runtime (A-M1); corruption,
identity, runtime-digest, wrong-dimension and wrong-interval tampering; a corrupt merged file with a consistent
self-hash; chunked versus unchunked jets; all ten primitive strata recomputed; node-local staging; a campaign path
containing URI-reserved characters (A-URI).
"""
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
import argparse,concurrent.futures,contextlib,copy,io,json,shutil,subprocess,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import digest,dump,load,object_hash
import production as p
from assemble import evaluate
REAL_RUN=subprocess.run

def plan(d,grid,seed=82819399):
    p.plan(NS(directory=d,seed=seed,seed_scheme='hashed',points=4,replicates=2,multiplier=1,shards=2,shard_policy='cost',threads=2,checkpoint_tasks=64,chunk_points=3,primitive_mode='recompute',grid=grid,sum_mode='compensated'))
    return load(d/'manifest.json')
def run(d,i,threads=2,scratch=None,max_blocks=None):p.run(NS(directory=d,index=i,threads=threads,scratch=scratch,max_blocks=max_blocks))
def scientific(doc):return [{k:r[k]for k in('uid','rep','graph','begin','end','total','values','quad','mp','max_abs')}for r in doc['native']['rows']]
def status_code(d):
    with contextlib.redirect_stdout(io.StringIO()):
        try:p.status(NS(directory=d,all=False,json=False,exclude=None));return 0
        except SystemExit as e:return e.code

def run_mode(root,mode):
    # The 'none' campaign lives in a directory with URI-reserved characters (A-URI): SQLite opens must not parse it.
    d=root/(mode if mode=='frozen'else f'{mode} #?%41 dir');m=plan(d,mode);assert [j['id']for j in m['jobs']]==list(range(len(m['jobs'])))and m['dimension']==3
    try:p.merge_group(d,m,'a_L3')
    except FileNotFoundError:pass
    else:raise AssertionError('missing checkpoint accepted')
    # A-M1: every native call uses a verified job-private copy, removed afterwards.
    scratch=root/f'scratch_{mode}';scratch.mkdir();calls=[]
    def spy(cmd,*a,**k):calls.append((cmd[0],digest(Path(cmd[0])),cmd[3]));return REAL_RUN(cmd,*a,**k)
    with mock.patch.object(p.subprocess,'run',side_effect=spy):run(d,0,scratch=str(scratch))
    assert calls and all(c.startswith(str(scratch/'c6_d3_runtime_'))and h==m['executable_sha256']and net.startswith(str(scratch/'c6_d3_runtime_'))for c,h,net in calls) and not any(scratch.iterdir())
    # Forced native failure: failure log, no checkpoint, runtime removed.
    j=m['jobs'][-1];g=d/'groups'/j['group']
    def fail(cmd,*a,**k):k['stdout'].write('forced failure\n');k['stdout'].flush();raise subprocess.CalledProcessError(2,cmd)
    with mock.patch.object(p.subprocess,'run',side_effect=fail):
        try:run(d,j['id'],scratch=str(scratch))
        except RuntimeError as e:assert 'forced failure'in str(e)
        else:raise AssertionError('native failure not reported')
    assert list((g/'logs').glob('*.failure.*.log'))and not list((g/'checkpoints').glob('*.json'))and not any(scratch.iterdir())
    for i in range(len(m['jobs'])):run(d,i)
    before={str(f):digest(f)for f in d.rglob('checkpoints/*.json')};run(d,0,threads=4);assert before=={str(f):digest(f)for f in d.rglob('checkpoints/*.json')}
    if mode=='none':
        # Node-local staging (tools/stage_runtime.py), run from a separate interpreter with no reference/ tree.
        staged=root/'staged';REAL_RUN([sys.executable,str(ROOT/'tools/stage_runtime.py'),str(staged)],check=True,capture_output=True)
        REAL_RUN([sys.executable,'-B',str(staged/'tools/production.py'),'run',str(d),'--index','0','--threads','1'],check=True,capture_output=True)
        assert before=={str(f):digest(f)for f in d.rglob('checkpoints/*.json')}
    # Restart after deleting a committed checkpoint, with a different thread count: identical scientific fields.
    victim=sorted((d/'groups/a_L6/checkpoints').glob('*.json'))[0];old=load(victim);victim.unlink()
    assert status_code(d)==1
    jid=next(j['id']for j in m['jobs']if j['group']=='a_L6'and j['shard']==int(victim.name[1:7]));run(d,jid,threads=1)
    assert scientific(load(victim))==scientific(old)and status_code(d)==0
    # Concurrent duplicate executions of one index: both succeed; the committed science equals a single run.
    victims=sorted((d/'groups/a_L5/checkpoints').glob('*.json'));olds={v:load(v)for v in victims}
    for v in victims:v.unlink()
    jid5=next(j['id']for j in m['jobs']if j['group']=='a_L5'and j['shard']==0)
    with concurrent.futures.ThreadPoolExecutor(2)as ex:list(ex.map(lambda t:run(d,jid5,threads=t),(1,2)))
    assert all(scientific(load(v))==scientific(olds[v])for v in victims)
    # Corruption, identity and runtime-digest tampering (payload hash recomputed where it is consistent).
    gr=d/'groups/a_L3';cfg=load(gr/'config.json');mh=digest(d/'manifest.json');db=p.dbopen(gr/'tasks.sqlite',True);block=list(p.rows_for(db,0))[:m['checkpoint_tasks']];db.close()
    cp=load(gr/'checkpoints/s000000_p000000.json');p.validate_checkpoint(cp,block,cfg,m,mh)
    bad=copy.deepcopy(cp);bad['native']['rows'][0]['values'][0]='1.23456'
    bad3=copy.deepcopy(cp);bad3['runtime']['executable_sha256']='0'*64
    bad5=copy.deepcopy(cp);bad5['runtime']['net_sha256']='2'*64
    bad4=copy.deepcopy(cp);bad4['manifest_sha256']='1'*64
    bad6=copy.deepcopy(cp);bad6['native']['dimension']=2;bad6['payload_sha256']=object_hash(bad6['native'])      # rehashed d=2 payload
    bad7=copy.deepcopy(cp);bad7['native']['rows'][0]['end']+=1;bad7['payload_sha256']=object_hash(bad7['native'])  # rehashed wrong interval
    for b,needle in ((bad,'payload corruption'),(bad3,'different executable'),(bad4,'identity mismatch'),(bad5,'different Sobol net'),(bad6,'metadata mismatch: dimension'),(bad7,'wrong task coordinates')):
        try:p.validate_checkpoint(b,block,cfg,m,mh)
        except ValueError as e:assert needle in str(e),e
        else:raise AssertionError('tampered checkpoint accepted: '+needle)
    # Merge one group, then all (resumable), assemble, rerun the complete merge.sh sequence (idempotent).
    with contextlib.redirect_stdout(io.StringIO()):
        p.merge(NS(directory=d,group='a_L3',scratch=None));p.merge(NS(directory=d,group=None,scratch=None))
        res=evaluate(d,32);import assemble;assemble.publish_result(d/'C6_result.json',res)
        assert res['dimension']==3 and res['shared_reference_standard_error']==0 and res['coefficients'][0]==1.5 and abs(res['coefficients'][1]+1/6)<1e-16
        snap={str(f):digest(f)for f in d.rglob('*')if f.is_file()};p.merge(NS(directory=d,group=None,scratch=None))
        assert assemble.publish_result(d/'C6_result.json',evaluate(d,32)).startswith('identical')
    assert snap=={str(f):digest(f)for f in d.rglob('*')if f.is_file()}
    # A rewritten merged covariance input, even with a new self-hash, is caught by the graph-replicate file check.
    target=d/'groups/a_L3/merged.json';raw=target.read_bytes();x=json.loads(raw);x['graph_replicates_sha256']='0'*64
    x['payload_sha256']=object_hash({k:v for k,v in x.items()if k!='payload_sha256'});target.write_text(json.dumps(x))
    try:
        try:evaluate(d,0)
        except ValueError as e:assert 'Checksum mismatch'in str(e),e
        else:raise AssertionError('corrupt merged.json accepted')
    finally:target.write_bytes(raw)
    # Chunked (merged) versus one unchunked native run of every stratum; every stratum, primitives included, is sampled.
    maxerr=0;primitives=set()
    for gg in m['groups']:
        base=d/'groups'/gg['name'];c=load(base/'config.json');merged=load(base/'merged.json');rows=[]
        for b in range(c['replicates']):
            for gi,n in sorted(c['counts'].items(),key=lambda x:int(x[0])):
                assert n>0;rows.append((len(rows),b,int(gi),0,n,n))
                if c['L']==6 and int(gi)in p.PIDS:primitives.add(int(gi))
        tf=root/f'unchunked_{mode}_{gg["name"]}.txt';tf.write_text(f'C6TASKS3D1 {c["L"]} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));o=root/f'unchunked_{mode}_{gg["name"]}.json'
        cmd=[ROOT/'bin/c6_integrate',ROOT/'inputs/graphs',ROOT/'inputs/gamma_d3.txt',base/'sobol.bin',tf,o,c['seed'],c['layout'],c['rate'],2,c['sum_mode'],ROOT/'inputs'/c['grid']if c['grid']else'-']
        REAL_RUN(list(map(str,cmd)),check=True,capture_output=True);n=load(o);tot=np.zeros_like(np.array(merged['batches']),dtype=np.longdouble)
        for r in n['rows']:tot[r['rep']]+=np.array(r['values'],np.longdouble)
        a=np.array(merged['batches'],np.longdouble);maxerr=max(maxerr,float(np.max(abs(a-tot)/np.maximum(1,abs(tot)))))
    assert maxerr<1e-12,maxerr
    assert primitives==p.PIDS,primitives
    return d,res,{'directory_name':d.name,'groups':len(m['groups']),'jobs':len(m['jobs']),'full_coverage':True,'private_runtime_native_calls':len(calls),'forced_failure_logged':True,'restart_after_deleted_checkpoint_identical':True,
                  'concurrent_duplicates_identical':True,'tampering_rejected':['payload','runtime executable digest','manifest identity','runtime Sobol net digest','rehashed d=2 payload','rehashed wrong interval','merged file with consistent self-hash'],
                  'merge_resumable_and_assembly_idempotent':True,'all_ten_primitive_strata_recomputed':True,'node_local_staging_resume':mode=='none','max_normalized_chunked_vs_unchunked_jet':maxerr,
                  'shared_reference_standard_error':res['shared_reference_standard_error'],'smoke_points_only':True,'not_an_accepted_new_C6_value':True}

def run_all(root):
    reports={};results={};dirs={}
    for mode in ('none','frozen'):dirs[mode],results[mode],reports[mode]=run_mode(root,mode)
    # Foreign-plan checkpoint: a checkpoint of another plan is rejected, never merged.
    other=root/'other';m2=plan(other,'none',seed=82819400);run(other,0)
    target=dirs['none']/'groups/a_L3/checkpoints/s000000_p000000.json';keep=target.read_bytes();target.unlink();shutil.copy2(other/'groups/a_L3/checkpoints/s000000_p000000.json',target)
    try:run(dirs['none'],0)
    except ValueError as e:assert 'identity mismatch'in str(e)
    else:raise AssertionError('foreign checkpoint accepted')
    finally:target.unlink();target.write_bytes(keep)
    # Interrupted (--max-blocks 1 per call) versus uninterrupted execution of the same plan: identical merged results.
    x,y=root/'x',root/'y';mx=plan(x,'none',seed=5550001);my=plan(y,'none',seed=5550001)
    for i in range(len(mx['jobs'])):run(x,i)
    for i in range(len(my['jobs'])):
        while True:
            n=len(list((y/'groups'/my['jobs'][i]['group']/'checkpoints').glob(f's{my["jobs"][i]["shard"]:06d}_*.json')))if(y/'groups'/my['jobs'][i]['group']/'checkpoints').exists()else 0
            run(y,i,max_blocks=1);n2=len(list((y/'groups'/my['jobs'][i]['group']/'checkpoints').glob(f's{my["jobs"][i]["shard"]:06d}_*.json')))
            if n2==n:break
    with contextlib.redirect_stdout(io.StringIO()):p.merge(NS(directory=x,group=None,scratch=None));p.merge(NS(directory=y,group=None,scratch=None))
    for g in mx['groups']:
        a,b=load(x/'groups'/g['name']/'merged.json'),load(y/'groups'/g['name']/'merged.json')
        assert a['batches']==b['batches']and digest(x/'groups'/g['name']/'graph_replicates.csv')==digest(y/'groups'/g['name']/'graph_replicates.csv'),g
    return {'status':'passed','grids':reports,'foreign_plan_checkpoint_rejected':True,'interrupted_equals_uninterrupted':True,
            'scope':'Small complete pipeline tests only. These noisy smoke results are not accepted physical estimates.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,help='optional record (never the shipped benchmarks/ evidence)');a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='c6_workflow_')as td:
        log=io.StringIO()
        with contextlib.redirect_stdout(log):x=run_all(Path(td))
    if a.output:dump(a.output,x)
    print(json.dumps(x,indent=2))
