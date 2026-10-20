#!/usr/bin/env python3
"""Merge scale (PLAN component F, A-ORC-6, R06): peak RSS, rows per second and wall time of `production.py merge` on a
synthetic group of about --rows task rows (10^6 on a cluster, J-VAL-3; 2*10^4 on the Mac), and the many-shard case.

Ported from C62d's tests/merge_scale.py (LRI_C8_D2_HPC) to C8(3). Runs in a scratch package (tests/c8pkg.py: the fake
worker, synthetic complete inputs with 2,441 free L7 graphs). The group is a_free_L7 of a test-only validation plan on
the bootstrap basis with one-point tasks (--plan-role validation --bootstrap-chunk 1, D.5), 2 replicates and the
smallest power-of-two point count giving >= --rows rows; only that group's indices are run and merged.
  * scale: `merge --group a_free_L7 --jobs J` in a fresh process and the serial reference merge in another; the four
    merged files byte-identical; the peak RSS of every merge process (RUSAGE_CHILDREN of a wrapper) <= 1 GB; the
    phase-1 and phase-2 rows per second printed by the merge, recorded for the planner's projection
    (production.py MERGE_PHASE1_ROWS_PER_S / MERGE_PHASE2_ROWS_PER_S, docs/PERFORMANCE.md).
  * many shards: the same group in --many-shards (500) shards (one point per replicate and graph); merged under RLIMIT_NOFILE = 48
    (fan-in reduced to 16) and with --fan-in 2, each byte-identical to the serial merge, with ceil(log_F 500) passes
    (3 and 9); RLIMIT_NOFILE = 33 (F < 2) refused. An EMFILE would fail the merge, so a pass also shows that the open
    descriptors stayed within the limit.
  * scratch (D.13, Stage 3a repair round 2): the scale group merged in one process with fan-in 2 (16 shard runs, 4
    passes) under spies: the scratch directory never holds more than two copies of the group's raw rows, one copy when
    the final pass starts, and none of the group's runs or tables after phase 2; byte-identical to the serial merge.
  * memory scaling (checkpoint review T-01/O02, the plan's bound "one block plus F rows"): the same group at a fixed
    checkpoint size (--scaling-checkpoint-tasks, 256) and a fixed fan-in (--scaling-fan-in, 16), at two point counts
    (--scaling-points, 4 and 32: 8x the rows per shard) in a single shard and in 4 shards (--scaling-shards 1,4). Each
    is merged in a fresh process (--jobs 1, so phase 1 runs in the measured process itself), again under tracemalloc,
    and by the serial reference; the four files byte-identical. From the small to the large one of each shard count
    the peak of the Python heap (tracemalloc: the live rows) may grow by at most --scaling-max-traced-growth-mb (2, on
    every platform: the exact gate) and the peak RSS by at most --scaling-max-growth-mb, whose default is per platform
    (checkpoint review, test robustness; RSS_GROWTH_MB): 16 MB on Linux and every platform but macOS (the strict bound;
    measured 1.4 MB at 4 -> 32 points and 0.5 MB at 16 -> 128 on a personal desktop), 48 MB on macOS, whose allocator keeps
    freed regions resident (measured 4.4 to 12.4 MB in one shard with the Python heap flat). A phase 1 that keeps a
    shard's rows grows by about 530 bytes per extra row of the shard (601b102 on a personal desktop at 16 -> 128 points: 278 MB
    of heap, 308 MB of RSS in one shard); scaled to 4 -> 32 points that is about 70 MB in one shard, above both bounds,
    and about 17 MB in four shards, which the tracemalloc gate catches on every platform. The record states the bound,
    its platform and its source.
Usage: python3 -B tests/merge_scale.py [--rows 20000] [--jobs 4] [--shards 16] [--run-jobs 8] [--many-shards 500] [--skip-many-shards]
       [--skip-memory-scaling] [--scaling-points 4,32] [--scaling-shards 1,4] [--scaling-checkpoint-tasks 256] [--output FILE]"""
from __future__ import annotations
import argparse,concurrent.futures,json,math,os,re,resource,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path.insert(0,str(ROOT/'tests'))
import c8pkg  # noqa: E402
JOB_ID=os.environ.get('SLURM_JOB_ID')  # a plan above 10^6 tasks must run inside a job (production.py); kept for that step only
for k in list(os.environ):
    if k.startswith(('C7_','C8_','SLURM_','SBATCH_','SQUEUE_')):os.environ.pop(k)
