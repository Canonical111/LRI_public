#!/usr/bin/env python3
"""Plan, run, check, recover and merge complete C8(3) campaigns (PLAN component D): 24 groups = campaigns a/b x
sectors free/power x loops 3..8 (a pilot subset plans only the groups its selection names).

Scientific point identities (campaign, sector, loop, replicate, graph, point) never depend on the scheduler, the index,
the chunk, the checkpoint block or the thread count. The native worker runs only from a verified job-private copy of
the planned executable and inputs. A claim (`run --index`) reads its own per-index task file, pinned in the manifest,
and never opens the group's tasks.sqlite. Checkpoint blocks are frozen at plan time (production.cut_blocks, R10: at
most --checkpoint-tasks tasks and --block-seconds of predicted work per block) in the per-index task file's block
column; every consumer reads those boundaries. Plans are built on node-local scratch and published with one rename
(D.4). Merges are parallel over shards (phase 1) and groups (phase 2, an external merge of bounded fan-in whose final
pass adds in the serial order), so every output is byte-identical to the serial merge (D.13). A group's merged.json is
its commit point (F8-d3): tables without one are uncommitted and a merge replaces a different one (reported), while a
committed table never changes.

Exit codes: 1 a refused plan or failed check (message on stderr), 64 invalid input, 65 refused (an empty selection,
a refused role, a seed check without its reservation or a seed held by another campaign, S2-002), 69 unknown state, 74 a
quota or write failure at a publish point (D.7).
"""
from __future__ import annotations
import argparse,decimal,hashlib,heapq,itertools,json,math,os,re,shlex,shutil,signal,sqlite3,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import (ROOT,Refuse,QuotaRefused,canon,checked,cpu_model,digest,dump,dump_point,fingerprint,fingerprint_key,fsync_dir,fsync_tree,io_fault,
                    load,object_hash,pow2,publish,publish_bytes,quota_guard,read_member,read_verified,umask_mode,utc,QUOTA_ERRNOS)
D=decimal.Decimal
SCHEMA='c8-d3-production-1';GROUP_SCHEMA='c8-d3-group-1';MERGED_SCHEMA='c8-d3-merged-1';NATIVE_SCHEMA='c8-d3-hpc-native-1'
COST_SCHEMA='c8-d3-cost-model-1';DESIGN_SCHEMA='c8-d3-design-1';SELECTION_SCHEMA='c8-d3-selection-1';BOOT_SCHEMA='c8-d3-bootstrap-proxy-1'
BUILD_SCHEMA='c8-d3-build-1';INPUTS_SCHEMA='c8-d3-hpc-inputs-1';SEEDS_SCHEMA='c8-d3-seeds-1'
ORDER=8;GAMMA='gamma_d3_8.txt';TASK_MAGIC='C8D3TASKS1'
# Tools whose bytes determine what a campaign computes or how it is scheduled: pinned by every plan (PLAN Stage 6
# PINNED_TOOLS). assemble.py and report.py only read finished data; their hashes are recorded as provenance.
PINNED_TOOLS=('production.py','common.py','prepare_inputs.py','slurm_submit.py','lanes.py')
PROVENANCE_TOOLS=('assemble.py','report.py')
SMALL_INPUTS=('gamma_d3_8.txt','two_loop.json','inventory.json')
MAX_ARRAY=1000
CAMPAIGNS=('a','b');SECTORS=('free','power');LOOPS=tuple(range(3,ORDER+1))
GROUPS=[(c,s,L)for c in CAMPAIGNS for s in SECTORS for L in LOOPS]
RATES={'a':'.8','b':'.7'};NET_BITS={'a':52,'b':60}
EFFICIENCY=0.9
PILOT_MIN_POINTS=4096;DEFAULT_REPLICATES=8
# MERGE_PHASE2_ROWS_PER_S below: 0.9 x J-PROF-1's clean 55,105-55,975 rows/s (a planning estimate, kept when R5b's lane
# defaults were reverted: J-OPT-R5b 54681216 measured x1.019 < 1.03).
TASK_SECONDS=60.;MAX_TASK_SECONDS=120.;MIN_CHUNK=256;INDEX_HOURS=1.5;BLOCK_SECONDS=900.;DEFAULT_THREADS=16;BOOTSTRAP_CHUNK=512
MAX_TASKS=5*10**7;MAX_CHECKPOINTS=2*10**5;PLAN_TASKS_IN_JOB=10**6
FILE_BUDGET=300000;PARTNER_FILE_RESERVE=300000   # H7E's joint Lustre file budget, this session's share and C62d's (D.7)
PROMOTED_SCRATCH_BYTES=4*2**20;BASE_PEAK_BYTES=2**29   # est_peak_bytes = max block kernel bytes + threads x 4 MB + 0.5 GB
# Merge projection (D.7, D.13): conservative planning values until J-VAL-3 measures them (docs/PERFORMANCE.md).
MERGE_PHASE1_ROWS_PER_S=4000.;MERGE_PHASE2_ROWS_PER_S=50000.;MERGE_FAN_IN=64;MERGE_MAX_HOURS=12.;MERGE_ROW_BYTES=900
MERGE_SCRATCH_BYTES=10**12   # [I] node-local /scratch of an Expanse node (C8_MERGE_SCRATCH_BYTES overrides)
PLAN_ROLES=('campaign','cost_sweep','cost_refresh','flag_check','validation')
NON_MEASURED_ROLES=('cost_sweep','cost_refresh','flag_check','validation')
CAMPAIGN_ROLES=('test','pilot_subset','pilot_full','production')
MP_CHECK=('on','off','stride16')
SYNTHETIC_LABEL='synthetic (test fixture; not a measurement)'
PRELIMINARY='preliminary_proxy (worst-case NNLS tier law of the RECON at q = mp = 1, x3; not a measurement)'
TAIL_K=16;MP_BINS=18
# tail_sum is the exact Decimal sum of the rows' tail_sum strings (C.3): no rounding, an Inexact signal is an error.
TAIL_SUM_CONTEXT=decimal.Context(prec=2000,traps=[decimal.Inexact,decimal.InvalidOperation])
PREFIX_RULE=('jet_i = (total/P) * sum of jet_i over the graph-replicate\'s tasks with end <= P (50-digit Decimal; total/P an exact power '
             'of two): the mean over the first P points on the full-stream scale; tails as graph_tails.csv over the same tasks')
C7_MESSAGE=('{d} was planned by the C7(3) tools (manifest schema {s}); LRI_C8_D3_HPC does not run, merge or assemble it: use a checkout '
            'of LRI_C7_D3_HPC@a6ce987, whose tool hashes the plan pins')
D2_MESSAGE=('{d} is a dimension-2 campaign (manifest schema {s}, C62d\'s LRI_C8_D2_HPC); this is the d=3 package')
# Base seeds used with the C7(3) package (a6ce987 production.py USED_BASE_SEEDS): refused by every C8(3) plan (HD6).
C7_USED_BASE_SEEDS={4805754955154533039:'C7(3) run1 (symmetry 2026-09-30)',3272672730315656627:'C7(3) pilot 566376',3867060233378731385:'C7(3) thread check 566376',
                    8885400701634497064:'C7(2) production',326694507229394458:'C7(2) pilot',2026093003:'delivered README/HPC example',481771:'delivered HPC example',
                    7611824:'delivered tests/workflow.py',816613:'delivered tests/staging.py'}
STOP_SIGNALS=(signal.SIGTERM,signal.SIGINT,signal.SIGHUP)

def np_():
    import numpy
    return numpy

def dbopen(path:Path,readonly=False):
    """SQLite. Read-only opens of the frozen, hash-checked task databases use an escaped file: URI with mode=ro and
    immutable=1, so no rollback, WAL or lock file activity happens on the shared filesystem (D.8, A-ORC-14)."""
    if readonly:c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    else:c=sqlite3.connect(str(path))
    c.execute('PRAGMA cache_size=-8192');c.execute('PRAGMA temp_store=FILE');return c

def group_name(c:str,s:str,L:int)->str:return f'{c}_{s}_L{L}'
def block_name(shard:int,part:int)->str:return f's{shard:06d}_p{part:06d}'
def stratum_of(sector:str,L:int,primitive:bool)->str:
    """Design strata (E.5): free L3..L8, the free L8 primitives (HD5), power L3..L8."""
    return 'free_L8_primitive'if (sector=='free'and L==8 and primitive)else f'{sector}_L{L}'
def hms(seconds)->str:
    d,s=divmod(int(math.ceil(seconds)),86400);return (f'{d}-'if d else'')+time.strftime('%H:%M:%S',time.gmtime(s))

# ---------------------------------------------------------------- Sobol nets (A-L5; the three-way check at every C8 shape)
def reachable_columns(max_count:int)->int:
    """Direction columns a stratum of max_count points can reach: points 0..n-1 use columns 0..ceil(log2 n)-1."""
    return 0 if max_count<=1 else (max_count-1).bit_length()

def gray_states(sv,shift,k:int):
    """States of points 0..2^k-1 (shape (2^k, dim)) as the native Net computes them: shift XOR the direction columns of
    the set bits of n ^ (n >> 1)."""
    np=np_();sv=np.asarray(sv,dtype=np.uint64);st=np.empty((1<<k,sv.shape[0]),dtype=np.uint64);st[0]=np.asarray(shift,dtype=np.uint64)
    for j in range(k):
        h=1<<j;st[h:2*h]=st[h-1::-1]^sv[:,j][None,:]
    return st

def gf2_rank(vectors)->int:
    basis={}
    for v in vectors:
        v=int(v)
        while v:
            top=v.bit_length()-1
            if top not in basis:basis[top]=v;break
            v^=basis[top]
    return len(basis)

def make_net(path:Path,B:int,dim:int,bits:int,seed:int,max_count:int|None=None)->dict:
    """Export B independently scrambled Sobol direction matrices (the digital shift is the worker's) and check every
    column a stratum of max_count points can reach (all bits when None) three ways (D.16): (a) the public API
    random_base2 points equal the exported Gray-code states (columns 0..min(m,16)-1); (b) a fresh identically seeded
    engine read back from the written file has the same direction integers and shift; (c) SciPy-independent: in every
    dimension the reachable direction integers are nonzero, below 2^bits and linearly independent over GF(2)."""
    np=np_()
    from scipy.stats import qmc
    import scipy
    m=bits if max_count is None else reachable_columns(max_count)
    if m>bits:raise ValueError('Sobol period exceeded')
    k=min(m,16);rng=np.random.default_rng(seed);seeds=[int(rng.integers(1,2**32-1))for _ in range(B)];shifts=[]
    with Path(path).open('xb')as f:
        f.write(struct.pack('<III',B,dim,bits))
        for s in seeds:
            engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s);sv=engine._sv.copy();shift=engine._shift.copy()
            pub=engine.random_base2(k)
            if pub.shape!=(1<<k,dim)or not np.array_equal(gray_states(sv,shift,k).astype(np.float64)/2**bits,pub):
                raise RuntimeError(f'Sobol export failed the public-API comparison (columns 0..{k-1})')
            shifts.append(shift);f.write(sv.astype('<u8').tobytes())
    raw=Path(path).read_bytes()
    if struct.unpack('<III',raw[:12])!=(B,dim,bits)or len(raw)!=12+B*dim*bits*8:raise RuntimeError('Sobol export has the wrong size')
    for b,s in enumerate(seeds):
        sv=np.frombuffer(raw,dtype='<u8',count=dim*bits,offset=12+b*dim*bits*8).reshape(dim,bits)
        fresh=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s)
        if not np.array_equal(sv[:,:m],np.asarray(fresh._sv,dtype=np.uint64)[:,:m])or not np.array_equal(np.asarray(shifts[b],dtype=np.uint64),np.asarray(fresh._shift,dtype=np.uint64)):
            raise RuntimeError(f'Sobol export differs from a fresh identically seeded engine (columns 0..{m-1})')
        for d,row in enumerate(sv):
            cols=[int(x)for x in row[:m]]
            if any(c==0 or c>=1<<bits for c in cols):raise RuntimeError(f'Sobol direction integer zero or out of range (dimension {d})')
            if gf2_rank(cols)!=m:raise RuntimeError(f'Sobol direction columns 0..{m-1} of dimension {d} are linearly dependent over GF(2)')
    return {'scipy':scipy.__version__,'seed':seed,'B':B,'dim':dim,'bits':bits,'sha256':digest(path),'columns_checked':m,
            'public_API_points_checked':(1<<k)*B,'checks':['public_api','fresh_engine','gf2_structure']}

# ---------------------------------------------------------------- seeds (HD6)
def derive_seeds(seed:int,campaign:str,sector:str,L:int)->dict:
    """Native (digital-shift) and net seeds of one group: the SHA-256 of 'c8-d3|<seed>|<campaign>|<sector>|<L>|<role>',
    role native or net (first 8 bytes, little endian, mod 2^63)."""
    if campaign not in CAMPAIGNS or sector not in SECTORS:raise ValueError('unknown campaign or sector')
    h=lambda role:int.from_bytes(hashlib.sha256(f'c8-d3|{seed}|{campaign}|{sector}|{L}|{role}'.encode()).digest()[:8],'little')%(2**63)
    return {'native':h('native'),'net':h('net')}

def seed_registry()->dict:
    """HD6's registry of used seeds: C7(3)'s USED_BASE_SEEDS, the archived records' seeds and run1's 20 group native and
    net seeds (tests/fixtures/run1_groups.json, copied from run1's group configs)."""
    bases=dict(C7_USED_BASE_SEEDS);derived={}
    for f in sorted((ROOT/'reference/records').glob('*/config.json')):
        try:s=load(f).get('seed')
        except (OSError,ValueError):continue
        if type(s)is int:bases.setdefault(s,f'archived record {f.parent.name}')
    fx=ROOT/'tests/fixtures/run1_groups.json'
    if fx.exists():
        d=load(fx);bases.setdefault(int(d['base_seed']),'C7(3) run1 base seed')
        for name,g in d['groups'].items():
            derived[int(g['seed'])]=f'C7(3) run1 group {name} native seed';derived[int(g['net']['seed'])]=f'C7(3) run1 group {name} net seed'
    return {'bases':bases,'derived':derived}

def symmetry_site()->bool:
    """C8_SITE=symmetry or a symmetry host (a BeeGFS mount at /mnt/beegfs; tools/ledger.py host_sites), whatever C8_SITE says."""
    if os.environ.get('C8_SITE')=='symmetry':return True
    import ledger
    return 'symmetry'in ledger.host_sites(os.environ)

def read_seed_file(path:Path,exclude_source:str|None=None)->dict:
    """{seed: source} from a forbidden-seed file: tools/seeds.py's log ($C8_SEEDS, schema c8-d3-seeds-1), a design
    bundle's forbidden list, or a plain JSON list of integers. exclude_source: the log entries of that source are left out
    (a campaign's own reservation is no forbidden seed for its retry, S2-002); another source's entry of the same seed
    still forbids it."""
    doc=json.loads(Path(path).read_bytes())
    items=doc.get('seeds')if isinstance(doc,dict)else doc
    if not isinstance(items,list):raise ValueError(f'{path}: not a seed list (tools/seeds.py log or a JSON list of integers)')
    out={}
    for x in items:
        s=x.get('seed')if isinstance(x,dict)else x
        if isinstance(s,bool)or not isinstance(s,int):raise ValueError(f'{path}: seed entry {x!r} is not an integer')
        if exclude_source is not None and isinstance(x,dict)and x.get('source')==exclude_source:continue
        out[s]=f'{path} ({x.get("source")or x.get("label")or"listed"})'if isinstance(x,dict)else str(path)
    return out

def seed_refusal(seed:int,forbidden:dict)->str|None:
    """Why `seed` may not be used (HD6): it is a registry base seed or a forbidden seed, it equals a derived seed of the
    registry or of a forbidden base, or one of its own C8 group seeds equals any of them."""
    r=seed_registry()
    if seed in r['bases']:return f'seed {seed} is a known used base seed ({r["bases"][seed]})'
    if seed in forbidden:return f'seed {seed} is a forbidden seed ({forbidden[seed]})'
    listed=dict(r['derived'])
    for b,src in forbidden.items():
        for c,s,L in GROUPS:x=derive_seeds(b,c,s,L);listed[x['native']]=src;listed[x['net']]=src
    if seed in listed:return f'seed {seed} equals a derived group seed of {listed[seed]}'
    every={**listed,**r['bases'],**forbidden}
    for c,s,L in GROUPS:
        x=derive_seeds(seed,c,s,L)
        for role in('native','net'):
            if x[role]in every:return f'group {group_name(c,s,L)} would reuse the {role} seed of {every[x[role]]}'
    return None

# ---------------------------------------------------------------- inputs
class Inputs:
    """An inputs directory (the package's inputs/, or a test fixture under C8_INPUTS) and its manifest."""
    def __init__(self,d:Path,m:dict):self.dir=Path(d);self.m=m
    @property
    def rel(self)->str:
        try:return self.dir.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:return str(self.dir.resolve())
    def where(self,name:str)->Path:return self.dir/name
    def sha(self,name:str)->str:return self.m['sha256'][name]
    def pack(self,sector:str,L:int)->Path:return self.dir/f'packs/{sector}_L{L}.pack'

def inputs_from_record(rel:str)->Path:return Path(rel)if os.path.isabs(rel)else ROOT/rel
def load_inventory(I:Inputs)->dict:return load(I.where('inventory.json'))
INSPECT=('products','segments','addends','numerators','kernel_bytes','fmax')
def op_count(row:dict)->int:return int(row['products'])+int(row['addends'])

# ---------------------------------------------------------------- cost bases (D.5, HD11)
COST_KEY=re.compile(r'(a|b):(free|power):[2-8]:[0-9]+')
GROUP_KEY=re.compile(r'(a|b):(free|power):[2-8]')
POOLED_KEY=re.compile(r'(free|power):[2-8]:[0-9]+')

def norm_cpu(s)->str:return ' '.join(str(s or'').split())

def read_cost_model(path:Path,backend:str)->tuple[dict,bytes]:
    """A measured c8-d3-cost-model-1 of this package (make_cost_model.py), validated in full: schema, dimension 3,
    order 8, backend, measured (never the synthetic fixture or tools/bootstrap_proxy.json), rates identity default, and
    campaign:sector:L:graph keys (C62d's R05; pooled keys refused) of positive finite seconds per point."""
    data=Path(path).read_bytes()
    try:m=json.loads(data)
    except ValueError as e:raise ValueError(f'cannot read cost model {path}: {e}')
    if not isinstance(m,dict):raise ValueError(f'{path} is not a cost model')
    if m.get('schema')==BOOT_SCHEMA:raise ValueError(f'{path} is tools/bootstrap_proxy.json, a preliminary proxy: never a cost model (D.5)')
    if m.get('synthetic')or m.get('label')==SYNTHETIC_LABEL:raise ValueError(f'{path} is the synthetic test fixture ({SYNTHETIC_LABEL}): only --plan-role validation admits it (D.5, HC1)')
    if m.get('schema')!=COST_SCHEMA or m.get('dimension')!=3 or m.get('order')!=ORDER or m.get('measured')is not True:
        raise ValueError(f'{path} is not a measured {COST_SCHEMA} cost model of this package (dimension 3, order 8)')
    if m.get('backend')!=backend:raise ValueError(f'cost model backend {m.get("backend")!r} differs from --backend {backend}')
    if m.get('rates_identity','default')!='default':raise ValueError(f'cost model rates identity {m.get("rates_identity")!r} is not the default (.8/.7)')
    c=m.get('seconds_per_point')
    if not isinstance(c,dict)or not c:raise ValueError(f'cost model {path} has no seconds_per_point entries')
    for k,v in c.items():
        if isinstance(k,str)and POOLED_KEY.fullmatch(k):raise ValueError(f'cost model key {k!r} is pooled over the campaigns; keys are campaign:sector:L:graph (R05)')
        if not isinstance(k,str)or not COST_KEY.fullmatch(k):raise ValueError(f'cost model key {k!r} is not campaign:sector:L:graph')
        if isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)or v<=0:raise ValueError(f'cost model entry {k} = {v!r} is not a positive finite number of seconds')
    return m,data

