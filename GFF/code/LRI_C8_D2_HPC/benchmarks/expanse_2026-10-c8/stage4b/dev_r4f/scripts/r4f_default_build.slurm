#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:40:00 --no-requeue
#SBATCH -J c8d2-r4f-defbuild
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R4f (development probe; PLAN "Performance plan", host deviation R4f): the default build of the commit under
# test, in its export, with GMP_PREFIX unset. bin/c8d2_decimal, bin/c8d2_gmp and bin/c8d2_gmp_prof must equal the
# Stage-3 baseline byte for byte (decimal 3dbd51bb..., gmp 5c5328af..., prof d1cc6551...): the knob leaves the default
# build unchanged (A-RPL-8). Exit 3 otherwise, and no dependent job starts. Also make c7ref (G-C7 references for the
# replay subset) and the input verification (the two L8 packs hard-linked from C8_L8_PACKS and re-hashed against
# inputs/manifest.json by make). These binaries are the baseline of every R4f comparison.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4fdef.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$C8_PACKAGE"
test ! -e bin && test ! -e build
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
t0=$(date +%s)
make -j16 2>&1 | tee "$E/make_all.log" | tail -3
make -j16 gmp profile 2>&1 | tee "$E/make_gmp_profile.log" | tail -3
make c7ref > "$E/make_c7ref.log" 2>&1; tail -2 "$E/make_c7ref.log"
echo "builds in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/ref/c7d2_decimal bin/ref/c7d2_gmp | tee "$E/binaries.sha256"
mkdir "$E/build_records"; cp bin/c8d2_decimal.build.json bin/c8d2_gmp.build.json bin/c8d2_gmp_prof.build.json "$E/build_records/"
{ ldd bin/c8d2_gmp; readelf -d bin/c8d2_gmp | grep -E 'NEEDED|RPATH|RUNPATH' || true; } > "$E/ldd_gmp.txt"; grep libgmp "$E/ldd_gmp.txt"
python3 - "$E" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
stage3 = {'bin/c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'bin/c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3',
          'bin/c8d2_gmp_prof': 'd1cc6551df116cd106ebf99985cf20035387acaad9ff1fcd77274a0b51de75d7'}
got = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in stage3}
br = json.loads(Path('bin/c8d2_gmp.build.json').read_text())
rec = {'stage3': stage3, 'now': got, 'identical': {p: got[p] == h for p, h in stage3.items()},
       'all_identical': all(got[p] == h for p, h in stage3.items()), 'GMP_PREFIX': br.get('GMP_PREFIX'),
       'gmp_header': br.get('gmp_header'), 'gmp_library': br.get('gmp_library'),
       'note': 'GMP_PREFIX unset: the default build of the R4f commit against the Stage-3 hashes (jobs 54637262, '
               '54643359, 54658871, 54661715; Spack GCC 13.3.0, Boost 1.77, Spack GMP 6.2.1).'}
(E / 'default_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('identical', 'all_identical', 'GMP_PREFIX')}, indent=1))
sys.exit(0 if rec['all_identical'] else 3)
PY
echo "finished $(date -Is)"
