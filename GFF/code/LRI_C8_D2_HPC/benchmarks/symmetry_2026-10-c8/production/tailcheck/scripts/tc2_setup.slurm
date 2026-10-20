#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Tail check, Codex follow-up (2026-10-08): register the two fresh seeds in symmetry's seed log (tools/seeds.py check,
# then add with a label): TC_CERT_SEED, the randomness (primes, evaluation points) of the multi-prime cancellation
# verification, and TC_DL_SEED, the base seed of the double-lift targeted nested-N runs; then write the DL run's setup
# (members checked by sha256, the two campaigns' scrambled power nets) with tc_nested.py --setup-only.
# Usage: sbatch -J c8d2-tc2setup --export=ALL,TC_CERT_SEED=<s>,TC_DL_SEED=<s>,TC_RUN=<dir> tc2_setup.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
WK=/mnt/beegfs/zzheng1/c8d2/work/tailcheck2-ba68f401e46e
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/tc2setup.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); cert seed $TC_CERT_SEED; dl seed $TC_DL_SEED; run $TC_RUN; evidence $E"
sha256sum "$WK/tc_nested.py" "$WK/tc_dl_graphs.txt" "$WK/tc2_setup.slurm" "$C8_SEEDS" | tee "$E/inputs.sha256"
cd "$PKG"
python3 -B tools/seeds.py check "$TC_CERT_SEED" --log "$C8_SEEDS" && echo "cert seed free in $C8_SEEDS"
python3 -B tools/seeds.py check "$TC_DL_SEED" --log "$C8_SEEDS" && echo "dl seed free in $C8_SEEDS"
python3 -B tools/seeds.py add --seed "$TC_CERT_SEED" --label "tc2cert/tc2neg (C8(2) tail check: randomness of the multi-prime randomized cancellation verification, primes and evaluation points; not an RQMC seed, never in an estimate)" --log "$C8_SEEDS"
python3 -B tools/seeds.py add --seed "$TC_DL_SEED" --label "$TC_RUN (C8(2) tail check: double-lift targeted nested-N runs of 16 power L8 graphs, test only, never in an estimate)" --log "$C8_SEEDS"
python3 -B tools/seeds.py list --log "$C8_SEEDS" | tail -4
sha256sum "$C8_SEEDS" | tee "$E/seeds_after.sha256"; cp "$C8_SEEDS" "$E/forbidden_seeds_after.json"
python3 -B "$WK/tc_nested.py" --pkg "$PKG" --rundir "$TC_RUN" --graphs "$WK/tc_dl_graphs.txt" --seed "$TC_DL_SEED" --reps 32 --setup-only
cp "$TC_RUN/setup.json" "$E/"; ls -la "$TC_RUN"
echo "done at $(date -Is)"
