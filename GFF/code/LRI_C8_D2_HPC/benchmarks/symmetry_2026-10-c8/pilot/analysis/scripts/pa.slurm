#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Post-pilot analysis of the C8(2) L8 pilot (2026-10-06; docs/DESIGN.md, "After the pilot", steps 1-2 and the candidate
# freezes of step 4; nothing is planned or submitted). Reads the pilot; writes only this job's evidence folder and NEW
# bundles under /mnt/beegfs/zzheng1/c8-d2/designs/ (design.py publishes atomically and never overwrites). No seed is drawn.
#  0. production.py status (exit 0), verify_result.py of C8_result.json, accounting.py (complete: eta_node), sacct -X
#     --duplicates of every ledger job.
#  1. design.py report (exact path) with --json and --tails-out; design.py report --numerics dd+mp256 --cost-model
#     <the profile model> (route (b) re-costed table).
#  2. design.py freeze (non-test) at --target-rel 1e-3, 5e-4, 2.5e-4, 1.35e-4: (a) the exact path, (b) route (b) with
#     the approval, the profile cost model (18e50440...) and the gate record of job 570574 (42e6d2d8...);
#     --spent-core-hours = 1,930 (development total) + ceil(the pilot's allocated core-hours), --total-cap 1,000,000
#     (chosen not to bind), --seeds-log $C8_SEEDS (read: its seeds are recorded as forbidden).
#  3. design.py report --bundle for each bundle (its SE recomputed from its counts; agrees expected).
#  4. pa_analysis.py: per-index measured vs estimated, the pilot efficiencies, bundle sizes, walls on 4/8/16 nodes,
#     the Expanse cost-model ratio and the stand-in decomposition against J-SWEEP-2.
# Usage (from the login node): sbatch -J c8d2-pa --export=ALL pa.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_SEEDS:?}"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/pilot1-20261006-ba68f401e46e
SW=/mnt/beegfs/zzheng1/c8-d2/sweep2-5d7586e9f1ab
DES=/mnt/beegfs/zzheng1/c8-d2/designs
WK=/mnt/beegfs/zzheng1/c8d2/work/pilot-analysis-ba68f401e46e
CM_DD=$PKG/cost_models/gmp_symmetry_amd_c8_dd+mp256.json
GATE=$PKG/benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json
REF='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (C62d PLAN-REVIEW-LOG)'
DEV=1930; CAP=1000000
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/pa.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir -p "$(dirname "$E")" "$DES"; mkdir "$E" || exit 64
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $PKG ($(cat "$PKG.commit")); pilot $RUN; evidence $E"
{ hostname; lscpu | grep -E 'Model name|^CPU\(s\)'; } > "$E/node.txt"
cd "$PKG" || exit 64
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" "$CM_DD" cost_models/gmp_symmetry_amd_c8.json cost_models/gmp_expanse_amd_c8.json "$GATE" \
  inputs/manifest.json tools/{design,production,accounting,ledger,verify_result}.py "$WK"/pa_analysis.py "$WK"/pa.slurm "$C8_SEEDS" | tee "$E/inputs.sha256"
