#!/usr/bin/env python3
"""Stage 4b R4f (development probe): the same worker source linked against different GMP builds, compared on the
frozen Stage-4a fixture blocks (benchmarks/fixtures8, staged from the pinned packs exactly as tools/benchkit.py does).

  r4f_bench.py speed --package PKG --exe baseline=PATH --exe fat=PATH --exe zen2=PATH --output DIR
                     [--blocks heavy_free_L8,heavy_power_L8] [--threads 64] [--repeats 3] [--deadline 1620]
      One NUMA-aligned set of --threads physical cores per block (benchkit.partition; on an exclusive Expanse node the
      two sockets), the blocks side by side, each in its own lane. In each lane, repeat r runs every executable once,
      in the order of the --exe list rotated by r (so no executable always runs first or last). Wall, integration and
      load seconds, task seconds, RSS and the rows digest of every run; per (block, executable) the median of the
      repeats and the speedup of each executable over the first one (baseline). Every run of a block must give the
      same rows digest (all scientific fields of all rows). A run is not started when the lane's previous run says it
      would end after --deadline seconds from the start (recorded as skipped). The record is rewritten after every run.
  r4f_bench.py profile --package PKG --exe baseline=PATH --exe fat=PATH [--prof baseline=PATH --prof fat=PATH]
                       --output DIR [--blocks ...] [--stride 8] [--threads all] [--perf perf]
      Every --stride-th task of each block, at --threads threads on the job's cores: `perf record -F 999 -N` of each
      --exe, then `perf report --no-children --stdio -n` (--sort symbol and --sort dso,symbol), parsed by benchkit: the
      plan's shares, the top 40 symbols and every libgmp symbol; and each --prof executable (make profile: tier timers)
      run plainly for the first-pass / binary128 / MP split. Rows digests must agree across all runs of a block.
Dry runs (tests/test_gmp_prefix.py, with the fake worker): --fixtures DIR --fake-topology SxNxC --no-pin.
Exit 0 when every run succeeded and the rows agree, 1 otherwise (the record says why).
"""
from __future__ import annotations
import argparse,json,math,os,re,shutil,statistics,subprocess,sys,tempfile,threading,time
from pathlib import Path

def log(msg):print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def setup(pkg:Path):
    sys.path.insert(0,str(pkg/'tools'))
    import benchkit as bk
    from common import load
    return bk,load

def parse_exes(items):
    out={}
    for it in items or[]:
        name,_,path=it.partition('=')
        if not name or not path or name in out:raise SystemExit(f'bad or repeated --exe/--prof {it!r} (NAME=PATH)')
        p=Path(path).resolve()
        if not p.is_file():raise SystemExit(f'{p} does not exist')
        out[name]=p
    return out

class Run:
    def __init__(self,a,mode):
        self.a=a;self.bk,self.load=setup(Path(a.package).resolve());bk=self.bk
        self.m=bk.load_fixtures(Path(a.fixtures))if a.fixtures else bk.load_fixtures();self.I=self.m['_inputs'];self.inv=self.load(self.I.where('inventory.json'));self.gamma=self.I.where(bk.GAMMA)
        self.out=Path(a.output).resolve()
        if self.out.exists():raise SystemExit(f'{self.out} exists')
        self.out.mkdir(parents=True)
        base=Path(a.scratch or os.environ.get('TMPDIR')or tempfile.gettempdir());self.scratch=Path(tempfile.mkdtemp(prefix=f'r4f_{mode}_',dir=base))
        self.blocks={};self.pin=not a.no_pin
        if a.fake_topology and self.pin:raise SystemExit('--fake-topology needs --no-pin (dry runs only)')
        self.cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores()
    def block(self,name):
        if name not in self.blocks:
            b=self.bk.block_of(self.m,name);g=self.scratch/'graphs'/name
            b['staging']=self.bk.stage_graphs(self.I,self.inv,b['sector'],b['L'],b['graphs'],g);b['graphs_root']=str(g);self.blocks[name]=b
        return self.blocks[name]
    def cmd(self,exe,b,out,threads,tasks=None):
        n=self.m['native']
        return self.bk.native_cmd(exe,b['graphs_root'],self.gamma,b['net_path'],tasks or b['tasks_path'],out,b['native_seed'],n['layout'],n['rate'],threads,n['sum_mode'])
    def native(self,cmd,cpus,threads,out:Path,logf:Path,prefix=()):
        out.unlink(missing_ok=True);t0=time.perf_counter()
        with open(logf,'w')as lf:
            cp=subprocess.run([*prefix,*cmd],stdout=lf,stderr=subprocess.STDOUT,env=self.bk.omp_env(threads),preexec_fn=self.bk.pinner(cpus,self.pin))
        wall=time.perf_counter()-t0
        if cp.returncode or not out.is_file():raise RuntimeError(f'exit {cp.returncode}: {Path(logf).read_text(errors="replace")[-800:]}')
        n=self.load(out);s=self.bk.native_summary(n,threads);s['rows_digest']=self.bk.combined_digest(self.bk.rows_digest(n['rows']));s['wall_seconds']=wall
        if n.get('tier_timers'):s['tier_timers']=n['tier_timers']
        out.unlink();return s,n

