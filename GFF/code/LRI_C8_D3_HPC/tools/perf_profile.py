#!/usr/bin/env python3
"""Stage-4a profiles P1, P2 and P3, the MP self-check overhead and the f_E repeat (PLAN "Performance plan"; A-PERF-1) on
the frozen fixtures of benchmarks/fixtures8 (tools/prepare_benchmarks.py --order 8), C7(3)'s benchmarks/fixtures and
the Stage-3 baseline executables. Profiling only: no worker change.

Port to C8(3) of C62d's tools/perf_profile.py (LRI_C8_D2_HPC@651c56f, sha256 13bc832c...). The d=3 changes: names
(c8d3, -DC7_USE_GMP, the d=3 kernel's regions), every worker run with --mp-check (the fixtures' mode, on), the per-graph
tier timers of bin/c8d3_gmp_prof and the population re-weighting of the stratified P1 blocks (tier_split), the passive
OpenMP wait policy in P1 (an idle thread sleeps instead of spinning into the profile; --wait-policy), and two modes:
`mpcheck` (the MP self-check overhead, PLAN C.4) and `fe` (f_E against symmetry, A-PERF-1).

  perf_profile.py p1 --output DIR [--blocks strat_free_L7,strat_power_L7,strat_free_L8,strat_power_L8,heavy_free_L8,heavy_power_L8] [--threads 64]
  perf_profile.py p2 --output DIR [--blocks nopromo_free_L7,nopromo_free_L8,strat_free_L8] [--threads 64]
  perf_profile.py p3 --output DIR [--blocks random_free_L7,random_power_L7,random_free_L8,random_power_L8] [--rates .8,.7]
  perf_profile.py mpcheck --output DIR [--blocks strat_free_L7,strat_power_L7,strat_free_L8,strat_power_L8] [--threads 64]
  perf_profile.py fe --output DIR [--repeats 3]
  perf_profile.py p1-reparse --input P1DIR [--output FILE]   (offline: the perf summaries again from the saved reports)
Common options: --exe (default bin/c8d3_gmp), --expect-sha256 HEX, --scratch DIR (node-local; perf.data and staged graphs
stay there), --fixtures DIR, --perf PATH, --fake-topology SxNxC --no-pin (dry runs only; recorded as such).

P1 (time per function; tier split). The block runs at --threads threads on the first NUMA-aligned set of that many cores
(one socket of 4 NUMA nodes at 64 threads on an EPYC node) under `perf record -F 999 [-g] -N`; then the plan's
`perf report --no-children --sort symbol --stdio` (with -n), and --sort dso,symbol and --sort dso, parsed into the shares
the plan names (benchkit.perf_shares: __addtf3/__subtf3/__multf3/__divtf3, expq, sqrtq, __gmpf_*, __gmpn_*, malloc/free,
expl, sqrtl, MP -> long double conversion, calculate_reference<long double>, libgomp, kernel) and a top-40 table.
Concurrently, on the second set of cores (the other socket), bin/c8d3_gmp_prof (make profile, -DC8_TIER_TIMERS) runs the
same block: first pass / binary128 / MP seconds and calls (the tier split), in total and per graph; a stratified block
(strata and weights in its fixture record) is re-weighted to the population of its (sector, L). --sequential runs both
on the first set. Source lines
(best effort; the shift loop and calculate_reference<long double> are inlined code without a symbol of their own): a
debug-info twin of the worker (the Makefile's gmp command plus -g, built in the scratch directory) is used only when its
allocated sections (.text, .rodata, .data, ...) equal the baseline's byte for byte at the same addresses; then
`perf annotate --stdio` of the worker's symbols gives per-instruction samples, and addr2line on the twin maps them to
src/kernel.hpp lines and regions (shift loop, calculate_reference, calculate_products, calculate_shared, evaluate,
sample). -g is off by default: the --no-children self-time table does not use call chains, and at 64 threads -g writes
about 1 kB per sample (--call-graph fp to enable). Without perf (missing, or perf_event_paranoid refuses): the tier
timers alone plus `ltrace -c -e '__gmpf_*'` on one thread on a mini block (16 tasks x 64 points of the heaviest power L8
tasks), when ltrace exists.

P2 (is the first pass latency-bound?). `perf stat -x, -e cycles,instructions,branches,branch-misses,L1-dcache-loads,
L1-dcache-load-misses,task-clock` on the promotion-free blocks (no binary128 or MP point) at --threads threads, with
OMP_WAIT_POLICY=passive so barrier spinning does not count as work (--wait-policy default to keep libgomp's default),
plus one thread on the heaviest tasks of each block (--serial-seconds of predicted work); IPC = instructions/cycles.
The decision rule (R6 go if IPC < 1.5 or the interleave-probe speedup >= 1.2) uses tools/benchmark.py
--interleave-probe as the fallback and second measure.

P3 (margin distribution at the tests). bin/c8d3_gmp_ratiohist (make ratiohist) on the uniform-draw blocks at every
--rates value (campaign a .8, campaign b .7), on all cores: the log10(|v|/err) histograms at the 1e-9 test (failing
long-double points), the 1e-23 test (every binary128 evaluation) and the MP evaluations, per (sector, L, rate), with
consistency checks against the row counters and the fractions below 10^-k (benchkit.ratio_summary).

mpcheck (PLAN C.4: production keeps --mp-check on if its overhead is <= 3% of the total CPU, else stride16). Each block
runs bin/c8d3_gmp_prof three times, --mp-check on, off and stride16 (the order rotated per block), on one set of
--threads cores; with two sets the blocks are split between them (each block's three runs on the same set). The
overhead of a mode is (its task seconds - off's) / its task seconds, and the MP tier's share of it (the MP tier seconds
of the mode minus off's): the same points, the same MP calls, only the error accumulation differs (A-KER-7: the rows are
bitwise those of off apart from the self-check fields, checked). Re-weighted to the population like P1.

fe (A-PERF-1: f_E, EPYC 7742 against symmetry's EPYC 7532 per group, from C7(3)'s fixtures, benchmarks/fixtures, and
benchmarks/symmetry_2026-10/validation_567197/bench). C7(3)'s worker (bin/ref/c7d3_gmp, make c7ref: a6ce987's source
and command lines; symmetry ran the same source with GCC 11.4) and the C8 worker in order-7 mode (bin/c8d3_gmp, bitwise
the same rows, A-RPL-1) run each fixture with symmetry's exact arguments: (a) isolated, pinned to the first cores of
socket 0 with the rest of the node idle, at 1 thread (all four groups) and 2 and 4 threads (L7), --repeats times, the
matched comparison with symmetry's records; (b) at symmetry's lane width on one socket with the other socket idle: 64
single-thread copies at once, one per core of socket 0, so L3, memory bandwidth and the all-core clock are those of a
full 64-thread lane. f_E = Expanse integration seconds / symmetry's (median of the repeats; > 1 means Expanse is slower);
the loaded-socket factor = (b) / (a).
"""
from __future__ import annotations
import argparse,concurrent.futures,json,math,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import STRICT_CXXFLAGS,ROOT,cxx_command,digest,load,utc
import benchkit as bk

SCHEMA='c8-d3-prof-{}-1'
P2_EVENTS='cycles,instructions,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,task-clock'
DEFAULTS={'p1':'strat_free_L7,strat_power_L7,strat_free_L8,strat_power_L8,heavy_free_L8,heavy_power_L8','p2':'nopromo_free_L7,nopromo_free_L8,strat_free_L8',
          'p3':'random_free_L7,random_power_L7,random_free_L8,random_power_L8','mpcheck':'strat_free_L7,strat_power_L7,strat_free_L8,strat_power_L8'}

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def jdump(path:Path,obj)->None:Path(path).write_text(json.dumps(obj,indent=1,sort_keys=False,default=str)+'\n')

