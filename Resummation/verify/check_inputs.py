#!/usr/bin/env python3
"""Check the external inputs of Resummation/ against the live files of the sibling folders (new tool, 2026-10-14).

Reads data/inputs/INPUTS.json. For every entry:
  file   our copy (frozen in data/inputs/ or an input inside a code tree) must have its registered sha256, and the live
         sibling file (path relative to the repository root, e.g. NRG/results/ds13_final.json) must be byte-identical;
  value  the value used by the resummation (JSON pointer, text pattern or CSV row/column in the shipped file) must equal the value the
         sibling folder publishes, compared on the digits both give (the shorter decimal string).
Status: PASS if equal, FAIL if different or missing, SKIP if the sibling folder is not in this repository (for example
when Resummation/ is used on its own) or does not exist (the 2d/3d literature extraction: cited in the entry).
Usage: python3 verify/check_inputs.py   (from Resummation/)
"""
import hashlib, json, re, sys
from decimal import Decimal, localcontext
from pathlib import Path

RS = Path(__file__).resolve().parent.parent
REPO = RS.parent
sys.path.insert(0, str(RS/'verify'))
import rsum_lib as L

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def get(base, spec):
    if 'literal' in spec:                       # a value our code computes from an expression, frozen at export (see entry)
        return spec['literal']
    p = base/spec['file']
    if 'csv_key' in spec:                       # {'csv_key': [column, value], 'column': name}: the row whose key equals value
        import csv
        k, v = spec['csv_key']
        rows = [r for r in csv.DictReader(p.open()) if abs(float(r[k]) - float(v)) < 1e-9]
        if len(rows) != 1:
            raise KeyError('%d rows with %s = %s' % (len(rows), k, v))
        return rows[0][spec['column']]
    if 'pointer' in spec:
        o = json.loads(p.read_text())
        for k in spec['pointer'].strip('/').split('/'):
            o = o[int(k)] if isinstance(o, list) else o[k]
        return str(o)
    m = re.search(spec['regex'], p.read_text())
    if not m:
        raise KeyError('pattern not found: ' + spec['regex'])
    return m.group(1)


def same_digits(a, b):
    """Equal on the significant digits of the shorter of two decimal strings (the longer rounded half-even to them)."""
    with localcontext() as ctx:
        ctx.prec = 400
        da, db = Decimal(a.strip()), Decimal(b.strip())
        if da == db:
            return True
        sig = lambda s: len(re.sub(r'[^0-9]', '', s.strip().lstrip('+-').lstrip('0.')))
        n = min(sig(a), sig(b))
        q = lambda d: d.scaleb(-d.adjusted()).quantize(Decimal(1).scaleb(-(n - 1)))
        return da.adjusted() == db.adjusted() and q(da) == q(db)


def main():
    reg = json.loads((RS/'data'/'inputs'/'INPUTS.json').read_text())
    T = L.Table('external inputs (frozen copies and values) against the sibling folders')
    for e in reg['entries']:
        if e['kind'] == 'file':
            ours = RS/e['path']
            if not ours.exists() or sha(ours) != e['sha256']:
                T.add(e['id'], 'FAIL', 'our copy missing or changed', e['sha256'][:16], 'registered sha256'); continue
            if not e['sibling']:
                T.add(e['id'], 'SKIP', 'no sibling folder', '-', e.get('citation', '')[:90]); continue
            folder = REPO/e['sibling'].split('/')[0]
            if not folder.is_dir():
                T.add(e['id'], 'SKIP', 'sibling folder %s absent' % folder.name, '-', e['sibling']); continue
            live = REPO/e['sibling']
            ok = live.exists() and sha(live) == e['sha256']
            T.add(e['id'], 'PASS' if ok else 'FAIL', 'identical' if ok else ('differs' if live.exists() else 'missing'),
                  e['sibling'], 'frozen copy = live sibling file (sha256)')
        else:
            try:
                ours = get(RS, e['used_in'])
            except Exception as x:
                T.add(e['id'], 'FAIL', 'cannot read our value: %s' % x, '-', e['used_in']['file']); continue
            if not e['sibling']:
                T.add(e['id'], 'SKIP', ours[:24], 'no sibling folder yet', e.get('citation', '')[:90]); continue
            folder = REPO/e['sibling']['file'].split('/')[0]
            if not folder.is_dir():
                T.add(e['id'], 'SKIP', ours[:24], 'sibling folder %s absent' % folder.name, e['sibling']['file']); continue
            try:
                theirs = get(REPO, e['sibling'])
            except Exception as x:
                T.add(e['id'], 'FAIL', ours[:24], 'cannot read sibling: %s' % x, e['sibling']['file']); continue
            ok = same_digits(ours, theirs)
            T.add(e['id'], 'PASS' if ok else 'FAIL', ours[:24], theirs[:24], '%s %s (shared digits)' % (
                e['sibling']['file'], e['sibling'].get('pointer', e['sibling'].get('regex', e['sibling'].get('column', '')))))
    return T.report(RS/'.work'/'check_inputs.txt')


if __name__ == '__main__':
    sys.exit(main())
