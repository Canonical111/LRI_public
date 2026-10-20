#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 04:00:00 --no-requeue
#SBATCH -J c8d2-ckfix-val1
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-VAL-1 on Expanse for the checkpoint-review fixes (site deviation U1), in the export of the commit under test: the
# commands of `make test` one by one, each to the end with its own record and exit code (so one run reports every
# failure): make all gmp (the prerequisites: the input verification, binaries current), tests/validate.py (the replay
# subset, the native refusals, and the inspector part: CK-K03's private temporary directory and T-04's traced execution
# order at L7 and L8), the `make test-python` list (unit_orchestration with the A-ORC-13 claim on the real bin/c8d2_gmp
# and the Linux fingerprint path and the R18 bootstrap regeneration in a copy of this export; test_pipeline, ast_scan,
# gen/test_regress, merge_scale --rows 20000, check_vendored --no-review-record, vendored_isolated --in-place, the
# delivery-verifier test, check_inputs), the real-worker workflow.py and staging.py, then verify_result_tamper and
# combine_core (O10). Mirrors stage3b/scripts/expanse_s3b_val1.slurm. Temporary package copies and campaigns live on
# the node-local NVMe (the first run, job 54641703, on Lustre took 78 min for unit_orchestration alone).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=ckval1.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"; R=$E/records; mkdir "$R"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
unset C8_SEEDS C8_SITE C8_INPUTS
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal bin/c8d2_gmp | tee "$E/binaries.sha256"
status=0
run() {
  local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -2 "$E/$name.log" | cut -c1-300
  if [ $c -ne 0 ]; then status=1; grep -E '^FAIL|Error|Traceback' "$E/$name.log" | head -20 | cut -c1-300; fi
}
run make_prerequisites make all gmp
run validate python3 -B tests/validate.py --output "$R/validate.json"
run unit_orchestration python3 -B tests/unit_orchestration.py --output "$R/unit_orchestration.json"
run test_pipeline python3 -B tests/test_pipeline.py --output "$R/test_pipeline.json"
run ast_scan python3 -B tests/ast_scan.py --output "$R/ast_scan.json"
run test_regress python3 -B gen/test_regress.py --output "$R/test_regress.json"
run merge_scale python3 -B tests/merge_scale.py --rows 20000 --output "$R/merge_scale.json"
run check_vendored python3 -B tests/check_vendored.py --no-review-record --output "$R/check_vendored.json"
run vendored_isolated python3 -B tests/vendored_isolated.py --in-place --output "$R/vendored_isolated.json"
run delivery_verifier python3 -B tests/test_delivery_verifier.py
run check_inputs python3 -B tests/check_inputs.py --output "$R/check_inputs.json"
run workflow python3 -B tests/workflow.py --output "$R/workflow.json"
run staging python3 -B tests/staging.py --output "$R/staging.json"
run verify_result_tamper python3 -B tests/verify_result_tamper.py --output "$R/verify_result_tamper.json"
run combine_core python3 -B tests/combine_core.py --output "$R/combine_core.json"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
