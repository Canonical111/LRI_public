# C8(3) production prod1-20261008 environment (C63d, window H11-prod-c63d-20261008); source in bash on symmetry.
source ~/c8d3/env.sh >/dev/null
export C8_PACKAGE=$C8_ROOT/pkg/4fbd1bae5a88; cd "$C8_PACKAGE"
source slurm/sites/symmetry/profiles.sh
c8_profile lanes; unset C8_LANE_DRILL C8_LANE_CPUS C8_LANE_TIME
export C8_BUDGET_LINE=production C8_PRODUCTION_SU_CAP=20000
unset C8_COMPUTE_CAP
export C8_RESERVATION='mode=reservation;id=H11-prod-c63d-20261008;amd_nodes=9;amd_total=12;until=2026-10-14T12:00:00Z'
export C8_OTHER_SITE_SU='dev=1912.26;pilot=0.00;production=0.00;asof=2026-10-12T04:02:39Z;ref=expanse tools/budget.py own totals at 2026-10-12T04:02:39Z'
export E=$C8_ROOT/evidence/4fbd1bae5a88/production
export C8_RUN=$C8_ROOT/runs/prod1-20261008
export C8_MERGE_SBATCH_ARGS="-p amdq -c 64 --mem=240G -t $(python3 -c "import json;print(json.load(open('$C8_RUN/manifest.json'))['scale']['suggested_merge_time'])")"
export C8_LANE_TIME=07:30:00
SUB="python3 -B $C8_PACKAGE/tools/slurm_submit.py"
