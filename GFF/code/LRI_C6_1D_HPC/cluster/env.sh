# Environment for c6sum jobs on symmetry. Source from every job script.
# The site module scripts reference unset variables: load them with nounset off, then restore the caller's setting.
case $- in *u*) _c6_nounset=1 ;; *) _c6_nounset=0 ;; esac
set +u
source /etc/profile.d/modules.sh
module load gcc/11.2.0 anaconda3/2023.07-2
(( _c6_nounset )) && set -u
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
export C6_HOME=/mnt/beegfs/zzheng1/lri_c6_1d
export C6_CODE=${C6_CODE:-$C6_HOME/code/current}
export C6_DATA=$C6_HOME/data
export C6_RUNS=$C6_HOME/runs
export C6_LEVELS=$C6_HOME/levels
export C6_LOGS=$C6_HOME/logs
export OMP_PLACES=cores OMP_PROC_BIND=spread OPENBLAS_NUM_THREADS=1
# Physical cores available to this job (hpc-clusters rule 7); whole Intel node -> 40.
phys_alloc() {
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
# Identities of everything that determines the numbers: source, both executables, graph files, weights manifest.
c6_identities() {
  python - "$C6_CODE" "$C6_DATA" <<'PY'
import sys, json, hashlib, os
code, data = sys.argv[1], sys.argv[2]
def h(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.exists(p) else None
ids = {'source': h(f'{code}/src/c6sum.cpp'), 'c6sum': h(f'{code}/bin/c6sum'), 'c6sum_ld': h(f'{code}/bin/c6sum_ld'),
       'graphs6': h(f'{data}/graphs6.bin'), 'graphs7': h(f'{data}/graphs7.bin'), 'weights_manifest': h(f'{data}/weights_manifest.json'),
       'code_dir': os.path.realpath(code)}
print(json.dumps(ids, sort_keys=True))
PY
}
# Production gate: validation/APPROVED.json must exist and match the current identities exactly.
c6_require_approval() {
  local A=$C6_HOME/validation/APPROVED.json
  [[ -s $A ]] || { echo "no validation approval ($A); run cluster/validate_all.sh first" >&2; return 1; }
  local cur; cur=$(c6_identities)
  python - "$A" "$cur" <<'PY' || { echo "validation approval does not match the current binaries/data; revalidate" >&2; return 1; }
import sys, json
a = json.load(open(sys.argv[1])); cur = json.loads(sys.argv[2])
sys.exit(0 if a.get('pass') is True and a.get('identities') == cur and all(cur.values()) else 1)
PY
}
# Queue state of this user's jobs whose names match a regex; exits nonzero if squeue fails (unknown state).
c6_active_jobs() {
  local q; q=$(squeue -u "$USER" -h -o '%j') || { echo "squeue failed: queue state unknown" >&2; return 1; }
  grep -cE "$1" <<< "$q" || true
}
# Campaign lock (mkdir is atomic on BeeGFS): c6_lock NAME acquires $C6_HOME/.NAME.lock or fails; released on exit.
c6_lock() {
  local d=$C6_HOME/.$1.lock
  mkdir "$d" 2>/dev/null || { echo "lock $d held ($(cat "$d/owner" 2>/dev/null)); another submission is in progress" >&2; return 1; }
  echo "$(hostname) $$ $(date +%F_%T)" > "$d/owner"; trap "rm -rf '$d'" EXIT
}
# Level status: 0 = merged and matches the approved identities; 2 = absent; 1 = present but mismatched or corrupt.
c6_level_status() {
  local f=$C6_LEVELS/$1.json
  [[ -e $f ]] || return 2
  python "$C6_CODE/tools/levelcheck.py" "$f" "$(python -c "import json;print(json.dumps(json.load(open('$C6_HOME/validation/APPROVED.json'))['identities']))")" "$C6_DATA/weights_manifest.json"
}
# Resource accounting for the stopping rule (PLAN 4.5 (c), (d)); prints JSON.
#  - Consumption: every job ID recorded in $C6_HOME/SUBMITTED.txt (arrays, merges, batches) is queried with
#    `sacct --duplicates`, so requeued and failed attempts are included; NNodes x ElapsedRaw is summed over all rows.
#  - Accounting coverage: every recorded job ID must have accounting rows, and every array must show at least its
#    recorded number of distinct task indices. Completion is not read from sacct states: it is the presence of the
#    merged N* light and hard levels, which exist only when all their sectors completed (and which the decision
#    file binds by hash).
#  - coverage_complete = accounting coverage and both N* levels present; analyze.py treats false as unresolved.
c6_resources() {
  local nstar=$1 ids out
  ids=$(grep -oE '(array|merge|job)=[0-9]+' "$C6_HOME/SUBMITTED.txt" | cut -d= -f2 | sort -u | paste -sd, -)
  [[ -n $ids ]] || { echo "no submitted production jobs recorded" >&2; return 1; }
  out=$(sacct --duplicates -X -n -P -j "$ids" -o JobID,JobName,NNodes,ElapsedRaw,State) || { echo "sacct failed" >&2; return 1; }
  python - "$nstar" "$C6_HOME/SUBMITTED.txt" "$C6_LEVELS" <<PY
import sys, json, re, os
nstar, subf, lv = int(sys.argv[1]), sys.argv[2], sys.argv[3]
expected = {}   # job id -> expected number of array tasks (1 for non-arrays)
for ln in open(subf):
    m = re.search(r'array=(\d+) tasks=(\d+)', ln)
    if m: expected[m.group(1)] = int(m.group(2))
    for key in ('merge', 'job'):
        m = re.search(key + r'=(\d+)', ln)
        if m: expected.setdefault(m.group(1), 1)
seen = {}; tot = 0.0; last = 0.0
names = (f'c6_L6_H_light_N{nstar}.dbl', f'c6_L6_H_hard_N{nstar}.ld')
for ln in """$out""".splitlines():
    jid, name, nn, el, st = (ln.split('|') + [''] * 5)[:5]
    if not el.isdigit():
        continue
    base, _, task = jid.partition('_')
    seen.setdefault(base, set()).add(task.strip('[]') or '0')
    h = int(nn or 1) * int(el) / 3600; tot += h
    if name in names:
        last += h
missing = sorted(j for j in expected if j not in seen)
short = sorted(j for j, n in expected.items() if j in seen and len(seen[j]) < n)
levels = {f: os.path.exists(os.path.join(lv, f)) for f in (f'L6_H_light_N{nstar}.dbl.json', f'L6_H_hard_N{nstar}.ld.json')}
complete = not missing and not short and all(levels.values())
proj = last * ((nstar + 3) / (nstar + 1)) ** 5 / 12
print(json.dumps({'production_node_hours': round(tot, 3), 'N_star': nstar, 'N_star_node_hours': round(last, 3),
                  'projected_next_hours_on_12_nodes': round(proj, 3), 'coverage_complete': complete,
                  'coverage': {'jobs_recorded': len(expected), 'jobs_without_accounting': missing, 'arrays_short_of_tasks': short, 'N_star_levels': levels}}))
PY
}
# Continuation guard (PLAN 4.5): an L6 degree N > 16 may be submitted only if decisions/decision_N<N-2>.json says
# 'continue' with next_degree N, for the current N-2 light and hard level files (hash-bound).
c6_require_continuation() {
  local N=$1
  (( N <= 16 )) && return 0
  python - "$C6_HOME/decisions/decision_N$((N - 2)).json" "$C6_LEVELS" "$N" <<'PY' || { echo "no valid 'continue' decision for N=$N" >&2; return 1; }
import sys, json, hashlib, os
dec, lv, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(dec))
ok = d.get('decision') == 'continue' and d.get('next_degree') == n and d.get('levels_at_N_star') and all(
    os.path.exists(f'{lv}/{f}') and hashlib.sha256(open(f'{lv}/{f}', 'rb').read()).hexdigest() == h for f, h in d['levels_at_N_star'].items())
sys.exit(0 if ok else 1)
PY
}
# Partition routing (user, 2026-09-29: "prioritize amdq"): amdq alone if it has at least $1 idle nodes, otherwise
# amdq first with defq as fallback. Both builds are x86-64-v3 and run on either node type with identical results.
c6_partition() {
  local idle; idle=$(sinfo -h -p amdq -t idle -o %D 2>/dev/null | awk '{s+=$1} END{print s+0}')
  if (( idle >= $1 )); then echo amdq; else echo amdq,defq; fi
}
