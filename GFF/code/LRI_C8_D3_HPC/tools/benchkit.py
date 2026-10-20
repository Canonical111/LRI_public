#!/usr/bin/env python3
"""Shared helpers of the Stage-4a profiling tools (PLAN "Performance plan", P1-P4; tools/prepare_benchmarks.py --order 8,
tools/perf_profile.py, tools/benchmark.py --lane-shapes / --interleave-probe).

Port to C8(3) of C62d's tools/benchkit.py (LRI_C8_D2_HPC@651c56f, sha256 dd185ce1...; the d-independent design of its
Stage 4a, reused as the plan's Performance plan asks). The d=3 changes: names (c8d3, C8D3TASKS1, gamma_d3_8.txt, seed
prefix c8-d3-bench), the worker's --mp-check argument (native_cmd), the d=3 row fields of the identity digest
(production.SCIENTIFIC), the d=3 ratio-histogram keys (bins -1..-401 and zero_or_below; ratios >= 1 are in -1), and the
shares the d=3 kernel adds (sqrtq and sqrtl: one square root per term, U*sqrt(U), in every tier).

- Fixtures: benchmarks/fixtures8/manifest.json (schema c8-d3-benchmark-fixtures-1) and its task and net files, every file
  verified against the manifest's sha256, the inventory and the gamma file against the pins of the inputs they were made
  from. Graph members are staged from the pinned packs (the L8 packs are built by `make inputs-l8`, not in git), each
  member verified against its inventory sha256, exactly as production.py's stage_graphs does. verified_inputs (opt_speed,
  prepare_benchmarks --order 8; S4-005) first runs prepare_inputs.verify on the inputs folder and records the verified
  manifest, inventory and gamma hashes.
- CPU sets: NxT lane shapes partitioned into disjoint, NUMA-aligned sets of physical cores of the job's affinity set
  (sysfs NUMA lists, one logical CPU per core), refused when a shape does not fit; deterministic LPT shares and
  production-style blocks (each part's tasks by cost descending, cut into checkpoint blocks of max(16 x T, 256) tasks).
- Run identity: host, CPU model, kernel, lscpu/numactl text, perf version and paranoia, Slurm ids, OpenMP environment,
  the package commit (or export name) and every executable's sha256, --describe and build record.
- Parsers (pure, unit-tested on captured text in tests/test_profiling.py): perf report (--stdio, -n, any of the sort keys
  symbol / dso / dso,symbol), perf stat -x, CSV, the perf record summary line, perf annotate --stdio, addr2line -a -i -f,
  ltrace -c, /proc/<pid>/numa_maps, /sys node numastat counters, and the native ratio histograms of bin/c8d3_gmp_ratiohist.
Nothing here changes a numerical input or the worker: profiling only (Stage 4a).
"""
from __future__ import annotations
import hashlib,heapq,json,math,os,platform,re,shutil,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,canon,digest,load,read_member,utc,verified_bytes

FIXTURE_SCHEMA='c8-d3-benchmark-fixtures-1'
FIXTURES8=ROOT/'benchmarks'/'fixtures8'
TASK_MAGIC='C8D3TASKS1';ORDER=8;GAMMA='gamma_d3_8.txt'
# Every scientific field of a d=3 row (production.SCIENTIFIC; 'seconds' is the only field left out).
SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax','nondirect','nonmoderate',
            'mp_checked','mp_hist','mp_min_log10','mp_alarm')
MP_CHECK_MODES=('on','off','stride16')

def cpu_model_noprobe()->str|None:
    """The CPU model without starting any process: /proc/cpuinfo's model name (Linux), else platform.machine()."""
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):return line.split(':',1)[1].strip()
    except OSError:pass
    return platform.machine()or None

class BenchError(Exception):
    """A refusal: code 64 invalid input or lane shape, 65 fixture/input/executable mismatch, 69 a tool or input missing."""
    def __init__(self,code:int,msg:str):super().__init__(msg);self.code=code

# ---------------------------------------------------------------- seeds and fixtures
def bench_seed(seed:int,name:str,role:str)->int:
    """A fixture block's native ('native') or Sobol-net ('net') seed: SHA-256 of 'c8-d3-bench|<seed>|<block>|<role>',
    first 8 bytes little endian, mod 2^63 (the scheme of production.derive_seeds, with its own prefix)."""
    return int.from_bytes(hashlib.sha256(f'c8-d3-bench|{seed}|{name}|{role}'.encode()).digest()[:8],'little')%(2**63)

def rank_key(seed:int,name:str,gid:int)->str:
    """Deterministic, version-independent random order of graphs: sort by SHA-256 of 'c8-d3-bench|<seed>|<name>|<id>'."""
    return hashlib.sha256(f'c8-d3-bench|{seed}|{name}|{gid}'.encode()).hexdigest()

def inputs_of(rel:str):
    """The production.Inputs object of an inputs folder relative to the package (inputs/ or a test fixture)."""
    import production as prod
    d=ROOT/rel
    if not (d/'manifest.json').is_file():raise BenchError(69,f'{d}/manifest.json is missing')
    return prod.Inputs(d,load(d/'manifest.json'))

