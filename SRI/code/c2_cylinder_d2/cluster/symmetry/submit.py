#!/usr/bin/env python3
"""Symmetry entry point of cluster/sitekit/submit.py (adds --site symmetry).

  $PY cluster/symmetry/submit.py --check | --stage PILOT|P1|P2 [--submit] | --probe [--submit]
See cluster/symmetry/README.md and cluster/sitekit/submit.py --help.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'sitekit'))
import submit  # noqa: E402

if __name__ == '__main__':
    submit.main(['--site', 'symmetry', *sys.argv[1:]])
