#!/bin/bash
#SBATCH -N 1 -n 1 --exclusive --mem=64G -t 00:20:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# C8(2) PRODUCTION preparation on symmetry (2026-10-06): build the gated dd+mp256 profile executable in the pilot's
# export (C8_PACKAGE = pkg/ba68f401e46e, commit ba68f40, whose default binaries the pilot build 570620 made) with
# `make gmp NUMERICS=dd,mp256` and Ubuntu GCC 11.4 on one AMD node, once. Template: s6fix4/scripts/s4build.slurm
# (job 570582, which built the gated a46f3060... in export 900e5906522a), reduced to the profile build.
#   0. Refuses if the export is not ba68f40 or bin/c8d2_gmp_dd+mp256 already exists (exit 64).
#   1. Before: sha256 of every file under bin/, a size+mtime listing of the export outside bin/.
#   2. make gmp NUMERICS=dd,mp256 (its `inputs` prerequisite runs tools/prepare_inputs.py, which only verifies the
#      packs, the L8 packs included, the small inputs and the vendored pins).
#   3. Checks (exit 3 on any failure, record written either way):
#      - bin/c8d2_gmp_dd+mp256 sha256 = a46f3060a27f4d5e... (the build the dd+mp256 J-FLAG gate 570574 passed);
#      - every default executable and build record under bin/ unchanged (sha256), and exactly two new files
#        (bin/c8d2_gmp_dd+mp256 and its .build.json); the export outside bin/ unchanged (size and mtime of every file);
#      - production.describe(exe, 'dd+mp256') and production.read_build_record(exe, 'gmp', 'dd+mp256', required=True)
#        (the non-test plan's own Z3 checks); NUMERICS dd+mp256, macro_overrides [], no development, Boost 1_77,
#        build_directory = this export (W3);
#      - the build record equal to the gated build's record (s6fix4/s4build.570582.0, in this export) in every field but
#        build_directory and time stamps; its libgmp 4dc20a90... = the gate's (design.check_gate on the gate record
#        s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json, sha256 42e6d2d8..., against this export's inputs);
#      - the runtime fingerprint of a staged copy on this node (common.fingerprint / runtime_identity_key, as a claim
#        computes it; Y6/Z6 problems, W7 loader overrides): recorded, and compared with the pilot's pinned key 04f1e51d....
# Usage: C8_PACKAGE=... sbatch --export=ALL -p amddebugq --exclude=<list> -J c8d2-prbuild prbuild.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}"
D=/mnt/beegfs/zzheng1/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=prbuild.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
test "$(cat "$C8_PACKAGE.commit")" = ba68f401e46e4071ca5593ae40ec92a1755dcc98 || { echo "export is not ba68f40; refusing" >&2; exit 64; }
test ! -e bin/c8d2_gmp_dd+mp256 && test ! -e bin/c8d2_gmp_dd+mp256.build.json || { echo "bin/c8d2_gmp_dd+mp256 exists; refusing" >&2; exit 64; }
find bin -type f | sort | xargs sha256sum > "$E/bin_before.sha256"
find . -path ./bin -prune -o -type f -printf '%P %s %T@\n' | sort > "$E/tree_before.txt"
t0=$(date +%s)
make gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "profile build in $(( $(date +%s) - t0 )) s"
find bin -type f | sort | xargs sha256sum > "$E/bin_after.sha256"
find . -path ./bin -prune -o -type f -printf '%P %s %T@\n' | sort > "$E/tree_after.txt"
sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
bin/c8d2_gmp_dd+mp256 --describe > "$E/describe_dd+mp256.json"
cp bin/c8d2_gmp_dd+mp256.build.json "$E/"
ldd bin/c8d2_gmp_dd+mp256 > "$E/ldd_dd+mp256.txt" 2>&1
python3 -B - "$E" "$C8_PACKAGE" <<'PY'
import json, os, shutil, sys, tempfile
from pathlib import Path
E, PKG = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(PKG / 'tools'))
import common, design, production as prod
WANT = 'a46f3060a27f4d5e3af19023fc5bb67a7ca2dc6c4242e671ef4bdb9427254c8c'
GATE = PKG / 'benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json'
GATE_SHA = '42e6d2d80a484c2bddc8bba37180c400191c79722d9a11ddf9eb535429e0a800'
GATED_REC = PKG / 'benchmarks/symmetry_2026-10-c8/s6fix4/s4build.570582.0/build_records/c8d2_gmp_dd+mp256.build.json'
PILOT_KEY = '04f1e51dfc2e89b039f567261a341d5723806390bdd1a222245ac5c2584c360b'
NEW = {'bin/c8d2_gmp_dd+mp256', 'bin/c8d2_gmp_dd+mp256.build.json'}
rd = lambda f: {l.split(None, 1)[1].strip(): l.split()[0] for l in Path(f).read_text().splitlines() if l.strip()}
before, after = rd(E / 'bin_before.sha256'), rd(E / 'bin_after.sha256')
exe = PKG / 'bin' / 'c8d2_gmp_dd+mp256'
rec = {'schema': 'c8-d2-production-profile-build-1', 'package': str(PKG), 'commit': Path(str(PKG) + '.commit').read_text().strip(),
       'slurm_job': os.environ.get('SLURM_JOB_ID'), 'host': os.uname().nodename, 'utc': common.utc()}
