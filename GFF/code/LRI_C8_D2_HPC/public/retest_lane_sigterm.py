#!/usr/bin/env python3
"""Single rerun of the load-sensitive case lane_sigterm after a failed `make -f public.mk test`.

Usage, from the package folder: make -f public.mk retest-lane-sigterm LOG=<full output of the failed test run>

The case lane_sigterm of tests/unit_orchestration.py has a 0.8 s timing margin in its stuck_native variant (see the
README). On a loaded node one lane can miss it, and the test then fails with a fixed signature. make stops test-python
at that step, so the later steps of test-python do not run. This script:

  1. reads LOG and refuses (exit 2) unless the failure is exactly that one: lane_sigterm is the only failure of
     unit_orchestration, in its stuck_native variant, with lane exit codes [-9, 143] or [143, -9] and
     '1 lane(s) killed after 4 s', and make stopped test-python at the unit_orchestration line of the Makefile;
  2. reruns lane_sigterm alone, once;
  3. runs the steps of test-python after unit_orchestration, copied verbatim from the package Makefile into a make
     fragment in public/out/ and run with that Makefile, so its variables apply unchanged.

Exit 0 only if the rerun and every later step pass. No shipped file is modified.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

MAKE_VARS = ('MAKEFLAGS', 'MFLAGS', 'MAKELEVEL', 'MAKEOVERRIDES', 'GNUMAKEFLAGS')  # as PKGENV in public.mk
CASE = 'lane_sigterm'


def refuse(msg):
    print(f'retest-lane-sigterm: REFUSED: {msg}', file=sys.stderr)
    print('Run the full `make -f public.mk test` again instead; this target covers only the failure in the README.', file=sys.stderr)
    sys.exit(2)


def test_python_recipe(makefile):
    """(prerequisites, [(line number, recipe line)]) of the rule test-python in the package Makefile."""
    lines = makefile.read_text().split('\n')
    heads = [i for i, l in enumerate(lines) if re.match(r'test-python\s*:', l)]
    if len(heads) != 1:
        raise SystemExit(f'retest-lane-sigterm: {makefile}: expected one rule test-python, found {len(heads)}')
    i = heads[0]
    prereq = lines[i].split(':', 1)[1].strip()
    recipe = []
    for j in range(i + 1, len(lines)):
        if not lines[j].startswith('\t'):
            break
        recipe.append((j + 1, lines[j]))
    return prereq, recipe


def check_log(text, orch_line):
    lines = text.split('\n')
    fails = [i for i, l in enumerate(lines) if l.startswith('FAIL ')]
    if len(fails) != 1 or not lines[fails[0]].startswith(f'FAIL {CASE}: AssertionError: (\'stuck_native\','):
        refuse(f'expected exactly one FAIL line, of {CASE} in its stuck_native variant; the log has {len(fails)}: '
               + '; '.join(lines[i][:100] for i in fails[:3]))
    # The FAIL line is cut at 500 characters; the full assertion message ends the traceback printed after it.
    block = []
    for l in lines[fails[0] + 1:]:
        if l.startswith(('PASS ', 'FAIL ', '{"status": ')):
            break
        block.append(l)
    final = [l for l in block if l.startswith("AssertionError: ('stuck_native',")]
    if len(final) != 1:
        refuse(f'no single AssertionError line of the stuck_native variant in the traceback after the FAIL line')
    f = final[0]
    need = ['SIGTERM forwarded to 2 lane(s)', '1 lane(s) killed after 4 s']
    missing = [s for s in need if s not in f]
    codes = [c for c in ('lane exit codes [-9, 143]', 'lane exit codes [143, -9]') if c in f]
    if missing or len(codes) != 1:
        refuse(f'the {CASE} failure lacks the timing signature (missing {missing + ([] if codes else ["lane exit codes [-9, 143] or [143, -9]"])})')
    summaries = []
    for l in text.split('\n'):
        if l.startswith('{"status": '):
            try:
                summaries.append(json.loads(l))
            except ValueError:
                pass
    orch = [s for s in summaries if s.get('requested') == 'all' and 'executed' in s and 'failed' in s]
    if len(orch) != 1 or orch[0].get('status') != 'failed' or orch[0].get('failed') != [CASE]:
        refuse(f'the unit_orchestration summary line is missing or names other failures ({orch})')
    # GNU make >= 4 names the Makefile line ("[Makefile:242: test-python]"); make 3.81 (macOS) names the target only.
    errs = re.findall(r'^make(?:\[\d+\])?: \*\*\* \[(?:Makefile:(\d+): )?([\w-]+)\] Error (\d+)$', text, re.M)
    errs = [e for e in errs if e[1] == 'test-python']
    if len(errs) != 1 or errs[0][0] not in ('', str(orch_line)) or errs[0][2] != '1':
        refuse(f'make did not stop test-python at Makefile:{orch_line} (unit_orchestration) alone; make errors {errs}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--log', required=True, help='full output of the failed `make -f public.mk test` run')
    ap.add_argument('--python', required=True, help='the PY of that run')
    ap.add_argument('--make', default='make')
    ap.add_argument('--out', default='public/out')
    a = ap.parse_args()
    if not a.log:
        refuse('no LOG given: make -f public.mk retest-lane-sigterm LOG=<log of the failed test run>')
    log = Path(a.log)
    if not log.is_file():
        refuse(f'LOG {log} is not a file')
    makefile = Path('Makefile')
    prereq, recipe = test_python_recipe(makefile)
    orch = [k for k, (_, l) in enumerate(recipe) if 'tests/unit_orchestration.py' in l]
    if len(orch) != 1:
        raise SystemExit(f'retest-lane-sigterm: expected one unit_orchestration step in test-python, found {len(orch)}')
    orch_line = recipe[orch[0]][0]
    rest = recipe[orch[0] + 1:]
    check_log(log.read_text(errors='replace'), orch_line)
    print(f'retest-lane-sigterm: {log} shows the timing failure of {CASE} only; make stopped test-python at Makefile:{orch_line}')

    env = {k: v for k, v in os.environ.items() if k not in MAKE_VARS}
    env.update(C8_ALLOW_NO_L8='1', OPENBLAS_NUM_THREADS='1')
    cmd = [a.python, '-B', 'tests/unit_orchestration.py', '--only', CASE]
    print('+ ' + ' '.join(cmd), flush=True)
    if subprocess.run(cmd, env=env).returncode != 0:
        print(f'retest-lane-sigterm: FAIL: {CASE} failed again on its single rerun', file=sys.stderr)
        return 1

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    frag = out / 'test_python_rest.mk'
    frag.write_text(f'# Generated by public/retest_lane_sigterm.py: the recipe lines of test-python after unit_orchestration,\n'
                    f'# copied verbatim from Makefile lines {rest[0][0]}-{rest[-1][0]}. Run as make -f Makefile -f {frag} test-python-rest.\n'
                    f'.PHONY: test-python-rest\ntest-python-rest: {prereq}\n' + ''.join(l + '\n' for _, l in rest))
    cmd = [a.make, '-f', 'Makefile', '-f', str(frag), 'test-python-rest', f'PYTHON={a.python}']
    print(f'+ {" ".join(cmd)}   ({len(rest)} steps, Makefile lines {rest[0][0]}-{rest[-1][0]})', flush=True)
    rc = subprocess.run(cmd, env=env).returncode
    if rc != 0:
        print(f'retest-lane-sigterm: FAIL: a later step of test-python failed (make exit {rc})', file=sys.stderr)
        return 1
    print(f'retest-lane-sigterm: PASS: {CASE} passed on its single rerun and the {len(rest)} later steps of test-python passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
