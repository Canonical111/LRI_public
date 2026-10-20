#!/bin/bash
#SBATCH -p debugq -N 1 -n 1 --exclusive --mem=180G -t 01:00:00
#SBATCH -J c8d2-jgen3
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-GEN-3 (PLAN.md Verification, A-INV-4) on a symmetry Intel debugq node at 40 threads.
# A wrapper around the package's own slurm/gen/crossnode.slurm, which runs unchanged from the git-archive export:
# make -C gen; build_free and build_power on classes7/classes8 at 40 threads into a BeeGFS scratch directory;
# publish_inventory.py members; cmp of MEMBERS.sha256 and of the builder inventories against the reference.
# Around it the wrapper:
#   1. precheck: the partial reference copy (MANIFEST.json, SHA256SUMS, MEMBERS.sha256, inventory_L7/L8.json) verifies
#      against the MANIFEST pin, and the export's builder sources and classes7/8 equal the MANIFEST's pins;
#   2. platform record: lscpu, OS, compiler (g++ -v), glibc, libgomp/libstdc++ packages, Python, env.sh hash;
#   3. after the build: builder binaries (sha256, ldd), then a member-by-member comparison of MEMBERS.sha256 and a
#      class-by-class comparison of the builder inventories (compare.json);
#   4. deletes the scratch build tree (crossnode.slurm already removes the stage; the builder binaries go too).
# Submit on the login node:
#   C8_PACKAGE=<SCRATCH>/c8d2/pkg/<sha12> C8_GEN_REFERENCE=<partial reference copy> C8_MANIFEST_PIN=<sha256> \
#     sbatch --export=ALL jgen3.slurm
set -euo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_GEN_REFERENCE:?}" "${C8_MANIFEST_PIN:?}"
[ "$(uname -m)" = x86_64 ] || { echo "refusing: x86-64 only" >&2; exit 64; }
TAG=$(basename "$C8_PACKAGE")
RC=${SLURM_RESTART_COUNT:-0}
E=<SCRATCH>/c8d2/evidence/$TAG/gen3.$SLURM_JOB_ID.$RC    # written by crossnode.slurm
W=<SCRATCH>/c8d2/gen/$TAG/gen3.$SLURM_JOB_ID.$RC         # crossnode.slurm's scratch build tree
P=<SCRATCH>/c8d2/evidence/$TAG/jgen3.$SLURM_JOB_ID.$RC   # this wrapper's records
mkdir -p "$(dirname "$P")"
mkdir "$P"
echo "jgen3: job $SLURM_JOB_ID restart $RC on $(hostname) at $(date -Is); records $P; crossnode evidence $E; scratch $W"
sha256sum "$0" "$HOME/c8d2/env.sh" "$C8_PACKAGE/slurm/gen/crossnode.slurm" | tee "$P/scripts.sha256"

# ---- 1. precheck -------------------------------------------------------------------------------------------------
python3 - "$C8_GEN_REFERENCE" "$C8_MANIFEST_PIN" "$C8_PACKAGE" "$P/precheck.json" <<'PY'
import hashlib, json, sys
from pathlib import Path
ref, pin, pkg, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
man = json.loads((ref / 'MANIFEST.json').read_bytes())
sums = {}
for line in (ref / 'SHA256SUMS').read_text().splitlines():
    hx, path = line.split('  ', 1)
    sums[path] = hx
files = {f: dict(sha256=h(ref / f), sha256sums=sums.get(f)) for f in ('MEMBERS.sha256', 'inventory_L7.json', 'inventory_L8.json')}
srcs = {k: dict(pin=v, export=h(pkg / k) if (pkg / k).exists() else None) for k, v in man['gen_sources_sha256'].items()}
classes = {k: dict(pin=v, export=h(pkg / 'reference/c8d1_inputs8' / k)) for k, v in man['classes_sha256'].items()}
used = ['gen/Makefile', 'gen/build_free.cpp', 'gen/build_power.cpp', 'gen/c8gen.hpp', 'gen/check_edge_forests.cpp',
        'gen/test_keys.cpp', 'gen/publish_inventory.py', 'slurm/gen/crossnode.slurm']
