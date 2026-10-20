#!/usr/bin/env python3
"""Fresh matched-sample kernel benchmarks, with exact commands and raw logs.

Three modes:
  benchmark.py --output DIR [--repeats 3]
      C7(3)'s matched benchmarks (unchanged; they need C7(3)'s src/c7d3_integrate.cpp and experiments/quotient_reuse,
      which the C8(3) package does not carry: kept for provenance only).
  benchmark.py --lane-shapes 8x16,4x32,2x64,1x128,16x8 --output DIR [--workload p4_L8] [--fraction 1]
               [--exe bin/c8d3_gmp] [--expect-sha256 HEX] [--block-tasks auto|N|all] [--block-seconds 900] [--mp-check on]
               [--scratch DIR]
      P4 (PLAN "Performance plan"; C8(3) Stage 4a; port of C62d's --lane-shapes, LRI_C8_D2_HPC@2083d84, sha256
      3677001b...): for each NxT shape, N native lanes pinned to disjoint NUMA-aligned sets of T physical cores of the
      job's CPU set (benchkit.partition from sysfs; a shape that does not fit is refused before anything runs) work
      through equal shares of the fixed workload of benchmarks/fixtures8 (deterministic LPT on cost-model seconds). Each
      lane is its own process, pinned like production.py run under a lane: per native block it stages the block's graph
      members from the pinned pack (verified against the inventory sha256), runs the worker at T threads with
      OMP_PROC_BIND=close OMP_PLACES=cores and --mp-check on, and samples the worker's /proc/<pid>/numa_maps. Blocks follow
      production's two maxima (D.6, production.cut_blocks): at most --block-tasks tasks (auto: max(16 x T, 256), the
      plan's default --checkpoint-tasks) and at most --block-seconds (BLOCK_SECONDS, 900) of predicted work at width T,
      each part's tasks by cost descending. The workload's tasks follow production's chunking (<= 60 s per task, D.5).
      Recorded per shape: node wall, throughput in cost-model seconds per node-second (and per core), busy fraction,
      OpenMP efficiency, staging and graph-load seconds and their share of node time (R5a; the PACK_FORMAT decision),
      per-lane wall, peak RSS (VmHWM) per block and lane, per-lane NUMA placement and the node numastat counters, and an
      order-independent digest of every row's scientific fields (equal across shapes: thread identity).
  benchmark.py --interleave-probe --output DIR [--probe-exe bin/diag/c8d3_interleave_probe]
               [--probe-graphs nopromo_free_L8:2,nopromo_free_L7:2,strat_free_L8:2,strat_free_L7:2]
      P2's fallback (R6 = plan #6 go/no-go): the micro-benchmark benchmarks/probes/interleave_probe.cpp (built here into
      bin/diag/ with the worker's gmp command when missing) on the heaviest graphs of the named fixture blocks, one
      single-threaded process per graph, each pinned to its own core: time per point of kernel.hpp's calculate_products
      against 2 and 4 points in lock-step (bit-identical results required); the probe speedup is the sequential over the
      lock-step time.
Dry runs: --fake-topology SxNxC --no-pin (recorded as such; never a measurement).
"""
from pathlib import Path
import argparse,json,math,os,shutil,statistics,struct,subprocess,sys,tempfile,time,platform
from decimal import Decimal as D
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,compiler_identity,cxx_command,dump,exe_identity,host_info,load,digest
PROBE_EXE=ROOT/'bin/diag/c8d3_interleave_probe'

def build_reference(path):
    """The original d=3 worker (reference/src, gmp backend), built with exactly the Makefile's command (common.cxx_command)."""
    src=ROOT/'reference/src/c7d3_integrate.cpp';cmd=cxx_command([src],path,defines=('C7_USE_GMP',),libs=('-lquadmath','-lgmp'))
    subprocess.run(cmd,check=True);return {**compiler_identity(cmd),'sha256':digest(path)}