class Ctx:
    """Fixtures, inputs, cores, scratch and output of one run."""
    def __init__(self,a,mode:str):
        self.a=a;self.mode=mode;self.m=bk.load_fixtures(a.fixtures);self.I=self.m['_inputs'];self.inv=load(self.I.where('inventory.json'))
        self.gamma=self.I.where(bk.GAMMA);self.pin=not a.no_pin
        self.cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores()
        if a.fake_topology and self.pin:raise bk.BenchError(64,'--fake-topology needs --no-pin (the fake CPU numbers do not exist)')
        self.out=Path(a.output).resolve()
        if self.out.exists():raise bk.BenchError(64,f'{self.out} exists; give a new output directory')
        base=Path(a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir())
        self.out.mkdir(parents=True);self.scratch=Path(tempfile.mkdtemp(prefix=f'c8d3_{mode}_',dir=base))
        self.staged={}
    def block(self,name:str)->dict:
        """The fixture block with its graphs staged once into the scratch directory (timed). With --smoke-tasks N the
        block is cut to its first N tasks (uid order), each to its first --smoke-points points: a function test of the
        tools on a small allocation, never a measurement (recorded as 'smoke')."""
        if name not in self.staged:
            b=bk.block_of(self.m,name);g=self.scratch/'graphs'/name;ids=b['graphs']
            if getattr(self.a,'smoke_tasks',0):
                _o,L,rows=bk.read_tasks(b['tasks_path']);rows=sorted(rows)[:self.a.smoke_tasks]
                rows=[(u,rep,gid,lo,min(hi,lo+self.a.smoke_points),tot)for u,rep,gid,lo,hi,tot in rows]
                f=self.scratch/f'{name}.smoke.tasks';bk.write_tasks(f,8,L,rows);b['tasks_path']=str(f);b['tasks']=len(rows)
                ids=sorted({r[2]for r in rows});b['smoke']={'tasks':len(rows),'points_per_task_max':self.a.smoke_points}
                b['strata']={k:v for k,v in (b.get('strata')or{}).items()if int(k)in ids}or None
            b['staging']=bk.stage_graphs(self.I,self.inv,b['sector'],b['L'],ids,g);b['graphs_root']=str(g);self.staged[name]=b
        return self.staged[name]
    def cmd(self,exe,b:dict,out:Path,threads:int,tasks=None,rate=None,mp_check=None)->list[str]:
        n=self.m['native']
        return bk.native_cmd(exe,b['graphs_root'],self.gamma,b['net_path'],tasks or b['tasks_path'],out,b['native_seed'],n['layout'],rate or n['rate'],threads,n['sum_mode'],
                             mp_check or n.get('mp_check','on'))

def check_exe(path:Path,kind:str|None,expect:str|None=None)->dict:
    """The executable's identity; refuses a missing one, a wrong diagnostic kind, or a sha256 that does not start with
    --expect-sha256."""
    rec=bk.exe_identity(path)
    if not rec['present']:raise bk.BenchError(69,f'{path} is missing (make gmp / make profile / make ratiohist)')
    d=rec.get('describe')or{}
    if kind is None and d.get('diagnostic'):raise bk.BenchError(65,f'{path} is a diagnostic build ({d.get("diagnostic_kind")}); give the release worker')
    if kind is not None and d.get('diagnostic_kind')!=kind:raise bk.BenchError(65,f'{path}: diagnostic_kind {d.get("diagnostic_kind")!r}, expected {kind!r}')
    if expect and not rec['sha256'].startswith(expect.lower()):raise bk.BenchError(65,f'{path}: sha256 {rec["sha256"][:12]}... is not the expected {expect}')
    return rec

def run(cmd,cpus,threads:int,logf:Path,pin:bool,wait_policy=None,timeout=None)->dict:
    """One pinned process (the native, or perf/ltrace wrapping it); wall seconds, exit code, stderr tail."""
    t0=time.perf_counter()
    with open(logf,'w')as lf:
        cp=subprocess.run(cmd,stdout=lf,stderr=subprocess.STDOUT,env=bk.omp_env(threads,wait_policy=wait_policy),preexec_fn=bk.pinner(cpus,pin),timeout=timeout)
    wall=time.perf_counter()-t0;text=Path(logf).read_text(errors='replace')
    return {'cmd':cmd,'returncode':cp.returncode,'wall_seconds':wall,'cpus':sorted(cpus),'threads':threads,'log':str(logf),'log_tail':text[-1500:]}

def native_result(out:Path,threads:int,rec:dict)->dict:
    if rec['returncode']!=0 or not Path(out).is_file():raise RuntimeError(f'native run failed (exit {rec["returncode"]}): {rec["log_tail"][-800:]}')
    n=load(out);s=bk.native_summary(n,threads);s['rows_digest']=bk.combined_digest(bk.rows_digest(n['rows']));return {'summary':s,'native':n}

def perf_available(perf:str,scratch:Path)->dict:
    """Whether perf can count and sample this user's processes here (tried, not inferred from perf_event_paranoid)."""
    info={'perf':shutil.which(perf),'paranoid':bk.read_text('/proc/sys/kernel/perf_event_paranoid'),'version':bk.run_text([perf,'--version'])}
    if info['perf']is None:return {**info,'ok':False,'reason':f'{perf} not found on PATH'}
    for name,cmd in (('stat',[perf,'stat','-x,','-e','task-clock','--','true']),('record',[perf,'record','-N','-F','999','-o',str(scratch/'probe.data'),'--','true'])):
        try:cp=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        except (OSError,subprocess.SubprocessError)as e:return {**info,'ok':False,'reason':f'perf {name} probe: {e}'}
        if cp.returncode:return {**info,'ok':False,'reason':f'perf {name} probe exit {cp.returncode}: {cp.stderr.strip()[-600:]}'}
    return {**info,'ok':True,'reason':None}

def lanes_for(ctx:Ctx,threads:int)->tuple[list,list|None]:
    """The first NUMA-aligned set of `threads` cores, and the second one (None when it does not fit)."""
    a=bk.partition(ctx.cores,1,threads)[0]
    try:b=bk.partition(ctx.cores,2,threads)[1]
    except bk.BenchError:b=None
    return a,b

# ---------------------------------------------------------------- P1
def build_twin(dest:Path,cpus=None,pin:bool=False)->dict:
    """The Makefile's gmp compile command plus -g (debug info only): bin/c8d3_gmp's twin for source-line lookup."""
    # The Makefile's word order and relative source path, run from the package root (so __FILE__ strings match too).
    cmd=cxx_command(['src/c8d3_integrate.cpp'],dest,defines=('C7_USE_GMP',),libs=('-lquadmath','-lgmp'))
    cmd.insert(cmd.index(STRICT_CXXFLAGS[0]),'-g')
    t0=time.perf_counter();cp=subprocess.run(cmd,capture_output=True,text=True,timeout=1800,cwd=ROOT,preexec_fn=bk.pinner(cpus,pin and cpus is not None))
    return {'command':cmd,'returncode':cp.returncode,'seconds':time.perf_counter()-t0,'stderr':cp.stderr[-1500:]}