rec['profile_sha256'] = common.digest(exe); rec['profile_is_gated_build'] = rec['profile_sha256'] == WANT
rec['defaults_unchanged'] = {k: {'before': v, 'after': after.get(k), 'equal': after.get(k) == v} for k, v in sorted(before.items())}
rec['defaults_all_unchanged'] = all(v['equal'] for v in rec['defaults_unchanged'].values())
rec['new_files'] = sorted(set(after) - set(before)); rec['only_the_profile_files_added'] = set(rec['new_files']) == NEW and not (set(before) - set(after))
rec['tree_outside_bin_unchanged'] = (E / 'tree_before.txt').read_text() == (E / 'tree_after.txt').read_text()
rec['tree_outside_bin_files'] = len((E / 'tree_after.txt').read_text().splitlines())
why = []
try: d = prod.describe(exe, 'dd+mp256'); rec['describe'] = {k: d.get(k) for k in ('numerics', 'diagnostic', 'tail_top', 'numerics_params')}
except Exception as e: why.append(f'describe: {e}')
try: prod.read_build_record(exe, 'gmp', 'dd+mp256', required=True); rec['read_build_record_nontest'] = 'accepted'
except Exception as e: why.append(f'read_build_record: {e}'); rec['read_build_record_nontest'] = str(e)
br = json.loads((PKG / 'bin' / 'c8d2_gmp_dd+mp256.build.json').read_text()); gr = json.loads(GATED_REC.read_text())
skip = {'build_directory', 'host', 'created_utc'}
diff = sorted(k for k in set(br) | set(gr) if k not in skip and br.get(k) != gr.get(k))
rec['build_record_vs_gated_570582'] = {'differing_fields': diff, 'skipped': sorted(skip & (set(br) | set(gr))),
                                        'build_directory': [gr.get('build_directory'), br.get('build_directory')]}
rec['build_record_equal_to_gated'] = not diff
rec['build_record_fields'] = {k: br.get(k) for k in ('NUMERICS', 'macro_overrides', 'parameter_overrides', 'development', 'required_flags_present', 'diagnostic',
                                                     'BOOST_LIB_VERSION', 'executable_sha256', 'compiler', 'build_directory', 'GMP_PREFIX')}
