#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-s3b-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 3 part B on Expanse (site deviation U1): the native executables built in the export of the commit under test
# (make, make gmp inspect, make sanitize, make c7ref), the two L8 packs hard-linked from an earlier export (make
# re-hashes every pack against inputs/manifest.json); then the forbidden-seed log $C8_SEEDS is created if absent and
# the L=2 control's seed (job 54637264, A-IN-6(b)) is registered in it (tools/seeds.py).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<directory with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3bbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS
cd "$C8_PACKAGE"
test ! -e bin && test ! -e build
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
t0=$(date +%s)
make -j8 2>&1 | tee "$E/make_all.log"
make -j8 gmp inspect 2>&1 | tee "$E/make_gmp_inspect.log"
make -j8 sanitize 2>&1 | tee "$E/make_sanitize.log"
make c7ref 2>&1 | tee "$E/make_c7ref.log"
echo "builds in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/c8d2_decimal_san bin/c8d2_gmp_san bin/ref/c7d2_decimal bin/ref/c7d2_gmp | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_decimal_san c8d2_gmp_san; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
if [ ! -e "$C8_SEEDS" ]; then python3 -B tools/seeds.py init; fi
python3 -B tools/seeds.py add --seed 7082694491065029298 --label 'L=2 control, A-IN-6(b), Expanse job 54637264 (Stage 3 part A)'
python3 -B tools/seeds.py list | tee "$E/seeds_after.txt"
echo "finished $(date -Is)"
