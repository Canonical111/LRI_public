#!/usr/bin/env python3
"""Native acceptance and replay gates of the C8(2) worker (PLAN component C), on the real executables.

Default run (J-VAL-1 subset; `--full` for J-VAL-2):
  describe      A-KER-3: --describe of bin/c8d2_{decimal,gmp}: schema c8-d2-build-1, orders [7,8], lmax 8, kmax 6,
                numerics exact, diagnostic false, the 16 tail fields.
  bad_inputs    A-KER-1/2 (and the native part of A-FLAG-6): each refusal exits 2 with its message (task L=9, L=1,
                order-7 L=8, orders 6 and 9, gamma of the other order, a trailing gamma token, data after the last
                gamma row, a dim-32 net, a graph with E>16, bad scalar rates, @FILE rate maps with a missing, extra or
                duplicate graph, a trailing token or a value outside (0, 1]; Z4, Stage-6 fix round 3: a G-file whose
                body ends early or holds an unreadable token in every section of the loader, graph_truncations: the
                mask list, a denominator size, a monomial-id list, a coefficient row, the rate-table size and the
                table, refused by the worker and, when built, by bin/c8d2_inspect with "truncated graph");
                L=2 runs at both orders (K=5 and K=6),
                order 7 and order 8 run with their gamma files, and the native JSON reports order, numerics and
                max_rss_kb with row width 2(order+1-L); a valid @FILE map echoes each row's rate and equals the
                scalar run when every rate equals the scalar.
  replay        G-REF (A-RPL-1): the research worker reference/LRI_C7_d2_progress/code/c7d2_integrate.cpp (built
                here with the Makefile's flags) against bin/c8d2_* at order 7: decimal exact; gmp exact when mp = 0,
                <= 1e-30 normalized when mp > 0, counters identical.
                G-C7 (A-RPL-2): bin/ref/c7d2_* (make c7ref) against bin/c8d2_* at order 7, identical task rows,
                net, gamma_d2_7.txt, seed 7738251: exact in every row (values, quad, mp, max_abs), mp > 0 included.
                G-JET (A-RPL-3): order 8 against order 7 on the same tasks: b and c slots 0..7-L exact (c offset
                8-L -> 9-L), quad, mp, max_abs and the tail fields identical, the new slot finite.
                L=2 graph and every L3-L7 kernel with --full (3,773, the 262 new L7 kernels staged from the packs),
                the first 8 and 8 heaviest per (sector, L) otherwise; 2 replicates x 64 points, rate .8, layout 0,
                plus rates .8/.9 x layouts 0/1/2 at L7.
  invariance    A-RPL-6 (chunks and layouts): the 3 heaviest L7 and L8 kernels per sector, layouts 0/1/2, both
                backends: 23-point chunks agree with whole tasks to <= 1e-12 normalized, chunked runs at 1 and 4
                threads are identical, and the chunk rows' tail fields merge to the whole task's (top 16 and argmax
                identical, tail_sum <= 1e-15 relative), and (chunk_merge, Stage-6 fix round 4) the chunks tile the task,
                their quad and mp add up to the whole's and the largest chunk max_abs is the whole's. R1: each run in
                common.omp_child_env and its OpenMP team observed (team_run; a team other than the request, or none
                observable, fails).
  inspector     A-KER-5: on 100 kernels (25 per sector at L7 and L8) bin/c8d2_inspect's addends equal
                inputs/inventory.json's and the worker's own (src/c8d2_integrate.cpp built with -DC8_ORDER_TRACE, a
                diagnostic build whose task loop records what it runs), and the worker's executed order on a block of
                50 tasks equals the order predicted from the inventory; the trace build's rows equal bin/c8d2_decimal's
                (T-04). CK-K03: the inspector's temporary files live in a private mkdtemp directory (0700, files 0600)
                that a normal run, an error exit, SIGTERM and SIGUSR1 all remove; an ignored SIGHUP stays ignored.
  class_b       PLAN addition (ii): a build without the tail fields (-DC8_NO_TAIL_FIELDS) writes every other field
                exactly as bin/c8d2_* does (L7 and L8, both backends). Y1 (Stage-6 fix round 2): each build is bound to
                the worker it is compared with (tools/build_record.py bound_tool_command: its make flags and compiler,
                and for gmp its GMP_PREFIX words, gmp.h and resolved libgmp sha256), else refused.
  diagnostics   bin/c8d2_gmp_prof and bin/c8d2_gmp_ratiohist, when built (make profile ratiohist), write rows
                identical to bin/c8d2_gmp, say "diagnostic":true and count every evaluation once.
Optional:
  --bk8         G-BK8 (A-RPL-4): L7 and L8, 400 kernels per sector (100 heaviest, 300 random), 2 x 256 points:
                decimal against gmp, identical counters, exact rows when mp = 0, <= 1e-30 normalized when mp > 0.
                W2 (Stage-6 fix round 4, S6A4-02): every row field is compared (compare, tails=True; a field no rule
                covers fails): when mp > 0 also max_abs, every tail_top entry and tail_sum within 1e-30 normalized, the
                tail widths equal (min(16, points)), tail_argmax equal or a near tie (TIE_POLICY: in both rows the two
                largest |t| agree within the tolerance; counted as tail_argmax_ties); when mp = 0 the tail fields
                exact; every argmax inside its row. The records carry row_rule c8-d2-bk8-row-rule-2.
  --l2-control  A-IN-6(b): the L=2 graph at order 8 (K=6), rates .8 and .9, 32 replicates x 2^16 points, fresh
                seed: |b_j - B2[j]| <= 4 SE per campaign and combined; wa/wb = 6 exactly; |b_j - 6c_j| <=
                2^-60 |b_j| per row and per replicate sum (R08).
  --l8self DIR  G-L8SELF (A-RPL-7): DIR/c8d2_{decimal,gmp} (the Stage-3 baseline) against bin/c8d2_* on the L8
                sample (2,000 kernels: per sector the 100 heaviest and random ones, 1,600 free and 400 power;
                2 x 512 points): exact in every scientific field.
Acceptance (Stage-6 fix round 4, W1/W22's class): "status":"passed" says only that every test the record executed
passed; --only and the options choose them. coverage(record, gate), and `--check RECORD --gate NAME` (exit 0 only for
acceptance evidence), recompute whether a record is the evidence of J-VAL-1, J-VAL-2, G-BK8, G-L8SELF or A-IN-6b (its
scope, sizes and parts; a skipped part is no evidence); every record lists them in "acceptance".
Numbers are compared as Decimal strings, never binary64. Each executable writes its own fresh output file. The
record goes only to --output. --jobs runs that many native batches at once, each with --threads threads. Every native
launch (run, fresh_output) gets harness_env: no inherited OMP_*, GOMP_*, KMP_* control and its own thread count (R1).
"""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,json,os,random,secrets,shutil,struct,subprocess,sys,tempfile,time
from decimal import Decimal as D,getcontext
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import load,dump,digest,environment_record,cxx_command,omp_child_env,TeamWatch
getcontext().prec=60
IDENTITY=('uid','rep','graph','begin','end','total')
TAIL=('tail_top','tail_sum','tail_argmax')
GMP_MP_TOLERANCE=D('1e-30')
SEED=7738251
GAMMA7=ROOT/'reference/c7d2_hpc_a55958f/inputs/gamma_d2_7.txt'
GAMMA8=ROOT/'inputs/gamma_d2_8.txt'
L2_GRAPH=ROOT/'reference/LRI_C7_d2_progress/inputs/L2/G0.txt'
BACKENDS=('decimal','gmp')

# ---------------------------------------------------------------- shared helpers (also used by the other native tests)
def exe(backend:str)->Path:return ROOT/'bin'/f'c8d2_{backend}'
def ref_exe(backend:str)->Path:return ROOT/'bin'/'ref'/f'c7d2_{backend}'
def require(*paths:Path,hint:str)->None:
    missing=[str(p)for p in paths if not p.exists()]
    if missing:raise SystemExit(f'missing {", ".join(missing)}; build them first ({hint})')

_INV=None
def inventory()->dict:
    global _INV
    if _INV is None:_INV=load(ROOT/'inputs/inventory.json')
    return _INV

def stage(root:Path,sector:str,L:int,ids)->Path:
    """Write the G-files of (sector, L, ids) to root/L<L>/G<id>.txt from the package's packs, each checked against its
    inputs/inventory.json sha256. L=2 is the two-loop control graph (id 0). Returns root."""
    dest=root/f'L{L}';dest.mkdir(parents=True,exist_ok=True)
    if L==2:
        if set(ids)!={0}:raise ValueError('the L=2 control graph has id 0')
        shutil.copyfile(L2_GRAPH,dest/'G0.txt');return root
    rows={r['id']:r for r in inventory()[sector][str(L)]}
    pack=ROOT/f'inputs/packs/{sector}_L{L}.pack'
    with pack.open('rb')as f:
        for g in sorted(set(ids)):
            target=dest/f'G{g}.txt'
            if target.exists():continue
            r=rows[g];f.seek(r['offset']);data=f.read(r['length'])
            if len(data)!=r['length']or hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError(f'{pack} member G{g} does not match inputs/inventory.json')
            target.write_bytes(data)
    return root