rec = dict(schema='c8-d2-jgen3-precheck-1', reference=str(ref), package=str(pkg),
           manifest_pin=pin, manifest_sha256=h(ref / 'MANIFEST.json'),
           sha256sums_sha256=h(ref / 'SHA256SUMS'), manifest_sha256sums_sha256=man['sha256sums_sha256'],
           reference_files=files,
           reference_ok=h(ref / 'MANIFEST.json') == pin and h(ref / 'SHA256SUMS') == man['sha256sums_sha256']
                        and all(v['sha256'] == v['sha256sums'] for v in files.values()),
           sources_used_by_this_job=used,
           sources_used_equal_pins=all(srcs[k]['pin'] == srcs[k]['export'] for k in used),
           sources_differing_from_pins=sorted(k for k, v in srcs.items() if v['pin'] != v['export']),
           classes_equal_pins={k: v['pin'] == v['export'] for k, v in classes.items()},
           classes78_equal_pins=all(classes[f'classes{L}.txt']['pin'] == classes[f'classes{L}.txt']['export'] for L in (7, 8)))
rec['passed'] = rec['reference_ok'] and rec['sources_used_equal_pins'] and rec['classes78_equal_pins']
out.write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('manifest_sha256', 'reference_ok', 'sources_used_equal_pins',
                                      'sources_differing_from_pins', 'classes78_equal_pins', 'passed')}, indent=1))
sys.exit(0 if rec['passed'] else 1)
PY

# ---- 2. platform record ------------------------------------------------------------------------------------------
( set +e
  echo "## hostname"; hostname
  echo "## date"; date -Is
  echo "## uname -a"; uname -a
  echo "## /etc/os-release"; cat /etc/os-release
  echo "## lscpu"; lscpu
  echo "## numactl -H"; numactl -H
  echo "## Cpus_allowed_list"; grep Cpus_allowed_list /proc/self/status
  echo "## MemTotal"; grep MemTotal /proc/meminfo
  echo "## g++"; command -v g++; readlink -f "$(command -v g++)"; g++ --version | head -1
  echo "## g++ -v"; g++ -v 2>&1
  echo "## glibc (ldd --version)"; ldd --version 2>&1 | head -1
  echo "## dpkg-query"
  dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' libc6 libgomp1 libstdc++6 libgcc-s1 libquadmath0 \
    gcc-11 g++-11 libgmp10 libgmp-dev 2>&1
  echo "## python"; command -v python3; python3 -c 'import sys; print(sys.version)'
  echo "## modules"; module list 2>&1
  echo "## environment"; env | grep -E '^(OMP_|GOMP_|SLURM_JOB_ID|SLURM_JOB_NODELIST|SLURM_JOB_PARTITION|SLURM_CPUS_ON_NODE|SLURM_MEM_PER_NODE|C8_)' | sort
) > "$P/platform.txt" 2>&1
grep -E '^(Model name|CPU\(s\)|Thread\(s\) per core|Socket\(s\)|NUMA node\(s\))' "$P/platform.txt" || true
g++ --version | head -1 || true
ldd --version 2>&1 | head -1 || true

# ---- 3. the package's J-GEN-3 script, unchanged ------------------------------------------------------------------
set +e
bash "$C8_PACKAGE/slurm/gen/crossnode.slurm"
xrc=$?
set -e
echo "jgen3: crossnode.slurm exit $xrc at $(date -Is)"

( set +e
  cd "$W/bin" || exit 0
  echo "## sha256"; sha256sum build_free build_power check_edge_forests test_keys
  for b in build_free build_power; do
    echo "## ldd $b"; ldd "$b"
    echo "## resolved libraries of $b"; ldd "$b" | awk '$3 ~ /^\// {print $3}' | xargs -r readlink -f
  done
  echo "## build records"; for f in *.build.txt; do echo "# $f"; cat "$f"; done
) > "$P/builders.txt" 2>&1

set +e
python3 - "$E" "$C8_GEN_REFERENCE" "$P" "$xrc" <<'PY'
import hashlib, json, os, socket, sys
from pathlib import Path
e, ref, p, xrc = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
h = lambda q: hashlib.sha256(q.read_bytes()).hexdigest() if q.exists() else None
def members(q):
    d = {}
    if q.exists():
        for line in q.read_text().splitlines():
            hx, path = line.split('  ', 1)
            d[path] = hx
    return d
