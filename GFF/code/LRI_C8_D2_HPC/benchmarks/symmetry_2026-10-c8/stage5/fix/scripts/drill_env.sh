# Shell setup of the post-merge sharedq lane drill J-DRL-8 on symmetry (PLAN "Recovery of a completed index"), sourced
# in fresh login shells with FXPKG set to the merged head's export: drill-mode lane workers (C8_LANE_DRILL=1, 2 CPUs,
# 3G, no --exclusive, --no-requeue) and 2-CPU merges on sharedq, as Stage 5's drills (stage5/scripts/drill_env.sh),
# outside the H7 AMD cap; sharedqos runs at most 4 jobs of a user at once. Plans are made in sharedq plan jobs
# (fxplan.slurm), never on the login node.
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
source "$HOME/c8d2/env.sh"
: "${FXPKG:?set FXPKG to the export}"
export C8_ENV_SETUP=$HOME/c8d2/env.sh C8_PACKAGE=$FXPKG
export C8_LANE_DRILL=1 C8_LANE_CPUS=2 C8_LANE_MEM=3G C8_MERGE_JOBS=2 C8_MERGE_MEM=3G C8_SBATCH_ARGS="-p sharedq"
export C8_LANE_TIME=00:30:00 C8_MERGE_TIME=00:30:00
STATUS(){ python3 -B $C8_PACKAGE/tools/production.py status "$@"; }
SUBMIT(){ $C8_PACKAGE/slurm/submit.sh "$@"; }
SQ(){ squeue -u <USER> -h -o '%i %j %T %P %M %l %R %E' | grep c8d2; }
sums(){ (cd "$1" && find groups -name merged.json -o -name graph_replicates.csv -o -name graph_tails.csv -o -name graph_costs.csv | sort | xargs sha256sum; ls C8_test_result*.json 2>/dev/null | xargs -r sha256sum); }
