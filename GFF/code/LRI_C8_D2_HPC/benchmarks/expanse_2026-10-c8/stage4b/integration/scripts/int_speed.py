#!/usr/bin/env python3
"""Stage-4b integration, J-OPT speed gate (PLAN A-PERF-2): every cumulative binary on ONE exclusive node, interleaved,
--repeats runs each, medians, on the L8 sweep sample. Run from the package root of the export that holds this script
(its tests/validate.py defines the sample and stages the graphs from that export's pinned L8 packs).

  int_speed.py --exe B0=PATH --exe B1=PATH ... --step R5a=B0:B1 --step R3a=B1:B2 ... --cost-model FILE
               --output DIR --scratch DIR [--repeats 3] [--shape 16x8] [--block-tasks 256]
               [--expect B0=SHA256] [--ipc NAME,NAME --perf perf --ipc-threads 64]

Workload (fixed before any run; the same for every binary and repeat):
- The L8 sweep sample of A-RPL-7 (tests/validate.py l8self_sample: free 100 heaviest + 1,500 random, power 100 heaviest
  + 300 random), 2 replicates x 512 points per graph, the gmp backend, the nets of G-L8SELF (validate.make_net with the
  same seeds), seed 7738251, layout 0, rate .8, compensated sums: the rows are G-L8SELF's rows.
- The sweep's execution shape on Expanse: --shape N x T lanes (default 16 x 8, the R5b default and P4's best), each a
  NUMA-aligned set of T physical cores (tools/benchkit.partition), the worker at T threads with OMP_PROC_BIND=close,
  OMP_PLACES=cores. The 2,000 graphs are split over the lanes by deterministic LPT on the J-SWEEP-1 cost model
  (campaign a seconds per point x 1,024 points); a graph's two replicates stay in one lane; each lane runs its free
  graphs and then its power graphs as native blocks of at most --block-tasks tasks (production's checkpoint_tasks
  max(16 x T, 256) = 256 at T = 8), heaviest first. The lane assignment is identical for every run, so lane-to-socket
  placement cannot bias a comparison.
- Run order: repeat r runs the binaries in the --exe order rotated by r x ceil(k/repeats) positions, so each binary
  takes early, middle and late slots.

Metrics (pre-registered; the gate uses the first):
- lane_thread_seconds: T x the sum over every native block of its wall time (process start to exit: start-up, graph
  loading, integration, output). This is the node time the sample occupies at perfect lane packing, independent of the
  end-of-run tail; per sector as well.
- node_wall: first lane start to last lane end (reported, not gated: dominated by the heaviest lane).
- load_share: sum of the worker's load_seconds over the sum of block walls; busy_fraction: sum of task seconds over
  (cores x node_wall); openmp_efficiency of the integration phase.
- Speedup of a step from:to = median(from) / median(to) of lane_thread_seconds (total and per sector). A step meets
  A-PERF-2's bar when the total speedup is >= 1.03.
Exactness: the order-independent digest of every row's scientific fields (tools/benchkit.rows_digest) must be the same
for every binary and every repeat; otherwise exit 1.

--ipc A,B (the R3c rule): perf stat -x, -e cycles,instructions,task-clock with OMP_WAIT_POLICY=passive (as P2) of
binary A on socket 0 and binary B on socket 1 at --ipc-threads threads, concurrently, on the frozen heavy_free_L8
fixture block (benchmarks/fixtures8; 256 tasks x 16,384 points).
The record goes to DIR/int_speed.json; staged graphs and native outputs stay on --scratch (node-local).
"""
from __future__ import annotations
import argparse,concurrent.futures,json,math,os,shutil,statistics,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import benchkit as bk
import validate as V
from common import digest,load

T_SAMPLE_POINTS=512;REPS=2

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def kv(items,what):
    out={}
    for s in items or[]:
        k,sep,v=s.partition('=')
        if not sep or not k or not v:raise SystemExit(f'{what} {s!r}: expected NAME=VALUE')
        if k in out:raise SystemExit(f'{what} {k} given twice')
        out[k]=v
    return out

