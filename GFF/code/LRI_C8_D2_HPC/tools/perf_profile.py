#!/usr/bin/env python3
"""Stage-4a profiles P1, P2 and P3 (PLAN "Performance plan"; A-PERF-1) on the frozen fixtures of benchmarks/fixtures8
(tools/prepare_benchmarks.py --order 8) and the Stage-3 baseline executables. Profiling only: no worker change.

  perf_profile.py p1 --output DIR [--blocks heavy_free_L7,heavy_power_L7,heavy_free_L8,heavy_power_L8] [--threads 64]
  perf_profile.py p2 --output DIR [--blocks nopromo_free_L7,nopromo_free_L8,heavy_free_L8] [--threads 64]
  perf_profile.py p3 --output DIR [--blocks random_free_L7,random_power_L7,random_free_L8,random_power_L8] [--rates .8,.9]
                    [--worker-exe bin/c8d2_gmp]
  perf_profile.py p1-reparse --input P1DIR [--output FILE]   (offline: the perf summaries again from the saved reports)
Common options: --exe (default bin/c8d2_gmp; P3 bin/c8d2_gmp_ratiohist), --expect-sha256 HEX (8 to 64 hex digits: the
sha256 prefix of the --exe the mode measures, checked in every mode before any output, scratch or run; Z21), --scratch DIR
(node-local; perf.data and staged graphs stay there and are removed at the end unless --keep-scratch), --fixtures DIR,
--perf PATH, --fake-topology SxNxC --no-pin (dry runs only; recorded as such). P1 only: --keep-perf-data moves every
block's perf.data into <output>/perf_data/ and records its path, size and sha256 (with or without --keep-scratch; Z22).

P1 (time per function; tier split). The block runs at --threads threads on the first NUMA-aligned set of that many cores
(one socket of 4 NUMA nodes at 64 threads on an EPYC node) under `perf record -F 999 [-g] -N`; then the plan's
`perf report --no-children --sort symbol --stdio` (with -n), and --sort dso,symbol and --sort dso, parsed into the shares
the plan names (benchkit.perf_shares: __addtf3/__subtf3/__multf3/__divtf3, expq, __gmpf_*, __gmpn_*, malloc/free, expl,
MP -> long double conversion, calculate_reference<long double>, libgomp, kernel) and a top-40 table. Concurrently, on
the second set of cores (the other socket), bin/c8d2_gmp_prof (make profile, -DC8_TIER_TIMERS) runs the same block:
first pass / binary128 / MP seconds and calls (the tier split). --sequential runs both on the first set. The two runs
of a block must have identical scientific rows (benchkit.SCIENTIFIC): a difference (a stale or different --prof-exe) is
an error naming the block and the differing uids, and P1 exits 1 (Z20). Without perf the release worker still runs
every requested block, directly (no perf wrapping it; its team watched), in place of the perf run, and the same
comparison binds the tier-timer worker to it on every block (W19, Stage-6 fix round 4: the fallback compared the two
workers on a mini block only, so a difference in a requested block went unnoticed). Source lines
(best effort; the shift loop and calculate_reference<long double> are inlined code without a symbol of their own): a
debug-info twin of the worker (the Makefile's gmp command plus -g, built in the scratch directory) is used only when its
allocated sections (.text, .rodata, .data, ...) equal the baseline's byte for byte at the same addresses; then
`perf annotate --stdio` of the worker's symbols gives per-instruction samples, and addr2line on the twin maps them to
src/kernel.hpp lines and regions (shift loop, calculate_reference, calculate_products, calculate_shared, evaluate,
sample). -g is off by default: the --no-children self-time table does not use call chains, and at 64 threads -g writes
about 1 kB per sample (--call-graph fp to enable). Without perf (missing, or perf_event_paranoid refuses): the tier
timers of every block, bound to the release worker's direct run of that block as above (W19), plus, when ltrace
exists, `ltrace -c -e '__gmpf_*'` of the release worker on a mini block (16 tasks x 64 points of the heaviest power L8
tasks, one thread) and a plain run of that mini block: the traced rows, when it finishes, must equal the plain run's.

P2 (is the first pass latency-bound?). `perf stat -x, -e cycles,instructions,branches,branch-misses,L1-dcache-loads,
L1-dcache-load-misses,task-clock` on the promotion-free blocks (no binary128 or MP point) at --threads threads, with
OMP_WAIT_POLICY=passive so barrier spinning does not count as work (--wait-policy default to keep libgomp's default),
plus one thread on the heaviest tasks of each block (--serial-seconds of predicted work); IPC = instructions/cycles.
The decision rule (R6 go if IPC < 1.5 or the interleave-probe speedup >= 1.2) uses tools/benchmark.py
--interleave-probe as the fallback and second measure.

P3 (margin distribution at the tests). bin/c8d2_gmp_ratiohist (make ratiohist) on the uniform-draw blocks at every
--rates value, on all cores: the log10(|v|/err) histograms at the 1e-9 test (failing long-double points), the 1e-23
test (every binary128 evaluation) and the MP evaluations, per (sector, L, rate), with consistency checks against the
row counters and the fractions below 10^-k (benchkit.ratio_summary). The release worker (--worker-exe, a release
build) then runs the same block at the same rate and threads, and the two runs must have identical scientific rows:
a difference (a stale or different ratio-histogram build, whose margins would then describe another computation) is
an error naming the block, the rate and the uids, and P3 exits 1 (Stage-6 fix round 4, W19's class: P3 measured the
diagnostic build without ever binding it to the release worker). P3 therefore runs every (block, rate) twice.
"""
from __future__ import annotations
import argparse,concurrent.futures,json,math,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import REQUIRED_CXXFLAGS,ROOT,TeamWatch,cxx_command,digest,load,team_message,utc
import benchkit as bk

