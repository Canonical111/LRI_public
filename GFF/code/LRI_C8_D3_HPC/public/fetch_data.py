#!/usr/bin/env python3
"""Fetch and place the hosted C8(3) files (GFF/data/C8_3/HOSTED.json); run from code/LRI_C8_D3_HPC.

  python3 -B public/fetch_data.py [--tier replay|test|rerun|optional|all] [--data ../../data/C8_3]
                                  [--url BASE | --from-dir DIR] [--dry-run]

The files are in the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766). HOSTED.json gives, for each file, its name there ("remote": its repository path with
/ replaced by __). The 24 replay-tier tables and the 4 optional-tier tail tables come in two bundles ("bundles": one
.tar.gz each); a bundle is downloaded once, checked against its sha256, and its members are extracted into DATA and each
checked against the sha256 that HOSTED.json gives for it.

Tiers are cumulative in this order: replay (graph_replicates.csv, 332 MB: replay steps H), test (+ the L7 packs and the
two C7(3) reference tars, about 0.7 GB: test-native, test-full, test-replay), rerun (+ the two L8 packs, 8.8 GB: a
production rerun), optional (+ the L8 graph_tails.csv, about 2.1 GB: prod1/tail_ntrend/prod_tails.py only).

Every file is checked against the sha256 that HOSTED.json gives, which a git-tracked file already pins (named in
HOSTED.json); the tar members are checked against reference/DELIVERY_MANIFEST.json after extraction. Then:
  * packs/{free,power}_L7.pack are copied to inputs/packs/ (and checked against inputs/manifest.json);
  * the two tars are extracted into this package (only reference/inputs/{free,power}/L7/ and
    reference/records/production_{a,b}/ members are accepted);
  * the L8 packs stay in DATA/store/packs/<sha256>.pack and `make link-l8 STORE=DATA/store` links them into inputs/packs/.
The base URL (the record's files, https://zenodo.org/records/23466766/files) comes from --url, else $C8_3_DATA_URL, else
HOSTED.json base_url; a file is fetched from <base URL>/<remote>. --from-dir takes the files from a local directory that holds them either laid out like DATA or
under their Zenodo names.
Existing files with the right hash are kept. Exit 0 when every selected file is present and verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = ['replay', 'test', 'rerun', 'optional']
TAR_PREFIXES = ('reference/inputs/free/L7/', 'reference/inputs/power/L7/', 'reference/records/production_a/', 'reference/records/production_b/')


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def good(p: Path, f: dict) -> bool:
    if not p.is_file():
        return False
    if f.get('bytes') is not None and p.stat().st_size != f['bytes']:
        return False
    return f.get('sha256') is None or sha(p) == f['sha256']


def get(f: dict, dest: Path, url: str | None, src: Path | None) -> None:
    """Fetch HOSTED entry f (a file or a bundle) into dest; f['remote'] is its name in the record."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.part')
    if src is not None:
        cands = [src / f['name'], src / f['remote']]
        hit = next((c for c in cands if c.is_file()), None)
        if hit is None:
            raise SystemExit(f'fetch_data: {f["name"]}: not in {src} (looked for {f["name"]} and {f["remote"]})')
        shutil.copyfile(hit, tmp)
    else:
        with urllib.request.urlopen(url.rstrip('/') + '/' + f['remote']) as r, open(tmp, 'wb') as o:
            shutil.copyfileobj(r, o, 1 << 22)
    if not good(tmp, f):
        tmp.unlink()
        raise SystemExit(f'fetch_data: {f["name"]}: size or sha256 differs from HOSTED.json; removed')
    os.replace(tmp, dest)


def unbundle(bundle: Path, members: dict, data: Path) -> int:
    """Extract the members of a downloaded bundle into data; only the HOSTED entries listed for it are accepted."""
    n = 0
    with tarfile.open(bundle) as t:
        for m in t.getmembers():
            if m.isdir():
                continue
            name = m.name[2:] if m.name.startswith('./') else m.name
            f = members.get(name)
            if not m.isfile() or f is None or '..' in Path(name).parts:
                raise SystemExit(f'fetch_data: {bundle.name}: unexpected member {m.name!r}; nothing more extracted')
            out = data / name
            if good(out, f):
                n += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + '.part')
            with t.extractfile(m) as r, open(tmp, 'wb') as o:
                shutil.copyfileobj(r, o, 1 << 22)
            if not good(tmp, f):
                tmp.unlink()
                raise SystemExit(f'fetch_data: {name} from {bundle.name}: size or sha256 differs from HOSTED.json')
            os.replace(tmp, out)
            n += 1
    missing = [k for k in members if not good(data / k, members[k])]
    if missing:
        raise SystemExit(f'fetch_data: {bundle.name} lacks {len(missing)} of its members, e.g. {missing[0]}')
    return n


