#!/usr/bin/env python3
"""A-RPL-6 thread identity (HR22): an L8 free block and an L8 power block of 64 tasks x 256 points (32 kernels: the 8
heaviest and 24 random ones, 2 replicates) give identical scientific fields (every row field except 'seconds', the
class-B tail fields included) at 1, 8, 16 and 64 threads, and when split over 8 lane processes of 8 threads each,
run concurrently on disjoint CPU sets of this job's affinity mask. Every run deletes and rewrites its own output file,
and the recomputation is asserted (a fresh file with a new integration time). Both backends unless --backends.
--executable PATH tests that one worker instead (A-FLAG-3 F5: an opt-in numerics profile, bin/c8d2_gmp_<p>; also
tests/numerics_flags.py). The record goes only to --output.
Team sizes (X3, Stage-6 fix round 1): the worker reports the thread count it was asked for, not the team the OpenMP
runtime gave it, and an inherited OMP_THREAD_LIMIT=1 (or OMP_DYNAMIC=true) would run every request serially and still
give identical rows. Every run therefore gets the inherited environment WITHOUT any OpenMP control (OMP_*, GOMP_*,
KMP_*) and with OMP_DYNAMIC=false (child_env), and its team is observed while it runs: the largest number of threads
of the worker process (/proc/<pid>/task, sampled every POLL_SECONDS; libgomp keeps a region's threads until the
process exits, and the worker starts no other thread). A run or lane whose observed team is not exactly the requested
thread count fails the block (AssertionError), and so does a run whose team cannot be observed (no /proc). The record
lists the observed teams (team_observed, teams_observed) and team_sizes_verified.
W22 (Stage-6 fix round 4, a host residual of round 3): "status":"passed" (A-RPL-6 acceptance evidence) only with the
complete coverage coverage() recomputes from the record: both default backends (bin/c8d2_gmp and bin/c8d2_decimal,
no --executable) x both sectors, each block identical, of 64 tasks x 256 points on 32 graphs, run at exactly 1, 8, 16
and 64 threads and as 8 lanes x 8 threads, every observed team the requested size (team_observed, teams_observed) and
team_sizes_verified. A run restricted by --backends, --threads, --lanes or --lane-threads whose blocks are identical
is labelled "development run (...)" naming what it lacks, and exits 3 (0: acceptance evidence; a failed block raises).
A --executable run (F5 of an opt-in profile, A-FLAG-3) is judged by coverage(record, gate='F5') (both sectors of that
one executable, the same sizes, threads, lanes and teams) and says F5_STATUS, never plain "passed", so it cannot be
taken for A-RPL-6 evidence (--check RECORD --gate F5). A consumer checks a record with `thread_identity.py --check RECORD` (exit 0 only for a record that says
"passed" and whose recomputed coverage is complete) or coverage(record); coverage(record, teams=False) skips only the
team conditions, for the summaries of records made before X3 (which observed no team)."""
from __future__ import annotations
from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from common import dump,digest,environment_record,load
from validate import exe,stage,heavy_and_random,tasks_text,task_rows,native_cmd,make_net,scientific,GAMMA8,require

OMP_PREFIXES=('OMP_','GOMP_','KMP_')
POLL_SECONDS=0.002
THREADS=(1,8,16,64);LANES,LANE_THREADS=8,8;BACKENDS=('gmp','decimal');SECTORS=('free','power')   # A-RPL-6's configuration
TASKS,POINTS,GRAPHS=64,256,32   # per block: 32 kernels (8 heaviest, 24 random) x 2 replicates, 256 points per task

def child_env(base=None)->dict:
    """The worker environment of a thread-identity run: the inherited one without any OpenMP control (OMP_*, GOMP_*,
    KMP_*: OMP_THREAD_LIMIT, OMP_DYNAMIC=true or OMP_NUM_THREADS could change the team the worker's num_threads clause
    asks for) and OMP_DYNAMIC=false (the runtime gives every parallel region the requested team)."""
    e={k:v for k,v in (os.environ if base is None else base).items()if not k.startswith(OMP_PREFIXES)}
    e['OMP_DYNAMIC']='false';return e

def task_count(pid:int)->int|None:
    """The number of threads of a live process (Linux /proc/<pid>/task), None when it cannot be read."""
    try:return len(os.listdir(f'/proc/{pid}/task'))
    except OSError:return None

