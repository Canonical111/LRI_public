#!/usr/bin/env python3
"""Write HANDOFF_inventory8_d2.json, the H1 handoff of the frozen inventory to C8(3) (PLAN.md A-INV-5).

Refuses (exit 1, nothing written) unless
  * every published copy given with --copy verifies against the pin with gen/verify_inventory.py (all four steps),
    and every copy on another host given with --copy-record PATH=FILE has a verify_inventory.py --output record FILE
    for PATH with the same pin and a pass;
  * every A-INV record is green and complete (Stage-6 finding S6-B-02): each record has schema c8-d2-gate-1, its
    own gate name and passed true, and the test records (test_keys, test_run_l8, test_verify_inventory) no failed
    check and a non-empty list of passed checks; A-INV-1 (test_keys.json, test_run_l8.json); A-INV-2
    (regress_L3_L7.json) with the full coverage of gen/regress.h1_problems: every loop 3..7, both sectors, thread
    identity against 1 thread, every G-file, inventory and header-row check, the side-file controls; A-INV-3 (the
    tree's gates/: gen/gates.summary_problems, the summary and the record of each of the eleven gates, all passed, loops
    7 and 8, no injected failure); A-INV-4 (crossnode.json: MEMBERS.sha256 identical to the tree's); A-INV-5
    (test_verify_inventory.json) and the refused second publication record;
  * DECISIONS.md logs C63d's acknowledgment of the d pipeline (item C1);
  * the HANDOFF file does not exist yet (a later revision adds C63d's gate results or an r2 tree explicitly).
Records the MANIFEST.json sha256 and md5, the date, the gate summary with evidence paths, the D4 pipeline
statement, the checksum hierarchy and the r2 procedure, with empty fields for C63d's pin and gates 1-7 (gate 5:
the forest certificate).

Usage: python3 -B gen/handoff_inventory.py --pin SHA --copy PATH [--copy PATH ...] [--copy-record PATH=FILE ...]
           --evidence DIR
           --decisions .../LRI_C8_shared/inventory/DECISIONS.md --refusal FILE --output .../HANDOFF_inventory8_d2.json
           [--note TEXT ...]
  DIR holds the Stage-1 job records: gen1.*/{test_keys,test_run_l8,test_verify_inventory,regress_L3_L7}.json and
  gen3.*/crossnode.json; FILE is the recorded output of the refused second publication."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

GEN = Path(__file__).resolve().parent
R2 = ('inventory8_d2/ is never modified. A defect found after H1 (by C63d\'s gates 1-7, by C62d\'s tests or later) '
      'is handled by publishing inventory8_d2_r2/ with a new MANIFEST sha256 and a SUPERSEDES.json naming the '
      'defect and the affected classes; this HANDOFF file is then updated and both packages re-pin; C62d reruns '
      'A-IN-3..5 and A-RPL-7 on the affected kernels. Campaigns planned against r1 keep their inputs-manifest pin, '
      'so merge and assemble refuse them under the r2 package; they stay usable only with the commit they were '
      'planned with.')


def load(name: str):
    spec = importlib.util.spec_from_file_location(f'c8d2_gen_{name}', GEN / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# evidence pattern -> the record's gate name; the test records also list their checks
RECORDS = (('A-INV-1 test_keys', 'gen1.*/test_keys.json', 'A-INV-1 test_keys', True),
           ('A-INV-1 injected failing gate', 'gen1.*/test_run_l8.json', 'A-INV-1 injected failing gate (gen/run_l8.sh)',
            True),
           ('A-INV-2 regress', 'gen1.*/regress_L3_L7.json', 'A-INV-2 regress', False),
           ('A-INV-4 crossnode', 'gen3.*/crossnode.json', 'A-INV-4 crossnode', False),
           ('A-INV-5 test_verify_inventory', 'gen1.*/test_verify_inventory.json', 'A-INV-5 test_verify_inventory', True))


def record_problems(j, gate_name: str, checks: bool) -> list[str]:
    """Why a gate record is not a complete pass of gate_name: schema, gate name, passed true; a test record also
    needs failed == [] and a non-empty list of checks, every one passed."""
    if not isinstance(j, dict):
        return ['not a JSON object']
    out = []
    if j.get('schema') != 'c8-d2-gate-1' or j.get('gate') != gate_name:
        out.append(f'schema {j.get("schema")!r} and gate {j.get("gate")!r}, not c8-d2-gate-1 {gate_name!r}')
    if j.get('passed') is not True:
        out.append('not passed')
    if checks:
        c = j.get('checks')
        if j.get('failed') != [] or not isinstance(c, list) or not c or not all(
                isinstance(x, dict) and x.get('passed') is True for x in c):
            out.append('failed checks, or no list of passed checks')
    return out


def one(evidence: Path, pattern: str) -> Path:
    found = sorted(evidence.glob(pattern))
    if len(found) != 1:
        raise SystemExit(f'expected exactly one {pattern} under {evidence}, found {len(found)}')
    return found[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pin', required=True)
    ap.add_argument('--copy', action='append', type=Path, required=True)
    ap.add_argument('--copy-record', action='append', default=[], help='PATH=FILE: a copy verified on another host')
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--decisions', type=Path, required=True)
    ap.add_argument('--refusal', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--note', action='append', default=[], help='a sentence recorded under "notes" (site, pending checks)')
    a = ap.parse_args()
    if a.output.exists():
        raise SystemExit(f'{a.output} exists: a HANDOFF revision is an explicit, separate step')
    problems: list[str] = []
    copies = {}
    for c in a.copy:
        r = subprocess.run([sys.executable, '-B', str(GEN / 'verify_inventory.py'), str(c), '--pin', a.pin],
                           capture_output=True, text=True)
        copies[str(c)] = dict(verified=r.returncode == 0, output=r.stdout.strip().splitlines()[-5:])
        if r.returncode != 0:
            problems.append(f'copy {c} does not verify against the pin')
    for spec in a.copy_record:
        path, sep, fname = spec.partition('=')
        try:
            v = json.loads(Path(fname).read_text()) if sep else {}
        except (OSError, ValueError):
            v = {}
        ok = (bool(sep) and v.get('passed') is True and v.get('pin') == a.pin and v.get('tree', '').rstrip('/')
              == path.rstrip('/'))
        copies[path] = dict(verified=ok, record=fname)
        if not ok:
            problems.append(f'copy record {spec} does not show a pass for that path and pin')
    tree = a.copy[0]
    man_bytes = (tree / 'MANIFEST.json').read_bytes()
    man = json.loads(man_bytes)
    rec = {}
    regress, gates = load('regress'), load('gates')
    for gate, pattern, gate_name, checks in RECORDS:
        p = one(a.evidence, pattern)
        try:
            j = json.loads(p.read_text())
        except ValueError:
            j = None
        why = record_problems(j, gate_name, checks)
        if gate == 'A-INV-2 regress' and isinstance(j, dict):
            why += regress.h1_problems(j)
        rec[gate] = dict(passed=not why, evidence=p.relative_to(a.evidence).as_posix())
        if why:
            problems.append(f'{gate} is not green and complete ({p}): ' + '; '.join(dict.fromkeys(why)))
    cross = json.loads(one(a.evidence, 'gen3.*/crossnode.json').read_text())
    members_sha = hashlib.sha256((tree / 'MEMBERS.sha256').read_bytes()).hexdigest()
    if cross.get('members_sha256') != members_sha or cross.get('reference_members_sha256') != members_sha:
        problems.append('A-INV-4: the cross-node MEMBERS.sha256 is not the published one')
    why3 = gates.summary_problems(tree / 'gates')
    try:
        verdicts = json.loads((tree / 'gates/summary.json').read_text()).get('gates')
    except (OSError, ValueError, AttributeError):
        verdicts = None
    rec['A-INV-3 gates'] = dict(passed=not why3, gates=verdicts, evidence='gates/*.json inside the tree')
    if why3:
        problems.append('A-INV-3 is not green and complete: ' + '; '.join(why3))
    refusal = a.refusal.read_text()
    rec['A-INV-5 second publish refused'] = dict(passed='refusing to publish' in refusal,
                                                 evidence=a.refusal.name)
    if not rec['A-INV-5 second publish refused']['passed']:
        problems.append('no record of a refused second publication')
    log = a.decisions.read_text()
    ack = re.search(r'^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*C1\s*\|\s*ACK', log, re.M)
    if not ack:
        problems.append('DECISIONS.md does not log C63d\'s acknowledgment of the d pipeline (C1)')
    if problems:
        print('refusing to write the HANDOFF:\n  ' + '\n  '.join(problems))
        return 1
    out = dict(
        schema='c8-inventory-d2-handoff-1', handoff='H1', sender='C62d (LRI_C8_D2_HPC)',
        recipient='C63d (LRI_C8_D3_HPC)', date=time.strftime('%Y-%m-%d'),
        manifest_sha256=a.pin, manifest_md5=hashlib.md5(man_bytes).hexdigest(),
        copies={k: v['verified'] for k, v in copies.items()},
        verify_command='python3 -B src/gen/verify_inventory.py <tree> --pin <manifest_sha256> (the verifier is also '
                       'in LRI_C8_D2_HPC/gen/)',
        generating_commit=man.get('git_commit'), generating_jobs=man.get('slurm_job_ids'), host=man.get('host'),
        cpu=man.get('cpu'), counts=man.get('counts'), selection_counts=man.get('selection_counts'),
        payload={k: dict(sha256=v['sha256'], md5=v['md5'], members=v['members']) for k, v in man['payload'].items()},
        gate_summary=rec, d_pipeline=man.get('d_pipeline'),
        d_pipeline_acknowledged=f'DECISIONS.md item C1, ACK logged {ack.group(1)}',
        checksum_hierarchy=man.get('checksum_hierarchy'), member_layout=man.get('member_layout'),
        r2_procedure=R2, notes=a.note,
        c63d=dict(pin_recorded=None, gates_1_7=None, gate_5_forest_certificate=None,
                  note='C63d records here its pin of MANIFEST.json and its gates 1-7 (gate 5: whether the forest '
                       'certificate covers the d=2 identity; a negative result triggers the bare-series identity '
                       'at L8 under the r2 procedure).'))
    a.output.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(written=str(a.output), manifest_sha256=a.pin, manifest_md5=out['manifest_md5']), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