SCHEMA='c8-d2-prof-{}-1'
P2_EVENTS='cycles,instructions,branches,branch-misses,L1-dcache-loads,L1-dcache-load-misses,task-clock'
DEFAULTS={'p1':'heavy_free_L7,heavy_power_L7,heavy_free_L8,heavy_power_L8','p2':'nopromo_free_L7,nopromo_free_L8,heavy_free_L8',
          'p3':'random_free_L7,random_power_L7,random_free_L8,random_power_L8'}

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

def jdump(path:Path,obj)->None:Path(path).write_text(json.dumps(obj,indent=1,sort_keys=False,default=str)+'\n')

class Ctx:
    """Fixtures, inputs, cores, blocks, scratch and output of one run. The constructor only checks (fixtures, topology,
    block names, a new output directory); open() creates the output and scratch directories, after the mode has
    checked its executables (Z21's class, Stage-6 fix round 3: a refusal leaves no output, scratch or worker run)."""
    def __init__(self,a,mode:str):
        self.a=a;self.mode=mode;self.m=bk.load_fixtures(a.fixtures);self.I=self.m['_inputs'];self.inv=load(self.I.where('inventory.json'))
        self.gamma=self.I.where(bk.GAMMA);self.pin=not a.no_pin
        self.cores=bk.fake_cores(a.fake_topology)if a.fake_topology else bk.host_cores()
        if a.fake_topology and self.pin:raise bk.BenchError(64,'--fake-topology needs --no-pin (the fake CPU numbers do not exist)')
        self.blocks=[s for s in a.blocks.split(',')if s]
        if not self.blocks:raise bk.BenchError(64,'--blocks names no fixture block')
        for b in self.blocks:bk.block_of(self.m,b)  # an unknown name is refused here
        self.out=Path(a.output).resolve()
        if self.out.exists():raise bk.BenchError(64,f'{self.out} exists; give a new output directory')
        self.scratch=None;self.staged={}
    def open(self)->None:
        base=Path(self.a.scratch or os.environ.get('SLURM_TMPDIR')or tempfile.gettempdir())
        self.out.mkdir(parents=True);self.scratch=Path(tempfile.mkdtemp(prefix=f'c8d2_{self.mode}_',dir=base))
    def block(self,name:str)->dict:
        """The fixture block with its graphs staged once into the scratch directory (timed)."""
        if name not in self.staged:
            b=bk.block_of(self.m,name);g=self.scratch/'graphs'/name
            b['staging']=bk.stage_graphs(self.I,self.inv,b['sector'],b['L'],b['graphs'],g);b['graphs_root']=str(g);self.staged[name]=b
        return self.staged[name]
    def cmd(self,exe,b:dict,out:Path,threads:int,tasks=None,rate=None)->list[str]:
        n=self.m['native']
        return bk.native_cmd(exe,b['graphs_root'],self.gamma,b['net_path'],tasks or b['tasks_path'],out,b['native_seed'],n['layout'],rate or n['rate'],threads,n['sum_mode'])

def check_exe(path:Path,kind:str|None,expect:str|None=None)->dict:
    """The executable's identity; refuses a malformed --expect-sha256 (64), a missing executable, a wrong diagnostic
    kind, or a sha256 that does not start with --expect-sha256 (benchkit.require_sha256). Every mode calls it for the
    executable it measures, with the mode's --expect-sha256, before Ctx.open (Z21, Stage-6 fix round 3: P3 had
    dropped it)."""
    bk.expect_prefix(expect)
    rec=bk.exe_identity(path)
    if not rec['present']:raise bk.BenchError(69,f'{path} is missing (make gmp / make profile / make ratiohist)')
    d=rec.get('describe')or{}
    if kind is None and d.get('diagnostic'):raise bk.BenchError(65,f'{path} is a diagnostic build ({d.get("diagnostic_kind")}); give the release worker')
    if kind is not None and d.get('diagnostic_kind')!=kind:raise bk.BenchError(65,f'{path}: diagnostic_kind {d.get("diagnostic_kind")!r}, expected {kind!r}')
    bk.require_sha256(path,rec['sha256'],expect)
    return rec

