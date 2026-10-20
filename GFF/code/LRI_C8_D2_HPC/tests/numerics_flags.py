#!/usr/bin/env python3
"""A-FLAG-3 F-gates of an opt-in numerics profile (Stage 4c; PLAN A-FLAG-1..5, J-FLAG-<profile>): the profile's
executable bin/c8d2_gmp_<p> (`make gmp NUMERICS=<p>`) against the exact path bin/c8d2_gmp, on a cluster node.

  numerics_flags.py --profile P --output DIR [--f1-baseline DIR0] [options]   the gates of profile P (dd, mp256, exp1,
                                                                               dd+mp256+exp1, ...)
  numerics_flags.py --self-test --output DIR [options]       the exact binary as its own "profile": F2 must give
                                                              dC8 = 0 exactly, every row and point identical
  numerics_flags.py --f1-baseline-only --output DIR [options]  only the F1 exact baseline (reused by later runs)

F1  Accuracy on the A-RPL-5 point set (tests/forced_tiers.py: per sector 200 L7 graphs x 256 points and 400 L8 graphs x
    64 points, the heaviest included, rate .8, the nets and seeds of forced_tiers.py; the points per graph double until
    the exact path has >= 10^4 binary128-accepted and >= 10^3 MP points per sector). tests/numerics_f1.cpp, compiled
    with the build record's command of the executable under test, evaluates every point with that build's evaluate().
    The exact baseline (write mode, bin/c8d2_gmp) also computes an independent 450-digit value per point and stores it
    with the exact path's own value (DIR/f1_baseline, reusable with --f1-baseline). The profile (read mode) must give
    relative error <= 1e-6 against the 450-digit value at every point (the exact path's bound), the same points
    (hash of the log-coordinates), no sample()/evaluate() level mismatch and no *_violations counter of the profile's
    own C8_NX_F1_CHECKS. The per-tier distributions of the relative and the err-scaled error are reported next to the
    exact path's, with the paired difference to the exact value and the tier transitions.
    Coverage (X1, Stage-6 fix round 1): F1 passes only with the full A-RPL-5 coverage, for a fresh and for a reused
    baseline alike (f1_coverage, recorded as F1.coverage): scale 1, both sectors, per (sector, L) the prescribed graphs
    (f1_ids) and points per graph (F1_SAMPLE x 2^doublings, contiguous ranges from 0), the exact path's binary128-accepted
    and MP counts per sector at least F1_NEED (recounted from the baseline's stats; a baseline whose doublings ran out
    first fails), and the profile evaluated every baseline point. --sectors other than free,power is a development
    option. A development run records the reduced coverage and is never "passed".
    Build binding (X2): the F1 tools must have exactly the kernel of the executables they stand for. The run copies the
    sources (src/ and tests/numerics_f1.cpp, the package's relative layout) into one read-only snapshot, rebuilds each
    executable there with its build record's command and requires the rebuild to be byte-identical (sha256): a stale
    executable (sources changed since it was built), another toolchain or other libraries are refused before anything
    is written. The F1 tools are compiled from the same snapshot with the same commands. The record carries the snapshot
    (every file's sha256) and the reproduction of each executable (build_binding), the snapshot of the profile's tool
    (F1.tool_snapshot_sha256) and the binding of the baseline's exact tool (F1.baseline_binding; a reused baseline
    without one, or whose binding names another source snapshot than this run's, is refused). Y1 (Stage-6 fix round 2):
    each F1 tool must also run with the libgmp of the executable it stands for: the library the compiled tool resolves
    here, and the one the executable resolves here, must have the sha256 its build record names (gmp_library), else
    the run stops before the tool evaluates a point (F1.tool_gmp_library, and tool_gmp_library in baseline.json).
    Z19 (Stage-6 fix round 3): a reused baseline (--f1-baseline) must name that library too: its tool_gmp_library must
    say match with the sha256 the exact executable's build record names (want, tool and worker_now), and the exact
    executable must resolve that library here now (build_record.check_linked); a baseline without tool_gmp_library
    (made before fix round 2), with another library, or an exact executable that now resolves another library is
    refused before anything is written (f1_baseline.reused_gmp_library records the check). The record also copies
    the baseline's tool_gmp_library and says whether the baseline was reused (f1_baseline.tool_gmp_library, .reused):
    design.check_gate requires both, the profile's F1.tool_gmp_library and, for a reused baseline, the reuse check
    (Z19 downstream, integration of fix round 3).
F2  Paired mini-campaign on identical streams: every graph of every (campaign, sector, L) in --f2-loops (default
    3..8: all L7 and L8 kernels, and the cheap L3-L6 ones so that the full C8 can be assembled), --f2-replicates (4)
    x --f2-points (256) points, campaign a at rate .8 and b at .9, native seeds and nets derived from --seed. Each block
    of <= 256 tasks runs with the exact and the profile binary back to back on the same lane (alternating which goes
    first). dC8 = sum over (campaign, sector, L, graph) of 1/2 J8[L] . (profile - exact jets), J8 the C8 row of the
    vendored assembly's complex-step Jacobian (tools/assemble.jacobians, the module design.py uses) at the exact run's
    loop means; SE_d from the replicate scatter (sum over campaigns of Var_rep/(4 R)). Gate: |dC8| + 3 SE_d <= 0.062 in
    total and per (sector, L >= 7); per-task normalized differences max_j |dv_j|/max(1, |v_j|) <= 1e-9. When a bound
    fails only because 3 SE_d is too large (|dC8| < 0.062), the replicates double (up to --f2-max-doublings). Reported:
    per (campaign, sector, L) and total, the per-task difference distribution and quantiles, the nonlinear dC8 of the
    full assembly at the two means, and the projection |dC8| + 3 SE_d sqrt(n_mini/n_prod) to production point counts.
F3  Promotion fractions per tier and their change: per (campaign, sector, L) from F2's row counters (quad = promoted
    beyond the first pass, mp = MP tier), and per finer tier (long double, dd, binary128, mp256, mp350) from F1.
F4  Speed per (sector, L=8) on the L8 sweep sample (tests/validate.py l8self_sample: 2,000 graphs, 2 x 512 points,
    G-L8SELF's nets, seed 7738251, rate .8): --f4-repeats (3) interleaved runs of each binary on one node in --shape
    lanes (LPT on the J-SWEEP-1 cost model, blocks <= 256 tasks), the median lane-thread seconds per sector and the
    speedup exact/profile. Every repeat of one binary must give the same rows. F2's per-(campaign, sector, L) task
    seconds give an indicative (single, block-interleaved) ratio for every L.
F5  Thread identity of the profile binary: tests/thread_identity.py's blocks (L8 free and power, 64 tasks x 256 points)
    at --f5-threads and as --f5-lanes lanes of --f5-lane-threads threads, each run in an environment without OpenMP
    controls (OMP_DYNAMIC=false) and its observed OpenMP team required to be the requested one (X3; the record's
    F5.team_sizes_verified and F5.teams). F2 and F4 run the workers in the same sanitized environment.

Seeds (PLAN D9: every campaign this plan executes is in the forbidden-seed log). Before F2 starts, the run registers
its F2 campaign in the log given by --seeds-log (default $C8_SEEDS; a run with F2 and no log is refused before
anything is written): the base seed and, for every (campaign, sector, L) of loops 3..8, the derived native and net
seeds, each under a fixed label ("J-FLAG F2 <role> seed <group> of base <seed> (tests/numerics_flags.py)"). The gates
reuse one base seed on purpose (every profile is paired against the exact path on the same streams), so entries of
the same base with the same labels are left as they are ("present"); a seed already logged under another source, an
archived C7(2) seed, or a derived C8 group seed of a logged campaign is refused (exit) before any output exists. The
check and the append are one transaction under the log's lock (tools/seeds.py reserve, W20, Stage-6 fix round 4), so no
production plan can register one of these seeds in between. The record says what was added (f2_seeds).
Inputs (W18, Stage-6 fix round 4): the record carries the authenticated input set of the run (inputs: the sha256 of
inputs/manifest.json, every listed input, pack and vendored pin hashed against it before anything is built or
written, and again at the end, verified_at_end; a change during the run fails the record). design.check_gate requires
it complete and equal to the pilot's (freeze) or the plan's inputs manifest. A fresh F1 baseline records the same
identity (baseline.json inputs) and a reused one must carry the run's, else it is refused before anything is written.
--self-test uses bin/c8d2_gmp as the profile: F1 paired identical at every point, F2 dC8 = 0 and every task difference
0 exactly, F3 changes 0, F4 rows identical between the two "binaries". The same strict identity is required of a
profile executable whose every profile is still a stub (--describe numerics_params "stub":true: the Stage-4c
framework's no-op headers), which proves the hook plumbing computes the exact path. Development options (--f1-scale, --f2-graphs,
--f4-sample, fewer F5 threads, --sectors) make a run a development run: the record says so and never says "passed".
Records go only to --output DIR (which must not exist): DIR/numerics_flags.json, DIR/f1/, DIR/f2/ (per-row CSV),
DIR/f4/, DIR/f5/ and DIR/f1_baseline/ when computed here. Exit 0 when every gate of the run passed (or, for a
development run, would have passed), 1 otherwise.
"""
from __future__ import annotations
import argparse,concurrent.futures,csv,gzip,hashlib,json,math,os,queue,shutil,statistics,subprocess,sys,tempfile,threading,time
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from common import digest,dump,environment_record,load,numerics_name
import validate as V

SCHEMA='c8-d2-numerics-flags-1';BASELINE_SCHEMA='c8-d2-numerics-f1-baseline-1';BINDING_SCHEMA='c8-d2-build-binding-1'
WORKER_SOURCE='src/c8d2_integrate.cpp';F1_SOURCE='tests/numerics_f1.cpp'   # relative: the Makefile's spelling (X2)
BOUND_DC8=0.062                 # 1% of the SE at the tightest target (1.35e-4 x |C8| ~ 4.6e4), A-FLAG-3 (F2)
BOUND_TASK=D('1e-9')            # per-task normalized difference (F2)
BOUND_F1=1e-6                   # relative error of an accepted value against 450 digits (F1; the exact path's bound)
F1_SEED=7011                    # tests/forced_tiers.py's native seed
F1_SAMPLE={7:(50,150,256),8:(100,300,64)}   # tests/forced_tiers.py's SAMPLE: L -> (heaviest, random, points per graph)
F1_NEED=(10_000,1_000)          # binary128-accepted and MP points per sector (A-RPL-5)
RATES={'a':'.8','b':'.9'};NET_BITS={'a':52,'b':60};CAMPAIGNS=('a','b');SECTORS=('free','power')
TIER_NAMES=('long_double','double_double','binary128','mp256','mp350')
COST_MODEL=ROOT/'benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json'
BLOCK_TASKS=256
PROJECT_POINTS=(32768,262144,2097152)   # production points per graph and campaign for F2's projection

