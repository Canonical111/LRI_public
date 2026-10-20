#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=4G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check v2 (2026-10-08): negative and positive controls of tc_cert (tc_negctl.py: forest term dropped, numerator
# doubled, rate tables x3 and x2.4 taken as given (infinite variance), one stored rate tampered, and the unmodified
# graphs), with explicit assertions. The control payloads, the list, tc_cert's records and the assertion results are
# written to this job's evidence folder. Exits nonzero (STATUS = FAILED) unless tc_cert exits 3 (records not
# certified, as these must be) and every control's assertion holds.
# Usage (login node): sbatch -J c8d2-tc2neg --export=ALL,TC_CERT_SEED=<seed> tc_negctl.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck2-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tc2neg.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
fail() { echo "FAILED: $*" | tee "$E/STATUS"; rm -rf "$TMPDIR"; exit 1; }
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
[ -n "${TC_CERT_SEED:-}" ] || fail "TC_CERT_SEED not set"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); export $PKG; evidence $E; seed $TC_CERT_SEED"
sha256sum "$WK/tc_cert.cpp" "$WK/tc_negctl.py" "$WK/tc_negctl.slurm" "$PKG/inputs/inventory.json" | tee "$E/inputs.sha256"
g++ -O2 -std=c++17 -fopenmp -o "$TMPDIR/tc_cert" "$WK/tc_cert.cpp" || fail "compile"
CMD_MAKE=(python3 -B "$WK/tc_negctl.py" make "$PKG/inputs" "$E")
CMD_CERT=("$TMPDIR/tc_cert" "$E/negctl_list.txt" "$E/cert.jsonl" --seed "$TC_CERT_SEED" --threads 4 --primes 4 --points 2 --expect 9)
CMD_CHECK=(python3 -B "$WK/tc_negctl.py" check "$E" "$E/cert.jsonl")
printf '%q ' "${CMD_MAKE[@]}" > "$E/commands.txt"; echo >> "$E/commands.txt"
printf '%q ' "${CMD_CERT[@]}" | sed "s|$TMPDIR/tc_cert|tc_cert|" >> "$E/commands.txt"; echo >> "$E/commands.txt"
printf '%q ' "${CMD_CHECK[@]}" >> "$E/commands.txt"; echo '<tc_cert exit> negctl_check.json' >> "$E/commands.txt"
"${CMD_MAKE[@]}" || fail "make controls"
t=$(date +%s); "${CMD_CERT[@]}" 2> "$E/cert.stderr"; rc=$?
echo "$rc" > "$E/cert.exit"; echo "tc_cert exit $rc after $(( $(date +%s) - t )) s"; cat "$E/cert.stderr"
"${CMD_CHECK[@]}" "$rc" "$E/negctl_check.json" | tee "$E/negctl_check.txt"; rc2=${PIPESTATUS[0]}
echo "$rc2" > "$E/check.exit"
[ "$rc2" -eq 0 ] || fail "negative-control assertions (exit $rc2)"
echo "PASSED" | tee "$E/STATUS"
rm -rf "$TMPDIR"
