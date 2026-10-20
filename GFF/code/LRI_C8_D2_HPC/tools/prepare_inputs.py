#!/usr/bin/env python3
"""The C8(2) inputs: kernel packs, inventory and manifest (PLAN.md component B; A-IN-3, A-IN-4, A-IN-5).

Sources (never modified):
  free L3..L7   reference/LRI_C7_d2_progress/inputs/L<L>/G<id>.txt, the frozen C7(2) G-files (the free L3..L6
                legacy rate tables are reused byte for byte, never regenerated)
  power L3..L7  reference/power_mass/inputs/L<L>/G<id>.txt
  L7            the reference G-files must equal the inventory8_d2 L7 payload member for member (2,441 + 709), so
                the frozen L7 files and the published inventory are one set of bytes
  L8            the members of inventory8_d2/payload/L8_{free,power}.tar named by selection.json (16,064 + 4,336),
                each checked against MEMBERS.sha256 (the tree is first verified against the manifest's pin)
Selection: every finite kernel, except the zero-channel kernels at the top loop (C7(2)'s `L==7 and
mass_numerator==4` becomes `L==8 and mass_numerator==4`). Pack: the G-file bytes concatenated in ascending id order.

inventory.json  {sector: {L: [row, ...]}}; row = {id, primitive, s_G, wa, wb, offset, length, sha256, monomials,
                terms, cost = max(1, M*T), products, segments, addends, numerators, kernel_bytes}. wa and wb are the
                G-file header tokens (exact text, never binary64). The last five fields come from bin/c8d2_inspect,
                which runs the worker's own load_graph/prepare (x86-64 only: kernel.hpp needs an 80-bit long double).
manifest.json   schema c8-d2-hpc-inputs-1, dimension 2, order 8, epsilon 2s-2; sha256 of every input relative to
                the inputs folder (the twelve packs, gamma_d2_8.txt, two_loop.json,
                verification/two_loop_extension8.json, inventory.json); counts per sector and L;
                inventory8_d2_manifest_sha256; vendored_assembly_handoff_sha256 and vendored_assembly {handoff_sha256,
                files} copied from tools/VENDORED.json (hashed only, never parsed: PLAN "One rule governs reads of
                vendor/"); reference_manifest_sha256 and reference_c8_manifest_sha256.
                A test fixture (tests/fixtures/inputs_mini) also has `shared_with_package`: files resolved in the
                package's own inputs/ (its L3..L7 packs and small inputs), with their sha256.
The low-loop files gamma_d2_8.txt, two_loop.json and verification/two_loop_extension8.json are written by
tools/make_lowloop.py; this tool only pins them.

Commands:
  prepare_inputs.py [--folder DIR]
        verify (make inputs): every listed file at its sha256 and every vendored pin; a missing L8 pack is SKIPPED
        (L3..L7 build and verify only, PLAN component B); --require-l8 makes it an error
  prepare_inputs.py --l8 --inventory TREE [--folder DIR]
        build the two L8 packs into inputs/packs (DIR/packs) from TREE (make inputs-l8) and verify them against the
        manifest; an existing corrupt or truncated L8 pack is replaced (only the immutable inputs must verify first)
  prepare_inputs.py --regenerate DEST --inventory TREE [--inspect BIN] [--threads N]
        a complete regeneration of every generated file into DEST (J-IN-2; tests/check_inputs.py compares it)
  prepare_inputs.py --mini DEST --inventory TREE
        tests/fixtures/inputs_mini: a manifest and two L8 packs holding the 8 smallest selected L8 G-files per
        sector; its L3..L7 packs and small inputs are the package's own (shared_with_package)
verify() is the library entry point (plan, check_inputs.py, check_vendored.py): it hashes vendored files with the
hash helper common.digest and imports nothing from vendor/. C8_ALLOW_NO_L8=1 lets it skip missing L8 packs (it
prints SKIPPED; every plan made under it is test-only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from common import ROOT, digest, omp_child_env, umask_mode

SCHEMA = 'c8-d2-hpc-inputs-1'
ORDER = 8
SOURCES = {'free': ROOT / 'reference/LRI_C7_d2_progress/inputs', 'power': ROOT / 'reference/power_mass/inputs'}
SMALL = ('gamma_d2_8.txt', 'two_loop.json', 'verification/two_loop_extension8.json')
L8_PACKS = ('packs/free_L8.pack', 'packs/power_L8.pack')
TOP_SKIP_L = 8   # the top loop's zero-channel kernels (s_G = 4) are not integrated
MINI_PER_SECTOR = 8


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def dumps(obj) -> str:
    return json.dumps(obj, indent=1) + '\n'


def header(data: bytes) -> list[str]:
    h = data.split(b'\n', 1)[0].decode().split(' ')
    if len(h) != 7 or h[0] != 'C7D2GRAPH1':
        raise ValueError(f'not a C7D2GRAPH1 header: {h[:3]}')
    return h


# ---- the frozen inventory tree ----------------------------------------------------------------------------------
def verify_tree(tree: Path, pin: str | None) -> None:
    """The tree verifies against the external pin with gen/verify_inventory.py (all four steps)."""
    if not pin:
        raise SystemExit('no inventory8_d2 pin: give one in the manifest (inventory8_d2_manifest_sha256)')
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'gen/verify_inventory.py'), str(tree), '--pin', pin],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'{tree} does not verify against the inventory8_d2 pin {pin}:\n{r.stdout[-2000:]}')


def tree_members(tree: Path) -> dict[str, str]:
    out = {}
    for line in (tree / 'MEMBERS.sha256').read_bytes().decode().split('\n'):
        if line:
            h, name = line.split('  ', 1)
            out[name] = h
    return out


def l8_selection(tree: Path) -> dict[str, list[int]]:
    sel = json.loads((tree / 'selection.json').read_bytes())
    return {s: sorted(int(i) for i in sel['L8'][s]) for s in ('free', 'power')}


def builder_rows(tree: Path, L: int, sector: str) -> dict[int, dict]:
    inv = json.loads((tree / f'inventory_L{L}.json').read_bytes(), parse_float=str)
    return {g['id']: g for g in inv[sector]}


# ---- packs and rows ---------------------------------------------------------------------------------------------
def reference_items(sector: str, L: int) -> list[tuple[int, dict, bytes]]:
    """(id, builder row, G-file bytes) of every selected kernel of a reference loop, ascending id."""
    inv = json.loads((SOURCES[sector] / f'L{L}/inventory.json').read_bytes(), parse_float=str)
    out = []
    for g in sorted(inv, key=lambda g: g['id']):
        if g['status'] != 'finite-kernel' or (L == TOP_SKIP_L and g['mass_numerator'] == 4):
            continue
        out.append((g['id'], g, (SOURCES[sector] / f'L{L}/G{g["id"]}.txt').read_bytes()))
    return out


def tree_items(tree: Path, sector: str, members: dict[str, str]) -> list[tuple[int, dict, bytes]]:
    """(id, builder row, G-file bytes) of the selected L8 kernels from the payload tar, each at MEMBERS.sha256."""
    rows = builder_rows(tree, 8, sector)
    ids = l8_selection(tree)[sector]
    out = []
    with tarfile.open(tree / f'payload/L8_{sector}.tar', 'r:') as tf:
        for i in ids:
            g = rows[i]
            if g['status'] != 'finite-kernel' or g['mass_numerator'] == 4:
                raise SystemExit(f'selection.json lists L8 {sector} {i}, which is not a selected finite kernel')
            name = f'L8_{sector}/G{i}.txt'
            data = tf.extractfile(tf.getmember(name)).read()
            if sha256_bytes(data) != members.get(name):
                raise SystemExit(f'{name}: not at its MEMBERS.sha256 entry')
            out.append((i, g, data))
    return out


def check_l7_against_tree(items: dict[tuple[str, int], list], members: dict[str, str]) -> dict:
    """A-IN-3: the reference L7 G-files are the inventory8_d2 L7 payload, member for member."""
    out = {}
    for sector in ('free', 'power'):
        ref = {f'L7_{sector}/G{i}.txt': sha256_bytes(d) for i, _, d in items[(sector, 7)]}
        tree = {k: v for k, v in members.items() if k.startswith(f'L7_{sector}/')}
        if ref != tree:
            raise SystemExit(f'L7 {sector}: the reference G-files differ from the inventory8_d2 payload '
                             f'({len(set(ref) ^ set(tree))} names, {sum(ref[k] != tree[k] for k in set(ref) & set(tree))} contents)')
        out[sector] = len(ref)
    return out


def write_pack(path: Path, items: list[tuple[int, dict, bytes]]) -> list[dict]:
    rows = []
    with path.open('wb') as f:
        for i, g, data in items:
            h = header(data)
            if int(h[1]) != g['L'] or int(h[2]) != i:
                raise SystemExit(f'{path.name}: G{i} header names L{h[1]} G{h[2]}')
            M, T = int(h[5]), int(h[6])
            rows.append(dict(id=i, primitive=bool(g.get('primitive', False)), s_G=int(g['mass_numerator']), wa=h[3], wb=h[4],
                             offset=f.tell(), length=len(data), sha256=sha256_bytes(data), monomials=M, terms=T,
                             cost=max(1, M * T)))
            f.write(data)
    return rows


INSPECT_FIELDS = ('products', 'segments', 'addends', 'numerators', 'kernel_bytes')


def inspect_pack(exe: Path, pack: Path, L: int, rows: list[dict], threads: int) -> None:
    """Add the c8d2_inspect fields to rows, checking its masks and terms against the header counts."""
    with tempfile.TemporaryDirectory(prefix='c8d2_inspect_') as td:
        idx = Path(td) / 'index.txt'
        idx.write_text(''.join(f'{r["id"]} {L} {r["offset"]} {r["length"]}\n' for r in rows))
        # R1 (Stage-6 residual): the controlled OpenMP environment (no inherited OMP_*, GOMP_*, KMP_* control)
        r = subprocess.run([str(exe), str(pack), str(idx), str(threads)], capture_output=True, text=True,
                           env=omp_child_env(threads, {**os.environ, 'TMPDIR': td}, bind=False))
    if r.returncode != 0:
        raise SystemExit(f'c8d2_inspect failed on {pack.name}: {r.stderr[-1000:]}')
    got = [json.loads(line) for line in r.stdout.splitlines()]
    if [g['id'] for g in got] != [x['id'] for x in rows]:
        raise SystemExit(f'c8d2_inspect returned other graphs than asked for {pack.name}')
    for x, g in zip(rows, got):
        if (g['masks'], g['terms'], g['L']) != (x['monomials'], x['terms'], L):
            raise SystemExit(f'{pack.name} G{x["id"]}: inspector sizes differ from the header')
        if not (g['products'] > 0 and g['addends'] > 0 and g['kernel_bytes'] > 0):
            raise SystemExit(f'{pack.name} G{x["id"]}: nonpositive inspector field')
        x.update({k: g[k] for k in INSPECT_FIELDS})


def vendored_pins() -> dict:
    """The vendored assembly pins, copied from the committed tools/VENDORED.json (R15)."""
    v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
    return dict(handoff_sha256=v['handoff']['sha256'], handoff_path=v['handoff']['path'],
                files={f['vendored_path']: f['sha256'] for f in v['files']},
                source='tools/VENDORED.json')


def regenerate(dest: Path, tree: Path | None, pin: str | None, inspect: Path | None, threads: int,
               l8: bool = True) -> dict:
    """Every generated input into dest: packs, inventory.json (with the inspector fields when inspect is given),
    manifest.json; the low-loop files are copied from inputs/ (make_lowloop.py writes and verifies them).
    l8=False builds the L3..L7 part only and needs no tree (tests: the vendor/ rule spy); its manifest is incomplete."""
    (dest / 'packs').mkdir(parents=True, exist_ok=True)
    items = {(s, L): reference_items(s, L) for s in ('free', 'power') for L in range(3, 8)}
    l7 = None
    if l8:
        verify_tree(tree, pin)
        members = tree_members(tree)
        l7 = check_l7_against_tree(items, members)
        for s in ('free', 'power'):
            items[(s, 8)] = tree_items(tree, s, members)
    inv, hashes = {'free': {}, 'power': {}}, {}
    for (s, L), it in sorted(items.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        pack = dest / f'packs/{s}_L{L}.pack'
        rows = write_pack(pack, it)
        if inspect:
            inspect_pack(inspect, pack, L, rows, threads)
        inv[s][str(L)] = rows
        hashes[f'packs/{s}_L{L}.pack'] = digest(pack)
    for name in SMALL:
        data = (ROOT / 'inputs' / name).read_bytes()
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        (dest / name).write_bytes(data)
        hashes[name] = sha256_bytes(data)
    (dest / 'inventory.json').write_bytes(json.dumps(inv, separators=(',', ':')).encode() + b'\n')
    hashes['inventory.json'] = digest(dest / 'inventory.json')
    vend = vendored_pins()
    doc = dict(schema=SCHEMA, dimension=2, order=ORDER, epsilon='2s-2', sha256=dict(sorted(hashes.items())),
               counts={s: {L: len(v) for L, v in loops.items()} for s, loops in inv.items()},
               inventory8_d2_manifest_sha256=pin, inventory8_d2_l7_members=l7,
               selection_rule='every finite kernel; at L=8 not the kernels with s_G = 4 (zero channel weight)',
               vendored_assembly_handoff_sha256=vend['handoff_sha256'], vendored_assembly=vend,
               reference_manifest_sha256=digest(ROOT / 'reference/SHA256SUMS'),
               reference_c8_manifest_sha256=digest(ROOT / 'reference/SHA256SUMS_c8'),
               inspector_fields=list(INSPECT_FIELDS) if inspect else None)
    (dest / 'manifest.json').write_bytes(dumps(doc).encode())
    return doc


def mini(dest: Path, tree: Path) -> dict:
    """tests/fixtures/inputs_mini from inputs/inventory.json and the tree: the 8 smallest selected L8 G-files per
    sector (by bytes, then id), member hashes checked; everything else is the package's own inputs."""
    pkg = verify(ROOT / 'inputs', allow_no_l8=True)
    verify_tree(tree, pkg['inventory8_d2_manifest_sha256'])
    members = tree_members(tree)
    full = json.loads((ROOT / 'inputs/inventory.json').read_bytes())
    (dest / 'packs').mkdir(parents=True, exist_ok=True)
    inv, hashes = {'free': {}, 'power': {}}, {}
    for s in ('free', 'power'):
        for L in range(3, 8):
            inv[s][str(L)] = full[s][str(L)]
        rows8 = full[s]['8']
        pick = sorted(sorted(rows8, key=lambda r: (r['length'], r['id']))[:MINI_PER_SECTOR], key=lambda r: r['id'])
        builder = builder_rows(tree, 8, s)
        items = []
        with tarfile.open(tree / f'payload/L8_{s}.tar', 'r:') as tf:
            for r in pick:
                name = f'L8_{s}/G{r["id"]}.txt'
                data = tf.extractfile(tf.getmember(name)).read()
                if sha256_bytes(data) != members[name] or sha256_bytes(data) != r['sha256']:
                    raise SystemExit(f'{name}: not at its MEMBERS.sha256 and inventory entries')
                items.append((r['id'], builder[r['id']], data))
        pack = dest / f'packs/{s}_L8.pack'
        rows = write_pack(pack, items)
        for x, r in zip(rows, pick):
            x.update({k: r[k] for k in INSPECT_FIELDS if k in r})
        inv[s]['8'] = rows
        hashes[f'packs/{s}_L8.pack'] = digest(pack)
    (dest / 'inventory.json').write_bytes(json.dumps(inv, separators=(',', ':')).encode() + b'\n')
    hashes['inventory.json'] = digest(dest / 'inventory.json')
    shared = {k: v for k, v in pkg['sha256'].items() if k not in L8_PACKS and k != 'inventory.json'}
    doc = dict(schema=SCHEMA, dimension=2, order=ORDER, epsilon='2s-2', test_fixture=True,
               scope='TEST FIXTURE: the 8 smallest selected L8 G-files per sector; plans with it are test-only',
               sha256=dict(sorted(hashes.items())), shared_with_package=dict(sorted(shared.items())),
               counts={s: {L: len(v) for L, v in loops.items()} for s, loops in inv.items()},
               inventory8_d2_manifest_sha256=pkg['inventory8_d2_manifest_sha256'],
               vendored_assembly_handoff_sha256=pkg['vendored_assembly_handoff_sha256'],
               vendored_assembly=pkg['vendored_assembly'], package_manifest_sha256=digest(ROOT / 'inputs/manifest.json'),
               reference_manifest_sha256=pkg['reference_manifest_sha256'],
               reference_c8_manifest_sha256=pkg['reference_c8_manifest_sha256'])
    (dest / 'manifest.json').write_bytes(dumps(doc).encode())
    return doc


