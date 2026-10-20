#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The dd+mp256 profile cost sweep re-measured on the NEW profile build of Stage-6 fix round 3 (route (b)'s cost model must
# record the gated build's sha256: design.py freeze refuses a model of an executable that no --numerics-gate passed; the
# model of job 570240, cost_models/gmp_symmetry_amd_c8_dd+mp256.json 9b0dfec6..., records d5df32ac..., which Z4 replaced).
# Template: pre6/scripts/p6sweep.slurm (job 570240), the same plan: J-SWEEP-2's shape on bin/c8d2_gmp_dd+mp256 of this
# export (s3build's profile.sha256): slurm/sweep.sh -> tools/sweep.py --numerics dd+mp256 --approved-numerics-change
# "<the user's approval>", a test-only plan of all 24,173 graphs, both campaigns, 2 replicates x 512 points, chunked with
# J-SWEEP-1's cost model (Expanse 54641706) so that its task layout is J-SWEEP-2's and 570240's; the ledger registration
# (role sweep) before any index; 8 x 8 NUMA-pinned process slots (--threads 8), heaviest first; merge (32 processes);
# the measured cost model under dd+mp256 (every campaign:sector:L:graph key, numerics identity dd+mp256, the new
# executable) and the calibration rows, written to the sweep's OWN calibration file in the evidence folder
# (tools/calibration.json is never written). The sweep registers its base seed in $C8_SEEDS itself (Y13) and sweep.sh
# adds it again ("present"); the Mac merges it into the mirror and lists it for Expanse's log. No GMP_PREFIX, no --rates.
# The model is installed (note extended by the approval and the gate) by s3des.slurm.
# Usage: C8_PACKAGE=... BUILD_EVIDENCE=<s3build evidence dir> SWEEP_SEED=<fresh> sbatch --export=ALL --dependency=afterok:<s3build> -J c8d2-s3sweep s3sweep.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${SWEEP_SEED:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3sweep.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=<SCRATCH>/c8-d2/sweepdd-$TAG; CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $W; evidence $E; chunking model $CM1"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
python3 -B -c "import sys; sys.path.insert(0, 'tools'); import production as p; r = p.APPROVED_PROFILES.get('dd+mp256'); print('approval reference matches production.APPROVED_PROFILES:', r == sys.argv[1]); sys.exit(0 if r == sys.argv[1] else 64)" "$REF" || exit 64
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 "$CM1" cost_models/gmp_symmetry_amd_c8.json tools/sweep.py tools/production.py tools/make_cost_model.py | tee "$E/binaries.sha256"
PROF=$(cut -c1-64 "$BUILD_EVIDENCE/profile.sha256")
grep -q "^$PROF  bin/c8d2_gmp_dd+mp256\$" "$E/binaries.sha256" \
  || { echo "bin/c8d2_gmp_dd+mp256 is not s3build's profile build $PROF; refusing" >&2; exit 64; }
echo "profile build $PROF (s3build)"
S=/tmp/c8d2_$SLURM_JOB_ID; mkdir -p "$S"; echo "node-local scratch $S"
python3 -B tools/seeds.py check "$SWEEP_SEED" | tee "$E/seed_check_before.txt"
t0=$(date +%s); status=0
bash slurm/sweep.sh "$W" --seed "$SWEEP_SEED" --points 512 --replicates 2 --threads 8 --cost-model "$CM1" \
  --numerics dd+mp256 --approved-numerics-change "$REF" \
  --forbid-seeds-from "$C8_SEEDS" --merge-jobs 32 --cost-model-out "$E/cost_model.json" --calibration "$E/calibration_dd+mp256.json" --scratch "$S" \
  > "$E/sweep.stdout" 2>&1 || status=$?
echo "sweep exit $status after $(( $(date +%s) - t0 )) s"; tail -25 "$E/sweep.stdout"
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl"
python3 -B tools/production.py status "$W" --json > "$E/status.json" 2>&1 || true
python3 -B tools/seeds.py check "$SWEEP_SEED" | tee "$E/seed_check_after.txt"
python3 -B tools/seeds.py list > "$E/seeds_after.txt" 2>&1
python3 -B - "$E/cost_model.json" "$E/manifest.json" "$PROF" <<'PY' || status=3
import json, sys
m = json.load(open(sys.argv[1])); man = json.load(open(sys.argv[2]))
ok = (m['numerics'] == 'dd+mp256' and m['keys'] == 48346 and len(m['seconds_per_point']) == 48346 and man.get('numerics') == 'dd+mp256'
      and m['executable_sha256'] == sys.argv[3])
print('cost model: numerics', m['numerics'], 'keys', m['keys'], 'executable', m['executable_sha256'][:12], 'cpu', m['cpu_models'], 'hosts', m['hosts'],
      '; campaign approval:', repr(man.get('approved_numerics_change')), '; ok:', ok)
sys.exit(0 if ok else 3)
PY
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
