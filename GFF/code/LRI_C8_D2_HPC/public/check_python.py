#!/usr/bin/env python3
"""Preflight of `make -f public.mk test`: does this Python's os.urandom open /dev/urandom at the Python level?

The package's test A-ORC-13 (tests/unit_orchestration.py, test_per_claim_reads) runs one claim under an audit-hook spy
and refuses any Python-level open outside the package, the campaign, the runtime and the platform class. CPython builds
whose os.urandom calls getrandom() (distribution and conda builds) raise no audit event there. Some builds (seen with a
python-build-standalone CPython 3.12.9) read /dev/urandom through a Python-level open instead, which raises the 'open'
audit event; the claim then shows /dev/urandom as a stray read and A-ORC-13 fails although nothing is wrong with the
package. The delivered test is not changed; this check stops `test` first with an explanation. Exit 0: fine; 2: such a
build. Usage: python3 -B public/check_python.py
"""
import sys

seen = []


def hook(event, args):
    if event == 'open' and args and 'urandom' in str(args[0]):
        seen.append(str(args[0]))


sys.addaudithook(hook)
import os  # noqa: E402
import random  # noqa: E402

os.urandom(16)
random.Random()  # seeds from os.urandom, as tempfile's name generator does
if seen:
    print(f'check_python: {sys.executable} (Python {sys.version.split()[0]}) opens {seen[0]} at the Python level for '
          'os.urandom. The claim-read test A-ORC-13 counts that as a stray read and would fail for this reason alone. '
          'Use a CPython whose os.urandom calls getrandom() (for example a distribution or conda build) and rerun; '
          'make -f public.mk test PY=/path/to/python3.', file=sys.stderr)
    sys.exit(2)
print(f'check_python: {sys.executable} (Python {sys.version.split()[0]}): os.urandom does not open /dev/urandom at the '
      'Python level (getrandom); fine for A-ORC-13')
