#!/usr/bin/env python3
"""Fetch the raw per-sector engine outputs of indep_d1 (new tool, 2026-10-19). Run from code/indep_d1/.

The 293 raw chunk outputs engine/runs/<run>/*.cfg.json (131 MB; public/RAW_SHA256SUMS.txt) are not in the repository.
They are hosted in the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) as one archive
(public/HOSTED.json: hosted_name, bytes, sha256). This tool takes the archive from
  (default)  its hosted_url (https://zenodo.org/records/23466766/files/<hosted_name>), downloaded with urllib;
             --url-base replaces the record's base URL (for a mirror, or a local copy given as file:///<dir>);
  --file     a copy of the archive already on disk,
checks its size and sha256, unpacks it into <work>/raw (regular files and directories only, no absolute or '..'
paths), checks every file against public/RAW_SHA256SUMS.txt, and prints the replay-raw command. Exit status 1 only if
a fetch was attempted and failed.
Usage: python3 public/fetch_raw.py [--file ARCHIVE | --url-base URL] [--work DIR]
"""
import argparse, hashlib, json, shutil, sys, tarfile, urllib.request
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
PLACEHOLDER = 'ZENODO_RECORD_URL'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def safe_extract(archive, dest):
    with tarfile.open(archive, 'r:gz') as t:
        members = t.getmembers()
        for m in members:
            p = PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()):
                raise SystemExit('refusing archive member %r' % m.name)
        for m in members:
            out = dest/m.name
            if m.isdir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as s, open(out, 'wb') as d:
                    shutil.copyfileobj(s, d, 1 << 20)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file'); ap.add_argument('--url-base'); ap.add_argument('--work', default=str(PKG/'.work'))
    a = ap.parse_args()
    f = json.loads((HERE/'HOSTED.json').read_text())['files'][0]
    work = Path(a.work).resolve()
    arc, raw = work/f['hosted_name'], work/'raw'
    work.mkdir(parents=True, exist_ok=True)
    ok_arc = lambda p: p.is_file() and p.stat().st_size == f['bytes'] and sha(p) == f['sha256']
    attempted = False
    if a.file:
        attempted = True
        shutil.copyfile(a.file, arc)
    elif not ok_arc(arc):
        url = (a.url_base.rstrip('/') + '/' + f['hosted_name']) if a.url_base else f.get('hosted_url') or ''
        if url and PLACEHOLDER not in url:
            attempted = True
            part = arc.with_suffix(arc.suffix + '.part')
            try:
                with urllib.request.urlopen(url) as s, open(part, 'wb') as d:
                    shutil.copyfileobj(s, d, 1 << 20)
                part.replace(arc)
            except OSError as e:
                print('DOWNLOAD FAILED  %s: %s' % (url, e))
                part.unlink(missing_ok=True)
    if not ok_arc(arc):
        print('MISSING  %s (%d bytes, sha256 %s)\n         needed by %s\n         source: the Zenodo data record, file %s (%s)'
              % (f['hosted_name'], f['bytes'], f['sha256'], f['needed_by'], f['hosted_name'],
                 'record not yet published' if PLACEHOLDER in (f.get('hosted_url') or PLACEHOLDER) else f['hosted_url']))
        if arc.exists():
            print('         (the copy at %s has the wrong size or sha256; removed)' % arc)
            arc.unlink()
        return 1 if attempted else 0
    print('OK       %s (%d bytes, sha256 %s...)' % (arc, f['bytes'], f['sha256'][:16]))
    safe_extract(arc, raw)
    want = [l.split() for l in (HERE/'RAW_SHA256SUMS.txt').read_text().splitlines() if l.strip() and not l.startswith('#')]
    bad = [p for h, p in want if not (raw/p).is_file() or sha(raw/p) != h]
    if bad:
        print('FAIL     %d of %d files differ from public/RAW_SHA256SUMS.txt (first: %s)' % (len(bad), len(want), bad[0]))
        return 1
    print('OK       %d files in %s match public/RAW_SHA256SUMS.txt\nnext:    make -f public.mk replay-raw RAW=%s'
          % (len(want), raw, raw))
    return 0


if __name__ == '__main__':
    sys.exit(main())
