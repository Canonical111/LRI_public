#!/usr/bin/env python3
"""Check results/sr_values.json against the exported tree (new tool, 2026-10-15; standard library only).

Every published value that names a "file" and a JSON "pointer" (RFC 6901) is resolved in the tree and must carry the
same digits: a string leaf equal to the published string (a trailing "..." of the record is ignored), a number leaf
whose repr equals it, a list elementwise. The uncertainty is checked the same way when it has its own pointer.
Literature values and values without a pointer give INFO rows. Run from SRI/:  python3 verify/check_sr_values.py
"""
import json, sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERIFY = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY))
import sri_lib as L  # noqa: E402

SRI = VERIFY.parent
REPO = SRI.parent


def resolve(doc, pointer):
    x = doc
    for raw in pointer.lstrip('/').split('/'):
        k = raw.replace('~1', '/').replace('~0', '~')
        x = x[int(k)] if isinstance(x, list) else x[k]
    return x


def same(published, leaf):
    if isinstance(leaf, list) and isinstance(published, list):
        return len(leaf) == len(published) and all(same(p, l) for p, l in zip(published, leaf))
    if isinstance(leaf, str):
        a, b = published.rstrip('.'), leaf.rstrip('.').strip()
        if a == b:
            return True
        try:
            return Decimal(a) == Decimal(b)
        except InvalidOperation:
            return False
    if isinstance(leaf, (int, float)) and not isinstance(leaf, bool):
        return published == repr(leaf) or Decimal(published) == Decimal(repr(leaf))
    return False


def walk(node, path, out):
    if isinstance(node, dict) and 'value' in node and 'status' in node:
        out.append((path, node)); return
    if isinstance(node, dict):
        for k, v in node.items():
            if path == '' and k == 'packages':
                continue
            walk(v, path + '/' + k, out)


def main():
    pub = json.loads((SRI/'results'/'sr_values.json').read_text())
    entries = []
    walk(pub, '', entries)
    T = L.Table('SRI results/sr_values.json against the exported tree')
    for path, e in entries:
        if not (e.get('file') and e.get('pointer')):
            T.add(path, 'INFO', e['value'] if isinstance(e['value'], str) else ', '.join(e['value']), e['status'],
                  'no pointer: ' + str(e.get('source', ''))[:60])
            continue
        f = REPO/e['file']
        if not f.exists():
            T.add(path, 'SKIP' if not (SRI/'code'/e.get('package', '?')).exists() else 'FAIL', '(missing)', e['file'],
                  'package not in this tree' if not (SRI/'code'/e.get('package', '?')).exists() else 'file missing')
            continue
        doc = json.loads(f.read_text())
        try:
            leaf = resolve(doc, e['pointer'])
        except (KeyError, IndexError, ValueError):
            T.add(path, 'FAIL', '(pointer not found)', e['pointer'], e['file']); continue
        ok = same(e['value'], leaf)
        if ok and e.get('uncertainty_pointer') and 'uncertainty' in e:
            ok = same(e['uncertainty'], resolve(doc, e['uncertainty_pointer']))
        shown = e['value'] if isinstance(e['value'], str) else ', '.join(e['value'])
        T.check(path, ok, shown[:40], e['file'].split('/', 3)[-1][:40] + ' ' + e['pointer'], 'digits equal (' + e['status'] + ')')
    sys.exit(T.report())


if __name__ == '__main__':
    main()
