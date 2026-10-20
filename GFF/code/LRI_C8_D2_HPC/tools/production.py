#!/usr/bin/env python3
"""Plan, run, check, recover and merge complete C8(2) campaigns (24 groups: campaigns a/b x sectors free/power x
loops 3..8; PLAN.md component D).

Scientific point identities (campaign, sector, loop, replicate, graph, point) do not depend on scheduler, index,
chunk, checkpoint or thread ids. The native worker runs only from a verified job-private copy of the planned
executable and inputs. A claim (`run --index`) reads its own per-index task file, pinned in the manifest, and never
opens the group's tasks.sqlite. Merges are parallel over shards and groups, with an external merge of bounded fan-in
whose final pass adds in the serial order, so every output is byte-identical to the serial merge. The external merge's
intermediate runs live in a persistent per-campaign work directory (<campaign>/merge_work, or under --work-dir), named by
the identities of their inputs, so an interrupted merge resumes from its completed runs, each reused only after it is
verified to hold exactly the merge of its inputs (rows, order and an order-independent keyed digest of its lines, the
key drawn afresh by each merge and the expectation coming from phase 1's fresh runs); a group's runs are removed only
after its merged.json is published.
Phase 1 streams each shard block by block (sorted spill runs merged with the same fan-in), so a merge process holds
at most one checkpoint block plus F rows, whatever the number of rows per shard.
A claim pins the campaign's CPU vendor at its first claim (RUN/cpu_vendor.json) and refuses another vendor (exit 64;
F5); likewise the runtime compatibility identity (RUN/runtime_identity.json: glibc and the content hashes of the
interpreter and every loaded library, not the host, Slurm ids or CPU model; X8), which run-skip, the duplicate check and
both merges also require of every checkpoint. A plan of a design bundle keeps a verified copy of the bundle files
(<campaign>/design_bundle; X9), which assemble and combine use, so a batch copied to another site needs no original
bundle path (or give --bundle DIR, verified against the pinned digest). Non-test plans refuse a cost model measured
under other numerics (X10). A claim logs one 'claim_io {json}' line at exit (R07, F9): /proc/self/io rchar, the native
children's rchar, the fingerprint's bytes and its own bytes per category, and the non-own bytes that tools/claim_io.py
compares.
Allow-lists (Stage 6): every NON-test plan refuses numerics outside APPROVED_PROFILES ({dd+mp256}; --pilot or --design)
and a --rates map outside APPROVED_RATES (empty: R7 stays off); a non-test --pilot under any numerics other than exact
or under --rates is refused unless APPROVED_PROFILE_PILOTS holds it (empty: the smoke and the pilot stay exact); every
non-test plan whose numerics are not exact runs only an executable that a recorded, passed, full-scale J-FLAG gate
covers (route (b): the bundle's gate records; any other plan: --numerics-gate RECORD); test-only plans (gates, sweeps)
take any implemented profile or valid map with --approved-numerics-change.
Route (b) (host decision 2026-10-05): `plan --design B` of a bundle that tools/design.py froze from an EXACT pilot
under an approved profile (`freeze --numerics P`, P in APPROVED_PROFILES, the user-approved set {dd+mp256}) needs
`--numerics P --approved-numerics-change "<ref>"` and a `--cost-model` measured under P; a profile outside the set, a
bundle whose numerics differ from its pilot's without the route-(b) record, a cost model of another numerics identity
and (non-test) an executable that none of the bundle's J-FLAG gate records passed are refused, as is (any plan) a bundle
whose gate entries lack the X1-X3 evidence of the current design.check_gate (gate_evidence_missing: a bundle frozen with
a gate record check_gate now refuses); the manifest records the route (`numerics_route`: profile, approvals, gates,
exact pilot, both cost models, the executable and whether it was gated).
Stage-6 fix round 2: every native worker runs in the controlled OpenMP environment (common.omp_child_env: no inherited
OMP_*, GOMP_* or KMP_* control such as OMP_THREAD_LIMIT; OMP_NUM_THREADS = the claim's threads, OMP_DYNAMIC=FALSE,
close binding on cores), whatever the entry point (lane, array, sweep, direct), and an ELF worker's team is watched
while it runs (common.TeamWatch): one that has not shown the requested team after TEAM_DEADLINE_SECONDS (60 s) and has
used TEAM_CPU_SECONDS (30 s) of CPU time is stopped and the claim refused with exit 64, nothing of the block kept; each
checkpoint records the team (runtime.omp_team; Y2). A
claim of a dynamic ELF worker refuses (64) an incomplete runtime fingerprint (a failed or partial ldd probe, an
unhashed library or interpreter) before any pin is published or block run (Y6). Without the runtime pin, a first
checkpoint whose fingerprint is missing or malformed makes both merges refuse instead of disabling the identity check
(Y8). A plan --design refuses bundle replicates outside the production bounds (powers of two in [32, 128]) unless the
bundle is --test-only, and fewer than 2 in any bundle (Y10).
Stage-6 fix round 3: a NON-test plan runs only an executable whose build record (bin/<exe>.build.json, written by make)
is a valid record of that very build: present and readable, schema c8-d2-build-record-1, its executable name, sha256,
backend and NUMERICS the plan's, no diagnostic kind, the required numerical flags in effect and no development option
(Z3; a test-only plan still accepts a missing record with a warning). A NON-test plan registers its base seed in the
seed log named by its first --forbid-seeds-from (a tools/seeds.py log, $C8_SEEDS) itself: after every other check and
the build of the staging directory, under the log's lock, the fresh log is re-read, the seed re-checked against it
(a seed registered meanwhile by another plan is refused, nothing published), the seed appended (source = the campaign
directory, as `tools/seeds.py add RUN` writes it) and only then is the campaign published, still under the lock; so no
direct command can publish a non-test campaign whose seed is not in the log (Z15). Test-only plans register nothing.
Stage-6 fix round 4: a claim refuses (64) to run under a dynamic-loader override (LD_PRELOAD, LD_AUDIT,
LD_DYNAMIC_WEAK and their macOS counterparts; common.loader_overrides), which would decide which implementation of an
interposed function runs without changing any library's bytes; the order of objects preloaded through
/etc/ld.so.preload and a set GLIBC_TUNABLES are part of the runtime identity (W7). A campaign whose executable a J-FLAG
gate admitted (numerics_route.executable_gated) is bound to the libgmp that gate validated (gate_gmp_binding: the
gates' gmp_library.profile for this executable): a claim whose worker resolves another libgmp refuses (64) before any
pin is published or block run, and run-skip, the duplicate check and both merges refuse a checkpoint of another libgmp
(W8). A claim streams its index's task rows one block at a time from a job-private snapshot of its task file, copied
and verified against the manifest pin first (snapshot_tasks, snapshot_blocks; staging uses the streamed, verified
reader too), so a claim holds one block of rows whatever its index's size, and est_peak_bytes adds the per-block rows
and the plan metadata every claim parses (W9). Calibration rows are used only under the numerics and rates identity
they were measured with (calibration_row; W11).
"""
from __future__ import annotations
import argparse,decimal,hashlib,heapq,itertools,json,math,os,re,shlex,shutil,signal,sqlite3,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
from common import (ROOT,Refuse,TeamWatch,canon,checked,digest,dump,elf_kind,fingerprint,fingerprint_key,fingerprint_malformed,fingerprint_problems,load,
                    loader_overrides,loader_refusal,numerics_name,object_hash,omp_child_env,omp_inherited,pow2,publish,read_verified,replace_file,
                    runtime_identity,runtime_identity_key,team_message,umask_mode,utc)
D=decimal.Decimal
SCHEMA='c8-d2-production-1';GROUP_SCHEMA='c8-d2-group-1';MERGED_SCHEMA='c8-d2-merged-1';NATIVE_SCHEMA='c8-d2-hpc-native-1'
COST_SCHEMA='c8-d2-cost-model-1';RATES_SCHEMA='c8-d2-rates-1';DESIGN_SCHEMA='c8-d2-design-1';BOOT_SCHEMA='c8-d2-bootstrap-proxy-1'
BUILD_SCHEMA='c8-d2-build-1';INPUTS_SCHEMA='c8-d2-hpc-inputs-1';BUILD_RECORD_SCHEMA='c8-d2-build-record-1'
ORDER=8;GAMMA='gamma_d2_8.txt';TASK_MAGIC='C8D2TASKS1'
# claim_io record schema: -2 reads the staged members exactly (F12); -1 (tools before the F12 fix) read the pack buffered
CPU_PIN='cpu_vendor.json';CPU_PIN_SCHEMA='c8-d2-cpu-vendor-1';VENDOR_REFUSED=64;CLAIM_IO_SCHEMA='c8-d2-claim-io-2'
# X8: the campaign's runtime compatibility identity (common.runtime_identity), pinned by the first claim like the CPU
# vendor; a claim on another library stack is refused with the same exit status (64), so a lane releases and stops.
RUNTIME_PIN='runtime_identity.json';RUNTIME_PIN_SCHEMA='c8-d2-runtime-pin-1'
# X9: the design-bundle files a campaign needs (design_meta.json, design.json, counts/*), copied into the campaign at
# plan time and verified through the manifest's meta_sha256, so assemble and combine work after a batch is copied.
PINNED_BUNDLE='design_bundle'
# Tools whose bytes the plan pins: run, merge, status and assemble refuse a changed one (merge and assemble accept it
# only with --accept-tool-change, which is recorded). design.py, combine.py and the accounting tools are not pinned.
PINNED_TOOLS=('production.py','common.py','prepare_inputs.py','assemble.py','lanes.py','slurm_submit.py','stage_runtime.py')
SMALL_INPUTS=('gamma_d2_8.txt','two_loop.json','inventory.json')
MAX_ARRAY=1000          # common Slurm MaxArraySize (indices 0..999; symmetry allows 1000, Expanse 999)
CAMPAIGNS=('a','b');SECTORS=('free','power');LOOPS=tuple(range(3,ORDER+1))
GROUPS=[(c,s,L)for c in CAMPAIGNS for s in SECTORS for L in LOOPS]
DEFAULT_RATES={'a':'.8','b':'.9'}
NET_BITS={'a':52,'b':60}
EFFICIENCY=0.9          # planning: busy fraction of a lane's cores (index sizing and the lane deadline)
PILOT_MIN_POINTS=4096
# Y10: the replicates per (sector, L) of a design bundle, checked by every plan independently of design.py: a
# production (non-test) bundle's are powers of two in [32, 128] (PLAN component E: design.py freeze's --min-replicates 32
# and --max-replicates 128); a --test-only bundle's may be smaller, never below 2 (assemble needs two replicate rows per
# group: a one-replicate campaign would run and merge but could not be assembled).
PRODUCTION_REPLICATES=(32,128);MIN_REPLICATES=2
TASK_SECONDS=60.;MAX_TASK_SECONDS=120.;MIN_CHUNK=256;INDEX_HOURS=1.5
MAX_TASKS=5*10**7;MAX_CHECKPOINTS=2*10**5;EXPANSE_FILE_CAP=10**6;PLAN_TASKS_IN_JOB=10**6
PROMOTED_SCRATCH_BYTES=4*2**20;BASE_PEAK_BYTES=2**29   # est_peak_bytes = max block kernel bytes + threads x 4 MB + 0.5 GB
# W9 (S6-C-R4-03, Stage-6 fix round 4): what a claim holds besides the kernels, added to est_peak_bytes. A claim streams
# its task rows one block at a time (snapshot_blocks), so the rows it holds are those of one block of at most
# checkpoint_tasks tasks: the row tuples, the block's task file text, the native output parsed, its canonical JSON
# (object_hash) and the indented checkpoint (dump). Measured with tracemalloc on Python 3.10: about 10 KiB per task row
# (an L3 row, the widest jet); counted at 16 KiB. Every claim also parses the manifest (about 1.1 KiB per job entry)
# and inputs/inventory.json (about 1.0 KiB per row: 24 MiB for the 24,173 rows); counted at 2 KiB each.
TASK_ROW_PEAK_BYTES=16*2**10;JOB_ENTRY_BYTES=2*2**10;INVENTORY_ROW_BYTES=2*2**10
TASK_READ_CHUNK=1<<18   # snapshot_tasks and snapshot_blocks read the task file in pieces of at most 256 KiB
PLAN_WRITE_ROWS=200000  # plan writes and self-checks a per-index task file in pieces of this many rows
# Merge projection (R06): phase-1 rows per second per process and phase-2 rows per second per pass, measured by
# tests/merge_scale.py (docs/PERFORMANCE.md); conservative planning values, never a gate on data.
MERGE_PHASE1_ROWS_PER_S=4000.;MERGE_PHASE2_ROWS_PER_S=60000.;MERGE_FAN_IN=64;MERGE_MAX_HOURS=12.
C7_MESSAGE=('{d} was planned by the C7(2) tools (manifest schema {s}). LRI_C8_D2_HPC does not run, merge or assemble it: '
            'use a checkout of LRI_C7_D2_HPC@a55958f, whose tool hashes the plan pins.')
# Base seeds of the C7(2) 2026 campaigns (legacy additive seed arithmetic) and the archived C7(2) net bases.
USED_2026={8885400701634497064:'C7(2) symmetry production run1-20260930-m4096',326694507229394458:'C7(2) Expanse plan run1-20260930-m4096 (abandoned)',
           2765894070584243940:'C7(2) Expanse pilot (job 54545302)'}
ARCHIVED_NET_BASES={12983:'archived C7(2) pilot nets',837425:'archived C7(2) campaign-a nets',915437:'archived C7(2) campaign-b nets'}
# Route (b) allow-list (host decision 2026-10-05; PLAN-REVIEW-LOG "Stage-5 close"): the user-approved numerics profiles
# that a bundle frozen from an EXACT pilot may carry (design.py freeze --numerics P; its allocation re-costed with a cost
# model measured under P, its variance the exact pilot's), each with its approval reference. Every other profile is
# refused by design.py freeze and report, by plan --design and (below) by every non-test plan. Changing this set is a
# user decision.
APPROVED_PROFILES={'dd+mp256':'user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'}
# The allow-lists apply to EVERY non-test plan (Stage 6, the allow-list scope): a non-test plan refuses numerics outside
# APPROVED_PROFILES (plan --pilot --numerics P, and plan --design of any bundle whose numerics are not exact: route (a),
# a bundle frozen from a pilot under P, and route (b)) and a --rates map whose rates identity (the sha256 of the map
# file) is not in APPROVED_RATES. APPROVED_RATES is empty: the user keeps R7 off (check-in 2026-10-05). Test-only plans
# (the J-FLAG gates' and the sweeps' measurements) take any implemented profile and any valid map with
# --approved-numerics-change. Changing either set is a user decision.
APPROVED_RATES:dict={}
# Profile pilots (Stage 6; the user's decision of 2026-10-05: the smoke and the pilot stay on the EXACT path). A
# NON-test `plan --pilot` runs exact at the default rates; a non-test pilot under numerics P (P in APPROVED_PROFILES)
# or under a rate map (its rates identity in APPROVED_RATES) is refused unless (P, rates identity) is a key here, with
# the user's approval reference as the value: {('dd+mp256', 'default'): '<ref>'} would allow a dd+mp256 pilot (route
# (a)), {('exact', '<sha256 of the map>'): '<ref>'} a measurement under an approved R7 map. Empty: no profile pilot has
# the user's go. Test-only pilots (--test-graphs: the J-FLAG gates, sweeps, the smoke) are not affected. Changing this
# set is a user decision.
APPROVED_PROFILE_PILOTS:dict={}

def np_():
    import numpy
    return numpy

def dbopen(path:Path,readonly=False):
    # Read-only opens use a percent-encoded file: URI, so '#', '?', '%' or spaces in a campaign path are not URI syntax.
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro'if readonly else str(path),uri=readonly)
    c.execute('PRAGMA cache_size=-8192');c.execute('PRAGMA temp_store=FILE');return c

def group_name(c:str,s:str,L:int)->str:return f'{c}_{s}_L{L}'
def block_name(shard:int,part:int)->str:return f's{shard:06d}_p{part:06d}'
def stratum_of(sector:str,L:int,primitive:bool)->str:
    """Design strata (component E): free L3..L8, the free L8 primitives, power L3..L8."""
    return 'free_L8_primitive'if (sector=='free'and L==8 and primitive)else f'{sector}_L{L}'
def hms(seconds)->str:
    d,s=divmod(int(math.ceil(seconds)),86400);return (f'{d}-'if d else'')+time.strftime('%H:%M:%S',time.gmtime(s))

# ---------------------------------------------------------------- Sobol nets (A-L5; every order-8 shape, A-ORC-7)
def reachable_columns(max_count:int)->int:
    """Direction columns a stratum of max_count points can reach: points 0..n-1 use columns 0..ceil(log2 n)-1."""
    return 0 if max_count<=1 else (max_count-1).bit_length()

def gray_state(sv,shift,n:int):
    """State of point n as the native Net computes it: shift XOR the direction columns of the set bits of n ^ (n >> 1)."""
    np=np_();st=np.asarray(shift,dtype=np.uint64).copy();g=n^(n>>1)
    while g:
        j=(g&-g).bit_length()-1;st^=np.asarray(sv,dtype=np.uint64)[:,j];g&=g-1
    return st

def gray_states(sv,shift,k:int):
    """States of points 0..2^k-1 (shape (2^k, dim)), equal to gray_state for every n."""
    np=np_();sv=np.asarray(sv,dtype=np.uint64);st=np.empty((1<<k,sv.shape[0]),dtype=np.uint64);st[0]=np.asarray(shift,dtype=np.uint64)
    for j in range(k):
        h=1<<j;st[h:2*h]=st[h-1::-1]^sv[:,j][None,:]
    return st

def check_public(sv,shift,public,k:int,bits:int)->None:
    """(a) the public random_base2(k) points equal the exported states at the same indices (columns 0..k-1)."""
    np=np_()
    if public.shape!=(1<<k,len(shift))or not np.array_equal(gray_states(sv,shift,k).astype(np.float64)/2**bits,public):
        raise RuntimeError(f'Sobol export failed the public-API comparison (columns 0..{k-1})')

