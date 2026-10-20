#!/usr/bin/env python3
"""Member access for the test tools (PLAN.md B, "Member access for tests").

The test tools read single G-files as <root>/<sector>/L{L}/G{id}.txt. The C8(3) kernels live only in the packs
(inputs/packs/{free,power}_L{L}.pack), so this helper extracts the requested members by inventory offset and length,
verifies each against its inventory sha256 (the inventory itself verified against inputs/manifest.json) and, for
L >= 7, against the d=3 payload's MEMBERS_d3.sha256 when the inputs hold its copy (inputs/d3/MEMBERS_d3.sha256, Stage
2b; rows "<sha256>  L<L>_<sector>/G<id>.txt"), and writes them into a private temporary directory (0700) that it
removes on exit, also after an error. validate.py, check_points.py, forced_tiers.py,
sanitize.py, class_b.py, inspect_check.py and run1_replay.py read every graph through it (L <= 6 included, one code
path for all loops). The L = 2 control graph, which is in no pack, is reference/inputs/free/L2/G0.txt, checked against
its pinned sha256. The inputs directory defaults to C8_INPUTS, else the package's inputs/ (prepare_inputs.inputs_dir).

  python3 -B tools/members.py extract --dest DIR [--inputs DIR] SECTOR:L:ID...
  python3 -B tools/members.py extract --sector S --L L --ids 1,2,3 [--inputs DIR] --to DIR
      (both write DIR/<sector>/L<L>/G<id>.txt; a refusal exits 1 and leaves no temporary directory)
  python3 -B tools/members.py mini --to DIR
      a C8_INPUTS directory from tests/fixtures/inputs_mini/ (prepare_inputs.materialize_mini), checked by verify()

Python:
  with extracted([(sector, L, id), ...]) as root: ...          # root/<sector>/L<L>/G<id>.txt, removed afterwards
  with extract([(sector, L, [ids]), ...], inputs) as root: ...  # the same, requests grouped by (sector, L)
  extract_to([(sector, L, id), ...], dest)                      # into an existing directory
  with mini_inputs() as inputs: ...                             # inputs_mini materialized in a private directory
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, digest, read_member  # noqa: E402

L2_GRAPH = ROOT / 'reference/inputs/free/L2/G0.txt'
L2_SHA256 = '0476ef907b1f4461e0261eacc06e021e6d18b6ebb4827729866c3efd03ac3fef'   # SHA256SUMS, reference/DELIVERY_MANIFEST.json


class MemberError(ValueError):
    pass


def inputs_dir(inputs=None) -> Path:
    if inputs:
        return Path(inputs).resolve()
    import prepare_inputs
    return prepare_inputs.inputs_dir()


def inventory(inputs: Path | None = None) -> dict:
    """inputs/inventory.json, after its sha256 matched inputs/manifest.json."""
    inputs = inputs_dir(inputs)
    man = json.loads((inputs / 'manifest.json').read_text())
    data = (inputs / 'inventory.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != man['sha256']['inventory.json']:
        raise MemberError(f'{inputs / "inventory.json"}: sha256 differs from {inputs / "manifest.json"}')
    return json.loads(data)


MEMBERS_D3 = 'd3/MEMBERS_d3.sha256'   # the inputs' copy of the d=3 payload's member list (Stage 2b)


def member_pins(inputs: Path) -> dict:
    """The inputs' copy of MEMBERS_d3.sha256 (Stage 2b), as {'<sector>/L<L>/G<id>.txt': sha256}; {} when absent.
    Its own sha256 is pinned in inputs/manifest.json; it is checked against that pin here."""
    f = Path(inputs) / MEMBERS_D3
    out = {}
    if f.exists():
        data = f.read_bytes()
        man = json.loads((Path(inputs) / 'manifest.json').read_text())
        if hashlib.sha256(data).hexdigest() != (man.get('sha256') or {}).get(MEMBERS_D3):
            raise MemberError(f'{f}: sha256 differs from {Path(inputs) / "manifest.json"}')
        for line in data.decode('ascii').splitlines():
            parts = line.split('  ', 1)
            if len(parts) == 2 and '_' in parts[1].split('/', 1)[0]:
                stem, g = parts[1].split('/', 1)
                L, sector = stem.split('_', 1)
                out[f'{sector}/{L}/{g}'] = parts[0]
    return out


def extract_to(selection, dest: Path, inputs: Path | None = None) -> list[Path]:
    """Writes every (sector, L, id) of `selection` as dest/<sector>/L<L>/G<id>.txt; returns the paths."""
    inputs = inputs_dir(inputs)
    inv = None
    pins = None
    rows: dict = {}
    out = []
    by_pack: dict = {}
    for sector, L, gid in selection:
        L, gid = int(L), int(gid)
        if L == 2:
            if (sector, gid) != ('free', 0):
                raise MemberError(f'the only L = 2 graph is free G0 (asked for {sector} G{gid})')
            if digest(L2_GRAPH) != L2_SHA256:
                raise MemberError(f'{L2_GRAPH}: sha256 differs from its pin {L2_SHA256}')
            p = Path(dest) / 'free/L2/G0.txt'
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(L2_GRAPH, p)
            out.append(p)
            continue
        if inv is None:
            inv = inventory(inputs)
        if pins is None and L >= 7:
            pins = member_pins(inputs)
        key = (sector, L)
        if key not in rows:
            try:
                rows[key] = {r['id']: r for r in inv[sector][str(L)]}
            except KeyError:
                raise MemberError(f'inventory: no {sector} L{L} kernels in {inputs / "inventory.json"}') from None
        r = rows[key].get(gid)
        if r is None:
            raise MemberError(f'{sector} L{L} graph {gid} is not in {inputs / "inventory.json"}')
        by_pack.setdefault(key, {})[gid] = r
    for (sector, L), rs in by_pack.items():
        pack = inputs / f'packs/{sector}_L{L}.pack'
        d = Path(dest) / sector / f'L{L}'
        d.mkdir(parents=True, exist_ok=True)
        fd = os.open(pack, os.O_RDONLY)   # each member read exactly (common.read_member: os.pread, no Python buffer; F12)
        try:
            for r in sorted(rs.values(), key=lambda r: r['offset']):
                data = read_member(fd, r['offset'], r['length'])
                h = hashlib.sha256(data).hexdigest()
                if len(data) != r['length'] or h != r['sha256']:
                    raise MemberError(f'{pack}: member G{r["id"]} at offset {r["offset"]} differs from its inventory '
                                      f'sha256 {r["sha256"]}')
                name = f'{sector}/L{L}/G{r["id"]}.txt'
                if L >= 7 and pins and pins.get(name) != h:
                    raise MemberError(f'{name}: the member differs from MEMBERS_d3.sha256 (or is not listed there)')
                p = d / f'G{r["id"]}.txt'
                p.write_bytes(data)
                out.append(p)
        finally:
            os.close(fd)
    return out


@contextlib.contextmanager
def extracted(selection, inputs: Path | None = None, base: Path | None = None):
    """A private temporary directory (0700) holding the selection (removed on exit, also after an error)."""
    td = Path(tempfile.mkdtemp(prefix='c8d3_members_', dir=base))
    try:
        extract_to(selection, td, inputs)
        yield td
    finally:
        shutil.rmtree(td, ignore_errors=True)


@contextlib.contextmanager
def mini_inputs(base: Path | None = None):
    """tests/fixtures/inputs_mini/ materialized as a C8_INPUTS directory (prepare_inputs.materialize_mini) in a private
    temporary directory, verified by prepare_inputs.verify(), removed on exit."""
    import prepare_inputs
    td = Path(tempfile.mkdtemp(prefix='c8d3_inputs_mini_', dir=base))
    try:
        d = prepare_inputs.materialize_mini(td / 'inputs')
        prepare_inputs.verify(d, env={})
        yield d
    finally:
        shutil.rmtree(td, ignore_errors=True)


@contextlib.contextmanager
def extract(requests, inputs: Path | None = None):
    """requests: [(sector, L, [ids])]; yields the root of <sector>/L<L>/G<id>.txt (removed on exit)."""
    with extracted([(s, L, g) for s, L, ids in requests for g in sorted(set(ids))], inputs) as root:
        yield root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract')
    e.add_argument('--dest', '--to', dest='dest', type=Path, required=True)
    e.add_argument('--inputs', type=Path)
    e.add_argument('--sector', choices=['free', 'power'])
    e.add_argument('--L', type=int)
    e.add_argument('--ids')
    e.add_argument('members', nargs='*', help='SECTOR:L:ID')
    mi = sub.add_parser('mini')
    mi.add_argument('--to', type=Path, required=True)
    a = ap.parse_args(argv)
    sel = []
    if a.cmd == 'mini':
        import prepare_inputs
        try:
            d = prepare_inputs.materialize_mini(a.to)
            prepare_inputs.verify(d, env={})
        except (ValueError, OSError) as ex:
            print(f'members: {ex}', file=sys.stderr)
            return 1
        print(json.dumps({'inputs_mini': str(d)}))
        return 0
    try:
        if a.sector is not None or a.L is not None or a.ids is not None:
            if a.sector is None or a.L is None or a.ids is None or a.members:
                ap.error('--sector, --L and --ids go together and replace SECTOR:L:ID')
            sel = [(a.sector, a.L, int(x)) for x in a.ids.split(',') if x]
        else:
            for m in a.members:
                s, L, g = m.split(':')
                sel.append((s, int(L), int(g)))
        if not sel:
            ap.error('no member requested')
        with extracted(sel, a.inputs) as root:
            shutil.copytree(root, a.dest, dirs_exist_ok=True)
    except (MemberError, OSError, KeyError, ValueError) as ex:
        print(f'members: {ex}', file=sys.stderr)
        return 1
    print(json.dumps({'extracted': len(sel), 'to': str(a.dest)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
