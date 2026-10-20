#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 02:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 1 on symmetry sharedq: re-freeze the route-(b) bundles of pre6b (job 570302) with the RE-RUN dd+mp256
# gate record (s1flag.slurm; the 570210 record no longer passes design.check_gate, X1-X3), in the export built by
# s1build.slurm (its bin/ and the hard-linked L8 packs are used as they are; nothing is built here). Template:
# pre6b/scripts/p6bdes.slurm, route (b) only.
#  0. The executables are the gated ones: bin/c8d2_gmp 2cc5e88e... and bin/c8d2_gmp_dd+mp256 d5df32ac... (the build the
#     new gate passed and the profile cost model records); the gate record passes design.check_gate here too.
#  1. For T = 1e-3, 5e-4, 2.5e-4, 1.35e-4: design.py freeze --pilot <J-SWEEP-2 sweep2-5d7586e9f1ab> --test-only
#     --target-rel T --numerics dd+mp256 --approved-numerics-change "<approval>" --cost-model
#     cost_models/gmp_symmetry_amd_c8_dd+mp256.json --numerics-gate <GATE>; each bundle compared (p6b_compare.py) with
#     pre6b's bundle of the same target (<SCRATCH>/c8d2/work/p6bdes-77fab7153c0e/bundles/b_<T>): counts, r, s,
#     cost and SE must be equal (only the gate record differs);
#  2. production.py plan --design <bundle> --test-graphs all --numerics dd+mp256 --approved-numerics-change ... --cost-model
#     <profile model> (J-DES-5's sizing; gmp, --threads 8, --checkpoint-tasks 256, --index-hours 1.5), a fresh seed
#     checked against $C8_SEEDS, NOT submitted: route (b) re-checks the bundle's gate (check_gate) and requires the
#     executable to be gated; the plan pins the bundle's verified files in <campaign>/design_bundle (X9) and checks the
#     cost model's numerics (X10). des5_measure.py records the plan; the seed is added to $C8_SEEDS with a label; the plan
#     directory is DELETED.
# Usage (from <SCRATCH>/c8d2): C8_PACKAGE=... GATE=<new numerics_flags.json> SEEDS="b1 b2 b3 b4" \
#   sbatch --export=ALL --dependency=afterok:<s1flag> -J c8d2-s1des s1des.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${GATE:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s1des.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/s1des-$TAG; mkdir -p "$W/plans"; mkdir "$W/bundles" || { echo "$W/bundles exists; refusing" >&2; exit 64; }
SW=<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab
CMP_DD=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8_dd+mp256.json
P6B=$D/work/p6bdes-77fab7153c0e/bundles
CMP=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/pre6b/scripts/p6b_compare.py
M=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/des5/scripts/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); pilot $SW; gate $GATE; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_ALLOW_NO_L8
cd "$C8_PACKAGE" || exit 64
status=0
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 | tee "$E/binaries.sha256"
python3 -B - "$E/binaries.sha256" "$GATE" "$E/check_gate.json" <<'PY' || { echo "executables or gate refused"; exit 3; }
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import design
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
want = {'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17',
        'bin/c8d2_gmp_dd+mp256': 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d'}
ok = got == want
g = design.check_gate(Path(sys.argv[2]), 'dd+mp256', json.loads(Path('inputs/inventory.json').read_text()))
Path(sys.argv[3]).write_text(json.dumps({'executables_identical': ok, 'gate': g}, indent=1) + '\n')
print('executables gated and identical:', ok, '; check_gate passed:', g['sha256'][:12], 'profile', g['profile_executable_sha256'][:12])
sys.exit(0 if ok and g['profile_executable_sha256'] == want['bin/c8d2_gmp_dd+mp256'] else 3)
PY
sha256sum "$HOME/c8d2/env.sh" "$CMP_DD" "$GATE" tools/{design,production,accounting,ledger,seeds}.py "$M" "$CMP" | tee "$E/inputs.sha256"
set -- $SEEDS; i=0
for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; N=b_$T; B=$W/bundles/$N; P=$W/plans/$N
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" \
    --out "$B" --numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP_DD" --numerics-gate "$GATE" > "$E/freeze_$N.stdout" 2>&1; s=$?
  echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$N.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  python3 -B "$CMP" "$B" --ref "pre6b_570302=$P6B/$N" --out "$E/compare_$N.json"; s=$?; [ $s -eq 0 ] || { echo "compare $N exit $s (target or caps not met)"; status=$s; }
  python3 -B - "$E/compare_$N.json" <<'PY' || status=5
import json, sys
c = json.load(open(sys.argv[1])); r = c['refs']['pre6b_570302']; n = c['new']
if r.get('missing'): print('pre6b bundle missing'); sys.exit(5)
same = {k: r[k] for k in ('counts_equal', 'replicates_equal', 's_equal', 'batches_equal', 'eta_node_equal')}
same['cost_equal'] = r['cost_ratio_new_over_ref'] == 1.0; same['se_equal'] = r['se_ratio_new_over_ref'] == 1.0
print('same design as pre6b (570302):', same, '; design.json bytes equal:', r['design_json_bytes_equal'], '; gates',
      [g.get('sha256', '')[:12] for g in (n.get('profile_recost') or {}).get('gates') or []])
sys.exit(0 if all(same.values()) else 5)
PY
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$N.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$N.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all --numerics dd+mp256 \
    --approved-numerics-change "$REF" --cost-model "$CMP_DD" --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 \
    --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$N.stdout" 2> "$E/plan_$N.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $N exit $s after $wall s"; tail -3 "$E/plan_$N.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; rm -rf "$P" "$P".tmp.*; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "Stage-6 fix round 1: plan of the route (b) dd+mp256 re-freeze (new gate) at target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1 \
    || { echo "seed add $SEED FAILED"; status=66; }
  python3 -B "$M" "$P" "$B" --time "$E/time_plan_$N.txt" --wall "$wall" --out "$E/measure_$N.json"; s=$?; [ $s -eq 0 ] || status=$s
  python3 -B -c "import json,sys; m=json.load(open(sys.argv[1])); json.dump({k: m.get(k) for k in ('numerics', 'approved_numerics_change', 'numerics_route', 'executable_sha256', 'cost_model_sha256', 'cost_model_numerics', 'design')}, open(sys.argv[2], 'w'), indent=1)" \
    "$P/manifest.json" "$E/route_$N.json"
  ls -la "$P/design_bundle" > "$E/design_bundle_$N.txt" 2>&1; (cd "$P/design_bundle" 2>/dev/null && find . -type f | sort | xargs sha256sum) >> "$E/design_bundle_$N.txt" 2>&1
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$N.json.gz"
  du -sb "$P" > "$E/du_plan_$N.txt"; find "$P" -type f | wc -l >> "$E/du_plan_$N.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
done
ls -la "$W/plans" > "$E/plans_after.txt" 2>&1
tar -C "$W" -czf "$E/bundles.tgz" bundles
cp -p "$C8_SEEDS" "$E/forbidden_seeds_after.json"; sha256sum "$C8_SEEDS" > "$E/seeds_after.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
