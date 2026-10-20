#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:50:00 --no-requeue
#SBATCH -J c8d2-int-gate
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 4b integration: the exact gates of one or more cumulative steps on one exclusive Expanse compute node (128
# cores). INT_VARIANTS is a ';'-separated list of NAME|PACKAGE|BIN|FLAGS:
#   PACKAGE  a built export (int_build.slurm): bin/c8d2_{decimal,gmp}, bin/ref (make c7ref), bin/baseline (Stage 3);
#   BIN      '-' runs in PACKAGE itself; otherwise a directory holding another c8d2_gmp (a GMP_PREFIX build): a node-local
#            copy of PACKAGE (everything but bin/ and build/, the L8 packs as symlinks) gets that c8d2_gmp and PACKAGE's
#            c8d2_decimal, bin/ref and bin/baseline;
#   FLAGS    ','-separated extras: replay (validate.py --only replay: A-RPL-1/2/3 subset, for BIN builds whose package
#            subset ran with the default binaries), quaddiff (tests/quad_differential.py at 128 threads: R3a's proof on
#            this build), or '-'.
# Per variant, always: A-RPL-7 G-L8SELF (validate.py --l8self bin/baseline: the L8 sweep sample, 2,000 kernels x 2 x 512
# points, both backends, every scientific field exact against the Stage-3 baseline) and A-RPL-6 thread identity
# (tests/thread_identity.py: L8 free and power blocks at 1, 8, 16, 64 threads and 8 lanes x 8 threads, both backends).
# Every step runs; the job fails if any fails. Records: $C8_DATA/evidence/<sha12 of the last PACKAGE>/intgate.<job>.0/<NAME>/.
# Usage: INT_VARIANTS='S1|$C8_DATA/pkg/<a>|-|-;B4|$C8_DATA/pkg/<b>|$C8_DATA/work/<b>/int-zen2-S3src/bin|replay' \
#        sbatch --export=ALL [--dependency=afterok:<builds>] int_gate.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${INT_VARIANTS:?}"
S3DEC=3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a; S3GMP=5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3
LASTPKG=$(echo "$INT_VARIANTS" | tr ';' '\n' | tail -1 | cut -d'|' -f2)
TAG=$(basename "$LASTPKG"); RUN=intgate.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"; echo "variants: $INT_VARIANTS" | tee "$E/variants.txt"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
status=0
run() { local d=$1 name=$2; shift 2; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$d/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -2 "$d/$name.stdout" | cut -c1-300; [ $c -eq 0 ] || status=1; return 0; }
IFS=';' read -ra VS <<< "$INT_VARIANTS"
for v in "${VS[@]}"; do
  IFS='|' read -r NAME PKG BIN FLAGS <<< "$v"
  D=$E/$NAME; mkdir "$D" || exit 64; echo "#### $NAME: package $PKG, bin $BIN, flags $FLAGS $(date -Is)"
  for f in "$PKG/bin/c8d2_decimal" "$PKG/bin/c8d2_gmp" "$PKG/bin/ref/c7d2_gmp" "$PKG/bin/baseline/c8d2_gmp"; do test -x "$f" || { echo "missing $f" >&2; exit 69; }; done
  if [ "$BIN" = - ]; then P=$PKG; else
    P=$L/pkg_$NAME; mkdir "$P"
    ( cd "$PKG" && tar --exclude=./bin --exclude=./build --exclude=./inputs/packs/free_L8.pack --exclude=./inputs/packs/power_L8.pack -cf - . ) | tar -C "$P" -xf -
    for s in free power; do ln -s "$PKG/inputs/packs/${s}_L8.pack" "$P/inputs/packs/${s}_L8.pack"; done
    mkdir "$P/bin"; cp -a "$BIN/c8d2_gmp" "$BIN/c8d2_gmp.build.json" "$PKG/bin/c8d2_decimal" "$PKG/bin/c8d2_decimal.build.json" "$P/bin/"
    cp -a "$PKG/bin/ref" "$PKG/bin/baseline" "$P/bin/"
    { echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; ldd "$P/bin/c8d2_gmp" | grep libgmp; } | tee "$D/ldd.txt"
  fi
  sha256sum "$P/bin/c8d2_decimal" "$P/bin/c8d2_gmp" "$P/bin/baseline/c8d2_decimal" "$P/bin/baseline/c8d2_gmp" | tee "$D/binaries.sha256"
  [ "$(sha256sum "$P/bin/baseline/c8d2_decimal" | cut -c1-64)" = $S3DEC ] && [ "$(sha256sum "$P/bin/baseline/c8d2_gmp" | cut -c1-64)" = $S3GMP ] || { echo "bin/baseline is not Stage 3" >&2; exit 3; }
  cd "$P" || exit 64
  run "$D" l8self python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 32 --threads 4 --output "$D/l8self.json"
  run "$D" thread_identity python3 -B tests/thread_identity.py --output "$D/thread_identity.json"
  case ",$FLAGS," in *,replay,*) run "$D" replay python3 -B tests/validate.py --only replay --jobs 32 --threads 4 --output "$D/replay.json";; esac
  case ",$FLAGS," in *,quaddiff,*) run "$D" quad_differential python3 -B tests/quad_differential.py --output "$D/quad_differential.json" --threads 128 --scratch "$TMPDIR";; esac
  cd /; [ "$BIN" = - ] || rm -rf "$P"
done
python3 - "$E" <<'PY' || status=1
import json, sys
from pathlib import Path
E = Path(sys.argv[1]); out = {}
for d in sorted(p for p in E.iterdir() if p.is_dir()):
    r = {}
    for k in ('l8self', 'thread_identity', 'replay', 'quad_differential'):
        f = d / f'{k}.json'
        if f.is_file():
            j = json.loads(f.read_text()); r[k] = j.get('status') or ('passed' if j.get('passed') else j.get('verdict'))
            if k == 'l8self': r['l8self_tests'] = [{x: t[x] for x in ('sector', 'backend', 'graphs', 'rows', 'quad_points', 'mp_points')} for t in j['tests']]; r['candidate'] = j['tests'][0]['candidate']
            if k == 'thread_identity': r['thread_identity_blocks'] = [{x: b[x] for x in ('backend', 'sector', 'tasks', 'identical', 'quad', 'mp')} for b in j['blocks']]
        elif (d / f'{k}.stdout').is_file(): r[k] = 'FAILED (no record)'
    out[d.name] = r
(E / 'gate_summary.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out, indent=1)[:6000])
ok = all(v.get('l8self') == 'passed' and v.get('thread_identity') == 'passed' and all(v.get(k) in (None, 'passed') for k in ('replay', 'quad_differential')) for v in out.values())
sys.exit(0 if ok and out else 1)
PY
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
