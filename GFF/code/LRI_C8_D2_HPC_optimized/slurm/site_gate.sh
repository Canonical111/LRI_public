#!/bin/bash
#SBATCH --job-name=c8d2-ind-gate
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --output=c8d2-ind-gate-%j.log
# Per-site gate of the site layer (docs/SITES.md): AC1-AC4 and the package tests, in node-local scratch, one job per
# site on the production CPU type. Submit from the clone (the job name counts as this session's, c8d2-):
#   expanse:  sbatch -A yun124 -p compute -N1 -n1 -c 128 --mem=240G -t 03:00:00 slurm/site_gate.sh
#   symmetry: sbatch -p amdq --exclude=cn112 -N1 -n1 -c 64 --mem=245G -t 03:00:00 slurm/site_gate.sh
# with C8_ENV_SETUP=<clone>/slurm/env_<site>.sh exported. Optional: C8_GATE_REPO (default: the clone holding this
# script), C8_GATE_ORIGINAL (the staged original package's inputs/; default $C8_DATA/original/inputs), C8_GATE_BASE
# (df468f8), C8_GATE_JOBS (make -j, default 16), C8_GATE_SEED (the AC4 test plan's seed; the plan is never run).
# Steps (each logged; the job continues after a failure and the summary names every one):
#   AC1  pinned files unchanged since the base (working tree and HEAD); df468f8 and HEAD built from `git archive` in
#        two node-local trees with one environment; bin/c8d2_gmp and bin/c8d2_decimal byte-identical
#   AC2  benchmark_native.py build-baseline + compare on the frozen 52-case matrix, HEAD's c8d2_gmp against the
#        pristine baseline: status passed, every case exact, 300 rows, 18,247 binary128 and 3,327 MP promotions per
#        executable and thread count, 4 split checks <= 5e-16; the aggregate science digest is recorded (equality with
#        their sandbox's 366421b2... is reported, not required)
#   AC3  make test; kernel_checks --graph-list; hpc_scheduler, attach_inputs, allocation, refinement_allocation,
#        precision_delivery, site_layer; then, with the packs attached by symlink, hpc_cli, make test-workflow,
#        cluster_graph_tasks (tests/precision_allocation.py needs the absent precision_work/ and is not run)
#   AC4  production.py plan --test-graphs 1 with one seed and argument list from both trees: every group's config.json,
#        sobol.bin and tasks.sqlite byte-identical
# Output: $C8_DATA/gates/<site>-<UTC date>-<job>/ (logs, the replay comparison, summary.json); summary.json is also
# copied to <repo>/verification/site_gates/<site>-<UTC date>-<job>.json. Exit 0 only when every check passed.
# Local helper modes (no Slurm, no build): bash site_gate.sh --check-replay DIR | --compare-plans A B | --summary DIR
set -uo pipefail
PY="${C8_PYTHON:-python3}"
PINNED=(src Makefile tools/production.py tools/common.py tools/assemble.py tools/prepare_inputs.py tools/task_schedule.py
        tools/stage_runtime.py tools/slurm_submit.py slurm/run_array.sh slurm/merge.sh)
