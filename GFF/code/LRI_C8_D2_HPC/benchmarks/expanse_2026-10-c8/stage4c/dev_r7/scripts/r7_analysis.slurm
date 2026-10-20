#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-s4c-r7-analysis
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R7 (A-FLAG-6), the analysis after both sweeps and the complement have ended (site deviation U1):
#   1. tools/accounting.py on both sweeps (sacct now has the final elapsed times); assemble.py on both sweeps;
#   2. the fresh freeze (R14): design.py freeze --test-only --pilot sweep_map --rates-bundle prov at the four targets
#      1e-3, 5e-4, 2.5e-4, 1.35e-4 (relative to |C8| = 4.6e4), and the exact sweep's own test-only freezes at the same
#      targets (the variance x cost comparison in core-hours);
#   3. R14/R19 on real data: plan --design prov refused (nothing created); freeze --rates-bundle prov of the exact sweep
#      refused; freeze of the map sweep without --rates-bundle refused; a test-only plan --design fresh (2 graphs per
#      group) under the map accepted, and refused without --rates (the bundle pins the identity); the accepted plan is
#      recorded and removed (never run; its seed is registered);
#   4. design.py report of both sweeps (tails, P8; the map's heavy-tail diagnostics);
#   5. r7_compare.py: the unpaired agreement (sweeps and complement), the variance x cost tables and the freeze table.
# Evidence: $C8_DATA/evidence/<sha12>/r7analysis.<job>.0/. Exit 3 when a step fails or a refusal does not happen.
# Usage: C8_PACKAGE=<export> R7_DIR=<work> R7_SOURCE=<J-SWEEP-1> R7_SEED_PLANCHECK=<fresh> R7_APPROVAL=<text> sbatch --export=ALL r7_analysis.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R7_DIR:?}" "${R7_SOURCE:?}" "${R7_SEED_PLANCHECK:?}" "${R7_APPROVAL:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r7analysis.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; work $R7_DIR; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
SC=benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts; M=$R7_DIR/sweep_map; X=$R7_DIR/sweep_exact; PROV=$R7_DIR/prov
CM=$(ls -d $C8_DATA/evidence/$TAG/r7sweep_map.*.0 | tail -1)/cost_model.json
step() { echo "== $(date -Is) $*"; }
fail() { echo "FAILED: $*"; exit 3; }
refused() {  # refused <name> <needle> <command...>: the command must fail, print the needle and create nothing named in $R7_NOT
  local name=$1 needle=$2; shift 2
  if "$@" > "$E/refusal_$name.txt" 2>&1; then fail "$name was accepted"; fi
  grep -q -- "$needle" "$E/refusal_$name.txt" || { cat "$E/refusal_$name.txt"; fail "$name refused without '$needle'"; }
  [ -z "${R7_NOT:-}" ] || [ ! -e "$R7_NOT" ] || fail "$name created $R7_NOT"
  echo "refused as required: $name ($(grep -m1 -o -- "$needle" "$E/refusal_$name.txt"))"
}
step "1. accounting and assembly of the sweeps"
for A in map exact; do
  python3 -B tools/accounting.py "$R7_DIR/sweep_$A" --json > "$E/accounting_$A.json" 2> "$E/accounting_$A.stderr" || { cat "$E/accounting_$A.stderr"; fail "accounting $A"; }
  python3 -B tools/assemble.py "$R7_DIR/sweep_$A" > "$E/assemble_$A.txt" 2>&1 || { cat "$E/assemble_$A.txt"; fail "assemble $A"; }
  cp "$R7_DIR/sweep_$A/C8_test_result.json" "$E/C8_test_result_$A.json"
done
step "2. freezes at the four targets"
FRESH=(); EXACT=()
for t in 1e-3 5e-4 2.5e-4 1.35e-4; do
  python3 -B tools/design.py freeze --pilot "$M" --rates-bundle "$PROV" --test-only --target-rel $t --out "$R7_DIR/fresh_$t" > "$E/freeze_fresh_$t.json" 2>&1 || { cat "$E/freeze_fresh_$t.json"; fail "fresh freeze $t"; }
  python3 -B tools/design.py freeze --pilot "$X" --test-only --target-rel $t --out "$R7_DIR/exact_$t" > "$E/freeze_exact_$t.json" 2>&1 || { cat "$E/freeze_exact_$t.json"; fail "exact freeze $t"; }
  cp "$R7_DIR/fresh_$t/design_meta.json" "$E/fresh_${t}_design_meta.json"; cp "$R7_DIR/exact_$t/design_meta.json" "$E/exact_${t}_design_meta.json"
  cp "$R7_DIR/fresh_$t/design.json" "$E/fresh_${t}_design.json"; cp "$R7_DIR/exact_$t/design.json" "$E/exact_${t}_design.json"
  FRESH+=("$R7_DIR/fresh_$t"); EXACT+=("$R7_DIR/exact_$t")