def identity_problems(model:dict,exe_sha:str,cpu:str,mp_check:str)->dict:
    """HD11's identity fields of a measured model against a plan: executable sha256, CPU model, MP self-check mode."""
    out={}
    if model.get('executable_sha256')!=exe_sha:out['executable_sha256']=(model.get('executable_sha256'),exe_sha)
    if norm_cpu(model.get('cpu_model'))!=norm_cpu(cpu):out['cpu_model']=(model.get('cpu_model'),cpu)
    if model.get('mp_check')!=mp_check and not (model.get('mp_check_overhead')or{}).get(mp_check):out['mp_check']=(model.get('mp_check'),mp_check)
    return out

def mp_factor(model:dict,mp_check:str)->float:
    """1 when the model was measured in the plan's MP self-check mode; else the mode's measured overhead factor (P1)."""
    if model.get('mp_check')==mp_check:return 1.0
    return float(model['mp_check_overhead'][mp_check])

def read_synthetic(path:Path)->tuple[dict,bytes]:
    data=Path(path).read_bytes();m=json.loads(data)
    if not(isinstance(m,dict)and m.get('synthetic')is True and m.get('label')==SYNTHETIC_LABEL):raise ValueError(f'{path} is not the labelled synthetic fixture')
    r=m.get('seconds_per_point_by_group')
    if not isinstance(r,dict)or not r or any(not GROUP_KEY.fullmatch(k)or not(isinstance(v,(int,float))and v>0)for k,v in r.items()):
        raise ValueError(f'{path}: seconds_per_point_by_group must map campaign:sector:L to positive seconds')
    return m,data

def synthetic_seconds(m:dict,c:str,s:str,L:int,g:int)->float:
    k=f'{c}:{s}:{L}';key=f'{k}:{g}'
    if key in (m.get('seconds_per_point')or{}):return float(m['seconds_per_point'][key])
    if k not in m['seconds_per_point_by_group']:raise ValueError(f'the synthetic fixture has no rate for group {k}')
    return float(m['seconds_per_point_by_group'][k])

def load_bootstrap_proxy()->dict:
    p=ROOT/'tools/bootstrap_proxy.json';doc=load(p)
    if doc.get('schema')!=BOOT_SCHEMA or doc.get('label')!=PRELIMINARY:raise ValueError(f'{p} is not a {BOOT_SCHEMA} file')
    return doc

def proxy_seconds(doc:dict,A:int)->float:
    c=doc['coefficients_seconds']
    return doc['factor']*(c['c0']+c['a_ld']*A+c['q0']+c['a_q']*A+c['mp0']+c['a_mp']*A)