class Team:
    """Samples a child process's thread count (task_count) every POLL_SECONDS until stop(): .max is the largest count
    seen (None when no sample could be read)."""
    def __init__(self,proc:subprocess.Popen):
        self.proc=proc;self.max=None;self.samples=0;self._stop=threading.Event();self._count=task_count
        self._thread=threading.Thread(target=self._run,daemon=True);self._thread.start()
    def _run(self)->None:
        while not self._stop.is_set():
            n=self._count(self.proc.pid)
            if n is not None:self.max=n if self.max is None else max(self.max,n);self.samples+=1
            self._stop.wait(POLL_SECONDS)
    def stop(self)->int|None:
        self._stop.set();self._thread.join();return self.max

def launch(cmd,cpus=None)->tuple[subprocess.Popen,Team]:
    """Start one worker run (the sanitized environment, pinned to cpus when given) and watch its team."""
    p=subprocess.Popen(list(map(str,cmd)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=child_env(),
                       preexec_fn=(lambda:os.sched_setaffinity(0,cpus))if cpus else None)
    return p,Team(p)

def finish(p:subprocess.Popen,team:Team,out:Path,requested:int,label:str)->tuple[dict,int]:
    """Wait for the run; its output must exist and its observed team must be the requested thread count."""
    _,err=p.communicate();seen=team.stop()
    if p.returncode:raise RuntimeError(err[-2000:])
    if not out.exists():raise AssertionError(f'{out} was not written')
    if seen is None:raise AssertionError(f'{label}: the OpenMP team of the run cannot be observed (no /proc/<pid>/task): team sizes unverified')
    if seen!=requested:raise AssertionError(f'{label}: {requested} threads requested, the run had {seen} (an OpenMP team other than the request: '
                                            'OMP_THREAD_LIMIT, OMP_DYNAMIC or the runtime; thread identity would not test concurrent execution)')
    return load(out),seen

def run_one(cmd,out:Path,threads:int,cpus=None,label:str='run')->tuple[dict,int]:
    """One run of `threads` threads: (its output, the observed team size = threads)."""
    out.unlink(missing_ok=True);p,team=launch(cmd,cpus);return finish(p,team,out,threads,label)

def run_lanes(lanes:list,threads:int,label:str='lanes')->tuple[list[dict],list[int]]:
    """Concurrent lane processes [(cmd, out, cpus)], each of `threads` threads: (outputs, observed teams)."""
    procs=[]
    for cmd,out,cpus in lanes:out.unlink(missing_ok=True);procs.append((out,*launch(cmd,cpus)))
    docs=[];teams=[];err=None
    for i,(out,p,team)in enumerate(procs):
        try:d,t=finish(p,team,out,threads,f'{label} lane {i}');docs.append(d);teams.append(t)
        except (RuntimeError,AssertionError)as e:err=err or e
    if err:raise err
    return docs,teams

def lanes_cpus(n:int)->list[list[int]]:
    cpus=sorted(os.sched_getaffinity(0));size=len(cpus)//n
    if size<1:raise SystemExit(f'{len(cpus)} CPUs in the affinity mask cannot hold {n} lanes')
    return [cpus[i*size:(i+1)*size]for i in range(n)]

def block(td:Path,backend:str|None,sector:str,threads:list[int],lanes:int,lane_threads:int,executable:Path|None=None)->dict:
    x=Path(executable)if executable else exe(backend);tag=backend or x.name
    ids=heavy_and_random(sector,8,8,24,9001+(5 if sector=='power'else 0));root=stage(td/sector,sector,8,ids)
    net=td/f'{sector}.bin'
    if not net.exists():make_net(net,2,31,60,61817+(5 if sector=='power'else 0),256)
    rows=task_rows(ids,2,256);tasks=td/f'{sector}_tasks';tasks.write_text(tasks_text(8,8,rows))
    runs={};outs={}
    for th in threads:
        o=td/f'{sector}_{tag}_t{th}.json';d,seen=run_one(native_cmd(x,root,GAMMA8,net,tasks,o,threads=th),o,th,label=f'{tag} {sector} {th} threads')
        outs[th]=d;runs[f'threads_{th}']={'integration_seconds':d['integration_seconds'],'sha256':digest(o),'team_observed':seen}
    ref=[scientific(r)for r in outs[threads[0]]['rows']]
    for th,d in outs.items():
        if [scientific(r)for r in d['rows']]!=ref:raise AssertionError(f'{tag} {sector}: {th} threads differ from {threads[0]}')
    # 8 lane processes x 8 threads on disjoint CPU sets, launched together
    parts=[rows[i::lanes]for i in range(lanes)];cpus=lanes_cpus(lanes);spec=[]
    for i,part in enumerate(parts):
        t=td/f'{sector}_lane{i}.tasks';t.write_text(tasks_text(8,8,part));o=td/f'{sector}_{tag}_lane{i}.json'
        spec.append((native_cmd(x,root,GAMMA8,net,t,o,threads=lane_threads),o,cpus[i]))
    docs,teams=run_lanes(spec,lane_threads,f'{tag} {sector} {lanes} x {lane_threads}')
    merged={}
    for d in docs:
        for r in d['rows']:merged[r['uid']]=scientific(r)
    lane_rows=[merged[r['uid']]for r in outs[threads[0]]['rows']]
    if lane_rows!=ref:raise AssertionError(f'{tag} {sector}: the {lanes} x {lane_threads} lane split differs')
    runs[f'lanes_{lanes}x{lane_threads}']={'cpu_sets':[f'{c[0]}-{c[-1]}'for c in cpus],'teams_observed':teams}
    return {'backend':backend,'executable':str(x),'executable_sha256':digest(x),'sector':sector,'graphs':ids,'tasks':len(rows),'points_per_task':256,'identical':True,
            'team_sizes_verified':True,'runs':runs,'quad':sum(r['quad']for r in outs[threads[0]]['rows']),'mp':sum(r['mp']for r in outs[threads[0]]['rows'])}

def coverage(rec:dict,teams:bool=True,gate:str='A-RPL-6')->dict:
    """W22: whether a thread_identity record is A-RPL-6 acceptance evidence, recomputed from its blocks. complete only
    with: threads exactly THREADS and lanes LANES x LANE_THREADS; one block per (backend, sector) of BACKENDS x SECTORS
    and no other, each the default worker of its backend (no --executable: its executable, when recorded, is
    bin/c8d2_<backend>), identical, TASKS tasks x POINTS points on GRAPHS graphs, with a run at every thread count of
    THREADS and the LANES x LANE_THREADS lane split (LANES CPU sets); with teams, every run's observed team equal to its
    thread count, every lane's to LANE_THREADS, and team_sizes_verified in each block and the record (X3). teams=False
    skips only the team conditions (records made before X3). gate='F5' (A-FLAG-3 F5, an opt-in profile executable run
    with --executable): the same conditions for one block per sector of that one executable (no backend), which must
    not be a default worker. {'gate', 'complete': bool, 'why': [...], 'teams_checked': bool}."""
    if gate not in('A-RPL-6','F5'):raise ValueError(f'unknown gate {gate!r}')
    why=[];rec=rec if isinstance(rec,dict)else{}
    if rec.get('test')!='thread_identity':why.append(f'test {rec.get("test")!r}, not thread_identity')
    if not isinstance(rec.get('threads'),list)or sorted(rec['threads'])!=list(THREADS):why.append(f'threads {rec.get("threads")!r}, not {list(THREADS)}')
    if rec.get('lanes')!=f'{LANES}x{LANE_THREADS}':why.append(f'lanes {rec.get("lanes")!r}, not {LANES}x{LANE_THREADS}')
    blocks=rec.get('blocks')if isinstance(rec.get('blocks'),list)else[]
    keys=[(b.get('backend'),b.get('sector'))if isinstance(b,dict)else None for b in blocks]
    want=[(b,s)for b in BACKENDS for s in SECTORS]if gate=='A-RPL-6'else[(None,s)for s in SECTORS]
    if sorted(map(str,keys))!=sorted(map(str,want)):why.append(f'blocks {keys}, not one per (backend, sector) of {want} (--backends or --executable)')
    if gate=='F5':
        xs={str((b or{}).get('executable'))for b in blocks if isinstance(b,dict)}
        if len(xs)!=1 or any(Path(x).name in('c8d2_gmp','c8d2_decimal')for x in xs):why.append(f'executables {sorted(xs)}, not one opt-in profile executable')
    lane=f'lanes_{LANES}x{LANE_THREADS}'
    for b in blocks:
        if not isinstance(b,dict):continue
        tag=f'{b.get("backend")} {b.get("sector")}'
        x=b.get('executable')
        if gate=='A-RPL-6'and x is not None and Path(str(x)).name!=f'c8d2_{b.get("backend")}':why.append(f'{tag}: executable {x!r}, not the default bin/c8d2_{b.get("backend")} (--executable)')
        if b.get('identical')is not True:why.append(f'{tag}: not identical')
        if (b.get('tasks'),b.get('points_per_task'),len(b.get('graphs')or[]))!=(TASKS,POINTS,GRAPHS):
            why.append(f'{tag}: {b.get("tasks")!r} tasks x {b.get("points_per_task")!r} points on {len(b.get("graphs")or[])} graphs, not {TASKS} x {POINTS} on {GRAPHS}')
        runs=b.get('runs')if isinstance(b.get('runs'),dict)else{}
        need=[f'threads_{t}'for t in THREADS]+[lane]
        if sorted(runs)!=sorted(need):why.append(f'{tag}: runs {sorted(runs)}, not {need}')
        if len((runs.get(lane)or{}).get('cpu_sets')or[])!=LANES:why.append(f'{tag}: {len((runs.get(lane)or{}).get("cpu_sets")or[])} lane CPU sets, not {LANES}')
        if teams:
            bad=[f'threads_{t}: {(runs.get(f"threads_{t}")or{}).get("team_observed")!r}'for t in THREADS if (runs.get(f'threads_{t}')or{}).get('team_observed')!=t]
            if (runs.get(lane)or{}).get('teams_observed')!=[LANE_THREADS]*LANES:bad.append(f'{lane}: {(runs.get(lane)or{}).get("teams_observed")!r}')
            if bad:why.append(f'{tag}: observed teams other than requested ({"; ".join(bad)})')
            if b.get('team_sizes_verified')is not True:why.append(f'{tag}: team_sizes_verified {b.get("team_sizes_verified")!r}')
    if teams and rec.get('team_sizes_verified')is not True:why.append(f'team_sizes_verified {rec.get("team_sizes_verified")!r}')
    return {'gate':gate,'complete':not why,'why':why,'teams_checked':bool(teams)}

F5_STATUS='passed (F5 of an opt-in profile executable; not A-RPL-6 evidence)'
def check(path:Path,gate:str='A-RPL-6')->int:
    """--check [--gate F5]: 0 for a record whose status is that gate's pass ("passed" for A-RPL-6, F5_STATUS for F5)
    and whose recomputed coverage of the gate is complete, 1 otherwise."""
    rec=json.loads(Path(path).read_text());cov=coverage(rec,gate=gate);good=rec.get('status')==('passed'if gate=='A-RPL-6'else F5_STATUS)and cov['complete']
    print(json.dumps({'record':str(path),'status':rec.get('status'),'acceptance':good,'coverage':cov},indent=1));return 0 if good else 1

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);ap.add_argument('--backends',nargs='+',default=list(BACKENDS),choices=BACKENDS)
    ap.add_argument('--executable',type=Path,help='test this worker only (an opt-in numerics profile; A-FLAG-3 F5)')
    ap.add_argument('--threads',type=int,nargs='+',default=list(THREADS));ap.add_argument('--lanes',type=int,default=LANES);ap.add_argument('--lane-threads',type=int,default=LANE_THREADS)
    ap.add_argument('--check',type=Path,metavar='RECORD',help='check an existing record: exit 0 only for acceptance evidence (W22)')
    ap.add_argument('--gate',choices=('A-RPL-6','F5'),default='A-RPL-6',help='with --check: the gate (F5: a --executable record)')
    a=ap.parse_args(argv)
    if a.check:return check(a.check,a.gate)
    if a.output and a.output.exists():raise SystemExit(f'{a.output} exists')
    targets=[(None,a.executable.resolve())]if a.executable else[(b,None)for b in a.backends]
    require(*(x or exe(b)for b,x in targets),hint='make && make gmp')
    res=[];t0=time.time()
    with tempfile.TemporaryDirectory(prefix='c8d2_threads_')as td:
        for b,x in targets:
            for sector in ('free','power'):res.append(block(Path(td),b,sector,a.threads,a.lanes,a.lane_threads,executable=x));print(json.dumps(res[-1])[:400],flush=True)
    rec={'status':None,'test':'thread_identity','threads':a.threads,'lanes':f'{a.lanes}x{a.lane_threads}','blocks':res,
         'team_sizes_verified':all(b['team_sizes_verified']for b in res),'omp_environment':'sanitized (no OMP_*, GOMP_*, KMP_*; OMP_DYNAMIC=false)',
         'wall_seconds':round(time.time()-t0,1),'environment':environment_record()}
    gate='F5'if a.executable else'A-RPL-6'
    rec['coverage']=coverage(json.loads(json.dumps(rec,default=str)),gate=gate)  # W22: judged on the record as written
    rec['status']=(('passed'if gate=='A-RPL-6'else F5_STATUS)if rec['coverage']['complete']
                   else'development run ('+'; '.join(rec['coverage']['why'])[:500]+')')
    if a.output:dump(a.output,rec)
    print(json.dumps({k:v for k,v in rec.items()if k!='environment'},indent=1)[:4000])
    return 0 if rec['coverage']['complete']else 3

if __name__=='__main__':sys.exit(main())
