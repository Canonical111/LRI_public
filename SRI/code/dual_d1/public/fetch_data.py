#!/usr/bin/env python3
"""Fetch the hosted files of the dual_d1 snapshot (new tool, 2026-10-15; download added 2026-10-18). Run from code/dual_d1/.

The weight-6 C7 certificate (57 MB) is over the repository's 50 MB file limit (public/HOSTED.json). It is hosted in the
project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) under the flat name `hosted_name`. This tool
takes each file from
  (default)  its hosted_url (https://zenodo.org/records/23466766/files/<hosted_name>), downloaded with urllib;
             --url-base replaces the record's base URL (for a mirror, or a local copy given as file:///<dir>);
  --zip      the compendium's original archive LRI_1d_full_research_bundle.zip (2026-10-02; members
             LRI_research_compendium/<path>; read with zipfile, nothing else is extracted), or
  --dir      a directory that holds the files at their paths (for example an unpacked copy of that archive),
checks its sha256 and size against public/HOSTED.json (= the compendium's reproduction/MANIFEST.json), and writes it
to <work>/hosted/<path>. A file already present with the right sha256 is not fetched again. Exit status 1 only if a
fetch was attempted and failed (a report without a source exits 0, as replay-full expects).
Usage: python3 public/fetch_data.py [--zip FILE | --dir DIR | --url-base URL] [--work DIR] [--status]
"""
import argparse, hashlib, json, shutil, sys, urllib.request, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
PLACEHOLDER = 'ZENODO_RECORD_URL'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def good(out, f):
    return out.is_file() and out.stat().st_size == f['bytes'] and sha(out) == f['sha256']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip'); ap.add_argument('--dir'); ap.add_argument('--url-base')
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--status', action='store_true', help='only report what is present')
    a = ap.parse_args()
    H = json.loads((HERE/'HOSTED.json').read_text())['files']
    dest = Path(a.work).resolve()/'hosted'
    bad, attempted = 0, False
    for f in H:
        out = dest/f['path']
        tried = None
        if not a.status and not good(out, f):
            out.parent.mkdir(parents=True, exist_ok=True)
            if a.zip:
                tried = 'member %s of %s' % (f['original_archive_member'], a.zip)
                with zipfile.ZipFile(a.zip) as z, z.open(f['original_archive_member']) as s, open(out, 'wb') as d:
                    shutil.copyfileobj(s, d, 1 << 20)
            elif a.dir:
                tried = str(Path(a.dir)/f['path'])
                shutil.copy2(Path(a.dir)/f['path'], out)
            else:
                url = (a.url_base.rstrip('/') + '/' + f['hosted_name']) if a.url_base else f.get('hosted_url') or ''
                if url and PLACEHOLDER not in url:
                    tried, attempted = url, True
                    part = out.with_suffix(out.suffix + '.part')
                    try:
                        with urllib.request.urlopen(url) as s, open(part, 'wb') as d:
                            shutil.copyfileobj(s, d, 1 << 20)
                        part.replace(out)
                    except OSError as e:
                        print('DOWNLOAD FAILED  %s: %s' % (url, e))
                        part.unlink(missing_ok=True)
        if good(out, f):
            print('OK       %s (%d bytes, sha256 %s...)' % (out, f['bytes'], f['sha256'][:16]))
        else:
            bad += 1
            print('MISSING  %s\n         %d bytes, sha256 %s\n         needed by %s\n         sources: the Zenodo data record '
                  '(file %s; %s), or the member %s of %s (%s): make fetch-data ZIP=<that file>'
                  % (out, f['bytes'], f['sha256'], f['needed_by'], f['hosted_name'],
                     'record not yet published' if PLACEHOLDER in (f.get('hosted_url') or PLACEHOLDER) else f['hosted_url'],
                     f['original_archive_member'], f['original_archive']['name'], f['original_archive']['date']))
            if tried and out.exists():
                print('         (%s gave a file of the wrong size or sha256; removed)' % tried)
                out.unlink()
    # exit 1 only if a fetch was attempted and failed; a plain status report (or an unpublished record) exits 0
    return 1 if bad and not a.status and (a.zip or a.dir or attempted) else 0


if __name__ == '__main__':
    sys.exit(main())
