#!/usr/bin/env python3
"""Check the delivered note's references and optionally its distribution hashes.
Uses the Python standard library only; does not evaluate research integrals.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checksums', action='store_true', help='Also verify exact delivered file hashes.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    text = (root / 'long_range_ising_condensed.tex').read_text(encoding='utf-8')
    labels = re.findall(r'\\label\{([^}]+)\}', text)
    refs = re.findall(r'\\(?:eqref|ref|pageref|autoref|nameref)\{([^}]+)\}', text)
    citations = {v.strip() for a in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}', text) for v in a.split(',')}
    bibliography = set(re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}', text))
    errors = []
    missing_refs = sorted(set(refs) - set(labels))
    duplicates = [k for k, v in Counter(labels).items() if v > 1]
    missing_cites = sorted(citations - bibliography)
    if missing_refs: errors.append(f'Unresolved references: {missing_refs}')
    if duplicates: errors.append(f'Duplicate labels: {duplicates}')
    if missing_cites: errors.append(f'Missing bibliography entries: {missing_cites}')
    if args.checksums:
        manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            p = root / item['path']
            if not p.is_file():
                errors.append(f'Missing file: {item["path"]}')
            elif hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
                errors.append(f'Hash mismatch: {item["path"]}')
        print(f'Checked {len(manifest["files"])} distribution files.')
    print(f'{len(labels)} labels; {len(citations)} cited sources.')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Structural checks passed. No numerical or field-theory validation is implied.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
