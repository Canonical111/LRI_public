#!/bin/bash
#SBATCH -p amddebugq,amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Control run for J-SWEEP-3 (570035): its rows differ from J-SWEEP-2's in the last digits (relative ~1e-16) for the same
# task (same seed, net, begin/end, quad and mp counters). This job replans the IDENTICAL J-SWEEP-3 campaign (same
# arguments and seed) into a new directory and runs it on an AMD EPYC node with the same process shape as the Intel run
# (2 slots x 20 threads; s5sweep3_driver.py --procs 2), then compares its graph_replicates.csv rows with both:
#   equal to J-SWEEP-3 (Intel)  -> the difference comes from the block composition / thread count, not the CPU;
#   equal to J-SWEEP-2 (AMD)    -> the native's rows depend on the CPU (Intel Xeon Gold 6148 vs AMD EPYC 75x3).
# Usage: C8_PACKAGE=... SWEEP_SEED=... W2=... W3=... DRIVER=... ROWS=<s5sweep3_rows.py> sbatch --export=ALL -J c8d2-s5sw3amd s5sweep3amd.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SWEEP_SEED:?}" "${W2:?}" "${W3:?}" "${DRIVER:?}" "${ROWS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5sw3amd.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=<SCRATCH>/c8-d2/sweep3amd-$TAG; CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); campaign $W; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
S=/tmp/c8d2_$SLURM_JOB_ID; mkdir -p "$S"; status=0
python3 -B tools/production.py plan "$W" --pilot --points 512 --replicates 2 --test-graphs 168 --test-selection stratified --backend gmp \
  --threads 8 --seed "$SWEEP_SEED" --cost-model "$CM1" > "$E/plan.stdout" 2>&1 || { echo "plan failed"; tail -5 "$E/plan.stdout"; exit 3; }
python3 -B tools/ledger.py register "$W" --role sweep | tee "$E/ledger_register.txt"
python3 -B "$DRIVER" "$C8_PACKAGE" "$W" --threads 20 --procs 2 --scratch "$S" --merge-jobs 20 > "$E/driver.stdout" 2>&1 || status=$?
echo "runner + merge exit $status"; tail -3 "$E/driver.stdout" | cut -c1-200
cmp <(python3 -c "import json,sys;m=json.load(open('$W/manifest.json'));print(json.dumps(m['jobs']))") <(python3 -c "import json,sys;m=json.load(open('$W3/manifest.json'));print(json.dumps(m['jobs']))") && echo "job list identical to J-SWEEP-3's" | tee "$E/jobs_identical.txt"
python3 -B "$ROWS" "$W" "$W3" "$E/rows_vs_sweep3_intel.json"; a=$?
python3 -B "$ROWS" "$W" "$W2" "$E/rows_vs_sweep2_amd.json"; b=$?
echo "rows vs J-SWEEP-3 (Intel): exit $a; rows vs J-SWEEP-2 (AMD): exit $b"
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
