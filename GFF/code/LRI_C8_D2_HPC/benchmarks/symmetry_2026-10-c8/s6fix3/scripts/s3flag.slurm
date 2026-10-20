#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The dd+mp256 J-FLAG gate on the NEW profile build of Stage-6 fix round 3 (Z4 changed src/kernel.hpp, so the gated
# build d5df32ac... of jobs 570210/570373 is gone; the user approved dd+mp256 for production after the pilot, and the
# gate must pass again on the build that will run). Template: s6fix1/scripts/s1flag.slurm (job 570373). One whole amdq
# node (2 x EPYC 7543, 64 cores, 8 NUMA nodes; Ubuntu GCC 11.4), in the export built by s3build.slurm (afterok).
#   1. Identity: bin/c8d2_decimal, bin/c8d2_gmp and bin/c8d2_gmp_dd+mp256 are s3build's (its binaries_after_profile.sha256
#      and profile.sha256), before and after the gate.
#   2. tests/numerics_flags.py --profile dd+mp256 at FULL scale (A-FLAG-3; no development option): a FRESH F1 baseline,
#      the source snapshot and the byte-for-byte rebuild of both executables in it (X2), F1 with its coverage (X1) and the
#      libgmp provenance of both F1 tools (Y1; since fix round 3 recorded for the baseline too, Z19), F2 (the gates' fixed
#      base seed 820262401: its 49 seeds are already in symmetry's log, so none is added), F3, F4, F5 with the observed
#      team sizes (X3).
#   3. design.check_gate(record, 'dd+mp256', inputs/inventory.json) of this export (with fix round 3's Z19 check of the
#      libgmp provenance): the record must pass; the route-(b) freezes (s3des) and every later plan use it.
#   4. For the record: F2's totals and F3 are compared with 570373's (identical streams, so a valid-input-preserving Z4
#      gives the same numbers), and F4's exact-path median with 570373's (the exact executable's speed on the same
#      workload and node type: Z4 adds only load-time checks).
# Evidence: <SCRATCH>/c8d2/evidence/<sha12>/s3flag.<job>.0/. Scratch on the node-local /tmp (TMPDIR).
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<s3build evidence dir> sbatch --export=ALL --dependency=afterok:<s3build> -J c8d2-s3flag s3flag.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3flag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; seeds log $C8_SEEDS; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"; sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
sha256sum "$C8_SEEDS" | tee "$E/seeds_log_before.sha256"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_dd+mp256"
sha256sum $X | tee "$E/before.sha256"
check() {  # $1 = the sha256 listing to check, against s3build's
  python3 - "$1" "$BUILD_EVIDENCE" <<'PY'
import sys
from pathlib import Path
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
B = Path(sys.argv[2]); want = {l.split()[1]: l.split()[0] for l in (B / 'binaries_after_profile.sha256').read_text().splitlines()}
want = {k: want[k] for k in ('bin/c8d2_decimal', 'bin/c8d2_gmp')}; want['bin/c8d2_gmp_dd+mp256'] = (B / 'profile.sha256').read_text().split()[0]
bad = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
print('identity', 'ok' if not bad else f'DIFFERS {bad}', {k: v[:12] for k, v in want.items()}); sys.exit(1 if bad else 0)
PY
}
check "$E/before.sha256" || exit 3
status=0; t=$(date +%s)
echo "== numerics_flags.py --profile dd+mp256 (full scale) $(date -Is)"
python3 -B tests/numerics_flags.py --profile dd+mp256 --seeds-log "$C8_SEEDS" --output "$E/jflag_dd+mp256" --scratch "$TMPDIR" || status=$?
echo "numerics_flags.py exit $status after $(( $(date +%s) - t )) s"
sha256sum $X > "$E/after.sha256"; check "$E/after.sha256" || status=3
sha256sum "$C8_SEEDS" | tee "$E/seeds_log_after.sha256"
python3 - "$E/jflag_dd+mp256/numerics_flags.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(json.dumps({k: d.get(k) for k in ('mode', 'profile_name', 'status', 'verdicts', 'development', 'error', 'wall_seconds', 'f2_seeds')}, indent=1))
F2 = d.get('F2') or {}; F4 = d.get('F4') or {}
print('F2 total', json.dumps(F2.get('total')), 'per_task', json.dumps(F2.get('per_task'))[:600])
print('F4 speedup', json.dumps(F4.get('speedup_exact_over_profile')), 'medians', json.dumps(F4.get('medians'))[:600])
PY
python3 -B - "$E/jflag_dd+mp256/numerics_flags.json" "$E/check_gate.json" <<'PY' || status=4
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import design
inv = json.loads(Path('inputs/inventory.json').read_text())
try:
    g = design.check_gate(Path(sys.argv[1]), 'dd+mp256', inv); rec = {'passed': True, 'gate': g}
except Exception as e:
    rec = {'passed': False, 'error': str(e)}
Path(sys.argv[2]).write_text(json.dumps(rec, indent=1) + '\n')
print('design.check_gate:', 'PASSED' if rec['passed'] else 'REFUSED: ' + rec['error'][:600])
sys.exit(0 if rec['passed'] else 4)
PY
# 4. against the fix-round-1 gate 570373 (the same streams; F4 timing only for the record)
python3 - "$E/jflag_dd+mp256/numerics_flags.json" "$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/s6fix1/s1flag.570373.0/jflag_dd+mp256/numerics_flags.json" "$E/vs_570373.json" <<'PY' || true
import json, sys
n, o = (json.load(open(f)) for f in sys.argv[1:3])
def g(d, *ks):
    for k in ks: d = d.get(k) if isinstance(d, dict) else None
    return d
cmp = {'F2_total_equal': g(n, 'F2', 'total') == g(o, 'F2', 'total'), 'F2_per_task_equal': g(n, 'F2', 'per_task') == g(o, 'F2', 'per_task'),
       'F3_counters_equal': n.get('F3_counters') == o.get('F3_counters'), 'F3_tiers_equal': n.get('F3_tiers') == o.get('F3_tiers'),
       'F1_verdict_equal': g(n, 'F1', 'verdict') == g(o, 'F1', 'verdict'), 'F1_coverage_sectors_equal': g(n, 'F1', 'coverage', 'sectors') == g(o, 'F1', 'coverage', 'sectors'),
       'F4_speedup_new': g(n, 'F4', 'speedup_exact_over_profile'), 'F4_speedup_570373': g(o, 'F4', 'speedup_exact_over_profile'),
       'F4_medians_new': g(n, 'F4', 'medians'), 'F4_medians_570373': g(o, 'F4', 'medians')}
open(sys.argv[3], 'w').write(json.dumps(cmp, indent=1, default=str) + '\n'); print(json.dumps(cmp, indent=1, default=str)[:3000])
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