def run(cmd,cpus,threads:int,logf:Path,pin:bool,wait_policy=None,timeout=None,exe=None)->dict:
    """One pinned process (the native, or perf/ltrace wrapping it); wall seconds, exit code, stderr tail. The worker gets
    the controlled OpenMP environment (benchkit.omp_env: no inherited OMP_*, GOMP_* or KMP_* control). Stage-6 fix
    round 2 (Y2's defect class, as benchkit.run_watched for P4): a direct run of the native exe (cmd[0] is exe, not
    perf or ltrace wrapping it) has its OpenMP team watched (common.TeamWatch; an ELF worker on Linux): a worker that
    does not show the requested team after the deadline while computing is stopped, and native_result accepts a
    watched run only when its team was seen ('verified'). A wrapped run's team is not watched (team.watched false,
    team.wrapped true): this process sees perf's or ltrace's process, not the worker's."""
    direct=exe is not None and str(cmd[0])==str(exe);check=direct and bk.team_check(exe)
    t0=time.perf_counter()
    with open(logf,'w')as lf:
        p=subprocess.Popen(cmd,stdout=lf,stderr=subprocess.STDOUT,env=bk.omp_env(threads,wait_policy=wait_policy),preexec_fn=bk.pinner(cpus,pin))
        watch=TeamWatch(p,threads,check,on_smaller=lambda c:c.terminate())
        try:p.wait(timeout=timeout)
        except BaseException:  # the timeout (as subprocess.run: the child killed, then raised) or an interrupt
            watch.stop()
            if p.poll()is None:p.kill();p.wait()
            raise
        team=watch.stop()
    wall=time.perf_counter()-t0;text=Path(logf).read_text(errors='replace')
    return {'cmd':cmd,'returncode':p.returncode,'wall_seconds':wall,'cpus':sorted(cpus),'threads':threads,'log':str(logf),'log_tail':text[-1500:],
            'team':{**team,'watched':check,'wrapped':not direct}}

def native_result(out:Path,threads:int,rec:dict)->dict:
    tm=rec.get('team')or{}
    if tm.get('watched')and tm.get('verdict')!='verified':  # Y2's class: a measurement whose team is smaller or unknown is not accepted
        raise RuntimeError((team_message(tm)if tm.get('verdict')=='smaller'else f'the native worker did not show its OpenMP team of {threads} threads '
                            f'(verdict {tm.get("verdict")}, at most {tm.get("observed")} seen)')+f' (exit {rec["returncode"]})')
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
def twin_gmp_prefix(exe)->tuple[str|None,str|None]:
    """(GMP_PREFIX, note) of the profiled worker exe from its build record (tools/build_record.py worker_record: the
    record must describe exe); (None, why) without a usable record."""
    if exe is None:return None,'no worker given'
    import build_record as BR
    try:return BR.worker_record(Path(exe)).get('GMP_PREFIX')or None,None
    except BR.BindingRefused as e:return None,str(e)

def twin_directory(exe)->tuple[Path|None,list[str],str|None]:
    """W3's class (Stage-6 fix round 4, integration): (the working directory of the twin's compile, the relative words of
    the make flags and include environment it uses, why there is none). Without relative words: the package root, as
    before. With them: the profiled worker's build directory (its build record's build_directory, where those words
    meant what the worker's build read); None with the reason when the record names none (a record written before fix
    round 4, or no record) or it is not a directory: the twin is then not built (srcline skipped), never compiled where
    the words name other files."""
    import build_record as BR
    fl=BR.tool_flags();cxx=fl['CXX']or['g++']
    rel=BR.relative_words([w for k,_ in BR.FLAG_VARS for w in fl[k]],len(cxx))
    rel+=[d for v in BR.relative_env(names=BR.list_env(cxx[0])).values()for d in v if d not in rel]
    if not rel:return ROOT,[],None
    try:B=BR.build_directory(BR.worker_record(Path(exe)))if exe is not None else None
    except BR.BindingRefused as e:return None,rel,f'W3: the make flags or the include environment hold relative paths {rel[:6]}, and the worker has no usable build record ({e})'
    if B is None or not B.is_dir():
        return None,rel,(f'W3: the make flags or the include environment hold relative paths {rel[:6]}, and the worker\'s build record names no existing '
                         f'build_directory ({B}): where they meant what the worker\'s build read is unknown, so no twin is built')
    return B,rel,None

def build_twin(dest:Path,cpus=None,pin:bool=False,exe=None)->dict:
    """The Makefile's gmp compile command plus -g (debug info only): the profiled worker's twin for source-line lookup.
    Stage-6 fix round 2 (Y1's defect class): with exe, the twin gets the GMP_PREFIX words of exe's build record, placed
    as the Makefile places them (common.cxx_command gmp_prefix); before, a GMP_PREFIX worker's twin linked plain -lgmp,
    and same_code() could never accept it. W3's class (fix round 4): relative words in the make flags or the include
    environment are compiled in the worker's build directory (twin_directory), else the twin is not built (returncode
    None, the reason in error)."""
    # The Makefile's word order and relative source path, run from the package root (so __FILE__ strings match too).
    prefix,note=twin_gmp_prefix(exe)
    cmd=cxx_command(['src/c8d2_integrate.cpp'],dest,defines=('C8_USE_GMP',),libs=('-lquadmath','-lgmp'),gmp_prefix=prefix)
    cmd.insert(cmd.index(REQUIRED_CXXFLAGS[0]),'-g')
    cwd,rel,why=twin_directory(exe)
    if cwd is None:return {'command':cmd,'GMP_PREFIX':prefix,'gmp_prefix_note':note,'returncode':None,'seconds':0.0,'stderr':'','error':why,'relative_words':rel,'cwd':None}
    t0=time.perf_counter();cp=subprocess.run(cmd,capture_output=True,text=True,timeout=1800,cwd=cwd,preexec_fn=bk.pinner(cpus,pin and cpus is not None))
    return {'command':cmd,'GMP_PREFIX':prefix,'gmp_prefix_note':note,'returncode':cp.returncode,'seconds':time.perf_counter()-t0,'stderr':cp.stderr[-1500:],
            'relative_words':rel,'cwd':str(cwd)}

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
                     ('calculate_shared','std::pair<T,T> calculate_shared('),('evaluate','inline Eval evaluate('),('sample','std::array<ld,NLOGS> sample(')):
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
    rec=json.loads(src.read_text());worker=Path(((rec.get('identity')or{}).get('executables')or{}).get('worker',{}).get('path')or'c8d2_gmp').name
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

