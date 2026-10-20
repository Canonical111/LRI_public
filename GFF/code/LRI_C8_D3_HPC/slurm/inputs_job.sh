#!/bin/bash
# J-IN-1 (PLAN.md Verification "Expanse"; Stage 2b, G2b): the Stage-2b inputs, in two jobs.
#   C8_JOB=in1build  on the code commit: make inputs (the Stage-2a state, expected unchanged); make inputs-l8 with the
#                    published d=3 payload and its pin (D3PIN = the A.5 gate record's; gen3/verify_d3.py --pin runs
#                    first; the L8 packs go to the content-addressed store $C8_STORE/packs/<sha256>.pack and are
#                    hard-linked into the work copy); make inputs-inspect over all 24,173 kernels (the Stage-3a
#                    inspector, then make inputs merges the fields); make inputs-mini; gen3/gates_d3.py gate6. The
#                    generated files are copied to $EV/generated/ for the generated-data commit (the L8 packs stay in
#                    the store: pinned in inputs/manifest.json, never in git).
#   C8_JOB=in1check  on the generated-data commit: make link-l8 (the store's L8 packs into the work copy); then, with
#                    the L8 packs present: tests/check_inputs.py (A-IN-1..5: the Stage-2b regeneration byte for byte,
#                    the manifest, gate 6, the L8 rows on the packs, inputs_mini, A-IN-4 with a one-byte change to
#                    packs/free_L8.pack through the gate and through `production.py plan`), tests/inspect_check.py
#                    (A-KER-5 on all 24,173 kernels; the worker part on >= 100 graphs, L8 included), tests/members_test.py,
#                    gen3/gates_d3.py gate6, make inputs and make inputs-mini (both must change nothing), gen3/test_gen3.py
#                    --only tools.
# Plan: shared -c 16 --mem=32G -t 01:00:00 (this workflow: up to -t 02:00:00 for in1build).
# Two-part in1build (for debug's 30-min limit): C8_PHASE=l8 (copy, builds, make inputs, make inputs-l8; the work copy
# is kept) then C8_PHASE=inspect with C8_WORK=<that work copy> (make inputs-inspect, make inputs-mini, gate6, verify,
# the generated files); the default C8_PHASE=all runs both in one job. Evidence: <job>_<phase> for a part.
# Two-part in1check (independent jobs, each with its own work copy): C8_PHASE=inputs (everything but inspect_check)
# and C8_PHASE=kernels (make link-l8, the builds, verify, tests/inspect_check.py).
# Inputs (exported by the submitting shell; the job checks them): C8_PACKAGE ($C8_ROOT/pkg/<sha12>, a git archive
# export), C8_JOB, and for in1build C8_D3_PAYLOAD (the published tree) and C8_D3_PIN (its MANIFEST_d3.json sha256);
# C8_GATE_RECORD (optional: a copy of the A.5 gate record; make inputs-l8 and check_inputs.py compare the pins with it).
# The work copy is on Lustre ($C8_ROOT/work/<job>_<id>; the store's packs are hard-linked into it, so it must share the
# store's filesystem); it is removed when every step passed. Evidence: $C8_ROOT/evidence/<sha12>/<job>/.
# Submission (login node, after `source ~/c8d3/env.sh`):
#   C8_JOB=in1build C8_PACKAGE=$C8_ROOT/pkg/<sha12> C8_D3_PAYLOAD=$C8_STORE/d3_payload/46341a3c0f11 C8_D3_PIN=<sha256> \
#   C8_GATE_RECORD=<copy> python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role in1build \
#     --dir $C8_ROOT/evidence/<sha12>/in1build -- -A yun124 -p shared --nodes=1 --ntasks=1 -c 16 --mem=32G \
#     -t 02:00:00 --no-requeue -o $C8_ROOT/logs/%x_%j.out $C8_PACKAGE/slurm/inputs_job.sh
set -eo pipefail
if [ -z "${C8_ENV_SETUP:-}" ] || [ ! -r "$C8_ENV_SETUP" ]; then
  echo "inputs_job: C8_ENV_SETUP is not set or not readable (source ~/c8d3/env.sh before submitting)" >&2; exit 64
