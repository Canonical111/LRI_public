#!/usr/bin/env python3
"""Plan, run, check, recover and merge complete C8(2) campaigns (both forest sectors).

Scientific point identities (campaign, sector, loop, replicate, graph, point) do not depend on scheduler, shard,
chunk, checkpoint or thread IDs. SQLite task tables and sorted deterministic Decimal merges are disk backed. The
native worker runs only from a verified job-private copy of the planned executable and inputs.
"""
from __future__ import annotations
import argparse,decimal,hashlib,heapq,itertools,json,math,os,re,shlex,shutil,signal,sqlite3,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from common import ROOT,canon,checked,digest,dump,fingerprint,fingerprint_key,load,object_hash,pow2,publish,read_verified,umask_mode
from prepare_inputs import prepare,verify as verify_inputs
from task_schedule import assign_graph_bundles,freeze_blocks,task_blocks,rows_for,block_count as blocks_of
D=decimal.Decimal
SCHEMA='c8-d2-production-2';GROUP_SCHEMA='c8-d2-group-2';V1_SCHEMA='c8-d2-production-1';MERGED_SCHEMA='c8-d2-merged-1'
TOOLS=('production.py','assemble.py','common.py','prepare_inputs.py','task_schedule.py','stage_runtime.py','slurm_submit.py')
SMALL_INPUTS=('gamma_d2_8.txt','two_loop.json','inventory.json')
MAX_ARRAY=1000      # common Slurm MaxArraySize (array indices 0..999)
ASSUMED_EFFICIENCY=0.80  # planning only: busy fraction of the allocated cores (A-M4 target), used for wall-time estimates
V1_MESSAGE='{d} uses an incompatible prior campaign schema; create a new C8 campaign.'
# Base seeds of the 2026 campaigns made with the delivered additive seed arithmetic (refused under --seed-scheme legacy).
USED_2026={8885400701634497064:'symmetry production run1-20260930-m4096',326694507229394458:'Expanse plan run1-20260930-m4096 (abandoned)',
           2765894070584243940:'Expanse pilot (job 54545302)'}
# Net-matrix seeds of the archived free-sector nets: reference/LRI_C7_d2_progress/code/prepare.py, make_net(..., seed+L*7893).
ARCHIVED_NET_BASES={12983:'archived pilot nets',837425:'archived campaign-a nets',915437:'archived campaign-b nets'}

def dbopen(path:Path,readonly=False):
    # Read-only opens use a percent-encoded file: URI, so '#', '?', '%' or spaces in a campaign path are not URI syntax.
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro'if readonly else str(path),uri=readonly)
    c.execute('PRAGMA cache_size=-8192');c.execute('PRAGMA temp_store=FILE');return c

# ---------------------------------------------------------------- Sobol nets (A-L5)
def reachable_columns(max_count:int)->int:
    """Direction columns a stratum of max_count points can reach: points 0..n-1 use columns 0..ceil(log2 n)-1."""
    return 0 if max_count<=1 else (max_count-1).bit_length()

def gray_state(sv,shift,n:int):
    """State of point n as the native Net computes it: shift XOR the direction columns of the set bits of n ^ (n >> 1)."""
    st=np.asarray(shift,dtype=np.uint64).copy();g=n^(n>>1)
    while g:
        j=(g&-g).bit_length()-1;st^=np.asarray(sv,dtype=np.uint64)[:,j];g&=g-1
    return st

def gray_states(sv,shift,k:int):
    """States of points 0..2^k-1 (shape (2^k, dim)), equal to gray_state for every n. The reflected Gray code gives
    gray(n) = gray(2^(j+1)-1-n) | 2^j for 2^j <= n < 2^(j+1), so each half is the mirrored lower half XOR column j."""
    sv=np.asarray(sv,dtype=np.uint64);st=np.empty((1<<k,sv.shape[0]),dtype=np.uint64);st[0]=np.asarray(shift,dtype=np.uint64)
    for j in range(k):
        h=1<<j;st[h:2*h]=st[h-1::-1]^sv[:,j][None,:]
    return st

def check_public(sv,shift,public,k:int,bits:int)->None:
    """(a) the public random_base2(k) points equal the exported states at the same indices (columns 0..k-1)."""
    if public.shape!=(1<<k,len(shift))or not np.array_equal(gray_states(sv,shift,k).astype(np.float64)/2**bits,public):
        raise RuntimeError(f'Sobol export failed the public-API comparison (columns 0..{k-1})')

def check_fresh(sv,shift,fresh_sv,fresh_shift,m:int)->None:
    """(b) an identically seeded fresh engine has the same direction integers (columns 0..m-1, all bits) and shift."""
    sv=np.asarray(sv,dtype=np.uint64);fresh_sv=np.asarray(fresh_sv,dtype=np.uint64)
    if sv.shape[0]!=fresh_sv.shape[0]or not np.array_equal(sv[:,:m],fresh_sv[:,:m])or not np.array_equal(np.asarray(shift,dtype=np.uint64),np.asarray(fresh_shift,dtype=np.uint64)):
        raise RuntimeError(f'Sobol export differs from a fresh identically seeded engine (columns 0..{m-1})')

def gf2_rank(vectors)->int:
    basis={}
    for v in vectors:
        v=int(v)
        while v:
            top=v.bit_length()-1
            if top not in basis:basis[top]=v;break
            v^=basis[top]
    return len(basis)

def check_structure(sv,m:int,bits:int)->None:
    """(c) SciPy-independent: in every dimension the direction integers of columns 0..m-1 are nonzero, below 2^bits and
    linearly independent over GF(2) (a Sobol generating matrix is nonsingular; linear scrambling preserves that)."""
    for d,row in enumerate(np.asarray(sv,dtype=np.uint64)):
        cols=[int(x)for x in row[:m]]
        if any(c==0 or c>=1<<bits for c in cols):raise RuntimeError(f'Sobol direction integer zero or out of range (dimension {d}, columns 0..{m-1})')
        if gf2_rank(cols)!=m:raise RuntimeError(f'Sobol direction columns 0..{m-1} of dimension {d} are linearly dependent over GF(2)')

def make_net(path:Path,B:int,dim:int,bits:int,seed:int,max_count:int|None=None):
    """Export B independently scrambled Sobol direction matrices and check every column a stratum of max_count points can
    reach (all of them when None) by (a) public-API points, (b) a fresh engine read back from the written file, (c) a
    GF(2) structure check. Work is O(2^min(m,16) + m^2) per replicate, never proportional to the sample index."""
    from scipy.stats import qmc
    import scipy
    m=bits if max_count is None else reachable_columns(max_count)
    if m>bits:raise ValueError('Sobol period exceeded')
    k=min(m,16);rng=np.random.default_rng(seed);seeds=[int(rng.integers(1,2**32-1))for _ in range(B)];shifts=[]
    with path.open('xb')as f:
        f.write(struct.pack('<III',B,dim,bits))
        for s in seeds:
            engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s);sv=engine._sv.copy();shift=engine._shift.copy()
            check_public(sv,shift,engine.random_base2(k),k,bits);shifts.append(shift)
            f.write(sv.astype('<u8').tobytes())
    raw=path.read_bytes()
    if struct.unpack('<III',raw[:12])!=(B,dim,bits)or len(raw)!=12+B*dim*bits*8:raise RuntimeError('Sobol export has the wrong size')
    for b,s in enumerate(seeds):
        exported=np.frombuffer(raw,dtype='<u8',count=dim*bits,offset=12+b*dim*bits*8).reshape(dim,bits)
        fresh=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s);check_fresh(exported,shifts[b],fresh._sv,fresh._shift,m);check_structure(exported,m,bits)
    return {'scipy':scipy.__version__,'seed':seed,'B':B,'dim':dim,'bits':bits,'sha256':digest(path),'columns_checked':m,
            'public_API_points_checked':(1<<k)*B,'checks':['public_api','fresh_engine','gf2_structure']}

# ---------------------------------------------------------------- seeds (D6)
def legacy_offset(campaign:str,sector:str)->int:return (0 if sector=='free'else 0x156ad267)+(0 if campaign=='a'else 0x614ef703)

def derive_seeds(seed:int,campaign:str,sector:str,L:int,scheme:str)->dict:
    """Native (digital-shift) and net seeds of one group. 'legacy' is the delivered additive arithmetic; 'hashed' (default)
    makes every group's seeds independent SHA-256 functions of (seed, campaign, sector, L, role)."""
    if campaign not in('a','b')or sector not in('free','power'):raise ValueError('unknown campaign or sector')
    if scheme=='legacy':
        off=legacy_offset(campaign,sector);return {'native':(seed+L*1279+off)%(2**64),'net':(seed+18743*L+off*13)%(2**63)}
    if scheme!='hashed':raise ValueError('unknown seed scheme '+str(scheme))
    h=lambda role:int.from_bytes(hashlib.sha256(f'c8-d2|{seed}|{campaign}|{sector}|L{L}|{role}'.encode()).digest()[:8],'little')%(2**63)
    return {'native':h('native'),'net':h('net')}

