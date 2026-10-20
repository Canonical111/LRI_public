#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 03:00:00 --no-requeue
#SBATCH -J c8d2-gen2-build
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# J-GEN-2 on Expanse (site deviation U1; the symmetry script is slurm/gen/build_l8.slurm): the L7+L8 build of both
# sectors on one whole compute node (2 x AMD EPYC 7742, 128 cores) into Lustre staging, every A-INV-3 gate
# (gen/gates.py; Kirchhoff and forest counts in a 128-process pool), then gen/publish_inventory.py, which runs only
# after every gate has exited 0 (gen/run_l8.sh). The frozen tree goes to C8_GEN_TARGET (a staging target; the
# shared copies are made later with `publish_inventory.py copy`, each verified against the MANIFEST pin).
#   C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_GEN_COMMIT=<40-hex> C8_GEN_TARGET=$C8_DATA/gen/<sha12>/inventory8_d2 \
#     sbatch --export=ALL slurm/gen/expanse_build_l8.slurm
# Expanse sharing (agreed with C63d): at most 4 compute nodes per session during development; check
# `squeue -A yun124` against 22 running / 54 submitted normal-QOS jobs for the whole account before submitting.
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
# Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*,
# KMP_* from a module or the submitting shell) reaches the generator programs; each gets OMP_NUM_THREADS explicitly.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_DYNAMIC=FALSE
: "${C8_PACKAGE:?}" "${C8_GEN_COMMIT:?}" "${C8_GEN_TARGET:?}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RUN=gen2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN
W=$C8_DATA/gen/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"
mkdir "$E" "$W"
echo "job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) at $(date -Is); evidence $E; work $W"
lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)'
g++ --version | head -1
tar --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
NCPU=$(nproc)
echo "threads: $NCPU (exclusive node)"
export C8_GEN_BIN="$W/bin" C8_GEN_STAGE="$W/stage" C8_GEN_THREADS=$NCPU C8_GEN_JOBS=$NCPU
make -C "$C8_PACKAGE/gen" BIN="$C8_GEN_BIN"
cp "$C8_GEN_BIN"/*.build.txt "$E"/
bash "$C8_PACKAGE/gen/run_l8.sh"
cp -r "$C8_GEN_STAGE/gates" "$E/gates"
sha256sum "$C8_GEN_TARGET/MANIFEST.json" | tee "$E/MANIFEST.sha256"
md5sum "$C8_GEN_TARGET/MANIFEST.json" | tee "$E/MANIFEST.md5"
python3 -B "$C8_PACKAGE/gen/verify_inventory.py" "$C8_GEN_TARGET" --pin "$(cut -c1-64 "$E/MANIFEST.sha256")" \
  --output "$E/verify_inventory.json"
du -sh "$C8_GEN_STAGE" "$C8_GEN_TARGET"
echo "J-GEN-2 finished at $(date -Is)"
