#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-prof-build
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4a (PLAN "Performance plan", J-PROF-1..4 on Expanse, site deviation U1): the builds every profile job reads, in
# the export of the commit under test. The two L8 packs are hard-linked from C8_L8_PACKS (make re-hashes every pack
# against inputs/manifest.json). Then bin/c8d2_decimal and bin/c8d2_gmp must equal the Stage-3 baseline byte for byte
# (decimal 3dbd51bb..., gmp 5c5328af...; jobs 54637262, 54643359, 54658871): exit 3 otherwise, and no profile job
# (afterok) starts. The diagnostic builds (make profile ratiohist: c8d2_gmp_prof d1cc6551..., c8d2_gmp_ratiohist
# c307f2a3...) are compared too (informational), and make probes builds bin/c8d2_interleave_probe (P2's fallback;
# non-fatal: a failure is recorded and P2 then runs without the probe). Finally the fixtures: sha256 against
# benchmarks/fixtures8/manifest.json and every fixture graph staged from the packs (inventory sha256).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<directory with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=profbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
test ! -e bin && test ! -e build
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
t0=$(date +%s)
make -j16 2>&1 | tee "$E/make_all.log" | tail -3
make -j16 gmp 2>&1 | tee "$E/make_gmp.log" | tail -3
make -j16 profile ratiohist 2>&1 | tee "$E/make_diag.log" | tail -3
probe=0; make probes > "$E/make_probes.log" 2>&1 || probe=$?
echo "make probes exit $probe"; tail -5 "$E/make_probes.log" | cut -c1-300
echo "builds in $(( $(date +%s) - t0 )) s"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist $( [ -e bin/c8d2_interleave_probe ] && echo bin/c8d2_interleave_probe ) | tee "$E/binaries.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
[ -e bin/c8d2_interleave_probe.build.txt ] && cp bin/c8d2_interleave_probe.build.txt "$E/build_records/"
python3 - "$E" "$probe" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
stage3 = {'bin/c8d2_decimal': '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
          'bin/c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3'}
diag = {'bin/c8d2_gmp_prof': 'd1cc6551df116cd106ebf99985cf20035387acaad9ff1fcd77274a0b51de75d7',
        'bin/c8d2_gmp_ratiohist': 'c307f2a314a67fea489d85073325edf12e4521ac08772789ecf7626f37326ecf'}
got = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in {**stage3, **diag}}
rec = {'stage3_release': stage3, 'stage3_diagnostic': diag, 'now': got,
       'release_identical': all(got[p] == h for p, h in stage3.items()),
       'diagnostic_identical': {p: got[p] == h for p, h in diag.items()},
       'probe_build_exit': int(sys.argv[2]),
       'note': 'Stage-3 release hashes from jobs 54637262/54643359/54658871, diagnostic hashes from 54637262/54658970; '
               'same node type, Spack GCC 13.3.0, Boost 1.77, GMP 6.2.1. Profiles P1-P4 measure the release worker.'}
(E / 'binaries_vs_stage3.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
sys.exit(0 if rec['release_identical'] else 3)
PY
python3 -B tools/prepare_benchmarks.py --order 8 --stage-check "$TMPDIR/stagecheck" > "$E/fixtures_check.json"
tail -4 "$E/fixtures_check.json"
rm -rf "$TMPDIR"
echo "finished $(date -Is)"
