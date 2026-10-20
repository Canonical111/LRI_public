#!/bin/bash
#SBATCH -p amdq,amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Follow-up of the final J-VAL-1 (570027): its unit_orchestration run failed only in the test group `lanes`, where the
# test's lane worker runs with C8_LANES=2 on the job's whole affinity set; on a 64-core symmetry node that gives lanes
# of 32 cores, more than the test plan's checkpoint_tasks=8, and lanes.py refuses (64) as designed. The Expanse J-VAL-1
# runs used 16-CPU shared jobs (lanes of 8 cores). This job reruns ONLY that group on the same node type twice:
#   full     the whole 64-core affinity set (expected: the same refusal);
#   taskset  under `taskset -c 0-15` (16 CPUs = 8 physical cores per lane: the Expanse shared-job geometry).
# It also reruns the other two J-VAL-1 commands that failed there for environment/test reasons:
#   vendored_isolated --in-place  (570027: the symmetry venv had no pytest; pytest 9.1.1, Expanse's version, was then
#                                  installed into ~/c8d2/venv, pip freeze before/after kept);
#   test_numerics_flags           (570027: f2_profile case dse passes repr(numpy.float64) = "np.float64(...)" under
#                                  numpy 2.3.5 to the fake worker; nf_dse_repro.py shows it; a test defect, recorded).
# Usage: C8_PACKAGE=... REPRO=<nf_dse_repro.py> sbatch --export=ALL -J c8d2-s5val1b s5val1b.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${REPRO:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val1b.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|^CPU\(s\)|Thread' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS
cd "$C8_PACKAGE" || exit 64
python3 -B tests/unit_orchestration.py --only lanes --output "$E/lanes_full.json" > "$E/lanes_full.log" 2>&1; a=$?
echo "full affinity ($(nproc) CPUs): exit $a"; grep -E '^PASS|^FAIL|C8: ' "$E/lanes_full.log" | head -5 | cut -c1-300
taskset -c 0-15 python3 -B tests/unit_orchestration.py --only lanes --output "$E/lanes_taskset16.json" > "$E/lanes_taskset16.log" 2>&1; b=$?
echo "taskset -c 0-15: exit $b"; grep -E '^PASS|^FAIL|C8: ' "$E/lanes_taskset16.log" | head -5 | cut -c1-300
python3 -c 'import pytest,numpy;print("pytest",pytest.__version__,"numpy",numpy.__version__)' | tee "$E/versions.txt"
python3 -B tests/vendored_isolated.py --in-place --output "$E/vendored_isolated.json" > "$E/vendored_isolated.log" 2>&1; c=$?
echo "vendored_isolated --in-place: exit $c"; tail -2 "$E/vendored_isolated.log" | cut -c1-300
python3 -B tests/test_numerics_flags.py --output "$E/test_numerics_flags.json" > "$E/test_numerics_flags.log" 2>&1; d=$?
echo "test_numerics_flags: exit $d"; tail -1 "$E/test_numerics_flags.log" | cut -c1-300
python3 -B "$REPRO" "$C8_PACKAGE" > "$E/nf_dse_repro.log" 2>&1; echo "nf_dse_repro: exit $?"; grep -E "ValueError|dse rc" "$E/nf_dse_repro.log" | head -3
rm -rf "$TMPDIR"
echo "finished $(date -Is), lanes full $a, lanes taskset $b, vendored_isolated $c, test_numerics_flags $d"
[ $b -eq 0 ] && [ $c -eq 0 ]