def tier_split(n:dict)->dict:
    t=n.get('tier_timers')or{};secs={k:float(t.get(f'{k}_seconds',0))for k in ('first_pass','quad','mp')};tot=math.fsum(secs.values())
    thread_time=float(n['integration_seconds'])*int(n['threads'])
    return {'seconds':secs,'calls':{k:int(t.get(f'{k}_calls',0))for k in ('first_pass','quad','mp')},
            'share_of_tiers':{k:(v/tot if tot else None)for k,v in secs.items()},'share_of_thread_time':{k:(v/thread_time if thread_time else None)for k,v in secs.items()},
            'tiers_over_thread_time':tot/thread_time if thread_time else None,'clock':t.get('clock')}

def mini_tasks(b:dict,dest:Path,ntasks:int=16,points:int=64)->Path:
    """The ntasks costliest tasks of a block (cost model), each cut to its first `points` points."""
    _o,L,rows=bk.read_tasks(b['tasks_path']);spp=b['seconds_per_point']
    rows=sorted(rows,key=lambda r:(-spp[str(r[2])]*(r[4]-r[3]),r[0]))[:ntasks]
    bk.write_tasks(dest,8,L,[(u,rep,g,lo,min(hi,lo+points),tot)for u,rep,g,lo,hi,tot in rows]);return dest

PROF_PAIR=('the release worker and the tier-timer worker','a stale or different --prof-exe, so its tier timers do not describe the profiled computation')
RATIO_PAIR=('the release worker and the ratio-histogram build','a stale or different ratio-histogram build (--exe) or --worker-exe, so its margins do not describe the release computation')
def bind_rows(tag:str,x:list,y:list,errors:list,pair=PROF_PAIR)->dict:
    """Z20 (Stage-6 fix round 3): two runs of the same tasks that P1 combines (by default the release worker's and the
    tier-timer worker's; benchkit.rows_digest lists) must have identical scientific rows; a difference is an error of
    P1 naming `tag` (the block) and the first uids. Returns {} when identical, else benchkit.rows_mismatch."""
    if bk.combined_digest(x)==bk.combined_digest(y):return {}
    mm=bk.rows_mismatch(x,y)
    errors.append(f'{tag}: {pair[0]} disagree ({mm["rows_differing"]} rows with different scientific fields, uids {mm["uids"][:5]}; '
                  f'{mm["rows_in_one_run_only"]} rows in one run only, uids {mm["uids_in_one_run_only"][:5]}): {pair[1]}')
    log(f'{tag}: ROWS DIFFER ({pair[0]}): {mm}');return mm

def keep_perf_data(ctx:Ctx,blocks:list,res:dict,errors:list)->bool:
    """--keep-perf-data (Z22, Stage-6 fix round 3): every block's perf.data is moved from the scratch directory into
    <output>/perf_data/, where it survives the removal of the scratch directory (with or without --keep-scratch) and a
    job-local scratch purge; its retained path, size and sha256 go to the block's 'perf_data'. A file that cannot be
    moved is an error and the scratch directory is then kept (False returned), so the data is not deleted."""
    d=ctx.out/'perf_data';kept=True
    for b in blocks:
        src=ctx.scratch/f'{b}.perf.data'
        if not src.is_file():res[b]['perf_data']={'retained':False,'reason':'no perf.data (the perf run failed or wrote none)'};continue
        try:
            d.mkdir(exist_ok=True);dst=d/src.name;shutil.move(str(src),str(dst))
            res[b]['perf_data']={'retained':True,'path':str(dst),'relative_path':str(dst.relative_to(ctx.out)),'bytes':dst.stat().st_size,'sha256':digest(dst)}
        except OSError as e:
            kept=False;res[b]['perf_data']={'retained':False,'reason':f'{type(e).__name__}: {e}','left_in':str(src)}
            errors.append(f'{b} perf.data not retained');log(f'{b}: perf.data NOT retained: {e}; the scratch directory {ctx.scratch} is kept')
    return kept

