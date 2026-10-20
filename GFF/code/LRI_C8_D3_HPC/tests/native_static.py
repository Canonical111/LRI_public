#!/usr/bin/env python3
"""Static checks of the native code and its Makefile (PLAN.md C.1, C.2, C.8, C.9, A-KER-1 grep; Mac, seconds).

  python3 -B tests/native_static.py [--output FILE]

  * A-KER-1 (grep): no literal array size 6, 12, 14 or 28 remains in src/ or tests/point_checks.cpp
    (std::array<T,N> and C array declarations T x[N]; argv[6] and other subscripts are not sizes); the C.1 constants block and its static_asserts are present.
  * C.9 (unchanged on the default path), against reference/src (= a6ce987 src/), whitespace-insensitive: rates(),
    calculate_reference(), calculate_products() unchanged; prepare() unchanged apart from the
    #ifndef C8_TEST_UNGUARDED_INDEX / #endif pair around its index check (so every ordinary build preprocesses to the
    a6ce987 tokens); calculate_shared() unchanged apart from the A-L18 hunk; sample() unchanged apart from
    std::array<ld,6> -> std::array<ld,NLOGS> and its comment; evaluate() keeps every arithmetic statement of a6ce987
    (the shift, the moderate test, the first pass, the ratio test, the binary128 test, the MP conversion, y); the
    worker keeps a6ce987's stream mixing (as stream_seed, with (uint64_t(id)+1) for (id+1): S1-05), the Kahan step, the max_abs update, the value assignment, the
    in-block sort and the net point and grid arithmetic (the last two moved verbatim to src/stream.hpp; Net's
    constructor adds the S1-04 start-index guard).
  * C.8 Makefile, with a fake compiler and a fake worker (as tests/unit_orchestration.py's C7(3) Makefile test did):
    a single-token CPPFLAGS reaches the build record; flags that would override STRICT are refused before any compile;
    Boost < 1.70 is refused; Boost 1.86 is refused unless BOOST_ACCEPT=108600, which the record keeps; a failed
    build-info step and a backend that disagrees with --describe's mp_backend both leave no binary; `make -n` prints
    the default command lines token-identical to a6ce987's apart from file names (bin/c8d3_{gmp,decimal},
    bin/ref/c7d3_{gmp,decimal}, bin/c8d3_inspect); NUMERICS=<profile> is refused.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS: list[dict] = []


def ok(name, **kw):
    RESULTS.append({'test': name, **kw})
    print('PASS', name, flush=True)


def squash(s: str) -> str:
    return re.sub(r'\s+', '', s)


def function(text: str, head: str) -> str:
    """The text of the definition starting at `head` through its matching closing brace."""
    i = text.index(head)
    j = text.index('{', i)
    depth = 0
    for k in range(j, len(text)):
        depth += {'{': 1, '}': -1}.get(text[k], 0)
        if depth == 0:
            return text[i:k + 1]
    raise ValueError(head)


def _statement_end(text: str, i: int) -> int:
    """End (exclusive) of the statement starting at text[i]: a {...} block, else up to the first ';' outside brackets."""
    if text[i] == '{':
        depth = 0
        for k in range(i, len(text)):
            depth += {'{': 1, '}': -1}.get(text[k], 0)
            if depth == 0:
                return k + 1
        raise ValueError('unbalanced block')
    depth = 0
    for k in range(i, len(text)):
        c = text[k]
        depth += {'(': 1, '[': 1, '{': 1, ')': -1, ']': -1, '}': -1}.get(c, 0)
        if c == ';' and depth == 0:
            return k + 1
    raise ValueError('statement without ;')


def strip_quad_dispatch(text: str) -> tuple[str, int]:
    """calculate_shared without Stage 4b #4's binary128 dispatch (C62d's R3a design): the line
    `constexpr bool quad=std::is_same<T,Q>::value;` removed and every `if constexpr(quad) A else B` replaced by B (a braced
    B by its contents). The result must be the a6ce987 function (with the A-L18 hunk): every T other than Q, i.e. the MP
    backends, instantiates exactly the original statements. Returns (text, number of dispatched statements)."""
    decl = 'constexpr bool quad=std::is_same<T,Q>::value;'
    if decl not in text:
        return text, 0
    assert text.count(decl) == 1
    text = text.replace(decl, '', 1)
    key, out, i, n = 'if constexpr(quad)', [], 0, 0
    while True:
        k = text.find(key, i)
        if k < 0:
            out.append(text[i:])
            break
        out.append(text[i:k])
        a_end = _statement_end(text, k + len(key))
        m = re.match(r'\s*else\s*', text[a_end:])
        assert m, 'if constexpr(quad) without else'
        b = a_end + m.end()
        b_end = _statement_end(text, b)
        body = text[b:b_end]
        out.append(body[1:-1] if body.startswith('{') else body)
        i, n = b_end, n + 1
    return ''.join(out), n


def test_grep_and_constants():
    files = sorted((ROOT / 'src').glob('*.?pp')) + [ROOT / 'tests/point_checks.cpp']
    bad = []
    for f in files:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split('//')[0]
            if re.search(r'std::array<[^<>]*,\s*(6|12|14|28)\s*>', code) or re.search(r'\b(?:ld|long double|int|unsigned|double|float|char|Q|MP|T|uint64_t|uint32_t|size_t|std::\w+)\s+[A-Za-z_]\w*\s*\[\s*(6|12|14|28)\s*\]', code):
                bad.append(f'{f.relative_to(ROOT)}:{n}: {line.strip()}')
    assert not bad, bad
    k = (ROOT / 'src/kernel.hpp').read_text()
    for line in ('constexpr int LMAX=8;', 'constexpr int ORDER_MIN=7, ORDER_MAX=8;', 'constexpr int EMAX=2*LMAX;',
                 'constexpr int KMAX=ORDER_MAX-2;', 'constexpr int NLOGS=KMAX+1;', 'constexpr int NVALUES=2*NLOGS;',
                 'constexpr int DIMMAX=4*LMAX-1;', 'constexpr int MAXMASKS=16384, MAXTERMS=10000;', 'constexpr int TAILK=16;',
                 'static_assert(EMAX<=31,', 'static_assert(DIMMAX>=2*EMAX-1,', 'static_assert(NLOGS==KMAX+1 && NVALUES==2*(KMAX+1)',
                 'static_assert(std::tuple_size<decltype(Scratch::x)>::value==EMAX && std::tuple_size<decltype(Scratch::order)>::value==EMAX'):
        assert line in k, line
    assert '#if defined(C8_TEST_UNGUARDED_INDEX) && !defined(_GLIBCXX_ASSERTIONS)' in k
    ok('A-KER-1_grep_and_C.1_constants', files=[str(f.relative_to(ROOT)) for f in files])


def test_unchanged():
    ref = (ROOT / 'reference/src/kernel.hpp').read_text()
    new = (ROOT / 'src/kernel.hpp').read_text()
    same = {}
    for head in ('inline void rates(', 'template<class T> std::pair<T,T> calculate_reference(', 'inline std::pair<ld,ld> calculate_products('):
        assert squash(function(ref, head)) == squash(function(new, head)), head
        same[head] = 'identical'
    p_ref, p_new = function(ref, 'inline void prepare('), function(new, 'inline void prepare(')
    p_new_ordinary = '\n'.join(x for x in p_new.splitlines() if x.strip() not in ('#ifndef C8_TEST_UNGUARDED_INDEX', '#endif'))
    assert squash(p_ref) == squash(p_new_ordinary), 'prepare() differs beyond the test-only #ifndef'
    assert p_new.count('#ifndef C8_TEST_UNGUARDED_INDEX') == 1
    same['prepare'] = 'identical apart from the #ifndef C8_TEST_UNGUARDED_INDEX pair'
    s_ref = function(ref, 'template<class T,bool NeedError=true>')
    s_new = function(new, 'template<class T,bool NeedError=true>')
    hunk = ('exponential(T(logx[j])-T(shift)/g.L)', 'exponential(T(T(logx[j])-T(shift)/g.L))')
    s_mp, nq = strip_quad_dispatch(s_new)
    assert s_ref.count(hunk[0]) == 1 and squash(s_ref.replace(*hunk)) == squash(s_mp), 'calculate_shared differs beyond the A-L18 hunk and the #4 dispatch'
    same['calculate_shared'] = (f'identical apart from the A-L18 hunk and the Stage-4b #4 dispatch ({nq} if constexpr(quad) statements whose '
                                'else branches are the original statements)' if nq else 'identical apart from the A-L18 hunk')
    sa_ref = function(ref, 'inline std::array<ld,6> sample(')
    sa_new = function(new, 'inline std::array<ld,NLOGS> sample(')
    strip = lambda t: '\n'.join(x for x in t.splitlines() if not x.strip().startswith('//'))  # noqa: E731
    assert squash(strip(sa_ref).replace('std::array<ld,6>', 'std::array<ld,NLOGS>')) == squash(strip(sa_new)), 'sample() differs'
    same['sample'] = 'identical apart from the NLOGS array type and the comment'
    e_new = squash(function(new, 'inline Eval evaluate('))
    for stmt in ('ldshift=0;booldirect=true;for(intj=0;j<g.E;++j)if(lx[j]<-600||lx[j]>0)direct=false;',
                 'if(!direct){shift=-std::numeric_limits<ld>::infinity();for(automask:g.masks){ldv=0;while(mask){intj=__builtin_ctz(mask);mask&=mask-1;v+=lx[j];}shift=std::max(shift,v);}}',
                 'boolmoderate=true;for(intj=0;j<g.E;++j)if(fabsl(lx[j]-shift/g.L)>500)moderate=false;',
                 'autov=moderate?calculate_products(g,lx,shift,s):calculate_reference<ld>(g,lx,shift);',
                 'if(!moderate){s.S=0;for(intj=0;j<g.E;++j)s.S+=expl(lx[j]);}',
                 'ldratio=absolute(v.first)/(v.second+1e-4900L);intlev=0;ldf=v.first;',
                 'autoq=calculate_shared<Q>(g,lx,shift);lev=1;f=ld(q.first);', 'if(absolute(q.first)<Q(1e-23L)*q.second){',
                 'autom=calculate_shared<MP,false>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;',
                 'autom=calculate_shared<MP,true>(g,lx,shift);f=m.first.convert_to<ld>();lev=2;',
                 'ldy=f*expl(factor-(SpatialD/2.L)*shift)*g.Z;if(!std::isfinite(y))throwstd::runtime_error("nonfiniteintegrand");return{y,lev};'):
        assert stmt in e_new, stmt
    assert 'if(ratio<1e-9L)' in e_new
    same['evaluate'] = 'every a6ce987 arithmetic statement present'
    w_new = squash((ROOT / 'src/c8d3_integrate.cpp').read_text())
    st_new = squash((ROOT / 'src/stream.hpp').read_text())
    w_ref = (ROOT / 'reference/src/c7d3_integrate.cpp').read_text()
    for stmt in ('ldz=v[j]/t.total;if(mode=="compensated"){ldy=z-comp[j],x=sum[j]+y;comp[j]=(x-sum[j])-y;sum[j]=x;}elsesum[j]+=z;',
                 'r.maxabs=std::max(r.maxabs,fabsl(norm*(3*g.wb-g.wa)*v[0]));',
                 'for(intj=0;j<=K;++j){r.value[j]=norm*g.wa*sum[j];r.value[K+1+j]=norm*g.wb*sum[j];}',
                 'returnld(t.end-t.begin)*loaded.at(t.graph).addends.size();};returncost(a)>cost(b);});'):
        assert stmt in w_new and stmt in squash(w_ref), stmt
    # S1-05: (id+1) -> (uint64_t(id)+1), the same uint64 for every int id below INT_MAX (a6ce987's int overflow at INT_MAX
    # removed); S1-04: one start-index guard line in Net's constructor, else Net is a6ce987's token for token.
    assert 'seed+0x9e3779b97f4a7c15ULL*(t.rep+1)+0xbf58476d1ce4e5b9ULL*(g.id+1)' in squash(w_ref)
    assert '0xbf58476d1ce4e5b9ULL*(id+1)' not in st_new
    assert 'returnseed+0x9e3779b97f4a7c15ULL*(rep+1)+0xbf58476d1ce4e5b9ULL*(uint64_t(id)+1);' in st_new
    guard = 'if(bits<64&&(begin>>bits)!=0)throwstd::runtime_error("Sobolperiodexceeded(startindex"+std::to_string(begin)+">=2^"+std::to_string(bits)+")");'
    assert st_new.count(guard) == 1, 'the S1-04 start-index guard'
    assert squash(re.search(r'struct Net \{.*?\n\};', w_ref, re.S).group(0)) in st_new.replace(guard, ''), 'Net differs'
    grid_ref = 'intix=layout==0?2*j+1:(layout==2?j+1:j);ldy=u[ix]*32;intbin=std::min(31,int(y));'
    assert grid_ref in squash(w_ref) and grid_ref in st_new and 'ldw=axis[bin+1]-axis[bin];u[ix]=axis[bin]+w*(y-bin);jac*=32*w;' in st_new
    ok('C.9_unchanged_default_path', functions=same)


FAKE_CXX = """#!PYTHON
# Fake compiler for the Makefile tests: -E prints FAKE_BOOST (default 107700); --version prints a version; otherwise it
# writes to -o a fake worker whose --describe reports mp_backend gmp350 if -DC7_USE_GMP was given (FAKE_MP overrides).
import os,sys
a=sys.argv[1:]
if '-E'in a:sys.stdin.read();print(os.environ.get('FAKE_BOOST','107700'));sys.exit(0)
if '--version'in a:print('g++ (fake) 13.3.0');sys.exit(0)
out=a[a.index('-o')+1];mp=os.environ.get('FAKE_MP')or('gmp350'if'-DC7_USE_GMP'in a else'decimal300')
os.makedirs(os.path.dirname(out)or'.',exist_ok=True)
open(out,'w').write('#!PYTHON\\nimport json\\nprint(json.dumps({"schema":"c8-d3-build-1","mp_backend":"%s"}))\\n'%mp);os.chmod(out,0o755)
"""


def test_makefile(td: Path):
    m = td / 'mk'
    (m / 'src').mkdir(parents=True)
    (m / 'reference/src').mkdir(parents=True)
    shutil.copy2(ROOT / 'Makefile', m / 'Makefile')
    shutil.copytree(ROOT / 'tools', m / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
    for f in (ROOT / 'src').iterdir():
        shutil.copy2(f, m / 'src' / f.name)
    for f in ('c7d3_integrate.cpp', 'kernel.hpp'):
        shutil.copy2(ROOT / 'reference/src' / f, m / 'reference/src' / f)
    cxx = td / 'fakecxx'
    cxx.write_text(FAKE_CXX.replace('PYTHON', sys.executable))
    cxx.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ('CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LDLIBS', 'OPTFLAGS', 'CXX', 'BOOST_ACCEPT', 'NUMERICS')}
    gmp = m / 'bin/c8d3_gmp'
    rec = m / 'bin/c8d3_gmp.buildinfo.json'

    def mk(*args, target='bin/c8d3_gmp', python=sys.executable, **extra):
        gmp.unlink(missing_ok=True)
        rec.unlink(missing_ok=True)
        return subprocess.run(['make', '-s', '-C', str(m), target, f'CXX={cxx}', f'PYTHON={python}', *args], capture_output=True, text=True, env={**env, **extra})
    cp = mk('CPPFLAGS=-I/opt/boost/include')
    assert cp.returncode == 0, cp.stderr[-800:]
    bi = json.loads(rec.read_text())
    assert bi['schema'] == 'c8-d3-buildinfo-1' and '-I/opt/boost/include' in bi['command'] and bi['boost_version'] == 107700 and bi['boost_accept'] is None
    assert bi['command'][-2:] == ['-o', 'bin/c8d3_gmp'] and bi['describe']['mp_backend'] == 'gmp350' and bi['backend'] == 'gmp' and 'libprobe' in bi, bi
    i = bi['command'].index('-std=c++17')
    assert bi['command'][i:i + 4] == ['-std=c++17', '-fopenmp', '-ffp-contract=off', '-fno-fast-math'] and bi['command'].index('-I/opt/boost/include') < i
    for bad in ('LDFLAGS=-ffp-contract=fast', 'LDLIBS=-ffast-math', 'OPTFLAGS=-Ofast', 'CXXFLAGS=-std=c++20', 'CPPFLAGS=-mfpmath=387'):
        cp = mk(bad)
        assert cp.returncode != 0 and 'override the strict numerical flags' in cp.stderr and not gmp.exists(), (bad, cp.stderr[-300:])
    cp = mk(FAKE_BOOST='106600')
    assert cp.returncode != 0 and 'refused (< 1.70' in cp.stderr and not gmp.exists(), cp.stderr[-300:]
    cp = mk(FAKE_BOOST='108600')
    assert cp.returncode != 0 and 'require 1.77' in cp.stderr and not gmp.exists(), cp.stderr[-300:]
    cp = mk('BOOST_ACCEPT=108600', FAKE_BOOST='108600')
    assert cp.returncode == 0 and json.loads(rec.read_text())['boost_accept'] == '108600' and json.loads(rec.read_text())['boost_version'] == 108600, cp.stderr[-300:]
    failing = td / 'py_fail_write'
    failing.write_text(f'#!/bin/sh\n[ "$3" = write ] && exit 3\nexec {sys.executable} "$@"\n')
    failing.chmod(0o755)
    cp = mk(python=str(failing))
    assert cp.returncode != 0 and not gmp.exists(), 'binary kept after a failed build-info step'
    cp = mk(FAKE_MP='decimal300')
    assert cp.returncode != 0 and 'backend gmp' in cp.stderr and not gmp.exists(), cp.stderr[-300:]
    cp = subprocess.run(['make', '-s', '-C', str(m), 'bin/c8d3_gmp', 'CXX=g++', 'NUMERICS=fastexp'], capture_output=True, text=True, env=env)
    assert cp.returncode != 0 and 'no opt-in numerics profile' in cp.stderr, cp.stderr[-300:]
    want = {'bin/c8d3_gmp': ['-DC7_USE_GMP', 'src/c8d3_integrate.cpp', '-lquadmath', '-lgmp'],
            'bin/c8d3_decimal': ['src/c8d3_integrate.cpp', '-lquadmath'],
            'bin/ref/c7d3_gmp': ['-DC7_USE_GMP', 'reference/src/c7d3_integrate.cpp', '-lquadmath', '-lgmp'],
            'bin/ref/c7d3_decimal': ['reference/src/c7d3_integrate.cpp', '-lquadmath'],
            'bin/c8d3_inspect': ['-DC7_USE_GMP', 'src/c8d3_inspect.cpp', '-lquadmath', '-lgmp']}
    for target, mid in want.items():
        cp = subprocess.run(['make', '-n', '-B', '-C', str(m), target, 'CXX=g++'], capture_output=True, text=True, env=env)
        lines = [ln.split() for ln in cp.stdout.splitlines() if ln.startswith('g++')]
        expect = ['g++', '-O3', '-std=c++17', '-fopenmp', '-ffp-contract=off', '-fno-fast-math', *mid, '-o', target]
        assert expect in lines, (target, cp.stdout[-800:])
    ok('C.8_makefile_flags_boost_buildinfo_backend_default_commands', default_commands=list(want))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    test_grep_and_constants()
    test_unchanged()
    with tempfile.TemporaryDirectory(prefix='c8d3_native_static_') as td:
        test_makefile(Path(td))
    res = {'status': 'passed', 'tests': RESULTS}
    if a.output:
        a.output.write_text(json.dumps(res, indent=2) + '\n')
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
