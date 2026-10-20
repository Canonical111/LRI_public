#!/bin/bash
# Submit lri_1d_c4_exact jobs to symmetry from the login node (light work only). Run from an immutable read-only
# code snapshot ~/lri_1d_c4/<commit> deployed with `git archive` (see README); every job re-verifies the snapshot sha
# (c4_run1d.py sha: sources, validators, fits, vendored code, inputs, Slurm scripts) on its node.
#   slurm/submit.sh validate                          [partition]
#   slurm/submit.sh bench   LMAX "THREADS..."         [partition]   (C4_TASKS="0 1" to bench several tasks)
#   slurm/submit.sh prod    LMAX NNODES WPS BLOCK      [partition]
# Gates (all keyed by the snapshot sha): prod needs validation/<sha>/PASS; LMAX > 400 also needs
# validation/<sha>/A9_APPROVED (written by the coordinator after the Codex inspection); LMAX = 1000 needs the gate
# record results/<sha12>/gates_L400.txt and LMAX = 2000 results/<sha12>/gates_L1000.txt: recorded snapshot sha equal
# to this one, no FAIL, the staged A6d line, and the sha256 of both compared result files equal to the files now on
# disk. Partition default: amdq if it has idle nodes, else defq (user rule: amdq first). Memory: 245G amd, 180G intel.
# Job names use the prefix l1c4- (no package prefix of another tool).
set -euo pipefail
C4_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P); C4_DATA=${C4_DATA:-<SCRATCH>/lri_1d_c4}
export C4_ROOT C4_DATA
source "$C4_ROOT/slurm/env.sh"
for __v in $(compgen -e); do [[ $__v == SBATCH_* || $__v == SQUEUE_* ]] && unset "$__v"; done; unset __v
die() { echo "submit: $*" >&2; exit 2; }
w=$(find "$C4_ROOT" -type f -perm -u+w -print -quit); [[ -z $w ]] || die "code snapshot is writable ($w)"
export C4_EXPECT_SHA=$(cd "$C4_ROOT" && python c4_run1d.py sha --kind snapshot)
lock=; release_lock() { if [[ -n $lock ]]; then rm -rf "$lock"; fi; }
mkdir -p "$C4_DATA/logs"
mkdir "$C4_DATA/.submit.lock" 2>/dev/null || die "another submission holds $C4_DATA/.submit.lock"
lock=$C4_DATA/.submit.lock; trap release_lock EXIT
live() { local out; out=$(squeue -h -u "$USER" -n "$1" -o '%F %j %T') || return 1; echo "$out"; }
pick_part() {
  if [[ -n ${1:-} ]]; then echo "$1"; return; fi
  local idle; idle=$(sinfo -h -p amdq -o '%t %D' | awk '$1=="idle"{s+=$2} END{print s+0}') || die "sinfo failed"
  if (( idle > 0 )); then echo amdq; else echo defq; fi
}
memfor() { case $1 in amd*) echo 245G;; largememq) echo 370G;; *) echo 180G;; esac; }
timefor() { case $1 in debugq|amddebugq) echo 01:00:00;; *) echo "$2";; esac; }   # debug queues cap at 1 h
V=$C4_DATA/validation/$C4_EXPECT_SHA
R=$C4_DATA/results/${C4_EXPECT_SHA:0:12}
check_gate() {  # check_gate GATEFILE PREV CUR: staged A6d record bound to this snapshot and to the files on disk
  local G=$1 prev=$2 cur=$3 line ps cs
  [[ -f $G ]] || die "gate record $G missing"
  grep -qx "snapshot_sha $C4_EXPECT_SHA" "$G" || die "$G was not produced by snapshot $C4_EXPECT_SHA"
  ! grep -q '^FAIL' "$G" || die "$G contains FAIL"
  line=$(grep "^PASS A6d_${prev}_vs_${cur} " "$G") || die "$G has no PASS A6d_${prev}_vs_${cur}"
  ps=$(sed -n 's/.*prev_sha256=\([0-9a-f]\{64\}\).*/\1/p' <<<"$line"); cs=$(sed -n 's/.*cur_sha256=\([0-9a-f]\{64\}\).*/\1/p' <<<"$line")
  [[ $ps == "$(sha256sum "$R/c4_1d_L$prev.npz" | cut -c1-64)" ]] || die "L$prev result changed since its A6d record"
  [[ $cs == "$(sha256sum "$R/c4_1d_L$cur.npz" | cut -c1-64)" ]] || die "L$cur result changed since its A6d record"
}
case ${1:-} in
  validate)
    P=$(pick_part "${2:-}")
    b=$(live l1c4-validate) || die "squeue failed"; [[ -z $b ]] || die "validation live: $b"
    jid=$(sbatch --parsable -p "$P" --job-name=l1c4-validate --mem="$(memfor "$P")" --time="$(timefor "$P" 06:00:00)" \
      --output="$C4_DATA/logs/%x_%j.out" --export=ALL "$C4_ROOT/slurm/validate.slurm") || die "sbatch failed"
    echo "submitted $jid on $P (snapshot $C4_EXPECT_SHA); log $C4_DATA/logs/l1c4-validate_$jid.out" ;;
  bench)
    [[ ${2:-} =~ ^[0-9]+$ && -n ${3:-} ]] || die "usage: bench LMAX \"THREADS...\" [partition]"
    P=$(pick_part "${4:-}")
    export C4_LMAX=$2 C4_THREADS=$3
    jid=$(sbatch --parsable -p "$P" --job-name=l1c4-bench --mem="$(memfor "$P")" --time="$(timefor "$P" 08:00:00)" \
      --output="$C4_DATA/logs/%x_%j.out" --export=ALL "$C4_ROOT/slurm/bench.slurm") || die "sbatch failed"
    echo "submitted $jid on $P; log $C4_DATA/logs/l1c4-bench_$jid.out" ;;
  prod)
    [[ ${2:-} =~ ^[0-9]+$ && ${3:-} =~ ^[1-9][0-9]*$ && ${4:-} =~ ^[1-9][0-9]*$ && ${5:-} =~ ^[1-9][0-9]*$ ]] \
      || die "usage: prod LMAX NNODES WPS BLOCK [partition]"
    L=$2; NN=$3; WPS=$4; BLK=$5; P=$(pick_part "${6:-}")
    [[ -f $V/PASS ]] && grep -q "snapshot_sha $C4_EXPECT_SHA" "$V/PASS" || die "no validation PASS for snapshot $C4_EXPECT_SHA"
    (( L <= 400 )) || { [[ -f $V/A9_APPROVED ]] && grep -q "snapshot_sha $C4_EXPECT_SHA" "$V/A9_APPROVED"; } \
      || die "Lmax $L > 400 needs $V/A9_APPROVED (Codex inspection of this snapshot)"
    PREV=
    case $L in
      1000) PREV=400; check_gate "$R/gates_L400.txt" 200 400 ;;
      2000) PREV=1000; check_gate "$R/gates_L1000.txt" 400 1000 ;;
      200|400) ;;
      *) die "Lmax must be one of 200, 400, 1000, 2000 (the staged ladder)" ;;
    esac
    [[ ! -e $R/c4_1d_L$L.npz && ! -e $R/gates_L$L.txt ]] || die "result or gate record for Lmax $L exists in $R"
    b=$(live "l1c4-L$L") || die "squeue failed"; [[ -z $b ]] || die "jobs for Lmax $L live: $b"
    b=$(live "l1c4-L$L-asm") || die "squeue failed"; [[ -z $b ]] || die "assembly for Lmax $L live: $b"
    export C4_LMAX=$L C4_NNODES=$NN C4_WPS=$WPS C4_BLOCK=$BLK C4_PREV=$PREV
    jid=$(sbatch --parsable -p "$P" --job-name="l1c4-L$L" --array="0-$(( NN - 1 ))" --mem="$(memfor "$P")" \
      --time=24:00:00 --output="$C4_DATA/logs/%x_%A_%a.out" --export=ALL "$C4_ROOT/slurm/node.slurm") || die "sbatch failed"
    aid=$(sbatch --parsable -p "$P" --job-name="l1c4-L$L-asm" --dependency="afterok:${jid%%;*}" --mem="$(memfor "$P")" \
      --time=04:00:00 --output="$C4_DATA/logs/%x_%j.out" --export=ALL "$C4_ROOT/slurm/assemble.slurm") || die "sbatch (assemble) failed"
    echo "submitted array ${jid%%;*} (Lmax $L, $NN nodes on $P, $WPS workers/socket, block $BLK) + assemble $aid"
    echo "logs: $C4_DATA/logs/l1c4-L${L}_${jid%%;*}_<i>.out, per-part $C4_DATA/logs/run_L${L}_${jid%%;*}/part<k>.log, $C4_DATA/logs/l1c4-L$L-asm_$aid.out" ;;
  *) die "usage: $0 validate | bench LMAX THREADS | prod LMAX NNODES WPS BLOCK [partition]" ;;
esac
