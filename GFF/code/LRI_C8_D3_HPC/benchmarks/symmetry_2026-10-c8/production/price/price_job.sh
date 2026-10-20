#!/bin/bash
set -eo pipefail
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
set +e
$PY -B tools/design_fallback.py report --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/932f8e913c4c/cost_models/gmp_symmetry_epyc7543_c8.json --pc  --target-se 1 --json /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_pc_m15.json > /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_pc_m15.out 2>&1; echo "se1_pc_m15 rc=$?"
$PY -B tools/design_fallback.py report --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/932f8e913c4c/cost_models/gmp_symmetry_epyc7543_c8.json --pc  --target-se 1 --variance-margin 1.0 --json /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_pc_m10.json > /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_pc_m10.out 2>&1; echo "se1_pc_m10 rc=$?"
$PY -B tools/design_fallback.py report --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/932f8e913c4c/cost_models/gmp_symmetry_epyc7543_c8.json --target-se 1 --json /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_nopc_m15.json > /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se1_nopc_m15.out 2>&1; echo "se1_nopc_m15 rc=$?"
$PY -B tools/design_fallback.py report --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/932f8e913c4c/cost_models/gmp_symmetry_epyc7543_c8.json --pc  --target-se 1.15 --json /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se115_pc_m15.json > /mnt/beegfs/zzheng1/c8d3/evidence/932f8e913c4c/price/se115_pc_m15.out 2>&1; echo "se115_pc_m15 rc=$?"
