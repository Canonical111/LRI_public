#!/usr/bin/env python3
"""Expanse entry point of cluster/sitekit/submit.py (adds --site expanse).

  $PY cluster/expanse/submit.py --check | --stage PILOT|P1|P2 [--submit] | --probe [--submit]
See cluster/expanse/README.md and cluster/sitekit/submit.py --help.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'sitekit'))
import submit  # noqa: E402

if __name__ == '__main__':
    submit.main(['--site', 'expanse', *sys.argv[1:]])
