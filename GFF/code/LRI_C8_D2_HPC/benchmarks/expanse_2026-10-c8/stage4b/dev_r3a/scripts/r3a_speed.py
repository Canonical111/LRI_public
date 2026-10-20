#!/usr/bin/env python3
"""R3a speed comparison and IPC on one exclusive Expanse compute node (Stage 4b development evidence; A-PERF-2's gate
measurement on the L8 sweep sample is the integration step's). Run from the package root of the export under test.

  r3a_speed.py --baseline BASE_GMP --candidate bin/c8d2_gmp --output DIR [--repeats 3] [--threads 64] [--scratch DIR]
               [--prof bin/c8d2_gmp_prof] [--perf perf] [--budget-seconds 1500]

Phase 1 (speed and exactness): the two sockets in parallel, socket 0 on heavy_free_L8 and socket 1 on heavy_power_L8
(benchmarks/fixtures8, 256 tasks x 16,384 points each), each running baseline, candidate, baseline, candidate, ...
(--repeats of each) at --threads threads pinned to the socket's cores (OMP_PROC_BIND=close, OMP_PLACES=cores, as the
production lanes). Recorded per run: the native integration_seconds, the wall time and an order-independent digest of
every row's scientific fields (tools/benchkit.py); per block the medians, the speedup (baseline median over candidate
median of integration_seconds) and whether all rows of all runs are identical (they must be).
Phase 2 (IPC, for the R3c rule): `perf stat -e cycles,instructions,task-clock` with OMP_WAIT_POLICY=passive (as P2) of
the candidate on heavy_free_L8 on socket 0 and, concurrently, of the baseline on the same block on socket 1.
Phase 3 (optional, when --prof exists and the budget allows): the candidate's tier-timer build (make profile) on
heavy_free_L8 (socket 0) and heavy_power_L8 (socket 1): seconds per call of the first pass, binary128 and MP tiers.
The graphs are staged once from the pinned packs onto --scratch (node-local), checked against the inventory sha256.
"""
from __future__ import annotations
import argparse,concurrent.futures,gzip,json,os,shutil,statistics,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
import benchkit as bk
from common import digest,load

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

class Ctx:
    def __init__(self,a):
        self.a=a;self.m=bk.load_fixtures();self.I=self.m['_inputs'];self.inv=load(self.I.where('inventory.json'))
        self.gamma=self.I.where(bk.GAMMA);self.out=Path(a.output).resolve();self.out.mkdir(parents=True)
        self.scratch=Path(tempfile.mkdtemp(prefix='c8d2_r3a_speed_',dir=a.scratch or tempfile.gettempdir()));self.blocks={}
        cores=bk.host_cores();self.sockets=bk.partition(cores,2,a.threads)
    def block(self,name):
        if name not in self.blocks:
            b=bk.block_of(self.m,name);g=self.scratch/'graphs'/name
            b['staging']=bk.stage_graphs(self.I,self.inv,b['sector'],b['L'],b['graphs'],g);b['graphs_root']=str(g);self.blocks[name]=b
        return self.blocks[name]
    def run(self,exe,name,cpus,tag,pre=(),wait_policy=None):
        b=self.block(name);n=self.m['native'];o=self.scratch/f'{tag}.json';lg=self.scratch/f'{tag}.log'
        if o.exists():o.unlink()
        cmd=[*pre,*bk.native_cmd(exe,b['graphs_root'],self.gamma,b['net_path'],b['tasks_path'],o,b['native_seed'],n['layout'],n['rate'],self.a.threads,n['sum_mode'])]
        t0=time.perf_counter()
        with open(lg,'w')as f:cp=subprocess.run([str(c)for c in cmd],stdout=f,stderr=subprocess.STDOUT,env=bk.omp_env(self.a.threads,wait_policy=wait_policy),preexec_fn=bk.pinner(cpus),timeout=3600)
        wall=time.perf_counter()-t0
        if cp.returncode:raise RuntimeError(f'{tag}: exit {cp.returncode}: {lg.read_text()[-1500:]}')
        nat=json.loads(o.read_text());rows=nat['rows']
        rec={'tag':tag,'executable':str(exe),'integration_seconds':nat['integration_seconds'],'load_seconds':nat['load_seconds'],'wall_seconds':round(wall,3),
             'rows':len(rows),'quad':sum(r['quad']for r in rows),'mp':sum(r['mp']for r in rows),'rows_digest':bk.combined_digest(bk.rows_digest(rows)),
             'cpus':[min(cpus),max(cpus)],'threads':self.a.threads}
        if 'tier_timers'in nat:rec['tier_timers']=nat['tier_timers']
        return rec,o,lg

