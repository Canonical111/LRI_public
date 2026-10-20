#!/usr/bin/env python3
"""Publish the d=3 payload tree d3_payload/ (PLAN.md A.2 step 5, A-INV-5). Standard library (+ GNU tar for --tar gnu).

Layout (schema c8-d3-d3-payload-1):
  payload/{L7_free,L7_power,L8_free,L8_power}.tar   every regenerated d=3 G-file of the stage (L7: all finite kernels;
                    L8: all finite kernels, the s_G = 4 ones kept for future orders), members "<stem>/G<id>.txt" in
                    name order; deterministic: GNU tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner
                    --format=gnu --mode=0644 (--tar gnu, the default on Expanse) or the same normalization written by
                    Python's tarfile (--tar python, the tests)
  MEMBERS_d3.sha256 sha256 of every member, "<64 hex>  <stem>/G<id>.txt" in archive order
  rate_audit_L7.json, rate_audit_L8.json   regenerate_rates' per-file records (file paths relative to the stage)
  gates/*.json      every JSON record of the gates directory, unchanged: the seven gate records (g3common.H1_GATES;
                    each must be present and say "passed": true) and their supporting records (g3common.GATE_SUPPORT;
                    each must be present; one that carries "passed" must say true; H1's raw check_edge_forests outputs
                    carry none, gate 3's record being their verdict). Every record must parse as a JSON object.
  gates/gate5/<stem>.subgraphs.txt   the four builder side files of A.2 step 2a (--side), unchanged
  SHA256SUMS        every file except MANIFEST_d3.json and itself
  MANIFEST_d3.json  H1's MANIFEST sha256; gen3 source sha256s and the commit; compiler, host, CPU; Slurm job ids; counts;
                    each tar's sha256, md5, bytes, members; sha256 AND md5 of SHA256SUMS
The hierarchy is acyclic: members -> MEMBERS_d3.sha256 -> SHA256SUMS -> MANIFEST_d3.json -> the external pin (the A.5
gate record). Publication is atomic: the tree is written to a hidden sibling and renamed once; an existing target is
refused (a published tree is frozen). Nothing is written under C62d's trees.

Usage: publish_d3.py --stage DIR --gates DIR --side DIR --audits DIR --target DIR --h1-pin SHA256 --commit SHA
                     [--tar gnu|python] [--slurm-jobs ID ...] [--compiler-record FILE]
Exit 0 published; 1 a gate or supporting record is missing or failed (nothing published); 2 refused or bad input
(a missing side file or rate audit included).
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
from pathlib import Path

GEN3 = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN3))
import g3common as c  # noqa: E402

SCHEMA = 'c8-d3-d3-payload-1'
STEMS = ('L7_free', 'L7_power', 'L8_free', 'L8_power')
REQUIRED_GATES = c.H1_GATES
GNU_TAR_FLAGS = ['--sort=name', '--mtime=@0', '--owner=0', '--group=0', '--numeric-owner', '--format=gnu', '--mode=0644']
GFILE = re.compile(r'G(0|[1-9][0-9]*)\.txt')
HIERARCHY = ('tar members -> MEMBERS_d3.sha256; every file except MANIFEST_d3.json and SHA256SUMS -> SHA256SUMS; '
             'SHA256SUMS -> MANIFEST_d3.json (sha256sums_sha256, sha256sums_md5); MANIFEST_d3.json -> the external pin '
             '(LRI_C8_shared/assembly/H1_gates/ gate record). Verify with gen3/verify_d3.py TREE --pin <sha256>.')


def gnu_tar() -> str:
    for cand in (os.environ.get('C8_GNU_TAR'), 'tar', 'gtar'):
        if cand and shutil.which(cand):
            r = subprocess.run([cand, '--version'], capture_output=True, text=True)
            if r.returncode == 0 and 'GNU tar' in r.stdout:
                return cand
    c.die('GNU tar is required for --tar gnu (set C8_GNU_TAR), or use --tar python')


def make_tar(root: Path, members: list[str], out: Path, impl: str) -> None:
    if impl == 'gnu':
        lst = out.with_suffix('.list')
        lst.write_bytes(b''.join(m.encode() + b'\0' for m in members))
        try:
            subprocess.run([gnu_tar(), *GNU_TAR_FLAGS, '-C', str(root), '--null', '--no-recursion', '-T', str(lst),
                            '-cf', str(out)], check=True)
        finally:
            lst.unlink()
        return
    with tarfile.open(out, 'w', format=tarfile.GNU_FORMAT) as tf:
        for m in members:
            data = (root / m).read_bytes()
            ti = tarfile.TarInfo(m)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, '', ''
            tf.addfile(ti, io.BytesIO(data))


def gate_records(d: Path) -> tuple[dict[str, bytes], list[str]]:
    """Every *.json of the gates directory, for gates/ in the tree. The seven gate records must be present and say
    "passed": true; the supporting records g3common.GATE_SUPPORT names must be present; any record that carries a
    "passed" key must say true (H1's raw check_edge_forests outputs carry none: gate 3's record is their verdict)."""
    files, errors = {}, []
    gates = {f'{g}.json' for g in REQUIRED_GATES}
    for p in sorted(d.glob('*.json')):
        data = p.read_bytes()
        try:
            rec = json.loads(data)
        except ValueError as ex:
            errors.append(f'{p}: does not parse ({ex})')
            continue
        if not isinstance(rec, dict):
            errors.append(f'{p}: not a JSON object')
        elif p.name in gates and rec.get('passed') is not True:
            errors.append(f'{p}: gate did not pass')
        elif 'passed' in rec and rec['passed'] is not True:
            errors.append(f'{p}: supporting record did not pass')
        files[f'gates/{p.name}'] = data
    for g in REQUIRED_GATES:
        if f'gates/{g}.json' not in files:
            errors.append(f'{d}/{g}.json: required gate record missing')
        for name in c.GATE_SUPPORT.get(g, ()):
            if f'gates/{name}' not in files:
                errors.append(f'{d}/{name}: supporting record of {g} missing')
    return files, errors


def side_files(d: Path, stems: list[str]) -> dict[str, bytes]:
    """The builder side files of A.2 step 2a, for gates/gate5/ in the tree (exit 2 if one is missing)."""
    out = {}
    for stem in stems:
        p = d / c.side_file(stem)
        if p.is_symlink() or not p.is_file():
            c.die(f'{p}: missing builder side file (A.2 step 2a; published under d3_payload/{c.SIDE_DIR}/)')
        out[f'{c.SIDE_DIR}/{p.name}'] = p.read_bytes()
    return out


def cpu_model() -> str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stage', required=True, type=Path)
    ap.add_argument('--gates', required=True, type=Path)
    ap.add_argument('--side', required=True, type=Path, help='the builder side files <stem>.subgraphs.txt (A.2 step 2a)')
    ap.add_argument('--audits', required=True, type=Path, help='directory with rate_audit_L7.json, rate_audit_L8.json')
    ap.add_argument('--target', required=True, type=Path)
    ap.add_argument('--h1-pin', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--tar', choices=('gnu', 'python'), default='gnu')
    ap.add_argument('--slurm-jobs', nargs='*', default=[os.environ.get('SLURM_JOB_ID', '')])
    ap.add_argument('--compiler-record', type=Path, help='regenerate_rates.build.txt')
    ap.add_argument('--stems', default=','.join(STEMS), help=argparse.SUPPRESS)   # test fixtures only
    a = ap.parse_args(argv)
    target = c.refuse_c62d(a.target.resolve(), 'publication target')
    if not re.fullmatch(r'[0-9a-f]{64}', a.h1_pin):
        c.die(f'--h1-pin {a.h1_pin!r}: not a sha256')
    if target.exists() or target.is_symlink():
        c.die(f'{target}: exists (a published tree is frozen; refusing to publish)')
    files, errors = gate_records(a.gates)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print('publish_d3: NOT published (a gate or supporting record is missing or failed)', file=sys.stderr)
        return 1
    stems = a.stems.split(',')
    side = side_files(a.side, stems)
    files.update(side)
    for L in sorted({s.split('_')[0] for s in stems}):
        p = a.audits / f'rate_audit_{L}.json'
        if not p.is_file():
            c.die(f'{p}: missing rate audit')
        files[p.name] = p.read_bytes()
    tag = os.environ.get('SLURM_JOB_ID') or str(os.getpid())
    tmp = target.parent / f'.{target.name}.tmp.{tag}'
    c.refuse_c62d(tmp, 'staging directory')
    if tmp.exists():
        c.die(f'{tmp}: exists (remove a stale temporary tree by hand)')
    tmp.mkdir(parents=True)
    (tmp / 'payload').mkdir()
    tars, member_lines, counts = {}, [], {}
    for stem in stems:
        d = a.stage / stem
        names = sorted(p.name for p in d.iterdir() if GFILE.fullmatch(p.name)) if d.is_dir() else []
        if not names:
            shutil.rmtree(tmp)
            c.die(f'{d}: no G-files')
        extra = sorted(p.name for p in d.iterdir() if not GFILE.fullmatch(p.name))
        if extra:
            shutil.rmtree(tmp)
            c.die(f'{d}: unexpected files {extra[:5]}')
        members = sorted(f'{stem}/{n}' for n in names)
        out = tmp / 'payload' / f'{stem}.tar'
        make_tar(a.stage, members, out, a.tar)
        with tarfile.open(out, 'r:') as tf:
            back = [(m.name, c.sha256_bytes(tf.extractfile(m).read())) for m in tf]
        if [n for n, _ in back] != members or any(h != c.sha256_file(a.stage / n) for n, h in back):
            shutil.rmtree(tmp)
            c.die(f'{out}: members differ from the stage')
        member_lines += [f'{h}  {n}\n' for n, h in back]
        tars[stem] = dict(file=f'payload/{stem}.tar', sha256=c.sha256_file(out), md5=c.md5_file(out),
                          bytes=out.stat().st_size, members=len(back))
        counts[stem] = len(back)
    (tmp / 'MEMBERS_d3.sha256').write_text(''.join(member_lines))
    for rel, data in sorted(files.items()):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    listed = sorted((p.relative_to(tmp).as_posix() for p in tmp.rglob('*') if p.is_file()), key=str.encode)
    sums = ''.join(f'{c.sha256_file(tmp / n)}  {n}\n' for n in listed).encode()
    (tmp / 'SHA256SUMS').write_bytes(sums)
    build = a.compiler_record.read_text() if a.compiler_record and a.compiler_record.is_file() else None
    manifest = dict(schema=SCHEMA, h1_manifest_sha256=a.h1_pin, dimension=3, loops=[7, 8], checksum_hierarchy=HIERARCHY,
                    d_pipeline='regenerate_rates (gen3/regenerate_rates.cpp) rewrote the rate line of every H1 d=2 G-file '
                               'for d=3 and copied everything else; the magic is C7D3GRAPH1',
                    gen3_commit=a.commit,
                    gen3_sources_sha256={p.name: c.sha256_file(p) for p in sorted(GEN3.iterdir())
                                         if p.is_file() and p.suffix in ('.cpp', '.py', '.sh')},
                    compiler_record=build, host=socket.gethostname(), machine=platform.machine(), cpu=cpu_model(),
                    slurm_job_ids=[j for j in a.slurm_jobs if j], counts=counts, payload=tars,
                    gate_records=sorted(k for k in files if k.startswith('gates/') and k.endswith('.json')),
                    gate5_side_files={k: c.sha256_bytes(v) for k, v in sorted(side.items())},
                    members_file='MEMBERS_d3.sha256', files_listed=len(listed),
                    sha256sums_sha256=c.sha256_bytes(sums), sha256sums_md5=hashlib.md5(sums).hexdigest())
    (tmp / 'MANIFEST_d3.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    if target.exists() or target.is_symlink():
        shutil.rmtree(tmp)
        c.die(f'{target}: appeared during publication (refusing)')
    os.rename(tmp, target)
    pin = c.sha256_file(target / 'MANIFEST_d3.json')
    print(json.dumps(dict(published=str(target), manifest_sha256=pin, counts=counts)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
