#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-ckfix-build
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Checkpoint-review fixes on Expanse: the native executables built in the export of the commit under test (make,
# make gmp inspect, make sanitize, make c7ref), the two L8 packs hard-linked from an earlier export (make re-hashes
# every pack against inputs/manifest.json); then bin/c8d2_decimal and bin/c8d2_gmp compared with the Stage-3 builds
# (decimal 3dbd51bb..., gmp 5c5328af...; jobs 54637262 and 54643359). Exit 3 when a default binary differs: then the
# replay gates A-RPL-1..3 must be rerun (validate.py replay subset in J-VAL-1, J-VAL-2 on a subset).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<directory with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=ckbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
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
cp bin/c8d2_inspect.build.txt "$E/build_records/"
python3 - "$E" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
stage3 = {'bin/c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'bin/c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3'}
got = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in stage3}
rec = {'stage3': stage3, 'now': got, 'identical': got == stage3,
       'note': 'Stage-3 hashes from jobs 54637262 (part A) and 54643359 (part B, tag c8-stage3); same node type, Spack GCC 13.3.0, Boost 1.77, GMP 6.2.1'}
(E / 'binaries_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
sys.exit(0 if rec['identical'] else 3)
PY
echo "finished $(date -Is)"
