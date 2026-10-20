#!/usr/bin/env python3
"""A-INV-5: gen/handoff_inventory.py writes HANDOFF_inventory8_d2.json only when everything is green and complete,
and gen/publish_inventory.py publishes only a stage whose A-INV-3 gates are complete.
Pure logic on miniature trees and synthetic evidence records, seconds.

Checks:
  * the HANDOFF is written from complete evidence: the tree's gates/ holds the summary and a passed record of each of
    the eleven A-INV-3 gates; the test records list their passed checks; the A-INV-2 record covers every loop 3..7,
    both sectors and thread identity against 1 thread (gen/test_regress.synthetic_h1_record); and the HANDOFF is
    never overwritten;
  * Stage-6 finding S6-B-02, refused with nothing written: an A-INV-2 record of `regress.py --loops 3 --threads 1`, one
    with no loop, one with a single thread count, a bare `{"passed": true}` test record, a tree whose gates/summary.json
    records only a_zero_dim (the evidence this test accepted before the fix), a complete summary with a gate record
    missing or red;
  * as before: a red A-INV record, no C1 acknowledgment, a copy that does not verify, a remote copy record that is no
    pass;
  * publication (publish_inventory.py build on a miniature stage): a stage whose summary records only a_zero_dim, or
    whose j_rates record is red, is refused before anything is written; the complete stage is published and verifies.
Usage: python3 -B gen/test_handoff_inventory.py [--output FILE]"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GEN = Path(__file__).resolve().parent
ROOT = GEN.parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, GEN / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tvi = load('test_verify_inventory')
treg = load('test_regress')
GATES = load('gates').GATES


def gate_files(gates=GATES, red=(), missing=()) -> dict[str, bytes]:
    """gates/summary.json recording a pass of `gates`, and a record per gate (red ones failed, missing ones absent)."""
    files = {'gates/summary.json': json.dumps(dict(schema='c8-d2-gate-summary-1', gate='A-INV-3', loops=[7, 8],
                                                   passed=True, gates={g: True for g in gates},
                                                   injected_failure=None)).encode()}
    for g in gates:
        if g not in missing:
            files[f'gates/{g}.json'] = json.dumps(dict(schema='c8-d2-gate-1', gate=f'A-INV-3 {g}',
                                                       passed=g not in red)).encode()
    return files


def test_record(gate: str) -> str:
    return json.dumps(dict(schema='c8-d2-gate-1', gate=gate, passed=True, failed=[],
                           checks=[dict(check='a', passed=True, detail='')]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail: str = '') -> None:
        results.append(dict(check=name, passed=bool(ok), detail=detail[-400:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-300:]}' if detail and not ok else ''), flush=True)

    with tempfile.TemporaryDirectory(prefix='c8d2_handoff_') as td:
        root = Path(td)
        stage = root / 's'
        payload = {}
        for stem in ('L7_free', 'L7_power', 'L8_free', 'L8_power'):
            (stage / stem).mkdir(parents=True)
            (stage / stem / 'G1.txt').write_text(f'C7D2GRAPH1 {stem[1]} 1 1 0 1 1\n3 \n1 0 1 0\n4\n0 1 1 0 \n')
            payload[stem] = (stage, [f'{stem}/G1.txt'])

        def make_tree(name: str, files: dict[str, bytes]) -> tuple[Path, str]:
            tvi.pub.write_tree(root / f'.{name}', payload, files, dict(git_commit='0' * 40, d_pipeline='D4 statement'),
                               tar_impl='python')
            tvi.pub.publish_dir(root / f'.{name}', root / name)
            return root / name, hashlib.sha256((root / name / 'MANIFEST.json').read_bytes()).hexdigest()

        # a miniature tree whose gates/ records a complete pass
        tree, pin = make_tree('inventory8_d2', gate_files())
        shutil.copytree(tree, root / 'copy2')
        ev = root / 'evidence'
        (ev / 'gen1.1.0').mkdir(parents=True)
        (ev / 'gen3.3.0').mkdir(parents=True)
        tests = {'test_keys': 'A-INV-1 test_keys', 'test_run_l8': 'A-INV-1 injected failing gate (gen/run_l8.sh)',
                 'test_verify_inventory': 'A-INV-5 test_verify_inventory'}
        for n, gate in tests.items():
            (ev / 'gen1.1.0' / f'{n}.json').write_text(test_record(gate))
        regress_path = ev / 'gen1.1.0/regress_L3_L7.json'
        full_regress = treg.synthetic_h1_record()
        regress_path.write_text(json.dumps(full_regress))
        msha = hashlib.sha256((tree / 'MEMBERS.sha256').read_bytes()).hexdigest()
        (ev / 'gen3.3.0/crossnode.json').write_text(json.dumps(dict(schema='c8-d2-gate-1', gate='A-INV-4 crossnode',
                                                                    passed=True, members_sha256=msha,
                                                                    reference_members_sha256=msha)))
        refusal = root / 'second_publish.txt'
        refusal.write_text('refusing to publish: .../inventory8_d2 exists (a published tree is frozen)\n')
        dec = root / 'DECISIONS.md'
        dec.write_text('| Date | Item | Answer | Recorded by |\n|---|---|---|---|\n| 2026-10-03 | C1 | ACK. | C63d |\n')

        remote = '/mnt/beegfs/elsewhere/inventory8_d2'
        rec_ok = root / 'verify_remote.json'
        rec_ok.write_text(json.dumps(dict(tree=remote, pin=pin, passed=True)))
        rec_bad = root / 'verify_remote_bad.json'
        rec_bad.write_text(json.dumps(dict(tree=remote, pin=pin, passed=False)))

        def run(out: Path, decisions: Path = dec, copy2: Path | None = root / 'copy2', record: Path | None = rec_ok,
                first: Path = tree, first_pin: str = pin) -> subprocess.CompletedProcess:
            cmd = [sys.executable, '-B', str(GEN / 'handoff_inventory.py'), '--pin', first_pin, '--copy', str(first)]
            cmd += ['--copy', str(copy2)] if copy2 else []
            cmd += ['--copy-record', f'{remote}={record}'] if record else []
            cmd += ['--evidence', str(ev), '--decisions', str(decisions), '--refusal', str(refusal),
                    '--output', str(out), '--note', 'site note']
            return subprocess.run(cmd, capture_output=True, text=True)

        def refused(name: str, out: Path, needle: str, **kw) -> None:
            r = run(out, **kw)
            check(name, r.returncode == 1 and not out.exists() and needle in r.stdout + r.stderr,
                  f'rc={r.returncode} exists={out.exists()} ' + r.stdout + r.stderr)

        out = root / 'HANDOFF_inventory8_d2.json'
        r = run(out)
        h = json.loads(out.read_text()) if out.exists() else {}
        check('writes the HANDOFF when everything is green and complete', r.returncode == 0
              and h.get('manifest_sha256') == pin
              and h.get('manifest_md5') == hashlib.md5((tree / 'MANIFEST.json').read_bytes()).hexdigest()
              and all(v['passed'] for v in h.get('gate_summary', {}).values()) and 'r2_procedure' in h
              and h.get('gate_summary', {}).get('A-INV-3 gates', {}).get('gates') == {g: True for g in GATES}
              and h.get('d_pipeline') == 'D4 statement' and h.get('c63d', {}).get('gate_5_forest_certificate', 1) is None
              and h.get('copies', {}).get(remote) is True and h.get('notes') == ['site note'],
              r.stdout + r.stderr)
        r = run(out)
        check('refuses to overwrite an existing HANDOFF', r.returncode != 0 and 'exists' in (r.stdout + r.stderr))
        regress_path.write_text(json.dumps(dict(full_regress, passed=False)))
        refused('refuses when an A-INV record is red', root / 'h2.json', 'A-INV-2 regress')
        # S6-B-02: partial A-INV-2 evidence
        partial = dict(full_regress, loops=[3], threads=[1], threads_identical={},
                       builds=[b for b in full_regress['builds'] if b['L'] == 3 and b['threads'] == 1],
                       sectors={k: v for k, v in full_regress['sectors'].items() if k.endswith('_L3')},
                       controls={'side_files_free_eq_power_L3': True})
        regress_path.write_text(json.dumps(partial))
        refused('S6-B-02: refuses the A-INV-2 record of regress.py --loops 3 --threads 1', root / 'h2a.json', 'loops [3]')
        regress_path.write_text(json.dumps(dict(full_regress, loops=[], builds=[], sectors={})))
        refused('S6-B-02: refuses an A-INV-2 record that selected no loop', root / 'h2b.json', 'loops []')
        regress_path.write_text(json.dumps(dict(full_regress, threads=[8], threads_identical={},
                                                builds=[b for b in full_regress['builds'] if b['threads'] == 8])))
        refused('S6-B-02: refuses an A-INV-2 record with a single thread count', root / 'h2c.json', 'thread identity')
        regress_path.write_text(json.dumps(full_regress))
        (ev / 'gen1.1.0/test_keys.json').write_text(json.dumps(dict(passed=True)))
        refused('S6-B-02: refuses a bare {"passed": true} test record', root / 'h2d.json', 'A-INV-1 test_keys')
        (ev / 'gen1.1.0/test_keys.json').write_text(test_record(tests['test_keys']))
        # S6-B-02: incomplete A-INV-3 evidence in the tree
        t_part, p_part = make_tree('tree_only_a', gate_files(gates=('a_zero_dim',)))
        refused('S6-B-02: refuses a tree whose summary records only a_zero_dim', root / 'h2e.json',
                'not exactly the eleven A-INV-3 gates', copy2=None, record=None, first=t_part, first_pin=p_part)
        t_miss, p_miss = make_tree('tree_missing', gate_files(missing=('h_kirchhoff',)))
        refused('S6-B-02: refuses a complete summary with the h_kirchhoff record missing', root / 'h2f.json',
                'gates/h_kirchhoff.json missing', copy2=None, record=None, first=t_miss, first_pin=p_miss)
        t_red, p_red = make_tree('tree_red', gate_files(red=('j_rates',)))
        refused('S6-B-02: refuses a complete summary with the j_rates record red', root / 'h2g.json',
                'gates/j_rates.json is not a passed', copy2=None, record=None, first=t_red, first_pin=p_red)
        r = run(root / 'h2h.json', copy2=None, record=None)
        check('control: the complete tree alone (no second copy) is accepted', r.returncode == 0, r.stdout + r.stderr)
        nodec = root / 'D2.md'
        nodec.write_text('| Date | Item | Answer | Recorded by |\n|---|---|---|---|\n')
        refused('refuses without the C1 acknowledgment', root / 'h3.json', 'C1', decisions=nodec)
        bad = root / 'copy_bad'
        shutil.copytree(tree, bad)
        (bad / 'selection.json').write_text('{}')
        refused('refuses when a copy does not verify', root / 'h4.json', 'does not verify', copy2=bad)
        refused('refuses when a remote copy record is not a pass', root / 'h5.json', 'copy record', record=rec_bad)

        # publication: publish_inventory.py build on a miniature stage
        pub_bin = root / 'genbin'
        pub_bin.mkdir()
        for exe in ('build_free', 'build_power', 'check_edge_forests'):
            (pub_bin / exe).write_bytes(b'not a real executable\n')
            (pub_bin / f'{exe}.build.txt').write_text('command: g++ -O3 x.cpp\ncompiler: g++ (test) 0\n')

        def pub_stage(name: str, files: dict[str, bytes]) -> Path:
            st = root / name
            for stem in ('L7_free', 'L7_power', 'L8_free', 'L8_power'):
                (st / stem).mkdir(parents=True)
                (st / stem / 'G1.txt').write_text(f'C7D2GRAPH1 {stem[1]} 1 1 0 1 1\n3 \n1 0 1 0\n4\n0 1 1 0 \n')
                (st / stem / 'inventory.json').write_text('[{"id":1,"status":"finite-kernel"}]\n')
            sel = {'free': [1], 'power': [1], 'primitive': []}
            files = dict(files, **{'gates/coverage.json': json.dumps(dict(selection={'7': sel, '8': sel},
                                                                          partitions={'7': {}, '8': {}})).encode()})
            for rel, data in files.items():
                (st / rel).parent.mkdir(parents=True, exist_ok=True)
                (st / rel).write_bytes(data)
            return st

        def publish(st: Path, target: Path) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, '-B', str(GEN / 'publish_inventory.py'), 'build', '--stage', str(st),
                                   '--target', str(target), '--package', str(ROOT), '--bin', str(pub_bin),
                                   '--commit', '0' * 40, '--tar', 'python', '--slurm-jobs'],
                                  capture_output=True, text=True)

        for name, files, needle in (('only a_zero_dim in the summary', gate_files(gates=('a_zero_dim',)),
                                     'not exactly the eleven A-INV-3 gates'),
                                    ('the j_rates record red', gate_files(red=('j_rates',)),
                                     'gates/j_rates.json is not a passed')):
            target = root / f'pub_{name.split()[1]}' / 'inventory8_d2'
            target.parent.mkdir()
            r = publish(pub_stage(f'stage_{name.split()[1]}', files), target)
            check(f'S6-B-02: publication refuses a stage with {name}', r.returncode != 0 and not target.exists()
                  and not list(target.parent.iterdir()) and needle in r.stdout + r.stderr,
                  f'rc={r.returncode} exists={target.exists()} ' + r.stdout[-300:] + r.stderr[-300:])
        target = root / 'pub_full' / 'inventory8_d2'
        target.parent.mkdir()
        r = publish(pub_stage('stage_full', gate_files()), target)
        ok = r.returncode == 0 and target.is_dir()
        if ok:
            v = subprocess.run([sys.executable, '-B', str(GEN / 'verify_inventory.py'), str(target), '--pin',
                                hashlib.sha256((target / 'MANIFEST.json').read_bytes()).hexdigest()],
                               capture_output=True, text=True)
            ok = v.returncode == 0 and all((target / f'gates/{g}.json').is_file() for g in GATES)
        check('publication: the stage with the complete A-INV-3 gates is published and verifies', ok,
              r.stdout[-300:] + r.stderr[-300:])
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-5 test_handoff_inventory', passed=not failed, failed=failed,
               checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_handoff_inventory: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