def build_lanes(a,cm,sample,lanes):
    """Per lane: [(sector, [task rows])] blocks; the LPT shares and their predicted cost."""
    spp=cm['seconds_per_point'];items=[];missing=[]
    for sector,ids in sample.items():
        for g in ids:
            k=f'a:{sector}:8:{g}'
            if k not in spp:missing.append(k);continue
            items.append((spp[k]*REPS*T_SAMPLE_POINTS,(sector,g),None))
    if missing:raise SystemExit(f'the cost model has no entry for {len(missing)} sample graphs, e.g. {missing[:3]}')
    shares=bk.lpt_shares(items,len(lanes));uid={}
    for sector in ('free','power'):
        for r in range(REPS):
            for g in sorted(sample[sector]):uid[(sector,r,g)]=len(uid)
    gpb=max(1,a.block_tasks//REPS);plan=[]
    for share in shares:
        blocks=[]
        for sector in ('free','power'):
            gs=[it[1][1]for it in sorted((it for it in share if it[1][0]==sector),key=lambda x:(-x[0],x[1]))]
            for i in range(0,len(gs),gpb):
                rows=[(uid[(sector,r,g)],r,g,0,T_SAMPLE_POINTS,T_SAMPLE_POINTS)for g in gs[i:i+gpb]for r in range(REPS)]
                blocks.append((sector,rows))
        plan.append(blocks)
    return plan,[sum(it[0]for it in s)for s in shares]

def run_lane(exe,lane,cpus,blocks,roots,nets,T,tag,scratch,pin=True):
    recs=[];t_start=time.perf_counter();digs=[]
    for j,(sector,rows) in enumerate(blocks):
        tf=scratch/'tasks'/f'lane{lane}.b{j}.tasks'
        out=scratch/'out'/f'{tag}.lane{lane}.b{j}.json';lg=scratch/'out'/f'{tag}.lane{lane}.b{j}.log'
        out.unlink(missing_ok=True)
        cmd=bk.native_cmd(exe,roots[sector],V.GAMMA8,nets[sector],tf,out,V.SEED,0,.8,T,'compensated')
        t0=time.perf_counter()
        with open(lg,'w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=bk.omp_env(T),preexec_fn=bk.pinner(cpus,pin),timeout=3600)
        wall=time.perf_counter()-t0
        if cp.returncode:raise RuntimeError(f'{tag} lane {lane} block {j}: exit {cp.returncode}: {lg.read_text()[-1500:]}')
        if not out.is_file():raise RuntimeError(f'{tag} lane {lane} block {j}: no output')
        nat=load(out);s=bk.native_summary(nat,T)
        if s['tasks']!=len(rows):raise RuntimeError(f'{tag} lane {lane} block {j}: {s["tasks"]} rows for {len(rows)} tasks')
        digs+=bk.rows_digest(nat['rows'],sector)
        recs.append({'sector':sector,'tasks':len(rows),'wall_seconds':wall,'t_start':t0-t_start,**{k:s[k]for k in ('points','quad','mp','task_seconds','load_seconds','integration_seconds','openmp_efficiency','max_rss_kb')}})
        out.unlink();lg.unlink()
    return {'lane':lane,'cpus':[min(cpus),max(cpus)],'wall_seconds':time.perf_counter()-t_start,'blocks':recs},digs

def one_run(a,name,exe,r,plan,cpusets,roots,nets,T,scratch):
    tag=f'{name}.r{r}';t0=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan))as pool:
        futs=[pool.submit(run_lane,exe,k,cpusets[k],plan[k],roots,nets,T,tag,scratch,a.pin)for k in range(len(plan))]
        res=[f.result()for f in futs]
    node_wall=time.perf_counter()-t0
    lanes=[x[0]for x in res];digs=[d for x in res for d in x[1]];blocks=[b for l in lanes for b in l['blocks']]
    rec={'binary':name,'repeat':r,'node_wall_seconds':node_wall,'lanes':lanes,'rows':len(digs),'rows_digest':bk.combined_digest(digs),
         'lane_thread_seconds':T*math.fsum(b['wall_seconds']for b in blocks),
         'per_sector':{},'quad':sum(b['quad']for b in blocks),'mp':sum(b['mp']for b in blocks)}
    for sector in ('free','power'):
        bs=[b for b in blocks if b['sector']==sector]
        rec['per_sector'][sector]={'lane_thread_seconds':T*math.fsum(b['wall_seconds']for b in bs),'blocks':len(bs),'tasks':sum(b['tasks']for b in bs),
                                   'load_seconds':math.fsum(b['load_seconds']for b in bs),'integration_seconds':math.fsum(b['integration_seconds']for b in bs),
                                   'task_seconds':math.fsum(b['task_seconds']for b in bs),'quad':sum(b['quad']for b in bs),'mp':sum(b['mp']for b in bs)}
    wall=math.fsum(b['wall_seconds']for b in blocks);ts=math.fsum(b['task_seconds']for b in blocks);integ=math.fsum(b['integration_seconds']for b in blocks)
    rec['load_share']=math.fsum(b['load_seconds']for b in blocks)/wall
    rec['busy_fraction']=ts/(len(plan)*T*node_wall)
    rec['openmp_efficiency']=ts/(T*integ)if integ else None
    rec['max_rss_kb_per_block']=max((b['max_rss_kb']or 0)for b in blocks)
    return rec

