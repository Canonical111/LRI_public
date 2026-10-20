#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00
#SBATCH -J c8d2-prof4
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# J-PROF-4 on symmetry (PLAN "Performance plan", P4, job table row J-PROF-1..4; the Expanse run is expanse_prof4.slurm):
# the lane-shape table on an AMD node (2 x EPYC 7532/7543, 64 cores, NPS=4: 8 NUMA nodes x 8 cores).
# tools/benchmark.py --lane-shapes 1x64,2x32,4x16,8x8 --fraction 0.5 on the fixed L8 workload p4_L8 of
# benchmarks/fixtures8: the first half of each sector's uniform draw (791 free + 214 power graphs x 2 replicates x
# 16,384 points, ~21,100 cost-model seconds), so that one shape takes ~5-6 min on 64 cores and the four fit amddebugq's
# hour. Per shape: N lane processes pinned to disjoint NUMA-aligned core sets, production-style blocks of
# max(16 x T, 256) tasks, graph members staged per block from the packs on BeeGFS; throughput in cost-model seconds per
# node-second (cost model: Expanse EPYC 7742 seconds, so the absolute numbers carry symmetry's CPU-class factor; the
# shape ranking is what P4 decides), busy fraction, OpenMP efficiency, staging + load share, RSS, NUMA placement.
# The worker is built here when the export has none (symmetry's GCC 11.4: its sha256 differs from Expanse's 5c5328af...
# and is recorded; the default numerics are the same source). The L8 packs: C8_L8_PACKS (a directory holding the pinned
# free_L8.pack and power_L8.pack; hard-linked, else copied) or C8_INVENTORY (inventory8_d2; make inputs-l8 builds them);
# `make gmp` re-hashes every pack against inputs/manifest.json. Expected wall ~25-30 min.
# Usage (after the H7 check, see submit_prof4_symmetry.sh):
#   C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/<sha12> C8_L8_PACKS=<dir> sbatch --export=ALL symmetry_prof4.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
: "${C8_PACKAGE:?}"
D=/mnt/beegfs/zzheng1/c8d2
TAG=$(basename "$C8_PACKAGE"); RUN=prof4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; command -v numastat || echo "numastat: missing (sysfs counters are read directly)"; } > "$E/node.txt" 2>&1
grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
S=${SLURM_TMPDIR:-${TMPDIR:-/tmp}}; S=$S/c8d2_prof4_$SLURM_JOB_ID; mkdir -p "$S"; echo "node-local scratch $S"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS
cd "$C8_PACKAGE"
status=0
for s in free power; do
  f=inputs/packs/${s}_L8.pack
  if [ ! -e "$f" ] && [ -n "${C8_L8_PACKS:-}" ]; then ln "$C8_L8_PACKS/${s}_L8.pack" "$f" 2>/dev/null || cp "$C8_L8_PACKS/${s}_L8.pack" "$f"; fi
done
if [ ! -e inputs/packs/free_L8.pack ] || [ ! -e inputs/packs/power_L8.pack ]; then
  if [ -n "${C8_INVENTORY:-}" ]; then make inputs-l8 INVENTORY="$C8_INVENTORY" > "$E/make_inputs_l8.log" 2>&1 || status=$?
  else echo "no L8 packs: set C8_L8_PACKS or C8_INVENTORY"; exit 69; fi
  [ $status -eq 0 ] || { echo "make inputs-l8 failed"; tail -20 "$E/make_inputs_l8.log"; exit $status; }
fi
if [ ! -x bin/c8d2_gmp ]; then make -j16 gmp > "$E/make_gmp.log" 2>&1 || { echo "make gmp failed"; tail -20 "$E/make_gmp.log"; exit 2; }
else make gmp > "$E/make_gmp.log" 2>&1 || { echo "make gmp (pack verification) failed"; tail -20 "$E/make_gmp.log"; exit 2; }; fi
tail -3 "$E/make_gmp.log" | cut -c1-300
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"; bin/c8d2_gmp --describe > "$E/describe_c8d2_gmp.json"; cp bin/c8d2_gmp.build.json "$E/"
python3 -B tools/prepare_benchmarks.py --order 8 > "$E/fixtures_verify.json" 2>&1 || { echo "fixtures do not verify"; cat "$E/fixtures_verify.json"; exit 65; }
t0=$(date +%s)
python3 -B tools/benchmark.py --lane-shapes "${C8_P4_SHAPES:-1x64,2x32,4x16,8x8}" --workload p4_L8 --fraction "${C8_P4_FRACTION:-0.5}" \
  --output "$E/p4" --scratch "$S" > "$E/p4.stdout" 2>&1 || status=$?
echo "benchmark --lane-shapes exit $status after $(( $(date +%s) - t0 )) s"; tail -12 "$E/p4.stdout" | cut -c1-300
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