def graph_truncations(text:str)->dict:
    """Z4 (Stage-6 fix round 3, S6A3-04): {case: G-file text} of a valid G-file's text, ended early or with one
    unreadable token in every section src/kernel.hpp's load_graph reads after the header: the mask list, the first
    denominator size, the first monomial-id list and coefficient row, the last coefficient of the last term, the
    rate-table size, the middle and the last entry of the table. load_graph must refuse each with "truncated graph"
    (before the fix, a mask list that ended early left n unassigned before its comparison and resize)."""
    t=text.split();L=int(t[1]);E=2*L;M=int(t[5]);T=int(t[6]);p=7+M;terms=[]
    for _ in range(T):n=int(t[p]);terms.append((p,n));p+=1+n+E
    R=int(t[p])
    if t[0]!='C7D2GRAPH1'or R!=1<<E or len(t)!=p+1+R:raise ValueError('graph_truncations needs a valid G-file')
    cut=lambda k:' '.join(t[:k])+'\n';bad=lambda k:' '.join(t[:k]+['x']+t[k+1:])+'\n'
    (p0,n0),(pl,nl)=terms[0],terms[-1]
    return {'mask_list':cut(7+M//2),'unreadable_mask':bad(7+M//2),'denominator_size':cut(7+M),'unreadable_denominator_size':bad(p0),
            'monomial_ids':cut(p0+1+n0//2),'unreadable_monomial_id':bad(p0+1+n0//2),'coefficients':cut(p0+1+n0+E//2),
            'unreadable_coefficient':bad(p0+1+n0+E//2),'last_term':cut(pl+nl+E),'rate_table_size':cut(p),'unreadable_rate_table_size':bad(p),
            'rate_table':cut(p+1+R//2),'unreadable_rate':bad(p+1+R//2),'rate_table_last':cut(p+R)}

def by_cost(sector:str,L:int)->list:
    """Kernel ids of (sector, L), heaviest first (proxy cost max(1, M*T), ties by id)."""
    return [r['id']for r in sorted(inventory()[sector][str(L)],key=lambda r:(-r['cost'],r['id']))]

def heavy_and_random(sector:str,L:int,heavy:int,rand:int,seed:int)->list:
    order=by_cost(sector,L);rest=sorted(order[heavy:]);rng=random.Random(seed)
    return sorted(order[:heavy]+rng.sample(rest,min(rand,len(rest))))

def tasks_text(order:int,L:int,rows)->str:
    return f'C8D2TASKS1 {order} {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows)
def c7_tasks_text(L:int,rows)->str:
    return f'C7D2TASKS1 {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows)
def task_rows(ids,reps:int,n:int,chunk:int|None=None)->list:
    """(uid, rep, graph, begin, end, total) for every replicate and graph, whole tasks or chunks of `chunk` points."""
    out=[];uid=0
    for r in range(reps):
        for g in ids:
            for b in range(0,n,chunk or n):out.append((uid,r,g,b,min(n,b+(chunk or n)),n));uid+=1
    return out

def native_threads(cmd)->int:
    """The thread count of a native_cmd command line (its 10th of 12 words, the last one '-'); 1 for any other command."""
    return int(cmd[9])if len(cmd)==12 and str(cmd[11])=='-'else 1

def harness_env(threads:int,env=None)->dict:
    """R1 (Stage-6 residual after fix round 2): the environment of every native launch of the test harnesses that use
    this module (validate.py, forced_tiers.py, numerics_flags.py's F1 tool): common.omp_child_env, i.e. env (default:
    this process's environment) without any inherited OpenMP control (OMP_*, GOMP_*, KMP_*: an inherited
    OMP_THREAD_LIMIT=1 or OMP_DYNAMIC=true would shrink the team the program's thread argument asks for, and a
    multi-threaded check would run serially), with OMP_NUM_THREADS=threads and OMP_DYNAMIC=FALSE; unbound
    (bind=False: --jobs runs unpinned batches concurrently, which must not all bind to the first cores)."""
    return omp_child_env(threads,env,bind=False)

def run(cmd,env=None,timeout=None,threads:int|None=None)->subprocess.CompletedProcess:
    """Run a native program (stdout and stderr captured; a nonzero exit raises RuntimeError) in harness_env(threads, env):
    threads defaults to native_threads(cmd), so a worker run gets its own thread count."""
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=harness_env(native_threads(cmd)if threads is None else threads,env),timeout=timeout)
    if p.returncode:raise RuntimeError(f'{cmd[0]} exited {p.returncode}: {p.stderr[-3000:]}')
    return p

def fresh_output(cmd,out:Path,env=None,threads:int|None=None)->dict:
    """Run cmd (whose output argument is out) after deleting out; the output must exist afterwards."""
    out.unlink(missing_ok=True);run(cmd,env=env,threads=threads)
    if not out.exists():raise AssertionError(f'{cmd[0]} exited 0 without writing {out}')
    return load(out)

def team_run(cmd,out:Path,threads:int,label:str)->tuple[dict,dict]:
    """R1 (Stage-6 residual after fix round 2): one run of a thread-identity comparison (A-RPL-6 invariance). The run gets
    the controlled OpenMP environment common.omp_child_env(threads) (no inherited OMP_*, GOMP_*, KMP_*; OMP_DYNAMIC=FALSE;
    it runs alone, so bound as production binds), its output is deleted first and must exist afterwards, and its OpenMP
    team is observed while it runs (common.TeamWatch, as production.py and tests/thread_identity.py observe it: the
    worker's /proc/<pid>/task count, which libgomp keeps at the team size from the first parallel region to the exit).
    A team other than `threads`, a run whose team was not seen before it exited, and a platform where it cannot be seen
    (no /proc: macOS) fail (AssertionError): an identity between two serial runs is no thread identity. Returns
    (the output, the team record)."""
    out.unlink(missing_ok=True)
    p=subprocess.Popen(list(map(str,cmd)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=omp_child_env(threads))
    watch=TeamWatch(p,threads)
    try:_,err=p.communicate()
    finally:
        if p.poll()is None:p.kill();p.wait()
        team=watch.stop()
    if p.returncode:raise RuntimeError(f'{label}: {cmd[0]} exited {p.returncode}: {err[-3000:]}')
    if not out.exists():raise AssertionError(f'{label}: {cmd[0]} exited 0 without writing {out}')
    if team['verdict']!='verified'or team['observed']!=threads:
        raise AssertionError(f'{label}: {threads} OpenMP threads requested, team {team["verdict"]} (largest seen {team["observed"]}; '
                             +('no /proc/<pid>/task here: the team cannot be observed'if team['verdict']=='unavailable'else
                               'an OpenMP control or a runtime that ignores the request')+'): the thread identity would compare serial runs')
    return load(out),team

def native_cmd(executable,root,gamma,net,tasks,out,seed=SEED,layout=0,rate=.8,threads=1,mode='compensated'):
    return [executable,root,gamma,net,tasks,out,seed,layout,rate,threads,mode,'-']

def make_net(path:Path,B:int,dim:int,bits:int,seed:int,max_count:int)->dict:
    """A test net in the native format (12-byte header B, dim, bits, then B direction matrices of dim x bits uint64):
    B independently scrambled SciPy Sobol matrices, the construction of tools/production.py's make_net, written
    independently of the orchestration code. Checked: the public random_base2(k) points of every replicate equal the
    native state shift ^ (direction columns of gray(n)) for the first k = min(m, 12) columns, and every direction
    integer of the m columns a stratum of max_count points reaches is nonzero and below 2^bits. The worker applies its
    own seeded digital shift, so the file holds the matrices only."""
    import numpy as np
    from scipy.stats import qmc
    m=0 if max_count<=1 else (max_count-1).bit_length()
    if m>bits:raise ValueError('Sobol period exceeded')
    k=min(m,12);rng=np.random.default_rng(seed);seeds=[int(rng.integers(1,2**32-1))for _ in range(B)]
    with path.open('xb')as f:
        f.write(struct.pack('<III',B,dim,bits))
        for s in seeds:
            e=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=s);sv=np.asarray(e._sv,dtype=np.uint64).copy();shift=np.asarray(e._shift,dtype=np.uint64).copy()
            if sv.shape!=(dim,bits):raise RuntimeError(f'unexpected SciPy direction matrix shape {sv.shape}')
            st=np.empty((1<<k,dim),dtype=np.uint64);st[0]=shift
            for j in range(k):h=1<<j;st[h:2*h]=st[h-1::-1]^sv[:,j][None,:]
            if not np.array_equal(st.astype(np.float64)/2.0**bits,e.random_base2(k)):raise RuntimeError('Sobol export failed the public-API check')
            if m and ((sv[:,:m]==0).any()or(sv[:,:m]>>np.uint64(bits)).any()):raise RuntimeError('Sobol direction integer zero or out of range')
            f.write(sv.astype('<u8').tobytes())
    if path.stat().st_size!=12+B*dim*bits*8:raise RuntimeError('Sobol export has the wrong size')
    return {'B':B,'dim':dim,'bits':bits,'seed':seed,'columns_checked':m,'sha256':digest(path)}

def scientific(r:dict)->dict:return {k:v for k,v in r.items()if k!='seconds'}

def same(x,y)->bool:return x==y

BK8_ROW_RULE='c8-d2-bk8-row-rule-2'   # W2: G-BK8 compares every row field, max_abs and the tail fields of mp>0 rows included
NTAIL=16   # the worker's tail_top length (src/c8d2_integrate.cpp NTAIL): min(16, points of the row) entries
ROW_NUMERIC=('values','max_abs')   # the numeric row fields compared exactly (mp = 0) or within GMP_MP_TOLERANCE (mp > 0)
TIE_POLICY=('tail_argmax: equal; an mp > 0 row may differ only at a near tie, i.e. when in BOTH rows the two largest |t| '
            '(tail_top[0], tail_top[1]) agree within GMP_MP_TOLERANCE normalized (rounding inside the tolerance can then move '
            'the first maximum to the other point); every argmax lies in the row\'s point range [begin, end)')
def normalized(u,v)->D:return abs(D(u)-D(v))/max(D(1),abs(D(u)))

def tail_shape(r:dict,what:str)->None:
    """The tail fields of one row: tail_top holds min(NTAIL, end - begin) finite values >= 0 in descending order,
    tail_sum is finite and tail_argmax is a point index of the row; AssertionError otherwise."""
    top=r.get('tail_top');n=min(NTAIL,int(r['end'])-int(r['begin']))
    if not isinstance(top,list)or len(top)!=n:raise AssertionError(f'{what}: row {r.get("uid")} tail width {len(top)if isinstance(top,list)else top!r}, not {n}')
    vals=[D(v)for v in top]
    if any(not v.is_finite()or v<0 for v in vals)or vals!=sorted(vals,reverse=True):raise AssertionError(f'{what}: row {r.get("uid")} tail_top not descending finite |t|')
    if not D(r['tail_sum']).is_finite():raise AssertionError(f'{what}: row {r.get("uid")} tail_sum not finite')
    a=r.get('tail_argmax')
    if not isinstance(a,int)or isinstance(a,bool)or not int(r['begin'])<=a<int(r['end']):raise AssertionError(f'{what}: row {r.get("uid")} tail_argmax {a!r} outside [begin, end)')

def compare(ref:dict,new:dict,backend:str,tails:bool=False)->dict:
    """The C7(2) A-L6 replay rule for one matched batch, applied to EVERY field of every row (W2, Stage-6 fix round 4,
    S6A4-02); raises AssertionError on any violation. Rows: identity and jet width equal; quad and mp equal; decimal (or
    any row with mp = 0): values and max_abs equal as strings; gmp rows with mp > 0: every value AND max_abs within
    GMP_MP_TOLERANCE normalized, |x - y|/max(1, |x|). tails (G-BK8: both rows are C8(2) rows): the tail fields too,
    exact when mp = 0; when mp > 0 the widths equal, every tail_top entry and tail_sum within GMP_MP_TOLERANCE
    normalized, tail_argmax equal or a near tie (TIE_POLICY); every row's tail fields well formed (tail_shape). Without
    tails (G-REF: the research worker writes no tail fields) the reference rows must have none. Field coverage: a row
    field that no rule above compares (other than 'seconds') fails the batch, so a field cannot be skipped silently.
    The header fields both outputs share (HEADER_COMMON but the MP backend's own) are equal."""
    rr,nr=ref['rows'],new['rows']
    for k in HEADER_COMMON:
        if k in('mp_backend','mp_digits10')or k not in ref or k not in new:continue
        if ref[k]!=new[k]:raise AssertionError(f'{backend}: header field {k}: {new[k]!r} != {ref[k]!r}')
    if len(rr)!=len(nr):raise AssertionError(f'{backend}: row count {len(nr)} != reference {len(rr)}')
    covered=set(IDENTITY)|{'quad','mp','seconds','rate'}|set(ROW_NUMERIC)|(set(TAIL)if tails else set())
    worst=D(0);worst_max_abs=D(0);tail_worst=D(0);tail_rel=D(0);mp_rows=0;tail_exact=0;ties=0
    for x,y in zip(rr,nr):
        xs,ys=set(x),set(y)
        if not tails and xs&set(TAIL):raise AssertionError(f'{backend}: the reference row {x.get("uid")} has tail fields; compare it with tails=True')
        extra=(xs|(ys-(set(TAIL)if not tails else set())))-covered
        if extra:raise AssertionError(f'{backend}: row {x.get("uid")} field(s) {sorted(extra)} not covered by the comparison rule (W2)')
        miss=[k for k in (*IDENTITY,'quad','mp',*ROW_NUMERIC,*(TAIL if tails else()))if k not in x or k not in y]
        if miss or ('rate'in xs)!=('rate'in ys):raise AssertionError(f'{backend}: row {x.get("uid")} lacks field(s) {miss or ["rate"]}')
        if tuple(x[k]for k in IDENTITY)!=tuple(y[k]for k in IDENTITY):raise AssertionError(f'{backend}: row identity {tuple(y[k]for k in IDENTITY)} != {tuple(x[k]for k in IDENTITY)}')
        if len(x['values'])!=len(y['values']):raise AssertionError(f'{backend}: jet width {len(y["values"])} != {len(x["values"])}')
        if x['quad']!=y['quad']or x['mp']!=y['mp']:raise AssertionError(f'{backend}: changed promotion count in row {x["uid"]}')
        if 'rate'in xs and x['rate']!=y['rate']:raise AssertionError(f'{backend}: row {x["uid"]} rate {y["rate"]!r} != {x["rate"]!r}')
        if tails:tail_shape(x,f'{backend} reference');tail_shape(y,backend)
        if backend=='decimal'or y['mp']==0:
            if x['values']!=y['values']or x['max_abs']!=y['max_abs']:raise AssertionError(f'{backend}: row {x["uid"]} differs from the reference (exact equality required)')
            if tails:
                if any(x[k]!=y[k]for k in TAIL):raise AssertionError(f'{backend}: tail fields of row {x["uid"]} (mp=0) differ (exact equality required)')
                tail_exact+=1
        else:
            mp_rows+=1
            for u,v in zip(x['values'],y['values']):worst=max(worst,normalized(u,v))
            if worst>GMP_MP_TOLERANCE:raise AssertionError(f'{backend}: row {x["uid"]} with mp>0 differs by {worst} > {GMP_MP_TOLERANCE} (normalized)')
            worst_max_abs=max(worst_max_abs,normalized(x['max_abs'],y['max_abs']))
            if worst_max_abs>GMP_MP_TOLERANCE:raise AssertionError(f'{backend}: row {x["uid"]} with mp>0: max_abs differs by {worst_max_abs} > {GMP_MP_TOLERANCE} (normalized)')
            if tails:
                for u,v in zip(x['tail_top']+[x['tail_sum']],y['tail_top']+[y['tail_sum']]):
                    tail_worst=max(tail_worst,normalized(u,v));tail_rel=max(tail_rel,abs(D(u)-D(v))/max(abs(D(u)),D('1e-4900')))
                if tail_worst>GMP_MP_TOLERANCE:raise AssertionError(f'{backend}: row {x["uid"]} with mp>0: tail fields differ by {tail_worst} > {GMP_MP_TOLERANCE} (normalized)')
                if x['tail_argmax']!=y['tail_argmax']:
                    near=lambda r:len(r['tail_top'])>=2 and normalized(r['tail_top'][0],r['tail_top'][1])<=GMP_MP_TOLERANCE
                    if not (near(x)and near(y)):raise AssertionError(f'{backend}: row {x["uid"]} with mp>0: tail_argmax {y["tail_argmax"]} != {x["tail_argmax"]} without a near tie ({TIE_POLICY})')
                    ties+=1
    out={'rows':len(rr),'graphs':len({r['graph']for r in nr}),'mp_rows':mp_rows,'max_normalized_difference_mp_rows':str(worst),
         'max_abs_max_normalized_difference_mp_rows':str(worst_max_abs)}
    if tails:out.update(tail_rows_exact=tail_exact,tail_max_normalized_difference_mp_rows=str(tail_worst),tail_max_relative_difference_mp_rows=str(tail_rel),tail_argmax_ties=ties)
    return out

HEADER_COMMON=('L','seed','layout','bits','rate','sum_mode','long_double_bits','mp_backend','mp_digits10')
def compare_exact(ref:dict,new:dict,what:str)->dict:
    """G-C7: exact equality of every field the C7(2) worker writes (identity, values, quad, mp, max_abs) in every row,
    and of the common header fields."""
    for k in HEADER_COMMON:
        if ref.get(k)!=new.get(k):raise AssertionError(f'{what}: header field {k}: {new.get(k)!r} != {ref.get(k)!r}')
    rr,nr=ref['rows'],new['rows']
    if len(rr)!=len(nr):raise AssertionError(f'{what}: row count {len(nr)} != {len(rr)}')
    mp_rows=0;fields=set(IDENTITY+('values','quad','mp','max_abs','seconds','rate'))
    for x,y in zip(rr,nr):
        # W2's class: every field the C7(2) worker writes is compared (its rows carry no tail fields; the C8(2) rows'
        # tail fields are G-JET's and G-BK8's), and a field outside the rule fails instead of being skipped
        extra=(set(x)|(set(y)-set(TAIL)))-fields
        if extra or set(x)&set(TAIL):raise AssertionError(f'{what}: row {x.get("uid")} field(s) {sorted(extra|(set(x)&set(TAIL)))} not covered by the G-C7 rule')
        if ('rate'in x)!=('rate'in y)or('rate'in x and x['rate']!=y['rate']):raise AssertionError(f'{what}: row {x.get("uid")} rate differs')
        for k in IDENTITY+('values','quad','mp','max_abs'):
            if x[k]!=y[k]:raise AssertionError(f'{what}: row {x["uid"]} field {k}: {y[k]!r} != {x[k]!r}')
        mp_rows+=x['mp']>0
    return {'rows':len(rr),'mp_rows':mp_rows,'quad_points':sum(r['quad']for r in rr),'mp_points':sum(r['mp']for r in rr)}

def compare_jet(o7:dict,o8:dict,L:int,what:str)->dict:
    """G-JET: order 8 against order 7 on the same tasks."""
    if o7.get('order')!=7 or o8.get('order')!=8:raise AssertionError(f'{what}: orders {o7.get("order")}/{o8.get("order")}')
    K7,K8=7-L,8-L;rr,nr=o7['rows'],o8['rows']
    if len(rr)!=len(nr):raise AssertionError(f'{what}: row count')
    fields=set(IDENTITY+('values','quad','mp','max_abs','seconds','rate')+TAIL)
    for x,y in zip(rr,nr):
        # W2's class: both are C8(2) rows; every field is compared below, and a field outside the rule fails
        if set(x)!=set(y)or set(x)-fields or not set(TAIL)<=set(x):raise AssertionError(f'{what}: row {x.get("uid")} fields {sorted(set(x)^set(y))or sorted(set(x)-fields)or "without tails"} not covered by the G-JET rule')
        if 'rate'in x and x['rate']!=y['rate']:raise AssertionError(f'{what}: row {x["uid"]} rate differs between orders')
        if tuple(x[k]for k in IDENTITY)!=tuple(y[k]for k in IDENTITY):raise AssertionError(f'{what}: row identity')
        if len(x['values'])!=2*(K7+1)or len(y['values'])!=2*(K8+1):raise AssertionError(f'{what}: row widths {len(x["values"])}/{len(y["values"])}')
        for j in range(K7+1):
            if y['values'][j]!=x['values'][j]:raise AssertionError(f'{what}: row {x["uid"]} b slot {j}: {y["values"][j]} != {x["values"][j]}')
            if y['values'][K8+1+j]!=x['values'][K7+1+j]:raise AssertionError(f'{what}: row {x["uid"]} c slot {j}: {y["values"][K8+1+j]} != {x["values"][K7+1+j]}')
        for k in ('quad','mp','max_abs')+TAIL:
            if x[k]!=y[k]:raise AssertionError(f'{what}: row {x["uid"]} field {k} differs between orders')
        for v in (y['values'][K8],y['values'][2*K8+1]):
            if not D(v).is_finite():raise AssertionError(f'{what}: row {x["uid"]} new slot not finite: {v}')
    return {'rows':len(rr)}

def merge_tails(rows:list)->tuple:
    """The 16 largest |t| of the union of rows (descending Decimals), the Decimal sum of tail_sum, and the argmax of the
    union (ties to the smaller point index), as C63d's merge defines them."""
    vals=sorted((D(v)for r in rows for v in r['tail_top']),reverse=True)[:16]
    best=min(rows,key=lambda r:(-D(r['tail_top'][0]),r['tail_argmax']))
    return vals,sum(D(r['tail_sum'])for r in rows),best['tail_argmax']

def chunk_merge(r:dict,parts:list,what:str)->tuple:
    """A-RPL-6: the chunk rows of one whole task against the whole row, every field (W2's class, Stage-6 fix round 4:
    before, quad, mp, max_abs and the chunks' coverage of the task were not compared). The chunks tile [begin, end) of
    the whole task exactly once (same total); quad and mp add up to the whole's (each point's tier does not depend on
    the chunking); max_abs is the largest chunk max_abs (the same points); tail_top and tail_argmax merge exactly
    (merge_tails); values (the per-task Kahan grouping differs) and tail_sum are returned as differences for the
    caller's bounds: (max normalized value difference, tail_sum relative difference). AssertionError otherwise."""
    span=sorted((p['begin'],p['end'])for p in parts)
    if span[0][0]!=r['begin']or span[-1][1]!=r['end']or any(a[1]!=b[0]for a,b in zip(span,span[1:]))or any(p['total']!=r['total']for p in parts):
        raise AssertionError(f'{what}: the chunks {span} do not tile [{r["begin"]}, {r["end"]}) of the whole task')
    if sum(p['quad']for p in parts)!=r['quad']or sum(p['mp']for p in parts)!=r['mp']:raise AssertionError(f'{what}: chunk quad/mp do not add up to the whole task\'s')
    if max(D(p['max_abs'])for p in parts)!=D(r['max_abs']):raise AssertionError(f'{what}: the largest chunk max_abs is not the whole task\'s')
    sums=[sum(D(p['values'][j])for p in parts)for j in range(len(r['values']))]
    if any(len(p['values'])!=len(r['values'])for p in parts):raise AssertionError(f'{what}: chunk jet width differs')
    e=max([D(0)]+[abs(D(v)-z)/max(D(1),abs(D(v)))for v,z in zip(r['values'],sums)])
    top,tsum,arg=merge_tails(parts)
    if [D(v)for v in r['tail_top']]!=top or r['tail_argmax']!=arg:raise AssertionError(f'{what}: tail merge')
    return e,abs(tsum-D(r['tail_sum']))/max(D(r['tail_sum']),D('1e-4900'))

# ---------------------------------------------------------------- A-KER-3
def describe(backends)->dict:
    out={}
    for b in backends:
        d=json.loads(run([exe(b),'--describe']).stdout)
        want={'schema':'c8-d2-build-1','dimension':2,'orders':[7,8],'lmax':8,'kmax':6,'emax':16,'dimmax':31,'numerics':'exact','diagnostic':False,'tail_top':16,
              'mp_backend':'gmp350'if b=='gmp'else'decimal300'}
        bad={k:(d.get(k),v)for k,v in want.items()if d.get(k)!=v}
        if bad:raise AssertionError(f'{b} --describe: {bad}')
        out[b]=d
    return {'test':'describe','status':'passed','describe':out}

# ---------------------------------------------------------------- A-KER-1/2
def bad_inputs(td:Path,backends)->dict:
    """Every refusal exits 2 and names its reason; the valid order/L combinations run."""
    td=td/'bad';td.mkdir()
    free3=stage(td/'free','free',3,[by_cost('free',3)[0]]);g3=by_cost('free',3)[0]
    l2=stage(td/'l2','free',2,[0])
    have8=(ROOT/'inputs/packs/free_L8.pack').exists();l8_case=()  # the valid L=8 run below, when the L8 pack exists
    if have8:
        g8=by_cost('free',8)[-1];free8=stage(td/'free8','free',8,[g8]);l8_case=((8,8,free8,GAMMA8,[g8]),)
    nets={}
    def net(L,layout=0,dim=None,B=2,bits=60):
        key=(L,layout,dim,B,bits)
        if key not in nets:
            p=td/f'net_{len(nets)}.bin';make_net(p,B,dim or (2*L if layout==2 else 4*L-1),bits,4401+len(nets),64);nets[key]=p
        return nets[key]
    def tasks(text,name='tasks'):p=td/name;p.write_text(text);return p
    rows=[(0,0,g3,0,16,16),(1,1,g3,0,16,16)]
    results=[];b=backends[0];out=td/'out.json'
    def refuse(name,cmd,needle):
        out.unlink(missing_ok=True)
        p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=harness_env(native_threads(cmd)))  # R1
        if p.returncode!=2 or needle not in p.stderr:raise AssertionError(f'{name}: exit {p.returncode}, stderr {p.stderr[-500:]!r}; expected exit 2 and {needle!r}')
        if out.exists():raise AssertionError(f'{name}: refused run wrote {out}')
        results.append({'case':name,'exit':2,'message':p.stderr.strip()[-300:]})
    E=exe(b)
    # task header: L outside [2, order], order outside [7, 8]
    refuse('order 8, L=9',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(8,9,rows)),out),'outside [2, order=8]')
    refuse('order 8, L=1',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(8,1,rows)),out),'outside [2, order=8]')
    refuse('order 7, L=8',native_cmd(E,free3,GAMMA7,net(3),tasks(tasks_text(7,8,rows)),out),'outside [2, order=7]')
    refuse('order 9',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(9,3,rows)),out),'task order 9 outside [7, 8]')
    refuse('order 6',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(6,3,rows)),out),'task order 6 outside [7, 8]')
    refuse('C7 task header',native_cmd(E,free3,GAMMA7,net(3),tasks(c7_tasks_text(3,rows)),out),'expected C8D2TASKS1')
    # gamma: label/column mismatch, trailing token, data after the last row
    refuse('order-8 task with gamma_d2_7.txt',native_cmd(E,free3,GAMMA7,net(3),tasks(tasks_text(8,3,rows)),out),'gamma label mismatch')
    refuse('order-7 task with gamma_d2_8.txt',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(7,3,rows)),out),'gamma label mismatch')
    lines=GAMMA8.read_text().splitlines(keepends=True);bad=td/'gamma_trailing.txt';bad.write_text(''.join(lines[:3])+lines[3].rstrip('\n')+' 1.0\n'+''.join(lines[4:]))
    refuse('gamma trailing token',native_cmd(E,free3,bad,net(3),tasks(tasks_text(8,3,rows)),out),'trailing token')
    bad2=td/'gamma_extra_row.txt';bad2.write_text(GAMMA8.read_text()+'-1 0.5 0 0 0 0 0 0 0\n')
    refuse('gamma data after the last row',native_cmd(E,free3,bad2,net(3),tasks(tasks_text(8,3,rows)),out),'data after the row of L=8')
    lines7=GAMMA7.read_text().splitlines(keepends=True);bad3=td/'gamma_short.txt';bad3.write_text(''.join(lines7[:2])+' '.join(lines7[2].split()[:-1])+'\n'+''.join(lines7[3:]))
    refuse('gamma row with a missing log value',native_cmd(E,free3,bad3,net(3),tasks(tasks_text(7,3,rows)),out),'fewer than 6 log values')
    # net dimension above DIMMAX
    refuse('dim=32',native_cmd(E,free3,GAMMA8,net(3,dim=32),tasks(tasks_text(8,3,rows)),out),'net dimension 32 exceeds DIMMAX=31')
    # a graph with E > 16 (header L=9) in an L=8 task
    big=td/'big';(big/'L8').mkdir(parents=True);(big/'L8'/'G1.txt').write_text('C7D2GRAPH1 9 1 1 0 1 1\n1\n1 0 '+'1 '*18+'\n4\n0 1 1 0\n')
    refuse('graph with E>16',native_cmd(E,big,GAMMA8,net(8),tasks(tasks_text(8,8,[(0,0,1,0,16,16)])),out),'more than EMAX=16 propagators')
    # Z4 (Stage-6 fix round 3, S6A3-04): a G-file whose body ends early or holds an unreadable token, in every section
    # of load_graph, is refused with "truncated graph" by the worker and by the inspector (the same loader)
    gtext=(free3/'L3'/f'G{g3}.txt').read_text();cases=graph_truncations(gtext)
    for case,text in cases.items():
        root=td/f'trunc_{case}';(root/'L3').mkdir(parents=True);(root/'L3'/f'G{g3}.txt').write_text(text)
        refuse(f'G-file {case}',native_cmd(E,root,GAMMA8,net(3),tasks(tasks_text(8,3,rows)),out),'truncated graph')
    inspect=ROOT/'bin/c8d2_inspect'
    if inspect.exists():
        for case,text in cases.items():
            pack=td/f'trunc_{case}.pack';pack.write_bytes(text.encode());index=td/f'trunc_{case}.index';index.write_text(f'{g3} 3 0 {len(text.encode())}\n')
            p=subprocess.run([str(inspect),str(pack),str(index),'1'],capture_output=True,text=True,env=harness_env(1))  # R1
            if p.returncode!=2 or 'truncated graph'not in p.stderr or p.stdout:raise AssertionError(f'inspector, G-file {case}: exit {p.returncode}, stderr {p.stderr[-300:]!r}, stdout {p.stdout[:200]!r}')
            results.append({'case':f'inspector: G-file {case}','exit':2,'message':p.stderr.strip()[-300:]})
    else:results.append({'case':'inspector: truncated G-files','skipped':'bin/c8d2_inspect is not built (make inspect)'})
    # scalar rates
    for r in ('0','1.5','0.8x','-0.5','nan',''):
        refuse(f'scalar rate {r!r}',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(8,3,rows)),out,rate=r),'invalid rate argument')
    # @FILE rate maps (R7): exact coverage of the task file's graphs, one 'graph rate' per line, values in (0, 1]
    two=[(0,0,g3,0,16,16)];other=by_cost('free',3)[1]
    for name,text,needle in (('rate file missing graph',f'{other} 0.8\n','has no rate for graph'),
                             ('rate file extra graph',f'{g3} 0.8\n{other} 0.9\n',f'lists graph {other}, which is not in the task file'),
                             ('rate file duplicate graph',f'{g3} 0.8\n{g3} 0.8\n','duplicate graph'),
                             ('rate file trailing token',f'{g3} 0.8 x\n',"expected exactly 'graph rate'"),
                             ('rate file value 0',f'{g3} 0\n','invalid rate for graph'),
                             ('rate file value above 1',f'{g3} 1.25\n','invalid rate for graph'),
                             ('rate file value not decimal',f'{g3} 0.8e\n','invalid rate for graph'),
                             ('rate file bad graph id',f'G{g3} 0.8\n','invalid graph id')):
        rf=td/'rates.txt';rf.write_text(text)
        refuse(name,native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(8,3,two)),out,rate='@'+str(rf)),needle)
    refuse('rate file missing',native_cmd(E,free3,GAMMA8,net(3),tasks(tasks_text(8,3,two)),out,rate='@'+str(td/'absent.txt')),'cannot open rate file')
    # valid runs: both orders, L=2 at both orders, row widths, order/numerics/max_rss_kb, @FILE echo
    runs=[]
    for be in backends:
        E2=exe(be)
        for order,L,root,gamma,ids in ((7,2,l2,GAMMA7,[0]),(8,2,l2,GAMMA8,[0]),(7,3,free3,GAMMA7,[g3]),(8,3,free3,GAMMA8,[g3]))+l8_case:
            rws=[(i,r,ids[0],0,16,16)for i,r in enumerate(range(2))]
            d=fresh_output(native_cmd(E2,root,gamma,net(L),tasks(tasks_text(order,L,rws)),out),out)
            if d['schema']!='c8-d2-hpc-native-1'or d['order']!=order or d['L']!=L or d['numerics']!='exact'or not isinstance(d['max_rss_kb'],int)or d['max_rss_kb']<=0:raise AssertionError(f'{be} order {order} L={L}: header {d}')
            if sys.platform.startswith('linux')and d.get('max_rss_source')!='VmHWM':raise AssertionError(f'{be}: max_rss_kb must come from VmHWM on Linux, not {d.get("max_rss_source")}')
            if any(len(r['values'])!=2*(order+1-L)for r in d['rows']):raise AssertionError(f'{be} order {order} L={L}: row width')
            if any(len(r['tail_top'])!=16 or not isinstance(r['tail_argmax'],int)for r in d['rows']):raise AssertionError(f'{be}: tail fields')
            runs.append({'backend':be,'order':order,'L':L,'K':order-L,'row_width':2*(order+1-L),'max_rss_kb':d['max_rss_kb']})
        rf=td/'rates_ok.txt';rf.write_text(f'{g3} 0.8\n')
        scal=fresh_output(native_cmd(E2,free3,GAMMA8,net(3),tasks(tasks_text(8,3,two)),out,rate=.8),out)
        filed=fresh_output(native_cmd(E2,free3,GAMMA8,net(3),tasks(tasks_text(8,3,two)),out,rate='@'+str(rf)),out)
        if filed['rate']!='file'or any(r['rate']!=scal['rate']for r in filed['rows']):raise AssertionError(f'{be}: @FILE echo {filed["rate"]} {[r.get("rate")for r in filed["rows"]]}')
        if [{k:v for k,v in scientific(r).items()if k!='rate'}for r in filed['rows']]!=[scientific(r)for r in scal['rows']]:raise AssertionError(f'{be}: @FILE run differs from the scalar run at the same rate')
        runs.append({'backend':be,'rate_file':'echoed rates equal the scalar header rate; rows identical to the scalar run'})
    return {'test':'bad_inputs','status':'passed','refusals':results,'valid_runs':runs,'l8_pack_present':have8}