def p1(a)->int:
    ctx=Ctx(a,'p1');exe=Path(a.exe).resolve();prof=Path(a.prof_exe).resolve();out=ctx.out
    wsha=check_exe(exe,None,a.expect_sha256)['sha256'];check_exe(prof,'tier_timers')  # before any output (Z21's class)
    blocks=ctx.blocks;A,B=lanes_for(ctx,a.threads)
    ctx.open();ident=bk.identity({'worker':exe,'prof':prof},a.perf);ident['worker_check']=wsha;pa=perf_available(a.perf,ctx.scratch)
    # W19 (Stage-6 fix round 4): the release worker runs every block with or without perf (under perf record, or
    # directly), so the two streams run concurrently in both cases unless --sequential or one socket only
    conc=not a.sequential and B is not None;B=B if conc else A
    rkey,rtag=('perf_run','perf')if pa['ok']else('release_run','release')  # the release worker's run of a block, and its name in errors and files
    log(f'P1 blocks {blocks}; perf {"available" if pa["ok"] else "UNAVAILABLE: "+str(pa["reason"])}; release worker {"under perf" if pa["ok"] else "directly (no perf)"} on {len(A)} cores {A[0]}..{A[-1]}; tier timers on {B[0]}..{B[-1]} ({"concurrent" if conc else "sequential"})')
    res={b:{'block':{k:v for k,v in ctx.block(b).items()if k not in('seconds_per_point','graphs','net')}}for b in blocks}
    cg=a.call_graph!='none';twin=ctx.scratch/'c8d2_gmp_dbginfo'
    errors=[];rows={};keep_scratch=False  # rows[(block, 'release'|'prof')]: benchkit.rows_digest of the run (Z20, W19)
    def release_stream():
        for b in blocks:
            try:
                blk=ctx.block(b);o=ctx.scratch/f'{b}.{rtag}_native.json'
                if pa['ok']:
                    data=ctx.scratch/f'{b}.perf.data'
                    pre=[a.perf,'record','-N','-F',str(a.freq),'-o',str(data)]+(['--call-graph',a.call_graph]if cg else[])+['--']
                    log(f'perf record {b} ({blk["tasks"]} tasks, predicted {blk["predicted"].get("wall_seconds",0):.0f} s)')
                    r=run(pre+ctx.cmd(exe,blk,o,a.threads),A,a.threads,out/f'{b}.perf_record.log',ctx.pin,exe=exe)
                    r['record']=bk.parse_perf_record_stderr(Path(r['log']).read_text(errors='replace'))
                else:  # W19: the release worker itself on the block the tier timers measure, not on a mini block
                    log(f'release worker {b} ({blk["tasks"]} tasks, predicted {blk["predicted"].get("wall_seconds",0):.0f} s; no perf)')
                    r=run(ctx.cmd(exe,blk,o,a.threads),A,a.threads,out/f'{b}.release.log',ctx.pin,exe=exe)
                nr=native_result(o,a.threads,r);rows[b,'release']=bk.rows_digest(nr['native']['rows'])
                res[b][rkey]={**{k:v for k,v in r.items()if k!='log_tail'},'native':nr['summary']};o.unlink()
            except Exception as e:  # recorded; the other blocks still run
                res[b][f'{rkey}_error']=f'{type(e).__name__}: {e}';errors.append(f'{b} {rtag} run');log(f'{b} {rtag} run FAILED: {e}')
    def prof_stream():
        if pa['ok']and not a.no_srcline:
            log('building the debug-info twin');res['_twin']=build_twin(twin,B,ctx.pin,exe)
        for b in blocks:
            try:
                blk=ctx.block(b);o=ctx.scratch/f'{b}.prof_native.json';log(f'tier timers {b}')
                r=run(ctx.cmd(prof,blk,o,a.threads),B,a.threads,out/f'{b}.prof.log',ctx.pin,exe=prof);nr=native_result(o,a.threads,r)
                rows[b,'prof']=bk.rows_digest(nr['native']['rows'])
                res[b]['tier_run']={**{k:v for k,v in r.items()if k!='log_tail'},'native':nr['summary'],'tier_split':tier_split(nr['native'])};o.unlink()
            except Exception as e:  # recorded; the other blocks still run
                res[b]['tier_run_error']=f'{type(e).__name__}: {e}';errors.append(f'{b} tier run');log(f'{b} tier run FAILED: {e}')
    streams=[release_stream,prof_stream]
    if conc:
        with concurrent.futures.ThreadPoolExecutor(2)as ex:
            for f in [ex.submit(s)for s in streams]:f.result()
    else:
        for s in streams:s()
    for b in blocks:  # Z20, W19: a block whose two runs differ fails P1, with or without perf (before Z20, only recorded as rows_identical... false)
        if not(res[b].get(rkey)and res[b].get('tier_run')):res[b]['rows_identical_worker_vs_prof']=None;continue  # a failed run: already an error
        mm=bind_rows(b,rows[b,'release'],rows[b,'prof'],errors);res[b]['rows_identical_worker_vs_prof']=not mm
        if mm:res[b]['rows_mismatch']=mm
    srcinfo={'status':'not attempted'};fallback=None
    def record(stage:str)->dict:
        # Written after every phase, so that a job stopped by its time limit keeps what it has measured.
        rec={'schema':SCHEMA.format('p1'),'profile':'P1','stage':stage,'identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],'perf':pa,
             'settings':{'threads':a.threads,'freq':a.freq,'call_graph':a.call_graph,'perf_cpus':A,'tier_cpus':B,'concurrent':conc,'pinned':ctx.pin,
                         'fake_topology':a.fake_topology,'scratch':str(ctx.scratch),'expect_sha256':bk.expect_prefix(a.expect_sha256),
                         'keep_perf_data':a.keep_perf_data,'keep_scratch':a.keep_scratch,'scratch_kept':bool(a.keep_scratch or keep_scratch)},
             'srcline_twin':srcinfo,'blocks':{b:{k:v for k,v in res[b].items()}for b in blocks},'fallback':fallback,'errors':list(errors),'written_utc':utc()}
        jdump(out/'p1.json',rec);log(f'wrote {out/"p1.json"} (stage {stage})');return rec
    tw=res.pop('_twin',None);record('runs')
    if pa['ok']:
        if tw is not None and tw['returncode']==0:
            try:srcinfo={'twin_build':tw,**same_code(exe,twin,ctx.scratch)}
            except (RuntimeError,OSError)as e:srcinfo={'twin_build':tw,'identical':False,'differences':[f'comparison failed: {e}']}
        elif tw is not None:srcinfo={'twin_build':tw,'identical':False,'differences':[tw.get('error')or'twin build failed']}
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
        if a.keep_perf_data:keep_scratch=not keep_perf_data(ctx,blocks,res,errors)  # Z22: moved to <output>/perf_data
        else:
            for b in blocks:(ctx.scratch/f'{b}.perf.data').unlink(missing_ok=True)
    if not pa['ok']:
        # W19 (Stage-6 fix round 4): the tier-timer worker is bound to the release worker on every requested block (the
        # release_run above, compared like a perf run). Before, the fallback compared the two workers on the mini block
        # only, so a difference in a requested block went unnoticed whenever the mini block's rows agreed.
        fallback={'reason':pa['reason'],'tier_timers':'above (tier_run of every block)',
                  'binding':{'compared':'release_run (the release worker, directly) and tier_run (the tier-timer worker) of every block, at --threads',
                             'threads':a.threads,'blocks':{b:res[b].get('rows_identical_worker_vs_prof')for b in blocks}}}
        if shutil.which('ltrace'):
            # The GMP call counts: ltrace on a mini block, with a plain run of that mini block as its reference (the
            # traced run must compute what the plain one does; Z20's class)
            mb=next((b for b in ('heavy_power_L8','heavy_free_L8')if b in ctx.m['blocks']),blocks[-1])
            base=ctx.scratch/'mini_plain.json';lt=ctx.scratch/'mini_ltrace.json';lo=ctx.scratch/'ltrace.txt';r0=n0=None;ntasks=0
            try:
                blk=ctx.block(mb);mt=mini_tasks(blk,ctx.scratch/'mini.tasks');ntasks=len(bk.read_tasks(mt)[2])
                r0=run(ctx.cmd(exe,blk,base,1,tasks=mt),A[:1],1,out/'mini_plain.log',ctx.pin,exe=exe);n0=native_result(base,1,r0)
                r1=run(['ltrace','-c','-f','-e','__gmpf_*','-o',str(lo),'--',*ctx.cmd(exe,blk,lt,1,tasks=mt)],A[:1],1,out/'mini_ltrace.log',ctx.pin,timeout=3600,exe=exe)
                fallback['ltrace']={'block':mb,'tasks':ntasks,'points_per_task':64,'plain_wall_seconds':r0['wall_seconds'],'ltrace_wall_seconds':r1['wall_seconds'],
                                    'returncode':r1['returncode'],'table':bk.parse_ltrace_c(lo.read_text())if lo.is_file()else None}
                if r1['returncode']==0 and lt.is_file():
                    mm=bind_rows(f'{mb} (mini block, ltrace)',bk.rows_digest(n0['native']['rows']),bk.rows_digest(load(lt)['rows']),errors,
                                 ('the plain and the ltrace-traced release worker','the traced run is not the computation the plain run describes'))
                    fallback['ltrace']['rows_identical_plain_vs_ltrace']=not mm
                if lo.is_file():shutil.copy2(lo,out/'mini_ltrace_c.txt')
            except Exception as e:  # recorded; best effort, as before (the tier timers are bound above, not here)
                fallback['ltrace']=f"failed: {type(e).__name__}: {e}";log(f'ltrace on the mini block FAILED: {e}')
        else:fallback['ltrace']='ltrace not found'
    record('final');cleanup(ctx,a,keep_scratch)
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
    ctx=Ctx(a,'p2');exe=Path(a.exe).resolve();out=ctx.out;wsha=check_exe(exe,None,a.expect_sha256)['sha256']  # before any output (Z21's class)
    blocks=ctx.blocks;A,_B=lanes_for(ctx,a.threads)
    ctx.open();ident=bk.identity({'worker':exe},a.perf);ident['worker_check']=wsha;pa=perf_available(a.perf,ctx.scratch);res={}
    log(f'P2 blocks {blocks}; perf {"available" if pa["ok"] else "UNAVAILABLE: "+str(pa["reason"])}; {a.threads} threads on {A[0]}..{A[-1]}')
    wp=None if a.wait_policy=='default'else a.wait_policy;errors=[]
    for b in blocks:
        blk=ctx.block(b);res[b]={'block':{k:v for k,v in blk.items()if k not in('seconds_per_point','graphs','net')}}
        for tag,cpus,threads,tasks,pred in (('parallel',A,a.threads,None,blk['predicted'].get('wall_seconds')),('serial',A[:1],1,*serial_tasks(blk,ctx.scratch/f'{b}.serial.tasks',a.serial_seconds))):
            try:
                o=ctx.scratch/f'{b}.{tag}.json';st=ctx.scratch/f'{b}.{tag}.perfstat.csv'
                pre=[a.perf,'stat','-x,','-o',str(st),'-e',a.events,'--']if pa['ok']else[]
                log(f'{b} {tag}: {threads} thread(s){" under perf stat" if pre else ""}')
                r=run(pre+ctx.cmd(exe,blk,o,threads,tasks=tasks),cpus,threads,out/f'{b}.{tag}.log',ctx.pin,wait_policy=wp,exe=exe);nr=native_result(o,threads,r)
                stat=bk.parse_perf_stat_csv(st.read_text())if st.is_file()else None
                if st.is_file():shutil.copy2(st,out/st.name)
                res[b][tag]={**{k:v for k,v in r.items()if k!='log_tail'},'predicted_seconds':pred,'native':nr['summary'],'perf_stat':stat,
                             'promotion_free':nr['summary']['quad']==0 and nr['summary']['mp']==0};o.unlink()
            except Exception as e:  # recorded; the other runs still go
                res[b][tag]={'error':f'{type(e).__name__}: {e}'};errors.append(f'{b} {tag}');log(f'{b} {tag} FAILED: {e}')
    ipc={b:{t:((res[b][t].get('perf_stat')or{}).get('derived')or{}).get('ipc')for t in ('parallel','serial')}for b in res}
    rec={'schema':SCHEMA.format('p2'),'profile':'P2','identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],'perf':pa,
         'settings':{'threads':a.threads,'events':a.events,'wait_policy':a.wait_policy,'serial_seconds':a.serial_seconds,'cpus':A,'pinned':ctx.pin,'fake_topology':a.fake_topology,
                     'expect_sha256':bk.expect_prefix(a.expect_sha256)},
         'blocks':res,'ipc':ipc,'decision_rule':'R6 go if IPC < 1.5 on the promotion-free blocks or the interleave-probe speedup >= 1.2 (tools/benchmark.py --interleave-probe)',
         'errors':errors,'finished_utc':utc()}
    jdump(out/'p2.json',rec);cleanup(ctx,a);log(f'wrote {out/"p2.json"}'+(f'; ERRORS: {errors}'if errors else''));return 1 if errors else 0