_SEC=re.compile(r'^\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]{8,})\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([A-Za-z]*)\s+\d+\s+\d+\s+\d+\s*$')
def alloc_sections(exe:Path)->dict:
    """readelf -S -W: {name: (type, address, size)} of the allocated, non-NOTE sections."""
    txt=bk.run_text(['readelf','-S','-W',str(exe)])
    if txt is None:raise RuntimeError('readelf unavailable')
    out={}
    for line in txt.splitlines():
        m=_SEC.match(line)
        if m and 'A'in m[7]and m[2]!='NOTE':out[m[1]]=(m[2],int(m[3],16),int(m[5],16))
    return out

def same_code(base:Path,twin:Path,tmp:Path)->dict:
    """Allocated sections equal by name, type, address, size and (non-NOBITS) content: then the twin's addresses and
    source lines describe the baseline's instructions."""
    sa,sb=alloc_sections(base),alloc_sections(twin);diffs=[]
    if sa!=sb:diffs.append('section table: '+', '.join(sorted(k for k in set(sa)|set(sb)if sa.get(k)!=sb.get(k))))
    for name,(typ,_addr,size)in sorted(sa.items()):
        if typ=='NOBITS'or size==0 or name not in sb:continue
        h=[]
        for exe,tag in ((base,'a'),(twin,'b')):
            f=tmp/f'sec_{tag}.bin';cp=subprocess.run(['objcopy','-O','binary',f'--only-section={name}',str(exe),str(f)],capture_output=True,text=True)
            if cp.returncode:raise RuntimeError(f'objcopy {name}: {cp.stderr.strip()[-300:]}')
            h.append(digest(f));f.unlink()
        if h[0]!=h[1]:diffs.append(f'{name} content')
    return {'identical':not diffs,'differences':diffs,'sections':sorted(sa)}

def kernel_regions(text:str)->dict:
    """Line ranges in src/kernel.hpp: the shift loop (evaluate's max-plus loop over g.masks) and the bodies of
    calculate_reference, calculate_products, calculate_shared, evaluate and sample (from the signature line to the
    first following line that is exactly '}')."""
    lines=text.splitlines();out={}
    for i,l in enumerate(lines,1):
        if 'for(auto mask:g.masks)'in l and 'shift=-std::numeric_limits'in l:out['shift_loop']=(i,i)
    for name,sig in (('calculate_reference','std::pair<T,T> calculate_reference('),('calculate_products','std::pair<ld,ld> calculate_products('),
                     ('calculate_shared','std::pair<T,T> calculate_shared('),('mp_check_record','inline void mp_check_record('),('evaluate','inline Eval evaluate('),
                     ('sample','std::array<ld,NLOGS> sample(')):
        for i,l in enumerate(lines,1):
            if sig in l:
                j=next((k for k in range(i,len(lines)+1)if lines[k-1].rstrip()=='}'),i);out[name]=(i,j);break
    return out

def srcline(perf:str,data:Path,exe:Path,twin:Path,total_samples:int,scratch:Path)->dict:
    """Per-instruction samples of the worker's symbols (perf annotate) mapped to source lines through the twin."""
    cp=subprocess.run([perf,'annotate','-i',str(data),'--stdio','-d',exe.name],capture_output=True,text=True,timeout=900)
    if cp.returncode:return {'status':'perf annotate failed','stderr':cp.stderr[-800:]}
    (scratch/f'annotate_{data.stem}.txt').write_text(cp.stdout)
    funcs=bk.parse_annotate(cp.stdout);share={}
    for f in funcs:
        for addr,pct in f['instructions'].items():share[addr]=share.get(addr,0.)+pct/100*f['samples']/max(1,total_samples)*100
    if not share:return {'status':'no annotated samples in the worker','functions':len(funcs)}
    q=''.join(f'{a:#x}\n'for a in sorted(share))
    cp=subprocess.run(['addr2line','-e',str(twin),'-a','-i','-f','-C'],input=q,capture_output=True,text=True,timeout=600)
    if cp.returncode:return {'status':'addr2line failed','stderr':cp.stderr[-800:]}
    where=bk.parse_addr2line(cp.stdout);regions=kernel_regions((ROOT/'src/kernel.hpp').read_text())
    by_line,by_func,by_region={},{},{k:0. for k in regions}
    for addr,pct in share.items():
        fr=where.get(addr)or[('??','??',None)];fn,fl,ln=fr[0];key=f'{Path(fl).name}:{ln}'
        by_line[key]=by_line.get(key,0.)+pct;by_func[fn]=by_func.get(fn,0.)+pct
        if Path(fl).name=='kernel.hpp'and ln is not None:
            for k,(lo,hi)in regions.items():
                if lo<=ln<=hi:by_region[k]+=pct
    top=lambda d:[{'where':k,'percent':round(v,4)}for k,v in sorted(d.items(),key=lambda kv:-kv[1])[:40]]
    return {'status':'ok','worker_percent_annotated':round(sum(share.values()),4),'functions_annotated':len(funcs),
            'kernel_regions_lines':{k:list(v)for k,v in regions.items()},'kernel_regions_percent':{k:round(v,4)for k,v in by_region.items()},
            'top_lines':top(by_line),'top_innermost_functions':top(by_func),
            'note':'percent of all samples of the block; innermost inlined frame of each sampled instruction (addr2line -i on the -g twin)'}

def perf_reports(perf:str,data:Path,out:Path,name:str,callgraph:bool)->dict:
    """The plan's report and two companions, parsed."""
    g=['-g','none']if callgraph else[];res={}
    specs=(('symbol',['--sort','symbol','--percent-limit','0.01']),('dso_symbol',['--sort','dso,symbol','--percent-limit','0.01']),('dso',['--sort','dso','--percent-limit','0']))
    for tag,extra in specs:
        cmd=[perf,'report','-i',str(data),'--no-children','--stdio','-n',*extra,*g]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
        f=out/f'{name}.perf_report_{tag}.txt';f.write_text(cp.stdout)
        if cp.returncode:raise RuntimeError(f'perf report --sort {tag} failed: {cp.stderr[-600:]}')
        res[tag]={'command':cmd,'file':f.name,'parsed':bk.parse_perf_report(cp.stdout)}
    hdr=subprocess.run([perf,'report','-i',str(data),'--header-only'],capture_output=True,text=True,timeout=600)
    (out/f'{name}.perf_header.txt').write_text(hdr.stdout)
    return res

def report_summary(rp:dict,worker:str)->dict:
    """The P1 'perf' record of one block from its three parsed reports (perf_reports' result): totals, the plan's shares
    (benchkit.perf_shares on the dso,symbol report, and on the symbol report), the top-40 symbols and the DSO table."""
    dso_rows=rp['dso_symbol']['parsed']['rows'];total=sum(r['samples']or 0 for r in rp['dso']['parsed']['rows'])
    sym=bk.symbol_table(dso_rows)
    return {'reports':{k:{'command':v['command'],'file':v['file'],'header':v['parsed']['header']}for k,v in rp.items()},'total_samples':total,
            'shares':bk.perf_shares(dso_rows,worker),'shares_from_symbol_report':bk.perf_shares(rp['symbol']['parsed']['rows'],None),
            'top40':[{k:s[k]for k in('symbol','overhead','samples','dsos')}for s in sym[:40]],'dso':bk.dso_table(rp['dso']['parsed']['rows'])[:20]}