fi
source "$C8_ENV_SETUP"
set -u
: "${C8_PACKAGE:?C8_PACKAGE (the git archive export of the commit under test)}" "${C8_ROOT:?}" "${C8_STORE:?}" "${C8_JOB:?C8_JOB=in1build|in1check}"
: "${SLURM_JOB_ID:?inputs_job runs inside a Slurm job}"
case "$C8_JOB" in in1build|in1check) ;; *) echo "inputs_job: C8_JOB must be in1build or in1check" >&2; exit 64 ;; esac
if [ "$C8_JOB" = in1build ]; then
  [ -d "${C8_D3_PAYLOAD:-}" ] && [ ${#C8_D3_PIN} -eq 64 ] || { echo "inputs_job: in1build needs C8_D3_PAYLOAD (a payload tree) and C8_D3_PIN (its 64-hex pin)" >&2; exit 64; }
fi
GATE=()
if [ -n "${C8_GATE_RECORD:-}" ]; then
  [ -f "$C8_GATE_RECORD" ] || { echo "inputs_job: C8_GATE_RECORD=$C8_GATE_RECORD is not a file" >&2; exit 64; }
  GATE=(GATE_RECORD="$C8_GATE_RECORD")
fi
PHASE="${C8_PHASE:-all}"
case "$C8_JOB:$PHASE" in in1build:all|in1build:l8|in1build:inspect|in1check:all|in1check:inputs|in1check:kernels) ;; *) echo "inputs_job: C8_PHASE=$PHASE is not a phase of $C8_JOB" >&2; exit 64 ;; esac
SHA12=$(basename "$C8_PACKAGE")
case "$SHA12" in *[!0-9a-f]*|'') echo "inputs_job: C8_PACKAGE must be \$C8_ROOT/pkg/<sha12> (got $C8_PACKAGE)" >&2; exit 64 ;; esac
[ ${#SHA12} -eq 12 ] || { echo "inputs_job: C8_PACKAGE must end in a 12-hex commit (got $SHA12)" >&2; exit 64; }
source "$C8_PACKAGE/slurm/site.sh"; c8_set_scratch   # $SLURM_TMPDIR, else the site's node-local disk (slurm/site.sh)
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}" PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
EV="$C8_ROOT/evidence/$SHA12/$C8_JOB"; [ "$PHASE" = all ] || EV="${EV}_$PHASE"
W="$C8_ROOT/work/${C8_JOB}_$SLURM_JOB_ID"
if [ "$PHASE" = inspect ]; then
  W="${C8_WORK:?C8_PHASE=inspect needs C8_WORK, the work copy of the l8 part}"
  case "$W" in "$C8_ROOT"/work/in1build_*) ;; *) echo "inputs_job: C8_WORK=$W is not an in1build work copy" >&2; exit 64 ;; esac
  [ -f "$W/inputs/packs/free_L8.pack" ] || { echo "inputs_job: $W has no L8 packs (run the l8 part first)" >&2; exit 64; }
fi
case "$W" in /expanse/lustre/scratch/zzheng8/temp_project/c8d2*|*/LRI_C8_shared/inventory*) echo "inputs_job: $W is under C62d's tree" >&2; exit 64 ;; esac
mkdir -p "$EV" "$C8_SCRATCH"
export TMPDIR="$C8_SCRATCH/tmp"
mkdir -p "$TMPDIR"
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }
STATUS=()
step() {   # step NAME CMD...: runs CMD in the work copy, logs to $EV/NAME.log, records PASS/FAIL and the seconds
  local name=$1; shift; local t0=$(date +%s) rc=0
  stamp "$name: $*"
  ( cd "$W" && "$@" ) > "$EV/$name.log" 2>&1 || rc=$?
  local dt=$(( $(date +%s) - t0 ))
  if [ $rc -eq 0 ]; then STATUS+=("{\"step\":\"$name\",\"status\":\"PASS\",\"seconds\":$dt}"); stamp "$name PASS ($dt s)";
  else STATUS+=("{\"step\":\"$name\",\"status\":\"FAIL\",\"rc\":$rc,\"seconds\":$dt}"); stamp "$name FAIL rc=$rc ($dt s)"; tail -n 25 "$EV/$name.log"; fi
}
stamp "inputs_job $C8_JOB on $(hostname), job $SLURM_JOB_ID, package $SHA12, $OMP_NUM_THREADS threads, work $W"
{
  echo "host: $(hostname)"; echo "job: $SLURM_JOB_ID"; echo "package: $C8_PACKAGE"; echo "machine: $(uname -m)"
  echo "site: ${C8_SITE:-}"; echo "work: $W"; echo "scratch: $C8_SCRATCH"; echo "threads: $OMP_NUM_THREADS"
  echo "d3_payload: ${C8_D3_PAYLOAD:-}"; echo "d3_pin: ${C8_D3_PIN:-}"; echo "gate_record: ${C8_GATE_RECORD:-}"
  lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node'
  echo "g++: $(g++ --version | head -n 1)"; echo "python: $(python3 --version 2>&1)"
  lfs quota -u "$USER" /expanse/lustre/scratch 2>/dev/null | tail -n 1 || true
} > "$EV/environment.txt"
cat "$EV/environment.txt"
if [ "$PHASE" != inspect ]; then
  mkdir -p "$(dirname "$W")"
  [ ! -e "$W" ] || { echo "inputs_job: $W exists" >&2; exit 64; }
  stamp "copying the export to $W"
  cp -a "$C8_PACKAGE/." "$W/"
