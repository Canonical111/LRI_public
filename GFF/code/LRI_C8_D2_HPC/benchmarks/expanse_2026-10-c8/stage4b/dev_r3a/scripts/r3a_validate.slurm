#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=32 --mem=64G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-r3a-val
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R3a, development: (1) tests/quad_differential.py (kernel ranges on the fixture blocks, >= 2^32 random pairs
# per operation, edge lists, injection self-test, ASan+UBSan run) at 32 threads; (2) G-L8SELF (A-RPL-7):
# tests/validate.py --l8self baseline/ (the Stage-3 c8d2_{decimal,gmp}) against bin/c8d2_* on the L8 sample (2,000
# kernels, 2 x 512 points, both backends, every scientific field exact); (3) validate.py --only replay (A-RPL-1/2/3 on
# the subset of J-VAL-1: G-REF, G-C7, G-JET). Node-local scratch for every staged graph and temporary file.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build> r3a_validate.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r3aval.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges baseline/c8d2_decimal baseline/c8d2_gmp | tee "$E/binaries.sha256"
status=0
t0=$(date +%s); python3 -B tests/quad_differential.py --output "$E/quad_differential.json" --threads 32 --scratch "$TMPDIR" > "$E/quad_differential.stdout" 2>&1 || status=$?
echo "quad_differential exit $status in $(( $(date +%s) - t0 )) s"; tail -40 "$E/quad_differential.stdout"
t0=$(date +%s); s=0; python3 -B tests/validate.py --only none --l8self baseline --jobs 8 --threads 4 --output "$E/l8self.json" > "$E/l8self.stdout" 2>&1 || s=$?
echo "l8self exit $s in $(( $(date +%s) - t0 )) s"; grep -E 'passed|FAIL|Error|differ' "$E/l8self.stdout" | tail -5; [ $s -eq 0 ] || status=$s
python3 -c "
import json;d=json.load(open('$E/l8self.json'))
for t in d['tests']:print(t['test'],t['sector'],t['backend'],'graphs',t['graphs'],'rows',t['rows'],'quad',t['quad_points'],'mp',t['mp_points'])" 2>&1 | tail -6
t0=$(date +%s); s=0; python3 -B tests/validate.py --only replay --jobs 8 --threads 4 --output "$E/replay.json" > "$E/replay.stdout" 2>&1 || s=$?
echo "replay exit $s in $(( $(date +%s) - t0 )) s"; tail -3 "$E/replay.stdout" | cut -c1-300; [ $s -eq 0 ] || status=$s
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
