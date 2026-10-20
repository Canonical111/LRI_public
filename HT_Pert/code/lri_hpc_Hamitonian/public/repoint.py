#!/usr/bin/env python3
"""Make a re-pointed run-time copy of the lri_hpc_Hamitonian analysis (HT_Pert/code/lri_hpc_Hamitonian).

The analysis scripts were run in an agent session's temporary directory and then copied into the package; about 50 of
them still name absolute paths of the authors' machine: the session scratch directory (<TMP>/scratchpad/{eps5,
identity, ...}), the project folder (<PROJECT>/lri_hpc_Hamitonian/..., <PROJECT>/lri_eh_hpc/lri_eh) and unarchived
pkg/ copies (sys.path.insert(0, HERE/'pkg')). The shipped files are never modified. This tool copies analysis/,
analysis_original/ and lri_hpc/ into <work>/tree/ and rewrites, in the copy only, every such prefix to the copy (or
to the shipped lri_eh_hpc), in its original form and in the tokenized form the public scrub may have written
(<TMP>, <PROJECT>, <HOME>). The archived layout (HT note, appendix "Temporary paths"):
    <scratch>/identity/B/pkgref                       -> tree/            (an lri_hpc copy; rule applied first)
    <scratch>/identity                                -> tree/analysis/identity_checks
    <scratch>/eps5                                    -> tree/analysis/eps5_window
    <scratch>/eh_review                               -> tree/analysis/eh_review
    <project>/lri_hpc_Hamitonian/analysis/eh_addon_review -> tree/analysis/eh_review   (byte-identical d5_all.json)
    <project>/lri_hpc_Hamitonian                      -> tree/
    <project>/lri_eh_hpc                              -> ../lri_eh_hpc (the shipped add-on, read only)
The pkg/ imports are served by PYTHONPATH (tree/ for lri_hpc, the shipped lri_eh_hpc for lri_eh): see env().
If numpy >= 2.4, identity_checks/reconcile/refit_corrected.py line 38 (float() of a one-element 1-D array, a
TypeError there) is rewritten in the copy to take .item() of the same array (identical value); the change is logged.
The campaign plan (data/HT_1d/thermal_expanse/campaign/plan.json) is copied to tree/results/expanse/campaign/ where
write_updated_results.py looks for it.
usage: python3 public/repoint.py --work .work [--eh ../lri_eh_hpc] [--data ../../data/HT_1d]
Prints the tree path; exit 1 if a rewritten script still names an absolute private path."""
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
# Absolute prefixes as the analysis session wrote them, or as the public scrub tokenized them.
SCR = r"(?:/private/tmp/claude-\d+/[^/\s'\"]+/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}|<TMP>)/scratchpad"
PROJ = r"(?:/Users/[^/\s'\"]+/Documents/Agent[_]LRI|<HOME>/Documents/Agent[_]LRI|<PROJECT>)"
LEFT = re.compile(r"/private/tmp/claude|/Users/[A-Za-z]|<TMP>|<PROJECT>|<HOME>")
NP24 = ("float(X(np.array([l]))@cf)", "(X(np.array([l]))@cf).item()")


def rules(tree, eh):
    """(compiled pattern, replacement) in the order applied (the pkgref rule must come first)."""
    R = [(SCR + '/identity/B/pkgref', tree), (SCR + '/identity', tree + '/analysis/identity_checks'),
         (SCR + '/eps5', tree + '/analysis/eps5_window'), (SCR + '/eh_review', tree + '/analysis/eh_review'),
         (PROJ + '/lri_hpc_Hamitonian/analysis/eh_addon_review', tree + '/analysis/eh_review'),
         (PROJ + '/lri_hpc_Hamitonian', tree), (PROJ + '/lri_eh_hpc', eh)]
    return [(re.compile(a + r'(?![A-Za-z0-9_])'), b) for a, b in R]


def env(tree, eh):
    """Environment for running scripts of the copy: lri_hpc and lri_eh importable, no bytecode, one BLAS thread."""
    e = dict(os.environ)
    e['PYTHONPATH'] = os.pathsep.join([tree, eh] + ([e['PYTHONPATH']] if e.get('PYTHONPATH') else []))
    e.update(PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1')
    return e


def make(work, eh, data, quiet=False):
    tree = os.path.abspath(os.path.join(work, 'tree'))
    eh = os.path.abspath(eh)
    if os.path.exists(tree):
        shutil.rmtree(tree)
    ign = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store')
    for d in ('analysis', 'analysis_original', 'lri_hpc'):
        shutil.copytree(os.path.join(PKG, d), os.path.join(tree, d), ignore=ign)
    plan = os.path.join(data, 'thermal_expanse', 'campaign', 'plan.json')
    if os.path.exists(plan):
        os.makedirs(os.path.join(tree, 'results', 'expanse', 'campaign'))
        shutil.copy2(plan, os.path.join(tree, 'results', 'expanse', 'campaign', 'plan.json'))
    R = rules(tree, eh)
    changed, left, notes = [], [], []
    import numpy
    np24 = tuple(int(x) for x in numpy.__version__.split('.')[:2]) >= (2, 4)
    for root, _, files in os.walk(os.path.join(tree, 'analysis')):
        for f in files:
            if not f.endswith(('.py', '.sh')):
                continue
            p = os.path.join(root, f)
            src = open(p, encoding='utf-8').read()
            new = src
            for rx, b in R:
                new = rx.sub(lambda m, b=b: b, new)
            if np24 and p.endswith('identity_checks/reconcile/refit_corrected.py') and NP24[0] in new:
                new = new.replace(NP24[0], NP24[1])
                notes.append('numpy >= 2.4: refit_corrected.py line 38 float(arr) -> arr.item() in the copy')
            if new != src:
                open(p, 'w', encoding='utf-8').write(new)
                changed.append(os.path.relpath(p, tree))
            if LEFT.search(new.replace(tree, '').replace(eh, '')):
                left.append(os.path.relpath(p, tree))
    if not quiet:
        print(f'repoint: {len(changed)} scripts rewritten in {tree}; plan.json {"copied" if os.path.exists(plan) else "ABSENT"}')
        for n in notes:
            print('repoint:', n)
        if left:
            print('repoint: still naming a private path:', left)
    return tree, changed, left, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--eh', default=os.path.join(PKG, '..', 'lri_eh_hpc'))
    ap.add_argument('--data', default=os.path.join(PKG, '..', '..', 'data', 'HT_1d'))
    a = ap.parse_args()
    if not os.path.exists(os.path.join(a.eh, 'lri_eh', 'exact.py')):
        sys.exit(f'repoint: sibling package {a.eh} (lri_eh_hpc) missing')
    tree, _, left, _ = make(a.work, a.eh, a.data)
    print(tree)
    sys.exit(1 if left else 0)


if __name__ == '__main__':
    main()
