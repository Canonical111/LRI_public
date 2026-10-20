"""Approved engine builds and their arithmetic (MSC-021). results/builds.json lists, per build id, the git commit
of the engine sources and the extra compiler flags of build_engine.sh on symmetry (Linux: g++, -march=x86-64-v3,
-fopenmp). verify(build) recomputes the build id exactly as build_engine.sh does (sha256 of cluster_engine.cpp,
dd.h, sha256.h at that commit plus the compile command) and refuses unknown or unreproducible ids. The precision
follows from the flags: -DUSE_DOUBLE -> 'double' (eps 2^-53; accumulators double-double since 3bf22f0), otherwise
'dd' (eps 2^-104).
usage: python builds.py            (verifies every listed build)"""
import os, sys, json, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MANIFEST = os.path.join(ROOT, 'results', 'builds.json')
EPS = {'double': 2.0 ** -53, 'dd': 2.0 ** -104}


class BuildError(RuntimeError):
    pass


def compute_id(commit, extra):
    src = b''.join(subprocess.run(['git', '-C', ROOT, 'show', f'{commit}:code/{f}'], capture_output=True, check=True).stdout
                   for f in ('cluster_engine.cpp', 'dd.h', 'sha256.h'))
    flags = f'-O3 -march=x86-64-v3 -ffp-contract=off -std=c++17 -Wall -Wextra {extra} -fopenmp'
    return hashlib.sha256(src + f'g++ {flags}\n'.encode()).hexdigest()[:16]


_cache = {}
def verify(build):
    """returns the manifest entry (with 'precision') of a verified, approved build; raises BuildError otherwise"""
    if build in _cache: return _cache[build]
    man = json.load(open(MANIFEST))
    ent = man.get(build)
    if ent is None or not ent.get('approved'):
        raise BuildError(f'engine build {build} is not an approved build in results/builds.json')
    try:
        got = compute_id(ent['commit'], ent['extra_flags'])
    except subprocess.CalledProcessError as e:
        raise BuildError(f'cannot reproduce build {build}: {e}')
    if got != build:
        raise BuildError(f'build {build}: sources at {ent["commit"]} with flags {ent["extra_flags"]!r} give {got}')
    prec = 'double' if '-DUSE_DOUBLE' in ent['extra_flags'].split() else 'dd'
    if ent.get('precision') != prec:
        raise BuildError(f'build {build}: recorded precision {ent.get("precision")} != flags ({prec})')
    _cache[build] = dict(ent, precision=prec, eps=EPS[prec])
    return _cache[build]


def eps(build):
    """roundoff unit of a verified build: 2^-53 (double) or 2^-104 (dd)"""
    return EPS[verify(build)['precision']]


if __name__ == '__main__':
    bad = 0
    for b in json.load(open(MANIFEST)):
        try:
            e = verify(b); print('ok ', b, e['precision'], e['commit'], e['extra_flags'] or '(none)', '-', e.get('note', ''))
        except BuildError as ex:
            bad += 1; print('BAD', ex)
    sys.exit(1 if bad else 0)
