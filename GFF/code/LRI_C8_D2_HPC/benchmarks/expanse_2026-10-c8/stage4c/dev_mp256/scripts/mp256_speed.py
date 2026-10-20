#!/usr/bin/env python3
"""R4b `mp256` development speed comparison on one exclusive Expanse compute node (Stage 4c; PLAN A-FLAG-3/5, D1).
The F4 gate measurement on the L8 sweep sample belongs to the gate agent. Run from the package root of an export built
by stage4c/scripts/s4c_build.slurm (bin/c8d2_gmp and bin/c8d2_gmp_mp256 present).

  mp256_speed.py --output DIR [--exact bin/c8d2_gmp] [--profile bin/c8d2_gmp_mp256] [--repeats 3] [--threads 64]
                 [--scratch DIR] [--timer-stride 1] [--budget-seconds 1500]

Phase 0: the tier-timer variants of both executables are compiled into the scratch directory, each with its own build
record's command plus -DC8_TIER_TIMERS after -DC8_USE_GMP (for bin/c8d2_gmp this is `make profile`'s command); the
graphs of heavy_free_L8 and heavy_power_L8 (benchmarks/fixtures8: 256 tasks x 16,384 points each, the 128 heaviest
L8 graphs per sector) are staged from the pinned packs.
Phase 1 (speed): the two sockets in parallel, socket 0 on heavy_free_L8 and socket 1 on heavy_power_L8, each running
--repeats rounds of both executables (order exact, mp256 in even rounds and mp256, exact in odd ones) at --threads
threads pinned to the socket's cores (OMP_PROC_BIND=close, OMP_PLACES=cores, as the production lanes). Per run: the
native integration_seconds, the wall time, the rows digest (tools/benchkit.py, every scientific field), the quad and
mp counters, and the mp256 tier's own count of accepted and escalated MP evaluations (its stderr line at exit). Per
block: the medians, the speedups (exact median over mp256 median), whether every repeat of one executable gives the
same rows, and the comparison of the two executables' rows (identical rows; per row the normalized difference
max_j |dv_j|/max(1, |v_j|) and the relative one; the quad and mp counters must agree).
Phase 2 (per tier; within the budget): the two tier-timer variants on the same blocks (every --timer-stride-th task),
socket-parallel: seconds and calls per tier, so microseconds per call of the first pass, the binary128 tier and the MP
tier (for mp256: the 77-digit evaluation plus, for an escalated point, the 350-digit one), the MP-tier speedup and the
time shares. Their rows must equal the non-timer executables' rows on the same tasks.
Writes DIR/mp256_speed.json, the logs, and the first round's native JSON of each executable (gzip). Exit 0 when every
executable's repeats are identical and the counters agree, 1 otherwise.
"""
from __future__ import annotations
import argparse,concurrent.futures,gzip,json,math,os,re,shutil,statistics,subprocess,sys,tempfile,time
from decimal import Decimal as D
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
import benchkit as bk
from common import digest,load

BLOCKS=('heavy_free_L8','heavy_power_L8')
COUNTER=re.compile(r'^mp256 tier: (\d+) MP evaluations: (\d+) accepted at (\d+) digits, (\d+) escalated to 350 digits \(ratio ([^)]+)\)$',re.M)

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def timer_command(exe:Path,out:Path)->list[str]:
    """exe's build-record command with -DC8_TIER_TIMERS after -DC8_USE_GMP and out as the output."""
    cmd=list(load(exe.with_name(exe.name+'.build.json'))['command'])
    if cmd.count('-DC8_USE_GMP')!=1 or '-o'not in cmd:raise SystemExit(f'{exe}: unexpected build command {cmd}')
    cmd.insert(cmd.index('-DC8_USE_GMP')+1,'-DC8_TIER_TIMERS');cmd[cmd.index('-o')+1]=str(out);return cmd