cpu = next((l.split(':', 1)[1].strip() for l in open('/proc/cpuinfo') if l.startswith('model name')), None)
man = json.loads((ref / 'MANIFEST.json').read_bytes())
new, old = members(e / 'MEMBERS.sha256'), members(ref / 'MEMBERS.sha256')
differ = sorted(k for k in set(new) & set(old) if new[k] != old[k])
groups = {}
for k in sorted(set(new) | set(old)):
    g = groups.setdefault(k.split('/', 1)[0], dict(reference=0, this_run=0, equal=0, differing=0))
    g['reference'] += k in old
    g['this_run'] += k in new
    g['equal'] += k in old and k in new and old[k] == new[k]
    g['differing'] += k in old and k in new and old[k] != new[k]
inv = {}
for L in (7, 8):
    a, b = e / f'inventories/inventory_L{L}.json', ref / f'inventory_L{L}.json'
    r = dict(sha256=h(a), reference_sha256=h(b), identical=a.exists() and a.read_bytes() == b.read_bytes())
    if a.exists() and not r['identical']:
        x, y = json.loads(a.read_bytes()), json.loads(b.read_bytes())
        for sector in ('free', 'power'):
            xs, ys = {c['id']: c for c in x.get(sector, [])}, {c['id']: c for c in y.get(sector, [])}
            ids = sorted(i for i in set(xs) | set(ys) if xs.get(i) != ys.get(i))
            fields = sorted({f for i in ids if i in xs and i in ys for f in set(xs[i]) | set(ys[i])
                             if xs[i].get(f) != ys[i].get(f)})
            r[f'{sector}_differing_ids'] = ids[:200]
            r[f'{sector}_differing_count'] = len(ids)
            r[f'{sector}_differing_fields'] = fields
        r['top_level_differing_keys'] = sorted(k for k in set(x) | set(y) if k not in ('free', 'power') and x.get(k) != y.get(k))
    inv[f'L{L}'] = r
rec = dict(schema='c8-d2-jgen3-compare-1', gate='A-INV-4 (J-GEN-3): Intel cross-platform inventory identity',
           site='symmetry', partition=os.environ.get('SLURM_JOB_PARTITION'), job=os.environ.get('SLURM_JOB_ID'),
           host=socket.gethostname(), cpu=cpu, threads=40, crossnode_exit=xrc, crossnode_evidence=str(e),
           wrapper_records=str(p), reference=str(ref), reference_manifest_sha256=h(ref / 'MANIFEST.json'),
           reference_host=man.get('host'), reference_cpu=man.get('cpu'), reference_threads=man.get('threads'),
           reference_jobs=man.get('slurm_job_ids'), reference_commit=man.get('git_commit'),
           reference_compiler=man['builders']['build_free'].get('compiler'),
           members_sha256=h(e / 'MEMBERS.sha256'), reference_members_sha256=h(ref / 'MEMBERS.sha256'),
           members_file_identical=(e / 'MEMBERS.sha256').exists()
                                  and (e / 'MEMBERS.sha256').read_bytes() == (ref / 'MEMBERS.sha256').read_bytes(),
           members_this_run=len(new), members_reference=len(old), members_equal=len(set(new) & set(old)) - len(differ),
           members_differing=differ[:500], members_differing_count=len(differ),
           only_in_this_run=sorted(set(new) - set(old))[:200], only_in_reference=sorted(set(old) - set(new))[:200],
           members_by_group=groups, inventories=inv)
rec['identical'] = (xrc == 0 and rec['members_file_identical'] and not differ and set(new) == set(old)
                    and all(v['identical'] for v in inv.values()))
(p / 'compare.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('host', 'cpu', 'crossnode_exit', 'members_sha256', 'reference_members_sha256',
                                      'members_this_run', 'members_equal', 'members_differing_count',
                                      'members_by_group', 'identical')}, indent=1))
print('inventories identical:', {k: v['identical'] for k, v in inv.items()})
sys.exit(0 if rec['identical'] else 1)
PY
crc=$?
set -e

# ---- 4. delete the scratch build tree ----------------------------------------------------------------------------
rm -rf "$W"
rmdir --ignore-fail-on-non-empty "$(dirname "$W")"
test ! -e "$W"
echo "jgen3: scratch $W deleted; evidence kept:"
du -sh "$E" "$P" || true
ls -la "$E" "$P" || true
echo "jgen3: done at $(date -Is); crossnode exit $xrc; compare exit $crc"
[ "$xrc" = 0 ] && [ "$crc" = 0 ]
