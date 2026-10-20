#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=8G -t 00:45:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# X8 (Stage-6 fix round 1) on real Slurm: the campaign's runtime compatibility identity (RUN/runtime_identity.json:
# glibc, the ELF interpreter's and every ldd-resolved library's sha256; not the host, the Slurm ids or the CPU model) is
# pinned by the first claim and enforced by every later claim, by run-skip and by both merges. A tiny test-only campaign
# (one graph per group, 256 points, two replicates (plan's minimum), one index per group; never a scientific result) in the export built
# by s1build.slurm; sharedq (Intel nodes; the campaign's vendor pin is therefore Intel), outside the H7 AMD-pool cap.
# A different library stack is made real, not faked: a byte copy of the libgmp.so.10 that ldd resolves, with one zero
# byte appended (the loader ignores trailing bytes; its sha256 differs), first on LD_LIBRARY_PATH.
#   MODE=a (node n1): plan RUN (fresh seed, checked against $C8_SEEDS, added after the plan; ledger role plan);
#     a1 run --index 0: exit 0, the pin is published;
#     a2 run --index 1 under the other libgmp: exit 64 before any block ("runtime identity refused"), no checkpoint;
#     a3 run --index 0 under the other libgmp: exit 64 (the pin is checked before run-skip).
#   MODE=b (node n2 != n1, submitted with --exclude=n1 after a):
#     b1 run --index 1 with the node's own libraries: exit 0 (same identity, another host and Slurm job);
#     b2 every index (0 again: all blocks valid, run-skip accepts the other host's checkpoints); status exits 0;
#     b3 the pin-less resume path: the pin moved aside, run --index 0 under the other libgmp publishes that stack's pin and
#        then refuses its own checkpoint at run-skip ("another runtime library stack"); with that pin in place
#        `merge --jobs 2`, `merge --jobs 1` and `merge --serial` refuse; the original pin is restored (the other pin kept as evidence);
#     b4 merge --jobs 2 with the original pin: exit 0.
# Usage: C8_PACKAGE=... RUNDIR=<SCRATCH>/c8-d2/x8-<sha12> MODE=a SEED=<fresh> sbatch --export=ALL -J c8d2-s1x8a s1x8.slurm
#        C8_PACKAGE=... RUNDIR=... MODE=b sbatch --export=ALL --exclude=<n1> -J c8d2-s1x8b s1x8.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${RUNDIR:?}" "${MODE:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s1x8$MODE.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID mode $MODE on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $RUNDIR; evidence $E"
{ hostname; lscpu; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_INPUTS C8_ALLOW_NO_L8 LD_LIBRARY_PATH
cd "$C8_PACKAGE" || exit 64
P="python3 -B tools/production.py"
status=0
expect() {  # expect NAME CODE CMD... : run CMD, log to $E/NAME.log, record (name, wanted, got) in $E/steps.txt
  local name=$1 want=$2; shift 2; local t=$(date +%s)
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "$name want=$want got=$c $(( $(date +%s) - t ))s" | tee -a "$E/steps.txt"
  if [ "$want" = nonzero ]; then [ $c -ne 0 ] || status=1; else [ $c -eq "$want" ] || status=1; fi
  tail -2 "$E/$name.log" | cut -c1-400
}
ALT=$TMPDIR/altlib; mkdir -p "$ALT"
lib=$(ldd bin/c8d2_gmp | awk '/libgmp\.so/{print $3}'); [ -n "$lib" ] || { echo "no libgmp in ldd"; exit 3; }
cp "$lib" "$ALT/$(basename "$lib")"; printf '\0' >> "$ALT/$(basename "$lib")"
{ echo "original $lib"; sha256sum "$lib" "$ALT/$(basename "$lib")"; echo "ldd under LD_LIBRARY_PATH=$ALT:"; LD_LIBRARY_PATH=$ALT ldd bin/c8d2_gmp; } | tee "$E/altlib.txt"
sha256sum bin/c8d2_gmp tools/production.py tools/common.py "$HOME/c8d2/env.sh" | tee "$E/inputs.sha256"
pins() { for f in runtime_identity.json cpu_vendor.json; do [ -e "$RUNDIR/$f" ] && sha256sum "$RUNDIR/$f"; done; }
case $MODE in
a)
  : "${SEED:?}"
  test ! -e "$RUNDIR" || { echo "$RUNDIR exists; refusing"; exit 64; }
  python3 -B tools/seeds.py check "$SEED" > "$E/seed_check.txt" 2>&1 || { echo "seed $SEED refused"; cat "$E/seed_check.txt"; exit 65; }
  expect plan 0 $P plan "$RUNDIR" --pilot --test-graphs 1 --test-selection cheapest --points 256 --replicates 2 --threads 2 \
    --shards 1 --backend gmp --cost-model cost_models/gmp_symmetry_amd_c8.json --seed "$SEED"
  [ -e "$RUNDIR/manifest.json" ] || { echo "plan failed"; exit 3; }
  python3 -B tools/ledger.py register "$RUNDIR" --role plan > "$E/ledger_register.txt" 2>&1 || status=1
  python3 -B tools/seeds.py add --seed "$SEED" --label "Stage-6 fix round 1 X8 real-Slurm check ($RUNDIR; test-only, 256 points, never a result)" > "$E/seeds_add.txt" 2>&1 || status=66
  cp -p "$RUNDIR/manifest.json" "$E/manifest.json"
  expect a1_run_index0 0 $P run "$RUNDIR" --index 0 --threads 2
  pins | tee "$E/pins_after_a1.txt"; cp -p "$RUNDIR/runtime_identity.json" "$E/runtime_identity.json"
  before=$(find "$RUNDIR/groups" -name '*.json' -path '*checkpoints*' | sort | xargs sha256sum)
  expect a2_run_index1_otherlib 64 env LD_LIBRARY_PATH="$ALT" $P run "$RUNDIR" --index 1 --threads 2
  expect a3_run_index0_otherlib 64 env LD_LIBRARY_PATH="$ALT" $P run "$RUNDIR" --index 0 --threads 2
  after=$(find "$RUNDIR/groups" -name '*.json' -path '*checkpoints*' | sort | xargs sha256sum)
  if [ "$before" = "$after" ]; then echo "checkpoints unchanged by the refused claims" | tee -a "$E/steps.txt"; else echo "CHECKPOINTS CHANGED" | tee -a "$E/steps.txt"; status=1; fi
  grep -h "runtime identity\|run-time library" "$E"/a2_*.log "$E"/a3_*.log | cut -c1-600 | tee "$E/refusal_messages.txt"
  grep -h '^claim_io' "$E"/a2_*.log | cut -c1-400 > "$E/claim_io_refused.txt" || true
  pins | tee "$E/pins_after_a3.txt";;
