#!/bin/bash
# J-H1-COPY (PLAN.md A.2 step 0, A-INV-6): gen3/gates_d3.py h1-copy. The HANDOFF's Expanse tree is copied into
# $C8_STORE/h1/<pin sha12>/ through a staging directory and one rename, H1's own verify_inventory.py --pin runs on the
# copy, and the source's listing (files, sizes, mtimes, MANIFEST sha256) is recorded before and after, which must be
# equal. The source is only read; every write path is refused under C62d's trees.
# Inputs, exported on the login node before the submit line (sbatch's default --export=ALL carries them into the job;
# nothing is passed as a script argument, which slurm_submit.py raw refuses):
#   C8_PACKAGE    $C8_ROOT/pkg/<sha12>, a git archive export of the commit under test
#   C8_H1_PIN     H1's MANIFEST sha256 (the HANDOFF's pin, 64 hex)
#   C8_H1_SOURCE  the HANDOFF's Expanse tree
# Evidence: $C8_ROOT/evidence/<sha12>/h1_copy/ (h1_copy.json, verify_inventory_copy.json,
# h1_source_listing_before.json, which J-GEN-D3 takes as C8_H1_BEFORE, and h1_source_listing_after.json).
# C8_SCRATCH and TMPDIR=$C8_SCRATCH/tmp are computed inside the job (D.10), never on the login node.
# Submission (login node, after `source ~/c8d3/env.sh`; docs/HPC.md "Stage 1b"):
#   export C8_PACKAGE=$C8_ROOT/pkg/<sha12> C8_H1_PIN=<H1 MANIFEST sha256> C8_H1_SOURCE=<the HANDOFF's tree>
#   python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role h1_copy --dir $C8_ROOT/evidence/<sha12>/h1_copy -- \
#     -A yun124 -p shared --nodes=1 --ntasks=1 -c 4 --mem=8G -t 01:00:00 --no-requeue \
#     -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/h1_copy.sh
# No #SBATCH lines: the options above are the job's (slurm_submit.py names it and sets the comment, D.11).
set -eo pipefail
if [ -z "${C8_ENV_SETUP:-}" ] || [ ! -r "$C8_ENV_SETUP" ]; then
  echo "J-H1-COPY: C8_ENV_SETUP is not set or not readable (source ~/c8d3/env.sh before submitting)" >&2; exit 64
fi
source "$C8_ENV_SETUP"
set -u
fail() { echo "J-H1-COPY: $*" >&2; exit 64; }
: "${C8_PACKAGE:?C8_PACKAGE (the git archive export of the commit under test)}" "${C8_ROOT:?}" "${C8_STORE:?}"
: "${SLURM_JOB_ID:?J-H1-COPY runs inside a Slurm job}"
: "${C8_H1_PIN:?C8_H1_PIN (H1 MANIFEST sha256)}" "${C8_H1_SOURCE:?C8_H1_SOURCE (the HANDOFF tree)}"
source "$C8_PACKAGE/slurm/site.sh"; c8_set_scratch   # $SLURM_TMPDIR, else the site's node-local disk (slurm/site.sh)
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
SHA12=$(basename "$C8_PACKAGE")
case "$SHA12" in *[!0-9a-f]*|'') fail "C8_PACKAGE must be \$C8_ROOT/pkg/<sha12> (got $C8_PACKAGE)" ;; esac
[ ${#SHA12} -eq 12 ] || fail "C8_PACKAGE must end in a 12-hex commit (got $SHA12)"
case "$C8_H1_PIN" in *[!0-9a-f]*|'') fail "C8_H1_PIN is not a sha256 (got $C8_H1_PIN)" ;; esac
[ ${#C8_H1_PIN} -eq 64 ] || fail "C8_H1_PIN is not a sha256 (got $C8_H1_PIN)"
[ -d "$C8_H1_SOURCE" ] || fail "C8_H1_SOURCE $C8_H1_SOURCE is not a directory"
EV="$C8_ROOT/evidence/$SHA12/h1_copy"
mkdir -p "$EV" "$C8_SCRATCH"
export TMPDIR="$C8_SCRATCH/tmp"
mkdir -p "$TMPDIR"
cd "$C8_PACKAGE"
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }

stamp "J-H1-COPY on $(hostname), job $SLURM_JOB_ID, package $SHA12, source $C8_H1_SOURCE, store $C8_STORE/h1"
{
  echo "host: $(hostname)"; echo "job: $SLURM_JOB_ID"; echo "package: $C8_PACKAGE"; echo "machine: $(uname -m)"
  echo "site: ${C8_SITE:-}"; echo "h1_pin: $C8_H1_PIN"; echo "h1_source: $C8_H1_SOURCE"; echo "store: $C8_STORE/h1"
  echo "python: $(python3 --version 2>&1)"
} > "$EV/environment.txt"
python3 -B gen3/gates_d3.py h1-copy --source "$C8_H1_SOURCE" --store "$C8_STORE/h1" --pin "$C8_H1_PIN" --evidence "$EV"
stamp "J-H1-COPY PASSED: $C8_STORE/h1/${C8_H1_PIN:0:12}; C8_H1_BEFORE=$EV/h1_source_listing_before.json"
