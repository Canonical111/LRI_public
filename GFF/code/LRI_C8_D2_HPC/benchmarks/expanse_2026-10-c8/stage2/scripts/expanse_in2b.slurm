#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=48G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-in2b-check
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-IN-2, part b, on Expanse (site deviation U1), on an export of the commit that holds the generated inputs:
# make inspect, make inputs-l8 INVENTORY=<tree> (the L8 packs, verified against the committed manifest), then
# tests/check_inputs.py with the tree and the inspector (A-IN-3/4/5: every generated file byte for byte, the L8 packs
# present), tests/check_vendored.py (A-ASM-1(a)+(b) on the cluster export) and, informational here (a G3/J-VAL-1
# item), tests/vendored_isolated.py --in-place. Usage: C8_PACKAGE=... C8_INVENTORY=<tree> sbatch --export=ALL expanse_in2b.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_INVENTORY:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=in2b.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN
mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; tree $C8_INVENTORY; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
cd "$C8_PACKAGE"
make inspect
cp bin/c8d2_inspect.build.txt "$E/"; sha256sum bin/c8d2_inspect | tee "$E/c8d2_inspect.sha256"
t0=$(date +%s); make inputs-l8 INVENTORY="$C8_INVENTORY" | tee "$E/inputs_l8.out"; echo "inputs-l8 in $(( $(date +%s) - t0 )) s"
python3 -B tests/check_inputs.py --inventory "$C8_INVENTORY" --inspect bin/c8d2_inspect --threads "$SLURM_CPUS_PER_TASK" \
  --output "$E/check_inputs.json"
python3 -B tests/check_vendored.py --no-review-record --output "$E/check_vendored.json"
python3 -B tests/vendored_isolated.py --in-place --output "$E/vendored_isolated_in_place.json" \
  || echo "vendored_isolated --in-place did not pass (informational at this stage: a G3/J-VAL-1 item); see the record"
echo "J-IN-2b finished at $(date -Is)"