done
python3 - "$R7_DIR/fresh_1.35e-4/design_meta.json" "$PROV/design_meta.json" "$PROV/rates.json" <<'PY' || fail "fresh bundle pins"
import hashlib, json, sys
m = json.load(open(sys.argv[1])); pm = hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest(); rs = hashlib.sha256(open(sys.argv[3], 'rb').read()).hexdigest()
ok = m['provisional'] is False and m['rates_identity'] == rs and m['rates_bundle']['meta_sha256'] == pm and m['rates_bundle']['rates_identity'] == rs
print(json.dumps({'fresh_non_provisional': m['provisional'] is False, 'rates_identity': m['rates_identity'], 'provisional_meta_sha256': pm, 'pins_ok': ok}))
sys.exit(0 if ok else 1)
PY
step "3. R14/R19 refusals and the plan acceptance on real data"
R7_NOT=$R7_DIR/plan_prov refused plan_design_provisional 'provisional' python3 -B tools/production.py plan "$R7_DIR/plan_prov" --design "$PROV" --test-graphs 2 \
  --cost-model "$CM" --threads 16 --seed "$R7_SEED_PLANCHECK" --rates "$PROV/rates.json" --approved-numerics-change "$R7_APPROVAL"
R7_NOT=$R7_DIR/f_exact_under_map refused freeze_exact_with_map 'R14' python3 -B tools/design.py freeze --pilot "$X" --rates-bundle "$PROV" --test-only --target-rel 1e-3 --out "$R7_DIR/f_exact_under_map"
R7_NOT=$R7_DIR/f_map_without_bundle refused freeze_map_without_bundle '--rates-bundle' python3 -B tools/design.py freeze --pilot "$M" --test-only --target-rel 1e-3 --out "$R7_DIR/f_map_without_bundle"
R7_NOT=$R7_DIR/plan_fresh_norates refused plan_fresh_without_rates 'rates identity' python3 -B tools/production.py plan "$R7_DIR/plan_fresh_norates" --design "$R7_DIR/fresh_1.35e-4" \
  --test-graphs 2 --cost-model "$CM" --threads 16 --seed "$R7_SEED_PLANCHECK"
python3 -B tools/production.py plan "$R7_DIR/plan_fresh" --design "$R7_DIR/fresh_1.35e-4" --test-graphs 2 --cost-model "$CM" --threads 16 --seed "$R7_SEED_PLANCHECK" \
  --rates "$PROV/rates.json" --approved-numerics-change "$R7_APPROVAL" > "$E/plan_fresh.txt" 2>&1 || { cat "$E/plan_fresh.txt"; fail "plan --design fresh under the map"; }
cp "$R7_DIR/plan_fresh/manifest.json" "$E/plan_fresh_manifest.json"; python3 -B tools/production.py status "$R7_DIR/plan_fresh" > "$E/plan_fresh_status.txt" 2>&1 || true
python3 -B tools/seeds.py add --seed "$R7_SEED_PLANCHECK" --label "Stage 4c R7 plan-only acceptance check ($R7_DIR/plan_fresh, never run, removed)" | tee "$E/seeds_add_plancheck.txt"
python3 - "$E/plan_fresh_manifest.json" "$R7_DIR/fresh_1.35e-4/design_meta.json" <<'PY' || fail "plan_fresh manifest"
import hashlib, json, sys
m = json.load(open(sys.argv[1])); dm = hashlib.sha256(open(sys.argv[2], 'rb').read()).hexdigest(); bm = json.load(open(sys.argv[2]))
ok = m['rates_identity'] == bm['rates_identity'] and (m.get('design') or {}).get('meta_sha256') == dm and m['test_only'] and m['approved_numerics_change']
print(json.dumps({'plan_rates_identity': m['rates_identity'], 'design_meta_sha256': (m.get('design') or {}).get('meta_sha256'), 'allocation': m['allocation'],
                  'approved_numerics_change': m['approved_numerics_change'], 'ok': bool(ok)}))
sys.exit(0 if ok else 1)
PY
rm -rf "$R7_DIR/plan_fresh"
step "4. design reports of the sweeps"
for A in map exact; do
  python3 -B tools/design.py report --pilot "$R7_DIR/sweep_$A" --test-only --json "$E/report_$A.json" --tails-out "$E/tails_$A.csv" > "$E/report_$A.txt" 2>&1 || { cat "$E/report_$A.txt"; fail "report $A"; }
done
step "5. comparison"
python3 -B $SC/r7_compare.py --package . --map "$M" --exact "$X" --map-pilot "$R7_DIR/pilot_map" --exact-pilot "$R7_DIR/pilot_exact" --source "$R7_SOURCE" \
  --rates "$PROV/rates.json" --fresh-bundles "${FRESH[@]}" --exact-bundles "${EXACT[@]}" --out "$E/compare.json" > "$E/compare.txt" 2>&1 || { cat "$E/compare.txt"; fail "compare"; }
cat "$E/compare.txt"
cp "$C8_SEEDS" "$E/seeds_after.json"
echo "finished $(date -Is), status 0"
