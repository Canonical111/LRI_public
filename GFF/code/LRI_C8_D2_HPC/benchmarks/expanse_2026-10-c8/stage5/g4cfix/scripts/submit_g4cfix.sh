#!/bin/bash
# Mac driver of the Stage-5 G4c-fix check (g4cfix_check.slurm) on Expanse. Run from the repository root with the fix
# commit checked out and nothing uncommitted under tools/ src/ tests/ Makefile. It:
#   1. extracts `git archive HEAD` into $C8_DATA/work/g4cfix-<sha12> (refused when it exists) and checks it file by file
#      against the archive (ckpt_fix/scripts/export_check.py -> ../setup_export_check_<sha12>.json);
#   2. runs the H7E-R admission (stage4a/scripts/h7_admit.py on a fresh `squeue -A <ACCOUNT>`; record in ../admission/);
#   3. submits the job (shared, 16 CPUs, 32 GB, 0:45) and prints its id and log.
# Rules: the existing ControlMaster only (`ssh -O check expanse` must say "Master running"); one job.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); cd "$S/../../../../.."
[ -f Makefile ] && [ -e .git ] || { echo "run from a checkout of the package" >&2; exit 64; }
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster for expanse; nothing done" >&2; exit 69; }
dirty=$(git status --porcelain -- tools src tests Makefile benchmarks/expanse_2026-10-c8/stage5/g4cfix/scripts)
[ -z "$dirty" ] || { echo "uncommitted changes in exported paths:"; echo "$dirty"; exit 64; } >&2
D=<SCRATCH>/temp_project/c8d2; R=benchmarks/expanse_2026-10-c8/stage5/g4cfix; A=$R/admission; mkdir -p "$A"
h=$(git rev-parse HEAD); t=${h:0:12}; W=$D/work/g4cfix-$t; LT=$(mktemp -d "${TMPDIR:-/tmp}/c8d2_g4cfix.XXXXXX")
ssh -T expanse "lfs quota -u <USER> /expanse/lustre/scratch" | tail -2 | tee -a "$A/lfs_quota.txt"
if ssh -T expanse "test -e $W"; then echo "$W exists; refusing" >&2; exit 64; fi
git archive --format=tar "$h" | ssh -T expanse "mkdir -p $W && tar -x -C $W"
ssh -T expanse "python3 - $W" < benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/tree_manifest.py > "$LT/tree.txt"
python3 benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py "$h" "$LT/tree.txt" expanse "$W" "$R/setup_export_check_$t.json" >&2
name=c8d2-s5-g4cfix
ssh -T expanse "squeue -A <ACCOUNT> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$LT/squeue.txt"
cp "$LT/squeue.txt" "$A/squeue_before_${name}_$(date +%Y%m%dT%H%M%S).txt"
python3 benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py --site expanse --me <USER> --job "$name" --partition shared --nodes 1 < "$LT/squeue.txt" | tee -a "$A/h7e_r_admission.jsonl"
id=$(ssh -T expanse "cd $D && C8_WORK=$W sbatch --parsable --export=ALL $W/$R/scripts/g4cfix_check.slurm")
echo "$(date -u +%FT%TZ) $name $id shared C8_WORK=$W" >> "$A/submitted.txt"
echo "job $id; log $D/logs/${name}_$id.out; evidence $D/evidence/g4cfix-$t/g4cfix.$id.0; work $W"
ssh -T expanse "squeue -u <USER> -h -o '%i %j %T %P %M %l %r'" >&2
rm -rf "$LT"