GROUPS=[(c,s,L)for c in('a','b')for s in('free','power')for L in range(3,9)]

def seed_registry()->dict:
    """Known used seeds: base seeds, native (digital-shift) seeds and net-matrix seeds of the archived records and plans
    (reference/LRI_C7_d2_progress, reference/power_mass) and of the 2026 campaigns (legacy arithmetic)."""
    bases,native,net={},{},{}
    for folder in ('reference/LRI_C7_d2_progress/records','reference/power_mass/records'):
        for f in sorted((ROOT/folder).rglob('*.json')):
            try:d=json.loads(f.read_text())
            except ValueError:continue
            if not isinstance(d,dict):continue
            src=str(f.relative_to(ROOT))
            if str(d.get('schema','')).startswith('c7-d2-native')and type(d.get('seed'))is int:bases[d['seed']]=native[d['seed']]=src
            s=(d.get('args')or{}).get('seed')if isinstance(d.get('args'),dict)else None
            if s is not None and str(s).isdigit():bases[int(s)]=native[int(s)]=src
    pm=ROOT/'reference/power_mass/verification/production_manifest.json'
    if pm.exists():
        for c in load(pm).get('campaigns',[]):
            bases[int(c['seed'])]=native[int(c['seed'])]=str(pm.relative_to(ROOT));bases[int(c['net_seed'])]=str(pm.relative_to(ROOT))
            for L in range(3,9):net[int(c['net_seed'])+7893*L]=str(pm.relative_to(ROOT))
    for b,src in ARCHIVED_NET_BASES.items():
        bases[b]=src
        for L in range(2,9):net[b+7893*L]=src
    for b,src in USED_2026.items():
        bases[b]=src
        for c,s,L in GROUPS:x=derive_seeds(b,c,s,L,'legacy');native[x['native']]=src;net[x['net']]=src
    return {'bases':bases,'native':native,'net':net}

def legacy_refusal(seed:int)->str|None:
    r=seed_registry()
    if seed in r['bases']:return f'seed {seed} is a known archived or used base seed ({r["bases"][seed]})'
    for c,s,L in GROUPS:
        x=derive_seeds(seed,c,s,L,'legacy')
        if x['native']in r['native']:return f'under the legacy arithmetic group {c}_{s}_L{L} would reuse the digital-shift seed of {r["native"][x["native"]]}'
        if x['net']in r['net']:return f'under the legacy arithmetic group {c}_{s}_L{L} would reuse the net seed of {r["net"][x["net"]]}'
    return None

# ---------------------------------------------------------------- planning
def exe_for(backend:str)->Path:return ROOT/'bin'/('c8d2_gmp'if backend=='gmp'else'c8d2_decimal')

def load_calibration()->dict:return {'backends':{},'scope':'No C8 timing calibration; pilot measurements required.'}

def calibration_row(cal:dict,backend:str,sector:str,L:int):
    row=(((cal.get('backends')or{}).get(backend)or{}).get(sector)or{}).get(str(L))
    return row if row and row.get('seconds_per_proxy_unit')else None

def hms(seconds:int)->str:
    d,s=divmod(int(seconds),86400);return (f'{d}-'if d else'')+time.strftime('%H:%M:%S',time.gmtime(s))