FILES=('merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv','graph_promotions.csv')
GROUP='a_free_L7';L7_GRAPHS=2441
WRAP=r'''import json,resource,subprocess,sys,time
limit=int(sys.argv[1]);cmd=sys.argv[2:]
def pre():
    if limit:resource.setrlimit(resource.RLIMIT_NOFILE,(limit,resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
t=time.time();cp=subprocess.run(cmd,capture_output=True,text=True,preexec_fn=pre);w=time.time()-t
r=resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps({'code':cp.returncode,'wall':w,'maxrss':r.ru_maxrss,'stdout':cp.stdout[-4000:],'stderr':cp.stderr[-4000:]}))
'''
def rss_bytes(x:int)->int:return x if sys.platform=='darwin'else 1024*x
# The default peak-RSS growth bound of the memory-scaling gate, per platform (MB; see the docstring). Linux keeps the
# strict bound; macOS's allocator retains freed memory, so there the tracemalloc gate is the exact one.
RSS_GROWTH_MB={'darwin':48.};RSS_GROWTH_MB_STRICT=16.
def rss_growth_bound_mb(platform:str=sys.platform)->float:return RSS_GROWTH_MB.get(platform,RSS_GROWTH_MB_STRICT)

class Pkg:
    def __init__(self,td:Path):
        counts={s:dict(v)for s,v in c8pkg.DEFAULT_COUNTS.items()};counts['free'][7]=L7_GRAPHS
        self.td=td;self.pkg=c8pkg.make(td,counts=counts);self.env=c8pkg.env()
        self.wrap=td/'wrap.py';self.wrap.write_text(WRAP)
    def T(self,*args,check=True):
        env=dict(self.env,SLURM_JOB_ID=JOB_ID)if (JOB_ID and args[0]=='plan')else self.env
        cp=subprocess.run([PY,'-B',str(self.pkg/'tools/production.py'),*map(str,args)],capture_output=True,text=True,env=env)
        if check and cp.returncode:raise RuntimeError(f'production.py {args}: {cp.returncode}\n{cp.stderr[-2000:]}')
        return cp
    def wrapped(self,limit:int,*args)->dict:
        cp=subprocess.run([PY,'-B',str(self.wrap),str(limit),PY,'-B',str(self.pkg/'tools/production.py'),*map(str,args)],capture_output=True,text=True,env=self.env)
        return json.loads(cp.stdout)

