#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-r5-bench
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R5a/R5b development on one exclusive Expanse compute node (site deviation U1), in the export built by
# r5_build.slurm:
#   1. P4's lane shape 16x8 (the R5b default on Expanse compute) on the fixed workload p4_L8 (4,018 L8 tasks), with the
#      Stage-3 baseline worker (C8_BASELINE_BIN/c8d2_gmp, 5c5328af..., checked): "before";
#   2. the same with the R5a worker bin/c8d2_gmp: "after". The load share of node time before and after, throughput,
#      busy fraction, OpenMP efficiency, peak RSS per lane; the rows digests must be equal (exactness on all 4,018 tasks);
#   3. G-L8SELF (A-RPL-7 machinery): tests/validate.py --l8self against the baseline on the full L8 sample (2,000
#      kernels, 2 x 512 points, both backends), exact in every scientific field;
#   4. A-RPL-6 thread identity: tests/thread_identity.py (L8 free and power blocks, 1, 8, 16, 64 threads and 8 lanes x
#      8 threads, both backends) on the R5a workers.
# Expected wall ~19 min (2 x ~6.2 + 2.7 + 2.5 min).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> [C8_BASELINE_BIN=<dir>] sbatch --export=ALL --dependency=afterok:<build> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
BASE=${C8_BASELINE_BIN:-$C8_DATA/pkg/c17688158e2b/bin}
TAG=$(basename "$C8_PACKAGE"); RUN=r5bench.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; baseline $BASE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"; export TMPDIR=$S
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_decimal bin/c8d2_gmp "$BASE/c8d2_decimal" "$BASE/c8d2_gmp" | tee "$E/binaries.sha256"
[ "$(sha256sum "$BASE/c8d2_gmp" | cut -c1-64)" = 5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3 ] || { echo "baseline gmp is not Stage 3" >&2; exit 3; }
[ "$(sha256sum "$BASE/c8d2_decimal" | cut -c1-64)" = 3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a ] || { echo "baseline decimal is not Stage 3" >&2; exit 3; }
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -4 "$E/$name.stdout" | cut -c1-300; [ $c -eq 0 ] || status=1; }
run p4_before python3 -B tools/benchmark.py --lane-shapes 16x8 --workload p4_L8 --exe "$BASE/c8d2_gmp" --expect-sha256 5c5328af932912bb --output "$E/p4_before" --scratch "$S"
run p4_after python3 -B tools/benchmark.py --lane-shapes 16x8 --workload p4_L8 --exe bin/c8d2_gmp --output "$E/p4_after" --scratch "$S"
run l8self python3 -B tests/validate.py --only none --l8self "$BASE" --jobs 32 --threads 4 --output "$E/l8self.json"
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
python3 - "$E" <<'PY' || status=1
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); out = {}
for k in ('before', 'after'):
    f = E / f'p4_{k}' / '16x8.json'
    if not f.is_file(): out[k] = None; continue
    s = json.loads(f.read_text())
    out[k] = {x: s.get(x) for x in ('wall_seconds', 'throughput_cost_model_s_per_node_s', 'busy_fraction', 'openmp_efficiency',
                                    'load_share_of_node_time', 'stage_share_of_node_time', 'load_staging_share_of_node_time', 'load_seconds',
                                    'stage_seconds', 'native_overhead_seconds', 'lane_end_spread_seconds', 'max_rss_kb_per_lane',
                                    'sum_lane_peak_rss_kb', 'blocks', 'tasks', 'quad', 'mp', 'rows', 'rows_digest', 'errors')}
    out[k]['lowest_lane_numa_local_fraction'] = min((l.get('numa_local_fraction') or 1) for l in s.get('lanes_detail', []))
b, a = out.get('before'), out.get('after')
if b and a:
    out['rows_identical'] = b['rows_digest'] == a['rows_digest'] and b['rows'] == a['rows'] and not b['errors'] and not a['errors']
    out['p4_stage4a_digest_prefix'] = '16d6ff3d'
    out['rows_equal_stage4a_p4'] = str(a['rows_digest']).startswith('16d6ff3d')
    out['throughput_ratio_after_over_before'] = a['throughput_cost_model_s_per_node_s'] / b['throughput_cost_model_s_per_node_s']
(E / 'r5_summary.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out, indent=1))
sys.exit(0 if b and a and out['rows_identical'] else 1)
PY
echo "finished $(date -Is), status $status"
exit $status
