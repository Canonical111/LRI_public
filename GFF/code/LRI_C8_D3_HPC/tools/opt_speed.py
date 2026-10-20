#!/usr/bin/env python3
"""The A-PERF-2 speed gate of Stage 4b (PLAN "Performance plan", default-path optimizations: "each gated by A-PERF-2";
A-PERF-2: ">= 3% speedup (median of 3 runs, same node, L8 sweep sample), or is reverted"). Port to C8(3) of C62d's
integration speed script (LRI_C8_D2_HPC@14d7347, benchmarks/expanse_2026-10-c8/stage4b/integration/scripts/
int_speed.py), the d-independent design of its A-PERF-2 measurement, with per-binary lane shapes added (R5b compares
the old and the new default shape of one binary).

  opt_speed.py --exe B0=PATH --exe B1=PATH [...] --step NAME=FROM:TO [...] --output DIR --scratch DIR
               [--shape 16x8] [--shape-of NAME=NxT ...] [--repeats 3] [--block-tasks auto|N] [--expect NAME=SHA256PREFIX ...]
               [--cost-model cost_models/gmp_expanse_epyc7742_c8.json] [--mp-check on]
               [--inputs inputs] [--sample-sizes HEAVY,FREE,POWER] [--fake-topology SxNxC] [--no-pin]

Workload (fixed before any run; the same for every binary and repeat):
- The L8 sweep sample of A-RPL-8 (tests/validate.py l8self_sample: per sector the 100 costliest kernels plus a
  random.Random(81113) draw of 1,500 free and 300 power), 2 replicates x 512 points per kernel, the gmp backend, the
  net of G-L8SELF (validate.l8self_net, seed 81121), native seed validate.SEED, layout 0, rate .8, compensated sums,
  --mp-check on: the rows are G-L8SELF's gmp rows. The members are staged from the pinned packs and checked against
  their inventory sha256 (tools/benchkit.stage_graphs).
- The sweep's execution shape on Expanse: N x T lanes (--shape, default 16 x 8 = the R5b default and P4's best;
  --shape-of NAME=NxT gives one binary another shape), each a NUMA-aligned set of T physical cores
  (tools/benchkit.partition), the worker at T threads with OMP_PROC_BIND=close, OMP_PLACES=cores. The kernels are
  split over the lanes by deterministic LPT on the cost model (campaign a seconds per point x 1,024 points); a kernel's
  two replicates stay in one lane; each lane runs its free kernels and then its power kernels as native blocks of at
  most --block-tasks tasks (auto: production's checkpoint_tasks max(16 x T, 256) = 256 at T = 8 and 16), costliest
  first. A shape's lane plan is the same in every run.
- Run order: repeat r runs the binaries in the --exe order rotated by r x ceil(k/repeats) places, so each binary takes
  early, middle and late slots.

Metrics (fixed before the runs; the gate uses the first):
- lane_thread_seconds: T x the sum over every native block of its wall time (process start to exit: start-up, graph
  loading, integration, output), i.e. the core-seconds the sample occupies at perfect lane packing, independent of the
  end-of-run tail; also per sector.
- node_wall (first lane start to last lane end; reported, not gated), load_share (sum of the worker's load_seconds over
  the sum of block walls), busy_fraction (task seconds over cores x node wall), openmp_efficiency.
- Speedup of a step FROM:TO = median(FROM) / median(TO) of lane_thread_seconds (total and per sector); a step meets
  A-PERF-2's bar when the total speedup is >= 1.03. cumulative_vs_first gives every binary against the first --exe
  (the Stage-3 baseline in the J-OPT jobs).
Exactness: the order-independent digest of every row's scientific fields (tools/benchkit.rows_digest) must be the same
for every binary, shape and repeat; otherwise exit 1. The record goes to DIR/opt_speed.json; staged graphs and native
outputs stay on --scratch (node-local) and are removed.
Inputs: before anything is created, selected or run, the inputs folder is verified against its manifest by
prepare_inputs.verify (tools/benchkit.verified_inputs: every pinned file, inventory.json and gamma_d3_8.txt among them,
the Stage-2b chain, the vendored pins); the inventory is parsed from the bytes checked against its pin; a failure
exits 65. The record keeps the verified hashes ("inputs_verified": manifest, inventory, gamma, skipped packs, test-only
reasons).
Dry runs and tests: --fake-topology SxNxC --no-pin, --inputs (another inputs folder), --sample-sizes and inputs with a
test-only reason (inputs_mini's test_inputs marker, a skipped pack) mark the record "smoke": true (never a measurement).
"""
from __future__ import annotations
import argparse,concurrent.futures,json,math,os,shutil,statistics,subprocess,sys,tempfile,time
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'tests')]
import benchkit as bk  # noqa: E402
import validate as V  # noqa: E402  (tests/validate.py: the L8 sweep sample, its net and seed)
from common import ROOT,digest,load  # noqa: E402