status=0
python3 -B tools/production.py status "$RUN" > "$E/status.txt" 2>&1; s=$?; echo "status exit $s"; [ $s -eq 0 ] || status=$s
python3 -B tools/verify_result.py "$RUN/C8_result.json" > "$E/verify_result.txt" 2>&1; s=$?; echo "verify_result exit $s"; tail -3 "$E/verify_result.txt"; [ $s -eq 0 ] || status=$s
python3 -B tools/accounting.py "$RUN" --output "$E/accounting.json" > "$E/accounting.stdout" 2>&1; s=$?; echo "accounting exit $s"; [ $s -eq 0 ] || { echo "accounting incomplete; nothing designed"; exit 4; }
JOBS=$(python3 -c "import json;print(','.join(json.loads(l)['jobid'] for l in open('$RUN/submissions.jsonl') if l.strip()))")
sacct -X --duplicates -j "$JOBS" -o JobID,JobName%28,Partition,NodeList,AllocCPUS,Submit,Start,End,ElapsedRaw,State > "$E/sacct.txt" 2>&1
SPENT=$(python3 -c "import json,math;a=json.load(open('$E/accounting.json'));print($DEV+math.ceil(a['allocated_core_hours']))")
python3 -c "import json;a=json.load(open('$E/accounting.json'));print('accounting', {k:a[k] for k in ('complete','allocated_core_hours','work_core_hours','overhead_core_hours','busy_thread_core_hours','eta_node','core_hours_by_role')})"
echo "spent core-hours $SPENT (development $DEV + the pilot's allocated core-hours, rounded up); total cap $CAP"
t=$(date +%s); python3 -B tools/design.py report --pilot "$RUN" --json "$E/report_exact.json" --tails-out "$E/tails.csv" > "$E/report_exact.txt" 2>&1; s=$?
echo "report (exact) exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || status=$s
t=$(date +%s); python3 -B tools/design.py report --pilot "$RUN" --numerics dd+mp256 --cost-model "$CM_DD" --json "$E/report_ddmp256.json" > "$E/report_ddmp256.txt" 2>&1; s=$?
echo "report (dd+mp256, route (b)) exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || status=$s
BUNDLES=""
for T in 1e-3 5e-4 2.5e-4 1.35e-4; do
  for R in exact ddmp256; do
    N=pilot1-20261006-$R-$T; B=$DES/$N
    if [ "$R" = exact ]; then X=(); else X=(--numerics dd+mp256 --approved-numerics-change "$REF" --cost-model "$CM_DD" --numerics-gate "$GATE"); fi
    t=$(date +%s)
    /usr/bin/time -v -o "$E/time_freeze_$N.txt" python3 -B tools/design.py freeze --pilot "$RUN" --target-rel "$T" --spent-core-hours "$SPENT" --total-cap "$CAP" \
      --seeds-log "$C8_SEEDS" --out "$B" "${X[@]}" > "$E/freeze_$N.stdout" 2>&1; s=$?
    echo "freeze $N exit $s after $(( $(date +%s) - t )) s"; [ $s -eq 0 ] || { status=$s; tail -3 "$E/freeze_$N.stdout"; continue; }
    cp -p "$B/design.json" "$E/design_$N.json"; cp -p "$B/design_meta.json" "$E/design_meta_$N.json"
    sha256sum "$B"/design.json "$B"/design_meta.json "$B"/counts/* >> "$E/bundles.sha256"
    python3 -B tools/design.py report --pilot "$RUN" --bundle "$B" --json "$E/report_bundle_$N.json" > "$E/report_bundle_$N.txt" 2>&1; s=$?
    echo "report --bundle $N exit $s: $(grep -E '^bundle ' "$E/report_bundle_$N.txt" | cut -c1-260)"; [ $s -eq 0 ] || status=$s
    BUNDLES="$BUNDLES $B"
  done
done
tar czf "$E/bundles.tgz" -C "$DES" $(for b in $BUNDLES; do basename "$b"; done)
t=$(date +%s)
python3 -B "$WK/pa_analysis.py" --package "$PKG" --run "$RUN" --sweep "$SW" --accounting "$E/accounting.json" --bundles $BUNDLES --out "$E/pa_analysis.json" \
  > "$E/pa_analysis.stdout" 2>&1; s=$?; echo "pa_analysis exit $s after $(( $(date +%s) - t )) s"; tail -40 "$E/pa_analysis.stdout"; [ $s -eq 0 ] || status=$s
sha256sum "$RUN/manifest.json" "$RUN/C8_result.json" > "$E/pilot_after.sha256"; cmp <(head -2 "$E/inputs.sha256") "$E/pilot_after.sha256" && echo "pilot manifest and result unchanged"
rm -rf "$TMPDIR"; echo "done at $(date -Is), status $status"; exit $status
