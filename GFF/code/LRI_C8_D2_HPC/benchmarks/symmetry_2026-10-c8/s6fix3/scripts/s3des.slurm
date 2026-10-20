#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 3 on symmetry sharedq: install the re-measured dd+mp256 profile cost model (s3sweep) and re-freeze the
# route-(b) bundles with the NEW gate record (s3flag) of the NEW profile build (Z4 replaced d5df32ac...), in the export
# built by s3build.slurm (nothing is built here). Templates: pre6/scripts/p6des.slurm (the model install, job 570241) and
# s6fix1/scripts/s1des.slurm (the re-freeze, job 570379).
#  0. The executables are s3build's (bin/c8d2_gmp and bin/c8d2_gmp_dd+mp256), and the gate record passes this export's
#     design.check_gate (Z19's libgmp provenance included) for exactly that profile build.
#  1. tools/accounting.py of the profile sweep campaign (complete: the sweep job has ended).
#  2. The sweep's cost model installed as $W/cost_models/gmp_symmetry_amd_c8_dd+mp256.json with only its note extended by
#     the approval reference and the gate (every other field checked equal; no-clobber); the Mac commits the same bytes
#     as cost_models/gmp_symmetry_amd_c8_dd+mp256.json. Compared, per (campaign, sector, L), with the model it replaces
#     (this export's cost_models/gmp_symmetry_amd_c8_dd+mp256.json, 9b0dfec6..., job 570240, build d5df32ac...).
#  3. For T = 1e-3, 5e-4, 2.5e-4, 1.35e-4: design.py freeze --pilot <J-SWEEP-2 sweep2-5d7586e9f1ab> --test-only
#     --target-rel T --numerics dd+mp256 --approved-numerics-change "<approval>" --cost-model <the installed model>
#     --numerics-gate <GATE>; p6b_compare.py against the bundle of the same target of job 570379
#     (work/s1des-c30bfc5f0bdf/bundles/b_<T>, the old model and gate): the target met and the caps held are required;
#     counts, r, s, cost and SE differences are recorded (the profile costs are re-measured, so equality is not expected).
#  4. production.py plan --design <bundle> --test-graphs all --numerics dd+mp256 --approved-numerics-change ... --cost-model
#     <the installed model> (J-DES-5's sizing; gmp, --threads 8, --checkpoint-tasks 256, --index-hours 1.5), a fresh
#     seed checked against $C8_SEEDS, NOT submitted: route (b) re-checks the bundle's gate entry (gate_evidence_missing,
#     the gmp_library of fix round 3 included) and requires the executable to be gated; des5_measure.py records the
#     plan; the seed is added to $C8_SEEDS with a label (a test-only plan does not register itself, Z15); the plan
#     directory is DELETED.
# Usage (from <SCRATCH>/c8d2): C8_PACKAGE=... BUILD_EVIDENCE=<s3build> SWEEP_EVIDENCE=<s3sweep> GATE=<s3flag numerics_flags.json> \
#   SEEDS="b1 b2 b3 b4" sbatch --export=ALL --dependency=afterok:<s3flag>:<s3sweep> -J c8d2-s3des s3des.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${BUILD_EVIDENCE:?}" "${SWEEP_EVIDENCE:?}" "${GATE:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3des.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/s3des-$TAG; mkdir -p "$W/plans" "$W/cost_models"; mkdir "$W/bundles" || { echo "$W/bundles exists; refusing" >&2; exit 64; }
SW=<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab
OLD_DD=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8_dd+mp256.json   # 9b0dfec6..., job 570240, build d5df32ac... (replaced)
CMP_DD=$W/cost_models/gmp_symmetry_amd_c8_dd+mp256.json             # the re-measured model, installed in step 2
SWP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['source_campaign'])" "$SWEEP_EVIDENCE/cost_model.json")
REF1=$D/work/s1des-c30bfc5f0bdf/bundles
CMP=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/pre6b/scripts/p6b_compare.py
M=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/des5/scripts/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); pilot $SW; gate $GATE; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS C8_ALLOW_NO_L8
cd "$C8_PACKAGE" || exit 64
status=0
sha256sum bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 | tee "$E/binaries.sha256"
python3 -B - "$E/binaries.sha256" "$GATE" "$E/check_gate.json" "$BUILD_EVIDENCE" <<'PY' || { echo "executables or gate refused"; exit 3; }
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import design
got = {l.split()[1]: l.split()[0] for l in open(sys.argv[1]).read().splitlines()}
B = Path(sys.argv[4]); want = {l.split()[1]: l.split()[0] for l in (B / 'binaries_after_profile.sha256').read_text().splitlines()}
want = {'bin/c8d2_gmp': want['bin/c8d2_gmp'], 'bin/c8d2_gmp_dd+mp256': (B / 'profile.sha256').read_text().split()[0]}
ok = got == want
g = design.check_gate(Path(sys.argv[2]), 'dd+mp256', json.loads(Path('inputs/inventory.json').read_text()))
Path(sys.argv[3]).write_text(json.dumps({'executables_identical': ok, 'gate': g}, indent=1) + '\n')
print('executables = s3build\'s:', ok, '; check_gate passed:', g['sha256'][:12], 'profile', g['profile_executable_sha256'][:12], 'gmp_library', g.get('gmp_library'))
sys.exit(0 if ok and g['profile_executable_sha256'] == want['bin/c8d2_gmp_dd+mp256'] and g['exact_executable_sha256'] == want['bin/c8d2_gmp'] else 3)
PY
# 1. accounting of the profile sweep
python3 -B tools/accounting.py "$SWP" --output "$E/accounting_sweepdd.json" > "$E/accounting_sweepdd.stdout" 2>&1; s=$?
echo "accounting $SWP exit $s"; tail -3 "$E/accounting_sweepdd.stdout" | cut -c1-300; [ $s -eq 0 ] || status=$s
# 2. the re-measured profile cost model, note extended by the approval reference and the gate (every other field equal), no-clobber
GJOB=$(basename "$(dirname "$(dirname "$GATE")")")
python3 -B - "$SWEEP_EVIDENCE/cost_model.json" "$CMP_DD" "$REF" "$E/cost_model_install.json" "$GJOB" "$OLD_DD" <<'PY' || exit 3
import hashlib, json, sys
src, dst, ref, rec, gjob, old = sys.argv[1:7]
b = open(src, 'rb').read(); m0 = json.loads(b); m = json.loads(b)
if m0.get('numerics') != 'dd+mp256' or m0.get('keys') != 48346: sys.exit(f'{src}: numerics {m0.get("numerics")!r}, keys {m0.get("keys")}: not the full dd+mp256 model')
m['note'] = (f"{m0.get('note')}; measured under numerics dd+mp256, --approved-numerics-change '{ref}' (the campaign manifest's "
             f"approved_numerics_change; production.APPROVED_PROFILES['dd+mp256']), with the build {m0['executable_sha256'][:12]} of Stage-6 fix round 3 "
             f"that the dd+mp256 J-FLAG gate passed (symmetry {gjob}); route (b) cost model (docs/DESIGN.md), cost_models/gmp_symmetry_amd_c8_dd+mp256.json; "
             "it replaces the model of job 570240 (build d5df32ac)")
