#!/usr/bin/env python3
"""Fetch this package's hosted files from the Zenodo data record, check them and put them in place.

The hosted files are not in git, and test and replay do not need them. public/hosted.json lists each file of the record
that belongs to this package: its name, size and sha256, and either
  place   the package path where the file goes (copied unchanged), or
  unpack  a .tar.gz extracted at the package root, with the sha256 of every member.
A file already in place with the right sha256 is not fetched again. Members must be plain files under the package root;
an existing file with a different sha256 is not overwritten (the tool stops).
usage: fetch_hosted.py --url BASE [--cache DIR] [--check]
BASE is the record's file URL (https://zenodo.org/records/<id>/files). A local directory or a file:// URL works too.
--check only reports which hosted files are in place. Standard library only."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
PLACEHOLDER = "ZENODO_RECORD_URL"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def pkg_path(rel):
    p = os.path.normpath(os.path.join(PKG, rel))
    if os.path.isabs(rel) or not p.startswith(PKG + os.sep):
        raise SystemExit(f"fetch-data: refusing path outside the package: {rel}")
    return p


def in_place(entry):
    """True when every file this entry provides is present with its sha256."""
    if "place" in entry:
        p = pkg_path(entry["place"])
        return os.path.isfile(p) and sha256(p) == entry["sha256"]
    return all(os.path.isfile(pkg_path(m)) and sha256(pkg_path(m)) == h for m, h in entry["members"].items())


def download(base, name, dest):
    tmp = dest + ".part"
    if os.path.isdir(base):
        shutil.copyfile(os.path.join(base, name), tmp)
    else:
        url = base.rstrip("/") + "/" + urllib.parse.quote(name)
        if url.startswith(("http://", "https://")):
            url += "?download=1"
        try:
            with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 22)
        except (urllib.error.URLError, OSError) as exc:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise SystemExit(f"fetch-data: download failed for {url}: {exc}")
    os.replace(tmp, dest)


def write_member(data, dest, want):
    if os.path.exists(dest):
        if sha256(dest) == want:
            return
        raise SystemExit(f"fetch-data: {os.path.relpath(dest, PKG)} exists with a different sha256; move it away first")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, dest)


def unpack(archive, entry):
    members = entry["members"]
    seen = set()
    with tarfile.open(archive, "r:gz") as t:
        for ti in t:
            if not ti.isfile() or ti.name not in members:
                raise SystemExit(f"fetch-data: unexpected member {ti.name} in {entry['name']}")
            data = t.extractfile(ti).read()
            if hashlib.sha256(data).hexdigest() != members[ti.name]:
                raise SystemExit(f"fetch-data: sha256 mismatch for member {ti.name}")
            write_member(data, pkg_path(ti.name), members[ti.name])
            seen.add(ti.name)
    missing = set(members) - seen
    if missing:
        raise SystemExit(f"fetch-data: {entry['name']} lacks {len(missing)} members, e.g. {sorted(missing)[0]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--cache", default=os.path.join(PKG, ".work", "fetch"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(os.path.join(HERE, "hosted.json")))
    base = a.url[len("file://"):] if a.url.startswith("file://") else a.url
    todo = []
    for e in spec["files"]:
        ok = in_place(e)
        where = e.get("place") or f"{len(e['members'])} files under {os.path.commonpath(list(e['members']))}/"
        print(f"{'in place' if ok else 'missing '}  {e['name']}  {e['bytes']:,} B  -> {where}")
        if not ok:
            todo.append(e)
    if a.check or not todo:
        print("fetch-data: all hosted files in place" if not todo else f"fetch-data: {len(todo)} file(s) missing")
        return 0 if not todo else 1
    if base == PLACEHOLDER:
        print(f"fetch-data: the Zenodo record is not published yet ({spec['record']}); "
              "set DATA_URL=<record file URL> or wait for the release")
        return 2
    os.makedirs(a.cache, exist_ok=True)
    for e in todo:
        local = os.path.join(a.cache, e["name"])
        if not (os.path.isfile(local) and os.path.getsize(local) == e["bytes"] and sha256(local) == e["sha256"]):
            print(f"download  {e['name']}")
            download(base, e["name"], local)
        size, h = os.path.getsize(local), sha256(local)
        if size != e["bytes"] or h != e["sha256"]:
            os.remove(local)
            raise SystemExit(f"fetch-data: {e['name']}: got {size} B sha256 {h}, expected {e['bytes']} B {e['sha256']}")
        if "place" in e:
            dest = pkg_path(e["place"])
            if os.path.exists(dest):
                raise SystemExit(f"fetch-data: {e['place']} exists with a different sha256; move it away first")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(local, dest + ".part")
            os.replace(dest + ".part", dest)
        else:
            unpack(local, e)
        print(f"OK        {e['name']}")
    done = all(in_place(e) for e in spec["files"])
    print("fetch-data: all hosted files in place" if done else "fetch-data: FAILED")
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
