#!/bin/bash
# J-GEN-D3 (PLAN.md Stage 1b, A.2 steps 1-6; G1b = A-INV-2(b), A-INV-3, A-INV-4, A-INV-5's publication, A-INV-6 after).
# Expanse `shared`, one job:
#   1. make gen3 (bin/gen3/regenerate_rates with A.1's command, and size_probe; a compiler warning fails the build);
#   2. gen3/run_d3.sh --h1 on the verified H1 copy $C8_STORE/h1/<pin sha12> (made by J-H1-COPY, slurm/h1_copy.sh):
#      verify, extract, builders (the gate-5 side files from H1's pinned builders), probe, regen (N threads and N
#      single-thread shards), gates 1(b), 2, 3, 4, 5, 7, determinism, publish into $C8_STORE/d3_payload/<pin sha12>
#      (only after every gate exited 0), verify_d3 (prints the MANIFEST_d3 sha256, the external pin of A.5) and source
#      (the HANDOFF's tree unchanged since the intake).
# Inputs, exported on the login node before the submit line (sbatch's default --export=ALL carries them into the job;
# nothing is passed as a script argument, which slurm_submit.py raw refuses):
#   C8_PACKAGE    $C8_ROOT/pkg/<sha12>, a git archive export of a commit after G2a: gate 7 reads inputs/two_loop.json,
#                 inputs/order7/two_loop.json and inputs/gamma_d3_8.txt, which Stage 2a writes (checked at start)
#   C8_H1_PIN     H1's MANIFEST sha256 (the HANDOFF's pin, 64 hex)
#   C8_H1_SOURCE  the HANDOFF's Expanse tree (only read: its listing must still equal the intake's)
#   C8_H1_BEFORE  J-H1-COPY's h1_source_listing_before.json
# Derived inside the job, never on the login node: C8_SCRATCH ($SLURM_TMPDIR, else the site's node-local disk, slurm/site.sh;
# env.sh leaves it unset), TMPDIR=$C8_SCRATCH/tmp, the work directory $C8_SCRATCH/gen_d3, the evidence directory
# $C8_ROOT/evidence/<sha12>/gen_d3, the H1 copy, the target, the threads ($SLURM_CPUS_PER_TASK) and the commit.
# Submission (login node, after `source ~/c8d3/env.sh`; docs/HPC.md "Stage 1b"):
#   export C8_PACKAGE=$C8_ROOT/pkg/<sha12> C8_H1_PIN=<H1 MANIFEST sha256> C8_H1_SOURCE=<the HANDOFF's tree> \
#     C8_H1_BEFORE=<J-H1-COPY evidence>/h1_source_listing_before.json
#   python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role gen_d3 --dir $C8_ROOT/evidence/<sha12>/gen_d3 -- \
#     -A yun124 -p shared --nodes=1 --ntasks=1 -c 64 --mem=120G -t 02:00:00 --no-requeue \
#     -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/gen_d3.sh
# No #SBATCH lines: the options above are the job's (slurm_submit.py names it and sets the comment, D.11).
set -eo pipefail
if [ -z "${C8_ENV_SETUP:-}" ] || [ ! -r "$C8_ENV_SETUP" ]; then
  echo "J-GEN-D3: C8_ENV_SETUP is not set or not readable (source ~/c8d3/env.sh before submitting)" >&2; exit 64
