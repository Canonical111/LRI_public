#!/bin/bash
set -eo pipefail
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
$PY -B tools/design_fallback.py freeze --pilot /mnt/beegfs/zzheng1/c8d3/runs/pilotF-s6-20261007 --pc /mnt/beegfs/zzheng1/c8d3/runs/pilotC-s6-20261008 --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/4fbd1bae5a88/cost_models/gmp_symmetry_epyc7543_c8.json --out /mnt/beegfs/zzheng1/c8d3/evidence/4fbd1bae5a88/production/design_prod --target-se 1 --variance-margin 1.0 --spent-core-hours 512 --total-cap 20000 --seeds-log $C8_SEEDS > /mnt/beegfs/zzheng1/c8d3/evidence/4fbd1bae5a88/production/design_freeze.json
