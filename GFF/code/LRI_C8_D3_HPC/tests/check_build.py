#!/usr/bin/env python3
"""Build records of the native binaries (PLAN.md C.8, HD9, A-KER-3; F row check_build.py).

  python3 -B tests/check_build.py --expect-gcc 13.3.0 --expect-boost 107700 --expect-gmp-lib "$C8_GMP/lib" \\
      --expect-gmp-version 6.2.1 bin/c8d3_gmp.buildinfo.json bin/c8d3_decimal.buildinfo.json \\
      bin/ref/c7d3_gmp.buildinfo.json bin/ref/c7d3_decimal.buildinfo.json [--output FILE]      (Expanse, every build job)
  python3 -B tests/check_build.py --expect-gcc 11.4.0 --expect-boost 107700 --expect-gmp-lib /usr/lib/x86_64-linux-gnu \\
      --expect-gmp-version 6.2.1 --gmp-search system RECORD...                               (symmetry, Amendment A1)
  python3 -B tests/check_build.py --selftest                                                  (Mac: canned outputs)

Each named record must exist (a missing one fails with a message) and have schema c8-d3-buildinfo-1, its binary's
sha256, a compiler_version naming g++ --expect-gcc, boost_version --expect-boost, no C8_TEST_UNGUARDED_INDEX in its
command (only the self-test binary may carry it), and a "backend" equal to the command's (-DC7_USE_GMP: gmp, else
decimal) and to --describe's mp_backend (gmp350 / decimal300). tools/libprobe.py is re-run on the binary and its
result must equal the recorded one (NEEDED, RPATH/RUNPATH, the libgmp block). By backend:
  * GMP builds: libgmp.so.10 NEEDED, --expect-gmp-lib in RPATH/RUNPATH (--gmp-search rpath, the default: Expanse's
    Spack GMP; --gmp-search system, symmetry's system GMP, requires no RPATH), env -i ldd and the loader trace both resolving
    realpath(--expect-gmp-lib/libgmp.so.10), whose own version is --expect-gmp-version; and for bin/c8d3_gmp (schema
    c8-d3-build-1) the self-report: gmp.applicable true, gmp.runtime_version equal to the probe's version and
    gmp.library equal to the probe's realpath. bin/ref/c7d3_gmp (whose --describe has no gmp field) is judged by the
    probe alone.
  * Decimal builds: no libgmp in NEEDED, the ldd resolution or the loader trace ("not_applicable"); bin/c8d3_decimal
    reports {"applicable": false}.
--selftest runs the same decision function on canned records and canned readelf / ldd / LD_DEBUG outputs, and
requires these to fail: a GMP record whose probe resolves /lib64/libgmp.so.10 (6.1.2); a bin/c8d3_gmp whose
self-report differs from the probe; a decimal record with libgmp in NEEDED; a missing record; a record whose command
carries the test-only macro; and a good GMP and a good decimal record to pass. Symmetry's toolchain (Ubuntu 22.04 g++
11.4.0, Boost 1.77, the system GMP 6.2.1 that ldd finds as /lib/x86_64-linux-gnu/libgmp.so.10, realpath
/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1, no RPATH): a good record passes under --gmp-search system and fails under
the default rpath rule; one resolving another GMP (6.3.0 in /opt), one built by g++ 13.3.0, and an Expanse record
(g++ 13.3.0 and the Spack GMP) fail against the symmetry expectations.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import libprobe  # noqa: E402
from common import digest  # noqa: E402

SCHEMA = 'c8-d3-buildinfo-1'
BACKEND_OF_MP = {'gmp350': 'gmp', 'decimal300': 'decimal'}
PROBE_KEYS = ('needed', 'rpath', 'runpath', 'libgmp')


def judge(rec: dict, probe_now: dict, o: argparse.Namespace, sha_ok: bool = True, realpath=None) -> list[str]:
    """Every problem of one build record, given the probe re-run now (pure function; the self-test feeds canned data)."""
    realpath = realpath or __import__('os').path.realpath
    bad = []
    if rec.get('schema') != SCHEMA:
        bad.append(f'schema {rec.get("schema")!r} is not {SCHEMA}')
    if not sha_ok:
        bad.append('the binary\'s sha256 differs from the record')
    cv = rec.get('compiler_version') or ''
    if o.expect_gcc and not ('g++' in cv and o.expect_gcc in cv):
        bad.append(f'compiler_version {cv!r} is not g++ {o.expect_gcc}')
    if o.expect_boost is not None and rec.get('boost_version') != o.expect_boost:
        bad.append(f'boost_version {rec.get("boost_version")} is not {o.expect_boost}')
    cmd = rec.get('command') or []
    if any('C8_TEST_UNGUARDED_INDEX' in t for t in cmd):
        bad.append('the command carries the test-only macro C8_TEST_UNGUARDED_INDEX')
    want = 'gmp' if '-DC7_USE_GMP' in cmd else 'decimal'
    desc = rec.get('describe') or {}
    if rec.get('backend') != want or BACKEND_OF_MP.get(desc.get('mp_backend')) != want:
        bad.append(f'backend {rec.get("backend")!r}, command {want}, --describe mp_backend {desc.get("mp_backend")!r} disagree')
    old = rec.get('libprobe') or {}
    if {k: old.get(k) for k in PROBE_KEYS} != {k: probe_now.get(k) for k in PROBE_KEYS}:
        bad.append(f'the library probe now differs from the record: now {[probe_now.get(k) for k in PROBE_KEYS]}, '
                   f'recorded {[old.get(k) for k in PROBE_KEYS]}')
    if want == 'gmp':
        bad += libprobe.gmp_problems(probe_now, o.expect_gmp_lib, o.expect_gmp_version, realpath=realpath,
                                     search=getattr(o, 'gmp_search', 'rpath'))
        if desc.get('schema') == 'c8-d3-build-1':
            g = desc.get('gmp') or {}
            pg = probe_now.get('libgmp') if isinstance(probe_now.get('libgmp'), dict) else {}
            if not (g.get('applicable') is True and g.get('runtime_version') == pg.get('version')
                    and g.get('library') == pg.get('ldd_realpath')):
                bad.append(f'the self-report {g} differs from the probe (version {pg.get("version")}, library {pg.get("ldd_realpath")})')
    else:
        bad += libprobe.decimal_problems(probe_now)
        if desc.get('schema') == 'c8-d3-build-1' and desc.get('gmp') != {'applicable': False}:
            bad.append(f'a decimal build reports gmp {desc.get("gmp")}')
    return bad


def check_paths(paths, o) -> dict:
    out, ok = {}, True
    for p in paths:
        p = Path(p)
        if not p.exists():
            out[str(p)] = [f'{p}: missing build record (make writes it)']
            ok = False
            continue
        rec = json.loads(p.read_text())
        binary = p.with_name(p.name[:-len('.buildinfo.json')])
        sha_ok = binary.exists() and digest(binary) == rec.get('sha256')
        bad = judge(rec, libprobe.probe(binary), o, sha_ok)
        out[str(p)] = bad
        ok = ok and not bad
    return {'passed': ok, 'records': out}


# ---- self-test on canned outputs ---------------------------------------------------------------------------------
SPACK = '/cm/shared/apps/spack/0.21.2/cpu/a/opt/spack/linux-rocky8-zen2/gcc-13.3.0/gmp-6.2.1-eywq454gcb355knxklm3gnfrkmj3nscw/lib'
READELF_GMP = f''' 0x0000000000000001 (NEEDED)             Shared library: [libquadmath.so.0]
 0x0000000000000001 (NEEDED)             Shared library: [libgmp.so.10]
 0x0000000000000001 (NEEDED)             Shared library: [libstdc++.so.6]
 0x000000000000000f (RPATH)              Library rpath: [{SPACK}:/cm/shared/apps/spack/0.21.2/cpu/a/opt/spack/gcc-13.3.0/lib64]
'''
READELF_DEC = ''' 0x0000000000000001 (NEEDED)             Shared library: [libquadmath.so.0]
 0x0000000000000001 (NEEDED)             Shared library: [libstdc++.so.6]
'''
LDD_GMP = f'''	linux-vdso.so.1 (0x00007ffd)
	libquadmath.so.0 => /cm/gcc/lib64/libquadmath.so.0 (0x00007f1)
	libgmp.so.10 => {SPACK}/libgmp.so.10 (0x00007f2)
'''
LDD_SYS = '''	libquadmath.so.0 => /cm/gcc/lib64/libquadmath.so.0 (0x00007f1)
	libgmp.so.10 => /lib64/libgmp.so.10 (0x00007f2)
'''
LDD_DEC = '''	libquadmath.so.0 => /cm/gcc/lib64/libquadmath.so.0 (0x00007f1)
'''
TRACE_GMP = f'''     12345:	calling init: /cm/gcc/lib64/libquadmath.so.0
     12345:	calling init: {SPACK}/libgmp.so.10
'''
TRACE_SYS = '''     12345:	calling init: /lib64/libgmp.so.10
'''
# symmetry (Ubuntu 22.04, merged /usr): the system GMP, no RPATH
SYM_LIB = '/usr/lib/x86_64-linux-gnu'
READELF_SYM = ''' 0x0000000000000001 (NEEDED)             Shared library: [libquadmath.so.0]
 0x0000000000000001 (NEEDED)             Shared library: [libgmp.so.10]
 0x0000000000000001 (NEEDED)             Shared library: [libstdc++.so.6]
'''
LDD_SYM = '''	libquadmath.so.0 => /lib/x86_64-linux-gnu/libquadmath.so.0 (0x00007f1)
	libgmp.so.10 => /lib/x86_64-linux-gnu/libgmp.so.10 (0x00007f2)
'''
TRACE_SYM = '''     12345:	calling init: /lib/x86_64-linux-gnu/libgmp.so.10
'''
LDD_OPT = '''	libgmp.so.10 => /opt/gmp-6.3.0/lib/libgmp.so.10 (0x00007f2)
'''
TRACE_OPT = '''     12345:	calling init: /opt/gmp-6.3.0/lib/libgmp.so.10
'''


def selftest() -> dict:
    o = argparse.Namespace(expect_gcc='13.3.0', expect_boost=107700, expect_gmp_lib=SPACK, expect_gmp_version='6.2.1')
    real = {f'{SPACK}/libgmp.so.10': f'{SPACK}/libgmp.so.10.4.1', '/lib64/libgmp.so.10': '/usr/lib64/libgmp.so.10.3.2',
            '/lib/x86_64-linux-gnu/libgmp.so.10': f'{SYM_LIB}/libgmp.so.10.4.1', f'{SYM_LIB}/libgmp.so.10': f'{SYM_LIB}/libgmp.so.10.4.1',
            '/opt/gmp-6.3.0/lib/libgmp.so.10': '/opt/gmp-6.3.0/lib/libgmp.so.10.5.0'}
    realpath = lambda p: real.get(p, p)  # noqa: E731
    version = lambda p: {'/usr/lib64/libgmp.so.10.3.2': '6.1.2', '/opt/gmp-6.3.0/lib/libgmp.so.10.5.0': '6.3.0'}.get(p, '6.2.1')  # noqa: E731

    def probe(readelf, ldd, trace):
        return libprobe.summarize(libprobe.parse_readelf(readelf), libprobe.parse_ldd(ldd), libprobe.parse_ld_debug(trace),
                                  realpath=realpath, version=version)

    def record(name, cmd_gmp, probe_rec, describe):
        cmd = ['g++', '-O3', '-std=c++17', '-fopenmp', '-ffp-contract=off', '-fno-fast-math', *(['-DC7_USE_GMP'] if cmd_gmp else []),
               'src/c8d3_integrate.cpp', '-lquadmath', *(['-lgmp'] if cmd_gmp else []), '-o', f'bin/{name}']
        return {'schema': SCHEMA, 'binary': name, 'command': cmd, 'compiler_version': 'g++ (GCC) 13.3.0', 'boost_version': 107700,
                'describe': describe, 'sha256': 'x', 'backend': 'gmp' if cmd_gmp else 'decimal', 'libprobe': probe_rec}
    good_gmp = probe(READELF_GMP, LDD_GMP, TRACE_GMP)
    sys_gmp = probe(READELF_GMP, LDD_SYS, TRACE_SYS)
    dec = probe(READELF_DEC, LDD_DEC, '')
    dec_needed = probe(READELF_GMP, LDD_DEC, '')
    self_ok = {'schema': 'c8-d3-build-1', 'mp_backend': 'gmp350', 'gmp': {'applicable': True, 'header_version': '6.2.1', 'runtime_version': '6.2.1',
                                                                          'library': f'{SPACK}/libgmp.so.10.4.1'}}
    self_bad = {**self_ok, 'gmp': {**self_ok['gmp'], 'library': '/usr/lib64/libgmp.so.10.3.2', 'runtime_version': '6.1.2'}}
    c7 = {'schema': 'c7-d3-build-1', 'mp_backend': 'gmp350'}
    cases = {
        'good_c8_gmp': (record('c8d3_gmp', True, good_gmp, self_ok), good_gmp, True),
        'good_c8_decimal': (record('c8d3_decimal', False, dec, {'schema': 'c8-d3-build-1', 'mp_backend': 'decimal300', 'gmp': {'applicable': False}}), dec, True),
        'good_ref_gmp_probe_only': (record('c7d3_gmp', True, good_gmp, c7), good_gmp, True),
        'gmp_record_resolving_system_6.1.2': (record('c7d3_gmp', True, sys_gmp, c7), sys_gmp, False),
        'c8_gmp_self_report_differs': (record('c8d3_gmp', True, good_gmp, self_bad), good_gmp, False),
        'decimal_with_libgmp_needed': (record('c8d3_decimal', False, dec_needed, {'schema': 'c8-d3-build-1', 'mp_backend': 'decimal300', 'gmp': {'applicable': False}}), dec_needed, False),
        'probe_changed_since_build': (record('c7d3_gmp', True, good_gmp, c7), sys_gmp, False),
    }
    rec_macro = record('c8d3_gmp', True, good_gmp, self_ok)
    rec_macro['command'] = rec_macro['command'][:-2] + ['-DC8_TEST_UNGUARDED_INDEX'] + rec_macro['command'][-2:]
    cases['command_with_test_macro'] = (rec_macro, good_gmp, False)
    out = {}
    for name, (rec, now, want_pass) in cases.items():
        bad = judge(rec, now, o, True, realpath=realpath)
        if (not bad) != want_pass:
            raise AssertionError(f'check_build --selftest: {name}: expected {"pass" if want_pass else "failure"}, got {bad}')
        out[name] = 'passed' if not bad else bad
    # symmetry (Amendment A1): g++ 11.4.0, Boost 1.77, the system GMP 6.2.1, no RPATH (--gmp-search system)
    sym = argparse.Namespace(expect_gcc='11.4.0', expect_boost=107700, expect_gmp_lib=SYM_LIB, expect_gmp_version='6.2.1', gmp_search='system')
    sym_rpath = argparse.Namespace(**{**vars(sym), 'gmp_search': 'rpath'})
    good_sym = probe(READELF_SYM, LDD_SYM, TRACE_SYM)
    opt_sym = probe(READELF_SYM, LDD_OPT, TRACE_OPT)
    sym_self = {**self_ok, 'gmp': {**self_ok['gmp'], 'library': f'{SYM_LIB}/libgmp.so.10.4.1'}}

    def sym_record(name, cmd_gmp, probe_rec, describe, gcc='g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0'):
        return {**record(name, cmd_gmp, probe_rec, describe), 'compiler_version': gcc}
    sym_dec = {'schema': 'c8-d3-build-1', 'mp_backend': 'decimal300', 'gmp': {'applicable': False}}
    sym_cases = {
        'symmetry_good_c8_gmp': (sym, sym_record('c8d3_gmp', True, good_sym, sym_self), good_sym, True),
        'symmetry_good_ref_gmp_probe_only': (sym, sym_record('c7d3_gmp', True, good_sym, c7), good_sym, True),
        'symmetry_good_c8_decimal': (sym, sym_record('c8d3_decimal', False, dec, sym_dec), dec, True),
        'symmetry_record_under_the_rpath_rule': (sym_rpath, sym_record('c8d3_gmp', True, good_sym, sym_self), good_sym, False),
        'symmetry_resolving_gmp_6.3.0_in_opt': (sym, sym_record('c7d3_gmp', True, opt_sym, c7), opt_sym, False),
        'symmetry_built_by_gcc_13.3.0': (sym, sym_record('c8d3_gmp', True, good_sym, sym_self, gcc='g++ (GCC) 13.3.0'), good_sym, False),
        'expanse_record_against_symmetry': (sym, record('c8d3_gmp', True, good_gmp, self_ok), good_gmp, False),
    }
    for name, (oo, rec, now, want_pass) in sym_cases.items():
        bad = judge(rec, now, oo, True, realpath=realpath)
        if (not bad) != want_pass:
            raise AssertionError(f'check_build --selftest: {name}: expected {"pass" if want_pass else "failure"}, got {bad}')
        out[name] = 'passed' if not bad else bad
    missing = check_paths(['/nonexistent/bin/c8d3_gmp.buildinfo.json'], o)
    if missing['passed']:
        raise AssertionError('check_build --selftest: a missing record passed')
    out['missing_record'] = missing['records']
    return {'status': 'passed', 'selftest': out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('records', nargs='*')
    ap.add_argument('--expect-gcc', default='13.3.0')
    ap.add_argument('--expect-boost', type=int, default=107700)
    ap.add_argument('--expect-gmp-lib')
    ap.add_argument('--expect-gmp-version', default='6.2.1')
    ap.add_argument('--gmp-search', choices=('rpath', 'system'), default='rpath',
                    help='rpath: --expect-gmp-lib must be in RPATH/RUNPATH (Expanse); system: the loader\'s default search finds it, no RPATH (symmetry)')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    if a.selftest:
        r = selftest()
    else:
        if not a.records or not a.expect_gmp_lib:
            ap.error('records and --expect-gmp-lib are required (or --selftest)')
        r = check_paths(a.records, a)
        r['status'] = 'passed' if r['passed'] else 'failed'
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(r, indent=2))
    return 0 if r['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