# ---------------------------------------------------------------- G-REF, G-C7, G-JET
def build_reference(path:Path)->list:
    """The research worker (G-REF), compiled with the Makefile's flags (common.cxx_command)."""
    cmd=cxx_command([ROOT/'reference/LRI_C7_d2_progress/code/c7d2_integrate.cpp'],path);subprocess.run(cmd,check=True);return cmd

def replay_selection(sector:str,L:int,full:bool)->list:
    if L==2:return [0]
    rows=inventory()[sector][str(L)];ids=[r['id']for r in rows]
    if full:return ids
    return sorted(set(ids[:8]+by_cost(sector,L)[:8]))

def replay_item(td:Path,item:dict,threads:int,reference:Path)->dict:
    sector,L,ids,rate,layout=item['sector'],item['L'],item['ids'],item['rate'],item['layout']
    d=Path(tempfile.mkdtemp(prefix=f'{sector}{L}_',dir=td));n=item['points']
    rows=task_rows(ids,2,n)
    t_c7=d/'t_c7';t_c7.write_text(c7_tasks_text(L,rows));t_o7=d/'t_o7';t_o7.write_text(tasks_text(7,L,rows));t_o8=d/'t_o8';t_o8.write_text(tasks_text(8,L,rows))
    cmd=lambda x,t,gamma,o:native_cmd(x,item['root'],gamma,item['net'],t,o,SEED,layout,rate,threads)
    res={};ref=fresh_output(cmd(reference,t_c7,GAMMA7,d/'ref.json'),d/'ref.json')if item['ref']else None
    for b in BACKENDS:
        c7=fresh_output(cmd(ref_exe(b),t_c7,GAMMA7,d/f'c7_{b}.json'),d/f'c7_{b}.json')
        o7=fresh_output(cmd(exe(b),t_o7,GAMMA7,d/f'o7_{b}.json'),d/f'o7_{b}.json')
        o8=fresh_output(cmd(exe(b),t_o8,GAMMA8,d/f'o8_{b}.json'),d/f'o8_{b}.json')
        res[f'G-C7/{b}']=compare_exact(c7,o7,f'G-C7 {b} {sector} L{L} rate {rate} layout {layout}')
        res[f'G-JET/{b}']=compare_jet(o7,o8,L,f'G-JET {b} {sector} L{L} rate {rate} layout {layout}')
        if ref is not None:res[f'G-REF/{b}']=compare(ref,o7,b)
    shutil.rmtree(d)
    return res