gate_py() {
  "$PY" - "$@" <<'PY'
import hashlib,json,os,sys,time
from decimal import Decimal
MANIFEST='3cb097e3840aeea7403a97b38486bc176dcda7f28fc27f9db46a1cde42a3dbd8';SANDBOX='366421b26dd4a0b25c62db7f5dc6ee84a2319c908053e0df263ba0e1768cd484'
HEADER=('schema','order','L','seed','layout','bits','rate','sum_mode','long_double_bits','mp_backend','mp_digits10')
ROW=('uid','rep','graph','begin','end','total','values','quad','mp','max_abs')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb')as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def replay(d):
    c=json.load(open(os.path.join(d,'comparison.json')));probs=[];tot={}
    if c.get('status')!='passed':probs.append(f'status {c.get("status")!r}')
    if c.get('manifest_sha256')!=MANIFEST:probs.append(f'manifest {c.get("manifest_sha256")}')
    cases=c.get('cases',[])
    if len(cases)!=52:probs.append(f'{len(cases)} cases, not 52')
    for case in cases:
        for r in case.get('runs',[]):
            x=r.get('exact_check')or{};k=f'{r.get("executable")}_t{r.get("threads")}';t=tot.setdefault(k,{'rows':0,'quad':0,'mp':0})
            if x.get('exact')is not True:probs.append(f'{case["name"]} {k} not exact')
            for f in t:t[f]+=x.get(f,0)
    want={f'{e}_t{n}'for e in('baseline','candidate')for n in c.get('thread_counts',[])}
    if set(tot)!=want or not want:probs.append(f'runs {sorted(tot)} differ from {sorted(want)}')
    for k,t in sorted(tot.items()):
        if (t['rows'],t['quad'],t['mp'])!=(300,18247,3327):probs.append(f'{k}: rows {t["rows"]}, binary128 {t["quad"]}, MP {t["mp"]} (want 300, 18247, 3327)')
    sp=c.get('split_checks',[])
    if len(sp)!=4 or any(Decimal(s['max_normalized_merge_rounding'])>Decimal('5e-16')for s in sp):probs.append(f'split checks {[s.get("max_normalized_merge_rounding")for s in sp]}')
    digests={}
    for case in sorted(x['name']for x in cases):
        n=json.load(open(os.path.join(d,case,'candidate_t1_r0.json')))
        doc={'header':{k:n.get(k)for k in HEADER},'rows':[{k:r.get(k)for k in ROW}for r in n['rows']]}
        digests[case]=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    agg=hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest()
    return {'check':'AC2 frozen replay','passed':not probs,'problems':probs,'cases':len(cases),'totals':tot,'split_checks':[s.get('max_normalized_merge_rounding')for s in sp],
            'candidate_sha256':c.get('candidate_sha256'),'baseline_sha256':c.get('baseline_sha256'),'science_digest':agg,'equals_sandbox_digest':agg==SANDBOX,
            'case_digests':{k:digests[k]for k in('free_L3','free_L8','power_L8')if k in digests}}
PATH_KEYS={'package'}  # the plan's only path-valued manifest key (production.py: package=str(ROOT)); every other key must match
def plans(a,b):
    ga=sorted(os.listdir(os.path.join(a,'groups')));gb=sorted(os.listdir(os.path.join(b,'groups')));probs=[]if ga==gb else[f'groups differ: {ga} vs {gb}'];files={}
    for g in ga:
        for f in ('config.json','sobol.bin','tasks.sqlite'):
            x,y=(sha(os.path.join(r,'groups',g,f))if os.path.exists(os.path.join(r,'groups',g,f))else None for r in(a,b));files[f'{g}/{f}']=x
            if x is None or x!=y:probs.append(f'{g}/{f}: {x} vs {y}')
    ma,mb=(json.load(open(os.path.join(r,'manifest.json')))for r in(a,b))
    diff=sorted(k for k in set(ma)|set(mb)if ma.get(k)!=mb.get(k))
    probs+=[f'manifest key {k!r} differs (only the path keys {sorted(PATH_KEYS)} may)'for k in diff if k not in PATH_KEYS]
    return {'check':'AC4 plan invariance','passed':not probs and len(ga)==24,'problems':probs,'groups':len(ga),'files_compared':len(files),
            'manifest_keys_differing':diff}
def summary(d):
    steps=[]
    for line in open(os.path.join(d,'steps.tsv')):
        name,rc,sec,log=line.rstrip('\n').split('\t');steps.append({'step':name,'rc':int(rc),'seconds':float(sec),'log':log})
    env=json.load(open(os.path.join(d,'environment.json')))if os.path.exists(os.path.join(d,'environment.json'))else{}
    det={};bad=[]
    for f in sorted(os.listdir(d)):
        if f.startswith('check_')and f.endswith('.json'):
            try:det[f[6:-5]]=json.load(open(os.path.join(d,f)))
            except (OSError,ValueError)as x:det[f[6:-5]]={'passed':False,'error':f'unreadable {f}: {x}'}
            if isinstance(det[f[6:-5]],dict)and det[f[6:-5]].get('passed')is False:bad.append(f[:-5])
    failed=[s['step']for s in steps if s['rc']]+bad
    return {'schema':'c8ind-site-gate-1','status':'passed'if steps and not failed else'failed','failed_steps':failed,'steps':steps,'checks':det,'environment':env,
            'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
mode=sys.argv[1]
r=replay(sys.argv[2])if mode=='replay'else plans(sys.argv[2],sys.argv[3])if mode=='plans'else summary(sys.argv[2])
print(json.dumps(r,indent=1,sort_keys=True));sys.exit(0 if r.get('passed',r.get('status')=='passed')else 1)
PY
}
case "${1:-}" in
  --check-replay) shift; gate_py replay "${1:?directory}"; exit $? ;;
  --compare-plans) shift; gate_py plans "${1:?plan A}" "${2:?plan B}"; exit $? ;;
  --summary) shift; gate_py summary "${1:?results directory}"; exit $? ;;
  "") ;;
  *) echo "usage: sbatch ... slurm/site_gate.sh | site_gate.sh --check-replay DIR | --compare-plans A B | --summary DIR" >&2; exit 64 ;;
