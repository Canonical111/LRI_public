#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=8G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check, Codex follow-up (2026-10-08): extraction of the per-replicate prefix data of the earlier nested run
# (48 graphs, job 571385's run) and of the double-lift targeted run, with the production's per-replicate jets of the
# same graphs and the J8 check (tc_nested_extract.py); then the joint-resampling statistics (tc_nested_joint.py).
# Reads the runs and the production batch; writes only this job's evidence folder.
# Usage: sbatch -J c8d2-tc2an --export=ALL,TC_RUN=<dl run dir>,TC_CERT=<tc2cert evidence>/cert.jsonl.gz tc2_analyze.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck2-ba68f401e46e
OLD=/mnt/beegfs/zzheng1/c8-d2/tailcheck-nested-20261007-ba68f401e46e
PROD=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
FINAL=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-final/C8_final.json
SEL=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tcselect.571353.0/select_data.csv.gz
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tc2an.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
fail() { echo "FAILED: $*" | tee "$E/STATUS"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E; dl run $TC_RUN"
sha256sum "$WK/tc_nested_extract.py" "$WK/tc_nested_joint.py" "$WK/tc2_analyze.slurm" "$WK/tc_nested_classes.txt" "$TC_CERT" \
  "$OLD/setup.json" "$TC_RUN/setup.json" "$TC_RUN"/net_*.bin "$FINAL" "$SEL" "$PKG/inputs/two_loop.json" | tee "$E/inputs.sha256"
(cd "$TC_RUN" && sha256sum out/*.json) > "$E/native_outputs_dl.sha256"; wc -l "$E/native_outputs_dl.sha256"
(cd "$OLD" && sha256sum -c --quiet <<< "$(cat "$WK/native_outputs_old.sha256")") && echo "old run's 96 native outputs match job 571385's sha256" || fail "old native outputs changed"
cp "$TC_RUN/setup.json" "$E/setup_dl.json"; cp "$TC_RUN/calls.jsonl" "$E/calls_dl.jsonl"
cd "$PKG" || fail "cd"
t=$(date +%s); python3 -B "$WK/tc_nested_extract.py" --run "old=$OLD" --run "dl=$TC_RUN" --prod "$PROD" --final "$FINAL" --two-loop "$PKG/inputs/two_loop.json" \
  --select "$SEL" --tools "$PKG/tools" --out "$E/nested_extract.json.gz" > "$E/extract.stdout" 2>&1; rc=$?
echo "extract exit $rc after $(( $(date +%s) - t )) s"; tail -3 "$E/extract.stdout"; [ "$rc" -eq 0 ] || fail "extract exit $rc"
t=$(date +%s); python3 -B "$WK/tc_nested_joint.py" "$E/nested_extract.json.gz" "$WK/tc_nested_classes.txt" "$TC_CERT" "$E/nested_joint.json" --boot 2000 > "$E/joint.stdout" 2>&1; rc=$?
echo "joint exit $rc after $(( $(date +%s) - t )) s"; cat "$E/joint.stdout"; [ "$rc" -eq 0 ] || fail "joint exit $rc"
echo "PASSED" | tee "$E/STATUS"