def p1_reparse(a)->int:
    """Rebuild every block's 'perf' summary of a finished P1 record from the report texts saved beside it, with the
    current parser (no perf, no worker, no cluster). Everything else of the record is kept; the result goes to
    --output (default <input>/p1_reparsed.json), never over the original p1.json."""
    d=Path(a.input).resolve();src=d/'p1.json'
    if not src.is_file():raise bk.BenchError(69,f'{src} is missing')
    rec=json.loads(src.read_text());worker=Path(((rec.get('identity')or{}).get('executables')or{}).get('worker',{}).get('path')or'c8d3_gmp').name
    out=Path(a.output).resolve()if a.output else d/'p1_reparsed.json'
    if out.exists()or out==src:raise bk.BenchError(64,f'{out} exists (or is the input); give a new output file')
    done=[]
    for b,x in rec['blocks'].items():
        old=x.get('perf')
        if not isinstance(old,dict)or 'reports'not in old:continue
        rp={}
        for tag,info in old['reports'].items():
            f=d/info['file']
            if not f.is_file():raise bk.BenchError(69,f'{f} is missing: the saved perf report of {b} ({tag})')
            rp[tag]={'command':info['command'],'file':info['file'],'parsed':bk.parse_perf_report(f.read_text())}
        new=report_summary(rp,worker)
        if old.get('total_samples')is not None and new['total_samples']!=old['total_samples']:raise bk.BenchError(65,f'{b}: {new["total_samples"]} samples now, {old["total_samples"]} in the record')
        x['perf']={**old,**new};done.append(b)
    if not done:raise bk.BenchError(65,f'{src}: no block has saved perf reports')
    rec['reparsed']={'utc':utc(),'from':str(src),'from_sha256':digest(src),'blocks':done,'parser_package_commit':bk.package_commit(),
                     'note':'perf summaries rebuilt from the saved report texts by perf_profile.py p1-reparse; runs, tier timers and source lines unchanged'}
    jdump(out,rec);log(f'wrote {out} ({len(done)} blocks reparsed)');return 0

TIERS=('first_pass','quad','mp')
def per_graph_table(n:dict)->dict:
    """{graph: {'points', 'task_seconds', 'seconds': {tier: s}, 'calls': {tier: n}}} from the rows and the per-graph tier
    timers of a bin/c8d3_gmp_prof run."""
    t=n.get('tier_timers')or{};pg=t.get('per_graph')or{};out={}
    for r in n['rows']:
        g=out.setdefault(str(r['graph']),{'points':0,'task_seconds':0.,'quad':0,'mp':0})
        g['points']+=r['end']-r['begin'];g['task_seconds']+=float(r['seconds']);g['quad']+=r['quad'];g['mp']+=r['mp']
    for gid,v in pg.items():
        g=out.setdefault(str(gid),{'points':0,'task_seconds':0.,'quad':0,'mp':0})
        g['seconds']={k:float(v[i])for i,k in enumerate(TIERS)};g['calls']={k:int(v[3+i])for i,k in enumerate(TIERS)}
    return out

def reweighted(table:dict,strata:dict|None)->dict|None:
    """Population estimate of the tier split per point: sum_g w_g x (seconds_g / points_g) per tier and for the task
    time, over the graphs of a stratified block (w_g its fixture weight); None without weights."""
    if not strata or any((strata.get(g)or{}).get('weight')is None for g in table):return None
    acc={k:0. for k in (*TIERS,'task')};calls={k:0. for k in TIERS};W=0.
    for g,v in table.items():
        w=float(strata[g]['weight']);p=v['points']
        if not p or 'seconds'not in v:return None
        W+=w;acc['task']+=w*v['task_seconds']/p
        for k in TIERS:acc[k]+=w*v['seconds'][k]/p;calls[k]+=w*v['calls'][k]/p
    task=acc['task']
    return {'graphs':len(table),'weight_sum':W,'task_seconds_per_point':task/W,
            'tier_seconds_per_point':{k:acc[k]/W for k in TIERS},'calls_per_point':{k:calls[k]/W for k in TIERS},
            'share_of_task_time':{**{k:acc[k]/task for k in TIERS},'other':1-math.fsum(acc[k]for k in TIERS)/task},
            'microseconds_per_call':{k:(1e6*acc[k]/calls[k]if calls[k]else None)for k in TIERS},
            'rule':'sum over the block\'s graphs of weight x (seconds / points), weights from the fixture strata (graphs of the population each stands for)'}

def tier_split(n:dict,strata:dict|None=None)->dict:
    t=n.get('tier_timers')or{};secs={k:float(t.get(f'{k}_seconds',0))for k in TIERS};tot=math.fsum(secs.values())
    thread_time=float(n['integration_seconds'])*int(n['threads']);task=math.fsum(float(r['seconds'])for r in n['rows'])
    calls={k:int(t.get(f'{k}_calls',0))for k in TIERS};table=per_graph_table(n)
    return {'seconds':secs,'calls':calls,'task_seconds':task,
            'share_of_tiers':{k:(v/tot if tot else None)for k,v in secs.items()},'share_of_thread_time':{k:(v/thread_time if thread_time else None)for k,v in secs.items()},
            'share_of_task_time':{**{k:(v/task if task else None)for k,v in secs.items()},'other':(1-tot/task if task else None)},
            'microseconds_per_call':{k:(1e6*secs[k]/calls[k]if calls[k]else None)for k in TIERS},
            'tiers_over_thread_time':tot/thread_time if thread_time else None,'clock':t.get('clock'),
            'per_graph':table,'population':reweighted(table,strata)}

def mini_tasks(b:dict,dest:Path,ntasks:int=16,points:int=64)->Path:
    """The ntasks costliest tasks of a block (cost model), each cut to its first `points` points."""
    _o,L,rows=bk.read_tasks(b['tasks_path']);spp=b['seconds_per_point']
    rows=sorted(rows,key=lambda r:(-spp[str(r[2])]*(r[4]-r[3]),r[0]))[:ntasks]
    bk.write_tasks(dest,8,L,[(u,rep,g,lo,min(hi,lo+points),tot)for u,rep,g,lo,hi,tot in rows]);return dest

