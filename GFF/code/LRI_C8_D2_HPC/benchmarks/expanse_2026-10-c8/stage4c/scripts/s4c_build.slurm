#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-s4c-build
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4c (branch c8 and the profile branches; Expanse, site deviation U1): build an export and check its identity.
#   1. The two L8 packs of C8_L8_PACKS are re-hashed against the export's inputs/manifest.json, then hard-linked into
#      inputs/packs/ (make re-hashes every pack again).
#   2. make -j16 (bin/c8d2_decimal), make -j16 gmp (bin/c8d2_gmp), then `make gmp NUMERICS=<p>` for every profile of
#      C8_S4C_PROFILES (default "dd mp256 exp1 dd,mp256,exp1"), four builds at once.
#   3. s4c_identity.py: A-RPL-8 (the default executables' sha256 against the final default binary 99a51c1d... and
#      1d2a2181...), the preprocessed program against C8_REF_PACKAGE (default the b47b008 export, whose src/ is the
#      final default binary's), --describe and build records of the profile executables, and the stub identity (a
#      profile executable whose profiles are all stubs writes the rows of bin/c8d2_gmp).
# Evidence: $C8_DATA/evidence/<sha12>/s4cbuild.<job>.0/ (identity.json, binaries.sha256, describe/, build_records/,
# make.log). Exit 3 when a build or an identity check fails.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir> [C8_S4C_PROFILES="dd ..."] [C8_REF_PACKAGE=<export>] \
#          sbatch --export=ALL s4c_build.slurm      (submit_s4c.sh build does this after the admission check)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
REF=${C8_REF_PACKAGE:-$C8_DATA/pkg/b47b0082c0f7}; PROFILES=${C8_S4C_PROFILES:-dd mp256 exp1 dd,mp256,exp1}
TAG=$(basename "$C8_PACKAGE"); RUN=s4cbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; packs $C8_L8_PACKS; reference $REF; profiles $PROFILES; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
python3 - "$C8_L8_PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
import hashlib, json, sys
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
{ make -j16 && make -j16 gmp; } > "$E/make.log" 2>&1 || { echo "default build FAILED"; tail -40 "$E/make.log"; exit 3; }
pids=(); names=()
for p in $PROFILES; do
  make gmp NUMERICS="$p" > "$E/make_${p//,/+}.log" 2>&1 & pids+=($!); names+=("$p")
done
st=0; for i in "${!pids[@]}"; do wait "${pids[$i]}" || { echo "profile build ${names[$i]} FAILED"; tail -60 "$E/make_${names[$i]//,/+}.log"; st=3; }; done
[ $st = 0 ] || exit 3
echo "builds in $(( $(date +%s) - t0 )) s"
canon=$(for p in $PROFILES; do python3 -c "import sys;sys.path.insert(0,'tools');from common import numerics_name;print(numerics_name(sys.argv[1]))" "$p"; done)
sha256sum bin/c8d2_decimal bin/c8d2_gmp $(for p in $canon; do echo "bin/c8d2_gmp_$p"; done) | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp $(for p in $canon; do echo "c8d2_gmp_$p"; done); do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
status=0
python3 -B benchmarks/expanse_2026-10-c8/stage4c/scripts/s4c_identity.py "$E" "$REF" $canon || status=3
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