def stratum_counts(a,rows:list,sector:str,L:int,prim:dict|None)->dict:
    """Frozen per-graph counts. C8 defaults are untrained, without reused C7 errors."""
    counts={}
    for r in rows:
        if a.allocation_counts is not None:
            n=a.allocation_counts[sector][str(L)][str(r['id'])]*a.multiplier
            if sector=='power':n=max(4,n*a.power_multiplier//a.power_divisor)
            counts[r['id']]=n
            continue
        fixed=a.loop_points.get(L,a.points)
        if sector=='free'and L==8 and r['primitive']:
            n=fixed*a.multiplier if fixed is not None else prim[r['id']]
        else:
            n=(fixed if fixed is not None else max(4,r['points']))*a.multiplier
            if sector=='power':n=max(4,n*a.power_multiplier//a.power_divisor)
        counts[r['id']]=n
    return counts

def power_divisor_violations(a,inv:dict)->list[str]:
    bad=[]
    for L in range(3,9):
        for r in inv['power'][str(L)]:
            fixed=a.loop_points.get(L,a.points)
            if a.allocation_counts is not None:fixed=a.allocation_counts['power'][str(L)][str(r['id'])]
            n=(fixed if fixed is not None else max(4,r['points']))*a.multiplier*a.power_multiplier
            if n<4*a.power_divisor:bad.append(f'power L{L} graph {r["id"]}: {n} / {a.power_divisor} < 4')
    return bad

def primitive_plan(a,table:dict)->dict:
    """Recompute every eight-loop primitive. C7 scalar periods cannot replace L7 jets."""
    if a.primitive_mode!='recompute':raise ValueError('C8 requires recomputed primitive jets')
    ids=sorted(r['id']for r in table['free']['8']if r['primitive'])
    n=a.loop_points.get(8,a.points if a.points is not None else a.primitive_points)*a.multiplier
    counts={str(g):n for g in ids} if a.allocation_counts is None else {str(g):a.allocation_counts['free']['8'][str(g)]*a.multiplier for g in ids}
    return {'allocation':'uniform' if a.allocation_counts is None else 'frozen pilot allocation','counts':counts,
            'budget_points_per_replicate':sum(counts.values()),'points_per_replicate':sum(counts.values()),
            'projected_primitive_block_se':None,'hypothetical':None,
            'projection_note':'No C8 pilot variance is assumed.'}

COST_KEY=re.compile(r'(free|power):[3-8]:[0-9]+')

def load_cost_model(path:Path,backend:str)->dict:
    """A --cost-model file, validated in full (type, schema, dimension, order, backend, a non-empty map of
    'sector:L:graph' keys to positive finite seconds per point) before the campaign directory exists."""
    try:m=load(Path(path))
    except (OSError,ValueError)as e:raise ValueError(f'cannot read cost model {path}: {e}')from e
    if not isinstance(m,dict)or m.get('schema')!='c8-d2-cost-model-1'or m.get('dimension')!=2 or m.get('order')!=8:raise ValueError(f'{path} is not a c8-d2-cost-model-1 cost model')
    if m.get('backend')!=backend:raise ValueError(f'cost model backend {m.get("backend")!r} differs from --backend {backend}')
    c=m.get('seconds_per_point')
    if not isinstance(c,dict)or not c:raise ValueError(f'cost model {path} has no seconds_per_point entries')
    for k,v in c.items():
        if not isinstance(k,str)or not COST_KEY.fullmatch(k):raise ValueError(f'cost model key {k!r} is not sector:L:graph')
        if isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)or v<=0:raise ValueError(f'cost model entry {k} = {v!r} is not a positive finite number of seconds')
    return m

def read_build_record(exe:Path):
    br=exe.with_name(exe.name+'.build.json')
    if not br.exists():
        print(f'warning: no build record {br.name}; rebuild with `make clean && make` (or `make -B`) to record compiler, flags and library versions (A-L13)',file=sys.stderr);return None
    rec=load(br)
    if rec.get('executable_sha256')!=digest(exe):raise ValueError(f'{br} describes a different executable than {exe}; rebuild with `make clean && make` (or `make -B`)')
    if rec.get('optimized')is False:print(f'warning: {exe.name} was built without optimization (OPTFLAGS={rec.get("OPTFLAGS")!r})',file=sys.stderr)
    return rec

def plan(a):
    out=a.directory.resolve();exe=exe_for(a.backend)
    # Every argument check comes before any file or directory is created.
    if a.loop_points and a.points is not None:raise ValueError('Use either --points or --loop-points')
    loop_points={}
    if a.loop_points:
        for field in a.loop_points.split(','):
            parts=field.split(':')
            if len(parts)!=2:raise ValueError('--loop-points must be L:points,L:points,...')
            L,n=map(int,parts)
            if L not in range(3,9) or L in loop_points or n<4 or not pow2(n):raise ValueError('Loop counts require distinct L=3..8 and powers of two >=4')
            loop_points[L]=n
    a.loop_points=loop_points
    a.allocation_counts=None
    if a.allocation and (a.points is not None or loop_points):raise ValueError('--allocation cannot be combined with --points or --loop-points')
    if out.exists():raise FileExistsError('Use a new campaign directory')
    if a.replicates<4 or a.replicates%2 or min(a.shards,a.threads,a.checkpoint_tasks,a.chunk_points)<1 or a.test_graphs<0:raise ValueError('invalid sizes')
    if a.checkpoint_tasks>100000:raise ValueError('checkpoint_tasks exceeds the native task-file limit (100000)')
    if a.threads>a.checkpoint_tasks:raise ValueError(f'--threads {a.threads} exceeds --checkpoint-tasks {a.checkpoint_tasks}: at most {a.checkpoint_tasks} threads can ever be busy')
    if a.checkpoint_graphs is not None and a.checkpoint_graphs<1:raise ValueError('--checkpoint-graphs must be positive')
    if a.checkpoint_seconds is not None and (not math.isfinite(a.checkpoint_seconds)or a.checkpoint_seconds<=0):raise ValueError('--checkpoint-seconds must be positive and finite')
    if a.checkpoint_seconds is not None and a.cost_model is None:raise ValueError('--checkpoint-seconds requires a measured --cost-model (summed kernel core-seconds)')
    if a.task_order=='legacy'and(a.checkpoint_graphs is not None or a.checkpoint_seconds is not None):raise ValueError('Explicit graph/time checkpoint limits require --task-order graph')
    if not all(pow2(n)for n in(a.multiplier,a.power_multiplier,a.power_divisor,a.primitive_points))or(a.points is not None and not pow2(a.points)):
        raise ValueError('counts, multipliers and the power divisor must be powers of two')
    if not 0<=a.seed<2**63:raise ValueError('seed outside [0,2^63)')
    if a.seed_scheme=='legacy':
        why=legacy_refusal(a.seed)
        if why:raise ValueError(why+'; under --seed-scheme legacy it would repeat archived or used streams. Choose a fresh random seed.')
    if a.checkpoint_tasks<16*a.threads:print(f'warning: --checkpoint-tasks {a.checkpoint_tasks} < 16 x {a.threads} threads; per-block barriers will idle cores',file=sys.stderr)
    prepare();im=verify_inputs()  # A-L16: every listed input, the ten packs included
    inv=load(ROOT/'inputs/inventory.json');allocation_file=None
    if a.allocation:
        allocation_file=load(a.allocation)
        if allocation_file.get('schema')!='c8-d2-allocation-1' or allocation_file.get('dimension')!=2 or allocation_file.get('order')!=8:
            raise ValueError('Not a C8(2) frozen allocation')
        if allocation_file.get('inputs_manifest_sha256')!=digest(ROOT/'inputs/manifest.json'):
            raise ValueError('Allocation describes different graph inputs')
        if a.seed in allocation_file.get('pilot_seeds',[]):raise ValueError('Production must use a fresh seed, independent of its allocation pilot')
        ac=allocation_file['counts']
        if set(ac)!=set(inv):raise ValueError('Allocation must include both forest sectors')
        for sector in inv:
            if set(ac[sector])!=set(inv[sector]):raise ValueError('Allocation must include loops3--8')
            for L,rows in inv[sector].items():
                if set(ac[sector][L])!={str(r['id']) for r in rows}:raise ValueError(f'Allocation graph coverage mismatch: {sector} L{L}')
                if any(type(n)is not int or n<4 or not pow2(n) for n in ac[sector][L].values()):raise ValueError('Allocation counts must be powers of two >=4')
        a.allocation_counts=ac
    prim=primitive_plan(a,inv)
    bad=power_divisor_violations(a,inv)
    if bad:raise ValueError(f'--power-divisor {a.power_divisor} would leave {len(bad)} power strata below 4 points before the floor, e.g. '+'; '.join(bad[:5]))
    measured=a.cost_model is not None;cost_model=load_cost_model(a.cost_model,a.backend)if measured else None
    costs={k:float(v)for k,v in cost_model['seconds_per_point'].items()}if measured else{}
    unknown_cost=max(costs.values(),default=1.)
    if not exe.exists():raise FileNotFoundError('Build the selected backend with make or make gmp: '+str(exe))
    build=json.loads(subprocess.check_output([str(exe),'--describe'],text=True))
    if build['dimension']!=2 or build['order']!=8:raise ValueError('wrong executable')
    build_record=read_build_record(exe);cal=load_calibration();prim_counts={int(g):n for g,n in(prim['counts']or{}).items()}
    all_counts={}
    for campaign,sector,L in GROUPS:
        rows=inv[sector][str(L)];counts=stratum_counts(a,rows,sector,L,prim_counts)
        if a.test_graphs:
            # Explicitly labelled incomplete workflow test; never a production result.
            selected={r['id']for r in sorted(rows,key=lambda r:(r['cost'],r['id']))[:a.test_graphs]}
            counts={g:(n if g in selected else 0)for g,n in counts.items()}
        bits=52 if campaign=='a'else 60
        if max(counts.values())>2**bits:raise ValueError(f'Sobol period exceeded: group {campaign}_{sector}_L{L} has a stratum of {max(counts.values())} > 2^{bits} points')
        all_counts[campaign,sector,L]=counts
    out.mkdir(parents=True);(out/'groups').mkdir()
    if measured:dump(out/'cost_model.json',cost_model)
    if allocation_file is not None:dump(out/'allocation.json',allocation_file)
    pending=[]
    for campaign,sector,L in GROUPS:
        name=f'{campaign}_{sector}_L{L}';p=out/'groups'/name;p.mkdir();rows=inv[sector][str(L)];counts=all_counts[campaign,sector,L]
        bits=52 if campaign=='a'else 60;seeds=derive_seeds(a.seed,campaign,sector,L,a.seed_scheme);top=max(counts.values())
        net=make_net(p/'sobol.bin',a.replicates,4*L-1,bits,seeds['net'],max(top,1))
        db=dbopen(p/'tasks.sqlite');db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER); CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
        uid=0;total_cost=0.;expected_buffer=[];task_buffer=[]
        for rep in range(a.replicates):
            for row in rows:
                gi=row['id'];total=counts[gi];expected_buffer.append((rep,gi,total))
                if len(expected_buffer)>=10000:db.executemany('INSERT INTO expected VALUES(?,?,?)',expected_buffer);expected_buffer.clear()
                per=costs.get(f'{sector}:{L}:{gi}',unknown_cost)if measured else float(row['cost'])
                for start in range(0,total,a.chunk_points):
                    stop=min(total,start+a.chunk_points);cost=(stop-start)*per;total_cost+=cost
                    task_buffer.append((uid,rep,gi,start,stop,total,cost));uid+=1
                    if len(task_buffer)>=10000:db.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL,NULL)',task_buffer);task_buffer.clear()
        if expected_buffer:db.executemany('INSERT INTO expected VALUES(?,?,?)',expected_buffer)
        if task_buffer:db.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,NULL,NULL)',task_buffer)
        db.commit();db.close()
        spu=1. if measured else(calibration_row(cal,a.backend,sector,L)or{}).get('seconds_per_proxy_unit')
        pending.append(dict(name=name,campaign=campaign,sector=sector,L=L,p=p,tasks=uid,cost=total_cost,spu=spu,seed=seeds['native'],counts=counts,net=net))
    calibrated=all(g['spu']for g in pending)
    # Shard sizes follow estimated core-seconds; uncalibrated proxy units only when a calibration row is missing.
    weight=lambda g:g['cost']*g['spu']if calibrated else g['cost']
    wmax=max((weight(g)for g in pending if g['tasks']),default=0.) or 1.
    groups=[];jobs=[];estimates={}
    for g in pending:
        want=a.shards if a.shard_policy=='uniform'else max(1,round(a.shards*weight(g)/wmax))
        # Only one task database/cache remains open at a time during planning.
        nshards=min(want,g['tasks']);db=dbopen(g['p']/'tasks.sqlite');heap=[(0.,i)for i in range(nshards)];heapq.heapify(heap);shard_cost=[0.]*nshards
        def batched(query,update,step):
            cur=db.cursor();buf=[]
            for row in db.execute(query):
                buf.append(step(row))
                if len(buf)>=100000:cur.executemany(update,buf);buf.clear()
            if buf:cur.executemany(update,buf)
        def lpt(row):
            tid,cost=row;c,i=heapq.heappop(heap);heapq.heappush(heap,(c+cost,i));shard_cost[i]+=cost;return (i,tid)
        if nshards and a.task_order=='graph':nshards,shard_cost=assign_graph_bundles(db,want)
        elif nshards:batched('SELECT uid,cost FROM tasks ORDER BY cost DESC,uid','UPDATE tasks SET shard=? WHERE uid=?',lpt)
        # Frozen position inside each shard: estimated cost descending, then uid, so a checkpoint block holds similar tasks.
        state={'shard':None,'pos':0}
        def position(row):
            tid,shard=row
            if shard!=state['shard']:state.update(shard=shard,pos=0)
            state['pos']+=1;return (state['pos']-1,tid)
        if nshards and a.task_order=='legacy':batched('SELECT uid,shard FROM tasks ORDER BY shard,cost DESC,uid','UPDATE tasks SET pos=? WHERE uid=?',position)
        db.execute('CREATE INDEX shard_order ON tasks(shard,pos)');db.execute('CREATE INDEX stream_order ON tasks(rep,gi,lo)');db.commit()
        block_stats=freeze_blocks(db,nshards,a.checkpoint_tasks,a.checkpoint_graphs,a.checkpoint_seconds)if a.task_order=='graph'else None
        db.close()
        s=g['spu'];longest=max(shard_cost,default=0.)
        estimates[g['name']]={'cost_units':g['cost'],'shards':nshards,'tasks':g['tasks'],
                              'core_hours':g['cost']*s/3600 if s else None,'max_shard_core_seconds':longest*s if s else None,
                              'max_shard_wall_seconds':longest*s/(a.threads*ASSUMED_EFFICIENCY)if s else None,
                              'estimate':'available'if s else'unavailable',
                              **({'checkpoint_layout':block_stats}if block_stats else{})}
        config={'schema':GROUP_SCHEMA,'name':g['name'],'campaign':g['campaign'],'sector':g['sector'],'L':g['L'],'seed':g['seed'],'seed_scheme':a.seed_scheme,'layout':0,
                'rate':'.8'if g['campaign']=='a'else'.9','replicates':a.replicates,'counts':{str(k):v for k,v in g['counts'].items()},'net':g['net'],'sum_mode':a.sum_mode,
                'primitive_mode':a.primitive_mode,'shards':nshards,'block_order':('graph bundles: descending total estimated cost, graph id, replicate, begin, uid'if a.task_order=='graph'else'pos: estimated cost descending, then uid'),'tasks':g['tasks'],
                'tasks_sha256':digest(g['p']/'tasks.sqlite'),'samples':sum(g['counts'].values())*a.replicates,'build':build}
        if block_stats:config['checkpoint_layout']=block_stats
        dump(g['p']/'config.json',config);groups.append({'name':g['name'],'sha256':digest(g['p']/'config.json')})
        base=len(jobs);jobs.extend({'id':base+i,'group':g['name'],'shard':i}for i in range(nshards))
    est=estimate_summary(estimates,pending,a,cal,measured,calibrated)
    manifest=dict(schema=SCHEMA,tool_sha256={n:digest(ROOT/'tools'/n)for n in TOOLS},dimension=2,order=8,epsilon='2s-2',package=str(ROOT),
                  inputs_manifest_sha256=digest(ROOT/'inputs/manifest.json'),backend=a.backend,build=build,build_record=build_record,executable_sha256=digest(exe),
                  threads=a.threads,checkpoint_tasks=a.checkpoint_tasks,primitive_mode=a.primitive_mode,
                  task_order=a.task_order,checkpoint_graphs=a.checkpoint_graphs,checkpoint_seconds=a.checkpoint_seconds,
                  purpose=a.purpose,
                  allocation={'frozen':'inputs/inventory.json contains an untrained default of 4096 points; point_override and multipliers are fixed before this campaign',
                              'point_override':a.points,'loop_points':a.loop_points,'multiplier':a.multiplier,'power_multiplier':a.power_multiplier,'power_divisor':a.power_divisor,
                              'power_count':'max(4, points x multiplier x power_multiplier / power_divisor)','primitive_points':a.primitive_points,'primitive':prim},
                  seed=a.seed,seed_scheme=a.seed_scheme,shard_policy=a.shard_policy,groups=groups,jobs=jobs,campaign_weights={'a':.5,'b':.5},
                  groups_independent_by_loop_campaign_sector=True,sampling_unit='complete graph-summed randomized replicate, not chunk',
                  power_sector='explicitly integrated; NOT assumed zero',test_only=bool(a.test_graphs),test_graphs=a.test_graphs,
                  cost_model_sha256=digest(out/'cost_model.json')if measured else None,point_override=a.points,allocation_multiplier=a.multiplier,
                  allocation_file_sha256=digest(out/'allocation.json') if allocation_file is not None else None,
                  power_multiplier=a.power_multiplier,power_divisor=a.power_divisor,primitive_points=a.primitive_points,estimates=est)
    dump(out/'manifest.json',manifest)
    if len(jobs)>MAX_ARRAY:print(f'note: {len(jobs)} jobs exceed one array of {MAX_ARRAY}; slurm/submit.sh splits them into offset windows (C8_INDEX_OFFSET)',file=sys.stderr)
    ch=lambda x:float(f'{x:.4g}')if isinstance(x,float)else x  # 4 significant digits
    print(json.dumps({'directory':str(out),'jobs':len(jobs),'samples':sum(load(out/'groups'/g['name']/'config.json')['samples']for g in groups),'backend':a.backend,
                      'test_only':manifest['test_only'],'estimate_basis':est['basis'],'estimated_core_hours':ch(est['total_core_hours'])if est['total_core_hours']is not None else'unavailable',
                      'estimated_core_hours_by_group':{k:(ch(v['core_hours'])if v['core_hours']is not None else'unavailable')for k,v in estimates.items()},
                      'estimated_max_shard_wall_seconds':ch(est['max_shard_wall_seconds'])if est['max_shard_wall_seconds']is not None else'unavailable',
                      'suggested_sbatch_time':hms(est['suggested_time_seconds'])if est['suggested_time_seconds']else'unavailable (give --time)',
                      'power_divisor':a.power_divisor,'power_divisor_effect':est['power_divisor_effect'],
                      'primitive_allocation':prim['allocation'],'primitive_points_per_replicate':prim['points_per_replicate'],
                      'projected_primitive_block_se (projection from archived variances)':{'used':prim['projected_primitive_block_se'],
                          **({f"hypothetical {prim['hypothetical']['allocation']} (not used)":prim['hypothetical']['projected_primitive_block_se']}if prim['hypothetical']else{})}},indent=2))