def legacy_main(a):
    P=a.output.resolve();P.mkdir(parents=True,exist_ok=False);reference_build=build_reference(P/'reference')
    trial=P/'quotient_candidate';trial.mkdir();shutil.copyfile(ROOT/'src/c7d3_integrate.cpp',trial/'c7d3_integrate.cpp');shutil.copyfile(ROOT/'experiments/quotient_reuse/kernel.hpp',trial/'kernel.hpp')
    candidate=trial/'worker'
    ccmd=cxx_command([trial/'c7d3_integrate.cpp'],candidate,defines=('C7_USE_GMP',),libs=('-lquadmath','-lgmp'));subprocess.run(ccmd,check=True)
    candidate_build={**compiler_identity(ccmd),**exe_identity(candidate)}
    from prepare_benchmarks import prepare_benchmarks
    fixtures=prepare_benchmarks();profile=ROOT/'benchmarks/fixtures';records=[];comparisons=[]
    for sector in ('free','power'):
      for L in (6,7):
        inv=ROOT/'reference/inputs'/sector
        ids=fixtures['records'][f'{sector}_L{L}']['ids'];n=4096 if L==6 else 512
        nf=P/f'{sector}_L{L}.net';nf.write_bytes((profile/f'{sector}_L{L}.net').read_bytes())
        tasks=P/f'{sector}_L{L}.tasks';tasks.write_text(f'C7D3TASKS1 {L} {2*len(ids)}\n'+''.join(f'{i} {r} {g} 0 {n} {n}\n'for i,(r,g)in enumerate((r,g)for r in range(2)for g in ids)))
        outputs={}
        variants=[('reference',P/'reference',1),('gmp',candidate,1)]
        if L==7:variants += [('gmp',candidate,2),('gmp',candidate,4)]
        for tag,exe,threads in variants:
            times=[];memory=[];integrations=[];loads=[];cmd=None
            for rep in range(a.repeats):
                stem=P/f'{sector}_L{L}_{tag}_t{threads}_r{rep}';out=stem.with_suffix('.json');mem=stem.with_suffix('.time');log=stem.with_suffix('.log')
                cmd=list(map(str,[exe,inv,ROOT/'inputs/gamma_d3_7.txt',nf,tasks,out,5461981,0,.8,threads,'compensated','-']))
                before=time.perf_counter();cp=subprocess.run(['/usr/bin/time','-v','-o',str(mem)]+cmd,capture_output=True,text=True,check=True,env=dict(os.environ,OMP_PROC_BIND='close',OMP_PLACES='cores'))
                times.append(time.perf_counter()-before);log.write_text(cp.stderr);data=load(out);memory.append(int(next(l.rsplit(':',1)[1]for l in mem.read_text().splitlines()if'Maximum resident'in l))/1024);integrations.append(data['integration_seconds']);loads.append(data['load_seconds']);outputs[(tag,threads)]=data
                print(sector,L,tag,threads,rep,'wall',times[-1],flush=True)
            records.append(dict(sector=sector,L=L,variant=tag,threads=threads,graphs=len(ids),samples=n*len(ids)*2,median_wall_s=statistics.median(times),median_integration_s=statistics.median(integrations),median_load_s=statistics.median(loads),max_rss_mib=max(memory),wall_s=times,rss_mib=memory,command=cmd))
        ref=outputs[('reference',1)]
        for (tag,t),dat in outputs.items():
            if tag=='reference':continue
            error=max(abs(D(x)-D(y))/max(D(1),abs(D(x)))for r,s in zip(ref['rows'],dat['rows'])for x,y in zip(r['values'],s['values']))
            counts_equal=all(r[k]==s[k]for r,s in zip(ref['rows'],dat['rows'])for k in ('quad','mp'))
            if error>D('1e-12')or not counts_equal:raise AssertionError((sector,L,tag,error,counts_equal))
            comparisons.append(dict(sector=sector,L=L,backend=tag,threads=t,normalized_error=str(error),fallback_counts_match=counts_equal))
    env=dict(platform=platform.platform(),python=platform.python_version(),compiler=compiler_identity(cxx_command([ROOT/'src/c7d3_integrate.cpp'],P/'x'))['compiler_version'],cpu_quota=Path('/sys/fs/cgroup/cpu.max').read_text().strip()if Path('/sys/fs/cgroup/cpu.max').exists()else None,processor_count=os.cpu_count())
    env.update(host=host_info(),builds={'reference':{**reference_build,**exe_identity(P/'reference')},'candidate':candidate_build})
    dump(P/'benchmarks.json',dict(records=records,comparisons=comparisons,environment=env,scope='Selected expensive classes; matched points. Local timings, NOT a multi-node measurement.'))


