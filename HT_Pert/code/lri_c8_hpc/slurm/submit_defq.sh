#!/bin/bash
# Submit lri_c8 jobs to symmetry defq (run on the login node; light work only).
#   slurm/submit_defq.sh validate [extra sbatch args]
#   slurm/submit_defq.sh lanes /abs/campaign.json /mnt/beegfs/.../runs/<name> [extra sbatch args]
# `lanes` submits only array tasks that still lack an accepted output, so the same command
# resumes a campaign after TIMEOUT or exit 75. Under a cross-node mutex it refuses while any
# job writing to the same output directory is queued or running (by name prefix and by the
# job ids it recorded), and only then moves owner files aside whose recorded job is not live
# (scripts/clean_owners.py) and submits. It is the only supported launcher of lanes.
# Extra sbatch args: only an exact allowlist in --name=value form (e.g. --time=12:00:00);
# job name, array, export, output and chdir are always the wrapper's.
# Env: C8_DATA (default <SCRATCH>/lri_c8), C8_MAX_NODES (array throttle, default 8),
#      C8_RETRY_FAILED=1 to resubmit lanes whose last attempt failed or ended unclassified.
set -euo pipefail
C8_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
C8_DATA=${C8_DATA:-<SCRATCH>/lri_c8}
export C8_ROOT C8_DATA C8_CACHE_ROLE=login
source "$C8_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "submit_defq: errexit lost after sourcing the environment" >&2; exit 2; }
die() { echo "submit_defq: $*" >&2; exit 2; }
lock=
release_lock() { if [[ -n $lock ]]; then rm -rf "$lock"; fi; }
take_lock() {  # cross-node mutex held through query, cleanup and submission (mkdir is atomic)
  mkdir -p "$(dirname "$1")"
  mkdir "$1" 2>/dev/null || die "another submission holds $1 (remove it only if no submit_defq.sh is running)"
  lock=$1; trap release_lock EXIT
  echo "$(hostname) $$ $(date '+%Y-%m-%dT%H:%M:%S%z')" > "$lock/owner"
}
check_args() {  # extra sbatch options: an exact allowlist, only in --name=value form
  local x
  for x in "$@"; do
    case $x in
      --time=?*|--partition=?*|--qos=?*|--account=?*|--exclude=?*|--nodelist=?*|--begin=?*|--dependency=?*|\
      --reservation=?*|--mail-type=?*|--mail-user=?*|--comment=?*|--nice=?*|--hold) ;;
      *) die "extra sbatch argument '$x' not allowed (use --time=, --partition=, --qos=, --account=, --exclude=, --nodelist=, --begin=, --dependency=, --reservation=, --mail-type=, --mail-user=, --comment=, --nice=, --hold)" ;;
    esac
  done
}
# Inherited SQUEUE_* settings (format, states, users, ...) must not filter the query, and
# inherited SBATCH_* settings take precedence over #SBATCH directives (memory, requeue,
# signal, partition, ...), so neither may reach squeue/sbatch.
for __v in $(compgen -e); do [[ $__v == SQUEUE_* || $__v == SBATCH_* ]] && unset "$__v"; done; unset __v
live() {  # non-terminal jobs whose name starts with $1 or whose base id is recorded in file $2
  local out ids=
  # --states=all: the default view omits SUSPENDED (and other non-running) jobs.
  out=$(squeue -h -u "$USER" --states=all -o '%F %j %T') || return 1
  if [[ -f $2 ]]; then ids=$(awk '{printf " %s", $1}' "$2"); fi
  awk -v p="$1" -v ids="$ids " '
    $3 ~ /^(COMPLETED|CANCELLED|FAILED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE|PREEMPTED|REVOKED)/ {next}
    index($2, p) == 1 || index(ids, " " $1 " ") {print}' <<<"$out"
}
submit() {  # sbatch with a checked, numeric job id; the allocation invariants are explicit
  local jid
  jid=$(sbatch --parsable --nodes=1 --ntasks=1 --exclusive --mem=180G --no-requeue "$@") || die "sbatch failed"
  jid=${jid%%;*}
  [[ $jid =~ ^[0-9]+$ ]] || die "unexpected sbatch output: $jid"
  echo "$jid"
}
mode=${1:-}; shift || true
case $mode in
  validate)
    check_args "$@"
    name="c8-val-${C8_SRC16:0:8}"; record="$C8_DATA/validation/submissions.txt"
    mkdir -p "$C8_DATA/logs" "$C8_DATA/validation"
    take_lock "$C8_DATA/validation/.submit.lock"
    busy=$(live "$name" "$record") || die "squeue failed; not submitting"
    [[ -z $busy ]] || die "validation already queued/running:"$'\n'"$busy"
    # With --export=ALL an inherited variable beats a value given in --export (sbatch man
    # page), so the job's paths are set in this shell's environment instead.
    export C8_ROOT C8_DATA
    jid=$(submit --job-name="$name" --chdir="$C8_DATA" --output="$C8_DATA/logs/%x_%j.out" \
      --export=ALL "$@" "$C8_ROOT/slurm/defq_validate.slurm") || exit 2
    echo "$jid $name $(date '+%Y-%m-%dT%H:%M:%S%z') validate" >> "$record"
    echo "submitted $jid; log $C8_DATA/logs/${name}_${jid}.out; receipt $C8_DATA/validation/${C8_SRC16}_${jid}/receipt.json" ;;
  lanes)
    [[ $# -ge 2 ]] || die "usage: lanes /abs/campaign.json /mnt/beegfs/.../runs/<name> [sbatch args]"
    campaign=$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1"); out=$2; shift 2
    check_args "$@"
    [[ -f $campaign ]] || die "no campaign $campaign"
    beegfs=/mnt/beegfs/; [[ ${C8_LOCAL_TEST:-0} == 1 ]] && beegfs=${C8_TEST_OUTPUT_PREFIX:-$beegfs}  # tests only
    [[ $out == "$beegfs"* ]] || die "output must be on $beegfs"
    mkdir -p "$out/logs"; out=$(cd "$out" && pwd -P)
    [[ $out == "$beegfs"* ]] || die "output resolves outside $beegfs: $out"
    take_lock "$out/.submit.lock"
    prefix="c8-$(printf %s "$out" | sha256sum | cut -c1-8)"
    busy=$(live "$prefix" "$out/submissions.txt") || die "squeue failed; not submitting"
    [[ -z $busy ]] || die "jobs writing to $out are queued/running:"$'\n'"$busy"
    args=(); if [[ ${C8_RETRY_FAILED:-0} == 1 ]]; then args=(--retry-failed); fi
    info=$(python "$C8_ROOT/scripts/campaign_info.py" todo "$campaign" "$out" ${args[@]+"${args[@]}"}) \
      || die "campaign_info failed"
    read -r todo cid <<<"$info"
    [[ -n $todo && -n $cid ]] || die "campaign_info printed nothing usable: $info"
    [[ $todo != - ]] || { echo "submit_defq: nothing to submit (all accepted, or only held lanes left)" >&2; exit 0; }
    # No job of this output directory is live (checked under the mutex). Owner files are
    # moved aside only if the job recorded in each one is not live either.
    python "$C8_ROOT/scripts/clean_owners.py" "$out" >&2 || die "owner files are not provably stale; not submitting"
    name="$prefix-$cid"
    # With --export=ALL an inherited variable beats a value given in --export (sbatch man
    # page): put exactly the checked paths into this shell's environment.
    export C8_ROOT C8_DATA CAMPAIGN="$campaign" C8_OUTPUT="$out"
    jid=$(submit --job-name="$name" --array="${todo}%${C8_MAX_NODES:-8}" \
      --chdir="$out" --output="$out/logs/%x_%A_%a.out" --export=ALL --signal=B:USR1@1800 \
      "$@" "$C8_ROOT/slurm/defq_lane.slurm") || exit 2
    echo "$jid $name $(date '+%Y-%m-%dT%H:%M:%S%z') lanes=$todo" >> "$out/submissions.txt"
    echo "submitted $jid (lanes $todo); logs $out/logs/${name}_${jid}_<lane>.out; journals $out/journals/$cid/" ;;
  *) die "usage: $0 validate | lanes CAMPAIGN OUTDIR [sbatch args]" ;;
esac