def check_fresh(sv,shift,fresh_sv,fresh_shift,m:int)->None:
    """(b) an identically seeded fresh engine has the same direction integers (columns 0..m-1, all bits) and shift."""
    np=np_();sv=np.asarray(sv,dtype=np.uint64);fresh_sv=np.asarray(fresh_sv,dtype=np.uint64)
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
    linearly independent over GF(2)."""
    np=np_()
    for d,row in enumerate(np.asarray(sv,dtype=np.uint64)):
        cols=[int(x)for x in row[:m]]
        if any(c==0 or c>=1<<bits for c in cols):raise RuntimeError(f'Sobol direction integer zero or out of range (dimension {d}, columns 0..{m-1})')
        if gf2_rank(cols)!=m:raise RuntimeError(f'Sobol direction columns 0..{m-1} of dimension {d} are linearly dependent over GF(2)')

def make_net(path:Path,B:int,dim:int,bits:int,seed:int,max_count:int|None=None):
    """Export B independently scrambled Sobol direction matrices and check every column a stratum of max_count points can
    reach (all of them when None) by (a) public-API points, (b) a fresh engine read back from the written file, (c) a
    GF(2) structure check. Work is O(2^min(m,16) + m^2) per replicate, never proportional to the sample index."""
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
            check_public(sv,shift,engine.random_base2(k),k,bits);shifts.append(shift)
            f.write(sv.astype('<u8').tobytes())
    raw=Path(path).read_bytes()
    if struct.unpack('<III',raw[:12])!=(B,dim,bits)or len(raw)!=12+B*dim*bits*8:raise RuntimeError('Sobol export has the wrong size')
    for b,s in enumerate(seeds):
        exported=np.frombuffer(raw,dtype='<u8',count=dim*bits,offset=12+b*dim*bits*8).reshape(dim,bits)
        fresh=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s);check_fresh(exported,shifts[b],fresh._sv,fresh._shift,m);check_structure(exported,m,bits)
    return {'scipy':scipy.__version__,'seed':seed,'B':B,'dim':dim,'bits':bits,'sha256':digest(path),'columns_checked':m,
            'public_API_points_checked':(1<<k)*B,'checks':['public_api','fresh_engine','gf2_structure']}

# ---------------------------------------------------------------- seeds (D9)
def derive_seeds(seed:int,campaign:str,sector:str,L:int)->dict:
    """Native (digital-shift) and net seeds of one group: SHA-256 of 'c8-d2|<seed>|<campaign>|<sector>|L<L>|<role>'
    (first 8 bytes, little endian, mod 2^63). There is no legacy seed scheme at order 8."""
    if campaign not in CAMPAIGNS or sector not in SECTORS:raise ValueError('unknown campaign or sector')
    h=lambda role:int.from_bytes(hashlib.sha256(f'c8-d2|{seed}|{campaign}|{sector}|L{L}|{role}'.encode()).digest()[:8],'little')%(2**63)
    return {'native':h('native'),'net':h('net')}

def _c7_legacy(seed:int,campaign:str,sector:str,L:int)->dict:
    off=(0 if sector=='free'else 0x156ad267)+(0 if campaign=='a'else 0x614ef703)
    return {'native':(seed+L*1279+off)%(2**64),'net':(seed+18743*L+off*13)%(2**63)}

def seed_registry()->dict:
    """Known used seeds: base, native (digital-shift) and net seeds of the archived C7(2) records and plans (reference/)
    and of the C7(2) 2026 campaigns with their derived group seeds (legacy additive arithmetic, C7(2)'s 20 groups)."""
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
            for L in range(3,8):net[int(c['net_seed'])+7893*L]=str(pm.relative_to(ROOT))
    for b,src in ARCHIVED_NET_BASES.items():
        bases[b]=src
        for L in range(2,8):net[b+7893*L]=src
    for b,src in USED_2026.items():
        bases[b]=src
        for c in CAMPAIGNS:
            for s in SECTORS:
                for L in range(3,8):x=_c7_legacy(b,c,s,L);native[x['native']]=src;net[x['net']]=src
    return {'bases':bases,'native':native,'net':net}

def read_seed_file(path:Path)->dict:
    """{seed: source} from a forbidden-seed file: tools/seeds.py's log (schema c8-d2-seeds-1), a design bundle's
    forbidden list, or a plain JSON list of integers."""
    return seed_entries(json.loads(Path(path).read_bytes()),path)

def seed_entries(doc,path)->dict:
    """{seed: source} of a parsed forbidden-seed file (read_seed_file) or of a seed log read under its lock (Z15)."""
    items=doc.get('seeds')if isinstance(doc,dict)else doc
    if not isinstance(items,list):raise ValueError(f'{path}: not a seed list (tools/seeds.py log or a JSON list of integers)')
    out={}
    for x in items:
        s=x.get('seed')if isinstance(x,dict)else x
        if isinstance(s,bool)or not isinstance(s,int):raise ValueError(f'{path}: seed entry {x!r} is not an integer')
        out[s]=f'{path} ({x.get("source")or x.get("label")or"listed"})'if isinstance(x,dict)else f'{path}'
    return out

def seed_refusal(seed:int,forbidden:dict)->str|None:
    """Why `seed` may not be used: it equals a listed seed, base or derived (the C7(2) registry: archived and 2026 base
    seeds and their derived native and net seeds; every forbidden base seed and its C8 group seeds), or one of its own
    C8 group seeds equals one."""
    r=seed_registry()
    if seed in r['bases']:return f'seed {seed} is a known archived or used base seed ({r["bases"][seed]})'
    if seed in forbidden:return f'seed {seed} is a forbidden seed ({forbidden[seed]})'
    listed={**r['net'],**r['native']}
    for b,src in forbidden.items():
        for c,s,L in GROUPS:x=derive_seeds(b,c,s,L);listed[x['native']]=src;listed[x['net']]=src
    if seed in listed:return f'seed {seed} equals a derived group seed of {listed[seed]}'
    every={**listed,**r['bases'],**forbidden}
    for c,s,L in GROUPS:
        x=derive_seeds(seed,c,s,L)
        for role in('native','net'):
            if x[role]in every:return f'group {group_name(c,s,L)} would reuse the {role} seed of {every[x[role]]}'
    return None

# ---------------------------------------------------------------- inputs (the package's inputs/ or a test fixture)
class Inputs:
    """An inputs folder relative to the package (inputs/, or tests/fixtures/inputs_mini selected with C8_INPUTS) and its
    manifest; a fixture's L3..L7 packs and small inputs are the package's own (shared_with_package)."""
    def __init__(self,rel:str,m:dict):self.rel=rel;self.dir=ROOT/rel;self.m=m
    @property
    def fixture(self)->bool:return bool(self.m.get('test_fixture'))
    def where(self,name:str)->Path:
        if name in self.m['sha256']:return self.dir/name
        if name in (self.m.get('shared_with_package')or{}):return ROOT/'inputs'/name
        raise KeyError(f'{name} is not listed in {self.rel}/manifest.json')
    def sha(self,name:str)->str:return self.m['sha256'].get(name)or self.m['shared_with_package'][name]
    def pack(self,sector:str,L:int)->Path:return self.where(f'packs/{sector}_L{L}.pack')
    def has(self,name:str)->bool:return name in self.m['sha256']or name in (self.m.get('shared_with_package')or{})

def inputs_rel_from_env(env=None)->str:
    env=os.environ if env is None else env;v=env.get('C8_INPUTS')
    if not v:return 'inputs'
    p=Path(v).resolve()
    try:return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:raise ValueError(f'C8_INPUTS={v} is not inside the package {ROOT}; test inputs live in the package (tests/fixtures/inputs_mini)')

def load_inventory(I:Inputs)->dict:return load(I.where('inventory.json'))

def verified_inventory(m:dict)->dict:
    """W23's class (Stage-6 fix round 4): a planned campaign's inputs inventory, parsed from the bytes whose sha256 the
    campaign's pinned inputs manifest lists (manifest inputs_manifest_sha256 -> inputs manifest -> inventory.json),
    each file read once; assemble and combine use it instead of re-reading inventory.json after verify_base checked it."""
    im=read_verified(ROOT/m['inputs']/'manifest.json',m['inputs_manifest_sha256']);I=Inputs(m['inputs'],im)
    return read_verified(I.where('inventory.json'),I.sha('inventory.json'))

# ---------------------------------------------------------------- frozen rate maps (R7 only; R04)
RATE_TEXT=re.compile(r'(?:0?\.[0-9]+|1(?:\.0*)?|0\.[0-9]*[1-9][0-9]*)')

def validate_rates(data:bytes,im_sha:str,inv:dict,schema:str=RATES_SCHEMA)->dict:
    """A frozen rate map (schema c8-d2-rates-1; design.py rates of another package's pilot passes <prefix>-rates-1, H6)
    for this inputs manifest: complete coverage of every graph of every (sector, L) in both campaigns, no unknown graph,
    decimal strings in (0, 1], campaigns a and b different per graph."""
    try:doc=json.loads(data)
    except ValueError as e:raise ValueError(f'rate map is not JSON: {e}')
    if not isinstance(doc,dict)or doc.get('schema')!=schema:raise ValueError(f'rate map schema is not {schema}')
    if doc.get('inputs_manifest_sha256')!=im_sha:raise ValueError('rate map was made for another inputs manifest (inputs_manifest_sha256)')
    r=doc.get('rates')
    if not isinstance(r,dict)or set(r)!=set(CAMPAIGNS):raise ValueError('rate map needs exactly the campaigns a and b')
    for s in SECTORS:
        for L in LOOPS:
            want={str(x['id'])for x in inv[s][str(L)]}
            for c in CAMPAIGNS:
                got=((r[c].get(s)or{}).get(str(L)))
                if not isinstance(got,dict):raise ValueError(f'rate map: campaign {c} has no {s} L{L} table')
                miss=sorted(want-set(got),key=int);extra=sorted(set(got)-want,key=lambda x:(len(x),x))
                if miss:raise ValueError(f'rate map: campaign {c} {s} L{L} has no rate for graph {miss[0]} ({len(miss)} missing)')
                if extra:raise ValueError(f'rate map: campaign {c} {s} L{L} lists unknown graph {extra[0]}')
                for g,v in got.items():
                    if not isinstance(v,str)or not RATE_TEXT.fullmatch(v)or not D(0)<D(v)<=D(1):raise ValueError(f'rate map: campaign {c} {s} L{L} graph {g}: {v!r} is not a decimal string in (0, 1]')
            for g in want:
                if D(r['a'][s][str(L)][g])==D(r['b'][s][str(L)][g]):raise ValueError(f'rate map: {s} L{L} graph {g} has equal rates in campaigns a and b')
    return doc

# ---------------------------------------------------------------- cost bases (measured, calibrated proxy, bootstrap)
COST_KEY=re.compile(r'(a|b):(free|power):[3-8]:[0-9]+')
POOLED_KEY=re.compile(r'(free|power):[3-8]:[0-9]+')

def load_cost_model(path:Path,backend:str,rates_identity:str,test_only:bool,data:bytes|None=None,numerics:str|None=None,
                    exceptions:list|None=None)->dict:
    """A --cost-model file, validated in full before anything is created: schema, dimension, order, backend, rates
    identity, numerics identity (when `numerics`, the plan's profile, is given; X10), and a non-empty map of
    campaign:sector:L:graph keys (R05; a pooled sector:L:graph key is refused) to positive finite seconds per point.
    A NON-test plan refuses a cost model measured under other numerics (or recording none): its task sizes, index
    sizes and lane deadlines would come from another profile's speed. A test-only plan (gates, sweeps) keeps it with a
    warning, and the exception record is appended to `exceptions` (the plan writes it into its manifest)."""
    try:m=json.loads(data if data is not None else Path(path).read_bytes())
    except (OSError,ValueError)as e:raise ValueError(f'cannot read cost model {path}: {e}')from e
    if not isinstance(m,dict)or m.get('schema')!=COST_SCHEMA or m.get('dimension')!=2 or m.get('order')!=ORDER:raise ValueError(f'{path} is not a {COST_SCHEMA} cost model (dimension 2, order 8)')
    if m.get('backend')!=backend:raise ValueError(f'cost model backend {m.get("backend")!r} differs from --backend {backend}')
    ri=m.get('rates_identity')
    if ri!=rates_identity:
        if not test_only:raise ValueError(f'cost model rates identity {ri!r} differs from the plan\'s {rates_identity!r} (D15)')
        print(f'warning: cost model rates identity {ri!r} differs from the plan\'s {rates_identity!r}; accepted for a test-only plan',file=sys.stderr)
    if numerics is not None and m.get('numerics')!=numerics:
        why=(f'cost model numerics identity {m.get("numerics")!r} differs from the plan\'s numerics {numerics!r} (X10): task, index and lane-deadline '
             f'sizes would come from another profile\'s costs; measure one under {numerics} (tools/sweep.py'+(f' --numerics {numerics}'if numerics!='exact'else'')+')')
        if not test_only:raise ValueError(why+'; only a test-only plan (sweeps, gates) keeps such a cost model, as a recorded exception')
        print(f'warning: {why}; accepted for a test-only plan and recorded in the manifest (cost_model_numerics_exception)',file=sys.stderr)
        if exceptions is not None:
            exceptions.append({'cost_model_numerics':m.get('numerics'),'plan_numerics':numerics,'scope':'test-only plan',
                               'rule':'non-test plans refuse a cost model of other numerics (production.load_cost_model, X10)'})
    c=m.get('seconds_per_point')
    if not isinstance(c,dict)or not c:raise ValueError(f'cost model {path} has no seconds_per_point entries')
    for k,v in c.items():
        if isinstance(k,str)and POOLED_KEY.fullmatch(k):raise ValueError(f'cost model key {k!r} is pooled over the campaigns (sector:L:graph); C8(2) costs are keyed campaign:sector:L:graph (R05)')
        if not isinstance(k,str)or not COST_KEY.fullmatch(k):raise ValueError(f'cost model key {k!r} is not campaign:sector:L:graph')
        if isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)or v<=0:raise ValueError(f'cost model entry {k} = {v!r} is not a positive finite number of seconds')
    return m

def load_calibration(path:Path|None=None)->dict:return load(path or ROOT/'tools/calibration.json')

def calibration_row(cal:dict,backend:str,campaign:str,sector:str,L:int,numerics:str='exact',rates_identity:str='default'):
    """The campaign-keyed proxy row (backend, campaign, sector, L), else None (C7(2)'s pooled rows are never found).
    W11 (S6D-R4-02, Stage-6 fix round 4): a row is a measurement of one numerics profile under one rate map, recorded in
    its source (tools/calibrate.py: source.numerics, source.rates_identity); it is used only by a plan of the same
    numerics and rates identity. A row of another identity, or one that records none, is refused (ValueError naming
    both) instead of sizing the plan's tasks with another map's or profile's speed: an exact sweep under --rates, or a
    sweep under a profile, that updated this calibration file cannot silently re-time default-rate exact plans."""
    row=((((((cal.get('backends')or{}).get(backend)or{}).get(campaign)or{}).get(sector))or{}).get(str(L)))
    if not (isinstance(row,dict)and row.get('seconds_per_proxy_unit')):return None
    src=row.get('source')if isinstance(row.get('source'),dict)else{}
    got=(src.get('numerics'),src.get('rates_identity'))
    if got!=(numerics,rates_identity):
        raise ValueError(f'calibration row ({backend}, {campaign}, {sector}, L{L}) of tools/calibration.json was measured under numerics {got[0]!r} and '
                         f'rates identity {got[1]!r} (its source {src.get("run")!r}), this plan has numerics {numerics!r} and rates identity '
                         f'{rates_identity!r} (W11): a calibration row is used only under the identity it was measured with. Give --cost-model '
                         'measured under this identity, plan with --bootstrap-chunk P --shards N, or restore the calibration rows of this identity '
                         '(a sweep under another identity writes its own --calibration file)')
    return row

PRELIMINARY='preliminary_proxy (C7(2) pooled-campaign calibration, L8 from L7, x3; not a measurement)'
def load_bootstrap_proxy()->dict:
    p=ROOT/'tools/bootstrap_proxy.json';doc=load(p)
    if doc.get('schema')!=BOOT_SCHEMA or doc.get('label')!=PRELIMINARY:raise ValueError(f'{p} is not a {BOOT_SCHEMA} file')
    return doc

def bootstrap_row(doc:dict,backend:str,sector:str,L:int)->float|None:
    v=(((doc.get('rows')or{}).get(backend)or{}).get(sector)or{}).get(str(L))
    return float(v)if v else None