# ---------------------------------------------------------------- design bundles (E.5) and selection files (D.3)
def read_bundle(bundle:Path)->dict:
    """A frozen design bundle (design.py freeze, H6, or tools/design_fallback.py): design_meta.json (its sha256 is the
    bundle identity), design.json and counts/<campaign>_<sector>_L<L>.txt, each verified against design_meta.json.
    A provisional bundle (no counts, s or r) is refused by every plan, test-only included (R14, R19)."""
    bundle=Path(bundle).resolve();mb=(bundle/'design_meta.json').read_bytes();meta=json.loads(mb)
    if meta.get('schema')!=DESIGN_SCHEMA:raise ValueError(f'{bundle} is not a {DESIGN_SCHEMA} design bundle')
    if meta.get('provisional')or not meta.get('counts_sha256')or not meta.get('design_sha256'):
        raise ValueError(f'{bundle} is a provisional bundle: it carries no counts, s or r and is no allocation source in any plan (R14, R19). '
                         f'First measure under it (the measurement campaign {meta.get("measurement_campaign")or "named in its design_meta.json"}), then make a '
                         'fresh bundle with a freeze of that campaign')
    d=read_verified(bundle/'design.json',meta['design_sha256'])
    if not isinstance(d.get('strata'),dict)or not isinstance(d.get('replicates'),dict)or any('s'not in v for v in d['strata'].values()):
        raise ValueError(f'{bundle}: design.json has no s per stratum or no replicates (a provisional bundle is refused, R19)')
    counts={}
    for name,h in meta['counts_sha256'].items():
        data=(bundle/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=h:raise ValueError(f'{bundle/name} differs from the digest in design_meta.json')
        mm=re.fullmatch(r'counts/([ab])_(free|power)_L([3-8])\.txt',name)
        if not mm:raise ValueError(f'{bundle}: unexpected counts file {name}')
        counts[(mm.group(1),mm.group(2),int(mm.group(3)))]={int(a):int(b)for a,b in (ln.split()for ln in data.decode().splitlines()if ln.strip())}
    if set(counts)!=set(GROUPS):raise ValueError(f'{bundle}: counts files for {len(counts)} groups, need all 24')
    return {'path':bundle,'meta':meta,'meta_sha256':hashlib.sha256(mb).hexdigest(),'design':d,'counts':counts}

def read_selection(path:Path,im_sha:str,inv:dict,test_only:bool,min_chunk:int)->tuple[dict,bytes]:
    """A selection file (schema c8-d3-selection-1; D.3), checked before anything is created. An empty selection
    ("groups": {} with a non-null empty_reason) is refused with 65."""
    data=Path(path).read_bytes()
    try:doc=json.loads(data)
    except ValueError as e:raise ValueError(f'selection file {path} is not JSON: {e}')
    if not isinstance(doc,dict)or doc.get('schema')!=SELECTION_SCHEMA:raise ValueError(f'{path} is not a {SELECTION_SCHEMA} selection file')
    if doc.get('inputs_manifest_sha256')!=im_sha:raise ValueError(f'selection file {path} was made for another inputs manifest')
    g=doc.get('groups')
    if not isinstance(g,dict):raise ValueError(f'selection file {path} has no groups table')
    if not g:
        if doc.get('empty_reason'):raise Refuse(65,f'empty selection: nothing to plan ({path}: {doc["empty_reason"]}); the pilot runbook never plans an empty PC (D.3, R01)')
        raise ValueError(f'selection file {path} has no group and no empty_reason')
    if doc.get('role')not in('stage_a','confirm')and not test_only:raise ValueError(f'a non-test --graphs plan needs a selection of role stage_a or confirm (got {doc.get("role")!r})')
    if doc.get('role')=='confirm':   # the PC cap (E.8; S3-001): a confirm selection without its cap record, or over it, is refused
        c=doc.get('cap');ks=('pf_l8_seconds','fraction','cap_seconds','used_seconds')
        if not isinstance(c,dict)or any(isinstance(c.get(k),bool)or not isinstance(c.get(k),(int,float))or not math.isfinite(c[k])or c[k]<0 for k in ks)or not 0<c['fraction']<=0.25:
            raise ValueError(f'confirm selection {path} carries no valid PC cap record ({", ".join(ks)}; fraction at most 0.25, E.8)')
        if c['cap_seconds']>c['fraction']*c['pf_l8_seconds']*(1+1e-12)or c['used_seconds']>c['cap_seconds']*(1+1e-12):
            raise ValueError(f'confirm selection {path} is over its recorded PC cap: {c["used_seconds"]:.6g} s used of {c["cap_seconds"]:.6g} s '
                             f'({c["fraction"]:g} of PF\'s L8 cost {c["pf_l8_seconds"]:.6g} s; E.8)')
    for key,rows in g.items():
        mm=re.fullmatch(r'(free|power):([3-8])',str(key))
        if not mm:raise ValueError(f'selection key {key!r} is not sector:L')
        s,L=mm.group(1),int(mm.group(2));ids={r['id']for r in inv[s].get(str(L),[])}
        if not isinstance(rows,list)or not rows:raise ValueError(f'selection key {key} holds no graph (no empty group is planned)')
        seen=set()
        for r in rows:
            gid=r.get('id')if isinstance(r,dict)else None
            if not isinstance(gid,int)or gid not in ids:raise ValueError(f'selection {key}: graph {gid!r} is not in the inventory'+(' (L8: the to-integrate set of selection.json)'if L==8 else''))
            if gid in seen:raise ValueError(f'selection {key}: graph {gid} appears twice')
            seen.add(gid);P=r.get('points')
            if not isinstance(P,int)or not pow2(P)or (P<PILOT_MIN_POINTS and not test_only):raise ValueError(f'selection {key} graph {gid}: points {P!r} must be a power of two >= {PILOT_MIN_POINTS}')
            nest=r.get('nest')or[]
            if not isinstance(nest,list)or any(not isinstance(b,int)or not pow2(b)or b<min_chunk or b>=P or P%b for b in nest)or nest!=sorted(set(nest)):
                raise ValueError(f'selection {key} graph {gid}: nest {nest!r} must be powers of two, strictly increasing, >= --min-chunk {min_chunk}, below and dividing {P}')
    return doc,data

# ---------------------------------------------------------------- executables (C.2, C.5, HD9)
def exe_for(backend:str,numerics:str='exact')->Path:
    if numerics!='exact':
        if backend!='gmp':raise ValueError('opt-in numerics profiles exist for the gmp backend only')
        return ROOT/'bin'/f'c8d3_gmp_{numerics}'
    return ROOT/'bin'/('c8d3_gmp'if backend=='gmp'else'c8d3_decimal')

def read_buildinfo(exe:Path):
    bi=exe.with_name(exe.name+'.buildinfo.json')
    if not bi.exists():print(f'warning: no build record {bi.name}; rebuild with make to record compiler, flags and libraries',file=sys.stderr);return None
    rec=load(bi)
    if rec.get('sha256')not in(None,digest(exe)):raise ValueError(f'{bi} describes a different executable than {exe}; rebuild (make)')
    return rec

def describe(exe:Path,numerics:str,buildinfo=None)->dict:
    """--describe of a production worker (C.2): schema c8-d3-build-1, dimension 3, order 8 supported, the plan's
    numerics, not a diagnostic or self-test build (C.5, C.7), and a GMP runtime equal to its build record (HD9)."""
    if not exe.exists():raise FileNotFoundError(f'Build the executable first (make): {exe}')
    try:b=json.loads(subprocess.run([str(exe),'--describe'],capture_output=True,text=True,timeout=120,check=True).stdout)
    except (OSError,subprocess.SubprocessError,ValueError)as e:raise ValueError(f'{exe} --describe failed ({e})')
    if b.get('schema')!=BUILD_SCHEMA or b.get('dimension')!=3 or ORDER not in (b.get('orders')or[]):raise ValueError(f'{exe} is not a C8(3) worker (--describe: {b.get("schema")}, orders {b.get("orders")})')
    if b.get('diagnostic')or b.get('unguarded_index_selftest'):raise ValueError(f'{exe} is a diagnostic or self-test build; plan and run accept production builds only (C.5, C.7)')
    if b.get('numerics','exact')!=numerics:raise ValueError(f'{exe} reports numerics {b.get("numerics")!r}, the plan asks for {numerics!r}')
    g=b.get('gmp')or{}
    if b.get('mp_backend')=='gmp350':
        if g.get('applicable')is not True:raise ValueError(f'{exe}: a GMP worker without its runtime gmp block (--describe gmp: {g!r}; A-KER-3)')
    elif g.get('applicable')is not False:raise ValueError(f'{exe}: a {b.get("mp_backend")} worker whose gmp.applicable is not false ({g!r}; A-KER-3)')
    rec=None
    if buildinfo:
        rec=buildinfo.get('gmp')if isinstance(buildinfo.get('gmp'),dict)else(buildinfo.get('describe')or{}).get('gmp')   # tools/buildinfo.py keeps it under describe
    if g.get('applicable')and isinstance(rec,dict):
        for k in ('runtime_version','library'):
            if rec.get(k)is not None and g.get(k)!=rec.get(k):raise ValueError(f'{exe}: runtime GMP {k} {g.get(k)!r} differs from its build record {rec.get(k)!r} (HD9, A-KER-3)')
    return b

def self_test(exe:Path,I:Inputs,inv:dict,mp_check:str)->None:
    """Run the executable on one tiny order-8 task before its hash is frozen (a foreign or stale binary fails here)."""
    advice=f'the executable {exe} does not run on this machine; rebuild it here (make clean && make)'
    row=inv['free']['3'][0]
    with tempfile.TemporaryDirectory(prefix='c8d3_selftest_')as td:
        td=Path(td);stage_members(td/'graphs',I,'free',3,[row['id']],{row['id']:row});make_net(td/'net.bin',2,11,52,20261001)
        (td/'tasks.txt').write_text(f'{TASK_MAGIC} {ORDER} 3 1\n0 0 {row["id"]} 0 4 4\n')
        cmd=[str(exe),str(td/'graphs'),str(I.where(GAMMA)),str(td/'net.bin'),str(td/'tasks.txt'),str(td/'out.json'),'1','0','.8','1','compensated','-','--mp-check',mp_check]
        try:cp=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        except (OSError,subprocess.SubprocessError)as e:raise RuntimeError(f'Self-test failed ({e}): {advice}')from e
        if cp.returncode:raise RuntimeError(f'Self-test failed (exit {cp.returncode}: {(cp.stderr or cp.stdout)[-2000:].strip()}): {advice}')
        try:n=json.loads((td/'out.json').read_text());good=n['schema']==NATIVE_SCHEMA and n['order']==ORDER and n['L']==3 and len(n['rows'])==1 and all(D(v).is_finite()for v in n['rows'][0]['values'])
        except Exception as e:raise RuntimeError(f'Self-test produced unreadable output ({e}): {advice}')from e
        if not good:raise RuntimeError('Self-test produced invalid output: '+advice)

def stage_members(dest:Path,I:Inputs,sector:str,L:int,graphs,inventory:dict)->Path:
    """Copy only the given graph members out of the kernel pack, each read exactly (common.read_member: os.pread, no
    Python buffer; F12) and verified against its inventory sha256 (D.15)."""
    out=Path(dest)/f'L{L}';out.mkdir(parents=True,exist_ok=True)
    fd=os.open(I.pack(sector,L),os.O_RDONLY)
    try:
        for gi in sorted(set(graphs)):
            row=inventory[gi];data=read_member(fd,row['offset'],row['length'])
            if len(data)!=row['length']or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError(f'Packed graph content mismatch: {sector} L{L} G{gi}')
            (out/f'G{gi}.txt').write_bytes(data)
    finally:os.close(fd)
    return Path(dest)

# ---------------------------------------------------------------- blocks (D.6, R10)
def cut_blocks(seconds,N:int,S:float,w:int,n:int|None=None)->dict:
    """The frozen checkpoint blocks of one shard, its tasks in pos order (a pure function; D.6, R10). A block holds at
    most N tasks and at most S seconds of predicted work at lane width w: W(B) = sum s_t / w. Fullness
    phi(B) = max(|B|/N, W(B)/S); valid when phi <= 1. seconds=None (the bootstrap basis): phi = |B|/N.
    1. greedy in pos order until the next task would make the block invalid;
    2. last-two rebalance when there are k >= 2 blocks and phi(B_k) < 1/2: B_{k-1} u B_k is re-cut at the one boundary
       that leaves both valid and maximizes min(phi'), ties to the larger B'_{k-1} (the greedy cut is a candidate);
    3. a block still below 1/2 is kept and recorded as small_block.
    Returns {'bounds': [start of each block..., n], 'phi': [...], 'wall': [...] (None under bootstrap), 'small_block'}."""
    n=len(seconds)if seconds is not None else int(n)
    if N<1 or (seconds is not None and (not S>0 or w<1)):raise ValueError('cut_blocks: N >= 1, S > 0 and w >= 1 are required')
    pref=None
    if seconds is not None:
        pref=[0.0]*(n+1);acc=0.0
        for i,x in enumerate(seconds):acc+=float(x);pref[i+1]=acc
    eps=1e-12
    def W(i,j):return (pref[j]-pref[i])/w if pref is not None else None
    def phi(i,j):return max((j-i)/N,W(i,j)/S)if pref is not None else (j-i)/N
    def valid(i,j):return j-i<=N and (pref is None or W(i,j)<=S*(1+eps))
    if seconds is not None:
        for i,x in enumerate(seconds):
            if x/w>S/2*(1+eps):raise ValueError(f'task {i}: {x:.6g} s / {w} threads > --block-seconds/2 = {S/2:g} s')
    bounds=[0];i=0
    while i<n:
        j=i+1
        while j<n and valid(i,j+1):j+=1
        bounds.append(j);i=j
    small=None;k=len(bounds)-1
    if k>=2 and phi(bounds[-2],n)<0.5:
        i0=bounds[-3];best=None
        for c in range(i0+1,n):
            if valid(i0,c)and valid(c,n):
                v=min(phi(i0,c),phi(c,n))
                if best is None or v>best[0]+eps or (abs(v-best[0])<=eps and c>best[1]):best=(v,c)
        if best is not None:bounds[-2]=best[1]
        for b in (k-2,k-1):
            p=phi(bounds[b],bounds[b+1])
            if p<0.5:small={'block':b,'phi':p,'reason':'no valid cut gives both blocks half the target'};break
    return {'bounds':bounds,'phi':[phi(bounds[b],bounds[b+1])for b in range(len(bounds)-1)],
            'wall':[W(bounds[b],bounds[b+1])for b in range(len(bounds)-1)]if pref is not None else None,'small_block':small}

def merge_passes(runs:int,F:int)->int:
    """Passes of the external merge of `runs` sorted runs with fan-in F: ceil(log_F(runs)), at least 1 (integers)."""
    p,cap=1,F
    while cap<runs:p+=1;cap*=F
    return p

def parse_test_graphs(v):
    if v is None:return None
    if v=='all':return 'all'
    if not str(v).isdigit()or int(v)<1:raise ValueError('--test-graphs takes a positive integer or "all"')
    return int(v)

def parse_group_replicates(items)->dict:
    out={}
    for it in items or[]:
        mm=re.fullmatch(r'(free|power):([3-8])=([0-9]+)',it)
        if not mm or int(mm.group(3))<2:raise ValueError(f'--group-replicates {it!r} must be SECTOR:L=R with R >= 2 (e.g. power:8=16)')
        out[(mm.group(1),int(mm.group(2)))]=int(mm.group(3))
    return out

def select_graphs(rows:list,n,mode:str,cost_of,L:int)->set:
    """--test-graphs N|all: 'cheapest' takes the N cheapest by inventory cost; 'stratified' takes N/2 cheapest and N/2
    heaviest by measured (or proxy) cost, plus every L7 primitive and at least 16 L8 primitives (8 cheapest, 8
    heaviest); deterministic (D.2, A-ORC-2)."""
    if n=='all':return {r['id']for r in rows}
    if mode=='cheapest':return {r['id']for r in sorted(rows,key=lambda r:(r['cost'],r['id']))[:n]}
    by=sorted(rows,key=lambda r:(cost_of(r),r['id']));lo=n//2;hi=n-lo
    out={r['id']for r in by[:lo]}|{r['id']for r in (by[len(by)-hi:]if hi else[])}
    prim=[r for r in by if r.get('primitive')]
    if L==7:out|={r['id']for r in prim}
    if L==8:out|={r['id']for r in prim[:8]}|{r['id']for r in prim[-8:]}
    return out

def task_bounds(n:int,chunk:int,nest)->list:
    """Task intervals of one graph-replicate: multiples of chunk, cut at every nest boundary (D.3, D.5)."""
    cuts=sorted(set(range(0,n,chunk))|{b for b in (nest or())if 0<b<n}|{n})
    return list(zip(cuts[:-1],cuts[1:]))

# ---------------------------------------------------------------- the Lustre file guard (D.7)
def lfs_quota(kind:str,name:str,path:Path)->dict:
    """`lfs quota -q -<kind> <name> <path>`: {'files':used,'file_limit':limit,'kbytes':used,'kbyte_limit':limit} (69 on failure)."""
    try:cp=subprocess.run(['lfs','quota','-q',f'-{kind}',name,str(path)],capture_output=True,text=True,timeout=60)
    except (OSError,subprocess.SubprocessError)as e:raise Refuse(69,f'lfs quota -{kind} {name} failed ({e}); the file guard cannot be evaluated')
    if cp.returncode:raise Refuse(69,f'lfs quota -{kind} {name} failed (exit {cp.returncode}): {(cp.stderr or cp.stdout).strip()[-300:]}')
    toks=cp.stdout.split();nums=[]
    for t in toks:
        t=t.rstrip('*')
        if re.fullmatch(r'[0-9]+',t):nums.append(int(t))
        elif t=='-':nums.append(None)
    # kbytes quota limit grace files quota limit grace
    vals=[x for x in nums]
    if len(vals)<8:raise Refuse(69,f'lfs quota -{kind} {name}: unexpected output {cp.stdout.strip()[-200:]!r}')
    kb,kq,kl,_,f,fq,fl,_=vals[:8]
    return {'kbytes':kb,'kbyte_limit':kl or kq,'files':f,'file_limit':fl or fq}

def file_guard(projected:int,max_files:int|None,where:Path)->dict:
    """Under C8_SITE=expanse: --max-files = min(C8_FILE_BUDGET, free files of `lfs quota -u` - C8_PARTNER_FILE_RESERVE);
    prints the user and group quotas. Elsewhere only an explicit --max-files applies."""
    rec={'projected_files':projected}
    if os.environ.get('C8_SITE')=='expanse':
        budget=int(os.environ.get('C8_FILE_BUDGET',FILE_BUDGET));reserve=int(os.environ.get('C8_PARTNER_FILE_RESERVE',PARTNER_FILE_RESERVE))
        probe=where
        while not probe.exists():probe=probe.parent
        u=lfs_quota('u',os.environ.get('C8_QUOTA_USER','zzheng8'),probe);g=lfs_quota('g',os.environ.get('C8_QUOTA_GROUP','yun124'),probe)
        free=(u['file_limit']or 0)-(u['files']or 0);cap=min(budget,free-reserve)
        if max_files is not None:cap=min(cap,max_files)
        rec.update(user_quota=u,group_quota=g,file_budget=budget,partner_reserve=reserve,free_files=free,max_files=cap)
        print(f'Lustre: user files {u["files"]:,} of {u["file_limit"]:,} (free {free:,}); group kbytes {g["kbytes"]:,} of {g["kbyte_limit"]or 0:,}'
              f'{" (OVER the group limit)"if g["kbyte_limit"]and g["kbytes"]>g["kbyte_limit"]else""}; --max-files = min({budget:,}, {free:,} - {reserve:,}) = {cap:,}',file=sys.stderr)
    elif max_files is not None:rec['max_files']=max_files
    cap=rec.get('max_files')
    if cap is not None and projected>cap:raise ValueError(f'{projected:,} projected files > --max-files {cap:,} (D.7: this session\'s Lustre file budget)')
    return rec

# ---------------------------------------------------------------- planning (D.2-D.7)
def plan_scratch(a,test_only:bool)->Path:
    """Node-local scratch of the plan (D.4): $SLURM_TMPDIR, else /scratch/$USER/job_$SLURM_JOB_ID, inside a job (or
    --scratch); outside a job only a test-only plan with an explicit --scratch."""
    if a.scratch:
        if not os.environ.get('SLURM_JOB_ID')and not test_only:raise ValueError('outside a Slurm job a plan needs to be test-only with an explicit --scratch (D.4); real plans run in slurm/plan.sh')
        return Path(a.scratch).resolve()
    if not os.environ.get('SLURM_JOB_ID'):raise ValueError('outside a Slurm job plan refuses unless it is test-only with an explicit --scratch (D.4); real plans run in slurm/plan.sh')
    if os.environ.get('SLURM_TMPDIR'):return Path(os.environ['SLURM_TMPDIR'])
    return Path('/scratch')/os.environ.get('USER','')/f'job_{os.environ["SLURM_JOB_ID"]}'

def plan(a):
    """Every argument, input, seed, cap, Sobol-period, task-seconds and file-count check runs before anything is created;
    with --reserve-seed (required with --forbid-seeds-from, one of those logs: 65 otherwise) the seed is then rechecked
    and reserved in the seed log (S2-002); the campaign is built on
    node-local scratch, copied to <dir>.tmp.<host>.<pid>[.<job>] beside the target, fsynced and published with one rename
    that fails when the target exists (D.4, S2-005)."""
    out=a.directory.resolve()
    if out.exists():raise FileExistsError(f'Use a new campaign directory ({out} exists)')
    tg=parse_test_graphs(a.test_graphs);requested_test=bool(a.test_only or tg is not None)
    # HD5: exactly one allocation source; the modifiers.
    if bool(a.pilot)==(a.design is not None):raise ValueError('give exactly one allocation source: --pilot [--points P] or --design BUNDLE (HD5)')
    if a.graphs is not None:
        if not a.pilot:raise ValueError('--graphs requires --pilot (D.3a)')
        if tg is not None:raise ValueError('--graphs refuses --test-graphs (D.3a)')
    if a.points is not None and not a.pilot:raise ValueError('--points belongs to --pilot')
    P=a.points if a.points is not None else PILOT_MIN_POINTS
    if a.pilot and (not pow2(P)or (P<PILOT_MIN_POINTS and not requested_test)):raise ValueError(f'--pilot --points {P}: a power of two >= {PILOT_MIN_POINTS}, unless a test-only plan (--test-graphs) (HD5)')
    if a.replicates is not None and a.design is not None:raise ValueError('--replicates belongs to --pilot; a design bundle fixes the replicates')
    R=a.replicates if a.replicates is not None else DEFAULT_REPLICATES
    if R<2:raise ValueError('at least 2 replicates')
    greps=parse_group_replicates(a.group_replicates)
    if greps and a.design is not None:raise ValueError('--group-replicates belongs to --pilot; a design bundle fixes the replicates')
    if a.test_selection!='cheapest'and tg is None:raise ValueError('--test-selection needs --test-graphs')
    if a.threads<1 or a.max_tasks<1 or a.max_checkpoints<1:raise ValueError('invalid sizes')
    T=a.checkpoint_tasks if a.checkpoint_tasks is not None else max(16*a.threads,256)
    if not 1<=T<=100000:raise ValueError('--checkpoint-tasks must be in [1, 100000] (the native task-file limit)')
    if a.threads>T:raise ValueError(f'--threads {a.threads} exceeds --checkpoint-tasks {T}: at most {T} threads can ever be busy')
    S=a.block_seconds if a.block_seconds is not None else BLOCK_SECONDS
    if not S>0:raise ValueError('--block-seconds must be positive')
    if not 0<=a.seed<2**63:raise ValueError('seed outside [0, 2^63)')
    if a.plan_role not in PLAN_ROLES:raise ValueError(f'--plan-role must be one of {", ".join(PLAN_ROLES)}')
    if a.mp_check not in MP_CHECK:raise ValueError(f'--mp-check must be one of {", ".join(MP_CHECK)}')
    if a.numerics!='exact':
        if not a.approved_numerics_change:raise ValueError('--numerics other than exact is a numerics change: it needs --approved-numerics-change "<user ref>" (U1, A-FLAG-1)')
        if a.pilot and a.plan_role=='campaign':raise ValueError('every pilot plan refuses an opt-in numerics profile (U1, A-FLAG-1)')
    # D.5: exactly one cost basis.
    boot=a.bootstrap_chunk is not None;prior=a.prior_cost_model is not None;cm=a.cost_model is not None
    if boot+prior+cm>1:raise ValueError('one cost basis per plan: give one of --cost-model, --bootstrap-chunk and --prior-cost-model (D.5)')
    synthetic=False
    if cm:
        try:synthetic=bool(json.loads(Path(a.cost_model).read_bytes()).get('synthetic'))
        except (OSError,ValueError,AttributeError):synthetic=False
    task_s=a.task_seconds if a.task_seconds is not None else TASK_SECONDS;min_chunk=a.min_chunk if a.min_chunk is not None else MIN_CHUNK
    if not task_s>0 or not a.max_task_seconds>0 or not(min_chunk>=1 and pow2(min_chunk)):raise ValueError('invalid --task-seconds, --max-task-seconds or --min-chunk (a power of two)')
    if a.shards is not None and a.index_hours is not None:raise ValueError('give --index-hours or --shards, not both')
    if a.shards is not None and a.shards<1:raise ValueError('--shards must be positive')
    # ---- the plan's input gate (PLAN B, A-IN-4, A-ASM-1(b)): creates nothing; the plan is test-only if asked or if the inputs are incomplete
    import prepare_inputs as pi
    v=pi.plan_inputs(requested_test)
    test_only=bool(v['test_only'])
    for r in v['test_only_reasons']:print(f'test-only: {r}',file=sys.stderr)
    I=Inputs(Path(v['inputs']),v['manifest']);im_sha=v['manifest_sha256'];skipped=set(v['skipped'])
    # ---- roles (D.2, D.3a, D.5, HD11)
    role=a.plan_role
    if role in NON_MEASURED_ROLES and not test_only:raise ValueError(f'--plan-role {role} is a non-measured role: test-only plans only (HD11, D.5)')
    if boot:
        if role=='campaign':raise ValueError('--bootstrap-chunk with --plan-role campaign: a campaign plan uses the measured basis on an identity-matching model (HD11); the bootstrap basis belongs to cost_sweep, cost_refresh, flag_check and validation')
        if not test_only:raise ValueError('--bootstrap-chunk is for a test-only plan only (the first sweep, D.5)')
        if a.index_hours is not None or a.task_seconds is not None or a.min_chunk is not None:raise ValueError('--bootstrap-chunk refuses --index-hours, --task-seconds and --min-chunk, which need a time estimate (D.5)')
        if a.shards is None:raise ValueError('--bootstrap-chunk needs --shards N (no time estimate exists to size indices)')
        if not pow2(a.bootstrap_chunk):raise ValueError('--bootstrap-chunk must be a power of two')
    if synthetic:
        if role!='validation':raise ValueError(f'the synthetic fixture {a.cost_model} ({SYNTHETIC_LABEL}) is validation-only: --plan-role {role} refuses it (D.5, HC1)')
        if not test_only:raise ValueError('the synthetic fixture needs a test-only plan')
    if role=='validation':
        if a.design is not None:raise ValueError('--plan-role validation refuses --design (D.5)')
        if prior:raise ValueError('--plan-role validation refuses --prior-cost-model (D.5)')
        if cm and not synthetic:raise ValueError('--plan-role validation refuses a measured model: a test plan on an identity-matching measured model keeps role campaign (D.5, HC1)')
        if not(boot or synthetic):raise ValueError('--plan-role validation needs the bootstrap basis (--bootstrap-chunk P --shards N) or the synthetic fixture (--cost-model tests/fixtures/cost_model_synthetic.json) (D.5)')
    if role in('cost_sweep','flag_check')and not boot:raise ValueError(f'--plan-role {role} plans on the bootstrap basis (--bootstrap-chunk P --shards N) (D.5)')
    if prior:
        if role!='cost_refresh':raise ValueError('--prior-cost-model is the prior-model basis of --plan-role cost_refresh only (D.5, D.14)')
        if not test_only:raise ValueError('the prior-model basis needs a test-only plan')
        if not a.pilot or a.design is not None or a.graphs is not None:raise ValueError('the prior-model basis needs the sweep\'s allocation --pilot --points P --replicates R (never --design or --graphs) (D.5)')
        if P>512 or R>2:raise ValueError(f'the prior-model basis admits only the sweep\'s allocation: --points <= 512 and --replicates <= 2 (got {P}, {R}) (D.5)')
        if tg is None:raise ValueError('the prior-model basis needs --test-graphs all or a subset (D.5)')
        if not a.prior_factor>=1:raise ValueError(f'--prior-factor {a.prior_factor} is below 1 (D.5)')
    if role=='campaign'and not cm:raise ValueError('--plan-role campaign needs the measured basis: --cost-model of an identity-matching model measured on this executable (HD11); '
                                                   'the first sweep of a binary is a cost_sweep (tools/sweep.py), a changed binary\'s a cost_refresh (tools/sweep.py --refresh)')
    if role=='cost_refresh'and not(boot or prior or cm):raise ValueError('--plan-role cost_refresh needs one basis: --prior-cost-model, --bootstrap-chunk or --cost-model (D.14)')
    if not test_only and not a.forbid_seeds_from:raise ValueError('a non-test plan must pass --forbid-seeds-from $C8_SEEDS (HD6)')
    if a.forbid_seeds_from:
        # S2-002: a plan that checks its seed against a log (every non-test plan, every sweep) also reserves it in that same
        # log, durably and atomically (the reservation below, under the log's lock): refused (65) before anything is read or
        # built without --reserve-seed naming one of its --forbid-seeds-from logs. Test-only plans that check no seed (the
        # J-SMK-1 twins, prefix_check.py --real) neither check nor need to reserve.
        if a.reserve_seed is None:
            raise Refuse(65,'a plan that checks its seed (--forbid-seeds-from) must reserve it in the same log: add --reserve-seed $C8_SEEDS '
                            '(slurm/plan.sh and tools/sweep.py pass it; HD6, S2-002); nothing was planned')
        if os.path.realpath(a.reserve_seed)not in {os.path.realpath(f)for f in a.forbid_seeds_from}:
            raise Refuse(65,f'--reserve-seed {a.reserve_seed} is not one of the --forbid-seeds-from logs ({", ".join(map(str,a.forbid_seeds_from))}): the seed '
                            'is reserved in the log it was checked against (HD6, S2-002); nothing was planned')
    if a.graphs is not None:campaign_role='pilot_subset'
    elif test_only:campaign_role='test'
    elif a.pilot:campaign_role='pilot_full'
    else:campaign_role='production'
    H=a.index_hours if a.index_hours is not None else (None if a.shards is not None else INDEX_HOURS)
    if H is not None and not H>0:raise ValueError('--index-hours must be positive')
    # ---- inventory, selection, bundle, seeds
    inv=load_inventory(I);loops_present={(s,int(L))for s in SECTORS for L in inv.get(s,{})if str(L).isdigit()}
    selection=None;sel_bytes=None
    if a.graphs is not None:selection,sel_bytes=read_selection(Path(a.graphs),im_sha,inv,test_only,min_chunk)
    forbidden={};ident=str(out)   # the campaign's stable identity, its resolved directory: its own reservation never forbids its retry (S2-002)
    for f in a.forbid_seeds_from or[]:forbidden.update(read_seed_file(f,ident))
    bundle=read_bundle(a.design)if a.design is not None else None
    if bundle is not None:
        meta=bundle['meta']
        if meta.get('test_only')and not test_only:raise ValueError(f'{a.design} is a --test-only bundle: only test-only plans accept it (E.5)')
        if meta.get('inputs_manifest_sha256')!=im_sha:raise ValueError('the design bundle was frozen for another inputs manifest')
        if meta.get('numerics','exact')!=a.numerics:raise ValueError(f'the design bundle was frozen for numerics {meta.get("numerics")!r}')
        if meta.get('label')=='fallback'and not test_only and not a.approved_fallback:raise ValueError(f'{a.design} is a fallback bundle (tools/design_fallback.py): a non-test plan from it needs --approved-fallback "<user ref>" (HD16, E.5)')
        for s in meta.get('forbidden_seeds',[]):forbidden.setdefault(int(s),f'design bundle {bundle["path"]}')
    if not test_only and symmetry_site():
        # Amendment A1: symmetry keeps its own seed log; a non-test plan there must forbid at least every seed of the
        # package mirror (designs/forbidden_seeds.json, a byte copy of Expanse's $C8_SEEDS at an evidence commit), so a log
        # that started empty or missed the sync cannot let a used Expanse seed through (HD6)
        mir=ROOT/'designs'/'forbidden_seeds.json'
        if not mir.exists():raise ValueError(f'the package mirror {mir} is missing: a non-test plan on symmetry checks its forbidden seeds against it (HD6, A1)')
        gaps=sorted(set(read_seed_file(mir,ident))-set(forbidden))
        if gaps:raise ValueError(f'the forbidden seeds (--forbid-seeds-from) lack {len(gaps)} seed(s) of the package mirror {mir} (e.g. {gaps[:5]}): on symmetry '
                                 '$C8_SEEDS starts as a copy of Expanse\'s log or of the mirror (seeds.py init --from, seeds.py merge; HD6, A1)')
    why=seed_refusal(a.seed,forbidden)
    if why:raise ValueError(why+'; choose a fresh random seed (python3 -c "import secrets;print(secrets.randbits(63))")')
    # ---- the executable (C.2, HD9)
    exe=exe_for(a.backend,a.numerics);bi=read_buildinfo(exe)if exe.exists()else None;build=describe(exe,a.numerics,bi);exe_sha=digest(exe)
    host_cpu=cpu_model()
    # ---- the cost basis (D.5, HD11)
    model=None;model_bytes=None;syn=None;syn_bytes=None;prior_model=None;prior_bytes=None;bproxy=None;mpf=1.0
    if cm and not synthetic:
        model,model_bytes=read_cost_model(Path(a.cost_model),a.backend);prob=identity_problems(model,exe_sha,host_cpu,a.mp_check)
        if prob:raise ValueError('the cost model is not identity-matching (HD11): '+'; '.join(f'{k} model {x!r} vs plan {y!r}'for k,(x,y) in prob.items())+
                                 f'; model executable {model.get("executable_sha256")}, plan executable {exe_sha}. Measure this binary first: tools/sweep.py --refresh '
                                 f'{a.cost_model} (D.14)')
        mpf=mp_factor(model,a.mp_check)
        if role=='cost_refresh'and model.get('executable_sha256')!=exe_sha:raise ValueError('internal: a measured refresh needs equal executables')
    elif synthetic:syn,syn_bytes=read_synthetic(Path(a.cost_model))
    elif prior:
        try:prior_model,prior_bytes=read_cost_model(Path(a.prior_cost_model),a.backend)
        except ValueError as e:raise ValueError(f'--prior-cost-model: {e}')
        if prior_model.get('executable_sha256')==exe_sha:raise ValueError(f'the prior model {a.prior_cost_model} was measured on this executable ({exe_sha[:12]}): use the measured basis '
                                                                         '(--cost-model; tools/sweep.py --refresh chooses it) (D.5, D.14)')
        prob={k:v for k,v in identity_problems(prior_model,exe_sha,host_cpu,a.mp_check).items()if k!='executable_sha256'}
        if prob:raise ValueError('the prior model does not qualify (HD11): '+'; '.join(f'{k} model {x!r} vs plan {y!r}'for k,(x,y) in prob.items())+'; use the bootstrap basis (D.14)')
        mpf=mp_factor(prior_model,a.mp_check)
    elif boot:bproxy=load_bootstrap_proxy()
    basis='measured'if model else('synthetic'if syn else('prior_model'if prior_model else'bootstrap'))
    costs=model['seconds_per_point']if model else(prior_model['seconds_per_point']if prior_model else{})
    # ---- per group: graphs, counts, replicates, per-graph seconds and chunks (no file yet)
    sel_groups={}
    if selection is not None:
        for key,rows in selection['groups'].items():s,L=key.split(':');sel_groups[(s,int(L))]={r['id']:r for r in rows}
    G={}
    for c,s,L in GROUPS:
        name=group_name(c,s,L)
        if selection is not None and (s,L)not in sel_groups:continue   # pilot_subset: exactly the selected groups
        rows=list(inv.get(s,{}).get(str(L),[]))
        if f'packs/{s}_L{L}.pack'in skipped:rows=[]   # C8_ALLOW_NO_L8 (test-only): no pack here, so no graph
        byid={r['id']:r for r in rows}
        def unit(r,c=c,s=s,L=L):
            if model or prior_model:
                k=f'{c}:{s}:{L}:{r["id"]}'
                if k not in costs:raise ValueError(f'{name}: graph {r["id"]} has no cost-model key {k} in {a.cost_model or a.prior_cost_model}; measure it first (tools/sweep.py)')
                return float(costs[k])*mpf*(a.prior_factor if prior_model else 1.0)
            if syn:return synthetic_seconds(syn,c,s,L,r['id'])
            return None
        if selection is not None:sel=set(sel_groups[(s,L)])
        elif tg is None:sel=set(byid)
        else:
            def cost_of(r):
                try:x=unit(r)
                except ValueError:x=None
                if x is None and bproxy is not None and all(r.get(f)is not None for f in('products','addends')):x=proxy_seconds(bproxy,op_count(r))
                return x if x is not None else float(r['cost'])
            sel=select_graphs(rows,tg,a.test_selection,cost_of,L)
        for gid in sorted(sel):
            r=byid[gid];missing=[f for f in INSPECT if r.get(f)is None]
            if missing:raise ValueError(f'{I.rel}/inventory.json: {s} L{L} graph {gid} has no inspect fields ({", ".join(missing)}); `make inputs-inspect` fills them '
                                        '(PLAN B): plan refuses any selected graph without them')
        if bundle is not None:
            base=bundle['counts'][(c,s,L)];strata=bundle['design']['strata'];reps=int(bundle['design']['replicates'][f'{s}_L{L}'])
            if set(base)!={r['id']for r in rows}:raise ValueError(f'design bundle counts of {name} do not cover exactly the inventory graphs')
            counts={g:base[g]*int(strata[stratum_of(s,L,bool(byid[g].get('primitive')))]['s'])for g in sel}
            nest={};labels={}
        elif selection is not None:
            reps=greps.get((s,L),R);counts={g:int(sel_groups[(s,L)][g]['points'])for g in sel}
            nest={g:list(sel_groups[(s,L)][g].get('nest')or[])for g in sel if sel_groups[(s,L)][g].get('nest')}
            labels={g:sel_groups[(s,L)][g].get('label')for g in sel}
        else:
            reps=greps.get((s,L),R);counts={g:P for g in sel};nest={};labels={}
        if reps<2:raise ValueError(f'{name}: at least 2 replicates')
        if any(not pow2(n)for n in counts.values()):raise ValueError(f'{name}: per-graph counts must be powers of two')
        bits=NET_BITS[c]
        if counts and max(counts.values())>2**bits:raise ValueError(f'Sobol period exceeded: group {name} has a stratum of {max(counts.values())} > 2^{bits} points')
        per={};chunk={};prelim={}
        for g in sorted(counts):
            r=byid[g];n=counts[g]
            if boot:
                ch=min(a.bootstrap_chunk,n);sp=proxy_seconds(bproxy,op_count(r));prelim[g]=sp
                for lo,hi in task_bounds(n,ch,nest.get(g)):
                    if (hi-lo)*sp>a.max_task_seconds:raise ValueError(f'{name} graph {g}: a {hi-lo}-point task needs {(hi-lo)*sp:.1f} preliminary seconds > --max-task-seconds '
                                                                     f'{a.max_task_seconds:g} ({PRELIMINARY}); lower --bootstrap-chunk')
                chunk[g]=ch;per[g]=None;continue
            cg=unit(r)
            if cg is None:raise ValueError(f'{name}: no cost basis for graph {g}: give --cost-model, or plan the first sweep with --bootstrap-chunk P --shards N (D.5)')
            ch=1<<max(0,int(math.floor(math.log2(task_s/cg))))if task_s>=cg else 1
            ch=min(max(min_chunk,ch),n);per[g]=cg;chunk[g]=ch
            worst=max((hi-lo)*cg for lo,hi in task_bounds(n,ch,nest.get(g)))
            if worst>a.max_task_seconds:raise ValueError(f'{name} graph {g}: a task is predicted at {worst:.1f} s > --max-task-seconds {a.max_task_seconds:g}; '
                                                         'raise --max-task-seconds or lower --min-chunk')
        tb={g:task_bounds(counts[g],chunk[g],nest.get(g))for g in counts}
        ntasks=reps*sum(len(tb[g])for g in counts)
        secs=None if boot else reps*sum(counts[g]*per[g]for g in counts)
        psecs=reps*sum(counts[g]*prelim[g]for g in counts)if boot else None
        G[name]=dict(name=name,campaign=c,sector=s,L=L,counts=counts,nest=nest,labels=labels,reps=reps,chunk=chunk,per=per,prelim=prelim,tb=tb,byid=byid,
                     ntasks=ntasks,secs=secs,psecs=psecs,bits=bits,
                     maxtask=None if boot else max((max((hi-lo)*per[g]for lo,hi in tb[g])for g in counts),default=0.),
                     maxprelim=max((max((hi-lo)*prelim[g]for lo,hi in tb[g])for g in counts),default=0.)if boot else None)
    if selection is not None and any(not g['counts']for g in G.values()):raise ValueError('a pilot_subset plan creates no empty group')
    if selection is not None and selection.get('role')=='confirm':
        # S3-R2-001 (E.8): the PC cap holds for what this plan will run, priced as its own estimates are (its counts,
        # replicates and --group-replicates, the basis's seconds per point and the MP self-check factor), not only for the
        # selection's recorded pricing at 8 replicates
        if boot:raise ValueError('a confirm selection is planned with a cost estimate (--cost-model): its PC cap is checked against the planned cost (E.8, S3-R2-001)')
        planned=math.fsum(g['secs']for g in G.values());cap=float(selection['cap']['cap_seconds'])
        if planned>cap*(1+1e-12):raise ValueError(f'the PC plan costs {planned:.6g} s ({basis} basis, MP factor {mpf:g}, replicates '
                                                  f'{sorted({g["reps"]for g in G.values()})}) > its selection\'s cap {cap:.6g} s ({selection["cap"]["fraction"]:g} of PF\'s L8 '
                                                  f'cost, priced at {selection["cap"]["used_seconds"]:.6g} s): plan PC at the replicates it was selected for (E.8, S3-R2-001)')
    # caps decided by the task counts alone come before any task-sized structure
    for c in CAMPAIGNS:
        n=sum(g['ntasks']for g in G.values()if g['campaign']==c)
        if n>a.max_tasks:raise ValueError(f'campaign {c} has {n:,} tasks > --max-tasks {a.max_tasks:,}')
    total_tasks=sum(g['ntasks']for g in G.values())
    if total_tasks==0:raise ValueError('the plan has no work (every group is empty)')
    if total_tasks>PLAN_TASKS_IN_JOB and not os.environ.get('SLURM_JOB_ID'):raise ValueError(f'{total_tasks:,} tasks > {PLAN_TASKS_IN_JOB:,}: plan inside a job (slurm/plan.sh), never on a login node')
    for g in G.values():
        if not g['ntasks']:g['nshards']=0;continue
        if a.shards is not None:g['nshards']=min(a.shards,g['ntasks'])
        else:g['nshards']=min(g['ntasks'],max(1,math.ceil(g['secs']/(H*3600*a.threads*EFFICIENCY))))
    nckpt_lo=sum(math.ceil(g['ntasks']/T)for g in G.values()if g['ntasks'])
    if nckpt_lo>a.max_checkpoints:raise ValueError(f'at least {nckpt_lo:,} checkpoint blocks > --max-checkpoints {a.max_checkpoints:,}; raise --checkpoint-tasks')
    # the exact LPT and the frozen blocks per shard (task-sized arrays; still nothing on disk)
    for g in G.values():
        if g['ntasks']:_lpt_blocks(g,T,S,a.threads,boot,a.threads)
    nckpt=sum(sum(j['blocks']for j in g['shard_jobs'])for g in G.values()if g['ntasks'])
    if nckpt>a.max_checkpoints:raise ValueError(f'{nckpt:,} checkpoint blocks > --max-checkpoints {a.max_checkpoints:,}; raise --checkpoint-tasks')
    njobs=sum(g['nshards']for g in G.values())
    files=2*njobs+nckpt+2*njobs+2*njobs+12*len(G)+32
    print(f'projected files: {files:,} (per-index task and block files {2*njobs:,}, checkpoints {nckpt:,}, lane claims and done markers {2*njobs:,}, '
          f'attempt logs {2*njobs:,}, group files {12*len(G):,})',file=sys.stderr)
    lustre=file_guard(files,a.max_files,out.parent)
    F=MERGE_FAN_IN;merge={};scratch_cap=float(os.environ.get('C8_MERGE_SCRATCH_BYTES',MERGE_SCRATCH_BYTES))
    for g in G.values():
        if not g['ntasks']:continue
        passes=merge_passes(g['nshards'],F);sb=g['ntasks']*MERGE_ROW_BYTES*2
        merge[g['name']]={'rows':g['ntasks'],'runs':g['nshards'],'passes':passes,'scratch_bytes':sb,
                          'projected_seconds':g['ntasks']/MERGE_PHASE1_ROWS_PER_S+passes*g['ntasks']/MERGE_PHASE2_ROWS_PER_S}
    mmax=max((v['projected_seconds']for v in merge.values()),default=0.)
    # D.7/D.13 scratch peak of the merge job: phase 1 leaves every group's raw rows on scratch (one copy of all rows; a
    # shard being sorted adds at most its own rows once more), and a group in a phase-2 pass holds at most one more copy
    # of its own rows (the batch being written; _phase2 deletes each consumed batch and, after the final pass, the
    # group's runs and tables). merge.sh runs C8_MERGE_JOBS groups at once (default: the job's CPUs, 24 in Expanse's
    # default merge shape), so every group may hold its second copy at the same time: the peak is bounded by the sum over
    # groups of rows x bytes per row x 2, i.e. the sum of the per-group scratch_bytes, which the guard compares.
    speak=sum(v['scratch_bytes']for v in merge.values())
    if mmax>MERGE_MAX_HOURS*3600:raise ValueError(f'the largest group needs a projected {mmax/3600:.1f} h of merge > {MERGE_MAX_HOURS:g} h; split the campaign into batches (D.7)')
    if speak>0.8*scratch_cap:raise ValueError(f'the merge needs a projected {speak/1e9:.1f} GB of scratch (every group\'s raw rows, x 2 for the groups in a '
                                             f'pass) > 0.8 x the merge node\'s /scratch ({scratch_cap/1e9:.0f} GB) (D.7, D.13); split the campaign into batches')
    print(f'projected merge scratch: {speak/1e9:.3g} GB (rows x {MERGE_ROW_BYTES} bytes x 2, summed over groups) of {scratch_cap/1e9:.0f} GB',file=sys.stderr)
    scratch=plan_scratch(a,test_only)
    # the self-test runs the worker once (a temporary directory, removed): still nothing is created
    self_test(exe,I,inv,a.mp_check)
    if a.reserve_seed is not None:
        # HD6 at plan time (S2-002): under the seed log's own lock (the session lock; on symmetry the NFS home's), the log is
        # re-read, the seed rechecked against it and reserved for this campaign's identity before anything is built or
        # published; the entry stays whatever happens later (an interrupted plan, sweep or run keeps it). A plan that checks
        # seeds (--forbid-seeds-from: every non-test plan and sweep) reserves exclusively: another identity's entry of the
        # seed, or a derived-seed collision, refuses (65); a test-only plan that checks none (twins, prefix checks)
        # registers without that recheck.
        import seeds
        st=seeds.reserve(a.reserve_seed,a.seed,ident,exclusive=bool(a.forbid_seeds_from),refusal=lambda others:seed_refusal(a.seed,{**forbidden,**others}))
        print(f'seed {a.seed}: {st} for {ident} in {a.reserve_seed} ({"exclusive" if a.forbid_seeds_from else "registered without a seed check"}; HD6)',file=sys.stderr)
    fp=fingerprint(exe)
    # ---- build on scratch, copy, publish (D.4). The staging copy beside the target is this attempt's own (host, pid,
    # SLURM_JOB_ID when present); another attempt's is never removed, only listed (it may belong to a live plan), and the
    # publication is a rename that fails when the target exists, an empty directory included (common.rename_noreplace,
    # S2-005).
    from common import rename_noreplace
    jobid=os.environ.get('SLURM_JOB_ID');host=re.sub(r'[^A-Za-z0-9_-]','_',os.uname().nodename)
    tmp=out.with_name(f'{out.name}.tmp.{host}.{os.getpid()}'+(f'.{jobid}'if jobid else''))
    others=sorted(p.name for p in out.parent.iterdir()if p.name.startswith(out.name+'.tmp.')and p.name!=tmp.name)if out.parent.is_dir()else[]
    if others:print(f'plan: staging directories of other plan attempts beside {out}, left in place (they may belong to a live plan; remove them by '
                    f'hand once their plan jobs have ended): {", ".join(others)}',file=sys.stderr)
    if tmp.exists():shutil.rmtree(tmp)   # this name is ours: a dead earlier process with this pid on this host (pid reuse) left it
    work=Path(tempfile.mkdtemp(prefix='c8d3_plan_',dir=scratch));stage=work/'campaign'
    try:
        stage.mkdir();(stage/'groups').mkdir()
        x=dict(T=T,S=S,H=H,boot=boot,basis=basis,test_only=test_only,tg=tg,I=I,im_sha=im_sha,exe=exe,exe_sha=exe_sha,build=build,buildinfo=bi,
               model=model,model_bytes=model_bytes,syn=syn,syn_bytes=syn_bytes,prior_model=prior_model,prior_bytes=prior_bytes,bproxy=bproxy,mpf=mpf,
               bundle=bundle,selection=selection,sel_bytes=sel_bytes,forbidden=forbidden,merge=merge,files=files,lustre=lustre,P=P,R=R,greps=greps,
               skipped=skipped,task_s=task_s,min_chunk=min_chunk,role=role,campaign_role=campaign_role,fp=fp,host_cpu=host_cpu,
               reasons=v['test_only_reasons'],inv=inv)
        manifest=_build(a,stage,G,x)
        _self_check(stage,manifest,inv,G,x)
        out.parent.mkdir(parents=True,exist_ok=True)
        try:
            io_fault('plan_rename')
            shutil.copytree(stage,tmp);fsync_tree(tmp);rename_noreplace(tmp,out);fsync_dir(out.parent)
        except FileExistsError:   # the target appeared meanwhile (another attempt): the rename itself refused, nothing replaced
            shutil.rmtree(tmp,ignore_errors=True)
            raise FileExistsError(f'Use a new campaign directory ({out} was created by another attempt while this plan ran; nothing published, '
                                  f'this attempt\'s staging copy {tmp.name} removed)')
        except OSError as e:
            shutil.rmtree(tmp,ignore_errors=True)
            quota_guard(e,out,'plan publication')
    except BaseException:
        shutil.rmtree(tmp,ignore_errors=True);raise
    finally:shutil.rmtree(work,ignore_errors=True)
    _print_plan(out,manifest)

def _lpt_blocks(g:dict,T:int,S:float,w:int,boot:bool,threads:int)->None:
    """Per-task arrays of one group in uid order (rep, graph ascending, begin), the LPT shard assignment (heaviest first,
    ties by uid), the frozen position inside each shard (estimated seconds descending, then uid) and the frozen blocks
    of every shard (cut_blocks)."""
    np=np_();gids=sorted(g['counts']);reps=g['reps'];n=g['ntasks']
    rep=np.empty(n,np.int64);gi=np.empty(n,np.int64);lo=np.empty(n,np.int64);hi=np.empty(n,np.int64);tot=np.empty(n,np.int64);cost=np.empty(n,np.float64)
    k=0
    for r in range(reps):
        for gid in gids:
            b=g['tb'][gid];m=len(b);arr=np.asarray(b,dtype=np.int64)
            unit=g['prelim'][gid]if boot else g['per'][gid]
            rep[k:k+m]=r;gi[k:k+m]=gid;lo[k:k+m]=arr[:,0];hi[k:k+m]=arr[:,1];tot[k:k+m]=g['counts'][gid];cost[k:k+m]=(arr[:,1]-arr[:,0])*unit;k+=m
    if not boot:   # D.6: a task with s_t/w > S/2 is refused before anything is created, naming its group, graph and points
        over=np.nonzero(cost/w>S/2*(1+1e-12))[0]
        if len(over):
            u=int(over[0])
            raise ValueError(f'group {g["name"]} graph {int(gi[u])} replicate {int(rep[u])} points [{int(lo[u])}, {int(hi[u])}) of {int(tot[u])}: '
                             f'{float(cost[u]):.6g} s / {w} threads > --block-seconds/2 = {S/2:g} s ({len(over)} such task(s); D.6): give a larger '
                             f'--block-seconds, more --threads, or a cost model with shorter tasks')
    order=np.argsort(-cost,kind='stable')
    ns=g['nshards'];heap=[(0.,i)for i in range(ns)];heapq.heapify(heap);shard=np.empty(n,np.int64)
    cl=cost.tolist();pop=heapq.heappop;push=heapq.heappush
    for u in order.tolist():
        c,i=pop(heap);push(heap,(c+cl[u],i));shard[u]=i
    byshard=order[np.argsort(shard[order],kind='stable')]
    pos=np.empty(n,np.int64);cnt=np.bincount(shard,minlength=ns);start=np.concatenate([[0],np.cumsum(cnt)[:-1]]).astype(np.int64)
    pos[byshard]=np.arange(n)-np.repeat(start,cnt)
    block=np.empty(n,np.int64);kb={gid:int(g['byid'][gid]['kernel_bytes'])for gid in gids};jobs=[]
    for sh in range(ns):
        idx=byshard[start[sh]:start[sh]+cnt[sh]]
        cut=cut_blocks(None if boot else cost[idx].tolist(),T,S,w,n=len(idx))
        bnd=cut['bounds'];bl=np.empty(len(idx),np.int64)
        for b in range(len(bnd)-1):bl[bnd[b]:bnd[b+1]]=b
        block[idx]=bl;graphs=gi[idx]
        peak=max(sum(kb[q]for q in set(graphs[bnd[b]:bnd[b+1]].tolist()))for b in range(len(bnd)-1))
        ec=float(cost[idx].sum())
        jobs.append({'shard':sh,'tasks':int(len(idx)),'blocks':len(bnd)-1,'block_tasks':[bnd[b+1]-bnd[b]for b in range(len(bnd)-1)],
                     'block_wall':cut['wall'],'block_phi':cut['phi'],'small_block':cut['small_block'],
                     'est_core_seconds':None if boot else ec,'est_proxy_seconds':ec if boot else None,
                     'max_block_seconds':max(cut['wall'])if cut['wall']else None,
                     'est_peak_bytes':int(peak+threads*PROMOTED_SCRATCH_BYTES+BASE_PEAK_BYTES)})
    g['A']=dict(rep=rep,gi=gi,lo=lo,hi=hi,tot=tot,cost=cost,shard=shard,pos=pos,block=block,byshard=byshard,cnt=cnt,start=start)
    g['shard_jobs']=jobs
    small=sum(1 for j in jobs if j['small_block'])
    if small:print(f'{g["name"]}: {small} shard(s) keep a small final block (no valid cut gives both blocks half the target; D.6)',file=sys.stderr)

def _row_line(u,r,gi,lo,hi,t,b)->str:return f'{u} {r} {gi} {lo} {hi} {t} {b}\n'

def _build(a,stage:Path,G:dict,x:dict)->dict:
    T=x['T'];groups=[];jobs=[];est={};pmt={}
    if x['model_bytes']is not None:(stage/'cost_model.json').write_bytes(x['model_bytes'])
    if x['syn_bytes']is not None:(stage/'synthetic_cost_model.json').write_bytes(x['syn_bytes'])
    if x['prior_bytes']is not None:(stage/'prior_cost_model.json').write_bytes(x['prior_bytes'])
    if x['sel_bytes']is not None:(stage/'selection.json').write_bytes(x['sel_bytes'])
    boot=x['boot']
    for c,s,L in GROUPS:
        name=group_name(c,s,L)
        if name not in G:continue
        g=G[name];p=stage/'groups'/name;p.mkdir();(p/'tasks').mkdir()
        seeds=derive_seeds(a.seed,c,s,L);top=max(g['counts'].values(),default=1)
        net=make_net(p/'sobol.bin',g['reps'],4*L-1,g['bits'],seeds['net'],max(top,1))
        db=dbopen(p/'tasks.sqlite');db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER,block INTEGER);'
                                                     'CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
        db.executemany('INSERT INTO expected VALUES(?,?,?)',((r,gid,g['counts'][gid])for r in range(g['reps'])for gid in sorted(g['counts'])))
        shard_jobs=[]
        if g['ntasks']:
            A=g['A'];n=g['ntasks']
            rows=zip(range(n),A['rep'].tolist(),A['gi'].tolist(),A['lo'].tolist(),A['hi'].tolist(),A['tot'].tolist(),A['cost'].tolist(),A['shard'].tolist(),A['pos'].tolist(),A['block'].tolist())
            while True:
                part=list(itertools.islice(rows,200000))
                if not part:break
                db.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',part)
            db.execute('CREATE INDEX shard_order ON tasks(shard,pos)');db.execute('CREATE INDEX stream_order ON tasks(rep,gi,lo)')
            for sj in g['shard_jobs']:
                sh=sj['shard'];idx=A['byshard'][A['start'][sh]:A['start'][sh]+A['cnt'][sh]]
                data=''.join(_row_line(u,r,gi,lo,hi,t,b)for u,r,gi,lo,hi,t,b in zip(idx.tolist(),A['rep'][idx].tolist(),A['gi'][idx].tolist(),A['lo'][idx].tolist(),
                                                                                   A['hi'][idx].tolist(),A['tot'][idx].tolist(),A['block'][idx].tolist())).encode()
                f=p/'tasks'/f's{sh:06d}.tsv';f.write_bytes(data)
                blocks={'schema':'c8-d3-blocks-1','group':name,'shard':sh,'block_tasks':sj['block_tasks'],'pred_wall_seconds':sj['block_wall'],'phi':sj['block_phi'],
                        'small_block':sj['small_block'],'basis':x['basis'],'checkpoint_tasks':T,'block_seconds':x['S'],'threads':a.threads}
                bdata=(json.dumps(blocks,sort_keys=True,separators=(',',':'))+'\n').encode();bf=p/'tasks'/f's{sh:06d}.blocks.json';bf.write_bytes(bdata)
                shard_jobs.append({'group':name,'campaign':c,'sector':s,'L':L,'shard':sh,'tasks':sj['tasks'],'blocks':sj['blocks'],
                                   'tasks_file':f'groups/{name}/tasks/s{sh:06d}.tsv','tasks_sha256':hashlib.sha256(data).hexdigest(),'tasks_bytes':len(data),
                                   'blocks_file':f'groups/{name}/tasks/s{sh:06d}.blocks.json','blocks_sha256':hashlib.sha256(bdata).hexdigest(),
                                   'est_core_seconds':sj['est_core_seconds'],'est_proxy_seconds':sj['est_proxy_seconds'],'est_peak_bytes':sj['est_peak_bytes'],
                                   'max_block_seconds':sj['max_block_seconds'],'small_block':sj['small_block']})
            db.commit()
            for j in shard_jobs:   # plan-time self-check (R07): the per-index files equal the SQLite rows by (shard, pos)
                want=''.join(_row_line(*row)for row in db.execute('SELECT uid,rep,gi,lo,hi,total,block FROM tasks WHERE shard=? ORDER BY pos',(j['shard'],))).encode()
                if (stage/j['tasks_file']).read_bytes()!=want or hashlib.sha256(want).hexdigest()!=j['tasks_sha256']:
                    raise RuntimeError(f'per-index task file of {name} shard {j["shard"]} differs from tasks.sqlite')
        db.commit();db.close()
        cfg={'schema':GROUP_SCHEMA,'dimension':3,'order':ORDER,'name':name,'campaign':c,'sector':s,'L':L,'seed':seeds['native'],'seed_scheme':'hashed','layout':0,
             'rate':RATES[c],'replicates':g['reps'],'counts':{str(k):v for k,v in sorted(g['counts'].items())},
             'nest':{str(k):v for k,v in sorted(g['nest'].items())},'labels':{str(k):v for k,v in sorted(g['labels'].items())if v},
             'chunks':{str(k):v for k,v in sorted(g['chunk'].items())},
             'strata':{str(k):stratum_of(s,L,bool(g['byid'][k].get('primitive')))for k in sorted(g['counts'])},
             'net':net,'sum_mode':'compensated','shards':g['nshards'],'block_order':'pos: estimated seconds descending, then uid; blocks frozen by cut_blocks (D.6)',
             'tasks':g['ntasks'],'tasks_sha256':digest(p/'tasks.sqlite'),'samples':sum(g['counts'].values())*g['reps'],'build':x['build'],'numerics':a.numerics,
             'mp_check':a.mp_check,'cost_basis':x['basis'],'campaign_role':x['campaign_role'],'predicted_max_task_seconds':g['maxtask'],
             'preliminary_max_task_seconds':g['maxprelim']}
        dump(p/'config.json',cfg);groups.append({'name':name,'sha256':digest(p/'config.json')})
        base=len(jobs)
        for i,j in enumerate(shard_jobs):jobs.append({'id':base+i,**j})
        est[name]={'tasks':g['ntasks'],'shards':g['nshards'],'core_hours':None if boot else g['secs']/3600,
                   'preliminary_core_hours':g['psecs']/3600 if boot else None,'merge':x['merge'].get(name)}
        pmt[name]=g['maxtask']if not boot else{'preliminary':g['maxprelim'],'label':PRELIMINARY}
    tot=None if boot else sum(e['core_hours']for e in est.values())
    wall=None if boot else max((j['est_core_seconds']/(a.threads*EFFICIENCY)for j in jobs),default=0.)
    mem_mb=math.ceil((1.5*max(j['est_peak_bytes']for j in jobs)+2**30)/2**20)
    mmax=max((v['projected_seconds']for v in x['merge'].values()),default=0.)
    label={'measured':'seconds per point (identity-matching measured cost model)','synthetic':SYNTHETIC_LABEL,'bootstrap':'unavailable (bootstrap)',
           'prior_model':(f'prior_model (model of executable {(x["prior_model"]or{}).get("executable_sha256","")[:12]}, plan executable {x["exe_sha"][:12]}, '
                          f'x{a.prior_factor:g})')}[x['basis']]
    alloc=({'source':'pilot','points':x['P'],'replicates':x['R'],'group_replicates':{f'{s}:{L}':r for (s,L),r in sorted(x['greps'].items())},
            'graphs':None if x['selection']is None else{'path':str(Path(a.graphs).resolve()),'sha256':hashlib.sha256(x['sel_bytes']).hexdigest(),
                                                         'role':x['selection'].get('role'),'seed':x['selection'].get('seed')}}
           if a.pilot else{'source':'design','bundle':str(x['bundle']['path']),'meta_sha256':x['bundle']['meta_sha256']})
    pm=x['prior_model']
    manifest=dict(schema=SCHEMA,tool_sha256={n:digest(ROOT/'tools'/n)for n in PINNED_TOOLS},provenance_tool_sha256={n:digest(ROOT/'tools'/n)for n in PROVENANCE_TOOLS if (ROOT/'tools'/n).exists()},
                  dimension=3,order=ORDER,epsilon='2s-3',loops=sorted({g['L']for g in G.values()}),package=str(ROOT),
                  inputs=x['I'].rel,inputs_manifest_sha256=x['im_sha'],inputs_test_only_reasons=x['reasons'],skipped_packs=sorted(x['skipped']),
                  backend=a.backend,numerics=a.numerics,approved_numerics_change=a.approved_numerics_change,mp_check=a.mp_check,
                  build=x['build'],buildinfo=x['buildinfo'],executable=x['exe'].name,executable_sha256=x['exe_sha'],executable_self_test='passed',fingerprint=x['fp'],
                  threads=a.threads,checkpoint_tasks=T,block_seconds=x['S'],plan_role=x['role'],campaign_role=x['campaign_role'],
                  allocation=alloc,
                  design=({'bundle':str(x['bundle']['path']),'meta_sha256':x['bundle']['meta_sha256'],'design_sha256':x['bundle']['meta']['design_sha256'],
                           'label':x['bundle']['meta'].get('label'),'approved_fallback':a.approved_fallback,'batches':int(x['bundle']['design'].get('batches',1)),
                           's':{k:int(v['s'])for k,v in x['bundle']['design']['strata'].items()},'r':{k:int(v)for k,v in x['bundle']['design']['replicates'].items()},
                           'test_only':bool(x['bundle']['meta'].get('test_only'))}if x['bundle']else None),
                  selection=({'sha256':hashlib.sha256(x['sel_bytes']).hexdigest(),'role':x['selection'].get('role'),'seed':x['selection'].get('seed')}
                             if x['selection']is not None else None),
                  seed=a.seed,seed_scheme='hashed',forbidden_seed_sources=sorted({str(v)for v in x['forbidden'].values()}),groups=groups,jobs=jobs,
                  campaign_weights={'a':.5,'b':.5},power_sector='explicitly integrated; NOT assumed zero',
                  sampling_unit='complete graph-summed randomized replicate, not chunk',test_only=x['test_only'],test_graphs=x['tg'],
                  test_selection=a.test_selection if x['tg']is not None else None,cost_basis=x['basis'],
                  cost_model_sha256=hashlib.sha256(x['model_bytes']).hexdigest()if x['model_bytes']is not None else None,
                  cost_model_executable_sha256=(x['model']or{}).get('executable_sha256'),mp_check_factor=x['mpf'],
                  synthetic_cost_model_sha256=hashlib.sha256(x['syn_bytes']).hexdigest()if x['syn_bytes']is not None else None,
                  prior_model=({'path':str(Path(a.prior_cost_model).resolve()),'sha256':hashlib.sha256(x['prior_bytes']).hexdigest(),'executable_sha256':pm.get('executable_sha256'),
                                'cpu_model':pm.get('cpu_model'),'mp_check':pm.get('mp_check'),'job_ids':pm.get('job_ids')}if pm else None),
                  prior_factor=a.prior_factor if pm else None,
                  bootstrap_proxy={'sha256':digest(ROOT/'tools/bootstrap_proxy.json'),'label':PRELIMINARY}if x['boot']else None,
                  chunking=({'bootstrap_chunk':a.bootstrap_chunk,'label':PRELIMINARY}if x['boot']else{'task_seconds':x['task_s'],'min_chunk':x['min_chunk']})|{'max_task_seconds':a.max_task_seconds},
                  index_sizing={'index_hours':x['H'],'shards':a.shards,'assumed_efficiency':EFFICIENCY},
                  scale={'tasks':sum(j['tasks']for j in jobs),'checkpoints':sum(j['blocks']for j in jobs),'jobs':len(jobs),'projected_files':x['files'],'lustre':x['lustre'],
                         'merge_fan_in':MERGE_FAN_IN,'merge':x['merge'],'merge_projected_max_seconds':mmax,'suggested_merge_time':hms(max(3600,2*mmax+900)),
                         'merge_scratch_bytes_peak':sum(v['scratch_bytes']for v in x['merge'].values()),
                         'small_block_shards':sum(1 for j in jobs if j['small_block'])},
                  estimates={'basis':x['basis'],'label':label,'groups':est,'total_core_hours':tot,'max_index_wall_seconds':wall,
                             'suggested_time_seconds':None if x['boot']else max(900,math.ceil(1.5*wall/60)*60),'predicted_max_task_seconds':pmt,
                             'estimate':'unavailable (bootstrap)'if x['boot']else'available','mem_suggestion_mb':mem_mb,
                             'note':'planning estimates, not measurements'})
    dump(stage/'manifest.json',manifest)
    return manifest

