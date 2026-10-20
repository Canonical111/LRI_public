#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-s3-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 3, PLAN component C, on Expanse (site deviation U1): every native executable built from scratch in the export
# of the commit under test. `make` (bin/c8d2_decimal plus the input verification, which hashes every pack, the two
# hard-linked L8 packs included, against inputs/manifest.json), `make gmp`, `make inspect`, `make profile ratiohist
# sanitize` and `make c7ref` (the C7(2) reference executables built with C7(2)'s own Makefile on this node type).
# Then the G-L8SELF baseline (A-RPL-7 machinery): src/, the Makefile and the build-record tools copied to a second
# directory and built there independently; its bin/c8d2_{decimal,gmp} become $C8_PACKAGE/bin/baseline/.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<directory with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
make -j8 profile ratiohist sanitize 2>&1 | tee "$E/make_diagnostic.log"
make c7ref 2>&1 | tee "$E/make_c7ref.log"
echo "builds in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_decimal_san bin/c8d2_gmp_san bin/ref/c7d2_decimal bin/ref/c7d2_gmp | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist c8d2_decimal_san c8d2_gmp_san; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_inspect.build.txt "$E/build_records/"; bin/c8d2_inspect --describe > "$E/describe/c8d2_inspect.json"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
B=$C8_DATA/work/$TAG-baseline-build.$SLURM_JOB_ID; mkdir -p "$B/tools"
cp -R src Makefile "$B/"; cp tools/build_record.py tools/common.py "$B/tools/"
make -C "$B" -j2 bin/c8d2_decimal bin/c8d2_gmp 2>&1 | tee "$E/make_baseline.log"
mkdir bin/baseline; cp "$B/bin/c8d2_decimal" "$B/bin/c8d2_gmp" "$B/bin/c8d2_decimal.build.json" "$B/bin/c8d2_gmp.build.json" bin/baseline/
sha256sum bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp | tee "$E/baseline.sha256"
if cmp -s bin/c8d2_decimal bin/baseline/c8d2_decimal && cmp -s bin/c8d2_gmp bin/baseline/c8d2_gmp; then echo "baseline rebuild byte-identical"; else echo "baseline rebuild DIFFERS (recorded; G-L8SELF still compares outputs)"; fi | tee "$E/baseline_verdict.txt"
echo "finished $(date -Is)"