rec['build_record_gmp_library'] = (br.get('gmp_library') or {}).get('sha256')
rec['w3_build_directory_is_the_export'] = os.path.realpath(br.get('build_directory') or '/nonexistent') == str(PKG.resolve())
rec['gate_record_sha256'] = common.digest(GATE); rec['gate_record_is_42e6d2d8'] = rec['gate_record_sha256'] == GATE_SHA
try:
    inv = json.loads((PKG / 'inputs' / 'inventory.json').read_text())
    g = design.check_gate(GATE, 'dd+mp256', inv, None)
    rec['check_gate'] = {k: g.get(k) for k in ('sha256', 'slurm_job', 'profile_executable_sha256', 'exact_executable_sha256', 'gmp_library', 'inputs_manifest_sha256', 'host', 'cpu_model', 'compiler', 'F2_total')}
    gl = (g.get('gmp_library') or {}).get('profile')
    rec['gate_profile_executable_is_this_build'] = g.get('profile_executable_sha256') == rec['profile_sha256']
    rec['libgmp_is_the_gates'] = rec['build_record_gmp_library'] == gl
except Exception as e: why.append(f'check_gate: {e}'); rec['check_gate'] = str(e)
runtime = Path(tempfile.mkdtemp(prefix='c8d2_runtime_'))
try:
    st = runtime / exe.name; shutil.copyfile(exe, st); os.chmod(st, 0o700); counter = {'bytes': 0}; cpu = {}
    fp = common.fingerprint(st, counter, cpu); kind = common.elf_kind(st)
    rec['fingerprint'] = {'cpu_vendor': cpu.get('vendor'), 'cpu_model': fp.get('cpu_model'), 'glibc': fp.get('glibc'),
                          'libraries': {k: (v.get('sha256') if isinstance(v, dict) else v) for k, v in (fp.get('libraries') or {}).items()},
                          'problems': common.fingerprint_problems(fp, kind, cpu), 'malformed': common.fingerprint_malformed(fp),
                          'loader_overrides': common.loader_overrides(), 'preload_order': fp.get('preload_order'), 'loader_env': fp.get('loader_env'),
                          'runtime_identity_key': common.runtime_identity_key(fp), 'runtime_identity': common.runtime_identity(fp)}
    rec['runtime_key_equals_pilot_pin'] = rec['fingerprint']['runtime_identity_key'] == PILOT_KEY
finally:
    shutil.rmtree(runtime, ignore_errors=True)
rec['problems'] = why
rec['ok'] = (rec['profile_is_gated_build'] and rec['defaults_all_unchanged'] and rec['only_the_profile_files_added'] and rec['tree_outside_bin_unchanged']
             and not why and rec['build_record_equal_to_gated'] and rec['w3_build_directory_is_the_export'] and rec['gate_record_is_42e6d2d8']
             and rec.get('gate_profile_executable_is_this_build') is True and rec.get('libgmp_is_the_gates') is True
             and not rec['fingerprint']['problems'] and not rec['fingerprint']['loader_overrides'] and rec['runtime_key_equals_pilot_pin'])
(E / 'identity.json').write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
print('profile', rec['profile_sha256'][:12], 'gated build:', rec['profile_is_gated_build'], '; defaults unchanged:', rec['defaults_all_unchanged'],
      '; only the profile files added:', rec['only_the_profile_files_added'], rec['new_files'], '; tree outside bin unchanged:', rec['tree_outside_bin_unchanged'],
      '; build record = gated record (but build_directory):', rec['build_record_equal_to_gated'], rec['build_record_vs_gated_570582']['differing_fields'],
      '; read_build_record non-test:', rec['read_build_record_nontest'], '; gate 42e6d2d8:', rec['gate_record_is_42e6d2d8'],
      '; gate admits this build:', rec.get('gate_profile_executable_is_this_build'), '; libgmp = gate:', rec.get('libgmp_is_the_gates'), rec['build_record_gmp_library'][:12] if rec['build_record_gmp_library'] else None,
      '; runtime key', (rec['fingerprint']['runtime_identity_key'] or '')[:12], '= pilot pin:', rec['runtime_key_equals_pilot_pin'],
      '; problems:', why or 'none', '; OK:', rec['ok'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_gmp_dd+mp256 > "$E/binaries_end.sha256"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
