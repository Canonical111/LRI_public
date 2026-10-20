#!/usr/bin/env python3
"""A-INV-5 (R02): the checksum hierarchy of inventory8_d2/ on a miniature tree. Pure logic, seconds.

Builds a miniature tree with gen/publish_inventory.write_tree (the Python tar writer, so it runs without GNU tar)
and checks:
  * the lists are acyclic: SHA256SUMS lists every file except MANIFEST.json and itself (MEMBERS.sha256 included),
    MANIFEST.json pins sha256(SHA256SUMS), and no file records its own hash;
  * gen/verify_inventory.py passes all four steps on the untouched tree;
  * it fails on a one-byte change to a G-file member, to a listed file, to SHA256SUMS and to MANIFEST.json, on an
    unlisted extra file, on a SHA256SUMS that lists MANIFEST.json or itself, and on a wrong pin;
  * it fails on newline-only changes of the checksum lists (the last LF of SHA256SUMS turned into CR, CRLF line
    ends in SHA256SUMS or MEMBERS.sha256), which a universal-newline read would hide;
  * publication is atomic and frozen: a second publish to the same target refuses, a failure while writing leaves
    no target, and `copy` refuses a source that does not verify.
Usage: python3 -B gen/test_verify_inventory.py [--output FILE]"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

GEN = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, GEN / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pub = load('publish_inventory')
ver = load('verify_inventory')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def flip(p: Path, offset: int) -> None:
    b = bytearray(p.read_bytes())
    b[offset] ^= 0x01
    p.write_bytes(bytes(b))


def mini_tree(root: Path, name: str = 'inventory8_d2') -> tuple[Path, str]:
    stage = root / f'stage_{name}'
    payload = {}
    for stem in ('L7_free', 'L7_power', 'L8_free', 'L8_power'):
        d = stage / stem
        d.mkdir(parents=True)
        names = []
        for gid in (3, 12, 40):
            (d / f'G{gid}.txt').write_text(f'C7D2GRAPH1 {stem[1]} {gid} 1.5 0.25 2 1\n3 5 \n2 0 1 1 0\n4\n0 1 1 0 \n')
            names.append(f'{stem}/G{gid}.txt')
        payload[stem] = (stage, sorted(names))
    files = {'inventory_L7.json': b'{"schema":"c8-inventory-d2-builder-1","L":7,"free":[],"power":[]}\n',
             'inventory_L8.json': b'{"schema":"c8-inventory-d2-builder-1","L":8,"free":[],"power":[]}\n',
             'selection.json': b'{"schema":"c8-inventory-d2-selection-1"}\n',
             'gates/summary.json': b'{"passed":true}\n', 'src/gen/x.py': b'print(1)\n'}
    tmp = root / f'.{name}.tmp'
    pub.write_tree(tmp, payload, files, dict(note='miniature'), tar_impl='python')
    target = root / name
    pub.publish_dir(tmp, target)
    return target, sha(target / 'MANIFEST.json')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail: str = '') -> None:
        results.append(dict(check=name, passed=bool(ok), detail=detail[:300]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[:200]}' if detail and not ok else ''), flush=True)

    def failing_steps(tree: Path, pin: str) -> list[str]:
        return [k for k, v in ver.verify(tree, pin).items() if v]

    with tempfile.TemporaryDirectory(prefix='c8d2_tvi_') as td:
        root = Path(td)
        tree, pin = mini_tree(root)
        sums = (tree / 'SHA256SUMS').read_text()
        listed = [line.split('  ', 1)[1] for line in sums.splitlines()]
        allfiles = sorted(p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file())
        check('SHA256SUMS lists every file except MANIFEST.json and itself',
              sorted(listed) == [f for f in allfiles if f not in ('MANIFEST.json', 'SHA256SUMS')], str(listed))
        check('MEMBERS.sha256 is listed in SHA256SUMS', 'MEMBERS.sha256' in listed)
        man = json.loads((tree / 'MANIFEST.json').read_text())
        check('MANIFEST.json pins sha256(SHA256SUMS)', man['sha256sums_sha256'] == sha(tree / 'SHA256SUMS'))
        check('no file records the hash of MANIFEST.json', all(pin not in p.read_text(errors='ignore')
                                                               for p in tree.rglob('*') if p.is_file()))
        members = (tree / 'MEMBERS.sha256').read_text().splitlines()
        check('MEMBERS.sha256 lists all 12 G-file members', len(members) == 12, str(len(members)))
        check('untouched tree verifies (all four steps)', failing_steps(tree, pin) == [], str(failing_steps(tree, pin)))

        def mutated(label: str, mutate, expect_step: str) -> None:
            t2 = root / f'mut_{len(results)}'
            shutil.copytree(tree, t2)
            mutate(t2)
            steps = failing_steps(t2, pin)
            check(f'detects {label} (step {expect_step})', expect_step in steps, str(steps))

        def member_byte(t: Path) -> None:
            tp = t / 'payload/L8_power.tar'
            data = tp.read_bytes()
            off = data.index(b'C7D2GRAPH1 8 40')  # inside a member's content, past its header block
            flip(tp, off + 5)

        mutated('a one-byte change to a G-file member', member_byte, '3_members')
        mutated('a one-byte change to a listed file', lambda t: flip(t / 'selection.json', 3), '1_sha256sums')
        mutated('a one-byte change to MEMBERS.sha256', lambda t: flip(t / 'MEMBERS.sha256', 0), '1_sha256sums')
        mutated('a one-byte change to SHA256SUMS', lambda t: flip(t / 'SHA256SUMS', 0), '2_manifest_pins_sha256sums')

        # Newline-only changes: the checksum lists are hashed and parsed as bytes, never in universal-newline text
        # mode, so CR and CRLF are changes like any other byte (independent verifier finding of 2026-10-03).
        def last_newline_to_cr(t: Path) -> None:
            p = t / 'SHA256SUMS'
            b = p.read_bytes()
            p.write_bytes(b[:-1] + b'\r')

        def crlf(name: str):
            def f(t: Path) -> None:
                p = t / name
                p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
            return f

        mutated('the last LF of SHA256SUMS turned into CR (one byte)', last_newline_to_cr, '2_manifest_pins_sha256sums')
        mutated('the last LF of SHA256SUMS turned into CR, parsed (one byte)', last_newline_to_cr, '1_sha256sums')
        mutated('SHA256SUMS rewritten with CRLF line ends', crlf('SHA256SUMS'), '2_manifest_pins_sha256sums')
        mutated('SHA256SUMS rewritten with CRLF line ends, parsed', crlf('SHA256SUMS'), '1_sha256sums')
        mutated('MEMBERS.sha256 rewritten with CRLF line ends', crlf('MEMBERS.sha256'), '1_sha256sums')
        mutated('MEMBERS.sha256 rewritten with CRLF line ends, parsed', crlf('MEMBERS.sha256'), '3_members')
        mutated('a one-byte change to MANIFEST.json', lambda t: flip(t / 'MANIFEST.json', 5), '4_external_pin')
        mutated('an unlisted extra file', lambda t: (t / 'gates/extra.json').write_text('{}\n'), '1_sha256sums')

        def lists_manifest(t: Path) -> None:
            with (t / 'SHA256SUMS').open('a') as f:
                f.write(f'{sha(t / "MANIFEST.json")}  MANIFEST.json\n')

        def lists_itself(t: Path) -> None:
            with (t / 'SHA256SUMS').open('a') as f:
                f.write(f'{"0" * 64}  SHA256SUMS\n')

        mutated('a SHA256SUMS that lists MANIFEST.json', lists_manifest, '1_sha256sums')
        mutated('a SHA256SUMS that lists itself', lists_itself, '1_sha256sums')
        check('a wrong pin fails step 4', '4_external_pin' in failing_steps(tree, '0' * 64))
        # frozen, atomic publication
        tmp2 = root / '.again.tmp'
        tmp2.mkdir()
        try:
            pub.publish_dir(tmp2, tree)
            check('a second publish to the same target refuses', False, 'publish_dir returned')
        except SystemExit:
            check('a second publish to the same target refuses', sha(tree / 'MANIFEST.json') == pin)

        real = pub.make_tar

        def broken(src_root, members, out, impl):
            if 'L8' in out.name:
                raise RuntimeError('injected failure while writing the payload')
            return real(src_root, members, out, impl)

        pub.make_tar = broken
        target = root / 'never'
        try:
            stage_root = root / 'b'
            stage_root.mkdir()
            try:
                t3, _ = mini_tree(stage_root, 'never')
            except RuntimeError:
                pass
            check('a failure while writing leaves no published target', not (stage_root / 'never').exists())
        finally:
            pub.make_tar = real
        bad = root / 'bad_source'
        shutil.copytree(tree, bad)
        flip(bad / 'selection.json', 2)
        try:
            pub.copy(argparse.Namespace(source=bad, target=root / 'copy_target', pin=pin, move=False))
            check('copy refuses a source that does not verify', False, 'copy returned')
        except SystemExit:
            check('copy refuses a source that does not verify', not (root / 'copy_target').exists())
        rc = pub.copy(argparse.Namespace(source=tree, target=root / 'copy_ok', pin=pin, move=False))
        check('copy of a verified tree publishes a verified, byte-identical copy',
              rc == 0 and failing_steps(root / 'copy_ok', pin) == []
              and all((root / 'copy_ok' / f).read_bytes() == (tree / f).read_bytes() for f in allfiles))
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-5 test_verify_inventory', passed=not failed, failed=failed,
               checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_verify_inventory: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