def _self_check(stage:Path,m:dict,inv:dict,G:dict,x:dict)->None:
    """Plan-time self-check (D.6): blocks, per-block task counts, W(B) and phi, est_core_seconds and est_peak_bytes
    recomputed from the written per-index task files and the inventory, independently of cut_blocks; any difference
    refuses the publication."""
    for j in m['jobs']:
        g=G[j['group']];cfg=load(stage/'groups'/j['group']/'config.json')
        rows=[tuple(map(int,l.split()))for l in (stage/j['tasks_file']).read_text().splitlines()]
        if len(rows)!=j['tasks']:raise RuntimeError(f'self-check: {j["tasks_file"]} has {len(rows)} rows, the job entry {j["tasks"]}')
        blocks={}
        for r in rows:blocks.setdefault(r[6],[]).append(r)
        if sorted(blocks)!=list(range(j['blocks'])):raise RuntimeError(f'self-check: {j["tasks_file"]} block column is not 0..{j["blocks"]-1}')
        if any(rows[i][6]>rows[i+1][6]for i in range(len(rows)-1)):raise RuntimeError(f'self-check: {j["tasks_file"]} blocks are not contiguous in pos order')
        kb={r['id']:int(r['kernel_bytes'])for r in inv[j['sector']][str(j['L'])]}
        bdoc=json.loads((stage/j['blocks_file']).read_bytes())
        unit=lambda gid:(g['prelim'][gid]if x['boot']else g['per'][gid])
        peak=0;tot=0.;walls=[];phis=[]
        for b in range(j['blocks']):
            br=blocks[b];secs=math.fsum((r[4]-r[3])*unit(r[2])for r in br);tot+=secs
            peak=max(peak,sum(kb[q]for q in {r[2]for r in br}))
            if x['boot']:walls.append(None);phis.append(len(br)/m['checkpoint_tasks'])
            else:
                w=secs/m['threads'];walls.append(w);phis.append(max(len(br)/m['checkpoint_tasks'],w/m['block_seconds']))
            if len(br)>m['checkpoint_tasks']or (not x['boot']and walls[-1]>m['block_seconds']*(1+1e-9)):raise RuntimeError(f'self-check: block {b} of {j["tasks_file"]} exceeds a maximum')
        if [len(blocks[b])for b in range(j['blocks'])]!=bdoc['block_tasks']:raise RuntimeError(f'self-check: block task counts of {j["blocks_file"]} differ')
        close=lambda u,v:(u is None and v is None)or (u is not None and v is not None and abs(u-v)<=1e-9*max(1.,abs(u),abs(v)))
        if not all(close(u,v)for u,v in zip(walls,bdoc['pred_wall_seconds']or[None]*len(walls)))or not all(close(u,v)for u,v in zip(phis,bdoc['phi'])):
            raise RuntimeError(f'self-check: W(B) or phi of {j["blocks_file"]} differ from the recomputation')
        want_peak=peak+m['threads']*PROMOTED_SCRATCH_BYTES+BASE_PEAK_BYTES
        if want_peak!=j['est_peak_bytes']:raise RuntimeError(f'self-check: est_peak_bytes of index {j["id"]} {j["est_peak_bytes"]} != {want_peak}')
        est=j['est_proxy_seconds']if x['boot']else j['est_core_seconds']
        if not close(tot,est):raise RuntimeError(f'self-check: estimated seconds of index {j["id"]} {est} != {tot}')
        if cfg['tasks']!=g['ntasks']:raise RuntimeError('self-check: group task count')

