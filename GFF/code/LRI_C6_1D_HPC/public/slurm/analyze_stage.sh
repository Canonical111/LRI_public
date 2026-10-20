#!/bin/bash
#SBATCH -J c6ana -N 1 -n 1 -c 2 --mem=8G -t 01:00:00
# analyze_stage.sh: final-mode analysis at N* = $N (PLAN.md Sec 4.5 and 8; inspection finding REV-005).
# Resource accounting (c6_resources), assembly, rounding, the pre-registered estimate and the stopping decision
# $C6_HOME/decisions/decision_N$N.json, which production.sh N=<N+2> requires. The original campaign ran the same four
# steps through an operator script on symmetry (ops/analyze_job.sh, MODE=final), which is not part of the package.
# Written by public/slurm/adapt.py into the site copy as cluster/analyze_stage.sh. Submit after a stage completed:
#   sbatch -p <SHARED_PARTITION> -o $C6_HOME/logs/%x_%j.out --export=ALL,C6_CODE=$C6_HOME/code/current,N=16 \
#          $C6_HOME/code/current/cluster/analyze_stage.sh
set -euo pipefail
source "${C6_CODE:?}/cluster/env.sh"
: "${N:?set N, the highest completed L6 degree}"
A=$C6_HOME/analysis; mkdir -p "$A" "$C6_HOME/decisions"
c6_resources "$N" > "$A/resources_N$N.json"
python "$C6_CODE/tools/assemble.py" "$C6_LEVELS" "$C6_DATA/weights_manifest.json" "$A/assembled_N$N.json" > "$A/assemble_N$N.log"
python "$C6_CODE/tools/rounding.py" "$C6_LEVELS" "$C6_DATA/weights_manifest.json" "$A/rounding_N$N.json" > "$A/rounding_N$N.log"
python "$C6_CODE/tools/analyze.py" "$A/assembled_N$N.json" "$A/rounding_N$N.json" "$A/C6_N$N.json" \
       --resources "$A/resources_N$N.json" --decision-dir "$C6_HOME/decisions" | tee "$A/analyze_N$N.log"
python - "$C6_HOME/decisions/decision_N$N.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"decision at N*={d['N_star']}: {d['decision']} {d['reasons']} next={d['next_degree']}")
PY
