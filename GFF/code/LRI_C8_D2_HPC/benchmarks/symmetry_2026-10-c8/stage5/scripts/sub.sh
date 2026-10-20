#!/bin/bash
# Mac-side admission + sbatch for the Stage-5 symmetry jobs (package 5d7586e9f1ab; benchmarks/symmetry_2026-10-c8/stage5).
#   bash sub.sh NAME ADMIT_PARTITION "ENV=... ENV=..." <sbatch args...>
# 1. a fresh `squeue -u <USER>` snapshot (kept in admission/), 2. for an AMD partition (amdq, amddebugq, amdpreq) the H7
# check (stage4a/scripts/h7_admit.py of the Expanse folder: at most 4 live c8d2-* jobs on the AMD pool, the new one
# included; other <USER> jobs never counted or touched), 3. sbatch on symmetry with --parsable --export=ALL -J NAME
# from <SCRATCH>/c8d2, 4. one line in admission/submitted.txt. Prints the job id. ADMIT_PARTITION 'none':
# sharedq/debugq jobs (outside the H7 cap) get the snapshot but no cap check.
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd); R=$(cd "$S/.." && pwd); PKG=$(cd "$R/../../.." && pwd)
name=$1 part=$2 envs=$3; shift 3
ts=$(date -u +%Y%m%dT%H%M%SZ)
ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; squeue -u <USER> -h -r -o '%i|%T|%P|%q|%D|%u|%j'" > "$R/admission/squeue_before_${name}_$ts.txt" \
  || { echo "squeue failed; nothing submitted" >&2; exit 69; }
if [ "$part" != none ]; then
  <HOME>/anaconda3/bin/python3 "$PKG/benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py" --site symmetry --me <USER> --job "$name" --partition "$part" \
    < "$R/admission/squeue_before_${name}_$ts.txt" | tee -a "$R/admission/h7_admission.jsonl" >&2
fi
id=$(ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; cd <SCRATCH>/c8d2 && $envs sbatch --parsable --export=ALL -J $name $*")
echo "$ts $name $id $part $envs $*" >> "$R/admission/submitted.txt"
echo "$id"