TRACE=r'''import json,sys,tracemalloc
tracemalloc.start();sys.path.insert(0,sys.argv[1]+'/tools')
import production
production.main(sys.argv[2:])
print('TRACED '+json.dumps({'peak':tracemalloc.get_traced_memory()[1]}))
'''
def memory_scaling(X:Pkg,td:Path,a)->dict:
    """T-01/O02: the memory of `merge --jobs 1` (phase 1 in the measured process) at a fixed checkpoint size and fan-in
    for 8x more rows per shard, a single shard and several: the peak of the Python heap (tracemalloc, the live data;
    deterministic) and the peak RSS (with the allocator's own retention, which levels off at a few times one block)."""
    tr=td/'trace.py';tr.write_text(TRACE);pts=[int(x)for x in a.scaling_points.split(',')]
    bound=a.scaling_max_growth_mb if a.scaling_max_growth_mb is not None else rss_growth_bound_mb()
    out={'checkpoint_tasks':a.scaling_checkpoint_tasks,'fan_in':a.scaling_fan_in,'max_traced_growth_bytes':int(a.scaling_max_traced_growth_mb*2**20),
         'max_rss_growth_bytes':int(bound*2**20),'rss_bound':{'platform':sys.platform,'mb':bound,
         'source':'--scaling-max-growth-mb'if a.scaling_max_growth_mb is not None else f'platform default ({RSS_GROWTH_MB_STRICT:g} MB; macOS {RSS_GROWTH_MB["darwin"]:g} MB)'},
         'cases':{}};ok=True
    for shards in (int(x)for x in a.scaling_shards.split(',')):
        res={}
        for P in pts:
            d=td/f'mem_s{shards}_p{P}';info=campaign(X,d,P,shards,a.scaling_checkpoint_tasks,a.run_jobs,771200100+10*shards+P)
            par=copy(d,td/f'mem_s{shards}_p{P}_par');trc=copy(d,td/f'mem_s{shards}_p{P}_trace');ser=copy(d,td/f'mem_s{shards}_p{P}_ser')
            margs=('merge',par,'--group',GROUP,'--jobs',1,'--fan-in',a.scaling_fan_in,'--scratch',td)
            rp=X.wrapped(0,*margs);assert rp['code']==0,rp['stderr']
            cp=subprocess.run([PY,'-B',str(tr),str(X.pkg),'merge',str(trc),'--group',GROUP,'--jobs','1','--fan-in',str(a.scaling_fan_in),'--scratch',str(td)],
                              capture_output=True,text=True,env=X.env)
            assert cp.returncode==0,cp.stderr[-2000:]
            traced=json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('TRACED '))[7:])['peak']
            X.T('merge',ser,'--group',GROUP,'--serial','--scratch',td)
            res[P]=dict(rows=info['rows'],rows_per_shard=info['rows']/shards,blocks=info['blocks'],peak_rss_bytes=rss_bytes(rp['maxrss']),traced_peak_bytes=traced,
                        identical=merged_bytes(par)==merged_bytes(ser)==merged_bytes(trc),wall_seconds=rp['wall'])
            for q in (d,par,trc,ser):shutil.rmtree(q)
        lo,hi=res[min(pts)],res[max(pts)];g_rss=hi['peak_rss_bytes']-lo['peak_rss_bytes'];g_tr=hi['traced_peak_bytes']-lo['traced_peak_bytes']
        case=dict(points=res,rows_ratio=hi['rows']/lo['rows'],rows_per_shard_ratio=hi['rows_per_shard']/lo['rows_per_shard'],traced_growth_bytes=g_tr,
                  rss_growth_bytes=g_rss,rss_growth_bytes_per_extra_row=g_rss/max(1,hi['rows']-lo['rows']),
                  passed=all(r['identical']for r in res.values())and hi['rows_per_shard']>=4*lo['rows_per_shard']and g_tr<=out['max_traced_growth_bytes']
                         and g_rss<=out['max_rss_growth_bytes'])
        out['cases'][f'shards_{shards}']=case;ok=ok and case['passed']
        print(json.dumps({f'memory_scaling shards={shards}':case},indent=1),flush=True)
    out['passed']=ok;return out

SCRATCH=r'''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools')
import production as P
group=sys.argv[2];rec={'writes':[],'phase2':{}}
def size(d):return sum(f.stat().st_size for f in Path(d).iterdir()if f.is_file())
w0=P._write_run
def w(items,out):
    n=w0(items,out);rec['writes'].append(size(Path(out).parent));return n
p0=P._phase2
def p2(name,runs,work,F,changes,stats):
    e=rec['phase2'][name]={'runs':len(runs),'one_copy':sum(Path(r).stat().st_size for r in runs),'fan_in':F}
    r=p0(name,runs,work,F,changes,stats)
    e['left_after']=sorted(f.name for f in Path(work).iterdir()if f.name.startswith(name+'.'));e['passes']=r['passes'];return r
f0=P._final_pass
def fp(p,cfg,m,mh,stream,work,changes,stats):
    rec['phase2'][cfg['name']]['work_bytes_at_final_pass']=size(work);return f0(p,cfg,m,mh,stream,work,changes,stats)
P._write_run=w;P._phase2=p2;P._final_pass=fp
P.main(sys.argv[3:])
print('SCRATCH '+json.dumps(rec))
'''
def scratch_footprint(X:Pkg,d:Path,td:Path,F:int=2)->dict:
    """D.13 "scratch holds at most two copies of a group's raw rows" (Stage 3a repair round 2): the real merge
    (--jobs 1 --parse-jobs 1, in one process) of the scale campaign's group with fan-in F (16 shards, F = 2: 4 passes),
    with spies on production._write_run, _phase2 and _final_pass. The bytes in the merge's scratch directory after every
    run file written (the moment before a consumed batch is deleted) stay within 2 x one copy (the group's shard runs as
    phase 1 left them); when the final pass starts the directory holds one copy (the last level, every consumed level
    deleted; before the fix: one copy per pass); after phase 2 no run or table of the group is left; the merged files
    equal the serial merge's byte for byte."""
    sc=td/'scratch_spy.py';sc.write_text(SCRATCH);par=copy(d,td/'scratch_par');ser=copy(d,td/'scratch_ser')
    cp=subprocess.run([PY,'-B',str(sc),str(X.pkg),GROUP,'merge',str(par),'--group',GROUP,'--jobs','1','--parse-jobs','1','--fan-in',str(F),'--scratch',str(td)],
                      capture_output=True,text=True,env=X.env)
    assert cp.returncode==0,cp.stderr[-2000:]
    rec=json.loads(next(l for l in cp.stdout.splitlines()if l.startswith('SCRATCH '))[8:]);X.T('merge',ser,'--group',GROUP,'--serial','--scratch',td)
    e=rec['phase2'][GROUP];one=e['one_copy'];peak=max(rec['writes']);slack=4096
    out=dict(fan_in=F,shard_runs=e['runs'],passes=e['passes'],expected_passes=math.ceil(math.log(e['runs'])/math.log(F)-1e-12),one_copy_bytes=one,
             peak_bytes=peak,peak_copies=peak/one,final_pass_bytes=e['work_bytes_at_final_pass'],final_pass_copies=e['work_bytes_at_final_pass']/one,
             left_after_phase2=e['left_after'],identical=merged_bytes(par)==merged_bytes(ser))
    out['passed']=(out['identical']and out['passes']==out['expected_passes']>=3 and peak<=2*one+slack and e['work_bytes_at_final_pass']<=one+slack
                   and not e['left_after'])
    for q in (par,ser):shutil.rmtree(q)
    return out

