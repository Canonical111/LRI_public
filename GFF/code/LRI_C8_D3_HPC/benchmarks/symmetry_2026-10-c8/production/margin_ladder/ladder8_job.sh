#!/bin/bash
# Fine depth ladder for the deficit levels of margin probe 571479 (ladder8.py), on one amdq node share.
set -eo pipefail
: "${C8_PACKAGE:?}"; : "${C8_LADDER_EV:?}"; : "${C8_LADDER_PROBE:?}"
source "$C8_PACKAGE/slurm/common.sh"
cd "$C8_PACKAGE"
TAG=${SLURM_JOB_ID:-$$}
echo "job ${SLURM_JOB_ID:-} on $(hostname) $(date -u +%FT%TZ); cpu ${C8_CPU_READ:-?}; package $C8_PACKAGE; probe $C8_LADDER_PROBE" > "$C8_LADDER_EV/environment_$TAG.txt"
"$PY" -B "$C8_LADDER_EV/ladder8.py" "$C8_LADDER_PROBE" "$C8_LADDER_EV/ladder_$TAG.json" "${SLURM_CPUS_PER_TASK:-16}" 2>&1 | tee "$C8_LADDER_EV/ladder_$TAG.log"
( cd "$C8_LADDER_EV" && find . -type f ! -name 'SHA256SUMS*' -print0 | sort -z | xargs -0 sha256sum > "SHA256SUMS_$TAG" )