def estimate_summary(estimates,pending,a,cal,measured,calibrated)->dict:
    avail=all(e['core_hours']is not None for e in estimates.values())
    total=sum(e['core_hours']for e in estimates.values())if avail else None
    wall=max((e['max_shard_wall_seconds']for e in estimates.values()),default=0.)if avail else None
    power=sum(e['core_hours']for k,e in estimates.items()if '_power_'in k)if avail else None
    pu=sum(g['cost']for g in pending if g['sector']=='power');fu=sum(g['cost']for g in pending if g['sector']=='free')
    effect={'power_divisor':a.power_divisor,'core_hours':total,'core_hours_at_power_divisor_1':(total+(a.power_divisor-1)*power)if avail else None,
            'proxy_or_cost_units':fu+pu,'units_at_power_divisor_1':fu+pu*a.power_divisor}
    effect['change_core_hours']=(effect['core_hours']-effect['core_hours_at_power_divisor_1'])if avail else'unavailable'
    effect['change_fraction_of_units']=(fu+pu)/(fu+pu*a.power_divisor)-1 if fu+pu else 0.
    rows={}
    if not measured:
        for g in pending:rows[g['name']]=calibration_row(cal,a.backend,g['sector'],g['L'])
    return {'basis':'measured (--cost-model: seconds per point, no calibration factor)'if measured else'proxy (inventory cost x points, x CALIBRATION seconds per proxy unit)',
            'backend':a.backend,'calibration_rows':rows if not measured else None,'calibration_sha256':None,
            'shard_basis':'estimated core-seconds'if calibrated else'uncalibrated proxy units (calibration unavailable for this backend)',
            'assumed_thread_efficiency':ASSUMED_EFFICIENCY,'groups':estimates,'total_core_hours':total,'max_shard_wall_seconds':wall,
            'suggested_time_seconds':max(900,math.ceil(3*wall/60)*60)if avail else None,'power_divisor_effect':effect,
            'estimate':'available'if avail else'unavailable','note':'planning estimates from a hardware-specific calibration, not measurements'}

# ---------------------------------------------------------------- verification of a planned campaign
def verify_base(directory:Path,check_executable=True,accept_tool_change=False):
    """Manifest, pinned tools, inputs and (optionally) the executable. Returns (manifest, inputs manifest, manifest sha256,
    accepted tool changes). A changed tool is an error unless accept_tool_change (merge/assemble only)."""
    data=(directory/'manifest.json').read_bytes();m=json.loads(data);mh=hashlib.sha256(data).hexdigest()
    if m.get('schema')==V1_SCHEMA:raise ValueError(V1_MESSAGE.format(d=directory))
    if m.get('schema')!=SCHEMA or m.get('dimension')!=2 or m.get('order')!=8:raise ValueError(f'campaign schema {m.get("schema")} is not {SCHEMA}')
    changes={}
    for n,h in m['tool_sha256'].items():
        f=ROOT/'tools'/n;cur=digest(f)if f.exists()else None
        if cur!=h:
            if not accept_tool_change:raise ValueError(f'Checksum mismatch: tools/{n} differs from the tool pinned by the plan; merge and assemble accept a changed tool only with --accept-tool-change (recorded as provenance)')
            changes[n]={'planned':h,'current':cur}
    im=read_verified(ROOT/'inputs/manifest.json',m['inputs_manifest_sha256'])
    if im.get('schema')!='c8-d2-hpc-inputs-1':raise ValueError('wrong inputs manifest')
    if m.get('cost_model_sha256'):checked(directory/'cost_model.json',m['cost_model_sha256'])
    if m.get('allocation_file_sha256'):checked(directory/'allocation.json',m['allocation_file_sha256'])
    for name in SMALL_INPUTS:checked(ROOT/'inputs'/name,im['sha256'][name])
    if check_executable:checked(exe_for(m['backend']),m['executable_sha256'])
    return m,im,mh,changes

