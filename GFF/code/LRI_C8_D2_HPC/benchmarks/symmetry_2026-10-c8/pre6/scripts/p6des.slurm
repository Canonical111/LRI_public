#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 06:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# The J-DES-5 re-check on symmetry sharedq with the F11-fixed tools/design.py and route (b) (pre-Stage-6; PLAN job
# J-DES-5's shape, stage5/des5/scripts/s5des5.slurm):
#  1. tools/accounting.py on the dd+mp256 profile sweep campaign (sweepdd-<tag>, after its job ended).
#  2. The profile cost model is installed as $W/cost_models/gmp_symmetry_amd_c8_dd+mp256.json: the sweep's
#     make_cost_model.py output with only its `note` extended by the approval reference (note is one of
#     make_cost_model.py's volatile fields; every other field is checked equal), published no-clobber. The freezes and
#     plans below use this file; the Mac installs the same bytes as cost_models/gmp_symmetry_amd_c8_dd+mp256.json.
#  3. tools/design.py report --test-only on the merged J-SWEEP-2 sweep (sweep2-5d7586e9f1ab, exact, all 24,173 graphs;
#     its eta_node from its self-registered ledger, R10), exact and re-costed under dd+mp256 (--numerics dd+mp256
#     --cost-model <profile model>).
#  4. For T = 1e-3, 5e-4, 2.5e-4, 1.35e-4:
#     (x) design.py freeze --pilot <J-SWEEP-2> --test-only --target-rel T (the F11-fixed split; J-DES-5's arguments);
#     (b) the route-(b) freeze: the same plus --numerics dd+mp256 --approved-numerics-change "<approval>" --cost-model
#         <profile model> --numerics-gate <the 570210 gate record in this export>;
#     then production.py plan --design <bundle> --test-graphs all (test-only bundles are accepted by test-only plans
#     only), J-DES-5's sizing (gmp, --threads 8, --checkpoint-tasks 256, --index-hours 1.5), (x) with the exact symmetry
#     cost model, (b) with --numerics dd+mp256 --approved-numerics-change "<approval>" and the profile cost model; a
#     fresh seed checked against $C8_SEEDS, under GNU time -v; NOT submitted. des5_measure.py records the plan; the
#     manifest's numerics_route is kept; the seed is added to $C8_SEEDS with a label; the plan directory is DELETED.
#     The exact bundles are compared with J-DES-5's (design.json, counts).
# Usage: C8_PACKAGE=... SWEEP_RUN=p6sweep.<job>.0 SEEDS="x1 x2 x3 x4 b1 b2 b3 b4" sbatch --export=ALL --dependency=afterok:<sweep> -J c8d2-p6des p6des.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SWEEP_RUN:?}" "${SEEDS:?}" "${C8_SEEDS:?}"
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=p6des.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=$D/work/p6des-$TAG; mkdir -p "$W/bundles" "$W/plans" "$W/cost_models"
SW=<SCRATCH>/c8-d2/sweep2-5d7586e9f1ab; SWP=<SCRATCH>/c8-d2/sweepdd-$TAG
CMS=$D/evidence/$TAG/$SWEEP_RUN/cost_model.json; CM=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8.json
CMP=$W/cost_models/gmp_symmetry_amd_c8_dd+mp256.json
GATE=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json
OLD=$D/work/des5-5d7586e9f1ab/bundles
M=$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/stage5/des5/scripts/des5_measure.py
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; pilot $SW; profile sweep $SWP; work $W; evidence $E"
{ hostname; lscpu; free -g; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
status=0
# 1. accounting of the profile sweep
python3 -B tools/accounting.py "$SWP" --output "$E/accounting_sweepdd.json" > "$E/accounting_sweepdd.stdout" 2>&1; s=$?
echo "accounting sweepdd exit $s"; tail -3 "$E/accounting_sweepdd.stdout" | cut -c1-300; [ $s -eq 0 ] || status=$s
# 2. the profile cost model, note extended by the approval reference (every other field equal), no-clobber
python3 -B - "$CMS" "$CMP" "$REF" "$E/cost_model_install.json" <<'PY' || exit 3
import hashlib, json, os, sys
src, dst, ref, rec = sys.argv[1:5]
b = open(src, 'rb').read(); m0 = json.loads(b); m = json.loads(b)
if m0.get('numerics') != 'dd+mp256' or m0.get('keys') != 48346: sys.exit(f'{src}: numerics {m0.get("numerics")!r}, keys {m0.get("keys")}: not the full dd+mp256 model')
m['note'] = (f"{m0.get('note')}; measured under numerics dd+mp256, --approved-numerics-change '{ref}' (the campaign manifest's "
             "approved_numerics_change; production.APPROVED_PROFILES['dd+mp256']), with the build d5df32ac that the dd+mp256 J-FLAG gate passed "
             "(symmetry job 570210); route (b) cost model (docs/DESIGN.md), cost_models/gmp_symmetry_amd_c8_dd+mp256.json")
diff = sorted(k for k in set(m0) | set(m) if k != 'note' and m0.get(k) != m.get(k))
out = (json.dumps(m, indent=2, allow_nan=False) + '\n').encode()
if diff or json.loads(out) != m: sys.exit(f'installed model differs beyond the note: {diff}')
with open(dst, 'xb') as f: f.write(out)
r = {'source': src, 'source_sha256': hashlib.sha256(b).hexdigest(), 'installed': dst, 'installed_sha256': hashlib.sha256(out).hexdigest(),
     'changed_fields': ['note'], 'note': m['note'], 'numerics': m['numerics'], 'keys': m['keys'], 'executable_sha256': m['executable_sha256'],
     'cpu_models': m['cpu_models'], 'hosts': m['hosts'], 'job_ids': m['job_ids'], 'source_manifest_sha256': m['source_manifest_sha256']}
open(rec, 'w').write(json.dumps(r, indent=1) + '\n'); print(json.dumps(r, indent=1))
PY
cp -p "$CMP" "$E/gmp_symmetry_amd_c8_dd+mp256.json"
sha256sum "$HOME/c8d2/env.sh" "$CM" "$CMP" "$GATE" tools/{design,production,accounting,ledger,seeds}.py bin/c8d2_gmp bin/c8d2_gmp_dd+mp256 "$M" | tee "$E/inputs.sha256"
# 3. reports (exact, and re-costed under dd+mp256)
t=$(date +%s); python3 -B tools/design.py report --pilot "$SW" --test-only --json "$E/report_exact.json" > "$E/report_exact.stdout" 2>&1; s=$?
echo "report exact exit $s after $(( $(date +%s) - t )) s"; head -8 "$E/report_exact.stdout" | cut -c1-200; [ $s -eq 0 ] || status=$s
t=$(date +%s); python3 -B tools/design.py report --pilot "$SW" --test-only --numerics dd+mp256 --cost-model "$CMP" --json "$E/report_dd+mp256.json" \
  > "$E/report_dd+mp256.stdout" 2>&1; s=$?
echo "report dd+mp256 exit $s after $(( $(date +%s) - t )) s"; head -8 "$E/report_dd+mp256.stdout" | cut -c1-200; [ $s -eq 0 ] || status=$s
# 4. freezes and plans
set -- $SEEDS; i=0
for R in x b; do
 for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  i=$((i+1)); SEED=${!i}; N=p6${R}_$T; B=$W/bundles/$N; P=$W/plans/$N
  if [ $R = x ]; then FX=(); PX=(--cost-model "$CM"); LBL="exact (F11-fixed design.py)"
  else FX=(--numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP" --numerics-gate "$GATE")
       PX=(--numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CMP"); LBL="route (b) dd+mp256"; fi
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$SW" --test-only --target-rel "$T" --seeds-log "$C8_SEEDS" \
    --out "$B" "${FX[@]}" > "$E/freeze_$N.stdout" 2>&1; s=$?
  echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -5 "$E/freeze_$N.stdout"; continue; }
  cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"; sha256sum "$B"/design.json "$B"/design_meta.json >> "$E/bundles.sha256"
  if [ $R = x ]; then
    python3 -B - "$B" "$OLD/des5_$T" "$E/compare_des5_$T.json" <<'PY'
import json, sys
from pathlib import Path
new, old, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
dn, do = json.loads((new / 'design.json').read_bytes()), json.loads((old / 'design.json').read_bytes())
mn, mo = json.loads((new / 'design_meta.json').read_bytes()), json.loads((old / 'design_meta.json').read_bytes())
r = {'new': str(new), 'des5': str(old), 'design_json_bytes_equal': (new / 'design.json').read_bytes() == (old / 'design.json').read_bytes(),
     'design_fields_differing': sorted(k for k in set(dn) | set(do) if dn.get(k) != do.get(k)),
     'replicates_equal': dn['replicates'] == do['replicates'], 's_equal': {k: v['s'] for k, v in dn['strata'].items()} == {k: v['s'] for k, v in do['strata'].items()},
     'counts_equal': mn['counts_sha256'] == mo['counts_sha256'],
     'se_total': [dn['predicted']['se_total'], do['predicted']['se_total']], 'core_hours': [dn['predicted']['cost_total_core_hours'], do['predicted']['cost_total_core_hours']],
     'replicates': [dn['replicates'], do['replicates']], 's': [{k: v['s'] for k, v in dn['strata'].items()}, {k: v['s'] for k, v in do['strata'].items()}]}
out.write_text(json.dumps(r, indent=1) + '\n')
print('vs J-DES-5:', {k: r[k] for k in ('design_json_bytes_equal', 'replicates_equal', 's_equal', 'counts_equal', 'se_total', 'core_hours')})
PY
  fi
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check_$N.txt" 2>&1 || { echo "seed $SEED refused"; status=65; continue; }
  t=$(date +%s)
  /usr/bin/time -v -o "$E/time_plan_$N.txt" python3 -B tools/production.py plan "$P" --design "$B" --test-graphs all "${PX[@]}" --backend gmp \
    --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" > "$E/plan_$N.stdout" 2> "$E/plan_$N.stderr"; s=$?
  wall=$(( $(date +%s) - t )); echo "plan $N exit $s after $wall s"; tail -3 "$E/plan_$N.stderr" | cut -c1-300
  if [ $s -ne 0 ]; then status=$s; continue; fi
  python3 -B tools/seeds.py add --seed "$SEED" --label "pre-Stage-6 J-DES-5 re-check plan, $LBL, target-rel $T ($P; test-only, never submitted, deleted after measurement)" >> "$E/seeds_add.txt" 2>&1
  python3 -B "$M" "$P" "$B" --time "$E/time_plan_$N.txt" --wall "$wall" --out "$E/measure_$N.json"; s=$?; [ $s -eq 0 ] || status=$s
  python3 -B -c "import json,sys; m=json.load(open(sys.argv[1])); json.dump({k: m.get(k) for k in ('numerics', 'approved_numerics_change', 'numerics_route', 'executable_sha256', 'cost_model_sha256', 'design')}, open(sys.argv[2], 'w'), indent=1)" \
    "$P/manifest.json" "$E/route_$N.json"
  gzip -c "$P/manifest.json" > "$E/plan_manifest_$N.json.gz"
  du -sb "$P" > "$E/du_plan_$N.txt"; find "$P" -type f | wc -l >> "$E/du_plan_$N.txt"
  rm -rf "$P"; if [ -e "$P" ]; then echo "plan directory $P NOT deleted"; status=70; else echo "deleted $P" | tee -a "$E/deleted.txt"; fi
 done
done
ls -la "$W/plans" > "$E/plans_after.txt" 2>&1
tar -C "$W" -czf "$E/bundles.tgz" bundles
python3 -B tools/seeds.py list > "$E/seeds_after.txt" 2>&1
echo "finished $(date -Is), status $status"
exit $status
