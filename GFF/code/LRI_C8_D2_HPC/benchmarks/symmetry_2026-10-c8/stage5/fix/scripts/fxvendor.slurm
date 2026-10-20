#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=6G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# F5 on real Slurm: the CPU-vendor pin refuses a claim from another vendor. C8_RUN is the A-ORC-13 campaign of
# fxio.slurm, whose first claims ran on an AMD amddebugq node and pinned RUN/cpu_vendor.json to AuthenticAMD. This job
# runs on sharedq, an Intel node, and expects:
#   1. `production.py run RUN --index IDX` (an index fxio never ran) to stop before any block with exit 64 and a message
#      naming both vendors; no checkpoint of that index, nothing else in the campaign changed (listing before/after);
#   2. `lanes.py worker RUN` (the lane worker, as slurm/lane_worker.sh execs it) to refuse with 64 before any claim
#      (no lanes/claims entry);
#   3. `production.py status RUN --fast` to print the pin.
# Usage: C8_PACKAGE=... C8_RUN=... IDX=... sbatch --export=ALL -J c8d2-fxvendor fxvendor.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${IDX:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=fxvendor.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; run $C8_RUN; index $IDX; evidence $E"
grep -m1 -E 'vendor_id' /proc/cpuinfo | tee "$E/node_vendor.txt"; grep -m1 'model name' /proc/cpuinfo | tee -a "$E/node_vendor.txt"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
cp "$C8_RUN/cpu_vendor.json" "$E/cpu_vendor.json"; cat "$E/cpu_vendor.json"
listing() { (cd "$C8_RUN" && find . -path ./lanes/logs -prune -o -type f -printf '%p %s %T@\n' | sort); }
listing > "$E/listing_before.txt"
status=0
python3 -B "$C8_PACKAGE/tools/production.py" run "$C8_RUN" --index "$IDX" --threads 2 > "$E/run.log" 2>&1; c=$?
echo "production.py run --index $IDX exit $c (expected 64)"; grep -E '^C8: index|claim_io' "$E/run.log" | cut -c1-600
[ $c -eq 64 ] || status=1
python3 -B "$C8_PACKAGE/tools/lanes.py" worker "$C8_RUN" > "$E/worker.log" 2>&1; w=$?
echo "lanes.py worker exit $w (expected 64)"; tail -3 "$E/worker.log" | cut -c1-600
[ $w -eq 64 ] || status=1
listing > "$E/listing_after.txt"
if cmp -s "$E/listing_before.txt" "$E/listing_after.txt"; then echo "campaign unchanged (every file, size and mtime)"; else echo "campaign CHANGED:"; diff "$E/listing_before.txt" "$E/listing_after.txt" | head -20; status=1; fi
ls "$C8_RUN/lanes/claims" 2>/dev/null | head; ls "$C8_RUN/groups"/*/checkpoints 2>/dev/null | grep -c json | sed 's/^/checkpoints: /'
python3 -B "$C8_PACKAGE/tools/production.py" status "$C8_RUN" --fast > "$E/status.txt" 2>&1; echo "status exit $? (1 expected: incomplete)"; grep -i 'cpu vendor' "$E/status.txt"
grep -qi 'cpu vendor: AuthenticAMD' "$E/status.txt" || { echo "status does not print the AMD pin"; status=1; }
python3 - "$E" "$c" "$w" "$status" <<'PY'
import json,sys
from pathlib import Path
E=Path(sys.argv[1]);run=(E/'run.log').read_text();wk=(E/'worker.log').read_text()
rec={'node_vendor':(E/'node_vendor.txt').read_text().strip(),'pin':json.loads((E/'cpu_vendor.json').read_text()),
     'run_exit':int(sys.argv[2]),'run_message':[l for l in run.splitlines() if l.startswith('C8: index')],
     'run_claim_io':[json.loads(l[9:]) for l in run.splitlines() if l.startswith('claim_io ')],
     'worker_exit':int(sys.argv[3]),'worker_tail':wk.splitlines()[-3:],
     'campaign_unchanged':(E/'listing_before.txt').read_text()==(E/'listing_after.txt').read_text(),
     'status_pin_lines':[l for l in (E/'status.txt').read_text().splitlines() if 'cpu vendor' in l.lower()],
     'passed':sys.argv[4]=='0'}
(E/'vendor_refusal.json').write_text(json.dumps(rec,indent=1)+'\n')
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
