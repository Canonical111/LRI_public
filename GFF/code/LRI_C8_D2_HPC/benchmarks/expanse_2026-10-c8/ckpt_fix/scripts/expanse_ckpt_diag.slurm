#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=16G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-ckfix-diag
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Diagnostic builds for the checkpoint-review fixes (added 2026-10-04 to the run on d98e3a1): the ckfix build job made
# only the release, inspector, sanitizer and c7ref builds, so J-VAL-1's validate skipped its diagnostics part (as Stage
# 3b's J-VAL-1 did); T-04 changed src/c8d2_integrate.cpp, which these builds compile. In the export of the commit under
# test (after the build, val1 and mscale jobs): make profile ratiohist; their sha256 against Stage 3 part A (job
# 54637262: c8d2_gmp_prof d1cc6551..., c8d2_gmp_ratiohist c307f2a3...; informational); tests/validate.py --only
# diagnostics (rows identical to bin/c8d2_gmp at L7 and L8 in both sectors; every evaluation counted once).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=ckdiag.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'; g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_SEEDS C8_SITE C8_INPUTS
cd "$C8_PACKAGE"
if [ -e bin/c8d2_gmp_prof ] || [ -e bin/c8d2_gmp_ratiohist ]; then echo "refusing: diagnostic builds already present"; exit 64; fi
status=0
make -j8 profile ratiohist > "$E/make_profile_ratiohist.log" 2>&1 || status=1
tail -4 "$E/make_profile_ratiohist.log" | cut -c1-250
sha256sum bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_decimal bin/c8d2_gmp | tee "$E/binaries.sha256"
mkdir "$E/build_records"; cp bin/c8d2_gmp_prof.build.json bin/c8d2_gmp_ratiohist.build.json "$E/build_records/"
python3 - "$E" <<'PY'
import hashlib, json, sys
from pathlib import Path
E = Path(sys.argv[1])
stage3a = {'bin/c8d2_gmp_prof': 'd1cc6551df116cd106ebf99985cf20035387acaad9ff1fcd77274a0b51de75d7',
           'bin/c8d2_gmp_ratiohist': 'c307f2a314a67fea489d85073325edf12e4521ac08772789ecf7626f37326ecf'}
got = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in stage3a}
rec = {'stage3a': stage3a, 'now': got, 'identical': {p: got[p] == stage3a[p] for p in stage3a},
       'note': 'Stage-3 part A hashes from job 54637262 (export 7607a9f); same node type, Spack GCC 13.3.0, Boost 1.77, GMP 6.2.1; informational (diagnostic builds)'}
(E / 'diag_binaries_vs_stage3a.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
PY
python3 -B tests/validate.py --only diagnostics --output "$E/validate_diagnostics.json" > "$E/validate_diagnostics.log" 2>&1 || status=1
tail -20 "$E/validate_diagnostics.log" | cut -c1-250
rm -f bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_gmp_prof.build.json bin/c8d2_gmp_ratiohist.build.json
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
