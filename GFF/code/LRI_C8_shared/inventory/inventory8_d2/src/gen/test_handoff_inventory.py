#!/usr/bin/env python3
"""A-INV-5: gen/handoff_inventory.py writes HANDOFF_inventory8_d2.json only when everything is green.
Pure logic on a miniature tree and synthetic evidence records, seconds.
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
spec = importlib.util.spec_from_file_location('test_verify_inventory', GEN / 'test_verify_inventory.py')
tvi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tvi)


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
        # a miniature tree whose gates/summary.json records a full pass
        stage = root / 's'
        payload = {}
        for stem in ('L7_free', 'L7_power', 'L8_free', 'L8_power'):
            (stage / stem).mkdir(parents=True)
            (stage / stem / 'G1.txt').write_text(f'C7D2GRAPH1 {stem[1]} 1 1 0 1 1\n3 \n1 0 1 0\n4\n0 1 1 0 \n')
            payload[stem] = (stage, [f'{stem}/G1.txt'])
        files = {'gates/summary.json': json.dumps(dict(passed=True, loops=[7, 8], injected_failure=None,
                                                       gates={'a_zero_dim': True})).encode()}
        tvi.pub.write_tree(root / '.t', payload, files, dict(git_commit='0' * 40, d_pipeline='D4 statement'),
                           tar_impl='python')
        tvi.pub.publish_dir(root / '.t', root / 'inventory8_d2')
        tree = root / 'inventory8_d2'
        pin = hashlib.sha256((tree / 'MANIFEST.json').read_bytes()).hexdigest()
        shutil.copytree(tree, root / 'copy2')
        ev = root / 'evidence'
        (ev / 'gen1.1.0').mkdir(parents=True)
        (ev / 'gen3.3.0').mkdir(parents=True)
        for n in ('test_keys', 'test_run_l8', 'regress_L3_L7', 'test_verify_inventory'):
            (ev / 'gen1.1.0' / f'{n}.json').write_text(json.dumps(dict(passed=True)))
        msha = hashlib.sha256((tree / 'MEMBERS.sha256').read_bytes()).hexdigest()
        (ev / 'gen3.3.0/crossnode.json').write_text(json.dumps(dict(passed=True, members_sha256=msha,
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

        def run(out: Path, decisions: Path = dec, copy2: Path = root / 'copy2',
                record: Path = rec_ok) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, '-B', str(GEN / 'handoff_inventory.py'), '--pin', pin, '--copy',
                                   str(tree), '--copy', str(copy2), '--copy-record', f'{remote}={record}',
                                   '--evidence', str(ev), '--decisions', str(decisions), '--refusal', str(refusal),
                                   '--output', str(out)], capture_output=True, text=True)

        out = root / 'HANDOFF_inventory8_d2.json'
        r = run(out)
        h = json.loads(out.read_text()) if out.exists() else {}
        check('writes the HANDOFF when everything is green', r.returncode == 0 and h.get('manifest_sha256') == pin
              and h.get('manifest_md5') == hashlib.md5((tree / 'MANIFEST.json').read_bytes()).hexdigest()
              and all(v['passed'] for v in h.get('gate_summary', {}).values()) and 'r2_procedure' in h
              and h.get('d_pipeline') == 'D4 statement' and h.get('c63d', {}).get('gate_5_forest_certificate', 1) is None
              and h.get('copies', {}).get(remote) is True,
              r.stdout + r.stderr)
        r = run(out)
        check('refuses to overwrite an existing HANDOFF', r.returncode != 0 and 'exists' in (r.stdout + r.stderr))
        (ev / 'gen1.1.0/regress_L3_L7.json').write_text(json.dumps(dict(passed=False)))
        r = run(root / 'h2.json')
        check('refuses when an A-INV record is red', r.returncode == 1 and not (root / 'h2.json').exists(),
              r.stdout + r.stderr)
        (ev / 'gen1.1.0/regress_L3_L7.json').write_text(json.dumps(dict(passed=True)))
        nodec = root / 'D2.md'
        nodec.write_text('| Date | Item | Answer | Recorded by |\n|---|---|---|---|\n')
        r = run(root / 'h3.json', decisions=nodec)
        check('refuses without the C1 acknowledgment', r.returncode == 1 and not (root / 'h3.json').exists(),
              r.stdout + r.stderr)
        bad = root / 'copy_bad'
        shutil.copytree(tree, bad)
        (bad / 'selection.json').write_text('{}')
        r = run(root / 'h4.json', copy2=bad)
        check('refuses when a copy does not verify', r.returncode == 1 and not (root / 'h4.json').exists(),
              r.stdout + r.stderr)
        r = run(root / 'h5.json', record=rec_bad)
        check('refuses when a remote copy record is not a pass', r.returncode == 1 and not (root / 'h5.json').exists(),
              r.stdout + r.stderr)
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-5 test_handoff_inventory', passed=not failed, failed=failed,
               checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_handoff_inventory: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