POINTS=V.L8SELF_POINTS;REPS=2;RATE='.8';LAYOUT=0;BAR=1.03
DEFAULT_MODEL=ROOT/'cost_models'/'gmp_expanse_epyc7742_c8.json'

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def kv(items,what:str)->dict:
    out={}
    for s in items or[]:
        k,sep,v=s.partition('=')
        if not sep or not k or not v:raise SystemExit(f'{what} {s!r}: expected NAME=VALUE')
        if k in out:raise SystemExit(f'{what} {k} given twice')
        out[k]=v
    return out

def uids(sample:dict)->dict:
    """One task uid per (sector, replicate, kernel), independent of any lane plan (the rows' identity)."""
    u={}
    for sector in ('free','power'):
        for r in range(REPS):
            for g in sorted(sample[sector]):u[(sector,r,g)]=len(u)
    return u

def build_lanes(cm:dict,sample:dict,nlanes:int,T:int,block_tasks:int|None)->tuple[list,list]:
    """Per lane: [(sector, [task rows])] native blocks, and each lane's predicted cost-model seconds (LPT)."""
    spp=cm['seconds_per_point'];items=[];missing=[]
    for sector,ids in sample.items():
        for g in ids:
            k=f'a:{sector}:8:{g}'
            if k not in spp:missing.append(k);continue
            items.append((spp[k]*REPS*POINTS,(sector,g),None))
    if missing:raise SystemExit(f'the cost model has no entry for {len(missing)} sample kernels, e.g. {missing[:3]}')
    shares=bk.lpt_shares(items,nlanes);uid=uids(sample);B=block_tasks or max(16*T,256);gpb=max(1,B//REPS);plan=[]
    for share in shares:
        blocks=[]
        for sector in ('free','power'):
            gs=[it[1][1]for it in sorted((it for it in share if it[1][0]==sector),key=lambda x:(-x[0],x[1]))]
            for i in range(0,len(gs),gpb):
                rows=[(uid[(sector,r,g)],r,g,0,POINTS,POINTS)for g in gs[i:i+gpb]for r in range(REPS)]
                blocks.append((sector,rows))
        plan.append(blocks)
    return plan,[math.fsum(it[0]for it in s)for s in shares]

def run_lane(exe,lane,cpus,blocks,roots,gamma,net,T,tag,scratch,pin,mp_check):
    recs=[];t_start=time.perf_counter();digs=[]
    for j,(sector,rows) in enumerate(blocks):
        tf=scratch/'tasks'/f'{tag}.lane{lane}.b{j}.tasks';bk.write_tasks(tf,8,8,rows)
        out=scratch/'out'/f'{tag}.lane{lane}.b{j}.json';lg=scratch/'out'/f'{tag}.lane{lane}.b{j}.log';out.unlink(missing_ok=True)
        cmd=bk.native_cmd(exe,roots[sector],gamma,net,tf,out,V.SEED,LAYOUT,RATE,T,'compensated',mp_check)
        t0=time.perf_counter()
        with open(lg,'w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=bk.omp_env(T),preexec_fn=bk.pinner(cpus,pin),timeout=3600)
        wall=time.perf_counter()-t0
        if cp.returncode:raise RuntimeError(f'{tag} lane {lane} block {j}: exit {cp.returncode}: {lg.read_text()[-1500:]}')
        if not out.is_file():raise RuntimeError(f'{tag} lane {lane} block {j}: no output')
        nat=load(out);s=bk.native_summary(nat,T)
        if s['tasks']!=len(rows):raise RuntimeError(f'{tag} lane {lane} block {j}: {s["tasks"]} rows for {len(rows)} tasks')
        digs+=bk.rows_digest(nat['rows'],sector)
        recs.append({'sector':sector,'tasks':len(rows),'wall_seconds':wall,'t_start':t0-t_start,
                     **{k:s[k]for k in ('points','quad','mp','task_seconds','load_seconds','integration_seconds','openmp_efficiency','max_rss_kb')}})
        out.unlink();lg.unlink();tf.unlink()
    return {'lane':lane,'cpus':[min(cpus),max(cpus)],'wall_seconds':time.perf_counter()-t_start,'blocks':recs},digs

def one_run(a,name,exe,r,shape,plan,cpusets,roots,gamma,net,scratch)->dict:
    N,T=shape;tag=f'{name}.r{r}';t0=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan))as pool:
        futs=[pool.submit(run_lane,exe,k,cpusets[k],plan[k],roots,gamma,net,T,tag,scratch,a.pin,a.mp_check)for k in range(len(plan))]
        res=[f.result()for f in futs]
    node_wall=time.perf_counter()-t0
    lanes=[x[0]for x in res];digs=[d for x in res for d in x[1]];blocks=[b for l in lanes for b in l['blocks']]
    rec={'binary':name,'repeat':r,'shape':f'{N}x{T}','node_wall_seconds':node_wall,'lanes':lanes,'rows':len(digs),'rows_digest':bk.combined_digest(digs),
         'lane_thread_seconds':T*math.fsum(b['wall_seconds']for b in blocks),'per_sector':{},
         'quad':sum(b['quad']for b in blocks),'mp':sum(b['mp']for b in blocks)}
    for sector in ('free','power'):
        bs=[b for b in blocks if b['sector']==sector]
        rec['per_sector'][sector]={'lane_thread_seconds':T*math.fsum(b['wall_seconds']for b in bs),'blocks':len(bs),'tasks':sum(b['tasks']for b in bs),
                                   'load_seconds':math.fsum(b['load_seconds']for b in bs),'integration_seconds':math.fsum(b['integration_seconds']for b in bs),
                                   'task_seconds':math.fsum(b['task_seconds']for b in bs),'quad':sum(b['quad']for b in bs),'mp':sum(b['mp']for b in bs)}
    wall=math.fsum(b['wall_seconds']for b in blocks);ts=math.fsum(b['task_seconds']for b in blocks);integ=math.fsum(b['integration_seconds']for b in blocks)
    rec['load_share']=math.fsum(b['load_seconds']for b in blocks)/wall if wall else None
    rec['busy_fraction']=ts/(N*T*node_wall)if node_wall else None
    rec['openmp_efficiency']=ts/(T*integ)if integ else None
    rec['max_rss_kb_per_block']=max((b['max_rss_kb']or 0)for b in blocks)
    return rec

