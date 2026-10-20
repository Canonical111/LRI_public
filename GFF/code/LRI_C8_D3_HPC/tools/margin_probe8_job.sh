#!/bin/bash
# tools/margin_probe8_job.sh: the L8 margin re-derivation on one whole symmetry AMD node (tools/margin_probe8.py;
# RECON "Margin re-derivation" (a)-(d); user decision 2026-10-08). A raw job (docs/HPC.md "Margin re-derivation"),
# submitted from the login shell of a symmetry session (source ~/c8d3/env.sh; C8_PACKAGE = the export):
#
#   E=$C8_ROOT/evidence/<sha12 of the export>/margin
#   C8_MARGIN_EV=$E python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role margin --dir $E -- \
#       -p amdq --nodes=1 --ntasks=1 -c 64 --mem=240G -t 03:00:00 -o $C8_ROOT/logs/%x_%j.out \
#       $C8_PACKAGE/tools/margin_probe8_job.sh
#
# Variables (sbatch exports the submitting shell's environment):
#   C8_MARGIN_EV          required: the evidence directory, the raw job's --dir ($C8_ROOT/evidence/<sha12>/<name>)
#   C8_MARGIN_SELECTION   optional: a selection JSON (margin_probe8.py select). Default $C8_MARGIN_EV/selection.json,
#                         made in the job by `select` on the export's committed pilot report when it does not exist
#   C8_MARGIN_SELECT_ARGS optional: extra select options, e.g. "--class-reps 1" (only when the job makes the selection)
#   C8_MARGIN_ARGS        optional: extra probe options, e.g. "--max-flags 80000 --max-chains 40000"
# Steps: slurm/common.sh (the CPU pin: exit 68 off EPYC 7543; the node-local scratch C8_SCRATCH, where the members
# are extracted; one BLAS thread per process); the inputs: the export's own when its L8 packs are linked (a J-BLD-built
# export), else a work copy $C8_ROOT/work/margin_<job id>/inputs (hard links of the export's inputs, the store's L8
# packs linked in by prepare_inputs.py link-l8; removed at the end); select (unless the selection exists); probe over
# all allocated CPUs with --skip-existing (a resubmission into the same evidence directory continues where a timed-out
# job stopped: finished graphs are kept, never recomputed or overwritten); report (MARGIN_REPORT_<job id>.md and
# margin_report_<job id>.json); SHA256SUMS of the evidence directory. Exit status: the probe's or report's on failure.
set -eo pipefail
: "${C8_PACKAGE:?Set C8_PACKAGE to the export (slurm_submit.py raw runs from it)}"
: "${C8_MARGIN_EV:?Set C8_MARGIN_EV to the evidence directory (the raw job --dir)}"
source "$C8_PACKAGE/slurm/common.sh"   # site, Python check, CPU pin (68), C8_SCRATCH, BLAS threads
cd "$C8_PACKAGE"
EV=$C8_MARGIN_EV
TAG=${SLURM_JOB_ID:-$$}
mkdir -p "$EV" "$EV/probe"
W=${SLURM_CPUS_PER_TASK:-$(nproc)}
{
  echo "job: ${SLURM_JOB_ID:-} on $(hostname) (${SLURM_JOB_PARTITION:-?}), $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "package: $C8_PACKAGE"
  echo "cpu_read: ${C8_CPU_READ:-?} (${C8_CPU_SOURCE:-?})"
  echo "workers: $W; scratch: ${C8_SCRATCH:-}"
  echo "python: $("$PY" -c 'import sys,numpy,mpmath;print(sys.version.split()[0],"numpy",numpy.__version__,"mpmath",mpmath.__version__)')"
  echo "gmpy2: $("$PY" -c 'import gmpy2;print(gmpy2.version())' 2>/dev/null || echo absent)"
  echo "selection: ${C8_MARGIN_SELECTION:-$EV/selection.json}; select args: ${C8_MARGIN_SELECT_ARGS:-}; probe args: ${C8_MARGIN_ARGS:-}"
} > "$EV/environment_$TAG.txt"
INP=${C8_INPUTS:-$C8_PACKAGE/inputs}
WORK=''
if [[ ! -e "$INP/packs/free_L8.pack" || ! -e "$INP/packs/power_L8.pack" ]]; then
  : "${C8_STORE:?the L8 packs are not linked into $INP and C8_STORE (the pack store) is unset}"
  WORK=$C8_ROOT/work/margin_$TAG
  mkdir -p "$WORK"
  trap 'rm -rf "$WORK"' EXIT
  cp -al "$INP" "$WORK/inputs" 2>/dev/null || { rm -rf "$WORK/inputs"; cp -a "$INP" "$WORK/inputs"; }
  rm -f "$WORK/inputs/packs/free_L8.pack" "$WORK/inputs/packs/power_L8.pack"
  "$PY" -B tools/prepare_inputs.py link-l8 --store "$C8_STORE" --inputs "$WORK/inputs" | tee "$EV/link_l8_$TAG.log"
  INP=$WORK/inputs
fi
echo "inputs: $INP" >> "$EV/environment_$TAG.txt"
SEL=${C8_MARGIN_SELECTION:-$EV/selection.json}
if [[ ! -e "$SEL" ]]; then
  # shellcheck disable=SC2086
  "$PY" -B tools/margin_probe8.py select --out "$SEL" --inputs "$INP" ${C8_MARGIN_SELECT_ARGS:-} 2>&1 | tee "$EV/select_$TAG.log"
fi
# shellcheck disable=SC2086
"$PY" -B tools/margin_probe8.py probe --selection "$SEL" --out "$EV/probe" --inputs "$INP" --workers "$W" --skip-existing \
  ${C8_MARGIN_ARGS:-} 2>&1 | tee "$EV/probe_$TAG.log"
"$PY" -B tools/margin_probe8.py report "$EV/probe" --out "$EV/MARGIN_REPORT_$TAG.md" --json "$EV/margin_report_$TAG.json"
( cd "$EV" && find . -type f ! -name 'SHA256SUMS*' -print0 | sort -z | xargs -0 sha256sum > "SHA256SUMS_$TAG" )
echo "margin: done; $EV/MARGIN_REPORT_$TAG.md"
