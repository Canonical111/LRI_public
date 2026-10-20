#!/bin/bash
#SBATCH -A <ACCOUNT> -p debug -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s5e-exp1
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5, J-EXP-1 (PLAN "Expanse (J-EXP-1..4)", A-EXP-3): on the `debug` partition, one whole node, the build and
# `make test` of the final commit's git-archive export C8_PACKAGE. This job is also the export's build: every later
# Stage-5 Expanse job (J-EXP-2..4, the zen2 gates, J-SWEEP-2E, the pilot plan) uses its bin/.
#   1. The two L8 packs of C8_L8_PACKS (default pkg/7aac898add43) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/ (make re-hashes every pack again).
#   2. The plan's commands: make && make gmp, then make c7ref and make inspect (tests/validate.py, part of make test,
#      needs bin/ref/ and bin/c8d2_inspect and names them when missing; J-VAL-1 template), then `make test`
#      (validate subset, test-python, workflow, staging) with its records in <evidence>/test/.
#   3. Checks: BOOST_LIB_VERSION 1_77 in every bin/*.build.json (A-EXP-1); the default executables equal the final
#      default binaries (decimal 99a51c1d..., gmp 1d2a2181...; A-RPL-8), c7ref 4537dcfd.../6c829386..., inspect 63c194fd...
# The exact default path only (D1): no NUMERICS, no GMP_PREFIX, no CPPFLAGS overrides.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> [C8_L8_PACKS=<dir>] sbatch --export=ALL s5e_exp1.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
PACKS=${C8_L8_PACKS:-$C8_DATA/pkg/7aac898add43/inputs/packs}
TAG=$(basename "$C8_PACKAGE"); RUN=s5eexp1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) partition ${SLURM_JOB_PARTITION:-?} at $(date -Is); package $C8_PACKAGE; packs $PACKS; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"; g++ --version | head -1
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
step() { echo "== $(date -Is) $*"; }
step "1. re-hash the L8 packs against inputs/manifest.json, then hard-link"
python3 - "$PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
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
for s in free power; do ln "$PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
status=0
step "2. make && make gmp; make c7ref; make inspect"
t0=$(date +%s)
{ make -j32 && make -j32 gmp && make c7ref && make -j8 inspect; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries.sha256"
mkdir "$E/build_records"; for x in bin/*.build.json bin/ref/*.build.json; do cp "$x" "$E/build_records/$(echo "$x" | tr / _)"; done
cp bin/c8d2_inspect.build.txt "$E/build_records/" 2>/dev/null
step "3. checks: BOOST_LIB_VERSION 1_77, executables against the final default build"
python3 - "$E" <<'PY' || status=3
import glob, hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1]); h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
want = {'bin/c8d2_decimal': '99a51c1d3f520f16a846eea90149e6cb9d42772db819dbdb2286cb12cb13bcbf',
        'bin/c8d2_gmp': '1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa',
        'bin/c8d2_inspect': '63c194fd8bd6822cf9da737fa953c155ea4b7dece8d729e2864f2578e21a0002',
        'bin/ref/c7d2_decimal': '4537dcfd501dec8ba28062e1d09a5308f9ba604919bd7deabdec5ee768faaaaf',
        'bin/ref/c7d2_gmp': '6c82938635462c881b22d8ae92cfb1497ef3efe7bbd9c08cfa5ffda0e2770a52'}
ex = {k: {'sha256': h(k), 'expected': v, 'identical': h(k) == v} for k, v in want.items()}
boost = {p: json.loads(Path(p).read_text()).get('BOOST_LIB_VERSION') for p in sorted(glob.glob('bin/*.build.json') + glob.glob('bin/ref/*.build.json'))}
rec = {'executables': ex, 'BOOST_LIB_VERSION': boost, 'boost_1_77_everywhere': bool(boost) and all(v == '1_77' for v in boost.values()),
       'identical': all(v['identical'] for v in ex.values())}
rec['ok'] = rec['identical'] and rec['boost_1_77_everywhere']
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if rec['ok'] else 3)
PY
step "4. make test OUTPUT=$E/test"
t=$(date +%s)
make test OUTPUT="$E/test" > "$E/make_test.log" 2>&1; c=$?
echo "== make test exit $c after $(( $(date +%s) - t )) s"
grep -E '^(PASS|FAIL)|passed|FAILED|Error' "$E/make_test.log" | cut -c1-240 | tail -40
[ $c -eq 0 ] || status=1
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s <(cut -c1-64 "$E/binaries.sha256") <(cut -c1-64 "$E/binaries_after.sha256"); then echo "executables unchanged by make test"; else echo "executables CHANGED during make test" >&2; status=3; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
