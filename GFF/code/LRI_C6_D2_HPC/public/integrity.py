#!/usr/bin/env python3
"""Check the released package against the checksum lists it ran with (no network, any OS, a few seconds).

SHA256SUMS_HPC.json is the package's own list at git commit 6aaf656 (1,546 files). The public release leaves out
benchmarks/ (validation evidence, 217 files) and the stray duplicate 'SHA256SUMS_HPC 2.json', and the public scrub may
replace account names and scratch paths in a few files that no record binds (listed in SCRUBBED). This script is the
`--ignore-missing` verification of that list: a listed file that is absent is fine only under NOT_SHIPPED; a changed file
is fine only in SCRUBBED; every other listed file, in particular src/, tools/ (5 of them pinned by the production plan),
inputs/ and reference/, must match. reference/SHA256SUMS.json (787 files of the earlier delivery) must match in full.
Files added for the release (public.mk, public/, REVIEWS.md) and build outputs are reported as unlisted.
Merged notes: the TeX notes of the earlier calculations under reference/ (and their LaTeX build artifacts and templates)
are merged into the condensed note GFF/note (author rule 2026-10-16: one TeX note per direction) and are not shipped. Both
lists keep their lines; MERGED_NOTES names exactly the paths that may be absent for that reason, and nothing else may.
SCRUBBED-list mode: public/SCRUBBED.txt, written by the release's scrub (one package-relative path per line, '#'
comments), extends SCRUBBED; a path there under src/, inputs/, reference/, the Makefile or one of the 5 tools pinned by
the production plan is refused (those files are hash-bound and must never be scrubbed).
"""
import hashlib, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
NOT_SHIPPED = ('benchmarks/', 'SHA256SUMS_HPC 2.json')
SCRUBBED = ('README.md', 'docs/HPC.md', 'slurm/run_array.sh', 'slurm/submit.sh', 'slurm/expanse_env.sh.example',
            'tests/unit_orchestration.py')
SKIP = ('.git/', 'public/out', 'bin/', '.venv/', 'runs/', 'SHA256SUMS_HPC.json')
MERGED_NOTES = tuple('reference/' + p for p in (
    'C6_numerical_methods.tex', 'C6_numerical_methods.pdf', 'C6_numerical_methods_appendix.tex',
    'long_range_ising_complete.tex', 'long_range_ising_complete.pdf',
    'code/method_appendix_template.tex', 'provenance/previous_note.tex',
    'verification/latex_artifacts/C6_numerical_methods.aux', 'verification/latex_artifacts/C6_numerical_methods.log',
    'verification/latex_artifacts/C6_numerical_methods.out', 'verification/latex_artifacts/long_range_ising_complete.aux',
    'verification/latex_artifacts/long_range_ising_complete.log', 'verification/latex_artifacts/long_range_ising_complete.out',
    'verification/latex_artifacts/long_range_ising_complete.toc',
    'baseline_previous/C6_d2_d3_precision.tex', 'baseline_previous/C6_d2_d3_precision.pdf',
    'baseline_previous/C6_precision_appendix.tex', 'baseline_previous/long_range_ising_complete.tex',
    'baseline_previous/long_range_ising_complete.pdf', 'baseline_previous/provenance/previous_note.tex',
    'baseline_previous/code/precision_appendix_template.tex'))
PROTECTED = ('src/', 'inputs/', 'reference/', 'Makefile', 'tools/production.py', 'tools/assemble.py', 'tools/common.py',
             'tools/prepare_inputs.py', 'tools/primitive_allocation.py')


def scrubbed_list():
    """The built-in SCRUBBED plus public/SCRUBBED.txt; returns (allowed, refused)."""
    f = PKG / 'public/SCRUBBED.txt'
    extra = [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')] if f.is_file() else []
    refused = [x for x in extra if x == 'Makefile' or x.startswith(PROTECTED)]
    return tuple(sorted(set(SCRUBBED) | (set(extra) - set(refused)))), refused


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def check(listing, root, label, allow_missing=(), allow_changed=(), merged=frozenset()):
    ok = absent = scrubbed = notes = 0; fails = []
    for f, h in listing.items():
        p = root / f
        if not p.is_file():
            if f in merged: notes += 1
            elif allow_missing and f.startswith(allow_missing): absent += 1
            else: fails.append('missing ' + f)
        elif f in merged: fails.append('present but listed as merged ' + f)
        elif sha(p) == h: ok += 1
        elif f in allow_changed: scrubbed += 1
        else: fails.append('changed ' + f)
    print(f"{'PASS' if not fails else 'FAIL'}  {label}: {ok} match, {absent} not shipped, {notes} merged notes not shipped, "
          f"{scrubbed} scrubbed (not record-bound), "
          f"{len(fails)} missing or changed" + ('' if not fails else ': ' + ', '.join(fails[:8])))
    return fails


def main():
    pkg = json.loads((PKG / 'SHA256SUMS_HPC.json').read_text())
    allowed, refused = scrubbed_list()
    fails = check(pkg, PKG, 'SHA256SUMS_HPC.json (package at 6aaf656)', NOT_SHIPPED, allowed, frozenset(MERGED_NOTES))
    if refused:
        print('FAIL  public/SCRUBBED.txt names hash-bound files: ' + ', '.join(refused)); fails += refused
    ref = json.loads((PKG / 'reference/SHA256SUMS.json').read_text())
    fails += check(ref, PKG / 'reference', 'reference/SHA256SUMS.json (earlier delivery, verbatim)',
                   merged=frozenset(p[len('reference/'):] for p in MERGED_NOTES))
    listed = set(pkg) | {'reference/' + f for f in ref}
    stray = [p for p in MERGED_NOTES if p not in listed]
    if stray:
        print('FAIL  MERGED_NOTES names paths that no checksum list contains: ' + ', '.join(stray)); fails += stray
    print(f'info  merged notes not shipped (one TeX note per direction): {len(MERGED_NOTES)} paths')
    unlisted = sorted(str(p.relative_to(PKG)) for p in PKG.rglob('*') if p.is_file() and str(p.relative_to(PKG)) not in pkg
                      and not str(p.relative_to(PKG)).startswith(SKIP) and '__pycache__' not in p.parts and p.name != '.DS_Store'
                      and not str(p.relative_to(PKG)).startswith('reference/'))
    print(f'info  unlisted files (added for the release or built): {len(unlisted)}: ' + ', '.join(unlisted[:12]))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