fi
source "$C8_ENV_SETUP"
set -u
fail() { echo "J-GEN-D3: $*" >&2; exit 64; }
: "${C8_PACKAGE:?C8_PACKAGE (the git archive export of the commit under test)}" "${C8_ROOT:?}" "${C8_STORE:?}"
: "${SLURM_JOB_ID:?J-GEN-D3 runs inside a Slurm job}"
: "${C8_H1_PIN:?C8_H1_PIN (H1 MANIFEST sha256)}" "${C8_H1_SOURCE:?C8_H1_SOURCE (the HANDOFF tree)}"
: "${C8_H1_BEFORE:?C8_H1_BEFORE (J-H1-COPY h1_source_listing_before.json)}"
source "$C8_PACKAGE/slurm/site.sh"; c8_set_scratch   # $SLURM_TMPDIR, else the site's node-local disk (slurm/site.sh)
THREADS="${SLURM_CPUS_PER_TASK:-64}"
export OMP_NUM_THREADS="$THREADS" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
SHA12=$(basename "$C8_PACKAGE")
case "$SHA12" in *[!0-9a-f]*|'') fail "C8_PACKAGE must be \$C8_ROOT/pkg/<sha12> (got $C8_PACKAGE)" ;; esac
[ ${#SHA12} -eq 12 ] || fail "C8_PACKAGE must end in a 12-hex commit (got $SHA12)"
case "$C8_H1_PIN" in *[!0-9a-f]*|'') fail "C8_H1_PIN is not a sha256 (got $C8_H1_PIN)" ;; esac
[ ${#C8_H1_PIN} -eq 64 ] || fail "C8_H1_PIN is not a sha256 (got $C8_H1_PIN)"
PIN12=${C8_H1_PIN:0:12}
H1="$C8_STORE/h1/$PIN12"
TARGET="$C8_STORE/d3_payload/$PIN12"
[ -d "$H1" ] || fail "$H1: no verified H1 copy (run J-H1-COPY, slurm/h1_copy.sh, first)"
[ -d "$C8_H1_SOURCE" ] || fail "C8_H1_SOURCE $C8_H1_SOURCE is not a directory"
[ -f "$C8_H1_BEFORE" ] && [ -r "$C8_H1_BEFORE" ] || fail "C8_H1_BEFORE $C8_H1_BEFORE is not a readable file"
[ ! -e "$TARGET" ] || fail "$TARGET exists (a published tree is frozen)"
for f in inputs/two_loop.json inputs/order7/two_loop.json inputs/gamma_d3_8.txt reference/reference/d3_C6_two_loop.json; do
  [ -f "$C8_PACKAGE/$f" ] || fail "$C8_PACKAGE/$f is missing: gate 7 reads it, so J-GEN-D3 runs on a commit after G2a"
done
EV="$C8_ROOT/evidence/$SHA12/gen_d3"
mkdir -p "$EV" "$C8_SCRATCH"
export TMPDIR="$C8_SCRATCH/tmp"
mkdir -p "$TMPDIR"
cd "$C8_PACKAGE"
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }

stamp "J-GEN-D3 on $(hostname), job $SLURM_JOB_ID, package $SHA12, $THREADS threads, H1 $PIN12, scratch $C8_SCRATCH"
{
  echo "host: $(hostname)"; echo "job: $SLURM_JOB_ID"; echo "package: $C8_PACKAGE"; echo "machine: $(uname -m)"
  echo "site: ${C8_SITE:-}"; echo "scratch: $C8_SCRATCH"; echo "tmpdir: $TMPDIR"
  echo "h1_pin: $C8_H1_PIN"; echo "h1_copy: $H1"; echo "h1_source: $C8_H1_SOURCE"; echo "h1_before: $C8_H1_BEFORE"
  echo "target: $TARGET"
  lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node'
  echo "g++: $(g++ --version | head -n 1)"; echo "python: $(python3 --version 2>&1)"; echo "tar: $(tar --version | head -n 1)"
} > "$EV/environment.txt"
cat "$EV/environment.txt"

stamp "make gen3"
make gen3 CXX=g++ 2>&1 | tee "$EV/make_gen3.log"
cp bin/gen3/regenerate_rates.build.txt bin/gen3/size_probe.build.txt "$EV/"
sha256sum bin/gen3/regenerate_rates bin/gen3/size_probe > "$EV/binaries.sha256"

stamp "gen3/run_d3.sh --h1 $H1"
bash gen3/run_d3.sh --h1 "$H1" --pin "$C8_H1_PIN" --d2 "$C8_STORE/c7d2_frozen" --evidence "$EV" \
  --work "$C8_SCRATCH/gen_d3" --target "$TARGET" --source "$C8_H1_SOURCE" --source-before "$C8_H1_BEFORE" \
  --threads "$THREADS" --commit "$SHA12"
stamp "J-GEN-D3 PASSED: $TARGET; MANIFEST_d3.json sha256 (the A.5 external pin): $(cat "$EV/MANIFEST_d3.sha256")"
