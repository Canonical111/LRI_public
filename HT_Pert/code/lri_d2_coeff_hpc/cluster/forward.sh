# shellcheck shell=bash
# run_forwarding CMD [ARGS...]: run CMD in the background, forward USR1, TERM and INT to it until it exits,
# and return its exit status (a signal death of CMD returns 128+N as usual).
# cluster/job.sbatch uses it because only the batch shell receives --signal=B:USR1, and bash runs traps
# only between commands, so a foreground child would never be told. Tested by tests/test_cluster.py.

__lri_coeff_child=
__lri_coeff_pending=
__lri_coeff_signalled=0
__lri_coeff_forward() {
  __lri_coeff_signalled=1
  if [[ -n $__lri_coeff_child ]]; then
    echo "job: SIG$1 at $(date '+%H:%M:%S'), forwarded to $__lri_coeff_child"
    kill -s "$1" "$__lri_coeff_child" 2>/dev/null || true
  else
    __lri_coeff_pending=$1   # arrived before the child started: deliver it right after the start
  fi
}

run_forwarding() {
  local rc= r
  trap '__lri_coeff_forward USR1' USR1
  trap '__lri_coeff_forward TERM' TERM
  trap '__lri_coeff_forward INT' INT
  "$@" &
  __lri_coeff_child=$!
  if [[ -n $__lri_coeff_pending ]]; then __lri_coeff_forward "$__lri_coeff_pending"; fi
  # A trapped signal makes wait return early with a status > 128, and the trap runs before the next
  # command. After such an interruption wait again: it returns the child's saved status once the child
  # has ended, or 127 if this shell already collected it (then the previous status was the child's).
  while :; do
    __lri_coeff_signalled=0
    wait "$__lri_coeff_child" && r=0 || r=$?
    if (( r == 127 )) && [[ -n $rc ]]; then break; fi
    rc=$r
    (( r > 128 && __lri_coeff_signalled )) || break
  done
  trap - USR1 TERM INT
  __lri_coeff_child=
  return "$rc"
}
