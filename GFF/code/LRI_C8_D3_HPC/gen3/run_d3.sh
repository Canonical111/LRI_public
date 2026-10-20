#!/bin/bash
# gen3/run_d3.sh: the d=3 payload pipeline (PLAN.md components A.2 and A.3; C63d's part of H1).
#
#   gen3/run_d3.sh --pre-h1 --d2 DIR --evidence DIR --work DIR [--threads N] [--bin-dir DIR]
#       J-GEN-D3-0 (Stage 1a, gate 1(a), A-INV-2(a)): gates_d3.py gate1a on C7(2)'s frozen d=2 payloads in DIR
#       ($C8_STORE/c7d2_frozen): every one of the 3,512 C7(3) payloads reproduced byte for byte.
#   gen3/run_d3.sh --h1 DIR --pin SHA256 --d2 DIR --evidence DIR --work DIR --target DIR --source DIR --source-before FILE
#                  [--threads N] [--bin-dir DIR] [--commit SHA]
#       J-GEN-D3 (Stage 1b) on the verified H1 copy DIR ($C8_STORE/h1/<sha12>, made by `gates_d3.py h1-copy`):
#         verify     the copy's code authenticated by this package (gates_d3.py h1-auth, S4-001: MANIFEST.json at --pin,
#                    SHA256SUMS at the MANIFEST, every file under src/ at SHA256SUMS, nothing unlisted) and snapshotted
#                    into $WORK/h1gen/src; then H1's own verify_inventory.py --pin, run from that snapshot (A.2 step 1)
#         extract    the four payload tars into node-local scratch (step 2)
#         builders   the snapshot re-checked (h1-auth --check); H1's pinned builders rebuilt from it with its Makefile,
#                    run as run_l8.sh:37-44, and H1's `publish_inventory.py members` on their stage: the gate-5 side
#                    files (step 2a). Nothing of the H1 copy runs before it is authenticated.
#         probe      gen3's size_probe on classes{7,8}.txt (sizes for gate 2, masks for gate 5 (e))
#         regen      regenerate_rates on every finite L7 and L8 kernel at N threads, then again as N single-thread
#                    processes (A.4), and the rate audits (step 3)
#         gate1b gate2 gate3 gate4 gate5 gate7 determinism   (step 4; every gate is hard)
#         publish    d3_payload/ at --target, only after every gate exited 0 (step 5): the gate records and their
#                    supporting records of $EV/gates under gates/, the four builder side files under gates/gate5/
#         verify_d3  gen3/verify_d3.py --pin <sha256 of MANIFEST_d3.json> (step 6; the pin is printed and recorded for
#                    the A.5 gate record)
#         source     C62d's source tree unchanged since the intake (A-INV-6)
#       Gate 7 reads the package's inputs/two_loop.json, inputs/order7/two_loop.json and inputs/gamma_d3_8.txt, which
#       Stage 2a writes (check_dimension8.py's defaults): J-GEN-D3 runs on a commit after G2a.
# On Expanse, J-GEN-D3 runs this through slurm/gen_d3.sh (D.10 preamble; C8_SCRATCH computed inside the job).
# Every output, scratch, staging and evidence path is refused under C62d's trees (g3common.refuse_c62d).
# Failure propagation (C8(1) R10/R11/R15): set -euo pipefail; every step in the foreground (background shards are
# each `wait`ed by pid); no "|| echo"; no process substitution. On Expanse it runs inside a Slurm job only (HD15).
# Test hooks (gen3/test_gen3.py only), honoured only with C8_SITE=fake and C8_GEN3_TEST_HOOKS=1:
# C8_GEN3_STEP_<name> (a shell command) replaces step <name>.
set -euo pipefail

GEN3=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PKG=$(dirname "$GEN3")
PY=${C8_PYTHON:-python3}
HOOKS=0
if [ "${C8_SITE:-}" = fake ] && [ "${C8_GEN3_TEST_HOOKS:-0}" = 1 ]; then HOOKS=1; fi