def group_of(directory:Path,m:dict,name:str):
    p=directory/'groups'/name;cfg=read_verified(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==name))
    if cfg.get('schema')!=GROUP_SCHEMA:raise ValueError('wrong group config schema')
    checked(p/'tasks.sqlite',cfg['tasks_sha256']);return p,cfg

def validate_checkpoint(doc,block,cfg,m,mh):
    if doc.get('manifest_sha256')!=mh or doc.get('config_hash')!=object_hash(cfg):raise ValueError('checkpoint identity mismatch')
    rt=doc.get('runtime')or{}
    if rt.get('executable_sha256')!=m['executable_sha256']or doc.get('executable_sha256')!=m['executable_sha256']:raise ValueError('checkpoint was produced by a different executable')
    if rt.get('inputs_manifest_sha256')!=m['inputs_manifest_sha256']:raise ValueError('checkpoint was produced from different inputs')
    if rt.get('net_sha256')!=cfg['net']['sha256']:raise ValueError('checkpoint was produced from a different Sobol net')
    n=doc['native']
    if object_hash(n)!=doc.get('payload_sha256'):raise ValueError('checkpoint payload corruption')
    expected={'schema':'c8-d2-hpc-native-1','order':8,'L':cfg['L'],'seed':cfg['seed'],'layout':cfg['layout'],'bits':cfg['net']['bits'],'sum_mode':cfg['sum_mode'],'mp_backend':cfg['build']['mp_backend'],'mp_digits10':cfg['build']['mp_digits10'],'long_double_bits':cfg['build']['long_double_bits']}
    for k,v in expected.items():
        if n.get(k)!=v:raise ValueError('native metadata mismatch: '+k)
    if abs(D(n['rate'])-D(cfg['rate']))>D(2)**(-cfg['build']['long_double_bits']+1):raise ValueError('importance rate mismatch')
    if len(n['rows'])!=len(block):raise ValueError('incomplete checkpoint')
    for expected,r in zip(block,n['rows']):
        if tuple(r[k]for k in ('uid','rep','graph','begin','end','total'))!=tuple(expected):raise ValueError('wrong task coordinates')
        if len(r['values'])!=2*(9-cfg['L'])or any(not D(v).is_finite()for v in r['values']):raise ValueError('invalid jet')
        if not 0<=r['mp']<=r['quad']<=r['end']-r['begin']:raise ValueError('invalid promotion counters')
    return n

# ---------------------------------------------------------------- execution
def stage_graphs(td,cfg,block,inventory):
    """Seek only assigned graph blobs and verify their content hashes."""
    root=td/'graphs';dest=root/f'L{cfg["L"]}';dest.mkdir(parents=True)
    pack=ROOT/f'inputs/packs/{cfg["sector"]}_L{cfg["L"]}.pack'
    with pack.open('rb')as f:
        for gi in sorted({r[2]for r in block}):
            row=inventory[gi];f.seek(row['offset']);data=f.read(row['length'])
            if len(data)!=row['length']or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Packed graph content mismatch')
            (dest/f'G{gi}.txt').write_bytes(data)
    return root

def stage_runtime(runtime:Path,m:dict,im:dict,cfg:dict,net:Path)->dict:
    """Copy the plan's executable, gamma_d2_8.txt and the group's Sobol net into the job-private directory; verify every
    COPY and use only the copies (graph members are staged per block by stage_graphs)."""
    src=exe_for(m['backend']);exe=runtime/src.name;shutil.copyfile(src,exe);os.chmod(exe,0o700);exe_sha=digest(exe)
    if exe_sha!=m['executable_sha256']:raise ValueError(f'{src} differs from the planned executable; never rebuild inside a campaign')
    gamma=runtime/'gamma_d2_8.txt';shutil.copyfile(ROOT/'inputs/gamma_d2_8.txt',gamma);checked(gamma,im['sha256']['gamma_d2_8.txt'])
    netcopy=runtime/'sobol.bin';shutil.copyfile(net,netcopy);net_sha=digest(netcopy)
    if net_sha!=cfg['net']['sha256']:raise ValueError('the Sobol net differs from the plan: '+str(net))
    return {'executable':exe,'gamma':gamma,'net':netcopy,'executable_sha256':exe_sha,'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':net_sha}

SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs')
STOP_SIGNALS=(signal.SIGTERM,signal.SIGINT,signal.SIGHUP)
# Native children of `run`, and the deferred stop signal of a launch in progress. Launch and registration are atomic
# with respect to TERM/INT/HUP: during them the handler only records the signal (blocking the signals instead would be
# inherited by the child), and it is raised once the child is registered, so the cleanup always finds the child.
_NATIVE={'launching':False,'pending':None,'children':[]}

class Terminated(BaseException):
    """Raised by the SIGTERM/SIGINT/SIGHUP handler of `run`; unwinds through the cleanup of the job-private runtime."""
    def __init__(self,signum):super().__init__(f'stopped by signal {signum}');self.signum=signum

def _stop(signum,frame):
    for s in STOP_SIGNALS:signal.signal(s,signal.SIG_IGN)  # a second signal must not interrupt the cleanup
    if _NATIVE['launching']:_NATIVE['pending']=signum;return
    raise Terminated(signum)

def _after_launch(child):"""Test seam: called right after a native child is created and registered, while stop signals are deferred."""

def run_native(cmd,log):
    """Run one native work block. The child is registered before any stop signal can unwind (stop_children() in run's
    cleanup always finds it); an interruption while it runs stops and reaps it here, before its block directory goes."""
    _NATIVE['launching']=True
    try:child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);_NATIVE['children'].append(child);_after_launch(child)
    except BaseException:
        _NATIVE['launching']=False
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        raise
    _NATIVE['launching']=False
    try:
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        rc=child.wait()
    except BaseException:
        stop_children();raise
    _NATIVE['children'].remove(child)
    if rc:raise subprocess.CalledProcessError(rc,cmd)

def stop_children():
    """Terminate (after 10 s kill) and reap every registered native child."""
    while _NATIVE['children']:
        child=_NATIVE['children'].pop()
        if child.poll()is None:
            try:child.terminate();child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()

def run(a):
    """Run one job index. SIGTERM, SIGINT and SIGHUP stop the native child, remove the job-private runtime and exit
    with 128+signal; committed checkpoints stay (publication is atomic), the interrupted block is simply redone later.
    SIGKILL, node failure or an expired Slurm KillWait cannot be cleaned up."""
    main_thread=threading.current_thread()is threading.main_thread()
    _NATIVE.update(launching=False,pending=None,children=[])
    old={s:signal.signal(s,_stop)for s in STOP_SIGNALS}if main_thread else{}
    try:_run(a)
    except Terminated as t:
        print(f'run: {t}; native work stopped, job-private runtime removed, committed checkpoints kept',file=sys.stderr,flush=True)
        raise SystemExit(128+t.signum)
    finally:
        for s,h in old.items():signal.signal(s,h)

