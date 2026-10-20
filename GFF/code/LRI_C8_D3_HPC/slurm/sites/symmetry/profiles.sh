# Per-role sbatch options on symmetry (Amendment A1; PLAN D.10; sourced after ~/c8d3/env.sh): `c8_profile ROLE`
# exports C8_SBATCH_ARGS for tools/slurm_submit.py. Site values live only here and in env.sh, never in #SBATCH lines.
# Every symmetry CPU partition is EXCLUSIVE (whole nodes); slurm_submit.py adds --exclude=cn112 to every AMD-pool job
# (cn112 is AVX-512; the bitwise gates hold on the AVX2 nodes) and refuses longq, preq, amdpreq and sharedq.
# The CPU pin (HD11; one CPU model per speed measurement and per campaign): slurm_submit.py also excludes, from every
# AMD-pool job, the AMD nodes known not to be EPYC 7543 (budget.SYMMETRY.cpu_exclude: cn079-082, cn084, cn085, cn087,
# cn092, EPYC 7532) and those of C8_AMD_EXCLUDE_EXTRA (env.sh), merged into the job's own --exclude; slurm/site.sh c8_cpu_guard
# stops (68) a job that lands on another CPU. No option below changes for it.
#   lanes   whole AMD nodes (EPYC 7532/7543, 64 cores, NPS4 = 8 NUMA nodes of 8 cores): -p amdq, C8_LANE_MEM=240G; the
#           default lane shape (C8_LANES unset) is 8 x 8 at the plan's --threads 8 (tools/lanes.py). lanes N submits
#           N workers and one merge, all on amdq, so N + 1 AMD-pool nodes count against H7 (4 in development: N <= 3;
#           5 in the pilot window: N <= 4). Lane time auto, at most 23:30:00 (amdq 24 h).
#   intel   whole Intel nodes (Gold 6148, 2 sockets x 20 cores): -p defq, C8_LANE_MEM=180G, one lane per socket
#           (2 x 20, C8_LANES unset, or C8_LANES=socket). Outside the H7 cap; f_class 1.5 (no measured Intel model).
#           One CPU vendor per campaign: never mix amdq and defq workers in one campaign.
#   debug   quick checks: -p amddebugq (AMD, at most 1 h, counted in H7) or debug-intel (-p debugq, at most 1 h; raw jobs
#           there only under intel_* or drill_* roles).
# Merges take C8_MERGE_SBATCH_ARGS, which EVERY profile sets (a merge left over from another profile would put an AMD
# campaign's float64 assembly on an AVX-512 Intel node; slurm_submit.py also refuses a merge of another vendor than
# its workers): a whole amdq node with -c 64 for lanes and debug, a whole defq node with -c 40 (the physical cores) for
# intel and debug-intel. slurm/merge.sh sizes --jobs/--parse-jobs from SLURM_CPUS_PER_TASK (4 when -c is missing).
C8_MERGE_AMD="-p amdq -c 64 --mem=240G -t 02:00:00"
C8_MERGE_INTEL="-p defq -c 40 --mem=180G -t 02:00:00"
export C8_LANE_MEM=240G
export C8_MERGE_SBATCH_ARGS="$C8_MERGE_AMD"
c8_profile() {
  case "${1:-}" in
    lanes)       export C8_SBATCH_ARGS="-p amdq" C8_LANE_MEM=240G C8_MERGE_SBATCH_ARGS="$C8_MERGE_AMD" ;;
    intel)       export C8_SBATCH_ARGS="-p defq" C8_LANE_MEM=180G C8_MERGE_SBATCH_ARGS="$C8_MERGE_INTEL" ;;
    debug)       export C8_SBATCH_ARGS="-p amddebugq --mem=240G -t 00:59:00" C8_MERGE_SBATCH_ARGS="$C8_MERGE_AMD" ;;
    debug-intel) export C8_SBATCH_ARGS="-p debugq --mem=180G -t 00:59:00" C8_MERGE_SBATCH_ARGS="$C8_MERGE_INTEL" ;;
    *) echo "c8_profile lanes|intel|debug|debug-intel" >&2; return 64 ;;
  esac
}
