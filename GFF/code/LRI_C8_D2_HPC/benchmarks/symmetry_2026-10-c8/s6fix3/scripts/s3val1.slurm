#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-VAL-1 on symmetry for the Stage-6 fix-round-3 head (PLAN job table: template, -t 02:00:00; a whole amdq node), in the
# export built by s3build.slurm (afterok). Template: s6res2/scripts/rsval1.slurm (job 570515), the same steps; step 3 adds
# tests/combine_core.py (Z8's combine-side refusals). Fix round 3 runs inside make test: validate's bad_inputs with the 14
# Z4 truncations (worker and inspector), tests/test_native_guards.py (Z3, Z4; in an export without .git its before-fix
# parts are skipped: s3build ran them against the a42cfb7 export), unit_orchestration (Z3 plan side, Z6, Z7, Z11, Z13,
# Z15, the cross-group Z3/Z19/Z9 checks) on Linux with the real worker, test_pipeline (Z9, Z10, Z12), test_regress (Z5),
# test_gmp_binding (Z1, Z2, Z18, the Z2 consumers), test_numerics_flags (Z19 and its check_gate side), test_profiling
# (Z20-Z22); verify_result_tamper (Z8) in step 3.
#   1. tests/check_venv.py --strict;
#   2. `make test OUTPUT=<evidence>/test`, literally, as ONE command (validate subset, test-python, workflow, staging);
#      it must exit 0;
#   3. tests/assembly_checks.py --exact, tests/verify_result_tamper.py (R3, Z8), tests/combine_core.py (Z8) and
#      tests/compat_2026.py;
#   4. the executables are unchanged by make (sha256 before and after);
#   5. R1 on the real node with hostile inherited controls: `tests/validate.py --only invariance` run with
#      OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none exported (the controls
#      test_omp_launch inherits on its stand-in); it must pass with every team verified (a 4-thread run given a team of
#      1 fails in team_run). Then the teams of both invariance records are summarized (teams.json).
# Temporary package copies and campaigns on the node-local /tmp (TMPDIR). C8_SEEDS/C8_SITE/C8_INPUTS unset (the tests
# make their own).
# Usage: C8_PACKAGE=... sbatch --export=ALL --dependency=afterok:<s3build> -J c8d2-s3val1 s3val1.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3val1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"; python3 --version; python3 -c 'import numpy;print("numpy",numpy.__version__)'
python3 -m pip freeze > "$E/pip_freeze.txt" 2>&1
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
env | grep -E '^(OMP_|GOMP_|KMP_)' | sort > "$E/omp_env_inherited.txt"; echo "inherited OpenMP controls: $(wc -l < "$E/omp_env_inherited.txt")"
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
status=0
run() {
  local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "== $name exit $c after $(( $(date +%s) - t )) s"; echo "$name $c $(( $(date +%s) - t ))" >> "$E/exits.txt"; tail -3 "$E/$name.log" | cut -c1-300
  if [ $c -ne 0 ]; then status=1; grep -E '^FAIL|Error|Traceback|failed' "$E/$name.log" | head -30 | cut -c1-300; fi
}
run check_venv_strict python3 -B tests/check_venv.py --strict --output "$E/check_venv_strict.json"
run make_test make test OUTPUT="$E/test"
grep -E '^(PASS|FAIL)|"status"|passed|FAILED' "$E/make_test.log" | grep -v '^PASS' | cut -c1-200 | tail -40
run assembly_checks python3 -B tests/assembly_checks.py --exact --output "$E/assembly_checks.json"
run verify_result_tamper python3 -B tests/verify_result_tamper.py --output "$E/verify_result_tamper.json"
run combine_core python3 -B tests/combine_core.py --output "$E/combine_core.json"
run compat_2026 python3 -B tests/compat_2026.py --output "$E/compat_2026.json"
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=1; fi
# 5. R1 with hostile inherited OpenMP controls (env(1) sets them for the one command only)
run invariance_hostile_env env OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none \
  python3 -B tests/validate.py --only invariance --output "$E/validate_invariance_hostile_env.json"
python3 - "$E" <<'PY' || status=1
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); out = {}
for name, f in (('make_test_validate', E / 'test' / 'validate.json'), ('hostile_env_invariance', E / 'validate_invariance_hostile_env.json')):
    if not f.exists(): out[name] = {'record': str(f), 'missing': True}; continue
    rec = json.loads(f.read_text()); rows = [t for t in rec['tests'] if t.get('test') == 'random_access_chunks']
    want = {'whole_1': 1, 'chunks_4': 4, 'chunks_1': 1}
    out[name] = {'record': str(f), 'status': rec.get('status'), 'invariance_rows': len(rows),
                 'team_sizes_verified_all': bool(rows) and all(r.get('team_sizes_verified') is True for r in rows),
                 'teams_observed_equal_request_all': bool(rows) and all(r.get('teams_observed') == want for r in rows),
                 'thread_identical_all': bool(rows) and all(r.get('thread_identical') is True for r in rows),
                 'distinct_teams_observed': sorted({json.dumps(r.get('teams_observed'), sort_keys=True) for r in rows}),
                 'omp_environment': sorted({r.get('omp_environment') for r in rows}),
                 'configurations': [f"{r['backend']} {r['sector']} L{r['L']} layout {r['layout']}" for r in rows]}
ok = all(not v.get('missing') and v['status'] == 'passed' and v['invariance_rows'] == 24 and v['team_sizes_verified_all']
         and v['teams_observed_equal_request_all'] and v['thread_identical_all'] for v in out.values())
out['ok'] = ok
(E / 'teams.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: (v if k == 'ok' else {x: v.get(x) for x in ('status', 'invariance_rows', 'team_sizes_verified_all', 'teams_observed_equal_request_all', 'distinct_teams_observed')}) for k, v in out.items()}, indent=1))
sys.exit(0 if ok else 1)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