b)
  test -e "$RUNDIR/runtime_identity.json" || { echo "no pin: run MODE=a first"; exit 64; }
  pins | tee "$E/pins_before.txt"
  n=$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['jobs']))" "$RUNDIR/manifest.json")
  expect b1_run_index1_samelib_otherhost 0 $P run "$RUNDIR" --index 1 --threads 2
  for i in $(seq 0 $((n-1))); do [ $i -eq 1 ] && continue; expect b2_run_index$i 0 $P run "$RUNDIR" --index $i --threads 2; done
  expect b2_status 0 $P status "$RUNDIR"
  pins | tee "$E/pins_after_b2.txt"; cmp -s "$E/pins_before.txt" "$E/pins_after_b2.txt" || { echo "PIN CHANGED"; status=1; }
  python3 - "$RUNDIR" > "$E/checkpoint_hosts.json" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); from common import runtime_identity_key
hosts = {}
for f in sorted(Path(sys.argv[1]).glob('groups/*/checkpoints/*.json')):
    rt = json.loads(f.read_text())['runtime']; fp = rt['fingerprint']
    hosts.setdefault(fp.get('host'), {'checkpoints': 0, 'runtime_keys': set(), 'jobs': set()})
    h = hosts[fp.get('host')]; h['checkpoints'] += 1; h['runtime_keys'].add(runtime_identity_key(fp)); h['jobs'].add((fp.get('slurm') or {}).get('SLURM_JOB_ID'))
print(json.dumps({k: {'checkpoints': v['checkpoints'], 'runtime_keys': sorted(v['runtime_keys']), 'jobs': sorted(map(str, v['jobs']))} for k, v in hosts.items()}, indent=1))
PY
  cat "$E/checkpoint_hosts.json"
  mv "$RUNDIR/runtime_identity.json" "$TMPDIR/runtime_identity.original.json"
  expect b3_run_index0_otherlib_nopin nonzero env LD_LIBRARY_PATH="$ALT" $P run "$RUNDIR" --index 0 --threads 2
  cp -p "$RUNDIR/runtime_identity.json" "$E/runtime_identity.otherlib.json" 2>/dev/null || echo "no pin published by b3"
  expect b3_merge_jobs2_otherpin nonzero $P merge "$RUNDIR" --jobs 2
  expect b3_merge_jobs1_otherpin nonzero $P merge "$RUNDIR" --jobs 1
  expect b3_merge_serial_otherpin nonzero $P merge "$RUNDIR" --serial
  grep -h "runtime library stack\|runtime identity" "$E"/b3_*.log | cut -c1-600 | tee "$E/refusal_messages_b3.txt"
  ls "$RUNDIR"/groups/*/merged.json > "$E/merged_after_b3.txt" 2>&1 && { echo "A MERGE PUBLISHED UNDER THE OTHER PIN"; status=1; }
  rm -f "$RUNDIR/runtime_identity.json"; mv "$TMPDIR/runtime_identity.original.json" "$RUNDIR/runtime_identity.json"
  pins | tee "$E/pins_restored.txt"; cmp -s "$E/pins_before.txt" "$E/pins_restored.txt" || { echo "PIN NOT RESTORED"; status=1; }
  expect b4_merge_jobs2 0 $P merge "$RUNDIR" --jobs 2
  ls "$RUNDIR"/groups/*/merged.json | wc -l | tee "$E/merged_count.txt"
  $P status "$RUNDIR" --json > "$E/status.json" 2>&1 || true;;
*) echo "MODE a or b"; exit 64;;
esac
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
