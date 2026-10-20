#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=8G -t 03:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check v2 (2026-10-08): the multi-prime randomized cancellation verification (tc_cert.cpp v2: 4 random primes in
# [2^61, 2^62) x 2 random points per prime per graph) over every inventory graph L3..L8 of both sectors of the export's
# packs (members checked against inventory.json's sha256), then the pass/fail check tc_cert_check.py. Exits nonzero
# (and writes STATUS = FAILED) on a compile failure, a member-list failure, a nonzero tc_cert exit, a missing or extra
# record, or any failed check. Reads the export; writes only this job's evidence folder.
# Usage (login node): sbatch -J c8d2-tc2cert --export=ALL,TC_CERT_SEED=<seed> tc_cert.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck2-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tc2cert.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
fail() { echo "FAILED: $*" | tee "$E/STATUS"; rm -rf "$TMPDIR"; exit 1; }
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
[ -n "${TC_CERT_SEED:-}" ] || fail "TC_CERT_SEED not set"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); export $PKG; evidence $E; seed $TC_CERT_SEED"
echo "$TC_CERT_SEED" > "$E/seed.txt"
sha256sum "$WK/tc_cert.cpp" "$WK/tc_cert_list.py" "$WK/tc_cert_check.py" "$WK/tc_cert.slurm" "$PKG/inputs/inventory.json" | tee "$E/inputs.sha256"
g++ --version | head -1 > "$E/compiler.txt"
g++ -O2 -std=c++17 -fopenmp -o "$TMPDIR/tc_cert" "$WK/tc_cert.cpp" || fail "compile"
t=$(date +%s); python3 -B "$WK/tc_cert_list.py" "$PKG/inputs" "$E/members.txt" --loops 3-8 2> "$E/list.stderr"; rc=$?
echo "$rc" > "$E/list.exit"; echo "list exit $rc after $(( $(date +%s) - t )) s"; cat "$E/list.stderr"
[ "$rc" -eq 0 ] || fail "member list exit $rc"
t=$(date +%s); /usr/bin/time -v -o "$E/time_cert.txt" "$TMPDIR/tc_cert" "$E/members.txt" "$E/cert.jsonl" --seed "$TC_CERT_SEED" --threads 8 --primes 4 --points 2 --expect 24173 2> "$E/cert.stderr"; rc=$?
echo "$rc" > "$E/cert.exit"; echo "cert exit $rc after $(( $(date +%s) - t )) s"; cat "$E/cert.stderr"
python3 -B "$WK/tc_cert_check.py" "$E/members.txt" "$E/cert.jsonl" "$rc" "$E/cert_check.json" --expect 24173 --primes 4 --points 2 > "$E/cert_check.txt" 2>&1; rc2=$?
cat "$E/cert_check.txt"; echo "$rc2" > "$E/check.exit"
gzip -k "$E/cert.jsonl" "$E/members.txt"
[ "$rc" -eq 0 ] || fail "tc_cert exit $rc"
[ "$rc2" -eq 0 ] || fail "tc_cert_check exit $rc2"
echo "PASSED" | tee "$E/STATUS"
rm -rf "$TMPDIR"