def p1(a)->int:
    ctx=Ctx(a,'p1');exe=Path(a.exe).resolve();prof=Path(a.prof_exe).resolve();out=ctx.out
    ident=bk.identity({'worker':exe,'prof':prof},a.perf);ident['worker_check']=check_exe(exe,None,a.expect_sha256)['sha256'];check_exe(prof,'tier_timers')
    blocks=[s for s in a.blocks.split(',')if s];A,B=lanes_for(ctx,a.threads);pa=perf_available(a.perf,ctx.scratch)
    conc=not a.sequential and B is not None and pa['ok'];B=B if conc else A
    log(f'P1 blocks {blocks}; perf {"available" if pa["ok"] else "UNAVAILABLE: "+str(pa["reason"])}; perf stream on {len(A)} cores {A[0]}..{A[-1]}; tier timers on {B[0]}..{B[-1]} ({"concurrent" if conc else "sequential"})')
    res={b:{'block':{k:v for k,v in ctx.block(b).items()if k not in('seconds_per_point','graphs','net')}}for b in blocks}
    cg=a.call_graph!='none';twin=ctx.scratch/'c8d3_gmp_dbginfo';wp=None if a.wait_policy=='default'else a.wait_policy
    errors=[]
    def perf_stream():
        for b in blocks:
            try:
                blk=ctx.block(b);data=ctx.scratch/f'{b}.perf.data';o=ctx.scratch/f'{b}.perf_native.json'
                pre=[a.perf,'record','-N','-F',str(a.freq),'-o',str(data)]+(['--call-graph',a.call_graph]if cg else[])+['--']
                log(f'perf record {b} ({blk["tasks"]} tasks, predicted {blk["predicted"].get("wall_seconds",0):.0f} s)')
                r=run(pre+ctx.cmd(exe,blk,o,a.threads),A,a.threads,out/f'{b}.perf_record.log',ctx.pin,wait_policy=wp)
                r['record']=bk.parse_perf_record_stderr(Path(r['log']).read_text(errors='replace'));nr=native_result(o,a.threads,r)
                res[b]['perf_run']={**{k:v for k,v in r.items()if k!='log_tail'},'native':nr['summary']};o.unlink()
            except Exception as e:  # recorded; the other blocks still run
                res[b]['perf_run_error']=f'{type(e).__name__}: {e}';errors.append(f'{b} perf run');log(f'{b} perf run FAILED: {e}')
    def prof_stream():
        if pa['ok']and not a.no_srcline:
            log('building the debug-info twin');res['_twin']=build_twin(twin,B,ctx.pin)
        for b in blocks:
            try:
                blk=ctx.block(b);o=ctx.scratch/f'{b}.prof_native.json';log(f'tier timers {b}')
                r=run(ctx.cmd(prof,blk,o,a.threads),B,a.threads,out/f'{b}.prof.log',ctx.pin,wait_policy=wp);nr=native_result(o,a.threads,r)
                res[b]['tier_run']={**{k:v for k,v in r.items()if k!='log_tail'},'native':nr['summary'],'tier_split':tier_split(nr['native'],blk.get('strata'))};o.unlink()
            except Exception as e:  # recorded; the other blocks still run
                res[b]['tier_run_error']=f'{type(e).__name__}: {e}';errors.append(f'{b} tier run');log(f'{b} tier run FAILED: {e}')
    streams=([perf_stream]if pa['ok']else[])+[prof_stream]
    if conc:
        with concurrent.futures.ThreadPoolExecutor(2)as ex:
            for f in [ex.submit(s)for s in streams]:f.result()
    else:
        for s in streams:s()
    for b in blocks:
        pr,tr=res[b].get('perf_run'),res[b].get('tier_run')
        res[b]['rows_identical_worker_vs_prof']=(pr['native']['rows_digest']==tr['native']['rows_digest'])if pr and tr else None
    srcinfo={'status':'not attempted'};fallback=None
    def record(stage:str)->dict:
        # Written after every phase, so that a job stopped by its time limit keeps what it has measured.
        rec={'schema':SCHEMA.format('p1'),'profile':'P1','stage':stage,'identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],'perf':pa,
             'settings':{'threads':a.threads,'freq':a.freq,'call_graph':a.call_graph,'perf_cpus':A,'tier_cpus':B,'concurrent':conc,'pinned':ctx.pin,
                         'wait_policy':a.wait_policy,'mp_check':ctx.m['native'].get('mp_check'),'fake_topology':a.fake_topology,'scratch':str(ctx.scratch)},
             'srcline_twin':srcinfo,'blocks':{b:{k:v for k,v in res[b].items()}for b in blocks},'fallback':fallback,'errors':list(errors),'written_utc':utc()}
        jdump(out/'p1.json',rec);log(f'wrote {out/"p1.json"} (stage {stage})');return rec
    tw=res.pop('_twin',None);record('runs')
    if pa['ok']:
        if tw is not None and tw['returncode']==0:
            try:srcinfo={'twin_build':tw,**same_code(exe,twin,ctx.scratch)}
            except (RuntimeError,OSError)as e:srcinfo={'twin_build':tw,'identical':False,'differences':[f'comparison failed: {e}']}
        elif tw is not None:srcinfo={'twin_build':tw,'identical':False,'differences':['twin build failed']}
        def report(b):
            data=ctx.scratch/f'{b}.perf.data'
            if not data.is_file():return b,{'error':'no perf.data (the perf run failed)'}
            try:rp=perf_reports(a.perf,data,out,b,cg)
            except (RuntimeError,OSError,subprocess.SubprocessError)as e:errors.append(f'{b} perf report');return b,{'error':f'{type(e).__name__}: {e}'}
            pr=report_summary(rp,exe.name)
            if not srcinfo.get('identical'):pr['srcline']={'status':'skipped: '+('; '.join(srcinfo.get('differences',[]))or srcinfo.get('status','no twin'))}
            return b,pr
        def lines(b):
            data=ctx.scratch/f'{b}.perf.data'
            try:sl=srcline(a.perf,data,exe,twin,res[b]['perf']['total_samples'],ctx.scratch)
            except (OSError,subprocess.SubprocessError)as e:sl={'status':f'failed: {type(e).__name__}: {e}'}
            return b,sl
        log('perf reports')
        with concurrent.futures.ThreadPoolExecutor(min(8,len(blocks)))as ex:
            for b,pr in ex.map(report,blocks):res[b]['perf']=pr
        record('reports')
        todo=[b for b in blocks if srcinfo.get('identical')and 'total_samples'in res[b]['perf']]
        if todo:
            log('source lines (perf annotate + addr2line on the -g twin)')
            with concurrent.futures.ThreadPoolExecutor(min(8,len(todo)))as ex:
                for b,sl in ex.map(lines,todo):res[b]['perf']['srcline']=sl
        if not a.keep_perf_data:
            for b in blocks:(ctx.scratch/f'{b}.perf.data').unlink(missing_ok=True)
    if not pa['ok']:
        fallback={'reason':pa['reason'],'tier_timers':'above (tier_run of every block)'}
        if shutil.which('ltrace'):
            mb=next((b for b in ('heavy_power_L8','strat_power_L8')if b in ctx.m['blocks']),blocks[-1]);blk=ctx.block(mb)
            mt=mini_tasks(blk,ctx.scratch/'mini.tasks');base=ctx.scratch/'mini_plain.json';lt=ctx.scratch/'mini_ltrace.json';lo=ctx.scratch/'ltrace.txt'
            try:
                r0=run(ctx.cmd(exe,blk,base,1,tasks=mt),A[:1],1,out/'mini_plain.log',ctx.pin)
                r1=run(['ltrace','-c','-f','-e','__gmpf_*','-o',str(lo),'--',*ctx.cmd(exe,blk,lt,1,tasks=mt)],A[:1],1,out/'mini_ltrace.log',ctx.pin,timeout=3600)
                fallback['ltrace']={'block':mb,'tasks':16,'points_per_task':64,'plain_wall_seconds':r0['wall_seconds'],'ltrace_wall_seconds':r1['wall_seconds'],
                                    'returncode':r1['returncode'],'table':bk.parse_ltrace_c(lo.read_text())if lo.is_file()else None}
                if lo.is_file():shutil.copy2(lo,out/'mini_ltrace_c.txt')
            except (OSError,subprocess.SubprocessError)as e:fallback['ltrace']=f"failed: {type(e).__name__}: {e}"
        else:fallback['ltrace']='ltrace not found'
    record('final');cleanup(ctx,a)
    if errors:log(f'ERRORS: {errors}')
    return 1 if errors else 0

# ---------------------------------------------------------------- P2
def serial_tasks(b:dict,dest:Path,seconds:float)->tuple[Path,float]:
    """The costliest tasks of a block (cost-model order) until their predicted single-thread time reaches `seconds`."""
    _o,L,rows=bk.read_tasks(b['tasks_path']);spp=b['seconds_per_point'];rows=sorted(rows,key=lambda r:(-spp[str(r[2])]*(r[4]-r[3]),r[0]));out=[];acc=0.
    for r in rows:
        out.append(r);acc+=spp[str(r[2])]*(r[4]-r[3])
        if acc>=seconds:break
    bk.write_tasks(dest,8,L,out);return dest,acc