def summarize(rec:dict,names:list,steps:dict)->None:
    """Medians per binary, the steps' speedups and the cumulative factors (in place)."""
    runs=rec['runs']
    med=lambda f:{k:statistics.median(f(x)for x in runs if x['binary']==k)for k in names}  # noqa: E731
    rec['medians']={'lane_thread_seconds':med(lambda x:x['lane_thread_seconds']),
                    'free_lane_thread_seconds':med(lambda x:x['per_sector']['free']['lane_thread_seconds']),
                    'power_lane_thread_seconds':med(lambda x:x['per_sector']['power']['lane_thread_seconds']),
                    'node_wall_seconds':med(lambda x:x['node_wall_seconds']),'load_share':med(lambda x:x['load_share']),
                    'busy_fraction':med(lambda x:x['busy_fraction']),'openmp_efficiency':med(lambda x:x['openmp_efficiency'])}
    rec['spread']={k:(max(x['lane_thread_seconds']for x in runs if x['binary']==k)-min(x['lane_thread_seconds']for x in runs if x['binary']==k))
                     /rec['medians']['lane_thread_seconds'][k]for k in names}
    M=rec['medians'];rec['speedups']={}
    for k,(f,t) in steps.items():
        s={m:M[m][f]/M[m][t]for m in ('lane_thread_seconds','free_lane_thread_seconds','power_lane_thread_seconds','node_wall_seconds')}
        s['meets_3pct_bar']=s['lane_thread_seconds']>=BAR;rec['speedups'][k]={'from':f,'to':t,**s}
    rec['cumulative_vs_first']={k:M['lane_thread_seconds'][names[0]]/M['lane_thread_seconds'][k]for k in names}
    rec['rows_identical']=len({x['rows_digest']for x in runs})==1;rec['rows_digest']=runs[0]['rows_digest']if runs else None

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--exe',action='append',required=True);p.add_argument('--step',action='append',default=[]);p.add_argument('--expect',action='append',default=[])
    p.add_argument('--shape',default='16x8');p.add_argument('--shape-of',action='append',default=[])
    p.add_argument('--cost-model',type=Path,default=DEFAULT_MODEL);p.add_argument('--output',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--block-tasks',default='auto');p.add_argument('--mp-check',default='on',choices=bk.MP_CHECK_MODES)
    p.add_argument('--inputs',default='inputs',help='SMOKE/TEST ONLY when not inputs: another inputs folder (relative to the package)')
    p.add_argument('--sample-sizes',help='SMOKE/TEST ONLY: HEAVY,FREE,POWER instead of 100,1500,300')
    p.add_argument('--fake-topology',help='SMOKE ONLY: SxNxC topology (tools/benchkit.fake_cores)');p.add_argument('--no-pin',action='store_true')
    a=p.parse_args(argv);t0=time.time();a.pin=not a.no_pin
    if a.repeats<1:p.error('--repeats must be >= 1')
    exes={k:str(Path(v).resolve())for k,v in kv(a.exe,'--exe').items()};names=list(exes)
    steps={k:tuple(v.split(':'))for k,v in kv(a.step,'--step').items()}
    for k,ft in steps.items():
        if len(ft)!=2 or any(x not in exes for x in ft):raise SystemExit(f'--step {k}: FROM:TO must name two --exe binaries')
    for k,v in exes.items():
        if not Path(v).is_file():raise SystemExit(f'--exe {k}: {v} is missing')
    sha={k:digest(Path(v))for k,v in exes.items()}
    for k,v in kv(a.expect,'--expect').items():
        if not sha.get(k,'').startswith(v):raise SystemExit(f'{k}: sha256 {sha.get(k)} does not start with the expected {v}')
    (base_shape,)=bk.parse_shapes(a.shape);shape_of={k:base_shape for k in names}
    for k,v in kv(a.shape_of,'--shape-of').items():
        if k not in exes:raise SystemExit(f'--shape-of {k}: not an --exe name')
        (shape_of[k],)=bk.parse_shapes(v)
    sizes=None
    if a.sample_sizes:
        h,f,pw=(int(x)for x in a.sample_sizes.split(','));sizes={'heavy':h,'free':f,'power':pw}
    # S4-005: the inputs verified against their manifest (prepare_inputs.verify) before anything is created, selected or run
    try:I,inv,vin=bk.verified_inputs(a.inputs)
    except bk.BenchError as e:print(f'opt_speed: {e}',file=sys.stderr);return e.code
    smoke=bool(a.fake_topology or a.sample_sizes or a.inputs!='inputs'or vin['test_only_reasons'])
    a.output.mkdir(parents=True);a.scratch.mkdir(parents=True,exist_ok=True)
    scratch=Path(tempfile.mkdtemp(prefix='c8d3_opt_speed_',dir=a.scratch));(scratch/'tasks').mkdir();(scratch/'out').mkdir()
    cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores()
    shapes=sorted(set(shape_of.values()));cpusets={s:bk.partition(cores,*s)for s in shapes}
    cm=load(a.cost_model);sample=V.l8self_sample(inv,sizes)
    gamma=I.where(bk.GAMMA)
    rec={'schema':'c8-d3-stage4b-opt-speed-1','smoke':smoke,'host':os.uname().nodename,'repeats':a.repeats,'block_tasks':a.block_tasks,
         'shapes':{k:f'{n}x{t}'for k,(n,t) in shape_of.items()},'cpusets':{f'{n}x{t}':[[min(c),max(c)]for c in cpusets[(n,t)]]for n,t in shapes},
         'workload':{'sample':'tests/validate.py l8self_sample (A-RPL-8 L8 sweep sample)','graphs':{k:len(v)for k,v in sample.items()},'sizes':sizes or V.L8SELF_SIZES,
                     'replicates':REPS,'points':POINTS,'backend':'gmp','seed':V.SEED,'net_seed':V.L8SELF_NET_SEED,'draw_seed':V.L8SELF_DRAW,
                     'layout':LAYOUT,'rate':RATE,'sum_mode':'compensated','mp_check':a.mp_check,'inputs':str(I.dir)},
         'inputs_verified':vin,
         'cost_model':{'path':str(a.cost_model),'sha256':digest(a.cost_model),'executable_sha256':cm.get('executable_sha256')},
         'binaries':{k:{'path':exes[k],'sha256':sha[k]}for k in names},'steps':{k:{'from':f,'to':t}for k,(f,t) in steps.items()},
         'bar':BAR,'metric':'lane_thread_seconds (T x the sum of the native blocks\' walls), median of the repeats',
         'identity':bk.identity({k:Path(v)for k,v in exes.items()})}
    status=1
    try:
        roots={};t1=time.perf_counter();rec['staging']={}
        for sector,ids in sample.items():
            roots[sector]=scratch/'graphs'/sector;rec['staging'][sector]=bk.stage_graphs(I,inv,sector,8,ids,roots[sector])
        net=V.l8self_net(scratch);rec['net']={'path':net.name,'sha256':digest(net)}
        rec['staging_seconds']=time.perf_counter()-t1;log(f'staged {sum(len(v)for v in sample.values())} kernels in {rec["staging_seconds"]:.0f} s')
        plans={}
        for n,t in shapes:
            bt=bk.block_tasks(t,a.block_tasks);plans[(n,t)],pred=build_lanes(cm,sample,n,t,bt)
            rec.setdefault('lane_plans',{})[f'{n}x{t}']={'block_tasks':bt or max(16*t,256),'lanes':[{'lane':k,'predicted_cost_model_seconds':pred[k],
                'blocks':[{'sector':s,'tasks':len(rows)}for s,rows in plans[(n,t)][k]]}for k in range(n)]}
            log(f'{n}x{t}: predicted cost-model seconds per lane {min(pred):.1f}-{max(pred):.1f}, blocks per lane {min(len(b)for b in plans[(n,t)])}-{max(len(b)for b in plans[(n,t)])}')
        runs=[];rot=math.ceil(len(names)/a.repeats);rec['runs']=runs
        for r in range(a.repeats):
            order=names[(r*rot)%len(names):]+names[:(r*rot)%len(names)]
            for name in order:
                s=shape_of[name];x=one_run(a,name,exes[name],r,s,plans[s],cpusets[s],roots,gamma,net,scratch);runs.append(x)
                log(f'{name} r{r} ({x["shape"]}): lane-thread s {x["lane_thread_seconds"]:.1f} (free {x["per_sector"]["free"]["lane_thread_seconds"]:.1f}, '
                    f'power {x["per_sector"]["power"]["lane_thread_seconds"]:.1f}), node wall {x["node_wall_seconds"]:.1f} s, load share {x["load_share"]:.4f}, '
                    f'busy {x["busy_fraction"]:.3f}, digest {x["rows_digest"][:12]}')
        summarize(rec,names,steps)
        log('speedups: '+json.dumps({k:round(v['lane_thread_seconds'],4)for k,v in rec['speedups'].items()})+f'; rows identical {rec["rows_identical"]}')
        status=0 if rec['rows_identical']else 1
    except Exception as e:  # noqa: BLE001  (recorded, then re-raised)
        rec['error']=f'{type(e).__name__}: {e}';raise
    finally:
        rec['wall_seconds']=round(time.time()-t0,1);rec['status']='passed'if status==0 else'failed'
        (a.output/'opt_speed.json').write_text(json.dumps(rec,indent=1)+'\n')
        shutil.rmtree(scratch,ignore_errors=True)
    print(json.dumps({'speedups':rec.get('speedups'),'cumulative_vs_first':rec.get('cumulative_vs_first'),'rows_identical':rec.get('rows_identical'),'smoke':smoke},indent=1))
    return status

if __name__=='__main__':sys.exit(main())
