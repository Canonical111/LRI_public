#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-g4b-build
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, G4b (branch c8; Expanse, site deviation U1): build every executable of the final head in its git-archive
# export (C8_PACKAGE), for the final J-VAL-2 and J-VAL-3 (g4b_val2.slurm, g4b_val3.slurm).
#   1. The two L8 packs of C8_L8_PACKS are re-hashed against this export's inputs/manifest.json, then hard-linked into
#      inputs/packs/ (make re-hashes every pack again).
#   2. make, make gmp inspect, make profile ratiohist, make c7ref, make quaddiff (16 CPUs).
#   3. bin/baseline/c8d2_{decimal,gmp}: byte copies of the Stage-3 baseline (C8_BASELINE_BIN; tag c8-stage3 build,
#      sha256 3dbd51bb... and 5c5328af..., checked), the A-RPL-7 reference of g4b_val3.slurm.
#   4. identity.json: every executable against the final candidate e7ef98d's build (job 54672108) and, for the c7ref
#      references, Stage 3's (54637262). src/ and the Makefile are unchanged since e7ef98d, so every hash must be equal;
#      a difference is recorded and fails this job (the gates still decide exactness; the speed record would not apply).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir> [C8_BASELINE_BIN=<dir>] sbatch --export=ALL final_build.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
BASE=${C8_BASELINE_BIN:-$C8_DATA/pkg/c17688158e2b/bin}
S3DEC=3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a; S3GMP=5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3
TAG=$(basename "$C8_PACKAGE"); RUN=g4bbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; packs $C8_L8_PACKS; baseline $BASE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
# 1. Re-hash the source packs against this export's manifest before linking them.
python3 - "$C8_L8_PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
import hashlib, json, os, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); man = json.loads(Path('inputs/manifest.json').read_text())['sha256']; rec = {}
for s in ('free', 'power'):
    p = src / f'{s}_L8.pack'; h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    rec[s] = {'source': str(p), 'bytes': p.stat().st_size, 'inode': p.stat().st_ino, 'sha256': h.hexdigest(),
              'manifest': man[f'packs/{s}_L8.pack'], 'equal': h.hexdigest() == man[f'packs/{s}_L8.pack']}
out.write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if all(v['equal'] for v in rec.values()) else 3)
PY
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
{ make -j16 && make -j16 gmp inspect && make -j16 profile ratiohist && make c7ref && make -j16 quaddiff; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"
mkdir bin/baseline && cp -p "$BASE/c8d2_decimal" "$BASE/c8d2_gmp" bin/baseline/ || exit 3
[ "$(sha256sum bin/baseline/c8d2_decimal | cut -c1-64)" = $S3DEC ] && [ "$(sha256sum bin/baseline/c8d2_gmp | cut -c1-64)" = $S3GMP ] || { echo "bin/baseline is not the Stage-3 build" >&2; exit 3; }
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
bin/c8d2_inspect --describe > "$E/describe/c8d2_inspect.json"; cp bin/c8d2_inspect.build.txt bin/c8d2_quad_differential.build.txt bin/c8d2_quad_ranges.build.txt "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
status=0
python3 - "$E" <<'PY' || status=1
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1]); h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ref = {  # e7ef98d's build, job 54672108 (intbuild.54672108.0/binaries.sha256); c7ref also Stage 3's 54637262
    'bin/c8d2_decimal': '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf',
    'bin/c8d2_gmp': '1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa',
    'bin/c8d2_gmp_prof': 'f338a547d7356856fba911810a03be31ea3a4c4cc073f61aabf023b0fbc53439',
    'bin/c8d2_gmp_ratiohist': '5d0b7c97d7797513abf7e540717d2d845b8ad1220d330284fbf3f2ad50841e2e',
    'bin/c8d2_inspect': '63c194fd8bd6822cf9da737fa953c155ea4b7dece8d729e2864f2578e21a0002',
    'bin/ref/c7d2_decimal': '4537dcfd501dec8ba28062e1d09a5308f9ba604919bd7deabdec5ee768faaaaf',
    'bin/ref/c7d2_gmp': '6c82938635462c881b22d8ae92cfb1497ef3efe7bbd9c08cfa5ffda0e2770a52',
    'bin/c8d2_quad_differential': '3db26f744b912ba900134a1d39f42f2ae5d0c1c99f16db3eb4a5c544fe3e058f',
    'bin/c8d2_quad_ranges': '3d87f79c79371b639f6e780c31f5baf1ff8a2ebc1db36ffcbe19c7f197f2d893'}
rec = {k: {'this': h(k), 'e7ef98d_54672108': v, 'identical': h(k) == v} for k, v in ref.items()}
rec = {'binaries': rec, 'identical': all(v['identical'] for v in rec.values()),
       'rule': 'src/ and the Makefile are unchanged since e7ef98d: every executable equals the final candidate build byte for byte'}
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['identical'] else 3)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