def p2(a)->int:
    ctx=Ctx(a,'p2');exe=Path(a.exe).resolve();out=ctx.out;ident=bk.identity({'worker':exe},a.perf);check_exe(exe,None,a.expect_sha256)
    blocks=[s for s in a.blocks.split(',')if s];A,_B=lanes_for(ctx,a.threads);pa=perf_available(a.perf,ctx.scratch);res={}
    log(f'P2 blocks {blocks}; perf {"available" if pa["ok"] else "UNAVAILABLE: "+str(pa["reason"])}; {a.threads} threads on {A[0]}..{A[-1]}')
    wp=None if a.wait_policy=='default'else a.wait_policy;errors=[]
    for b in blocks:
        blk=ctx.block(b);res[b]={'block':{k:v for k,v in blk.items()if k not in('seconds_per_point','graphs','net')}}
        for tag,cpus,threads,tasks,pred in (('parallel',A,a.threads,None,blk['predicted'].get('wall_seconds')),('serial',A[:1],1,*serial_tasks(blk,ctx.scratch/f'{b}.serial.tasks',a.serial_seconds))):
            try:
                o=ctx.scratch/f'{b}.{tag}.json';st=ctx.scratch/f'{b}.{tag}.perfstat.csv'
                pre=[a.perf,'stat','-x,','-o',str(st),'-e',a.events,'--']if pa['ok']else[]
                log(f'{b} {tag}: {threads} thread(s){" under perf stat" if pre else ""}')
                r=run(pre+ctx.cmd(exe,blk,o,threads,tasks=tasks),cpus,threads,out/f'{b}.{tag}.log',ctx.pin,wait_policy=wp);nr=native_result(o,threads,r)
                stat=bk.parse_perf_stat_csv(st.read_text())if st.is_file()else None
                if st.is_file():shutil.copy2(st,out/st.name)
                res[b][tag]={**{k:v for k,v in r.items()if k!='log_tail'},'predicted_seconds':pred,'native':nr['summary'],'perf_stat':stat,
                             'promotion_free':nr['summary']['quad']==0 and nr['summary']['mp']==0};o.unlink()
            except Exception as e:  # recorded; the other runs still go
                res[b][tag]={'error':f'{type(e).__name__}: {e}'};errors.append(f'{b} {tag}');log(f'{b} {tag} FAILED: {e}')
    ipc={b:{t:((res[b][t].get('perf_stat')or{}).get('derived')or{}).get('ipc')for t in ('parallel','serial')}for b in res}
    rec={'schema':SCHEMA.format('p2'),'profile':'P2','identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],'perf':pa,
         'settings':{'threads':a.threads,'events':a.events,'wait_policy':a.wait_policy,'serial_seconds':a.serial_seconds,'cpus':A,'pinned':ctx.pin,'fake_topology':a.fake_topology},
         'blocks':res,'ipc':ipc,'decision_rule':'R6 go if IPC < 1.5 on the promotion-free blocks or the interleave-probe speedup >= 1.2 (tools/benchmark.py --interleave-probe)',
         'errors':errors,'finished_utc':utc()}
    jdump(out/'p2.json',rec);cleanup(ctx,a);log(f'wrote {out/"p2.json"}'+(f'; ERRORS: {errors}'if errors else''));return 1 if errors else 0

# ---------------------------------------------------------------- P3
def p3(a)->int:
    ctx=Ctx(a,'p3');exe=Path(a.exe).resolve();out=ctx.out;ident=bk.identity({'ratiohist':exe},a.perf);check_exe(exe,'ratio_histogram')
    threads=a.threads or len(ctx.cores);A=bk.partition(ctx.cores,1,threads)[0];blocks=[s for s in a.blocks.split(',')if s];rates=[s for s in a.rates.split(',')if s];res={}
    log(f'P3 blocks {blocks} at rates {rates}; {threads} threads');errors=[]
    for b in blocks:
        blk=ctx.block(b)
        for rate in rates:
            try:
                o=ctx.scratch/f'{b}.{rate}.json';log(f'{b} rate {rate}')
                r=run(ctx.cmd(exe,blk,o,threads,rate=rate),A,threads,out/f'{b}.rate{rate}.log',ctx.pin);nr=native_result(o,threads,r)
                res[f'{b}@{rate}']={'block':b,'sector':blk['sector'],'L':blk['L'],'rate':rate,'graphs':len(blk['graphs']),'wall_seconds':r['wall_seconds'],
                                    'native':nr['summary'],'ratio':bk.ratio_summary(nr['native'])};o.unlink()
            except Exception as e:  # recorded; the other runs still go
                errors.append(f'{b}@{rate}: {type(e).__name__}: {e}');log(f'{b} rate {rate} FAILED: {e}')
    rec={'schema':SCHEMA.format('p3'),'profile':'P3','identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],
         'settings':{'threads':threads,'rates':rates,'cpus':A,'pinned':ctx.pin,'fake_topology':a.fake_topology},
         'bins':'floor(log10(|v|/err)); key 0 = every ratio >= 1; -401 = zero_or_below (0 or < 1e-400). ld_fail: points failing the 1e-9 test; quad: every binary128 evaluation (the 1e-23 test fails below 1e-23); mp: every MP evaluation',
         'results':res,'errors':errors,'all_checks_ok':bool(res)and not errors and all(v['ratio']['ok']for v in res.values()),'finished_utc':utc()}
    jdump(out/'p3.json',rec);cleanup(ctx,a);log(f'wrote {out/"p3.json"}');return 0 if rec['all_checks_ok']else 1