def log(msg:str)->None:print(f'[{time.strftime("%H:%M:%S")}] {msg}',flush=True)

# ---------------------------------------------------------------- executables and their build records
def describe(exe:Path)->dict:
    cp=subprocess.run([str(exe),'--describe'],capture_output=True,text=True,timeout=120)
    if cp.returncode:raise SystemExit(f'{exe} --describe failed: {cp.stderr[-500:]}')
    return json.loads(cp.stdout)

def build_record(exe:Path)->dict:
    br=exe.with_name(exe.name+'.build.json')
    if not br.is_file():raise SystemExit(f'{exe}: no build record {br.name}; build it with make (make gmp NUMERICS=<p>)')
    rec=load(br)
    if rec.get('executable_sha256')!=digest(exe):raise SystemExit(f'{br} describes another executable than {exe}; rebuild (make -B)')
    return rec

INPUTS_SCHEMA='c8-d2-gate-inputs-1'
def input_identity()->dict:
    """W18 (Stage-6 fix round 4, S6H4-01): the authenticated input set of the run. Every scientific input the gate reads
    is under the package's inputs/ and vendor/: the G-file payloads (V.stage: inputs/packs at their inventory.json
    sha256), the gamma table (V.GAMMA8), the two-loop data (assemble.two_loop, inputs/two_loop.json) and the vendored
    assembly (assemble.vendored, F2's Jacobians and coefficients); inputs/manifest.json pins all of them (gamma,
    inventory, the twelve packs, two_loop, the vendored assembly's HANDOFF and files). The manifest is read once, its
    sha256 taken from those bytes, and tools/prepare_inputs.py verify hashes every listed file against it (a mismatch
    stops the run, SystemExit, before anything is written). A missing L8 pack (a machine without `make inputs-l8`, such
    as the Mac) is recorded in skipped and makes the identity incomplete: design.check_gate refuses an incomplete one.
    The identity is the manifest's sha256, the same inputs_manifest_sha256 every campaign and design bundle records."""
    import prepare_inputs as PI
    p=ROOT/'inputs';data=(p/'manifest.json').read_bytes();sha=hashlib.sha256(data).hexdigest()
    try:m=PI.verify(p,expected_manifest_sha256=sha,allow_no_l8=True)
    except (ValueError,OSError)as e:raise SystemExit(f'the gate\'s inputs do not verify against inputs/manifest.json ({e}); nothing written (W18)')
    skipped=sorted(n for n in PI.L8_PACKS if not (p/n).is_file())
    return {'schema':INPUTS_SCHEMA,'folder':'inputs','manifest_sha256':sha,'verified':True,'skipped':skipped,'complete':not skipped,
            'files':dict(sorted(m['sha256'].items())),'vendored_assembly_handoff_sha256':(m.get('vendored_assembly')or{}).get('handoff_sha256'),
            'vendored_assembly_files':dict(sorted(((m.get('vendored_assembly')or{}).get('files')or{}).items())),
            'verified_by':'tools/prepare_inputs.py verify(inputs/, the manifest bytes\' sha256): every listed input, the packs and the vendored pins hashed'}

def inputs_unchanged(start:dict)->dict:
    """W18: the input set verified again at the end of the run (same manifest bytes, every file at its pin): a change
    during the run fails the record (verdict inputs_unchanged)."""
    try:end=input_identity()
    except SystemExit as e:return {'unchanged':False,'why':str(e)}
    same=end['manifest_sha256']==start['manifest_sha256']and end['skipped']==start['skipped']
    return {'unchanged':same,'why':None if same else f'inputs manifest {end["manifest_sha256"][:12]}... at the end, {start["manifest_sha256"][:12]}... at the start'}

def identity(exe:Path,want:str)->dict:
    """sha256, --describe (a C8(2) gmp worker of numerics `want`, not a diagnostic build) and the build record."""
    d=describe(exe)
    if d.get('schema')!='c8-d2-build-1'or d.get('mp_backend')!='gmp350':raise SystemExit(f'{exe} is not a C8(2) gmp worker ({d.get("schema")}, {d.get("mp_backend")})')
    if d.get('diagnostic'):raise SystemExit(f'{exe} is a diagnostic build')
    if d.get('numerics')!=want:raise SystemExit(f'{exe} reports numerics {d.get("numerics")!r}, expected {want!r}')
    br=build_record(exe)
    stub=sorted(k for k,v in (d.get('numerics_params')or{}).items()if isinstance(v,dict)and v.get('stub'))
    return {'path':str(exe),'sha256':digest(exe),'describe':d,'build_record':br,'stub_profiles':stub}

def build_command(exe:Path,source:str,out:Path)->list[str]:
    """The compile command of exe's build record with `source` (a path relative to the snapshot) as the source and out
    as the output. The record must be a Makefile build: one source word, exactly src/c8d2_integrate.cpp, and one -o."""
    cmd=list(build_record(exe)['command'])
    src=[i for i,w in enumerate(cmd)if w.endswith('c8d2_integrate.cpp')]
    if len(src)!=1 or cmd[src[0]]!=WORKER_SOURCE or cmd.count('-o')!=1 or cmd.index('-o')+2>len(cmd):
        raise SystemExit(f'{exe}: unexpected build command {cmd} (a Makefile build of {WORKER_SOURCE}, relative, with one -o)')
    cmd[src[0]]=source;cmd[cmd.index('-o')+1]=str(out)
    return cmd

def tool_command(exe:Path,out:Path)->list[str]:
    """The F1 tool's command: exe's build-record command with tests/numerics_f1.cpp as the source (compiled in the
    snapshot, so the tool has exactly that executable's kernel: sources, macros, flags, libraries)."""
    return build_command(exe,F1_SOURCE,out)

