#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=32 --mem=60G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-r4f-val
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R4f (development probe): exactness of the workers linked against one GMP variant (R4F_VARIANT, built by
# r4f_gmp_build.slurm into $C8_DATA/work/<sha12>/r4f-<variant>/bin), against the default build of the same commit in
# $C8_PACKAGE/bin (r4f_default_build.slurm: byte-identical to the Stage-3 baseline). A node-local copy of the export
# (everything but bin/ and build/; the two L8 packs as symlinks into the export) holds the variant's bin/c8d2_{decimal,
# gmp} and the export's bin/ref, and runs:
#   1. the allocated sections of the variant bin/c8d2_gmp against the baseline's (tools/perf_profile.same_code): which
#      sections the knob changed;
#   2. tests/validate.py --only replay: G-REF, G-C7 and G-JET on the subset (A-RPL-1/2/3; mp > 0 rows included);
#   3. tests/validate.py --l8self $C8_PACKAGE/bin: G-L8SELF (A-RPL-7) on the L8 sample, 2,000 kernels x 2 x 512 points,
#      every scientific field exact, both backends;
#   4. r4f_bench.py profile: every 8th task of heavy_free_L8 and heavy_power_L8 at 32 threads, perf record of the
#      baseline and the variant worker (libgmp symbols, shares) and the tier timers of both c8d2_gmp_prof builds.
# Every step runs; the job fails if any does. Staged graphs, perf.data and the package copy stay on node-local scratch.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> R4F_VARIANT=fat|host sbatch --export=ALL [--dependency=afterok:...] ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R4F_VARIANT:?}"
case $R4F_VARIANT in fat|host) ;; *) echo "R4F_VARIANT must be fat or host" >&2; exit 64;; esac
TAG=$(basename "$C8_PACKAGE"); RUN=r4fval-$R4F_VARIANT.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
W=$C8_DATA/work/$TAG/r4f-$R4F_VARIANT; P=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); variant $R4F_VARIANT; package $C8_PACKAGE; workers $W; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"; } > "$E/node.txt" 2>&1
grep -E 'Model name|perf_event_paranoid' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
for f in "$W/bin/c8d2_decimal" "$W/bin/c8d2_gmp" "$W/bin/c8d2_gmp_prof" "$C8_PACKAGE/bin/c8d2_gmp" "$C8_PACKAGE/bin/c8d2_gmp_prof" "$C8_PACKAGE/bin/ref/c7d2_gmp"; do
  test -x "$f" || { echo "missing $f" >&2; exit 69; }
done
mkdir "$L/pkg"
( cd "$C8_PACKAGE" && tar --exclude=./bin --exclude=./build --exclude=./inputs/packs/free_L8.pack --exclude=./inputs/packs/power_L8.pack -cf - . ) | tar -C "$L/pkg" -xf -
for s in free power; do ln -s "$C8_PACKAGE/inputs/packs/${s}_L8.pack" "$L/pkg/inputs/packs/${s}_L8.pack"; done
mkdir "$L/pkg/bin"; cp -a "$W/bin/c8d2_decimal" "$W/bin/c8d2_gmp" "$W/bin/c8d2_gmp_prof" "$W"/bin/*.build.json "$L/pkg/bin/"; cp -a "$C8_PACKAGE/bin/ref" "$L/pkg/bin/ref"
sha256sum "$L/pkg/bin/c8d2_decimal" "$L/pkg/bin/c8d2_gmp" "$L/pkg/bin/c8d2_gmp_prof" "$C8_PACKAGE/bin/c8d2_decimal" "$C8_PACKAGE/bin/c8d2_gmp" "$C8_PACKAGE/bin/c8d2_gmp_prof" | tee "$E/binaries.sha256"
{ echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; echo "# variant"; ldd "$L/pkg/bin/c8d2_gmp" | grep libgmp; echo "# baseline"; ldd "$C8_PACKAGE/bin/c8d2_gmp" | grep libgmp; } | tee "$E/ldd.txt"
cd "$L/pkg"
python3 - "$C8_PACKAGE/bin/c8d2_gmp" "$L/pkg/bin/c8d2_gmp" "$E/sections_vs_baseline.json" "$L" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import perf_profile as pp
base, var, out, tmp = sys.argv[1:5]
r = pp.same_code(Path(base), Path(var), Path(tmp))
sa, sb = pp.alloc_sections(Path(base)), pp.alloc_sections(Path(var))
r['sizes'] = {k: {'baseline': sa.get(k, [None, None, None])[2], 'variant': sb.get(k, [None, None, None])[2]} for k in sorted(set(sa) | set(sb))}
Path(out).write_text(json.dumps(r, indent=1) + '\n'); print(json.dumps({'identical': r['identical'], 'differences': r['differences']}))
PY
status=0
run() { local name=$1; shift; echo "== $name $(date -Is)"; if "$@" > "$E/$name.stdout" 2>&1; then echo "== $name passed $(date -Is)"; else echo "== $name: FAILED $(date -Is)"; tail -30 "$E/$name.stdout"; status=1; fi; grep -E 'passed in|FAILED|Error|rror:' "$E/$name.stdout" | head -10 || true; }
run replay python3 -B tests/validate.py --only replay --jobs 8 --threads 4 --output "$E/replay.json"
run l8self python3 -B tests/validate.py --only none --l8self "$C8_PACKAGE/bin" --jobs 8 --threads 4 --output "$E/l8self.json"
run profile python3 -B "$P/r4f_bench.py" profile --package "$L/pkg" --stride 8 --scratch "$L" --output "$E/profile" \
  --exe "baseline=$C8_PACKAGE/bin/c8d2_gmp" --exe "$R4F_VARIANT=$L/pkg/bin/c8d2_gmp" \
  --prof "baseline=$C8_PACKAGE/bin/c8d2_gmp_prof" --prof "$R4F_VARIANT=$L/pkg/bin/c8d2_gmp_prof"
cd /; rm -rf "$L/pkg" "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
