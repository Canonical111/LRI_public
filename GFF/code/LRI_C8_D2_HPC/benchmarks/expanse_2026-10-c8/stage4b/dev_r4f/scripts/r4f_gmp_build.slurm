#!/bin/bash
#SBATCH -A yun124 -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-r4f-gmp
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b R4f (development probe): GMP 6.2.1, the version of the Spack GMP the package links on Expanse, built from the
# official tarball as one variant (R4F_VARIANT):
#   fat   ./configure --enable-fat         (every x86-64 kernel set; the CPU is chosen at run time by cpuid)
#   host  ./configure --host=<config.guess> (the kernels and thresholds of this node's CPU, as GMP's own config.guess
#                                            names it; zen2-pc-linux-gnu on an EPYC 7742)
# both with Spack's other arguments (--enable-cxx --enable-shared --enable-static --with-pic) and Spack's compiler (GCC
# 13.3.0 of env_expanse.sh). The tarball is checked first: sha256 eae9326b... (Spack's pin for gmp-6.2.1.tar.bz2, the
# bytes the Spack GMP was built from) and a VALIDSIG of its gmplib.org .sig by the GMP release key 343C2FF0...28C67298
# (fingerprint published on gmplib.org). The build runs on node-local scratch with the Spack GMP removed from CPATH,
# LIBRARY_PATH and LD_LIBRARY_PATH; `make check` must pass with no FAIL or ERROR; then `make install` into a staging
# directory, copied to ~/c8d2/opt/gmp-6.2.1-<fat|cpu> (refused if it exists). Finally the workers of the commit under
# test (src/, Makefile and the build-record tools of $C8_PACKAGE) are built with GMP_PREFIX=<that prefix> into
# $C8_DATA/work/<sha12>/r4f-<variant>/bin: c8d2_decimal (must equal Stage 3: the knob leaves it alone), c8d2_gmp and
# c8d2_gmp_prof; ldd under this environment (LD_LIBRARY_PATH still lists the Spack GMP) must resolve libgmp.so.10 to
# the new prefix (DT_RPATH).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> R4F_VARIANT=fat|host sbatch --export=ALL ...
set -euo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${R4F_VARIANT:?}"
case $R4F_VARIANT in fat|host) ;; *) echo "R4F_VARIANT must be fat or host" >&2; exit 64;; esac
TAG=$(basename "$C8_PACKAGE"); RUN=r4fgmp-$R4F_VARIANT.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
W=$C8_DATA/work/$TAG/r4f-$R4F_VARIANT
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); variant $R4F_VARIANT; package $C8_PACKAGE; evidence $E; workers $W"
test ! -e "$W" || { echo "$W exists; refusing to overwrite" >&2; exit 65; }
{ hostname; lscpu; gcc --version | head -1; g++ --version | head -1; } > "$E/node.txt"; grep -E 'Model name' "$E/node.txt"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
SRC=$HOME/c8d2/src/gmp; TB=$SRC/gmp-6.2.1.tar.bz2; KEY=343C2FF0FBEE5EC2EDBEF399F3599FF828C67298
# 1. The tarball: Spack's sha256 pin and the release signature (a private copy of the keyring: no shared gpg state).
echo "eae9326beb4158c386e39a356818031bd28f3124cf915f8c5b1dc4c7a36b4d7c  $TB" | sha256sum -c - | tee "$E/tarball_sha256.txt"
cp -R "$SRC/gnupg" "$L/gnupg"; chmod 700 "$L/gnupg"
GNUPGHOME=$L/gnupg gpg --batch --status-fd 1 --verify "$TB.sig" "$TB" > "$E/tarball_gpg.txt" 2>&1 || true
grep -q "^\[GNUPG:\] VALIDSIG $KEY " "$E/tarball_gpg.txt" || { echo "signature check FAILED" >&2; cat "$E/tarball_gpg.txt"; exit 65; }
grep -E 'VALIDSIG|Good signature|Signature made' "$E/tarball_gpg.txt"
# 2. Configure and build on node-local scratch, without the Spack GMP on any search path.
strip_gmp() {  # strip_gmp VAR: drop the Spack GMP's directories from the path list VAR (unset VAR when nothing is left)
  local IFS=: d out=(); for d in ${!1:-}; do [[ -z "$d" || "$d" == "$C8_GMP"* ]] || out+=("$d"); done
  if [ ${#out[@]} -gt 0 ]; then export "$1=${out[*]}"; else unset "$1"; fi
}
cd "$L"; tar xjf "$TB"; cd gmp-6.2.1
GUESS=$(./config.guess); echo "$GUESS" | tee "$E/config_guess.txt"
if [ "$R4F_VARIANT" = fat ]; then NAME=fat; HOSTARG=(--enable-fat); else NAME=${GUESS%%-*}; HOSTARG=(--host="$GUESS"); fi
PREFIX=$HOME/c8d2/opt/gmp-6.2.1-$NAME; echo "$PREFIX" > "$E/prefix.txt"
test ! -e "$PREFIX" || { echo "$PREFIX exists; refusing to overwrite" >&2; exit 65; }
CONF=(--prefix="$PREFIX" --enable-cxx --enable-shared --enable-static --with-pic "${HOSTARG[@]}")
printf '%s\n' "${CONF[@]}" > "$E/configure_args.txt"
t0=$(date +%s)
(
  strip_gmp CPATH; strip_gmp LIBRARY_PATH; strip_gmp LD_LIBRARY_PATH
  env | grep -E '^(CPATH|LIBRARY_PATH|LD_LIBRARY_PATH|PATH)=' > "$E/build_env.txt" || true
  ! grep -qF "$C8_GMP" "$E/build_env.txt"
  CC=gcc CXX=g++ ./configure "${CONF[@]}" > "$E/configure.out" 2>&1
  make -j16 > "$E/make.log" 2>&1
  echo "build $(( $(date +%s) - t0 )) s"
  set +e; make -j16 check > "$E/make_check.log" 2>&1; echo $? > "$E/make_check.exit"; set -e
  make install DESTDIR="$L/stage" > "$E/make_install.log" 2>&1
)
grep -E '^ *(CC|CFLAGS|MPN_PATH)=|^using ABI' "$E/configure.out" | tee "$E/configure_summary.txt"
grep 'config.status: linking' "$E/configure.out" | sed 's/config.status: linking //' > "$E/mpn_links.txt"
gzip -c config.log > "$E/config.log.gz"
python3 - "$E" <<'PY'
import json, re, sys
from pathlib import Path
E = Path(sys.argv[1]); log = (E / 'make_check.log').read_text(errors='replace')
tot = {k: 0 for k in ('TOTAL', 'PASS', 'SKIP', 'XFAIL', 'FAIL', 'XPASS', 'ERROR')}; dirs = 0
for m in re.finditer(r'^# (TOTAL|PASS|SKIP|XFAIL|FAIL|XPASS|ERROR):\s+(\d+)', log, re.M):
    tot[m[1]] += int(m[2]); dirs += m[1] == 'TOTAL'
rc = int((E / 'make_check.exit').read_text())
rec = {'make_check_exit': rc, 'summaries': dirs, 'totals': tot, 'passed': rc == 0 and dirs > 0 and tot['FAIL'] == 0 and tot['ERROR'] == 0 and tot['XPASS'] == 0}
(E / 'make_check_summary.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec))
sys.exit(0 if rec['passed'] else 4)
PY
echo "gmp built and checked in $(( $(date +%s) - t0 )) s"
# 3. Install: copy the staged tree into place; record every installed file.
mkdir -p "$(dirname "$PREFIX")"; cp -a "$L/stage$PREFIX" "$PREFIX"
( cd "$PREFIX" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$E/installed.sha256"
grep -E '__GMP_CC |__GMP_CFLAGS ' "$PREFIX/include/gmp.h" | tee "$E/gmp_h_config.txt"
diff "$C8_GMP/include/gmp.h" "$PREFIX/include/gmp.h" > "$E/gmp_h_vs_spack.diff" || true; echo "gmp.h vs Spack: $(grep -c '^[<>]' "$E/gmp_h_vs_spack.diff") changed lines"
LIB=$(readlink -f "$PREFIX/lib/libgmp.so.10"); sha256sum "$LIB" | tee "$E/libgmp_sha256.txt"
{ echo "# nm -D (dynamic)"; nm -D --defined-only "$LIB" | grep -E ' __gmpn_(cpuvec|mul_basecase)' || true
  echo "# nm (symtab)"; nm --defined-only "$LIB" | grep -E ' __gmpn_(cpuvec|mul_basecase)' || true; } | tee "$E/libgmp_symbols.txt"
objdump -d --no-show-raw-insn "$LIB" > "$L/libgmp.dis"
for f in $(nm --defined-only "$LIB" | awk '$3 ~ /^__gmpn_(mul_basecase|addmul_1|mul_1|add_n|copyi|sqr_basecase)(_[a-z0-9]+)?$/ {print $3}' | sort -u); do
  body=$(awk -v f="<$f>:" '$2==f{p=1;next} p&&/^$/{exit} p' "$L/libgmp.dis")
  printf '%s insns=%s mulx=%s adox_adcx=%s mul=%s\n' "$f" "$(printf '%s\n' "$body" | grep -c .)" "$(printf '%s\n' "$body" | grep -cE '\smulx\s')" \
    "$(printf '%s\n' "$body" | grep -cE '\s(adox|adcx)\s')" "$(printf '%s\n' "$body" | grep -cE '\smul\s')"
done | tee "$E/kernel_instructions.txt"
# 4. The workers of the commit under test against the new GMP (GMP_PREFIX), in their own directory.
mkdir -p "$W/tools"; cp -R "$C8_PACKAGE/src" "$C8_PACKAGE/Makefile" "$W/"; cp "$C8_PACKAGE/tools/build_record.py" "$C8_PACKAGE/tools/common.py" "$W/tools/"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS
make -C "$W" -j3 bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof GMP_PREFIX="$PREFIX" 2>&1 | tee "$E/make_workers.log" | grep -E 'build.json|rror' || true
sha256sum "$W/bin/c8d2_decimal" "$W/bin/c8d2_gmp" "$W/bin/c8d2_gmp_prof" | tee "$E/workers.sha256"
mkdir "$E/build_records"; cp "$W"/bin/*.build.json "$E/build_records/"
{ echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"; ldd "$W/bin/c8d2_gmp"; readelf -d "$W/bin/c8d2_gmp" | grep -E 'NEEDED|RPATH|RUNPATH'; } > "$E/ldd_gmp.txt"; grep -E 'libgmp|RPATH|RUNPATH' "$E/ldd_gmp.txt"
python3 - "$E" "$W" "$PREFIX" "$LIB" <<'PY'
import hashlib, json, sys
from pathlib import Path
E, W, prefix, lib = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
br = json.loads((W / 'bin/c8d2_gmp.build.json').read_text()); gl = br.get('gmp_library') or {}
rec = {'prefix': prefix, 'libgmp_realpath': lib, 'libgmp_sha256': h(lib),
       'decimal_sha256': h(W / 'bin/c8d2_decimal'), 'gmp_sha256': h(W / 'bin/c8d2_gmp'), 'gmp_prof_sha256': h(W / 'bin/c8d2_gmp_prof'),
       'decimal_equals_stage3': h(W / 'bin/c8d2_decimal') == '3dbd51bb1bd658927e3521059fbc77309fb112384145dabf1cc6347eb890805a',
       'build_record_GMP_PREFIX': br.get('GMP_PREFIX'), 'build_record_gmp_header': br.get('gmp_header'), 'build_record_gmp_library': gl,
       'resolves_to_prefix': gl.get('realpath') == lib and gl.get('sha256') == h(lib), 'rpath': gl.get('rpath'), 'runpath': gl.get('runpath')}
# Spack's GCC adds its own lib64 to the DT_RPATH of every executable (the default build has it too), so the prefix is
# one entry of the rpath list; what matters is the library ldd resolves under LD_LIBRARY_PATH, and no DT_RUNPATH.
rec['rpath_has_prefix'] = f'{prefix}/lib' in (rec['rpath'] or '').split(':')
rec['ok'] = rec['decimal_equals_stage3'] and rec['resolves_to_prefix'] and rec['rpath_has_prefix'] and not rec['runpath']
(E / 'workers_check.json').write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1))
sys.exit(0 if rec['ok'] else 3)
PY
cd /; rm -rf "$L/gmp-6.2.1" "$L/stage" "$L/gnupg" "$L/libgmp.dis"
echo "finished $(date -Is)"