def replay(td:Path,full:bool,jobs:int,threads:int)->list:
    require(exe('decimal'),exe('gmp'),hint='make && make gmp')
    require(ref_exe('decimal'),ref_exe('gmp'),hint='make c7ref')
    reference=td/'reference_worker';cmd=build_reference(reference)
    items=[];batch=24;n=64
    groups=[('free',2)]+[(s,L)for s in('free','power')for L in range(3,8)]
    for sector,L in groups:
        ids=replay_selection(sector,L,full);root=stage(td/f'graphs_{sector}',sector,L,ids)
        configs=[(.8,0)]+([(r,l)for r in(.8,.9)for l in(0,1,2)if(r,l)!=(.8,0)]if L==7 else[])
        for rate,layout in configs:
            net=td/f'net_{sector}_L{L}_{layout}.bin'
            if not net.exists():make_net(net,2,2*L if layout==2 else 4*L-1,60,983507+L+(11255 if sector=='power'else 0)+1009*layout,n)
            for off in range(0,len(ids),batch):
                items.append(dict(sector=sector,L=L,ids=ids[off:off+batch],rate=rate,layout=layout,root=root,net=net,points=n,ref=(rate,layout)==(.8,0)))
    stats={};t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs)as pool:
        futures={pool.submit(replay_item,td,it,threads,reference):it for it in items}
        for k,fut in enumerate(concurrent.futures.as_completed(futures)):
            it=futures[fut];res=fut.result()
            key=(it['sector'],it['L'],it['rate'],it['layout'])
            s=stats.setdefault(key,{'graphs':set(),'gates':{}})
            s['graphs'].update(it['ids'])
            for gate,r in res.items():
                g=s['gates'].setdefault(gate,{'rows':0,'mp_rows':0,'max_normalized_difference_mp_rows':D(0),'quad_points':0,'mp_points':0})
                g['rows']+=r['rows'];g['mp_rows']+=r.get('mp_rows',0);g['quad_points']+=r.get('quad_points',0);g['mp_points']+=r.get('mp_points',0)
                g['max_normalized_difference_mp_rows']=max(g['max_normalized_difference_mp_rows'],D(r.get('max_normalized_difference_mp_rows','0')))
            if k%50==0:print(f'replay {k+1}/{len(items)} items, {time.time()-t0:.0f} s',flush=True)
    out=[]
    for (sector,L,rate,layout),s in sorted(stats.items()):
        out.append({'test':'replay_all_kernels'if full else'replay_subset','sector':sector,'L':L,'rate':rate,'layout':layout,'graphs':len(s['graphs']),
                    'points_per_task':n,'replicates':2,'seed':SEED,
                    'gates':{gate:{**{k:v for k,v in g.items()if k!='max_normalized_difference_mp_rows'},'max_normalized_difference_mp_rows':str(g['max_normalized_difference_mp_rows'])}
                             for gate,g in sorted(s['gates'].items())}})
    total=sum(len(s['graphs'])for (sector,L,rate,layout),s in stats.items()if (rate,layout)==(.8,0))
    return [{'test':'replay_summary','status':'passed','kernels':total,'full':full,'reference_worker_command':cmd,
             'reference_binaries':{b:digest(ref_exe(b))for b in BACKENDS},'c8_binaries':{b:digest(exe(b))for b in BACKENDS},
             'rules':{'G-REF':'decimal exact strings; gmp exact if mp=0, <=1e-30 normalized if mp>0; counters identical',
                      'G-C7':'exact strings in every row field the C7(2) worker writes (identity, values, quad, mp, max_abs), mp>0 rows included',
                      'G-JET':'b and c slots 0..7-L exact (c offset 8-L -> 9-L); quad, mp, max_abs and tail fields identical; new slot finite'},
             'wall_seconds':round(time.time()-t0,1)}]+out

