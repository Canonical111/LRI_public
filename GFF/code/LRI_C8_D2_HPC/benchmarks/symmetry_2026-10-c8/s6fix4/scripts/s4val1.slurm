#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-VAL-1 on symmetry for the Stage-6 fix-round-4 head (PLAN job table: a whole amdq node, -t 02:00:00), in the export
# built by s4build.slurm (afterok), plus the fix-round-4 checks that need the real workers on x86-64. Template:
# s6fix3/scripts/s3val1.slurm (job 570541) and the J-VAL-3 steps of s3val23.slurm (job 570535).
#   1. tests/check_venv.py --strict;
#   2. `make test OUTPUT=<evidence>/test`, literally, as ONE command (validate subset with the A-RPL-6 chunk merge on real
#      rows, now checked by W2's stricter chunk_merge; test-python with every fix-round-4 test, unit_orchestration on Linux
#      with the real worker; workflow, staging); it must exit 0;
#   3. tests/assembly_checks.py --exact, tests/verify_result_tamper.py, tests/combine_core.py, tests/compat_2026.py;
#   4. W1/W22's class: `tests/validate.py --check <test>/validate.json --gate J-VAL-1` (the acceptance check of the record
#      make test wrote) must exit 0;
#   5. W2 on real rows: `tests/validate.py --only none --bk8` (G-BK8: decimal against gmp, 400 kernels per sector at L7
#      and L8; the row rule c8-d2-bk8-row-rule-2 with max_abs, the tail fields and tail_argmax), then `--check bk8.json
#      --gate G-BK8`; the rows compared field by field with fix round 3's 570535 record;
#   6. W22: tests/thread_identity.py at its full default configuration (status "passed" only when coverage() is complete:
#      both workers x both sectors, 1/8/16/64 threads and 8 x 8 lanes, every team observed), then `--check`;
#   7. the executables are unchanged by make (sha256 before and after);
#   8. R1 with hostile inherited OpenMP controls: tests/validate.py --only invariance with OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true
#      OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none; every team verified (teams.json).
# Temporary package copies and campaigns on the node-local /tmp (TMPDIR). C8_SEEDS/C8_SITE/C8_INPUTS unset.
# DONE=<evidence dir of an earlier s4val1 on the same executables> (the rerun after a tests-only fix): steps 5, 6 and 8,
# which passed there, are not repeated (their records stay that run's); steps 1-4 and 7 run in full.
# Usage: C8_PACKAGE=... [DONE=...] sbatch --export=ALL --dependency=afterok:<s4build> -J c8d2-s4val1 s4val1.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s4val1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"; python3 --version; python3 -c 'import numpy;print("numpy",numpy.__version__)'
python3 -m pip freeze > "$E/pip_freeze.txt" 2>&1
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_ALLOW_NO_L8
env | grep -E '^(OMP_|GOMP_|KMP_)' | sort > "$E/omp_env_inherited.txt"; echo "inherited OpenMP controls: $(wc -l < "$E/omp_env_inherited.txt")"
env | grep -E '^(LD_PRELOAD|LD_AUDIT|LD_DYNAMIC_WEAK|GLIBC_TUNABLES|DYLD_)' | sort > "$E/loader_env_inherited.txt"; echo "inherited loader overrides (W7): $(wc -l < "$E/loader_env_inherited.txt")"
cat /etc/ld.so.preload > "$E/etc_ld_so_preload.txt" 2>&1 || echo "(no /etc/ld.so.preload)" > "$E/etc_ld_so_preload.txt"
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
run check_jval1 python3 -B tests/validate.py --check "$E/test/validate.json" --gate J-VAL-1
if [ -z "${DONE:-}" ]; then
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 16 --threads 4 --output "$E/bk8.json"
run check_bk8 python3 -B tests/validate.py --check "$E/bk8.json" --gate G-BK8
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
run check_thread_identity python3 -B tests/thread_identity.py --check "$E/thread_identity.json"
fi
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged"; else echo "executables CHANGED" >&2; status=1; fi
if [ -z "${DONE:-}" ]; then
run invariance_hostile_env env OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true OMP_NUM_THREADS=64 GOMP_SPINCOUNT=0 KMP_AFFINITY=none \
  python3 -B tests/validate.py --only invariance --output "$E/validate_invariance_hostile_env.json"