def _print_plan(out:Path,m:dict)->None:
    e=m['estimates'];ch=lambda v:float(f'{v:.4g}')if isinstance(v,float)else v
    print(json.dumps({'directory':str(out),'jobs':len(m['jobs']),'tasks':m['scale']['tasks'],'checkpoints':m['scale']['checkpoints'],'backend':m['backend'],
                      'numerics':m['numerics'],'mp_check':m['mp_check'],'test_only':m['test_only'],'plan_role':m['plan_role'],'campaign_role':m['campaign_role'],
                      'cost_basis':m['cost_basis'],'estimate_label':e['label'],
                      'estimated_core_hours':ch(e['total_core_hours'])if e['total_core_hours']is not None else e['estimate'],
                      'max_index_wall_seconds':ch(e['max_index_wall_seconds'])if e['max_index_wall_seconds']is not None else'unavailable (bootstrap)',
                      'projected_files':m['scale']['projected_files'],'manifest_bytes':(out/'manifest.json').stat().st_size,
                      'merge_passes':{k:v['passes']for k,v in m['scale']['merge'].items()},'suggested_merge_time':m['scale']['suggested_merge_time'],
                      'small_block_shards':m['scale']['small_block_shards'],'array_mem_suggestion_mb':e['mem_suggestion_mb']},indent=2))
    if len(m['jobs'])>MAX_ARRAY:print(f'note: {len(m["jobs"])} jobs exceed one array of {MAX_ARRAY}; slurm_submit.py submit splits them into windows (C8_INDEX_OFFSET)',file=sys.stderr)

# ---------------------------------------------------------------- verification of a planned campaign
def verify_base(directory:Path,check_executable=True,accept_tool_change=False,vendored=False,scheduling_copies=True):
    """Manifest, pinned tools, inputs manifest, small inputs, the copied cost and selection files and (optionally) the
    executable and the vendored pins (merge and assemble; `run` never opens vendor/, A-ORC-13). Returns (manifest,
    Inputs, manifest sha256, accepted tool changes). A changed tool refuses unless accept_tool_change (merge and
    assemble only; recorded). scheduling_copies=False leaves the campaign's copies of a scheduling basis
    (synthetic_cost_model.json, prior_cost_model.json) unopened: a cost consumer never opens one (D.5, make_cost_model)."""
    data=(Path(directory)/'manifest.json').read_bytes();m=json.loads(data);mh=hashlib.sha256(data).hexdigest();sch=str(m.get('schema',''))
    if sch.startswith('c7-'):raise ValueError(C7_MESSAGE.format(d=directory,s=sch))
    if sch.startswith('c8-d2')or m.get('dimension')==2:raise ValueError(D2_MESSAGE.format(d=directory,s=sch))
    if sch!=SCHEMA or m.get('dimension')!=3 or m.get('order')!=ORDER:raise ValueError(f'campaign schema {sch} is not {SCHEMA} (dimension 3, order 8)')
    changes={}
    for n,h in m['tool_sha256'].items():
        f=ROOT/'tools'/n;cur=digest(f)if f.exists()else None
        if cur!=h:
            if not accept_tool_change:raise ValueError(f'Checksum mismatch: tools/{n} differs from the tool pinned by the plan; merge and assemble accept a changed tool only with --accept-tool-change (recorded as provenance)')
            changes[n]={'planned':h,'current':cur}
    idir=inputs_from_record(m['inputs']);im=read_verified(idir/'manifest.json',m['inputs_manifest_sha256'])
    if im.get('schema')!=INPUTS_SCHEMA or im.get('dimension')!=3:raise ValueError('wrong inputs manifest')
    I=Inputs(idir,im)
    for name in SMALL_INPUTS:checked(I.where(name),I.sha(name))
    if m.get('cost_model_sha256'):checked(Path(directory)/'cost_model.json',m['cost_model_sha256'])
    if scheduling_copies:
        if m.get('synthetic_cost_model_sha256'):checked(Path(directory)/'synthetic_cost_model.json',m['synthetic_cost_model_sha256'])
        if m.get('prior_model'):checked(Path(directory)/'prior_cost_model.json',m['prior_model']['sha256'])
    if m.get('selection'):checked(Path(directory)/'selection.json',m['selection']['sha256'])
    if check_executable:checked(ROOT/'bin'/m['executable'],m['executable_sha256'])
    if vendored:
        v=im.get('vendored_assembly')or{}
        if not v:raise ValueError('the inputs manifest carries no vendored assembly pins')
        checked(ROOT/'vendor/c8_assembly/HANDOFF_assembly.json',v['handoff_sha256'])
        for name,h in v['files'].items():checked(ROOT/name,h)
    return m,I,mh,changes

def campaign_role_of(directory:Path)->str:
    m,_,_,_=verify_base(directory,check_executable=False,accept_tool_change=True)
    r=m.get('campaign_role')
    if r not in CAMPAIGN_ROLES:raise ValueError(f'{directory}: campaign_role {r!r} is unknown')
    return r

def group_of(directory:Path,m:dict,name:str,schema:str=GROUP_SCHEMA):
    """The group directory and its config, verified against the manifest's pin (tasks.sqlite is not read here)."""
    p=Path(directory)/'groups'/name;cfg=read_verified(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==name))
    if cfg.get('schema')!=schema or cfg.get('dimension')!=3:raise ValueError('wrong group config schema: '+name)
    return p,cfg

def check_tasks_db(p:Path,cfg:dict)->None:
    """status, merge and verify_delivery verify the group's tasks.sqlite once per group (run never opens it, D.8)."""
    checked(p/'tasks.sqlite',cfg['tasks_sha256'])

def job_rows(directory:Path,j:dict)->list:
    """The index's own task rows (uid rep graph begin end total block, in pos order), verified against the manifest pin."""
    data=(Path(directory)/j['tasks_file']).read_bytes()
    if len(data)!=j['tasks_bytes']or hashlib.sha256(data).hexdigest()!=j['tasks_sha256']:
        raise ValueError(f'the task file of index {j["id"]} ({j["tasks_file"]}) differs from the manifest pin (sha256, bytes)')
    rows=[tuple(map(int,line.split()))for line in data.decode().splitlines()]
    if len(rows)!=j['tasks']or any(len(r)!=7 for r in rows):raise ValueError(f'malformed task file {j["tasks_file"]}')
    return rows

