#!/usr/bin/env python3
"""Download this package's hosted data files from the paper's Zenodo record, check them, and put them in place.

Usage (from the package folder, normally through `make -f public.mk fetch-data`):
  python3 -B public/fetch.py --base https://zenodo.org/records/23466766/files [--all] [--keep] [--list public/hosted.json]
(the record: https://doi.org/10.5281/zenodo.23466766; each file is <base>/<name>)

public/hosted.json lists the files: `name` (the file name in the record), `bytes`, `sha256`, `optional` (fetched only with
--all), and either `unpack` (a tar.gz, unpacked into that folder, relative to the package folder) or `dest` (the file is
placed there as it is). Each file is downloaded to public/out/downloads/, its size and sha256 are checked, and only then
is it unpacked or moved into place; a tar.gz is removed after unpacking unless --keep is given. A file already in place
at the listed sha256, or a tar.gz unpacked before (a stamp in public/out/downloads/), is not fetched again. Python
standard library only.
"""
import argparse, hashlib, json, os, shutil, sys, tarfile, urllib.error, urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
BASE = 'https://zenodo.org/records/23466766/files'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def download(url, part, size):
    req = urllib.request.Request(url, headers={'User-Agent': 'LRI_public fetch.py'})
    done = 0
    try:
        r = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f'fetch: {url}: HTTP {e.code} {e.reason}.', file=sys.stderr)
        if e.code == 404:
            print('The record publishes its files together with the paper; if it is not public yet, try again later.',
                  file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f'fetch: {url}: {e.reason} (no network, or the host is unreachable).', file=sys.stderr)
        sys.exit(2)
    with r, open(part, 'wb') as f:
        while True:
            b = r.read(1 << 22)
            if not b:
                break
            f.write(b)
            done += len(b)
            print(f'\r  {done / 2**20:9.1f} of {size / 2**20:.1f} MiB', end='', flush=True)
    print()


def safe_members(t, dest):
    root = dest.resolve()
    for m in t.getmembers():
        target = (dest / m.name).resolve()
        if os.path.isabs(m.name) or not (target == root or root in target.parents):
            raise SystemExit(f'fetch: refusing member outside the target folder: {m.name}')
        if not (m.isfile() or m.isdir()):
            raise SystemExit(f'fetch: refusing a member that is not a regular file or folder: {m.name}')
        yield m


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--base', required=True, help='the record\'s file URL, https://zenodo.org/records/<id>/files')
    ap.add_argument('--list', default=str(PKG / 'public' / 'hosted.json'))
    ap.add_argument('--all', action='store_true', help='also the files marked optional')
    ap.add_argument('--keep', action='store_true', help='keep each tar.gz in public/out/downloads/ after unpacking it')
    ap.add_argument('--again', action='store_true', help='unpack again a tar.gz that was unpacked before')
    a = ap.parse_args()
    files = [e for e in json.loads(Path(a.list).read_text()) if a.all or not e.get('optional')]
    if '://' not in a.base:
        print(f'fetch: --base {a.base} is not a URL; the record is {BASE}.')
        print('They are listed with sizes and sha256 in this package\'s DATA.md:')
        for e in files:
            print(f"  {e['name']}  {e['bytes']:,} B  sha256 {e['sha256']}")
        return 2
    dl = PKG / 'public' / 'out' / 'downloads'
    dl.mkdir(parents=True, exist_ok=True)
    for e in files:
        dest = PKG / e['dest'] if e.get('dest') else None
        if dest and dest.is_file() and dest.stat().st_size == e['bytes'] and sha256(dest) == e['sha256']:
            print(f"{e['name']}: already in place ({e['dest']})")
            continue
        stamp = dl / (e['name'] + '.unpacked')
        if e.get('unpack') and stamp.is_file() and stamp.read_text().strip() == e['sha256'] and not a.again:
            print(f"{e['name']}: already unpacked into {e['unpack']} (public/out/downloads/{stamp.name}; --again to redo)")
            continue
        got = dl / e['name']
        if not (got.is_file() and got.stat().st_size == e['bytes'] and sha256(got) == e['sha256']):
            part = dl / (e['name'] + '.part')
            print(f"{e['name']}: downloading {e['bytes'] / 2**20:.1f} MiB")
            download(f"{a.base.rstrip('/')}/{e['name']}?download=1", part, e['bytes'])
            if part.stat().st_size != e['bytes'] or sha256(part) != e['sha256']:
                raise SystemExit(f"fetch: {e['name']}: size or sha256 differs from public/hosted.json; the download is left in {part}")
            part.rename(got)
        print(f"{e['name']}: size and sha256 checked")
        if e.get('unpack'):
            target = PKG / e['unpack']
            target.mkdir(parents=True, exist_ok=True)
            with tarfile.open(got, 'r:gz') as t:
                kw = {'filter': 'fully_trusted'} if hasattr(tarfile, 'fully_trusted_filter') else {}  # members checked above
                t.extractall(target, members=list(safe_members(t, target)), **kw)
            stamp.write_text(e['sha256'] + '\n')
            print(f"{e['name']}: unpacked into {e['unpack']}")
            if not a.keep:
                got.unlink()
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(got), str(dest))
            print(f"{e['name']}: placed at {e['dest']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
