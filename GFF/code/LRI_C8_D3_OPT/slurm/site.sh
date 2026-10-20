# slurm/site.sh: site rules for the job scripts (run_hpc.sh, build.sh, plan.sh, assemble.sh, run_array.sh). Sourced
# after the env file ($C8OPT_ENV_SETUP, from slurm/sites/<site>/env.sh.example). It defines functions only.
#
#   c8opt_site        checks C8OPT_SITE (symmetry or expanse; anything else exits 64) and sets C8OPT_CPU_EXPECT:
#                     symmetry 'AMD EPYC 7543 32-Core Processor' (amdq; cn112 is an Intel node and is excluded at
#                     submission), Expanse 'AMD EPYC 7742 64-Core Processor'.
#   c8opt_cpu_guard   [strict|lenient] compares this node's first /proc/cpuinfo 'model name' (spaces collapsed) with
#                     C8OPT_CPU_EXPECT. On a mismatch it exits 68 with one line naming the host and both models. It
#                     is lenient (a WARNING only) when called 'lenient' and C8OPT_ANY_CPU=1: build and test jobs may
#                     run elsewhere, integration lanes never. A campaign's binary is pinned by hash in its plan; one
#                     CPU model per campaign keeps every checkpoint from one arithmetic environment.
#   c8opt_scratch     exports C8OPT_SCRATCH, the job's node-local directory, and TMPDIR below it: $SLURM_TMPDIR when
#                     set, else symmetry /local1/$USER/job_$SLURM_JOB_ID, Expanse /scratch/$USER/job_$SLURM_JOB_ID
#                     (node-local NVMe). Never the shared filesystem (staging would lose its point) and never /tmp.
#                     Exits 74 when it cannot create it.
#   c8opt_omp         OpenMP placement for the native worker: one thread per core, close binding, no dynamic teams.
#   c8opt_check_env   verifies what the env file set up: its completion marker (C8OPT_ENV_COMPLETE, cleared before
#                     sourcing), the package venv's python with the tested Python 3.11, numpy 2.3.5, scipy 1.17.0 and
#                     mpmath 1.3.0; and with 'build',
#                     the site's g++ (symmetry 11.4.0, Expanse 13.3.0), the Boost multiprecision and GMP headers, and a
#                     GMP and libquadmath link. It exits 65 naming what is missing.
c8opt_site() {
  case "${C8OPT_SITE:-}" in
    symmetry) C8OPT_CPU_EXPECT='AMD EPYC 7543 32-Core Processor' ;;
    expanse)  C8OPT_CPU_EXPECT='AMD EPYC 7742 64-Core Processor' ;;
    *) echo "c8opt: C8OPT_SITE='${C8OPT_SITE:-}' is not symmetry or expanse (source the site's env file)" >&2; exit 64 ;;
  esac
  export C8OPT_CPU_EXPECT
}
c8opt_cpu_guard() {
  c8opt_site
  local mode="${1:-strict}" got
  got=$(sed -n '/^model name/{s/^[^:]*:[[:space:]]*//p;q;}' /proc/cpuinfo 2>/dev/null | tr -s ' ') || got=''
  export C8OPT_CPU_READ="$got"
  [[ "$got" == "$C8OPT_CPU_EXPECT" ]] && return 0
  if [[ "$mode" == lenient && "${C8OPT_ANY_CPU:-0}" == 1 ]]; then
    echo "c8opt: WARNING: $(hostname) has CPU '$got', not the site's '$C8OPT_CPU_EXPECT' (C8OPT_ANY_CPU=1: build/test only)" >&2
    return 0
  fi
  echo "c8opt: $(hostname) has CPU '$got', but $C8OPT_SITE campaigns run on '$C8OPT_CPU_EXPECT' only (exit 68; resubmit with the site's partition and exclusions: tools/submit.py)" >&2
  exit 68
}
c8opt_scratch() {
  c8opt_site
  local base
  if [[ -n "${SLURM_TMPDIR:-}" ]]; then base="$SLURM_TMPDIR"
  elif [[ "$C8OPT_SITE" == symmetry ]]; then base="/local1/${USER:-$(id -un)}/job_${SLURM_JOB_ID:?not inside a Slurm job}"
  else base="/scratch/${USER:-$(id -un)}/job_${SLURM_JOB_ID:?not inside a Slurm job}"; fi
  mkdir -p "$base/tmp" || { echo "c8opt: cannot create the node-local scratch $base" >&2; exit 74; }
  export C8OPT_SCRATCH="$base" TMPDIR="$base/tmp"
}
c8opt_omp() {
  export OPENBLAS_NUM_THREADS=1 OMP_DYNAMIC=FALSE OMP_PROC_BIND="${OMP_PROC_BIND:-close}" OMP_PLACES="${OMP_PLACES:-cores}"
  export C8_GRAPH_BATCH="${C8_GRAPH_BATCH:-8}"
}
c8opt_check_env() {
  c8opt_site
  local why=''
  [[ "${C8OPT_ENV_COMPLETE:-}" == "$C8OPT_SITE" ]] || why="the env file did not complete (C8OPT_ENV_COMPLETE='${C8OPT_ENV_COMPLETE:-}')"
  [[ -z "$why" && "${C8OPT_PYTHON:-}" == "$HOME/c8opt/venv/bin/python3" && -x "$C8OPT_PYTHON" ]] \
    || [[ -n "$why" ]] || why="C8OPT_PYTHON='${C8OPT_PYTHON:-}' is not the package venv's python ($HOME/c8opt/venv/bin/python3)"
  # the tested stack (requirements-tested.txt without pynauty): Python 3.11, numpy 2.3.5, scipy 1.17.0, mpmath 1.3.0
  [[ -z "$why" ]] && { "$C8OPT_PYTHON" -c 'import sys,numpy,scipy,mpmath; assert sys.version_info[:2] == (3, 11); assert (numpy.__version__, scipy.__version__, mpmath.__version__) == ("2.3.5", "1.17.0", "1.3.0")' 2>/dev/null \
    || why="$C8OPT_PYTHON is not Python 3.11 with numpy 2.3.5, scipy 1.17.0 and mpmath 1.3.0"; }
  if [[ -z "$why" && "${1:-}" == build ]]; then
    local want got t
    case "$C8OPT_SITE" in symmetry) want=11.4.0 ;; expanse) want=13.3.0 ;; esac
    got=$(${CXX:-g++} -dumpfullversion 2>/dev/null) || got=''
    [[ "$got" == "$want" ]] || why="${CXX:-g++} is '$got', not the site's $want (module load failed?)"
    t=$(mktemp -d "${TMPDIR:-/tmp}/c8opt_env.XXXXXX") || why="no temporary directory"
    if [[ -z "$why" ]]; then
      printf '#include <boost/multiprecision/cpp_bin_float.hpp>\n#include <gmp.h>\n#include <quadmath.h>\nint main(){mpz_t z; mpz_init(z); __float128 q = 1; return (int)(q - 1) + (int)mpz_sgn(z);}\n' > "$t/c.cpp"
      ${CXX:-g++} ${CPPFLAGS:-} -std=c++17 "$t/c.cpp" ${LDFLAGS:-} -lquadmath -lgmp -o "$t/c" > "$t/log" 2>&1 && "$t/c" \
        || why="Boost/GMP/libquadmath headers or link failed: $(tail -n 3 "$t/log" | tr '\n' ' ')"
      rm -rf "$t"
    fi
  fi
  [[ -z "$why" ]] || { echo "c8opt: environment check failed: $why" >&2; exit 65; }
}