fi
MK="make -j $OMP_NUM_THREADS CXX=g++ PYTHON=python3"
case "$C8_JOB" in
in1build)
  if [ "$PHASE" != inspect ]; then
  step make_native $MK bin/c8d3_inspect bin/gen3/size_probe
  step inputs_2a make inputs PYTHON=python3
  step inputs_l8 make inputs-l8 PYTHON=python3 D3PAYLOAD="$C8_D3_PAYLOAD" D3PIN="$C8_D3_PIN" STORE="$C8_STORE" \
       ${GATE[@]+"${GATE[@]}"} VERIFY_OUTPUT="$EV/verify_d3.json" L8_RECORD="$EV/inputs_l8.json"
  fi
  if [ "$PHASE" = l8 ]; then
    ( cd "$W" && ls -li inputs/packs/ && ls -li "$C8_STORE/packs/" ) > "$EV/packs_listing.txt" 2>&1 || true
  else
  step inputs_inspect make inputs-inspect PYTHON=python3
  step inputs_mini make inputs-mini PYTHON=python3
  step gate6 python3 -B gen3/gates_d3.py gate6 --evidence "$EV"
  step verify python3 -B tools/prepare_inputs.py verify
  mkdir -p "$EV/generated/inputs/packs" "$EV/generated/inspect" "$EV/generated/tests/fixtures"
  ( cd "$W" && cp -a inputs/inventory.json inputs/manifest.json inputs/selection.json inputs/h1 inputs/d3 "$EV/generated/inputs/" \
      && cp -a inputs/packs/free_L7.pack inputs/packs/power_L7.pack "$EV/generated/inputs/packs/" \
      && cp -a inspect/inspect.json "$EV/generated/inspect/" && cp -a tests/fixtures/inputs_mini "$EV/generated/tests/fixtures/" ) \
    || STATUS+=("{\"step\":\"copy_generated\",\"status\":\"FAIL\"}")
  ( cd "$W" && sha256sum inputs/packs/*.pack inputs/*.json inputs/h1/* inputs/d3/* inspect/inspect.json tests/fixtures/inputs_mini/*.json tests/fixtures/inputs_mini/packs/* ) > "$EV/generated.sha256" || true
  ( cd "$W" && ls -li inputs/packs/ && ls -li "$C8_STORE/packs/" ) > "$EV/packs_listing.txt" 2>&1 || true
  fi
  ;;
in1check)
  step link_l8 make link-l8 PYTHON=python3 STORE="$C8_STORE"
  step make_native $MK bin/c8d3_gmp bin/c8d3_inspect bin/gen3/size_probe test-builds
  ( cd "$W" && ls -li inputs/packs/ && ls -li "$C8_STORE/packs/" ) > "$EV/packs_listing.txt" 2>&1 || true
  step verify python3 -B tools/prepare_inputs.py verify
  if [ "$PHASE" != kernels ]; then
  step check_inputs env ${C8_GATE_RECORD:+C8_GATE_RECORD="$C8_GATE_RECORD"} python3 -B tests/check_inputs.py --output "$EV/check_inputs.json"
  fi
  if [ "$PHASE" != inputs ]; then
  step inspect_check python3 -B tests/inspect_check.py --output "$EV/inspect_check.json"
  fi
  if [ "$PHASE" != kernels ]; then
  step members_test python3 -B tests/members_test.py
  step gate6 python3 -B gen3/gates_d3.py gate6 --evidence "$EV"
  step inputs_unchanged bash -c 'make inputs PYTHON=python3 2> "$0" && grep -q "changed: none" "$0"' "$EV/inputs_unchanged.stderr"
  step mini_unchanged bash -c 'python3 -B tools/prepare_inputs.py mini > "$0" && python3 -c "import json,sys;sys.exit(0 if json.load(open(sys.argv[1]))[\"changed\"]==[] else 1)" "$0"' "$EV/mini_unchanged.json"
  step gen3_tools python3 -B gen3/test_gen3.py --only tools --output "$EV/test_gen3_tools.json"
  fi
  ;;
esac
{ printf '{"job":"%s","slurm_job":"%s","host":"%s","package":"%s","steps":[' "$C8_JOB" "$SLURM_JOB_ID" "$(hostname)" "$SHA12"
  (IFS=,; printf '%s' "${STATUS[*]}"); printf ']}\n'; } > "$EV/summary.json"
cat "$EV/summary.json"
if printf '%s\n' "${STATUS[@]}" | grep -q '"FAIL"'; then stamp "inputs_job $C8_JOB: FAILED steps (see $EV; work copy kept: $W)"; exit 1; fi
if [ "$PHASE" = l8 ]; then stamp "inputs_job $C8_JOB (l8 part): passed; work copy kept for the inspect part: C8_WORK=$W"; exit 0; fi
rm -rf "$W"
stamp "inputs_job $C8_JOB: all steps passed ($EV)"