esac

# ---------------------------------------------------------------- the gate job
set -e
[[ -n "${C8_ENV_SETUP:-}" && -r "$C8_ENV_SETUP" ]] || { echo "C8: set C8_ENV_SETUP to slurm/env_<site>.sh" >&2; exit 64; }
source "$C8_ENV_SETUP"
PY="${C8_PYTHON:-python3}"
: "${SLURM_JOB_ID:?submit site_gate.sh with sbatch}"; : "${C8_SITE:?the env file sets C8_SITE}"; : "${C8_DATA:?the env file sets C8_DATA}"
set +e
# The clone: C8_GATE_REPO, else the one holding this script, else (sbatch runs a spool copy) the submission directory.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; REPO="${C8_GATE_REPO:-}"
if [[ -z "$REPO" ]]; then
  for d in "$here/.." "${SLURM_SUBMIT_DIR:-}"; do
    if [[ -n "$d" && -f "$d/slurm/site_gate.sh" ]] && git -C "$d" rev-parse --git-dir >/dev/null 2>&1; then REPO="$(cd "$d" && pwd)"; break; fi
  done
fi
[[ -n "$REPO" ]] || { echo "C8: cannot find the clone; set C8_GATE_REPO or submit from the clone's root" >&2; exit 64; }
BASE="${C8_GATE_BASE:-df468f8}"; J="${C8_GATE_JOBS:-16}"; ORIG="${C8_GATE_ORIGINAL:-$C8_DATA/original/inputs}"
SEED="${C8_GATE_SEED:-8795672985463472}"; SITE="$C8_SITE"; DAY="$(date -u +%Y%m%d)"; TAG="$SITE-$DAY-$SLURM_JOB_ID"
OUT="$C8_DATA/gates/$TAG"; W="${TMPDIR:-/tmp}/c8gate_$SLURM_JOB_ID"
mkdir -p "$OUT" "$W" || exit 64
: > "$OUT/steps.tsv"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
step() {  # step NAME DIR COMMAND...: run in DIR, log to $OUT/NAME.log, record rc and seconds
  local name="$1" dir="$2"; shift 2
  local t0; t0=$(date +%s)
  ( cd "$dir" && "$@" ) > "$OUT/$name.log" 2>&1; local rc=$?
  printf '%s\t%s\t%s\t%s\n' "$name" "$rc" "$(( $(date +%s) - t0 ))" "$OUT/$name.log" >> "$OUT/steps.tsv"
  echo "C8 gate: $name rc=$rc" >&2; return $rc
}
empty_diff() { local d; d="$(git -C "$REPO" diff --stat "$@" -- "${PINNED[@]}")" || return 2; echo "$d"; [[ -z "$d" ]]; }
{
  echo "{\"job\": \"$SLURM_JOB_ID\", \"site\": \"$SITE\", \"node\": \"$(hostname)\", \"repo\": \"$REPO\", \"base\": \"$BASE\","
  echo " \"head\": \"$(git -C "$REPO" rev-parse HEAD)\", \"dirty\": $( [[ -z "$(git -C "$REPO" status --porcelain)" ]] && echo false || echo true ),"
  echo " \"scratch\": \"$W\", \"original_inputs\": \"$ORIG\"}"
} > "$W/env_head.json"
"$PY" - "$W/env_head.json" "$OUT/environment.json" <<'PY'
import json,os,platform,shutil,subprocess,sys
e=json.load(open(sys.argv[1]))
def out(cmd):
    try:return subprocess.run(cmd,capture_output=True,text=True,timeout=120).stdout.strip()
    except (OSError,subprocess.SubprocessError)as x:return f'unavailable: {x}'
e.update(lscpu=out(['lscpu']),numa=out(['numactl','-H'])if shutil.which('numactl')else None,nproc=os.cpu_count(),gcc=out(['gcc','--version']).splitlines()[:1],
         python=platform.python_version(),uname=platform.platform())
for m in ('numpy','scipy','mpmath'):
    try:e[m]=__import__(m).__version__
    except ImportError:e[m]=None
json.dump(e,open(sys.argv[2],'w'),indent=1,sort_keys=True)
PY