def build_probe(dest:Path)->dict:
    """bin/diag/c8d3_interleave_probe from benchmarks/probes/interleave_probe.cpp with the worker's gmp command (the
    Makefile's flags and order, common.cxx_command); never a worker, never accepted by plan."""
    dest.parent.mkdir(parents=True,exist_ok=True)
    cmd=cxx_command(['benchmarks/probes/interleave_probe.cpp'],dest,defines=('C7_USE_GMP',),libs=('-lquadmath','-lgmp'))
    t0=time.perf_counter();cp=subprocess.run(cmd,capture_output=True,text=True,timeout=1800,cwd=ROOT)
    rec={'command':cmd,'returncode':cp.returncode,'seconds':time.perf_counter()-t0,'stderr':cp.stderr[-1500:],**compiler_identity(cmd)}
    if cp.returncode==0:rec['sha256']=digest(dest);dest.with_name(dest.name+'.build.txt').write_text(' '.join(cmd)+'\n'+str(rec.get('compiler_version'))+'\n')
    return rec

# ---------------------------------------------------------------- P4: lane shapes
def log(msg):print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def workload_items(m:dict,name:str,fraction:float)->tuple[list,dict]:
    """(cost, (part, uid), row) items of a fixture workload, keeping the first ceil(fraction x k) graphs of each part's
    draw order, and the parts' native settings and inventory members."""
    import benchkit as bk
    if name not in m['workloads']:raise bk.BenchError(64,f'no workload {name!r}; known: {", ".join(sorted(m["workloads"]))}')
    if not 0<fraction<=1:raise bk.BenchError(64,f'--fraction {fraction}: must be in (0, 1]')
    I=m['_inputs'];inv=load(I.where('inventory.json'));items=[];parts={}
    for bn in m['workloads'][name]['blocks']:
        b=bk.block_of(m,bn);keep=set(b['draw_order'][:math.ceil(fraction*len(b['draw_order']))]);_o,L,rows=bk.read_tasks(b['tasks_path'])
        rows=[r for r in rows if r[2]in keep];spp=b['seconds_per_point']
        rowsinv={r['id']:r for r in inv[b['sector']][str(L)]}
        parts[bn]={'sector':b['sector'],'L':L,'net':b['net_path'],'seed':b['native_seed'],'pack':str(I.pack(b['sector'],L)),'graphs':len(keep),
                   'members':{str(g):{k:rowsinv[g][k]for k in ('offset','length','sha256')}for g in sorted(keep)}}
        items+=[(spp[str(r[2])]*(r[4]-r[3]),(bn,r[0]),list(r))for r in rows]
    return items,parts