# ---------------------------------------------------------------- MP self-check overhead (PLAN C.4)
MODES=('on','off','stride16')
def mpcheck(a)->int:
    ctx=Ctx(a,'mpcheck');exe=Path(a.exe).resolve();out=ctx.out;ident=bk.identity({'prof':exe},'perf');check_exe(exe,'tier_timers',a.expect_sha256)
    blocks=[s for s in a.blocks.split(',')if s];A,B=lanes_for(ctx,a.threads);wp=None if a.wait_policy=='default'else a.wait_policy
    sets=[A]+([B]if B is not None else[]);res={b:{'block':{k:v for k,v in ctx.block(b).items()if k not in('seconds_per_point','graphs','net','strata','chunks')}}for b in blocks}
    errors=[]
    log(f'MP self-check overhead: blocks {blocks}, modes {MODES} (rotated), {a.threads} threads on {len(sets)} core set(s)')
    def stream(i:int,mine:list):
        for j,b in enumerate(mine):
            blk=ctx.block(b);k=(blocks.index(b))%3;order=MODES[k:]+MODES[:k]
            for mode in order:
                try:
                    o=ctx.scratch/f'{b}.{mode}.json';log(f'{b} --mp-check {mode} on set {i}')
                    r=run(ctx.cmd(exe,blk,o,a.threads,mp_check=mode),sets[i],a.threads,out/f'{b}.{mode}.log',ctx.pin,wait_policy=wp);nr=native_result(o,a.threads,r)
                    n=nr['native'];res[b][mode]={'cpus':f'{sets[i][0]}-{sets[i][-1]}','wall_seconds':r['wall_seconds'],'native':nr['summary'],'tier_split':tier_split(n,blk.get('strata')),
                                                'mp_checked':sum(x.get('mp_checked',0)for x in n['rows']),'mp_alarm':sum(x.get('mp_alarm',0)for x in n['rows']),
                                                'values_digest':bk.combined_digest([(str(x['uid']),'',__import__('hashlib').sha256(bk.canon([x[f]for f in ('values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax')]).encode()).hexdigest())for x in n['rows']])}
                    o.unlink()
                except Exception as e:  # recorded; the other runs still go
                    res[b][mode]={'error':f'{type(e).__name__}: {e}'};errors.append(f'{b} {mode}');log(f'{b} {mode} FAILED: {e}')
    parts=[blocks[i::len(sets)]for i in range(len(sets))]
    with concurrent.futures.ThreadPoolExecutor(len(sets))as ex:
        for f in [ex.submit(stream,i,parts[i])for i in range(len(sets))]:f.result()
    summary={}
    for b in blocks:
        r=res[b]
        if any('error'in r.get(m,{'error':1})for m in MODES):continue
        off=r['off']['tier_split'];x={'values_identical_across_modes':len({r[m]['values_digest']for m in MODES})==1,'mp_calls':r['off']['tier_split']['calls']['mp']}
        for m in ('on','stride16'):
            ts=r[m]['tier_split'];x[m]={'task_overhead':(ts['task_seconds']-off['task_seconds'])/ts['task_seconds'],
                 'mp_tier_overhead':(ts['seconds']['mp']-off['seconds']['mp'])/ts['task_seconds'],
                 'mp_tier_ratio':(ts['seconds']['mp']/off['seconds']['mp'])if off['seconds']['mp']else None,'mp_checked':r[m]['mp_checked'],'mp_alarm':r[m]['mp_alarm']}
            pa,po=ts.get('population'),off.get('population')
            if pa and po:
                x[m]['population_mp_tier_overhead']=(pa['tier_seconds_per_point']['mp']-po['tier_seconds_per_point']['mp'])/pa['task_seconds_per_point']
                x[m]['population_task_overhead']=(pa['task_seconds_per_point']-po['task_seconds_per_point'])/pa['task_seconds_per_point']
        summary[b]=x
    rec={'schema':SCHEMA.format('mpcheck'),'profile':'MP self-check overhead (PLAN C.4)','identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],
         'settings':{'threads':a.threads,'sets':[f'{s[0]}-{s[-1]}'for s in sets],'wait_policy':a.wait_policy,'pinned':ctx.pin,'fake_topology':a.fake_topology},
         'blocks':res,'summary':summary,
         'decision_rule':'production keeps --mp-check on if its overhead is <= 3% of the total CPU (the population task time), else stride16 (PLAN C.4)',
         'errors':errors,'finished_utc':utc()}
    jdump(out/'mpcheck.json',rec);cleanup(ctx,a);log(f'wrote {out/"mpcheck.json"}'+(f'; ERRORS: {errors}'if errors else''));return 1 if errors else 0

# ---------------------------------------------------------------- f_E (A-PERF-1)
def symmetry_basis(d:Path)->dict:
    """symmetry's matched records (validation_567197/bench): {(sector, L, threads): median integration seconds} of the
    production worker (production_scaling.json at 1, 2, 4 threads, L7) and of the 'reference' variant (benchmarks.json:
    the original worker, 1 thread, L6 and L7), with their host."""
    ps=load(d/'production_scaling.json');bm=load(d/'benchmarks.json');out={}
    for r in ps['records']:out[(r['sector'],int(r['L']),int(r['threads']),'production')]=float(r['median_integration_s'])
    for r in bm['records']:
        if r['variant']=='reference':out[(r['sector'],int(r['L']),int(r['threads']),'reference')]=float(r['median_integration_s'])
    return {'values':out,'host':ps.get('host'),'executable_sha256':(ps.get('executable')or{}).get('sha256'),'compiler':((ps.get('build')or{}).get('compiler'))}

