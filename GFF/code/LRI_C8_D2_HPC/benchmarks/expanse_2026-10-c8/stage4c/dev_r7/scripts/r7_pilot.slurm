#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=32 --mem=64G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-s4c-r7-pilot
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R7 (A-FLAG-6): the many-replicate complement of the unpaired comparison, as `plan --pilot --rates` (the
# pilot form under the map) and its exact twin. At 2 replicates the sweeps' SEs have very few degrees of freedom in the
# strata with few graphs (L3-L5); here every graph has 32 replicates x 512 points:
#   production.py plan --pilot --points 512 --replicates 32 --test-graphs 400 (test-only; the 400 cheapest graphs per
#   group by the inventory's cost, i.e. L3-L6 complete and the same 400 L7/L8 graphs in both arms) --bootstrap-chunk 512
#   --shards 4 --threads 8, under the map (--rates ... --approved-numerics-change) and on the exact path (fresh seeds);
#   tools/seeds.py add; ledger.py register --role sweep (a standalone all-index runner, as tools/sweep.py's);
#   every index through tools/sweep.py's own runner (run_indices: NUMA-aware CPU slots of 8, heaviest first);
#   production.py merge --jobs 8; assemble.py --bootstrap 0 (recorded; a partial graph set may fail a physical gate).
# Evidence: $C8_DATA/evidence/<sha12>/r7pilot.<job>.0/. Exit 3 on a failed plan, run or merge.
# Usage: C8_PACKAGE=<export> R7_DIR=<work> R7_SEED_MAP=<fresh> R7_SEED_EXACT=<fresh> R7_APPROVAL=<text> sbatch --export=ALL r7_pilot.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R7_DIR:?}" "${R7_SEED_MAP:?}" "${R7_SEED_EXACT:?}" "${R7_APPROVAL:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r7pilot.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; work $R7_DIR; evidence $E"
lscpu | grep -E 'Model name|NUMA node\(s\)'; taskset -cp $$
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
test -s "$R7_DIR/prov/rates.json" || { echo "no provisional map in $R7_DIR/prov"; exit 64; }
status=0
for ARM in map exact; do
  W=$R7_DIR/pilot_$ARM; seed=$R7_SEED_EXACT; extra=()
  [ $ARM = map ] && { seed=$R7_SEED_MAP; extra=(--rates "$R7_DIR/prov/rates.json" --approved-numerics-change "$R7_APPROVAL"); }
  echo "== $(date -Is) $ARM: plan $W (seed $seed)"; t0=$(date +%s)
  python3 -B tools/production.py plan "$W" --pilot --points 512 --replicates 32 --test-graphs 400 --backend gmp --threads 8 --seed "$seed" \
    --bootstrap-chunk 512 --shards 4 --forbid-seeds-from "$C8_SEEDS" "${extra[@]}" > "$E/plan_$ARM.txt" 2>&1 || { cat "$E/plan_$ARM.txt"; status=3; break; }
  python3 -B tools/seeds.py add "$W" | tee -a "$E/seeds_add.txt"
  python3 -B tools/ledger.py register "$W" --role sweep --note "Stage 4c R7 complement: all indices run by tools/sweep.py's runner in this job" | tee -a "$E/ledger_$ARM.txt"
  echo "== $(date -Is) $ARM: run"
  S="$S" python3 -B - "$W" > "$E/run_$ARM.txt" 2>&1 <<'PY' || { tail -40 "$E/run_$ARM.txt"; status=3; break; }
import os, sys, types
from pathlib import Path
sys.path.insert(0, 'tools')
import sweep
a = types.SimpleNamespace(threads=8, procs=None, scratch=os.environ['S'])
failed = sweep.run_indices(Path(sys.argv[1]).resolve(), a, dict(os.environ))
print('failed indices:', failed)
sys.exit(1 if failed else 0)
PY
  tail -3 "$E/run_$ARM.txt"
  echo "== $(date -Is) $ARM: merge"
  python3 -B tools/production.py merge "$W" --jobs 8 --scratch "$S" > "$E/merge_$ARM.txt" 2>&1 || { tail -40 "$E/merge_$ARM.txt"; status=3; break; }
  python3 -B tools/assemble.py "$W" --bootstrap 0 > "$E/assemble_$ARM.txt" 2>&1 || echo "assemble $ARM exit $? (recorded; partial graph sets)"
  cp "$W/manifest.json" "$E/manifest_$ARM.json"; [ $ARM = map ] && cp "$W/rates.json" "$E/campaign_rates_$ARM.json"
  python3 -B tools/production.py status "$W" --json > "$E/status_$ARM.json" 2>&1 || true
  echo "== $ARM done in $(( $(date +%s) - t0 )) s"
done
cp "$C8_SEEDS" "$E/seeds_after.json"
echo "finished $(date -Is), status $status"
exit $status
