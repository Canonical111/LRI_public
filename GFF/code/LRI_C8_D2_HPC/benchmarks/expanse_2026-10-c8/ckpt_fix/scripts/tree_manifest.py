#!/usr/bin/env python3
"""tree_manifest.py DIR: one line per entry "<kind> <mode> <sha256|target> <path>" (sorted), kind f/l/d-other; used on
both sides to show that an extracted export equals `git archive` (files, modes, no symlink or special file)."""
import hashlib, os, stat, sys
root = sys.argv[1]
out = []
for d, dirs, files in os.walk(root):
    for n in files + [x for x in dirs if os.path.islink(os.path.join(d, x))]:
        p = os.path.join(d, n); rel = os.path.relpath(p, root); s = os.lstat(p)
        if stat.S_ISLNK(s.st_mode): out.append(f'l {oct(stat.S_IMODE(s.st_mode))} {os.readlink(p)} {rel}')
        elif stat.S_ISREG(s.st_mode):
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
            out.append(f'f {oct(stat.S_IMODE(s.st_mode))} {h.hexdigest()} {rel}')
        else: out.append(f'x {oct(stat.S_IMODE(s.st_mode))} - {rel}')
sys.stdout.write(''.join(l + '\n' for l in sorted(out, key=lambda l: l.split(' ', 3)[3])))