# AC1: pinned files, two trees, byte-identical executables
step ac1_pinned_unchanged_worktree "$REPO" empty_diff "$BASE"
step ac1_pinned_unchanged_head "$REPO" empty_diff "$BASE" HEAD
step extract_trees "$W" bash -c "mkdir -p wt_base wt_head && git -C '$REPO' archive '$BASE' | tar -x -C wt_base && git -C '$REPO' archive HEAD | tar -x -C wt_head"
step ac1_build_base "$W/wt_base" make -j"$J" gmp decimal PYTHON="$PY"
step ac1_build_head "$W/wt_head" make -j"$J" gmp decimal PYTHON="$PY"
step ac1_identical_gmp "$W" cmp wt_base/bin/c8d2_gmp wt_head/bin/c8d2_gmp
step ac1_identical_decimal "$W" cmp wt_base/bin/c8d2_decimal wt_head/bin/c8d2_decimal
"$PY" -c 'import hashlib,json,sys;json.dump({p:hashlib.sha256(open(p,"rb").read()).hexdigest() for p in sys.argv[2:] if __import__("os").path.exists(p)},open(sys.argv[1],"w"),indent=1)' \
  "$OUT/check_executables.json" "$W"/wt_base/bin/c8d2_gmp "$W"/wt_head/bin/c8d2_gmp "$W"/wt_base/bin/c8d2_decimal "$W"/wt_head/bin/c8d2_decimal
cp "$W"/wt_head/bin/*.build.json "$OUT/" 2>/dev/null; ldd "$W/wt_head/bin/c8d2_gmp" > "$OUT/ldd_c8d2_gmp.txt" 2>&1

# AC2: frozen replay against the pristine baseline built with HEAD's flags
step ac2_build_baseline "$W/wt_head" "$PY" -B tools/benchmark_native.py build-baseline --backend gmp --output "verification/${SITE}_baseline_gmp"
step ac2_compare "$W/wt_head" "$PY" -B tools/benchmark_native.py compare --manifest optimization_work/baseline_profile/matrix/manifest.json \
  --baseline "verification/${SITE}_baseline_gmp" --candidate bin/c8d2_gmp --output "verification/${SITE}_exact_replay" --threads 1 2 --repeats 1
step ac2_check "$W" bash -c "bash '$REPO/slurm/site_gate.sh' --check-replay '$W/wt_head/verification/${SITE}_exact_replay' > '$OUT/check_ac2_replay.json'"
cp "$W/wt_head/verification/${SITE}_exact_replay/comparison.json" "$OUT/ac2_comparison.json" 2>/dev/null

# AC3: package tests (no packs), then with the packs attached
step ac3_make_test "$W/wt_head" make test PYTHON="$PY"
step ac3_kernel_graph_list "$W/wt_head" "$PY" -B tests/kernel_checks.py --graph-list tests/fixtures/graphs.txt
for t in hpc_scheduler attach_inputs allocation refinement_allocation precision_delivery site_layer; do
  step "ac3_$t" "$W/wt_head" "$PY" -B "tests/$t.py"
done
step attach_head "$W/wt_head" "$PY" -B tools/attach_inputs.py "$ORIG" --mode symlink
step attach_base "$W/wt_base" "$PY" -B tools/attach_inputs.py "$ORIG" --mode symlink
step ac3_hpc_cli "$W/wt_head" "$PY" -B tests/hpc_cli.py
step ac3_test_workflow "$W/wt_head" make test-workflow PYTHON="$PY"
step ac3_cluster_graph_tasks "$W/wt_head" "$PY" -B tests/cluster_graph_tasks.py

# AC4: the same test plan from both trees
PLAN_ARGS=(--seed "$SEED" --backend gmp --test-graphs 1 --points 4 --replicates 4 --shards 2 --threads 8 --checkpoint-tasks 512)
step ac4_plan_base "$W/wt_base" "$PY" -B tools/production.py plan "$W/plan_base" "${PLAN_ARGS[@]}"
step ac4_plan_head "$W/wt_head" "$PY" -B tools/production.py plan "$W/plan_head" "${PLAN_ARGS[@]}"
step ac4_check "$W" bash -c "bash '$REPO/slurm/site_gate.sh' --compare-plans '$W/plan_base' '$W/plan_head' > '$OUT/check_ac4_plans.json'"

gate_py summary "$OUT" > "$OUT/summary.json"; rc=$?
mkdir -p "$REPO/verification/site_gates" && cp "$OUT/summary.json" "$REPO/verification/site_gates/$TAG.json"
echo "C8 gate: summary $OUT/summary.json (copied to $REPO/verification/site_gates/$TAG.json); exit $rc" >&2
rm -rf "$W"
exit $rc
