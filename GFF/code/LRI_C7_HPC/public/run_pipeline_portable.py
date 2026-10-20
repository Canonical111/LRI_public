#!/usr/bin/env python3
"""Portable run of tests/test_pipeline.py (which ships verbatim and runs first in `make -f public.mk test`).

One check of tests/test_pipeline.py (section "--original is unchanged ...") compares the live reassembly of the archived
calculation with the committed fixture tests/fixtures/assemble_original_0227dc5.json by exact dict equality (o0==o1).
That holds on the platform that wrote the fixture but not everywhere: on symmetry AMD nodes (numpy 1.24.3) the floats
differ in the last bits, as in tests/validate.py. public.mk calls this script only when test_pipeline.py failed at
exactly that assertion. It runs the WHOLE test again from a work copy in which that one comparison is replaced by a
float comparison at 1e-12 relative (1e-12 absolute below 1); every other line is unchanged. The copy lives in
.work/portable_tests/, a mirror of the package whose entries are symbolic links to the shipped files, so the test finds
its ROOT, tools and fixtures as usual. Nothing shipped is modified.
"""
import os, subprocess, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
OLD = "and o0==o1"
NEW = "and _close(o0,o1)"
HELPER = '''
def _close(a, b, rtol=1e-12):  # public/run_pipeline_portable.py: float comparison instead of exact equality
    if isinstance(a, dict): return isinstance(b, dict) and a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list): return isinstance(b, list) and len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= rtol * max(1.0, abs(a), abs(b))
    return a == b
'''


def main() -> int:
    work = PKG / '.work' / 'portable_tests'
    if work.exists():
        subprocess.run(['rm', '-rf', str(work)], check=True)
    (work / 'tests').mkdir(parents=True)
    for e in PKG.iterdir():
        if e.name not in ('.work', 'tests'):
            os.symlink(e, work / e.name)
    for e in (PKG / 'tests').iterdir():
        if e.name != 'test_pipeline.py':
            os.symlink(e, work / 'tests' / e.name)
    src = (PKG / 'tests/test_pipeline.py').read_text()
    if src.count(OLD) != 1:
        sys.exit(f'test_pipeline.py: expected the comparison {OLD!r} exactly once, found {src.count(OLD)}')
    lines = src.split('\n'); roots = [k for k, l in enumerate(lines) if l.startswith('ROOT=')]
    if len(roots) != 1:  # the helper goes right after the module's ROOT= line (the first 'def' is inside the fake integrator string)
        sys.exit(f'test_pipeline.py: expected one module-level ROOT= line, found {len(roots)}')
    i = roots[0] + 1
    patched = '\n'.join(lines[:i]) + '\n' + HELPER + '\n' + '\n'.join(lines[i:])
    (work / 'tests/test_pipeline.py').write_text(patched.replace(OLD, NEW))
    print('tests/test_pipeline.py: rerunning with the archived-baseline comparison at 1e-12 relative (copy in .work/portable_tests)', flush=True)
    return subprocess.run([sys.executable, str(work / 'tests/test_pipeline.py')], env=dict(os.environ, OPENBLAS_NUM_THREADS='1')).returncode


if __name__ == '__main__':
    sys.exit(main())
