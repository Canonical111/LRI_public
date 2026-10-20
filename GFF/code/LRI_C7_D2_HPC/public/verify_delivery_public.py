#!/usr/bin/env python3
"""The delivered verifier tools/verify_delivery.py, run unchanged on the public tree, with the merged notes accounted for.

The TeX notes of reference/ (the earlier seventh-order calculation's method note, its template and the progress note of
its power-free campaign, with their PDFs) are merged into the condensed note GFF/note (author rule 2026-10-16: one TeX
note per direction) and are not shipped. DELIVERY_MANIFEST.json, SHA256SUMS and the other checksum lists ship unchanged,
so the delivered verifier reports these five files as missing. This wrapper imports the delivered verify() without
modifying it, accepts exactly the 'Missing regular file' errors of MERGED_NOTES (one INFO row), and fails on any other
error, on a merged note that is present, and on a MERGED_NOTES path that the manifest does not list.
Prints the delivered report (JSON) with the reclassification added; exit status 0 only if nothing else is wrong.
Usage: python3 -B public/verify_delivery_public.py [--root DIR]
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
MERGED_NOTES = ('reference/notes/C7_d2_complete.tex', 'reference/notes/C7_d2_complete.pdf',
                'reference/notes/C7_d2_complete_template.tex',
                'reference/LRI_C7_d2_progress/notes/C7_d2_progress.tex',
                'reference/LRI_C7_d2_progress/notes/C7_d2_progress.pdf')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=PKG)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('verify_delivery_delivered', a.root / 'tools/verify_delivery.py')
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    try:
        report = vd.verify(a.root, strict=False)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        report = dict(status='failed', errors=[str(exc)])
        print(json.dumps(report, indent=2))
        return 1
    listed = {row['path'] for row in json.loads((a.root / 'DELIVERY_MANIFEST.json').read_text())['files']}
    accepted = {'Missing regular file: ' + p for p in MERGED_NOTES}
    others = [e for e in report['errors'] if e not in accepted]
    gone = sorted(e[len('Missing regular file: '):] for e in report['errors'] if e in accepted)
    problems = list(others)
    problems += ['merged note present (it should not be shipped): ' + p for p in MERGED_NOTES if (a.root / p).exists()]
    problems += ['MERGED_NOTES path not in DELIVERY_MANIFEST.json: ' + p for p in MERGED_NOTES if p not in listed]
    report['delivered_status'] = report['status']
    report['merged_notes_not_shipped'] = gone
    report['status'] = 'passed' if not problems else 'failed'
    report['errors'] = problems
    print(json.dumps(report, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