class Ctx:
    def __init__(self,a):
        self.a=a;self.m=bk.load_fixtures();self.I=self.m['_inputs'];self.inv=load(self.I.where('inventory.json'))
        self.gamma=self.I.where(bk.GAMMA);self.out=Path(a.output).resolve();self.out.mkdir(parents=True)
        self.scratch=Path(tempfile.mkdtemp(prefix='c8d2_mp256_speed_',dir=a.scratch or tempfile.gettempdir()));self.blocks={}
        self.sockets=bk.partition(bk.host_cores(),2,a.threads)
    def block(self,name):
        if name not in self.blocks:
            b=bk.block_of(self.m,name);g=self.scratch/'graphs'/name
            b['staging']=bk.stage_graphs(self.I,self.inv,b['sector'],b['L'],b['graphs'],g);b['graphs_root']=str(g);self.blocks[name]=b
        return self.blocks[name]
    def run(self,exe,name,cpus,tag,tasks=None):
        b=self.block(name);n=self.m['native'];o=self.scratch/f'{tag}.json';lg=self.scratch/f'{tag}.log'
        if o.exists():o.unlink()
        cmd=bk.native_cmd(exe,b['graphs_root'],self.gamma,b['net_path'],tasks or b['tasks_path'],o,b['native_seed'],n['layout'],n['rate'],self.a.threads,n['sum_mode'])
        t0=time.perf_counter()
        with open(lg,'w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=bk.omp_env(self.a.threads),preexec_fn=bk.pinner(cpus),timeout=3600)
        wall=time.perf_counter()-t0;text=lg.read_text()
        if cp.returncode:raise RuntimeError(f'{tag}: exit {cp.returncode}: {text[-1500:]}')
        nat=json.loads(o.read_text());rows=nat['rows'];c=COUNTER.findall(text)
        rec={'tag':tag,'executable':str(exe),'numerics':nat.get('numerics'),'integration_seconds':nat['integration_seconds'],'load_seconds':nat['load_seconds'],
             'wall_seconds':round(wall,3),'rows':len(rows),'points':sum(r['end']-r['begin']for r in rows),'quad':sum(r['quad']for r in rows),'mp':sum(r['mp']for r in rows),
             'rows_digest':bk.combined_digest(bk.rows_digest(rows)),'cpus':[min(cpus),max(cpus)],'threads':self.a.threads}
        if c:
            tot,acc,dig,esc,ratio=c[-1];rec['mp256_tier']={'mp_evaluations':int(tot),'accepted':int(acc),'escalated':int(esc),'digits10':int(dig),'ratio':ratio,
                                                         'escalated_fraction':int(esc)/int(tot)if int(tot)else None}
        if 'tier_timers'in nat:rec['tier_timers']=nat['tier_timers']
        return rec,o,lg

def compare_rows(e:dict,p:dict)->dict:
    """Row-by-row comparison of the exact and the mp256 native outputs of the same tasks."""
    pr={r['uid']:r for r in p['rows']};ident=0;counters_equal=True;nd=[];rd=[];dmax=D(0);changed=[]
    for r in e['rows']:
        q=pr.pop(r['uid'])
        if (r['quad'],r['mp'])!=(q['quad'],q['mp']):counters_equal=False
        same=bk.rows_digest([r])[0][2]==bk.rows_digest([q])[0][2];ident+=same
        n_=r_=D(0)
        for a,b in zip(r['values'],q['values']):
            x,y=D(a),D(b);d=abs(y-x)
            if d:n_=max(n_,d/max(D(1),abs(x)));r_=max(r_,d/abs(x)if x else D('Infinity'))
        nd.append(n_);rd.append(r_)
        if not same and len(changed)<20:changed.append({'uid':r['uid'],'graph':r['graph'],'normalized':str(n_),'relative':str(r_)})
    if pr:raise RuntimeError(f'{len(pr)} rows only in the mp256 output')
    return {'rows':len(e['rows']),'identical_rows':ident,'counters_equal':counters_equal,'max_normalized_difference':str(max(nd,default=D(0))),
            'max_relative_difference':str(max(rd,default=D(0))),'rows_with_value_difference':sum(1 for x in nd if x),'first_changed_rows':changed}

def phase1(c:Ctx)->dict:
    a=c.a;exes={'exact':Path(a.exact).resolve(),'mp256':Path(a.profile).resolve()};res={}
    def seq(name,cpus):
        runs=[];keep={}
        for r in range(a.repeats):
            for v in (('exact','mp256')if r%2==0 else('mp256','exact')):
                tag=f'{name}.{v}.r{r}';log(f'start {tag} on cpus {min(cpus)}-{max(cpus)}');rec,o,lg=c.run(exes[v],name,cpus,tag);rec['variant']=v;rec['round']=r;runs.append(rec)
                log(f'{tag}: integration {rec["integration_seconds"]:.2f} s, wall {rec["wall_seconds"]:.2f} s, digest {rec["rows_digest"][:12]}'
                    +(f', mp256 tier {rec["mp256_tier"]}'if 'mp256_tier'in rec else''))
                shutil.copy(lg,c.out/lg.name)
                if r==0:keep[v]=o
                else:o.unlink()
        cmp=compare_rows(json.loads(keep['exact'].read_text()),json.loads(keep['mp256'].read_text()))
        for v,o in keep.items():
            with open(o,'rb')as f,gzip.open(c.out/f'{name}.{v}.native.json.gz','wb')as g:shutil.copyfileobj(f,g)
        med={v:statistics.median(x['integration_seconds']for x in runs if x['variant']==v)for v in exes}
        wmed={v:statistics.median(x['wall_seconds']for x in runs if x['variant']==v)for v in exes}
        dig={v:sorted({x['rows_digest']for x in runs if x['variant']==v})for v in exes}
        tiers=[x['mp256_tier']for x in runs if x['variant']=='mp256'and 'mp256_tier'in x]
        return name,{'runs':runs,'median_integration_seconds':med,'median_wall_seconds':wmed,
                     'integration_seconds':{v:[x['integration_seconds']for x in runs if x['variant']==v]for v in exes},
                     'speedup_integration':med['exact']/med['mp256'],'speedup_wall':wmed['exact']/wmed['mp256'],
                     'rows_repeatable':{v:len(d)==1 for v,d in dig.items()},'rows_identical_between_executables':dig['exact']==dig['mp256'],
                     'rows_comparison':cmp,'mp256_tier':tiers[0]if tiers and all(t==tiers[0]for t in tiers)else tiers,
                     'staging':c.blocks[name]['staging'],'predicted_cost_model_seconds':c.blocks[name]['predicted'].get('cost_model_seconds')}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        for name,r in pool.map(lambda x:seq(*x),((BLOCKS[0],c.sockets[0]),(BLOCKS[1],c.sockets[1]))):res[name]=r
    return res

def per_call(t:dict)->dict:
    out={}
    for k in ('first_pass','quad','mp'):
        s,n=t[f'{k}_seconds'],t[f'{k}_calls'];out[k]={'seconds':s,'calls':n,'us_per_call':1e6*s/n if n else None}
    tot=sum(out[k]['seconds']for k in out)
    for k in out:out[k]['share']=out[k]['seconds']/tot if tot else None
    return out

def phase2(c:Ctx,tools:dict,p1:dict)->dict:
    a=c.a;res={}
    def one(name,cpus):
        b=c.block(name);order,L,rows=bk.read_tasks(Path(b['tasks_path']));sub=rows[::a.timer_stride];tf=c.scratch/f'{name}.timers.tasks';bk.write_tasks(tf,order,L,sub)
        out={'tasks':len(sub),'stride':a.timer_stride}
        for v in (('exact','mp256')):
            rec,o,lg=c.run(tools[v],name,cpus,f'{name}.{v}.timers',tasks=tf);shutil.copy(lg,c.out/lg.name)
            nat=json.loads(o.read_text());o.unlink()
            ref=json.loads(gzip.open(c.out/f'{name}.{v}.native.json.gz','rt').read());want={r['uid']:bk.rows_digest([r])[0][2]for r in ref['rows']}
            rec['rows_equal_non_timer']=all(want.get(r['uid'])==bk.rows_digest([r])[0][2]for r in nat['rows'])
            rec['per_call']=per_call(rec['tier_timers']);out[v]=rec
            log(f'{name} {v} timers: '+', '.join(f'{k} {x["us_per_call"]:.1f} us x {x["calls"]} ({100*x["share"]:.1f}%)'for k,x in rec['per_call'].items()if x['us_per_call']))
        e,p=out['exact']['per_call'],out['mp256']['per_call']
        out['speedup_per_call']={k:(e[k]['us_per_call']/p[k]['us_per_call']if e[k]['us_per_call']and p[k]['us_per_call']else None)for k in e}
        out['speedup_tier_seconds']={k:(e[k]['seconds']/p[k]['seconds']if p[k]['seconds']else None)for k in e}
        out['speedup_thread_seconds']=sum(e[k]['seconds']for k in e)/sum(p[k]['seconds']for k in p)
        return name,out
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
        for name,r in pool.map(lambda x:one(*x),((BLOCKS[0],c.sockets[0]),(BLOCKS[1],c.sockets[1]))):res[name]=r
    return res

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output',required=True);p.add_argument('--exact',default='bin/c8d2_gmp');p.add_argument('--profile',default='bin/c8d2_gmp_mp256')
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--threads',type=int,default=64);p.add_argument('--scratch')
    p.add_argument('--timer-stride',type=int,default=1);p.add_argument('--budget-seconds',type=float,default=1500)
    a=p.parse_args();t0=time.time();c=Ctx(a)
    exes={'exact':Path(a.exact).resolve(),'mp256':Path(a.profile).resolve()}
    rec={'schema':'c8-d2-mp256-speed-1','host':os.uname().nodename,'executables':{k:{'path':str(v),'sha256':digest(v)}for k,v in exes.items()},
         'threads':a.threads,'repeats':a.repeats,'sockets':[[min(s),max(s)]for s in c.sockets],'identity':bk.identity(exes)}
    ok=False
    try:
        # phase 0: tier-timer variants (compiled while the graphs are staged)
        tools={k:c.scratch/f'{v.name}_timers'for k,v in exes.items()};cmds={k:timer_command(v,tools[k])for k,v in exes.items()}
        procs={k:subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)for k,cmd in cmds.items()}
        for b in BLOCKS:c.block(b)
        log('graphs staged: '+json.dumps({b:c.blocks[b]['staging']for b in BLOCKS}))
        comp={}
        for k,pr in procs.items():
            outp,_=pr.communicate();comp[k]={'command':cmds[k],'returncode':pr.returncode,'output':outp[-3000:]}
            if pr.returncode:raise RuntimeError(f'compiling the {k} tier-timer variant failed: {outp[-2000:]}')
            comp[k]['sha256']=digest(tools[k]);d=subprocess.run([str(tools[k]),'--describe'],capture_output=True,text=True,check=True);comp[k]['describe']=json.loads(d.stdout)
        rec['timer_variants']=comp;log('tier-timer variants compiled')
        rec['phase1']=p1=phase1(c)
        log('phase 1 done: '+json.dumps({k:(round(v['speedup_integration'],4),v['rows_repeatable'],v['rows_comparison']['identical_rows'])for k,v in p1.items()}))
        if time.time()-t0<a.budget_seconds:
            rec['phase2']=phase2(c,tools,p1);log('phase 2 done: '+json.dumps({k:v['speedup_per_call']for k,v in rec['phase2'].items()}))
        else:rec['phase2']={'skipped':f'over the time budget ({a.budget_seconds} s)'}
        ok=all(all(v['rows_repeatable'].values())and v['rows_comparison']['counters_equal']for v in p1.values())\
           and all(v[x]['rows_equal_non_timer']for v in rec['phase2'].values()if isinstance(v,dict)and 'exact'in v for x in ('exact','mp256'))
    except Exception as e:
        rec['error']=f'{type(e).__name__}: {e}';log(rec['error'])
    finally:
        rec['passed_checks']=ok;rec['wall_seconds']=round(time.time()-t0,1);(c.out/'mp256_speed.json').write_text(json.dumps(rec,indent=1)+'\n')
        shutil.rmtree(c.scratch,ignore_errors=True)
    if 'phase1'in rec:
        print(json.dumps({'speedup_integration':{k:v['speedup_integration']for k,v in rec['phase1'].items()},
                          'mp256_tier':{k:v['mp256_tier']for k,v in rec['phase1'].items()},
                          'identical_rows':{k:v['rows_comparison']['identical_rows']for k,v in rec['phase1'].items()},
                          'mp_speedup_per_call':{k:v.get('speedup_per_call',{}).get('mp')for k,v in rec.get('phase2',{}).items()if isinstance(v,dict)},'checks':ok},indent=1))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
