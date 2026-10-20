#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=16G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-g2b-check
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# The Stage-2b assembly checks on a cluster export (site deviation U1): tests/check_vendored.py (A-ASM-1(a)+(b)),
# tests/vendored_isolated.py --in-place (the cluster part of A-ASM-1, a G3/G5 J-VAL-1 item, run early), tests/
# assembly_checks.py --exact (A-ASM-2/4/5; the cluster part of A-ASM-4, a G3/G5 J-VAL-3 item, run early),
# tests/compat_2026.py (A-ASM-3), tests/verify_result_tamper.py (A-ASM-7) and tests/combine_core.py.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL expanse_g2b.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=g2b.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN
mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
python3 -c 'import sys,numpy,sympy,mpmath,pytest; print("python", sys.version.split()[0], "numpy", numpy.__version__, "sympy", sympy.__version__, "mpmath", mpmath.__version__, "pytest", pytest.__version__)'
cd "$C8_PACKAGE"
status=0
run() { local name=$1; shift; echo "== $name"; "$@" || { echo "== $name: FAILED"; status=1; }; }
run check_vendored python3 -B tests/check_vendored.py --no-review-record --output "$E/check_vendored.json"
run vendored_isolated python3 -B tests/vendored_isolated.py --in-place --output "$E/vendored_isolated_in_place.json"
run assembly_checks python3 -B tests/assembly_checks.py --exact --output "$E/assembly_checks_exact.json" --provenance "$E/exact_check_provenance.json"
run compat_2026 python3 -B tests/compat_2026.py --output "$E/compat_2026.json"
run verify_result_tamper python3 -B tests/verify_result_tamper.py --output "$E/verify_result_tamper.json"
run combine_core python3 -B tests/combine_core.py --output "$E/combine_core.json"
echo "finished $(date -Is), status $status"
exit $status
