#!/usr/bin/env python3
"""export_check.py COMMIT LISTING SITE EXPORT OUT.json (run in the git checkout, on the Mac)

LISTING is tree_manifest.py's output for an extracted export ("<kind> <mode> <sha256> <path>" per entry). The export
equals `git archive COMMIT` when: the same paths as the archive stream (and as git ls-tree -r), every file's sha256
equal to its archive member's, every entry a regular file, and every mode equal to git's recorded mode (100644 ->
0644, 100755 -> 0755) up to the group-write bit, which the extracting user's umask decides (git archive's tar.umask
0002 gives 0664/0775; a umask of 022 clears it). Writes schema c8-d2-export-check-1."""
import hashlib, io, json, subprocess, sys, tarfile
commit, listing, site, export, out = sys.argv[1:6]
full = subprocess.run(['git', 'rev-parse', commit], capture_output=True, text=True, check=True).stdout.strip()
tar = subprocess.run(['git', 'archive', '--format=tar', full], capture_output=True, check=True).stdout
arch = {}
with tarfile.open(fileobj=io.BytesIO(tar)) as t:
    for m in t.getmembers():
        if m.isfile():
            arch[m.name] = hashlib.sha256(t.extractfile(m).read()).hexdigest()
git = {}
for line in subprocess.run(['git', 'ls-tree', '-r', full], capture_output=True, text=True, check=True).stdout.splitlines():
    meta, path = line.split('\t', 1)
    git[path] = meta.split()[0]
remote, kinds = {}, {}
for line in open(listing):
    kind, mode, h, path = line.rstrip('\n').split(' ', 3)
    remote[path] = (int(mode, 8), h)
    kinds[path] = kind
want_mode = {'100644': 0o644, '100755': 0o755}
content = sorted(p for p in set(arch) & set(remote) if arch[p] != remote[p][1])
modes = sorted(p for p in set(git) & set(remote) if (remote[p][0] & ~0o020) != want_mode.get(git[p], -1))
nonreg = sorted(p for p, k in kinds.items() if k != 'f')
rec = dict(schema='c8-d2-export-check-1', commit=full, site=site, export=export,
           method='git archive --format=tar(.gz) <commit> extracted on the site; tree_manifest.py listing (sha256, lstat mode) of every '
                  'entry against the local archive stream members and git ls-tree modes (100644 -> 0644, 100755 -> 0755, group-write bit '
                  'left to the extracting umask)',
           files_git=len(git), files_archive=len(arch), files_export=len(remote),
           only_in_archive=sorted(set(arch) - set(remote))[:50], only_in_export=sorted(set(remote) - set(arch))[:50],
           content_mismatches=content[:50], mode_mismatches_vs_git=modes[:50], nonregular_in_export=nonreg[:50],
           group_write_bits=sorted({oct(m & 0o020) for m, _ in remote.values()}),
           content_listing_sha256=hashlib.sha256(''.join(f'{arch[p]}  {p}\n' for p in sorted(arch)).encode()).hexdigest())
rec['equal'] = not (rec['only_in_archive'] or rec['only_in_export'] or content or modes or nonreg) and set(git) == set(arch)
open(out, 'w').write(json.dumps(rec, indent=1) + '\n')
print(json.dumps({k: rec[k] for k in ('commit', 'files_git', 'files_archive', 'files_export', 'equal')}))
sys.exit(0 if rec['equal'] else 1)
