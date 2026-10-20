#!/bin/bash
#SBATCH -p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 3 on symmetry: build every executable of the merged fix-round-3 head in its git-archive export
# (C8_PACKAGE = pkg/<sha12>) on one AMD node with Ubuntu GCC 11.4, once, for the jobs that follow (s3val1, s3val23,
# s3flag, s3sweep). Z4 adds truncation checks to src/kernel.hpp's load_graph and Z3 a compile-time refusal of external
# C8_NX_* hooks, so this is NOT A-RPL-8: every executable that compiles load_graph changes, and the exact replays of
# s3val23 (J-VAL-2, J-VAL-3, A-RPL-7) prove that valid inputs give the same outputs bit for bit. Template:
# s6res2/scripts/rsbuild.slurm (job 570514).
#   1. The two L8 packs of C8_L8_PACKS (pkg/7a8aad783c31/inputs/packs) are re-hashed against this export's
#      inputs/manifest.json, then hard-linked into inputs/packs/.
#   2. make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize, then make c7ref (the exact default path: no
#      NUMERICS, no GMP_PREFIX, no CPPFLAGS/CXXFLAGS/LDFLAGS overrides). The new hashes are recorded; each is compared
#      with the a42cfb7 build (= the Stage-5 build of 5d7586e, job 570514) and listed as changed or unchanged. The
#      reference workers of make c7ref must stay e696d7f3.../7e3c8c92... (the plan's values; exit 3 otherwise).
#   3. make gmp NUMERICS=dd,mp256 builds the new bin/c8d2_gmp_dd+mp256 (its sha256 recorded; the gate s3flag runs on it);
#      every default executable keeps its sha256; --describe numerics dd+mp256, no development option, no stub.
#   4. Every build record (default, diagnostic, profile): macro_overrides an empty list (Z3: the compiler's own probe
#      finds no C8_* macro or source switch beyond the Makefile's -D words), parameter_overrides empty, development
#      false; the production builds also required_flags_present; Boost 1_77 everywhere.
#   5. A-RPL-7's Stage-3 baseline: bin/c8d2_{decimal,gmp} of pkg/b4273c59e911 (tag c8-stage3, built there by Stage-5
#      job 570026: c121b1e6.../23624153...) byte-copied into bin/baseline/ after their sha256 are checked; and, for the
#      extra L8 comparison with the previous default build, bin/c8d2_{decimal,gmp} of pkg/a42cfb718e69 (job 570514:
#      619ddf7d.../2cc5e88e...) into bin/prev/.
#   6. The Z4 checks on the real node, early: tests/test_native_guards.py with C8_GUARDS_OLD_TREE = the a42cfb7 export
#      (every kernel unit preprocessed and syntax-checked with the Makefile flags; the hook refusals, and a42cfb7 accepting
#      the injection; the loaders of this commit and of a42cfb7 on real G-files of every (sector, L), L8 included, byte
#      for byte, every truncation refused, and a42cfb7's loader with a pattern-initialized n refusing a short mask list
#      for the wrong reason) and tests/validate.py --only bad_inputs (14 truncated G-files each refused by the worker
#      and the inspector with 'truncated graph').
# A mismatch exits 3 (stop and report).
# Usage: C8_PACKAGE=... C8_L8_PACKS=... sbatch --export=ALL -J c8d2-s3build s3build.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L8_PACKS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s3build.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
BASE=$D/pkg/b4273c59e911; PREV=$D/pkg/a42cfb718e69
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); packs $C8_L8_PACKS; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
g++ --version | head -1 | tee "$E/gcc.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
test ! -e bin && test ! -e build || { echo "bin/ or build/ exists in the export; refusing" >&2; exit 64; }
python3 - "$C8_L8_PACKS" "$E/l8_packs.json" <<'PY' || { echo "L8 packs do not match inputs/manifest.json; nothing linked" >&2; exit 3; }
import hashlib, json, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); man = json.loads(Path('inputs/manifest.json').read_text())['sha256']; rec = {}
for s in ('free', 'power'):
    p = src / f'{s}_L8.pack'; h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    rec[s] = {'source': str(p), 'bytes': p.stat().st_size, 'inode': p.stat().st_ino, 'sha256': h.hexdigest(),
              'manifest': man[f'packs/{s}_L8.pack'], 'equal': h.hexdigest() == man[f'packs/{s}_L8.pack']}
