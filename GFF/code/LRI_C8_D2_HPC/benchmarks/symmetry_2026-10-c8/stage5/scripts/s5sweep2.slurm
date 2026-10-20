#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SWEEP-2 on symmetry (PLAN job table J-SWEEP-1/2; A-PERF-4) on the FINAL default binary (export 5d7586e9f1ab, built
# by s5build): slurm/sweep.sh -> tools/sweep.py, a test-only plan of all 24,173 graphs, both campaigns, 2 replicates x
# 512 points, chunked with J-SWEEP-1's cost model (Expanse 54641706, the Stage-3 baseline; no bootstrap), the ledger
# registration (role sweep) before any index, 8 x 8 NUMA-pinned process slots (--threads 8, R5b default lanes),
# heaviest first; merge (32 processes); the measured cost model of the final binary on symmetry AMD (every
# campaign:sector:L:graph key, R05) and the campaign-keyed calibration rows (written to a copy in the evidence folder,
# never to the export's tools/calibration.json); sweep.sh adds the base seed to $C8_SEEDS (symmetry), and the Mac-side
# seedsync.sh then merges it into Expanse's log and the mirror. Default path: no --rates, no --numerics, no GMP_PREFIX.
# Usage: C8_PACKAGE=... SWEEP_SEED=<fresh> sbatch --export=ALL --dependency=... -J c8d2-s5sweep2 s5sweep2.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SWEEP_SEED:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5sweep2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=<SCRATCH>/c8-d2/sweep2-$TAG; CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $W; evidence $E; chunking model $CM1"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp "$CM1" | tee "$E/binaries.sha256"
cp tools/calibration.json "$E/calibration_before.json"; cp tools/calibration.json "$E/calibration.json"
S=/tmp/c8d2_$SLURM_JOB_ID; mkdir -p "$S"; echo "node-local scratch $S"
python3 -B tools/seeds.py check "$SWEEP_SEED" | tee "$E/seed_check_before.txt"
t0=$(date +%s); status=0
bash slurm/sweep.sh "$W" --seed "$SWEEP_SEED" --points 512 --replicates 2 --threads 8 --cost-model "$CM1" \
  --forbid-seeds-from "$C8_SEEDS" --merge-jobs 32 --cost-model-out "$E/cost_model.json" --calibration "$E/calibration.json" --scratch "$S" \
  > "$E/sweep.stdout" 2>&1 || status=$?
echo "sweep exit $status after $(( $(date +%s) - t0 )) s"; tail -25 "$E/sweep.stdout"
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl"
python3 -B tools/production.py status "$W" --json > "$E/status.json" 2>&1 || true
python3 -B tools/seeds.py check "$SWEEP_SEED" | tee "$E/seed_check_after.txt"
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
