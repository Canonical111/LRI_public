#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-gen1-regress
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# J-GEN-1 (PLAN.md Verification): make -C gen, the A-INV-1 tests and the A-INV-2 regression at L3..L7 on x86-64.
# Submit from anywhere (sharedq: --no-requeue, and every output goes to a fresh <name>.<jobid>.<restart> directory):
#   C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/<sha12> sbatch --export=ALL slurm/gen/regress.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
# Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*,
# KMP_* from a module or the submitting shell) reaches the generator programs; each gets OMP_NUM_THREADS explicitly.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_DYNAMIC=FALSE
: "${C8_PACKAGE:?C8_PACKAGE must name the git archive export}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RUN=gen1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=/mnt/beegfs/zzheng1/c8d2/evidence/$TAG/$RUN
W=/mnt/beegfs/zzheng1/c8d2/gen/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"
mkdir "$E" "$W"
echo "job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) at $(date -Is); evidence $E; work $W"
lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)'
g++ --version | head -1
python3 -c 'import sys,numpy,scipy,mpmath,sympy; print("python", sys.version.split()[0], "numpy", numpy.__version__, "scipy", scipy.__version__, "mpmath", mpmath.__version__, "sympy", sympy.__version__)'
cd "$C8_PACKAGE"
make -C gen BIN="$W/bin"
cp "$W"/bin/*.build.txt "$E"/
python3 -B gen/check_sources.py --output "$E/check_sources.json"
python3 -B gen/test_keys.py --bin "$W/bin" --output "$E/test_keys.json"
python3 -B gen/test_run_l8.py --output "$E/test_run_l8.json"
python3 -B gen/test_verify_inventory.py --output "$E/test_verify_inventory.json"
python3 -B gen/test_regress.py --output "$E/test_regress.json"
python3 -B gen/test_handoff_inventory.py --output "$E/test_handoff_inventory.json"
python3 -B gen/regress.py --classes reference/LRI_C7_d2_progress/reference --threads 1,8 --explain \
  --bin "$W/bin" --work "$W/work" --output "$E/regress_L3_L7.json"
rm -rf "$W/work"
echo "J-GEN-1 passed at $(date -Is)"
