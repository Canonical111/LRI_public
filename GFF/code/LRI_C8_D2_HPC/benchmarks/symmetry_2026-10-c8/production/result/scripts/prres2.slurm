#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 6 --mem=32G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Post-production steps, part 2 (2026-10-07). In job 571287, `design.py report --pilot <the batch>` exited 2 before it
# wrote anything: its target table sizes base counts from the campaign's largest per-replicate point count (524,288 in
# this batch, against 4,096 in a pilot), so even the minimum design (r = 32, s = 1) has 252,175 checkpoints against the
# default per-batch cap of 200,000. The caps bound the target table's hypothetical designs only. The tail statistics
# (`tails`, `--tails-out`) and the bundle block do not depend on them. Here the report runs with the two caps raised
# explicitly (--max-checkpoints 100000000 --max-tasks 2000000000; check_options requires only positive integers), so
# the heavy-tail confirmation of docs/DESIGN.md "After the pilot" step 2 comes from the tool itself. The target table it
# prints describes designs scaled to this batch's per-replicate cost and is NOT a design input. pr_followup.py runs
# beside it. Reads the batch; writes only this job's evidence folder.
# Usage (login node): sbatch -J c8d2-prres2 --export=ALL prres2.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e
BUNDLE=/mnt/beegfs/zzheng1/c8-d2/designs/pilot1-20261006-ddmp256-2.5e-4
WK=/mnt/beegfs/zzheng1/c8d2/work/prod-ba68f401e46e
CAPS=(--max-checkpoints 100000000 --max-tasks 2000000000)
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/prres2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $PKG ($(cat "$PKG.commit")); batch $RUN; evidence $E"
cd "$PKG" || exit 64
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" "$BUNDLE/design_meta.json" tools/design.py "$WK"/pr_followup.py "$WK"/prres2.slurm | tee "$E/inputs.sha256"
( t=$(date +%s); /usr/bin/time -v -o "$E/time_report.txt" python3 -B tools/design.py report --pilot "$RUN" "${CAPS[@]}" --json "$E/report.json" --tails-out "$E/tails.csv" \
    > "$E/report.txt" 2>&1; echo "report exit $? after $(( $(date +%s) - t )) s" > "$E/report.exit" ) &
P1=$!
( t=$(date +%s); /usr/bin/time -v -o "$E/time_report_bundle.txt" python3 -B tools/design.py report --pilot "$RUN" --bundle "$BUNDLE" "${CAPS[@]}" --json "$E/report_bundle.json" \
    > "$E/report_bundle.txt" 2>&1; echo "report --bundle exit $? after $(( $(date +%s) - t )) s" > "$E/report_bundle.exit" ) &
P2=$!
( t=$(date +%s); /usr/bin/time -v -o "$E/time_followup.txt" python3 -B "$WK/pr_followup.py" --package "$PKG" --run "$RUN" --out "$E/followup.json" \
    > "$E/followup.stdout" 2>&1; echo "followup exit $? after $(( $(date +%s) - t )) s" > "$E/followup.exit" ) &
P3=$!
wait $P1 $P2 $P3
status=0
for f in report.exit report_bundle.exit followup.exit; do cat "$E/$f"; grep -q 'exit 0 ' "$E/$f" || status=1; done
grep -v '^ *UNDEFINED\|^ *CONFIRMED' "$E/report.txt" | head -60; grep -c '^ *CONFIRMED' "$E/report.txt"
grep -E '^bundle |PROJECTION' "$E/report_bundle.txt"
cat "$E/followup.stdout"
grep -h -E 'Maximum resident|Elapsed' "$E"/time_*.txt
python3 - "$E/report.json" "$E/report_bundle.json" <<'EOF' | tee "$E/report_summary.txt"
import json, sys
r = json.load(open(sys.argv[1])); t = r['tails']
print('report: eta_node', r['eta_node'], r['eta_source'])
print('tails: graph_campaigns', t['graph_campaigns'], 'L8', t['graph_campaigns_L8'], 'screened', len(t['screened']), 'confirmed', len(t['confirmed']), 'undefined', len(t['undefined']))
for s in ('free', 'power'):
    c = [x for x in t['confirmed'] if x['sector'] == s]
    print(f'  confirmed {s}: {len(c)}; xi_mean min {min((x["xi_mean"] for x in c), default=None)} max {max((x["xi_mean"] for x in c), default=None)}; points min {min((x["points"] for x in c), default=None)}')
print('sector_P8', json.dumps(r['sector_P8']))
for st, x in r['strata'].items():
    if x.get('graphs'): print(f'  {st}: kurtosis {x.get("kurtosis")} skew {x.get("skewness")} share {x.get("largest_share")} P8 {x.get("P8")} flag {x.get("P8_flag")}')
for x in r['targets']: print('  target', {k: x.get(k) for k in ('target_rel', 'target_se', 'predicted_se_with_margin', 'allocated_core_hours', 'batches', 'error')})
b = json.load(open(sys.argv[2])).get('bundle') or {}
print('bundle', {k: b.get(k) for k in ('kind', 'se_total', 'se_raw_total', 'batches', 'agrees', 'pilot_is_the_frozen_pilot', 'relative_difference')})
EOF
gzip -k "$E/tails.csv" "$E/report.json" "$E/report_bundle.json" 2>/dev/null
sha256sum "$E"/tails.csv "$E"/report.json "$E"/report_bundle.json > "$E/large_files.sha256" 2>/dev/null
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" > "$E/batch_after.sha256"; cmp <(head -2 "$E/inputs.sha256") "$E/batch_after.sha256" && echo "batch manifest and result unchanged"
rm -rf "$TMPDIR"; echo "done at $(date -Is), status $status"; exit $status
