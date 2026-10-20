#!/usr/bin/env python3
"""The exact-check key gate of the vendored assembly (PLAN E.1 `tests/fixtures/exact_check_keys.json`, A-ASM-1(a),
A-ASM-4 `--exact`; C62d's R09).

Every leaf of the vendored `exact_check_results.json` (paths joined by "/"; `loop7_exact` and `affinity_order7`,
`affinity_order8` compared as whole values) is in exactly one class:
  exact              compared with the vendored results file by JSON equality (string-equal after canonical dumps);
                     every one required;
  float_diagnostics  checked against its bound (kinds `abs_lt`: |x| < bound; `abs_lt_key`: |x| < |value of the named
                     key|; `near`: |x - center| < tol); the value is reported, never compared for equality;
  provenance         matched by pattern, never compared, recorded apart.
A key in no class, a newly appeared key or a missing required key fails the gate. Without LRI_ROOT the vendored
exact_check.py silently omits the keys that read files under LRI_ROOT (`lri_root_dependent`); `gate(...,
lri_root=False)` requires every other exact key and accepts their absence.
Usage (the classification against the vendored results file): python3 -B tests/exact_keys.py"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / 'tests/fixtures/exact_check_keys.json'
RESULTS = ROOT / 'vendor/c8_assembly/exact_check_results.json'
WHOLE = re.compile(r'^(loop7_exact|affinity_order\d+)$')


def leaves(obj, prefix: str = ''):
    """(path, value) for every leaf; the WHOLE keys are leaves themselves."""
    if isinstance(obj, dict) and not WHOLE.match(prefix):
        for k, v in obj.items():
            yield from leaves(v, f'{prefix}/{k}' if prefix else k)
    else:
        yield prefix, obj


def canon(v) -> str:
    return json.dumps(v, sort_keys=True)


def is_provenance(classes: dict, key: str) -> bool:
    return any(re.match(p, key) for p in classes['provenance_patterns'])


def float_ok(classes: dict, key: str, got: dict) -> tuple[bool, str]:
    spec = classes['float_diagnostics'][key]
    x = float(got[key])
    if spec['kind'] == 'abs_lt':
        return abs(x) < float(spec['bound']), f'|{x!r}| < {spec["bound"]}'
    if spec['kind'] == 'abs_lt_key':
        if spec['bound'] not in got:
            return False, f'bound key {spec["bound"]} missing'
        b = abs(float(got[spec['bound']]))
        return abs(x) < b, f'|{x!r}| < |{spec["bound"]}| = {b!r}'
    if spec['kind'] == 'near':
        c, tol = float(spec['bound'][0]), float(spec['bound'][1])
        return abs(x - c) < tol, f'|{x!r} - ({spec["bound"][0]})| = {abs(x - c)!r} < {tol}'
    return False, f'unknown bound kind {spec["kind"]}'


def check_classes(classes: dict, reference: dict) -> list[str]:
    """The classification covers every leaf of the reference results exactly once, and names no other key."""
    errs = []
    ref = dict(leaves(reference))
    exact, flt = set(classes['exact']), set(classes['float_diagnostics'])
    if exact & flt:
        errs.append(f'keys both exact and float: {sorted(exact & flt)}')
    for k in ref:
        n = (k in exact) + (k in flt) + is_provenance(classes, k)
        if n != 1:
            errs.append(f'leaf {k!r} is in {n} classes')
    for k in sorted((exact | flt) - set(ref)):
        errs.append(f'classified key {k!r} is not a leaf of the results file')
    for p in classes['provenance_patterns']:
        if not any(re.match(p, k) for k in ref):
            errs.append(f'provenance pattern {p!r} matches no leaf')
    dep = classes.get('lri_root_dependent', {})
    for k in dep.get('exact', []):
        if k not in exact:
            errs.append(f'lri_root_dependent key {k!r} is not exact')
    for p in dep.get('provenance_patterns', []):
        if p not in classes['provenance_patterns']:
            errs.append(f'lri_root_dependent pattern {p!r} is not a provenance pattern')
    counts = dict(exact=len(exact), float_diagnostics=len(flt),
                  provenance=sum(1 for k in ref if is_provenance(classes, k)), leaves=len(ref))
    if classes.get('counts') != counts:
        errs.append(f'counts {classes.get("counts")} != {counts}')
    return errs


def gate(classes: dict, reference: dict, result: dict, lri_root: bool = True) -> dict:
    """A run's exact_check.py output against the vendored results file."""
    ref, got = dict(leaves(reference)), dict(leaves(result))
    dep = set(classes.get('lri_root_dependent', {}).get('exact', []))
    errors, exact_ok, absent_dependent = [], 0, []
    for k in classes['exact']:
        if k not in got:
            if not lri_root and k in dep:
                absent_dependent.append(k)
            else:
                errors.append(f'missing exact key {k!r}')
        elif canon(got[k]) != canon(ref[k]):
            errors.append(f'exact key differs: {k!r}: {canon(got[k])[:200]} != {canon(ref[k])[:200]}')
        else:
            exact_ok += 1
    floats = {}
    for k in classes['float_diagnostics']:
        if k not in got:
            errors.append(f'missing float key {k!r}')
            continue
        ok, how = float_ok(classes, k, got)
        floats[k] = dict(value=got[k], reference=ref.get(k), check=how, passed=ok)
        if not ok:
            errors.append(f'float diagnostic out of bound: {k!r}: {how}')
    provenance = {k: v for k, v in got.items() if is_provenance(classes, k)}
    for k in got:
        if k not in classes['exact'] and k not in classes['float_diagnostics'] and k not in provenance:
            errors.append(f'unclassified or new key {k!r}')
    return dict(passed=not errors, errors=errors, exact_equal=exact_ok, exact_required=len(classes['exact']) - len(
        absent_dependent), absent_lri_root_dependent=absent_dependent, float_diagnostics=floats, provenance=provenance)


def main() -> int:
    classes = json.loads(KEYS.read_bytes())
    reference = json.loads(RESULTS.read_bytes())
    errs = check_classes(classes, reference)
    self_gate = gate(classes, reference, reference)
    print(json.dumps(dict(classification_errors=errs, self_gate=dict(passed=self_gate['passed'],
                                                                         errors=self_gate['errors'])), indent=1))
    return 0 if not errs and self_gate['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