def ipc_phase(a,exes,scratch):
    names=a.ipc.split(',')
    if len(names)!=2 or any(n not in exes for n in names):raise SystemExit('--ipc A,B: two names given with --exe')
    m=bk.load_fixtures();I=m['_inputs'];inv=load(I.where('inventory.json'));b=bk.block_of(m,'heavy_free_L8');g=scratch/'ipc_graphs'
    b['staging']=bk.stage_graphs(I,inv,b['sector'],b['L'],b['graphs'],g);n=m['native']
    sockets=bk.partition(bk.host_cores(),2,a.ipc_threads)
    def one(name,cpus):
        st=scratch/f'ipc.{name}.perfstat.csv';o=scratch/f'ipc.{name}.json';lg=scratch/f'ipc.{name}.log'
        cmd=[a.perf,'stat','-x,','-o',str(st),'-e','cycles,instructions,task-clock','--',
             *bk.native_cmd(exes[name],g,I.where(bk.GAMMA),b['net_path'],b['tasks_path'],o,b['native_seed'],n['layout'],n['rate'],a.ipc_threads,n['sum_mode'])]
        t0=time.perf_counter()
        with open(lg,'w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=bk.omp_env(a.ipc_threads,wait_policy='passive'),preexec_fn=bk.pinner(cpus),timeout=3600)
        wall=time.perf_counter()-t0
        if cp.returncode:raise RuntimeError(f'ipc {name}: exit {cp.returncode}: {lg.read_text()[-1500:]}')
        nat=load(o);txt=st.read_text();shutil.copy(st,Path(a.output)/st.name);ps=bk.parse_perf_stat_csv(txt)
        return {'binary':name,'sha256':digest(Path(exes[name])),'cpus':[min(cpus),max(cpus)],'threads':a.ipc_threads,'wall_seconds':wall,
                'integration_seconds':nat['integration_seconds'],'rows_digest':bk.combined_digest(bk.rows_digest(nat['rows'])),
                'ipc':ps['derived']['ipc'],'multiplexed':ps['multiplexed'],'perf_stat':ps}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        res=list(pool.map(lambda x:one(*x),zip(names,sockets)))
    return {'block':'heavy_free_L8','staging':b['staging'],'runs':res,'rows_identical':len({x['rows_digest']for x in res})==1,
            'rule':'R3c is attempted only if the IPC of the binary128 tier binary is below 1.5 (PLAN Performance plan; Stage-4a DECISIONS)'}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--exe',action='append',required=True);p.add_argument('--step',action='append',default=[]);p.add_argument('--expect',action='append',default=[])
    p.add_argument('--cost-model',required=True);p.add_argument('--output',required=True);p.add_argument('--scratch',required=True)
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--shape',default='16x8');p.add_argument('--block-tasks',type=int,default=256)
    p.add_argument('--ipc');p.add_argument('--perf',default='perf');p.add_argument('--ipc-threads',type=int,default=64)
    p.add_argument('--smoke-sample',type=int,help='SMOKE ONLY (never a measurement): the first n graphs of each sector')
    p.add_argument('--fake-topology',help='SMOKE ONLY: SxNxC topology (tools/benchkit.fake_cores); implies --no-pin')
    a=p.parse_args();t0=time.time();a.pin=not a.fake_topology
    exes={k:str(Path(v).resolve())for k,v in kv(a.exe,'--exe').items()};names=list(exes)
    steps={k:tuple(v.split(':'))for k,v in kv(a.step,'--step').items()}
    for k,(f,t) in steps.items():
        if f not in exes or t not in exes:raise SystemExit(f'--step {k}: {f} or {t} is not an --exe name')
    sha={k:digest(Path(v))for k,v in exes.items()}
    for k,v in kv(a.expect,'--expect').items():
        if not sha.get(k,'').startswith(v):raise SystemExit(f'{k}: sha256 {sha.get(k)} does not start with the expected {v}')
    out=Path(a.output);out.mkdir(parents=True);scratch=Path(tempfile.mkdtemp(prefix='c8d2_int_speed_',dir=a.scratch))
    (scratch/'tasks').mkdir();(scratch/'out').mkdir()
    (N,T),=bk.parse_shapes(a.shape);cpusets=bk.partition(bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores(),N,T)
    cm=load(Path(a.cost_model));sample=V.l8self_sample()
    if a.smoke_sample:sample={k:v[:a.smoke_sample]for k,v in sample.items()}
    rec={'schema':'c8-d2-stage4b-int-speed-1','smoke':bool(a.smoke_sample or a.fake_topology),'host':os.uname().nodename,'shape':f'{N}x{T}','cpusets':[[min(c),max(c)]for c in cpusets],
         'repeats':a.repeats,'block_tasks':a.block_tasks,'workload':{'sample':'tests/validate.py l8self_sample (A-RPL-7 L8 sweep sample)','graphs':{k:len(v)for k,v in sample.items()},
         'replicates':REPS,'points':T_SAMPLE_POINTS,'backend':'gmp','seed':V.SEED,'layout':0,'rate':.8,'sum_mode':'compensated'},
         'cost_model':{'path':a.cost_model,'sha256':digest(Path(a.cost_model)),'executable_sha256':cm.get('executable_sha256')},
         'binaries':{k:{'path':exes[k],'sha256':sha[k]}for k in names},'steps':{k:{'from':f,'to':t}for k,(f,t) in steps.items()},
         'identity':bk.identity({k:Path(v)for k,v in exes.items()},perf=a.perf)}
    try:
        roots={};nets={};t1=time.perf_counter()
        for sector,ids in sample.items():
            roots[sector]=V.stage(scratch/'graphs'/sector,sector,8,ids);nets[sector]=scratch/f'self_{sector}.bin'
            rec.setdefault('nets',{})[sector]=V.make_net(nets[sector],2,31,60,7702+(1 if sector=='power'else 0),T_SAMPLE_POINTS)
        rec['staging_seconds']=time.perf_counter()-t1;log(f'staged {sum(len(v)for v in sample.values())} graphs in {rec["staging_seconds"]:.0f} s')
        plan,pred=build_lanes(a,cm,sample,cpusets)
        for k,blocks in enumerate(plan):
            for j,(sector,rows) in enumerate(blocks):(scratch/'tasks'/f'lane{k}.b{j}.tasks').write_text(V.tasks_text(8,8,rows))
        rec['lane_plan']=[{'lane':k,'predicted_cost_model_seconds':pred[k],'blocks':[{'sector':s,'tasks':len(rows)}for s,rows in plan[k]]}for k in range(len(plan))]
        log(f'{len(plan)} lanes, predicted cost-model seconds per lane {min(pred):.1f}-{max(pred):.1f}, blocks per lane {min(len(b)for b in plan)}-{max(len(b)for b in plan)}')
        runs=[];rot=math.ceil(len(names)/a.repeats)
        for r in range(a.repeats):
            order=names[(r*rot)%len(names):]+names[:(r*rot)%len(names)]
            for name in order:
                x=one_run(a,name,exes[name],r,plan,cpusets,roots,nets,T,scratch);runs.append(x)
                log(f'{name} r{r}: lane-thread s {x["lane_thread_seconds"]:.1f} (free {x["per_sector"]["free"]["lane_thread_seconds"]:.1f}, power {x["per_sector"]["power"]["lane_thread_seconds"]:.1f}), '
                    f'node wall {x["node_wall_seconds"]:.1f} s, load share {x["load_share"]:.4f}, busy {x["busy_fraction"]:.3f}, digest {x["rows_digest"][:12]}')
        rec['runs']=runs
        med=lambda f:{k:statistics.median(f(x)for x in runs if x['binary']==k)for k in names}
        rec['medians']={'lane_thread_seconds':med(lambda x:x['lane_thread_seconds']),
                        'free_lane_thread_seconds':med(lambda x:x['per_sector']['free']['lane_thread_seconds']),
                        'power_lane_thread_seconds':med(lambda x:x['per_sector']['power']['lane_thread_seconds']),
                        'node_wall_seconds':med(lambda x:x['node_wall_seconds']),'load_share':med(lambda x:x['load_share']),
                        'busy_fraction':med(lambda x:x['busy_fraction']),'openmp_efficiency':med(lambda x:x['openmp_efficiency'])}
        M=rec['medians'];rec['speedups']={}
        for k,(f,t) in steps.items():
            s={m:M[m][f]/M[m][t]for m in ('lane_thread_seconds','free_lane_thread_seconds','power_lane_thread_seconds','node_wall_seconds')}
            s['meets_3pct_bar']=s['lane_thread_seconds']>=1.03;rec['speedups'][k]={'from':f,'to':t,**s}
        rec['cumulative_vs_first']={k:M['lane_thread_seconds'][names[0]]/M['lane_thread_seconds'][k]for k in names}
        rec['rows_identical']=len({x['rows_digest']for x in runs})==1;rec['rows_digest']=runs[0]['rows_digest']
        log('speedups: '+json.dumps({k:round(v['lane_thread_seconds'],4)for k,v in rec['speedups'].items()})+f'; rows identical {rec["rows_identical"]}')
        if a.ipc:rec['ipc']=ipc_phase(a,exes,scratch);log('IPC: '+json.dumps({x['binary']:x['ipc']for x in rec['ipc']['runs']}))
    finally:
        rec['wall_seconds']=round(time.time()-t0,1);(out/'int_speed.json').write_text(json.dumps(rec,indent=1)+'\n')
        shutil.rmtree(scratch,ignore_errors=True)
    ok=rec.get('rows_identical')and(not a.ipc or rec['ipc']['rows_identical'])
    print(json.dumps({'speedups':rec.get('speedups'),'rows_identical':rec.get('rows_identical'),'ipc':{x['binary']:x['ipc']for x in rec.get('ipc',{}).get('runs',[])}},indent=1))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
