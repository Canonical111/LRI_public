#!/usr/bin/env python3
"""Build and publish the frozen d=2 inventory tree inventory8_d2/ (PLAN.md component A, A-INV-5, handoff H1).

Layout of a tree (schema c8-inventory-d2-1):
  MANIFEST.json     classes1..8 sha256; gen/ source sha256s and git commit; compiler, flags, host, CPU; Slurm job
                    ids; counts per (L, sector, status); sha256, md5, bytes and member count of every payload tar;
                    sha256 of SHA256SUMS (which covers everything else)
  SHA256SUMS        sha256 of every file in the tree (relative path) EXCEPT MANIFEST.json and SHA256SUMS itself
  MEMBERS.sha256    sha256 of every G-file inside the tars, by member path "<tar stem>/G<id>.txt"
  inventory_L7.json, inventory_L8.json   builder inventories of both sectors: {"schema", "L", "free": [...],
                    "power": [...]}, the builders' inventory.json texts embedded byte for byte (long-double digits
                    are never re-serialized)
  selection.json    to-integrate sets (L7: all finite kernels; L8: finite kernels with s_G != 4) and the coverage
                    partition
  gates/*.json      outputs of the A-INV gates
  payload/{L7_free,L7_power,L8_free,L8_power}.tar   every finite-kernel G-file (L8 includes the finite kernels with
                    s_G = 4), members "<tar stem>/G<id>.txt" in name order; GNU tar --sort=name --mtime=@0
                    --owner=0 --group=0 --numeric-owner --format=gnu --mode=0644
  src/              the gen/ and slurm/gen/ sources of the generating commit

The checksum hierarchy is acyclic (R02): G-file members -> MEMBERS.sha256; every file except MANIFEST.json and
SHA256SUMS (MEMBERS.sha256 included) -> SHA256SUMS; SHA256SUMS -> MANIFEST.json. MANIFEST.json is pinned only from
outside the tree (HANDOFF_inventory8_d2.json, the consumers' manifests). The files are written in that order:
payload, MEMBERS.sha256, the other files, SHA256SUMS, MANIFEST.json. No file records its own hash, and the tree
records no absolute path of itself, so verified copies are byte-identical.

Publication is atomic: the tree is written to a hidden sibling directory and renamed once; an existing target is
refused, so a published tree is frozen and never overwritten (defects go to inventory8_d2_r2/, never in place).

Commands:
  build   --stage S --target T --package P --commit SHA [--jobs N] [--tar gnu|python]
          S holds L{7,8}_{free,power}/ (builder outputs) and gates/ (gen/gates.py, all passed)
  copy    --source T0 --target T --pin SHA [--move]
          verify T0 against the pin, copy it (or rename it with --move, for an rsync'ed temporary copy),
          verify the copy, and publish it atomically at T
  members --stage S --output FILE [--inventories DIR]
          MEMBERS.sha256 (and, with --inventories, inventory_L*.json) of a stage, for the cross-node check J-GEN-3
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from multiprocessing import Pool
from pathlib import Path

SCHEMA = 'c8-inventory-d2-1'
TARS = (('L7_free', 7, 'free'), ('L7_power', 7, 'power'), ('L8_free', 8, 'free'), ('L8_power', 8, 'power'))
RESERVED = ('MANIFEST.json', 'SHA256SUMS')
GNU_TAR_FLAGS = ['--sort=name', '--mtime=@0', '--owner=0', '--group=0', '--numeric-owner', '--format=gnu',
                 '--mode=0644']
D4_PIPELINE = ('The builder bodies (masks, terms, forests, weights, statuses) do not depend on d and come from '
               'gen/build_free and gen/build_power. The rate line (last line of a G-file) is the only d-dependent '
               'part: these builders write it at d=2 (parity rule, rate[S] = max(|S| odd ? 1 : 2, twice[S])/2 for '
               '0 < S < 2^E - 1, and 0 at S = 0 and S = 2^E - 1); the d=3 rate line is rewritten from these d=2 '
               'G-files by C63d\'s regenerate_rates.cpp. The builders take no d parameter (DECISIONS.md C1, '
               'acknowledged by C63d on 2026-10-03).')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def gnu_tar() -> str:
    for cand in (os.environ.get('C8_GNU_TAR'), 'tar', 'gtar'):
        if cand and shutil.which(cand):
            r = subprocess.run([cand, '--version'], capture_output=True, text=True)
            if r.returncode == 0 and 'GNU tar' in r.stdout:
                return cand
    raise SystemExit('GNU tar is required for the payload (set C8_GNU_TAR), or use --tar python in tests')


def make_tar(src_root: Path, members: list[str], out: Path, impl: str) -> None:
    """Write `members` (paths relative to src_root, already in name order) into the tar `out`."""
    if impl == 'gnu':
        lst = out.with_suffix('.list')
        lst.write_bytes(b''.join(m.encode() + b'\0' for m in members))
        try:
            subprocess.run([gnu_tar(), *GNU_TAR_FLAGS, '-C', str(src_root), '--null', '--no-recursion',
                            '-T', str(lst), '-cf', str(out)], check=True)
        finally:
            lst.unlink()
        return
    if impl != 'python':
        raise ValueError(impl)
    with tarfile.open(out, 'w', format=tarfile.GNU_FORMAT) as tf:
        for m in members:
            data = (src_root / m).read_bytes()
            ti = tarfile.TarInfo(m)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, '', ''
            tf.addfile(ti, io.BytesIO(data))


def tar_member_hashes(tar_path: Path) -> list[tuple[str, str]]:
    """(member path, sha256) of every member, in archive order; refuses anything but regular files."""
    out = []
    with tarfile.open(tar_path, 'r:') as tf:
        for m in tf:
            if not m.isfile() or m.name.startswith('/') or '..' in m.name.split('/'):
                raise ValueError(f'{tar_path.name}: unsafe or non-regular member {m.name!r}')
            out.append((m.name, sha256_bytes(tf.extractfile(m).read())))
    return out


def write_tree(tmp: Path, payload: dict[str, tuple[Path, list[str]]], files: dict[str, bytes], manifest: dict,
               tar_impl: str = 'gnu') -> dict:
    """Write a complete tree into the fresh directory `tmp` in the R02 order and return the manifest.

    payload: tar stem -> (source root, member paths relative to the root, each starting with "<stem>/").
    files: other tree files (relative path -> bytes), e.g. inventories, selection, gates, src."""
    tmp.mkdir()
    (tmp / 'payload').mkdir()
    members_lines, tars = [], {}
    for stem in sorted(payload):
        root, members = payload[stem]
        if any(not m.startswith(stem + '/') for m in members) or members != sorted(members):
            raise ValueError(f'{stem}: members must be "{stem}/..." in name order')
        out = tmp / 'payload' / f'{stem}.tar'
        make_tar(root, members, out, tar_impl)
        read_back = tar_member_hashes(out)
        if [n for n, _ in read_back] != members:
            raise ValueError(f'{stem}.tar: members differ from the request')
        for name, h in read_back:
            if h != sha256_file(root / name):
                raise ValueError(f'{stem}.tar: member {name} differs from its source file')
        members_lines += [f'{h}  {n}\n' for n, h in read_back]
        tars[stem] = dict(file=f'payload/{stem}.tar', sha256=sha256_file(out), md5=md5_file(out),
                          bytes=out.stat().st_size, members=len(read_back))
    (tmp / 'MEMBERS.sha256').write_bytes(''.join(members_lines).encode())
    for rel, data in sorted(files.items()):
        if rel in RESERVED or rel == 'MEMBERS.sha256' or rel.startswith('payload/'):
            raise ValueError(f'reserved path {rel}')
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    listed = sorted((p.relative_to(tmp).as_posix() for p in tmp.rglob('*') if p.is_file()), key=str.encode)
    assert not set(listed) & set(RESERVED)
    sums = ''.join(f'{sha256_file(tmp / n)}  {n}\n' for n in listed)
    (tmp / 'SHA256SUMS').write_bytes(sums.encode())
    manifest = dict(manifest, schema=SCHEMA, payload=tars, members_file='MEMBERS.sha256',
                    sha256sums_sha256=sha256_bytes(sums.encode()), files_listed=len(listed))
    (tmp / 'MANIFEST.json').write_bytes((json.dumps(manifest, indent=1, sort_keys=True) + '\n').encode())
    return manifest


def publish_dir(tmp: Path, target: Path) -> None:
    """Atomic publication by one rename; an existing target is refused (never overwritten)."""
    if target.exists() or target.is_symlink():
        raise SystemExit(f'refusing to publish: {target} exists (a published tree is frozen)')
    os.rename(tmp, target)


def tmp_for(target: Path) -> Path:
    tag = os.environ.get('SLURM_JOB_ID') or str(os.getpid())
    tmp = target.parent / f'.{target.name}.tmp.{tag}'
    if tmp.exists():
        raise SystemExit(f'{tmp} exists: remove a stale temporary tree by hand')
    return tmp


# ---- build mode -------------------------------------------------------------------------------------------------
def finite_ids(inv_text: str) -> list[int]:
    return [g['id'] for g in json.loads(inv_text) if g['status'] == 'finite-kernel']


def stage_payload(stage: Path) -> dict[str, tuple[Path, list[str]]]:
    """Every finite-kernel G-file of the stage, checked against the builder inventory."""
    out = {}
    for stem, L, sector in TARS:
        d = stage / stem
        ids = finite_ids((d / 'inventory.json').read_text())
        on_disk = sorted(p.name for p in d.glob('G*.txt'))
        if sorted(f'G{i}.txt' for i in ids) != on_disk:
            raise SystemExit(f'{stem}: G-files on disk differ from the inventory\'s finite kernels')
        out[stem] = (stage, sorted(f'{stem}/{n}' for n in on_disk))
    return out


def combined_inventory(stage: Path, L: int) -> bytes:
    free = (stage / f'L{L}_free/inventory.json').read_bytes().rstrip(b'\n')
    power = (stage / f'L{L}_power/inventory.json').read_bytes().rstrip(b'\n')
    json.loads(free), json.loads(power)  # both must parse
    data = (b'{"schema":"c8-inventory-d2-builder-1","L":' + str(L).encode() + b',"free":' + free + b',"power":'
            + power + b'}\n')
    json.loads(data)
    return data


def counts(stage: Path) -> dict:
    out = {}
    for stem, L, sector in TARS:
        c: dict[str, int] = {}
        for g in json.loads((stage / stem / 'inventory.json').read_text()):
            c[g['status']] = c.get(g['status'], 0) + 1
        out[stem] = c
    return out


def cpu_model() -> str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def build(a) -> int:
    stage, pkg = a.stage.resolve(), a.package.resolve()
    summary = json.loads((stage / 'gates/summary.json').read_text())
    if not summary.get('passed') or summary.get('injected_failure') or summary.get('loops') != [7, 8]:
        raise SystemExit('refusing to publish: gates/summary.json does not record a full pass')
    files: dict[str, bytes] = {f'inventory_L{L}.json': combined_inventory(stage, L) for L in (7, 8)}
    cov = json.loads((stage / 'gates/coverage.json').read_text())
    sel = dict(schema='c8-inventory-d2-selection-1',
               rule='L7: all finite kernels; L8: finite kernels with s_G != 4 (the zero channel 3w_B - w_A = '
                    '6(s_G - 4)/D_G vanishes at s_G = 4). Ids are class ids of classesL.txt.',
               L7=dict(free=cov['selection']['7']['free'], power=cov['selection']['7']['power'],
                       primitive=cov['selection']['7']['primitive']),
               L8=dict(free=cov['selection']['8']['free'], power=cov['selection']['8']['power'],
                       primitive=cov['selection']['8']['primitive']),
               counts={f'L{L}_{s}': len(cov['selection'][str(L)][s]) for L in (7, 8) for s in ('free', 'power')},
               coverage_partition=cov['partitions'])
    files['selection.json'] = (json.dumps(sel, indent=1) + '\n').encode()
    for p in sorted((stage / 'gates').glob('*.json')):
        files[f'gates/{p.name}'] = p.read_bytes()
    src_sha = {}
    for sub in ('gen', 'slurm/gen'):
        for p in sorted((pkg / sub).glob('*')):
            if p.is_file() and not p.name.endswith('.pyc'):
                rel = f'{sub}/{p.name}'
                files[f'src/{rel}'] = p.read_bytes()
                src_sha[rel] = sha256_bytes(files[f'src/{rel}'])
    classes = {f'classes{L}.txt': sha256_file(pkg / f'reference/c8d1_inputs8/classes{L}.txt') for L in range(1, 9)}
    builds = {}
    for exe in ('build_free', 'build_power', 'check_edge_forests'):
        rec = (a.bin / f'{exe}.build.txt').read_text().splitlines()
        builds[exe] = dict(sha256=sha256_file(a.bin / exe), command=rec[0].split(': ', 1)[1],
                           compiler=rec[1].split(': ', 1)[1])
    manifest = dict(
        created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), dimension=2, loops=[7, 8],
        package='LRI_C8_D2_HPC', git_commit=a.commit, classes_sha256=classes, gen_sources_sha256=src_sha,
        builders=builds, host=socket.gethostname(), cpu=cpu_model(), machine=platform.machine(),
        threads=os.environ.get('C8_GEN_THREADS'), slurm_job_ids=sorted({x for x in a.slurm_jobs if x}),
        counts=counts(stage), selection_counts=sel['counts'], gates=summary.get('gates'),
        d_pipeline=D4_PIPELINE,
        checksum_hierarchy='G-file members -> MEMBERS.sha256; every file except MANIFEST.json and SHA256SUMS -> '
                           'SHA256SUMS; SHA256SUMS -> MANIFEST.json (sha256sums_sha256); MANIFEST.json is pinned '
                           'only from outside the tree (HANDOFF_inventory8_d2.json). Verify a copy with '
                           'gen/verify_inventory.py TREE --pin <sha256 of MANIFEST.json>.',
        member_layout='payload/<stem>.tar holds <stem>/G<id>.txt, id = class id in classesL.txt; text G-files, '
                      'magic C7D2GRAPH1, the C7(2) format',
        defects='A published tree is never modified. A defect found later is published as inventory8_d2_r2/ '
                'with SUPERSEDES.json naming it and the affected classes; the HANDOFF is updated and both packages '
                're-pin.')
    target = a.target.resolve()
    tmp = tmp_for(target)
    try:
        man = write_tree(tmp, stage_payload(stage), files, manifest, a.tar)
        verify = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('verify_inventory.py')),
                                 str(tmp), '--pin', sha256_file(tmp / 'MANIFEST.json')])
        if verify.returncode != 0:
            raise SystemExit('the freshly written tree does not verify')
        publish_dir(tmp, target)
    except BaseException:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise
    pin = sha256_file(target / 'MANIFEST.json')
    print(json.dumps(dict(published=str(target), manifest_sha256=pin, manifest_md5=md5_file(target / 'MANIFEST.json'),
                          payload={k: v['members'] for k, v in man['payload'].items()}), indent=1))
    return 0


# ---- copy mode --------------------------------------------------------------------------------------------------
def verify_tree(tree: Path, pin: str) -> None:
    r = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('verify_inventory.py')), str(tree),
                        '--pin', pin])
    if r.returncode != 0:
        raise SystemExit(f'{tree} does not verify against the pin {pin}')


def copy(a) -> int:
    source, target = a.source.resolve(), a.target.resolve()
    if target.exists():
        raise SystemExit(f'refusing to publish: {target} exists (a published tree is frozen)')
    verify_tree(source, a.pin)
    if a.move:
        publish_dir(source, target)
    else:
        tmp = tmp_for(target)
        try:
            shutil.copytree(source, tmp, symlinks=False)
            verify_tree(tmp, a.pin)
            publish_dir(tmp, target)
        except BaseException:
            if tmp.exists():
                shutil.rmtree(tmp)
            raise
    verify_tree(target, a.pin)
    print(f'published {target} (MANIFEST.json sha256 {a.pin})')
    return 0


# ---- members mode (J-GEN-3) -------------------------------------------------------------------------------------
def _hash_member(args):
    root, name = args
    return name, sha256_file(Path(root) / name)


def members(a) -> int:
    stage = a.stage.resolve()
    payload = stage_payload(stage)
    jobs = [(str(root), m) for stem in sorted(payload) for root, ms in [payload[stem]] for m in ms]
    with Pool(a.jobs) as pool:
        hashed = pool.map(_hash_member, jobs, chunksize=64)
    a.output.write_bytes(''.join(f'{h}  {n}\n' for n, h in hashed).encode())
    if a.inventories:
        a.inventories.mkdir(parents=True, exist_ok=True)
        for L in (7, 8):
            (a.inventories / f'inventory_L{L}.json').write_bytes(combined_inventory(stage, L))
    print(f'{len(hashed)} members written to {a.output}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--stage', type=Path, required=True)
    b.add_argument('--target', type=Path, required=True)
    b.add_argument('--package', type=Path, required=True)
    b.add_argument('--bin', type=Path, required=True)
    b.add_argument('--commit', required=True)
    b.add_argument('--slurm-jobs', nargs='*', default=[os.environ.get('SLURM_JOB_ID', '')])
    b.add_argument('--tar', choices=('gnu', 'python'), default='gnu')
    c = sub.add_parser('copy')
    c.add_argument('--source', type=Path, required=True)
    c.add_argument('--target', type=Path, required=True)
    c.add_argument('--pin', required=True)
    c.add_argument('--move', action='store_true')
    m = sub.add_parser('members')
    m.add_argument('--stage', type=Path, required=True)
    m.add_argument('--output', type=Path, required=True)
    m.add_argument('--inventories', type=Path)
    m.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    a = ap.parse_args()
    if a.cmd == 'build' and not re.fullmatch(r'[0-9a-f]{40}', a.commit):
        raise SystemExit('--commit must be a full 40-hex git commit id')
    return dict(build=build, copy=copy, members=members)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