def fe(a)->int:
    import statistics,prepare_benchmarks as pb
    fx=pb.verify_fixtures7();folder=ROOT/'benchmarks/fixtures';c7=Path(a.c7_exe).resolve();c8=Path(a.c8_exe).resolve()
    rc7=check_exe(c7,None);rc8=check_exe(c8,None);ident=bk.identity({'c7ref':c7,'c8':c8},'perf')
    cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores();pin=not a.no_pin
    if a.fake_topology and pin:raise bk.BenchError(64,'--fake-topology needs --no-pin (the fake CPU numbers do not exist)')
    out=Path(a.output).resolve()
    if out.exists():raise bk.BenchError(64,f'{out} exists; give a new output directory')
    out.mkdir(parents=True);scratch=Path(tempfile.mkdtemp(prefix='c8d3_fe_',dir=a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir()))
    sock0=bk.partition(cores,1,a.loaded_threads)[0];sym=symmetry_basis(a.symmetry);gamma=ROOT/'reference/inputs/gamma_d3_7.txt'
    groups=[('free',6),('free',7),('power',6),('power',7)];runs=[];errors=[]
    # symmetry's task files, as C7(3)'s tools/benchmark.py wrote them: the fixture's 16 graphs x 2 replicates with 4096
    # points at L6 and 512 at L7 (the committed L7 task file; benchmark_production.py ran it as is)
    tasks={}
    for s,L in groups:
        ids=fx['records'][f'{s}_L{L}']['ids'];n=4096 if L==6 else 512;tf=scratch/f'{s}_L{L}.tasks'
        tf.write_text(f'C7D3TASKS1 {L} {2*len(ids)}\n'+''.join(f'{i} {r} {g} 0 {n} {n}\n'for i,(r,g)in enumerate((r,g)for r in range(2)for g in ids)))
        if L==7 and tf.read_bytes()!=(folder/f'{s}_L{L}.tasks').read_bytes():raise bk.BenchError(65,f'{tf.name} differs from the committed fixture task file')
        tasks[(s,L)]=tf
    def cmd(exe,s,L,o,threads):
        return [str(x)for x in (exe,ROOT/'reference/inputs'/s,gamma,folder/f'{s}_L{L}.net',tasks[(s,L)],o,5461981,0,.8,threads,'compensated','-')]
    def one(tag,exe,s,L,threads,rep,cpus):
        o=scratch/f'{tag}_{s}_L{L}_t{threads}_r{rep}.json';r=run(cmd(exe,s,L,o,threads),cpus,threads,scratch/f'{o.stem}.log',pin)
        nr=native_result(o,threads,r);n=nr['native'];o.unlink()
        return {'tag':tag,'sector':s,'L':L,'threads':threads,'repeat':rep,'cpus':f'{cpus[0]}-{cpus[-1]}','wall_seconds':r['wall_seconds'],
                'integration_seconds':float(n['integration_seconds']),'load_seconds':float(n['load_seconds']),'task_seconds':nr['summary']['task_seconds'],
                'rows_digest':bk.combined_digest([(str(x['uid']),'',__import__('hashlib').sha256(bk.canon([x[f]for f in ('values','quad','mp','max_abs')]).encode()).hexdigest())for x in n['rows']])}
    log(f'f_E: isolated runs on {sock0[0]}.., loaded runs: {a.loaded_threads} single-thread copies on {sock0[0]}..{sock0[-1]} ({a.repeats} repeats)')
    for rep in range(a.repeats):
        for s,L in groups:
            for th in ((1,2,4)if L==7 else(1,)):
                for tag,exe in (('c7ref',c7),('c8',c8))if th==1 else(('c7ref',c7),):
                    try:runs.append({'mode':'isolated',**one(tag,exe,s,L,th,rep,sock0[:th])})
                    except Exception as e:errors.append(f'isolated {tag} {s} L{L} t{th} r{rep}: {e}');log(errors[-1])
    for rep in range(a.repeats):
        for s,L in groups:
            log(f'loaded {s} L{L} repeat {rep}: {len(sock0)} copies')
            with concurrent.futures.ThreadPoolExecutor(len(sock0))as ex:
                fs=[ex.submit(one,'c7ref',c7,s,L,1,f'{rep}c{i}',[cpu])for i,cpu in enumerate(sock0)]
                for f in fs:
                    try:runs.append({'mode':'loaded',**f.result()})
                    except Exception as e:errors.append(f'loaded {s} L{L} r{rep}: {e}');log(errors[-1])
    table=[]
    for s,L in groups:
        ref=[r['rows_digest']for r in runs if r['sector']==s and r['L']==L]
        identical=len(set(ref))==1
        for th in ((1,2,4)if L==7 else(1,)):
            iso=[r['integration_seconds']for r in runs if r['mode']=='isolated'and r['tag']=='c7ref'and r['sector']==s and r['L']==L and r['threads']==th]
            c8i=[r['integration_seconds']for r in runs if r['mode']=='isolated'and r['tag']=='c8'and r['sector']==s and r['L']==L and r['threads']==th]
            row={'sector':s,'L':L,'threads':th,'expanse_isolated_median_s':statistics.median(iso)if iso else None,'expanse_c8_isolated_median_s':statistics.median(c8i)if c8i else None,
                 'rows_identical_all_runs':identical}
            for var in ('production','reference'):
                v=sym['values'].get((s,L,th,var))
                row[f'symmetry_{var}_s']=v
                if v and iso:row[f'f_E_isolated_vs_{var}']=statistics.median(iso)/v
            if th==1:
                ld=[r['integration_seconds']for r in runs if r['mode']=='loaded'and r['sector']==s and r['L']==L]
                if ld:
                    row.update({'expanse_loaded_median_s':statistics.median(ld),'expanse_loaded_max_s':max(ld),'expanse_loaded_n':len(ld),
                                'loaded_socket_factor':statistics.median(ld)/row['expanse_isolated_median_s']if row['expanse_isolated_median_s']else None})
                    for var in ('production','reference'):
                        v=sym['values'].get((s,L,1,var))
                        if v:row[f'f_E_loaded_vs_{var}']=statistics.median(ld)/v
            table.append(row)
    rec={'schema':SCHEMA.format('fe'),'profile':'f_E (A-PERF-1)','identity':ident,'fixtures7_manifest_sha256':digest(folder/'manifest.json'),
         'executables':{'c7ref':rc7['sha256'],'c8':rc8['sha256']},'symmetry':{k:v for k,v in sym.items()if k!='values'}|{'records':{f'{k[0]}_L{k[1]}_t{k[2]}_{k[3]}':v for k,v in sym['values'].items()}},
         'settings':{'repeats':a.repeats,'loaded_threads':a.loaded_threads,'loaded_cpus':f'{sock0[0]}-{sock0[-1]}','pinned':pin,'fake_topology':a.fake_topology,
                     'arguments':'seed 5461981, layout 0, rate .8, 1-4 threads, compensated, no grid; 4096 points per graph and replicate at L6, 512 at L7: symmetry\'s (validation_567197/bench, C7(3) tools/benchmark.py)'},
         'table':table,'runs':runs,'errors':errors,'finished_utc':utc(),
         'definitions':{'f_E':'Expanse integration seconds / symmetry\'s (median of the repeats); > 1 means EPYC 7742 is slower than symmetry\'s EPYC 7532',
                        'loaded_socket_factor':'median single-thread time with 64 copies on socket 0 (the other socket idle) / the isolated single-thread time'}}
    jdump(out/'fe.json',rec)
    if not a.keep_scratch:shutil.rmtree(scratch,ignore_errors=True)
    log(f'wrote {out/"fe.json"}'+(f'; ERRORS: {errors}'if errors else''));return 1 if errors else 0

def cleanup(ctx:Ctx,a)->None:
    if not a.keep_scratch:shutil.rmtree(ctx.scratch,ignore_errors=True)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sub=p.add_subparsers(dest='mode',required=True)
    for mode in ('p1','p2','p3','mpcheck'):
        q=sub.add_parser(mode);q.add_argument('--output',type=Path,required=True);q.add_argument('--blocks',default=DEFAULTS[mode])
        q.add_argument('--exe',default=str(ROOT/{'p3':'bin/c8d3_gmp_ratiohist','mpcheck':'bin/c8d3_gmp_prof'}.get(mode,'bin/c8d3_gmp')));q.add_argument('--expect-sha256')
        q.add_argument('--threads',type=int,default=0 if mode=='p3'else 64,help='p3: 0 = every core of the allocation')
        q.add_argument('--fixtures',type=Path,default=bk.FIXTURES8);q.add_argument('--scratch');q.add_argument('--perf',default='perf')
        q.add_argument('--fake-topology');q.add_argument('--no-pin',action='store_true');q.add_argument('--keep-scratch',action='store_true')
        q.add_argument('--keep-perf-data',action='store_true')
        q.add_argument('--smoke-tasks',type=int,default=0,help='function test only: cut every block to its first N tasks');q.add_argument('--smoke-points',type=int,default=64)
        if mode=='p1':
            q.add_argument('--prof-exe',default=str(ROOT/'bin/c8d3_gmp_prof'));q.add_argument('--freq',type=int,default=999)
            q.add_argument('--wait-policy',default='passive',choices=('passive','active','default'))
            q.add_argument('--call-graph',default='none',choices=('none','fp','dwarf'));q.add_argument('--sequential',action='store_true');q.add_argument('--no-srcline',action='store_true')
        if mode=='p2':
            q.add_argument('--events',default=P2_EVENTS);q.add_argument('--serial-seconds',type=float,default=30.)
            q.add_argument('--wait-policy',default='passive',choices=('passive','active','default'))
        if mode=='p3':q.add_argument('--rates',default='.8,.7')
        if mode=='mpcheck':q.add_argument('--wait-policy',default='passive',choices=('passive','active','default'))
    q=sub.add_parser('fe',help='f_E against symmetry on C7(3)\'s fixtures (A-PERF-1)');q.add_argument('--output',type=Path,required=True)
    q.add_argument('--c7-exe',default=str(ROOT/'bin/ref/c7d3_gmp'));q.add_argument('--c8-exe',default=str(ROOT/'bin/c8d3_gmp'));q.add_argument('--repeats',type=int,default=3)
    q.add_argument('--symmetry',type=Path,default=ROOT/'benchmarks/symmetry_2026-10/validation_567197/bench');q.add_argument('--loaded-threads',type=int,default=64)
    q.add_argument('--scratch');q.add_argument('--fake-topology');q.add_argument('--no-pin',action='store_true');q.add_argument('--keep-scratch',action='store_true')
    q=sub.add_parser('p1-reparse',help='rebuild a finished P1 record\'s perf summaries from its saved report texts (Mac-runnable)')
    q.add_argument('--input',type=Path,required=True,help='the P1 output directory (holds p1.json and <block>.perf_report_*.txt)')
    q.add_argument('--output',type=Path,help='default <input>/p1_reparsed.json')
    a=p.parse_args(argv)
    try:return {'p1':p1,'p2':p2,'p3':p3,'mpcheck':mpcheck,'fe':fe,'p1-reparse':p1_reparse}[a.mode](a)
    except bk.BenchError as e:print(f'perf_profile {a.mode}: {e}',file=sys.stderr);return e.code

if __name__=='__main__':sys.exit(main())
