#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=64G -t 03:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Post-production steps of the C8(2) production batch (2026-10-07; docs/HPC.md "Pilot runbook" step 4 for a production
# batch, docs/DESIGN.md "Production batches" and "After the pilot" step 2; production/submit_sequence.sh section 7).
# Reads the campaign; writes only this job's evidence folder and the combine output directory (new, no-clobber).
#  0. sha256 of the inputs; production.py status (full); verify_result.py of C8_result.json.
#  1. accounting.py (complete only once every ledger job is terminal) and sacct -X --duplicates of every ledger job.
#  2. combine.py on the K = 1 batch -> $OUT/C8_final.json; verify_result.py on it; C8_final vs C8_result.
#  3. design.py report --pilot <the batch> --json --tails-out (heavy tails at >= 32,768 points per replicate);
#     design.py report --pilot <the batch> --bundle <its bundle> (the bundle's SE recomputed from the batch's sigma:
#     a PROJECTION, since the batch is not the bundle's frozen pilot).
#  4. pr_result_analysis.py: realized vs predicted variance, the pilot's screen followed up, the confirmed tails' share
#     and growth, cost vs estimate.
# Steps 2-4 run concurrently (single-threaded each). Usage (login node): sbatch -J c8d2-prres --export=ALL prres.slurm
# Test mode (C8_PRRES_TEST=1): only step 4 on the pilot against itself, into a test evidence folder.
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
PILOT=/mnt/beegfs/zzheng1/c8-d2/pilot1-20261006-ba68f401e46e
BUNDLE=/mnt/beegfs/zzheng1/c8-d2/designs/pilot1-20261006-ddmp256-2.5e-4
OUT=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-final
WK=/mnt/beegfs/zzheng1/c8d2/work/prod-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prres.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $PKG ($(cat "$PKG.commit")); batch $RUN; evidence $E"
{ hostname; lscpu | grep -E 'Model name|^CPU\(s\)'; } > "$E/node.txt"
cd "$PKG" || exit 64
if [ "${C8_PRRES_TEST:-0}" = 1 ]; then
  /usr/bin/time -v -o "$E/time_analysis_test.txt" python3 -B "$WK/pr_result_analysis.py" --package "$PKG" --run "$PILOT" --pilot "$PILOT" --out "$E/analysis_test.json" \
    > "$E/analysis_test.stdout" 2>&1; s=$?
  cat "$E/analysis_test.stdout"; grep -E 'Maximum resident|Elapsed' "$E/time_analysis_test.txt"; rm -rf "$TMPDIR"; echo "test done at $(date -Is), exit $s"; exit $s
fi
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" "$RUN/submissions.jsonl" "$BUNDLE/design_meta.json" "$PILOT/manifest.json" "$PILOT/C8_result.json" \
  inputs/manifest.json tools/{design,production,accounting,ledger,verify_result,combine,assemble}.py "$WK"/pr_result_analysis.py "$WK"/prres.slurm | tee "$E/inputs.sha256"
status=0
t=$(date +%s); python3 -B tools/production.py status "$RUN" > "$E/status.txt" 2>&1; s=$?; echo "status exit $s after $(( $(date +%s) - t )) s"; tail -3 "$E/status.txt"; [ $s -eq 0 ] || status=$s
python3 -B tools/verify_result.py "$RUN/C8_result.json" > "$E/verify_result.txt" 2>&1; s=$?; echo "verify_result (C8_result.json) exit $s"; tail -3 "$E/verify_result.txt"; [ $s -eq 0 ] || status=$s
python3 -B tools/accounting.py "$RUN" --output "$E/accounting.json" > "$E/accounting.stdout" 2>&1; s=$?; echo "accounting exit $s"; [ $s -eq 0 ] || status=$s
JOBS=$(python3 -c "import json;print(','.join(sorted({json.loads(l)['jobid'] for l in open('$RUN/submissions.jsonl') if l.strip()})))")
sacct -X --duplicates -j "$JOBS" -o JobID,JobName%22,Partition,State%20,Submit,Start,End,Elapsed,ElapsedRaw,AllocCPUS,NodeList > "$E/sacct.txt" 2>&1
sacct -X --duplicates -j 570753 -o JobID,JobName%22,Partition,State%20,Submit,Start,End,Elapsed,ElapsedRaw,AllocCPUS,NodeList > "$E/sacct_probe.txt" 2>&1
python3 -c "import json;a=json.load(open('$E/accounting.json'));print('accounting', {k:a.get(k) for k in ('complete','allocated_core_hours','work_core_hours','overhead_core_hours','busy_thread_core_hours','eta_node','core_hours_by_role','ledger_jobs','sacct_records')})"
# 2-4 concurrently
( t=$(date +%s); /usr/bin/time -v -o "$E/time_combine.txt" python3 -B tools/combine.py "$RUN" --output "$OUT" > "$E/combine.stdout" 2> "$E/combine.stderr"; s=$?
  echo "combine exit $s after $(( $(date +%s) - t )) s" > "$E/combine.exit"
  python3 -B tools/verify_result.py "$OUT/C8_final.json" > "$E/verify_final.txt" 2>&1; echo "verify_result (C8_final.json) exit $?" >> "$E/combine.exit" ) &