def extract(tar: Path) -> int:
    ref = {e['path']: e['sha256'] for e in json.loads((ROOT / 'reference/DELIVERY_MANIFEST.json').read_text())['files']}
    n = 0
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            name = m.name.lstrip('./')
            if m.isdir():
                continue
            if not m.isfile() or not name.startswith(TAR_PREFIXES) or '..' in Path(name).parts:
                raise SystemExit(f'fetch_data: {tar.name}: unexpected member {m.name!r}; nothing more extracted')
            out = ROOT / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with t.extractfile(m) as r, open(out, 'wb') as o:
                shutil.copyfileobj(r, o)
            want = ref.get(name[len('reference/'):])
            if want is None or sha(out) != want:
                raise SystemExit(f'fetch_data: {name} is not the file reference/DELIVERY_MANIFEST.json lists')
            n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tier', default='replay', choices=ORDER + ['all'])
    ap.add_argument('--data', type=Path, default=ROOT / '../../data/C8_3')
    ap.add_argument('--url')
    ap.add_argument('--from-dir', type=Path)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    data = a.data.resolve()
    doc = json.loads((data / 'HOSTED.json').read_text())
    upto = len(ORDER) if a.tier == 'all' else ORDER.index(a.tier) + 1
    sel = [f for f in doc['files'] if f['tier'] in ORDER[:upto]]
    url = a.url or os.environ.get('C8_3_DATA_URL') or doc.get('base_url')
    bundles = {b['remote']: b for b in doc.get('bundles', [])}
    total = sum(f['bytes'] or 0 for f in sel)
    print(f'fetch_data: tier {a.tier}: {len(sel)} files, {total / 1e9:.2f} GB')
    todo = [f for f in sel if not good(data / f['name'], f)]
    direct = [f for f in todo if f['remote'] not in bundles]
    need_b = sorted({f['remote'] for f in todo if f['remote'] in bundles})
    if a.dry_run or (url is None and a.from_dir is None):
        for f in direct:
            print(f'  needed: {f["name"]} ({f["bytes"]} bytes) <- {f["remote"]}')
        for r in need_b:
            print(f'  needed: bundle {r} ({bundles[r]["bytes"]} bytes, {bundles[r]["n_members"]} members)')
        if url is None and a.from_dir is None and todo:
            print('fetch_data: HOSTED.json has no base_url; give --url, $C8_3_DATA_URL or --from-dir', file=sys.stderr)
            return 2
        return 0
    for f in direct:
        print(f'  fetching {f["remote"]}', flush=True)
        get(f, data / f['name'], url, a.from_dir)
    for r in need_b:
        b = bundles[r]
        bp = data / b['name']
        if not good(bp, b):
            print(f'  fetching bundle {r}', flush=True)
            get(b, bp, url, a.from_dir)
        members = {f['name']: f for f in doc['files'] if f['remote'] == r}
        print(f'  extracted {unbundle(bp, members, data)} members of {b["name"]} (each checked against HOSTED.json)')
    # placement
    im = json.loads((ROOT / 'inputs/manifest.json').read_text())['sha256']
    for f in sel:
        p = data / f['name']
        if f['name'].startswith('packs/') and f['name'].endswith('_L7.pack'):
            dst = ROOT / 'inputs' / f['name']
            if not (dst.is_file() and sha(dst) == im[f['name']]):
                shutil.copyfile(p, dst)
                if sha(dst) != im[f['name']]:
                    raise SystemExit(f'fetch_data: {dst} differs from inputs/manifest.json')
            print(f'  placed inputs/{f["name"]}')
        elif f['name'].endswith('.tar'):
            print(f'  extracted {extract(p)} members of {f["name"]} (checked against reference/DELIVERY_MANIFEST.json)')
    if any(f['name'].startswith('store/packs/') for f in sel):
        subprocess.run(['make', 'link-l8', f'STORE={data / "store"}'], cwd=ROOT, check=True)
    print('fetch_data: done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