# ---- verification -----------------------------------------------------------------------------------------------
def verify(folder: Path | None = None, expected_manifest_sha256: str | None = None, allow_no_l8: bool | None = None,
           rebuild: tuple[str, ...] = ()) -> dict:
    """Check every file the inputs manifest lists (packs included), every shared package file of a fixture and every
    vendored pin; return the manifest. Vendored files are hashed with common.digest, never parsed or imported.
    rebuild (build_l8 only): manifest entries among the L8 packs that are about to be rebuilt; they are neither read
    nor required, so a corrupt or truncated pack does not block its own repair. Everything else is checked as usual."""
    if not set(rebuild) <= set(L8_PACKS):
        raise ValueError(f'rebuild may name only the L8 packs {L8_PACKS}, not {sorted(set(rebuild) - set(L8_PACKS))}')
    p = ROOT / 'inputs' if folder is None else Path(folder)
    data = (p / 'manifest.json').read_bytes()
    if expected_manifest_sha256 and sha256_bytes(data) != expected_manifest_sha256:
        raise ValueError(f'Checksum mismatch: {p / "manifest.json"}')
    m = json.loads(data)
    if m.get('schema') != SCHEMA or m.get('dimension') != 2 or m.get('order') != ORDER:
        raise ValueError(f'{p / "manifest.json"} is not a C8(2) inputs manifest (schema {SCHEMA}, order 8)')
    if allow_no_l8 is None:
        allow_no_l8 = os.environ.get('C8_ALLOW_NO_L8') == '1'
    bad, skipped = [], []
    for name, h in sorted(m['sha256'].items()):
        f = p / name
        if name in rebuild:
            continue
        if not f.is_file():
            if name in L8_PACKS and allow_no_l8:
                skipped.append(name)
            else:
                bad.append(f'{name} (missing)')
        elif digest(f) != h:
            bad.append(name)
    for name, h in sorted((m.get('shared_with_package') or {}).items()):
        f = ROOT / 'inputs' / name
        if not f.is_file():
            if name in L8_PACKS and allow_no_l8:
                skipped.append(f'package {name}')
            else:
                bad.append(f'package {name} (missing)')
        elif digest(f) != h:
            bad.append(f'package {name}')
    vend = m.get('vendored_assembly') or {}
    if vend:
        if digest(ROOT / vend['handoff_path']) != vend['handoff_sha256'] or vend['handoff_sha256'] != m.get('vendored_assembly_handoff_sha256'):
            bad.append(vend['handoff_path'])
        for name, h in sorted(vend['files'].items()):
            f = ROOT / name
            if not f.is_file() or digest(f) != h:
                bad.append(name)
    if bad:
        raise ValueError('Checksum mismatch in the inputs: ' + ', '.join(bad) + '; restore the shipped files '
                         '(git checkout, or make inputs-l8 INVENTORY=... for the L8 packs) before planning')
    if skipped:
        print('SKIPPED (no L8 packs here; plans made now are test-only): ' + ', '.join(skipped), file=sys.stderr)
    return m