die() { echo "run_d3.sh: $*" >&2; exit 64; }
sha256s() {  # sha256s DIR NAME...: "<sha256>  NAME" rows (portable: no sha256sum on macOS)
  "$PY" -B -c 'import hashlib, sys, os; [print(hashlib.sha256(open(os.path.join(sys.argv[1], n), "rb").read()).hexdigest() + "  " + n) for n in sys.argv[2:]]' "$@"
}
stamp() { echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"; }

MODE= ; D2= ; EV= ; WORK= ; THREADS= ; BIN= ; H1= ; PIN= ; TARGET= ; SOURCE= ; BEFORE= ; COMMIT=
while [ $# -gt 0 ]; do
  case "$1" in
    --pre-h1) MODE=pre; shift ;;
    --h1) MODE=h1; H1=${2:?--h1 DIR}; shift 2 ;;
    --pin) PIN=${2:?}; shift 2 ;;
    --d2) D2=${2:?}; shift 2 ;;
    --evidence) EV=${2:?}; shift 2 ;;
    --work) WORK=${2:?}; shift 2 ;;
    --threads) THREADS=${2:?}; shift 2 ;;
    --bin-dir) BIN=${2:?}; shift 2 ;;
    --target) TARGET=${2:?}; shift 2 ;;
    --source) SOURCE=${2:?}; shift 2 ;;
    --source-before) BEFORE=${2:?}; shift 2 ;;
    --commit) COMMIT=${2:?}; shift 2 ;;
    *) die "unknown argument $1" ;;
  esac
done
[ -n "$MODE" ] || die "--pre-h1 or --h1 DIR is required"
[ -n "$D2" ] && [ -n "$EV" ] && [ -n "$WORK" ] || die "--d2, --evidence and --work are required"
if [ -d /expanse ] && [ -z "${SLURM_JOB_ID:-}" ] && [ "$HOOKS" != 1 ]; then
  die "on Expanse this runs inside a Slurm job only (HD15: the login node only submits, queries and copies)"
fi
THREADS=${THREADS:-${SLURM_CPUS_PER_TASK:-$(getconf _NPROCESSORS_ONLN)}}
case "$THREADS" in ''|*[!0-9]*|0) die "--threads $THREADS is not a positive integer" ;; esac
BIN=${BIN:-$PKG/bin/gen3}
COMMIT=${COMMIT:-${C8_PACKAGE_COMMIT:-$(basename "$PKG")}}
# Refuse every path this script writes under C62d's trees (A.2 step 0).
"$PY" -B -c 'import sys; sys.path.insert(0, sys.argv[1]); import g3common as c; [c.refuse_c62d(p, w) for w, p in zip(sys.argv[2::2], sys.argv[3::2]) if p]' \
  "$GEN3" "evidence directory" "$EV" "scratch directory" "$WORK" "publication target" "$TARGET"
mkdir -p "$EV"

run_step() {  # run_step NAME FUNCTION
  local cmd="" var="C8_GEN3_STEP_$1"
  if [ "$HOOKS" = 1 ]; then cmd=${!var:-}; fi
  stamp "step $1: start"
  if [ -n "$cmd" ]; then bash -c "$cmd"; else "$2"; fi
  stamp "step $1: exit 0"
}

# ---- --pre-h1: gate 1(a) -----------------------------------------------------------------------------------------
step_gate1a() {
  "$PY" -B "$GEN3/gates_d3.py" gate1a --d2 "$D2" --bin "$BIN/regenerate_rates" --work "$WORK/gate1a" \
    --evidence "$EV" --threads "$THREADS"
}
if [ "$MODE" = pre ]; then
  [ -x "$BIN/regenerate_rates" ] || die "$BIN/regenerate_rates is missing: run make gen3 first"
  run_step gate1a step_gate1a
  stamp "gate 1(a) passed: $EV/gate1a.json"
  exit 0
fi

