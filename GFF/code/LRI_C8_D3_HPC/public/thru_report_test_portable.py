#!/usr/bin/env python3
"""tests/thru_report_test.py, rerun with float equality to relative 1e-12 when only the Python version differs.

The verbatim test (production commit 4fbd1bae) re-derives smk4/thru_report.json from the 82 smk4_hook records. It
requires the result to equal the committed smk4/thru_report_s6b.json and thru_report_s6.json field by field. Those
records were written with Python 3.10. Since Python 3.12, sum() of floats uses compensated (Neumaier) summation, so
three re-derived floats move by one unit in the last place:
  - a_orc_13.fit_non_own_on_staged_bytes.slope (rel 1.6e-16);
  - a_perf_3.openmp.L8.time_weighted_mean (rel 2.2e-16);
  - a_perf_3.openmp.all.time_weighted_mean (rel 1.1e-16).
Measured on one Mac: Python 3.10 and 3.11 reproduce the records bitwise, while 3.12 and 3.14 give exactly these three
differences. An Intel Xeon 6148 with Python 3.12 gives the same three (symmetry job 574508), so the CPU plays no part.

This script runs the verbatim test first. Only when it fails with exactly the assertion
"smk4/thru_report_s6b.json is not this re-derivation" does it rerun the same test file (runpy, no copy). In the rerun,
the floats that the test reads with json.loads compare equal within relative 1e-12. Every other check is unchanged,
including the verdicts, counts, medians, efficiencies, sha256 and the remaining stages after that line.
The script says which of the two runs passed.
"""
from __future__ import annotations

import json
import math
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / 'tests/thru_report_test.py'
SIGNATURE = 'smk4/thru_report_s6b.json is not this re-derivation'
REL = 1e-12


class TolFloat(float):
    """A float read from JSON whose == holds within relative REL (the test's other comparisons are untouched)."""

    def __eq__(self, other):
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            a, b = float(self), float(other)
            if not (math.isfinite(a) and math.isfinite(b)):   # inf and NaN compare exactly (json's encoder tests o == inf)
                return a == b
            return a == b or abs(a - b) <= REL * max(abs(a), abs(b))
        return NotImplemented

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    __hash__ = float.__hash__


def main() -> int:
    cp = subprocess.run([sys.executable, '-B', str(TEST)], cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(cp.stdout)
    if cp.returncode == 0:
        print('thru_report_test: verbatim test PASSED')
        return 0
    sys.stderr.write(cp.stderr)
    if SIGNATURE not in cp.stderr:
        return cp.returncode
    print(f'thru_report_test: the verbatim test stops at "{SIGNATURE}", which is expected with Python >= 3.12 '
          f'(this is {sys.version.split()[0]}): sum() of floats changed. Rerunning the same test with float equality to relative '
          f'{REL:g}.', flush=True)
    loads = json.loads

    def tolerant_loads(s, *a, **k):
        k.setdefault('parse_float', TolFloat)
        return loads(s, *a, **k)

    json.loads = tolerant_loads
    sys.argv = [str(TEST)]
    try:
        runpy.run_path(str(TEST), run_name='__main__')
    except SystemExit as e:
        if e.code not in (0, None):
            raise
    print(f'thru_report_test (portable float comparison, rel {REL:g}): PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