P1=$!
( t=$(date +%s); /usr/bin/time -v -o "$E/time_report.txt" python3 -B tools/design.py report --pilot "$RUN" --json "$E/report.json" --tails-out "$E/tails.csv" > "$E/report.txt" 2>&1; s=$?
  echo "report exit $s after $(( $(date +%s) - t )) s" > "$E/report.exit"
  t=$(date +%s); /usr/bin/time -v -o "$E/time_report_bundle.txt" python3 -B tools/design.py report --pilot "$RUN" --bundle "$BUNDLE" --json "$E/report_bundle.json" > "$E/report_bundle.txt" 2>&1; s=$?
  echo "report --bundle exit $s after $(( $(date +%s) - t )) s" >> "$E/report.exit" ) &
P2=$!
( t=$(date +%s); /usr/bin/time -v -o "$E/time_analysis.txt" python3 -B "$WK/pr_result_analysis.py" --package "$PKG" --run "$RUN" --pilot "$PILOT" --accounting "$E/accounting.json" \
    --out "$E/analysis.json" > "$E/analysis.stdout" 2>&1; s=$?
  echo "analysis exit $s after $(( $(date +%s) - t )) s" > "$E/analysis.exit" ) &
P3=$!
wait $P1 $P2 $P3
cat "$E/combine.exit" "$E/combine.stdout" "$E/combine.stderr"; tail -3 "$E/verify_final.txt"
cat "$E/report.exit"; tail -25 "$E/report.txt"; grep -E '^bundle |PROJECTION' "$E/report_bundle.txt"
cat "$E/analysis.exit" "$E/analysis.stdout"
grep -h -E 'Maximum resident|Elapsed' "$E"/time_*.txt
for f in combine.exit report.exit analysis.exit; do grep -q 'exit [1-9]' "$E/$f" && status=1; done
grep -q 'verify_result (C8_final.json) exit 0' "$E/combine.exit" || status=1
python3 - "$RUN/C8_result.json" "$OUT/C8_final.json" <<'EOF' | tee "$E/final_vs_result.txt"
import json, sys
r, f = (json.load(open(p)) for p in sys.argv[1:3])
print('C8_result', r['C8_full'], r['sampling_standard_error']); print('C8_final ', f['C8_full'], f['sampling_standard_error'])
print('identical C8_full and SE:', r['C8_full'] == f['C8_full'] and r['sampling_standard_error'] == f['sampling_standard_error'])
print('final', f.get('final'), 'status', f.get('status'), 'batches', json.dumps(f.get('batches'))[:400])
print('coefficients equal:', r['coefficients'] == f['coefficients'])
EOF
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" "$RUN/submissions.jsonl" > "$E/batch_after.sha256"; cmp <(head -3 "$E/inputs.sha256") "$E/batch_after.sha256" && echo "batch manifest, result and ledger unchanged"
gzip -k "$E/tails.csv" "$E/report.json" 2>/dev/null
ls -la "$OUT" > "$E/combine_output_listing.txt"; sha256sum "$OUT"/* >> "$E/combine_output_listing.txt"
rm -rf "$TMPDIR"; echo "done at $(date -Is), status $status"; exit $status