def blocks_of_rows(rows:list,nblocks:int)->list:
    """The frozen blocks of an index from the block column of its task file (D.6): never re-derived from a count."""
    out=[[]for _ in range(nblocks)]
    for r in rows:
        if not 0<=r[6]<nblocks:raise ValueError(f'task {r[0]}: block {r[6]} outside 0..{nblocks-1}')
        out[r[6]].append(r[:6])
    if any(not b for b in out):raise ValueError('a frozen block holds no task')
    return out

def iter_job_blocks(directory:Path,j:dict):
    """The index's frozen blocks streamed in order (merge phase 1): the file is checked against the manifest pin before
    the first block and hashed again while it is parsed, so at most one block of rows is held."""
    path=Path(directory)/j['tasks_file']
    def differs():return ValueError(f'the task file of index {j["id"]} ({j["tasks_file"]}) differs from the manifest pin (sha256, bytes)')
    if path.stat().st_size!=j['tasks_bytes']or digest(path)!=j['tasks_sha256']:raise differs()
    h=hashlib.sha256();size=0;count=0;block=[];cur=0
    with path.open('rb')as f:
        for line in f:
            h.update(line);size+=len(line);r=tuple(map(int,line.split()))
            if len(r)!=7:raise ValueError(f'malformed task file {j["tasks_file"]}')
            if r[6]!=cur:
                if r[6]!=cur+1 or not block:raise ValueError(f'{j["tasks_file"]}: blocks are not contiguous')
                yield block;block=[];cur=r[6]
            block.append(r[:6]);count+=1
    if size!=j['tasks_bytes']or h.hexdigest()!=j['tasks_sha256']:raise differs()
    if count!=j['tasks']or cur!=j['blocks']-1:raise ValueError(f'malformed task file {j["tasks_file"]}')
    if block:yield block

def _num(x)->D:
    v=D(str(x))
    if not v.is_finite():raise ValueError('non-finite number')
    return v

def validate_checkpoint(doc,block,cfg,m,mh):
    """A committed checkpoint against its block: identity, runtime, payload digest, native metadata (order 8, the
    numerics profile, the MP self-check mode, D.8), task coordinates, jets of width 2(9 - L), promotion counters and
    the class-B fields of C.3 (tails, nondirect/nonmoderate, the MP self-check histogram); returns the native record."""
    if doc.get('manifest_sha256')!=mh or doc.get('config_hash')!=object_hash(cfg):raise ValueError('checkpoint identity mismatch')
    rt=doc.get('runtime')or{}
    if rt.get('executable_sha256')!=m['executable_sha256']:raise ValueError('checkpoint was produced by a different executable')
    if rt.get('inputs_manifest_sha256')!=m['inputs_manifest_sha256']:raise ValueError('checkpoint was produced from different inputs')
    if rt.get('net_sha256')!=cfg['net']['sha256']:raise ValueError('checkpoint was produced from a different Sobol net')
    n=doc['native']
    if object_hash(n)!=doc.get('payload_sha256'):raise ValueError('checkpoint payload corruption')
    b=cfg['build'];expected={'schema':NATIVE_SCHEMA,'order':ORDER,'L':cfg['L'],'seed':cfg['seed'],'layout':cfg['layout'],'bits':cfg['net']['bits'],'sum_mode':cfg['sum_mode'],
                             'mp_backend':b['mp_backend'],'mp_digits10':b['mp_digits10'],'long_double_bits':b['long_double_bits'],'numerics':m['numerics'],'mp_check':m['mp_check']}
    for k,v in expected.items():
        if n.get(k)!=v:raise ValueError('native metadata mismatch: '+k)
    if (b.get('gmp')or{}).get('applicable')and n.get('gmp')!=b['gmp']:
        raise ValueError(f'the worker\'s runtime GMP {n.get("gmp")!r} differs from the planned build {b["gmp"]!r} (HD9, A-KER-3)')
    if abs(D(n['rate'])-D(cfg['rate']))>D(2)**(-b['long_double_bits']+1):raise ValueError('importance rate mismatch')
    if len(n['rows'])!=len(block):raise ValueError('incomplete checkpoint')
    K=ORDER-cfg['L'];mode=m['mp_check']
    for want,r in zip(block,n['rows']):
        if tuple(r[k]for k in ('uid','rep','graph','begin','end','total'))!=tuple(want[:6]):raise ValueError('wrong task coordinates')
        if len(r['values'])!=2*(K+1)or any(not D(v).is_finite()for v in r['values']):raise ValueError('invalid jet')
        npts=r['end']-r['begin']
        if not 0<=r['mp']<=r['quad']<=npts:raise ValueError('invalid promotion counters')
        try:
            if mode=='off'and not any(k in r for k in MP_FIELDS):r={**r,**mp_fields(r)}   # the worker omits them under off (C.3)
            top=[_num(x)for x in r['tail_top']];ts=_num(r['tail_sum'])
            ok=(len(top)==min(TAIL_K,npts)and all(x>=y for x,y in zip(top,top[1:]))and all(x>=0 for x in top)and ts>=0
                and isinstance(r['tail_argmax'],int)and r['begin']<=r['tail_argmax']<r['end']
                and all(isinstance(r[k],int)and 0<=r[k]<=npts for k in('nondirect','nonmoderate'))
                and isinstance(r['mp_checked'],int)and 0<=r['mp_checked']<=r['mp']and isinstance(r['mp_alarm'],int)and 0<=r['mp_alarm']<=r['mp_checked']
                and isinstance(r['mp_hist'],list)and len(r['mp_hist'])==MP_BINS and sum(r['mp_hist'])==r['mp_checked']
                and (r['mp_min_log10']is None if r['mp_checked']==0 else _min_log10_ok(r['mp_min_log10'])))
        except (KeyError,TypeError,ValueError,decimal.InvalidOperation):ok=False
        if not ok:raise ValueError(f'invalid class-B fields in row {r.get("uid")} (C.3)')
        if (mode=='on'and r['mp_checked']!=r['mp'])or (mode=='off'and r['mp_checked']!=0):raise ValueError(f'row {r["uid"]}: mp_checked {r["mp_checked"]} contradicts --mp-check {mode}')
    return n

MP_FIELDS=('mp_checked','mp_hist','mp_min_log10','mp_alarm')
def mp_fields(r:dict)->dict:
    """The MP self-check fields of a row; the worker omits them under --mp-check off (C.3), where they are 0/null."""
    return {'mp_checked':r.get('mp_checked',0),'mp_hist':r.get('mp_hist',[0]*MP_BINS),'mp_min_log10':r.get('mp_min_log10'),'mp_alarm':r.get('mp_alarm',0)}

def _min_log10_ok(v)->bool:
    """mp_min_log10 of a checked row: a finite number or -inf (an exact zero at the MP tier, kernel.hpp mp_check_record)."""
    x=D(str(v));return x.is_finite()or(x.is_infinite()and x<0)

def checkpoint_vendor(doc:dict)->str:
    """The CPU vendor of a checkpoint, from the cpu_model of its runtime fingerprint (every checkpoint records it): 'amd',
    'intel', else 'other: <model>' ('unknown' without one). The merge refuses checkpoints of several vendors (S2-001):
    native rows differ between vendors (x87 expl/logl) and the float64 assembly is bitwise only within one."""
    s=norm_cpu(((doc.get('runtime')or{}).get('fingerprint')or{}).get('cpu_model'))
    if not s:return 'unknown'
    return 'amd'if s.upper().startswith('AMD')else'intel'if s.upper().startswith('INTEL')else f'other: {s}'

def mixed_vendors(vendors,where:str)->None:
    if len(vendors)>1:raise ValueError(f'{where}: the checkpoints were computed on CPUs of several vendors ({", ".join(sorted(vendors))}): one CPU vendor per '
                                       'campaign (S2-001; native rows differ between vendors, so they are never merged together); nothing merged')

# ---------------------------------------------------------------- execution (D.8)
def stage_runtime(runtime:Path,m:dict,I:Inputs,cfg:dict,net:Path)->dict:
    """Copy the executable, gamma_d3_8.txt and the group's Sobol net into the job-private 0700 runtime; verify every COPY
    and use only the copies. Graph members are staged per block (stage_members), each hash-checked."""
    src=ROOT/'bin'/m['executable'];exe=runtime/src.name;shutil.copyfile(src,exe);os.chmod(exe,0o700);exe_sha=digest(exe)
    if exe_sha!=m['executable_sha256']:raise ValueError(f'{src} differs from the planned executable; never rebuild inside a campaign')
    gamma=runtime/GAMMA;shutil.copyfile(I.where(GAMMA),gamma);checked(gamma,I.sha(GAMMA))
    netcopy=runtime/'sobol.bin';shutil.copyfile(net,netcopy);net_sha=digest(netcopy)
    if net_sha!=cfg['net']['sha256']:raise ValueError('the Sobol net differs from the plan: '+str(net))
    return {'executable':exe,'gamma':gamma,'net':netcopy,'executable_sha256':exe_sha,'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':net_sha}

SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax','nondirect','nonmoderate',
            'mp_checked','mp_hist','mp_min_log10','mp_alarm')
_NATIVE={'launching':False,'pending':None,'children':[]}

class Terminated(BaseException):
    """Raised by the SIGTERM/SIGINT/SIGHUP handler of `run`; unwinds through the cleanup of the job-private runtime."""
    def __init__(self,signum):super().__init__(f'stopped by signal {signum}');self.signum=signum

def _stop(signum,frame):
    for s in STOP_SIGNALS:signal.signal(s,signal.SIG_IGN)
    if _NATIVE['launching']:_NATIVE['pending']=signum;return
    raise Terminated(signum)

def _after_launch(child):"""Test seam: called right after a native child is created and registered, while stop signals are deferred."""

def run_native(cmd,log):
    """Run one native work block; the child is registered before any stop signal can unwind (the signal-safe launch
    boundary, D.16)."""
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
    while _NATIVE['children']:
        child=_NATIVE['children'].pop()
        if child.poll()is None:
            try:child.terminate();child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()

def run(a):
    """Run one job index. SIGTERM, SIGINT and SIGHUP stop the native child, remove the job-private runtime and exit with
    128+signal; committed checkpoints stay (publication is atomic), the interrupted block is redone later."""
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
    directory=a.directory.resolve();m,I,mh,_=verify_base(directory);idx=a.index
    if idx is None:
        if 'SLURM_ARRAY_TASK_ID'not in os.environ:raise ValueError('give --index or run inside a Slurm array (SLURM_ARRAY_TASK_ID)')
        off=os.environ.get('C8_INDEX_OFFSET','0')
        if not off.isdigit():raise ValueError('C8_INDEX_OFFSET must be a non-negative integer')
        idx=int(off)+int(os.environ['SLURM_ARRAY_TASK_ID'])
    if not 0<=idx<len(m['jobs']):raise ValueError('job index outside plan')
    j=m['jobs'][idx];p,cfg=group_of(directory,m,j['group']);blocks=blocks_of_rows(job_rows(directory,j),j['blocks'])
    threads=a.threads or m['threads'];T=m['checkpoint_tasks']
    if threads<1:raise ValueError('invalid thread count')
    if threads>T:raise ValueError(f'{threads} threads exceed checkpoint_tasks={T}: at most {T} threads can ever be busy; use fewer threads or re-plan')
    scratch=a.scratch or os.environ.get('C8_SCRATCH')or os.environ.get('SLURM_TMPDIR')or None
    inv={r['id']:r for r in load_inventory(I)[cfg['sector']][str(cfg['L'])]}
    _NATIVE['launching']=True;runtime=None
    try:
        runtime=Path(tempfile.mkdtemp(prefix='c8d3_runtime_',dir=scratch));os.chmod(runtime,0o700);_NATIVE['launching']=False
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        rt=stage_runtime(runtime,m,I,cfg,p/'sobol.bin');counter={'bytes':0};fp=fingerprint(rt['executable'],counter)
        print(f'fingerprint {fingerprint_key(fp)} ({fp.get("cpu_model")}); fingerprint_bytes {counter["bytes"]}',flush=True)
        (p/'checkpoints').mkdir(exist_ok=True);(p/'logs').mkdir(exist_ok=True);done=0
        for part,block in enumerate(blocks):
            name=block_name(j['shard'],part);dest=p/'checkpoints'/f'{name}.json'
            if dest.exists():validate_checkpoint(load(dest),block,cfg,m,mh);continue
            if a.max_blocks is not None and done>=a.max_blocks:print(f'stopped after {done} blocks (--max-blocks)',flush=True);break
            with tempfile.TemporaryDirectory(prefix='block_',dir=runtime)as td:
                td=Path(td);graphroot=stage_members(td/'graphs',I,cfg['sector'],cfg['L'],[r[2]for r in block],inv);tasks=td/'tasks.txt'
                tasks.write_text(f'{TASK_MAGIC} {ORDER} {cfg["L"]} {len(block)}\n'+''.join(' '.join(map(str,r[:6]))+'\n'for r in block));out=td/'native.json'
                cmd=list(map(str,[rt['executable'],graphroot,rt['gamma'],rt['net'],tasks,out,cfg['seed'],cfg['layout'],cfg['rate'],threads,cfg['sum_mode'],'-','--mp-check',m['mp_check']]))
                try:
                    with (td/'native.log').open('w')as log:run_native(cmd,log)
                except subprocess.CalledProcessError as exc:
                    message=(td/'native.log').read_text();publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message);raise RuntimeError('Native work block failed: '+message[-4000:])from exc
                n=load(out)
                doc={'runtime':{'executable_sha256':rt['executable_sha256'],'inputs_manifest_sha256':rt['inputs_manifest_sha256'],'net_sha256':rt['net_sha256'],
                                'fingerprint':fp,'fingerprint_bytes':counter['bytes']},
                     'manifest_sha256':mh,'config_hash':object_hash(cfg),'index':idx,'block':part,'native':n,'payload_sha256':object_hash(n),
                     'task_file_sha256':digest(tasks),'index_tasks_sha256':j['tasks_sha256']}
                validate_checkpoint(doc,block,cfg,m,mh)
                try:dump_point(dest,doc,'checkpoint_publish');state='committed'
                except FileExistsError:
                    prior=validate_checkpoint(load(dest),block,cfg,m,mh)
                    for x,y in zip(prior['rows'],n['rows']):
                        if any(x.get(k)!=y.get(k)for k in SCIENTIFIC):raise ValueError('Conflicting duplicate execution: '+str(dest))
                    state='verified duplicate (published concurrently by another run)'
                done+=1;print(f'{state} {j["group"]}/{name}',flush=True)
    finally:
        _NATIVE['launching']=False;stop_children()
        if runtime is not None:shutil.rmtree(runtime,ignore_errors=True)

# ---------------------------------------------------------------- merge (D.13, C.3)
def _row_fields(r:dict)->str:
    """One raw task row of a run file (tab-separated; never a partial sum): rep graph begin end total quad mp seconds
    tail_sum tail_argmax tail_top values nondirect nonmoderate mp_checked mp_alarm mp_min_log10 mp_hist."""
    q=mp_fields(r)
    return '\t'.join((str(r['rep']),str(r['graph']),str(r['begin']),str(r['end']),str(r['total']),str(r['quad']),str(r['mp']),repr(float(r['seconds'])),
                      str(r['tail_sum']),str(r['tail_argmax']),' '.join(map(str,r['tail_top'])),' '.join(map(str,r['values'])),
                      str(r['nondirect']),str(r['nonmoderate']),str(q['mp_checked']),str(q['mp_alarm']),
                      'null'if q['mp_min_log10']is None else str(q['mp_min_log10']),' '.join(map(str,q['mp_hist']))))+'\n'

def _parse_run_line(line:str):
    f=line.rstrip('\n').split('\t');return (int(f[0]),int(f[1]),int(f[2])),f

MERGED_FILES=('graph_replicates','graph_tails','graph_promotions','graph_costs')

def validate_merged(p:Path,cfg:dict,m:dict,mh:str,schema:str=MERGED_SCHEMA)->dict:
    d=load(p/'merged.json')
    if d.get('schema')!=schema or d.get('complete')is not True or d.get('manifest_sha256')!=mh or d.get('config_hash')!=object_hash(cfg)or d.get('sector')!=cfg['sector']\
       or d.get('L')!=cfg['L']or d.get('campaign')!=cfg['campaign']or d.get('numerics')!=m['numerics']or d.get('mp_check')!=m['mp_check']or d.get('order')!=ORDER:
        raise ValueError('existing merged.json does not belong to this plan: '+str(p/'merged.json'))
    if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d.get('payload_sha256'):raise ValueError('merged payload checksum mismatch: '+str(p/'merged.json'))
    for f in MERGED_FILES:checked(p/f'{f}.csv',d[f'{f}_sha256'])
    nested=bool(cfg.get('nest'))
    if nested!=(d.get('graph_prefixes_sha256')is not None)or d.get('prefix_rule')!=PREFIX_RULE:raise ValueError('merged.json prefix records do not match the plan\'s nest boundaries')
    if nested:
        checked(p/'graph_prefixes.csv',d['graph_prefixes_sha256'])
        want=cfg['replicates']*sum(len(v)for v in cfg['nest'].values())
        if d.get('prefix_rows')!=want:raise ValueError(f'merged.json prefix_rows {d.get("prefix_rows")} != {want}')
    elif d.get('prefix_rows')!=0:raise ValueError('merged.json prefix_rows must be 0 without nested graphs')
    if len(d['batches'])!=cfg['replicates']or d.get('replicates')!=cfg['replicates']:raise ValueError('merged replicate count mismatch')
    return d

_MW={}

def _merge_init(directory:str,mh:str)->None:
    d=Path(directory);data=(d/'manifest.json').read_bytes()
    if hashlib.sha256(data).hexdigest()!=mh:raise ValueError('manifest.json changed during the merge')
    _MW.clear();_MW.update(directory=d,m=json.loads(data),mh=mh,cfg={})

def _mw_group(name:str):
    if name not in _MW['cfg']:_MW['cfg'][name]=group_of(_MW['directory'],_MW['m'],name)
    return _MW['cfg'][name]

def _write_run(items,out:Path)->int:
    out=Path(out);fd,tname=tempfile.mkstemp(prefix=out.name+'.tmp.',dir=out.parent);n=0
    try:
        with os.fdopen(fd,'w')as f:
            for _,line in items:f.write(line);n+=1
            f.write('#end\n')
        os.replace(tname,out)
    except BaseException:
        try:os.unlink(tname)
        except OSError:pass
        raise
    return n

def _run_lines(path:Path):
    with Path(path).open()as f:
        for line in f:
            if line=='#end\n':return
            a,b,c,_=line.split('\t',3);yield (int(a),int(b),int(c)),line
    raise ValueError(f'truncated run file {path}')

def _read_run(path:Path):
    for k,line in _run_lines(path):yield k,line.rstrip('\n').split('\t')

