#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-gen3-crossnode
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# A-INV-4 on Expanse (site deviation U1; the symmetry script is slurm/gen/crossnode.slurm, an Intel debugq node at 40
# threads): the L7+L8 build repeated on a second, different compute node at C8_XNODE_THREADS threads (default 64,
# against J-GEN-2's 128) into a scratch directory; its MEMBERS.sha256 and builder inventories must be byte-identical
# to J-GEN-2's tree. Expanse compute nodes are all AMD EPYC 7742, so this is a node and thread-count check, not an
# architecture check; the symmetry Intel run adds that later. The job refuses to pass on the reference's own host.
# Submit after J-GEN-2 has started, excluding its node, and after it succeeded:
#   C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_GEN_REFERENCE=<J-GEN-2 tree> \
#     sbatch --export=ALL --dependency=afterok:<J-GEN-2 job> --exclude=<J-GEN-2 node> slurm/gen/expanse_crossnode.slurm
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
# Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control (OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_*,
# KMP_* from a module or the submitting shell) reaches the generator programs; each gets OMP_NUM_THREADS explicitly.
for v in $(compgen -e); do case "$v" in OMP_*|GOMP_*|KMP_*) unset "$v";; esac; done
export OMP_DYNAMIC=FALSE
: "${C8_PACKAGE:?}" "${C8_GEN_REFERENCE:?}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RUN=gen3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN
W=$C8_DATA/gen/$TAG/$RUN
mkdir -p "$(dirname "$E")" "$(dirname "$W")"
mkdir "$E" "$W"
trap 'rm -rf "$W/stage"' EXIT
echo "job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) at $(date -Is); evidence $E; work $W"
lscpu | grep -E 'Model name|^CPU\(s\)|NUMA node\(s\)|Thread\(s\) per core'
g++ --version | head -1
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
THREADS=${C8_XNODE_THREADS:-64}
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
python3 - "$E" "$C8_GEN_REFERENCE" "$status" "$THREADS" <<'PY'
import hashlib, json, socket, sys
from pathlib import Path
e, ref, status, threads = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
cpu = next((l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')), None)
man = json.loads((ref / 'MANIFEST.json').read_bytes())
host = socket.gethostname()
different = host != man.get('host')
rec = dict(schema='c8-d2-gate-1', gate='A-INV-4 crossnode', site='expanse', passed=status == 0 and different,
           host=host, cpu=cpu, threads=threads, reference_host=man.get('host'), reference_cpu=man.get('cpu'),
           reference_threads=man.get('threads'), reference_jobs=man.get('slurm_job_ids'), different_node=different,
           members_sha256=h(e / 'MEMBERS.sha256'), reference_members_sha256=h(ref / 'MEMBERS.sha256'),
           members_lines=sum(1 for _ in open(e / 'MEMBERS.sha256')),
           inventories_identical={f'L{L}': h(e / f'inventories/inventory_L{L}.json') == h(ref / f'inventory_L{L}.json')
                                  for L in (7, 8)}, reference=str(ref),
           scope='a second Expanse compute node (same CPU model, different thread count); the architecture '
                 'cross-check (symmetry Intel debugq, 40 threads, PLAN J-GEN-3) is pending: symmetry compute is down')
(e / 'crossnode.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(rec, indent=1))
sys.exit(0 if rec['passed'] else 1)
PY
