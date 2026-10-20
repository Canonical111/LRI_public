#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The dd+mp256 J-FLAG gate RE-RUN after Stage-6 fix round 1 (template: stage5/close/scripts/clflag.slurm, job 570210).
# The record of 570210 no longer passes design.check_gate: it has no F1 coverage record (X1), no build binding of the F1
# tools to the executables (X2) and no verified OpenMP team sizes in F5 (X3); its F1 coverage itself was complete. The
# fixed harness (tests/numerics_flags.py, tests/thread_identity.py of the merged head) records all three. One whole amdq
# node (2 x EPYC 7543, 64 cores, 8 NUMA nodes; Ubuntu GCC 11.4), in the export built by s1build.slurm (afterok).
#   1. Identity: bin/c8d2_decimal and bin/c8d2_gmp are symmetry's default executables (619ddf7d..., 2cc5e88e...; A-RPL-8)
#      and bin/c8d2_gmp_dd+mp256 is the gated build d5df32ac... (s1build's profile.sha256), before and after the gate.
#   2. tests/numerics_flags.py --profile dd+mp256 at FULL scale (A-FLAG-3; no development option): a FRESH F1 baseline
#      (a reused baseline without a binding is refused, X2), the source snapshot and the byte-for-byte rebuild of both
#      executables in it (X2), F1 with its coverage (X1), F2 (the gates' fixed base seed 820262401: its 49 seeds are
#      already in symmetry's log, so none is added), F3, F4, F5 with the observed team sizes (X3).
#   3. design.check_gate(record, 'dd+mp256', inputs/inventory.json): the record must pass the fixed check (the route-(b)
#      freezes and plans use it).
# Evidence: <SCRATCH>/c8d2/evidence/<sha12>/s1flag.<job>.0/. Scratch on the node-local /tmp (TMPDIR).
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<s1build evidence dir> sbatch --export=ALL --dependency=afterok:<s1build> -J c8d2-s1flag s1flag.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s1flag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
check() {  # $1 = the sha256 listing to check
  python3 - "$1" "$BUILD_EVIDENCE/profile.sha256" <<'PY'
import sys
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
want = {'bin/c8d2_decimal': '619ddf7d1cf94d6229c841cd3fbe22574045ec65a1b69f8b827f1e26f180895f',
        'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17',
        'bin/c8d2_gmp_dd+mp256': 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d'}
assert open(sys.argv[2]).read().split()[0] == want['bin/c8d2_gmp_dd+mp256'], 's1build built another profile executable'
bad = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
print('identity', 'ok' if not bad else f'DIFFERS {bad}'); sys.exit(1 if bad else 0)
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
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