def _run(a):
    directory=a.directory.resolve();m,im,mh,_=verify_base(directory);idx=a.index
    if idx is None:
        if 'SLURM_ARRAY_TASK_ID'not in os.environ:raise ValueError('give --index or run inside a Slurm array (SLURM_ARRAY_TASK_ID)')
        off=os.environ.get('C8_INDEX_OFFSET','0')
        if not off.isdigit():raise ValueError('C8_INDEX_OFFSET must be a non-negative integer')
        idx=int(off)+int(os.environ['SLURM_ARRAY_TASK_ID'])
    if not 0<=idx<len(m['jobs']):raise ValueError('job index outside plan')
    j=m['jobs'][idx];p,cfg=group_of(directory,m,j['group']);checked(p/'sobol.bin',cfg['net']['sha256'])
    threads=a.threads or m['threads'];T=m['checkpoint_tasks']
    if threads<1:raise ValueError('invalid thread count')
    if threads>T:raise ValueError(f'{threads} threads exceed checkpoint_tasks={T}: at most {T} threads can ever be busy; use fewer threads or re-plan')
    if T<16*threads:print(f'warning: checkpoint_tasks={T} < 16 x {threads} threads; per-block barriers and start-up will idle cores',file=sys.stderr)
    scratch=a.scratch or os.environ.get('SLURM_TMPDIR')or None
    # One small inventory index in Python. Native memory is bounded by the work block.
    inv={r['id']:r for r in load(ROOT/'inputs/inventory.json')[cfg['sector']][str(cfg['L'])]}
    db=dbopen(p/'tasks.sqlite',True);runtime=Path(tempfile.mkdtemp(prefix='c8d2_runtime_',dir=scratch))
    try:
        rt=stage_runtime(runtime,m,im,cfg,p/'sobol.bin');fp=fingerprint(rt['executable']);done=0
        (p/'checkpoints').mkdir(exist_ok=True);(p/'logs').mkdir(exist_ok=True)
        for part,block in enumerate(task_blocks(db,j['shard'],T)):
            name=f's{j["shard"]:06d}_p{part:06d}';dest=p/'checkpoints'/f'{name}.json'
            if dest.exists():validate_checkpoint(load(dest),block,cfg,m,mh);continue
            if a.max_blocks is not None and done>=a.max_blocks:print(f'stopped after {done} blocks (--max-blocks)',flush=True);break
            with tempfile.TemporaryDirectory(prefix='block_',dir=runtime)as td:
                td=Path(td);graphroot=stage_graphs(td,cfg,block,inv);tasks=td/'tasks.txt'
                tasks.write_text(f'C8D2TASKS1 {cfg["L"]} {len(block)}\n'+''.join(' '.join(map(str,r))+'\n'for r in block));out=td/'native.json'
                cmd=list(map(str,[rt['executable'],graphroot,rt['gamma'],rt['net'],tasks,out,cfg['seed'],cfg['layout'],cfg['rate'],threads,cfg['sum_mode'],'-']))
                try:
                    with (td/'native.log').open('w')as log:run_native(cmd,log)
                except subprocess.CalledProcessError as exc:
                    message=(td/'native.log').read_text();publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message);raise RuntimeError('Native work block failed: '+message[-4000:])from exc
                n=load(out)
                doc={'runtime':{'executable_sha256':rt['executable_sha256'],'inputs_manifest_sha256':rt['inputs_manifest_sha256'],'net_sha256':rt['net_sha256'],'fingerprint':fp},
                     'manifest_sha256':mh,'config_hash':object_hash(cfg),'native':n,'payload_sha256':object_hash(n),'executable_sha256':rt['executable_sha256'],'task_file_sha256':digest(tasks)}
                validate_checkpoint(doc,block,cfg,m,mh)
                try:dump(dest,doc);state='committed'
                except FileExistsError:
                    # Another process published this block first (duplicate submission): keep it if scientifically identical.
                    prior=validate_checkpoint(load(dest),block,cfg,m,mh)
                    for x,y in zip(prior['rows'],n['rows']):
                        if any(x[k]!=y[k]for k in SCIENTIFIC):raise ValueError('Conflicting duplicate execution')
                    state='verified duplicate'
                done+=1;print(f'{state} {j["group"]}/{name}',flush=True)
    finally:
        stop_children();db.close();shutil.rmtree(runtime,ignore_errors=True)

# ---------------------------------------------------------------- merge
def validate_merged(p:Path,cfg:dict,m:dict,mh:str)->dict:
    d=load(p/'merged.json')
    if d.get('schema')!=MERGED_SCHEMA or d.get('complete')is not True or d.get('manifest_sha256')!=mh or d.get('config_hash')!=object_hash(cfg)or d.get('primitive_mode')!=m['primitive_mode']or d.get('sector')!=cfg['sector']or d.get('L')!=cfg['L']:
        raise ValueError('existing merged.json does not belong to this plan: '+str(p/'merged.json'))
    if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d.get('payload_sha256'):raise ValueError('merged payload checksum mismatch: '+str(p/'merged.json'))
    checked(p/'graph_replicates.csv',d['graph_replicates_sha256'])
    if len(d['batches'])!=cfg['replicates']or d.get('replicates')!=cfg['replicates']:raise ValueError('merged replicate count mismatch')
    return d

def merge_group(directory:Path,m:dict,name:str,scratch=None,mh=None,changes=None):
    p,config=group_of(directory,m,name);mh=mh or digest(directory/'manifest.json')
    dest=p/'merged.json'
    if dest.exists():validate_merged(p,config,m,mh);print(f'{name}: already merged and valid; skipped',flush=True);return dest
    source=dbopen(p/'tasks.sqlite',True);dim=2*(9-config['L']);fallbacks={'quad':0,'mp':0};count=0;seconds=0
    with tempfile.TemporaryDirectory(prefix='c8d2_merge_',dir=scratch)as td:
        db=dbopen(Path(td)/'merge.sqlite')
        # This database is private, disposable scratch and is rebuilt after a
        # failed merge. Durable checkpoint/result publication is unchanged.
        db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
        db.execute('CREATE TABLE actual(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,vals TEXT)')
        for shard in range(config['shards']):
            for part,block in enumerate(task_blocks(source,shard,m['checkpoint_tasks'])):
                f=p/'checkpoints'/f's{shard:06d}_p{part:06d}.json'
                if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
                n=validate_checkpoint(load(f),block,config,m,mh);seconds+=n['integration_seconds']
                db.executemany('INSERT INTO actual VALUES(?,?,?,?,?,?,?)',
                               ((r['uid'],r['rep'],r['graph'],r['begin'],r['end'],r['total'],json.dumps(r['values']))for r in n['rows']))
                count+=len(n['rows'])
                for r in n['rows']:
                    for k in fallbacks:fallbacks[k]+=r[k]
        if count!=config['tasks']:raise ValueError('wrong total task coverage')
        db.commit();db.execute('CREATE INDEX stream_sort ON actual(rep,gi,lo)')
        batches=[];csvtmp=Path(td)/'graph_replicates.csv';actual=iter(db.execute('SELECT rep,gi,lo,hi,total,vals FROM actual ORDER BY rep,gi,lo'));r=next(actual,None)
        with decimal.localcontext()as ctx,csvtmp.open('w')as f:
            ctx.prec=50;f.write('replicate,graph,'+','.join(f'jet_{i}'for i in range(dim))+'\n');batch=[D(0)]*dim;prevrep=0
            for rep,gi,total in source.execute('SELECT rep,gi,total FROM expected ORDER BY rep,gi'):
                if rep!=prevrep:batches.append([float(v)for v in batch]);batch=[D(0)]*dim;prevrep=rep
                graph=[D(0)]*dim;end=0
                while r is not None and (r[0],r[1])==(rep,gi):
                    rr,gg,lo,hi,tt,vals=r
                    if lo!=end or tt!=total or not 0<=lo<hi<=total:raise ValueError('incomplete, overlapping or inconsistent sample intervals')
                    graph=[x+D(v)for x,v in zip(graph,json.loads(vals))];end=hi;r=next(actual,None)
                if end!=total:raise ValueError(f'missing samples rep={rep},graph={gi}')
                f.write(f'{rep},{gi},'+','.join(map(str,graph))+'\n');batch=[x+y for x,y in zip(batch,graph)]
            if r is not None:raise ValueError('unexpected streams')
            batches.append([float(v)for v in batch])
        if len(batches)!=config['replicates']:raise ValueError('missing replicates')
        # Stream-copy the optional diagnostic table; never construct B x G x jet in RAM.
        target=p/'graph_replicates.csv'
        if target.exists():
            checked(target,digest(csvtmp))
        else:
            fd,tname=tempfile.mkstemp(prefix='graph_replicates.tmp.',dir=p)
            try:
                os.fchmod(fd,umask_mode())
                with csvtmp.open('rb')as i,os.fdopen(fd,'wb')as o:
                    shutil.copyfileobj(i,o);o.flush();os.fsync(o.fileno())
                try:os.link(tname,target)
                except FileExistsError:checked(target,digest(csvtmp))
            finally:os.unlink(tname)
        merged={'schema':MERGED_SCHEMA,'complete':True,'L':config['L'],'dimension':2,'config_hash':object_hash(config),'manifest_sha256':mh,'replicates':config['replicates'],'samples':config['samples'],'primitive_mode':config['primitive_mode'],'sector':config['sector'],'order':8,'batches':batches,'fallbacks':fallbacks,'integration_seconds_sum':seconds,'graph_replicates_sha256':digest(target)}
        if changes:merged['accepted_tool_changes']=changes
        merged['payload_sha256']=object_hash(merged)
        try:dump(dest,merged)
        except FileExistsError:
            # Another merge of the same complete group published first: accept it only if it is canonically identical.
            prior=validate_merged(p,config,m,mh)
            if canon(prior)!=canon(json.loads(json.dumps(merged,allow_nan=False))):raise ValueError('a different merged.json was published concurrently: '+str(dest))
            print(f'{name}: identical merged.json published concurrently; kept',flush=True)
        db.close()
    source.close();return dest

def merge(a):
    directory=a.directory.resolve();m,_,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=a.accept_tool_change)
    if changes:print('accepted tool changes (recorded in merged.json): '+', '.join(changes),file=sys.stderr)
    names=[a.group]if a.group else[g['name']for g in m['groups']]
    if any(n not in {g['name']for g in m['groups']}for n in names):raise ValueError('unknown group')
    workers=getattr(a,'workers',1)
    if workers<1:raise ValueError('--workers must be positive')
    if workers==1 or len(names)==1:
        for n in names:print(merge_group(directory,m,n,a.scratch,mh,changes),flush=True)
    else:
        # Each process owns one independent group and its own disk-backed
        # scratch database. Decimal summation order within a group is unchanged.
        with ProcessPoolExecutor(max_workers=min(workers,len(names)))as pool:
            outputs=pool.map(merge_group,itertools.repeat(directory),itertools.repeat(m),names,
                             itertools.repeat(a.scratch),itertools.repeat(mh),itertools.repeat(changes))
            for result in outputs:print(result,flush=True)

