#!/usr/bin/env python3
"""A-IN-3, A-IN-4, A-IN-5: regenerate the git-tracked inputs and compare them byte for byte; verify every pin.

  1. tools/make_lowloop.py regenerates gamma_d2_8.txt, two_loop.json and verification/two_loop_extension8.json byte
     for byte (its --verify adds the A-IN-1/2/6(a) checks; J-IN-1).
  2. tools/prepare_inputs.verify(): every file the manifest lists and every vendored pin. The L8 packs are required,
     except with C8_ALLOW_NO_L8=1 (the Mac), where a missing L8 pack is SKIPPED.
  3. With the frozen tree (--inventory TREE or $C8_INVENTORY), prepare_inputs regenerates the inputs into a scratch
     directory:
       * the L3..L7 packs byte-identical to inputs/packs; the L3..L6 packs also at C7(2)'s manifest sha256s;
       * the L7 packs hold 2,441 and 709 members; in a git checkout the 2,298 and 590 members of C7(2)'s packs
         (c8-base:inputs/inventory.json) are among them, with the same bytes;
       * the L8 packs (16,064 and 4,336 members) byte-identical to inputs/packs/*_L8.pack when present, otherwise
         at the manifest's pins;
       * inventory.json byte-identical when the inspector bin/c8d2_inspect (x86-64) is available; otherwise every
         row equal except the five inspector fields, which are SKIPPED;
       * manifest.json byte-identical (without the inspector: equal except the inventory.json hash);
       * tests/fixtures/inputs_mini regenerates byte for byte and verifies; its L8 members are at MEMBERS.sha256.
     Without the tree, step 3 is SKIPPED (printed) and only the hashes of step 2 are checked.
  4. A-IN-4: a one-byte change to an L3..L7 pack (in a scratch copy of the inputs) makes verify() fail.
  5. Stage-6 finding S6-B-01, the recovery command `make inputs-l8` (prepare_inputs.py --l8) in a sandbox package (a
     copy of tools/prepare_inputs.py, tools/common.py and gen/verify_inventory.py, a miniature inventory8_d2 tree and
     a manifest pinning its two L8 packs): it builds missing packs; it replaces a corrupt and a truncated pack with
     the pinned bytes; it refuses, leaving the existing packs byte for byte and no temporary file, when an immutable
     input is corrupt, when the tree does not verify against the pin, and when one rebuilt pack misses its pin (the
     other, correct one is not installed either).
     Stage-6 round-2 finding S6R2-B-03: with a corrupt free pack, a directory (the reviewer's example) or a symlink at
     packs/power_L8.pack is refused before anything is built, the free pack byte for byte unchanged; a failure of
     the second replacement (os.replace made to raise for power_L8.pack) restores the first pack, both when the
     originals were damaged packs and when they were missing, and leaves no temporary or backup file.
Usage: python3 -B tests/check_inputs.py [--inventory TREE] [--inspect BIN] [--output FILE]
Exit status 0 when every performed check passes."""
from __future__ import annotations

import argparse
import filecmp
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import make_lowloop  # noqa: E402
import prepare_inputs as pi  # noqa: E402
from common import digest  # noqa: E402

# C7(2)'s inputs manifest at LRI_C7_D2_HPC@a55958f (= this repository's tag c8-base): the L3..L6 packs are unchanged.
C7_PACKS = {
    'packs/free_L3.pack': '996bacb7b8d8585ca87dba7e33fac5b139722aecb920a75ea31e30fe7cd1aa1f',
    'packs/free_L4.pack': 'f7b44ee8616a6af9d21e9d523451934ac39dbf6714effc5ae68c1b5061d05a64',
    'packs/free_L5.pack': '1b3d40f9a0cec3533c860f1fb0d919bbd45e7fda0cb0c1075ebf30658941255e',
    'packs/free_L6.pack': '9321c372d83d18b6d4922e1b4dbb81f99bb0f07b3b2d280557634c0f55377200',
    'packs/power_L3.pack': '7b6d20ca86906b8c59225bd43dcec29caedbc081cac858ec6aa67ea35b0c2de5',
    'packs/power_L4.pack': '22ec47cf5a66b0414f9074da9a6d091bf82dd9b2de50fd2b73c579222c3860fd',
    'packs/power_L5.pack': '69822e78e96841e58477d8cebd6f7c035e63f3534574116add134827e5fa6e02',
    'packs/power_L6.pack': 'd711979240cd044a670eb6ecd004db25a4412ed1d0c32a63a1aad52ae8773259'}
