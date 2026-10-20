#!/usr/bin/env bash
# Build and test the native workers (tools/submit.py build).
# - On the site's integration CPU it builds in place in $C8OPT_PACKAGE/bin (outside the delivery manifest); campaigns
#   pin that binary.
# - A test build on another CPU (submit.py build --any-cpu, C8OPT_ANY_CPU=1) builds only in its node-local copy: the
#   package's bin/ never holds a binary from a CPU the campaigns do not run on.
# Every test runs in a node-local copy of the package whose inputs/ and results/ are symlinks: the tests write
# verification/*.json, which must not change the delivered files.
# Evidence: $C8OPT_ROOT/evidence/build_<job id>/ (environment, describe, logs, summary.json). Exits 1 if any step
# failed; a setup failure stops the job before any test runs.
#SBATCH --job-name=c8opt-build
#SBATCH --output=c8opt-build-%j.out
set -uo pipefail
: "${C8OPT_ENV_SETUP:?Set C8OPT_ENV_SETUP to the site env file}"
unset C8OPT_ENV_COMPLETE
source "$C8OPT_ENV_SETUP" || { echo "c8opt: sourcing $C8OPT_ENV_SETUP failed" >&2; exit 65; }
: "${C8OPT_PACKAGE:?}" "${C8OPT_ROOT:?}"
source "$C8OPT_PACKAGE/slurm/site.sh"
c8opt_cpu_guard lenient
c8opt_scratch
c8opt_omp
c8opt_check_env build          # a failed module load or venv activation stops here (exit 65), before any build
EV="$C8OPT_ROOT/evidence/build_${SLURM_JOB_ID:-local}"
mkdir -p "$EV" || { echo "c8opt build: cannot create $EV" >&2; exit 1; }
N=${SLURM_CPUS_PER_TASK:-$(nproc)}
ANY=${C8OPT_ANY_CPU:-0}
STATUS=()
step() {   # step NAME CMD...: runs in the current directory, logs to $EV/NAME.log, records PASS/FAIL and seconds
  local name=$1; shift; local t0=$SECONDS rc=0
  "$@" > "$EV/$name.log" 2>&1 || rc=$?
  local dt=$((SECONDS - t0))
  if [[ $rc == 0 ]]; then STATUS+=("{\"step\":\"$name\",\"status\":\"PASS\",\"seconds\":$dt}"); echo "[$(date -u +%T)] $name PASS ($dt s)"
  else STATUS+=("{\"step\":\"$name\",\"status\":\"FAIL\",\"rc\":$rc,\"seconds\":$dt}"); echo "[$(date -u +%T)] $name FAIL rc=$rc ($dt s)"; tail -n 20 "$EV/$name.log"; fi
}
summary() {   # summary OK: writes summary.json
  printf '{"job":"%s","host":"%s","site":"%s","cpu":"%s","any_cpu":%s,"build_dir":"%s","steps":[%s],"ok":%s}\n' "${SLURM_JOB_ID:-}" \
    "$(hostname)" "$C8OPT_SITE" "$C8OPT_CPU_READ" "$([[ $ANY == 1 ]] && echo true || echo false)" "${BUILD_DIR:-}" \
    "$(IFS=,; echo "${STATUS[*]}")" "$1" > "$EV/summary.json"
}
fatal() { STATUS+=("{\"step\":\"setup\",\"status\":\"FAIL\",\"why\":\"$1\"}"); echo "c8opt build: $1" >&2; summary false; exit 1; }
{
  echo "job: ${SLURM_JOB_ID:-} on $(hostname) (${SLURM_JOB_PARTITION:-?}), $(date -u +%FT%TZ)"
  echo "site: $C8OPT_SITE; cpu: $C8OPT_CPU_READ (expected $C8OPT_CPU_EXPECT; C8OPT_ANY_CPU=$ANY)"
  echo "package: $C8OPT_PACKAGE; scratch: $C8OPT_SCRATCH; threads: $N"
  echo "cxx: $(${CXX:-g++} --version | head -1)"; echo "CPPFLAGS=${CPPFLAGS:-}"; echo "LDFLAGS=${LDFLAGS:-}"
  echo "python: $("$C8OPT_PYTHON" -c 'import sys,numpy,scipy,mpmath;print(sys.version.split()[0],"numpy",numpy.__version__,"scipy",scipy.__version__,"mpmath",mpmath.__version__)')"
  lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)' || true
} > "$EV/environment.txt"
cd "$C8OPT_PACKAGE" || fatal "cannot cd to $C8OPT_PACKAGE"
[[ "${C8OPT_VERIFY_DELIVERY:-1}" == 1 ]] && step delivery_verify "$C8OPT_PYTHON" -B tools/delivery.py verify --strict
W="$C8OPT_SCRATCH/pkg"
make_copy() {   # make_copy [--without-bin]: the node-local test copy, the large immutable data symlinked
  local ex=(--exclude=./inputs/free --exclude=./inputs/power --exclude=./results --exclude=./.git)
  [[ "${1:-}" == --without-bin ]] && ex+=(--exclude=./bin)
  mkdir -p "$W" || fatal "cannot create $W"
  ( tar "${ex[@]}" -cf - . | tar -xf - -C "$W" ) || fatal "copying the package to $W failed"
  ln -s "$C8OPT_PACKAGE/inputs/free" "$W/inputs/free" && ln -s "$C8OPT_PACKAGE/inputs/power" "$W/inputs/power" \
    && ln -s "$C8OPT_PACKAGE/results" "$W/results" || fatal "linking the data into $W failed"
  cd "$W" || fatal "cd $W failed"
  [[ "$(pwd -P)" != "$(cd "$C8OPT_PACKAGE" && pwd -P)" ]] || fatal "not in the test copy"
  STATUS+=('{"step":"test_copy","status":"PASS","seconds":0}')
}
build() {
  BUILD_DIR=$(pwd -P)
  step make_native make -j"$N" PYTHON="$C8OPT_PYTHON" gmp optimized baseline points reference bin/test_positive_quad
  [[ -f bin/c8d3_optimized ]] || fatal "bin/c8d3_optimized was not built in $BUILD_DIR"
  step describe bash -c 'bin/c8d3_optimized --describe | tee "'"$EV"'/describe_optimized.json" && bin/c8d3_gmp --describe > "'"$EV"'/describe_gmp.json"'
  sha256sum bin/* > "$EV/binaries.sha256" 2>/dev/null || true
  cp bin/*.buildinfo.json "$EV/" 2>/dev/null || true
}
if [[ "$ANY" == 1 ]]; then
  make_copy --without-bin; build               # a test build: the copy only
else
  build; make_copy                             # the integration CPU: in place, then test the built binaries in the copy
fi
step test_positive_quad bin/test_positive_quad
step test_native make PYTHON="$C8OPT_PYTHON" test-native
step test_points make PYTHON="$C8OPT_PYTHON" test-points
for t in test_optimization test_hpc_dispatch test_streaming_assembly test_rg test_campaign test_allocate test_cluster; do
  step "$t" "$C8OPT_PYTHON" -B "tests/$t.py"
done
cp -r "$W/verification" "$EV/verification_from_tests" 2>/dev/null || true
FAILED=0; for s in "${STATUS[@]}"; do [[ "$s" == *'"FAIL"'* ]] && FAILED=1; done
summary "$([[ $FAILED == 0 ]] && echo true || echo false)"
cat "$EV/summary.json"
exit $FAILED