# ---------------------------------------------------------------- status and recovery
def campaign_tag(directory:Path)->str:
    """Slurm --comment tag of one campaign's jobs: c8:<sha256(resolved campaign path + manifest sha256)[:12]>.
    Identically planned campaigns in different directories get different tags. Do not move a campaign directory while
    its jobs are queued (the tag would change)."""
    d=Path(directory).resolve();return 'c8:'+hashlib.sha256(f'{d}\n{digest(d/"manifest.json")}'.encode()).hexdigest()[:12]

def ranges(ids):
    out=[];ids=sorted(ids)
    for k,g in itertools.groupby(enumerate(ids),lambda t:t[1]-t[0]):
        g=[x for _,x in g];out.append(str(g[0])if len(g)==1 else f'{g[0]}-{g[-1]}')
    return ','.join(out)

def windows(indices,size:int)->list[dict]:
    """Rebase global job indices into array windows [off, off+size) with in-window task ids."""
    if size<1:raise ValueError('array window size must be positive')
    return [{'offset':off,'array':ranges([i-off for i in indices if off<=i<off+size])}for off in sorted({i//size*size for i in indices})]

def checkpoint_runtime(path:Path):
    """The runtime record of a checkpoint, read from the head of the file (it is the first key); full parse as fallback."""
    try:
        with path.open('rb')as f:head=f.read(32768).decode('utf-8','replace')
        i=head.find('"runtime":')
        if i>=0:
            i+=len('"runtime":')
            while i<len(head)and head[i]in' \n\t\r':i+=1
            return json.JSONDecoder().raw_decode(head,i)[0]
    except ValueError:pass
    try:return load(path).get('runtime')
    except (OSError,ValueError):return None

def tool_changes(directory:Path)->dict:
    """Pinned tools that differ from the plan: {name: {planned, current}} (empty when all match)."""
    m=load(Path(directory)/'manifest.json');out={}
    for n,h in m.get('tool_sha256',{}).items():
        f=ROOT/'tools'/n;cur=digest(f)if f.exists()else None
        if cur!=h:out[n]={'planned':h,'current':cur}
    return out

def status_report(directory:Path,exclude=(),max_array:int=MAX_ARRAY,listing=False,fingerprints=True):
    directory=directory.resolve();m,_,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=True);T=m['checkpoint_tasks'];missing=[];groups={}
    lines=[f'WARNING: pinned tools changed since planning ({", ".join(sorted(changes))}): run and every Slurm submission refuse; restore them, '
           f'or merge/assemble by hand with --accept-tool-change']if changes else[]
    for g in m['groups']:
        p,config=group_of(directory,m,g['name']);db=dbopen(p/'tasks.sqlite',True);done_g=total_g=0;fps={}
        for j in (j for j in m['jobs']if j['group']==g['name']):
            nb=blocks_of(db,j['shard'],T);have=0
            for k in range(nb):
                f=p/'checkpoints'/f's{j["shard"]:06d}_p{k:06d}.json'
                if f.exists():
                    have+=1
                    if fingerprints:
                        fp=(checkpoint_runtime(f)or{}).get('fingerprint');key=fingerprint_key(fp)or'none'
                        e=fps.setdefault(key,{'checkpoints':0,'hosts':set(),'cpu_model':(fp or{}).get('cpu_model'),'glibc':(fp or{}).get('glibc')});e['checkpoints']+=1;e['hosts'].add((fp or{}).get('host'))
            done_g+=have;total_g+=nb
            if have<nb:missing.append(j['id'])
            if have<nb or listing:lines.append(f'job {j["id"]:6d} {g["name"]} shard {j["shard"]:4d}: {have}/{nb} blocks')
        db.close();fpl={k:{**v,'hosts':sorted(h for h in v['hosts']if h)}for k,v in fps.items()}
        groups[g['name']]={'committed':done_g,'total':total_g,'merged':(p/'merged.json').exists(),'fingerprints':fpl}
        lines.append(f'group {g["name"]}: {done_g}/{total_g} blocks, {"merged"if groups[g["name"]]["merged"]else"not merged"}'+
                     (f', {len(fpl)} fingerprint(s): '+'; '.join(f'{k} x{v["checkpoints"]} ({v["cpu_model"]}, {v["glibc"]}, hosts {",".join(v["hosts"][:4])}{"..."if len(v["hosts"])>4 else""})'for k,v in sorted(fpl.items()))if fpl else''))
    active=sorted(set(exclude)&set(missing));todo=[i for i in missing if i not in active]
    est=m['estimates'].get('suggested_time_seconds')
    result=('C8_test_result.json'if m['test_only']else'C8_result.json')
    return {'complete':not missing,'missing_jobs':missing,'active_not_resubmitted':active,'groups':groups,'result_present':(directory/result).exists(),'result_file':result,'tool_changes':changes,
            'threads':m['threads'],'suggested_time':hms(est)if est else None,'resubmit':windows(todo,max_array),'campaign_tag':campaign_tag(directory),'lines':lines}

def parse_ids(text):return [int(x)for x in filter(None,(text or'').split(','))]

def status(a):
    """Committed/total checkpoint blocks per job index; exit 0 only when every block is committed."""
    size=a.max_array if getattr(a,'max_array',None)is not None else None
    if size is None:  # the site's array limit, as submit.sh/resubmit.sh use it
        env=os.environ.get('C8_MAX_ARRAY','')
        if env and not env.isdigit():raise ValueError('C8_MAX_ARRAY must be a positive integer')
        size=int(env)if env else MAX_ARRAY
    if size<1:raise ValueError('--max-array must be a positive integer')
    r=status_report(a.directory,parse_ids(getattr(a,'exclude',None)),size,getattr(a,'all',False));lines=r.pop('lines')
    if getattr(a,'json',False):print(json.dumps(r))
    else:
        print('\n'.join(lines));print('result: '+(f'{r["result_file"]} present'if r['result_present']else f'no {r["result_file"]}'))
        if r['missing_jobs']:
            print(f'{len(r["missing_jobs"])} incomplete job indices: {ranges(r["missing_jobs"])}')
            if r['active_not_resubmitted']:print(f'still queued or running (not resubmitted): {ranges(r["active_not_resubmitted"])}')
            for w in r['resubmit']:
                # Each line goes through the guarded submission path (tools/slurm_submit.py) with campaign and package bound.
                print(f'resubmit: C8_MAX_ARRAY={size} C8_RUN={shlex.quote(str(Path(a.directory).resolve()))} C8_PACKAGE={shlex.quote(str(ROOT))} '
                      f'{shlex.quote(str(ROOT/"slurm/submit.sh"))} --window {w["offset"]}:{w["array"]}')
            print('then submit slurm/merge.sh once complete; or run slurm/resubmit.sh instead, which submits the missing windows and a merge that waits for them and for live work (cancel any merge still pending first)')
        else:print('complete: every checkpoint block is committed')
    if r['missing_jobs']:sys.exit(1)

# Slurm job states (squeue %T). LIVE may still run or be released; TERMINAL finished for good; anything else (COMPLETING,
# STAGE_OUT, PREEMPTED, unknown) is UNCERTAIN and every submission refuses until Slurm settles it.
LIVE_STATES=frozenset('PENDING RUNNING SUSPENDED CONFIGURING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESIZING SIGNALING STOPPED RESV_DEL_HOLD POWER_UP_NODE'.split())
TERMINAL_STATES=frozenset('COMPLETED CANCELLED FAILED TIMEOUT NODE_FAIL BOOT_FAIL DEADLINE OUT_OF_MEMORY REVOKED'.split())

def queue_state(directory:Path,queue_text:str)->dict:
    """This campaign's jobs in a squeue snapshot ('%comment|%K|%T|%i' per line, from squeue --all --states=all -r):
    refuse={code,message} for uncertain states or unexpected records, else the live work indices and live merges."""
    directory=directory.resolve();tag=campaign_tag(directory);tagged=[]
    for line in queue_text.splitlines():
        parts=[x.strip()for x in line.split('|')]
        if len(parts)!=4 or not parts[0].startswith(tag+':'):continue
        comment,task,state,jobid=parts;tagged.append({'comment':comment,'task':task,'state':state,'jobid':jobid})
    def refuse(code,msg):return {'refuse':{'code':code,'message':msg},'tag':tag}
    uncertain=[j for j in tagged if j['state']not in LIVE_STATES|TERMINAL_STATES]
    if uncertain:return refuse(69,'tagged job(s) '+','.join(f'{j["jobid"]}={j["state"]}'for j in uncertain)+' are completing, preempted or in an unrecognised state; '
                                   'nothing submitted. Rerun once Slurm has settled them (requeued, finished or gone).')
    live=[j for j in tagged if j['state']in LIVE_STATES];merges=[j['jobid']for j in live if j['comment']==tag+':merge'];work=[]
    for j in live:
        if j['comment']==tag+':merge':continue
        off=j['comment'][len(tag)+1:]
        if not off.startswith('off=')or not off[4:].isdigit()or not j['task'].isdigit():
            return refuse(69,f'unexpected record for tagged job {j["jobid"]} ({j["comment"]}, task {j["task"]}); was squeue run with -r? nothing submitted')
        work.append({'index':int(off[4:])+int(j['task']),'jobid':j['jobid']})
    return {'refuse':None,'tag':tag,'live_merges':merges,'live_work':work,'live_indices':sorted({w['index']for w in work})}

def recovery_plan(directory:Path,queue_text:str,max_array:int=MAX_ARRAY)->dict:
    """Pure recovery decision: refuse={code,message}, or the arrays to resubmit and the live tasks the merge must wait for."""
    q=queue_state(directory,queue_text)
    if q['refuse']:return q
    if q['live_merges']:return {'refuse':{'code':65,'message':f'merge job(s) {",".join(q["live_merges"])} of this campaign are still queued or running; scancel them (or let them finish), then rerun'},'tag':q['tag']}
    r=status_report(directory,q['live_indices'],max_array,fingerprints=False);r.pop('lines')
    return {'refuse':None,'tag':q['tag'],'threads':r['threads'],'suggested_time':r['suggested_time'],'complete':r['complete'],'missing_jobs':r['missing_jobs'],
            'live_indices':q['live_indices'],'live_missing_not_resubmitted':r['active_not_resubmitted'],'arrays':r['resubmit'],
            'merge_waits_on_live_tasks':sorted({w['jobid']for w in q['live_work']})}

# sbatch options that C8_SBATCH_ARGS and extra script arguments may carry (exact spellings only: getopt-style
# abbreviations such as --arr are refused). Everything else, in particular array, dependency, export, export-file,
# comment, output, clusters and positional words, is refused, because the scripts set or rely on those themselves.
# Every allowed value option takes a REQUIRED argument in Slurm 23.02 (options with optional arguments, e.g. --nice,
# are excluded: sbatch would not consume the next token, so this parser would skip over it).
SBATCH_LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user begin signal job-name exclude licenses wckey'.split())
SBATCH_LONG_FLAG=frozenset('requeue no-requeue hold'.split())
SBATCH_SHORT_VALUE=frozenset('ApqCtcJxL')

def check_sbatch_args(tokens)->str|None:
    """None if every token is an allowed sbatch option (with its value), else the reason for refusing."""
    i=0
    while i<len(tokens):
        tok=tokens[i]
        if tok.startswith('--'):
            name,eq,_=tok[2:].partition('=')
            if name in SBATCH_LONG_FLAG and not eq:i+=1;continue
            if name not in SBATCH_LONG_VALUE:return f'sbatch option {tok} is not allowed'
            i+=1 if eq else 2
            if not eq and i>len(tokens):return f'sbatch option {tok} needs a value'
        elif tok.startswith('-')and len(tok)>=2:
            if tok[1]not in SBATCH_SHORT_VALUE:return f'sbatch option {tok} is not allowed'
            i+=1 if len(tok)>2 else 2
            if len(tok)==2 and i>len(tokens):return f'sbatch option {tok} needs a value'
        else:return f'unexpected word {tok!r} (only sbatch options are allowed)'
    return None

def time_option(tokens)->str|None:
    """The last --time/-t value in an allowlisted token list, else None."""
    out=None;i=0
    while i<len(tokens):
        tok=tokens[i]
        if tok.startswith('--time='):out=tok[7:];i+=1
        elif tok=='--time':out=tokens[i+1];i+=2
        elif tok.startswith('-t')and len(tok)>2:out=tok[2:];i+=1
        elif tok=='-t':out=tokens[i+1];i+=2
        elif tok.startswith('--')and '='not in tok and tok[2:]in SBATCH_LONG_VALUE:i+=2
        elif tok.startswith('-')and not tok.startswith('--')and len(tok)==2:i+=2
        else:i+=1
    return out

def check_args(a):
    why=check_sbatch_args(a.args[1:]if a.args[:1]==['--']else a.args)
    if why:sys.exit(f'C8: {why}. Allowed: --'+' --'.join(sorted(SBATCH_LONG_VALUE|SBATCH_LONG_FLAG))+' and -'+' -'.join(sorted(SBATCH_SHORT_VALUE)))

def recover(a):
    size=a.max_array if a.max_array is not None else MAX_ARRAY
    print(json.dumps(recovery_plan(a.directory,Path(a.queue).read_text(),size)))

def tag(a):print(campaign_tag(a.directory))

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True,help='a fresh random integer in [0, 2^63); never reuse one')
    q.add_argument('--seed-scheme',choices=['hashed'],default='hashed',help='SHA-256 per-group seeds in a C8-specific domain; no legacy C7 stream reuse')
    q.add_argument('--replicates',type=int,default=32);q.add_argument('--multiplier',type=int,default=1);q.add_argument('--power-multiplier',type=int,default=1)
    q.add_argument('--purpose',choices=['pilot','production'],default='pilot',help='Campaign intent, recorded in result; neither choice certifies convergence')
    q.add_argument('--power-divisor',type=int,default=1,help='power of two dividing every power-sector count (after the multipliers), floor 4; opt-in allocation change')
    q.add_argument('--shards',type=int,default=32,help='shards of the most expensive group (others scale with estimated cost unless --shard-policy uniform)')
    q.add_argument('--shard-policy',choices=['cost','uniform'],default='cost');q.add_argument('--threads',type=int,default=8);q.add_argument('--checkpoint-tasks',type=int,default=512)
    q.add_argument('--task-order',choices=['graph','legacy'],default='graph',help='graph: whole-graph LPT with frozen graph-local blocks (default); legacy: previous per-task LPT/fixed-size blocks')
    q.add_argument('--checkpoint-graphs',type=int,help='Hard maximum unique graphs loaded in a block; bounds native graph memory independently of task count')
    q.add_argument('--checkpoint-seconds',type=float,help='Target maximum summed modeled kernel core-seconds per block; requires --cost-model. Indivisible oversized tasks are reported, not split')
    q.add_argument('--chunk-points',type=int,default=65536);q.add_argument('--primitive-mode',choices=['recompute'],default='recompute');q.add_argument('--primitive-points',type=int,default=4096)
    q.add_argument('--primitive-allocation',choices=['uniform'],default='uniform',help='recompute-mode split of uniform allocation of all eight-loop primitives')
    q.add_argument('--points',type=int,help='Override all stratum counts, primitives included (power of 2), for pilots and tests')
    q.add_argument('--loop-points',help='Override selected loop counts, including primitives: e.g. 3:4096,4:1024,5:256,6:64,7:16,8:4; mutually exclusive with --points')
    q.add_argument('--allocation',type=Path,help='Complete frozen allocation from an independent C8 pilot; graph coverage and input hashes are checked')
    q.add_argument('--cost-model',type=Path,help='Frozen task timing model; affects placement and estimates, never sample counts');q.add_argument('--backend',choices=['decimal','gmp'],default='decimal')
    q.add_argument('--sum-mode',choices=['compensated','legacy'],default='compensated');q.add_argument('--test-graphs',type=int,default=0,help='INCOMPLETE workflow test only; number of cheap graphs per group');q.set_defaults(func=plan)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int);q.add_argument('--threads',type=int);q.add_argument('--scratch')
    q.add_argument('--max-blocks',type=int,help='commit at most this many new blocks, then stop (time slicing, tests)');q.set_defaults(func=run)
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--group');q.add_argument('--scratch')
    q.add_argument('--workers',type=int,default=1,help='Independent groups to merge concurrently; each uses a private disk-backed scratch database (default 1)')
    q.add_argument('--accept-tool-change',action='store_true',help='merge although a pinned tool changed; old and new hashes are recorded in merged.json');q.set_defaults(func=merge)
    q=s.add_parser('status');q.add_argument('directory',type=Path);q.add_argument('--all',action='store_true',help='also list complete jobs');q.add_argument('--json',action='store_true',help='machine-readable report')
    q.add_argument('--exclude',help='comma-separated job indices still queued or running; left out of the resubmission lines');q.add_argument('--max-array',type=int,default=None,help='largest array per resubmission line (default: $C8_MAX_ARRAY, else 1000)');q.set_defaults(func=status)
    q=s.add_parser('recover',help='recovery decision from a squeue snapshot (used by slurm/resubmit.sh)');q.add_argument('directory',type=Path)
    q.add_argument('--queue',required=True,help="file with 'squeue --all --states=all -u \"$(id -un)\" -h -r -o %%200k|%%K|%%T|%%i' output (the account of the real uid)");q.add_argument('--max-array',type=int,default=MAX_ARRAY);q.set_defaults(func=recover)
    q=s.add_parser('tag',help="print the campaign's Slurm comment tag");q.add_argument('directory',type=Path);q.set_defaults(func=tag)
    q=s.add_parser('check-sbatch-args',help='allowlist check of user sbatch options');q.add_argument('args',nargs=argparse.REMAINDER);q.set_defaults(func=check_args)
    a=p.parse_args();a.func(a)
if __name__=='__main__':main()
