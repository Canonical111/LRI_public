#!/usr/bin/env python3
"""`make inputs-l8`, the Stage-2b `make inputs`, `make link-l8` and inputs_mini end to end on a miniature d=3 payload
(PLAN B, A.2 step 6; Stage 2b). Mac; about a minute.

The miniature, in a scratch package (tools/, gen3/, the Makefile, vendor/, reference/inputs/ and inputs/ as committed,
hard links): a d=3 payload published by gen3/publish_d3.py (--tar python) whose L7 tars hold every C7(3) L7 member
(reference/inputs/) plus 2 free and 1 power s_G = 4 kernels made from real C7(3) members (new ids, w_B = w_A / 3), and
whose L8 tars hold synthetic L8 G-files (E = 16), one of them with s_G = 4 and not selected; rate audits (the C7(3)
members' double_lift from the committed inventory, the others from prepare_inputs.raw_valuations); fake passed gate
records; and a miniature H1 tree (selection.json, SHA256SUMS, MANIFEST.json) whose pin is passed with the tool's
test-only --fixture-h1-pin (the real tool pins H1's 46341a3c... and H1's counts). Checks:
  * make inputs-l8: exit 0; the manifest pins the Stage-2b small files, the L7 packs and the L8 packs, carries D3PIN
    and the H1 pin, l7_complete and l8_present; each L8 pack is a hard link of a read-only store blob
    <store>/packs/<sha256>.pack; the C7(3) L7 rows equal the committed ones (all fields but the offset), the new L7
    rows have s_G = 4 and no inspect fields, the L8 rows follow selection.json, MEMBERS_d3.sha256 and the rate audit;
    the build's gate-6 summary (3,511 C7(3) members from reference/inputs/, 2,888 compared with the payload's bytes);
  * the Stage-2b `make inputs`: in place, nothing changes; into a scratch directory, every file is byte-identical, with
    the L8 packs present (rows re-derived from them) and absent (rows carried forward); a second inputs-l8 is a no-op;
  * verify(): accepts the inputs (no test-only reason); refuses missing L8 packs unless C8_ALLOW_NO_L8=1; refuses a
    one-byte change to d3/MEMBERS_d3.sha256, and, with the manifest pin moved along, the broken chain;
  * make link-l8: links the store's blobs, again a no-op, refuses a different file in the way;
  * gates_d3.py gate6 on the miniature: the C7(3) rows, the payload digest and the L3-L6 packs pass; every L7 member is
    at its MEMBERS_d3.sha256 hash (the counts are the miniature's, so the record's verdict is not used);
  * inputs_mini: make inputs-mini (all of the miniature's L8 kernels, fewer than 8 per sector), materialized as a
    C8_INPUTS directory that verify() accepts, and tools/members.py extracting an L8 member from it byte for byte;
    `mini --out inputs` refused before anything is written (S4-003), and so are `mini` with its default destination
    symlinked to the package inputs and an --out whose packs/ links to inputs/packs (R2-S1-05).
Usage: python3 -B tests/inputs_l8_test.py [--keep]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_inputs as pi  # noqa: E402

PY = sys.executable
SECTORS = ('free', 'power')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def link_or_copy(src, dst) -> None:
    try:
        os.link(src, dst)
    except OSError:   # another filesystem
        shutil.copy2(src, dst)


def link_tree(src: Path, dst: Path, ignore=None) -> None:
    shutil.copytree(src, dst, copy_function=link_or_copy, ignore=ignore)


def scratch_pkg(td: Path) -> Path:
    pkg = td / 'pkg'
    (pkg / 'tools').mkdir(parents=True)
    for f in (ROOT / 'tools').iterdir():
        if f.is_file() and f.suffix in ('.py', '.json'):
            shutil.copy2(f, pkg / 'tools' / f.name)
    shutil.copytree(ROOT / 'gen3', pkg / 'gen3', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(ROOT / 'Makefile', pkg / 'Makefile')
    link_tree(ROOT / 'vendor', pkg / 'vendor', ignore=shutil.ignore_patterns('__pycache__'))
    link_tree(ROOT / 'reference/inputs', pkg / 'reference/inputs')
    shutil.copy2(ROOT / 'reference/DELIVERY_MANIFEST.json', pkg / 'reference/DELIVERY_MANIFEST.json')
    link_tree(ROOT / 'inputs', pkg / 'inputs', ignore=shutil.ignore_patterns('free_L8.pack', 'power_L8.pack'))
    for rel in ('tests/fixtures/c7_inputs/inventory.json', 'tests/fixtures/c7_inputs/manifest.json'):
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, pkg / rel)
    # the inspect data of the C7(3) kernels only (whatever the live stage): the miniature's new kernels have none
    c7 = json.loads((ROOT / 'tests/fixtures/c7_inputs/inventory.json').read_bytes())
    keep = {(s, L, r['id']) for s in SECTORS for L in c7[s] for r in c7[s][L]}
    d = json.loads((ROOT / pi.INSPECT_DATA).read_bytes())
    d['rows'] = {s: {L: [r for r in rs if (s, L, r[0]) in keep] for L, rs in loops.items() if L in c7[s]}
                 for s, loops in d['rows'].items()}
    (pkg / 'inspect').mkdir()
    (pkg / pi.INSPECT_DATA).write_text(json.dumps(d) + '\n')
    return pkg


def synthetic_l8(gid: int, s_g: int, seed: int) -> bytes:
    """A synthetic L = 8 d=3 G-file (E = 16): 40 masks of popcount 8, 5 terms, w_A = 0.1875, w_B = w_A s_G / 12."""
    rng = random.Random(seed)
    E, L = 16, 8
    masks = sorted({sum(1 << b for b in rng.sample(range(E), L)) for _ in range(60)})[:40]
    wb = {2: '0.03125', 4: '0.0625', 6: '0.09375'}[s_g]
    lines = [f'C7D3GRAPH1 {L} {gid} 0.1875 {wb} {len(masks)} 5', ' '.join(map(str, masks))]
    for _ in range(5):
        idx = sorted(rng.sample(range(len(masks)), rng.randint(1, 12)))
        co = [rng.choice((-1, 0, 0, 1, 2)) for _ in range(E)]
        lines.append(' '.join(map(str, [len(idx), *idx, *co])))
    lines.append(str(1 << E))
    lines.append(' '.join('0' if s in (0, (1 << E) - 1) else rng.choice(('0.75', '1', '1.5')) for s in range(1 << E)))
    return ('\n'.join(lines) + '\n').encode()


def new_l7(src: bytes, gid: int) -> bytes:
    """A real C7(3) L7 member re-headed as an s_G = 4 kernel (new id, w_A = 0.75, w_B = 0.25)."""
    head, rest = src.split(b'\n', 1)
    h = head.split()
    h[2], h[3], h[4] = str(gid).encode(), b'0.75', b'0.25'
    return b' '.join(h) + b'\n' + rest


def double_lift(data: bytes) -> int:
    g = pi.Member(data, 'fixture')
    return int((pi.raw_valuations(g.L, g.masks, g.terms) <= pi.DOUBLE_LIFT_RAW).sum())


def run(pkg: Path, *args, check=True, env=None) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if k not in ('C8_INPUTS', 'C8_ALLOW_NO_L8', 'PYTHONPYCACHEPREFIX')}
    e.update(PYTHONDONTWRITEBYTECODE='1', **(env or {}))
    cp = subprocess.run([PY, '-B', *map(str, args)], capture_output=True, text=True, cwd=str(pkg), env=e)
    if check and cp.returncode:
        raise AssertionError(f'{args}: exit {cp.returncode}\n{cp.stdout[-1500:]}\n{cp.stderr[-3000:]}')
    return cp


def files_of(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): sha(p.read_bytes()) for p in sorted(d.rglob('*'))
            if p.is_file() and '.build-' not in p.as_posix() and p.name != '.DS_Store'}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    td = Path(tempfile.mkdtemp(prefix='c8d3_inputs_l8_test_'))
    passed = []

    def ok(name):
        passed.append(name)
        print('PASS', name, flush=True)
    try:
        pkg = scratch_pkg(td)
        inp = pkg / 'inputs'
        # the C7(3) kernels (a6ce987's inventory) with their rows as the package holds them (Stage 2a or 2b)
        c7inv = json.loads((ROOT / 'tests/fixtures/c7_inputs/inventory.json').read_bytes())
        live = json.loads((ROOT / 'inputs/inventory.json').read_bytes())
        committed = {}
        for s in SECTORS:
            committed[s] = {}
            for L in ('3', '4', '5', '6', '7'):
                byid = {r['id']: r for r in live[s][L]}
                committed[s][L] = [byid[r['id']] for r in c7inv[s][L]]
                if L != '7':
                    assert committed[s][L] == live[s][L]
        # ---- the miniature d=3 payload and H1 tree --------------------------------------------------------------------
        stage, audits = td / 'stage', td / 'audits'
        audit = {7: [], 8: []}
        sel = {'L7': {}, 'L8': {}}
        new_ids = {'free': [900001, 900002], 'power': [900003]}
        for s in SECTORS:
            d7 = stage / f'L7_{s}'
            d7.mkdir(parents=True)
            rows = committed[s]['7']
            for r in rows:
                os.link(ROOT / f'reference/inputs/{s}/L7/G{r["id"]}.txt', d7 / f'G{r["id"]}.txt')
                audit[7].append(dict(file=f'L7_{s}/G{r["id"]}.txt', L=7, id=r['id'], double_lift_subsets=r['double_lift']))
            small = sorted(rows, key=lambda r: r['length'])
            for k, gid in enumerate(new_ids[s]):
                b = new_l7((ROOT / f'reference/inputs/{s}/L7/G{small[k]["id"]}.txt').read_bytes(), gid)
                (d7 / f'G{gid}.txt').write_bytes(b)
                audit[7].append(dict(file=f'L7_{s}/G{gid}.txt', L=7, id=gid, double_lift_subsets=double_lift(b)))
            sel['L7'][s] = sorted([r['id'] for r in rows] + new_ids[s])
            d8 = stage / f'L8_{s}'
            d8.mkdir()
            l8 = {'free': [(5, 6), (11, 2), (12, 4), (40, 6)], 'power': [(3, 2), (8, 6)]}[s]
            for gid, sg in l8:
                b = synthetic_l8(gid, sg, 1000 + gid)
                (d8 / f'G{gid}.txt').write_bytes(b)
                audit[8].append(dict(file=f'L8_{s}/G{gid}.txt', L=8, id=gid, double_lift_subsets=double_lift(b)))
            sel['L8'][s] = [gid for gid, sg in l8 if sg != 4]
        sel['L7']['primitive'] = sorted(r['id'] for r in committed['free']['7'] if r['primitive'])
        sel['L8']['primitive'] = [40]
        selection = dict(schema=pi.SELECTION_SCHEMA, rule='fixture (tests/inputs_l8_test.py)', L7=sel['L7'], L8=sel['L8'],
                         counts={f'L{L}_{s}': len(sel[f'L{L}'][s]) for L in (7, 8) for s in SECTORS})
        audits.mkdir()
        for L in (7, 8):
            (audits / f'rate_audit_L{L}.json').write_text(json.dumps(audit[L]) + '\n')
        h1 = td / 'h1'
        h1.mkdir()
        (h1 / 'selection.json').write_text(json.dumps(selection, indent=1) + '\n')
        (h1 / 'SHA256SUMS').write_text(f'{sha((h1 / "selection.json").read_bytes())}  selection.json\n')
        (h1 / 'MANIFEST.json').write_text(json.dumps(dict(schema='fixture', sha256sums_sha256=sha((h1 / 'SHA256SUMS').read_bytes()))))
        h1pin = sha((h1 / 'MANIFEST.json').read_bytes())
        sys.path.insert(0, str(ROOT / 'gen3'))
        import g3common as c
        gates, side = td / 'gates', td / 'side'
        gates.mkdir()
        for g in c.H1_GATES:
            (gates / f'{g}.json').write_text(json.dumps(dict(passed=True, gate=g)))
            for name in c.GATE_SUPPORT.get(g, ()):
                (gates / name).write_text(json.dumps(dict(passed=True) if g != 'gate3' else dict(L=7, rows=[])))
        side.mkdir()
        for stem in c.SIDE_STEMS:
            (side / c.side_file(stem)).write_text(f'0 {stem}\n')
        payload = td / 'store/d3_payload' / h1pin[:12]
        payload.parent.mkdir(parents=True)
        run(pkg, ROOT / 'gen3/publish_d3.py', '--stage', stage, '--gates', gates, '--side', side, '--audits', audits,
            '--target', payload, '--h1-pin', h1pin, '--commit', 'fixture', '--tar', 'python')
        pin = sha((payload / 'MANIFEST_d3.json').read_bytes())
        store = td / 'store'
        ok(f'miniature payload published ({sum(len(v) for v in sel["L7"].values() if isinstance(v, list))} L7 members '
           f'selected, pin {pin[:12]})')
        # ---- make inputs-l8 ---------------------------------------------------------------------------------------------
        cp = run(pkg, 'tools/prepare_inputs.py', 'l8', '--d3payload', payload, '--d3pin', pin, '--store', store, '--h1', h1,
                 '--fixture-h1-pin', h1pin, '--output', td / 'l8.json')
        rec = json.loads((td / 'l8.json').read_text())
        m = json.loads((inp / 'manifest.json').read_bytes())
        assert m['l7_complete'] is True and m['l8_present'] is True and m['d3_payload_manifest_sha256'] == pin
        assert m['inventory8_d2_manifest_sha256'] == h1pin and set(pi.STAGE2B_FILES) <= set(m['sha256'])
        assert m['counts'] == {s: {**{str(L): len(committed[s][str(L)]) for L in (3, 4, 5, 6)},
                                   '7': len(sel['L7'][s]), '8': len(sel['L8'][s])} for s in SECTORS}, m['counts']
        g6r = rec['report']['gate6']
        assert (g6r['c7d3_members'], g6r['new_l7_members'], g6r['payload_c7d3_bytes_compared'], len(g6r['c7d3_packs_reproduced'])) == (3511, 3, 2888, 10), g6r
        for rel in pi.L8_PACKS:
            blob = store / 'packs' / f'{m["sha256"][rel]}.pack'
            assert os.path.samefile(blob, inp / rel) and stat.S_IMODE(blob.stat().st_mode) == 0o444
            assert sha(blob.read_bytes()) == m['sha256'][rel]
        assert not [p for p in (store / 'packs').iterdir() if p.name.startswith('.tmp')]
        for rel, name in pi.D3_COPIES.items():
            assert (inp / rel).read_bytes() == (payload / name).read_bytes(), rel
        for rel, name in pi.H1_COPIES.items():
            assert (inp / rel).read_bytes() == (h1 / name).read_bytes(), rel
        ok('make inputs-l8: Stage-2b manifest and pins; L8 packs are hard links of read-only store blobs; small files are '
           'byte copies; gate-6 summary 3,511 / 2,888')
        inv = json.loads((inp / 'inventory.json').read_bytes())
        assert inv['inspect_complete'] is False and list(inv['free']) == [str(L) for L in range(3, 9)]
        keys = [k for k in pi.ROW_FIELDS if k != 'offset']
        for s in SECTORS:
            for L in (3, 4, 5, 6):
                assert inv[s][str(L)] == committed[s][str(L)], (s, L)
            got = {r['id']: r for r in inv[s]['7']}
            assert [r['id'] for r in inv[s]['7']] == sel['L7'][s]
            for r in committed[s]['7']:
                assert [got[r['id']][k] for k in keys] == [r[k] for k in keys], (s, r['id'])
            for gid in new_ids[s]:
                r = got[gid]
                assert r['s_G'] == 4 and all(r[k] is None for k in pi.INSPECT_FIELDS) and r['primitive'] is False, r
            ad = {x['id']: x['double_lift_subsets'] for x in audit[8] if x['file'].startswith(f'L8_{s}/')}
            assert [r['id'] for r in inv[s]['8']] == sel['L8'][s]
            for r in inv[s]['8']:
                b = (stage / f'L8_{s}/G{r["id"]}.txt').read_bytes()
                assert r['sha256'] == sha(b) and r['length'] == len(b) and r['double_lift'] == ad[r['id']]
                assert r['primitive'] is (r['id'] == 40) and r['s_G'] in (2, 6)
        ok('inventory: L3-L6 rows unchanged; C7(3) L7 rows equal the committed ones; new L7 rows s_G = 4; L8 rows follow '
           'selection.json, MEMBERS_d3.sha256 and the rate audit')
        # ---- the Stage-2b make inputs ---------------------------------------------------------------------------------
        before = files_of(inp)
        cp = run(pkg, 'tools/prepare_inputs.py', 'build')
        assert 'changed: none' in cp.stderr and '(2b-carry)' in cp.stderr and files_of(inp) == before, cp.stderr[-800:]
        want = {k: v for k, v in before.items() if k not in pi.L8_PACKS}
        out1 = td / 'regen1/inputs'
        cp = run(pkg, 'tools/prepare_inputs.py', 'build', '--out', out1)
        assert files_of(out1) == want and '(rederived_from)' in cp.stderr, (sorted(set(files_of(out1)) ^ set(want)), cp.stderr[-600:])
        aside = td / 'aside'
        aside.mkdir()
        for rel in pi.L8_PACKS:
            os.rename(inp / rel, aside / Path(rel).name)
        out2 = td / 'regen2/inputs'
        cp = run(pkg, 'tools/prepare_inputs.py', 'build', '--out', out2)
        assert files_of(out2) == want and '(carried)' in cp.stderr, cp.stderr[-800:]
        ok('make inputs (2b-carry): no change in place; byte-identical into a scratch directory with the L8 packs '
           '(re-derived) and without them (carried)')
        # ---- verify() -----------------------------------------------------------------------------------------------
        cp = run(pkg, 'tools/prepare_inputs.py', 'verify', check=False)
        assert cp.returncode == 1 and 'free_L8.pack' in cp.stderr and 'missing' in cp.stderr, cp.stderr[-500:]
        cp = run(pkg, 'tools/prepare_inputs.py', 'verify', env={'C8_ALLOW_NO_L8': '1'})
        assert json.loads(cp.stdout)['skipped'] == list(pi.L8_PACKS)
        for rel in pi.L8_PACKS:
            os.rename(aside / Path(rel).name, inp / rel)
        cp = run(pkg, 'tools/prepare_inputs.py', 'verify')
        v = json.loads(cp.stdout)
        assert v['skipped'] == [] and v['test_only_reasons'] == [], v
        mp = inp / 'd3/MEMBERS_d3.sha256'
        orig = mp.read_bytes()
        flipped = bytearray(orig)
        flipped[10] ^= 1
        mp.unlink()
        mp.write_bytes(bytes(flipped))
        cp = run(pkg, 'tools/prepare_inputs.py', 'verify', check=False)
        assert cp.returncode == 1 and 'Checksum mismatch' in cp.stderr and 'MEMBERS_d3.sha256' in cp.stderr, cp.stderr[-500:]
        man_orig = (inp / 'manifest.json').read_bytes()
        m2 = json.loads(man_orig)
        m2['sha256']['d3/MEMBERS_d3.sha256'] = sha(bytes(flipped))
        (inp / 'manifest.json').unlink()
        (inp / 'manifest.json').write_text(json.dumps(m2, indent=2) + '\n')
        cp = run(pkg, 'tools/prepare_inputs.py', 'verify', check=False)
        assert cp.returncode == 1 and 'd=3 SHA256SUMS lists' in cp.stderr, cp.stderr[-500:]
        mp.unlink()
        mp.write_bytes(orig)
        (inp / 'manifest.json').unlink()
        (inp / 'manifest.json').write_bytes(man_orig)
        run(pkg, 'tools/prepare_inputs.py', 'verify')
        ok('verify(): accepts (no test-only reason); missing L8 refused unless C8_ALLOW_NO_L8=1; a one-byte change to '
           'd3/MEMBERS_d3.sha256 refused, and with its pin moved along the broken chain refused')
        # ---- a second make inputs-l8, make link-l8 ----------------------------------------------------------------------
        before = files_of(inp)
        run(pkg, 'tools/prepare_inputs.py', 'l8', '--d3payload', payload, '--d3pin', pin, '--store', store, '--h1', h1,
            '--fixture-h1-pin', h1pin)
        assert files_of(inp) == before and len([p for p in (store / 'packs').iterdir()]) == 2
        for rel in pi.L8_PACKS:
            (inp / rel).unlink()
        cp = run(pkg, 'tools/prepare_inputs.py', 'link-l8', '--store', store)
        assert all(x['link'] == 'hard link' for x in json.loads(cp.stdout).values()), cp.stdout
        cp = run(pkg, 'tools/prepare_inputs.py', 'link-l8', '--store', store)
        assert all(x['link'] == 'present' for x in json.loads(cp.stdout).values()), cp.stdout
        (inp / 'packs/power_L8.pack').unlink()
        (inp / 'packs/power_L8.pack').write_bytes(b'something else\n')
        cp = run(pkg, 'tools/prepare_inputs.py', 'link-l8', '--store', store, check=False)
        assert cp.returncode == 1 and 'is not the store blob' in cp.stderr
        (inp / 'packs/power_L8.pack').unlink()
        run(pkg, 'tools/prepare_inputs.py', 'link-l8', '--store', store)
        assert files_of(inp) == before
        ok('a second make inputs-l8 changes nothing (store blobs reused); make link-l8 links, is idempotent, refuses a '
           'different file in the way')
        # ---- gate 6 on the miniature ---------------------------------------------------------------------------------
        ev = td / 'ev'
        run(pkg, 'gen3/gates_d3.py', 'gate6', '--evidence', ev, check=False)
        g6 = json.loads((ev / 'gate6.json').read_text())
        ck = g6['checks']
        assert all(ck[k]['passed'] for k in ('a_c7d3_rows', 'b_c7d3_payload_digest', 'c_l3_l6_packs_a6ce987')), ck
        assert ck['d_l7_members_d3']['errors'] == [] and ck['d_l7_members_d3']['chain'] is True
        assert ck['d_l7_members_d3']['new_members'] == {'free': 2, 'power': 1} and ck['d_l7_members_d3']['new_s_G'] == {'4': 3}
        ok('gates_d3.py gate6: C7(3) rows (3,511), payload digest, L3-L6 packs; every L7 member at its MEMBERS_d3 hash')
        # ---- inputs_mini --------------------------------------------------------------------------------------------
        run(pkg, 'tools/prepare_inputs.py', 'mini')
        mini = pkg / pi.MINI
        mm = json.loads((mini / 'manifest.json').read_bytes())
        assert mm['selection'] == {s: sel['L8'][s] for s in SECTORS} and mm['test_inputs'] == pi.MINI_LABEL
        assert sorted(p.relative_to(mini).as_posix() for p in mini.rglob('*') if p.is_file()) == sorted(pi.MINI_OWN)
        again = files_of(mini)
        run(pkg, 'tools/prepare_inputs.py', 'mini')
        assert files_of(mini) == again
        z = td / 'mini_inputs'
        run(pkg, 'tools/prepare_inputs.py', 'mini-materialize', '--to', z)
        cp = run(pkg, 'tools/prepare_inputs.py', 'gate', '--test-only', env={'C8_INPUTS': str(z)})
        assert json.loads(cp.stdout)['test_only'] is True
        cp = run(pkg, 'tools/prepare_inputs.py', 'gate', env={'C8_INPUTS': str(z)}, check=False)
        assert cp.returncode == 1 and 'non-test plan reads only the package inputs' in cp.stderr
        x = td / 'x'
        run(pkg, 'tools/members.py', 'extract', '--inputs', z, '--sector', 'power', '--L', 8, '--ids', '8', '--to', x)
        assert (x / 'power/L8/G8.txt').read_bytes() == (stage / 'L8_power/G8.txt').read_bytes()
        ok('inputs_mini: deterministic; materialized, verified, test-only through the gate; members.py extracts an L8 '
           'member byte for byte')
        # S4-003: `mini --out inputs` (the L8 packs present, so the build would get as far as writing) is refused
        # before anything is read or written; the package inputs keep every byte
        before = files_of(inp)
        cp = run(pkg, 'tools/prepare_inputs.py', 'mini', '--out', 'inputs', check=False)
        assert cp.returncode == 1 and 'overlaps the package inputs' in cp.stderr and files_of(inp) == before, \
            (cp.returncode, cp.stderr[-600:], sorted(k for k in set(before) | set(files_of(inp)) if before.get(k) != files_of(inp).get(k)))
        ok('inputs_mini: prepare_inputs.py mini --out inputs is refused before writing (S4-003)')
        # R2-S1-05: the default destination tests/fixtures/inputs_mini symlinked to the package inputs, and an --out whose
        # packs/ links to inputs/packs, are refused before anything is written; the package inputs keep every byte
        aside = mini.with_name('inputs_mini.aside')
        mini.rename(aside)
        mini.symlink_to(inp)
        try:
            cp = run(pkg, 'tools/prepare_inputs.py', 'mini', check=False)
        finally:
            mini.unlink()
            aside.rename(mini)
        nest = td / 'nest_out'
        nest.mkdir()
        (nest / 'packs').symlink_to(inp / 'packs')
        cp2 = run(pkg, 'tools/prepare_inputs.py', 'mini', '--out', nest, check=False)
        after = files_of(inp)
        assert all(c.returncode == 1 and 'overlaps the package inputs' in c.stderr for c in (cp, cp2)) and after == before \
            and sorted(q.name for q in nest.iterdir()) == ['packs'] and files_of(mini) == again, \
            (cp.returncode, cp.stderr[-400:], cp2.returncode, cp2.stderr[-400:], sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)))
        ok('inputs_mini: prepare_inputs.py mini with its default destination symlinked to the package inputs, and with an '
           '--out whose packs/ links to inputs/packs, is refused before writing; every package input byte unchanged (R2-S1-05)')
        print(json.dumps({'status': 'passed', 'tests': len(passed), 'seconds': round(time.time() - t0, 1)}))
        return 0
    finally:
        if a.keep:
            print('scratch kept:', td)
        else:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