def verified_inputs(rel:str,env=None)->tuple:
    """inputs_of after prepare_inputs.verify (S4-005; the plan's own check, not a copy): the manifest's schema, every
    file it pins by sha256 (inventory.json and gamma_d3_8.txt among them), the Stage-2b chain to the H1 and d3 pins and
    the vendored pins; missing L8 packs only with C8_ALLOW_NO_L8=1 (recorded as skipped). The inventory is parsed from
    exactly the bytes checked against its pin. Returns (production.Inputs on the verified manifest, inventory, the
    record of the verified hashes); BenchError 65 on any failure, before anything is selected or run."""
    import prepare_inputs as pi,production as prod
    I=inputs_of(rel)
    try:
        v=pi.verify(I.dir,env);pins=v['manifest']['sha256']
        inv=json.loads(verified_bytes(I.where('inventory.json'),pins['inventory.json']))
    except (ValueError,OSError,KeyError)as e:raise BenchError(65,f'{I.dir}: the inputs do not verify against their manifest (prepare_inputs.verify): {e}')from None
    rec={'inputs':v['inputs'],'manifest_sha256':v['manifest_sha256'],'inventory_sha256':pins['inventory.json'],'gamma_sha256':pins[GAMMA],
         'skipped':v['skipped'],'test_only_reasons':v['test_only_reasons'],'checked':'tools/prepare_inputs.py verify (every pinned file, the Stage-2b chain, the vendored pins)'}
    return prod.Inputs(I.dir,v['manifest']),inv,rec

def load_fixtures(folder:Path=FIXTURES8)->dict:
    """The fixture manifest after checking every listed file's sha256 and the inventory, gamma and inputs-manifest pins.
    Adds '_folder', '_manifest_sha256' and '_inputs' (the production.Inputs object)."""
    folder=Path(folder);mf=folder/'manifest.json'
    if not mf.is_file():raise BenchError(69,f'{mf} is missing: run tools/prepare_benchmarks.py --order 8 first')
    raw=mf.read_bytes();m=json.loads(raw)
    if m.get('schema')!=FIXTURE_SCHEMA:raise BenchError(65,f'{mf}: schema {m.get("schema")!r}, expected {FIXTURE_SCHEMA}')
    for name,sha in sorted(m['sha256'].items()):
        p=folder/name
        if not p.is_file():raise BenchError(65,f'fixture file missing: {p}')
        if digest(p)!=sha:raise BenchError(65,f'fixture file changed: {p} (its sha256 differs from {mf})')
    I=inputs_of(m['inputs'])
    if digest(I.dir/'manifest.json')!=m['inputs_manifest_sha256']:raise BenchError(65,f'{I.dir}/manifest.json differs from the one the fixtures were made with')
    for key,name in (('inventory_sha256','inventory.json'),('gamma_sha256',GAMMA)):
        if digest(I.where(name))!=m[key]:raise BenchError(65,f'{I.where(name)} differs from the {name} the fixtures were made with ({key})')
    m['_folder']=str(folder);m['_manifest_sha256']=hashlib.sha256(raw).hexdigest();m['_inputs']=I
    return m

def block_of(m:dict,name:str)->dict:
    if name not in m['blocks']:raise BenchError(64,f'no fixture block {name!r}; known: {", ".join(sorted(m["blocks"]))}')
    b=dict(m['blocks'][name]);f=Path(m['_folder']);b['tasks_path']=str(f/b['files']['tasks']);b['net_path']=str(f/b['files']['net'])
    return b

def read_tasks(path:Path)->tuple[int,int,list[tuple]]:
    lines=Path(path).read_text().splitlines();h=lines[0].split()
    if len(h)!=4 or h[0]!=TASK_MAGIC:raise BenchError(65,f'{path}: not a {TASK_MAGIC} task file')
    order,L,nt=map(int,h[1:]);rows=[tuple(map(int,ln.split()))for ln in lines[1:]if ln.strip()]
    if len(rows)!=nt or any(len(r)!=6 for r in rows):raise BenchError(65,f'{path}: {len(rows)} task rows, header says {nt}')
    return order,L,rows

