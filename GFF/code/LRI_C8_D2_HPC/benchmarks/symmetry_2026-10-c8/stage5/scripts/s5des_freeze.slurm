#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SMK-3, step 1 (PLAN "Design chain (J-SMK-3)"; A-DES-3): on the merged L8 smoke campaign, tools/accounting.py (the
# smoke's ledger: plan job, lane workers, merge; sacct), then
#   tools/design.py freeze --pilot $C8_RUN --test-only --target-rel <TARGET, default 1e-3> --spent-core-hours <SPENT> --total-cap 5000
#                          --out $C8_PACKAGE/designs/test_smoke1 --seeds-log $C8_SEEDS
# and design.py report on the frozen bundle (the target table and the bundle's own predicted SE). SPENT is the smoke's
# allocated core-hours from tools/accounting.py (the plan's "<accounting.py>"). The first run (570070, SPENT=1000 and
# 1e-3) was refused by the total-cap gate (design 5,071.9 core-h at 1e-3 > the 5,000 cap with any spend); the chain
# then freezes at TARGET=1.5e-3. That bundle (test_smoke1) has the minimum K = 1 batch, so combine.py refused both
# --partial with one batch and a final with two (570097); the chain was redone from BUNDLE=test_smoke1b frozen with
# BATCHES=2 (--batches 2 >= K is accepted).
# Usage: C8_PACKAGE=... C8_RUN=<smoke> SPENT=<development core-hours so far> OUT=<evidence dir> sbatch --export=ALL -J c8d2-s5desfrz s5des_freeze.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${SPENT:?}" "${OUT:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); pilot $C8_RUN; spent $SPENT; out $OUT"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"; cd "$C8_PACKAGE" || exit 64
s=0; B=$C8_PACKAGE/designs/${BUNDLE:-test_smoke1}
python3 -B tools/accounting.py "$C8_RUN" --output "$OUT/accounting_smoke.json" > "$OUT/accounting.stdout" 2>&1; echo "accounting exit $?"; tail -5 "$OUT/accounting.stdout" | cut -c1-300
t=$(date +%s)
python3 -B tools/design.py freeze --pilot "$C8_RUN" --test-only --target-rel "${TARGET:-1e-3}" --spent-core-hours "$SPENT" --total-cap 5000 ${BATCHES:+--batches "$BATCHES"} --out "$B" --seeds-log "$C8_SEEDS" \
  > "$OUT/freeze.stdout" 2>&1 || s=$?
echo "freeze exit $s after $(( $(date +%s) - t )) s"; tail -30 "$OUT/freeze.stdout" | cut -c1-300
if [ $s -eq 0 ]; then
  python3 -B tools/design.py report --pilot "$C8_RUN" --bundle "$B" --json "$OUT/report.json" > "$OUT/report.stdout" 2>&1 || s=$?
  echo "report exit $s"; tail -30 "$OUT/report.stdout" | cut -c1-300
  cp -p "$B/design_meta.json" "$OUT/design_meta.json"; cp -p "$B/design.json" "$OUT/design.json"; sha256sum "$B"/design_meta.json "$B"/design.json | tee "$OUT/bundle.sha256"
fi
echo "finished $(date -Is), status $s"
exit $s
