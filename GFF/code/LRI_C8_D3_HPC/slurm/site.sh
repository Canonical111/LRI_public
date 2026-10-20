# Sourced by every C8(3) job script (slurm/common.sh and the native, input and generation jobs: native_job.sh,
# inputs_job.sh, gen_d3_0.sh, gen_d3.sh, h1_copy.sh), after C8_ENV_SETUP and `set -u`: the site rules a job needs, in
# one place (Amendment A1; PLAN D.10). Not a job script itself; it defines functions only.
#
#   c8_set_scratch     exports C8_SCRATCH, the job's node-local scratch, computed HERE inside the job whatever the
#                      submitting shell held (A-EXP-1; --export=ALL would carry a login-node value in): $SLURM_TMPDIR,
#                      else the site's node-local disk: Expanse /scratch/$USER/job_$SLURM_JOB_ID; symmetry
#                      (C8_SITE=symmetry from env.sh) /local1/$USER/job_$SLURM_JOB_ID (symmetry sets no SLURM_TMPDIR:
#                      TaskProlog and JobContainerType are unset, and /scratch on its nodes is root's); never /tmp.
#                      It creates the directory and exits 74 if it cannot.
#   c8_toolchain_args  sets the array C8_TOOLCHAIN_ARGS, the expectations of tests/check_build.py for this site's
#                      toolchain (HD9: bitwise gates hold within one toolchain): Expanse g++ 13.3.0, Boost 1.77 (107700),
#                      the Spack GMP 6.2.1 of $C8_GMP by RPATH; symmetry g++ 11.4.0 (Ubuntu 22.04 system GCC), Boost
#                      1.77 (the boost/1.77.0 module's headers), the system GMP 6.2.1 (libgmp.so.10 resolving to
#                      /usr/lib/x86_64-linux-gnu by the loader's default search, no RPATH; C7(3) run1's toolchain).
#                      Any other C8_SITE exits 64.
#   c8_site_refusal    prints the text tools/ledger.py refuses the Mac fakes (C8_SITE=fake) with on this cluster
#                      ("this host is <site> but C8_SITE is 'fake'"), which val1 records as SITE_REFUSED.
#   c8_site_cpu        exports C8_CPU_EXPECT and C8_SITE_MODEL, computed HERE from C8_SITE (an inherited value is always
#                      overwritten; no override, the A-EXP-1 rule of C8_SCRATCH): Expanse 'AMD EPYC 7742 64-Core
#                      Processor' and gmp_expanse_epyc7742_c8.json, symmetry 'AMD EPYC 7543 32-Core Processor' and
#                      gmp_symmetry_epyc7543_c8.json (the site's measured cost model, cost_models/<C8_SITE_MODEL>), both
#                      empty for any other C8_SITE. The CPU is a package constant per site, never a model's string: the
#                      Mac tests bind it to cost_models/$C8_SITE_MODEL's cpu_model when that file exists, and HD11
#                      (production.py plan, cost_identity.py --host-cpu) compares the model with the host.
#   c8_cpu_guard       the job-side CPU pin (HD11: one CPU model per speed measurement and per campaign), run before any
#                      work by every job script that sources slurm/common.sh and by slurm/native_job.sh: nothing to do
#                      when C8_CPU_EXPECT is empty; on symmetry an Intel node (vendor GenuineIntel: defq, debugq) passes
#                      (outside the pin; the one-vendor rule covers it); else the first 'model name' of
#                      ${C8_PROC:-/proc}/cpuinfo (common.cpu_model's source), whitespace collapsed as production.norm_cpu
#                      does, must equal C8_CPU_EXPECT exactly, or the job exits 68 (EX_NOHOST) with one line naming the
#                      host, both CPUs and the remedy, before any scratch, claim or evidence is made. It exports
#                      C8_CPU_SOURCE (the file read) and C8_CPU_READ (the model read; native_job.sh's environment.txt
#                      records both). C8_PROC is the Mac tests' seam: when it is set the guard prints a loud WARNING line
#                      on stderr (the job's log) and C8_CPU_SOURCE says "TEST SEAM", so a stray export is never silent.
#   c8_vendor_guard    the job-side half of one CPU vendor per campaign (S2-001), run by slurm/common.sh after
#                      c8_cpu_guard: when C8_CPU_EXPECT is set (a real site) and C8_RUN names a campaign whose first work
#                      admission pinned its vendor ($C8_RUN/cpu_vendor.json, tools/slurm_submit.py), the node's first
#                      vendor_id of ${C8_PROC:-/proc}/cpuinfo (AuthenticAMD amd, GenuineIntel intel) must be that vendor, or
#                      the job exits 68 with one line naming the host, both vendors and the pin, before any scratch, claim,
#                      merge or output. Nothing to do without C8_RUN or a pin (a campaign job is admitted only after its pin
#                      is written), or under C8_SITE=fake or unset; an unreadable pin or vendor also exits 68.
c8_set_scratch() {
  if [[ -n "${SLURM_TMPDIR:-}" ]]; then C8_SCRATCH="$SLURM_TMPDIR"
  elif [[ "${C8_SITE:-}" == symmetry ]]; then C8_SCRATCH="/local1/${USER:-$(id -un)}/job_${SLURM_JOB_ID:?not inside a Slurm job}"
  else C8_SCRATCH="/scratch/${USER:-$(id -un)}/job_${SLURM_JOB_ID:?not inside a Slurm job}"; fi
  export C8_SCRATCH
  mkdir -p "$C8_SCRATCH" || { echo "C8: cannot create the job scratch $C8_SCRATCH (C8_SITE=${C8_SITE:-})" >&2; exit 74; }
}
c8_toolchain_args() {
  case "${C8_SITE:-}" in
    expanse)  C8_TOOLCHAIN_ARGS=(--expect-gcc 13.3.0 --expect-boost 107700 --expect-gmp-lib "${C8_GMP:?C8_GMP (the Spack GMP 6.2.1; ~/c8d3/env.sh on Expanse)}/lib"
                                 --expect-gmp-version 6.2.1) ;;
    symmetry) C8_TOOLCHAIN_ARGS=(--expect-gcc 11.4.0 --expect-boost 107700 --expect-gmp-lib /usr/lib/x86_64-linux-gnu --expect-gmp-version 6.2.1
                                 --gmp-search system) ;;
    *) echo "C8: C8_SITE=${C8_SITE:-<unset>}: the native jobs run on expanse or symmetry only (source ~/c8d3/env.sh)" >&2; exit 64 ;;
  esac
}
c8_site_refusal() { printf "this host is %s but C8_SITE is 'fake'" "${C8_SITE:-}"; }
c8_site_cpu() {
  case "${C8_SITE:-}" in
    expanse)  C8_CPU_EXPECT='AMD EPYC 7742 64-Core Processor'; C8_SITE_MODEL=gmp_expanse_epyc7742_c8.json ;;
    symmetry) C8_CPU_EXPECT='AMD EPYC 7543 32-Core Processor'; C8_SITE_MODEL=gmp_symmetry_epyc7543_c8.json ;;
    *)        C8_CPU_EXPECT=''; C8_SITE_MODEL='' ;;
  esac
  export C8_CPU_EXPECT C8_SITE_MODEL
}
c8_cpu_guard() {
  c8_site_cpu
  C8_CPU_SOURCE=''; C8_CPU_READ=''; export C8_CPU_SOURCE C8_CPU_READ   # what the guard read (environment.txt); never inherited
  [[ -n "$C8_CPU_EXPECT" ]] || return 0
  local f="${C8_PROC:-/proc}/cpuinfo" vendor='' model='' got='' host=''
  local -a words=()
  C8_CPU_SOURCE="$f"
  if [[ -n "${C8_PROC:-}" ]]; then   # the Mac tests' seam: never silent on a cluster node (a stray export would fake the pin)
    C8_CPU_SOURCE="$f (C8_PROC=$C8_PROC: TEST SEAM, not the node's /proc/cpuinfo)"
    echo "C8: WARNING: C8_PROC=$C8_PROC is set: the CPU pin reads $f, a TEST SEAM, not this node's /proc/cpuinfo (tools/lanes.py takes its topology there too); on a cluster unset C8_PROC in the submitting shell and resubmit (a submission's default --export=ALL carries it into every job; HD11)" >&2
  fi
  vendor=$(sed -n '/^vendor_id/{s/^[^:]*:[[:space:]]*//p;q;}' "$f" 2>/dev/null) || vendor=''
  model=$(sed -n '/^model name/{s/^[^:]*:[[:space:]]*//p;q;}' "$f" 2>/dev/null) || model=''
  IFS=$' \t\n' read -r -a words <<< "$model" || true
  if [[ ${#words[@]} -gt 0 ]]; then got=$(IFS=' '; printf '%s' "${words[*]}"); fi
  C8_CPU_READ="${got:-unreadable}"
  if [[ "$vendor" == GenuineIntel* && "${C8_SITE:-}" == symmetry ]]; then return 0; fi   # defq/debugq: outside the pin
  if [[ -n "$got" && "$got" == "$C8_CPU_EXPECT" ]]; then return 0; fi                     # exact; no substring match
  host=$(hostname 2>/dev/null) || host='?'
  echo "C8: ${host:-?} (C8_SITE=${C8_SITE:-}, partition ${SLURM_JOB_PARTITION:-?}, job ${SLURM_JOB_ID:-?}) is '${got:-unreadable}' but this site's jobs run on '$C8_CPU_EXPECT' only (HD11: the cost model's CPU; one CPU model per speed measurement and per campaign); nothing was claimed or written. Resubmit with the node excluded (symmetry: add it to C8_AMD_EXCLUDE_EXTRA; Expanse: -x <node> in the job's options) and record it (docs/HPC.md, CPU pin)" >&2
  exit 68
}
c8_vendor_guard() {
  [[ -n "${C8_CPU_EXPECT:-}" && -n "${C8_RUN:-}" ]] || return 0
  local pin="$C8_RUN/cpu_vendor.json" want='' raw='' got='' host=''
  [[ -e "$pin" ]] || return 0
  want=$(sed -n '/^[[:space:]]*"vendor":/{s/^[[:space:]]*"vendor":[[:space:]]*"\([a-z]*\)".*/\1/p;q;}' "$pin" 2>/dev/null) || want=''
  raw=$(sed -n '/^vendor_id/{s/^[^:]*:[[:space:]]*//p;q;}' "${C8_PROC:-/proc}/cpuinfo" 2>/dev/null) || raw=''
  case "$raw" in AuthenticAMD*) got=amd ;; GenuineIntel*) got=intel ;; *) got='' ;; esac
  if [[ -n "$want" && "$got" == "$want" ]]; then return 0; fi
  host=$(hostname 2>/dev/null) || host='?'
  echo "C8: ${host:-?} (C8_SITE=${C8_SITE:-}, partition ${SLURM_JOB_PARTITION:-?}, job ${SLURM_JOB_ID:-?}) has CPU vendor '${got:-unreadable}' (vendor_id '${raw:-?}'), but the campaign $C8_RUN is pinned to '${want:-unreadable}' ($pin, its first work admission; S2-001: native rows and the float64 assembly differ between vendors); nothing was claimed or written. Submit this campaign's jobs to the partitions of '${want:-its vendor}' only (c8_profile)" >&2
  exit 68
}