# ---------------------------------------------------------------- P3
def p3(a)->int:
    # Z21 (Stage-6 fix round 3): the ratio-histogram build is bound by --expect-sha256 like P1's and P2's worker (it was
    # dropped here), before any output, scratch or run.
    # W19's class (Stage-6 fix round 4): the release worker is checked here too (a release build), before any output
    ctx=Ctx(a,'p3');exe=Path(a.exe).resolve();wexe=Path(a.worker_exe).resolve();out=ctx.out
    rsha=check_exe(exe,'ratio_histogram',a.expect_sha256)['sha256'];wsha=check_exe(wexe,None)['sha256']
    threads=a.threads or len(ctx.cores);A=bk.partition(ctx.cores,1,threads)[0];blocks=ctx.blocks;rates=[s for s in a.rates.split(',')if s];res={}
    ctx.open();ident=bk.identity({'ratiohist':exe,'worker':wexe},a.perf);ident['ratiohist_check']=rsha;ident['worker_check']=wsha
    log(f'P3 blocks {blocks} at rates {rates}; {threads} threads; each also with the release worker (rows bound)');errors=[]
    for b in blocks:
        blk=ctx.block(b)
        for rate in rates:
            k=f'{b}@{rate}'
            try:
                o=ctx.scratch/f'{b}.{rate}.json';log(f'{b} rate {rate}')
                r=run(ctx.cmd(exe,blk,o,threads,rate=rate),A,threads,out/f'{b}.rate{rate}.log',ctx.pin,exe=exe);nr=native_result(o,threads,r)
                res[k]={'block':b,'sector':blk['sector'],'L':blk['L'],'rate':rate,'graphs':len(blk['graphs']),'wall_seconds':r['wall_seconds'],
                        'native':nr['summary'],'ratio':bk.ratio_summary(nr['native']),'rows_identical_worker_vs_ratiohist':None};o.unlink()
            except Exception as e:  # recorded; the other runs still go
                errors.append(f'{k}: {type(e).__name__}: {e}');log(f'{b} rate {rate} FAILED: {e}');continue
            # W19's class: the margins count only if the ratio-histogram build computes what the release worker computes
            # on this very block and rate (every measured run bound, no sample of them); a failed release run is an error
            try:
                ow=ctx.scratch/f'{b}.{rate}.release.json';log(f'{b} rate {rate}: release worker')
                rw=run(ctx.cmd(wexe,blk,ow,threads,rate=rate),A,threads,out/f'{b}.rate{rate}.release.log',ctx.pin,exe=wexe);nw=native_result(ow,threads,rw)
                mm=bind_rows(k,bk.rows_digest(nw['native']['rows']),bk.rows_digest(nr['native']['rows']),errors,RATIO_PAIR)
                res[k].update({'release_run':{'wall_seconds':rw['wall_seconds'],'team':rw['team'],'log':rw['log'],'native':nw['summary']},
                               'rows_identical_worker_vs_ratiohist':not mm,**({'rows_mismatch':mm}if mm else{})});ow.unlink()
            except Exception as e:  # recorded: without the binding the margins of this run are not accepted
                res[k]['release_run_error']=f'{type(e).__name__}: {e}';errors.append(f'{k} release run: {type(e).__name__}: {e}');log(f'{b} rate {rate} release run FAILED: {e}')
    rec={'schema':SCHEMA.format('p3'),'profile':'P3','identity':ident,'fixtures_manifest_sha256':ctx.m['_manifest_sha256'],
         'settings':{'threads':threads,'rates':rates,'cpus':A,'pinned':ctx.pin,'fake_topology':a.fake_topology,'expect_sha256':bk.expect_prefix(a.expect_sha256),
                     'worker_exe':str(wexe)},
         'bins':'floor(log10(|v|/err)); key 0 = every ratio >= 1; -401 = zero_or_below (0 or < 1e-400). ld_fail: points failing the 1e-9 test; quad: every binary128 evaluation (the 1e-23 test fails below 1e-23); mp: every MP evaluation',
         'results':res,'errors':errors,'all_checks_ok':bool(res)and not errors and all(v['ratio']['ok']for v in res.values()),'finished_utc':utc()}
    jdump(out/'p3.json',rec);cleanup(ctx,a);log(f'wrote {out/"p3.json"}');return 0 if rec['all_checks_ok']else 1