else  # steps 5, 6 and 8 stand from the earlier run on the same executables
  for f in bk8.json thread_identity.json validate_invariance_hostile_env.json; do cp -p "$DONE/$f" "$E/$f"; done; echo "steps 5, 6, 8 from $DONE" | tee "$E/done_from.txt"
fi
python3 - "$E" "$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/s6fix3/s3val23.570535.0/bk8.json" <<'PY' || status=1
import json, sys
from pathlib import Path
E, OLD = Path(sys.argv[1]), Path(sys.argv[2]); out = {}
for name, f in (('make_test_validate', E / 'test' / 'validate.json'), ('hostile_env_invariance', E / 'validate_invariance_hostile_env.json')):
    if not f.exists(): out[name] = {'record': str(f), 'missing': True}; continue
    rec = json.loads(f.read_text()); rows = [t for t in rec['tests'] if t.get('test') == 'random_access_chunks']
    want = {'whole_1': 1, 'chunks_4': 4, 'chunks_1': 1}
    out[name] = {'record': str(f), 'status': rec.get('status'), 'invariance_rows': len(rows),
                 'team_sizes_verified_all': bool(rows) and all(r.get('team_sizes_verified') is True for r in rows),
                 'teams_observed_equal_request_all': bool(rows) and all(r.get('teams_observed') == want for r in rows),
                 'thread_identical_all': bool(rows) and all(r.get('thread_identical') is True for r in rows),
                 'configurations': [f"{r['backend']} {r['sector']} L{r['L']} layout {r['layout']}" for r in rows]}
ok = all(not v.get('missing') and v['status'] == 'passed' and v['invariance_rows'] == 24 and v['team_sizes_verified_all']
         and v['teams_observed_equal_request_all'] and v['thread_identical_all'] for v in out.values())
# W2: the new G-BK8 record against fix round 3's (570535): the same tests, rows and maxima; the new row-rule fields recorded
new, old = json.loads((E / 'bk8.json').read_text()), json.loads(OLD.read_text())
key = lambda t: (t.get('sector'), t.get('L'))
nt, ot = {key(t): t for t in new.get('tests', [])}, {key(t): t for t in old.get('tests', [])}
common = ('graphs', 'rows', 'mp_rows', 'quad_points', 'mp_points', 'max_normalized_difference_mp_rows')
bk = {'status': new.get('status'), 'row_rule': new.get('row_rule'), 'acceptance': new.get('acceptance'),
      'tests': {f'{s} L{L}': {**{k: t.get(k) for k in common}, 'equal_to_570535': {k: t.get(k) == (ot.get((s, L)) or {}).get(k) for k in common},
                              **{k: v for k, v in t.items() if k.startswith(('max_', 'tail_')) and not isinstance(v, (list, dict))}}
                for (s, L), t in sorted(nt.items(), key=lambda x: str(x[0]))}}
bk['same_tests_as_570535'] = set(nt) == set(ot)
bk['equal_to_570535'] = bk['same_tests_as_570535'] and all(all(v['equal_to_570535'].values()) for v in bk['tests'].values())
out['bk8'] = bk
ti = json.loads((E / 'thread_identity.json').read_text())
out['thread_identity'] = {k: ti.get(k) for k in ('status', 'identical', 'team_sizes_verified', 'coverage')}
ok = ok and bk['status'] == 'passed' and bk['equal_to_570535'] and out['thread_identity']['status'] == 'passed'
out['ok'] = ok
(E / 'summary.json').write_text(json.dumps(out, indent=1, default=str) + '\n')
print(json.dumps({k: (v if not isinstance(v, dict) else {x: v.get(x) for x in ('status', 'invariance_rows', 'team_sizes_verified_all', 'row_rule', 'equal_to_570535', 'identical', 'team_sizes_verified')}) for k, v in out.items()}, indent=1, default=str))
sys.exit(0 if ok else 1)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
