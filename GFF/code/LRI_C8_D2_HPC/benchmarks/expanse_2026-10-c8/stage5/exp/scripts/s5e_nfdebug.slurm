#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:20:00 --no-requeue
#SBATCH -J c8d2-s5e-nfdebug
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5 on Expanse, diagnosis of J-EXP-1b's second failure: tests/test_numerics_flags.py group f2_profile failed on
# the debug node (its 'dse' F2 run wrote no record) although it passes on the Mac. This job runs that group alone,
# with test_numerics_flags.flags wrapped so that every numerics_flags.py call's exit code and stderr/stdout tails are
# printed, twice: on the job's 16 CPUs, and under `taskset -c 0-3`. Fakes only (no real worker), seconds of CPU.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL s5e_nfdebug.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s5enfdebug.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E; nproc $(nproc)"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
cd "$C8_PACKAGE" || exit 64
cat > "$TMPDIR/nfdbg.py" <<'PY'
import sys, json
sys.path.insert(0, 'tests'); import test_numerics_flags as T
orig = T.flags
def flags(td, out, *a, **k):
    cp, r = orig(td, out, *a, **k)
    print(f'--- flags({out}) exit {cp.returncode}, record {"present" if r else "MISSING"}; F2 {None if not r else (r.get("F2") or {}).get("status", r.get("F2") is not None)}', flush=True)
    if cp.returncode or not r or r.get('F2') is None:
        print('stderr tail:\n' + cp.stderr[-4000:] + '\nstdout tail:\n' + cp.stdout[-2500:], flush=True)
    return cp, r
T.flags = flags
try: T.test_f2_profile(); print('f2_profile PASSED')
except Exception as e:
    import traceback; traceback.print_exc(); print('f2_profile FAILED'); sys.exit(1)
PY
python3 -B "$TMPDIR/nfdbg.py" > "$E/f2_profile_16cpu.log" 2>&1; a=$?; echo "16 CPUs: exit $a"; grep -E '^---|PASSED|FAILED' "$E/f2_profile_16cpu.log"
taskset -c 0-3 python3 -B "$TMPDIR/nfdbg.py" > "$E/f2_profile_4cpu.log" 2>&1; b=$?; echo "taskset 0-3: exit $b"; grep -E '^---|PASSED|FAILED' "$E/f2_profile_4cpu.log"
rm -rf "$TMPDIR"; echo "finished $(date -Is), $a $b"
