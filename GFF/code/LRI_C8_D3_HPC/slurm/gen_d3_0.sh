#!/bin/bash
# J-GEN-D3-0 (PLAN.md Stage 1a, Verification table; G1a = A-INV-1 and A-INV-2(a)). Expanse `shared`, one job:
#   1. make gen3 gen3-sanitize (bin/gen3/regenerate_rates with A.1's command, size_probe, the sanitizer build and the
#      coverage self-test build; a compiler warning fails the build);
#   2. gen3/run_d3.sh --pre-h1: gate 1(a) on C7(2)'s frozen d=2 payloads in $C8_STORE/c7d2_frozen (pinned file by file
#      by gen3/pins/c7d2_frozen_d2.sha256): all 3,512 C7(3) payloads reproduced byte for byte, determinism (N threads
#      and 1), idempotence, bodies equal to the d=2 inputs except the magic and the rate line, minimum rates;
#   3. gen3/test_gen3.py --sanitize: A-INV-1's targeted cases and the 2,000-mutant corpus under
#      bin/gen3/regenerate_rates_san, the unguarded-index self-test under bin/selftest/regenerate_rates_unguarded_san
#      (SIGABRT at the dist[masks[m]] site), A.1's build without warnings on this toolchain, and the gate tools on
#      their miniature fixtures (the injected failing gate in run_d3.sh among them).
#   4. gates_d3.py summary-gen-d3-0: jgen_d3_0.json, passed (= G1a) only when gate 1(a) is a full pass on Expanse
#      x86-64 (machine x86_64, this job's numeric SLURM_JOB_ID, C8_SITE=expanse from env.sh) and the sanitizer part
#      passed. Off Expanse every record says run_class "rehearsal" and a_inv_2a false; such a dry run exits 0 only with
#      C8_GEN3_REHEARSAL=1 (and its jgen_d3_0.json still says passed false).
# Scratch: C8_SCRATCH is computed here, inside the job ($SLURM_TMPDIR, else the site's node-local disk, slurm/site.sh), and
# TMPDIR=$C8_SCRATCH/tmp, so g++'s temporaries and test_gen3.py's working tree stay off /tmp (D.10).
# Evidence: $C8_ROOT/evidence/<sha12>/gen_d3_0/ (gate1a.json, rate_audit_pre_h1.json, test_gen3_sanitize.json,
# build records, jgen_d3_0.json). Resources and submission (login node, after
# `source ~/c8d3/env.sh` and with C8_PACKAGE=$C8_ROOT/pkg/<sha12>, a git archive export of the commit under test):
#   python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role gen_d3_0 --dir $C8_ROOT/evidence/<sha12>/gen_d3_0 -- \
#     -A yun124 -p shared --nodes=1 --ntasks=1 -c 32 --mem=60G -t 01:00:00 --no-requeue \
#     -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/gen_d3_0.sh
# No #SBATCH lines: the options above are the job's (slurm_submit.py names it and sets the comment, D.11).
set -eo pipefail
if [ -z "${C8_ENV_SETUP:-}" ] || [ ! -r "$C8_ENV_SETUP" ]; then
  echo "J-GEN-D3-0: C8_ENV_SETUP is not set or not readable (source ~/c8d3/env.sh before submitting)" >&2; exit 64
fi
source "$C8_ENV_SETUP"
set -u
: "${C8_PACKAGE:?C8_PACKAGE (the git archive export of the commit under test)}" "${C8_ROOT:?}" "${C8_STORE:?}"
: "${SLURM_JOB_ID:?J-GEN-D3-0 runs inside a Slurm job}"
source "$C8_PACKAGE/slurm/site.sh"; c8_set_scratch   # $SLURM_TMPDIR, else the site's node-local disk (slurm/site.sh)
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-32}" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
SHA12=$(basename "$C8_PACKAGE")
case "$SHA12" in *[!0-9a-f]*|'') echo "J-GEN-D3-0: C8_PACKAGE must be \$C8_ROOT/pkg/<sha12> (got $C8_PACKAGE)" >&2; exit 64 ;; esac
[ ${#SHA12} -eq 12 ] || { echo "J-GEN-D3-0: C8_PACKAGE must end in a 12-hex commit (got $SHA12)" >&2; exit 64; }
EV="$C8_ROOT/evidence/$SHA12/gen_d3_0"
mkdir -p "$EV" "$C8_SCRATCH"
export TMPDIR="$C8_SCRATCH/tmp"
mkdir -p "$TMPDIR"
cd "$C8_PACKAGE"
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }

stamp "J-GEN-D3-0 on $(hostname), job $SLURM_JOB_ID, package $SHA12, $OMP_NUM_THREADS threads, scratch $C8_SCRATCH"
{
  echo "host: $(hostname)"; echo "job: $SLURM_JOB_ID"; echo "package: $C8_PACKAGE"; echo "machine: $(uname -m)"
  echo "site: ${C8_SITE:-}"; echo "scratch: $C8_SCRATCH"; echo "tmpdir: $TMPDIR"
  lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node'
  echo "g++: $(g++ --version | head -n 1)"; echo "python: $(python3 --version 2>&1)"; echo "tar: $(tar --version | head -n 1)"
} > "$EV/environment.txt"
cat "$EV/environment.txt"

stamp "make gen3 gen3-sanitize"
make gen3 gen3-sanitize CXX=g++ 2>&1 | tee "$EV/make_gen3.log"
cp bin/gen3/regenerate_rates.build.txt bin/gen3/regenerate_rates_san.build.txt bin/gen3/size_probe.build.txt \
   bin/selftest/regenerate_rates_unguarded_san.build.txt "$EV/"
sha256sum bin/gen3/regenerate_rates bin/gen3/regenerate_rates_san bin/gen3/size_probe \
   bin/selftest/regenerate_rates_unguarded_san > "$EV/binaries.sha256"

stamp "gate 1(a): gen3/run_d3.sh --pre-h1"
bash gen3/run_d3.sh --pre-h1 --d2 "$C8_STORE/c7d2_frozen" --evidence "$EV" --work "$C8_SCRATCH/gen_d3_0" \
  --threads "$OMP_NUM_THREADS"

stamp "A-INV-1 under the sanitizers, and the gate tools on their fixtures: gen3/test_gen3.py --sanitize"
python3 -B gen3/test_gen3.py --sanitize --output "$EV/test_gen3_sanitize.json"

if [ "${C8_GEN3_REHEARSAL:-0}" = 1 ]; then
  python3 -B gen3/gates_d3.py summary-gen-d3-0 --evidence "$EV" --rehearsal
  stamp "J-GEN-D3-0 rehearsal finished (not G1a unless jgen_d3_0.json says passed): $EV"
else
  python3 -B gen3/gates_d3.py summary-gen-d3-0 --evidence "$EV"
  stamp "J-GEN-D3-0 PASSED: $EV"
fi