def snapshot(dest:Path)->dict:
    """X2: one read-only copy of every source a worker or the F1 tool compiles from (src/, recursively, and
    tests/numerics_f1.cpp) in the package's relative layout, so that a build record's relative command compiles the
    same translation units there. {'files': {path: sha256}, 'sha256': the digest of that map}."""
    srcs=[f for f in sorted((ROOT/'src').rglob('*'))if f.is_file()and '__pycache__'not in f.parts and f.name!='.DS_Store']+[ROOT/F1_SOURCE]
    files={}
    for f in srcs:
        rel=f.relative_to(ROOT).as_posix();d=dest/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,d);d.chmod(0o444);files[rel]=digest(d)
    return {'files':files,'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}

def relative_of(exe:Path)->tuple[list[str],Path|None]:
    """W3's class (Stage-6 fix round 4, integration): (the relative paths that exe's build-record command, apart from its
    source and output, and the include environment of this process name, in order: build_record.relative_words and
    relative_env; the record's build_directory, None for a record written before fix round 4)."""
    import build_record as BR
    rec=build_record(exe);cmd=list(rec.get('command')or['']);drop={i for i,w in enumerate(cmd)if w==WORKER_SOURCE}
    if '-o'in cmd:o=cmd.index('-o');drop|={o,o+1}
    rel=BR.relative_words([w for i,w in enumerate(cmd)if i not in drop],BR.compiler_words(rec))
    rel+=[d for v in BR.relative_env(names=BR.list_env(cmd[0])).values()for d in v if d not in rel]
    return rel,BR.build_directory(rec)

def snapshot_levels(exes)->int:
    """W3's class: how many private parents the snapshot needs so that every relative word of the executables' build
    commands (relative_of) stays inside them (build_record.climb)."""
    import build_record as BR
    return max([BR.climb(r)for e in exes for r in relative_of(e)[0]]+[0])

def mirror_relative(exe:Path,snap:Path,top:Path)->dict:
    """W3's class (S6A4-03 in numerics_flags.py X2, Stage-6 fix round 4, integration): exe's build-record command and the F1
    tool's (the same words) run with the snapshot snap as their working directory, so each relative word (relative_of)
    must name there what it named in the record's build_directory B, where make compiled exe: it is mirrored into the
    snapshot (build_record.mirror: the first name that leaves the snapshot becomes a symlink to the same name under B;
    the snapshot's own src/ is never replaced; top is the private root the snapshot's parents lie in). Afterwards every
    word that names something under B must name the same file or directory from snap (a name already mirrored for
    another executable's build directory is refused). Refused (SystemExit), before anything is compiled: relative words
    in a record without build_directory (their meaning is unknown), a word that climbs above the private parents.
    Returns {'build_directory', 'relative_words', 'mirrored'}; words are never rewritten (a compiler embeds the include
    path it found, e.g. in __FILE__, so a rewritten word would change the bytes)."""
    import build_record as BR
    rel,B=relative_of(exe)
    if not rel:return {'build_directory':str(B)if B else None,'relative_words':[],'mirrored':[]}
    if B is None:raise SystemExit(f'{exe}: its build record names no build_directory (a record written before Stage-6 fix round 4) and its command or the '
                                  f'include environment holds relative paths {rel[:6]}, whose meaning is then unknown (W3): rebuild it with make')
    links=[];root=Path(os.path.realpath(snap))
    for r in rel:
        try:m=BR.mirror(snap,top,B,r)
        except BR.BindingRefused as e:raise SystemExit(f'{exe}: {e}')
        if m:links.append({'link':m,'word':r})
        here,there=Path(os.path.realpath(Path(snap)/r)),Path(os.path.realpath(B/r))
        if os.path.lexists(B/r)and here!=there and not (here.is_relative_to(root/'src')and Path(os.path.normpath(r)).parts[:1]==('src',)):
            raise SystemExit(f'{exe}: the relative word {r!r} names {here} from the source snapshot, not {there} as in its build directory {B} '
                             '(another executable\'s build directory claimed that name; W3): build both executables in one directory')
    return {'build_directory':str(B),'relative_words':rel,'mirrored':links}

def compile_in(snap:Path,cmd:list,what:str)->float:
    t0=time.time();cp=subprocess.run(cmd,cwd=snap,capture_output=True,text=True)
    if cp.returncode:raise SystemExit(f'compiling {what} failed ({" ".join(map(str,cmd))}):\n{cp.stderr[-3000:]}')
    return time.time()-t0

def bind(exe:Path,snap:Path,info:dict,td:Path,label:str,top:Path|None=None)->dict:
    """X2: exe rebuilt in the snapshot with its build record's command must be byte-identical (sha256) to exe, so the
    snapshot's sources, this compiler and these libraries are the ones that produced it; the F1 tool compiled from the
    same snapshot with the same command then has exactly exe's kernel. Refused (SystemExit): a build record pinning a
    src/numerics file at another sha256 than the snapshot's, a rebuild that fails or differs (a stale executable, built
    before the sources changed, or by another toolchain or from other sources). W3's class (fix round 4): the relative
    words of the command keep the meaning they had in the record's build_directory (mirror_relative; top: the private
    root of a nested snapshot, default snap itself)."""
    br=build_record(exe);want=digest(exe)
    pins=(br.get('numerics_sources')or{}).get('files')or{}
    stale=sorted(k for k,v in pins.items()if info['files'].get(k)!=v)
    if stale:raise SystemExit(f'{exe}: its build record pins {stale[0]} at another sha256 than the current sources: a stale executable; rebuild it with make')
    mr=mirror_relative(exe,snap,Path(top)if top else snap)  # W3's class: before anything is compiled
    out=td/f'reproduced_{label}';cmd=build_command(exe,WORKER_SOURCE,out);secs=compile_in(snap,cmd,f'the reproduction of {exe.name} (X2)')
    got=digest(out);out.unlink()
    if got!=want:raise SystemExit(f'{exe}: its build record\'s command on the current sources gives sha256 {got[:12]}..., not the executable\'s {want[:12]}...: the '
                                  'executable is stale (the sources changed since it was built) or was built by another toolchain or from other sources; rebuild it '
                                  'with make in this checkout and rerun (X2: the F1 tool must have exactly the kernel of the executable it stands for)')
    log(f'X2: {exe.name} reproduced byte for byte from the source snapshot {info["sha256"][:12]} in {secs:.0f} s')
    return {'executable':str(exe),'sha256':want,'reproduced_sha256':got,'reproduced':True,'snapshot_sha256':info['sha256'],
            'command':cmd[:cmd.index('-o')+1]+[f'<reproduced_{label}>']+cmd[cmd.index('-o')+2:],'seconds':round(secs,1),**mr}

def tool_library(exe:Path,tool:Path)->dict:
    """Y1: the F1 tool runs with exe's GMP: the libgmp the compiled tool resolves here and the one exe resolves here
    both have the sha256 exe's build record names (tools/build_record.py check_linked); SystemExit otherwise."""
    import build_record as BR
    want=(build_record(exe).get('gmp_library')or{}).get('sha256')
    if not want:raise SystemExit(f'{exe}: its build record names no libgmp sha256 (gmp_library; Y1): rebuild it with make where ldd runs')
    try:return BR.check_linked(tool,{'worker':str(exe),'gmp_library':{'sha256':want}})
    except BR.BindingRefused as e:raise SystemExit(f'the F1 tool of {exe.name}: {e}')

def reused_baseline_library(base:Path,B:dict,exact:Path)->dict:
    """Z19 (S6H3-01): a reused F1 baseline's exact tool ran with the libgmp the exact executable's build record names
    (baseline.json tool_gmp_library: match, and want, tool and worker_now all that sha256), and the exact executable
    resolves that library here now (its tool is not rebuilt when the baseline is reused, so compile_tool's check of it
    does not run). SystemExit otherwise; there is no compatibility path for a baseline without the field."""
    import build_record as BR
    want=(build_record(exact).get('gmp_library')or{}).get('sha256')
    if not want:raise SystemExit(f'{exact}: its build record names no libgmp sha256 (gmp_library; Y1): rebuild it with make where ldd runs')
    tl=B.get('tool_gmp_library')
    if not isinstance(tl,dict):raise SystemExit(f'{base}: the baseline records no tool_gmp_library (the libgmp its exact tool ran with; a baseline made before '
                                                'Stage-6 fix round 2): compute a fresh baseline (Z19)')
    seen={'want':tl.get('want_sha256'),'tool':(tl.get('tool')or{}).get('sha256'),'worker_now':(tl.get('worker_now')or{}).get('sha256')}
    if tl.get('match')is not True or set(seen.values())!={want}:
        raise SystemExit(f'{base}: the baseline\'s exact tool ran with libgmp {", ".join(f"{k} {str(v)[:12]}" for k,v in seen.items())} (match {tl.get("match")!r}), '
                         f'not the {want[:12]}... that {exact.name}\'s build record names: compute a fresh baseline (Z19)')
    try:now=BR.check_linked(exact,{'worker':str(exact),'gmp_library':{'sha256':want}},worker_now=False)
    except BR.BindingRefused as e:raise SystemExit(f'the exact executable {exact.name} does not run with its recorded libgmp here, so a baseline made with it '
                                                   f'cannot be reused (Z19): {e}')
    return {'want_sha256':want,'baseline_tool_gmp_library':seen,'exact_now':now['tool'],'match':True}

def compile_tool(exe:Path,out:Path,snap:Path)->tuple[list[str],dict]:
    """The F1 tool of exe, compiled in the snapshot (X2) with exe's build command, and its libgmp check (Y1)."""
    cmd=tool_command(exe,out);secs=compile_in(snap,cmd,'the F1 tool');lib=tool_library(exe,out)
    log(f'compiled {out.name} from {exe.name}\'s build command in the source snapshot in {secs:.0f} s (libgmp {lib["want_sha256"][:12]}...)');return cmd,lib

# ---------------------------------------------------------------- F1
def f1_sample(scale:float)->dict:
    if scale==1:return dict(F1_SAMPLE)
    return {L:(max(1,round(h*scale)),max(1,round(r*scale)),n)for L,(h,r,n)in F1_SAMPLE.items()}

def f1_ids(sector:str,L:int,heavy:int,rand:int)->list:
    return V.heavy_and_random(sector,L,heavy,rand,40417+L+(9 if sector=='power'else 0))

def f1_net_seed(sector:str,L:int)->int:return 30011+L+(9 if sector=='power'else 0)

def hist_add(a:dict,b:dict)->dict:
    out=dict(a)
    for k,v in b.items():out[k]=out.get(k,0)+v
    return out

def dmax(a:str|None,b:str|None)->str|None:
    if a is None:return b
    if b is None:return a
    return a if D(a)>=D(b)else b

def f1_merge(a:dict|None,b:dict)->dict:
    """Merge two numerics_f1 outputs (points, levels, tiers with histograms and maxima, paired, checks)."""
    if not a:return json.loads(json.dumps(b))
    out=json.loads(json.dumps(a))
    for k in ('points','level_mismatch','nonmoderate','nondirect'):out[k]=a[k]+b[k]
    out['level']=[x+y for x,y in zip(a['level'],b['level'])]
    for t in TIER_NAMES:
        x,y=out['tiers'][t],b['tiers'][t]
        for k in ('points','violations'):x[k]+=y[k]
        for k in ('max_relative_error','max_scaled_error'):x[k]=dmax(x[k],y[k])
        for k in ('hist_relative','hist_scaled'):x[k]=hist_add(x[k],y[k])
    if 'paired'in b:
        p=out.setdefault('paired',{'identical':0,'max_relative_difference':None,'hist_relative_difference':{},'transitions':{}});q=b['paired']
        p['identical']+=q['identical'];p['max_relative_difference']=dmax(p['max_relative_difference'],q['max_relative_difference'])
        p['hist_relative_difference']=hist_add(p['hist_relative_difference'],q['hist_relative_difference']);p['transitions']=hist_add(p['transitions'],q['transitions'])
    out['profile_checks']=hist_add(a.get('profile_checks',{}),b.get('profile_checks',{}))
    out['first_violations']=(a['first_violations']+b['first_violations'])[:20]
    out.pop('begin',None);out.pop('end',None)
    return out

def f1_verdict(stats:dict,self_test:bool=False)->dict:
    """The F1 gate on merged numerics_f1 read-mode stats."""
    viol=sum(stats['tiers'][t]['violations']for t in TIER_NAMES)
    checks={k:v for k,v in stats.get('profile_checks',{}).items()if k.endswith('_violations')and v}
    why=[]
    if viol:why.append(f'{viol} points with relative error > {BOUND_F1}')
    if stats['level_mismatch']:why.append(f'{stats["level_mismatch"]} sample()/evaluate() level mismatches')
    if checks:why.append(f'profile checks: {checks}')
    if self_test and stats.get('paired',{}).get('identical')!=stats['points']:why.append('self-test: not every point identical to the exact baseline')
    return {'passed':not why,'violations':viol,'failed_profile_checks':checks,'why':why}

def f1_coverage(B:dict,res:dict|None=None)->dict:
    """X1: the A-RPL-5 coverage of an F1 baseline (fresh or reused) and, with res (f1_profile's {sector: {L: result}}),
    of the profile pass over it. complete only with: scale 1, the prescribed sample and need, both sectors, per (sector,
    L) the prescribed graphs (f1_ids: the heaviest and the random ones), points per graph = F1_SAMPLE x 2^doublings
    in contiguous ranges from 0, the stored points = graphs x points per graph, per sector the exact path's
    binary128-accepted and MP counts (recounted from the stored stats) at least F1_NEED with need_met saying so, and
    (res) the profile's points equal to the baseline's in every (sector, L)."""
    why=[];secs={};B=B if isinstance(B,dict)else{}
    want_sample={str(L):{'heaviest':h,'random':r,'points':n}for L,(h,r,n)in F1_SAMPLE.items()};want_need={'binary128_accepted':F1_NEED[0],'mp_promoted':F1_NEED[1]}
    if B.get('scale')!=1:why.append(f'baseline scale {B.get("scale")!r}, not 1')
    if B.get('sample')!=want_sample:why.append(f'baseline sample {B.get("sample")!r}, not the prescribed {want_sample}')
    if B.get('need')!=want_need:why.append(f'baseline need {B.get("need")!r}, not {want_need}')
    sectors=B.get('sectors')if isinstance(B.get('sectors'),dict)else{}
    if set(sectors)!=set(SECTORS):why.append(f'baseline sectors {sorted(sectors)}, not {list(SECTORS)}')
    for s in SECTORS:
        sb=sectors.get(s)
        if not isinstance(sb,dict):continue
        dbl=sb.get('doublings');quad=mp=0;byL={}
        for L,(h,r,n)in F1_SAMPLE.items():
            x=(sb.get('by_L')or{}).get(str(L))
            if not isinstance(x,dict):why.append(f'{s} L{L}: not in the baseline');continue
            ids=x.get('graphs')or[];ppg=x.get('points_per_graph');st=x.get('stats')or{};pts=st.get('points');lev=st.get('level')or[0,0,0]
            if ids!=f1_ids(s,L,h,r):why.append(f'{s} L{L}: not the prescribed {h} heaviest + {r} random graphs')
            if not (isinstance(dbl,int)and dbl>=0 and ppg==n<<dbl):why.append(f'{s} L{L}: {ppg!r} points per graph, not {n} x 2^{dbl!r}')
            ends=[(q.get('begin'),q.get('end'))for q in x.get('ranges')or[]]
            if not (ends and ends[0][0]==0 and all(a[1]==b[0]for a,b in zip(ends,ends[1:]))and ends[-1][1]==ppg):why.append(f'{s} L{L}: point ranges {ends} do not cover [0, {ppg!r})')
            if not isinstance(ppg,int)or pts!=len(ids)*ppg:why.append(f'{s} L{L}: {pts!r} baseline points, not {len(ids)} graphs x {ppg!r}')
            quad+=int(lev[1]);mp+=int(lev[2])
            e={'graphs':len(ids),'points_per_graph':ppg,'points_baseline':pts}
            if res is not None:
                pp=((((res.get(s)or{}).get(str(L)))or{}).get('profile')or{}).get('points')
                e['points_profile']=pp
                if pp!=pts:why.append(f'{s} L{L}: the profile evaluated {pp!r} of the baseline\'s {pts!r} points')
            byL[str(L)]=e
        met=quad>=F1_NEED[0]and mp>=F1_NEED[1]
        if not met:why.append(f'{s}: {quad} binary128-accepted and {mp} MP points, below the need {F1_NEED[0]} and {F1_NEED[1]} (the doublings ran out)')
        if sb.get('need_met')is not met:why.append(f'{s}: need_met {sb.get("need_met")!r}, but the stored counts say {met}')
        secs[s]={'doublings':dbl,'binary128_accepted':quad,'mp_promoted':mp,'need_met':met,'by_L':byL}
    return {'complete':not why,'why':why,'scale':B.get('scale'),'sample':want_sample,'need':want_need,'sectors':secs,'profile_checked':res is not None}

def f1_tier_table(stats:dict)->dict:
    n=stats['points']or 1
    return {t:{'points':stats['tiers'][t]['points'],'fraction':stats['tiers'][t]['points']/n,'max_relative_error':stats['tiers'][t]['max_relative_error'],
               'violations':stats['tiers'][t]['violations']}for t in TIER_NAMES}

def f1_baseline(out:Path,exact:Path,threads:int,scale:float,max_doublings:int,sectors,td:Path,snap:Path,binding:dict,inputs:dict)->dict:
    """The exact path's F1 baseline: the A-RPL-5 point set, 450-digit references, the exact path's own values and its
    per-tier distributions; out/baseline.json pins every file. The tool is compiled in the source snapshot (X2) and
    baseline.json records the exact executable's binding to it (binding: bind()'s record of the exact executable) and
    the input set it was made from (inputs: input_identity(), W18; a reuse requires the same manifest)."""
    out.mkdir(parents=True);(out/'refs').mkdir();(out/'nets').mkdir()
    tool=td/'numerics_f1_exact';cmd,lib=compile_tool(exact,tool,snap);S=f1_sample(scale)
    rec={'schema':BASELINE_SCHEMA,'exact':{'path':str(exact),'sha256':digest(exact)},'tool_command':cmd,'tool_gmp_library':lib,'binding':binding,'inputs':inputs,
         'scale':scale,'seed':F1_SEED,'rate':'.8',
         'sample':{str(L):{'heaviest':h,'random':r,'points':n}for L,(h,r,n)in S.items()},'need':{'binary128_accepted':F1_NEED[0],'mp_promoted':F1_NEED[1]},'sectors':{}}
    t0=time.time()
    for sector in sectors:
        per={};points={L:S[L][2]for L in S};begin={L:0 for L in S};rounds=0
        for L,(h,r,n)in S.items():
            ids=f1_ids(sector,L,h,r);root=V.stage(td/'f1graphs'/sector,sector,L,ids);lst=td/f'f1_{sector}_L{L}.list'
            lst.write_text(''.join(f'{root}/L{L}/G{g}.txt\n'for g in ids));net=out/'nets'/f'{sector}_L{L}.bin'
            netrec=V.make_net(net,2,4*L-1,60,f1_net_seed(sector,L),n<<max_doublings)
            per[L]={'graphs':ids,'list':lst,'net':net,'net_record':netrec,'ranges':[],'stats':None}
        while True:
            for L in S:
                ref=out/'refs'/f'{sector}_L{L}_{begin[L]}_{points[L]}.txt';s=time.time()
                st=json.loads(V.run([tool,L,per[L]['list'],per[L]['net'],begin[L],points[L],F1_SEED,threads,ref,'write'],threads=threads).stdout)  # R1
                per[L]['ranges'].append({'begin':begin[L],'end':points[L],'ref':ref.name,'ref_sha256':digest(ref),'stats':st})
                per[L]['stats']=f1_merge(per[L]['stats'],st);log(f'F1 baseline {sector} L{L} [{begin[L]},{points[L]}) in {time.time()-s:.0f} s')
            quad=sum(per[L]['stats']['level'][1]for L in S);mp=sum(per[L]['stats']['level'][2]for L in S)
            if (quad>=F1_NEED[0]and mp>=F1_NEED[1])or scale!=1 or rounds>=max_doublings:break
            rounds+=1
            for L in S:begin[L]=points[L];points[L]*=2
        rec['sectors'][sector]={'doublings':rounds,'binary128_accepted':quad,'mp_promoted':mp,'need_met':quad>=F1_NEED[0]and mp>=F1_NEED[1],
                                'by_L':{str(L):{'graphs':per[L]['graphs'],'points_per_graph':points[L],'net':per[L]['net'].name,'net_sha256':digest(per[L]['net']),
                                                'net_record':per[L]['net_record'],'ranges':per[L]['ranges'],'stats':per[L]['stats']}for L in S}}
    rec['wall_seconds']=round(time.time()-t0,1);dump(out/'baseline.json',rec);return rec

def f1_profile(base_dir:Path,prof:Path,threads:int,td:Path,self_test:bool,out:Path,snap:Path,snap_sha:str)->dict:
    B=load(base_dir/'baseline.json')
    if B.get('schema')!=BASELINE_SCHEMA:raise SystemExit(f'{base_dir}/baseline.json is not an F1 baseline')
    tool=td/'numerics_f1_profile';cmd,lib=compile_tool(prof,tool,snap);out.mkdir(parents=True);res={};t0=time.time()
    for sector,sb in B['sectors'].items():
        res[sector]={}
        for Ls,x in sb['by_L'].items():
            L=int(Ls);net=base_dir/'nets'/x['net']
            if digest(net)!=x['net_sha256']:raise SystemExit(f'{net} differs from the baseline pin')
            root=V.stage(td/'f1graphs'/sector,sector,L,x['graphs']);lst=td/f'f1p_{sector}_L{L}.list';lst.write_text(''.join(f'{root}/L{L}/G{g}.txt\n'for g in x['graphs']))
            st=None
            for rg in x['ranges']:
                ref=base_dir/'refs'/rg['ref']
                if digest(ref)!=rg['ref_sha256']:raise SystemExit(f'{ref} differs from the baseline pin')
                s=time.time();y=json.loads(V.run([tool,L,lst,net,rg['begin'],rg['end'],B['seed'],threads,ref,'read'],threads=threads).stdout);st=f1_merge(st,y)
                log(f'F1 {sector} L{L} [{rg["begin"]},{rg["end"]}) in {time.time()-s:.0f} s')
            res[sector][Ls]={'profile':st,'exact':x['stats'],'verdict':f1_verdict(st,self_test),'tiers_profile':f1_tier_table(st),'tiers_exact':f1_tier_table(x['stats'])}
    allp=None
    for s in res.values():
        for v in s.values():allp=f1_merge(allp,v['profile'])
    rec={'baseline':str(base_dir),'baseline_sha256':digest(base_dir/'baseline.json'),'baseline_scale':B['scale'],'tool_command':cmd,'tool_gmp_library':lib,
         'tool_snapshot_sha256':snap_sha,'baseline_binding':B.get('binding'),'by_sector_L':res,
         'total':{'points':allp['points'],'tiers':f1_tier_table(allp),'paired':allp.get('paired'),'profile_checks':allp.get('profile_checks')},
         'verdict':f1_verdict(allp,self_test),'coverage':f1_coverage(B,res),'wall_seconds':round(time.time()-t0,1)}
    dump(out/'f1.json',rec);return rec

# ---------------------------------------------------------------- lanes
def lane_sets(n:int|None,t:int,fake:str|None)->tuple[list[list[int]],bool]:
    """n disjoint sets of t physical cores (NUMA-aligned through tools/benchkit.partition when the allocation allows it,
    else consecutive cores of the affinity set). n None: as many as fit."""
    import benchkit as bk
    cores=bk.fake_cores(fake)if fake else bk.host_cores()
    if n is None:n=max(1,len(cores)//t)
    if n*t>len(cores):raise SystemExit(f'lane shape {n}x{t} needs {n*t} physical cores; this allocation has {len(cores)}')
    try:return bk.partition(cores,n,t),True
    except bk.BenchError:
        cpus=[c for _,_,c in cores];return [cpus[i*t:(i+1)*t]for i in range(n)],False

def parse_shape(text:str)->tuple[int|None,int]:
    if text=='auto':return None,8
    n,_,t=text.partition('x')
    if not (n.isdigit()and t.isdigit()and int(n)>0 and int(t)>0):raise SystemExit(f'--shape {text!r}: NxT or auto')
    return int(n),int(t)

def run_native(exe,root,net,tasks,out,seed,rate,threads,cpus,pin,logf,L)->tuple[dict,float]:
    import benchkit as bk
    import thread_identity as TI
    out.unlink(missing_ok=True);cmd=bk.native_cmd(exe,root,V.GAMMA8,net,tasks,out,seed,0,rate,threads,'compensated');t0=time.perf_counter()
    env=bk.omp_env(threads,base=TI.child_env())  # X3: no inherited OpenMP control (OMP_THREAD_LIMIT, ...) reaches the worker
    with open(logf,'w')as f:cp=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,preexec_fn=bk.pinner(cpus,pin),timeout=6*3600)
    wall=time.perf_counter()-t0
    if cp.returncode:raise RuntimeError(f'{exe} exited {cp.returncode} on {tasks}: {Path(logf).read_text()[-1500:]}')
    n=load(out)
    if n.get('order')!=8 or n.get('L')!=L:raise RuntimeError(f'{out}: order {n.get("order")} L {n.get("L")}')
    out.unlink();Path(logf).unlink(missing_ok=True);return n,wall

# ---------------------------------------------------------------- F2
def derive(seed:int,group:str,role:str)->int:
    return int.from_bytes(hashlib.sha256(f'c8-d2-numerics-flags|{seed}|{group}|{role}'.encode()).digest()[:8],'little')%(2**63)

def f2_seed_entries(seed:int)->list[tuple[int,str]]:
    """(seed, label) of an F2 campaign: the base seed, then the native and net seeds of every (campaign, sector, L),
    loops 3..8 (whatever --f2-loops selects: the labels and the set are fixed by the base seed alone)."""
    out=[(seed,f'J-FLAG F2 base seed {seed} (tests/numerics_flags.py --seed)')]
    for c in CAMPAIGNS:
        for s in SECTORS:
            for L in range(3,9):
                g=f'{c}_{s}_L{L}'
                for role in ('native','net'):out.append((derive(seed,g,role),f'J-FLAG F2 {role} seed {g} of base {seed} (tests/numerics_flags.py)'))
    return out

def f2_clashes(doc:dict,entries:list,registry:dict)->list[str]:
    """W20: the collisions of the F2 entries [(seed, label)] with a seed log doc (read under its lock) and the archived
    C7(2) registry (production.seed_registry): an F2 seed that is an archived base, native or net seed; one logged under
    another source; or one equal to a derived C8 group seed (production.derive_seeds, every group) of a logged seed,
    i.e. a stream of a campaign in the log. The F2 campaign's own entries (identical seed and label) are not collisions:
    the gates reuse one base seed on purpose."""
    import production as prod
    own=set(entries);arch={**registry['net'],**registry['native'],**registry['bases']};clash=[]
    other=[(e['seed'],e.get('source'))for e in doc['seeds']if (e['seed'],e.get('source'))not in own]
    derived={}
    for b,src in other:
        for c,s,L in prod.GROUPS:
            x=prod.derive_seeds(b,c,s,L);derived.setdefault(x['native'],f'the native seed of {c}_{s}_L{L} of {b} ({src!r})');derived.setdefault(x['net'],f'the net seed of {c}_{s}_L{L} of {b} ({src!r})')
    logged={}
    for b,src in other:logged.setdefault(b,[]).append(src)
    for v,lab in entries:
        if v in arch:clash.append(f'{v} ({lab}): archived seed of {arch[v]}')
        clash+=[f'{v} ({lab}): logged as {src!r}'for src in logged.get(v,[])]
        if v in derived:clash.append(f'{v} ({lab}): equals {derived[v]}')
    return clash

def register_f2_seeds(log:Path,seed:int)->dict:
    """PLAN D9: add the F2 campaign's seeds to the seed log, in ONE transaction under its lock (W20, Stage-6 fix round 4,
    S6H4-03: before, the log was read and checked without the lock and the 49 seeds appended by separate locked adds, so
    a production plan could register the base seed in between and F2 then appended its own label beside it). Under the
    lock (tools/seeds.py reserve) the log is re-read, every F2 seed checked (f2_clashes: archived C7(2) seeds, seeds
    logged under another source, derived C8 group seeds of logged campaigns), and every missing entry appended before
    the lock is released. Refused (SystemExit) before anything is added when the log is missing or any seed collides:
    the F2 streams would then repeat another campaign's. Entries of the same base with the same labels are 'present'."""
    import seeds as SL
    import production as prod
    log=Path(log)
    if not log.is_file():raise SystemExit(f'F2 registers its seeds in the seed log, and {log} does not exist (tools/seeds.py init, or set C8_SEEDS)')
    entries=f2_seed_entries(seed);reg=prod.seed_registry()  # the archived registry is fixed: read before the lock
    try:st=SL.reserve(log,entries,lambda doc:f2_clashes(doc,entries,reg),f'tests/numerics_flags.py: F2 seeds of base {seed}')
    except SL.Refuse as r:raise SystemExit(f'F2 seeds collide with {log}: {r}; choose another --seed')from None
    return {'log':str(log),'base_seed':seed,'entries':len(entries),'added':st['added'],'present':st['present'],'log_sha256_after':digest(log),
            'transaction':'one locked read-check-append (tools/seeds.py reserve, W20)'}

def f2_graphs(sector:str,L:int,n:int|None)->list:
    ids=sorted(r['id']for r in V.inventory()[sector][str(L)])
    if n is None or L<7 or n>=len(ids):return ids
    return V.heavy_and_random(sector,L,n//2,n-n//2,52021+L+(9 if sector=='power'else 0))

def task_normalized(e:dict,p:dict)->tuple[D,D,list]:
    """(max_j |dv_j|/max(1, |v_j|), max_j |dv_j|/|v_j| (inf when v_j = 0 and dv_j != 0), [dv_j as Decimal])."""
    if (e['uid'],e['rep'],e['graph'],e['begin'],e['end'],e['total'])!=(p['uid'],p['rep'],p['graph'],p['begin'],p['end'],p['total']):raise AssertionError(f'row identity differs: {e["uid"]}')
    if len(e['values'])!=len(p['values']):raise AssertionError(f'row {e["uid"]}: jet widths differ')
    nd=rd=D(0);dv=[]
    for a,b in zip(e['values'],p['values']):
        x,y=D(a),D(b);d=y-x;dv.append(d)
        if d:nd=max(nd,abs(d)/max(D(1),abs(x)));rd=max(rd,abs(d)/abs(x)if x else D('Infinity'))
    return nd,rd,dv

def log_bin(x)->str:
    x=D(x)
    if x==0:return 'zero'
    if not x.is_finite():return 'inf'
    return str(math.floor(x.log10()))

def num(x):
    """A JSON number, or the string of a non-finite value (records are written with allow_nan=False)."""
    x=float(x);return x if math.isfinite(x)else str(x)

def quantiles(xs:list)->dict:
    if not xs:return {}
    s=sorted(xs);q=lambda f:s[min(len(s)-1,int(f*(len(s)-1)+.5))]
    return {'p50':q(.5),'p90':q(.9),'p99':q(.99),'p999':q(.999),'max':s[-1],'n':len(s),'zero':sum(1 for x in s if x==0)}

class F2Data:
    """Per (campaign, sector, L): the exact jets Y[r][g] and the differences dY[r][g] (profile - exact, from Decimal
    differences), the counters and task seconds of both binaries, and the per-task difference statistics."""
    def __init__(self):
        self.Y={};self.dY={};self.counts={};self.secs={};self.nd={};self.rd={};self.lock=threading.Lock()
    def add(self,key,ne:dict,np_:dict,writer=None):
        pr={r['uid']:r for r in np_['rows']}
        with self.lock:
            Y=self.Y.setdefault(key,{});dY=self.dY.setdefault(key,{});c=self.counts.setdefault(key,{'points':0,'quad_e':0,'mp_e':0,'quad_p':0,'mp_p':0})
            sec=self.secs.setdefault(key,[0.,0.]);nd=self.nd.setdefault(key,[]);rd=self.rd.setdefault(key,[])
            for e in ne['rows']:
                p=pr.pop(e['uid'],None)
                if p is None:raise AssertionError(f'{key}: the profile output lacks row {e["uid"]}')
                n_,r_,dv=task_normalized(e,p);k=(e['rep'],e['graph'])
                if k in Y:raise AssertionError(f'{key}: replicate {e["rep"]} graph {e["graph"]} twice')
                Y[k]=[float(v)for v in e['values']];dY[k]=[float(d)for d in dv];nd.append(n_);rd.append(r_)
                c['points']+=e['end']-e['begin'];c['quad_e']+=e['quad'];c['mp_e']+=e['mp'];c['quad_p']+=p['quad'];c['mp_p']+=p['mp']
                sec[0]+=float(e['seconds']);sec[1]+=float(p['seconds'])
                if writer:writer.writerow([*key,e['uid'],e['rep'],e['graph'],e['quad'],e['mp'],p['quad'],p['mp'],e['seconds'],p['seconds'],str(n_),*e['values'],'|',*map(str,dv)])
            if pr:raise AssertionError(f'{key}: the profile output has {len(pr)} extra rows')

def f2_analyze(data:F2Data,reps:int,loops,points:int,graphs_per:dict)->dict:
    """dC8 and SE_d per (sector, L) and in total from the per-graph linear map at the exact run's loop means; the
    nonlinear difference of the vendored coefficients at the two means; the gates; per-task statistics; F3 counters."""
    import numpy as np
    import assemble as asm
    loops=sorted(loops);K={L:9-L for L in loops}
    # per (c, s, L): replicate sums over graphs (R x 2k) of the exact jets and of the differences
    S={};dS={}
    for (c,s,L),Y in data.Y.items():
        gs=sorted({g for (r,g)in Y});S[(c,s,L)]=np.array([[math.fsum(Y[(r,g)][j]for g in gs)for j in range(2*K[L])]for r in range(reps)])
        dS[(c,s,L)]=np.array([[math.fsum(data.dY[(c,s,L)][(r,g)][j]for g in gs)for j in range(2*K[L])]for r in range(reps)])
    means={L:sum(S[(c,s,L)].mean(0)for c in CAMPAIGNS for s in SECTORS if (c,s,L)in S)/2 for L in loops}
    J=asm.jacobians(means,8);J8={L:np.asarray(J[L])[8].real.astype(float)for L in loops}
    def stat(keys)->dict:
        """dC8 = sum_c 1/2 mean_r d_c,r with d_c,r = sum over keys of campaign c of J8[L] . dS[r]; SE^2 = sum_c Var_r/(4R)."""
        mean=0.;var=0.
        for c in CAMPAIGNS:
            d=np.zeros(reps)
            for (cc,s,L)in keys:
                if cc==c:d=d+dS[(cc,s,L)]@J8[L]
            mean+=.5*float(d.mean());var+=.25*float(d.var(ddof=1))/reps if reps>1 else float('inf')
        se=math.sqrt(var);return {'dC8':mean,'se':num(se),'bound':num(abs(mean)+3*se),'passed':abs(mean)+3*se<=BOUND_DC8,'resolved':3*se<BOUND_DC8}
    per={};gates={}
    for s in SECTORS:
        for L in loops:
            keys=[k for k in dS if k[1]==s and k[2]==L]
            if not keys:continue
            per[f'{s}_L{L}']=stat(keys)
            if L>=7:gates[f'{s}_L{L}']=per[f'{s}_L{L}']
    total=stat(list(dS));gates['total']=total
    # the nonlinear difference in the vendored module's exact (Fraction) mode, so that no float cancellation of two
    # C8 values hides a small difference: the exact run's means and those means plus the mean differences
    from fractions import Fraction as Fr
    dm={L:sum(dS[(c,s,L)].mean(0)for c in CAMPAIGNS for s in SECTORS if (c,s,L)in dS)/2 for L in loops}
    ex=lambda v:np.array([Fr(float(x))for x in v],dtype=object)
    ce=asm.coefficients({L:ex(means[L])for L in loops},8)[8];cp=asm.coefficients({L:ex(means[L])+ex(dm[L])for L in loops},8)[8]
    c_e=float(ce);c_p=float(cp);c_d=float(cp-ce)
    allnd=[x for v in data.nd.values()for x in v];allrd=[x for v in data.rd.values()for x in v]
    task={'normalized':{k:num(v)for k,v in quantiles(allnd).items()},'relative':{k:num(v)for k,v in quantiles(allrd).items()},
          'hist_normalized':hist_count(allnd),'hist_relative':hist_count(allrd),'max_normalized':str(max(allnd,default=D(0))),
          'over_bound':sum(1 for x in allnd if x>BOUND_TASK),'bound':str(BOUND_TASK),
          'by_group':{f'{c}_{s}_L{L}':{'max_normalized':str(max(v,default=D(0))),'zero':sum(1 for x in v if x==0),'tasks':len(v)}for (c,s,L),v in sorted(data.nd.items())}}
    task['passed']=task['over_bound']==0
    n_mini=reps*points
    pj=lambda v,n:abs(v['dC8'])+3*float(v['se'])*math.sqrt(n_mini/n)
    proj={str(n):{k:{'projected':num(pj(v,n)),'within':pj(v,n)<=BOUND_DC8}for k,v in gates.items()}for n in PROJECT_POINTS}
    f3={}
    for (c,s,L),x in sorted(data.counts.items()):
        n=x['points']or 1
        f3[f'{c}_{s}_L{L}']={'points':x['points'],'quad_exact':x['quad_e']/n,'mp_exact':x['mp_e']/n,'quad_profile':x['quad_p']/n,'mp_profile':x['mp_p']/n,
                             'quad_change':(x['quad_p']-x['quad_e'])/n,'mp_change':(x['mp_p']-x['mp_e'])/n,
                             'task_seconds_exact':data.secs[(c,s,L)][0],'task_seconds_profile':data.secs[(c,s,L)][1],
                             'speed_ratio_exact_over_profile':data.secs[(c,s,L)][0]/data.secs[(c,s,L)][1]if data.secs[(c,s,L)][1]>0 else None}
    return {'replicates':reps,'points':points,'loops':loops,'graphs':graphs_per,'loop_means_exact':{str(L):means[L].tolist()for L in loops},
            'J8':{str(L):J8[L].tolist()for L in loops},'per_sector_L':per,'gates':gates,'total':total,
            'nonlinear':{'C8_exact_means':c_e,'C8_profile_means':c_p,'dC8':c_d,
                         'note':'the vendored coefficients at the two loop means in exact (Fraction) arithmetic: a cross-check of the linear map (partial sums when graphs or loops are subsets)'},
            'per_task':task,'projection':{'points_per_graph_mini':n_mini,'rule':'|dC8| + 3 SE_d sqrt(n_mini/n_prod): the mean difference kept as a bias, the SE scaled','by_points':proj},
            'f3_counters':f3,'passed':all(v['passed']for v in gates.values())and task['passed']}

def unresolved(gates:dict)->list:
    """The F2 gates that fail only because 3 SE_d is too large (|dC8| < 0.062): their replicates double."""
    return [k for k,v in gates.items()if not v['passed']and abs(v['dC8'])<BOUND_DC8]

def hist_count(xs)->dict:
    h={}
    for x in xs:b=log_bin(x);h[b]=h.get(b,0)+1
    return h

def f2_run(a,exact:Path,prof:Path,out:Path,td:Path,self_test:bool)->dict:
    """The paired mini-campaign; replicates double while a gate fails only by its SE."""
    loops=[int(x)for x in a.f2_loops.split(',')];reps=a.f2_replicates;P=a.f2_points;maxR=reps<<a.f2_max_doublings
    n,t=parse_shape(a.shape);lanes,aligned=lane_sets(n,t,a.fake_topology);pin=not a.fake_topology
    out.mkdir(parents=True);cm=load(COST_MODEL)['seconds_per_point']if COST_MODEL.is_file()else{}
    groups={};graphs_per={}
    for c in CAMPAIGNS:
        for s in SECTORS:
            for L in loops:
                if not (ROOT/f'inputs/packs/{s}_L{L}.pack').exists():raise SystemExit(f'inputs/packs/{s}_L{L}.pack is missing (make inputs-l8 for L8)')
                ids=f2_graphs(s,L,a.f2_graphs);graphs_per[f'{c}_{s}_L{L}']=len(ids)
                name=f'{c}_{s}_L{L}';root=V.stage(td/'f2graphs'/s,s,L,ids);net=td/f'f2_{name}.bin'
                nrec=V.make_net(net,maxR,4*L-1,NET_BITS[c],derive(a.seed,name,'net'),P)
                groups[(c,s,L)]={'ids':ids,'root':root,'net':net,'net_record':nrec,'seed':derive(a.seed,name,'native'),'rate':RATES[c]}
    data=F2Data();rounds=0;r0=0;runs=[];t0=time.time()
    fcsv=gzip.open(out/'rows.csv.gz','wt',newline='');w=csv.writer(fcsv)
    w.writerow(['campaign','sector','L','uid','rep','graph','quad_exact','mp_exact','quad_profile','mp_profile','seconds_exact','seconds_profile','normalized_difference','values_exact...','|','differences...'])
    try:
        while True:
            blocks=[]
            for (c,s,L),G in groups.items():
                ng=len(G['ids']);rows=[(r*ng+i,r,g,0,P,P)for r in range(r0,reps)for i,g in enumerate(G['ids'])]
                rows.sort(key=lambda x:(-cm.get(f'{c}:{s}:{L}:{x[2]}',0.),x[0]))
                for k in range(0,len(rows),BLOCK_TASKS):
                    part=rows[k:k+BLOCK_TASKS];cost=sum(cm.get(f'{c}:{s}:{L}:{x[2]}',1e-5)for x in part)*P
                    blocks.append((cost,(c,s,L),part))
            blocks.sort(key=lambda b:(-b[0],b[1],b[2][0][0]));Q=queue.Queue()
            for i,b in enumerate(blocks):Q.put((i,b))
            err=[];T=len(lanes[0])
            def lane(k):
                while not err:
                    try:i,(cost,key,part)=Q.get_nowait()
                    except queue.Empty:return
                    c,s,L=key;G=groups[key];tf=td/f'f2_lane{k}.tasks';tf.write_text(V.tasks_text(8,L,part))
                    try:
                        order=[('exact',exact),('profile',prof)];order=order if i%2==0 else order[::-1];res={}
                        for nm,x in order:res[nm]=run_native(x,G['root'],G['net'],tf,td/f'f2_lane{k}_{nm}.json',G['seed'],G['rate'],T,lanes[k],pin,td/f'f2_lane{k}.log',L)
                        data.add(key,res['exact'][0],res['profile'][0],w)
                        runs.append({'block':i,'group':f'{c}_{s}_L{L}','tasks':len(part),'lane':k,'first':order[0][0],'wall_exact':res['exact'][1],'wall_profile':res['profile'][1]})
                    except Exception as e:err.append(f'{c}_{s}_L{L} block {i}: {e}');return
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(lanes))as pool:list(pool.map(lane,range(len(lanes))))
            if err:raise RuntimeError(err[0])
            log(f'F2: replicates [{r0},{reps}) done ({len(blocks)} blocks, {time.time()-t0:.0f} s)')
            res=f2_analyze(data,reps,loops,P,graphs_per)
            todo=unresolved(res['gates'])
            if not todo or rounds>=a.f2_max_doublings:break
            log(f'F2: {todo} fail only by SE_d: the replicates double to {2*reps}');rounds+=1;r0=reps;reps*=2
    finally:fcsv.close()
    res.update(doublings=rounds,lanes={'shape':f'{len(lanes)}x{len(lanes[0])}','numa_aligned':aligned,'pinned':pin},seed=a.seed,
               nets={f'{c}_{s}_L{L}':G['net_record']for (c,s,L),G in groups.items()},native_seeds={f'{c}_{s}_L{L}':G['seed']for (c,s,L),G in groups.items()},
               rates=RATES,blocks=runs,rows_csv=str(out/'rows.csv.gz'),rows_csv_sha256=digest(out/'rows.csv.gz'),wall_seconds=round(time.time()-t0,1))
    if self_test:
        tot=res['total'];zero=tot['dC8']==0.0 and all(v['dC8']==0.0 for v in res['per_sector_L'].values())and res['per_task']['over_bound']==0 \
            and res['per_task']['normalized'].get('zero')==res['per_task']['normalized'].get('n')and all(abs(v['quad_change'])==0 and abs(v['mp_change'])==0 for v in res['f3_counters'].values())
        res['self_test']={'dC8_exactly_zero':zero,'nonlinear_dC8':res['nonlinear']['dC8']};res['passed']=res['passed']and zero
    dump(out/'f2.json',res);return res

# ---------------------------------------------------------------- F4
def f4_run(a,exact:Path,prof:Path,out:Path,td:Path,self_test:bool)->dict:
    """Interleaved repeats of both binaries on the L8 sweep sample in lanes; medians of the lane-thread seconds."""
    import benchkit as bk
    n,t=parse_shape(a.shape);lanes,aligned=lane_sets(n,t,a.fake_topology);pin=not a.fake_topology;T=len(lanes[0])
    L=a.f4_loop;sample=V.l8self_sample()if L==8 else{s:V.heavy_and_random(s,L,25,75,8813+(1 if s=='power'else 0))for s in SECTORS}
    if a.f4_sample:sample={k:v[:a.f4_sample]for k,v in sample.items()}
    cm=load(COST_MODEL)['seconds_per_point']if COST_MODEL.is_file()else{};REPS,PTS=2,512
    roots={};nets={};netrec={}
    for s,ids in sample.items():
        roots[s]=V.stage(td/'f4graphs'/s,s,L,ids);nets[s]=td/f'f4_{s}.bin';netrec[s]=V.make_net(nets[s],2,4*L-1,60,7702+(1 if s=='power'else 0),PTS)
    items=[(cm.get(f'a:{s}:{L}:{g}',1e-4)*REPS*PTS,(s,g),None)for s,ids in sample.items()for g in ids]
    shares=bk.lpt_shares(items,len(lanes));uid={}
    for s in SECTORS:
        for r in range(REPS):
            for g in sorted(sample[s]):uid[(s,r,g)]=len(uid)
    plan=[]
    for k,share in enumerate(shares):
        blocks=[]
        for s in SECTORS:
            gs=[it[1][1]for it in sorted((it for it in share if it[1][0]==s),key=lambda x:(-x[0],x[1]))]
            for i in range(0,len(gs),BLOCK_TASKS//REPS):
                rows=[(uid[(s,r,g)],r,g,0,PTS,PTS)for g in gs[i:i+BLOCK_TASKS//REPS]for r in range(REPS)];tf=td/f'f4_lane{k}_b{len(blocks)}.tasks'
                tf.write_text(V.tasks_text(8,L,rows));blocks.append((s,tf,len(rows)))
        plan.append(blocks)
    exes={'exact':exact,'profile':prof};runs=[]
    def one(name,r):
        def lane(k):
            recs=[];digs=[]
            for j,(s,tf,nt)in enumerate(plan[k]):
                nat,wall=run_native(exes[name],roots[s],nets[s],tf,td/f'f4_{name}_{k}_{j}.json',V.SEED,'.8',T,lanes[k],pin,td/f'f4_{name}_{k}_{j}.log',L)
                digs+=bk.rows_digest(nat['rows'],s);recs.append({'sector':s,'tasks':nt,'wall_seconds':wall,'quad':sum(x['quad']for x in nat['rows']),'mp':sum(x['mp']for x in nat['rows'])})
            return recs,digs
        t0=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(plan))as pool:res=list(pool.map(lane,range(len(plan))))
        blocks=[b for x in res for b in x[0]];digs=[d for x in res for d in x[1]]
        rec={'binary':name,'repeat':r,'node_wall_seconds':time.perf_counter()-t0,'rows_digest':bk.combined_digest(digs),
             'lane_thread_seconds':T*math.fsum(b['wall_seconds']for b in blocks),'quad':sum(b['quad']for b in blocks),'mp':sum(b['mp']for b in blocks),
             'per_sector':{s:T*math.fsum(b['wall_seconds']for b in blocks if b['sector']==s)for s in SECTORS}}
        log(f'F4 {name} r{r}: lane-thread s {rec["lane_thread_seconds"]:.1f} ({", ".join(f"{s} {v:.1f}"for s,v in rec["per_sector"].items())}), digest {rec["rows_digest"][:12]}')
        return rec
    names=['exact','profile']
    for r in range(a.f4_repeats):
        for nm in (names if r%2==0 else names[::-1]):runs.append(one(nm,r))
    med=lambda f,nm:statistics.median(f(x)for x in runs if x['binary']==nm)
    M={nm:{'total':med(lambda x:x['lane_thread_seconds'],nm),**{s:med(lambda x,s=s:x['per_sector'][s],nm)for s in SECTORS}}for nm in names}
    digests={nm:sorted({x['rows_digest']for x in runs if x['binary']==nm})for nm in names}
    rec={'loop':L,'sample':{s:len(v)for s,v in sample.items()},'replicates':REPS,'points':PTS,'shape':f'{len(lanes)}x{T}','numa_aligned':aligned,'pinned':pin,
         'repeats':a.f4_repeats,'runs':runs,'medians':M,
         'speedup_exact_over_profile':{k:M['exact'][k]/M['profile'][k]for k in M['exact']},
         'rows_repeatable':all(len(v)==1 for v in digests.values()),'rows_identical_between_binaries':digests['exact']==digests['profile'],'nets':netrec,
         'metric':'lane-thread seconds: threads x the sum of the native blocks\' wall times (start-up, load, integration, output), median of the repeats'}
    rec['passed']=rec['rows_repeatable']and(rec['rows_identical_between_binaries']or not self_test)
    out.mkdir(parents=True);dump(out/'f4.json',rec);return rec

# ---------------------------------------------------------------- F5
def f5_run(a,prof:Path,out:Path,td:Path)->dict:
    """F5: tests/thread_identity.py's blocks; each run's OpenMP team is observed and must be the requested one (X3)."""
    import thread_identity as TI
    res=[];t0=time.time()
    for s in SECTORS:res.append(TI.block(td/'f5',None,s,a.f5_threads,a.f5_lanes,a.f5_lane_threads,executable=prof));log(f'F5 {s}: identical, teams as requested')
    teams={b['sector']:{k:v.get('team_observed',v.get('teams_observed'))for k,v in b['runs'].items()}for b in res}
    verified=bool(res)and all(b.get('team_sizes_verified')is True for b in res)
    rec={'executable':str(prof),'sha256':digest(prof),'threads':a.f5_threads,'lanes':f'{a.f5_lanes}x{a.f5_lane_threads}','blocks':res,
         'team_sizes_verified':verified,'teams':teams,'omp_environment':'sanitized (no OMP_*, GOMP_*, KMP_*; OMP_DYNAMIC=false)',
         'passed':all(b['identical']for b in res)and verified,'wall_seconds':round(time.time()-t0,1)}
    out.mkdir(parents=True);dump(out/'f5.json',rec);return rec

# ---------------------------------------------------------------- main
def development(a)->list[str]:
    """The options that make this a development run (never a gate record)."""
    why=[]
    if a.f1_scale!=1:why.append(f'--f1-scale {a.f1_scale}')
    if a.f2_graphs is not None:why.append(f'--f2-graphs {a.f2_graphs}')
    if a.f2_loops!='3,4,5,6,7,8':why.append(f'--f2-loops {a.f2_loops}')
    if a.f2_replicates<4 or a.f2_points<256:why.append('fewer F2 replicates or points than 4 x 256')
    if a.f4_sample:why.append(f'--f4-sample {a.f4_sample}')
    if a.f4_loop!=8:why.append(f'--f4-loop {a.f4_loop}')
    if a.f4_repeats<3:why.append(f'--f4-repeats {a.f4_repeats}')
    if sorted(a.f5_threads)!=[1,8,16,64]or(a.f5_lanes,a.f5_lane_threads)!=(8,8):why.append('F5 thread counts other than 1, 8, 16, 64 and 8 x 8 lanes')
    if sorted(x.strip()for x in a.sectors.split(','))!=sorted(SECTORS):why.append(f'--sectors {a.sectors}')  # X1: F1 on both sectors
    if a.fake_topology:why.append('--fake-topology')
    return why

def main()->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    m=p.add_mutually_exclusive_group(required=True)
    m.add_argument('--profile',help='the opt-in profile (canonical name, e.g. dd or dd+mp256+exp1); its executable is bin/c8d2_gmp_<profile>')
    m.add_argument('--self-test',action='store_true',help='the exact binary as its own profile')
    m.add_argument('--f1-baseline-only',action='store_true',help='compute only the F1 exact baseline into OUTPUT/f1_baseline')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--exact',type=Path,default=ROOT/'bin/c8d2_gmp')
    p.add_argument('--profile-exe',type=Path,help='default bin/c8d2_gmp_<profile>')
    p.add_argument('--parts',default='F1,F2,F4,F5',help='F1,F2,F4,F5 (F3 comes with F1 and F2)')
    p.add_argument('--threads',type=int,default=len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else(os.cpu_count()or 1),help='F1 tool threads')
    p.add_argument('--scratch',type=Path,help='staging directory (node-local; default TMPDIR)')
    p.add_argument('--shape',default='auto',help='lanes NxT for F2 and F4 (auto: as many 8-core lanes as fit)')
    p.add_argument('--fake-topology',help='SxNxC topology without pinning (Mac tests only)')
    p.add_argument('--f1-baseline',type=Path,help='an existing F1 baseline directory (its baseline.json) of the same exact binary')
    p.add_argument('--f1-scale',type=float,default=1.0);p.add_argument('--f1-max-doublings',type=int,default=4)
    p.add_argument('--sectors',default='free,power')
    p.add_argument('--seed',type=int,default=820262401);p.add_argument('--f2-loops',default='3,4,5,6,7,8')
    p.add_argument('--seeds-log',type=Path,help='the forbidden-seed log F2 registers its seeds in (default $C8_SEEDS)')
    p.add_argument('--f2-replicates',type=int,default=4);p.add_argument('--f2-points',type=int,default=256);p.add_argument('--f2-max-doublings',type=int,default=2)
    p.add_argument('--f2-graphs',type=int,help='development: N graphs per (sector, L >= 7) (N/2 heaviest + N/2 random)')
    p.add_argument('--f4-repeats',type=int,default=3);p.add_argument('--f4-sample',type=int,help='development: the first N graphs per sector')
    p.add_argument('--f4-loop',type=int,default=8,choices=(7,8))
    p.add_argument('--f5-threads',type=int,nargs='+',default=[1,8,16,64]);p.add_argument('--f5-lanes',type=int,default=8);p.add_argument('--f5-lane-threads',type=int,default=8)
    a=p.parse_args()
    if a.output.exists():raise SystemExit(f'{a.output} exists')
    parts={x.strip().upper()for x in a.parts.split(',')if x.strip()}
    if not parts<={'F1','F2','F3','F4','F5'}:raise SystemExit(f'--parts {a.parts}: F1, F2, F4, F5')
    if 'F3'in parts:parts.discard('F3');parts|={'F1','F2'}
    exact=a.exact.resolve();t0=time.time();rec={'schema':SCHEMA,'utc_start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    rec['exact']=identity(exact,'exact')
    if a.self_test:prof=exact;pname='exact';rec['mode']='self-test'
    elif a.profile:
        pname=numerics_name(a.profile)
        if pname=='exact':raise SystemExit('--profile exact: use --self-test')
        if pname!=a.profile:raise SystemExit(f'--profile {a.profile!r}: the canonical name is {pname!r}')
        prof=(a.profile_exe or ROOT/'bin'/f'c8d2_gmp_{pname}').resolve();rec['mode']='profile'
    else:prof=None;pname=None;rec['mode']='f1-baseline-only'
    if prof is not None:rec['profile']=identity(prof,pname)if prof!=exact else rec['exact'];rec['profile_name']=pname
    # strict identity with the exact path: the self-test, and a profile executable whose every profile is a stub
    stubs=set(rec['profile']['stub_profiles'])if prof is not None and prof!=exact else set()
    strict=bool(a.self_test or(pname and pname!='exact'and stubs==set(pname.split('+'))))
    rec['strict_identity']={'required':strict,'why':'self-test'if a.self_test else('every profile of the executable is a stub'if strict else None)}
    dev=development(a);rec['development']=dev;rec['parts']=sorted(parts)if prof else['F1 baseline']
    rec['inputs']=input_identity()  # W18: the authenticated input set, verified before anything is built or written
    log(f'W18: inputs manifest {rec["inputs"]["manifest_sha256"][:12]}... verified ({"complete" if rec["inputs"]["complete"] else "skipped "+", ".join(rec["inputs"]["skipped"])})')
    want_f1='F1'in parts or rec['mode']=='f1-baseline-only';base=B=None
    snap=info=ex=reuse_lib=None  # set by the X2 snapshot below whenever want_f1; read only under want_f1 (tests/ast_scan.py)
    if want_f1 and a.f1_baseline:  # a reused baseline is checked before anything is built or written (X1, X2)
        base=a.f1_baseline.resolve();B=load(base/'baseline.json')
        if B.get('schema')!=BASELINE_SCHEMA:raise SystemExit(f'{base}/baseline.json is not an F1 baseline')
        if B['exact']['sha256']!=rec['exact']['sha256']:raise SystemExit(f'{base}: the baseline was made with exact binary {B["exact"]["sha256"][:12]}, not {rec["exact"]["sha256"][:12]}')
        if B['scale']!=a.f1_scale:raise SystemExit(f'{base}: baseline scale {B["scale"]} != --f1-scale {a.f1_scale}')
        bb=B.get('binding')if isinstance(B.get('binding'),dict)else{}
        if bb.get('reproduced')is not True or bb.get('sha256')!=B['exact']['sha256']:
            raise SystemExit(f'{base}: the baseline records no build binding of its exact tool to {B["exact"]["sha256"][:12]} (X2; a baseline made before '
                             'Stage-6 fix round 1): compute a fresh baseline')
    verdicts={}
    with tempfile.TemporaryDirectory(prefix='c8d2_flags_',dir=a.scratch)as td:
        td=Path(td)
        if want_f1:  # X2: one source snapshot; every executable an F1 tool stands for is rebuilt there byte for byte
            import build_record as BR  # W3's class: nested as deep as the build commands' relative words climb (mirror_relative)
            top=td/'snapshot';snap=BR.snapshot_root(top,snapshot_levels([exact]+([prof]if prof is not None and prof!=exact else[])));info=snapshot(snap)
            if B is not None and (B.get('binding')or{}).get('snapshot_sha256')!=info['sha256']:  # fix-round-1 residual: the reused baseline's tool
                raise SystemExit(f'{base}: the baseline\'s exact tool was compiled from source snapshot {str((B.get("binding")or{}).get("snapshot_sha256"))[:12]}, '
                                 f'not this run\'s {info["sha256"][:12]} (src/ or {F1_SOURCE} changed since): compute a fresh baseline (X2)')
            if B is not None:reuse_lib=reused_baseline_library(base,B,exact);log(f'Z19: the reused baseline\'s libgmp is {reuse_lib["want_sha256"][:12]}..., as {exact.name} resolves it here')
            if B is not None:  # W18: the reused baseline's 450-digit references describe the payloads it was made from (before anything is written)
                bi=(B.get('inputs')or{}).get('manifest_sha256')if isinstance(B.get('inputs'),dict)else None
                if bi!=rec['inputs']['manifest_sha256']:
                    raise SystemExit(f'{base}: the baseline was made from inputs manifest {str(bi)[:12]}..., not this run\'s {rec["inputs"]["manifest_sha256"][:12]}... '
                                     '(a baseline without an input identity predates Stage-6 fix round 4): compute a fresh baseline (W18)')
            ex={'exact':bind(exact,snap,info,td,'exact',top)}
            if prof is not None:ex['profile']=ex['exact']if prof==exact else bind(prof,snap,info,td,'profile',top)
            rec['build_binding']={'schema':BINDING_SCHEMA,'snapshot':info,'executables':ex,
                                  'rule':'every executable rebuilt in the read-only source snapshot with its build record\'s command is byte-identical to it (sha256); '
                                         'the F1 tools are compiled in the same snapshot with the same commands'}
        if prof is not None and 'F2'in parts:  # PLAN D9: the F2 campaign is registered before anything is written
            slog=a.seeds_log or (Path(os.environ['C8_SEEDS'])if os.environ.get('C8_SEEDS')else None)
            if slog is None:raise SystemExit('F2 registers its seeds in the forbidden-seed log: set C8_SEEDS or give --seeds-log FILE (PLAN D9)')
            rec['f2_seeds']=register_f2_seeds(slog,a.seed);log(f'F2 seeds: {rec["f2_seeds"]["added"]} added, {rec["f2_seeds"]["present"]} present in {slog}')
        a.output.mkdir(parents=True)
        try:
            if want_f1:
                if base is None:
                    base=a.output/'f1_baseline';log('F1: the exact baseline (450-digit references)')
                    B=f1_baseline(base,exact,a.threads,a.f1_scale,a.f1_max_doublings,[x.strip()for x in a.sectors.split(',')],td,snap,ex['exact'],rec['inputs'])
                rec['f1_baseline']={'path':str(base),'sha256':digest(base/'baseline.json'),'reused':bool(a.f1_baseline),'reused_gmp_library':reuse_lib,
                                    'tool_gmp_library':B.get('tool_gmp_library'),  # Z19 integration: the provenance design.check_gate requires
                                    'inputs_manifest_sha256':(B.get('inputs')or{}).get('manifest_sha256')}  # W18
                if prof is None:  # X1: a baseline-only run fails without the full coverage (unless it is a development run)
                    cov=f1_coverage(B);rec['f1_baseline']['coverage']=cov;verdicts['F1_baseline_coverage']=cov['complete']or bool(dev)
                else:
                    r=f1_profile(base,prof,a.threads,td,strict,a.output/'f1',snap,info['sha256']);rec['F1']={k:v for k,v in r.items()if k!='by_sector_L'}
                    verdicts['F1']=r['verdict']['passed']and(r['coverage']['complete']or bool(dev))  # X1: coverage is part of F1
                    if not r['coverage']['complete']:log(f'F1 coverage incomplete: {"; ".join(r["coverage"]["why"][:3])}')
                    rec['F3_tiers']={'profile':r['total']['tiers'],'exact':{t:sum(x['exact']['tiers'][t]['points']for s in r['by_sector_L'].values()for x in s.values())for t in TIER_NAMES},
                                     'transitions':(r['total'].get('paired')or{}).get('transitions')}
            if prof is not None and 'F2'in parts:
                log('F2: paired mini-campaign');r=f2_run(a,exact,prof,a.output/'f2',td,strict)
                rec['F2']={k:r[k]for k in ('replicates','points','loops','graphs','gates','total','nonlinear','per_task','projection','doublings','lanes','wall_seconds','passed')}
                if strict:rec['F2']['self_test']=r['self_test']
                rec['F3_counters']=r['f3_counters'];verdicts['F2']=r['passed']
            if prof is not None and 'F4'in parts:
                log('F4: speed');r=f4_run(a,exact,prof,a.output/'f4',td,strict);rec['F4']={k:v for k,v in r.items()if k not in('runs','nets')};verdicts['F4_rows']=r['passed']
            if prof is not None and 'F5'in parts:
                log('F5: thread identity');r=f5_run(a,prof,a.output/'f5',td);rec['F5']={k:v for k,v in r.items()if k!='blocks'};verdicts['F5']=r['passed']
        except Exception as e:
            rec['error']=f'{type(e).__name__}: {e}';verdicts['error']=False;log(rec['error'])
    end=inputs_unchanged(rec['inputs']);rec['inputs']['verified_at_end']=end['unchanged']  # W18: the inputs did not change during the run
    if not end['unchanged']:rec['inputs']['changed']=end['why'];verdicts['inputs_unchanged']=False;log(f'W18: {end["why"]}')
    rec['verdicts']=verdicts;ok=all(verdicts.values())
    rec['status']=('failed'if not ok else('development run (would pass)'if dev else'passed'))if prof is not None else('f1 baseline written'if ok else'failed')
    if prof is not None and rec.get('profile',{}).get('stub_profiles'):rec['note']=f'stub profile(s) {rec["profile"]["stub_profiles"]}: no numerics change implemented yet'
    rec['wall_seconds']=round(time.time()-t0,1);rec['environment']=environment_record()
    dump(a.output/'numerics_flags.json',rec)
    print(json.dumps({k:rec.get(k)for k in ('mode','profile_name','status','verdicts','development','note','error')},indent=1))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