diff = sorted(k for k in set(m0) | set(m) if k != 'note' and m0.get(k) != m.get(k))
out = (json.dumps(m, indent=2, allow_nan=False) + '\n').encode()
if diff or json.loads(out) != m: sys.exit(f'installed model differs beyond the note: {diff}')
with open(dst, 'xb') as f: f.write(out)
o = json.load(open(old)); per = {}
for k, v in m['seconds_per_point'].items():
    c, s, L, g = k.split(':'); x = per.setdefault(f'{c}:{s}:L{L}', [0.0, 0.0]); x[0] += v; x[1] += o['seconds_per_point'][k]
r = {'source': src, 'source_sha256': hashlib.sha256(b).hexdigest(), 'installed': dst, 'installed_sha256': hashlib.sha256(out).hexdigest(),
     'changed_fields': ['note'], 'note': m['note'], 'numerics': m['numerics'], 'keys': m['keys'], 'executable_sha256': m['executable_sha256'],
     'cpu_models': m['cpu_models'], 'hosts': m['hosts'], 'job_ids': m['job_ids'], 'source_manifest_sha256': m['source_manifest_sha256'],
     'replaced': {'path': old, 'sha256': hashlib.sha256(open(old, 'rb').read()).hexdigest(), 'executable_sha256': o['executable_sha256'], 'hosts': o.get('hosts'),
                  'same_keys': set(o['seconds_per_point']) == set(m['seconds_per_point'])},
     'new_over_replaced_by_group': {k: round(a / b, 4) for k, (a, b) in sorted(per.items())},
     'new_over_replaced_total': round(sum(a for a, _ in per.values()) / sum(b for _, b in per.values()), 4)}
open(rec, 'w').write(json.dumps(r, indent=1) + '\n'); print(json.dumps({k: r[k] for k in ('installed_sha256', 'executable_sha256', 'hosts', 'new_over_replaced_total')}, indent=1))
PY
cp -p "$CMP_DD" "$E/gmp_symmetry_amd_c8_dd+mp256.json"
sha256sum "$HOME/c8d2/env.sh" "$CMP_DD" "$OLD_DD" "$GATE" tools/{design,production,accounting,ledger,seeds}.py "$M" "$CMP" | tee "$E/inputs.sha256"
set -- $SEEDS; i=0
for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; N=b_$T; B=$W/bundles/$N; P=$W/plans/$N
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" \
    --out "$B" --numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP_DD" --numerics-gate "$GATE" > "$E/freeze_$N.stdout" 2>&1; s=$?
  echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$N.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  python3 -B "$CMP" "$B" --ref "s1des_570379=$REF1/$N" --out "$E/compare_$N.json"; s=$?; [ $s -eq 0 ] || { echo "compare $N exit $s (target or caps not met)"; status=$s; }
  python3 -B - "$E/compare_$N.json" <<'PY' || true
import json, sys
c = json.load(open(sys.argv[1])); r = c['refs']['s1des_570379']; n = c['new']
if r.get('missing'): print('the 570379 bundle is missing'); sys.exit(0)
same = {k: r.get(k) for k in ('counts_equal', 'replicates_equal', 's_equal', 'batches_equal', 'eta_node_equal')}
print('against 570379 (old model and gate):', same, '; cost ratio', r.get('cost_ratio_new_over_ref'), '; SE ratio', r.get('se_ratio_new_over_ref'),
      '; meets target', n.get('meets_target'), '; caps ok', n.get('caps_ok'), '; route (b) choice', (n.get('route_b_choice') or {}).get('chosen'),
      '; gates', [g.get('sha256', '')[:12] for g in (n.get('profile_recost') or {}).get('gates') or []])
PY
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$N.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$N.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all --numerics dd+mp256 \
    --approved-numerics-change "$REF" --cost-model "$CMP_DD" --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 \
    --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$N.stdout" 2> "$E/plan_$N.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $N exit $s after $wall s"; tail -3 "$E/plan_$N.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; rm -rf "$P" "$P".tmp.*; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "Stage-6 fix round 3: plan of the route (b) dd+mp256 re-freeze (new profile build, gate and cost model) at target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1 \
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
