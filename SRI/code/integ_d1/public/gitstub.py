#!/usr/bin/env python3
"""Stand-in for `git` in the work copies of the integ_d1 replay and test (new tool, 2026-10-18; standard library only).

The public tree carries no git history, but the verbatim tools of the package ask git about it: the gate checks that
the design files and the frozen provenance sidecar equal the blobs committed before the data (m4b_gate.py,
provenance.committed_blob_ok), builds.py recomputes an engine build id from the sources at the build's commit, and
test_gates.py makes local clones. replay_integ.py and selftest_integ.py put a `git` wrapper that runs this file first
on PATH, in the environment of the work-copy subprocesses only. It answers exactly these queries:

  git [-C ROOT] rev-parse COMMIT:PATH      the blob id recorded in public/git_blobs.json ("blobs")
  git [-C ROOT] log --diff-filter=A --format=%h -- PATH
                                           the commit that first added PATH ("first_added")
  git [-C ROOT] show COMMIT:PATH           the content of a shipped file whose git blob id equals the recorded one
                                           (ROOT/PATH, or public/historic/COMMIT/<name> for an older version)
  git [-C ROOT] hash-object FILE           computed here: sha1 of "blob <size>\\0" + content, as git does
  git clone -q --local SRC DST             a plain copy of the work tree SRC (what a local clone of a clean tree holds)

Anything else, including `rev-parse --short HEAD` (the verbatim tools fall back to 'unknown' there; it is only used
when a record is published, which the replay never does) and any COMMIT:PATH or PATH not in the table, exits non-zero
with a message on stderr. What this proves: each queried file equals its committed blob (content identity). What it
cannot prove: the order of the commits (that a design was committed before its data); that was checked on the git
history by the code inspections (REVIEWS.md). Every answered query is appended to $INTEG_GITSTUB_LOG if it is set.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLE = json.loads((HERE/'git_blobs.json').read_text())


def blob_id(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def fail(msg, code=128):
    sys.stderr.write('fatal: git stand-in (public tree, no history): %s\n' % msg)
    sys.exit(code)


def log(kind, query):
    p = os.environ.get('INTEG_GITSTUB_LOG')
    if p:
        with open(p, 'a') as f:
            f.write('%s\t%s\n' % (kind, query))


def main(argv):
    root = Path.cwd()
    while len(argv) >= 2 and argv[0] == '-C':
        root = (root/argv[1]).resolve()
        argv = argv[2:]
    if not argv:
        fail('no command', 2)
    cmd, rest = argv[0], argv[1:]
    if cmd == 'rev-parse' and len(rest) == 1 and ':' in rest[0]:
        bid = TABLE['blobs'].get(rest[0])
        if bid is None:
            fail('no recorded blob for %s' % rest[0])
        log('rev-parse', rest[0])
        print(bid)
        return
    if cmd == 'hash-object' and len(rest) == 1:
        p = (root/rest[0]) if not os.path.isabs(rest[0]) else Path(rest[0])
        if not p.is_file():
            fail('cannot open %s' % rest[0])
        log('hash-object', rest[0])
        print(blob_id(p.read_bytes()))
        return
    if cmd == 'log' and rest[:3] == ['--diff-filter=A', '--format=%h', '--'] and len(rest) == 4:
        c = TABLE['first_added'].get(rest[3])
        if c is None:
            fail('no recorded first-add commit for %s' % rest[3])
        log('log-first-added', rest[3])
        print(c)
        return
    if cmd == 'show' and len(rest) == 1 and ':' in rest[0]:
        key = rest[0]
        bid = TABLE['blobs'].get(key)
        if bid is None:
            fail('no recorded blob for %s' % key)
        commit, path = key.split(':', 1)
        cands = []
        if key in TABLE.get('historic', {}):
            cands.append(HERE.parent/TABLE['historic'][key])
        cands.append(root/path)
        for c in cands:
            if c.is_file():
                data = c.read_bytes()
                if blob_id(data) == bid:
                    log('show', key)
                    sys.stdout.buffer.write(data)
                    return
        fail('no shipped file has the blob %s of %s' % (bid, key))
    if cmd == 'clone' and rest[:2] == ['-q', '--local'] and len(rest) == 4:
        src, dst = Path(rest[2]).resolve(), Path(rest[3])
        if dst.exists():
            fail('destination %s exists' % dst)
        shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns('__pycache__', '.work'))
        log('clone', '%s -> %s' % (src, dst))
        return
    fail('unsupported query: git %s' % ' '.join(argv), 2)


if __name__ == '__main__':
    main(sys.argv[1:])
