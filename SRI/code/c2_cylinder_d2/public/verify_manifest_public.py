#!/usr/bin/env python3
"""Checksum check of the c2_cylinder_d2 package that honours the pruned export (new tool, 2026-10-15).

MANIFEST.sha256 ships verbatim (commit 98e1935; it lists every tracked file of the source repository). The public export
ships a subset; the rest is listed in public/NOT_EXPORTED.txt. Files whose placeholders were substituted at export are
listed in public/SCRUBBED.txt (if present). For every manifest entry:
  * present and sha256 equal                          -> ok
  * listed in NOT_EXPORTED.txt (or below a listed directory ending in "/") and absent -> not exported (accepted)
  * listed in SCRUBBED.txt and different              -> scrubbed (accepted), unless it is record-bound
  * anything else (missing, different)                -> FAIL
Record-bound files must match even if listed in SCRUBBED.txt: the archived raw records (checked against this manifest by
code/continuum/continuum_records.load_archived) and the solver code/hamiltonian/*.py (its sha256 set is the science
source identity eebafa82... of every production record).
No unlisted additions: every file of the package must be listed somewhere, or the check fails:
  * outside outputs/ and public/: in MANIFEST.sha256 (MANIFEST.sha256 and public.mk themselves excepted);
  * under outputs/: in public/SNAPSHOT.sha256;
  * under public/: one of the files of this overlay (PUBLIC_FILES).
Files the public repository's export writes into the package are tolerated, presence-optional, by exact path:
public/SCRUBBED.txt and, at the package root, RE-PINNED.json, RE-PINNED.md and MANIFEST.json (EXPORT_FILES).
Nothing else is tolerated (__pycache__/, *.pyc, .DS_Store and the run-time .work/ excepted).
The cluster records under outputs/ are checked by the dated snapshot public/SNAPSHOT.sha256 (selftest_c2cyl.py), and
each task directory's SHA256SUMS for the files it ships (the per-task job/run receipts and run logs are not
exported: job_receipt.json, expanse_job.json (the first Expanse version, pilot), run_receipt.json, run_log.txt).
Usage: python3 public/verify_manifest_public.py
"""
import hashlib, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
PUBLIC_FILES = {'c2cyl_common.py', 'replay_c2cyl.py', 'replay_full_c2cyl.py', 'run_suites.py', 'selftest_c2cyl.py',
                'verify_manifest_public.py', 'SNAPSHOT.sha256', 'NOT_EXPORTED.txt', 'tab_htpert_c2.json'}
EXPORT_FILES = {'public/SCRUBBED.txt', 'RE-PINNED.json', 'RE-PINNED.md', 'MANIFEST.json'}


def listed(name, pkg=PKG):
    p = Path(pkg) / 'public' / name
    return {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith('#')} if p.exists() else set()


def snapshot_names(pkg=PKG):
    p = Path(pkg) / 'public' / 'SNAPSHOT.sha256'
    return {l.split(None, 1)[1].strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith('#')} \
        if p.exists() else set()


def unlisted(pkg, man):
    """Files of the package that no list accounts for (see the module docstring)."""
    pkg = Path(pkg)
    snap = snapshot_names(pkg)
    extra = []
    for p in pkg.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(pkg).as_posix()
        parts = rel.split('/')
        if parts[0] == '.work' or '__pycache__' in parts or p.name == '.DS_Store' or rel.endswith('.pyc'):
            continue
        if rel in EXPORT_FILES or rel in ('public.mk', 'MANIFEST.sha256'):
            continue
        if parts[0] == 'outputs':
            ok = rel in snap
        elif parts[0] == 'public':
            ok = len(parts) == 2 and p.name in PUBLIC_FILES
        else:
            ok = rel in man
        if not ok:
            extra.append(rel)
    return sorted(extra)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record_bound(rel):
    return (rel.startswith('data/hamiltonian/raw/') and rel.endswith('.json')) or \
        (rel.startswith('code/hamiltonian/') and rel.endswith('.py'))


def check(pkg=PKG):
    PKG = Path(pkg)
    scr, nex = listed('SCRUBBED.txt', PKG), listed('NOT_EXPORTED.txt', PKG)
    rows = [l for l in (PKG / 'MANIFEST.sha256').read_text().splitlines() if l.strip() and not l.startswith('#')]
    man = {}
    for l in rows:
        h, rel = l.split('  ', 1)
        man[rel] = h
    ok, scrubbed, notexp, bad = 0, [], 0, []
    pref = tuple(x for x in nex if x.endswith('/'))
    not_exp = lambda rel: rel in nex or rel.startswith(pref)
    for rel, h in man.items():
        p = PKG / rel
        if not p.is_file():
            if not_exp(rel):
                notexp += 1
            else:
                bad.append(f'{rel} (missing)')
        elif not_exp(rel):
            bad.append(f'{rel} (listed as not exported but present)')
        elif sha(p) == h:
            ok += 1
        elif rel in scr and not record_bound(rel):
            scrubbed.append(rel)
        else:
            bad.append(rel)
    extra = unlisted(PKG, man)
    # task directories: the files they ship match their SHA256SUMS; absent ones are the not-exported receipts/logs
    sums_bad, sums_n, sums_absent = [], 0, set()
    for s in (sorted((PKG / 'outputs').rglob('SHA256SUMS')) if (PKG / 'outputs').is_dir() else []):
        for l in s.read_text().splitlines():
            if not l.strip():
                continue
            h, name = l.split(None, 1)
            f = s.parent / name.strip()
            if f.is_file():
                sums_n += 1
                if sha(f) != h and f.relative_to(PKG).as_posix() not in scr:
                    sums_bad.append(f.relative_to(PKG).as_posix())
            elif name.strip() in ('job_receipt.json', 'expanse_job.json', 'run_receipt.json', 'run_log.txt'):
                sums_absent.add(name.strip())
            else:
                sums_bad.append(f'{f.relative_to(PKG).as_posix()} (missing)')
    return dict(entries=len(man), ok=ok, scrubbed=scrubbed, not_exported=notexp, bad=bad, unlisted=extra,
                sums_checked=sums_n, sums_bad=sums_bad, sums_absent=sorted(sums_absent))


def main():
    r = check()
    print(f"MANIFEST.sha256: {r['entries']} entries, {r['ok']} match, {r['not_exported']} not exported, "
          f"{len(r['scrubbed'])} scrubbed {r['scrubbed'][:5]}, {len(r['bad'])} bad {r['bad'][:5]}, "
          f"{len(r['unlisted'])} unlisted shipped files {r['unlisted'][:5]}")
    print(f"outputs/**/SHA256SUMS: {r['sums_checked']} shipped files match, {len(r['sums_bad'])} bad {r['sums_bad'][:5]}; "
          f"not exported: {', '.join(r['sums_absent'])}")
    good = not r['bad'] and not r['unlisted'] and not r['sums_bad']
    print('verify_manifest_public', 'PASS' if good else 'FAIL')
    sys.exit(0 if good else 1)


if __name__ == '__main__':
    main()
