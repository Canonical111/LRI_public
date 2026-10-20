#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=16G -t 03:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check (2026-10-07): the per-graph analytic certificate (tc_cert.cpp) over every inventory graph L3..L8 of both
# sectors in the export's packs (members checked against inventory.json sha256). Reads the export; writes only this
# job's evidence folder. Usage (login node): sbatch -J c8d2-tccert --export=ALL tc_cert.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tccert.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); export $PKG; evidence $E"
sha256sum "$WK/tc_cert.cpp" "$WK/tc_cert_list.py" "$WK/tc_cert.slurm" "$PKG/inputs/inventory.json" | tee "$E/inputs.sha256"
g++ --version | head -1 > "$E/compiler.txt"
g++ -O2 -std=c++17 -fopenmp -o "$TMPDIR/tc_cert" "$WK/tc_cert.cpp" || exit 65
t=$(date +%s); python3 -B "$WK/tc_cert_list.py" "$PKG/inputs" "$E/members.txt" --loops 3-8 2> "$E/list.stderr"; echo "list exit $? after $(( $(date +%s) - t )) s" | tee "$E/list.exit"
cat "$E/list.stderr"
t=$(date +%s); /usr/bin/time -v -o "$E/time_cert.txt" "$TMPDIR/tc_cert" "$E/members.txt" "$E/cert.jsonl" 8; echo "cert exit $? after $(( $(date +%s) - t )) s" | tee "$E/cert.exit"
wc -l "$E/members.txt" "$E/cert.jsonl"
python3 - "$E/cert.jsonl" <<'PY'
import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
c = collections.Counter((r['sector'], r['L'], r['legacy_rates'], r['certified'], r['bounded']) for r in R)
for k, v in sorted(c.items()): print(k, v)
for k in ('rate_mismatch', 'structural_mismatch', 'failures', 'greedy_fail', 'degenerate_retries'): print(k, sum(r[k] for r in R))
print('errors', sum(1 for r in R if r['error']))
for L in range(3, 9):
    X = [r for r in R if r['L'] == L]
    if X: print(L, 'xi_bound max a/b', max(r['xi_bound_a'] for r in X), max(r['xi_bound_b'] for r in X), 'min 2nd margin a/b', min(r['min_second_margin_a'] for r in X), min(r['min_second_margin_b'] for r in X))
PY
rm -rf "$TMPDIR"
