#!/bin/bash
# Copy the Stage-4c gate evidence (J-FLAG) from Expanse into benchmarks/expanse_2026-10-c8/stage4c/gate/ (Mac side; the
# existing ControlMaster only). Copied: the build record (s4cbuild.<job>.0 without files of 1 MiB or more; note that
# find -size -1M would match only empty files), the F1 baseline record (numerics_flags.json, baseline.json and the
# nets; the 450-digit reference files stay on Expanse, pinned by
# sha256 in baseline.json and listed in refs.sha256 here), and per gate run numerics_flags.json, f1/f1.json, f2/f2.json,
# f4/f4.json and f5/f5.json (f2/rows.csv.gz stays on Expanse, pinned by sha256 in f2.json), with each job's log.
#   bash fetch_gate.sh <sha12> <build job> <baseline job> <gate job>...
set -euo pipefail
ssh -O check expanse 2>&1 | grep -q 'Master running' || { echo "no ControlMaster; nothing done" >&2; exit 69; }
S=$(cd "$(dirname "$0")" && pwd); G=$S/..; D=<SCRATCH>/temp_project/c8d2
T=${1:?sha12}; B=${2:?build job}; F=${3:?baseline job}; shift 3
E=$D/evidence/$T
mkdir -p "$G/logs"
ssh -T expanse "cd $E && find s4cbuild.$B.0 -type f -size -1024k | tar -cf - -T -" | tar -xf - -C "$G"
ssh -T expanse "cd $E && tar -cf - s4cgate.$F.0/binaries.sha256 s4cgate.$F.0/env_expanse.sha256 s4cgate.$F.0/f1_baseline_full/numerics_flags.json s4cgate.$F.0/f1_baseline_full/f1_baseline/baseline.json s4cgate.$F.0/f1_baseline_full/f1_baseline/nets" | tar -xf - -C "$G"
ssh -T expanse "cd $E/s4cgate.$F.0/f1_baseline_full/f1_baseline && sha256sum refs/*" > "$G/s4cgate.$F.0/f1_baseline_full/f1_baseline/refs.sha256"
for j in "$B" "$F" "$@"; do
  for n in build baseline gate; do ssh -T expanse "cat $D/logs/c8d2-s4c-gate-${n}_$j.out 2>/dev/null" > "$G/logs/c8d2-s4c-gate-${n}_$j.out" || true; done
done
find "$G/logs" -type f -empty -delete
for j in "$@"; do
  ssh -T expanse "cd $E && find s4cgate.$j.0 -type f \( -name '*.sha256' -o -name numerics_flags.json -o -name f1.json -o -name f2.json -o -name f4.json -o -name f5.json \) | tar -cf - -T -" | tar -xf - -C "$G"
  ssh -T expanse "cd $E && find s4cgate.$j.0 -name rows.csv.gz -exec sha256sum {} \;" > "$G/s4cgate.$j.0/rows_csv.sha256" || true
done
ssh -T expanse "sacct -j $(IFS=,; echo "$B,$F,$*") -X -o JobID,JobName%24,Partition,AllocCPUS,Elapsed,State,ExitCode,NodeList,Start,End -P" > "$G/sacct.txt"
echo "copied into $G"; ls "$G"
