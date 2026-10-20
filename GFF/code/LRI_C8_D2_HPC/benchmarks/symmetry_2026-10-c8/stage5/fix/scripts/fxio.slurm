#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# A-ORC-13 on real Slurm after the F9 fix (R07): a subset of a throughput-drill-shaped test campaign (J-SMK-4's plan
# arguments with a fresh seed, planned with the merged head), run claim by claim with the package's own
# `production.py run RUN --index I`, which now logs one `claim_io {json}` line at exit (rchar of /proc/self/io, the
# native launches' own rchar, fingerprint_bytes / fingerprint_rchar, the claim's own bytes per category, non_own_bytes).
# One whole AMD node in J-SMK-4's lane shape: SLOTS is a ';'-separated list of slots, each a ','-separated list of
# indices run one after the other with --threads 8 on one NUMA node (numactl --cpunodebind=k --membind=k), 8 slots at
# most. Each run's stdout+stderr is <evidence>/logs/idx<I>.log. Then tools/claim_io.py RUN --logs <those logs> decides
# the plan's comparison (fingerprint_bytes identical per fingerprint key; non-own bytes, with and without the
# fingerprint, of the smallest against the largest group by tasks.sqlite size, > 10x apart, within max(10%, 2 MB)).
# The campaign is a test campaign: it is never merged, and the indices outside SLOTS are never run (one of them is
# used by the F5 vendor-refusal check, fxvendor.slurm).
# Usage: C8_PACKAGE=... C8_RUN=... SLOTS="38;39;0,1,2" sbatch --export=ALL -J c8d2-fxio fxio.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${SLOTS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=fxio.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" "$E/logs" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; run $C8_RUN; slots $SLOTS; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
IFS=';' read -ra S <<< "$SLOTS"; [ ${#S[@]} -le 8 ] || { echo "at most 8 slots" >&2; exit 64; }
t0=$(date +%s); pids=()
for k in "${!S[@]}"; do
  ( IFS=',' read -ra L <<< "${S[$k]}"
    for i in "${L[@]}"; do
      s=$(date +%s)
      numactl --cpunodebind=$k --membind=$k python3 -B "$C8_PACKAGE/tools/production.py" run "$C8_RUN" --index "$i" --threads 8 > "$E/logs/idx$i.log" 2>&1
      echo "slot $k index $i exit $? after $(( $(date +%s) - s )) s" | tee -a "$E/slots.txt"
    done ) & pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
echo "all slots done after $(( $(date +%s) - t0 )) s"
python3 -B "$C8_PACKAGE/tools/claim_io.py" "$C8_RUN" --logs "$E"/logs/idx*.log --output "$E/claim_io.json"; c=$?
echo "claim_io.py exit $c (0 pass, 1 fail, 2 undecided)"
grep -h '^claim_io ' "$E"/logs/idx*.log | wc -l | sed 's/^/claim_io lines: /'
ls "$TMPDIR" | head; rm -rf "$TMPDIR"
echo "finished $(date -Is), status $c"; exit $c