out.write_text(json.dumps(rec, indent=1) + '\n'); print(json.dumps(rec, indent=1)); sys.exit(0 if all(v['equal'] for v in rec.values()) else 3)
PY
for s in free power; do ln "$C8_L8_PACKS/${s}_L8.pack" "inputs/packs/${s}_L8.pack" || exit 64; done
t0=$(date +%s)
{ make -j48 all gmp inspect profile ratiohist quaddiff probes sanitize && make c7ref; } > "$E/make.log" 2>&1 || { echo "build FAILED"; tail -40 "$E/make.log"; exit 3; }
echo "default builds in $(( $(date +%s) - t0 )) s"
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges bin/c8d2_interleave_probe bin/c8d2_decimal_san bin/c8d2_gmp_san"
sha256sum $X | tee "$E/binaries.sha256"
t0=$(date +%s)
make gmp NUMERICS=dd,mp256 > "$E/make_dd+mp256.log" 2>&1 || { echo "profile build FAILED"; tail -60 "$E/make_dd+mp256.log"; exit 3; }
echo "profile build in $(( $(date +%s) - t0 )) s"
sha256sum $X > "$E/binaries_after_profile.sha256"
sha256sum bin/c8d2_gmp_dd+mp256 | tee "$E/profile.sha256"
mkdir "$E/describe" "$E/build_records"
for x in c8d2_decimal c8d2_gmp c8d2_gmp_prof c8d2_gmp_ratiohist c8d2_gmp_dd+mp256; do bin/$x --describe > "$E/describe/$x.json"; cp bin/$x.build.json "$E/build_records/"; done
cp bin/c8d2_decimal_san.build.json bin/c8d2_gmp_san.build.json "$E/build_records/"
for x in c7d2_decimal c7d2_gmp; do cp bin/ref/$x.build.json "$E/build_records/ref_$x.build.json"; done
# 5. the Stage-3 baseline (A-RPL-7) and the previous default build, byte copies after their sha256 are checked
mkdir bin/baseline bin/prev || exit 3
cp -p "$BASE/bin/c8d2_decimal" "$BASE/bin/c8d2_gmp" "$BASE/bin/c8d2_decimal.build.json" "$BASE/bin/c8d2_gmp.build.json" bin/baseline/ || exit 3
cp -p "$PREV/bin/c8d2_decimal" "$PREV/bin/c8d2_gmp" "$PREV/bin/c8d2_decimal.build.json" "$PREV/bin/c8d2_gmp.build.json" bin/prev/ || exit 3
sha256sum bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp bin/prev/c8d2_decimal bin/prev/c8d2_gmp | tee "$E/baseline_prev.sha256"
python3 - "$E" "$C8_PACKAGE" <<'PY'
import json, sys
from pathlib import Path
E, PKG = Path(sys.argv[1]), Path(sys.argv[2])
# the a42cfb7 build (job 570514) = the Stage-5 symmetry build of 5d7586e (s5build.570026.0/binaries.sha256)
prev = {'bin/c8d2_decimal': '619ddf7d1cf94d6229c841cd3fbe22574045ec65a1b69f8b827f1e26f180895f',
        'bin/c8d2_gmp': '2cc5e88e76386c0d5c062eaf347cad95c0731a12d62a1af529660797ed715c17',
        'bin/c8d2_gmp_prof': '69e990c03cfc0256024763fda615cb1a9cffca41ec9f0518defaf5945b2fe62f',
        'bin/c8d2_gmp_ratiohist': '4f4638a210fe9ec5f383b1201885890562f6e40986952162aff4ee40a1d977e8',
        'bin/c8d2_inspect': '10fe813393ac4ce1fa82140d6262407481659833cf10097359035c1c623a29d9',
        'bin/ref/c7d2_decimal': 'e696d7f30cf2374e6b7051b659af334c0b2c9b385edaed2b0b55d36923124df5',
        'bin/ref/c7d2_gmp': '7e3c8c922bbbc70f0a15752ca23147acc360305ff4a947004484cce3024fe8c3',
        'bin/c8d2_quad_differential': '1e7a8d34008294b45cc912e74caa97f18b4da303552672e2d124e256db269a79',
        'bin/c8d2_quad_ranges': 'f616b70b3e5f01d7247f5b2c39fc3d2d231740ab8c31b0a36732b651cbdaacf5',
        'bin/c8d2_interleave_probe': 'b0acd9fb991f3e65507be4d8b4218592a6ac5f48ae23b35f7fe050290e22fca1',
        'bin/c8d2_decimal_san': 'c4013f99', 'bin/c8d2_gmp_san': 'b0e5a786'}  # sanitizers: prefixes of 570514's (path-dependent)
