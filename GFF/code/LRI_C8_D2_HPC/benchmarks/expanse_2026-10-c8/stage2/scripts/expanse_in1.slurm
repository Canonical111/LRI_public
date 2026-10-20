#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=2 --mem=8G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-in1-lowloop
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-IN-1 on Expanse (site deviation U1): tools/make_lowloop.py --verify with the cross-check against C63d's vendored
# inputs_d2_check (A-IN-1, A-IN-2, A-IN-6(a)). Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL expanse_in1.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=in1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN
mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
python3 -c 'import sys,mpmath; print("python", sys.version.split()[0], "mpmath", mpmath.__version__)'
cd "$C8_PACKAGE"
python3 -B tools/make_lowloop.py --verify --cross-check vendor/c8_assembly/inputs_d2_check --output "$E/make_lowloop_verify.json"
echo "J-IN-1 passed at $(date -Is)"
