#!/bin/bash
# Submit lri_1d_c5_exact jobs to symmetry from the login node (light work only). Run from an immutable read-only code
# snapshot ~/lri_1d_c5/<commit> deployed with `git archive` (slurm/README_SLURM.md); every job re-verifies the snapshot
# sha (`python run5.py sha --kind snapshot`: sources, validators, fits, vendored code, inputs, Slurm scripts) on its node.
#   slurm/submit.sh validate                          [partition]   (C5_VAL_WPS, C5_VAL_BLOCK, C5_VAL_TIME)
#   slurm/submit.sh bench   LMAX "THREADS..."         [partition]   (C5_TASKS="worst" | indices, C5_BLOCK, C5_TIME)
#   slurm/submit.sh prod    LMAX NNODES WPS BLOCK     [partition]   (C5_TIME, C5_ASM_PART, C5_ASM_TIME, C5_BENCH_L)
#   slurm/submit.sh assemble LMAX                     [partition]   (recovery: re-run the assembly of a finished rung)
# Gates (all keyed by the snapshot sha <sha>, records under $C5_DATA/validation/<sha>/ and results/<sha12>/):
#   validate: refused if validation/<sha>/PASS exists or a validation job is live.
#   bench:    needs validation/<sha>/PRELIM (A1-A3, A6a-c of this snapshot; written by the validation job) or PASS;
#             writes no checkpoints/results; one live benchmark job per LMAX.
#   prod:     LMAX in the staged ladder 240 320 400 500 (80 and 160 are run by the validation job); needs
#             validation/<sha>/PASS, validation/<sha>/A9_APPROVED (written by the coordinator after the Codex
#             inspection; a line containing "snapshot_sha <sha>"), the gate record of the previous rung
#             (240 <- gates_L160 with A6d_80_vs_160, 320 <- gates_L240 with A6d_160_vs_240, 400 <- gates_L320 with
#             A6d_240_vs_320, 500 <- gates_L400 with A6d_320_vs_400): recorded snapshot sha equal to this one, no FAIL,
#             PASS A4, A5, A6e and the staged A6d line, and the sha256 of both compared results equal to the files now
#             on disk; and a benchmark record validation/<sha>/bench_L<Lb>.json of this snapshot with Lb >= LMAX
#             (default: the largest such Lb; C5_BENCH_L picks another one >= LMAX). Sizing: refused unless
#             2 x WPS x peak_rss_GB <= 0.85 x node memory (Intel 191, AMD 256, largememq 384 GB), peak_rss_GB = max
#             over the record's runs of the designated worst-case task (worst_case true and spec_sha equal to
#             `run5.py worstspec --Lmax Lb`) with block >= BLOCK; other runs are ignored; the sizing is printed.
#   assemble: recovery for a rung whose node jobs finished but whose assembly failed or was interrupted: same gates
#             as prod except the sizing; refused while jobs of the rung are live or its gate record exists; an orphan
#             result without a gate record is moved to results/<sha12>/orphan/ after checking that its provenance names
#             this snapshot.
# Partition default: amdq if it has idle nodes outside active reservations, else defq (user rule: amdq first). Allowed:
# exclusive non-preemptible partitions only (the jobs are --no-requeue). Memory: 245G amd, 180G intel, 370G largememq;
# debug queues cap the time at 1 h. Job names: l1c5-validate, l1c5-bench-L<L>, l1c5-L<L>, l1c5-L<L>-asm (prefix l1c5-,
# no package prefix of another tool). Submissions are serialised by the mutex directory $C5_DATA/.submit.lock.
set -euo pipefail
C5_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P); C5_DATA=${C5_DATA:-<SCRATCH>/lri_1d_c5}
export C5_ROOT C5_DATA
source "$C5_ROOT/slurm/env.sh"
for __v in $(compgen -e); do [[ $__v == SBATCH_* || $__v == SQUEUE_* || $__v == SINFO_* ]] && unset "$__v"; done; unset __v
die() { echo "submit: $*" >&2; exit 2; }
w=$(find "$C5_ROOT" -type f -perm -u+w -print -quit); [[ -z $w ]] || die "code snapshot is writable ($w)"
C5_EXPECT_SHA=$(cd "$C5_ROOT" && python run5.py sha --kind snapshot); export C5_EXPECT_SHA
[[ $C5_EXPECT_SHA =~ ^[0-9a-f]{64}$ ]] || die "snapshot sha '$C5_EXPECT_SHA' is not a sha256"
V=$C5_DATA/validation/$C5_EXPECT_SHA
R=$C5_DATA/results/${C5_EXPECT_SHA:0:12}
lock=; release_lock() { if [[ -n $lock ]]; then rm -rf "$lock"; fi; }
mkdir -p "$C5_DATA/logs"
mkdir "$C5_DATA/.submit.lock" 2>/dev/null || die "another submission holds $C5_DATA/.submit.lock ($(cat "$C5_DATA/.submit.lock/owner" 2>/dev/null)); remove it if stale"
lock=$C5_DATA/.submit.lock; trap release_lock EXIT
echo "pid $$ host $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z') $*" > "$lock/owner"
sha() { sha256sum "$1" | cut -c1-64; }
live() { local out; out=$(squeue -h -u "$USER" -n "$1" -o '%F %j %T') || return 1; echo "$out"; }
nolive() { local b; b=$(live "$1") || die "squeue failed"; [[ -z $b ]] || die "job $1 live: $b"; }
PARTS="amdq amddebugq largememq defq debugq longq"
check_part() { [[ " $PARTS " == *" $1 "* ]] || die "partition '$1' not allowed (exclusive non-preemptible only: $PARTS)"; }
free_idle() {  # idle nodes of partition $1 not held by an active reservation (sinfo can show those as idle)
  local idle res
  idle=$(sinfo -h -N -p "$1" -t idle -o '%N' | sort -u) || return 1
  res=$(scontrol show res -o | awk '/State=ACTIVE/ {for (i = 1; i <= NF; i++) if ($i ~ /^Nodes=/) print substr($i, 7)}') || return 1
  if [[ -n $res ]]; then res=$(for n in $res; do scontrol show hostnames "$n"; done | sort -u) || return 1; fi
  comm -23 <(printf '%s\n' "$idle") <(printf '%s\n' "$res") | grep -c . || true
}
pick_part() {
  if [[ -n ${1:-} ]]; then check_part "$1"; echo "$1"; return; fi
  local n; n=$(free_idle amdq) || die "sinfo/scontrol failed"
  if (( n > 0 )); then echo amdq; else echo defq; fi
}
survey() {  # survey PARTITION NODES: say whether the job should start now
  local n; n=$(free_idle "$1") || die "sinfo/scontrol failed"
  if (( n >= $2 )); then echo "survey: $1 has $n idle unreserved node(s), job needs $2: should start now"
  else echo "survey: $1 has $n idle unreserved node(s), job needs $2: will QUEUE"; fi
}
memfor() { case $1 in amd*) echo 245G;; largememq) echo 370G;; *) echo 180G;; esac; }
nodemem() { case $1 in amd*) echo 256;; largememq) echo 384;; *) echo 191;; esac; }   # GB, for the sizing rule
corefor() { case $1 in amd*) echo 32;; *) echo 20;; esac; }    # physical cores per package (node.slurm re-checks)
timefor() { case $1 in debugq|amddebugq) echo 01:00:00;; *) echo "$2";; esac; }   # debug queues cap at 1 h
check_c4ref() {
  [[ -f $C5_C4REF ]] || die "A6e reference $C5_C4REF missing"
  [[ $(sha "$C5_C4REF") == "$C5_C4REF_SHA256" ]] || die "sha256 of $C5_C4REF is not the pinned $C5_C4REF_SHA256"
}
has_sha() { grep -Eq "snapshot_sha[ =]$C5_EXPECT_SHA([^0-9a-f]|\$)" "$1"; }   # a line naming the full sha
check_gate() {  # check_gate PREV CUR: gates_L<CUR> of this snapshot, complete, bound to the result files on disk
  local prev=$1 cur=$2 G=$R/gates_L$2.txt line ps cs rs
  [[ -f $G ]] || die "gate record $G missing"
  grep -qx "snapshot_sha $C5_EXPECT_SHA" "$G" || die "$G was not produced by snapshot $C5_EXPECT_SHA"
  ! grep -q '^FAIL' "$G" || die "$G contains FAIL"
  grep -qx 'PASS A4' "$G" || die "$G has no PASS A4"
  grep -qx 'PASS A5' "$G" || die "$G has no PASS A5"
  grep -q "^PASS A6e c4ref_sha256=$C5_C4REF_SHA256 " "$G" || die "$G has no PASS A6e against the pinned C4 reference"
  line=$(grep "^PASS A6d_${prev}_vs_${cur} " "$G") || die "$G has no PASS A6d_${prev}_vs_${cur}"
  ps=$(sed -n 's/.*prev_sha256=\([0-9a-f]\{64\}\).*/\1/p' <<<"$line"); cs=$(sed -n 's/.*cur_sha256=\([0-9a-f]\{64\}\).*/\1/p' <<<"$line")
  rs=$(sed -n 's/^result .* sha256 \([0-9a-f]\{64\}\)$/\1/p' "$G")
  [[ -f $R/c5_1d_L$prev.npz && -f $R/c5_1d_L$cur.npz ]] || die "result L$prev or L$cur missing in $R"
  [[ $ps == "$(sha "$R/c5_1d_L$prev.npz")" ]] || die "L$prev result changed since its A6d record"
  [[ $cs == "$(sha "$R/c5_1d_L$cur.npz")" && $rs == "$cs" ]] || die "L$cur result changed since its A6d record"
  echo "gate: $G ok (A4 A5 A6e A6d_${prev}_vs_${cur}; L$prev ${ps:0:12}, L$cur ${cs:0:12})"
}
size_check() {  # size_check LMAX WPS BLOCK PARTITION: print the sizing; non-zero status = refuse
  C5Z_V=$V C5Z_L=$1 C5Z_WPS=$2 C5Z_BLOCK=$3 C5Z_PART=$4 C5Z_MEM=$(nodemem "$4") C5Z_CORES=$(corefor "$4") \
    C5Z_BENCH_L=${C5_BENCH_L:-} python - <<'PY'
import glob, json, os, re, sys
e = os.environ
V, sha, L, wps, blk = e["C5Z_V"], e["C5_EXPECT_SHA"], int(e["C5Z_L"]), int(e["C5Z_WPS"]), int(e["C5Z_BLOCK"])
mem, part, cores = float(e["C5Z_MEM"]), e["C5Z_PART"], int(e["C5Z_CORES"])
recs = {}
for f in glob.glob(os.path.join(V, "bench_L*.json")):
    m = re.fullmatch(r"bench_L([1-9][0-9]*)\.json", os.path.basename(f))
    if m:
        recs[int(m.group(1))] = f
cand = sorted(Lb for Lb in recs if Lb >= L)
if e["C5Z_BENCH_L"]:
    Lb = int(e["C5Z_BENCH_L"])
    if Lb not in cand:
        sys.exit(f"sizing: C5_BENCH_L={Lb} has no record with Lmax >= {L} in {V} (records: {sorted(recs)})")
elif cand:
    Lb = cand[-1]
else:
    sys.exit(f"sizing: no benchmark record bench_L<Lb>.json with Lb >= {L} in {V} (records: {sorted(recs)})")
with open(recs[Lb]) as fh:
    rec = json.load(fh)
if rec.get("snapshot_sha") != sha or int(rec.get("Lmax", -1)) != Lb:
    sys.exit(f"sizing: {recs[Lb]} names snapshot {rec.get('snapshot_sha')!r} / Lmax {rec.get('Lmax')!r}")
import subprocess
wspec = subprocess.run([sys.executable, os.path.join(e["C5_ROOT"], "run5.py"), "worstspec", "--Lmax", str(Lb)],
                       capture_output=True, text=True, check=True).stdout.strip()
runs = [r for r in rec.get("runs", []) if int(r["block"]) >= blk and r.get("worst_case") is True
        and r.get("spec_sha") == wspec]
if not runs:
    sys.exit(f"sizing: {recs[Lb]} has no run of the designated worst-case task (spec_sha {wspec[:12]}) with block >= {blk}")
peak = max(float(r["peak_rss_GB"]) for r in runs)
need, limit, T = 2 * wps * peak, 0.85 * mem, cores // wps
ok = need <= limit
print(f"sizing: record {recs[Lb]} (Lmax {Lb} for requested {L}; {len(runs)} run(s) with block >= {blk}, jobs "
      f"{sorted({str(r.get('job')) for r in runs})}): peak_rss_GB {peak:.3f}")
print(f"sizing: need 2 x {wps} workers x {peak:.3f} = {need:.1f} GB vs limit 0.85 x {mem:.0f} GB = {limit:.1f} GB on {part}"
      f" (max WPS {int(limit // (2 * peak))}) -> {'OK' if ok else 'REFUSED'}")
if T > max(int(r["threads"]) for r in runs):
    print(f"sizing: WARNING {T} threads/worker exceed the benchmarked {max(int(r['threads']) for r in runs)}")
sys.exit(0 if ok else 1)
PY
}
case ${1:-} in
  validate)
    P=$(pick_part "${2:-}")
    [[ ! -e $V/PASS ]] || die "validation PASS exists for snapshot $C5_EXPECT_SHA ($V/PASS); remove it by hand to re-validate"
    nolive l1c5-validate
    export C5_VAL_WPS=${C5_VAL_WPS:-2} C5_VAL_BLOCK=${C5_VAL_BLOCK:-8}
    [[ $C5_VAL_WPS =~ ^[1-9][0-9]*$ && $C5_VAL_BLOCK =~ ^[1-9][0-9]*$ ]] || die "bad C5_VAL_WPS/C5_VAL_BLOCK"
    (( C5_VAL_WPS <= $(corefor "$P") )) || die "C5_VAL_WPS=$C5_VAL_WPS > $(corefor "$P") cores per socket on $P"
    check_c4ref
    survey "$P" 1
    jid=$(sbatch --parsable -p "$P" --job-name=l1c5-validate --mem="$(memfor "$P")" --time="$(timefor "$P" "${C5_VAL_TIME:-12:00:00}")" \
      --output="$C5_DATA/logs/%x_%j.out" --export=ALL "$C5_ROOT/slurm/validate.slurm") || die "sbatch failed"
    jid=${jid%%;*}
    echo "submitted validation $jid on $P (snapshot $C5_EXPECT_SHA; L80+L160 with $C5_VAL_WPS workers/socket, block $C5_VAL_BLOCK)"
    echo "logs: tail -f $C5_DATA/logs/l1c5-validate_$jid.out; per-part $C5_DATA/logs/run_L{80,160}_$jid/part{0,1}.log;" \
         "steps $V/{pytest,v1,v3,v7}.txt; gates $R/gates_L{80,160}.txt, $R/gatelogs_L{80,160}/" ;;
  bench)
    re_thr='^[1-9][0-9]*( [1-9][0-9]*)*$'; re_tasks='^([0-9]+|worst)( ([0-9]+|worst))*$'
    [[ ${2:-} =~ ^[1-9][0-9]*$ && ${3:-} =~ $re_thr ]] || die "usage: bench LMAX \"THREADS...\" [partition] (single spaces)"
    export C5_TASKS=${C5_TASKS:-worst} C5_BLOCK=${C5_BLOCK:-8}
    [[ $C5_TASKS =~ $re_tasks && $C5_BLOCK =~ ^[1-9][0-9]*$ ]] || die "bad C5_TASKS '$C5_TASKS' or C5_BLOCK '$C5_BLOCK'"
    { [[ -f $V/PRELIM ]] && has_sha "$V/PRELIM"; } || { [[ -f $V/PASS ]] && has_sha "$V/PASS"; } \
      || die "benchmarks need the preliminary validation $V/PRELIM (A1-A3, A6a-c) of snapshot $C5_EXPECT_SHA"
    P=$(pick_part "${4:-}")
    for T in $3; do (( T <= $(corefor "$P") )) || die "$T threads > $(corefor "$P") cores per socket on $P"; done
    nolive "l1c5-bench-L$2"
    export C5_LMAX=$2 C5_THREADS=$3
    survey "$P" 1
    jid=$(sbatch --parsable -p "$P" --job-name="l1c5-bench-L$2" --mem="$(memfor "$P")" --time="$(timefor "$P" "${C5_TIME:-08:00:00}")" \
      --output="$C5_DATA/logs/%x_%j.out" --export=ALL "$C5_ROOT/slurm/bench.slurm") || die "sbatch failed"
    jid=${jid%%;*}
    echo "submitted benchmark $jid on $P (Lmax $2, tasks '$C5_TASKS', threads '$3', block $C5_BLOCK); record $V/bench_L$2.json"
    echo "log: tail -f $C5_DATA/logs/l1c5-bench-L$2_$jid.out" ;;
  prod)
    [[ ${2:-} =~ ^[0-9]+$ && ${3:-} =~ ^[1-9][0-9]*$ && ${4:-} =~ ^[1-9][0-9]*$ && ${5:-} =~ ^[1-9][0-9]*$ ]] \
      || die "usage: prod LMAX NNODES WPS BLOCK [partition]"
    L=$2; NN=$3; WPS=$4; BLK=$5
    case $L in
      240) PREV=160; PP=80 ;;
      320) PREV=240; PP=160 ;;
      400) PREV=320; PP=240 ;;
      500) PREV=400; PP=320 ;;
      *) die "Lmax must be one of 240, 320, 400, 500 (the staged ladder; 80 and 160 are run by the validation job)" ;;
    esac
    P=$(pick_part "${6:-}"); PA=${C5_ASM_PART:-$P}; check_part "$PA"
    (( WPS <= $(corefor "$P") )) || die "WPS=$WPS > $(corefor "$P") cores per socket on $P"
    { [[ -f $V/PASS ]] && has_sha "$V/PASS"; } || die "no validation PASS for snapshot $C5_EXPECT_SHA"
    { [[ -f $V/A9_APPROVED ]] && has_sha "$V/A9_APPROVED"; } \
      || die "Lmax $L > 160 needs $V/A9_APPROVED (Codex inspection of this snapshot)"
    check_gate "$PP" "$PREV"
    check_c4ref
    size_check "$L" "$WPS" "$BLK" "$P" || die "refused by the memory sizing rule (or no usable benchmark record)"
    [[ ! -e $R/c5_1d_L$L.npz && ! -e $R/gates_L$L.txt ]] || die "result or gate record for Lmax $L exists in $R"
    nolive "l1c5-L$L"; nolive "l1c5-L$L-asm"
    export C5_LMAX=$L C5_NNODES=$NN C5_WPS=$WPS C5_BLOCK=$BLK C5_PREV=$PREV
    survey "$P" "$NN"
    jid=$(sbatch --parsable -p "$P" --job-name="l1c5-L$L" --array="0-$(( NN - 1 ))" --mem="$(memfor "$P")" \
      --time="$(timefor "$P" "${C5_TIME:-24:00:00}")" --output="$C5_DATA/logs/%x_%A_%a.out" --export=ALL \
      "$C5_ROOT/slurm/node.slurm") || die "sbatch failed"
    jid=${jid%%;*}
    aid=$(sbatch --parsable -p "$PA" --job-name="l1c5-L$L-asm" --dependency="afterok:$jid" --kill-on-invalid-dep=yes \
      --mem="$(memfor "$PA")" --time="$(timefor "$PA" "${C5_ASM_TIME:-04:00:00}")" --output="$C5_DATA/logs/%x_%j.out" \
      --export=ALL "$C5_ROOT/slurm/assemble.slurm") || { scancel "$jid" || true; die "sbatch (assemble) failed; array $jid cancelled"; }
    aid=${aid%%;*}
    echo "submitted array $jid (Lmax $L, $NN node(s) on $P, $WPS workers/socket, block $BLK) + assemble $aid on $PA (A6d vs L$PREV)"
    echo "logs: tail -f $C5_DATA/logs/l1c5-L${L}_${jid}_<i>.out; per-part $C5_DATA/logs/run_L${L}_${jid}/part<k>.log;" \
         "assembly $C5_DATA/logs/l1c5-L$L-asm_$aid.out; gates $R/gates_L$L.txt, $R/gatelogs_L$L/" ;;
  assemble)
    [[ ${2:-} =~ ^[0-9]+$ ]] || die "usage: assemble LMAX [partition]"
    L=$2
    case $L in
      240) PREV=160; PP=80 ;;
      320) PREV=240; PP=160 ;;
      400) PREV=320; PP=240 ;;
      500) PREV=400; PP=320 ;;
      *) die "Lmax must be one of 240, 320, 400, 500 (80 and 160 belong to the validation job)" ;;
    esac
    PA=$(pick_part "${3:-}")
    { [[ -f $V/PASS ]] && has_sha "$V/PASS"; } || die "no validation PASS for snapshot $C5_EXPECT_SHA"
    { [[ -f $V/A9_APPROVED ]] && has_sha "$V/A9_APPROVED"; } || die "needs $V/A9_APPROVED"
    check_gate "$PP" "$PREV"
    check_c4ref
    nolive "l1c5-L$L"; nolive "l1c5-L$L-asm"
    [[ ! -e $R/gates_L$L.txt ]] || die "gate record $R/gates_L$L.txt exists: the rung is complete (remove by hand to redo)"
    if [[ -e $R/c5_1d_L$L.npz ]]; then
      psha=$(python -c 'import json,sys,numpy as np; print(json.loads(str(np.load(sys.argv[1])["provenance"]))["snapshot_sha"])' \
        "$R/c5_1d_L$L.npz") || die "cannot read the provenance of the orphan $R/c5_1d_L$L.npz"
      [[ $psha == "$C5_EXPECT_SHA" ]] || die "orphan $R/c5_1d_L$L.npz names snapshot $psha, not this one"
      mkdir -p "$R/orphan"; ts=$(date +%Y%m%dT%H%M%S)
      mv "$R/c5_1d_L$L.npz" "$R/orphan/c5_1d_L$L.npz.$ts" || die "cannot move the orphan aside"
      echo "orphan result moved to $R/orphan/c5_1d_L$L.npz.$ts"
    fi
    export C5_LMAX=$L C5_PREV=$PREV
    aid=$(sbatch --parsable -p "$PA" --job-name="l1c5-L$L-asm" --mem="$(memfor "$PA")" \
      --time="$(timefor "$PA" "${C5_ASM_TIME:-04:00:00}")" --output="$C5_DATA/logs/%x_%j.out" --export=ALL \
      "$C5_ROOT/slurm/assemble.slurm") || die "sbatch (assemble) failed"
    aid=${aid%%;*}
    echo "submitted recovery assembly $aid (Lmax $L on $PA, A6d vs L$PREV); log $C5_DATA/logs/l1c5-L$L-asm_$aid.out" ;;
  *) die "usage: $0 validate [partition] | bench LMAX \"THREADS...\" [partition] | prod LMAX NNODES WPS BLOCK [partition] | assemble LMAX [partition]" ;;
esac