def _keep_original(target: Path) -> tuple[Path, str]:
    """A hidden recoverable copy of target beside it: a hard link (the pack stays in place), or, where the file system
    has no hard links, the pack renamed aside. Returns (backup, 'link' | 'moved')."""
    while True:
        bak = target.with_name(f'.{target.name}.orig.{secrets.token_hex(6)}')
        try:
            os.link(target, bak)
            return bak, 'link'
        except FileExistsError:
            continue
        except OSError:
            if os.path.lexists(bak):
                continue
            os.rename(target, bak)
            return bak, 'moved'


def install_all(staged: list[tuple[Path, Path]]) -> None:
    """Rename every staged file over its target, all or nothing (Stage-6 round-2 finding S6R2-B-03). Each existing
    target is first kept recoverable beside itself (_keep_original); then the renames run; if any step fails, every
    target gets its original back (a target that did not exist is removed again) and the error propagates. The
    backups are removed after success or restoration; a backup that could not be restored is kept and named."""
    kept: list[tuple[Path, Path | None, str]] = []
    replaced: set[Path] = set()
    try:
        for _, target in staged:
            kept.append((target, *_keep_original(target)) if os.path.lexists(target) else (target, None, 'absent'))
        for tmp, target in staged:
            os.replace(tmp, target)
            replaced.add(target)
    except BaseException as err:
        unrestored = []
        for target, bak, how in reversed(kept):
            try:
                if how == 'absent':
                    if target in replaced:
                        target.unlink()
                elif how == 'link' and target not in replaced:
                    bak.unlink()  # the original never left its place
                else:
                    os.replace(bak, target)
            except OSError as e:
                unrestored.append(f'{target} ({type(e).__name__}: {e}; the original is at {bak})')
        if unrestored:
            raise SystemExit('installing the rebuilt L8 packs failed (' + f'{type(err).__name__}: {err}' + ') and '
                             'these packs could not be restored: ' + '; '.join(unrestored)) from err
        raise
    for _, bak, how in kept:
        if bak is not None:
            bak.unlink()