def write_tasks(path:Path,order:int,L:int,rows)->None:
    rows=list(rows)
    if not rows:raise BenchError(64,f'{path}: no tasks')
    Path(path).write_text(f'{TASK_MAGIC} {order} {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows))

def stage_members(pack:Path,members:dict,L:int,ids,dest:Path)->dict:
    """dest/L<L>/G<id>.txt for every graph id, read from the pinned pack at the member's inventory offset and verified
    against its sha256 (production.stage_graphs); members: {id: inventory row (offset, length, sha256)}. Returns graphs,
    bytes and seconds."""
    t0=time.perf_counter();d=Path(dest)/f'L{L}';d.mkdir(parents=True,exist_ok=True);n=nbytes=0;pack=Path(pack)
    if not pack.is_file():raise BenchError(69,f'{pack} is missing: hard-link the pinned packs (make link-l8 STORE=$C8_STORE) or build them (make inputs-l8)')
    fd=os.open(pack,os.O_RDONLY)   # each member read exactly (common.read_member: os.pread, no Python buffer; F12)
    try:
        for gid in sorted(set(ids)):
            r=members.get(gid)
            if r is None:raise BenchError(65,f'graph {gid} is not in the inventory of {pack.name}')
            data=read_member(fd,r['offset'],r['length'])
            if len(data)!=r['length']or hashlib.sha256(data).hexdigest()!=r['sha256']:raise BenchError(65,f'{pack} member G{gid} does not match its inventory sha256')
            (d/f'G{gid}.txt').write_bytes(data);n+=1;nbytes+=len(data)
    finally:os.close(fd)
    return {'graphs':n,'bytes':nbytes,'seconds':time.perf_counter()-t0}

def stage_graphs(I,inventory:dict,sector:str,L:int,ids,dest:Path)->dict:
    """stage_members from the inputs' pinned pack of (sector, L) with the inventory's rows."""
    return stage_members(I.pack(sector,L),{r['id']:r for r in inventory[sector][str(L)]},L,ids,dest)

def native_cmd(exe,graphs,gamma,net,tasks,out,seed,layout,rate,threads,sum_mode='compensated',mp_check:str|None='on')->list[str]:
    """The worker's command line (src/c8d3_integrate.cpp): graphs_root gamma net tasks output seed layout rate threads
    sum_mode grid_or_dash [--mp-check on|off|stride16]. mp_check defaults to 'on', the mode of the sweep, the smoke, the
    pilot and the first cost model (C.4); None leaves the option out (the worker's own default, off)."""
    if mp_check is not None and mp_check not in MP_CHECK_MODES:raise BenchError(64,f'--mp-check {mp_check!r}: one of {", ".join(MP_CHECK_MODES)}')
    return [str(x)for x in (exe,graphs,gamma,net,tasks,out,seed,layout,rate,threads,sum_mode,'-')]+(['--mp-check',mp_check]if mp_check else[])

def omp_env(threads:int,base=None,wait_policy:str|None=None)->dict:
    """The worker environment of production lanes (sweep.py, run_array.sh): close binding on cores, fixed team size."""
    e={**(os.environ if base is None else base),'OMP_NUM_THREADS':str(threads),'OMP_PROC_BIND':'close','OMP_PLACES':'cores','OMP_DYNAMIC':'FALSE','OPENBLAS_NUM_THREADS':'1'}
    if wait_policy:e['OMP_WAIT_POLICY']=wait_policy
    return e

def pinner(cpus,pin:bool=True):
    """preexec_fn that pins the child (and so its threads and children) to cpus; None when pinning is off."""
    if not pin:return None
    cs=sorted(cpus)
    def pre():os.sched_setaffinity(0,cs)
    return pre

def rows_digest(rows:list,part:str='')->list[tuple]:
    """(part, uid, sha256 of the row's scientific fields) per native row: equal digests mean identical results."""
    return [(part,r['uid'],hashlib.sha256(canon([r.get(k)for k in SCIENTIFIC]).encode()).hexdigest())for r in rows]

def combined_digest(items)->str:
    return hashlib.sha256(''.join(f'{p}|{u}|{h}\n'for p,u,h in sorted(items)).encode()).hexdigest()

def native_summary(n:dict,threads:int)->dict:
    """Totals of one native JSON: points, promotions, task seconds, load/integration seconds, OpenMP efficiency, RSS."""
    rows=n['rows'];pts=sum(r['end']-r['begin']for r in rows);ts=math.fsum(float(r['seconds'])for r in rows)
    integ=float(n['integration_seconds'])
    return {'tasks':len(rows),'points':pts,'quad':sum(r['quad']for r in rows),'mp':sum(r['mp']for r in rows),
            'quad_fraction':sum(r['quad']for r in rows)/pts if pts else None,'mp_fraction':sum(r['mp']for r in rows)/pts if pts else None,
            'task_seconds':ts,'load_seconds':float(n['load_seconds']),'integration_seconds':integ,'threads':threads,
            'openmp_efficiency':ts/(threads*integ)if integ>0 else None,'max_rss_kb':n.get('max_rss_kb'),'graphs_loaded':n.get('graphs_loaded'),
            'nondirect':sum(r.get('nondirect',0)for r in rows),'nonmoderate':sum(r.get('nonmoderate',0)for r in rows),
            'mp_checked':sum(r.get('mp_checked',0)for r in rows),'mp_alarm':sum(r.get('mp_alarm',0)for r in rows),
            'microseconds_per_point_thread':1e6*ts/pts if pts else None}

# ---------------------------------------------------------------- CPU topology and lane shapes
def host_cores()->list[tuple[int,int,int]]:
    """(socket, NUMA node, cpu) for one logical CPU per physical core of this process's affinity set (sysfs; Linux)."""
    import lanes
    if not hasattr(os,'sched_getaffinity'):raise BenchError(69,'no sched_getaffinity on this platform (Linux only); use --fake-topology SxNxC --no-pin for a dry run')
    cpus=sorted(os.sched_getaffinity(0));nodes=lanes.numa_nodes();where={c:n for n,cl in nodes.items()for c in cl}
    return [(sock,where.get(cpu,-1),cpu)for (sock,_core),cpu in lanes.physical(cpus)]

def fake_cores(spec:str)->list[tuple[int,int,int]]:
    """'SxNxC': S sockets of N NUMA nodes of C cores each, CPUs numbered socket-major (dry runs and tests)."""
    m=re.fullmatch(r'(\d+)x(\d+)x(\d+)',spec or '')
    if not m or min(map(int,m.groups()))<1:raise BenchError(64,f'--fake-topology {spec!r}: expected SxNxC, e.g. 2x4x16')
    S,N,C=map(int,m.groups());out=[];cpu=0
    for s in range(S):
        for k in range(N):
            for _ in range(C):out.append((s,s*N+k,cpu));cpu+=1
    return out

def parse_shapes(text:str)->list[tuple[int,int]]:
    """'1x128,2x64,...' -> [(1, 128), (2, 64), ...]; refuses malformed, zero and repeated shapes."""
    out=[]
    for part in (text or '').split(','):
        m=re.fullmatch(r'\s*(\d+)x(\d+)\s*',part)
        if not m or int(m[1])<1 or int(m[2])<1:raise BenchError(64,f'lane shape {part.strip()!r}: expected NxT with N, T >= 1 (e.g. 8x16)')
        if (int(m[1]),int(m[2]))in out:raise BenchError(64,f'lane shape {part.strip()} is listed twice')
        out.append((int(m[1]),int(m[2])))
    return out

def partition(cores,n:int,t:int)->list[list[int]]:
    """n disjoint NUMA-aligned sets of t physical cores. A lane of t <= c cores (c = cores of a NUMA node) is a slice of
    one node (c divisible by t); a lane within a socket is a run of whole consecutive nodes of that socket (t a multiple
    of c dividing the socket); a wider lane is a run of whole sockets. Raises BenchError(64) when the shape does not fit."""
    if n<1 or t<1:raise BenchError(64,f'shape {n}x{t}: N and T must be >= 1')
    if any(node<0 for _,node,_ in cores):raise BenchError(64,'no NUMA node information for these CPUs (/sys/devices/system/node): lanes cannot be NUMA-aligned')
    bynode,sock_of={},{}
    for s,node,cpu in cores:
        bynode.setdefault(node,[]).append(cpu)
        if sock_of.setdefault(node,s)!=s:raise BenchError(64,f'NUMA node {node} spans sockets')
    nodes=sorted(bynode,key=lambda k:(sock_of[k],k));sizes=sorted({len(bynode[k])for k in nodes})
    if len(sizes)!=1:raise BenchError(64,f'NUMA nodes of unequal size in this allocation ({sizes} cores): lane shapes need equal nodes')
    c=sizes[0];per_sock={}
    for k in nodes:per_sock.setdefault(sock_of[k],[]).append(k)
    ks=sorted({len(v)for v in per_sock.values()})
    if len(ks)!=1:raise BenchError(64,f'sockets with unequal numbers of NUMA nodes ({ks}) in this allocation')
    k=ks[0];socks=sorted(per_sock);total=len(cores)
    if n*t>total:raise BenchError(64,f'shape {n}x{t} needs {n*t} cores; the allocation has {total} physical cores')
    if t<=c:
        if c%t:raise BenchError(64,f'shape {n}x{t}: {t} does not divide the {c} cores of a NUMA node')
        units=[sorted(bynode[nd])[i*t:(i+1)*t]for nd in nodes for i in range(c//t)]
    elif t<=c*k:
        if t%c or (c*k)%t:raise BenchError(64,f'shape {n}x{t}: a lane of {t} cores must be whole NUMA nodes ({c} cores each) that divide a socket ({c*k} cores)')
        g=t//c;units=[sorted(cpu for nd in per_sock[s][i*g:(i+1)*g]for cpu in bynode[nd])for s in socks for i in range(k//g)]
    else:
        if t%(c*k):raise BenchError(64,f'shape {n}x{t}: a lane wider than a socket must be whole sockets ({c*k} cores each)')
        g=t//(c*k)
        if len(socks)%g:raise BenchError(64,f'shape {n}x{t}: {len(socks)} sockets do not split into lanes of {g} sockets')
        units=[sorted(cpu for s in socks[i*g:(i+1)*g]for nd in per_sock[s]for cpu in bynode[nd])for i in range(len(socks)//g)]
    if n>len(units):raise BenchError(64,f'shape {n}x{t}: only {len(units)} NUMA-aligned sets of {t} cores fit this allocation')
    return units[:n]

def nodes_of(cores,cpus)->list[int]:
    where={cpu:node for _,node,cpu in cores};return sorted({where[c]for c in cpus})

def block_tasks(t:int,spec:str='auto')->int|None:
    """Tasks per native block: 'auto' = production's default checkpoint_tasks max(16 x T, 256); an integer; or 'all'
    (None: one native process per lane and part)."""
    if spec=='auto':return max(16*t,256)
    if spec=='all':return None
    if not str(spec).isdigit()or int(spec)<1:raise BenchError(64,f'--block-tasks {spec!r}: auto, all or a positive integer')
    return int(spec)

def lpt_shares(items,n:int)->list[list]:
    """Deterministic LPT: items (cost, key, payload) by cost descending then key, each to the least-loaded share
    (lowest index on ties)."""
    shares=[[]for _ in range(n)];heap=[(0.0,i)for i in range(n)]
    for it in sorted(items,key=lambda x:(-x[0],x[1])):
        load_,i=heapq.heappop(heap);shares[i].append(it);heapq.heappush(heap,(load_+it[0],i))
    return shares

def lane_blocks(share,T:int|None,parts,S:float|None=None,w:int|None=None)->list[tuple[str,list]]:
    """A lane's native blocks: per part (in the given order) its items by cost descending then key (production's block
    order 'pos'), cut into blocks of T items (T None: one block per part). With S (seconds) and w (the lane width) the
    blocks are production's (D.6, production.cut_blocks): at most T items and at most S seconds of predicted work at
    width w, W(B) = sum of the items' costs / w, with production's last-two rebalance."""
    out=[]
    for part in parts:
        rows=sorted((it for it in share if it[1][0]==part),key=lambda x:(-x[0],x[1]))
        if not rows:continue
        if S is not None:
            import production as prod
            bounds=prod.cut_blocks([it[0]for it in rows],T or len(rows),float(S),int(w or 1))['bounds']
            out+=[(part,rows[bounds[k]:bounds[k+1]])for k in range(len(bounds)-1)]
            continue
        step=T or max(1,len(rows))
        for i in range(0,len(rows),step):out.append((part,rows[i:i+step]))
    return out

# ---------------------------------------------------------------- identity
def run_text(cmd,timeout=60)->str|None:
    """stdout of a probe command, or None when it is missing or fails."""
    if shutil.which(cmd[0])is None:return None
    try:
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        return cp.stdout if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError):return None

def read_text(path)->str|None:
    try:return Path(path).read_text().strip()
    except OSError:return None

def exe_identity(path:Path)->dict:
    path=Path(path)
    if not path.is_file():return {'path':str(path),'present':False}
    rec={'path':str(path),'present':True,'sha256':digest(path),'bytes':path.stat().st_size}
    try:
        cp=subprocess.run([str(path),'--describe'],capture_output=True,text=True,timeout=120)
        rec['describe']=json.loads(cp.stdout)if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError,ValueError):rec['describe']=None
    br=path.with_name(path.name+'.buildinfo.json');rec['build_record']=load(br)if br.is_file()else None
    bt=path.with_name(path.name+'.build.txt');rec['build_text']=bt.read_text()if bt.is_file()else None
    return rec

def package_commit()->str:
    if (ROOT/'.git').exists()and shutil.which('git'):
        cp=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],capture_output=True,text=True)
        if cp.returncode==0:
            dirty=subprocess.run(['git','-C',str(ROOT),'status','--porcelain','tools','src','tests','benchmarks/fixtures8','benchmarks/probes','Makefile'],capture_output=True,text=True).stdout.strip()
            return cp.stdout.strip()+(' (uncommitted changes)'if dirty else'')
    return f'export {ROOT.name}'

def identity(executables:dict|None=None,perf:str='perf')->dict:
    """Host, build and executable identity carried by every profiling record."""
    return {'utc':utc(),'host':socket.gethostname(),'cpu_model':cpu_model_noprobe(),'kernel':platform.release(),'platform':platform.platform(),
            'python':sys.version.split()[0],'package':str(ROOT),'package_commit':package_commit(),'cpu_count':os.cpu_count(),
            'affinity':sorted(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else None,
            'slurm':{k:os.environ.get(k)for k in ('SLURM_JOB_ID','SLURM_JOB_NAME','SLURM_JOB_NODELIST','SLURM_JOB_PARTITION','SLURM_CPUS_ON_NODE','SLURM_RESTART_COUNT','SLURM_MEM_PER_NODE')},
            'omp_env':{k:v for k,v in sorted(os.environ.items())if k.startswith(('OMP_','GOMP_'))},
            'lscpu':run_text(['lscpu']),'numactl_hardware':run_text(['numactl','--hardware']),'perf_version':run_text([perf,'--version']),
            'perf_event_paranoid':read_text('/proc/sys/kernel/perf_event_paranoid'),'kptr_restrict':read_text('/proc/sys/kernel/kptr_restrict'),
            'executables':{k:exe_identity(Path(v))for k,v in (executables or{}).items()}}

# ---------------------------------------------------------------- perf report
_PCT=re.compile(r'^\s*(\d+(?:\.\d+)?)%\s+(.*)$')
# Some perf builds (RHEL 8's perf 4.18 on Expanse) append "IPC [IPC Coverage]" columns to symbol sorts; without branch
# (LBR) data each row then ends in "-      -" (with it: "1.23  [ 45.6%]"). Stripped before the symbol is read.
_IPC_TAIL=re.compile(r'\s+(?:-|\d+(?:\.\d+)?)\s+(?:-|\[\s*\d+(?:\.\d+)?%\s*\])\s*$')
def parse_perf_report(text:str)->dict:
    """perf report --stdio [-n] [--no-children] --sort {symbol | dso | dso,symbol}: the header (samples, event, lost,
    event count) and one row per entry: overhead (percent), samples (with -n), dso, level ('.' user, 'k' kernel) and
    symbol. Trailing IPC / IPC-coverage columns (when the header names them) are dropped. Call-graph lines under an
    entry are ignored."""
    head={};rows=[];has_samples=has_dso=has_symbol=has_ipc=False
    for line in text.splitlines():
        if line.startswith('#'):
            s=line[1:].strip()
            m=re.match(r"Samples:\s+(\S+)\s+of event '([^']+)'",s)
            if m:head['samples_text'],head['event']=m[1],m[2]
            m=re.match(r'Total Lost Samples:\s+(\d+)',s)
            if m:head['lost']=int(m[1])
            m=re.match(r'Event count \(approx\.\):\s+(\d+)',s)
            if m:head['event_count']=int(m[1])
            if s.startswith('Overhead'):has_samples='Samples'in s;has_dso='Shared Object'in s;has_symbol='Symbol'in s;has_ipc=bool(re.search(r'\bIPC\b',s))
            continue
        m=_PCT.match(line)
        if not m:continue
        rest=m[2].strip()
        if has_ipc:rest=_IPC_TAIL.sub('',rest)
        row={'overhead':float(m[1]),'samples':None,'dso':None,'level':None,'symbol':None}
        if has_samples:
            tok,_,rest=rest.partition(' ')
            if not tok.isdigit():continue
            row['samples']=int(tok);rest=rest.strip()
        if has_dso:
            if has_symbol:tok,_,rest=rest.partition(' ');row['dso']=tok;rest=rest.strip()
            else:row['dso']=rest;rest=''
        if has_symbol:
            m2=re.match(r'^\[(.)\]\s+(.*)$',rest)
            if m2:row['level'],row['symbol']=m2[1],m2[2].strip()
            else:row['symbol']=rest
        rows.append(row)
    return {'header':head,'rows':rows}

GMPF=re.compile(r'^__gmpf_');GMPN=re.compile(r'^__gmpn_|^mpn_');GMP_OTHER=re.compile(r'^__gmp[zq]?_')
QUAD_ARITH=('__addtf3','__subtf3','__multf3','__divtf3')
QUAD_OTHER=re.compile(r'^__(?:eq|ne|lt|le|gt|ge|unord|cmp)tf2$|^__(?:extend|trunc)\w*tf\w*2$|^__(?:float|fix)\w*tf\w*$|^__\w*tf\d$|^__sfp_handle_exceptions$')
FENV=re.compile(r'^(?:__)?fe(?:setenv|getenv|holdexcept|updateenv|setround|getround|clearexcept|raiseexcept|testexcept|setexceptflag|getexceptflag)$')
_SYMVER=re.compile(r'@.*$')
def base_symbol(s:str)->str:
    """A symbol as the classification sees it: without its version or PLT suffix (__lttf2@@GCC_4.3.0 -> __lttf2,
    cfree@GLIBC_2.2.5 -> cfree, __addtf3@plt -> __addtf3) and without glibc's internal __GI_ alias prefix
    (__GI_____strtold_l_internal -> ____strtold_l_internal)."""
    b=_SYMVER.sub('',s)
    return b[5:]if b.startswith('__GI_')else b
MALLOC=re.compile(r'^(?:_int_|__libc_)?(?:malloc|free|realloc|calloc|memalign)$|^cfree$|^malloc_consolidate$|^sysmalloc$|^unlink_chunk|^tcache_|^operator (?:new|delete)')
EXPL=re.compile(r'^(?:__)?(?:ieee754_)?expl(?:_finite)?$|^__expl_finite$|^__exp1l$|^__kernel_expl')
LOGL=re.compile(r'^(?:__)?(?:ieee754_)?logl(?:_finite)?$|^__logl_finite$')
EXPQ=re.compile(r'^(?:__)?expq$|^__quadmath_kernel_expq|^__expq')
SQRTQ=re.compile(r'^(?:__)?sqrtq$')
SQRTL=re.compile(r'^(?:__)?(?:ieee754_)?sqrtl(?:_finite)?$|^__sqrtl_finite$')
MPCONV=re.compile(r'^__gmpf_get_str$|^__gmpn_get_str$|^mpn_(?:bc|dc)_get_str|^__gmpn_(?:bc|dc)_get_str|^(?:____)?strtold(?:_l)?(?:_internal)?$|^__strtold_internal$|^____strtold_l_internal$|^str_to_mpn|^round_and_return|^__mpn_')
MPCONV_LIKELY=re.compile(r'^__gmpn_(?:pre)?(?:inv_)?divrem_1$|^__gmpn_preinv_divrem_1$')
CALC_REF_LD=re.compile(r'calculate_reference<long double>')
GOMP=re.compile(r'^gomp_|^GOMP_|^omp_')
NAMED=('__addtf3','__subtf3','__multf3','__divtf3','expq','sqrtq','expl','logl','sqrtl','__gmpf_get_str','__gmpn_get_str','strtold','____strtold_l_internal',
       'malloc','free','_int_malloc','_int_free','__gmpf_add','__gmpf_sub','__gmpf_mul','__gmpf_div','__gmpf_sqrt','__gmpf_set','__gmpf_init2','__gmpf_clear',
       '__gmpn_mul_basecase','__gmpn_sqr_basecase','__gmpn_add_n','__gmpn_sub_n','__gmpn_copyi','__gmpn_divrem','__gmpn_tdiv_qr','__gmpn_sqrtrem')

def symbol_table(rows:list)->list[dict]:
    """Rows of a dso,symbol (or symbol) report aggregated by symbol, overhead descending."""
    agg={}
    for r in rows:
        if r['symbol']is None:continue
        a=agg.setdefault(r['symbol'],{'symbol':r['symbol'],'overhead':0.,'samples':0 if r['samples']is not None else None,'dsos':set(),'level':r['level']})
        a['overhead']+=r['overhead']
        if a['samples']is not None and r['samples']is not None:a['samples']+=r['samples']
        if r['dso']:a['dsos'].add(r['dso'])
    out=[{**a,'dsos':sorted(a['dsos'])}for a in agg.values()]
    return sorted(out,key=lambda a:(-a['overhead'],a['symbol']))

def perf_shares(rows:list,worker:str|None=None)->dict:
    """Shares (percent of all samples) the plan names, from a symbol or dso,symbol report: each binary128 operation and
    their sum, the rest of libgcc's binary128 support, expq, sqrtq, expl, logl, sqrtl, __gmpf_*, __gmpn_*, other GMP, malloc/free,
    MP -> long double conversion (lower bound: get_str and strtold families; 'likely' adds GMP's divrem_1 helpers that
    get_str uses), calculate_reference<long double>, libgomp (barrier and spin), the fenv calls (fesetenv,
    feholdexcept, ...), kernel, and the worker's own code (worker = its DSO basename) not otherwise named. Symbols are
    classified by base_symbol (versions, @plt and __GI_ removed), so a PLT stub counts with its target (__addtf3@plt
    with __addtf3); 'plt_stubs' gives the stubs' total, and 'binary128_ops_by_dso' splits each binary128 operation by
    the DSO it ran in (libgcc_s, libquadmath's own copies used by its functions, the worker's PLT stubs)."""
    syms=symbol_table(rows);cat={k:0. for k in ('binary128_arith','binary128_other','expq','sqrtq','expl','logl','sqrtl','gmpf','gmpn','gmp_other','malloc_free',
        'mp_to_ld_lower','mp_to_ld_likely','calculate_reference_ld','libgomp','fenv','kernel','worker_other','unknown','other')}
    named={k:0. for k in NAMED};per_op={k:0. for k in QUAD_ARITH};plt=0.
    for a in syms:
        s,o=a['symbol'],a['overhead'];dsos=a['dsos'];b=base_symbol(s)
        if b in named:named[b]+=o
        if s.endswith('@plt'):plt+=o
        if a['level']=='k':cat['kernel']+=o;continue
        if b in QUAD_ARITH:per_op[b]+=o;cat['binary128_arith']+=o
        elif QUAD_OTHER.match(b):cat['binary128_other']+=o
        elif EXPQ.match(b):cat['expq']+=o
        elif SQRTQ.match(b):cat['sqrtq']+=o
        elif EXPL.match(b):cat['expl']+=o
        elif SQRTL.match(b):cat['sqrtl']+=o
        elif LOGL.match(b):cat['logl']+=o
        elif MPCONV.match(b):cat['mp_to_ld_lower']+=o
        elif GMPF.match(b):cat['gmpf']+=o
        elif GMPN.match(b):cat['gmpn']+=o
        elif GMP_OTHER.match(b):cat['gmp_other']+=o
        elif MALLOC.match(b):cat['malloc_free']+=o
        elif CALC_REF_LD.search(b):cat['calculate_reference_ld']+=o
        elif GOMP.match(b)or any('libgomp'in d for d in dsos):cat['libgomp']+=o
        elif FENV.match(b):cat['fenv']+=o
        elif worker and worker in dsos:cat['worker_other']+=o
        elif b.startswith('0x')or b=='[unknown]':cat['unknown']+=o
        else:cat['other']+=o
        if MPCONV_LIKELY.match(b):cat['mp_to_ld_likely']+=o
    cat['mp_to_ld_likely']+=cat['mp_to_ld_lower']
    cat['gmp_total']=cat['gmpf']+cat['gmpn']+cat['gmp_other']+cat['mp_to_ld_lower']
    by_dso={}
    for r in rows:
        if r['symbol']is None or r['level']=='k'or base_symbol(r['symbol'])not in QUAD_ARITH:continue
        d=by_dso.setdefault(r['dso']or'?',{});k=base_symbol(r['symbol']);d[k]=d.get(k,0.)+r['overhead']
    return {'categories':{k:round(v,4)for k,v in cat.items()},'binary128_ops':{k:round(v,4)for k,v in per_op.items()},'named':{k:round(v,4)for k,v in named.items()},
            'plt_stubs':round(plt,4),'binary128_ops_by_dso':{d:{k:round(v,4)for k,v in sorted(x.items())}for d,x in sorted(by_dso.items())},
            'total_listed':round(sum(a['overhead']for a in syms),4)}

def dso_table(rows:list)->list[dict]:
    agg={}
    for r in rows:
        d=r['dso']or'?';a=agg.setdefault(d,{'dso':d,'overhead':0.,'samples':0})
        a['overhead']+=r['overhead'];a['samples']+=r['samples']or 0
    return sorted(agg.values(),key=lambda a:(-a['overhead'],a['dso']))

def parse_perf_record_stderr(text:str)->dict:
    """perf record's summary: MB written, samples, lost chunks/samples ('Processed N events and lost M chunks')."""
    out={'mb':None,'samples':None,'lost_chunks':0,'lost_samples':0,'warnings':[]}
    m=re.search(r'Captured and wrote ([\d.]+) MB .*?\((\d+) samples\)',text)
    if m:out['mb'],out['samples']=float(m[1]),int(m[2])
    for m in re.finditer(r'lost (\d+) chunks',text):out['lost_chunks']+=int(m[1])
    for m in re.finditer(r'Lost (\d+) samples',text,re.I):out['lost_samples']+=int(m[1])
    out['warnings']=[l.strip()for l in text.splitlines()if 'WARNING'in l or 'Check IO/CPU overload'in l][:10]
    return out

# ---------------------------------------------------------------- perf stat
def parse_perf_stat_csv(text:str)->dict:
    """perf stat -x, output: per event value (None when <not counted>/<not supported>), unit, running percentage
    (multiplexing below 100), status; derived IPC = instructions / cycles when both were counted."""
    ev={}
    for line in text.splitlines():
        if not line.strip()or line.startswith('#'):continue
        f=line.split(',')
        if len(f)<3:continue
        raw=f[0].strip();name=f[2].strip()
        if not name:continue
        val=None;status='counted'
        if raw.startswith('<'):status=raw.strip('<>')
        else:
            try:val=float(raw)
            except ValueError:status='unparsed'
        pct=None
        if len(f)>4 and f[4].strip():
            try:pct=float(f[4])
            except ValueError:pct=None
        ev[name]={'value':val,'unit':f[1].strip()or None,'running_percent':pct,'status':status}
    def get(base):
        for k,v in ev.items():
            if k.split(':')[0]==base and v['value']is not None:return v['value']
        return None
    cyc,ins=get('cycles'),get('instructions')
    br,bm=get('branches'),get('branch-misses');l1,l1m=get('L1-dcache-loads'),get('L1-dcache-load-misses')
    der={'ipc':ins/cyc if cyc and ins is not None else None,'branch_miss_rate':bm/br if br and bm is not None else None,
         'l1d_miss_rate':l1m/l1 if l1 and l1m is not None else None}
    fe,be=get('stalled-cycles-frontend'),get('stalled-cycles-backend')
    if cyc:der['frontend_stall_fraction']=fe/cyc if fe is not None else None;der['backend_stall_fraction']=be/cyc if be is not None else None
    return {'events':ev,'derived':der,'multiplexed':any(v['running_percent']is not None and v['running_percent']<99.99 for v in ev.values())}

# ---------------------------------------------------------------- perf annotate, addr2line, ltrace
def parse_annotate(text:str)->list[dict]:
    """perf annotate --stdio: per annotated function the DSO, event, sample count, symbol (the objdump label) and the
    per-instruction local percentages {address: percent}."""
    out=[];cur=None
    for line in text.splitlines():
        m=re.search(r'(?:Source code & )?Disassembly of (\S+) for (\S+) \((\d+) samples',line)
        if m:cur={'dso':m[1],'event':m[2],'samples':int(m[3]),'symbol':None,'instructions':{}};out.append(cur);continue
        if cur is None:continue
        m=re.match(r'^\s*[:│]?\s*([0-9a-f]+)\s+<(.+)>:\s*$',line)
        if m and cur['symbol']is None:cur['symbol']=m[2];continue
        m=re.match(r'^\s*(\d+(?:\.\d+)?)\s*[:│]\s+([0-9a-f]+):',line)
        if m:
            p=float(m[1])
            if p>0:a=int(m[2],16);cur['instructions'][a]=cur['instructions'].get(a,0.)+p
    return out

def parse_addr2line(text:str)->dict[int,list[tuple]]:
    """addr2line -a -i -f -C output: {address: [(function, file, line), ...]} innermost frame first."""
    out={};cur=None;pend=None
    for line in text.splitlines():
        s=line.strip()
        if re.fullmatch(r'0x[0-9a-fA-F]+',s):cur=int(s,16);out[cur]=[];pend=None;continue
        if cur is None:continue
        if pend is None:pend=s;continue
        m=re.match(r'^(.*):(\d+|\?)(?: \(discriminator \d+\))?$',s)
        f,ln=(m[1],int(m[2])if m[2].isdigit()else None)if m else (s,None)
        out[cur].append((pend,f,ln));pend=None
    return out

def parse_ltrace_c(text:str)->dict:
    """ltrace -c table: per function % time, seconds, usecs/call, calls; plus the total row."""
    rows=[];total=None
    for line in text.splitlines():
        m=re.match(r'^\s*([\d.]+)\s+([\d.]+)\s+(\d+)?\s+(\d+)\s+(\S+)\s*$',line)
        if not m:continue
        r={'percent':float(m[1]),'seconds':float(m[2]),'usecs_per_call':int(m[3])if m[3]else None,'calls':int(m[4]),'function':m[5]}
        if r['function']=='total':total=r
        else:rows.append(r)
    return {'rows':rows,'total':total}

# ---------------------------------------------------------------- NUMA placement
def parse_numa_maps(text:str)->dict[int,int]:
    """kB of resident pages per NUMA node in /proc/<pid>/numa_maps (N<node>=<pages> x kernelpagesize_kB)."""
    out={}
    for line in text.splitlines():
        ps=4;m=re.search(r'kernelpagesize_kB=(\d+)',line)
        if m:ps=int(m[1])
        for n,p in re.findall(r'\bN(\d+)=(\d+)',line):out[int(n)]=out.get(int(n),0)+int(p)*ps
    return out

def numa_maps_of(pid:int)->dict[int,int]|None:
    try:return parse_numa_maps(Path(f'/proc/{pid}/numa_maps').read_text())
    except OSError:return None

def node_numastat(sysroot:str|None=None)->dict:
    """The per-node counters of /sys/devices/system/node/node*/numastat (numa_hit, numa_miss, local_node, other_node...)."""
    d=Path(sysroot or os.environ.get('C8_SYSFS','/sys'))/'devices/system/node';out={}
    for p in sorted(d.glob('node[0-9]*'))if d.is_dir()else[]:
        try:out[int(p.name[4:])]={k:int(v)for k,v in (ln.split()for ln in (p/'numastat').read_text().splitlines()if ln.strip())}
        except (OSError,ValueError):continue
    return out

def numastat_delta(before:dict,after:dict)->dict:
    return {n:{k:after[n][k]-before.get(n,{}).get(k,0)for k in after[n]}for n in sorted(after)}

# ---------------------------------------------------------------- ratio histograms (P3)
RATIO_ZERO=-402   # bin of "zero_or_below" (ratio 0 or below 1e-401), below every numbered bin (-1..-401; src/diagnostics.hpp)
CDF_EXPONENTS={'ld_fail':tuple(range(9,41)),'quad':tuple(range(9,41)),'mp':(23,30,40,50,60,63,70,77,80,100,120,150,200,250,300,330,350,400)}

def hist_counts(h:dict)->dict[int,int]:
    """Native histogram {'-k': n, 'zero_or_below': n} -> {floor(log10 ratio): n}; key -1 holds [0.1, 1) and every ratio
    >= 1 (src/diagnostics.hpp: bin b holds [10^-(b+1), 10^-b), key -(b+1))."""
    out={}
    for k,v in h.items():
        b=RATIO_ZERO if k=='zero_or_below'else int(k);out[b]=out.get(b,0)+int(v)
    return dict(sorted(out.items()))

def below(counts:dict,k:int)->int:
    """Number of ratios r < 10^-k: floor(log10 r) <= -k-1 (and every zero_or_below)."""
    return sum(n for b,n in counts.items()if b<=-k-1)

def ratio_summary(native:dict)->dict:
    """P3 summary of one ratiohist run: the three histograms, consistency with the row counters (every promoted point
    is counted once in ld_fail and once in quad; every MP point once in mp; the MP count equals the quad ratios below
    1e-23), and the fractions below 10^-k at the listed exponents."""
    rh=native['ratio_histogram'];rows=native['rows'];pts=sum(r['end']-r['begin']for r in rows)
    q=sum(r['quad']for r in rows);mp=sum(r['mp']for r in rows);out={'points':pts,'quad':q,'mp':mp,'histograms':{},'cdf':{},'checks':{}}
    for name in ('ld_fail','quad','mp'):
        c=hist_counts(rh.get(name,{}));tot=sum(c.values())
        out['histograms'][name]={str(k):v for k,v in c.items()}
        out['cdf'][name]={f'1e-{k}':(below(c,k)/tot if tot else None)for k in CDF_EXPONENTS[name]}
        out['checks'][f'{name}_total']=tot
    out['checks']['ld_fail_equals_quad_calls']=out['checks']['ld_fail_total']==q
    out['checks']['quad_equals_quad_calls']=out['checks']['quad_total']==q
    out['checks']['mp_equals_mp_calls']=out['checks']['mp_total']==mp
    out['checks']['quad_below_1e-23_equals_mp_calls']=below(hist_counts(rh.get('quad',{})),23)==mp
    out['checks']['ld_fail_all_below_1e-9']=below(hist_counts(rh.get('ld_fail',{})),9)==out['checks']['ld_fail_total']
    out['ok']=all(v for k,v in out['checks'].items()if isinstance(v,bool))
    qc=hist_counts(rh.get('quad',{}));acc={b:n for b,n in qc.items()if b>=-23}
    out['quad_accepted_margin_digits']={str(b+23):n for b,n in sorted(acc.items())}  # floor(log10 r) + 23 for accepted binary128 points (22 includes r >= 0.1)
    return out