def _phase1(jid:int,out:str,F:int)->dict:
    """Phase 1 for one shard: its checkpoints validated block by block against its per-index task file, the raw rows
    of each block sorted by (rep, graph, begin) into a spill run, the spill runs merged with fan-in F into the shard's
    run file. Peak memory: one checkpoint block plus F rows."""
    import array
    directory,m,mh=_MW['directory'],_MW['m'],_MW['mh'];j=m['jobs'][jid];p,cfg=_mw_group(j['group'])
    out=Path(out);stats={'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0};secs=array.array('d');tsecs=array.array('d')
    spill=lambda part:out.with_name(f'{out.name}.b{part:06d}')
    vendors=set()
    for part,block in enumerate(iter_job_blocks(directory,j)):
        f=p/'checkpoints'/f'{block_name(j["shard"],part)}.json'
        if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
        doc=load(f);n=validate_checkpoint(doc,block,cfg,m,mh);vendors.add(checkpoint_vendor(doc));del doc
        secs.append(float(n['integration_seconds']));tsecs.append(float(n['integration_seconds'])*int(n['threads']));stats['blocks']+=1
        stats['max_rss_kb']=max(stats['max_rss_kb'],int(n.get('max_rss_kb')or 0))
        for r in n['rows']:stats['quad']+=r['quad'];stats['mp']+=r['mp']
        stats['rows']+=len(n['rows'])
        lines=sorted((((r['rep'],r['graph'],r['begin']),_row_fields(r))for r in n['rows']),key=lambda t:t[0]);del n
        _write_run(lines,spill(part));del lines
    stats['secs']=secs.tolist();stats['tsecs']=tsecs.tolist();stats['vendors']=sorted(vendors);spills=[spill(k)for k in range(stats['blocks'])];level=0
    while len(spills)>F:
        level+=1;nxt=[]
        for k in range(0,len(spills),F):
            o=out.with_name(f'{out.name}.m{level}.{k//F:06d}');_write_run(heapq.merge(*(_run_lines(x)for x in spills[k:k+F]),key=lambda t:t[0]),o);nxt.append(o)
            for x in spills[k:k+F]:x.unlink()
        spills=nxt
    rows=_write_run(heapq.merge(*(_run_lines(x)for x in spills),key=lambda t:t[0]),out)
    for x in spills:x.unlink()
    if rows!=stats['rows']:raise ValueError(f'phase 1 of index {jid}: {rows} rows written, {stats["rows"]} validated')
    return stats

def exact_seconds(stats:dict)->dict:
    out={k:v for k,v in stats.items()if k not in('secs','tsecs')}
    out['seconds']=math.fsum(stats['secs']);out['thread_seconds']=math.fsum(stats['tsecs']);return out

def fan_in(requested:int)->int:
    import resource
    soft=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    F=min(requested,(soft-32)if soft!=resource.RLIM_INFINITY else requested)
    if F<2:raise ValueError(f'merge fan-in {F} < 2: RLIMIT_NOFILE soft limit {soft} leaves fewer than 2 run files open (raise it, ulimit -n) (D.13)')
    return F

def _phase2(name:str,runs:list,work:str,F:int,changes,stats:dict)->dict:
    """Phase 2 for one group: an external merge of its shard runs with fan-in F (resumable passes of F runs at a time),
    then the final pass in (rep, graph, begin) order. Scratch (D.13: at most two copies of the group's raw rows): each
    batch of F runs is deleted as soon as its merged run is complete, as phase 1 deletes its spill files, so a pass holds
    the group's rows once plus the batch being written; the runs the final pass read are deleted when it ends."""
    work=Path(work);m,mh=_MW['m'],_MW['mh'];p,cfg=_mw_group(name);level=0;runs=[Path(r)for r in runs];passes=0
    try:
        while len(runs)>F:
            level+=1;nxt=[]
            for k in range(0,len(runs),F):
                o=work/f'{name}.p{level}.r{k//F:06d}.run'
                if not(o.exists()and o.read_bytes().endswith(b'#end\n')):_write_run(heapq.merge(*(_run_lines(x)for x in runs[k:k+F]),key=lambda t:t[0]),o)
                for x in runs[k:k+F]:x.unlink(missing_ok=True)
                nxt.append(o)
            runs=nxt;passes+=1
        stream=heapq.merge(*(_read_run(r)for r in runs),key=lambda t:t[0])if runs else iter(())
        res=_final_pass(p,cfg,m,mh,stream,work,changes,stats);res['passes']=passes+1;return res
    finally:
        for x in runs:x.unlink(missing_ok=True)

def _merge_tops(top:list,tops:list)->list:
    return sorted(top+tops,key=lambda v:D(v),reverse=True)[:TAIL_K]

def _final_pass(p:Path,cfg:dict,m:dict,mh:str,stream,work:Path,changes,stats)->dict:
    """The unchanged 50-digit Decimal summation in (rep, graph, begin) order: graph_replicates.csv (byte-unchanged
    format), graph_tails.csv, graph_promotions.csv, graph_costs.csv and, for nested graphs, graph_prefixes.csv
    (C.3, R06)."""
    dim=2*(ORDER+1-cfg['L']);counts={int(k):v for k,v in cfg['counts'].items()};nest={int(k):v for k,v in (cfg.get('nest')or{}).items()}
    expected=[(rep,g,counts[g])for rep in range(cfg['replicates'])for g in sorted(counts)]
    r=next(stream,None)
    files={k:work/f'{cfg["name"]}.{k}.csv'for k in (*MERGED_FILES,'graph_prefixes')}
    try:return _final_pass_files(p,cfg,m,mh,stream,changes,stats,dim,counts,nest,expected,r,files)
    finally:
        for f in files.values():f.unlink(missing_ok=True)   # the group's scratch tables, once published (or after a failure)

def _final_pass_files(p:Path,cfg:dict,m:dict,mh:str,stream,changes,stats,dim,counts,nest,expected,r,files)->dict:
    """The body of _final_pass, writing the scratch tables `files` and publishing them into the group directory p."""
    batches=[];count=0;costs={};prefix_rows=0;row_seconds=D(0)
    with decimal.localcontext()as ctx,files['graph_replicates'].open('w')as fr,files['graph_tails'].open('w')as ft,files['graph_promotions'].open('w')as fp_,\
         files['graph_prefixes'].open('w')as fx:
        ctx.prec=50
        fr.write('replicate,graph,'+','.join(f'jet_{i}'for i in range(dim))+'\n')
        ft.write('replicate,graph,points,tail_sum,tail_argmax,tail_n,'+','.join(f'tail_top_{i+1}'for i in range(TAIL_K))+'\n')
        fp_.write('replicate,graph,quad,mp,nondirect,nonmoderate,mp_checked,mp_alarm,mp_min_log10,'+','.join(f'mp_hist_{i}'for i in range(MP_BINS))+'\n')
        if nest:fx.write('replicate,graph,points,total,'+','.join(f'jet_{i}'for i in range(dim))+',tail_sum,'+','.join(f'tail_top_{i+1}'for i in range(TAIL_K))+',tail_argmax\n')
        batch=[D(0)]*dim;prevrep=0
        for rep,gi,total in expected:
            if rep!=prevrep:batches.append([float(v)for v in batch]);batch=[D(0)]*dim;prevrep=rep
            graph=[D(0)]*dim;end=0;tsum=D(0);best=None;arg=None;top=[];pro=[0,0,0,0,0,0];hist=[0]*MP_BINS;mmin=None
            bounds=list(nest.get(gi,[]))
            while r is not None and (r[0][0],r[0][1])==(rep,gi):
                (_,_,lo),f=r;hi=int(f[3]);tt=int(f[4])
                if lo!=end or tt!=total or not 0<=lo<hi<=total:raise ValueError('incomplete, overlapping or inconsistent sample intervals')
                graph=[x+D(v)for x,v in zip(graph,f[11].split(' '))];end=hi;count+=1
                tsum=TAIL_SUM_CONTEXT.add(tsum,D(f[8]));tops=f[10].split(' ')if f[10]else[]
                if tops and (best is None or D(tops[0])>best or (D(tops[0])==best and int(f[9])<arg)):best=D(tops[0]);arg=int(f[9])
                top=_merge_tops(top,tops)
                pro[0]+=int(f[5]);pro[1]+=int(f[6]);pro[2]+=int(f[12]);pro[3]+=int(f[13]);pro[4]+=int(f[14]);pro[5]+=int(f[15])
                if f[16]!='null':mmin=D(f[16])if mmin is None else min(mmin,D(f[16]))
                hist=[x+int(y)for x,y in zip(hist,f[17].split(' '))]
                c=costs.setdefault(gi,[0,D(0),0]);c[0]+=hi-lo;c[1]+=D(f[7]);c[2]+=1;row_seconds+=D(f[7])
                while bounds and end>bounds[0]:raise ValueError(f'nested graph {gi}: no task boundary at its nest point {bounds[0]} (D.3)')
                if bounds and end==bounds[0]:
                    P=bounds.pop(0);scale=D(total)/D(P)
                    fx.write(f'{rep},{gi},{P},{total},'+','.join(str(x*scale)for x in graph)+f',{tsum},'+','.join(top+['']*(TAIL_K-len(top)))+f',{arg}\n');prefix_rows+=1
                r=next(stream,None)
            if end!=total:raise ValueError(f'missing samples rep={rep},graph={gi}')
            if bounds:raise ValueError(f'nested graph {gi}: no task boundary at its nest point {bounds[0]} (D.3)')
            fr.write(f'{rep},{gi},'+','.join(map(str,graph))+'\n');batch=[x+y for x,y in zip(batch,graph)]
            ft.write(f'{rep},{gi},{total},{tsum},{arg},{len(top)},'+','.join(top+['']*(TAIL_K-len(top)))+'\n')
            fp_.write(f'{rep},{gi},'+','.join(map(str,pro))+','+('null'if mmin is None else str(mmin))+','+','.join(map(str,hist))+'\n')
        if r is not None:raise ValueError('unexpected streams')
        if expected:batches.append([float(v)for v in batch])
        else:batches=[[0.]*dim for _ in range(cfg['replicates'])]
    with files['graph_costs'].open('w')as fc:
        fc.write('graph,points,row_seconds,tasks\n')
        for gi in sorted(costs):x=costs[gi];fc.write(f'{gi},{x[0]},{x[1]},{x[2]}\n')
    if count!=cfg['tasks']:raise ValueError('wrong total task coverage')
    if len(batches)!=cfg['replicates']:raise ValueError('missing replicates')
    for k in MERGED_FILES:_publish_copy(files[k],p/f'{k}.csv',cfg['name'],k=='graph_costs')   # graph_costs.csv: timing only
    if nest:_publish_copy(files['graph_prefixes'],p/'graph_prefixes.csv',cfg['name'])
    merged={'schema':MERGED_SCHEMA,'complete':True,'order':ORDER,'L':cfg['L'],'sector':cfg['sector'],'campaign':cfg['campaign'],'dimension':3,'config_hash':object_hash(cfg),
            'manifest_sha256':mh,'replicates':cfg['replicates'],'samples':cfg['samples'],'numerics':m['numerics'],'mp_check':m['mp_check'],'campaign_role':m['campaign_role'],
            'batches':batches,'fallbacks':{'quad':stats['quad'],'mp':stats['mp']},'integration_seconds_sum':stats['seconds'],'thread_seconds_sum':stats['thread_seconds'],
            'integration_core_seconds':float(row_seconds),'blocks':stats['blocks'],'max_rss_kb':stats['max_rss_kb'],
            # the digests of the bytes this merge published (its scratch tables), not a re-read of the group's files (F8-d3)
            **{f'{k}_sha256':digest(files[k])for k in MERGED_FILES},
            'graph_prefixes_sha256':digest(files['graph_prefixes'])if nest else None,'prefix_rows':prefix_rows,'prefix_rule':PREFIX_RULE,
            'units':'integration_seconds_sum: lane wall seconds of the blocks; integration_core_seconds: the sum of row seconds (F6)'}
    if changes:merged['accepted_tool_changes']=changes
    merged['payload_sha256']=object_hash(merged);dest=p/'merged.json'
    try:dump_point(dest,merged,'merge_output')
    except FileExistsError:
        prior=validate_merged(p,cfg,m,mh)
        if canon(prior)!=canon(json.loads(json.dumps(merged,allow_nan=False))):raise ValueError('a different merged.json was published concurrently: '+str(dest))
        print(f'{cfg["name"]}: identical merged.json published concurrently; kept',flush=True)
    return {'group':cfg['name'],'merged':str(dest)}

def _publish_copy(src:Path,target:Path,group:str='',timing:bool=False)->str:
    """Stream-copy a scratch table into the group. merged.json is a group's commit point (F8-d3, C62d's F8): its tables
    are committed once merged.json exists, and a committed table must stay identical (no-clobber; 'Checksum mismatch'
    otherwise). A table without a merged.json is uncommitted, left by an earlier merge whose merged.json was removed
    (the recovery of a completed index deletes a checkpoint and the group's merged.json) or by a merge stopped before
    its merged.json: a different one is replaced atomically and reported. graph_costs.csv (timing=True) changes
    whenever a block is recomputed; a changed scientific table is reported as such, and assemble then refuses a result
    whose science changed. Every reader of a group's tables checks them against merged.json's digests
    (validate_merged), so an uncommitted table is never read. Returns 'published', 'identical' or 'replaced'."""
    want=digest(src)
    if target.exists()and digest(target)==want:return 'identical'
    try:
        io_fault('merge_output')
        fd,tname=tempfile.mkstemp(prefix=target.name+'.tmp.',dir=target.parent)
    except OSError as e:
        quota_guard(e,target,'merge output');raise   # quota_guard always raises; the raise keeps the flow explicit
    try:
        os.fchmod(fd,umask_mode())
        with src.open('rb')as i,os.fdopen(fd,'wb')as o:shutil.copyfileobj(i,o);o.flush();os.fsync(o.fileno())
        try:os.link(tname,target);return 'published'
        except FileExistsError:pass
        old=digest(target)
        if old==want:return 'identical'
        if (target.parent/'merged.json').exists():raise ValueError(f'Checksum mismatch: {target} differs from the committed table (the group\'s merged.json exists)')
        os.replace(tname,target);tname=None
        what='timing only'if timing else'SCIENTIFIC TABLE CHANGED: the uncommitted table differed from the one these checkpoints give; assemble refuses a result whose science changed'
        print(f'{group or target.parent.name}: replaced the uncommitted {target.name} (no merged.json; sha256 {old[:12]} -> {want[:12]}; {what})',flush=True)
        return 'replaced'
    except OSError as e:
        if e.errno in QUOTA_ERRNOS:quota_guard(e,target,'merge output')
        raise
    finally:
        if tname is not None:
            try:os.unlink(tname)
            except OSError:pass

class _Serial:
    """A same-process stand-in for ProcessPoolExecutor (one process)."""
    def __init__(self,*a,**k):pass
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def submit(self,fn,*args):
        import concurrent.futures
        f=concurrent.futures.Future()
        try:f.set_result(fn(*args))
        except Exception as e:f.set_exception(e)
        return f

def merge(a):
    """merge [--jobs N] [--parse-jobs M] [--fan-in F] [--serial]: phase 1 parallel over every shard of every group (M
    processes; one sorted run per shard on node-local scratch), phase 2 parallel over groups (N processes), heaviest
    group first by recorded cost. --serial is the reference merge (one SQLite table per group), byte-identical.
    Checkpoints computed on CPUs of several vendors (checkpoint_vendor) are refused before anything is published, across
    every group the merge merges (S2-001)."""
    directory=a.directory.resolve();m,I,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=a.accept_tool_change,vendored=True)
    if changes:print('accepted tool changes (recorded in merged.json): '+', '.join(changes),file=sys.stderr)
    names=[a.group]if a.group else[g['name']for g in m['groups']]
    if any(n not in {g['name']for g in m['groups']}for n in names):raise ValueError('unknown group')
    if a.jobs<1 or (a.parse_jobs is not None and a.parse_jobs<1):raise ValueError('--jobs and --parse-jobs must be positive')
    F=fan_in(a.fan_in);todo=[]
    for n in names:
        p,cfg=group_of(directory,m,n)
        if (p/'merged.json').exists():validate_merged(p,cfg,m,mh);print(f'{n}: already merged and valid; skipped',flush=True);continue
        check_tasks_db(p,cfg);todo.append(n)
    if not todo:return
    if a.serial:   # S2-001: the CPU vendors of every group to merge, before the first group is published
        mixed_vendors({checkpoint_vendor({'runtime':checkpoint_runtime(f)})for n in todo for f in sorted((directory/'groups'/n/'checkpoints').glob('*.json'))},'merge --serial')
        for n in todo:merge_group_serial(directory,m,n,a.scratch,mh,changes)
        return
    _merge_parallel(a,directory,m,mh,changes,todo,F)

