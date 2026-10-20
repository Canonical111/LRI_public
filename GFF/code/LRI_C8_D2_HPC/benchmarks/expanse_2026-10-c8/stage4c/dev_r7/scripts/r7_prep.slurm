#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=16G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s4c-r7-prep
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4c R7 (opt-in rates, A-FLAG-6), step 1 on Expanse (site deviation U1): the provisional rate map from J-SWEEP-1,
# which stands in for the pilot (host decision 2026-10-04; it is NOT a design pilot).
#   0. the fresh seeds of this validation are checked against $C8_SEEDS (tools/seeds.py check);
#   1. the source bundle: design.py freeze --test-only of J-SWEEP-1 (default rates) at 1.35e-4, eta_node from its
#      ledger and sacct (design.py rates needs a non-provisional source bundle);
#   2. design.py report of J-SWEEP-1 with that bundle (record);
#   3. r7_spec.py: the per-(campaign, sector, L) spec from J-SWEEP-1's measured W^2 at .8 and .9 (rule in the script);
#   4. design.py rates -> the NEW provisional bundle $R7_DIR/prov (rates.json + design_meta.json only);
#   5. design.py report --bundle prov: "unavailable (provisional)" (R19, real data).
# Evidence: $C8_DATA/evidence/<sha12>/r7prep.<job>.0/. Exit 3 on a failed step.
# Usage: C8_PACKAGE=<export> R7_DIR=<work dir> R7_SOURCE=<J-SWEEP-1 campaign> R7_SEEDS="<seeds>" sbatch --export=ALL r7_prep.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R7_DIR:?}" "${R7_SOURCE:?}" "${R7_SEEDS:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r7prep.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; work $R7_DIR; source $R7_SOURCE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE" || exit 64
SC=benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts
step() { echo "== $(date -Is) $*"; }
fail() { echo "FAILED: $*"; exit 3; }
mkdir -p "$R7_DIR" || exit 64
test ! -e "$R7_DIR/src_bundle" && test ! -e "$R7_DIR/prov" || fail "$R7_DIR already holds a source or provisional bundle"
step "0. fresh seeds against $C8_SEEDS"
cp "$C8_SEEDS" "$E/seeds_before.json"
for s in $R7_SEEDS; do python3 -B tools/seeds.py check "$s" >> "$E/seeds_check.txt" 2>&1 || fail "seed $s is forbidden"; done; cat "$E/seeds_check.txt"
step "1. source bundle (test-only freeze of J-SWEEP-1)"
if ! python3 -B tools/design.py freeze --pilot "$R7_SOURCE" --out "$R7_DIR/src_bundle" --test-only --target-rel 1.35e-4 > "$E/freeze_source.json" 2> "$E/freeze_source.stderr"; then
  cat "$E/freeze_source.stderr"
  grep -q 'eta_node unavailable\|allocation unknown' "$E/freeze_source.stderr" || fail "source freeze"
  # J-SWEEP-1's own accounting (Stage 3b evidence, accounting.json): eta_node 0.38034094325605894 (test-only override)
  python3 -B tools/design.py freeze --pilot "$R7_SOURCE" --out "$R7_DIR/src_bundle" --test-only --target-rel 1.35e-4 --eta-node 0.38034094325605894 \
    > "$E/freeze_source.json" 2>> "$E/freeze_source.stderr" || fail "source freeze with --eta-node"
fi
cat "$E/freeze_source.json"; cp "$R7_DIR/src_bundle/design_meta.json" "$E/src_design_meta.json"
step "2. design report of J-SWEEP-1"
python3 -B tools/design.py report --pilot "$R7_SOURCE" --test-only --bundle "$R7_DIR/src_bundle" --json "$E/report_source.json" --tails-out "$E/tails_source.csv" \
  > "$E/report_source.txt" 2>&1 || { cat "$E/report_source.txt"; fail "report"; }
step "3. spec from J-SWEEP-1"
python3 -B $SC/r7_spec.py "$R7_SOURCE" --package . --spec-out "$E/spec.json" --record-out "$E/spec_derivation.json" > "$E/spec.txt" 2>&1 || { cat "$E/spec.txt"; fail "spec"; }
cat "$E/spec.txt"
(cd "$R7_DIR/src_bundle" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$E/src_bundle_before_rates.sha256"
step "4. design.py rates -> provisional bundle"
python3 -B tools/design.py rates --pilot "$R7_SOURCE" --source-bundle "$R7_DIR/src_bundle" --spec "$E/spec.json" --out "$R7_DIR/prov" > "$E/rates_out.json" 2>&1 || { cat "$E/rates_out.json"; fail "rates"; }
cat "$E/rates_out.json"; ls -la "$R7_DIR/prov" | tee "$E/prov_listing.txt"
cp "$R7_DIR/prov/design_meta.json" "$E/prov_design_meta.json"; cp "$R7_DIR/prov/rates.json" "$E/prov_rates.json"; sha256sum "$R7_DIR/prov/rates.json" | tee "$E/prov_rates.sha256"
(cd "$R7_DIR/src_bundle" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$E/src_bundle_after_rates.sha256"
cmp -s "$E/src_bundle_before_rates.sha256" "$E/src_bundle_after_rates.sha256" || fail "design.py rates changed the source bundle"
echo "source bundle byte-unchanged ($(wc -l < "$E/src_bundle_after_rates.sha256") files)"
step "5. report of the provisional bundle (R19)"
python3 -B tools/design.py report --pilot "$R7_SOURCE" --bundle "$R7_DIR/prov" --test-only > "$E/report_prov.txt" 2>&1; cat "$E/report_prov.txt"
grep -q 'unavailable (provisional)' "$E/report_prov.txt" || fail "the provisional report"
echo "finished $(date -Is), status 0"
