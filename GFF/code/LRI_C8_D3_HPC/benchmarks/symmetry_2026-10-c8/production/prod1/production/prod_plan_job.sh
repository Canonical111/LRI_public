#!/bin/bash
set -eo pipefail
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
slurm/plan.sh /mnt/beegfs/zzheng1/c8d3/runs/prod1-20261008 --design /mnt/beegfs/zzheng1/c8d3/evidence/4fbd1bae5a88/production/design_prod --approved-fallback 'PLAN-REVIEW-LOG.md:1443 (user decision 2026-10-08: design A, target SE 1, line 20,000 core-h)' --threads 8 --index-hours 1 --backend gmp --mp-check on --cost-model /mnt/beegfs/zzheng1/c8d3/pkg/4fbd1bae5a88/cost_models/gmp_symmetry_epyc7543_c8.json --forbid-seeds-from $C8_SEEDS --seed 7204841255549554256
set +e +o pipefail
$PY -B tools/cost_identity.py check /mnt/beegfs/zzheng1/c8d3/runs/prod1-20261008; echo "cost_identity rc=$?"
$PY -B tools/production.py role /mnt/beegfs/zzheng1/c8d3/runs/prod1-20261008
$PY -c "import json,sys;m=json.load(open(sys.argv[1]));e=m['estimates'];print(m['campaign_role'],m['cost_basis'],len(m['jobs']),'jobs',e.get('total_core_hours'),'core-h; max index wall',e.get('max_index_wall_seconds'))" /mnt/beegfs/zzheng1/c8d3/runs/prod1-20261008/manifest.json
