#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00
#SBATCH -J c8d2-gen2-build
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# J-GEN-2 (PLAN.md Verification): L7+L8 build of both sectors at 64 threads into BeeGFS staging, every A-INV-3 gate
# (gen/gates.py; Kirchhoff and forest counts in a 64-process pool), then gen/publish_inventory.py, which runs only
# after every gate has exited 0 (gen/run_l8.sh). The frozen tree goes to C8_GEN_TARGET.
#   C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/<sha12> C8_GEN_COMMIT=<40-hex> C8_GEN_TARGET=<.../inventory8_d2> \
#     sbatch --export=ALL slurm/gen/build_l8.slurm
# H7: one amdq node; survey the AMD pool (amdq, amddebugq, amdpreq) for live c8d2- jobs before submitting (cap 4).
set -euo pipefail
source "$HOME/c8d2/env.sh"
# Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*,
# KMP_* from a module or the submitting shell) reaches the generator programs; each gets OMP_NUM_THREADS explicitly.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_DYNAMIC=FALSE
: "${C8_PACKAGE:?}" "${C8_GEN_COMMIT:?}" "${C8_GEN_TARGET:?}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RUN=gen2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=/mnt/beegfs/zzheng1/c8d2/evidence/$TAG/$RUN
W=/mnt/beegfs/zzheng1/c8d2/gen/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"
mkdir "$E" "$W"
echo "job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) at $(date -Is); evidence $E; work $W"
lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)'
g++ --version | head -1
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