def campaign(X:Pkg,d:Path,points:int,shards:int,ckpt:int,run_jobs:int,seed:int)->dict:
    t=time.time()
    scratch=X.td/'scratch';scratch.mkdir(exist_ok=True)
    X.T('plan',d,'--seed',seed,'--pilot','--test-only','--points',points,'--replicates',2,'--plan-role','validation','--bootstrap-chunk',1,'--shards',shards,
        '--threads',1,'--checkpoint-tasks',ckpt,'--scratch',scratch)
    tp=time.time()-t;m=json.loads((d/'manifest.json').read_text());jobs=[j for j in m['jobs']if j['group']==GROUP]
    t=time.time()
    with concurrent.futures.ThreadPoolExecutor(run_jobs)as ex:list(ex.map(lambda j:X.T('run',d,'--index',j['id'],'--threads',1,'--scratch',scratch),jobs))
    cfg=json.loads((d/'groups'/GROUP/'config.json').read_text())
    return dict(rows=cfg['tasks'],shards=len(jobs),plan_seconds=tp,run_seconds=time.time()-t,blocks=sum(j['blocks']for j in jobs))

def merged_bytes(d:Path)->dict:return {f:(d/'groups'/GROUP/f).read_bytes()for f in FILES}

def copy(d:Path,dst:Path)->Path:shutil.copytree(d,dst,ignore=shutil.ignore_patterns('merged.json',*FILES[1:]));return dst

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--rows',type=int,default=20000);ap.add_argument('--jobs',type=int,default=4)
    ap.add_argument('--shards',type=int,default=16);ap.add_argument('--run-jobs',type=int,default=8);ap.add_argument('--checkpoint-tasks',type=int,default=4096)
    ap.add_argument('--skip-many-shards',action='store_true');ap.add_argument('--many-shards',type=int,default=500,help='shards of the many-shard case (PLAN: 500)');ap.add_argument('--output',type=Path)
    ap.add_argument('--skip-memory-scaling',action='store_true');ap.add_argument('--scaling-points',default='4,32');ap.add_argument('--scaling-shards',default='1,4')
    ap.add_argument('--scaling-checkpoint-tasks',type=int,default=256);ap.add_argument('--scaling-fan-in',type=int,default=16)
    ap.add_argument('--scaling-max-traced-growth-mb',type=float,default=2.);ap.add_argument('--scaling-max-growth-mb',type=float,default=None,
                    help=f'peak-RSS growth bound (default per platform: {RSS_GROWTH_MB_STRICT:g} MB, macOS {RSS_GROWTH_MB["darwin"]:g} MB)');a=ap.parse_args()
    rec={'schema':'c8-d3-gate-1','gate':'A-ORC-6 merge_scale','rows_requested':a.rows,'python':sys.version.split()[0],'host':os.uname().nodename,'platform':sys.platform}
    with tempfile.TemporaryDirectory(prefix='c8d3_merge_scale_',dir=os.environ.get('TMPDIR'))as td:
        X=Pkg(Path(td));P=1<<max(0,math.ceil(math.log2(a.rows/(2*L7_GRAPHS))))
        d=Path(td)/'scale';info=campaign(X,d,P,a.shards,a.checkpoint_tasks,a.run_jobs,771200001);rec['scale']=dict(points=P,**info)
        par=copy(d,Path(td)/'scale_par');ser=copy(d,Path(td)/'scale_ser')
        rp=X.wrapped(0,'merge',par,'--group',GROUP,'--jobs',a.jobs,'--scratch',td);rs=X.wrapped(0,'merge',ser,'--group',GROUP,'--serial','--scratch',td)
        assert rp['code']==0 and rs['code']==0,(rp['stderr'],rs['stderr'])
        same=merged_bytes(par)==merged_bytes(ser)
        p1=re.search(r'merge phase 1: (\d+) rows of (\d+) shards in ([0-9.]+) s with (\d+) process\(es\) \((\d+) rows/s\)',rp['stdout'])
        p2=re.search(r'merge phase 2: (\d+) rows of (\d+) group\(s\) in ([0-9.]+) s \((\d+) rows/s\)',rp['stdout'])
        rec['scale'].update(parallel=dict(jobs=a.jobs,wall_seconds=rp['wall'],peak_rss_bytes=rss_bytes(rp['maxrss']),phase1_rows_per_s=int(p1.group(5)),
                                          phase1_rows_per_s_per_process=int(p1.group(5))/min(a.jobs,int(p1.group(2))),phase1_seconds=float(p1.group(3)),
                                          phase2_rows_per_s=int(p2.group(4)),phase2_seconds=float(p2.group(3))),
                            serial=dict(wall_seconds=rs['wall'],peak_rss_bytes=rss_bytes(rs['maxrss'])),byte_identical=same)
        ok=same and rec['scale']['parallel']['peak_rss_bytes']<=2**30 and rec['scale']['serial']['peak_rss_bytes']<=2**30 and info['rows']>=a.rows
        rec['scale']['passed']=ok
        print(json.dumps(rec['scale'],indent=1),flush=True)
        rec['scratch']=scratch_footprint(X,d,Path(td));ok=ok and rec['scratch']['passed'];print(json.dumps({'scratch':rec['scratch']},indent=1),flush=True)
        if not a.skip_many_shards:
            N=a.many_shards;m=Path(td)/'many';info=campaign(X,m,1,N,a.checkpoint_tasks,a.run_jobs,771200002);assert info['shards']==N,info
            ser=copy(m,Path(td)/'many_ser');X.T('merge',ser,'--group',GROUP,'--serial','--scratch',td);ref=merged_bytes(ser)
            out={}
            for name,limit,extra,F in (('rlimit48',48,(),16),('fanin2',0,('--fan-in',2),2)):
                dst=copy(m,Path(td)/f'many_{name}');r=X.wrapped(limit,'merge',dst,'--group',GROUP,'--jobs',a.jobs,'--scratch',td,*extra)
                passes=re.search(r'merged \((\d+) pass\(es\), fan-in (\d+)\)',r['stdout'])
                out[name]=dict(code=r['code'],identical=r['code']==0 and merged_bytes(dst)==ref,passes=int(passes.group(1))if passes else None,
                               fan_in=int(passes.group(2))if passes else None,expected_passes=math.ceil(math.log(N)/math.log(F)-1e-12),expected_fan_in=F,stderr=r['stderr'][-300:]if r['code']else'')
            r=X.wrapped(33,'merge',copy(m,Path(td)/'many_33'),'--group',GROUP,'--jobs',a.jobs,'--scratch',td)
            out['rlimit33']=dict(code=r['code'],refused=r['code']!=0 and 'fan-in'in r['stderr']and '< 2'in r['stderr'])
            mok=all(out[k]['identical']and out[k]['passes']==out[k]['expected_passes']and out[k]['fan_in']==out[k]['expected_fan_in']for k in ('rlimit48','fanin2'))and out['rlimit33']['refused']
            rec['many_shards']=dict(shards=N,rows=info['rows'],passed=mok,**out);print(json.dumps(rec['many_shards'],indent=1),flush=True);ok=ok and mok
        if not a.skip_memory_scaling:
            rec['memory_scaling']=memory_scaling(X,Path(td),a);ok=ok and rec['memory_scaling']['passed']
    rec['passed']=ok
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(f'merge_scale: {"passed"if ok else"FAILED"}');return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