def build_l8(tree: Path, folder: Path | None = None) -> dict:
    """make inputs-l8: write the two L8 packs into inputs/packs (or folder/packs) from the tree and verify them against
    the manifest. It also repairs packs that exist but are corrupt or truncated (Stage-6 finding S6-B-01):
      1. preflight: the manifest and every immutable input (the L3..L7 packs, the small inputs, inventory.json, the
         vendored pins) verify; the two L8 packs are neither read nor required (verify(rebuild=L8_PACKS)); a test
         fixture's manifest is refused (its L8 packs are a subset, made by --mini);
      2. the tree verifies against the manifest's inventory8_d2 pin;
      3. both packs are written to temporary files beside their targets, flushed to disk and checked against their
         manifest pins and counts; only when both match are they installed, all or nothing (install_all: each existing
         pack is kept recoverable until both renames succeeded, and restored if one fails, Stage-6 round-2 finding
         S6R2-B-03); on any failure the existing packs, corrupt or not, are left as they were and no temporary or
         backup file remains;
      4. the whole folder verifies, the L8 packs required.
    An L8 pack target that exists but is not a regular file (a symlink, a directory, a special file) is refused in the
    preflight, before anything is built (S6R2-B-03)."""
    p = ROOT / 'inputs' if folder is None else Path(folder)
    m = verify(p, allow_no_l8=True, rebuild=L8_PACKS)
    if m.get('test_fixture') or m.get('shared_with_package') or any(k not in m['sha256'] for k in L8_PACKS):
        raise SystemExit(f'{p / "manifest.json"} is not a package inputs manifest with both L8 packs: '
                         'build_l8 rebuilds the package\'s own L8 packs (a fixture is made with --mini)')
    for name in L8_PACKS:
        target = p / name
        if os.path.lexists(target) and (target.is_symlink() or not target.is_file()):
            raise SystemExit(f'{target} exists but is not a regular file (a symlink, a directory or a special file): '
                             'build_l8 replaces only regular packs; move it away first. Nothing was changed')
    verify_tree(tree, m['inventory8_d2_manifest_sha256'])
    members = tree_members(tree)
    staged: list[tuple[Path, Path]] = []
    try:
        for s in ('free', 'power'):
            name = f'packs/{s}_L8.pack'
            target = p / name
            fd, tmp_name = tempfile.mkstemp(prefix=f'.{target.name}.tmp.', dir=target.parent)
            os.close(fd)
            tmp = Path(tmp_name)
            staged.append((tmp, target))
            os.chmod(tmp, umask_mode(0o666))
            rows = write_pack(tmp, tree_items(tree, s, members))
            with tmp.open('rb') as f:
                os.fsync(f.fileno())
            if digest(tmp) != m['sha256'][name] or len(rows) != m['counts'][s]['8']:
                raise SystemExit(f'the rebuilt {target.name} differs from the manifest pin; the existing pack is kept')
        install_all(staged)
    finally:
        for tmp, _ in staged:
            if tmp.exists():
                tmp.unlink()
    return verify(p, allow_no_l8=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--folder', type=Path, help='verify (or, with --l8, rebuild the L8 packs of) this inputs folder '
                                                 '(default inputs/)')
    ap.add_argument('--require-l8', action='store_true', help='verify: a missing L8 pack is an error')
    ap.add_argument('--l8', action='store_true', help='build the L8 packs into inputs/packs (make inputs-l8)')
    ap.add_argument('--regenerate', type=Path, metavar='DEST')
    ap.add_argument('--mini', type=Path, metavar='DEST')
    ap.add_argument('--inventory', type=Path, help='the frozen inventory8_d2 tree')
    ap.add_argument('--pin', help='--regenerate: the inventory8_d2 MANIFEST.json sha256 (default: the inputs manifest\'s)')
    ap.add_argument('--inspect', type=Path, help='--regenerate: bin/c8d2_inspect (x86-64)')
    ap.add_argument('--threads', type=int, default=os.cpu_count() or 1)
    a = ap.parse_args()
    if a.regenerate:
        pin = a.pin or json.loads((ROOT / 'inputs/manifest.json').read_bytes()).get('inventory8_d2_manifest_sha256')
        doc = regenerate(a.regenerate, a.inventory, pin, a.inspect, a.threads)
    elif a.mini:
        doc = mini(a.mini, a.inventory)
    elif a.l8:
        doc = build_l8(a.inventory, a.folder)
    else:
        doc = verify(a.folder, allow_no_l8=not a.require_l8)
    print(json.dumps({k: doc[k] for k in ('schema', 'counts', 'inventory8_d2_manifest_sha256') if k in doc}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
