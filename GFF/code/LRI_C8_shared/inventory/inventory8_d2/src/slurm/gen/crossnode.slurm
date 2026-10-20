#!/bin/bash
#SBATCH -p debugq -N 1 -n 1 --exclusive --mem=180G -t 01:00:00
#SBATCH -J c8d2-gen3-crossnode
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# J-GEN-3 (PLAN.md Verification, A-INV-4): the L7+L8 build repeated on an Intel debugq node at 40 threads into a
# scratch directory; its MEMBERS.sha256 must be byte-identical to that of the 64-thread AMD build (and so must the
# builder inventories).
#   C8_PACKAGE=/mnt/beegfs/zzheng1/c8d2/pkg/<sha12> C8_GEN_REFERENCE=<frozen tree from J-GEN-2> \
#     sbatch --export=ALL slurm/gen/crossnode.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_GEN_REFERENCE:?}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RUN=gen3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=/mnt/beegfs/zzheng1/c8d2/evidence/$TAG/$RUN
W=/mnt/beegfs/zzheng1/c8d2/gen/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"
mkdir "$E" "$W"
trap 'rm -rf "$W/stage"' EXIT
echo "job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) at $(date -Is); evidence $E; work $W"
lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)|Thread\(s\) per core'
g++ --version | head -1
THREADS=40
make -C "$C8_PACKAGE/gen" BIN="$W/bin"
cp "$W"/bin/*.build.txt "$E"/
mkdir "$W/stage"
for L in 7 8; do
  for sector in free power; do
    t0=$(date +%s)
    OMP_NUM_THREADS=$THREADS "$W/bin/build_$sector" "$C8_PACKAGE/reference/c8d1_inputs8/classes$L.txt" \
      "$W/stage/L${L}_$sector" "$W/stage/L${L}_$sector.subgraphs.txt"
    echo "built L$L $sector in $(( $(date +%s) - t0 )) s"
  done
done
python3 -B "$C8_PACKAGE/gen/publish_inventory.py" members --stage "$W/stage" --output "$E/MEMBERS.sha256" \
  --inventories "$E/inventories" --jobs "$THREADS"
status=0
if cmp "$E/MEMBERS.sha256" "$C8_GEN_REFERENCE/MEMBERS.sha256"; then echo "MEMBERS.sha256 identical"; else status=1; fi
for L in 7 8; do
  if cmp "$E/inventories/inventory_L$L.json" "$C8_GEN_REFERENCE/inventory_L$L.json"; then
    echo "inventory_L$L.json identical"
  else
    status=1
  fi
done
python3 - "$E" "$C8_GEN_REFERENCE" "$status" <<'PY'
import hashlib, json, socket, sys
from pathlib import Path
e, ref, status = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
cpu = next((l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')), None)
rec = dict(schema='c8-d2-gate-1', gate='A-INV-4 crossnode', passed=status == 0, host=socket.gethostname(), cpu=cpu,
           threads=40, members_sha256=h(e / 'MEMBERS.sha256'), reference_members_sha256=h(ref / 'MEMBERS.sha256'),
           members_lines=sum(1 for _ in open(e / 'MEMBERS.sha256')),
           inventories_identical={f'L{L}': h(e / f'inventories/inventory_L{L}.json') == h(ref / f'inventory_L{L}.json')
                                  for L in (7, 8)}, reference=str(ref))
(e / 'crossnode.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
PY
exit $status
