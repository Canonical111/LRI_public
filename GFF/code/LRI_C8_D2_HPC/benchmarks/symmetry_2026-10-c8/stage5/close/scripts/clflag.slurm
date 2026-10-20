#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The J-FLAG gate the user required before the first production use of dd+mp256 (user check-in 2026-10-05: "dd+mp256
# approved for production after the pilot (C62d PLAN-REVIEW-LOG)"; a short J-FLAG gate of the exact dd+mp256 build, no
# exp1, runs first), on the production site symmetry (user rule 2026-10-05, "symmetry first"): one whole amdq node
# (2 x EPYC 7543, 64 cores, 8 NUMA nodes; Ubuntu GCC 11.4), in the export built by clbuild.slurm (afterok).
# It replaces benchmarks/expanse_2026-10-c8/stage5/fix/scripts/fxe_flag.slurm, which was never submitted.
#   1. Identity: bin/c8d2_decimal and bin/c8d2_gmp are symmetry's default executables (619ddf7d..., 2cc5e88e...; A-RPL-8)
#      and bin/c8d2_gmp_dd+mp256 is the executable clbuild.slurm built (its profile.sha256), before and after the gate.
#   2. tests/numerics_flags.py --profile dd+mp256 at FULL scale (A-FLAG-3; no development option, so its record says
#      "passed" only if every gate passes): F1 on the whole A-RPL-5 point set against the exact F1 baseline computed in
#      this run on this node (450-digit references; relative error <= 1e-6 per point), F2 the paired mini-campaign over
#      every L3-L8 graph (|dC8| + 3 SE_d <= 0.062 in total and per (sector, L >= 7); per-task normalized <= 1e-9),
#      F3 from F1 and F2, F4 the L8 sweep sample with 3 interleaved repeats of each binary on this node (median), F5
#      thread identity (1, 8, 16, 64 threads and 8 x 8 lanes). F2 registers its 49 seeds (the gates' fixed base seed
#      820262401 and its derived seeds) in symmetry's log ($C8_SEEDS, passed as --seeds-log) or finds them "present".
# Evidence: <SCRATCH>/c8d2/evidence/<sha12>/clflag.<job>.0/ (jflag_dd+mp256/numerics_flags.json, f1/ f2/ f4/
# f5/ f1_baseline/, identity.json). Scratch on the node-local /tmp (TMPDIR).
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<clbuild evidence dir> sbatch --export=ALL --dependency=afterok:<clbuild> -J c8d2-clflag clflag.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=clflag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
        'bin/c8d2_gmp_dd+mp256': open(sys.argv[2]).read().split()[0]}
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
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
