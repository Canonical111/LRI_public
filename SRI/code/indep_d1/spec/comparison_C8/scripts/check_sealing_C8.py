#!/usr/bin/env python3
"""SEALED C8 STEP: independence hygiene of the C8 extension.
  1. Runtime audit: ../../comparison/scripts/check_sealing.py reruns the WHOLE archive-free pipeline (phase 1 + the C8 scripts)
     in a scratch copy under an audit hook; it fails if anything in the compendium, comparison/ or comparison_C8/ is opened,
     or if a fresh output (out/*.json, out/C8/*.json, spec_definitions.json, spec.json, spec.md) differs byte-wise.  Its
     result (../../comparison/sealing_report.json) is read here.
  2. Static scan: no production script (spec/scripts/*.py, spec/review/*C8*.py) contains a numeric literal whose first 12
     significant digits match a C8 archive number.
  3. Fingerprint scan: every >= 12-digit number in spec_definitions.json (C8_EXTENSION), spec.md, out/C8/*.json and
     review/*C8*.json that matches a C8 archive number must be one of our tagged archive-free values (closed forms evaluated
     here, independent numerics); anything else is a leak.
  4. Reference scan (read-only grep): no file of the project outside spec/comparison_C8 mentions 'comparison_C8' except the
     spec's own documentation, build metadata and the sealing scripts.
Output: ../sealing_report_C8.json
"""
import json, re
from pathlib import Path
import mpmath as mp

HERE = Path(__file__).resolve().parent
CMP = HERE.parent
SPEC = CMP.parent
ROOT = SPEC.parent
NUM_RE = re.compile(r'-?\d+\.\d+(?:[eE][-+]?\d+)?')


def fp(txt):
    d = re.sub(r'[eE].*$', '', txt).lstrip('-').replace('.', '').lstrip('0')
    return d[:12] if len(d) >= 12 else None


rep = {}
s1 = json.load(open(SPEC / 'comparison' / 'sealing_report.json'))
rep['runtime_audit_full_pipeline'] = {'pass': s1['runtime_audit']['pass'], 'violations': s1['runtime_audit']['violations'],
                                      'not_byte_identical': [k for k, v in s1['runtime_audit']['fresh_outputs_byte_identical'].items() if not v],
                                      'scripts_run': list(s1['runtime_audit']['scripts'])}
ARCH = {}
for m in NUM_RE.finditer((CMP / 'archive_C8_values.json').read_text()):
    k = fp(m.group(0))
    if k and set(k) != {'0'}:
        ARCH.setdefault(k, m.group(0))
rep['C8_archive_fingerprints'] = len(ARCH)
lit = []
for f in sorted(list((SPEC / 'scripts').glob('*.py')) + list((SPEC / 'review').glob('*C8*.py'))):
    for m in NUM_RE.finditer(f.read_text()):
        k = fp(m.group(0))
        if k and k in ARCH:
            lit.append(f'{f.relative_to(SPEC)}: {m.group(0)}')
rep['production_literals_matching_C8_archive'] = lit

mp.mp.dps = 60
vt8 = json.load(open(SPEC / 'out' / 'C8' / 'validation_targets_C8.json'))
OURS = [(mp.mpf(t['value']), t['id']) for t in vt8['targets'] if t.get('value') not in (None, 'None')]
OURS += [(mp.mpf(r['value']), r['id']) for r in vt8['independent_values']]
vt1 = json.load(open(SPEC / 'out' / 'validation_targets.json'))     # phase-1 archive-free values (closed forms, independent)
OURS += [(mp.mpf(t['value']), 'phase-1 ' + t['id']) for t in vt1['targets']]
OURS += [(mp.mpf(r['value']), 'phase-1 ' + r['id']) for r in vt1['independent_input_values']]
rg = json.load(open(SPEC / 'out' / 'C8' / 'rg_logs_C8.json'))
for key, logs in rg['C3_jets_all_logs']['jets'].items():
    for k, r in logs.items():
        OURS.append((mp.mpf(r['value']), f'{key} l^{k}'))
        OURS.append((mp.mpf(r['three_kink_independent']), f'{key} l^{k} (three-kink)'))


def explain(x):
    x = mp.mpf(x)
    tol = mp.mpf(10)**-11 * (1 + abs(x))
    for y, tag in OURS:
        if abs(x - y) < tol:
            return tag
    return None


spec_def = json.load(open(SPEC / 'spec_definitions.json'))
texts = {'spec_definitions.json[C8_EXTENSION]': json.dumps(spec_def['C8_EXTENSION']), 'spec.md': (SPEC / 'spec.md').read_text()}
for p in sorted((SPEC / 'out' / 'C8').glob('*.json')):
    texts[str(p.relative_to(SPEC))] = p.read_text()
for p in sorted((SPEC / 'review').glob('*C8*.json')):
    texts[str(p.relative_to(SPEC))] = p.read_text()
leaks, hits = [], {}
for name, txt in texts.items():
    for m in NUM_RE.finditer(txt):
        k = fp(m.group(0))
        if not k or k not in ARCH:
            continue
        why = explain(m.group(0))
        if why is None:
            leaks.append(f'{name}: {m.group(0)} (archive {ARCH[k][:30]})')
        else:
            hits.setdefault(name, {}).setdefault(why, 0)
            hits[name][why] += 1
rep['fingerprint_scan'] = {'files': list(texts), 'leaks': leaks, 'matches_explained_by_our_own_values': hits}

allowed = {'spec/README.md', 'spec/spec.md', 'spec/spec_definitions.json', 'spec/scripts/build_spec.py', 'spec/scripts/c8_block.py',
           'spec/scripts/validation_targets_C8.py', 'spec/scripts/derive_invariants_C8.py', 'spec/comparison/scripts/check_sealing.py',
           'spec/comparison/README.md', 'spec/review/README.md', 'spec/out/C8/validation_targets_C8.json', 'spec/out/C8/invariants_C8.json'}
refs = []
for p in ROOT.rglob('*'):
    if not p.is_file() or p.suffix not in ('.py', '.md', '.json', '.sh', '.txt', '.cpp', '.h', '.slurm') or 'comparison_C8' in str(p):
        continue
    if p.stat().st_size > 5_000_000:
        continue
    try:
        if 'comparison_C8' in p.read_text(errors='ignore'):
            rel = str(p.relative_to(ROOT))
            if rel not in allowed:
                refs.append(rel)
    except Exception:
        pass
rep['files_outside_mentioning_comparison_C8'] = sorted(refs)
rep['PASS'] = rep['runtime_audit_full_pipeline']['pass'] and not lit and not leaks and not refs
json.dump(rep, open(CMP / 'sealing_report_C8.json', 'w'), indent=1)
print('runtime audit', rep['runtime_audit_full_pipeline']['pass'], '| literals', lit, '| leaks', leaks[:5], '| refs', refs)
print('explained', hits)
print('PASS', rep['PASS'])
