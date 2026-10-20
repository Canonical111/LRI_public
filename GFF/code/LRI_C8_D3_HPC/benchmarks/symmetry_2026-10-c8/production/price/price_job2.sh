#!/bin/bash
set -eo pipefail
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
set +e
for v in "se1_pc_m15|--target-se 1" "se1_pc_m10|--target-se 1 --variance-margin 1.0" "se115_pc_m15|--target-se 1.15"; do
  n=${v%%|*}; a=${v#*|}
  $PY -B tools/design_fallback.py report --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --pc /mnt/beegfs/zzheng1/c8d3/runs/pilotC-s6-20261008 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/932f8e913c4c/cost_models/gmp_symmetry_epyc7543_c8.json $a --json /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/$n.json > /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/$n.out 2>&1; echo "$n rc=$?"
done
