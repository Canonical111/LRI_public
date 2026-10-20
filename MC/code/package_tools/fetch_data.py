#!/usr/bin/env python3
"""Download and unpack the MC files that are not in git (listed in data/HOSTED.json). Run from the MC folder.

  python3 code/package_tools/fetch_data.py [--what refit|fits|all] [--url BASE | --from-dir DIR] [--keep] [--dry-run]

  refit  the 1D block archives and merged summaries of the selected snapshots (make refit1d, refit-cited)
  fits   the per-degree fits of the selected runs (for inspection; no make target needs them)
  all    both (default)

Each downloaded file must have the size and SHA-256 that data/HOSTED.json gives. Archive members are accepted only as
regular files under data/1d/scan_data/ds<Δσ>/ in the folders HOSTED.json names, and every extracted block archive and
merged summary must have the SHA-256 that the coupling's analysis manifest (in git) pins. A member that git already
tracks is not overwritten: if it exists with the same bytes it is skipped, with other bytes it is an error.
The base URL comes from --url, else $MC_DATA_URL, else HOSTED.json base_url, the files of the Zenodo record
doi:10.5281/zenodo.23466766 (https://zenodo.org/records/23466766/files). --from-dir takes the files from a local
directory instead.
Downloads go to .work/downloads/ and are deleted after a successful unpack unless --keep. Exit 0 when every selected
file is in place and verified.
"""
import argparse, hashlib, json, os, re, shutil, sys, tarfile, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = 'data/1d/scan_data'
REFIT_DIR = r'(stage[A-Za-z0-9_]*_an|merged)_b(2048|4096|8192)_\d{8}_\d{6}'


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def manifest_pins(ds):
    """SHA-256 of every block archive and merged summary pinned by the analysis manifest of coupling ds,
    keyed by the path below ds<Δσ>/ (e.g. 'stageA_an_b2048_20260920_101653/blocks_0000.npz')."""
    d = ROOT / SCAN / f'ds{ds}'
    snap = json.loads((d / 'fits_v3_SELECTED.json').read_text())['snapshot']
    pins = {}
    for line in (d / f'analysis_v3_{snap}.manifest').read_text().splitlines():
        m = re.match(r'([0-9a-f]{64})  (.*)$', line)
        if m and f'/ds{ds}/' in m.group(2):
            rel = m.group(2).split(f'/ds{ds}/', 1)[1]
            if re.fullmatch(REFIT_DIR + r'/[A-Za-z0-9_.-]+', rel):
                pins[rel] = m.group(1)
    return pins


def member_ok(name, kind):
    """Accept data/1d/scan_data/ds<Δσ>/<folder>/<file> with folder of the archive's kind; return (ds, rel) or None."""
    m = re.fullmatch(r'data/1d/scan_data/ds([0-9.]+)/([A-Za-z0-9_]+(?:/fits)?)/([A-Za-z0-9_.-]+)', name)
    if not m or '..' in name:
        return None
    ds, folder, _ = m.groups()
    if kind == 'refit' and re.fullmatch(REFIT_DIR, folder):
        return ds, name.split(f'/ds{ds}/', 1)[1]
    if kind == 'fits' and folder.endswith('/fits'):
        sel = json.loads((ROOT / SCAN / f'ds{ds}' / 'fits_v3_SELECTED.json').read_text())['selected_run']
        if folder == f'{sel}/fits':
            return ds, name.split(f'/ds{ds}/', 1)[1]
    return None


def get(f, dest, url, src):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size == f['bytes'] and sha_file(dest) == f['sha256']:
        return
    tmp = dest.with_name(dest.name + '.part')
    if src is not None:
        shutil.copyfile(Path(src) / f['name'], tmp)
    else:
        u = url.rstrip('/') + '/' + f['name']
        print(f"downloading {f['name']} ({f['bytes'] / 1e6:.0f} MB)", flush=True)
        try:
            with urllib.request.urlopen(u) as r, open(tmp, 'wb') as o:
                shutil.copyfileobj(r, o, 1 << 22)
        except urllib.error.URLError as e:
            tmp.unlink(missing_ok=True)
            sys.exit(f"{f['name']}: download from {u} failed: {e}")
    size, digest = tmp.stat().st_size, sha_file(tmp)
    if size != f['bytes'] or digest != f['sha256']:
        tmp.unlink()
        sys.exit(f"{f['name']}: got {size} bytes, sha256 {digest}; expected {f['bytes']}, {f['sha256']}")
    tmp.replace(dest)


def unpack(f, archive):
    kind, n_new, n_same, pins_by_ds = f['kind'], 0, 0, {}
    with tarfile.open(archive, 'r:gz') as t:
        for m in t:
            if m.isdir():
                continue
            ok = member_ok(m.name, kind) if m.isfile() else None
            if ok is None:
                sys.exit(f"{f['name']}: unexpected member {m.name!r} (type {m.type!r}); nothing after it was unpacked")
            ds, rel = ok
            data = t.extractfile(m).read()
            digest = hashlib.sha256(data).hexdigest()
            if kind == 'refit':
                pins = pins_by_ds.setdefault(ds, manifest_pins(ds))
                if pins.get(rel) != digest:
                    sys.exit(f"{m.name}: sha256 {digest} is not the one the analysis manifest of ds{ds} pins ({pins.get(rel)})")
            out = ROOT / m.name
            if out.exists():
                if sha_file(out) != digest:
                    sys.exit(f"{m.name} exists with other bytes; not overwritten (git tracks it, or a local edit)")
                n_same += 1
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + '.part')
            tmp.write_bytes(data)
            os.chmod(tmp, 0o644)
            tmp.replace(out)
            n_new += 1
    if kind == 'refit':  # every pinned file of every coupling in the archive must now be present
        for ds, pins in pins_by_ds.items():
            miss = [r for r in pins if not (ROOT / SCAN / f'ds{ds}' / r).is_file()]
            if miss:
                sys.exit(f'ds{ds}: {len(miss)} pinned files missing after unpack, e.g. {miss[0]}')
    print(f"{f['name']}: {n_new} files unpacked, {n_same} already present with the same bytes")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--what', choices=('refit', 'fits', 'all'), default='all')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--url'); g.add_argument('--from-dir')
    p.add_argument('--keep', action='store_true'); p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    H = json.loads((ROOT / 'data/HOSTED.json').read_text())
    files = [f for f in H['files'] if a.what in ('all', f['kind'])]
    url = a.url or os.environ.get('MC_DATA_URL') or H['base_url']
    for f in files:
        print(f"{f['name']}  {f['bytes']} bytes  sha256 {f['sha256']}  -> {f['unpacks_to']}")
    if a.dry_run:
        return 0
    if a.from_dir is None and not re.match(r'(https?|file)://', url or ''):
        print(f"No usable base URL ({url!r}). Pass --url, set MC_DATA_URL or use --from-dir.")
        return 2
    for f in files:
        dest = ROOT / '.work/downloads' / f['name']
        get(f, dest, url, a.from_dir)
        unpack(f, dest)
        if not a.keep:
            dest.unlink()
    return 0


if __name__ == '__main__':
    sys.exit(main())
