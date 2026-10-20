#!/bin/bash
set -eo pipefail
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
set +e +o pipefail
$PY -B tools/production.py status /mnt/beegfs/zzheng1/c8d3/runs/thru-20261006; echo "status rc=$?"; $PY -B tools/verify_result.py /mnt/beegfs/zzheng1/c8d3/runs/thru-20261006; echo "verify_result rc=$?"
$PY -B tools/accounting.py /mnt/beegfs/zzheng1/c8d3/runs/thru-20261006 --json > /mnt/beegfs/zzheng1/c8d3/evidence/59d4922842ec/smk4/accounting.json; echo "accounting rc=$?"
$PY -B tools/thru_report.py /mnt/beegfs/zzheng1/c8d3/runs/thru-20261006 --job 570496 --accounting /mnt/beegfs/zzheng1/c8d3/evidence/59d4922842ec/smk4/accounting.json --sweep /mnt/beegfs/zzheng1/c8d3/runs/sweep2-20261006   --reference-opt-speed /mnt/beegfs/zzheng1/c8d3/evidence/59d4922842ec/opt_final/speed/opt_speed.json --reference-binary CAND --reference-shape 8x8   --hook-dir /mnt/beegfs/zzheng1/c8d3/evidence/59d4922842ec/smk4_hook --parts perf3,orc13,orc5 --strict --output /mnt/beegfs/zzheng1/c8d3/evidence/59d4922842ec/smk4/thru_report.json; echo "thru_report rc=$?"