def lane_run(spec_path:Path)->int:
    """One lane (an internal mode: benchmark.py --lane-run SPEC): its blocks one after another, each staged from the
    pack, run at the lane width, timed and summarized; the result goes to spec['result']."""
    import benchkit as bk
    sp=load(spec_path);res={'lane':sp['lane'],'cpus':sp['cpus'],'threads':sp['threads'],'pid':os.getpid(),
        'affinity':sorted(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else None,'blocks':[],'error':None}
    scr=Path(sp['scratch']);n=sp['native'];t=sp['threads']
    try:
        for k,blk in enumerate(sp['blocks']):
            part=sp['parts'][blk['part']];d=scr/f'b{k:03d}';d.mkdir(parents=True);t0=time.time()
            rows=[tuple(r)for r in blk['rows']];members={int(g):v for g,v in part['members'].items()}
            st=bk.stage_members(Path(part['pack']),members,part['L'],{r[2]for r in rows},d/'graphs')
            tasks=d/'tasks.txt';bk.write_tasks(tasks,8,part['L'],rows);out=d/'native.json';logf=d/'native.log'
            cmd=bk.native_cmd(sp['exe'],d/'graphs',sp['gamma'],part['net'],tasks,out,part['seed'],n['layout'],n['rate'],t,n['sum_mode'],sp.get('mp_check')or n.get('mp_check','on'))
            t1=time.time();numa_max=None;numa_last=None;nxt=t1+sp['numa_sample_seconds']
            with open(logf,'w')as lf:
                p=subprocess.Popen(cmd,stdout=lf,stderr=subprocess.STDOUT,env=bk.omp_env(t))
                while p.poll()is None:
                    time.sleep(0.2)
                    if time.time()>=nxt:
                        nm=bk.numa_maps_of(p.pid);nxt=time.time()+sp['numa_sample_seconds']
                        if nm:
                            numa_last=nm
                            if numa_max is None or sum(nm.values())>sum(numa_max.values()):numa_max=nm
            t2=time.time()
            if p.returncode!=0 or not out.is_file():raise RuntimeError(f'block {k} ({blk["part"]}): worker exit {p.returncode}: {logf.read_text(errors="replace")[-800:]}')
            nat=load(out);s=bk.native_summary(nat,t)
            res['blocks'].append({'part':blk['part'],'tasks':len(rows),'cost_model_seconds':blk['cost'],'t_start':t0,'t_native_start':t1,'t_end':t2,
                                  'stage_seconds':st['seconds'],'stage_bytes':st['bytes'],'graphs':st['graphs'],'native_wall_seconds':t2-t1,**s,
                                  'numa_kb_max':numa_max,'numa_kb_last':numa_last,'rows':bk.rows_digest(nat['rows'],blk['part'])})
            for f in (out,tasks):f.unlink()
            shutil.rmtree(d)
    except Exception as e:  # recorded; the main process reports the failed lane
        res['error']=f'{type(e).__name__}: {e}'
    Path(sp['result']).write_text(json.dumps(res)+'\n')
    return 0 if res['error']is None else 1

def shape_summary(n:int,t:int,lanes:list,cores,cpus_by_lane:list,numa_delta:dict,wall_total:float)->dict:
    import benchkit as bk
    blocks=[b for L in lanes for b in L['blocks']];errors=[L['error']for L in lanes if L['error']]
    if not blocks:return {'shape':f'{n}x{t}','errors':errors or['no block ran']}
    t0=min(b['t_start']for b in blocks);t1=max(b['t_end']for b in blocks);wall=t1-t0;ncores=n*t
    cms=math.fsum(b['cost_model_seconds']for b in blocks);task_s=math.fsum(b['task_seconds']for b in blocks)
    stage=math.fsum(b['stage_seconds']for b in blocks);load_=math.fsum(b['load_seconds']for b in blocks)
    integ=math.fsum(b['integration_seconds']*b['threads']for b in blocks)
    overhead=math.fsum(b['native_wall_seconds']-b['load_seconds']-b['integration_seconds']for b in blocks)
    lane_rows=[]
    for L,cs in zip(lanes,cpus_by_lane):
        bl=L['blocks'];mine=set(bk.nodes_of(cores,cs));nm=[b['numa_kb_max']for b in bl if b['numa_kb_max']]
        tot=sum(sum(x.values())for x in nm);loc=sum(v for x in nm for k,v in x.items()if int(k)in mine)
        lane_rows.append({'lane':L['lane'],'cpus':f'{cs[0]}-{cs[-1]}'if cs==list(range(cs[0],cs[-1]+1))else cs,'numa_nodes':sorted(mine),'blocks':len(bl),
                          'wall_seconds':(max(b['t_end']for b in bl)-min(b['t_start']for b in bl))if bl else None,
                          'cost_model_seconds':math.fsum(b['cost_model_seconds']for b in bl),'task_seconds':math.fsum(b['task_seconds']for b in bl),
                          'max_rss_kb':max((b['max_rss_kb']or 0 for b in bl),default=None),'numa_local_fraction':(loc/tot if tot else None),
                          'stage_seconds':math.fsum(b['stage_seconds']for b in bl),'load_seconds':math.fsum(b['load_seconds']for b in bl),'error':L['error']})
    rows=[tuple(r)for b in blocks for r in b['rows']]
    return {'shape':f'{n}x{t}','lanes':n,'threads':t,'cores':ncores,'wall_seconds':wall,'wall_including_setup_seconds':wall_total,
            'cost_model_seconds':cms,'throughput_cost_model_s_per_node_s':cms/wall if wall>0 else None,
            'throughput_per_core':cms/wall/ncores if wall>0 else None,'busy_fraction':task_s/(ncores*wall)if wall>0 else None,
            'openmp_efficiency':task_s/integ if integ>0 else None,'stage_seconds':stage,'load_seconds':load_,'native_overhead_seconds':overhead,
            'load_staging_share_of_node_time':math.fsum((b['stage_seconds']+b['load_seconds'])*b['threads']for b in blocks)/(ncores*wall)if wall>0 else None,
            'stage_share_of_node_time':math.fsum(b['stage_seconds']*b['threads']for b in blocks)/(ncores*wall)if wall>0 else None,
            'load_share_of_node_time':math.fsum(b['load_seconds']*b['threads']for b in blocks)/(ncores*wall)if wall>0 else None,
            'lane_end_spread_seconds':(max(max(b['t_end']for b in L['blocks'])for L in lanes if L['blocks'])-min(max(b['t_end']for b in L['blocks'])for L in lanes if L['blocks'])),
            'max_rss_kb_per_lane':max((r['max_rss_kb']or 0)for r in lane_rows),'sum_lane_peak_rss_kb':sum((r['max_rss_kb']or 0)for r in lane_rows),
            'blocks':len(blocks),'tasks':sum(b['tasks']for b in blocks),'points':sum(b['points']for b in blocks),'quad':sum(b['quad']for b in blocks),'mp':sum(b['mp']for b in blocks),
            'lanes_detail':lane_rows,'numastat_delta':numa_delta,'rows_digest':bk.combined_digest(rows),'rows':len(rows),'errors':errors,
            'block_detail':[{k:b[k]for k in ('part','tasks','cost_model_seconds','stage_seconds','load_seconds','integration_seconds','native_wall_seconds',
                                                 'task_seconds','openmp_efficiency','max_rss_kb','quad','mp','points')}|{'t_start':b['t_start']-t0,'t_end':b['t_end']-t0}
                            for b in blocks]}

def lane_shapes(a)->int:
    import benchkit as bk
    shapes=bk.parse_shapes(a.lane_shapes);m=bk.load_fixtures(a.fixtures)
    cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores();pin=not a.no_pin
    if a.fake_topology and pin:raise bk.BenchError(64,'--fake-topology needs --no-pin (the fake CPU numbers do not exist)')
    plans=[(n,t,bk.partition(cores,n,t),bk.block_tasks(t,a.block_tasks))for n,t in shapes]  # every shape checked before anything runs
    S=None if a.block_seconds<=0 else a.block_seconds
    exe=Path(a.exe).resolve();ex=bk.exe_identity(exe)
    if not ex['present']:raise bk.BenchError(69,f'{exe} is missing (make gmp)')
    if (ex.get('describe')or{}).get('diagnostic'):raise bk.BenchError(65,f'{exe} is a diagnostic build; P4 measures the release worker')
    if a.expect_sha256 and not ex['sha256'].startswith(a.expect_sha256.lower()):raise bk.BenchError(65,f'{exe}: sha256 {ex["sha256"][:12]}... is not the expected {a.expect_sha256}')
    items,parts=workload_items(m,a.workload,a.fraction)
    out=Path(a.output).resolve()
    if out.exists():raise bk.BenchError(64,f'{out} exists; give a new output directory')
    out.mkdir(parents=True)
    scratch=Path(tempfile.mkdtemp(prefix='c8d3_p4_',dir=a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir()))
    ident=bk.identity({'worker':exe})
    cms=math.fsum(i[0]for i in items)
    log(f'P4 workload {a.workload} x {a.fraction}: {len(items)} tasks, {cms:.0f} cost-model s ({cms/len(cores):.0f} s ideal on {len(cores)} cores); shapes {[f"{n}x{t}" for n,t,_,_ in plans]}')
    gamma=m['_inputs'].where(bk.GAMMA);results=[]
    for n,t,sets,T in plans:
        shares=bk.lpt_shares(items,n);specs=[];procs=[];d=scratch/f'{n}x{t}'
        for i,(cs,share)in enumerate(zip(sets,shares)):
            blocks=[{'part':p,'rows':[it[2]for it in rows],'cost':math.fsum(it[0]for it in rows)}for p,rows in bk.lane_blocks(share,T,list(parts),S,t)]
            sp={'lane':i,'cpus':cs,'threads':t,'exe':str(exe),'gamma':str(gamma),'native':m['native'],'mp_check':a.mp_check,'parts':parts,'blocks':blocks,
                'scratch':str(d/f'lane{i:02d}'),'result':str(d/f'lane{i:02d}.result.json'),'numa_sample_seconds':a.numa_sample_seconds}
            f=d/f'lane{i:02d}.spec.json';f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(sp));specs.append(sp)
        before=bk.node_numastat();log(f'shape {n}x{t}: {n} lanes, blocks of <= {T or "all"} tasks and <= {S or "any"} s at width {t}, lane shares {[round(math.fsum(it[0]for it in s)) for s in shares]} cost-model s')
        w0=time.perf_counter()
        for i,(cs,sp)in enumerate(zip(sets,specs)):
            lf=open(d/f'lane{i:02d}.log','w')
            procs.append((subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--lane-run',str(d/f'lane{i:02d}.spec.json')],stdout=lf,stderr=subprocess.STDOUT,
                                           env=bk.omp_env(t),preexec_fn=bk.pinner(cs,pin)),lf))
        for p,lf in procs:p.wait();lf.close()
        wall_total=time.perf_counter()-w0;after=bk.node_numastat()
        lanes=[]
        for i,sp in enumerate(specs):
            r=Path(sp['result'])
            lanes.append(load(r)if r.is_file()else{'lane':i,'blocks':[],'error':f'no result (lane log: {(d/f"lane{i:02d}.log").read_text(errors="replace")[-600:]})'})
            shutil.copy2(d/f'lane{i:02d}.log',out/f'{n}x{t}.lane{i:02d}.log')
        s=shape_summary(n,t,lanes,cores,sets,bk.numastat_delta(before,after),wall_total);results.append(s)
        (out/f'{n}x{t}.json').write_text(json.dumps(s,indent=1)+'\n')
        log(f'shape {n}x{t}: wall {s.get("wall_seconds",0):.1f} s, throughput {s.get("throughput_cost_model_s_per_node_s") or 0:.1f} cost-model s per node-second, busy {s.get("busy_fraction") or 0:.3f}, errors {s["errors"]}')
        shutil.rmtree(d,ignore_errors=True)
    ok=[s for s in results if not s['errors']]
    best=max(ok,key=lambda s:s['throughput_cost_model_s_per_node_s'])if ok else None
    rec={'schema':'c8-d3-prof-p4-1','profile':'P4','identity':ident,'fixtures_manifest_sha256':m['_manifest_sha256'],
         'workload':{'name':a.workload,'fraction':a.fraction,'tasks':len(items),'cost_model_seconds':cms,'parts':{k:{x:v[x]for x in ('sector','L','graphs','seed')}for k,v in parts.items()}},
         'settings':{'shapes':[f'{n}x{t}'for n,t,_,_ in plans],'block_tasks':a.block_tasks,'block_seconds':S,'mp_check':a.mp_check,'pinned':pin,'fake_topology':a.fake_topology,'cores':len(cores),
                     'numa_sample_seconds':a.numa_sample_seconds,'scratch':str(scratch),'omp':{'OMP_PROC_BIND':'close','OMP_PLACES':'cores','OMP_DYNAMIC':'FALSE'}},
         'shapes':[{k:v for k,v in s.items()if k not in('block_detail',)}for s in results],
         'table':[{k:s.get(k)for k in ('shape','wall_seconds','throughput_cost_model_s_per_node_s','throughput_per_core','busy_fraction','openmp_efficiency',
                                         'load_staging_share_of_node_time','max_rss_kb_per_lane','errors')}for s in results],
         'best_shape':best['shape']if best else None,
         'relative_to_best':{s['shape']:s['throughput_cost_model_s_per_node_s']/best['throughput_cost_model_s_per_node_s']for s in ok}if best else None,
         'all_shapes_identical_rows':len({s['rows_digest']for s in ok})==1 and len(ok)==len(results),'finished_utc':__import__('common').utc()}
    (out/'p4.json').write_text(json.dumps(rec,indent=1)+'\n')
    shutil.rmtree(scratch,ignore_errors=True)
    log(f'wrote {out/"p4.json"}; best shape {rec["best_shape"]}; identical rows across shapes: {rec["all_shapes_identical_rows"]}')
    return 0 if ok and len(ok)==len(results)and rec['all_shapes_identical_rows']else 1