def maps_libgmp(pid:int)->list[str]:
    try:return sorted({ln.split()[-1]for ln in Path(f'/proc/{pid}/maps').read_text().splitlines()if 'libgmp'in ln})
    except OSError:return []

def speed(a)->int:
    R=Run(a,'speed');bk=R.bk;exes=parse_exes(a.exe);names=list(exes);blocks=[b for b in a.blocks.split(',')if b]
    lanes=bk.partition(R.cores,len(blocks),a.threads)
    ident=bk.identity({k:v for k,v in exes.items()});ident['fake_topology']=a.fake_topology;ident['pinned']=R.pin;t_start=time.time();lock=threading.Lock();runs=[];errors=[]
    for b in blocks:R.block(b)
    def record(stage):
        with lock:
            res={}
            for b in blocks:
                res[b]={}
                for x in names:
                    rs=[r for r in runs if r['block']==b and r['exe']==x and 'summary'in r]
                    w=[r['summary']['wall_seconds']for r in rs];ig=[r['summary']['integration_seconds']for r in rs]
                    res[b][x]={'runs':len(rs),'wall_seconds':w,'integration_seconds':ig,'median_wall':statistics.median(w)if w else None,
                               'median_integration':statistics.median(ig)if ig else None,'libgmp_mapped':sorted({p for r in rs for p in r.get('libgmp_mapped',[])})}
                base=res[b][names[0]]
                for x in names:
                    r=res[b][x]
                    r['speedup_wall']=base['median_wall']/r['median_wall']if base['median_wall']and r['median_wall']else None
                    r['speedup_integration']=base['median_integration']/r['median_integration']if base['median_integration']and r['median_integration']else None
                digs={r['summary']['rows_digest']for r in runs if r['block']==b and 'summary'in r}
                res[b]['_rows']={'digests':sorted(digs),'identical':len(digs)==1}
            rec={'schema':'c8-d2-r4f-speed-1','stage':stage,'identity':ident,'fixtures_manifest_sha256':R.m['_manifest_sha256'],
                 'settings':{'blocks':blocks,'threads':a.threads,'repeats':a.repeats,'deadline_seconds':a.deadline,'lanes':{b:lanes[i]for i,b in enumerate(blocks)},
                             'order':'repeat r runs the executables in --exe order rotated by r','scratch':str(R.scratch)},
                 'executables':{k:str(v)for k,v in exes.items()},'staging':{b:R.blocks[b]['staging']for b in blocks},
                 'runs':list(runs),'results':res,'errors':list(errors),'elapsed_seconds':time.time()-t_start,'written_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
            (R.out/'speed.json').write_text(json.dumps(rec,indent=1,default=str)+'\n');return rec
    def lane(i,b):
        cpus=lanes[i];blk=R.block(b);last={}
        for rep in range(a.repeats):
            order=names[rep%len(names):]+names[:rep%len(names)]
            for x in order:
                est=last.get(x,max(last.values())if last else 0.)
                if time.time()-t_start+est>a.deadline:
                    with lock:runs.append({'block':b,'rep':rep,'exe':x,'skipped':f'deadline: elapsed {time.time()-t_start:.0f} s + previous {est:.0f} s > {a.deadline} s'})
                    log(f'{b} rep {rep} {x}: SKIPPED (deadline)');continue
                out=R.scratch/f'{b}.{x}.{rep}.json';logf=R.out/f'{b}.{x}.{rep}.log'
                try:
                    log(f'{b} rep {rep} {x} on cores {cpus[0]}..{cpus[-1]}')
                    # The worker's own maps: which libgmp it really loaded (sampled once, after start-up).
                    n_out=out;cmd=R.cmd(exes[x],blk,n_out,a.threads)
                    n_out.unlink(missing_ok=True);t0=time.perf_counter()
                    with open(logf,'w')as lf:
                        p=subprocess.Popen(cmd,stdout=lf,stderr=subprocess.STDOUT,env=bk.omp_env(a.threads),preexec_fn=bk.pinner(cpus,R.pin))
                        mapped=[]
                        for _ in range(100):
                            time.sleep(0.2);mapped=maps_libgmp(p.pid)
                            if mapped or p.poll()is not None:break
                        rc=p.wait()
                    wall=time.perf_counter()-t0
                    if rc or not n_out.is_file():raise RuntimeError(f'exit {rc}: {logf.read_text(errors="replace")[-800:]}')
                    n=R.load(n_out);s=bk.native_summary(n,a.threads);s['rows_digest']=bk.combined_digest(bk.rows_digest(n['rows']));s['wall_seconds']=wall;n_out.unlink()
                    last[x]=wall
                    with lock:runs.append({'block':b,'rep':rep,'exe':x,'cpus':[cpus[0],cpus[-1]],'summary':s,'libgmp_mapped':mapped})
                    log(f'{b} rep {rep} {x}: wall {wall:.1f} s, integration {s["integration_seconds"]:.1f} s, libgmp {mapped}')
                except Exception as e:
                    with lock:errors.append(f'{b} rep {rep} {x}: {type(e).__name__}: {e}'[:1500]);runs.append({'block':b,'rep':rep,'exe':x,'error':str(e)[:1500]})
                    log(f'{b} rep {rep} {x}: FAILED {e}')
                record('running')
    ths=[threading.Thread(target=lane,args=(i,b))for i,b in enumerate(blocks)]
    for t in ths:t.start()
    for t in ths:t.join()
    rec=record('final');shutil.rmtree(R.scratch,ignore_errors=True)
    bad=errors or not all(rec['results'][b]['_rows']['identical']for b in blocks)
    for b in blocks:
        for x in names:
            r=rec['results'][b][x];log(f'{b} {x}: median wall {r["median_wall"]}, speedup {r["speedup_wall"]}, runs {r["runs"]}')
        log(f'{b}: rows identical across all runs: {rec["results"][b]["_rows"]["identical"]}')
    return 1 if bad else 0

FAT_SUFFIX=re.compile(r'_(?:k8|k10|bd1|bd2|bd4|bt1|bt2|zen|zen2|core2|coreinhm|coreisbr|coreihwl|coreibwl|skylake|atom|silvermont|goldmont|nano|pentium4|x86_64|fat|init)$')
def gmp_table(dso_rows,bk)->dict:
    """Every libgmp symbol of a dso,symbol report (percent of all samples), and the same grouped by the function with a
    fat build's per-CPU suffix removed."""
    rows=[r for r in dso_rows if r['dso']and 'libgmp'in r['dso']and r['symbol']is not None]
    syms={};fun={}
    for r in rows:
        s=bk.base_symbol(r['symbol']);syms[s]=syms.get(s,0.)+r['overhead'];f=FAT_SUFFIX.sub('',s);fun[f]=fun.get(f,0.)+r['overhead']
    srt=lambda d:[{'symbol':k,'percent':round(v,4)}for k,v in sorted(d.items(),key=lambda kv:-kv[1])]
    return {'libgmp_total':round(sum(syms.values()),4),'symbols':srt(syms),'functions':srt(fun)}

def profile(a)->int:
    R=Run(a,'profile');bk=R.bk;exes=parse_exes(a.exe);profs=parse_exes(a.prof);blocks=[b for b in a.blocks.split(',')if b]
    cpus=[c for _s,_n,c in R.cores];threads=len(cpus)if a.threads=='all'else int(a.threads);cpus=cpus[:threads]
    ident=bk.identity({**exes,**{f'{k}_prof':v for k,v in profs.items()}},a.perf);ident['fake_topology']=a.fake_topology;ident['pinned']=R.pin;res={};errors=[]
    def write(stage):
        rec={'schema':'c8-d2-r4f-profile-1','stage':stage,'identity':ident,'fixtures_manifest_sha256':R.m['_manifest_sha256'],
             'settings':{'blocks':blocks,'stride':a.stride,'threads':threads,'cpus':cpus,'freq':a.freq},'executables':{k:str(v)for k,v in exes.items()},
             'prof_executables':{k:str(v)for k,v in profs.items()},'results':res,'errors':errors,'written_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        (R.out/'profile.json').write_text(json.dumps(rec,indent=1,default=str)+'\n');return rec
    for b in blocks:
        blk=R.block(b);_o,L,rows=bk.read_tasks(blk['tasks_path']);sub=[r for i,r in enumerate(rows)if i%a.stride==0]
        tasks=R.scratch/f'{b}.sub.tasks';bk.write_tasks(tasks,8,L,sub);res[b]={'tasks':len(sub),'of':len(rows),'perf':{},'tiers':{}}
        for x,exe in exes.items():
            data=R.scratch/f'{b}.{x}.perf.data'
            try:
                log(f'perf record {b} {x} ({len(sub)} tasks, {threads} threads)')
                s,_n=R.native(R.cmd(exe,blk,R.scratch/'o.json',threads,tasks),cpus,threads,R.scratch/'o.json',R.out/f'{b}.{x}.perf_record.log',
                              prefix=(a.perf,'record','-N','-F',str(a.freq),'-o',str(data),'--'))
                rep={}
                for tag,sort in (('symbol','symbol'),('dso_symbol','dso,symbol')):
                    cp=subprocess.run([a.perf,'report','-i',str(data),'--no-children','--stdio','-n','--sort',sort,'--percent-limit','0.01'],capture_output=True,text=True,timeout=1800)
                    f=R.out/f'{b}.{x}.perf_report_{tag}.txt';f.write_text(cp.stdout)
                    if cp.returncode:raise RuntimeError(f'perf report {sort}: {cp.stderr[-500:]}')
                    rep[tag]=bk.parse_perf_report(cp.stdout)
                dso_rows=rep['dso_symbol']['rows'];sym=bk.symbol_table(dso_rows)
                res[b]['perf'][x]={'native':s,'header':rep['dso_symbol']['header'],'shares':bk.perf_shares(dso_rows,Path(exe).name),'gmp':gmp_table(dso_rows,bk),
                                   'top40':[{k:t[k]for k in('symbol','overhead','samples','dsos')}for t in sym[:40]]}
                log(f'  {x}: wall {s["wall_seconds"]:.1f} s, libgmp {res[b]["perf"][x]["gmp"]["libgmp_total"]}% of samples')
            except Exception as e:errors.append(f'{b} perf {x}: {type(e).__name__}: {e}'[:1500]);log(f'{b} perf {x} FAILED: {e}')
            finally:data.unlink(missing_ok=True)
            write('running')
        for x,exe in profs.items():
            try:
                log(f'tier timers {b} {x}')
                s,n=R.native(R.cmd(exe,blk,R.scratch/'t.json',threads,tasks),cpus,threads,R.scratch/'t.json',R.out/f'{b}.{x}.prof.log')
                t=n.get('tier_timers')or{};secs={k:float(t.get(f'{k}_seconds',0))for k in('first_pass','quad','mp')};calls={k:int(t.get(f'{k}_calls',0))for k in('first_pass','quad','mp')}
                res[b]['tiers'][x]={'native':s,'seconds':secs,'calls':calls,'us_per_call':{k:(1e6*secs[k]/calls[k]if calls[k]else None)for k in secs}}
                log(f'  {x}: MP {res[b]["tiers"][x]["us_per_call"]["mp"]} us/call, binary128 {res[b]["tiers"][x]["us_per_call"]["quad"]} us/call')
            except Exception as e:errors.append(f'{b} tiers {x}: {type(e).__name__}: {e}'[:1500]);log(f'{b} tiers {x} FAILED: {e}')
            write('running')
        digs={v['native']['rows_digest']for v in res[b]['perf'].values()}|{v['native']['rows_digest']for v in res[b]['tiers'].values()}
        res[b]['rows']={'digests':sorted(digs),'identical':len(digs)==1}
        base=next(iter(profs),None)
        if base in res[b]['tiers']:
            bt=res[b]['tiers'][base]['us_per_call']
            for x,v in res[b]['tiers'].items():v['speedup_per_call']={k:(bt[k]/v['us_per_call'][k]if bt[k]and v['us_per_call'][k]else None)for k in bt}
    rec=write('final');shutil.rmtree(R.scratch,ignore_errors=True)
    bad=errors or not all(res[b]['rows']['identical']for b in blocks)
    return 1 if bad else 0

def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sp=p.add_subparsers(dest='mode',required=True)
    for m in('speed','profile'):
        q=sp.add_parser(m);q.add_argument('--package',required=True);q.add_argument('--exe',action='append',required=True);q.add_argument('--output',required=True)
        q.add_argument('--blocks',default='heavy_free_L8,heavy_power_L8');q.add_argument('--scratch');q.add_argument('--fixtures',help='fixture folder (default benchmarks/fixtures8)')
        q.add_argument('--fake-topology',help='SxNxC: dry runs on a machine without the topology (needs --no-pin)');q.add_argument('--no-pin',action='store_true')
        if m=='speed':q.add_argument('--threads',type=int,default=64);q.add_argument('--repeats',type=int,default=3);q.add_argument('--deadline',type=float,default=1620.)
        else:q.add_argument('--prof',action='append');q.add_argument('--stride',type=int,default=8);q.add_argument('--threads',default='all');q.add_argument('--perf',default='perf');q.add_argument('--freq',type=int,default=999)
    a=p.parse_args()
    return speed(a)if a.mode=='speed'else profile(a)

if __name__=='__main__':sys.exit(main())