def phase1(c:Ctx)->dict:
    a=c.a;exes={'baseline':Path(a.baseline).resolve(),'candidate':Path(a.candidate).resolve()};res={}
    def seq(name,cpus):
        runs=[];keep={}
        for r in range(a.repeats):
            for v in ('baseline','candidate'):
                tag=f'{name}.{v}.r{r}';log(f'start {tag} on cpus {min(cpus)}-{max(cpus)}');rec,o,lg=c.run(exes[v],name,cpus,tag);rec['variant']=v;runs.append(rec)
                log(f'{tag}: integration {rec["integration_seconds"]:.2f} s, wall {rec["wall_seconds"]:.2f} s, digest {rec["rows_digest"][:12]}')
                if r==0:keep[v]=o
                else:o.unlink()
        for v,o in keep.items():
            with open(o,'rb')as f,gzip.open(c.out/f'{name}.{v}.native.json.gz','wb')as g:shutil.copyfileobj(f,g)
        med={v:statistics.median(x['integration_seconds']for x in runs if x['variant']==v)for v in exes}
        wmed={v:statistics.median(x['wall_seconds']for x in runs if x['variant']==v)for v in exes}
        return name,{'runs':runs,'median_integration_seconds':med,'median_wall_seconds':wmed,'speedup_integration':med['baseline']/med['candidate'],
                     'speedup_wall':wmed['baseline']/wmed['candidate'],'rows_identical':len({x['rows_digest']for x in runs})==1,
                     'staging':c.blocks[name]['staging'],'predicted_cost_model_seconds':c.blocks[name]['predicted'].get('cost_model_seconds')}
    c.block('heavy_free_L8');c.block('heavy_power_L8')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        for name,r in pool.map(lambda x:seq(*x),(('heavy_free_L8',c.sockets[0]),('heavy_power_L8',c.sockets[1]))):res[name]=r
    return res

def perfstat(c:Ctx,exe,name,cpus,tag)->dict:
    st=c.scratch/f'{tag}.perfstat.csv'
    rec,o,lg=c.run(exe,name,cpus,tag,pre=[c.a.perf,'stat','-x,','-o',str(st),'-e','cycles,instructions,task-clock','--'],wait_policy='passive');o.unlink()
    txt=st.read_text();shutil.copy(st,c.out/st.name);s=bk.parse_perf_stat_csv(txt);rec['perf_stat']=s
    d=(s or{}).get('derived')or{};rec['ipc']=d.get('ipc')
    if rec['ipc']is None:
        ev=(s or{}).get('events')or{}
        try:rec['ipc']=ev['instructions']['value']/ev['cycles']['value']
        except Exception:pass
    return rec

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True)
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--threads',type=int,default=64);p.add_argument('--scratch')
    p.add_argument('--prof');p.add_argument('--perf',default='perf');p.add_argument('--budget-seconds',type=float,default=1500)
    a=p.parse_args();t0=time.time();c=Ctx(a)
    rec={'schema':'c8-d2-r3a-speed-1','host':os.uname().nodename,'baseline':{'path':a.baseline,'sha256':digest(Path(a.baseline))},
         'candidate':{'path':a.candidate,'sha256':digest(Path(a.candidate))},'threads':a.threads,'repeats':a.repeats,
         'sockets':[[min(s),max(s)]for s in c.sockets],'identity':bk.identity({'baseline':Path(a.baseline),'candidate':Path(a.candidate)},perf=a.perf)}
    try:
        rec['phase1']=phase1(c);log('phase 1 done: '+json.dumps({k:(round(v['speedup_integration'],4),v['rows_identical'])for k,v in rec['phase1'].items()}))
        jobs=[(Path(a.candidate).resolve(),'heavy_free_L8',c.sockets[0],'ipc.candidate'),(Path(a.baseline).resolve(),'heavy_free_L8',c.sockets[1],'ipc.baseline')]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
            ipc=list(pool.map(lambda j:perfstat(c,*j),jobs))
        rec['phase2']={'candidate':ipc[0],'baseline':ipc[1],'rule':'R3c is attempted only if the candidate IPC is below 1.5'}
        log(f'phase 2: IPC candidate {ipc[0]["ipc"]}, baseline {ipc[1]["ipc"]}')
        if a.prof and Path(a.prof).exists()and time.time()-t0<a.budget_seconds:
            jobs=[('heavy_free_L8',c.sockets[0]),('heavy_power_L8',c.sockets[1])]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
                tt=list(pool.map(lambda j:c.run(Path(a.prof).resolve(),j[0],j[1],f'{j[0]}.prof')[0],jobs))
            rec['phase3']={'executable':{'path':a.prof,'sha256':digest(Path(a.prof))},'runs':tt}
            log('phase 3 tier timers done')
        else:rec['phase3']={'skipped':'no --prof executable or over the time budget'}
    finally:
        rec['wall_seconds']=round(time.time()-t0,1);(c.out/'r3a_speed.json').write_text(json.dumps(rec,indent=1)+'\n')
        for f in c.scratch.glob('*.log'):shutil.copy(f,c.out/f.name)
        shutil.rmtree(c.scratch,ignore_errors=True)
    ok=all(v['rows_identical']for v in rec['phase1'].values())
    print(json.dumps({'speedup':{k:v['speedup_integration']for k,v in rec['phase1'].items()},'rows_identical':ok,
                      'ipc':{k:rec['phase2'][k]['ipc']for k in ('candidate','baseline')}},indent=1))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