must_equal = ('bin/ref/c7d2_decimal', 'bin/ref/c7d2_gmp')  # make c7ref builds the reference package: the plan's hashes
baseline = {'bin/baseline/c8d2_decimal': 'c121b1e65d540a0a1acc3a12cef5d6a13f7a1279b0a98f2f4e11df941dd08d93',
            'bin/baseline/c8d2_gmp': '23624153cd3e8b45cf8438658c905893689bb9707516038b4717a60c8c26d3a3',
            'bin/prev/c8d2_decimal': prev['bin/c8d2_decimal'], 'bin/prev/c8d2_gmp': prev['bin/c8d2_gmp']}
rd = lambda f: {l.split()[1]: l.split()[0] for l in (E / f).read_text().splitlines()}
got, after, bp = rd('binaries.sha256'), rd('binaries_after_profile.sha256'), rd('baseline_prev.sha256')
rec = {'binaries': {k: {'sha256': got.get(k), 'a42cfb7_570514': v, 'changed': not (got.get(k) or '').startswith(v)} for k, v in prev.items()}}
rec['c7ref_plan_hashes'] = all(not rec['binaries'][k]['changed'] for k in must_equal)
rec['changed'] = sorted(k for k, v in rec['binaries'].items() if v['changed']); rec['unchanged'] = sorted(k for k, v in rec['binaries'].items() if not v['changed'])
rec['baseline_prev'] = {k: {'sha256': bp.get(k), 'want': v, 'equal': bp.get(k) == v} for k, v in baseline.items()}
rec['baseline_prev_ok'] = all(v['equal'] for v in rec['baseline_prev'].values())
rec['defaults_unchanged_by_profile_build'] = got == after
brs = {p.name: json.loads(p.read_text()) for p in sorted((E / 'build_records').glob('*.build.json'))}
own = {k: v for k, v in brs.items() if not k.startswith('ref_')}
rec['build_records'] = {k: {x: v.get(x) for x in ('macro_overrides', 'parameter_overrides', 'development', 'required_flags_present', 'diagnostic',
                                                    'NUMERICS', 'BOOST_LIB_VERSION', 'executable_sha256', 'compiler')} for k, v in own.items()}
rec['z3_macro_overrides_empty'] = all(v.get('macro_overrides') == [] for v in own.values())
rec['no_parameter_overrides'] = all(not v.get('parameter_overrides') and v.get('development') is False for v in own.values())
prod = ('c8d2_decimal.build.json', 'c8d2_gmp.build.json', 'c8d2_gmp_dd+mp256.build.json')
rec['production_required_flags'] = all(own[k].get('required_flags_present') is True for k in prod)
rec['records_describe_their_executables'] = all(own[k].get('executable_sha256') == (got.get('bin/' + k[:-len('.build.json')]) or
                                                                                   (E / 'profile.sha256').read_text().split()[0]) for k in prod)