def _merge_parallel(a,directory:Path,m:dict,mh:str,changes,todo:list,F:int)->None:
    import concurrent.futures,multiprocessing
    cost={g:sum((j['est_core_seconds']or j['est_proxy_seconds']or 0.)for j in m['jobs']if j['group']==g)for g in todo}
    with tempfile.TemporaryDirectory(prefix='c8d3_merge_',dir=a.scratch)as work:
        runs={n:[]for n in todo};stats={n:{'secs':[],'tsecs':[],'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0}for n in todo};tasks=[]
        for j in m['jobs']:
            if j['group']in runs:out=str(Path(work)/f'{j["group"]}.s{j["shard"]:06d}.run');runs[j['group']].append(out);tasks.append((j['id'],out,j['group']))
        def pool(k):
            if k>1:return concurrent.futures.ProcessPoolExecutor(k,mp_context=multiprocessing.get_context('spawn'),initializer=_merge_init,initargs=(str(directory),mh))
            _merge_init(str(directory),mh);return _Serial()
        t0=time.time();pj=a.parse_jobs if a.parse_jobs is not None else a.jobs
        vendors=set()   # S2-001: every checkpoint of the merge on one CPU vendor, checked before phase 2 publishes anything
        with pool(pj)as ex:
            futs={ex.submit(_phase1,jid,out,F):g for jid,out,g in tasks};errors=[];quota=False
            for f in (concurrent.futures.as_completed(futs)if pj>1 else list(futs)):
                try:
                    s=f.result();g=futs[f];vendors|=set(s['vendors'])
                    for k in ('secs','tsecs'):stats[g][k]+=s[k]
                    for k in ('quad','mp','rows','blocks'):stats[g][k]+=s[k]
                    stats[g]['max_rss_kb']=max(stats[g]['max_rss_kb'],s['max_rss_kb'])
                except Exception as e:errors.append(f'{futs[f]}: {e}');quota|=isinstance(e,Refuse)and e.code==74
            if errors:
                msg='merge phase 1 failed: '+'; '.join(sorted(errors)[:5])
                raise Refuse(74,msg)if quota else RuntimeError(msg)
        mixed_vendors(vendors,'merge phase 1')
        t1=time.time();rows=sum(stats[n]['rows']for n in todo)
        print(f'merge phase 1: {rows} rows of {len(tasks)} shards in {t1-t0:.2f} s with {pj} process(es) ({rows/max(t1-t0,1e-9):.0f} rows/s)',flush=True)
        order=sorted(todo,key=lambda n:(-cost[n],n))
        with pool(a.jobs)as ex:
            futs={ex.submit(_phase2,n,runs[n],work,F,changes,exact_seconds(stats[n])):n for n in order};errors=[];quota=False
            for f in (concurrent.futures.as_completed(futs)if a.jobs>1 else list(futs)):
                try:r=f.result();print(f'{r["group"]}: merged ({r["passes"]} pass(es), fan-in {F}) -> {r["merged"]}',flush=True)
                except Exception as e:errors.append(f'{futs[f]}: {e}');quota|=isinstance(e,Refuse)and e.code==74
            if errors:
                msg='merge failed for '+'; '.join(sorted(errors))
                raise Refuse(74,msg)if quota else RuntimeError(msg)
        t2=time.time();print(f'merge phase 2: {rows} rows of {len(todo)} group(s) in {t2-t1:.2f} s ({rows/max(t2-t1,1e-9):.0f} rows/s)',flush=True)

def merge_group_serial(directory:Path,m:dict,name:str,scratch=None,mh=None,changes=None):
    """The reference merge: every frozen block of every shard validated in shard order (task file rows), the raw rows
    in one SQLite table on scratch, read back in (rep, graph, begin) order into the same final pass."""
    p,cfg=group_of(directory,m,name);mh=mh or digest(Path(directory)/'manifest.json')
    stats={'secs':[],'tsecs':[],'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0};vendors=set()
    with tempfile.TemporaryDirectory(prefix='c8d3_smerge_',dir=scratch)as td:
        db=dbopen(Path(td)/'merge.sqlite');db.execute('CREATE TABLE actual(rep INTEGER,gi INTEGER,lo INTEGER,line TEXT)')
        for j in (j for j in m['jobs']if j['group']==name):
            for part,block in enumerate(blocks_of_rows(job_rows(directory,j),j['blocks'])):
                f=p/'checkpoints'/f'{block_name(j["shard"],part)}.json'
                if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
                doc=load(f);n=validate_checkpoint(doc,block,cfg,m,mh);vendors.add(checkpoint_vendor(doc));del doc
                stats['secs'].append(float(n['integration_seconds']));stats['tsecs'].append(float(n['integration_seconds'])*int(n['threads']));stats['blocks']+=1
                stats['max_rss_kb']=max(stats['max_rss_kb'],int(n.get('max_rss_kb')or 0))
                for r in n['rows']:db.execute('INSERT INTO actual VALUES(?,?,?,?)',(r['rep'],r['graph'],r['begin'],_row_fields(r)));stats['quad']+=r['quad'];stats['mp']+=r['mp']
        mixed_vendors(vendors,name)   # S2-001, before anything of the group is published
        db.commit();db.execute('CREATE INDEX s ON actual(rep,gi,lo)')
        stream=(_parse_run_line(line)for (line,)in db.execute('SELECT line FROM actual ORDER BY rep,gi,lo'))
        res=_final_pass(p,cfg,m,mh,stream,Path(td),changes,exact_seconds(stats));db.close()
    print(f'{name}: merged (serial reference) -> {res["merged"]}',flush=True);return res

# ---------------------------------------------------------------- status, roles and recovery
def campaign_c(directory:Path)->str:
    """C of the campaign's job names and comments (D.11): sha256 of the resolved directory, first 12 hex digits."""
    return hashlib.sha256(str(Path(os.path.realpath(directory))).encode()).hexdigest()[:12]
def campaign_p(directory:Path)->str:return hashlib.sha256((Path(directory)/'manifest.json').read_bytes()).hexdigest()[:12]

def ranges(ids):
    out=[];ids=sorted(ids)
    for k,g in itertools.groupby(enumerate(ids),lambda t:t[1]-t[0]):
        g=[x for _,x in g];out.append(str(g[0])if len(g)==1 else f'{g[0]}-{g[-1]}')
    return ','.join(out)

def windows(indices,size:int)->list[dict]:
    if size<1:raise ValueError('array window size must be positive')
    return [{'offset':off,'array':ranges([i-off for i in indices if off<=i<off+size])}for off in sorted({i//size*size for i in indices})]

def checkpoint_runtime(path:Path):
    try:
        with path.open('rb')as f:head=f.read(65536).decode('utf-8','replace')
        i=head.find('"runtime":')
        if i>=0:
            i+=len('"runtime":')
            while i<len(head)and head[i]in' \n\t\r':i+=1
            return json.JSONDecoder().raw_decode(head,i)[0]
    except ValueError:pass
    try:return load(path).get('runtime')
    except (OSError,ValueError):return None

def job_progress(directory:Path,m:dict)->dict:
    """{job id: (committed blocks, total blocks)} from the checkpoint files (existence only; merge validates). Block
    counts come from the manifest's job entries (the frozen boundaries, D.6): tasks.sqlite is not opened, and lane
    done markers are never read (A-ORC-4)."""
    out={}
    for j in m['jobs']:
        d=Path(directory)/'groups'/j['group']/'checkpoints'
        out[j['id']]=(sum((d/f'{block_name(j["shard"],k)}.json').exists()for k in range(j['blocks'])),j['blocks'])
    return out

def status_report(directory:Path,exclude=(),max_array:int=MAX_ARRAY,listing=False,fingerprints=True,verify_db=True):
    directory=Path(directory).resolve();m,I,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=True);missing=[];groups={}
    lines=[f'WARNING: pinned tools changed since planning ({", ".join(sorted(changes))}): run and every submission refuse; restore them, '
           'or merge/assemble by hand with --accept-tool-change']if changes else[]
    prog=job_progress(directory,m)
    for g in m['groups']:
        p,config=group_of(directory,m,g['name'])
        if verify_db:check_tasks_db(p,config)
        done_g=total_g=0;fps={}
        for j in (j for j in m['jobs']if j['group']==g['name']):
            have,nb=prog[j['id']]
            if fingerprints:
                for k in range(nb):
                    f=p/'checkpoints'/f'{block_name(j["shard"],k)}.json'
                    if f.exists():
                        fp=(checkpoint_runtime(f)or{}).get('fingerprint');key=fingerprint_key(fp)or'none'
                        e=fps.setdefault(key,{'checkpoints':0,'hosts':set(),'cpu_model':(fp or{}).get('cpu_model'),'glibc':(fp or{}).get('glibc')});e['checkpoints']+=1;e['hosts'].add((fp or{}).get('host'))
            done_g+=have;total_g+=nb
            if have<nb:missing.append(j['id'])
            if have<nb or listing:lines.append(f'job {j["id"]:6d} {g["name"]} shard {j["shard"]:4d}: {have}/{nb} blocks')
        fpl={k:{**v,'hosts':sorted(h for h in v['hosts']if h)}for k,v in fps.items()}
        groups[g['name']]={'committed':done_g,'total':total_g,'merged':(p/'merged.json').exists(),'fingerprints':fpl}
        lines.append(f'group {g["name"]}: {done_g}/{total_g} blocks, {"merged"if groups[g["name"]]["merged"]else"not merged"}')
    import lanes
    active=sorted(set(exclude)&set(missing));todo=[i for i in missing if i not in active];claims=lanes.claims_summary(directory)
    est=m['estimates'].get('suggested_time_seconds')
    result={'test':'C8_test_result.json','pilot_full':'C8_pilot_result.json','production':'C8_result.json','pilot_subset':'subset_summary.json'}[m['campaign_role']]
    return {'complete':not missing,'missing_jobs':missing,'active_not_resubmitted':active,'groups':groups,'result_present':(directory/result).exists(),'result_file':result,
            'tool_changes':changes,'threads':m['threads'],'suggested_time':hms(est)if est else None,'resubmit':windows(todo,max_array),
            'campaign_c':campaign_c(directory),'campaign_role':m['campaign_role'],'lanes':claims,'lines':lines}

def parse_ids(text):return [int(x)for x in filter(None,(text or'').split(','))]

def status(a):
    """Committed/total checkpoint blocks per job index; exit 0 only when every block is committed."""
    size=a.max_array
    if size is None:
        env=os.environ.get('C8_MAX_ARRAY','')
        if env and not env.isdigit():raise ValueError('C8_MAX_ARRAY must be a positive integer')
        size=int(env)if env else MAX_ARRAY
    if size<1:raise ValueError('--max-array must be a positive integer')
    r=status_report(a.directory,parse_ids(a.exclude),size,a.all,fingerprints=not a.fast);lines=r.pop('lines')
    if a.json:print(json.dumps(r))
    else:
        print('\n'.join(lines));print('result: '+(f'{r["result_file"]} present'if r['result_present']else f'no {r["result_file"]}'))
        cl=r['lanes']
        if cl['claims']or cl['failures']:print(f'lanes: {cl["claims"]} claimed indices {ranges(cl["claimed"])} by jobs {",".join(cl["owners"])}; {cl["failures"]} failure records'+
                                                 (f' (indices {ranges(cl["failed"])})'if cl['failed']else'')+'. Claims of finished jobs are released by slurm_submit.py lanes N or tools/lanes.py release-stale')
        if r['missing_jobs']:
            print(f'{len(r["missing_jobs"])} incomplete job indices: {ranges(r["missing_jobs"])}')
            if r['active_not_resubmitted']:print(f'still queued or running (not resubmitted): {ranges(r["active_not_resubmitted"])}')
            for w in r['resubmit']:
                print(f'resubmit: C8_RUN={shlex.quote(str(Path(a.directory).resolve()))} {shlex.quote(sys.executable)} -B {shlex.quote(str(ROOT/"tools/slurm_submit.py"))} '
                      f'window {w["offset"]}:{w["array"]}')
            print('then the merge once complete; or slurm_submit.py resubmit (arrays) or slurm_submit.py lanes N (lane mode), which also submit a merge that waits for the work')
        else:print('complete: every checkpoint block is committed')
    if r['missing_jobs']:sys.exit(1)

def role(a):print(campaign_role_of(a.directory.resolve()))

# Slurm job states (squeue %T). LIVE may still run or be released; TERMINAL finished for good; anything else is UNCERTAIN.
LIVE_STATES=frozenset('PENDING RUNNING SUSPENDED CONFIGURING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESIZING SIGNALING STOPPED RESV_DEL_HOLD POWER_UP_NODE'.split())
TERMINAL_STATES=frozenset('COMPLETED CANCELLED FAILED TIMEOUT NODE_FAIL BOOT_FAIL DEADLINE OUT_OF_MEMORY REVOKED'.split())
QUEUE_FORMAT='%i|%K|%T|%200j|%200k'
NAME_RE=re.compile(r'c8d3-((?:pilot_|prod_)?[a-z][a-z0-9_]{0,31})-([0-9a-f]{12})-([0-9a-f]{12})')
LINE_PREFIXES=('pilot_','prod_')   # the role prefixes of the pilot and production budget lines (tools/budget.py LINE_PREFIX)
COMMENT_RE=re.compile(r'c8d3:([0-9a-f]{12}):([0-9a-f]{12}):([0-9a-f]{12})')

def parse_queue(directory:Path,queue_text:str):
    """This campaign's records from `squeue --all --states=all -u <user> -h -r -o '%i|%K|%T|%200j|%200k'`: selected by
    the C of the name (D.11), role from the name (its line prefix pilot_ or prod_ removed); a comment whose C, P or T disagrees, or a P
    of another plan, is returned as `uncertain`."""
    c=campaign_c(directory)
    try:p=campaign_p(directory)
    except OSError:p=None
    tagged=[]
    for line in queue_text.splitlines():
        parts=[x.strip()for x in line.split('|')]
        if len(parts)!=5:continue
        jobid,task,state,name,comment=parts;mn=NAME_RE.fullmatch(name)
        if not mn or mn.group(2)!=c:continue
        rec={'jobid':jobid,'task':task,'state':state,'role':next((mn.group(1)[len(x):]for x in LINE_PREFIXES if mn.group(1).startswith(x)),mn.group(1)),'name':name,'comment':comment,'uncertain':None}
        mc=COMMENT_RE.fullmatch(comment)
        if state in LIVE_STATES and(not mc or mc.group(1)!=c or mc.group(3)!=mn.group(3)or (p is not None and mc.group(2)not in(p,'0'*12))):
            rec['uncertain']=f'job {jobid}: comment {comment!r} does not match its name or this plan'
        tagged.append(rec)
    return c,tagged

def queue_state(directory:Path,queue_text:str)->dict:
    directory=Path(directory).resolve();c,tagged=parse_queue(directory,queue_text)
    def refuse(code,msg):return {'refuse':{'code':code,'message':msg},'c':c}
    bad=[j for j in tagged if j['state']not in LIVE_STATES|TERMINAL_STATES or j['uncertain']]
    if bad:return refuse(69,'job(s) '+', '.join(j['uncertain']or f'{j["jobid"]}={j["state"]}'for j in bad)+' are completing, preempted, in an unrecognised state or '
                             'not of this plan; nothing submitted. Rerun once Slurm has settled them.')
    live=[j for j in tagged if j['state']in LIVE_STATES];work=[]
    for j in live:
        if j['role']in('merge','lane'):continue
        mm=re.fullmatch(r'off([0-9]+)',j['role'])
        if not mm or not j['task'].isdigit():return refuse(69,f'unexpected record for job {j["jobid"]} ({j["name"]}, task {j["task"]}); was squeue run with -r? nothing submitted')
        work.append({'index':int(mm.group(1))+int(j['task']),'jobid':j['jobid']})
    return {'refuse':None,'c':c,'live_merges':[j['jobid']for j in live if j['role']=='merge'],'merge_states':{j['jobid']:j['state']for j in live if j['role']=='merge'},
            'live_lanes':sorted({j['jobid']for j in live if j['role']=='lane'}),'live_work':work,'live_indices':sorted({w['index']for w in work})}

def recovery_plan(directory:Path,queue_text:str,max_array:int=MAX_ARRAY)->dict:
    q=queue_state(directory,queue_text)
    if q['refuse']:return q
    if q['live_merges']:return {'refuse':{'code':65,'message':f'merge job(s) {",".join(q["live_merges"])} of this campaign are still queued or running; scancel them (or let them finish), then rerun'},'c':q['c']}
    if q['live_lanes']:return {'refuse':{'code':65,'message':f'lane worker job(s) {",".join(q["live_lanes"])} of this campaign are live: lane mode and array mode are not mixed. '
                                                          'Add lane workers with slurm_submit.py lanes N, or wait for them to finish'},'c':q['c']}
    r=status_report(directory,q['live_indices'],max_array,fingerprints=False,verify_db=False);r.pop('lines')
    return {'refuse':None,'c':q['c'],'threads':r['threads'],'suggested_time':r['suggested_time'],'complete':r['complete'],'missing_jobs':r['missing_jobs'],
            'live_indices':q['live_indices'],'live_missing_not_resubmitted':r['active_not_resubmitted'],'arrays':r['resubmit'],
            'merge_waits_on_live_tasks':sorted({w['jobid']for w in q['live_work']})}

# The inherited a6ce987 sbatch option allowlist (production.py:558-580; D.16), kept as the reference of
# tools/slurm_submit.py's campaign allowlist, which is this one WITHOUT begin, job-name, hold and requeue (D.11: --begin,
# -J, --hold and --requeue are refused on every path; tests/test_submit.py compares the two).
SBATCH_LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user begin signal job-name exclude nodelist licenses wckey'.split())
SBATCH_LONG_FLAG=frozenset('requeue no-requeue hold'.split())
SBATCH_SHORT_VALUE=frozenset('ApqCtcJxwL')

def check_args(a):
    """check-sbatch-args: the campaign allowlist of tools/slurm_submit.py (C8_SBATCH_ARGS, C8_MERGE_SBATCH_ARGS, extra
    options of `lanes N` and the array entry points); exit 64 with the reason, 0 when every token is allowed."""
    import slurm_submit as ss
    toks=a.args[1:]if a.args[:1]==['--']else a.args
    try:ss.parse_options(toks,'sbatch options',positional=False,allow=ss.CAMPAIGN_ALLOW)
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);sys.exit(r.code)

def recover(a):print(json.dumps(recovery_plan(a.directory,Path(a.queue).read_text(),a.max_array or MAX_ARRAY)))
def tag(a):print(campaign_c(a.directory))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True,help='a fresh random integer in [0, 2^63); never reuse one')
    q.add_argument('--pilot',action='store_true',help='allocation source: a uniform per-graph count per replicate (--points, default 4096)')
    q.add_argument('--points',type=int,help='--pilot points per graph per replicate (power of two; >= 4096 unless test-only)')
    q.add_argument('--design',type=Path,help='allocation source: a frozen design bundle')
    q.add_argument('--graphs',type=Path,help='a selection file (schema c8-d3-selection-1; with --pilot)')
    q.add_argument('--group-replicates',action='append',help='SECTOR:L=R: per-group replicates (both campaigns), e.g. power:8=16')
    q.add_argument('--replicates',type=int,help=f'--pilot replicates (default {DEFAULT_REPLICATES})')
    q.add_argument('--test-graphs',help='N|all: an INCOMPLETE test-only plan restricted to N graphs per group (all: every graph)')
    q.add_argument('--test-selection',choices=['cheapest','stratified'],default='cheapest')
    q.add_argument('--test-only',action='store_true',help='a test-only plan with every graph')
    q.add_argument('--forbid-seeds-from',type=Path,action='append',help='seed log ($C8_SEEDS) or list; required for non-test plans')
    q.add_argument('--backend',choices=['decimal','gmp'],default='gmp')
    q.add_argument('--cost-model',help='measured seconds per point (campaign:sector:L:graph), or the synthetic fixture (validation plans only)')
    q.add_argument('--prior-cost-model',help='the prior-model basis of a calibration refresh (--plan-role cost_refresh; D.14)')
    q.add_argument('--prior-factor',type=float,default=2.0)
    q.add_argument('--bootstrap-chunk',type=int,help=f'the bootstrap basis: fixed tasks of min(P, n_g) points (default {BOOTSTRAP_CHUNK}); needs --shards')
    q.add_argument('--plan-role',default='campaign',help='campaign|cost_sweep|cost_refresh|flag_check|validation (D.2)')
    q.add_argument('--threads',type=int,default=DEFAULT_THREADS,help='planned lane width');q.add_argument('--checkpoint-tasks',type=int,help='default max(16 x threads, 256)')
    q.add_argument('--block-seconds',type=float,help=f'predicted seconds per checkpoint block at the lane width (default {BLOCK_SECONDS:g}; D.6)')
    q.add_argument('--task-seconds',type=float,help=f'target task length (default {TASK_SECONDS:g})');q.add_argument('--max-task-seconds',type=float,default=MAX_TASK_SECONDS)
    q.add_argument('--min-chunk',type=int,help=f'smallest task in points (default {MIN_CHUNK})')
    q.add_argument('--index-hours',type=float,help=f'index sizing (default {INDEX_HOURS:g} h at the lane width)');q.add_argument('--shards',type=int,help='shards per group (instead of --index-hours)')
    q.add_argument('--max-tasks',type=int,default=MAX_TASKS,help='per campaign');q.add_argument('--max-checkpoints',type=int,default=MAX_CHECKPOINTS)
    q.add_argument('--max-files',type=int,help='projected Lustre files (on Expanse also bounded by the session file budget, D.7)')
    q.add_argument('--mp-check',default='on',help='MP self-check: on|off|stride16 (C.4)')
    q.add_argument('--numerics',default='exact');q.add_argument('--approved-numerics-change')
    q.add_argument('--approved-fallback',help='the user reference that approves a non-test plan from a fallback bundle (HD16)')
    q.add_argument('--reserve-seed',type=Path,help='the site\'s seed log ($C8_SEEDS): the seed rechecked and reserved for this campaign (its resolved directory) under the session lock before anything is built or published (HD6, S2-002; required with --forbid-seeds-from and one of those logs; slurm/plan.sh and tools/sweep.py pass it)')
    q.add_argument('--scratch',help='node-local scratch (outside a job: test-only plans only, D.4)');q.set_defaults(func=plan)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int);q.add_argument('--threads',type=int);q.add_argument('--scratch')
    q.add_argument('--max-blocks',type=int,help='commit at most this many new blocks, then stop (time slicing, tests)');q.set_defaults(func=run)
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--group');q.add_argument('--jobs',type=int,default=1,help='phase-2 processes (groups)')
    q.add_argument('--parse-jobs',type=int,help='phase-1 processes (shards; default --jobs)');q.add_argument('--scratch')
    q.add_argument('--fan-in',type=int,default=MERGE_FAN_IN,help='runs merged at once (bounded by RLIMIT_NOFILE - 32)');q.add_argument('--serial',action='store_true',help='the reference merge')
    q.add_argument('--accept-tool-change',action='store_true');q.set_defaults(func=merge)
    q=s.add_parser('status');q.add_argument('directory',type=Path);q.add_argument('--all',action='store_true');q.add_argument('--json',action='store_true')
    q.add_argument('--fast',action='store_true');q.add_argument('--exclude');q.add_argument('--max-array',type=int,default=None);q.set_defaults(func=status)
    q=s.add_parser('role',help='print the campaign_role (D.3a)');q.add_argument('directory',type=Path);q.set_defaults(func=role)
    q=s.add_parser('recover');q.add_argument('directory',type=Path);q.add_argument('--queue',required=True,help=f"file with 'squeue --all --states=all -u <user> -h -r -o {QUEUE_FORMAT}' output")
    q.add_argument('--max-array',type=int,default=MAX_ARRAY);q.set_defaults(func=recover)
    q=s.add_parser('tag',help="print the campaign's C (D.11)");q.add_argument('directory',type=Path);q.set_defaults(func=tag)
    q=s.add_parser('check-sbatch-args',help='the campaign allowlist of user sbatch options (D.11, D.16)');q.add_argument('args',nargs=argparse.REMAINDER);q.set_defaults(func=check_args)
    a=p.parse_args(argv)
    try:a.func(a)
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);sys.exit(r.code)
    except OSError as e:
        if e.errno in QUOTA_ERRNOS:print('C8: '+str(QuotaRefused(e,getattr(e,'filename',None)or'?','write')),file=sys.stderr);sys.exit(74)
        if isinstance(e,(FileExistsError,FileNotFoundError)):print(f'C8: {e}',file=sys.stderr);sys.exit(1)
        raise
    except (ValueError,RuntimeError)as e:print(f'C8: {e}',file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
