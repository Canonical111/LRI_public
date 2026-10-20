# Per-role sbatch options on Expanse (PLAN D.10; sourced after ~/c8d3/env.sh): `c8_profile ROLE` exports
# C8_SBATCH_ARGS for tools/slurm_submit.py. Site values live only here and in env.sh, never in #SBATCH lines.
#   lanes   whole compute nodes for lane workers: -A yun124 -p compute, C8_LANE_MEM=240G (slurm_submit.py lanes adds
#           --exclusive --nodes=1 --ntasks=1 itself; no --ntasks-per-node, references/expanse.md:182)
#   arrays  shared array elements: wide (32-64 cores), --mem <= 2G per core so the charge is by cores (F39), throttle
#           %8 (C8_THROTTLE) inside the session's shared share (HD13); the scripts add --nodes=1
#   debug   quick checks: -p debug, at most 30 min, two jobs per account
# Merges always take C8_MERGE_SBATCH_ARGS (shared, -c 24, --mem=48G), outside the normal-QOS share.
export C8_LANE_MEM=240G
export C8_MERGE_SBATCH_ARGS="-A yun124 -p shared -c 24 --mem=48G -t 02:00:00"
export C8_THROTTLE=8
c8_profile() {
  case "${1:-}" in
    lanes)  export C8_SBATCH_ARGS="-A yun124 -p compute" ;;
    arrays) export C8_SBATCH_ARGS="-A yun124 -p shared -c ${2:-32} --mem=$(( 2 * ${2:-32} ))G" ;;
    debug)  export C8_SBATCH_ARGS="-A yun124 -p debug -c ${2:-16} --mem=$(( 2 * ${2:-16} ))G -t 00:30:00" ;;
    *) echo "c8_profile lanes|arrays [cores]|debug [cores]" >&2; return 64 ;;
  esac
}
