#!/usr/bin/env python3
"""SEALED COMPARISON STEP.  Convert the archive-derived raw-coefficient file
(../archive_raw_coefficients.json, written by archive_values.py) into the plain layout
{atom: {p: {k: value}}} accepted by ../../scripts/assemble_from_raw.py.

This loader used to live inside the production assembler; it was moved here so that the
production code path cannot read archive data.  Used only by compare_with_archive.py and by
the reviewer sizing aid ../../review/cancellation_factors.py.
"""
import json
from pathlib import Path

ARCHIVE_RAW = Path(__file__).resolve().parent.parent / 'archive_raw_coefficients.json'


def load_archive_raw(path=ARCHIVE_RAW):
    d = json.load(open(path))
    assert 'raw' in d and isinstance(d['raw'], dict), 'not an archive_raw_coefficients.json layout'
    out = {}
    for atom, ps in d['raw'].items():
        out[atom] = {}
        for p, rec in ps.items():
            cf = {k: v for k, v in rec['coefficients_by_log_power'].items() if v is not None}
            for k in ('0', '1'):   # the archived polynomial is complete: absent log powers are 0
                if k not in rec['coefficients_by_log_power'] and k not in rec['missing_periods_by_log_power']:
                    cf[k] = '0'
            out[atom][p] = cf
    return out


# backward-compatible name (review/cancellation_factors.py used assemble_from_raw.load_raw)
load_raw = load_archive_raw
