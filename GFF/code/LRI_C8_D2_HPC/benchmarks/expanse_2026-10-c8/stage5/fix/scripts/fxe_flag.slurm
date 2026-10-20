#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:30:00 --no-requeue
#SBATCH -J c8d2-fxe-flag
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# The J-FLAG gate the user required before the first production use of dd+mp256 (user check-in 2026-10-05: "dd+mp256
# approved for production after the pilot (C62d PLAN-REVIEW-LOG)"; a short J-FLAG gate of the exact dd+mp256 build, no
# exp1, runs first). One exclusive compute node (2 x EPYC 7742, 128 cores; submitted with --exclude=<NODE>), in the
# merged head's export built by fxe_exp1.slurm (afterok):
#   1. `make gmp NUMERICS=dd,mp256` builds bin/c8d2_gmp_dd+mp256; A-RPL-8: the default executables bin/c8d2_decimal and
#      bin/c8d2_gmp keep their sha256 (99a51c1d..., 1d2a2181...) before and after; --describe and the build record of
#      the profile executable (numerics dd+mp256, not diagnostic, no development parameter override).
#   2. `tests/numerics_flags.py --profile dd+mp256` at FULL scale (A-FLAG-3: F1 on the whole A-RPL-5 point set against an
#      exact F1 baseline computed in the run, F2 the paired mini-campaign over every L3-L8 graph, F3 from F1 and F2, F4
#      the L8 sweep sample with interleaved repeats, F5 thread identity), status "passed" only at full scale. F2's base
#      seed is the gates' fixed seed (820262401); the run registers its 49 seeds in $C8_SEEDS (Expanse's log) or finds
#      them "present" (registered in Stage 5); the Mac driver checks them against symmetry's log and the mirror.
# Evidence: $C8_DATA/evidence/<sha12>/fxeflag.<job>.0/ (jflag_dd+mp256/numerics_flags.json, f1/ f2/ f4/ f5/, identity.json).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --exclude=<NODE> --dependency=afterok:<fxe_exp1> fxe_flag.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=fxeflag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; seeds log $C8_SEEDS; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1; sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || { echo "no node-local scratch $S" >&2; exit 69; }
export TMPDIR=$S/tmp OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "scratch $S"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_decimal bin/c8d2_gmp | tee "$E/defaults_before.sha256"
t0=$(date +%s)
make gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "profile build in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_decimal bin/c8d2_gmp > "$E/defaults_after.sha256"; sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
bin/c8d2_gmp_dd+mp256 --describe > "$E/describe_dd+mp256.json"; cp bin/c8d2_gmp_dd+mp256.build.json "$E/"
python3 - "$E" <<'PY' || exit 3
import json, sys
from pathlib import Path
E = Path(sys.argv[1])
want = {'bin/c8d2_decimal': '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf',
        'bin/c8d2_gmp': '1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa'}
rd = lambda f: {l.split()[1]: l.split()[0] for l in (E / f).read_text().splitlines()}
before, after = rd('defaults_before.sha256'), rd('defaults_after.sha256')
d = json.loads((E / 'describe_dd+mp256.json').read_text()); b = json.loads((E / 'c8d2_gmp_dd+mp256.build.json').read_text())
rec = {'A-RPL-8': {k: {'expected': v, 'before': before.get(k), 'after': after.get(k), 'unchanged': before.get(k) == after.get(k) == v} for k, v in want.items()},
       'profile': {'sha256': (E / 'profile.sha256').read_text().split()[0], 'numerics': d.get('numerics'), 'diagnostic': d.get('diagnostic'),
                   'numerics_params': d.get('numerics_params'), 'build_record_keys': sorted(b)}}
rec['ok'] = all(v['unchanged'] for v in rec['A-RPL-8'].values()) and d.get('numerics') == 'dd+mp256' and d.get('diagnostic') is False
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('A-RPL-8 defaults unchanged and profile dd+mp256 (not diagnostic):', rec['ok']); sys.exit(0 if rec['ok'] else 3)
PY
status=0; t=$(date +%s)
echo "== numerics_flags.py --profile dd+mp256 (full scale)"
python3 -B tests/numerics_flags.py --profile dd+mp256 --output "$E/jflag_dd+mp256" --scratch "$TMPDIR" || status=$?
echo "numerics_flags.py exit $status after $(( $(date +%s) - t )) s"
python3 - "$E/jflag_dd+mp256/numerics_flags.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(json.dumps({k: d.get(k) for k in ('status', 'verdicts', 'development', 'wall_seconds')}))
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