# ---------------------------------------------------------------- A-RPL-6: chunks, layouts, tails
def invariance(td:Path,backends)->list:
    out=[]
    for b in backends:
        for sector in ('free','power'):
            for L in (7,8):
                if L==8 and not (ROOT/f'inputs/packs/{sector}_L8.pack').exists():raise SystemExit(f'{sector}_L8.pack is missing: make inputs-l8 INVENTORY=...')
                ids=by_cost(sector,L)[:3];root=stage(td/f'inv_{sector}',sector,L,ids);n=64
                for layout in (0,1,2):
                    net=td/f'split_{sector}{L}_{layout}.bin'
                    if not net.exists():make_net(net,2,2*L if layout==2 else 4*L-1,52,273845+layout+100*L+(7 if sector=='power'else 0),n)
                    tasks=td/'tasks_split';o=td/f'split_{b}.json'
                    cmd=lambda th:native_cmd(exe(b),root,GAMMA8,net,tasks,o,741987,layout,.9,th)
                    lab=f'{b} {sector} L{L} layout {layout}'
                    # R1: every run in the controlled OpenMP environment, its team observed (team_run)
                    tasks.write_text(tasks_text(8,L,task_rows(ids,2,n)));whole,t_whole=team_run(cmd(1),o,1,f'{lab} whole, 1 thread')
                    split=task_rows(ids,2,n,23);tasks.write_text(tasks_text(8,L,split))
                    many,t_many=team_run(cmd(4),o,4,f'{lab} chunks, 4 threads');one,t_one=team_run(cmd(1),o,1,f'{lab} chunks, 1 thread')
                    if len(many['rows'])!=len(split)or[scientific(r)for r in many['rows']]!=[scientific(r)for r in one['rows']]:raise AssertionError(f'{b}: thread dependent result')
                    groups={}
                    for r in one['rows']:groups.setdefault((r['rep'],r['graph']),[]).append(r)
                    e=D(0);tail_sum_rel=D(0)
                    for r in whole['rows']:
                        x,t=chunk_merge(r,groups[(r['rep'],r['graph'])],f'{lab} uid {r["uid"]}');e=max(e,x);tail_sum_rel=max(tail_sum_rel,t)
                    if e>D('1e-12')or tail_sum_rel>D('1e-15'):raise AssertionError((b,sector,L,layout,'split',e,tail_sum_rel))
                    out.append(dict(test='random_access_chunks',backend=b,sector=sector,L=L,layout=layout,graphs=ids,max_normalized_difference=str(e),
                                    tail_top_and_argmax_identical=True,tail_sum_max_relative_difference=str(tail_sum_rel),threads=[1,4],chunk_size=23,thread_identical=True,
                                    teams_observed={'whole_1':t_whole['observed'],'chunks_4':t_many['observed'],'chunks_1':t_one['observed']},team_sizes_verified=True,
                                    omp_environment='controlled (common.omp_child_env: no inherited OMP_*, GOMP_*, KMP_*; OMP_DYNAMIC=FALSE; R1)'))
                    print(out[-1],flush=True)
    return out

# ---------------------------------------------------------------- A-KER-5: inspector against the worker's own execution order
def inspector_order(td:Path,loops=(7,8))->dict:
    """A-KER-5 on 100 kernels (25 per sector at L7 and L8). The worker's order comes from the worker itself (checkpoint
    review T-04): src/c8d2_integrate.cpp built with -DC8_ORDER_TRACE, whose parallel task loop records the uid each
    iteration runs ("execution_order") and the addends.size() of every loaded graph ("addends"). bin/c8d2_inspect's
    addends equal inputs/inventory.json's and the worker's; on a block of 50 tasks of 16..128 points the executed order
    equals the order predicted from the inventory alone (stable, by decreasing points x addends); and the trace build's
    rows equal bin/c8d2_decimal's (the trace changes no value)."""
    inspect=ROOT/'bin/c8d2_inspect';require(inspect,hint='make inspect');require(exe('decimal'),hint='make')
    trace=td/'c8d2_order_trace';cmd=cxx_command([ROOT/'src/c8d2_integrate.cpp'],trace,defines=['C8_ORDER_TRACE']);subprocess.run(cmd,check=True)
    d=json.loads(run([trace,'--describe']).stdout)
    if d.get('diagnostic')is not True or d.get('diagnostic_kind')!='order_trace':raise AssertionError(f'order-trace build --describe {d}')
    rng=random.Random(5102);checked=0;details=[]
    for sector in ('free','power'):
        for L in loops:
            pack=ROOT/f'inputs/packs/{sector}_L{L}.pack'
            if not pack.exists():raise SystemExit(f'{pack} is missing: make inputs-l8 INVENTORY=...')
            rows={r['id']:r for r in inventory()[sector][str(L)]};ids=sorted(rng.sample(sorted(rows),25))
            index=td/f'index_{sector}{L}.txt';index.write_text(''.join(f'{g} {L} {rows[g]["offset"]} {rows[g]["length"]}\n'for g in ids))
            ins={j['id']:j for j in map(json.loads,run([inspect,pack,index,4],threads=4).stdout.splitlines())}
            root=stage(td/f'ord_{sector}',sector,L,ids)
            sizes=[16,32,64,128]
            trows=[(i,0,g,0,rng.choice(sizes),128)for i,g in enumerate(ids)]+[(25+i,1,g,0,rng.choice(sizes),128)for i,g in enumerate(ids)]
            tasks=td/f'tasks_order_{sector}{L}';tasks.write_text(tasks_text(8,L,trows))
            net=td/f'ord_{sector}{L}.bin'
            if not net.exists():make_net(net,2,4*L-1,52,5102+L+(7 if sector=='power'else 0),128)
            got=fresh_output(native_cmd(trace,root,GAMMA8,net,tasks,td/'ord_trace.json',threads=4),td/'ord_trace.json')
            ref=fresh_output(native_cmd(exe('decimal'),root,GAMMA8,net,tasks,td/'ord_prod.json',threads=4),td/'ord_prod.json')
            for g in ids:
                a=ins[g]['addends'];w=got['addends'][str(g)];v=rows[g]['addends']
                if not a==w==v:raise AssertionError(f'{sector} L{L} G{g}: addends inspector {a}, worker {w}, inventory {v}')
            key=lambda t:-((t[4]-t[3])*rows[t[2]]['addends'])
            predicted=[t[0]for t in sorted(trows,key=key)]  # Python's sort is stable, as std::stable_sort
            if got['execution_order']!=predicted:raise AssertionError(f'{sector} L{L}: executed order differs: {got["execution_order"][:10]} vs predicted {predicted[:10]}')
            if [scientific(r)for r in got['rows']]!=[scientific(r)for r in ref['rows']]:raise AssertionError(f'{sector} L{L}: the order-trace build changed a row')
            checked+=len(ids);details.append({'sector':sector,'L':L,'graphs':len(ids),'tasks':len(trows)})
    return {'test':'inspector_execution_order','status':'passed','graphs':checked,'groups':details,'trace_build_command':cmd,
            'rule':'c8d2_inspect addends == inventory.json addends == the worker\'s addends.size(); the worker\'s executed order '
                   '(-DC8_ORDER_TRACE) == the stable order by -(end-begin)*addends predicted from the inventory; trace rows == bin/c8d2_decimal rows'}

