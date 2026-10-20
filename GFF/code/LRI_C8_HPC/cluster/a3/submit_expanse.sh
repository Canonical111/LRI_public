#!/bin/bash
# Amendment A3 (docs/EXTENSION_A3.md), Expanse login node: environment (env.sh of b1-b4), then a3_expanse.py
# (run | resubmit LABEL I... | merge LABEL | status | stopped-record); see that script for the checks.
set -eo pipefail
E=/expanse/lustre/scratch/zzheng8/temp_project/c8_hpc
source $E/env.sh >/dev/null 2>&1
exec "$C8_PYTHON" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/a3_expanse.py" "$@"
