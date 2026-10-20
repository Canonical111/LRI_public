#!/usr/bin/env python3
"""`make -f public.mk fetch-data`: download and unpack the hosted C7(1) merged records into ../../data/C7_1/.

The pointer lives in public/data_C7_1.json. The archive is a file of the project's Zenodo data record
(https://doi.org/10.5281/zenodo.23466766); this target downloads it from the url given there, checks its sha256 and
unpacks it. A copy already placed in the data folder is used if its sha256 matches. Only the Tier 2 replay
(`replay-full`) needs the data; `test` and `replay` do not.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, sys, tarfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=Path, default=Path('../../data/C7_1'))
    a = ap.parse_args()
    d = json.loads((HERE / 'data_C7_1.json').read_text())
    tgz = a.data / d['tarball']
    have = bool(d.get('sha256')) and tgz.is_file() and sha(tgz) == d['sha256']   # a copy already in place is used as is
    if not have and not d.get('url'):
        print('C7(1) merged records are not hosted yet.\n' + d['status'] + '\nContents: ' + d['contents']
              + f"\nSize: {d['size']}; sha256 {d.get('sha256')}.\nWhen hosted, this target downloads {d['tarball']}, checks its sha256 and unpacks it into {a.data}/c7_hpc/.")
        return 0
    a.data.mkdir(parents=True, exist_ok=True)
    if not have:
        print('downloading', d['url'], flush=True)
        part = tgz.with_name(tgz.name + '.part')   # renamed only when complete
        try:
            with urllib.request.urlopen(d['url']) as r, part.open('wb') as f:
                shutil.copyfileobj(r, f, 1 << 22)
        except OSError as e:   # URLError and HTTPError are OSErrors
            if part.exists():
                part.unlink()
            sys.exit(f"download of {d['url']} failed: {e}\n"
                     f"Place a copy of {d['tarball']} (sha256 {d['sha256']}; record {d.get('record')}) at {tgz} and rerun.")
        part.replace(tgz)
    if sha(tgz) != d['sha256']:
        sys.exit(f"{tgz}: sha256 differs from public/data_C7_1.json")
    with tarfile.open(tgz) as t:
        for m in t.getmembers():
            if not m.name.startswith('c7_hpc/') or '..' in Path(m.name).parts or not (m.isfile() or m.isdir()):
                sys.exit('unexpected archive member: ' + m.name)
        t.extractall(a.data)
    print('unpacked into', a.data / 'c7_hpc')
    return 0


if __name__ == '__main__':
    sys.exit(main())