# ---------------------------------------------------------------- CK-K03: the inspector's private temporary directory
def inspector_tempdir(td:Path,sector:str='free',L:int=7)->dict:
    """bin/c8d2_inspect's temporary files (checkpoint review CK-K03), with TMPDIR a fresh directory: a normal run and a
    failing run (exit 2) leave it empty; while a long run works, it holds exactly one entry, c8d2_inspect.XXXXXX, a real
    directory (no symlink) of this user with mode 0700, holding only the thread files g<k>.txt, regular with mode 0600;
    SIGTERM and SIGUSR1 kill the run and leave TMPDIR empty; an ignored SIGHUP stays ignored (the run goes on)."""
    import signal as sg,stat as st_
    inspect=ROOT/'bin/c8d2_inspect';require(inspect,hint='make inspect')
    rows={r['id']:r for r in inventory()[sector][str(L)]};pack=ROOT/f'inputs/packs/{sector}_L{L}.pack'
    ids=by_cost(sector,L)[:4]
    def index(path:Path,entries,lv=L)->Path:
        path.write_text(''.join(f'{g} {lv} {rows[g]["offset"]} {rows[g]["length"]}\n'for g in entries));return path
    tmp=td/'inspect_tmp';tmp.mkdir();threads=2;env=harness_env(threads,{**os.environ,'TMPDIR':str(tmp)})  # R1
    def left()->list:return sorted(x.name for x in tmp.iterdir())
    out={'sector':sector,'L':L,'threads':threads,'signals':{}}
    r=run([inspect,pack,index(td/'insp_ok.txt',ids),threads],env=env,threads=threads)
    if len(r.stdout.splitlines())!=len(ids)or left():raise AssertionError(f'normal run: {len(r.stdout.splitlines())} lines, left behind {left()}')
    out['normal_run_left_behind']=left()
    p=subprocess.run([str(inspect),str(pack),str(index(td/'insp_bad.txt',ids[:1],lv=L-1)),str(threads)],env=env,capture_output=True,text=True)
    if p.returncode!=2 or 'identity mismatch'not in p.stderr or left():raise AssertionError(f'failing run: exit {p.returncode}, {p.stderr[-300:]!r}, left behind {left()}')
    out['failing_run']={'exit':p.returncode,'left_behind':left()}
    long_index=index(td/'insp_long.txt',[ids[0]]*100000)
    def observe(proc)->dict:
        t0=time.time()
        while time.time()-t0<120:
            if proc.poll()is not None:raise AssertionError(f'the inspector ended (exit {proc.returncode}) before the check')
            ents=list(tmp.iterdir())
            if len(ents)==1 and ents[0].is_dir()and not ents[0].is_symlink()and len(list(ents[0].iterdir()))==threads:break
            if any(not x.is_dir()or x.is_symlink()for x in ents):raise AssertionError(f'TMPDIR holds a non-directory entry: {[x.name for x in ents]}')
            time.sleep(0.01)
        else:raise AssertionError(f'no private directory with {threads} thread files appeared under TMPDIR: {left()}')
        dr=ents[0];s=os.lstat(dr);files={f.name:os.lstat(f)for f in dr.iterdir()}
        info={'name':dr.name,'mode':oct(st_.S_IMODE(s.st_mode)),'files':{k:oct(st_.S_IMODE(v.st_mode))for k,v in files.items()}}
        if not(dr.name.startswith('c8d2_inspect.')and len(dr.name)==len('c8d2_inspect.')+6 and st_.S_ISDIR(s.st_mode)and st_.S_IMODE(s.st_mode)==0o700
               and s.st_uid==os.getuid()and sorted(files)==[f'g{k}.txt'for k in range(threads)]
               and all(st_.S_ISREG(v.st_mode)and st_.S_IMODE(v.st_mode)==0o600 and v.st_uid==os.getuid()for v in files.values())):
            raise AssertionError(f'private directory: {info}')
        return info
    for sig in (sg.SIGTERM,sg.SIGUSR1):
        if sg.getsignal(sig)is sg.SIG_IGN:out['signals'][sig.name]='skipped (ignored by this process, so by the inspector)';continue
        proc=subprocess.Popen([str(inspect),str(pack),str(long_index),str(threads)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            info=observe(proc);proc.send_signal(sig);rc=proc.wait(timeout=120)
            if rc!=-sig or left():raise AssertionError(f'{sig.name}: exit {rc}, left behind {left()}')
            out['signals'][sig.name]={'exit':rc,'private_directory':info,'left_behind':left()}
        finally:
            if proc.poll()is None:proc.kill();proc.wait()
    proc=subprocess.Popen(['/bin/sh','-c','trap "" HUP; exec "$0" "$@"',str(inspect),str(pack),str(long_index),str(threads)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        observe(proc);proc.send_signal(sg.SIGHUP);time.sleep(1.0)
        if proc.poll()is not None:raise AssertionError(f'an ignored SIGHUP ended the inspector (exit {proc.returncode})')
        proc.send_signal(sg.SIGTERM);rc=proc.wait(timeout=120)
        if rc!=-sg.SIGTERM or left():raise AssertionError(f'SIGTERM after the ignored SIGHUP: exit {rc}, left behind {left()}')
        out['signals']['SIGHUP_ignored']={'still_running_after_1_s':True,'then_SIGTERM_exit':rc}
    finally:
        if proc.poll()is None:proc.kill();proc.wait()
    return {'test':'inspector_private_tempdir','status':'passed',**out,
            'rule':'TMPDIR empty after a normal run, an error exit and SIGTERM/SIGUSR1; during a run exactly one mkdtemp directory c8d2_inspect.XXXXXX '
                   '(0700, this user, no symlink) holding only g<k>.txt (regular, 0600); an ignored SIGHUP stays ignored'}

# ---------------------------------------------------------------- class B: the tail fields change no other field
def class_b(td:Path,backends)->dict:
    from build_record import BindingRefused,bound_tool_command,verify_tool
    out=[];bindings={}
    for b in backends:
        notail=td/f'notail_{b}'
        try:
            cmd,binding=bound_tool_command([ROOT/'src/c8d2_integrate.cpp'],notail,exe(b),b,defines=['C8_NO_TAIL_FIELDS']+(['C8_USE_GMP']if b=='gmp'else[]),
                                           libs=('-lquadmath','-lgmp')if b=='gmp'else('-lquadmath',))
            subprocess.run(cmd,check=True);bindings[b]=verify_tool(notail,binding)
        except BindingRefused as e:raise SystemExit(f'class B ({b}): {e}')
        d=json.loads(run([notail,'--describe']).stdout)
        if d.get('diagnostic')is not True or d.get('diagnostic_kind')!='no_tail_fields'or d.get('tail_top')!=0:raise AssertionError(f'{b}: no-tail build describe {d}')
        for sector in ('free','power'):
            for order,L in ((7,7),(8,7),(8,8)):
                ids=heavy_and_random(sector,L,4,4,611+L);root=stage(td/f'cb_{sector}',sector,L,ids)
                net=td/f'cb_{sector}{L}.bin'
                if not net.exists():make_net(net,2,4*L-1,60,8121+L,64)
                tasks=td/'cb_tasks';tasks.write_text(tasks_text(order,L,task_rows(ids,2,64)))
                gamma=GAMMA7 if order==7 else GAMMA8
                with_t=fresh_output(native_cmd(exe(b),root,gamma,net,tasks,td/'cb_with.json',threads=8),td/'cb_with.json')
                without=fresh_output(native_cmd(notail,root,gamma,net,tasks,td/'cb_without.json',threads=8),td/'cb_without.json')
                for x,y in zip(with_t['rows'],without['rows']):
                    if any(k in y for k in TAIL)or scientific(y)!={k:v for k,v in scientific(x).items()if k not in TAIL}:raise AssertionError(f'{b} {sector} order {order} L{L}: class-B violation in row {x["uid"]}')
                out.append({'backend':b,'sector':sector,'order':order,'L':L,'rows':len(with_t['rows']),'quad':sum(r['quad']for r in with_t['rows']),'mp':sum(r['mp']for r in with_t['rows'])})
    return {'test':'class_b_tail_fields','status':'passed','runs':out,'bindings':bindings,'rule':'every non-tail field of every row identical with and without the tail fields'}

# ---------------------------------------------------------------- diagnostic builds
def diagnostics(td:Path)->dict:
    builds={k:ROOT/f'bin/c8d2_gmp_{k}'for k in('prof','ratiohist')}
    present={k:p for k,p in builds.items()if p.exists()}
    if not present:return {'test':'diagnostic_builds','status':'skipped','reason':'make profile ratiohist not run'}
    out=[]
    for k,p in present.items():
        d=json.loads(run([p,'--describe']).stdout)
        if d.get('diagnostic')is not True or d.get('diagnostic_kind')!={'prof':'tier_timers','ratiohist':'ratio_histogram'}[k]:raise AssertionError(f'{p} --describe {d}')
        for sector in ('free','power'):
            for L in (7,8):
                ids=heavy_and_random(sector,L,4,4,733+L);root=stage(td/f'dg_{sector}',sector,L,ids)
                net=td/f'dg_{sector}{L}.bin'
                if not net.exists():make_net(net,2,4*L-1,60,9177+L,128)
                tasks=td/'dg_tasks';tasks.write_text(tasks_text(8,L,task_rows(ids,2,128)))
                base=fresh_output(native_cmd(exe('gmp'),root,GAMMA8,net,tasks,td/'dg_base.json',threads=8),td/'dg_base.json')
                diag=fresh_output(native_cmd(p,root,GAMMA8,net,tasks,td/'dg_diag.json',threads=8),td/'dg_diag.json')
                if [scientific(r)for r in base['rows']]!=[scientific(r)for r in diag['rows']]:raise AssertionError(f'{p}: rows differ from bin/c8d2_gmp ({sector} L{L})')
                points=sum(r['end']-r['begin']for r in base['rows']);quad=sum(r['quad']for r in base['rows']);mp=sum(r['mp']for r in base['rows'])
                if k=='prof':
                    t=diag['tier_timers'];calls=(t['first_pass_calls'],t['quad_calls'],t['mp_calls'])
                    if calls!=(points,quad,mp):raise AssertionError(f'{p}: tier calls {calls} != points/quad/mp {(points,quad,mp)}')
                    info={'seconds':{n:t[f'{n}_seconds']for n in('first_pass','quad','mp')}}
                else:
                    h=diag['ratio_histogram'];counts=(sum(h['ld_fail'].values()),sum(h['quad'].values()),sum(h['mp'].values()))
                    if counts!=(quad,quad,mp):raise AssertionError(f'{p}: histogram counts {counts} != quad/quad/mp {(quad,quad,mp)}')
                    info={'histogram_counts':counts}
                out.append({'build':k,'sector':sector,'L':L,'points':points,'quad':quad,'mp':mp,**info})
    return {'test':'diagnostic_builds','status':'passed','runs':out,'rule':'rows identical to bin/c8d2_gmp; every evaluation counted once'}

# ---------------------------------------------------------------- A-RPL-4: G-BK8
def bk8_item(td:Path,item:dict,threads:int)->dict:
    d=Path(tempfile.mkdtemp(prefix='bk8_',dir=td));tasks=d/'tasks';tasks.write_text(tasks_text(8,item['L'],task_rows(item['ids'],2,item['points'])))
    outs={b:fresh_output(native_cmd(exe(b),item['root'],GAMMA8,item['net'],tasks,d/f'{b}.json',threads=threads),d/f'{b}.json')for b in BACKENDS}
    r=compare(outs['decimal'],outs['gmp'],'gmp',tails=True)  # W2: every row field, the tail fields and max_abs of mp>0 rows included
    shutil.rmtree(d)
    return {**r,'quad_points':sum(x['quad']for x in outs['gmp']['rows']),'mp_points':sum(x['mp']for x in outs['gmp']['rows'])}

def bk8(td:Path,jobs:int,threads:int)->list:
    require(exe('decimal'),exe('gmp'),hint='make && make gmp')
    items=[];n=256
    for sector in ('free','power'):
        for L in (7,8):
            ids=heavy_and_random(sector,L,100,300,8812+L+(17 if sector=='power'else 0));root=stage(td/f'bk8_{sector}',sector,L,ids)
            net=td/f'bk8_{sector}{L}.bin';make_net(net,2,4*L-1,60,5150+L+(3 if sector=='power'else 0),n)
            for off in range(0,len(ids),25):items.append(dict(sector=sector,L=L,ids=ids[off:off+25],root=root,net=net,points=n))
    stats={};t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs)as pool:
        futures={pool.submit(bk8_item,td,it,threads):it for it in items}
        for k,fut in enumerate(concurrent.futures.as_completed(futures)):
            it=futures[fut];r=fut.result()
            s=stats.setdefault((it['sector'],it['L']),{'graphs':0,'rows':0,'mp_rows':0,'max':D(0),'max_abs':D(0),'tail_rows_exact':0,'tail':D(0),'tail_rel':D(0),'ties':0,'quad_points':0,'mp_points':0})
            s['graphs']+=len(it['ids']);s['rows']+=r['rows'];s['mp_rows']+=r['mp_rows'];s['max']=max(s['max'],D(r['max_normalized_difference_mp_rows']))
            s['max_abs']=max(s['max_abs'],D(r['max_abs_max_normalized_difference_mp_rows']));s['tail']=max(s['tail'],D(r['tail_max_normalized_difference_mp_rows']))
            s['tail_rows_exact']+=r['tail_rows_exact'];s['tail_rel']=max(s['tail_rel'],D(r['tail_max_relative_difference_mp_rows']));s['ties']+=r['tail_argmax_ties']
            s['quad_points']+=r['quad_points'];s['mp_points']+=r['mp_points']
            print(f'G-BK8 {k+1}/{len(items)} {time.time()-t0:.0f} s',flush=True)
    return [{'test':'G-BK8','sector':s,'L':L,'graphs':v['graphs'],'points_per_task':n,'replicates':2,'rows':v['rows'],'mp_rows':v['mp_rows'],
             'max_normalized_difference_mp_rows':str(v['max']),'max_abs_max_normalized_difference_mp_rows':str(v['max_abs']),'quad_points':v['quad_points'],'mp_points':v['mp_points'],
             'tail_rows_exact':v['tail_rows_exact'],'tail_max_normalized_difference_mp_rows':str(v['tail']),'tail_max_relative_difference_mp_rows':str(v['tail_rel']),
             'tail_argmax_ties':v['ties'],'row_rule':BK8_ROW_RULE,'tie_policy':TIE_POLICY,
             'rule':'decimal vs gmp: counters identical; values, max_abs and the tail fields exact if mp=0; values, max_abs, tail_top and tail_sum '
                    '<=1e-30 normalized if mp>0, tail widths equal, tail_argmax equal or a near tie (tie_policy); every row field covered (W2)'}
            for (s,L),v in sorted(stats.items())]

# ---------------------------------------------------------------- A-IN-6(b): the L=2 control
def l2_control(td:Path,base_seed:int,threads:int,reps:int=32,points:int=2**16,chunk:int=4096)->dict:
    require(exe('decimal'),exe('gmp'),hint='make && make gmp')
    B2=[D(x)for x in load(ROOT/'inputs/two_loop.json')['B2']]
    if len(B2)!=7:raise AssertionError('two_loop.json must hold 7 B2 strings')
    header=L2_GRAPH.read_text().split()
    wa,wb=Fraction(header[3]),Fraction(header[4])
    if wa/wb!=6:raise AssertionError(f'L=2 graph weights wa={header[3]}, wb={header[4]}: wa/wb != 6')
    root=stage(td/'l2','free',2,[0]);bound=D(2)**-60;out={}
    for b in BACKENDS:
        camp={}
        for c,rate in (('a',.8),('b',.9)):
            h=lambda role:int.from_bytes(hashlib.sha256(f'c8-d2|l2-control|{base_seed}|{c}|{role}'.encode()).digest()[:8],'little')>>1
            net=td/f'l2_{c}.bin'
            if not net.exists():make_net(net,reps,7,60,h('net'),points)
            tasks=td/'l2_tasks';tasks.write_text(tasks_text(8,2,task_rows([0],reps,points,chunk)))
            d=fresh_output(native_cmd(exe(b),root,GAMMA8,net,tasks,td/'l2.json',h('native'),0,rate,threads),td/'l2.json')
            per={r:[[D(0)]*7,[D(0)]*7,[D(0)]*7]for r in range(reps)}  # sums of b_j, of c_j and of |b_j| over a replicate's rows
            worst_row=D(0)
            for row in d['rows']:
                v=[D(x)for x in row['values']]
                if len(v)!=14:raise AssertionError('L=2 at order 8 must write 14 values (K=6)')
                for j in range(7):
                    bj,cj=v[j],v[7+j];gap=abs(bj-6*cj)
                    if gap>bound*abs(bj):raise AssertionError(f'{b} {c}: row {row["uid"]} slot {j}: |b-6c| = {gap} > 2^-60 |b|')
                    worst_row=max(worst_row,gap/abs(bj)if bj else D(0))
                    s=per[row['rep']];s[0][j]+=bj;s[1][j]+=cj;s[2][j]+=abs(bj)
            worst_rep=D(0)
            for r,s in per.items():
                for j in range(7):
                    gap=abs(s[0][j]-6*s[1][j])
                    if gap>bound*s[2][j]:raise AssertionError(f'{b} {c}: replicate {r} slot {j}: |sum b - 6 sum c| > 2^-60 sum |b|')
                    worst_rep=max(worst_rep,gap/s[2][j])
            means=[];ses=[]
            for j in range(7):
                xs=[per[r][0][j]for r in range(reps)];m=sum(xs)/reps;var=sum((x-m)**2 for x in xs)/(reps-1)
                means.append(m);ses.append((var/reps).sqrt())
            camp[c]={'rate':rate,'native_seed':h('native'),'net_seed':h('net'),'means':means,'se':ses,'worst_row_relative_gap':worst_row,'worst_replicate_relative_gap':worst_rep,
                     'quad':sum(r['quad']for r in d['rows']),'mp':sum(r['mp']for r in d['rows'])}
        slots=[]
        for j in range(7):
            a,bb=camp['a'],camp['b'];m=(a['means'][j]+bb['means'][j])/2;se=(a['se'][j]**2+bb['se'][j]**2).sqrt()/2
            pulls={c:(camp[c]['means'][j]-B2[j])/camp[c]['se'][j]for c in('a','b')};pulls['combined']=(m-B2[j])/se
            slots.append({'j':j,'B2':str(B2[j]),**{f'mean_{c}':str(camp[c]['means'][j])for c in('a','b')},'mean_combined':str(m),
                          **{f'se_{c}':str(camp[c]['se'][j])for c in('a','b')},'se_combined':str(se),'pulls':{k:float(v)for k,v in pulls.items()}})
            bad={k:float(v)for k,v in pulls.items()if abs(v)>4}
            if bad:raise AssertionError(f'{b}: L=2 control slot {j}: |pull| > 4: {bad}')
        out[b]={'slots':slots,'campaigns':{c:{k:(str(v)if isinstance(v,D)else v)for k,v in camp[c].items()if k not in('means','se')}for c in camp}}
    return {'test':'l2_control','status':'passed','base_seed':base_seed,'replicates':reps,'points':points,'chunk':chunk,'order':8,'K':6,'graph':str(L2_GRAPH.relative_to(ROOT)),
            'weights':{'wa':header[3],'wb':header[4],'wa_over_wb':'6 (exact Fractions)'},'rounding_bound':'2^-60 |b_j| per row and per replicate sum (R08)','backends':out}

# ---------------------------------------------------------------- A-RPL-7 machinery: G-L8SELF
def l8self_sample()->dict:
    return {'free':heavy_and_random('free',8,100,1500,8813),'power':heavy_and_random('power',8,100,300,8814)}

def l8self(td:Path,base:Path,jobs:int,threads:int)->list:
    require(exe('decimal'),exe('gmp'),*(base/f'c8d2_{b}'for b in BACKENDS),hint='make && make gmp; the baseline directory holds c8d2_decimal and c8d2_gmp')
    items=[];n=512;sample=l8self_sample()
    for sector,ids in sample.items():
        root=stage(td/f'self_{sector}',sector,8,ids);net=td/f'self_{sector}.bin';make_net(net,2,31,60,7702+(1 if sector=='power'else 0),n)
        for off in range(0,len(ids),25):items.append(dict(sector=sector,ids=ids[off:off+25],root=root,net=net))
    def one(it):
        d=Path(tempfile.mkdtemp(prefix='self_',dir=td));tasks=d/'tasks';tasks.write_text(tasks_text(8,8,task_rows(it['ids'],2,n)));res={}
        for b in BACKENDS:
            x=fresh_output(native_cmd(base/f'c8d2_{b}',it['root'],GAMMA8,it['net'],tasks,d/'base.json',threads=threads),d/'base.json')
            y=fresh_output(native_cmd(exe(b),it['root'],GAMMA8,it['net'],tasks,d/'new.json',threads=threads),d/'new.json')
            if [scientific(r)for r in x['rows']]!=[scientific(r)for r in y['rows']]:raise AssertionError(f'G-L8SELF {b} {it["sector"]}: rows differ from the baseline')
            res[b]=(len(y['rows']),sum(r['quad']for r in y['rows']),sum(r['mp']for r in y['rows']))
        shutil.rmtree(d);return res
    stats={};t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs)as pool:
        futures={pool.submit(one,it):it for it in items}
        for k,fut in enumerate(concurrent.futures.as_completed(futures)):
            it=futures[fut]
            for b,(rows,q,m)in fut.result().items():
                s=stats.setdefault((it['sector'],b),[0,0,0,0]);s[0]+=len(it['ids']);s[1]+=rows;s[2]+=q;s[3]+=m
            print(f'G-L8SELF {k+1}/{len(items)} {time.time()-t0:.0f} s',flush=True)
    return [{'test':'G-L8SELF','sector':s,'backend':b,'graphs':v[0]//1,'rows':v[1],'quad_points':v[2],'mp_points':v[3],'points_per_task':n,'replicates':2,
             'baseline':{bb:digest(base/f'c8d2_{bb}')for bb in BACKENDS},'candidate':{bb:digest(exe(bb))for bb in BACKENDS},'rule':'every scientific field exact'}
            for (s,b),v in sorted(stats.items())]

# ---------------------------------------------------------------- acceptance coverage of a record (W1/W22's class)
DEFAULT_PARTS=('describe','bad_inputs','replay','invariance','inspector','class_b','diagnostics')
GATES=('J-VAL-1','J-VAL-2','G-BK8','G-L8SELF','A-IN-6b')
def _tests(rec,name)->list:return [t for t in (rec.get('tests')or[])if isinstance(t,dict)and t.get('test')==name]

def coverage(rec:dict,gate:str,row_rule:bool=True)->dict:
    """Stage-6 fix round 4 (W1/W22's class, S6A4-01's "consumers independently validate coverage"): whether a validate.py
    record is acceptance evidence for one gate, recomputed from its tests. A record's "status":"passed" says only that
    every test it executed passed; --only, --bk8, --l2-control and --l8self choose what it executes.
      J-VAL-2   (A-RPL-1/2/3 full, A-RPL-6 chunks, A-KER): --full and every default part executed; replay_summary over
                the L=2 graph and every L3-L7 kernel of inputs/inventory.json; one replay_all_kernels group per (sector,
                L) at rate .8 layout 0 and the five other (rate, layout) configurations at L7, each over every kernel of
                its (sector, L) with G-C7 and G-JET for both backends (and G-REF at .8/0) on 2 rows per kernel; the 24
                random_access_chunks of both backends, sectors, L7/L8 and layouts 0/1/2, thread identical; describe,
                bad_inputs, class_b and the inspector tests passed; the diagnostic builds passed, not skipped.
      J-VAL-1   the same without --full: the replay_subset groups over replay_selection's kernels (the first 8 and the
                8 heaviest per (sector, L)).
      G-BK8     (A-RPL-4): the four (sector, L) of free/power x L7/L8, 400 kernels and 800 rows each, 256 points x 2
                replicates; with row_rule, the W2 row rule (row_rule BK8_ROW_RULE, max_abs and tail differences of mp>0
                rows within GMP_MP_TOLERANCE); row_rule=False only for the summaries of records made before W2.
      G-L8SELF  (A-RPL-7): free and power x both backends, the L8 sweep sample (1,600 and 400 kernels), 2 rows per
                kernel, 512 points; baseline and candidate digests.
      A-IN-6b   the L=2 control: both backends, 32 replicates x 2^16 points, order 8, 7 slots per backend.
    {'gate', 'complete': bool, 'why': [...]}."""
    why=[];rec=rec if isinstance(rec,dict)else{}
    if gate not in GATES:raise ValueError(f'unknown gate {gate!r}; the gates are {GATES}')
    if rec.get('status')!='passed':why.append(f'status {rec.get("status")!r}')
    ran=set(rec.get('executed')or rec.get('parts')or[])
    if gate in('J-VAL-1','J-VAL-2'):
        full=gate=='J-VAL-2'
        if rec.get('full')is not full:why.append(f'full {rec.get("full")!r}, not {full} (J-VAL-2 is the --full run)')
        if not set(DEFAULT_PARTS)<=ran or not set(DEFAULT_PARTS)<=set(rec.get('parts')or[]):why.append(f'parts executed {sorted(ran)}, not every default part {list(DEFAULT_PARTS)} (--only)')
        groups=[('free',2)]+[(s,L)for s in('free','power')for L in range(3,8)]
        count=lambda s,L:len(replay_selection(s,L,full))
        rs=_tests(rec,'replay_summary');want=sum(count(s,L)for s,L in groups)
        if len(rs)!=1 or rs[0].get('status')!='passed'or rs[0].get('full')is not full or rs[0].get('kernels')!=want:
            why.append(f'replay_summary {[(x.get("status"),x.get("full"),x.get("kernels"))for x in rs]}, not one {"full "if full else""}summary of {want} kernels')
        rk={(t.get('sector'),t.get('L'),t.get('rate'),t.get('layout')):t for t in _tests(rec,'replay_all_kernels'if full else'replay_subset')}
        need=[(s,L,.8,0)for s,L in groups]+[(s,7,r,l)for s in('free','power')for r in(.8,.9)for l in(0,1,2)if(r,l)!=(.8,0)]
        if sorted(rk,key=str)!=sorted(need,key=str):why.append(f'replay groups {sorted(set(map(str,rk))^set(map(str,need)))[:6]} missing or extra')
        for k in need:
            t=rk.get(k)
            if t is None:continue
            gates=t.get('gates')or{};g=count(k[0],k[1]);want_g={f'{x}/{b}'for x in(('G-REF','G-C7','G-JET')if k[2:]==(.8,0)else('G-C7','G-JET'))for b in BACKENDS}
            if t.get('graphs')!=g or set(gates)!=want_g or any((gates[x]or{}).get('rows')!=2*g for x in gates):
                why.append(f'replay {k}: {t.get("graphs")!r} kernels (want {g}), gates {sorted(gates)} (want {sorted(want_g)}), rows {sorted({(gates[x]or{}).get("rows")for x in gates},key=str)} (want {2*g})')
        ch={(t.get('backend'),t.get('sector'),t.get('L'),t.get('layout')):t for t in _tests(rec,'random_access_chunks')}
        needc=[(b,s,L,l)for b in BACKENDS for s in('free','power')for L in(7,8)for l in(0,1,2)]
        if sorted(ch,key=str)!=sorted(needc,key=str)or any(ch[k].get('thread_identical')is not True for k in ch):why.append(f'random_access_chunks {len(ch)}, not the {len(needc)} thread-identical ones')
        for name in ('describe','bad_inputs','class_b_tail_fields','diagnostic_builds'):
            x=_tests(rec,name)
            if len(x)!=1 or x[0].get('status')!='passed':why.append(f'{name}: {[y.get("status")for y in x]}, not passed (a skipped part is no evidence)')
        if not (_tests(rec,'inspector_execution_order')or _tests(rec,'inspector_order_key'))or any(t.get('status')!='passed'for n in('inspector_execution_order','inspector_order_key','inspector_private_tempdir')for t in _tests(rec,n)):
            why.append('the inspector tests did not pass')
    elif gate=='G-BK8':
        if rec.get('bk8')is not True or (rec.get('executed')is not None and 'bk8'not in ran):why.append('--bk8 was not run')
        t={(x.get('sector'),x.get('L')):x for x in _tests(rec,'G-BK8')}
        need=[(s,L)for s in('free','power')for L in(7,8)]
        if sorted(t,key=str)!=sorted(need,key=str):why.append(f'G-BK8 blocks {sorted(t,key=str)}, not {need}')
        for k in need:
            x=t.get(k)
            if x is None:continue
            if (x.get('graphs'),x.get('rows'),x.get('points_per_task'),x.get('replicates'))!=(400,800,256,2):why.append(f'G-BK8 {k}: {x.get("graphs")!r} kernels, {x.get("rows")!r} rows, {x.get("points_per_task")!r} x {x.get("replicates")!r} points, not 400, 800, 256 x 2')
            try:big=D(x['max_normalized_difference_mp_rows'])>GMP_MP_TOLERANCE
            except (KeyError,TypeError,ArithmeticError):big=True
            if big:why.append(f'G-BK8 {k}: max_normalized_difference_mp_rows {x.get("max_normalized_difference_mp_rows")!r}')
            if row_rule:
                if x.get('row_rule')!=BK8_ROW_RULE:why.append(f'G-BK8 {k}: row rule {x.get("row_rule")!r}, not {BK8_ROW_RULE} (a record made before W2 compares no max_abs or tail fields of mp>0 rows)')
                else:
                    try:big=[f for f in('max_abs_max_normalized_difference_mp_rows','tail_max_normalized_difference_mp_rows')if D(x[f])>GMP_MP_TOLERANCE]+([]if isinstance(x.get('tail_argmax_ties'),int)else['tail_argmax_ties'])
                    except (KeyError,TypeError,ArithmeticError)as e:big=[str(e)]
                    if big:why.append(f'G-BK8 {k}: {big}')
    elif gate=='G-L8SELF':
        if rec.get('l8self')in(None,'')or (rec.get('executed')is not None and 'l8self'not in ran):why.append('--l8self was not run')
        t={(x.get('sector'),x.get('backend')):x for x in _tests(rec,'G-L8SELF')};size={s:len(v)for s,v in l8self_sample().items()}
        need=[(s,b)for s in('free','power')for b in BACKENDS]
        if sorted(t,key=str)!=sorted(need,key=str):why.append(f'G-L8SELF blocks {sorted(t,key=str)}, not {need}')
        for k in need:
            x=t.get(k)
            if x is not None and ((x.get('graphs'),x.get('rows'),x.get('points_per_task'),x.get('replicates'))!=(size[k[0]],2*size[k[0]],512,2)or not x.get('baseline')or not x.get('candidate')):
                why.append(f'G-L8SELF {k}: {x.get("graphs")!r} kernels, {x.get("rows")!r} rows, {x.get("points_per_task")!r} points, not {size[k[0]]}, {2*size[k[0]]}, 512 (or no digests)')
    else:
        t=_tests(rec,'l2_control');x=t[0]if len(t)==1 else{}
        if rec.get('l2_control')is not True or len(t)!=1:why.append('--l2-control was not run (once)')
        elif (x.get('status'),x.get('replicates'),x.get('points'),x.get('order'),sorted(x.get('backends')or{}))!=('passed',32,2**16,8,sorted(BACKENDS))or \
             any(len((v or{}).get('slots')or[])!=7 for v in (x.get('backends')or{}).values()):
            why.append(f'l2_control: {x.get("replicates")!r} x {x.get("points")!r} points, order {x.get("order")!r}, backends {sorted(x.get("backends")or{})}, not 32 x 65536, 8, both, 7 slots')
    return {'gate':gate,'complete':not why,'why':why}

def check(path:Path,gate:str)->int:
    """--check RECORD --gate NAME: 0 for a record that is acceptance evidence of that gate (coverage), 1 otherwise."""
    rec=json.loads(Path(path).read_text());cov=coverage(rec,gate)
    print(json.dumps({'record':str(path),'status':rec.get('status'),'acceptance':cov['complete'],'coverage':cov},indent=1));return 0 if cov['complete']else 1

# ---------------------------------------------------------------- main
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--full',action='store_true',help='replay every L3-L7 kernel (J-VAL-2)')
    p.add_argument('--only',choices=('describe','bad_inputs','replay','invariance','inspector','class_b','diagnostics','none'),nargs='*',help='run only these default parts')
    p.add_argument('--bk8',action='store_true');p.add_argument('--l2-control',action='store_true');p.add_argument('--l2-seed',type=int,help='base seed of the L=2 control (default: fresh)')
    p.add_argument('--l8self',type=Path,metavar='DIR',help='baseline directory with c8d2_decimal and c8d2_gmp')
    p.add_argument('--jobs',type=int,default=max(1,min(32,(os.cpu_count()or 2)//4)));p.add_argument('--threads',type=int,default=4)
    p.add_argument('--output',type=Path,help='write the JSON record here (must not exist)')
    p.add_argument('--check',type=Path,metavar='RECORD',help='check an existing record: exit 0 only if it is acceptance evidence of --gate')
    p.add_argument('--gate',choices=GATES,help='with --check: the gate (J-VAL-2, G-BK8, G-L8SELF, A-IN-6b)')
    a=p.parse_args()
    if a.check or a.gate:
        if not (a.check and a.gate):p.error('--check and --gate go together')
        sys.exit(check(a.check,a.gate))
    parts=set(a.only)if a.only is not None else {'describe','bad_inputs','replay','invariance','inspector','class_b','diagnostics'}
    if not parts-{'none'}and not(a.bk8 or a.l2_control or a.l8self):  # T-03: a run that selects nothing is no evidence
        p.error('no test selected (--only names no default part, and none of --bk8, --l2-control, --l8self is given)')
    if a.output and a.output.exists():raise SystemExit(f'{a.output} exists')
    backends=[b for b in BACKENDS if exe(b).exists()]
    if not backends:raise SystemExit('build bin/c8d2_decimal (make) first')
    tests=[];t0=time.time()
    with tempfile.TemporaryDirectory(prefix='c8d2_validate_')as td:
        td=Path(td)
        def step(name,fn):
            s=time.time();r=fn();r=r if isinstance(r,list)else[r];tests.extend(r);executed.append(name);print(f'{name}: passed in {time.time()-s:.0f} s',flush=True)
        executed=[]
        if 'describe'in parts:step('describe',lambda:describe(backends))
        if 'bad_inputs'in parts:step('bad_inputs',lambda:bad_inputs(td,backends))
        if 'replay'in parts:step('replay',lambda:replay(td,a.full,a.jobs,a.threads))
        if 'invariance'in parts:step('invariance',lambda:invariance(td,backends))
        if 'inspector'in parts:step('inspector',lambda:[inspector_tempdir(td),inspector_order(td)])
        if 'class_b'in parts:step('class_b',lambda:class_b(td,backends))
        if 'diagnostics'in parts:step('diagnostics',lambda:diagnostics(td))
        if a.bk8:step('bk8',lambda:bk8(td,a.jobs,a.threads))
        if a.l2_control:
            seed=a.l2_seed if a.l2_seed is not None else secrets.randbits(63)
            print(f'L=2 control base seed {seed} (register it in the forbidden-seed log)',flush=True)
            step('l2_control',lambda:l2_control(td,seed,a.threads))
        if a.l8self:step('l8self',lambda:l8self(td,a.l8self.resolve(),a.jobs,a.threads))
    if not executed:raise SystemExit('validate: no test executed')
    rec={'status':'passed','parts':sorted(parts),'executed':executed,'full':a.full,'bk8':a.bk8,'l2_control':a.l2_control,'l8self':str(a.l8self)if a.l8self else None,
         'tests':tests,'wall_seconds':round(time.time()-t0,1),'environment':environment_record()}
    # the gates this record is acceptance evidence for (coverage); "status" says only that every executed test passed
    rec['acceptance']={g:coverage(json.loads(json.dumps(rec,default=str)),g)['complete']for g in GATES}
    if a.output:dump(a.output,rec)
    print(json.dumps(rec,indent=1,default=str)[:20000])

if __name__=='__main__':main()