# ---------------------------------------------------------------- design bundles (component E)
def read_bundle(bundle:Path)->dict:
    """A frozen design bundle from tools/design.py freeze: design_meta.json (its sha256 is the bundle identity),
    design.json and counts/<campaign>_<sector>_L<L>.txt, each verified against the digests in design_meta.json.
    Provisional bundles (design.py rates) carry no allocation and are refused here (R14, R19). The counts are parsed
    from the verified bytes by design.parse_counts (fix round 3, Z9's class): before, a repeated graph line silently
    won last, and '+n', a count of 0 and an unterminated last line were accepted."""
    bundle=Path(bundle).resolve();mb=(bundle/'design_meta.json').read_bytes();meta=json.loads(mb)
    if meta.get('schema')!=DESIGN_SCHEMA:raise ValueError(f'{bundle} is not a {DESIGN_SCHEMA} design bundle')
    if meta.get('provisional'):
        raise ValueError(f'{bundle} is a provisional rates bundle (design.py rates): it carries no counts, replicates or sample multipliers and is '
                         'no allocation source in any plan (R19). First measure under its map (production.py plan --pilot --rates '
                         f'{bundle}/rates.json, or tools/sweep.py --rates), then make a fresh bundle with design.py freeze --rates-bundle {bundle}')
    db=(bundle/'design.json').read_bytes()
    if hashlib.sha256(db).hexdigest()!=meta['design_sha256']:raise ValueError(f'Checksum mismatch: {bundle/"design.json"}')
    d=json.loads(db);files={'design_meta.json':mb,'design.json':db}  # the verified bytes, pinned into the campaign (X9)
    counts={}
    for name,h in meta['counts_sha256'].items():
        m_=re.fullmatch(r'counts/([ab])_(free|power)_L([3-8])\.txt',name)
        if not m_:raise ValueError(f'{bundle}: design_meta.json lists an unexpected counts file {name!r}')
        data=(bundle/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=h:raise ValueError(f'{bundle/name} differs from the digest in design_meta.json')
        c,s,L=m_.groups();files[name]=data
        import design  # Z9's class (fix round 3 integration): the strict reader of design.read_bundle, not a lenient split
        counts[(c,s,int(L))]=design.parse_counts(bundle/name,data)
    if set(counts)!=set(GROUPS):raise ValueError(f'{bundle}: counts files for {len(counts)} groups, need all 24')
    return {'path':bundle,'meta':meta,'meta_sha256':hashlib.sha256(mb).hexdigest(),'design':d,'counts':counts,'files':files}

def bundle_replicates(bundle:dict)->dict:
    """Y10 (S6D-R2-02): the replicates of a design bundle (design.json 'replicates', one per (sector, L)), checked
    before anything is planned: exactly the twelve '<sector>_L<L>' entries, each an integer of at least MIN_REPLICATES
    (2) in any bundle, and in a production (non-test) bundle a power of two within PRODUCTION_REPLICATES [32, 128] (the
    production bounds). Reduced bounds come only from a --test-only bundle. Returns {'<sector>_L<L>': r}."""
    d=bundle['design'];reps=d.get('replicates')if isinstance(d,dict)else None;where=bundle['path']
    want={f'{s}_L{L}'for s in SECTORS for L in LOOPS}
    if not isinstance(reps,dict)or set(reps)!=want:
        raise ValueError(f'{where}: design.json "replicates" must list exactly {", ".join(sorted(want))} (got {sorted(reps)if isinstance(reps,dict)else repr(reps)}; Y10)')
    test=bool(bundle['meta'].get('test_only'));lo,hi=PRODUCTION_REPLICATES;bad=[]
    for k in sorted(want):
        r=reps[k]
        if isinstance(r,bool)or not isinstance(r,int):bad.append(f'{k}={r!r} (not an integer)')
        elif r<MIN_REPLICATES:bad.append(f'{k}={r} (fewer than {MIN_REPLICATES}: a group of one replicate cannot be assembled)')
        elif not test and not (lo<=r<=hi and pow2(r)):bad.append(f'{k}={r} (outside the production bounds: a power of two in [{lo}, {hi}])')
    if bad:
        raise ValueError(f'{where}: {"the --test-only" if test else "the production (non-test)"} design bundle has invalid replicates: {"; ".join(bad)} '
                         '(Y10: reduced replicate bounds only in a --test-only bundle; design.py freeze)')
    return dict(reps)

def design_bundle(directory:Path,m:dict,override=None)->Path|None:
    """The design bundle of a planned campaign (X9), resolved separately from its identity: --bundle OVERRIDE when given
    (a relocated copy), else the campaign's pinned copy <campaign>/design_bundle (plans since X9), else the path the
    plan recorded. Whichever is used, its design_meta.json must have the sha256 the campaign pinned (manifest
    design.meta_sha256), and design_meta.json pins every counts file by its digest, so the identity checks are those of
    the original bundle; the campaign manifest is never rewritten. None for a campaign planned from a pilot."""
    d=m.get('design')
    if not d:
        if override is not None:raise ValueError('--bundle: this campaign was planned from a pilot (no design bundle)')
        return None
    want=d['meta_sha256']
    if override is not None:p,what=Path(override).resolve(),'--bundle'
    elif d.get('pinned_copy'):p,what=Path(directory)/d['pinned_copy'],'the campaign\'s pinned copy of its design bundle'
    else:p,what=Path(d['bundle']),'the design bundle the campaign was planned with'
    f=p/'design_meta.json'
    if not f.is_file():
        raise ValueError(f'{what} ({p}) has no design_meta.json; give --bundle DIR, a copy of the bundle whose design_meta.json has sha256 {want}'
                         +(' (campaigns planned before the pinned copy record only the original path)'if not d.get('pinned_copy')else''))
    if digest(f)!=want:
        why='it is not the campaign\'s bundle'if override is not None else'the bundle changed'
        raise ValueError(f'{f} differs from the design_meta.json the campaign was planned with (sha256 {want}): {why}')
    return p

def gate_evidence_missing(g:dict)->list[str]:
    """Stage-6 residual of fix round 1: what a bundle's gate entry (design.check_gate's return, recorded at freeze) lacks
    of the X1-X3 evidence the current check_gate returns: F1_coverage (both sectors, each with at least
    design.GATE_F1_NEED binary128-accepted and MP-promoted points), source_snapshot_sha256 (the build binding's source
    snapshot) and F5_team_sizes_verified true; since fix round 3 (Z19 downstream) also gmp_library (the libgmp sha256 of
    the exact and the profile executable, which both F1 tools ran with, and whether the baseline was reused). A gate
    entry recorded before the fix (e.g. job 570210's) has none of them, one of fix round 1 (job 570373's) no
    gmp_library; their records are refused by the current check_gate, so the bundle cannot plan. Since fix round 4 (W18)
    also inputs_manifest_sha256, the inputs manifest the gate ran on (job 570536's entry has none). Empty when complete."""
    import design
    out=[];cov=g.get('F1_coverage');need=design.GATE_F1_NEED
    cnt=lambda v:isinstance(v,int)and not isinstance(v,bool)
    if not isinstance(cov,dict)or set(cov)!=set(SECTORS)or not all(isinstance(cov[s],dict)and cnt(cov[s].get('binary128_accepted'))and cnt(cov[s].get('mp_promoted'))
                                                                  and cov[s]['binary128_accepted']>=need[0]and cov[s]['mp_promoted']>=need[1]for s in SECTORS):
        out.append(f'F1_coverage {cov!r}'[:200]if cov is not None else'no F1_coverage')
    if not re.fullmatch(r'[0-9a-f]{64}',str(g.get('source_snapshot_sha256'))):out.append('no source_snapshot_sha256')
    if g.get('F5_team_sizes_verified')is not True:out.append(f'F5_team_sizes_verified {g.get("F5_team_sizes_verified")!r}')
    gl=g.get('gmp_library')  # Z19 downstream (fix round 3): the libgmp provenance of both F1 tools (design.gate_gmp_library)
    if not (isinstance(gl,dict)and all(re.fullmatch(r'[0-9a-f]{64}',str(gl.get(k)))for k in ('exact','profile'))and gl.get('f1_baseline_reused')in (True,False)):
        out.append('no gmp_library'if gl is None else f'gmp_library {gl!r}'[:200])
    # W18 (fix round 4, S6H4-01): the authenticated input set the gate ran on (design.gate_inputs; the gate entry's
    # inputs_manifest_sha256). A gate entry recorded before the fix (job 570536's, the 570539 bundles) has none
    if not re.fullmatch(r'[0-9a-f]{64}',str(g.get('inputs_manifest_sha256'))):out.append('no inputs_manifest_sha256')
    return out

def route_b(meta:dict,cost_model:dict|None=None,cost_bytes:bytes|None=None,exe_sha:str|None=None,test_only:bool=False,approval:str|None=None,
            final:bool=False)->dict|None:
    """Route (b) of a design bundle (design.py freeze --numerics P from an exact pilot): None for a bundle whose numerics
    are its pilot's (exact, or a pilot measured under a profile: route (a)). Otherwise the record must be complete, its
    profile in APPROVED_PROFILES and every gate entry must carry the X1-X3 evidence of the current design.check_gate
    (gate_evidence_missing; a bundle frozen with a gate record that check_gate now refuses cannot plan); with final=True
    also the plan's cost model (numerics identity = the profile) and executable (non-test: one that a gate of the
    bundle passed). Returns the manifest's numerics_route."""
    prof=meta.get('numerics','exact');pn=(meta.get('pilot')or{}).get('numerics',prof);rec=meta.get('profile_recost')
    if rec is None and pn==prof:return None
    if not isinstance(rec,dict):raise ValueError(f'the design bundle carries numerics {prof!r} but its pilot ran under {pn!r}, without a route-(b) record (profile_recost)')
    if prof not in APPROVED_PROFILES:raise ValueError(f'the design bundle\'s numerics profile {prof!r} is not in the user-approved set {sorted(APPROVED_PROFILES)} (route (b))')
    sha=re.compile(r'[0-9a-f]{64}');ep=rec.get('exact_pilot')or{};gates=rec.get('gates')or[];bcm=rec.get('cost_model')or{}
    why=[k for k,bad in (('route',rec.get('route')!='b'),('profile',rec.get('profile')!=prof),('exact pilot',pn!='exact'or ep.get('numerics')!='exact'),
                         ('approval',not str(rec.get('approval')or'').strip()),
                         ('gates',not gates or not all(isinstance(g,dict)and sha.fullmatch(str(g.get('sha256')))and sha.fullmatch(str(g.get('profile_executable_sha256')))
                                                       for g in gates)),
                         ('cost model',bcm.get('numerics')!=prof or not sha.fullmatch(str(bcm.get('sha256')))))if bad]
    if why:raise ValueError(f'the design bundle\'s route-(b) record is incomplete or inconsistent ({", ".join(why)}): refused')
    old=[f'{g.get("slurm_job")or str(g.get("sha256"))[:12]} ({"; ".join(w)})'for g in gates for w in [gate_evidence_missing(g)]if w]
    if old:
        raise ValueError(f'the design bundle\'s route-(b) gate record(s) {", ".join(old)} lack the evidence design.check_gate requires since Stage-6 fix '
                         f'round 1 (X1 F1_coverage, X2 source_snapshot_sha256, X3 F5_team_sizes_verified; fix round 3 gmp_library; fix round 4 '
                         f'inputs_manifest_sha256): a bundle frozen with a gate the current check_gate refuses cannot plan; re-run the gate '
                         f'(tests/numerics_flags.py --profile {prof}) and re-freeze the bundle with its record')
    # W18 (fix round 4): every gate ran on the bundle's inputs (the exact pilot's; plan checks the bundle's against its own)
    im=meta.get('inputs_manifest_sha256');other=[f'{g.get("slurm_job")or str(g.get("sha256"))[:12]} ({str(g["inputs_manifest_sha256"])[:12]}...)'
                                                for g in gates if g['inputs_manifest_sha256']!=im or ep.get('inputs_manifest_sha256',im)!=im]
    if other:
        raise ValueError(f'the design bundle\'s route-(b) gate record(s) {", ".join(other)} ran on another inputs manifest than the bundle\'s '
                         f'({str(im)[:12]}..., its exact pilot\'s): their F1 and F2 measurements need not describe these kernels (W18); re-run the gate on '
                         f'these inputs and re-freeze the bundle with its record')
    if not final:return None
    if cost_model is None:raise ValueError(f'a plan of a route-(b) bundle needs --cost-model measured under {prof} (tools/sweep.py --numerics {prof})')
    if cost_model.get('numerics')!=prof:
        raise ValueError(f'cost model numerics identity {cost_model.get("numerics")!r} differs from the bundle\'s profile {prof!r}: a route-(b) plan sizes its '
                         'tasks with a cost model measured under the profile')
    gx=sorted({g['profile_executable_sha256']for g in gates});gated=exe_sha in gx
    if not gated and not test_only:
        raise ValueError(f'the executable ({exe_sha}) is not a {prof} build that a J-FLAG gate of the bundle passed ({", ".join(x[:12] for x in gx)}): run the gate of '
                         f'this build (tests/numerics_flags.py --profile {prof}) and freeze with its record')
    return dict(route='b',profile=prof,approved_set_reference=APPROVED_PROFILES[prof],bundle_approval=rec['approval'],plan_approval=approval,gates=gates,
                exact_pilot=ep,bundle_cost_model=bcm,plan_cost_model=dict(sha256=hashlib.sha256(cost_bytes).hexdigest(),numerics=cost_model.get('numerics'),
                                                                          executable_sha256=cost_model.get('executable_sha256'),cpu_models=cost_model.get('cpu_models')),
                executable_sha256=exe_sha,executable_gated=gated,variance=rec.get('variance'))

def gated_route(numerics:str,source:str,gate_paths:list,exe_sha:str,inv:dict,approval:str|None,pilot_key:tuple|None=None,
                im_sha:str|None=None)->dict:
    """The numerics_route of a plan under a profile that is not route (b): a pilot under the profile (source 'pilot';
    non-test only with its key in APPROVED_PROFILE_PILOTS) or a bundle whose pilot ran under it (source 'design',
    route (a)). Every --numerics-gate RECORD must be a passed full-scale J-FLAG gate of the profile's production build
    (tools/design.py check_gate: schema, mode and profile, status, no development option, F1, F2 and F5, the F2 total
    passed and resolved, the gated build not a development build, F2 over every inventory graph of this plan) and the
    plan's executable one of the gated builds; else refused. W18 (fix round 4): every gate must have run on im_sha, the
    plan's own inputs manifest (design.gate_inputs; None: the package's inputs/manifest.json)."""
    import design
    gates=[design.check_gate(Path(g),numerics,inv,im_sha)for g in gate_paths]
    if len({g['sha256']for g in gates})!=len(gates):raise ValueError('--numerics-gate names one record twice')
    gx=sorted({g['profile_executable_sha256']for g in gates})
    if exe_sha not in gx:
        raise ValueError(f'the executable ({exe_sha}) is not the {numerics} build that the --numerics-gate record(s) passed ({", ".join(x[:12] for x in gx)}): '
                         f'run the gate of this build (tests/numerics_flags.py --profile {numerics}) and plan with its record')
    return dict(route='a'if source=='design'else'pilot',profile=numerics,approved_set_reference=APPROVED_PROFILES.get(numerics),plan_approval=approval,
                pilot_approval=APPROVED_PROFILE_PILOTS.get(pilot_key)if pilot_key else None,gates=gates,executable_sha256=exe_sha,executable_gated=True)

# W8 (S6-C-R4-02, Stage-6 fix round 4): an admitted (gated) profile executable is bound to the libgmp its gate validated.
GMP_SONAME=re.compile(r'libgmp\.so(?:\.[0-9]+)*')
SHA256_HEX=re.compile(r'[0-9a-f]{64}')

def gate_gmp_binding(m:dict)->set|None:
    """W8: the libgmp sha256(s) that the J-FLAG gate(s) admitting the campaign's executable validated, from the
    manifest's numerics_route (route (b): the bundle's gate entries; route (a) and profile pilots: design.check_gate's
    returns): gmp_library.profile of every gate whose profile_executable_sha256 is the campaign's executable (the
    libgmp the profile's F1 tool ran with, which check_gate requires to be the profile build record's). None when no
    gate admitted the executable (the exact path; a test-only plan of an ungated build). A gated campaign whose gates
    record no libgmp (a manifest of tools before Z19) is refused (ValueError): nothing then shows which library the
    gate validated."""
    nr=m.get('numerics_route')
    if not isinstance(nr,dict)or nr.get('executable_gated')is not True:return None
    exe=m.get('executable_sha256');gates=[g for g in nr.get('gates')or[]if isinstance(g,dict)and g.get('profile_executable_sha256')==exe]
    shas={s for s in ((g.get('gmp_library')or{}).get('profile')if isinstance(g.get('gmp_library'),dict)else None for g in gates)if isinstance(s,str)and SHA256_HEX.fullmatch(s)}
    if not shas:
        raise ValueError(f'the campaign\'s executable ({str(exe)[:12]}) is admitted by J-FLAG gate(s) {[g.get("slurm_job")or str(g.get("sha256"))[:12] for g in gates]} '
                         'that record no libgmp (gmp_library.profile; W8): nothing shows which libgmp the gate validated. Re-run the gate with the current '
                         'tools and re-plan (route (b): re-freeze the bundle with its record)')
    return shas

def gmp_binding_problem(identity:dict|None,binding:set,test_only:bool)->str|None:
    """W8: why a runtime identity (common.runtime_identity) is not bound to the gate's libgmp `binding`; None when it
    is: every libgmp the worker loads (soname libgmp.so[.N], or a path entry of that basename) has one of the binding's
    sha256. An identity naming no libgmp is refused too, except in a test-only campaign whose worker is no dynamic ELF
    (ldd unavailable and no library: the test stand-ins, macOS), where no library can be shown; a production worker
    always loads libgmp (Y6 refuses a failed probe)."""
    ident=identity if isinstance(identity,dict)else{};libs=ident.get('libraries')if isinstance(ident.get('libraries'),dict)else{}
    want=', '.join(sorted(s[:12]for s in binding))
    gmp={str(n):v for n,v in libs.items()if GMP_SONAME.fullmatch(os.path.basename(str(n)))}
    if gmp:
        bad=sorted(f'{n} (sha256 {str(v)[:12]})'for n,v in gmp.items()if v not in binding)
        return f'it loads {", ".join(bad)}, not the libgmp its J-FLAG gate validated ({want})'if bad else None
    if test_only and ident.get('ldd')=='unavailable'and not libs:return None
    return f'its runtime identity names no libgmp (ldd {ident.get("ldd")!r}, {len(libs)} libraries), so it is not shown to load the libgmp its J-FLAG gate validated ({want})'

# ---------------------------------------------------------------- executables
def exe_for(backend:str,numerics:str='exact')->Path:
    if numerics!='exact':
        if numerics_name(numerics)!=numerics:raise ValueError(f'--numerics {numerics!r}: the canonical profile name is {numerics_name(numerics)!r} (PLAN A-FLAG-1)')
        if backend!='gmp':raise ValueError('opt-in numerics profiles exist for the gmp backend only')
        return ROOT/'bin'/f'c8d2_gmp_{numerics}'
    return ROOT/'bin'/('c8d2_gmp'if backend=='gmp'else'c8d2_decimal')

def read_build_record(exe:Path,backend:str|None=None,numerics:str|None=None,required:bool=False):
    """The executable's build record bin/<exe>.build.json (tools/build_record.py, written by make). Every plan refuses a
    record that describes another executable (sha256) and a development build (A-FLAG-1: profile-parameter overrides
    such as -DC8_MP256_RATIO=..., -DC8_EXP1_RANGE=..., -DC8_DD_* or a C8_NX_* hook on the command line, recomputed from
    the recorded compiler options so that a record written before the field existed is checked too, or "development").
    Z3 (S6A3-03, Stage-6 fix round 3): a NON-test plan (required=True) also refuses a missing or unreadable record and
    one that is not a valid c8-d2-build-record-1 record of this production build: its schema, executable name, backend
    and NUMERICS (the plan's), no diagnostic kind and the required numerical flags in effect (required_flags_present).
    Without its record nothing shows how an executable was compiled (a copy without its sidecar could carry an
    injected hook while --describe calls it exact). A test-only plan keeps a missing record with a warning (None).
    Z3 integration (G1's macro_overrides, the compiler's own probe of the macros in effect): every plan refuses a record
    that lists any (a development build even when its "development" was edited to false), and a non-test plan also
    refuses one whose macro_overrides is not a list (null: the probe did not run; absent: a record made before fix
    round 3), since nothing then shows that no C8_* macro was injected."""
    br=exe.with_name(exe.name+'.build.json')
    if not br.exists():
        if required:
            raise ValueError(f'{exe} has no build record {br.name}: a non-test plan runs only an executable whose build record describes it (Z3: its compiler, '
                             'flags, numerics and overrides); build it with make (make clean && make, or make -B; make gmp NUMERICS=<p> for a profile), '
                             'never copy an executable without its record')
        print(f'warning: no build record {br.name}; rebuild with `make clean && make` (or `make -B`) to record compiler, flags and library versions',file=sys.stderr);return None
    try:rec=json.loads(br.read_bytes())
    except (OSError,ValueError)as e:raise ValueError(f'{br} is not a readable build record ({e}); rebuild with `make clean && make` (or `make -B`)')from None
    if not isinstance(rec,dict):raise ValueError(f'{br} is not a build record (a JSON {type(rec).__name__}); rebuild with `make clean && make` (or `make -B`)')
    if rec.get('executable_sha256')!=digest(exe):raise ValueError(f'{br} describes a different executable than {exe}; rebuild with `make clean && make` (or `make -B`)')
    import build_record as brm
    co=rec.get('compiler_options')
    ov=sorted(set(brm.parameter_overrides(co if isinstance(co,list)else[]))|set(rec.get('parameter_overrides')or[]))
    mo=rec.get('macro_overrides')  # Z3 (fix round 3, integration): the compiler probe's C8_* macros in effect, however they were set
    if ov or rec.get('development')or mo:
        raise ValueError(f'{exe} is a development build (profile-parameter overrides {ov}, macro overrides {mo if mo else []} in {br.name}); plan accepts '
                         'production builds only (A-FLAG-1)')
    if required:
        why=[]
        if rec.get('schema')!=BUILD_RECORD_SCHEMA:why.append(f'schema {rec.get("schema")!r}, not {BUILD_RECORD_SCHEMA}')
        if rec.get('executable')!=exe.name:why.append(f'it names the executable {rec.get("executable")!r}, not {exe.name}')
        if backend is not None and rec.get('backend')!=backend:why.append(f'backend {rec.get("backend")!r}, the plan\'s is {backend}')
        if numerics is not None and (rec.get('NUMERICS')or'exact')!=numerics:why.append(f'NUMERICS {rec.get("NUMERICS")!r}, the plan\'s numerics are {numerics}')
        if rec.get('diagnostic'):why.append(f'a diagnostic build ({rec.get("diagnostic")})')
        if rec.get('required_flags_present')is not True:why.append(f'required_flags_present is {rec.get("required_flags_present")!r} (the required numerical flags were not in effect)')
        if not isinstance(mo,list):why.append(f'macro_overrides is {mo!r}, not a list: the record does not show the macros in effect (the compiler probe did not '
                                              'run, or a record written before Stage-6 fix round 3; Z3)')
        if why:raise ValueError(f'{br} is not a valid build record of a production build for this non-test plan (Z3): {"; ".join(why)}; rebuild with make '
                                '(make clean && make, or make -B)')
    if rec.get('optimized')is False:print(f'warning: {exe.name} was built without optimization (OPTFLAGS={rec.get("OPTFLAGS")!r})',file=sys.stderr)
    return rec

def describe(exe:Path,numerics:str)->dict:
    """--describe of a production executable (A-KER-3): schema c8-d2-build-1, order 8 supported, the plan's numerics
    profile, not a diagnostic or sanitizer build, no profile built as a development variant (dd's -DC8_DD_DEVELOPMENT
    measurement builds; any -DC8_MP256_RATIO or -DC8_EXP1_RANGE override), the class-B tail fields present."""
    if not exe.exists():raise FileNotFoundError(f'Build the executable first (make, make gmp): {exe}')
    b=json.loads(subprocess.check_output([str(exe),'--describe'],text=True))
    if b.get('schema')!=BUILD_SCHEMA or b.get('dimension')!=2 or ORDER not in (b.get('orders')or[]):raise ValueError(f'{exe} is not a C8(2) worker (--describe: {b.get("schema")})')
    if b.get('diagnostic'):raise ValueError(f'{exe} is a diagnostic build ({b.get("diagnostic_kind")}); plan accepts production builds only')
    if b.get('numerics')!=numerics:raise ValueError(f'{exe} reports numerics {b.get("numerics")!r}, the plan asks for {numerics!r}')
    dev=sorted(k for k,v in (b.get('numerics_params')or{}).items()if isinstance(v,dict)and v.get('development'))
    if dev:raise ValueError(f'{exe} is a development build of profile(s) {dev} (--describe numerics_params: "development":true, a measurement variant); plan accepts production builds only (A-FLAG-1)')
    if b.get('tail_top')!=16:raise ValueError(f'{exe} writes no class-B tail fields (tail_top {b.get("tail_top")})')
    return b

# ---------------------------------------------------------------- planning
def select_graphs(rows:list,n,mode:str,cost_of)->set:
    """--test-graphs N|all (a test-only restriction of a group): 'cheapest' (C7(2)) takes the N cheapest by inventory
    cost; 'stratified' takes N/2 cheapest and N/2 heaviest by measured cost (or proxy cost without a cost model), plus
    every L7 primitive and at least 16 L8 primitives (8 cheapest, 8 heaviest), deduplicated and deterministic."""
    if n=='all':return {r['id']for r in rows}
    if mode=='cheapest':return {r['id']for r in sorted(rows,key=lambda r:(r['cost'],r['id']))[:n]}
    by=sorted(rows,key=lambda r:(cost_of(r),r['id']));lo=n//2;hi=n-lo
    out={r['id']for r in by[:lo]}|{r['id']for r in (by[len(by)-hi:]if hi else[])}
    prim=[r for r in by if r.get('primitive')]
    if prim and rows and rows[0].get('_L')==7:out|={r['id']for r in prim}
    if prim and rows and rows[0].get('_L')==8:out|={r['id']for r in prim[:8]}|{r['id']for r in prim[-8:]}
    return out

def merge_passes(runs:int,F:int)->int:
    """Passes of the external merge of `runs` sorted runs with fan-in F: ceil(log_F(runs)), at least 1 (integer arithmetic)."""
    p,cap=1,F
    while cap<runs:p+=1;cap*=F
    return p

def parse_test_graphs(v):
    if v is None:return None
    if v=='all':return 'all'
    if not v.isdigit()or int(v)<1:raise ValueError('--test-graphs takes a positive integer or "all"')
    return int(v)

def plan(a):
    """Every argument, input, seed, cap, Sobol-period and max-task-seconds check comes before anything is created; the
    campaign is then written into <dir>.tmp.<jobid or pid> and published with one rename (HR26)."""
    out=a.directory.resolve()
    if out.exists():raise FileExistsError(f'Use a new campaign directory ({out} exists)')
    tg=parse_test_graphs(a.test_graphs);test_only=tg is not None
    # D8: exactly one allocation source.
    if (a.pilot is None)==(a.design is None):raise ValueError('give exactly one allocation source: --pilot [--points P] or --design BUNDLE (D8)')
    # The bundle is read first, so that a provisional rates bundle is refused before any other check, in a test-only
    # and a non-test plan alike (R19).
    bundle=read_bundle(a.design)if a.design is not None else None
    if bundle is not None:route_b(bundle['meta'])  # route (b): the record and the allow-list, before any executable is described
    reps_of=bundle_replicates(bundle)if bundle is not None else None  # Y10: the replicate bounds, before anything else is read
    if a.points is not None and a.pilot is None:raise ValueError('--points belongs to --pilot')
    P=a.points if a.points is not None else PILOT_MIN_POINTS
    if a.pilot is not None:
        if not pow2(P):raise ValueError('--points must be a power of two')
        if P<PILOT_MIN_POINTS and not test_only:raise ValueError(f'--pilot --points {P} < {PILOT_MIN_POINTS} needs a test-only plan (--test-graphs; D8)')
    if a.replicates is not None and a.design is not None:raise ValueError('--replicates belongs to --pilot; a design bundle fixes the replicates')
    R=a.replicates if a.replicates is not None else 8
    if R<2:raise ValueError('at least 2 replicates')
    if a.test_selection=='stratified'and not test_only:raise ValueError('--test-selection needs --test-graphs')
    if min(a.threads,a.max_tasks,a.max_checkpoints)<1:raise ValueError('invalid sizes')
    T=a.checkpoint_tasks if a.checkpoint_tasks is not None else max(16*a.threads,256)
    if not 1<=T<=100000:raise ValueError('checkpoint_tasks must be in [1, 100000] (the native task-file limit)')
    if a.threads>T:raise ValueError(f'--threads {a.threads} exceeds --checkpoint-tasks {T}: at most {T} threads can ever be busy')
    if T<16*a.threads:print(f'warning: --checkpoint-tasks {T} < 16 x {a.threads} threads; per-block barriers will idle cores',file=sys.stderr)
    if not 0<=a.seed<2**63:raise ValueError('seed outside [0, 2^63)')
    # Cost basis (R13): measured, calibrated proxy (test-only), or the first-sweep bootstrap (test-only).
    boot=a.bootstrap_chunk is not None
    if boot:
        if not test_only:raise ValueError('--bootstrap-chunk is for a test-only plan only (the first sweep, R13)')
        if a.cost_model is not None:raise ValueError('--bootstrap-chunk and --cost-model exclude each other: a measured plan chunks by 60/c_g')
        if a.index_hours is not None or a.task_seconds is not None or a.min_chunk is not None:raise ValueError('--bootstrap-chunk refuses --index-hours, --task-seconds and --min-chunk, which need a time estimate (R13)')
        if a.shards is None:raise ValueError('--bootstrap-chunk needs --shards N (no time estimate exists to size indices)')
        if not pow2(a.bootstrap_chunk):raise ValueError('--bootstrap-chunk must be a power of two')
    if a.shards is not None and a.index_hours is not None:raise ValueError('give --index-hours or --shards, not both')
    if a.shards is not None and a.shards<1:raise ValueError('--shards must be positive')
    H=a.index_hours if a.index_hours is not None else(None if a.shards is not None else INDEX_HOURS)
    if H is not None and not H>0:raise ValueError('--index-hours must be positive')
    task_s=a.task_seconds if a.task_seconds is not None else TASK_SECONDS;min_chunk=a.min_chunk if a.min_chunk is not None else MIN_CHUNK
    if not task_s>0 or not a.max_task_seconds>0 or not (min_chunk>=1 and pow2(min_chunk)):raise ValueError('invalid --task-seconds, --max-task-seconds or --min-chunk (a power of two)')
    if a.cost_model is None and not boot and not test_only:raise ValueError('a non-test plan needs --cost-model (measured seconds per point, D15); test-only plans may use calibration rows or --bootstrap-chunk')
    # Numerics (D1, A-FLAG-2): the exact path unless approved.
    if (a.numerics!='exact'or a.rates)and not (a.approved_numerics_change or'').strip():
        raise ValueError('--numerics other than exact and --rates are numerics changes: they need --approved-numerics-change "<user approval reference>" (D1, A-FLAG-2)')
    if numerics_name(a.numerics)!=a.numerics:raise ValueError(f'--numerics {a.numerics!r}: the canonical profile name is {numerics_name(a.numerics)!r} (PLAN A-FLAG-1)')
    if not test_only and a.numerics!='exact'and a.numerics not in APPROVED_PROFILES:
        raise ValueError(f'--numerics {a.numerics!r} in a non-test plan: not in the user-approved set {sorted(APPROVED_PROFILES)} (production.APPROVED_PROFILES; '
                         'every non-test plan, --pilot or --design); only test-only plans (gates, sweeps) take another profile')
    rates_read=Path(a.rates).read_bytes()if a.rates else None  # W23's class: the map is read once; its approval and its identity are of these bytes
    rid=hashlib.sha256(rates_read).hexdigest()if a.rates and not test_only else'default'  # the non-test map's rates identity
    if not test_only and a.rates:
        if rid not in APPROVED_RATES:
            raise ValueError(f'--rates {a.rates} (rates identity {rid[:12]}...) in a non-test plan: R7 is not approved (production.APPROVED_RATES '
                             f'{sorted(APPROVED_RATES) or "is empty"}); only test-only plans (sweeps) measure under a rate map')
    # The pilot stays exact (the user's decision of 2026-10-05): a NON-test pilot under a profile or a rate map needs the
    # user's explicit go, a key of APPROVED_PROFILE_PILOTS.
    pkey=None
    if not test_only and a.pilot is not None and (a.numerics!='exact'or a.rates):
        pkey=(a.numerics,rid)
        if pkey not in APPROVED_PROFILE_PILOTS:
            raise ValueError(f'a non-test pilot runs on the exact path at the default rates (user decision 2026-10-05: the smoke and the pilot stay exact); '
                             f'--pilot under numerics {a.numerics!r} and rates identity {pkey[1][:12]!r} needs the user\'s explicit go '
                             f'(production.APPROVED_PROFILE_PILOTS {sorted(APPROVED_PROFILE_PILOTS) or "is empty"}); test-only pilots (--test-graphs) are not affected')
    # Gated executables (Stage 6): a NON-test plan whose numerics are not exact runs only a build that a recorded, passed,
    # full-scale J-FLAG gate covers: a route-(b) bundle's gate records (route_b below), else --numerics-gate RECORD.
    gate_paths=list(getattr(a,'numerics_gate',None)or[])
    rb=bundle is not None and bundle['meta'].get('profile_recost')is not None
    if gate_paths and a.numerics=='exact':raise ValueError('--numerics-gate belongs to a plan under a numerics profile; the exact path needs no gate')
    if gate_paths and rb:raise ValueError('--numerics-gate: a route-(b) bundle carries its own gate records (design.py freeze --numerics-gate); its plans take none')
    if not test_only and a.numerics!='exact'and not rb and not gate_paths:
        raise ValueError(f'a non-test plan under --numerics {a.numerics} runs only a build that a passed full-scale J-FLAG gate covers: give --numerics-gate RECORD '
                         f'(the record of tests/numerics_flags.py --profile {a.numerics} on this build; a route-(b) bundle carries its own)')
    if not test_only and not a.forbid_seeds_from:raise ValueError('a non-test plan must pass --forbid-seeds-from $C8_SEEDS (D9)')
    forbidden={}
    for f in a.forbid_seeds_from or []:forbidden.update(read_seed_file(f))
    rel=inputs_rel_from_env()
    if rel!='inputs'and not test_only:raise ValueError(f'C8_INPUTS={rel}: a non-test plan uses the package\'s inputs/ only')
    import prepare_inputs as pi
    allow_no_l8=test_only and os.environ.get('C8_ALLOW_NO_L8')=='1'
    # A-IN-4: every listed input, the twelve packs and the vendored pins (hash only). W23's class: the manifest's sha256 is
    # taken first and verify parses only bytes of that sha256, so the recorded identity is the manifest the plan used
    im_sha=digest(ROOT/rel/'manifest.json');im=pi.verify(ROOT/rel,expected_manifest_sha256=im_sha,allow_no_l8=allow_no_l8)
    I=Inputs(rel,im)
    if I.fixture and not test_only:raise ValueError(f'{rel} is a test fixture: plans with it are test-only (--test-graphs)')
    skipped={(s,L)for s in SECTORS for L in LOOPS if not I.pack(s,L).exists()}
    inv=read_verified(I.where('inventory.json'),I.sha('inventory.json'))  # W23's class: the verified bytes, read once
    for s in SECTORS:
        for L in LOOPS:
            for r in inv[s][str(L)]:r['_L']=L
    exe=exe_for(a.backend,a.numerics);build=describe(exe,a.numerics);build_record=read_build_record(exe,a.backend,a.numerics,required=not test_only)  # Z3
    # Rates identity (R04): 'default' (.8/.9) or the sha256 of the frozen map.
    rates_doc=None;rates_bytes=None;rates_identity='default'
    if a.rates:
        rates_bytes=rates_read;rates_doc=validate_rates(rates_bytes,im_sha,inv);rates_identity=hashlib.sha256(rates_bytes).hexdigest()
    # Allocation (D8).
    if bundle is not None:
        meta=bundle['meta']
        if meta.get('test_only')and not test_only:raise ValueError(f'{a.design} is a --test-only bundle: only test-only plans accept it')
        if meta.get('inputs_manifest_sha256')!=im_sha:raise ValueError('the design bundle was frozen for another inputs manifest')
        if meta.get('rates_identity','default')!=rates_identity:raise ValueError(f'the design bundle pins rates identity {meta.get("rates_identity")!r}; this plan has {rates_identity!r} (give --rates with the bundle\'s map)')
        if meta.get('numerics','exact')!=a.numerics:raise ValueError(f'the design bundle was frozen for numerics {meta.get("numerics")!r}')
        for s in meta.get('forbidden_seeds',[]):forbidden.setdefault(int(s),f'design bundle {bundle["path"]}')
    why=seed_refusal(a.seed,forbidden)
    if why:raise ValueError(why+'; choose a fresh random seed (python3 -c "import secrets;print(secrets.randbits(63))")')
    measured=a.cost_model is not None
    cost_bytes=Path(a.cost_model).read_bytes()if measured else None
    cm_exc=[]  # X10: a test-only plan's recorded cost-model numerics exception
    cost_model=load_cost_model(a.cost_model,a.backend,rates_identity,test_only,cost_bytes,numerics=a.numerics,exceptions=cm_exc)if measured else None
    costs={k:float(v)for k,v in cost_model['seconds_per_point'].items()}if measured else{}
    numerics_route=route_b(bundle['meta'],cost_model,cost_bytes,digest(exe),test_only,a.approved_numerics_change,final=True)if bundle is not None else None
    if gate_paths:numerics_route=gated_route(a.numerics,'design'if bundle is not None else'pilot',gate_paths,digest(exe),inv,a.approved_numerics_change,pkey,
                                             im_sha)  # W18: the gate ran on this plan's inputs
    if numerics_route is not None and numerics_route.get('executable_gated'):
        # W8: the gated executable is bound to the libgmp its gate validated (recorded; every claim checks its own)
        gb=gate_gmp_binding({'numerics_route':numerics_route,'executable_sha256':digest(exe)});numerics_route['gate_gmp_library']=sorted(gb)
        bl=((build_record.get('gmp_library')or{})if isinstance(build_record,dict)and isinstance(build_record.get('gmp_library'),dict)else{}).get('sha256')
        if bl is not None and bl not in gb:
            why=(f'the executable\'s build record ({exe.name}.build.json) names libgmp {str(bl)[:12]}, but its J-FLAG gate(s) validated libgmp '
                 f'{", ".join(sorted(s[:12] for s in gb))} (W8): a build against another libgmp needs its own gate')
            if not test_only:raise ValueError(why+'; re-run the gate of this build (tests/numerics_flags.py) and plan with its record')
            print(f'warning: {why}; accepted for a test-only plan, whose claims still refuse a worker that loads another libgmp',file=sys.stderr)
    cal=load_calibration()if not measured and not boot else None
    bproxy=load_bootstrap_proxy()if boot else None
    basis='measured'if measured else('bootstrap'if boot else'calibrated_proxy')
    # Per group: counts, replicates, selected graphs, per-graph cost and chunk, task arithmetic (no file yet).
    G={}
    for c,s,L in GROUPS:
        rows=inv[s][str(L)];name=group_name(c,s,L)
        if (s,L)in skipped:rows=[]  # C8_ALLOW_NO_L8 (test-only): no pack here, so no graph is selected
        cost_of=(lambda r,c=c,s=s,L=L:costs.get(f'{c}:{s}:{L}:{r["id"]}',float(r['cost'])))if measured else(lambda r:float(r['cost']))
        sel={r['id']for r in rows}if tg is None else select_graphs(rows,tg,a.test_selection,cost_of)
        if bundle:
            base=bundle['counts'][(c,s,L)];strata=bundle['design']['strata'];reps=reps_of[f'{s}_L{L}']
            if set(base)!={r['id']for r in inv[s][str(L)]}:raise ValueError(f'design bundle counts of {name} do not cover exactly the inventory graphs')
            counts={r['id']:base[r['id']]*int(strata[stratum_of(s,L,r.get('primitive',False))]['s'])for r in rows if r['id']in sel}
        else:
            reps=R;counts={r['id']:P for r in rows if r['id']in sel}
        if any(not pow2(n)for n in counts.values()):raise ValueError(f'{name}: per-graph counts must be powers of two')
        bits=NET_BITS[c]
        if counts and max(counts.values())>2**bits:raise ValueError(f'Sobol period exceeded: group {name} has a stratum of {max(counts.values())} > 2^{bits} points')
        byid={r['id']:r for r in rows}
        per={};chunk={};units={}
        for g in sorted(counts):
            r=byid[g];n=counts[g];units[g]=max(1,int(r['cost']))
            if 'kernel_bytes'not in r:raise ValueError(f'{rel}/inventory.json has no kernel_bytes for {s} L{L} graph {g} (bin/c8d2_inspect fields)')
            if boot:
                row=bootstrap_row(bproxy,a.backend,s,L)
                if not row:raise ValueError(f'tools/bootstrap_proxy.json has no {a.backend} row for {s} L{L}')
                ch=min(a.bootstrap_chunk,n);per[g]=None;secs=ch*units[g]*row
                if secs>a.max_task_seconds:raise ValueError(f'{name} graph {g}: a {ch}-point task needs {secs:.1f} preliminary seconds > --max-task-seconds {a.max_task_seconds:g} '
                                                            f'({PRELIMINARY}); lower --bootstrap-chunk')
                chunk[g]=ch;continue
            if measured:
                k=f'{c}:{s}:{L}:{g}'
                if k not in costs:raise ValueError(f'{name}: graph {g} has no cost-model key {k} in {a.cost_model}; plan the sweep first (tools/sweep.py) or use a test-only plan with --bootstrap-chunk')
                cg=costs[k]
            else:
                row=calibration_row(cal,a.backend,c,s,L,a.numerics,rates_identity)  # W11: only a row of the plan's numerics and rates identity
                if not row:raise ValueError(f'{name}: no cost basis (no --cost-model and no ({a.backend}, {c}, {s}, L{L}) row in tools/calibration.json); '
                                            'give --cost-model, or plan the first sweep with --bootstrap-chunk P --shards N (R13)')
                cg=units[g]*float(row['seconds_per_proxy_unit'])
            ch=1<<max(0,int(math.floor(math.log2(task_s/cg))))if task_s>=cg else 1
            ch=max(min_chunk,min(ch,n));ch=min(ch,n);per[g]=cg;chunk[g]=ch
            if ch*cg>a.max_task_seconds:raise ValueError(f'{name} graph {g}: a {ch}-point task is predicted at {ch*cg:.1f} s > --max-task-seconds {a.max_task_seconds:g}; '
                                                         'raise --max-task-seconds or lower --min-chunk')
        ntasks=reps*sum(counts[g]//chunk[g]for g in counts)
        secs=None if boot else reps*sum(counts[g]*per[g]for g in counts)
        G[name]=dict(name=name,campaign=c,sector=s,L=L,counts=counts,reps=reps,chunk=chunk,per=per,units=units,byid=byid,ntasks=ntasks,secs=secs,
                     proxy=reps*sum(counts[g]*units[g]for g in counts),bits=bits,
                     maxtask=None if boot else max((chunk[g]*per[g]for g in counts),default=0.),
                     prelim=max((chunk[g]*units[g]*bootstrap_row(bproxy,a.backend,s,L)for g in counts),default=0.)if boot else None)
    # Every cap that the task counts alone decide comes before any task-sized structure (O03): --max-tasks per campaign,
    # the login-node guard, the shard counts, lower bounds of the checkpoint blocks and of the projected files (a split
    # into shards only adds blocks), and the merge projection. Only then the exact LPT per group (task-sized arrays),
    # whose real per-index task counts give the exact block and file counts, checked again before anything is created.
    for c in CAMPAIGNS:
        n=sum(g['ntasks']for g in G.values()if g['campaign']==c)
        if n>a.max_tasks:raise ValueError(f'campaign {c} has {n:,} tasks > --max-tasks {a.max_tasks:,}')
    total_tasks=sum(g['ntasks']for g in G.values())
    if total_tasks>PLAN_TASKS_IN_JOB and not os.environ.get('SLURM_JOB_ID'):raise ValueError(f'{total_tasks:,} tasks > {PLAN_TASKS_IN_JOB:,}: plan inside a job (slurm/plan.sh), never on a login node')
    # Index sizing: shards per group from --index-hours (or --shards).
    for g in G.values():
        if not g['ntasks']:g['nshards']=0;continue
        if a.shards is not None:g['nshards']=min(a.shards,g['ntasks'])
        else:g['nshards']=min(g['ntasks'],max(1,math.ceil(g['secs']/(H*3600*a.threads*EFFICIENCY))))
    njobs=sum(g['nshards']for g in G.values())
    if njobs==0:raise ValueError('the plan has no work (every group is empty)')
    nckpt_lo=sum(math.ceil(g['ntasks']/T)for g in G.values()if g['ntasks'])
    if nckpt_lo>a.max_checkpoints:raise ValueError(f'at least {nckpt_lo:,} checkpoint blocks > --max-checkpoints {a.max_checkpoints:,}; raise --checkpoint-tasks')
    pinned=(2+len(GROUPS))if bundle is not None else 0  # X9: the campaign's pinned copy of the design bundle
    files_lo=njobs+nckpt_lo+2*njobs+8*len(G)+32+pinned
    if os.environ.get('C8_SITE')=='expanse'and files_lo>EXPANSE_FILE_CAP:raise ValueError(f'at least {files_lo:,} projected files > {EXPANSE_FILE_CAP:,} (half the Expanse Lustre file quota)')
    F=MERGE_FAN_IN;merge={}
    for g in G.values():
        if not g['ntasks']:continue
        passes=merge_passes(g['nshards'],F)
        merge[g['name']]={'rows':g['ntasks'],'runs':g['nshards'],'passes':passes,'projected_seconds':g['ntasks']/MERGE_PHASE1_ROWS_PER_S+passes*g['ntasks']/MERGE_PHASE2_ROWS_PER_S}
    mmax=max((v['projected_seconds']for v in merge.values()),default=0.)
    if mmax>MERGE_MAX_HOURS*3600:raise ValueError(f'the largest group needs a projected {mmax/3600:.1f} h of merge > {MERGE_MAX_HOURS:g} h; split the campaign into batches')
    # The exact LPT per group, so that the block and file caps are checked on the real per-index task counts.
    for g in G.values():
        if not g['ntasks']:continue
        A=_lpt(g);g['shard_tasks']=A['cnt'].tolist();g['shard_load']=A['load'];del A
    nckpt=sum(math.ceil(t/T)for g in G.values()if g['ntasks']for t in g['shard_tasks'])
    if nckpt>a.max_checkpoints:raise ValueError(f'{nckpt:,} checkpoint blocks > --max-checkpoints {a.max_checkpoints:,}; raise --checkpoint-tasks')
    files=njobs+nckpt+2*njobs+8*len(G)+32+pinned
    print(f'projected files: {files:,} (per-index task files {njobs:,}, checkpoints {nckpt:,}, lane done markers and attempt logs {2*njobs:,}, group files)',file=sys.stderr)
    if os.environ.get('C8_SITE')=='expanse'and files>EXPANSE_FILE_CAP:raise ValueError(f'{files:,} projected files > {EXPANSE_FILE_CAP:,} (half the Expanse Lustre file quota)')
    seed_log=None if test_only else registration_log(a.forbid_seeds_from)  # Z15: the log this non-test plan registers its seed in
    # W9: the plan metadata every claim parses (the manifest's job entries, the inputs inventory), part of est_peak_bytes
    meta_bytes=njobs*JOB_ENTRY_BYTES+sum(len(inv[s][str(L)])for s in SECTORS for L in LOOPS)*INVENTORY_ROW_BYTES
    # Build in a private staging directory, publish with one rename.
    stage=out.with_name(out.name+f'.tmp.{os.environ.get("SLURM_JOB_ID")or os.getpid()}')
    if stage.exists():shutil.rmtree(stage)
    reg=None
    try:
        stage.mkdir(parents=True);(stage/'groups').mkdir()
        manifest=_build(a,stage,G,dict(T=T,H=H,basis=basis,boot=boot,test_only=test_only,tg=tg,rel=rel,im_sha=im_sha,I=I,exe=exe,build=build,build_record=build_record,
                                       rates_identity=rates_identity,rates_bytes=rates_bytes,rates_doc=rates_doc,cost_model=cost_model,cost_bytes=cost_bytes,cal=cal,bproxy=bproxy,
                                       bundle=bundle,forbidden=forbidden,merge=merge,files=files,P=P,R=R,skipped=skipped,task_s=task_s,min_chunk=min_chunk,
                                       numerics_route=numerics_route,cm_exc=cm_exc,seed_log=seed_log,meta_bytes=meta_bytes))
        if seed_log is None:os.rename(stage,out)
        else:reg=register_seed(seed_log,a.seed,out,forbidden,lambda:os.rename(stage,out))  # Z15: under the log's lock, then published
    except BaseException:
        shutil.rmtree(stage,ignore_errors=True);raise
    if reg is not None:print(f'C8: base seed {a.seed} registered in {reg["log"]} (source {out}; {reg["entries"]} entries) before the campaign was published (Z15)',file=sys.stderr)
    _print_plan(out,manifest)

def registration_log(forbid_files)->Path:
    """Z15: the seed log a non-test plan registers its base seed in: its first --forbid-seeds-from file ($C8_SEEDS in
    every documented command; Expanse adds a read-only copy of symmetry's log after it), which must be a tools/seeds.py
    log (schema c8-d2-seeds-1), not a plain list or a bundle's list. Checked before anything is created."""
    import seeds
    log=Path(forbid_files[0])
    try:seeds.read_log(log)
    except (OSError,ValueError)as e:
        raise ValueError(f'a non-test plan registers its base seed in its first --forbid-seeds-from file, which must be a tools/seeds.py seed log ($C8_SEEDS, schema '
                         f'{seeds.SCHEMA}; tools/seeds.py init creates one): {log}: {e}')from None
    return log

def register_seed(log:Path,seed:int,out:Path,forbidden:dict,publish_campaign)->dict:
    """Z15 (S6R3-F-02): register a non-test campaign's base seed in its seed log and publish the campaign, atomically
    under the log's lock (tools/seeds.py register): the fresh log is re-read and the seed re-checked against it and every
    other forbidden source of the plan (seed_refusal), so a seed that another plan or `seeds.py add` registered after this
    plan read the log is refused and nothing is published; the entry's source is the campaign directory (as `seeds.py add
    RUN` writes it, so plan.sh's add after the plan finds it present); the campaign is renamed into place while the lock
    is held. A failed publication leaves the seed registered, never reusable."""
    import seeds
    def check(doc):
        fresh=dict(forbidden)
        for k,v in seed_entries(doc,log).items():fresh.setdefault(k,v)
        why=seed_refusal(seed,fresh)
        return why+'; choose a fresh random seed (python3 -c "import secrets;print(secrets.randbits(63))")'if why else None
    try:return seeds.register(log,seed,str(out),check,publish_campaign)
    except Refuse as r:raise ValueError(str(r))from None

def _lpt(G_g):
    """Per-task arrays of one group in uid order, the LPT shard assignment (heaviest first, ties by uid), and the frozen
    position inside each shard (estimated cost descending, then uid)."""
    np=np_()
    gids=sorted(G_g['counts']);reps=G_g['reps'];n=G_g['ntasks']
    rep=np.empty(n,np.int64);gi=np.empty(n,np.int64);lo=np.empty(n,np.int64);hi=np.empty(n,np.int64);tot=np.empty(n,np.int64);cost=np.empty(n,np.float64)
    k=0
    for r in range(reps):
        for g in gids:
            N=G_g['counts'][g];ch=G_g['chunk'][g];m=N//ch;unit=(G_g['per'][g]if G_g['per'][g]is not None else G_g['units'][g])
            rep[k:k+m]=r;gi[k:k+m]=g;lo[k:k+m]=np.arange(0,N,ch);hi[k:k+m]=lo[k:k+m]+ch;tot[k:k+m]=N;cost[k:k+m]=ch*unit;k+=m
    order=np.argsort(-cost,kind='stable')  # cost descending, uid ascending
    ns=G_g['nshards'];heap=[(0.,i)for i in range(ns)];heapq.heapify(heap);shard=np.empty(n,np.int64);load_=[0.]*ns
    cl=cost.tolist();pop=heapq.heappop;push=heapq.heappush
    for u in order.tolist():
        c,i=pop(heap);x=c+cl[u];push(heap,(x,i));shard[u]=i;load_[i]+=cl[u]
    byshard=order[np.argsort(shard[order],kind='stable')]  # shard ascending, then LPT order (cost desc, uid asc)
    pos=np.empty(n,np.int64);cnt=np.bincount(shard,minlength=ns);start=np.concatenate([[0],np.cumsum(cnt)[:-1]])
    pos[byshard]=np.arange(n)-np.repeat(start,cnt)
    return dict(rep=rep,gi=gi,lo=lo,hi=hi,tot=tot,cost=cost,shard=shard,pos=pos,byshard=byshard,cnt=cnt,start=start,load=load_)

def _build(a,stage:Path,G:dict,x:dict)->dict:
    T=x['T'];I=x['I'];groups=[];jobs=[];est={};pmt={}
    if x['cost_bytes']is not None:(stage/'cost_model.json').write_bytes(x['cost_bytes'])
    if x['rates_bytes']is not None:
        (stage/'rates.json').write_bytes(x['rates_bytes'])
        if digest(stage/'rates.json')!=x['rates_identity']:raise RuntimeError('rates.json copy differs from its identity')
    if x['bundle']is not None:
        # X9: the bundle files assemble and combine need, from the bytes read_bundle verified, under the campaign
        for name,data in x['bundle']['files'].items():
            f=stage/PINNED_BUNDLE/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        if digest(stage/PINNED_BUNDLE/'design_meta.json')!=x['bundle']['meta_sha256']:raise RuntimeError('the pinned copy of design_meta.json differs from the bundle identity')
    for c,s,L in GROUPS:
        g=G[group_name(c,s,L)];p=stage/'groups'/g['name'];p.mkdir();(p/'tasks').mkdir()
        seeds=derive_seeds(a.seed,c,s,L);top=max(g['counts'].values(),default=1)
        net=make_net(p/'sobol.bin',g['reps'],4*L-1,g['bits'],seeds['net'],max(top,1))
        db=dbopen(p/'tasks.sqlite');db.executescript('CREATE TABLE tasks(uid INTEGER PRIMARY KEY,rep INTEGER,gi INTEGER,lo INTEGER,hi INTEGER,total INTEGER,cost REAL,shard INTEGER,pos INTEGER);'
                                                     'CREATE TABLE expected(rep INTEGER,gi INTEGER,total INTEGER,PRIMARY KEY(rep,gi));')
        db.executemany('INSERT INTO expected VALUES(?,?,?)',((r,gid,g['counts'][gid])for r in range(g['reps'])for gid in sorted(g['counts'])))
        shard_jobs=[]
        if g['ntasks']:
            A=_lpt(g);n=g['ntasks']
            rows=zip(range(n),A['rep'].tolist(),A['gi'].tolist(),A['lo'].tolist(),A['hi'].tolist(),A['tot'].tolist(),A['cost'].tolist(),A['shard'].tolist(),A['pos'].tolist())
            while True:
                chunk=list(itertools.islice(rows,200000))
                if not chunk:break
                db.executemany('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)',chunk)
            db.execute('CREATE INDEX shard_order ON tasks(shard,pos)');db.execute('CREATE INDEX stream_order ON tasks(rep,gi,lo)')
            kb={gid:int(g['byid'][gid]['kernel_bytes'])for gid in g['counts']}
            for sh in range(g['nshards']):
                idx=A['byshard'][A['start'][sh]:A['start'][sh]+A['cnt'][sh]]
                # the per-index task file, written in pieces of PLAN_WRITE_ROWS rows (W9's class: no index-sized text)
                f=p/'tasks'/f's{sh:06d}.tsv';th=hashlib.sha256();tbytes=0
                with f.open('xb')as fo:
                    for k0 in range(0,len(idx),PLAN_WRITE_ROWS):
                        sub=idx[k0:k0+PLAN_WRITE_ROWS]
                        piece=''.join(f'{u} {r} {gi} {lo} {hi} {t}\n'for u,r,gi,lo,hi,t in zip(sub.tolist(),A['rep'][sub].tolist(),A['gi'][sub].tolist(),
                                                                                                A['lo'][sub].tolist(),A['hi'][sub].tolist(),A['tot'][sub].tolist())).encode()
                        fo.write(piece);th.update(piece);tbytes+=len(piece)
                gis=A['gi'][idx].tolist();peak=0
                for b0 in range(0,len(gis),T):peak=max(peak,sum(kb[q]for q in set(gis[b0:b0+T])))
                ec=float(A['cost'][idx].sum())
                # W9: + the rows of one block (a claim streams its task file block by block) + the plan metadata it parses
                shard_jobs.append({'group':g['name'],'campaign':c,'sector':s,'L':L,'shard':sh,'tasks':int(len(idx)),'blocks':math.ceil(len(idx)/T),
                                   'tasks_file':f'groups/{g["name"]}/tasks/s{sh:06d}.tsv','tasks_sha256':th.hexdigest(),'tasks_bytes':tbytes,
                                   'est_core_seconds':None if x['boot']else ec,'est_proxy_units':ec if x['boot']else None,
                                   'est_peak_bytes':peak+a.threads*PROMOTED_SCRATCH_BYTES+BASE_PEAK_BYTES+min(T,len(idx))*TASK_ROW_PEAK_BYTES+x['meta_bytes']})
            db.commit()
            # Plan-time self-check (R07): the per-index files equal the SQLite rows by (shard, pos), compared through their
            # sha256 and length, each side streamed (the file in 1 MiB pieces, the rows in PLAN_WRITE_ROWS pieces)
            for j in shard_jobs:
                wh=hashlib.sha256();wn=0;cur=db.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY pos',(j['shard'],))
                while rows_:=cur.fetchmany(PLAN_WRITE_ROWS):
                    piece=''.join(f'{u} {r} {gi} {lo} {hi} {t}\n'for u,r,gi,lo,hi,t in rows_).encode();wh.update(piece);wn+=len(piece)
                if wn!=j['tasks_bytes']or wh.hexdigest()!=j['tasks_sha256']or (stage/j['tasks_file']).stat().st_size!=wn or digest(stage/j['tasks_file'])!=j['tasks_sha256']:
                    raise RuntimeError(f'per-index task file of {g["name"]} shard {j["shard"]} differs from tasks.sqlite')
        db.commit();db.close()
        rates_cfg=DEFAULT_RATES[c]if x['rates_identity']=='default'else'file'
        config={'schema':GROUP_SCHEMA,'name':g['name'],'campaign':c,'sector':s,'L':L,'order':ORDER,'seed':seeds['native'],'seed_scheme':'hashed','layout':0,
                'rate':rates_cfg,'rates_identity':x['rates_identity'],'replicates':g['reps'],'counts':{str(k):v for k,v in sorted(g['counts'].items())},
                'graph_points':{str(k):v for k,v in sorted(g['counts'].items())},'chunks':{str(k):v for k,v in sorted(g['chunk'].items())},
                'strata':{str(k):stratum_of(s,L,bool(g['byid'][k].get('primitive')))for k in sorted(g['counts'])},
                'net':net,'sum_mode':'compensated','shards':g['nshards'],'block_order':'pos: estimated cost descending, then uid','tasks':g['ntasks'],
                'tasks_sha256':digest(p/'tasks.sqlite'),'samples':sum(g['counts'].values())*g['reps'],'build':x['build'],'numerics':a.numerics,
                'cost_basis':x['basis'],'predicted_max_task_seconds':g['maxtask'],'preliminary_max_task_seconds':g['prelim']}
        dump(p/'config.json',config);groups.append({'name':g['name'],'sha256':digest(p/'config.json')})
        base=len(jobs)
        for i,j in enumerate(shard_jobs):jobs.append({'id':base+i,**j})
        est[g['name']]={'tasks':g['ntasks'],'shards':g['nshards'],'core_hours':None if x['boot']else g['secs']/3600,'proxy_units':g['proxy'],
                        'max_index_core_seconds':max((j['est_core_seconds']or 0. for j in shard_jobs),default=0.)if not x['boot']else None}
        pmt[g['name']]=g['maxtask']if not x['boot']else{'preliminary':g['prelim'],'label':PRELIMINARY}
    boot=x['boot'];tot=None if boot else sum(e['core_hours']for e in est.values())
    wall=None if boot else max((j['est_core_seconds']/(a.threads*EFFICIENCY)for j in jobs),default=0.)
    mem_mb=math.ceil((1.5*max(j['est_peak_bytes']for j in jobs)+2**30)/2**20)
    mmax=max((v['projected_seconds']for v in x['merge'].values()),default=0.)
    alloc=({'source':'pilot','points':x['P'],'replicates':x['R'],'label':('measurement under the frozen rate map '+x['rates_identity'])if x['rates_identity']!='default'else None}
           if a.pilot is not None else{'source':'design','bundle':str(x['bundle']['path']),'meta_sha256':x['bundle']['meta_sha256']})
    manifest=dict(schema=SCHEMA,tool_sha256={n:digest(ROOT/'tools'/n)for n in PINNED_TOOLS},dimension=2,order=ORDER,epsilon='2s-2',package=str(ROOT),
                  inputs=x['rel'],inputs_manifest_sha256=x['im_sha'],skipped_packs=sorted(f'{s}_L{L}'for s,L in x['skipped']),
                  backend=a.backend,numerics=a.numerics,approved_numerics_change=a.approved_numerics_change,numerics_route=x['numerics_route'],
                  build=x['build'],build_record=x['build_record'],
                  executable=x['exe'].name,executable_sha256=digest(x['exe']),rates_identity=x['rates_identity'],
                  rates=DEFAULT_RATES if x['rates_identity']=='default'else'file (rates.json)',threads=a.threads,checkpoint_tasks=T,
                  allocation=alloc,design=({'bundle':str(x['bundle']['path']),'meta_sha256':x['bundle']['meta_sha256'],'design_sha256':x['bundle']['meta']['design_sha256'],
                                            'batches':int(x['bundle']['design']['batches']),'s':{k:int(v['s'])for k,v in x['bundle']['design']['strata'].items()},
                                            'r':{k:int(v)for k,v in x['bundle']['design']['replicates'].items()},'test_only':bool(x['bundle']['meta'].get('test_only')),
                                            'pinned_copy':PINNED_BUNDLE}
                                           if x['bundle']else None),
                  seed=a.seed,seed_scheme='hashed',forbidden_seed_sources=sorted({str(v)for v in x['forbidden'].values()}),
                  seed_log=str(Path(x['seed_log']).resolve())if x['seed_log']is not None else None,groups=groups,jobs=jobs,
                  campaign_weights={'a':.5,'b':.5},power_sector='explicitly integrated; NOT assumed zero',
                  sampling_unit='complete graph-summed randomized replicate, not chunk',test_only=x['test_only'],test_graphs=x['tg'],
                  test_selection=a.test_selection if x['test_only']else None,cost_basis=x['basis'],
                  cost_model_sha256=hashlib.sha256(x['cost_bytes']).hexdigest()if x['cost_bytes']is not None else None,
                  cost_model_numerics=x['cost_model'].get('numerics')if x['cost_model']is not None else None,
                  cost_model_numerics_exception=x['cm_exc'][0]if x['cm_exc']else None,
                  calibration_sha256=digest(ROOT/'tools/calibration.json')if x['basis']=='calibrated_proxy'else None,
                  bootstrap_proxy={'sha256':digest(ROOT/'tools/bootstrap_proxy.json'),'label':PRELIMINARY}if boot else None,
                  chunking=({'bootstrap_chunk':a.bootstrap_chunk,'label':PRELIMINARY}if boot else{'task_seconds':x['task_s'],'min_chunk':x['min_chunk']})|{'max_task_seconds':a.max_task_seconds},
                  index_sizing={'index_hours':x['H'],'shards':a.shards,'assumed_efficiency':EFFICIENCY},
                  scale={'tasks':sum(j['tasks']for j in jobs),'checkpoints':sum(j['blocks']for j in jobs),'jobs':len(jobs),'projected_files':x['files'],
                         'merge_fan_in':MERGE_FAN_IN,'merge':x['merge'],'merge_projected_max_seconds':mmax,'suggested_merge_time':hms(max(3600,2*mmax+900))},
                  estimates={'basis':x['basis'],'unit':'seconds per point (cost model)'if x['basis']=='measured'else('proxy cost x calibration seconds per proxy unit'
                                if x['basis']=='calibrated_proxy'else'proxy units (max(1, M x T) x points); no time estimate'),
                             'groups':est,'total_core_hours':tot,'max_index_wall_seconds':wall,'suggested_time_seconds':None if boot else max(900,math.ceil(1.5*wall/60)*60),
                             'predicted_max_task_seconds':pmt,'estimate':'unavailable (bootstrap)'if boot else'available','mem_suggestion_mb':mem_mb,
                             'note':'planning estimates from a hardware-specific cost model or calibration, not measurements'})
    dump(stage/'manifest.json',manifest)
    return manifest

def _print_plan(out:Path,m:dict)->None:
    e=m['estimates'];ch=lambda v:float(f'{v:.4g}')if isinstance(v,float)else v
    mb=(out/'manifest.json').stat().st_size
    print(json.dumps({'directory':str(out),'jobs':len(m['jobs']),'tasks':m['scale']['tasks'],'checkpoints':m['scale']['checkpoints'],'backend':m['backend'],
                      'numerics':m['numerics'],'rates_identity':m['rates_identity'],'test_only':m['test_only'],'cost_basis':m['cost_basis'],
                      'estimated_core_hours':ch(e['total_core_hours'])if e['total_core_hours']is not None else e['estimate'],
                      'estimated_core_hours_by_group':{k:(ch(v['core_hours'])if v['core_hours']is not None else'unavailable (bootstrap)')for k,v in e['groups'].items()},
                      'max_index_wall_seconds':ch(e['max_index_wall_seconds'])if e['max_index_wall_seconds']is not None else'unavailable (bootstrap)',
                      'predicted_max_task_seconds':{k:(ch(v)if not isinstance(v,dict)else{'preliminary':ch(v['preliminary']),'label':v['label']})for k,v in e['predicted_max_task_seconds'].items()},
                      'projected_files':m['scale']['projected_files'],'manifest_bytes':mb,'merge_passes':{k:v['passes']for k,v in m['scale']['merge'].items()},
                      'merge_projected_max_seconds':ch(m['scale']['merge_projected_max_seconds']),'suggested_merge_time':m['scale']['suggested_merge_time'],
                      'array_mem_suggestion_mb':e['mem_suggestion_mb'],'seed_log':m.get('seed_log')},indent=2))
    if len(m['jobs'])>MAX_ARRAY:print(f'note: {len(m["jobs"])} jobs exceed one array of {MAX_ARRAY}; slurm/submit.sh splits them into offset windows (C8_INDEX_OFFSET)',file=sys.stderr)

# ---------------------------------------------------------------- verification of a planned campaign
def verify_base(directory:Path,check_executable=True,accept_tool_change=False,vendored=False):
    """Manifest, pinned tools, inputs manifest, small inputs, cost model, rates map and (optionally) the executable and
    the vendored assembly pins (merge and assemble; run never opens vendor/). Returns (manifest, Inputs, manifest
    sha256, accepted tool changes). A changed tool is an error unless accept_tool_change (merge/assemble only)."""
    data=(Path(directory)/'manifest.json').read_bytes();m=json.loads(data);mh=hashlib.sha256(data).hexdigest()
    if str(m.get('schema','')).startswith('c7-'):raise ValueError(C7_MESSAGE.format(d=directory,s=m.get('schema')))
    if m.get('schema')!=SCHEMA or m.get('dimension')!=2 or m.get('order')!=ORDER:raise ValueError(f'campaign schema {m.get("schema")} is not {SCHEMA}')
    changes={}
    for n,h in m['tool_sha256'].items():
        f=ROOT/'tools'/n;cur=digest(f)if f.exists()else None
        if cur!=h:
            if not accept_tool_change:raise ValueError(f'Checksum mismatch: tools/{n} differs from the tool pinned by the plan; merge and assemble accept a changed tool only with --accept-tool-change (recorded as provenance)')
            changes[n]={'planned':h,'current':cur}
    im=read_verified(ROOT/m['inputs']/'manifest.json',m['inputs_manifest_sha256'])
    if im.get('schema')!=INPUTS_SCHEMA:raise ValueError('wrong inputs manifest')
    I=Inputs(m['inputs'],im)
    if m.get('cost_model_sha256'):checked(Path(directory)/'cost_model.json',m['cost_model_sha256'])
    if m['rates_identity']!='default':checked(Path(directory)/'rates.json',m['rates_identity'])
    for name in SMALL_INPUTS:checked(I.where(name),I.sha(name))
    if check_executable:checked(ROOT/'bin'/m['executable'],m['executable_sha256'])
    if vendored:
        v=im.get('vendored_assembly')or{}
        if not v:raise ValueError('the inputs manifest carries no vendored assembly pins')
        checked(ROOT/v['handoff_path'],v['handoff_sha256'])
        for name,h in v['files'].items():checked(ROOT/name,h)
    return m,I,mh,changes

def group_of(directory:Path,m:dict,name:str,schema:str=GROUP_SCHEMA):
    """The group directory and its config, verified against the manifest's pin (tasks.sqlite is not read here). schema:
    the config schema (design.py's reader of another package's campaign passes <prefix>-group-1; H6)."""
    p=Path(directory)/'groups'/name;cfg=read_verified(p/'config.json',next(g['sha256']for g in m['groups']if g['name']==name))
    if cfg.get('schema')!=schema:raise ValueError('wrong group config schema')
    return p,cfg

def check_tasks_db(p:Path,cfg:dict)->None:
    """status, merge and verify_delivery verify the group's tasks.sqlite once per group (run never opens it, R07)."""
    checked(p/'tasks.sqlite',cfg['tasks_sha256'])

def task_file_differs(j:dict)->ValueError:
    return ValueError(f'the task file of index {j["id"]} ({j["tasks_file"]}) differs from the manifest pin (sha256, bytes)')

def snapshot_tasks(directory:Path,j:dict,dest:Path,on_read=None)->Path:
    """W9 (S6-C-R4-03, Stage-6 fix round 4): the verified, immutable snapshot a claim streams its task rows from. The
    index's task file is copied into the job-private runtime (dest, created exclusively) in pieces of TASK_READ_CHUNK
    bytes, hashed while it is copied, checked against the manifest pin (bytes, sha256) and made read-only; nothing of
    the file is held in memory. A file that differs from the pin is refused before any block. on_read(nbytes) is told
    the bytes read from the shared file (claim_io's own bytes). Replaces job_rows, which read, decoded and kept every
    row of the index (an L8 index of 16 million tasks: gigabytes, before any native work)."""
    src=Path(directory)/j['tasks_file'];h=hashlib.sha256();n=0;fd=os.open(src,os.O_RDONLY)
    try:
        with open(dest,'xb')as o:
            while b:=os.read(fd,TASK_READ_CHUNK):
                h.update(b);n+=len(b);o.write(b)
    finally:
        os.close(fd)
        if on_read is not None:on_read(n)
    if n!=j['tasks_bytes']or h.hexdigest()!=j['tasks_sha256']:raise task_file_differs(j)
    os.chmod(dest,0o400);return dest

def snapshot_blocks(path:Path,j:dict,T:int,on_read=None):
    """W9: the task rows (uid rep graph begin end total, pos order) of a verified snapshot (snapshot_tasks), streamed in
    blocks of T: the file is read in pieces of TASK_READ_CHUNK bytes and at most one block of rows and one piece are
    held, whatever the index's size. A line that is not six integers, an unterminated last line or a row count other
    than the plan's is refused (ValueError). on_read(nbytes) is told every piece read (claim_io)."""
    fd=os.open(path,os.O_RDONLY);block=[];count=0;rest=b''
    try:
        while b:=os.read(fd,TASK_READ_CHUNK):
            if on_read is not None:on_read(len(b))
            lines=(rest+b).split(b'\n');rest=lines.pop()
            for line in lines:
                r=tuple(map(int,line.split()))
                if len(r)!=6:raise ValueError(f'malformed task file {j["tasks_file"]}')
                block.append(r);count+=1
                if len(block)==T:yield block;block=[]
    finally:os.close(fd)
    if rest or count!=j['tasks']:raise ValueError(f'malformed task file {j["tasks_file"]}')
    if block:yield block

def iter_job_blocks(directory:Path,j:dict,T:int):
    """The index's task rows in blocks of T (pos order), streamed (merge phase 1, O02): the file is checked against the
    manifest pin (bytes, sha256) before the first block and hashed again while it is parsed, the second check raising
    before the iteration ends, so no more than one block of rows is ever held. Same refusals as job_rows."""
    path=Path(directory)/j['tasks_file']
    def differs():return ValueError(f'the task file of index {j["id"]} ({j["tasks_file"]}) differs from the manifest pin (sha256, bytes)')
    if path.stat().st_size!=j['tasks_bytes']or digest(path)!=j['tasks_sha256']:raise differs()
    h=hashlib.sha256();size=0;count=0;block=[]
    with path.open('rb')as f:
        for line in f:
            h.update(line);size+=len(line);r=tuple(map(int,line.split()))
            if len(r)!=6:raise ValueError(f'malformed task file {j["tasks_file"]}')
            block.append(r);count+=1
            if len(block)==T:yield block;block=[]
    if size!=j['tasks_bytes']or h.hexdigest()!=j['tasks_sha256']:raise differs()
    if count!=j['tasks']:raise ValueError(f'malformed task file {j["tasks_file"]}')
    if block:yield block

def rate_map_for(directory:Path,m:dict):
    """The campaign's frozen rate map, parsed from the bytes verified against its identity (None for 'default')."""
    return read_verified(Path(directory)/'rates.json',m['rates_identity'])['rates']if m['rates_identity']!='default'else None

def validate_checkpoint(doc,block,cfg,m,mh,rates=None,runtime_key=None,gmp_binding=None):
    """A committed checkpoint against its block: identity, runtime, payload digest, native metadata (order 8, numerics,
    rates identity, rate), coordinates, jets, counters and the class-B tail fields; with runtime_key (run-skip, the
    duplicate check and both merges: the campaign's runtime compatibility identity, X8) also the runtime identity of the
    checkpoint's fingerprint (common.runtime_identity_key); with gmp_binding (gate_gmp_binding of a gated campaign; the
    same callers, W8) also that its fingerprint's libgmp is the one the gate validated (gmp_binding_problem); returns
    the native record."""
    if doc.get('manifest_sha256')!=mh or doc.get('config_hash')!=object_hash(cfg):raise ValueError('checkpoint identity mismatch')
    rt=doc.get('runtime')or{}
    if rt.get('executable_sha256')!=m['executable_sha256']or doc.get('executable_sha256')!=m['executable_sha256']:raise ValueError('checkpoint was produced by a different executable')
    if rt.get('inputs_manifest_sha256')!=m['inputs_manifest_sha256']:raise ValueError('checkpoint was produced from different inputs')
    if rt.get('net_sha256')!=cfg['net']['sha256']:raise ValueError('checkpoint was produced from a different Sobol net')
    if rt.get('rates_identity')!=m['rates_identity']or cfg.get('rates_identity')!=m['rates_identity']:raise ValueError('checkpoint was produced under another rates identity')
    if runtime_key is not None:
        bad=fingerprint_malformed(rt.get('fingerprint'))  # Y8: no identity can be read from it (refused, never a crash)
        if bad:raise ValueError(f'checkpoint was produced under another runtime library stack: {bad}, so it carries no runtime identity (the campaign\'s {runtime_key[:12]}; X8, Y8)')
        k=runtime_identity_key(rt.get('fingerprint'))
        if k!=runtime_key:raise ValueError(f'checkpoint was produced under another runtime library stack (runtime identity {str(k)[:12]}, the campaign\'s {runtime_key[:12]}; '
                                           f'host {(rt.get("fingerprint")or{}).get("host")}): its libraries differ from the campaign\'s (X8)')
    if gmp_binding is not None:
        fpx=rt.get('fingerprint');why=gmp_binding_problem(runtime_identity(fpx)if isinstance(fpx,dict)else None,gmp_binding,bool(m.get('test_only')))
        if why:raise ValueError(f'checkpoint was produced by a worker that is not bound to its gate\'s libgmp: {why} (W8; host '
                                f'{(fpx if isinstance(fpx,dict)else{}).get("host")}); a changed library needs a fresh J-FLAG gate')
    n=doc['native']
    if object_hash(n)!=doc.get('payload_sha256'):raise ValueError('checkpoint payload corruption')
    b=cfg['build'];expected={'schema':NATIVE_SCHEMA,'order':ORDER,'L':cfg['L'],'seed':cfg['seed'],'layout':cfg['layout'],'bits':cfg['net']['bits'],'sum_mode':cfg['sum_mode'],
                             'mp_backend':b['mp_backend'],'mp_digits10':b['mp_digits10'],'long_double_bits':b['long_double_bits'],'numerics':m['numerics']}
    for k,v in expected.items():
        if n.get(k)!=v:raise ValueError('native metadata mismatch: '+k)
    tol=D(2)**(-b['long_double_bits']+1);table=None
    if cfg['rate']=='file':
        if n.get('rate')!='file':raise ValueError('importance rate mismatch: the campaign uses its frozen rate map')
        table=rates[cfg['campaign']][cfg['sector']][str(cfg['L'])]
    elif abs(D(n['rate'])-D(cfg['rate']))>tol:raise ValueError('importance rate mismatch')
    if len(n['rows'])!=len(block):raise ValueError('incomplete checkpoint')
    K=9-cfg['L']
    for want,r in zip(block,n['rows']):
        if tuple(r[k]for k in ('uid','rep','graph','begin','end','total'))!=tuple(want):raise ValueError('wrong task coordinates')
        if len(r['values'])!=2*K or any(not D(v).is_finite()for v in r['values']):raise ValueError('invalid jet')
        if not 0<=r['mp']<=r['quad']<=r['end']-r['begin']:raise ValueError('invalid promotion counters')
        top=r.get('tail_top');npts=r['end']-r['begin']
        if not isinstance(top,list)or len(top)!=min(16,npts)or any(D(x)<D(y)for x,y in zip(top,top[1:]))or not D(r.get('tail_sum','nan')).is_finite()\
           or not isinstance(r.get('tail_argmax'),int)or not r['begin']<=r['tail_argmax']<r['end']:raise ValueError('invalid class-B tail fields')
        if cfg['rate']=='file'and abs(D(r.get('rate','nan'))-D(table[str(r['graph'])]))>tol:raise ValueError(f'row rate {r.get("rate")} of graph {r["graph"]} is off the frozen rate map')
    return n

# ---------------------------------------------------------------- execution
PREAD_CHUNK=1<<30  # one os.pread call reads at most this (macOS refuses a single read above INT_MAX bytes)

def read_member(fd:int,offset:int,length:int)->bytes:
    """Exactly the `length` bytes at `offset` of the open file descriptor `fd`, and nothing else (F12): os.pread in a loop
    over short reads, with no Python buffer and no shared file position. A buffered reader (`open(pack,'rb')`) sizes its
    buffer by the file system's st_blksize (524,288 bytes on BeeGFS) and, after a seek outside its buffer, refills one
    whole buffer behind the bytes asked for: up to st_blksize of neighbouring pack data per member, 0.7 bytes per staged
    byte at L8 on symmetry (2026-10-05). Fewer than `length` bytes come back only at the end of the file."""
    if length<=0:return b''
    parts=[];got=0
    while got<length:
        b=os.pread(fd,min(length-got,PREAD_CHUNK),offset+got)
        if not b:break
        parts.append(b);got+=len(b)
    return parts[0]if len(parts)==1 else b''.join(parts)

def stage_graphs(td,I:Inputs,cfg,block,inventory):
    """Read only the assigned graph members of the pack, each exactly (read_member: os.pread, no Python buffer; F12),
    verify their content hashes and write them to td/graphs/L<L>/G<id>.txt. Returns (graphs root, bytes read from the
    pack, members): the bytes read are the claim's own staged-member bytes (R07) and equal the members' lengths."""
    root=td/'graphs';dest=root/f'L{cfg["L"]}';dest.mkdir(parents=True);gids=sorted({r[2]for r in block});nread=0
    fd=os.open(I.pack(cfg['sector'],cfg['L']),os.O_RDONLY)
    try:
        for gi in gids:
            row=inventory[gi];data=read_member(fd,row['offset'],row['length']);nread+=len(data)
            if len(data)!=row['length']or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Packed graph content mismatch')
            (dest/f'G{gi}.txt').write_bytes(data)
    finally:os.close(fd)
    return root,nread,len(gids)

def stage_runtime(directory:Path,runtime:Path,m:dict,I:Inputs,cfg:dict,net:Path)->dict:
    """Copy the plan's executable, gamma_d2_8.txt, the group's Sobol net and (R7) the campaign's frozen rates.json into
    the job-private directory; verify every COPY and use only the copies (graph members are staged per block)."""
    src=ROOT/'bin'/m['executable'];exe=runtime/src.name;shutil.copyfile(src,exe);os.chmod(exe,0o700);exe_sha=digest(exe)
    if exe_sha!=m['executable_sha256']:raise ValueError(f'{src} differs from the planned executable; never rebuild inside a campaign')
    gamma=runtime/GAMMA;shutil.copyfile(I.where(GAMMA),gamma);checked(gamma,I.sha(GAMMA))
    netcopy=runtime/'sobol.bin';shutil.copyfile(net,netcopy);net_sha=digest(netcopy)
    if net_sha!=cfg['net']['sha256']:raise ValueError('the Sobol net differs from the plan: '+str(net))
    out={'executable':exe,'gamma':gamma,'net':netcopy,'executable_sha256':exe_sha,'inputs_manifest_sha256':m['inputs_manifest_sha256'],'net_sha256':net_sha,
         'rates_identity':m['rates_identity'],'rates':None}
    if m['rates_identity']!='default':
        rc=runtime/'rates.json';shutil.copyfile(Path(directory)/'rates.json',rc);data=rc.read_bytes()
        if hashlib.sha256(data).hexdigest()!=m['rates_identity']:raise ValueError('the staged copy of rates.json differs from the campaign\'s rates identity; nothing run')
        out['rates']=json.loads(data)['rates']
    return out

SCIENTIFIC=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs','tail_top','tail_sum','tail_argmax')
STOP_SIGNALS=(signal.SIGTERM,signal.SIGINT,signal.SIGHUP)
# Native children of `run`, and the deferred stop signal of a launch in progress (C7(2) IR2-02); 'omp' the claim's
# OpenMP team request ({'threads', 'check'}, set by _run) and 'team' the last launch's team record (Y2).
_NATIVE={'launching':False,'pending':None,'children':[],'omp':None,'team':None}

class TeamRefused(RuntimeError):
    """Y2: the native worker did not show the requested OpenMP team (common.TeamWatch verdict 'smaller'); it was
    stopped and nothing of its block is kept."""
    def __init__(self,record:dict):super().__init__(team_message(record));self.record=record

class Terminated(BaseException):
    """Raised by the SIGTERM/SIGINT/SIGHUP handler of `run`; unwinds through the cleanup of the job-private runtime."""
    def __init__(self,signum):super().__init__(f'stopped by signal {signum}');self.signum=signum

def _stop(signum,frame):
    for s in STOP_SIGNALS:signal.signal(s,signal.SIG_IGN)  # a second signal must not interrupt the cleanup
    if _NATIVE['launching']:_NATIVE['pending']=signum;return
    raise Terminated(signum)

def _after_launch(child):"""Test seam: called right after a native child is created and registered, while stop signals are deferred."""

# ---------------------------------------------------------------- reads per claim (R07, F9) and the CPU vendor pin (F5)
def proc_rchar()->int|None:
    """rchar of /proc/self/io: the bytes read by this process and by its children reaped so far (Linux); None elsewhere."""
    try:
        with open('/proc/self/io','rb')as f:data=f.read()
    except OSError:return None
    for line in data.split(b'\n'):
        if line.startswith(b'rchar:'):return int(line.split()[1])
    return None

_IO:dict={}
def _io_reset()->None:
    _IO.clear();_IO.update(index=None,rchar_start=proc_rchar(),native={'launches':0,'rchar':0,'unmeasured':0},fingerprint_bytes=None,fingerprint_rchar=None,
                          fingerprint_key=None,cpu_vendor=None,own={})

def _own(category:str,nbytes:int,files:int=1)->None:
    """Bytes this claim process reads of its own data: its task file, its checkpoints, the staged pack members of its
    blocks (the bytes stage_graphs read from the pack, exactly the members' since the F12 fix), each block's task file
    (hashed) and the native outputs read back."""
    o=_IO.setdefault('own',{}).setdefault(category,{'files':0,'bytes':0});o['files']+=files;o['bytes']+=int(nbytes)

def _native_io(r0)->None:
    """Add the rchar of one native launch: /proc/self/io after the child was reaped minus before its launch (this
    process reads nothing while it waits). Its reads are measured, not modelled: they are all of the claim's own
    job-private copies, the executable and its libraries (on symmetry 1.0008 bytes per staged byte at L8, its staged
    copies once; the 0.7 extra bytes per staged byte of Stage-5 J-SMK-4 were this process's buffered pack reads, F12)."""
    r1=proc_rchar();n=_IO.setdefault('native',{'launches':0,'rchar':0,'unmeasured':0});n['launches']+=1
    if r0 is None or r1 is None:n['unmeasured']+=1
    else:n['rchar']+=r1-r0

def claim_io_record(status:str)->dict:
    """The claim's 'claim_io' record (R07, F9): rchar at exit, and non_own_bytes = rchar - own bytes - native rchar, with
    and without the fingerprint (its in-process bytes, and its rchar with the ldd probe). tools/claim_io.py compares it
    between indices of the smallest and the largest group."""
    r=proc_rchar();own=_IO.get('own')or{};n=_IO.get('native')or{'launches':0,'rchar':0,'unmeasured':0};ob=sum(v['bytes']for v in own.values())
    rec={'schema':CLAIM_IO_SCHEMA,'index':_IO.get('index'),'status':status,'rchar':r,'rchar_start':_IO.get('rchar_start'),'native':n,
         'fingerprint_key':_IO.get('fingerprint_key'),'fingerprint_bytes':_IO.get('fingerprint_bytes'),'fingerprint_rchar':_IO.get('fingerprint_rchar'),
         'cpu_vendor':_IO.get('cpu_vendor'),'own':own,'own_bytes':ob,'non_own_bytes':None,'non_own_minus_fingerprint_bytes':None,'non_own_minus_fingerprint_rchar':None}
    if r is not None and not n['unmeasured']:
        rec['non_own_bytes']=r-ob-n['rchar']
        if rec['fingerprint_bytes']is not None:rec['non_own_minus_fingerprint_bytes']=rec['non_own_bytes']-rec['fingerprint_bytes']
        if rec['fingerprint_rchar']is not None:rec['non_own_minus_fingerprint_rchar']=rec['non_own_bytes']-rec['fingerprint_rchar']
    return rec

def pin_cpu_vendor(directory:Path,cpu:dict,idx:int,fp:dict)->dict:
    """F5: the campaign's CPU vendor. The first claim publishes RUN/cpu_vendor.json (no-clobber); every later claim reads
    it, and a claim on another vendor stops before any block (SystemExit 64): native rows differ between CPU vendors at
    about 1e-16 relative (glibc's x87 expl/logl in the kernel's first pass), so a duplicate block run on the other vendor
    would conflict and twin/restart bitwise identity holds only within a vendor (docs/HPC.md)."""
    path=Path(directory)/CPU_PIN
    doc={'schema':CPU_PIN_SCHEMA,'vendor':cpu['vendor'],'family':cpu.get('family'),'model':cpu.get('model'),'model_name':cpu.get('model_name'),
         'first_claim':{'index':idx,'host':fp.get('host'),'slurm_job':os.environ.get('SLURM_JOB_ID'),'utc':utc()},
         'rule':'every claim of this campaign runs on this CPU vendor (F5); production.py run refuses another one (exit 64)'}
    try:dump(path,doc);return doc
    except FileExistsError:pin=load(path)
    if pin.get('vendor')!=cpu['vendor']:
        print(f'C8: index {idx}: this node ({fp.get("host")}) has CPU vendor {cpu["vendor"]} ({cpu.get("model_name")}), but the campaign\'s first claim '
              f'(index {pin.get("first_claim",{}).get("index")} on {pin.get("first_claim",{}).get("host")}) ran on {pin.get("vendor")} ({pin.get("model_name")}); '
              f'{path}. Native rows differ between CPU vendors (x87 expl/logl, docs/HPC.md): keep a campaign on one vendor and submit it '
              'to the partitions of that vendor only (symmetry: amdq, not defq). Nothing run (exit 64).',file=sys.stderr,flush=True)
        raise SystemExit(VENDOR_REFUSED)
    return pin

def _identity_diff(a:dict,b:dict)->list[str]:
    """The fields in which two runtime identities differ (for the refusal message)."""
    out=[k for k in ('glibc','interpreter_sha256','ldd','preload_order','loader_env')if (a or{}).get(k)!=(b or{}).get(k)]  # W7: also the preload order and GLIBC_TUNABLES
    la,lb=(a or{}).get('libraries')or{},(b or{}).get('libraries')or{}
    out+=[f'library {n}'for n in sorted(set(la)|set(lb))if la.get(n,'(absent)')!=lb.get(n,'(absent)')]
    return out

def pin_runtime_identity(directory:Path,fp:dict,idx:int)->dict:
    """X8: the campaign's runtime compatibility identity (common.runtime_identity: glibc, the ELF interpreter's and every
    ldd-resolved library's sha256, whether ldd answered; not the host, the Slurm ids or the CPU model). The first claim
    publishes RUN/runtime_identity.json (no-clobber); every later claim compares its own identity with it and a claim on
    another library stack stops before any block (SystemExit 64, as for another CPU vendor), so a campaign never mixes
    blocks computed with different libgmp, libquadmath, libgomp or libc. Returns the pin."""
    path=Path(directory)/RUNTIME_PIN;ident=runtime_identity(fp);key=object_hash(ident)
    doc={'schema':RUNTIME_PIN_SCHEMA,'key':key,'identity':ident,
         'first_claim':{'index':idx,'host':fp.get('host'),'cpu_model':fp.get('cpu_model'),'slurm_job':os.environ.get('SLURM_JOB_ID'),'utc':utc()},
         'rule':'every claim of this campaign runs with this run-time library stack (X8); production.py run refuses another one (exit 64), '
                'and run-skip and merge refuse a checkpoint of another one'}
    try:dump(path,doc);return doc
    except FileExistsError:pin=read_runtime_pin(directory)
    if pin['key']!=key:
        diff=_identity_diff(pin['identity'],ident)
        print(f'C8: index {idx}: this node ({fp.get("host")}) runs the executable with another run-time library stack than the campaign\'s first claim '
              f'(index {pin.get("first_claim",{}).get("index")} on {pin.get("first_claim",{}).get("host")}): runtime identity {key[:12]} vs {pin["key"][:12]}, '
              f'differing in {", ".join(diff[:6])or"(unknown)"}; {path}. Blocks computed with other libraries are not mixed in one campaign (X8): '
              'submit it to nodes with the same image only. Nothing run (exit 64).',file=sys.stderr,flush=True)
        _IO['refusal']='runtime identity refused'
        raise SystemExit(VENDOR_REFUSED)
    return pin

def read_runtime_pin(directory:Path)->dict|None:
    """RUN/runtime_identity.json, checked (schema, key = the hash of its identity), or None when absent."""
    path=Path(directory)/RUNTIME_PIN
    if not path.exists():return None
    pin=load(path)
    if not isinstance(pin,dict)or pin.get('schema')!=RUNTIME_PIN_SCHEMA or object_hash(pin.get('identity'))!=pin.get('key'):
        raise ValueError(f'{path} is not a valid {RUNTIME_PIN_SCHEMA} pin (its key is not the hash of its identity); nothing run')
    return pin

def campaign_runtime_key(directory:Path,m:dict)->tuple[str|None,str]:
    """(key, source) of the runtime identity every checkpoint of the campaign must carry (both merges, X8): the pin of
    the first claim; for a campaign whose claims predate the pin, the identity of its first existing checkpoint in
    (index, block) order, so that the merge still refuses a campaign that mixes library stacks. That checkpoint must
    carry a well-formed runtime fingerprint (common.fingerprint_malformed): one without (missing, not a record, or
    lacking its library map) is refused (ValueError, Y8) instead of disabling the check for every other checkpoint.
    (None, 'no checkpoint') only for a campaign with no checkpoint at all."""
    pin=read_runtime_pin(directory)
    if pin is not None:return pin['key'],RUNTIME_PIN
    for j in m['jobs']:
        for k in range(j['blocks']):
            f=Path(directory)/'groups'/j['group']/'checkpoints'/f'{block_name(j["shard"],k)}.json'
            if f.exists():
                fp=(checkpoint_runtime(f)or{}).get('fingerprint');bad=fingerprint_malformed(fp);rel=f.relative_to(directory)
                if bad:raise ValueError(f'{rel}: {bad}; without {RUNTIME_PIN} the campaign\'s runtime identity is that of its first checkpoint, so it cannot be '
                                        'established and no checkpoint can be checked against it (X8, Y8). Nothing merged: re-run that block (delete the '
                                        'checkpoint and run its index) or restore its record')
                return runtime_identity_key(fp),f'the first checkpoint {rel} (no {RUNTIME_PIN})'
    return None,'no checkpoint'

def _team_stop(child)->None:
    """TeamWatch's action on a smaller team: stop the worker (SIGTERM; run_native then refuses the block)."""
    try:child.terminate()
    except OSError:pass

def run_native(cmd,log):
    """Run one native work block in the controlled OpenMP environment (common.omp_child_env: no inherited OMP_*,
    GOMP_* or KMP_* control, OMP_NUM_THREADS = the claim's threads, OMP_DYNAMIC=FALSE, close binding on cores; Y2)
    and watch its team (common.TeamWatch; for a worker that is an ELF executable, on Linux): a worker that has not
    shown the requested team after TEAM_DEADLINE_SECONDS of wall time and TEAM_CPU_SECONDS of CPU time is stopped and
    the block refused (TeamRefused); one that waits (no CPU time) is not. The team
    record is left in _NATIVE['team']. The child is registered before any stop signal can unwind."""
    omp=_NATIVE.get('omp')or{'threads':int(cmd[9]),'check':False}  # the worker's command line: threads is its 10th word
    _NATIVE['team']=None;_NATIVE['launching']=True
    try:child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=omp_child_env(omp['threads']));_NATIVE['children'].append(child);_after_launch(child)
    except BaseException:
        _NATIVE['launching']=False
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        raise
    _NATIVE['launching']=False;watch=None
    try:
        watch=TeamWatch(child,omp['threads'],omp['check'],on_smaller=_team_stop)
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        rc=child.wait()
    except BaseException:
        if watch is not None:_NATIVE['team']=watch.stop()
        stop_children();raise
    _NATIVE['team']=team=watch.stop()
    _NATIVE['children'].remove(child)
    if team['verdict']=='smaller':raise TeamRefused(team)
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
    with 128+signal; committed checkpoints stay (publication is atomic), the interrupted block is redone later."""
    main_thread=threading.current_thread()is threading.main_thread()
    _NATIVE.update(launching=False,pending=None,children=[],omp=None,team=None)
    old={s:signal.signal(s,_stop)for s in STOP_SIGNALS}if main_thread else{}
    _io_reset();status='error'
    try:_run(a);status='ok'
    except Terminated as t:
        status=f'signal {t.signum}'
        print(f'run: {t}; native work stopped, job-private runtime removed, committed checkpoints kept',file=sys.stderr,flush=True)
        raise SystemExit(128+t.signum)
    except SystemExit as e:
        status=(_IO.get('refusal')or'cpu vendor refused')if e.code==VENDOR_REFUSED else f'exit {e.code}';raise
    finally:
        _NATIVE['omp']=None
        # R07/F9: one claim_io line at exit (before the handlers are restored: a second stop signal stays ignored)
        try:print('claim_io '+json.dumps(claim_io_record(status),sort_keys=True),flush=True)
        except Exception as e:print(f'claim_io: not recorded ({type(e).__name__}: {e})',file=sys.stderr,flush=True)
        for s,h in old.items():signal.signal(s,h)

def _run(a):
    directory=a.directory.resolve();m,I,mh,_=verify_base(directory);idx=a.index
    if idx is None:
        if 'SLURM_ARRAY_TASK_ID'not in os.environ:raise ValueError('give --index or run inside a Slurm array (SLURM_ARRAY_TASK_ID)')
        off=os.environ.get('C8_INDEX_OFFSET','0')
        if not off.isdigit():raise ValueError('C8_INDEX_OFFSET must be a non-negative integer')
        idx=int(off)+int(os.environ['SLURM_ARRAY_TASK_ID'])
    if not 0<=idx<len(m['jobs']):raise ValueError('job index outside plan')
    _IO['index']=idx
    lo=loader_overrides()  # W7: before anything is staged, pinned or run
    if lo:
        print(f'C8: index {idx}: {loader_refusal(lo)}. Nothing was pinned or run (exit 64).',file=sys.stderr,flush=True)
        _IO['refusal']='loader override refused';raise SystemExit(VENDOR_REFUSED)
    j=m['jobs'][idx];p,cfg=group_of(directory,m,j['group'])
    gb=gate_gmp_binding(m)  # W8: the libgmp the gate of a gated executable validated (None otherwise)
    threads=a.threads or m['threads'];T=m['checkpoint_tasks']
    if threads<1:raise ValueError('invalid thread count')
    if threads>T:raise ValueError(f'{threads} threads exceed checkpoint_tasks={T}: at most {T} threads can ever be busy; use fewer threads or re-plan')
    if T<16*threads:print(f'warning: checkpoint_tasks={T} < 16 x {threads} threads; per-block barriers and start-up will idle cores',file=sys.stderr)
    scratch=a.scratch or os.environ.get('SLURM_TMPDIR')or None
    # W23's class: the inventory parsed from the bytes verified against the inputs manifest (verify_base checked the file;
    # a re-read could stage members by another inventory's offsets and digests)
    inv={r['id']:r for r in read_verified(I.where('inventory.json'),I.sha('inventory.json'))[cfg['sector']][str(cfg['L'])]}
    # The runtime is created with stop signals deferred (as a launch is), so that a signal arriving between the mkdir
    # and the try below cannot leave it behind; a deferred signal stops the run inside the try (cleanup below).
    _NATIVE['launching']=True;runtime=None
    try:
        runtime=Path(tempfile.mkdtemp(prefix='c8d2_runtime_',dir=scratch));_NATIVE['launching']=False
        if _NATIVE['pending']is not None:raise Terminated(_NATIVE['pending'])
        # W9: the index's task rows come from a verified job-private snapshot, streamed one block at a time
        snap=snapshot_tasks(directory,j,runtime/f'tasks.{idx}.tsv',on_read=lambda n:_own('task_file',n))
        rt=stage_runtime(directory,runtime,m,I,cfg,p/'sobol.bin');counter={'bytes':0};cpu={}
        r0=proc_rchar();fp=fingerprint(rt['executable'],counter,cpu);r1=proc_rchar()
        _IO.update(fingerprint_bytes=counter['bytes'],fingerprint_rchar=None if r0 is None or r1 is None else r1-r0,fingerprint_key=fingerprint_key(fp),cpu_vendor=cpu['vendor'])
        print(f'fingerprint {fingerprint_key(fp)} ({fp.get("cpu_model")}); fingerprint_bytes {counter["bytes"]}; cpu vendor {cpu["vendor"]} family {cpu.get("family")}',flush=True)
        # Y6: a production (dynamic ELF) worker's fingerprint must be complete before any pin is published or any block
        # runs: a failed or partial ldd probe would give nodes with different libraries the same runtime identity
        kind=elf_kind(rt['executable']);bad=fingerprint_problems(fp,kind,cpu)
        if bad:
            print(f'C8: index {idx}: the runtime fingerprint of the worker on this node ({fp.get("host")}) is incomplete: {"; ".join(bad)}. The campaign\'s '
                  'runtime identity (X8) needs a successful ldd probe and the content hashes of the ELF interpreter and of every library it loads; nothing '
                  'was pinned or run (exit 64). Check ldd and the library environment on this node, then resubmit.',file=sys.stderr,flush=True)
            _IO['refusal']='incomplete runtime fingerprint';raise SystemExit(VENDOR_REFUSED)
        if gb is not None:  # W8: before any pin is published or any block runs
            why=gmp_binding_problem(runtime_identity(fp),gb,bool(m['test_only']))
            if why:
                gates=[g.get('slurm_job')or str(g.get('sha256'))[:12]for g in (m['numerics_route'].get('gates')or[])if isinstance(g,dict)]
                print(f'C8: index {idx}: the campaign\'s {m["numerics"]} executable ({m["executable_sha256"][:12]}) is admitted by its J-FLAG gate(s) {gates}, '
                      f'which validated it with one libgmp; on this node ({fp.get("host")}) {why}. A changed libgmp needs a fresh gate of this build with this '
                      'library (tests/numerics_flags.py) and a new plan (W8). Nothing was pinned or run (exit 64).',file=sys.stderr,flush=True)
                _IO['refusal']='gate libgmp binding refused';raise SystemExit(VENDOR_REFUSED)
        # Y2: every native launch gets the controlled OpenMP environment (run_native); a real (ELF) worker's team is watched
        ctl=omp_child_env(threads,{});conflicts={k:v for k,v in omp_inherited().items()if ctl.get(k)!=v}
        if conflicts:print('omp: inherited OpenMP controls not passed to the native worker (Y2): '+' '.join(f'{k}={v}'for k,v in conflicts.items()),flush=True)
        _NATIVE['omp']={'threads':threads,'check':kind in('dynamic','static')}
        pin_cpu_vendor(directory,cpu,idx,fp)  # F5: refuses (exit 64) on another vendor than the campaign's first claim
        rkey=pin_runtime_identity(directory,fp,idx)['key']  # X8: refuses (exit 64) another run-time library stack
        (p/'checkpoints').mkdir(exist_ok=True);(p/'logs').mkdir(exist_ok=True);done=0
        first=[True]
        def snap_read(n):_own('task_file_snapshot',n,1 if first[0]else 0);first[0]=False
        for part,block in enumerate(snapshot_blocks(snap,j,T,on_read=snap_read)):
            name=block_name(j['shard'],part);dest=p/'checkpoints'/f'{name}.json'
            if dest.exists():validate_checkpoint(load(dest),block,cfg,m,mh,rt['rates'],rkey,gb);_own('checkpoints',dest.stat().st_size);continue
            if a.max_blocks is not None and done>=a.max_blocks:print(f'stopped after {done} blocks (--max-blocks)',flush=True);break
            with tempfile.TemporaryDirectory(prefix='block_',dir=runtime)as td:
                td=Path(td);graphroot,nread,nmembers=stage_graphs(td,I,cfg,block,inv);tasks=td/'tasks.txt'
                _own('staged_members',nread,nmembers)  # the bytes read from the pack: exactly the members' (F12)
                tasks.write_text(f'{TASK_MAGIC} {ORDER} {cfg["L"]} {len(block)}\n'+''.join(' '.join(map(str,r))+'\n'for r in block));out=td/'native.json'
                rate=cfg['rate']
                if rate=='file':
                    rf=td/f'rates.{name}.txt';table=rt['rates'][cfg['campaign']][cfg['sector']][str(cfg['L'])]
                    rf.write_text(''.join(f'{g} {table[str(g)]}\n'for g in sorted({r[2]for r in block})));rate='@'+str(rf)
                cmd=list(map(str,[rt['executable'],graphroot,rt['gamma'],rt['net'],tasks,out,cfg['seed'],cfg['layout'],rate,threads,cfg['sum_mode'],'-']))
                r0=proc_rchar()
                try:
                    try:
                        with (td/'native.log').open('w')as log:run_native(cmd,log)
                    finally:_native_io(r0)  # the child is reaped here, also when stopped
                except TeamRefused as exc:  # Y2: the worker did not show its team; stopped, nothing of the block kept (exit 64)
                    message=(td/'native.log').read_text();_own('native_logs',len(message.encode()))
                    publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message+f'\nC8 (Y2): {exc}\n')
                    print(f'C8: index {idx}, block {name}: {exc} (exit 64; lanes release the claim and stop).',file=sys.stderr,flush=True)
                    _IO['refusal']='omp team refused';raise SystemExit(VENDOR_REFUSED)from exc
                except subprocess.CalledProcessError as exc:
                    message=(td/'native.log').read_text();_own('native_logs',len(message.encode()))
                    publish(p/'logs'/f'{name}.failure.{time.time_ns()}.log',message);raise RuntimeError('Native work block failed: '+message[-4000:])from exc
                n=load(out);_own('native_outputs',out.stat().st_size);_own('block_task_files',tasks.stat().st_size)  # the native output; tasks.txt hashed below
                doc={'runtime':{'executable_sha256':rt['executable_sha256'],'inputs_manifest_sha256':rt['inputs_manifest_sha256'],'net_sha256':rt['net_sha256'],
                                'rates_identity':rt['rates_identity'],'fingerprint':fp,'fingerprint_bytes':counter['bytes'],'cpu':cpu,'omp_team':_NATIVE['team']},
                     'manifest_sha256':mh,'config_hash':object_hash(cfg),'index':idx,'block':part,'native':n,'payload_sha256':object_hash(n),
                     'executable_sha256':rt['executable_sha256'],'task_file_sha256':digest(tasks),'index_tasks_sha256':j['tasks_sha256']}
                validate_checkpoint(doc,block,cfg,m,mh,rt['rates'],rkey,gb)
                try:dump(dest,doc);state='committed'
                except FileExistsError:
                    # Another process published this block first (duplicate run): keep it if scientifically identical.
                    prior=validate_checkpoint(load(dest),block,cfg,m,mh,rt['rates'],rkey,gb);_own('checkpoints',dest.stat().st_size)
                    for x,y in zip(prior['rows'],n['rows']):
                        if any(x.get(k)!=y.get(k)for k in SCIENTIFIC):raise ValueError('Conflicting duplicate execution')
                    state='verified duplicate'
                tm=_NATIVE['team']or{};done+=1;print(f'{state} {j["group"]}/{name} (omp team {tm.get("verdict")}: {tm.get("observed")} of {tm.get("requested")} threads)',flush=True)
    finally:
        _NATIVE['launching']=False;stop_children()
        if runtime is not None:shutil.rmtree(runtime,ignore_errors=True)

# ---------------------------------------------------------------- merge
TAIL_K=16

def _row_fields(r:dict)->str:
    """One raw task row of a run file (tab-separated; never a partial sum): rep graph begin end total quad mp seconds
    tail_sum tail_argmax tail_top(space-separated) values(space-separated)."""
    return '\t'.join((str(r['rep']),str(r['graph']),str(r['begin']),str(r['end']),str(r['total']),str(r['quad']),str(r['mp']),repr(float(r['seconds'])),
                      r['tail_sum'],str(r['tail_argmax']),' '.join(r['tail_top']),' '.join(r['values'])))+'\n'

def _parse_run_line(line:str):
    f=line.rstrip('\n').split('\t');return (int(f[0]),int(f[1]),int(f[2])),f

def validate_merged(p:Path,cfg:dict,m:dict,mh:str,schema:str=MERGED_SCHEMA)->dict:
    """A published merged.json against its plan; schema: <prefix>-merged-1 for design.py's reader of another package's
    campaign (H6)."""
    d=load(p/'merged.json')
    if d.get('schema')!=schema or d.get('complete')is not True or d.get('manifest_sha256')!=mh or d.get('config_hash')!=object_hash(cfg)or d.get('sector')!=cfg['sector']or d.get('L')!=cfg['L']\
       or d.get('campaign')!=cfg['campaign']or d.get('rates_identity')!=m['rates_identity']or d.get('numerics')!=m['numerics']:
        raise ValueError('existing merged.json does not belong to this plan: '+str(p/'merged.json'))
    if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d.get('payload_sha256'):raise ValueError('merged payload checksum mismatch: '+str(p/'merged.json'))
    for f in ('graph_replicates','graph_tails','graph_costs'):checked(p/f'{f}.csv',d[f'{f}_sha256'])
    if len(d['batches'])!=cfg['replicates']or d.get('replicates')!=cfg['replicates']:raise ValueError('merged replicate count mismatch')
    return d

_MW={}  # per merge-worker process: the verified manifest, group configs and rate map (loaded once by _merge_init)

def _merge_init(directory:str,mh:str,rkey:str|None=None)->None:
    d=Path(directory);data=(d/'manifest.json').read_bytes()
    if hashlib.sha256(data).hexdigest()!=mh:raise ValueError('manifest.json changed during the merge')
    m=json.loads(data);_MW.clear();_MW.update(directory=d,m=m,mh=mh,cfg={},rates=rate_map_for(d,m),rkey=rkey,gb=gate_gmp_binding(m))  # W8: the gate's libgmp

def _mw_group(name:str):
    if name not in _MW['cfg']:_MW['cfg'][name]=group_of(_MW['directory'],_MW['m'],name)
    return _MW['cfg'][name]

RUN_DIGEST_MOD=1<<256
def _line_digest(line:bytes,key:bytes)->int:
    """A run line's term of the order-independent run digest (O01): the keyed BLAKE2b-256 of the line. The run digest is
    the sum mod 2^256 of its lines' terms. The key is drawn afresh by every merge (merge_key), so a run edited before
    the merge cannot be crafted to keep its digest (an unkeyed sum would allow a generalized-birthday search)."""
    return int.from_bytes(hashlib.blake2b(line,key=key,digest_size=32).digest(),'big')

def merge_key()->bytes:
    """The secret key of one merge's run digests, never stored."""
    return os.urandom(32)

def _phase1(jid:int,out:str,F:int=MERGE_FAN_IN,key:bytes=b'')->dict:
    """Phase 1 for one shard: its checkpoints validated block by block against its per-index task file (streamed and
    checked against the manifest pin), the raw rows of each block sorted by (rep, graph, begin) into a spill run, and the
    spill runs merged with fan-in F (several passes when the shard has more than F blocks) into the shard's run file,
    byte-identical to one sort of all its rows. Peak memory: one checkpoint block plus F rows, whatever the shard's row
    count (O02). Returns the statistics, and the run's rows, sha256 (its identity) and run_mset, the sum mod 2^256 of
    the keyed digests of its lines (_line_digest with this merge's key), which phase 2 checks reused intermediate runs
    against (O01)."""
    import array
    directory,m,mh=_MW['directory'],_MW['m'],_MW['mh'];j=m['jobs'][jid];p,cfg=_mw_group(j['group'])
    T=m['checkpoint_tasks'];out=Path(out);stats={'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0}
    # Nothing that outlives a block is allocated per block (the seconds go to flat C arrays, spill names are made after
    # the loop), so no small object pins the allocator's arenas between blocks and the peak RSS stays flat (O02).
    secs=array.array('d');tsecs=array.array('d');spill=lambda part:out.with_name(f'{out.name}.b{part:06d}')
    for part,block in enumerate(iter_job_blocks(directory,j,T)):
        f=p/'checkpoints'/f'{block_name(j["shard"],part)}.json'
        if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
        n=validate_checkpoint(load(f),block,cfg,m,mh,_MW['rates'],_MW.get('rkey'),_MW.get('gb'))
        secs.append(float(n['integration_seconds']));tsecs.append(float(n['integration_seconds'])*int(n['threads']));stats['blocks']+=1
        stats['max_rss_kb']=max(stats['max_rss_kb'],int(n.get('max_rss_kb')or 0))
        for r in n['rows']:stats['quad']+=r['quad'];stats['mp']+=r['mp']
        stats['rows']+=len(n['rows'])
        lines=sorted((((r['rep'],r['graph'],r['begin']),_row_fields(r))for r in n['rows']),key=lambda t:t[0]);del n,block
        _write_run(lines,spill(part));del lines
    stats['secs']=secs.tolist();stats['tsecs']=tsecs.tolist();spills=[spill(k)for k in range(stats['blocks'])];level=0
    while len(spills)>F:
        level+=1;nxt=[]
        for k in range(0,len(spills),F):
            o=out.with_name(f'{out.name}.m{level}.{k//F:06d}');_merge_spills(spills[k:k+F],o);nxt.append(o)
            for s in spills[k:k+F]:s.unlink()
        spills=nxt
    res=_merge_spills(spills,out,hashed=True,key=key)
    for s in spills:s.unlink()
    if res['rows']!=stats['rows']:raise ValueError(f'phase 1 of index {jid}: {res["rows"]} rows written, {stats["rows"]} validated')
    stats['run_sha256']=res['sha256'];stats['run_mset']=format(res['mset'],'064x');return stats

def exact_seconds(stats:dict)->dict:
    """The integration and thread seconds of a group as correctly rounded sums (math.fsum) of the per-block values: the
    same bytes whatever the order of the shards, of their completion, or of the blocks (serial and parallel merge)."""
    out={k:v for k,v in stats.items()if k not in('secs','tsecs')}
    out['seconds']=math.fsum(stats['secs']);out['thread_seconds']=math.fsum(stats['tsecs']);return out

def _complete_run(path:Path)->bool:
    try:
        with path.open('rb')as f:
            f.seek(0,2);n=f.tell()
            if n<5:return False
            f.seek(n-5);return f.read()==b'#end\n'
    except OSError:return False

def _read_run(path:Path):
    with path.open()as f:
        for line in f:
            if line=='#end\n':return
            yield _parse_run_line(line)
    raise ValueError(f'truncated run file {path}')

def _run_lines(path:Path):
    """(key, line) of every row of a run file in file order (the lines are copied verbatim by the merge passes)."""
    with Path(path).open()as f:
        for line in f:
            if line=='#end\n':return
            a,b,c,_=line.split('\t',3);yield (int(a),int(b),int(c)),line
    raise ValueError(f'truncated run file {path}')

def _write_run(items,out:Path,durable:bool=False,hashed:bool=False,key:bytes|None=None)->dict:
    """Write (key, line) items as a run file: a unique temporary file in out's directory, renamed into place after its
    '#end' line (flushed to disk first when durable), so a run with its '#end' line is complete (_complete_run) and two
    merges never write the same file. Returns its row count, with hashed the sha256 of its bytes, and with a digest key
    the order-independent digest of its lines (_line_digest)."""
    out=Path(out);fd,tname=tempfile.mkstemp(prefix=out.name+'.tmp.',dir=out.parent);h=hashlib.sha256()if hashed else None;n=0;acc=0
    digests=key is not None
    try:
        with os.fdopen(fd,'w')as f:
            for _,line in items:
                f.write(line);n+=1
                if hashed or digests:
                    b=line.encode()
                    if hashed:h.update(b)
                    if digests:acc+=_line_digest(b,key)
            f.write('#end\n');f.flush()
            if hashed:h.update(b'#end\n')
            if durable:os.fsync(f.fileno())
        os.replace(tname,out)
    except BaseException:
        try:os.unlink(tname)
        except OSError:pass
        raise
    return {'rows':n,'sha256':h.hexdigest()if hashed else None,'mset':acc%RUN_DIGEST_MOD if digests else None}

def _merge_spills(inputs:list,out:Path,hashed:bool=False,key:bytes|None=None)->dict:
    """Phase 1: merge a shard's spill runs (job-private scratch, not flushed to disk) in (rep, graph, begin) order."""
    return _write_run(heapq.merge(*(_run_lines(p)for p in inputs),key=lambda t:t[0]),out,hashed=hashed,key=key)

def _merge_runs(inputs:list,out:Path)->dict:
    """One output run of a phase-2 merge pass: the rows of `inputs` in (rep, graph, begin) order, written to a unique
    temporary file, flushed to disk and renamed into place (_write_run). Returns its row count."""
    return _write_run(heapq.merge(*(_run_lines(p)for p in inputs),key=lambda t:t[0]),out,durable=True)

def _verify_run(path:Path,rows:int,mset:int,key:bytes)->str|None:
    """None when the complete run at `path` is exactly the merge of its inputs: `rows` lines in (rep, graph, begin) order
    whose order-independent digest under this merge's key equals `mset`, the sum of its inputs' digests (phase 1's runs
    are made afresh from the validated checkpoints, so the expectation never comes from a stored file), and nothing
    after its '#end' line; else the reason (O01). Changing any byte of a row changes the digest; reordering rows breaks
    the order; the key is drawn after any edit, so no edit can be made to keep the digest."""
    n=0;acc=0;prev=None
    try:
        with Path(path).open('rb')as f:
            for line in f:
                if line==b'#end\n':
                    if f.read(1):return 'data after its #end line'
                    break
                try:a,b,c,_=line.split(b'\t',3);k=(int(a),int(b),int(c))
                except ValueError:return f'row {n} does not parse'
                if prev is not None and k<prev:return f'row {n} is out of (rep, graph, begin) order'
                prev=k;n+=1;acc+=_line_digest(line,key)
            else:return 'no #end line'
    except OSError as e:return f'unreadable ({e})'
    if n!=rows:return f'{n} rows, its inputs hold {rows}'
    if acc%RUN_DIGEST_MOD!=mset:return 'its rows differ from the merge of its inputs (content digest)'
    return None

RUN_KEY_SCHEMA='c8-d2-merge-run-1'
def run_key(inputs:list)->str:
    """The identity of a merge-pass output run: a hash of its inputs' identities (a phase-1 run's sha256, or the key of
    an earlier pass's output). A run's content is a function of its inputs' contents, so a complete run of the same
    key is the same run, and changed inputs never reuse an old one."""
    return hashlib.sha256('|'.join((RUN_KEY_SCHEMA,*inputs)).encode()).hexdigest()

def merge_work_dir(directory:Path,mh:str,work_dir=None)->Path:
    """The persistent per-campaign merge work directory: <campaign>/merge_work, or with --work-dir BASE the campaign's
    own subdirectory BASE/c8d2_merge_<first 16 hex digits of the manifest sha256>, so campaigns sharing a BASE never
    share (or clean) each other's runs."""
    return Path(work_dir).resolve()/f'c8d2_merge_{mh[:16]}'if work_dir else Path(directory)/'merge_work'

def clean_merge_work(persist:Path,name:str)->int:
    """Remove a group's intermediate runs (and leftover temporaries) from the work directory. Called only after the
    group's merged.json is published (or found published and valid)."""
    n=0
    for f in (persist.glob(f'{name}.p*')if persist.is_dir()else()):
        try:f.unlink();n+=1
        except FileNotFoundError:pass
    return n

def fan_in(requested:int)->int:
    import resource
    soft=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    F=min(requested,(soft-32)if soft!=resource.RLIM_INFINITY else requested)
    if F<2:raise ValueError(f'merge fan-in {F} < 2: RLIMIT_NOFILE soft limit {soft} leaves fewer than 2 run files open (raise it, ulimit -n)')
    return F

def _phase2(name:str,runs:list,keys:list,digests:list,work:str,persist:str,F:int,changes,stats:dict,dkey:bytes=b'')->dict:
    """Phase 2 for one group: external merge of its run files with fan-in F, then the final pass, which feeds the
    unchanged 50-digit Decimal summation in (rep, graph, begin) order. The intermediate runs live in the persistent
    work directory `persist`, named by run_key of their inputs. A complete one (_complete_run) is reused only after
    _verify_run shows that it holds exactly the merge of its inputs (their row counts and line digests, `digests`:
    (rows, run_mset) per phase-1 run under this merge's digest key dkey, propagated through the passes); one that fails
    is rebuilt and reported (O01). The merge is so resumable per output run. The runs are removed once this group's
    merged.json is published. The final pass writes its tables in the job-private `work` directory and publishes
    them."""
    work=Path(work);persist=Path(persist);m,mh=_MW['m'],_MW['mh'];p,cfg=_mw_group(name)
    level=0;runs=[Path(r)for r in runs];exp=[(int(r),int(d))for r,d in digests];passes=0;reused=0;written=0;rebuilt=0
    if len(exp)!=len(runs):raise ValueError(f'{name}: {len(runs)} runs but {len(exp)} run digests')
    try:
        while len(runs)>F:
            level+=1;nxt=[];nkeys=[];nexp=[];persist.mkdir(parents=True,exist_ok=True)
            for k in range(0,len(runs),F):
                key=run_key(keys[k:k+F]);out=persist/f'{name}.p{level}.r{k//F:06d}.{key[:32]}.run'
                want=(sum(r for r,_ in exp[k:k+F]),sum(d for _,d in exp[k:k+F])%RUN_DIGEST_MOD)
                complete=_complete_run(out);why=_verify_run(out,*want,dkey)if complete else None
                if complete and why is None:reused+=1
                else:
                    if complete:print(f'{name}: intermediate run {out} fails verification against its inputs ({why}); rebuilt',file=sys.stderr,flush=True)
                    got=_merge_runs(runs[k:k+F],out)['rows']
                    if got!=want[0]:raise ValueError(f'{out}: {got} rows written, its inputs hold {want[0]}')
                    if complete:rebuilt+=1
                    else:written+=1
                nxt.append(out);nkeys.append(key);nexp.append(want)
            runs,keys,exp=nxt,nkeys,nexp;passes+=1
        stream=heapq.merge(*(_read_run(r)for r in runs),key=lambda t:t[0])if runs else iter(())
        res=_final_pass(p,cfg,m,mh,stream,work,changes,stats)
    except FileNotFoundError:
        # A concurrent merge of this campaign published this group and removed its intermediate runs: its merged.json
        # is the one a rerun would keep ("already merged and valid").
        if not (p/'merged.json').exists():raise
        validate_merged(p,cfg,m,mh);res={'group':name,'merged':str(p/'merged.json'),'concurrent':True}
    clean_merge_work(persist,name);res.update(passes=passes+1,reused=reused,written=written,rebuilt=rebuilt);return res

def _final_pass(p:Path,cfg:dict,m:dict,mh:str,stream,work:Path,changes,stats)->dict:
    dim=2*(9-cfg['L']);expected=[(rep,int(g),n)for rep in range(cfg['replicates'])for g,n in sorted(((int(k),v)for k,v in cfg['counts'].items()))]
    r=next(stream,None);batches=[];count=0;costs={}
    rep_f=work/f'{cfg["name"]}.graph_replicates.csv';tail_f=work/f'{cfg["name"]}.graph_tails.csv';cost_f=work/f'{cfg["name"]}.graph_costs.csv'
    with decimal.localcontext()as ctx,rep_f.open('w')as fr,tail_f.open('w')as ft:
        ctx.prec=50
        fr.write('replicate,graph,'+','.join(f'jet_{i}'for i in range(dim))+'\n')
        ft.write('replicate,graph,points,tail_sum,tail_argmax,tail_n,'+','.join(f'top_{i+1}'for i in range(TAIL_K))+'\n')
        batch=[D(0)]*dim;prevrep=0
        for rep,gi,total in expected:
            if rep!=prevrep:batches.append([float(v)for v in batch]);batch=[D(0)]*dim;prevrep=rep
            graph=[D(0)]*dim;end=0;tsum=D(0);best=None;arg=None;top=[]
            while r is not None and (r[0][0],r[0][1])==(rep,gi):
                (_,_,lo),f=r;hi=int(f[3]);tt=int(f[4])
                if lo!=end or tt!=total or not 0<=lo<hi<=total:raise ValueError('incomplete, overlapping or inconsistent sample intervals')
                vals=f[11].split(' ');graph=[x+D(v)for x,v in zip(graph,vals)];end=hi;count+=1
                tsum+=D(f[8]);tops=f[10].split(' ')if f[10]else[]
                if tops and (best is None or D(tops[0])>best):best=D(tops[0]);arg=int(f[9])
                top=sorted(top+tops,key=lambda v:D(v),reverse=True)[:TAIL_K]
                c=costs.setdefault(gi,[0,D(0),0,0,0]);c[0]+=hi-lo;c[1]+=D(f[7]);c[2]+=1;c[3]+=int(f[5]);c[4]+=int(f[6])
                r=next(stream,None)
            if end!=total:raise ValueError(f'missing samples rep={rep},graph={gi}')
            fr.write(f'{rep},{gi},'+','.join(map(str,graph))+'\n');batch=[x+y for x,y in zip(batch,graph)]
            ft.write(f'{rep},{gi},{total},{tsum},{arg},{len(top)},'+','.join(top+['']*(TAIL_K-len(top)))+'\n')
        if r is not None:raise ValueError('unexpected streams')
        if expected:batches.append([float(v)for v in batch])
        else:batches=[[0.]*dim for _ in range(cfg['replicates'])]
    with cost_f.open('w')as fc:
        fc.write('graph,points,row_seconds,tasks,quad,mp\n')
        for gi in sorted(costs):x=costs[gi];fc.write(f'{gi},{x[0]},{x[1]},{x[2]},{x[3]},{x[4]}\n')
    if count!=cfg['tasks']:raise ValueError('wrong total task coverage')
    if len(batches)!=cfg['replicates']:raise ValueError('missing replicates')
    for src,dst,timing in ((rep_f,p/'graph_replicates.csv',False),(tail_f,p/'graph_tails.csv',False),(cost_f,p/'graph_costs.csv',True)):
        _publish_copy(src,dst,cfg['name'],timing)
    merged={'schema':MERGED_SCHEMA,'complete':True,'order':ORDER,'L':cfg['L'],'sector':cfg['sector'],'campaign':cfg['campaign'],'dimension':2,'config_hash':object_hash(cfg),
            'manifest_sha256':mh,'replicates':cfg['replicates'],'samples':cfg['samples'],'numerics':m['numerics'],'rates_identity':m['rates_identity'],'batches':batches,
            'fallbacks':{'quad':stats['quad'],'mp':stats['mp']},'integration_seconds_sum':stats['seconds'],'thread_seconds_sum':stats['thread_seconds'],
            'row_seconds_sum':float(sum((v[1]for v in costs.values()),D(0))),'blocks':stats['blocks'],'max_rss_kb':stats['max_rss_kb'],
            # the digests of the bytes this merge published (its scratch copies), not a re-read of the group's tables
            'graph_replicates_sha256':digest(rep_f),'graph_tails_sha256':digest(tail_f),'graph_costs_sha256':digest(cost_f)}
    if changes:merged['accepted_tool_changes']=changes
    merged['payload_sha256']=object_hash(merged);dest=p/'merged.json'
    try:dump(dest,merged)
    except FileExistsError:
        prior=validate_merged(p,cfg,m,mh)
        if canon(prior)!=canon(json.loads(json.dumps(merged,allow_nan=False))):raise ValueError('a different merged.json was published concurrently: '+str(dest))
        print(f'{cfg["name"]}: identical merged.json published concurrently; kept',flush=True)
    return {'group':cfg['name'],'merged':str(dest)}

def _publish_copy(src:Path,target:Path,group:str='',timing:bool=False)->str:
    """Stream-copy a scratch table into the group. merged.json is the commit point of a group (F8, A-ORC-12): its tables
    are committed once merged.json exists, and a committed table must be identical (no-clobber; 'Checksum mismatch'
    otherwise). A table without a merged.json is uncommitted, left by an earlier merge whose merged.json was removed
    (the recovery of a completed index deletes a checkpoint and the group's merged.json) or by a merge interrupted
    before its merged.json: a different one is replaced atomically and reported. graph_costs.csv (timing) changes
    whenever a block is recomputed; a changed scientific table (graph_replicates.csv, graph_tails.csv) is reported as
    such, and assemble then refuses a result whose science changed. Every reader of a group's tables goes through
    merged.json's digests, so an uncommitted table is never read. Returns 'published', 'identical' or 'replaced'."""
    want=digest(src)
    if target.exists()and digest(target)==want:return 'identical'
    fd,tname=tempfile.mkstemp(prefix=target.name+'.tmp.',dir=target.parent)
    try:
        os.fchmod(fd,umask_mode())
        with src.open('rb')as i,os.fdopen(fd,'wb')as o:shutil.copyfileobj(i,o);o.flush();os.fsync(o.fileno())
        try:os.link(tname,target);return 'published'
        except FileExistsError:pass
        old=digest(target)
        if old==want:return 'identical'
        if (target.parent/'merged.json').exists():raise ValueError(f'Checksum mismatch: {target} differs from the committed table (the group\'s merged.json exists)')
        os.replace(tname,target);tname=None
        what='timing only' if timing else 'SCIENTIFIC TABLE CHANGED: the uncommitted table differed from the one these checkpoints give; assemble refuses a result whose science changed'
        print(f'{group or target.parent.name}: replaced the uncommitted {target.name} (no merged.json; sha256 {old[:12]} -> {want[:12]}; {what})',flush=True)
        return 'replaced'
    finally:
        if tname is not None:os.unlink(tname)

def merge(a):
    """merge --jobs N [--fan-in F] [--work-dir BASE] [--scratch S]: phase 1 parallel over every shard of every group (one
    sorted run per shard, in a job-private directory under --scratch), phase 2 parallel over groups. Phase 2's
    intermediate runs live in the persistent per-campaign work directory (<campaign>/merge_work, or
    BASE/c8d2_merge_<manifest sha256 prefix> with --work-dir BASE) and a rerun reuses the complete ones; a group's runs
    are removed after its publication, and the directory once it is empty. --serial is the reference merge (C7(2)'s
    single SQLite pass), byte-identical by construction."""
    directory=a.directory.resolve();m,I,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=a.accept_tool_change,vendored=True)
    if changes:print('accepted tool changes (recorded in merged.json): '+', '.join(changes),file=sys.stderr)
    names=[a.group]if a.group else[g['name']for g in m['groups']]
    if any(n not in {g['name']for g in m['groups']}for n in names):raise ValueError('unknown group')
    if a.jobs<1:raise ValueError('--jobs must be positive')
    F=fan_in(a.fan_in);persist=merge_work_dir(directory,mh,a.work_dir)
    # X8: every checkpoint must carry the campaign's runtime compatibility identity (the first claim's pin)
    rkey,rsrc=campaign_runtime_key(directory,m)
    gb=gate_gmp_binding(m)  # W8: refuses a gated campaign whose gates record no libgmp before any work; each checkpoint is checked
    if gb is not None:print(f'merge: the gated executable is bound to libgmp {", ".join(sorted(x[:12] for x in gb))} (its J-FLAG gate; W8): every checkpoint must load it',file=sys.stderr)
    if rkey is not None and rsrc!=RUNTIME_PIN:print(f'merge: no {RUNTIME_PIN} (claims before the runtime pin): every checkpoint must carry the runtime identity of {rsrc}',file=sys.stderr)
    todo=[];published=[]
    for n in names:
        p,cfg=group_of(directory,m,n)
        if (p/'merged.json').exists():validate_merged(p,cfg,m,mh);print(f'{n}: already merged and valid; skipped',flush=True);published.append(n);continue
        check_tasks_db(p,cfg);todo.append(n)
    try:
        if todo and a.serial:
            for n in todo:merge_group_serial(directory,m,n,a.scratch,mh,changes,rkey);published.append(n)
        elif todo:published+=_merge_parallel(a,directory,m,mh,changes,todo,F,persist,rkey)
    finally:
        # intermediate runs of published groups only (an interrupted group keeps its runs for the rerun)
        for n in published:clean_merge_work(persist,n)
        if persist.is_dir():
            try:persist.rmdir()
            except OSError:pass

def _merge_parallel(a,directory:Path,m:dict,mh:str,changes,todo:list,F:int,persist:Path,rkey:str|None=None)->list:
    import concurrent.futures
    published=[]
    with tempfile.TemporaryDirectory(prefix='c8d2_merge_',dir=a.scratch)as work:
        runs={n:[]for n in todo};keys={};digs={};stats={n:{'secs':[],'tsecs':[],'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0}for n in todo};tasks=[]
        for j in m['jobs']:
            if j['group']in runs:out=str(Path(work)/f'{j["group"]}.s{j["shard"]:06d}.run');runs[j['group']].append(out);tasks.append((j['id'],out,j['group']))
        # spawned (not forked) workers: they inherit none of this process's descriptors, so the fan-in margin of
        # fan_in() holds inside them (a forked worker of a large pool starts with the pool's pipes open)
        import multiprocessing
        if a.jobs>1:Ex=lambda:concurrent.futures.ProcessPoolExecutor(a.jobs,mp_context=multiprocessing.get_context('spawn'),initializer=_merge_init,initargs=(str(directory),mh,rkey))
        else:_merge_init(str(directory),mh,rkey);Ex=lambda:_Serial(1)
        with Ex()as ex:
            t0=time.time();futs={};fout={};dkey=merge_key()  # this merge's run-digest key (O01), never stored
            for jid,out,g in tasks:f=ex.submit(_phase1,jid,out,F,dkey);futs[f]=g;fout[f]=out
            errors=[]
            for f in (concurrent.futures.as_completed(futs)if a.jobs>1 else list(futs)):
                try:
                    s=f.result();g=futs[f];keys[fout[f]]=s['run_sha256'];digs[fout[f]]=(s['rows'],int(s['run_mset'],16))
                    for k in ('secs','tsecs','quad','mp','rows','blocks'):stats[g][k]+=s[k]
                    stats[g]['max_rss_kb']=max(stats[g]['max_rss_kb'],s['max_rss_kb'])
                except Exception as e:errors.append(f'{futs[f]}: {e}')
            if errors:raise RuntimeError('merge phase 1 failed: '+'; '.join(sorted(errors)[:5]))
            t1=time.time();rows=sum(stats[n]['rows']for n in todo)
            print(f'merge phase 1: {rows} rows of {len(tasks)} shards in {t1-t0:.2f} s with {a.jobs} process(es) ({rows/max(t1-t0,1e-9):.0f} rows/s)',flush=True)
            order=sorted(todo,key=lambda n:-len(runs[n]));run_keys={n:[keys[o]for o in runs[n]]for n in todo};run_digs={n:[digs[o]for o in runs[n]]for n in todo}
            futs={ex.submit(_phase2,n,runs[n],run_keys[n],run_digs[n],work,str(persist),F,changes,exact_seconds(stats[n]),dkey):n for n in order};errors=[]
            for f in (concurrent.futures.as_completed(futs)if a.jobs>1 else list(futs)):
                try:
                    r=f.result();published.append(futs[f])
                    extra=(f', {r["reused"]} intermediate run(s) reused from {persist}'if r['reused']else'')+\
                          (f', {r["rebuilt"]} rebuilt after failing verification'if r.get('rebuilt')else'')+(' (published concurrently; kept)'if r.get('concurrent')else'')
                    print(f'{r["group"]}: merged ({r["passes"]} pass(es), fan-in {F}{extra}) -> {r["merged"]}',flush=True)
                except Exception as e:errors.append(f'{futs[f]}: {e}')
            if errors:
                if any(persist.glob('*.run')):print(f'merge: completed intermediate runs are kept in {persist}; a rerun resumes from them',file=sys.stderr,flush=True)
                raise RuntimeError('merge failed for '+'; '.join(sorted(errors)))
            t2=time.time();print(f'merge phase 2: {rows} rows of {len(todo)} group(s) in {t2-t1:.2f} s ({rows/max(t2-t1,1e-9):.0f} rows/s)',flush=True)
    return published

class _Serial:
    """A same-process stand-in for ProcessPoolExecutor (merge --jobs 1)."""
    def __init__(self,n):pass
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def submit(self,fn,*args):
        import concurrent.futures
        f=concurrent.futures.Future()
        try:f.set_result(fn(*args))
        except Exception as e:f.set_exception(e)
        return f

def merge_group_serial(directory:Path,m:dict,name:str,scratch=None,mh=None,changes=None,rkey=None):
    """The reference merge (C7(2)'s algorithm): every block of every shard validated in shard order against tasks.sqlite
    (and, with rkey, against the campaign's runtime identity, X8), the raw rows in one SQLite table, read back in
    (rep, graph, begin) order into the same final pass. W23's class (Stage-6 fix round 4): the task rows come from a
    private copy of tasks.sqlite verified against its pin while it is copied (merge's check_tasks_db verified the
    shared file, which the merge used to open again)."""
    p,cfg=group_of(directory,m,name);mh=mh or digest(Path(directory)/'manifest.json');rates=rate_map_for(directory,m);gb=gate_gmp_binding(m)  # W8
    T=m['checkpoint_tasks'];stats={'secs':[],'tsecs':[],'quad':0,'mp':0,'rows':0,'max_rss_kb':0,'blocks':0}
    with tempfile.TemporaryDirectory(prefix='c8d2_smerge_',dir=scratch)as td:
        tcopy=Path(td)/'tasks.sqlite';h=hashlib.sha256()
        with (p/'tasks.sqlite').open('rb')as i,tcopy.open('xb')as o:
            while b:=i.read(1<<20):h.update(b);o.write(b)
        if h.hexdigest()!=cfg['tasks_sha256']:raise ValueError(f'Checksum mismatch: {p/"tasks.sqlite"}')
        source=dbopen(tcopy,True)
        db=dbopen(Path(td)/'merge.sqlite');db.execute('CREATE TABLE actual(rep INTEGER,gi INTEGER,lo INTEGER,line TEXT)')
        for shard in range(cfg['shards']):
            cur=source.execute('SELECT uid,rep,gi,lo,hi,total FROM tasks WHERE shard=? ORDER BY pos',(shard,));part=0
            while block:=list(itertools.islice(cur,T)):
                f=p/'checkpoints'/f'{block_name(shard,part)}.json';part+=1
                if not f.exists():raise FileNotFoundError('Incomplete campaign: '+str(f))
                n=validate_checkpoint(load(f),block,cfg,m,mh,rates,rkey,gb)
                stats['secs'].append(float(n['integration_seconds']));stats['tsecs'].append(float(n['integration_seconds'])*int(n['threads']));stats['blocks']+=1
                stats['max_rss_kb']=max(stats['max_rss_kb'],int(n.get('max_rss_kb')or 0))
                for r in n['rows']:db.execute('INSERT INTO actual VALUES(?,?,?,?)',(r['rep'],r['graph'],r['begin'],_row_fields(r)));stats['quad']+=r['quad'];stats['mp']+=r['mp']
        db.commit();db.execute('CREATE INDEX s ON actual(rep,gi,lo)')
        stream=(_parse_run_line(line)for (line,)in db.execute('SELECT line FROM actual ORDER BY rep,gi,lo'))
        res=_final_pass(p,cfg,m,mh,stream,Path(td),changes,exact_seconds(stats));db.close();source.close()
    print(f'{name}: merged (serial reference) -> {res["merged"]}',flush=True);return res

# ---------------------------------------------------------------- status and recovery
def campaign_tag(directory:Path)->str:
    """Slurm --comment tag of one campaign's jobs: c8:<sha256(resolved campaign path + manifest sha256)[:12]>."""
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
        with path.open('rb')as f:head=f.read(65536).decode('utf-8','replace')
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

def job_progress(directory:Path,m:dict)->dict:
    """{job id: (committed blocks, total blocks)} from the checkpoint files (existence only; merge validates). Block
    counts come from the manifest's job entries (R07): tasks.sqlite is not opened."""
    out={}
    for j in m['jobs']:
        d=Path(directory)/'groups'/j['group']/'checkpoints'
        out[j['id']]=(sum((d/f'{block_name(j["shard"],k)}.json').exists()for k in range(j['blocks'])),j['blocks'])
    return out

def status_report(directory:Path,exclude=(),max_array:int=MAX_ARRAY,listing=False,fingerprints=True,verify_db=True):
    directory=Path(directory).resolve();m,I,mh,changes=verify_base(directory,check_executable=False,accept_tool_change=True);missing=[];groups={}
    lines=[f'WARNING: pinned tools changed since planning ({", ".join(sorted(changes))}): run and every Slurm submission refuse; restore them, '
           f'or merge/assemble by hand with --accept-tool-change']if changes else[]
    # A-FLAG-2: the numerics profile and the rates identity of the campaign, with the user approval of a numerics change.
    appr=m.get('approved_numerics_change')
    lines.append(f'numerics {m["numerics"]}, rates identity {m["rates_identity"]}'+(f' (approved numerics change: {appr})'if appr else'')+
                 (''if m['numerics']=='exact'and m['rates_identity']=='default'else' -- OPT-IN NUMERICS CHANGE (D1)'))
    prog=job_progress(directory,m);teams_all={}
    for g in m['groups']:
        p,config=group_of(directory,m,g['name'])
        if verify_db:check_tasks_db(p,config)
        done_g=total_g=0;fps={};teams={}
        for j in (j for j in m['jobs']if j['group']==g['name']):
            have,nb=prog[j['id']]
            if fingerprints:
                for k in range(nb):
                    f=p/'checkpoints'/f'{block_name(j["shard"],k)}.json'
                    if f.exists():
                        rt_=checkpoint_runtime(f)or{};fp=rt_.get('fingerprint');key=fingerprint_key(fp)or'none'
                        v=(rt_.get('omp_team')or{}).get('verdict')or'not recorded';teams[v]=teams.get(v,0)+1;teams_all[v]=teams_all.get(v,0)+1  # Y2, post hoc
                        e=fps.setdefault(key,{'checkpoints':0,'hosts':set(),'cpu_model':(fp or{}).get('cpu_model'),'glibc':(fp or{}).get('glibc')});e['checkpoints']+=1;e['hosts'].add((fp or{}).get('host'))
            done_g+=have;total_g+=nb
            if have<nb:missing.append(j['id'])
            if have<nb or listing:lines.append(f'job {j["id"]:6d} {g["name"]} shard {j["shard"]:4d}: {have}/{nb} blocks')
        fpl={k:{**v,'hosts':sorted(h for h in v['hosts']if h)}for k,v in fps.items()}
        groups[g['name']]={'committed':done_g,'total':total_g,'merged':(p/'merged.json').exists(),'fingerprints':fpl,'omp_teams':teams}
        lines.append(f'group {g["name"]}: {done_g}/{total_g} blocks, {"merged"if groups[g["name"]]["merged"]else"not merged"}'+
                     (f', {len(fpl)} fingerprint(s): '+'; '.join(f'{k} x{v["checkpoints"]} ({v["cpu_model"]}, {v["glibc"]}, hosts {",".join(v["hosts"][:4])}{"..."if len(v["hosts"])>4 else""})'for k,v in sorted(fpl.items()))if fpl else''))
    if teams_all:lines.append('omp teams of the committed blocks (Y2; the worker\'s team as watched while it ran): '+', '.join(f'{k} {v}'for k,v in sorted(teams_all.items()))+
                              ('; "smaller" never commits, "unverified" ran too briefly to see its team, "unavailable" is a test stand-in or a node without /proc'))
    import lanes
    active=sorted(set(exclude)&set(missing));todo=[i for i in missing if i not in active];claims=lanes.claims_summary(directory)
    est=m['estimates'].get('suggested_time_seconds')
    result='C8_test_result.json'if m['test_only']else'C8_result.json'
    pin=load(directory/CPU_PIN)if (directory/CPU_PIN).exists()else None
    lines.append(f'cpu vendor: {pin["vendor"]} ({pin.get("model_name")}), pinned by the first claim (index {pin["first_claim"]["index"]} on {pin["first_claim"]["host"]}); '
                 'claims on another vendor are refused (F5)'if pin else'cpu vendor: not pinned yet (the first claim pins it; F5)')
    rpin=read_runtime_pin(directory)
    lines.append(f'runtime identity: {rpin["key"][:12]} (glibc {rpin["identity"].get("glibc")}, {len(rpin["identity"].get("libraries")or{})} libraries), pinned by the first claim '
                 f'(index {rpin["first_claim"]["index"]} on {rpin["first_claim"]["host"]}); claims and checkpoints of another library stack are refused (X8)'
                 if rpin else'runtime identity: not pinned yet (the first claim pins it; X8)')
    return {'complete':not missing,'missing_jobs':missing,'active_not_resubmitted':active,'groups':groups,'result_present':(directory/result).exists(),'result_file':result,
            'cpu_vendor':pin,'runtime_identity':rpin,'omp_teams':teams_all if fingerprints else None,
            'numerics':m['numerics'],'rates_identity':m['rates_identity'],'approved_numerics_change':appr,
            'tool_changes':changes,'threads':m['threads'],'suggested_time':hms(est)if est else None,'resubmit':windows(todo,max_array),'campaign_tag':campaign_tag(directory),
            'lanes':claims,'lines':lines}

def parse_ids(text):return [int(x)for x in filter(None,(text or'').split(','))]

def status(a):
    """Committed/total checkpoint blocks per job index; exit 0 only when every block is committed. Done markers of lane
    mode are never read here: completeness is the checkpoint blocks (R03)."""
    size=a.max_array if getattr(a,'max_array',None)is not None else None
    if size is None:
        env=os.environ.get('C8_MAX_ARRAY','')
        if env and not env.isdigit():raise ValueError('C8_MAX_ARRAY must be a positive integer')
        size=int(env)if env else MAX_ARRAY
    if size<1:raise ValueError('--max-array must be a positive integer')
    r=status_report(a.directory,parse_ids(getattr(a,'exclude',None)),size,getattr(a,'all',False),fingerprints=not getattr(a,'fast',False));lines=r.pop('lines')
    if getattr(a,'json',False):print(json.dumps(r))
    else:
        print('\n'.join(lines));print('result: '+(f'{r["result_file"]} present'if r['result_present']else f'no {r["result_file"]}'))
        cl=r['lanes']
        if cl['claims']or cl['failures']:print(f'lanes: {cl["claims"]} claimed indices {ranges(cl["claimed"])} by jobs {",".join(cl["owners"])}; {cl["failures"]} failure records'+
                                                 (f' (indices {ranges(cl["failed"])})'if cl['failed']else'')+'. Claims of finished jobs are released by slurm/submit.sh --lanes or tools/lanes.py release-stale')
        if r['missing_jobs']:
            print(f'{len(r["missing_jobs"])} incomplete job indices: {ranges(r["missing_jobs"])}')
            if r['active_not_resubmitted']:print(f'still queued or running (not resubmitted): {ranges(r["active_not_resubmitted"])}')
            for w in r['resubmit']:
                print(f'resubmit: C8_MAX_ARRAY={size} C8_RUN={shlex.quote(str(Path(a.directory).resolve()))} C8_PACKAGE={shlex.quote(str(ROOT))} '
                      f'{shlex.quote(str(ROOT/"slurm/submit.sh"))} --window {w["offset"]}:{w["array"]}')
            print('then submit slurm/merge.sh once complete; or run slurm/resubmit.sh (arrays) or slurm/submit.sh --lanes N (lane mode), which also submit a merge that waits for the work')
        else:print('complete: every checkpoint block is committed')
    if r['missing_jobs']:sys.exit(1)

# Slurm job states (squeue %T). LIVE may still run or be released; TERMINAL finished for good; anything else (COMPLETING,
# STAGE_OUT, PREEMPTED, unknown) is UNCERTAIN and every submission refuses until Slurm settles it.
LIVE_STATES=frozenset('PENDING RUNNING SUSPENDED CONFIGURING REQUEUED REQUEUE_HOLD REQUEUE_FED SPECIAL_EXIT RESIZING SIGNALING STOPPED RESV_DEL_HOLD POWER_UP_NODE'.split())
TERMINAL_STATES=frozenset('COMPLETED CANCELLED FAILED TIMEOUT NODE_FAIL BOOT_FAIL DEADLINE OUT_OF_MEMORY REVOKED'.split())

def parse_queue(directory:Path,queue_text:str):
    """Tagged records of one campaign from 'squeue --all --states=all -h -r -o %200k|%K|%T|%i' output."""
    tag=campaign_tag(directory);tagged=[]
    for line in queue_text.splitlines():
        parts=[x.strip()for x in line.split('|')]
        if len(parts)!=4 or not parts[0].startswith(tag+':'):continue
        comment,task,state,jobid=parts;tagged.append({'comment':comment,'role':comment[len(tag)+1:],'task':task,'state':state,'jobid':jobid})
    return tag,tagged

def queue_state(directory:Path,queue_text:str)->dict:
    """This campaign's jobs in a squeue snapshot: refuse={code,message} for uncertain states or unexpected records, else
    the live work indices, live lane workers and live merges."""
    directory=Path(directory).resolve();tag,tagged=parse_queue(directory,queue_text)
    def refuse(code,msg):return {'refuse':{'code':code,'message':msg},'tag':tag}
    uncertain=[j for j in tagged if j['state']not in LIVE_STATES|TERMINAL_STATES]
    if uncertain:return refuse(69,'tagged job(s) '+','.join(f'{j["jobid"]}={j["state"]}'for j in uncertain)+' are completing, preempted or in an unrecognised state; '
                                   'nothing submitted. Rerun once Slurm has settled them (requeued, finished or gone).')
    live=[j for j in tagged if j['state']in LIVE_STATES];merges=[j for j in live if j['role']=='merge'];lanesj=[j for j in live if j['role']=='lane'];work=[]
    for j in live:
        if j['role']in('merge','lane'):continue
        if not j['role'].startswith('off=')or not j['role'][4:].isdigit()or not j['task'].isdigit():
            return refuse(69,f'unexpected record for tagged job {j["jobid"]} ({j["comment"]}, task {j["task"]}); was squeue run with -r? nothing submitted')
        work.append({'index':int(j['role'][4:])+int(j['task']),'jobid':j['jobid']})
    return {'refuse':None,'tag':tag,'live_merges':[j['jobid']for j in merges],'merge_states':{j['jobid']:j['state']for j in merges},
            'live_lanes':sorted({j['jobid']for j in lanesj}),'live_work':work,'live_indices':sorted({w['index']for w in work})}

def recovery_plan(directory:Path,queue_text:str,max_array:int=MAX_ARRAY)->dict:
    """Pure array-mode recovery decision: refuse={code,message}, or the arrays to resubmit and the live tasks the merge must wait for."""
    q=queue_state(directory,queue_text)
    if q['refuse']:return q
    if q['live_merges']:return {'refuse':{'code':65,'message':f'merge job(s) {",".join(q["live_merges"])} of this campaign are still queued or running; scancel them (or let them finish), then rerun'},'tag':q['tag']}
    if q['live_lanes']:return {'refuse':{'code':65,'message':f'lane worker job(s) {",".join(q["live_lanes"])} of this campaign are live: lane mode and array mode are not mixed. '
                                                          'Add lane workers with slurm/submit.sh --lanes N, or wait for them to finish'},'tag':q['tag']}
    r=status_report(directory,q['live_indices'],max_array,fingerprints=False,verify_db=False);r.pop('lines')
    return {'refuse':None,'tag':q['tag'],'threads':r['threads'],'suggested_time':r['suggested_time'],'complete':r['complete'],'missing_jobs':r['missing_jobs'],
            'live_indices':q['live_indices'],'live_missing_not_resubmitted':r['active_not_resubmitted'],'arrays':r['resubmit'],
            'merge_waits_on_live_tasks':sorted({w['jobid']for w in q['live_work']})}

# sbatch options that C8_SBATCH_ARGS and extra script arguments may carry (exact spellings only). Everything else, in
# particular array, dependency, export, export-file, comment, output, clusters, nodes, exclusive and positional words,
# is refused, because the scripts set or rely on those themselves. Every allowed value option takes a REQUIRED argument.
SBATCH_LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user begin signal job-name exclude nodelist licenses wckey'.split())
SBATCH_LONG_FLAG=frozenset('requeue no-requeue hold'.split())
SBATCH_SHORT_VALUE=frozenset('ApqCtcJxwL')

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

def sbatch_options(tokens)->list[tuple[str,str|None]]:
    """(name, value) pairs, in order, of a token list that check_sbatch_args() accepts: long names without '--', short
    letters; option VALUES are never read as options (C7I-17)."""
    why=check_sbatch_args(tokens)
    if why:raise ValueError(why)
    out=[];i=0
    while i<len(tokens):
        tok=tokens[i]
        if tok.startswith('--'):
            name,eq,val=tok[2:].partition('=')
            if name in SBATCH_LONG_FLAG and not eq:out.append((name,None));i+=1
            elif eq:out.append((name,val));i+=1
            else:out.append((name,tokens[i+1]));i+=2
        else:
            if len(tok)>2:out.append((tok[1],tok[2:]));i+=1
            else:out.append((tok[1],tokens[i+1]));i+=2
    return out

def option_value(tokens,long:str,short:str|None=None)->str|None:
    """The last value of an option (long name or short letter) in an allowlisted token list, else None."""
    v=None
    for n,x in sbatch_options(tokens):
        if n==long or (short and n==short):v=x
    return v

def time_option(tokens)->str|None:return option_value(tokens,'time','t')

def check_args(a):
    why=check_sbatch_args(a.args[1:]if a.args[:1]==['--']else a.args)
    if why:sys.exit(f'C8: {why}. Allowed: --'+' --'.join(sorted(SBATCH_LONG_VALUE|SBATCH_LONG_FLAG))+' and -'+' -'.join(sorted(SBATCH_SHORT_VALUE)))

def recover(a):
    size=a.max_array if a.max_array is not None else MAX_ARRAY
    print(json.dumps(recovery_plan(a.directory,Path(a.queue).read_text(),size)))

def tag(a):print(campaign_tag(a.directory))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('directory',type=Path);q.add_argument('--seed',type=int,required=True,help='a fresh random integer in [0, 2^63); never reuse one')
    q.add_argument('--pilot',action='store_const',const=True,help='allocation source: a uniform per-graph count per replicate (--points, default 4096)')
    q.add_argument('--points',type=int,help='--pilot points per graph per replicate (power of two; >= 4096 unless test-only)')
    q.add_argument('--design',type=Path,help='allocation source: a frozen bundle of tools/design.py freeze')
    q.add_argument('--replicates',type=int,help='--pilot replicates (default 8)')
    q.add_argument('--test-graphs',help='N|all: INCOMPLETE test-only plan restricted to N graphs per group')
    q.add_argument('--test-selection',choices=['cheapest','stratified'],default='cheapest')
    q.add_argument('--forbid-seeds-from',type=Path,action='append',help='seed log ($C8_SEEDS) or list; required for non-test plans, which register their '
                   'base seed in the first one (a tools/seeds.py log) under its lock before the campaign is published (Z15)')
    q.add_argument('--backend',choices=['decimal','gmp'],default='gmp');q.add_argument('--cost-model',type=Path,help='measured seconds per point (campaign:sector:L:graph)')
    q.add_argument('--threads',type=int,default=8,help='planned lane width');q.add_argument('--checkpoint-tasks',type=int,help='default max(16 x threads, 256)')
    q.add_argument('--task-seconds',type=float,help=f'target task length (default {TASK_SECONDS:g})');q.add_argument('--max-task-seconds',type=float,default=MAX_TASK_SECONDS)
    q.add_argument('--min-chunk',type=int,help=f'smallest task in points (default {MIN_CHUNK})')
    q.add_argument('--bootstrap-chunk',type=int,help='test-only first sweep (R13): fixed tasks of min(P, n_g) points, needs --shards')
    q.add_argument('--index-hours',type=float,help=f'index sizing (default {INDEX_HOURS:g} h of the lane width)');q.add_argument('--shards',type=int,help='shards per group (instead of --index-hours)')
    q.add_argument('--max-tasks',type=int,default=MAX_TASKS,help='per campaign');q.add_argument('--max-checkpoints',type=int,default=MAX_CHECKPOINTS)
    q.add_argument('--numerics',default='exact',help='numerics profile (opt-in profiles need --approved-numerics-change)');q.add_argument('--rates',type=Path,help='frozen rate map (R7 only)')
    q.add_argument('--approved-numerics-change',help='the user approval reference of a numerics change (A-FLAG-2)')
    q.add_argument('--numerics-gate',type=Path,action='append',help='a passed full-scale J-FLAG gate record of this profile build (repeatable); required by a '
                   'non-test plan under a profile that is not route (b) (route-(b) bundles carry their own)');q.set_defaults(func=plan)
    q=s.add_parser('run');q.add_argument('directory',type=Path);q.add_argument('--index',type=int);q.add_argument('--threads',type=int);q.add_argument('--scratch')
    q.add_argument('--max-blocks',type=int,help='commit at most this many new blocks, then stop (time slicing, tests)');q.set_defaults(func=run)
    q=s.add_parser('merge');q.add_argument('directory',type=Path);q.add_argument('--group');q.add_argument('--jobs',type=int,default=1)
    q.add_argument('--scratch',help='job-private temporary files: phase-1 runs, the final-pass tables, the serial reference database (default: the system temporary directory)')
    q.add_argument('--work-dir',type=Path,help='base of the persistent per-campaign directory of the intermediate merge runs (BASE/c8d2_merge_<manifest sha256 prefix>), from which an interrupted merge resumes (default: <campaign>/merge_work)')
    q.add_argument('--fan-in',type=int,default=MERGE_FAN_IN,help='runs merged at once (bounded by RLIMIT_NOFILE - 32)');q.add_argument('--serial',action='store_true',help='the reference merge (tests)')
    q.add_argument('--accept-tool-change',action='store_true',help='merge although a pinned tool changed; old and new hashes are recorded in merged.json');q.set_defaults(func=merge)
    q=s.add_parser('status');q.add_argument('directory',type=Path);q.add_argument('--all',action='store_true',help='also list complete jobs');q.add_argument('--json',action='store_true',help='machine-readable report')
    q.add_argument('--fast',action='store_true',help='skip the per-checkpoint fingerprint summary')
    q.add_argument('--exclude',help='comma-separated job indices still queued or running; left out of the resubmission lines');q.add_argument('--max-array',type=int,default=None,help='largest array per resubmission line (default: $C8_MAX_ARRAY, else 1000)');q.set_defaults(func=status)
    q=s.add_parser('recover',help='array-mode recovery decision from a squeue snapshot (used by slurm/resubmit.sh)');q.add_argument('directory',type=Path)
    q.add_argument('--queue',required=True,help="file with 'squeue --all --states=all -u \"$(id -un)\" -h -r -o %%200k|%%K|%%T|%%i' output");q.add_argument('--max-array',type=int,default=MAX_ARRAY);q.set_defaults(func=recover)
    q=s.add_parser('tag',help="print the campaign's Slurm comment tag");q.add_argument('directory',type=Path);q.set_defaults(func=tag)
    q=s.add_parser('check-sbatch-args',help='allowlist check of user sbatch options');q.add_argument('args',nargs=argparse.REMAINDER);q.set_defaults(func=check_args)
    a=p.parse_args(argv);a.func(a)
if __name__=='__main__':main()