# ---------------------------------------------------------------- P2 fallback: the interleave probe
def interleave_probe(a)->int:
    import benchkit as bk,concurrent.futures
    m=bk.load_fixtures(a.fixtures);I=m['_inputs'];inv=load(I.where('inventory.json'));exe=Path(a.probe_exe).resolve();build=None
    if not exe.is_file():
        if a.probe_exe!=str(PROBE_EXE):raise bk.BenchError(69,f'{exe} is missing')
        build=build_probe(exe)
        if build['returncode']!=0:raise bk.BenchError(69,f'building {exe} failed: {build["stderr"][-600:]}')
    cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores();pin=not a.no_pin
    if a.fake_topology and pin:raise bk.BenchError(64,'--fake-topology needs --no-pin')
    want=[]
    for part in a.probe_graphs.split(','):
        name,_,k=part.partition(':');b=bk.block_of(m,name.strip());k=int(k or 1);spp=b['seconds_per_point']
        for g in sorted(b['graphs'],key=lambda g:(-spp[str(g)],g))[:k]:want.append((name.strip(),b['sector'],b['L'],g))
    out=Path(a.output).resolve()
    if out.exists():raise bk.BenchError(64,f'{out} exists; give a new output directory')
    out.mkdir(parents=True);scratch=Path(tempfile.mkdtemp(prefix='c8d3_probe_',dir=a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir()))
    cpus=[c for _,_,c in cores];stride=4 if len(cpus)>=4*len(want)else 1;slots=cpus[::stride][:len(want)]
    if len(slots)<len(want):raise bk.BenchError(64,f'{len(want)} probe graphs need as many cores; the allocation has {len(cpus)}')
    rate=m['native']['rate'];jobs=[]
    for (name,s,L,g),cpu in zip(want,slots):
        bk.stage_graphs(I,inv,s,L,[g],scratch/name);jobs.append((name,s,L,g,cpu,scratch/name/f'L{L}'/f'G{g}.txt'))
    def one(j):
        name,s,L,g,cpu,path=j;t0=time.perf_counter()
        cp=subprocess.run([str(exe),str(path),rate,str(a.probe_points),str(1000003+g),str(a.probe_repeats)],capture_output=True,text=True,preexec_fn=bk.pinner([cpu],pin),env=bk.omp_env(1))
        try:r=json.loads(cp.stdout)
        except ValueError:r=None
        return {'block':name,'sector':s,'L':L,'graph':g,'cpu':cpu,'returncode':cp.returncode,'wall_seconds':time.perf_counter()-t0,'result':r,'stderr':cp.stderr[-600:]}
    log(f'interleave probe on {len(jobs)} graphs ({a.probe_points} points, {a.probe_repeats} repeats), cores {slots}')
    with concurrent.futures.ThreadPoolExecutor(len(jobs))as ex:res=list(ex.map(one,jobs))
    good=[r for r in res if r['returncode']==0 and r['result']]
    def gmean(xs):return math.exp(math.fsum(math.log(x)for x in xs)/len(xs))if xs else None
    summ={}
    for grp,sel in (('all',good),('promotion_free',[r for r in good if r['block'].startswith('nopromo')]),('heavy',[r for r in good if r['block'].startswith(('heavy','strat'))])):
        summ[grp]={w:{'geometric_mean':gmean([r['result']['speedup'][w]for r in sel]),'median':(statistics.median([r['result']['speedup'][w]for r in sel])if sel else None)}for w in ('2','4')}
    rec={'schema':'c8-d3-prof-interleave-1','profile':'P2 fallback (interleave probe)','identity':bk.identity({'probe':exe}),'probe_build':build,'fixtures_manifest_sha256':m['_manifest_sha256'],
         'settings':{'points':a.probe_points,'repeats':a.probe_repeats,'graphs':a.probe_graphs,'pinned':pin,'fake_topology':a.fake_topology},
         'results':res,'speedup':summ,'all_identical':bool(good)and all(r['result']['identical']['2']and r['result']['identical']['4']for r in good),
         'probe_speedup_2':summ['all']['2']['geometric_mean'],
         'decision_rule':'R6 go if IPC < 1.5 (P2 perf stat) or the probe speedup (2 points in lock-step) >= 1.2','finished_utc':__import__('common').utc()}
    (out/'interleave.json').write_text(json.dumps(rec,indent=1)+'\n');shutil.rmtree(scratch,ignore_errors=True)
    log(f'wrote {out/"interleave.json"}; speedup (2 points) {rec["probe_speedup_2"]}; identical {rec["all_identical"]}')
    return 0 if len(good)==len(res)and rec['all_identical']else 1

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output',type=Path);ap.add_argument('--repeats',type=int,default=3)
    ap.add_argument('--lane-shapes');ap.add_argument('--interleave-probe',action='store_true');ap.add_argument('--lane-run',type=Path,help=argparse.SUPPRESS)
    ap.add_argument('--workload',default='p4_L8');ap.add_argument('--fraction',type=float,default=1.0);ap.add_argument('--exe',default=str(ROOT/'bin/c8d3_gmp'))
    ap.add_argument('--expect-sha256');ap.add_argument('--block-tasks',default='auto');ap.add_argument('--block-seconds',type=float,default=900.)
    ap.add_argument('--mp-check',default='on',choices=('on','off','stride16'))
    ap.add_argument('--scratch');ap.add_argument('--numa-sample-seconds',type=float,default=15.)
    ap.add_argument('--fixtures',type=Path);ap.add_argument('--fake-topology');ap.add_argument('--no-pin',action='store_true')
    ap.add_argument('--probe-exe',default=str(PROBE_EXE));ap.add_argument('--probe-graphs',default='nopromo_free_L8:2,nopromo_free_L7:2,strat_free_L8:2,strat_free_L7:2')
    ap.add_argument('--probe-points',type=int,default=4096);ap.add_argument('--probe-repeats',type=int,default=5)
    a=ap.parse_args(argv)
    if a.lane_run:return lane_run(a.lane_run)
    if sum(map(bool,(a.lane_shapes,a.interleave_probe)))>1:ap.error('give one of --lane-shapes and --interleave-probe')
    if a.output is None:ap.error('--output is required')
    if a.lane_shapes or a.interleave_probe:
        import benchkit as bk
        if a.fixtures is None:a.fixtures=bk.FIXTURES8
        try:return lane_shapes(a)if a.lane_shapes else interleave_probe(a)
        except bk.BenchError as e:print(f'benchmark: {e}',file=sys.stderr);return e.code
    legacy_main(a);return 0
if __name__=='__main__':sys.exit(main())