def cleanup(ctx:Ctx,a,keep:bool=False)->None:
    """The scratch directory removed unless --keep-scratch (or keep: P1 could not move a perf.data out of it, Z22)."""
    if not(a.keep_scratch or keep):shutil.rmtree(ctx.scratch,ignore_errors=True)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sub=p.add_subparsers(dest='mode',required=True)
    for mode in ('p1','p2','p3'):
        q=sub.add_parser(mode);q.add_argument('--output',type=Path,required=True);q.add_argument('--blocks',default=DEFAULTS[mode])
        q.add_argument('--exe',default=str(ROOT/('bin/c8d2_gmp_ratiohist'if mode=='p3'else'bin/c8d2_gmp')));q.add_argument('--expect-sha256')
        q.add_argument('--threads',type=int,default=0 if mode=='p3'else 64,help='p3: 0 = every core of the allocation')
        q.add_argument('--fixtures',type=Path,default=bk.FIXTURES8);q.add_argument('--scratch');q.add_argument('--perf',default='perf')
        q.add_argument('--fake-topology');q.add_argument('--no-pin',action='store_true');q.add_argument('--keep-scratch',action='store_true')
        if mode=='p1':  # Z22: only P1 writes perf.data (P2 copies its perf stat CSVs to the output; P3 runs no perf)
            q.add_argument('--keep-perf-data',action='store_true',help='move every block\'s perf.data into <output>/perf_data/ (recorded; large)')
            q.add_argument('--prof-exe',default=str(ROOT/'bin/c8d2_gmp_prof'));q.add_argument('--freq',type=int,default=999)
            q.add_argument('--call-graph',default='none',choices=('none','fp','dwarf'));q.add_argument('--sequential',action='store_true');q.add_argument('--no-srcline',action='store_true')
        if mode=='p2':
            q.add_argument('--events',default=P2_EVENTS);q.add_argument('--serial-seconds',type=float,default=30.)
            q.add_argument('--wait-policy',default='passive',choices=('passive','active','default'))
        if mode=='p3':
            q.add_argument('--rates',default='.8,.9')
            q.add_argument('--worker-exe',default=str(ROOT/'bin/c8d2_gmp'),help='the release worker the ratio-histogram rows must equal on every block and rate')
    q=sub.add_parser('p1-reparse',help='rebuild a finished P1 record\'s perf summaries from its saved report texts (Mac-runnable)')
    q.add_argument('--input',type=Path,required=True,help='the P1 output directory (holds p1.json and <block>.perf_report_*.txt)')
    q.add_argument('--output',type=Path,help='default <input>/p1_reparsed.json')
    a=p.parse_args(argv)
    try:return {'p1':p1,'p2':p2,'p3':p3,'p1-reparse':p1_reparse}[a.mode](a)
    except bk.BenchError as e:print(f'perf_profile {a.mode}: {e}',file=sys.stderr);return e.code

if __name__=='__main__':sys.exit(main())