# ---- --h1: J-GEN-D3 ----------------------------------------------------------------------------------------------
[ -n "$PIN" ] && [ -n "$TARGET" ] && [ -n "$SOURCE" ] && [ -n "$BEFORE" ] || die "--h1 needs --pin, --target, --source and --source-before"
case "$PIN" in *[!0-9a-f]*|'') die "--pin is not a sha256" ;; esac
[ ${#PIN} -eq 64 ] || die "--pin is not a sha256"
if [ "$HOOKS" != 1 ] && [ "$(uname -m)" != x86_64 ]; then
  die "J-GEN-D3 runs on x86-64 only (H1's builders print long doubles; the gate-5 regeneration must match their tree)"
fi
[ -e "$TARGET" ] && die "$TARGET exists (a published tree is frozen)"
G="$EV/gates"
CLASSES="$PKG/reference/c8d1_inputs8"
STEMS="L7_free L7_power L8_free L8_power"
mkdir -p "$G" "$WORK"

step_verify() {
  rm -rf "$WORK/h1gen/src"
  "$PY" -B "$GEN3/gates_d3.py" h1-auth --tree "$H1" --pin "$PIN" --snapshot "$WORK/h1gen/src" --evidence "$EV"
  "$PY" -B "$WORK/h1gen/src/verify_inventory.py" "$H1" --pin "$PIN" --output "$EV/verify_inventory_jgen.json"
}
step_extract() {
  local stem
  mkdir -p "$WORK/h1"
  for stem in $STEMS; do tar -xf "$H1/payload/$stem.tar" -C "$WORK/h1"; done
}
step_builders() {
  local L sector cxx
  mkdir -p "$WORK/regen" "$EV/side" "$EV/h1gen_build"
  "$PY" -B "$GEN3/gates_d3.py" h1-auth --tree "$H1" --pin "$PIN" --snapshot "$WORK/h1gen/src" --check --evidence "$EV" \
    --name h1_code_auth_builders
  cxx=${H1_CXX:-$(command -v g++)}
  env -u CXXFLAGS -u OPTFLAGS make -C "$WORK/h1gen/src" BIN="$WORK/h1gen/bin" CXX="$cxx"
  for L in 7 8; do
    for sector in free power; do
      OMP_NUM_THREADS=$THREADS "$WORK/h1gen/bin/build_$sector" "$CLASSES/classes$L.txt" \
        "$WORK/regen/L${L}_$sector" "$WORK/regen/L${L}_$sector.subgraphs.txt"
      cp "$WORK/regen/L${L}_$sector.subgraphs.txt" "$EV/side/"
    done
  done
  "$PY" -B "$WORK/h1gen/src/publish_inventory.py" members --stage "$WORK/regen" --output "$EV/regen_MEMBERS.sha256" \
    --inventories "$EV/regen_inv" --jobs "$THREADS"
  cp "$WORK"/h1gen/bin/*.build.txt "$EV/h1gen_build/"
  sha256s "$WORK/h1gen/bin" build_free build_power check_edge_forests > "$EV/h1gen_build/binaries.sha256"
}
step_probe() {
  local L
  mkdir -p "$WORK/probe" "$EV/probe"
  for L in 7 8; do
    OMP_NUM_THREADS=$THREADS "$BIN/size_probe" "$CLASSES/classes$L.txt" "$WORK/probe/masks_L$L.txt" > "$WORK/probe/sizes_L$L.csv"
    cp "$WORK/probe/sizes_L$L.csv" "$EV/probe/"
  done
}
step_regen() {
  local stem f k pids=() pid
  mkdir -p "$WORK/d3" "$WORK/d3_one" "$WORK/shards" "$EV/audits"
  : > "$WORK/jobs_n.txt"
  : > "$WORK/jobs_one.txt"
  for stem in $STEMS; do
    mkdir -p "$WORK/d3/$stem" "$WORK/d3_one/$stem"
    for f in "$WORK/h1/$stem"/G*.txt; do
      echo "$f $WORK/d3/$stem/$(basename "$f")" >> "$WORK/jobs_n.txt"
      echo "$f $WORK/d3_one/$stem/$(basename "$f")" >> "$WORK/jobs_one.txt"
    done
  done
  OMP_NUM_THREADS=$THREADS "$BIN/regenerate_rates" "$WORK/jobs_n.txt" > "$WORK/audit_n.json"
  "$PY" -B "$GEN3/gates_d3.py" split-audit --audit "$WORK/audit_n.json" --stage "$WORK/d3" --out "$EV/audits"
  # A.4: the same regeneration with OMP_NUM_THREADS=1, as THREADS single-thread processes over shards of the list.
  awk -v n="$THREADS" -v d="$WORK/shards" '{ f = sprintf("%s/s%05d", d, (NR - 1) % n); print > f }' "$WORK/jobs_one.txt"
  for k in "$WORK"/shards/s*; do
    [ -s "$k" ] || continue
    OMP_NUM_THREADS=1 "$BIN/regenerate_rates" "$k" > "$k.json" 2> "$k.err" &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
}
step_gate1b() { "$PY" -B "$GEN3/gates_d3.py" gate1b --h1 "$WORK/h1" --d3 "$WORK/d3" --d2 "$D2" --evidence "$G"; }
step_gate2() {
  "$PY" -B "$GEN3/gates_d3.py" gate2 --d3 "$WORK/d3" --inventory "$H1" --sizes "$WORK/probe" --classes "$CLASSES" --evidence "$G"
}
step_gate3() { "$PY" -B "$GEN3/gates_d3.py" gate3 --bin "$WORK/h1gen/bin" --d3 "$WORK/d3" --classes "$CLASSES" --evidence "$G"; }
step_gate4() { "$PY" -B "$GEN3/gates_d3.py" gate4 --d3 "$WORK/d3" --inventory "$H1" --evidence "$G"; }
step_gate5() {
  "$PY" -B "$GEN3/gates_d3.py" gate5 --inventory "$H1" --h1gen "$WORK/h1gen" --regen "$EV" --side "$EV/side" \
    --classes "$CLASSES" --probe "$WORK/probe" --evidence "$G"
  rm -rf "$WORK/regen"   # the regenerated G-files (about 8.3 GB) after gate 5 (b) compared them
}
step_gate7() { "$PY" -B "$GEN3/gates_d3.py" gate7 --audits "$EV/audits" --h1 "$WORK/h1" --d3 "$WORK/d3" --evidence "$G"; }
step_determinism() {
  "$PY" -B "$GEN3/gates_d3.py" determinism --a "$WORK/d3" --b "$WORK/d3_one" --threads "$THREADS and 1" --evidence "$G"
}
step_publish() {
  "$PY" -B "$GEN3/publish_d3.py" --stage "$WORK/d3" --gates "$G" --side "$EV/side" --audits "$EV/audits" --target "$TARGET" \
    --h1-pin "$PIN" --commit "$COMMIT" --compiler-record "$BIN/regenerate_rates.build.txt"
}
step_verify_d3() {
  local pin
  pin=$(sha256s "$TARGET" MANIFEST_d3.json | cut -d' ' -f1)
  echo "$pin" > "$EV/MANIFEST_d3.sha256"
  "$PY" -B "$GEN3/verify_d3.py" "$TARGET" --pin "$pin" --output "$EV/verify_d3.json"
  stamp "MANIFEST_d3.json sha256 (the external pin of A.5): $pin"
}
step_source() {
  "$PY" -B "$GEN3/gates_d3.py" source-unchanged --source "$SOURCE" --before "$BEFORE" --evidence "$EV" --name h1_source_after_jgen
}

for s in verify extract builders probe regen gate1b gate2 gate3 gate4 gate5 gate7 determinism publish verify_d3 source; do
  run_step "$s" "step_$s"
done
stamp "J-GEN-D3 complete: $TARGET"