boost = {k: v.get('BOOST_LIB_VERSION') for k, v in brs.items()}
rec['BOOST_LIB_VERSION'] = boost; rec['boost_1_77_everywhere'] = bool(boost) and all(v == '1_77' for v in boost.values())
d = json.loads((E / 'describe' / 'c8d2_gmp_dd+mp256.json').read_text()); br = own['c8d2_gmp_dd+mp256.build.json']
np_ = d.get('numerics_params') or {}
rec['profile'] = {'sha256': (E / 'profile.sha256').read_text().split()[0], 'previous_gated_build_d5df32ac': 'd5df32ac87d612b2e94cee8dee770160d04f98ce48a421418ce750835f2fc33d',
                  'numerics': d.get('numerics'), 'diagnostic': d.get('diagnostic'), 'numerics_params': np_,
                  'development_overrides': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('development')),
                  'stubs': sorted(k for k, v in np_.items() if isinstance(v, dict) and v.get('stub')),
                  'build_record_numerics': br.get('NUMERICS'), 'build_record_numerics_sources': br.get('numerics_sources'), 'build_record_command': br.get('command')}
rec['profile']['changed'] = rec['profile']['sha256'] != rec['profile']['previous_gated_build_d5df32ac']
rec['profile_ok'] = (d.get('numerics') == 'dd+mp256' and d.get('diagnostic') is False and not rec['profile']['development_overrides']
                     and not rec['profile']['stubs'] and br.get('NUMERICS') == 'dd+mp256')
rec['describe'] = {p.stem: {k: json.loads(p.read_text()).get(k) for k in ('numerics', 'diagnostic', 'orders', 'compiler')} for p in sorted((E / 'describe').glob('*.json'))}
rec['ok'] = (rec['c7ref_plan_hashes'] and rec['baseline_prev_ok'] and rec['defaults_unchanged_by_profile_build'] and rec['z3_macro_overrides_empty']
             and rec['no_parameter_overrides'] and rec['production_required_flags'] and rec['records_describe_their_executables'] and rec['profile_ok']
             and rec['boost_1_77_everywhere'])
(E / 'identity.json').write_text(json.dumps(rec, indent=1) + '\n')
print('changed:', ' '.join(rec['changed'])); print('unchanged:', ' '.join(rec['unchanged']))
print('c7ref = plan hashes:', rec['c7ref_plan_hashes'], '; baseline and prev copies:', rec['baseline_prev_ok'], '; defaults unchanged by the profile build:',
      rec['defaults_unchanged_by_profile_build'], '; macro_overrides [] everywhere (Z3):', rec['z3_macro_overrides_empty'], '; no parameter overrides:',
      rec['no_parameter_overrides'], '; required flags:', rec['production_required_flags'], '; profile ok:', rec['profile_ok'], 'sha', rec['profile']['sha256'][:12],
      '; Boost 1_77:', rec['boost_1_77_everywhere'])
sys.exit(0 if rec['ok'] else 3)
PY
s=$?
if [ $s -eq 0 ]; then
  # 6. the Z4 checks on the real node (they read bin/ and inputs/, write only into the evidence and TMPDIR)
  t0=$(date +%s); C8_GUARDS_OLD_TREE=$PREV python3 -B tests/test_native_guards.py --output "$E/test_native_guards.json" > "$E/test_native_guards.log" 2>&1; g=$?
  echo "test_native_guards exit $g after $(( $(date +%s) - t0 )) s"; tail -4 "$E/test_native_guards.log" | cut -c1-300; [ $g -eq 0 ] || s=5
  t0=$(date +%s); python3 -B tests/validate.py --only bad_inputs --output "$E/validate_bad_inputs.json" > "$E/validate_bad_inputs.log" 2>&1; g=$?
  echo "validate --only bad_inputs exit $g after $(( $(date +%s) - t0 )) s"; tail -3 "$E/validate_bad_inputs.log" | cut -c1-300; [ $g -eq 0 ] || s=5
  sha256sum $X bin/c8d2_gmp_dd+mp256 > "$E/binaries_end.sha256"
  cmp -s <(sort "$E/binaries_end.sha256") <(cat "$E/binaries_after_profile.sha256" "$E/profile.sha256" | sort) || { echo "executables CHANGED by the checks" >&2; s=3; }
fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $s"; exit $s
