#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=32 --mem=60G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-r4f-ctrl
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R4f (development probe), layout control: is the gain of the GMP_PREFIX builds the library's, or the shifted
# code layout's? With GMP_PREFIX the worker's .text is the default one moved by 0x30 bytes (the longer DT_RPATH string).
# The control links the SAME Spack GMP through GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-spak, a directory of two symlinks
# (include, lib) into the Spack prefix whose path has the length of ~/c8d2/opt/gmp-6.2.1-zen2. The control worker
# then has the host-tuned worker's layout byte for byte (only the four characters "spak"/"zen2" of the rpath differ;
# checked with cmp) and the baseline's library. In one directory each, from this export's src/ and Makefile: the
# default worker (must equal Stage 3), the control worker and the host worker (GMP_PREFIX=~/c8d2/opt/gmp-6.2.1-zen2,
# must equal r4f_gmp_build's 0a77b88e...). Then r4f_bench.py profile on every 8th task of heavy_free_L8 and
# heavy_power_L8 at 32 threads, twice in rotated order: perf record and the tier timers of all three.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L8_PACKS=<dir with the pinned L8 packs> sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=r4fctrl.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
P=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage4b/dev_r4f/scripts; W=$C8_DATA/work/$TAG/r4f-ctrl
HOSTP=$HOME/c8d2/opt/gmp-6.2.1-zen2; SPAK=$HOME/c8d2/opt/gmp-6.2.1-spak
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; workers $W; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; perf --version 2>&1; echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"; } > "$E/node.txt" 2>&1
grep -E 'Model name|perf_event_paranoid' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
test ! -e "$W" || { echo "$W exists; refusing to overwrite" >&2; exit 65; }
test -x "$HOSTP/lib/libgmp.so.10" || test -e "$HOSTP/lib/libgmp.so.10" || { echo "missing $HOSTP (r4f_gmp_build.slurm host)" >&2; exit 69; }
[ ${#SPAK} -eq ${#HOSTP} ] || { echo "control prefix length ${#SPAK} != ${#HOSTP}" >&2; exit 64; }
if [ ! -e "$SPAK" ]; then mkdir "$SPAK"; ln -s "$C8_GMP/include" "$SPAK/include"; ln -s "$C8_GMP/lib" "$SPAK/lib"; fi
[ "$(readlink -f "$SPAK/lib/libgmp.so.10")" = "$(readlink -f "$C8_GMP/lib/libgmp.so.10")" ] || { echo "$SPAK does not point at the Spack GMP" >&2; exit 65; }
ls -la "$SPAK" | tee "$E/spak_prefix.txt"
# The pinned L8 packs (re-hashed against inputs/manifest.json by make inputs) for the fixture staging.
cd "$C8_PACKAGE"
for s in free power; do [ -e "inputs/packs/${s}_L8.pack" ] || ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack"; done
make inputs > "$E/make_inputs.log" 2>&1; tail -2 "$E/make_inputs.log"
for v in base spak host; do
  mkdir -p "$W/$v/tools"; cp -R src Makefile "$W/$v/"; cp tools/build_record.py tools/common.py "$W/$v/tools/"
  case $v in base) gp=();; spak) gp=(GMP_PREFIX="$SPAK");; host) gp=(GMP_PREFIX="$HOSTP");; esac
  make -C "$W/$v" -j3 bin/c8d2_gmp bin/c8d2_gmp_prof "${gp[@]}" > "$E/make_$v.log" 2>&1
  cp "$W/$v/bin/c8d2_gmp.build.json" "$E/c8d2_gmp.$v.build.json"
done
sha256sum "$W"/*/bin/c8d2_gmp "$W"/*/bin/c8d2_gmp_prof | tee "$E/binaries.sha256"
{ for v in base spak host; do echo "# $v"; ldd "$W/$v/bin/c8d2_gmp" | grep libgmp; readelf -d "$W/$v/bin/c8d2_gmp" | grep -E 'RPATH|RUNPATH' || true; done; } | tee "$E/ldd.txt"
python3 - "$W" "$E" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
W, E = Path(sys.argv[1]), Path(sys.argv[2])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def diffbytes(a, b):
    x, y = a.read_bytes(), b.read_bytes()
    return {'size_a': len(x), 'size_b': len(y), 'differing_bytes': sum(p != q for p, q in zip(x, y)) + abs(len(x) - len(y)),
            'offsets': [i for i, (p, q) in enumerate(zip(x, y)) if p != q][:64]}
rec = {'sha256': {v: {x: h(W / v / 'bin' / x) for x in ('c8d2_gmp', 'c8d2_gmp_prof')} for v in ('base', 'spak', 'host')},
       'expected': {'base': {'c8d2_gmp': '5c5328af932912bb6dff0ba72f124381f61ae25219b04d74c6f0e0b0d5153ed3',
                             'c8d2_gmp_prof': 'd1cc6551df116cd106ebf99985cf20035387acaad9ff1fcd77274a0b51de75d7'},
                    'host': {'c8d2_gmp': '0a77b88e81e4e8b779684fcacf078a817a5f7ff866b861726ebb1a1c6cc622ee',
                             'c8d2_gmp_prof': 'c722d5f81e592f449c74029ceecc7c871942b41b2d8a8f47a8105003dfb0b94d'}},
       'spak_vs_host': {x: diffbytes(W / 'spak/bin' / x, W / 'host/bin' / x) for x in ('c8d2_gmp', 'c8d2_gmp_prof')}}
rec['base_ok'] = rec['sha256']['base'] == rec['expected']['base']; rec['host_ok'] = rec['sha256']['host'] == rec['expected']['host']
rec['layout_ok'] = all(d['size_a'] == d['size_b'] and d['differing_bytes'] <= 8 for d in rec['spak_vs_host'].values())
(E / 'control_builds.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps({k: rec[k] for k in ('base_ok', 'host_ok', 'layout_ok', 'spak_vs_host')}))
sys.exit(0 if rec['base_ok'] and rec['host_ok'] and rec['layout_ok'] else 3)
PY
status=0
for round in 1 2; do
  if [ $round = 1 ]; then order=(base spak host); else order=(host spak base); fi
  ex=(); pr=(); for v in "${order[@]}"; do ex+=(--exe "$v=$W/$v/bin/c8d2_gmp"); pr+=(--prof "$v=$W/$v/bin/c8d2_gmp_prof"); done
  echo "== profile round $round (${order[*]}) $(date -Is)"
  python3 -B "$P/r4f_bench.py" profile --package "$C8_PACKAGE" --stride 8 --scratch "$L" --output "$E/profile_r$round" "${ex[@]}" "${pr[@]}" \
    > "$E/profile_r$round.stdout" 2>&1 || { status=1; echo "== profile round $round FAILED"; tail -20 "$E/profile_r$round.stdout"; }
  grep -E 'MP |FAILED' "$E/profile_r$round.stdout" | cut -c1-200 || true
done
cd /; rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
