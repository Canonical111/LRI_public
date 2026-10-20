#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=48G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-in2a-regen
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-IN-2, part a, on Expanse (site deviation U1): build bin/c8d2_inspect and regenerate every input from the frozen
# inventory8_d2 tree with the inspector over all 24,173 kernels (A-IN-3). The regenerated manifest.json,
# inventory.json and L7 packs are committed as generated data; part b verifies that commit (make inputs-l8,
# tests/check_inputs.py). Usage: C8_PACKAGE=... C8_INVENTORY=<tree> C8_PIN=<MANIFEST sha256> sbatch --export=ALL expanse_in2a.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_INVENTORY:?}" "${C8_PIN:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=in2a.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; W=$C8_DATA/inputs/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"; mkdir "$E" "$W"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; tree $C8_INVENTORY; evidence $E; work $W"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
cd "$C8_PACKAGE"
make inspect
cp bin/c8d2_inspect.build.txt "$E/"; sha256sum bin/c8d2_inspect | tee "$E/c8d2_inspect.sha256"
bin/c8d2_inspect --describe | tee "$E/c8d2_inspect.describe.json"
t0=$(date +%s)
python3 -B tools/prepare_inputs.py --regenerate "$W/inputs" --inventory "$C8_INVENTORY" --pin "$C8_PIN" \
  --inspect bin/c8d2_inspect --threads "$SLURM_CPUS_PER_TASK"
echo "regenerated in $(( $(date +%s) - t0 )) s"
cp "$W/inputs/manifest.json" "$W/inputs/inventory.json" "$E/"
(cd "$W/inputs" && sha256sum packs/*) | tee "$E/packs.sha256"
du -sh --apparent-size "$W/inputs"
echo "J-IN-2a finished at $(date -Is)"