COUNTS = {'free': {'3': 5, '4': 16, '5': 76, '6': 395, '7': 2441, '8': 16064},
          'power': {'3': 1, '4': 3, '5': 20, '6': 107, '7': 709, '8': 4336}}
MINI = ROOT / 'tests/fixtures/inputs_mini'


def l8_repair(td: Path, check) -> None:
    """S6-B-01 (step 5): prepare_inputs.py --l8 in a sandbox package whose ROOT is td/pkg, against a miniature tree."""
    spec = importlib.util.spec_from_file_location('c8d2_publish_inventory', ROOT / 'gen/publish_inventory.py')
    pub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pub)
    pkg = td / 'pkg'
    for rel in ('tools/prepare_inputs.py', 'tools/common.py', 'gen/verify_inventory.py'):
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, pkg / rel)
    # the miniature tree: three selected L8 kernels per sector and one with s_G = 4 that is not selected
    stage, payload, rows, selected = td / 'stage', {}, {}, {}
    for stem, L, sector in (('L7_free', 7, 'free'), ('L7_power', 7, 'power'), ('L8_free', 8, 'free'),
                            ('L8_power', 8, 'power')):
        (stage / stem).mkdir(parents=True)
        ids = (2, 5, 11, 14) if L == 8 else (1,)
        for i in ids:
            (stage / stem / f'G{i}.txt').write_text(f'C7D2GRAPH1 {L} {i} 0.{i}5 0.25 1 1\n{i} \n1 0 1 0\n4\n0 1 1 0 \n')
        payload[stem] = (stage, sorted(f'{stem}/G{i}.txt' for i in ids))
        if L == 8:
            rows[sector] = [dict(id=i, L=8, status='finite-kernel', mass_numerator=4 if i == 14 else 2, primitive=False)
                            for i in ids]
            selected[sector] = [i for i in ids if i != 14]
    files = {'inventory_L8.json': json.dumps(dict(schema='c8-inventory-d2-builder-1', L=8, **rows)).encode(),
             'selection.json': json.dumps(dict(schema='c8-inventory-d2-selection-1', L8=selected)).encode()}
    pub.write_tree(td / '.tree', payload, files, dict(note='miniature'), tar_impl='python')
    pub.publish_dir(td / '.tree', td / 'inventory8_d2')
    tree = td / 'inventory8_d2'
    pin = digest(tree / 'MANIFEST.json')
    want = {s: b''.join((stage / f'L8_{s}/G{i}.txt').read_bytes() for i in selected[s]) for s in ('free', 'power')}
    inputs = pkg / 'inputs'
    (inputs / 'packs').mkdir(parents=True)
    (inputs / 'packs/free_L3.pack').write_bytes(b'an immutable L3 pack\n')
    import hashlib
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731

    def manifest(power_pin: str | None = None, tree_pin: str = pin) -> None:
        doc = dict(schema=pi.SCHEMA, dimension=2, order=8, epsilon='2s-2',
                   sha256={'packs/free_L3.pack': sha(b'an immutable L3 pack\n'), 'packs/free_L8.pack': sha(want['free']),
                           'packs/power_L8.pack': power_pin or sha(want['power'])},
                   counts={'free': {'8': len(selected['free'])}, 'power': {'8': len(selected['power'])}},
                   inventory8_d2_manifest_sha256=tree_pin)
        (inputs / 'manifest.json').write_text(json.dumps(doc, indent=1) + '\n')

    def packs() -> dict:
        return {s: (inputs / f'packs/{s}_L8.pack').read_bytes() if (inputs / f'packs/{s}_L8.pack').is_file() else None
                for s in ('free', 'power')}

    def damage() -> dict:
        """A corrupt free pack (one byte flipped) and a truncated power pack."""
        b = bytearray(want['free'])
        b[3] ^= 1
        (inputs / 'packs/free_L8.pack').write_bytes(bytes(b))
        (inputs / 'packs/power_L8.pack').write_bytes(want['power'][:-7])
        return packs()

    def l8(tree_arg: Path = tree) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k != 'C8_ALLOW_NO_L8'}
        return subprocess.run([sys.executable, '-B', str(pkg / 'tools/prepare_inputs.py'), '--l8', '--inventory',
                               str(tree_arg)], capture_output=True, text=True, env=env)

    def no_temp() -> bool:
        return {p.name for p in (inputs / 'packs').iterdir()} <= {'free_L3.pack', 'free_L8.pack', 'power_L8.pack'}

    manifest()
    r = l8()
    check('S6-B-01: make inputs-l8 builds missing L8 packs at their pins',
          r.returncode == 0 and packs() == want and no_temp(), r.stdout[-300:] + r.stderr[-600:])
    damage()
    r = l8()
    check('S6-B-01: make inputs-l8 replaces a corrupt and a truncated L8 pack with the pinned bytes',
          r.returncode == 0 and packs() == want and no_temp(), r.stdout[-300:] + r.stderr[-600:])
    # refusals: the damaged packs stay as they are, and no temporary file remains
    before = damage()
    (inputs / 'packs/free_L3.pack').write_bytes(b'an immutable L3 pack, edited\n')
    r = l8()
    check('S6-B-01: a corrupt immutable input stops the rebuild; the L8 packs stay as they were',
          r.returncode != 0 and 'free_L3.pack' in r.stderr and packs() == before and no_temp(), r.stderr[-600:])
    (inputs / 'packs/free_L3.pack').write_bytes(b'an immutable L3 pack\n')
    other = td / 'tree_edited'
    shutil.copytree(tree, other)
    (other / 'selection.json').write_text('{}')
    r = l8(other)
    check('S6-B-01: a tree that does not verify against the pin stops the rebuild; the L8 packs stay as they were',
          r.returncode != 0 and 'does not verify' in r.stderr and packs() == before and no_temp(), r.stderr[-600:])
    manifest(power_pin='0' * 64)
    r = l8()
    check('S6-B-01: a rebuilt pack off its pin installs neither pack (no partial replacement), no temporary file',
          r.returncode != 0 and 'differs from the manifest pin' in r.stderr and packs() == before and no_temp(),
          r.stderr[-600:])
    manifest()
    r = l8()
    check('S6-B-01: ... and the next make inputs-l8 repairs both', r.returncode == 0 and packs() == want and no_temp(),
          r.stderr[-600:])
    # S6R2-B-03: non-regular targets are refused before installation; the installation is all or nothing
    power = inputs / 'packs/power_L8.pack'
    for kind in ('a directory', 'a symlink'):
        free_before = damage()['free']
        power.unlink()
        if kind == 'a directory':  # the reviewer's example
            power.mkdir()
        else:
            power.symlink_to(td / 'elsewhere.pack')
        r = l8()
        check(f'S6R2-B-03: {kind} at packs/power_L8.pack (and a corrupt free pack) is refused before anything is built; '
              'the free pack stays byte for byte',
              r.returncode != 0 and 'not a regular file' in r.stderr and packs()['free'] == free_before
              and (power.is_dir() if kind == 'a directory' else power.is_symlink()) and no_temp()
              and not (td / 'elsewhere.pack').exists(), r.stderr[-600:])
        power.rmdir() if kind == 'a directory' else power.unlink()

    def l8_failing_second_replace(no_links: bool = False) -> subprocess.CompletedProcess:
        """make inputs-l8 with os.replace made to raise when it installs power_L8.pack (the second replacement);
        no_links: os.link raises too (a file system without hard links: the originals are renamed aside instead)."""
        code = ('import os, sys\n'
                'from pathlib import Path\n'
                'sys.path.insert(0, sys.argv[1])\n'
                'import prepare_inputs as pi\n'
                'orig = os.replace\n'
                'def replace(src, dst, *a, **k):\n'
                '    if Path(dst).name == "power_L8.pack" and Path(src).name.startswith(".power_L8.pack.tmp."):\n'
                '        raise OSError("injected failure of the second replacement")\n'
                '    return orig(src, dst, *a, **k)\n'
                'os.replace = replace\n'
                'def no_link(*a, **k):\n'
                '    raise PermissionError(1, "injected: no hard links here")\n'
                'if sys.argv[3] == "1":\n'
                '    os.link = no_link\n'
                'pi.build_l8(Path(sys.argv[2]))\n')
        env = {k: v for k, v in os.environ.items() if k != 'C8_ALLOW_NO_L8'}
        return subprocess.run([sys.executable, '-B', '-c', code, str(pkg / 'tools'), str(tree), str(int(no_links))],
                              capture_output=True, text=True, env=env)

    for no_links in (False, True):
        before = damage()
        r = l8_failing_second_replace(no_links)
        how = ' (no hard links: originals renamed aside)' if no_links else ''
        check(f'S6R2-B-03: a failure of the second replacement restores the first pack{how} (damaged originals stay '
              'byte for byte), no temporary or backup file',
              r.returncode != 0 and 'injected failure of the second replacement' in r.stderr and packs() == before
              and no_temp(), dict(stderr=r.stderr[-600:], free_restored=packs()['free'] == before['free'],
                                  names=sorted(x.name for x in (inputs / 'packs').iterdir())))
    for s in ('free', 'power'):
        (inputs / f'packs/{s}_L8.pack').unlink()
    r = l8_failing_second_replace()
    check('S6R2-B-03: a failure of the second replacement with both packs missing leaves both missing (the first one '
          'is removed again), no temporary or backup file',
          r.returncode != 0 and 'injected failure of the second replacement' in r.stderr
          and packs() == {'free': None, 'power': None} and no_temp(),
          dict(stderr=r.stderr[-600:], names=sorted(x.name for x in (inputs / 'packs').iterdir())))
    r = l8()
    check('S6R2-B-03: ... and the next make inputs-l8 builds both', r.returncode == 0 and packs() == want and no_temp(),
          r.stderr[-600:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--inventory', type=Path, default=os.environ.get('C8_INVENTORY') or None)
    ap.add_argument('--inspect', type=Path, default=ROOT / 'bin/c8d2_inspect')
    ap.add_argument('--threads', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed, skipped = [], [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1200:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-500:]}' if detail and not ok else ''), flush=True)

    def skip(what: str) -> None:
        skipped.append(what)
        print('SKIPPED ' + what, flush=True)

    inputs = ROOT / 'inputs'
    # 1. the low-loop files
    with tempfile.TemporaryDirectory(prefix='c8d2_ll_') as td:
        files = make_lowloop.write(8, Path(td))
        for name, data in files.items():
            check(f'make_lowloop regenerates inputs/{name} byte for byte', (inputs / name).read_bytes() == data)
    # 2. every pin
    try:
        m = pi.verify(inputs)
        check('prepare_inputs.verify(): every listed file and every vendored pin', True)
    except Exception as e:
        m = json.loads((inputs / 'manifest.json').read_bytes())
        check('prepare_inputs.verify(): every listed file and every vendored pin', False, f'{type(e).__name__}: {e}')
    l8_present = all((inputs / p).is_file() for p in pi.L8_PACKS)
    if not l8_present:
        skip('the L8 packs are not here (C8_ALLOW_NO_L8=1): their bytes are checked where they are built (J-IN-2)')
    check('manifest: schema, dimension 2, order 8, the twelve packs and the counts of the plan',
          m.get('schema') == pi.SCHEMA and m.get('order') == 8 and m.get('counts') == COUNTS
          and sum(1 for k in m['sha256'] if k.startswith('packs/')) == 12, dict(counts=m.get('counts')))
    check('the L3..L6 packs are at C7(2)\'s manifest sha256s', all(m['sha256'].get(k) == v for k, v in C7_PACKS.items()))
    check('the manifest pins the vendored assembly from tools/VENDORED.json (A-IN-4, A-ASM-1(b))',
          m.get('vendored_assembly') == pi.vendored_pins()
          and m.get('vendored_assembly_handoff_sha256') == pi.vendored_pins()['handoff_sha256'])
    inv = json.loads((inputs / 'inventory.json').read_bytes())
    check('inventory.json rows carry the inspector fields, products, addends and kernel_bytes positive (A-IN-3)',
          all(all(r.get(k, 0) > 0 for k in ('products', 'addends', 'kernel_bytes')) and 'segments' in r and 'numerators' in r
              for s in inv for L in inv[s] for r in inv[s][L]))
    # C7(2)'s L7 members, from git when this is a checkout
    if (ROOT / '.git').exists():
        c7 = json.loads(subprocess.run(['git', '-C', str(ROOT), 'show', 'c8-base:inputs/inventory.json'], capture_output=True,
                                       check=True).stdout)
        ok = True
        for s in ('free', 'power'):
            new = {r['id']: r['sha256'] for r in inv[s]['7']}
            old = {r['id']: r['sha256'] for r in c7[s]['7']}
            ok &= len(old) == {'free': 2298, 'power': 590}[s] and all(new.get(i) == h for i, h in old.items())
        check('the 2,298 and 590 members of C7(2)\'s L7 packs are among the new L7 members, same bytes', ok)
    else:
        skip('C7(2)\'s L7 members (no .git here; checked in the checkout)')
    # 3. regeneration from the frozen tree
    tree = a.inventory
    inspect = a.inspect if a.inspect and a.inspect.is_file() else None
    if tree is None:
        skip('regeneration from inventory8_d2 (give --inventory TREE or C8_INVENTORY)')
    else:
        with tempfile.TemporaryDirectory(prefix='c8d2_inputs_') as td:
            dest = Path(td) / 'inputs'
            doc = pi.regenerate(dest, tree, m['inventory8_d2_manifest_sha256'], inspect, a.threads)
            for s in ('free', 'power'):
                for L in range(3, 8):
                    name = f'packs/{s}_L{L}.pack'
                    check(f'{name} regenerates byte for byte', filecmp.cmp(dest / name, inputs / name, shallow=False))
                for name in (f'packs/{s}_L8.pack',):
                    if (inputs / name).is_file():
                        check(f'{name} regenerates byte for byte', filecmp.cmp(dest / name, inputs / name, shallow=False))
                    else:
                        check(f'{name} regenerates at the manifest pin', digest(dest / name) == m['sha256'][name])
            check('the regenerated L7 packs hold 2,441 and 709 members, the L8 packs 16,064 and 4,336',
                  doc['counts'] == COUNTS, doc['counts'])
            new_inv = json.loads((dest / 'inventory.json').read_bytes())
            if inspect:
                check('inventory.json regenerates byte for byte (inspector fields included)',
                      filecmp.cmp(dest / 'inventory.json', inputs / 'inventory.json', shallow=False))
                check('manifest.json regenerates byte for byte',
                      filecmp.cmp(dest / 'manifest.json', inputs / 'manifest.json', shallow=False))
            else:
                skip('the inspector fields of inventory.json (no x86-64 bin/c8d2_inspect here; J-IN-2 regenerates them)')
                strip = lambda d: {s: {L: [{k: v for k, v in r.items() if k not in pi.INSPECT_FIELDS} for r in rows]
                                       for L, rows in d[s].items()} for s in d}
                check('inventory.json regenerates row for row, except the inspector fields', strip(new_inv) == strip(inv))
                def comparable(d: dict) -> dict:
                    d = json.loads(json.dumps(d))
                    d['sha256'] = {k: v for k, v in d['sha256'].items() if k != 'inventory.json'}
                    d.pop('inspector_fields', None)
                    return d
                mm = json.loads((dest / 'manifest.json').read_bytes())
                check('manifest.json regenerates, except the inventory.json hash', comparable(mm) == comparable(m))
            mini = Path(td) / 'mini'
            pi.mini(mini, tree)
            fa = sorted(p.relative_to(mini).as_posix() for p in mini.rglob('*') if p.is_file())
            fb = sorted(p.relative_to(MINI).as_posix() for p in MINI.rglob('*') if p.is_file() and p.name != '.DS_Store')
            check('tests/fixtures/inputs_mini regenerates byte for byte',
                  fa == fb and all(filecmp.cmp(mini / f, MINI / f, shallow=False) for f in fa), dict(regen=fa, shipped=fb))
    try:
        pi.verify(MINI, allow_no_l8=True)
        check('tests/fixtures/inputs_mini verifies (its own L8 packs, the package\'s L3..L7 packs)', True)
    except Exception as e:
        check('tests/fixtures/inputs_mini verifies (its own L8 packs, the package\'s L3..L7 packs)', False, str(e))
    # 4. A-IN-4: a one-byte change to a pack fails verify()
    with tempfile.TemporaryDirectory(prefix='c8d2_flip_') as td:
        cp = Path(td) / 'inputs'
        shutil.copytree(inputs, cp, ignore=shutil.ignore_patterns('*_L8.pack', '.DS_Store'))
        p = cp / 'packs/free_L5.pack'
        b = bytearray(p.read_bytes())
        b[10] ^= 1
        p.write_bytes(bytes(b))
        try:
            pi.verify(cp, allow_no_l8=True)
            check('a one-byte change to a pack makes verify() fail', False, 'accepted')
        except ValueError as e:
            check('a one-byte change to a pack makes verify() fail', 'free_L5.pack' in str(e), str(e))
    # 5. S6-B-01: make inputs-l8 repairs a corrupt or truncated L8 pack, atomically, from a verified tree
    with tempfile.TemporaryDirectory(prefix='c8d2_l8_repair_') as td:
        l8_repair(Path(td), check)
    rec = dict(schema='c8-d2-gate-1', gate='A-IN-3/4/5 check_inputs', passed=not failed, failed=failed, skipped=skipped,
               checks=results, inventory=str(tree) if tree else None, inspector=str(inspect) if inspect else None,
               l8_packs_present=l8_present, host=os.uname().nodename, python=sys.version.split()[0])
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'check_inputs: {len(results) - len(failed)}/{len(results)} checks passed, {len(skipped)} skipped')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
