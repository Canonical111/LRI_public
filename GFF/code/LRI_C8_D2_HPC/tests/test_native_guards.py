#!/usr/bin/env python3
"""Stage-6 fix round 3, G1: the two native source changes (Z3, Z4) tested with the host C++ compiler, without building
a worker (macOS has no __float128 and no libquadmath; on Linux the same tests run with the real headers). Stage-6 fix
round 4, G1: the native harnesses' acceptance rules (W1, W2, W22) and their consumers, on stand-ins (pure Python).

  hooks    Z3 (S6A3-03): src/kernel.hpp refuses every C8_NX_* numerics hook defined from outside src/numerics/. The
           preprocessor (-E; stub system headers, so no Boost, GMP or libquadmath is needed) stops with kernel.hpp's
           #error for every listed name given with -D, and for one hook through each other vector (-include, -imacros,
           -Wp,-D and a response file @FILE), in the default, gmp and all-profile worker, the inspector and the
           precision tools (forced_tiers, point_checks, numerics_f1); without an injection every one preprocesses.
           The refusal list names every C8_NX_* identifier of the code of src/, tests/*.cpp and benchmarks/probes/
           (completeness, comments stripped). Before the fix (git a42cfb7, when the checkout has it) the same -D
           injection preprocessed silently: the defect.
  loader   Z4 (S6A3-04): kernel.hpp's load_graph, with rates(), prepare() and the constants and structs they use, cut
           from the file into a harness that prints every field of the loaded Graph (the parsed header, masks, terms,
           the scaled rates, dp, choice_total, Z, and prepare()'s products, mon_ids, segments, addends, numerators and
           term slots, long doubles in %La). Valid G-files (the L=2 graph, and the heaviest and lightest kernel of
           every (sector, L) whose pack is present) load; every case of validate.graph_truncations (a body that ends
           early or holds an unreadable token in each section) of three of them is refused with "truncated graph:
           <path>". Before the fix (git a42cfb7): the old loader prints byte for byte the same on every valid file,
           and, built with -ftrivial-auto-var-init=pattern where the compiler has it (so its unassigned n is a fixed
           negative pattern instead of stack garbage), refuses a mask list that ends early with "bad denominator size"
           instead: the defect.
  syntax   every translation unit that includes src/kernel.hpp passes the compiler's -fsyntax-only (templates
           instantiated): the decimal, gmp, all-profile (dd+mp256+exp1), tier-timer, ratio-histogram, no-tail and
           order-trace workers, the inspector and the precision tools forced_tiers, point_checks, numerics_f1 (exact
           and profile), quad_ranges and the interleave probe. On Linux: the Makefile's flags (CXX, CPPFLAGS,
           OPTFLAGS, CXXFLAGS and the required flags; GMP_PREFIX's -I when set). On macOS: Apple clang for the
           x86_64 target (80-bit long double) with __float128 spelled long double and stub <quadmath.h> and <omp.h>,
           Boost and gmp.h from Homebrew; skipped, saying so, when they are not installed. A syntax check, not a
           build: the integrator builds and replays on symmetry.
  quad_coverage   W1 (S6A4-01): tests/quad_differential.py on a stand-in differential tool and sanitizer compiler (and
           the ranges of a stored symmetry record): the default run says "passed" (exit 0, coverage complete);
           --pairs 4 --ubsan-pairs 4 --no-ranges says "development run (...)" (exit 3) naming MIN_PAIRS, the ranges and
           the sanitizer; --min-pairs is gone (the finding's --pairs 4 --min-pairs 4 run is refused); --check accepts
           the stored records and refuses the development record, also with its status edited to "passed";
           coverage() names a short stream, a moved kernel window, a missing range block, an undetected injection and
           a sanitizer run without every edge pair.
  thread_coverage W22 (host residual): tests/thread_identity.py with stand-in blocks: the default run says "passed"
           (exit 0); --backends gmp, --threads 1 8, --lane-threads 4 and a restricted --executable say "development
           run (...)" (exit 3); a full --executable run is F5 evidence only (its own status, --check --gate F5);
           --check refuses the others, also with the status edited; coverage() accepts the stored post-X3 records, the
           pre-X3 ones only without the team conditions, and refuses the stored restricted run
           (s6fix1 thread_identity_omp_env.json: gmp only, status "passed") and a block with another team.
  bk8_compare     W2 (S6A4-02): validate.compare on stand-in decimal/gmp rows: identical rows pass; on an mp>0 row a
           tampered max_abs, tail_top entry, tail_sum, tail width or tail_argmax (no near tie) is refused, a change
           within 1e-30 normalized is accepted, a moved argmax at a near tie is accepted and counted; on an mp=0 row
           any tail change is refused; an argmax outside the row, an uncovered or missing row field, a tail-carrying
           G-REF reference and another header seed are refused; compare_exact and compare_jet refuse uncovered fields.
           G-BK8 end to end (bk8 with stand-in outputs) records the row rule and passes coverage(record, 'G-BK8'); a
           tampered max_abs in one gmp output fails it. A-RPL-6's chunk_merge refuses chunks that do not tile the
           task, quad or mp that do not add up, another max_abs and a tail merge that differs.
  summaries       the consumers: benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py judges
           quad_differential, thread_identity and the validate records (J-VAL-2, G-BK8, G-L8SELF, A-IN-6b) by status
           AND recomputed coverage: its stored records pass; edited ones (pairs 4 with status "passed", the stored
           gmp-only thread run, a G-BK8 record without a block, a validate_full without the replay) are FAILED;
           validate.py --check --gate accepts a symmetry J-VAL-1 record and refuses one whose diagnostic part was
           skipped (status "passed"), a J-VAL-1 record as J-VAL-2, and a pre-W2 G-BK8 record.
The before-fix parts read OLD (a42cfb7) from git; in an export without .git, C8_GUARDS_OLD_TREE=<export of a42cfb7>
(with its .commit file beside it) supplies them, else they are skipped (before_fix: null).
Usage: python3 -B tests/test_native_guards.py [--output FILE] [--only hooks,loader,syntax,quad_coverage,thread_coverage,bk8_compare,summaries]"""
from __future__ import annotations
import argparse,json,os,platform,re,shlex,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)
def skipped(name,why,**info):RESULTS.append({'test':name,'status':'skipped','reason':why,**info});print('SKIP',name,why,flush=True)
OLD='a42cfb7'   # the fix base of Stage-6 fix round 3
MAC=sys.platform=='darwin'
X86=platform.machine().lower()in('x86_64','amd64')
ERROR='a C8_NX_* numerics hook is defined from outside src/numerics/'

def cxx()->list[str]:return shlex.split(os.environ.get('CXX')or('c++'if MAC else'g++'))

def strip_comments(text:str)->str:
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    return re.sub(r'//[^\n]*','',text)

def old_export()->Path|None:
    """Integration of fix round 3: C8_GUARDS_OLD_TREE names a git-archive export of OLD (a package directory with
    <dir>.commit beside it, as the cluster exports pkg/<sha12> are made), for a checkout without .git (an export on the
    cluster): the before-fix parts then read OLD's sources from it. A directory whose .commit is not OLD is refused."""
    d=os.environ.get('C8_GUARDS_OLD_TREE')
    if not d:return None
    d=Path(d);c=Path(str(d)+'.commit')
    if not (d.is_dir()and c.is_file()and c.read_text().strip().startswith(OLD)):
        raise SystemExit(f'C8_GUARDS_OLD_TREE={d}: not an export of {OLD} (no {c.name} beside it naming {OLD})')
    return d

def old_file(rel:str)->str|None:
    """rel at git OLD (or in the C8_GUARDS_OLD_TREE export of OLD), or None when neither is available (an export)."""
    ex=old_export()
    if ex is not None:return (ex/rel).read_text()if (ex/rel).is_file()else None
    try:cp=subprocess.run(['git','-C',str(ROOT),'show',f'{OLD}:{rel}'],capture_output=True,text=True,timeout=60)
    except OSError:return None
    return cp.stdout if cp.returncode==0 else None

def old_tree(dest:Path)->bool:
    """src/ and the tools' sources at git OLD into dest (package layout); False when the checkout does not have them."""
    ex=old_export()
    if ex is not None:
        rels=[f.relative_to(ex).as_posix()for f in sorted((ex/'src').rglob('*'))if f.is_file()]+[f.relative_to(ex).as_posix()for f in sorted((ex/'tests').glob('*.cpp'))]
    else:
        try:cp=subprocess.run(['git','-C',str(ROOT),'ls-tree','-r','--name-only',OLD,'src','tests'],capture_output=True,text=True,timeout=60)
        except OSError:return False
        if cp.returncode:return False
        rels=cp.stdout.split()
    for rel in rels:
        if not (rel.startswith('src/')or rel.endswith('.cpp')):continue
        text=old_file(rel)
        if text is None:return False
        (dest/rel).parent.mkdir(parents=True,exist_ok=True);(dest/rel).write_text(text)
    return (dest/'src/kernel.hpp').exists()

# ---------------------------------------------------------------- stub system headers
STUB_QUADMATH='''#pragma once
#include <cstddef>
__float128 expq(__float128);__float128 fabsq(__float128);__float128 log10q(__float128);
__float128 strtoflt128(const char*,char**);int quadmath_snprintf(char*,std::size_t,const char*,...);
#define FLT128_DIG 33
'''
STUB_OMP='''#pragma once
inline double omp_get_wtime(){return 0;}inline int omp_get_thread_num(){return 0;}inline int omp_get_max_threads(){return 1;}
inline void omp_set_num_threads(int){}
'''
def stubs(d:Path,boost_gmp:bool)->Path:
    """d with stub <quadmath.h> and <omp.h>; with boost_gmp also empty Boost and GMP headers (enough for -E)."""
    d.mkdir(parents=True,exist_ok=True);(d/'quadmath.h').write_text(STUB_QUADMATH);(d/'omp.h').write_text(STUB_OMP)
    if boost_gmp:
        for h in ('boost/multiprecision/cpp_dec_float.hpp','boost/multiprecision/gmp.hpp','boost/version.hpp','gmp.h'):
            (d/h).parent.mkdir(parents=True,exist_ok=True);(d/h).write_text('#pragma once\n')
    return d

NX=['-DC8_USE_GMP','-DC8_NUMERICS','-DC8_NUMERICS_DD','-DC8_NUMERICS_MP256','-DC8_NUMERICS_EXP1']+(['-mavx2','-mfma']if X86 else[])
def units()->list[tuple[str,str,list[str]]]:
    """(label, source, defines) of every translation unit that includes src/kernel.hpp."""
    return [('decimal worker','src/c8d2_integrate.cpp',[]),('gmp worker','src/c8d2_integrate.cpp',['-DC8_USE_GMP']),
            ('dd+mp256+exp1 worker','src/c8d2_integrate.cpp',NX),('tier-timer worker','src/c8d2_integrate.cpp',['-DC8_USE_GMP','-DC8_TIER_TIMERS']),
            ('ratio-histogram worker','src/c8d2_integrate.cpp',['-DC8_USE_GMP','-DC8_RATIO_HISTOGRAM']),('no-tail worker','src/c8d2_integrate.cpp',['-DC8_NO_TAIL_FIELDS']),
            ('order-trace worker','src/c8d2_integrate.cpp',['-DC8_ORDER_TRACE']),('inspector','src/c8d2_inspect.cpp',[]),
            ('forced_tiers tool','tests/forced_tiers.cpp',['-DC8_USE_GMP']),('point_checks tool (decimal)','tests/point_checks.cpp',[]),
            ('point_checks tool (gmp)','tests/point_checks.cpp',['-DC8_USE_GMP']),('numerics_f1 tool (exact)','tests/numerics_f1.cpp',['-DC8_USE_GMP']),
            ('numerics_f1 tool (dd+mp256+exp1)','tests/numerics_f1.cpp',NX),('quad_ranges tool','tests/quad_ranges.cpp',['-DC8_USE_GMP']),
            ('interleave probe','benchmarks/probes/interleave_probe.cpp',['-DC8_USE_GMP'])]

# ---------------------------------------------------------------- hooks (Z3)
def refusal_list(kernel:str)->list[str]:
    """The C8_NX_* names of kernel.hpp's refusal (the #if defined(...) block right before the #error)."""
    k=kernel.index(f'#error "{ERROR}');block=kernel[kernel.rindex('#if defined(C8_NX_',0,k):k]
    return re.findall(r'defined\((C8_NX_\w+)\)',block)

def test_hooks():
    kernel=(ROOT/'src/kernel.hpp').read_text();listed=refusal_list(kernel)
    # completeness: every C8_NX_* identifier in the code of src/, tests/*.cpp and benchmarks/probes/ is refused
    files=[*sorted((ROOT/'src').rglob('*.hpp')),*sorted((ROOT/'src').glob('*.cpp')),*sorted((ROOT/'tests').glob('*.cpp')),*sorted((ROOT/'benchmarks/probes').glob('*.cpp'))]
    used=sorted({m for f in files for m in re.findall(r'\bC8_NX_\w+',strip_comments(f.read_text()))})
    missing=sorted(set(used)-set(listed));assert not missing,f'C8_NX_* names consulted by the sources but not refused by kernel.hpp: {missing}'
    assert len(listed)==len(set(listed))>=16,listed
    # the refusal comes before the stage-1 include of the profiles and before any use of a hook
    assert kernel.index(f'#error "{ERROR}')<kernel.index('#define C8_NX_STAGE 1')<kernel.index('#ifndef C8_NX_SHARED_BEGIN')
    with tempfile.TemporaryDirectory(prefix='c8d2_guards_')as td:
        td=Path(td);st=stubs(td/'stub',True)
        def pre(src,defs,extra=(),root=ROOT)->subprocess.CompletedProcess:
            return subprocess.run([*cxx(),'-std=c++17','-E','-I',str(st),*defs,*extra,str(root/src),'-o',os.devnull],capture_output=True,text=True,timeout=300)
        cases=0
        for label,src,defs in units():
            cp=pre(src,defs);assert cp.returncode==0,(label,'does not preprocess without an injection',cp.stderr[-800:])
            if ERROR in cp.stderr:raise AssertionError(f'{label}: refused without an injection')
        # every listed name with -D, in the default worker (a hook is consulted before any build distinction)
        for name in listed:
            cp=pre('src/c8d2_integrate.cpp',[],[f'-D{name}=1']);cases+=1
            assert cp.returncode and ERROR in cp.stderr,(name,cp.returncode,cp.stderr[-500:])
        # the finding's own injection and the other vectors, in every translation unit
        hdr=td/'inject.h';hdr.write_text('#define C8_NX_XS_Q(e) (e)\n');rsp=td/'inject.rsp';rsp.write_text('-DC8_NX_DESCRIBE(os)=\n')
        vectors={'-D (S6A3-03)':['-DC8_NX_SHARED_BEGIN(T)=s.products[0]=2;'],'-include':['-include',str(hdr)],'-imacros':['-imacros',str(hdr)],
                 '-Wp,-D':['-Wp,-DC8_NX_XS_MP(e)=e'],'@FILE':[f'@{rsp}']}
        seen={}
        for label,src,defs in units():
            for v,words in vectors.items():
                cp=pre(src,defs,words);cases+=1
                assert cp.returncode and ERROR in cp.stderr,(label,v,cp.returncode,cp.stderr[-500:])
                seen.setdefault(v,0);seen[v]+=1
        # the defect: at the fix base the finding's injection preprocessed silently
        before=None
        old=td/'old'
        if old_tree(old):
            cp=pre('src/c8d2_integrate.cpp',[],vectors['-D (S6A3-03)'],root=old)
            before={'commit':OLD,'returncode':cp.returncode,'refused':ERROR in cp.stderr}
            assert cp.returncode==0 and not before['refused'],f'{OLD} already refused the injection: {cp.stderr[-400:]}'
    ok('Z3_hooks_refused_every_name_every_vector_every_unit',names=listed,used=used,cases=cases,vectors=seen,before_fix=before)

# ---------------------------------------------------------------- loader (Z4)
HARNESS_HEAD='''#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <functional>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using ld=long double;
'''
HARNESS_MAIN=r'''
static void lds(const char*k,const std::vector<ld>&v){std::printf(" %s",k);for(ld x:v)std::printf(" %La",x);}
int main(int argc,char**argv){
    for(int a=1;a<argc;++a){
        try{Graph g=load_graph(argv[a],0.8L);
            std::printf("OK %s id=%d E=%d L=%d wa=%La wb=%La Z=%La masks",argv[a],g.id,g.E,g.L,g.wa,g.wb,g.Z);for(unsigned m:g.masks)std::printf(" %u",m);
            for(const auto&t:g.terms){std::printf(" term d=%d n=%d ids",t.denominator,t.numerator);for(int i:t.ids)std::printf(" %d",i);std::printf(" co");for(int c:t.co)std::printf(" %d",c);}
            lds("alpha",g.alpha);lds("dp",g.dp);lds("choice_total",g.choice_total);
            std::printf(" products");for(auto p:g.products)std::printf(" %d,%d",p.first,p.second);
            std::printf(" mon_ids");for(int i:g.mon_ids)std::printf(" %d",i);
            std::printf(" segments");for(auto s:g.segments)std::printf(" %d,%d,%d",s.parent,s.begin,s.end);
            std::printf(" addends");for(int i:g.addends)std::printf(" %d",i);
            std::printf(" numerators");for(const auto&n:g.numerators){std::printf(" [");for(auto p:n)std::printf(" %d,%d",p.first,p.second);std::printf(" ]");}
            std::printf("\n");}
        catch(const std::exception&e){std::printf("ERR %s\n",e.what());}
    }
    return 0;
}
'''
def loader_source(kernel:str)->str:
    """The harness: kernel's constants and structs (from 'constexpr int LMAX=' up to 'struct Scratch {') and its
    rates(), prepare() and load_graph() (from 'inline void rates(' to the closing brace of load_graph), verbatim."""
    lines=kernel.splitlines()
    at=lambda pred,start=0:next(i for i in range(start,len(lines))if pred(lines[i]))
    a=at(lambda l:l.startswith('constexpr int LMAX='));b=at(lambda l:l.startswith('struct Scratch {'),a)
    c=at(lambda l:l.startswith('inline void rates('));d=at(lambda l:l=='}',at(lambda l:l.startswith('inline Graph load_graph('),c))
    return HARNESS_HEAD+'\n'.join(lines[a:b]+lines[c:d+1])+'\n'+HARNESS_MAIN

def compile_harness(kernel:str,exe:Path,extra=())->subprocess.CompletedProcess:
    src=exe.with_suffix('.cpp');src.write_text(loader_source(kernel))
    return subprocess.run([*cxx(),'-std=c++17','-O1',*extra,str(src),'-o',str(exe)],capture_output=True,text=True,timeout=600)

def load_all(exe:Path,files)->list[str]:
    cp=subprocess.run([str(exe),*map(str,files)],capture_output=True,text=True,timeout=600)
    assert cp.returncode==0,cp.stderr[-800:]
    out=cp.stdout.splitlines();assert len(out)==len(files),(len(out),len(files));return out

def test_loader():
    import validate as V
    with tempfile.TemporaryDirectory(prefix='c8d2_loader_')as td:
        td=Path(td);new=td/'loader_new';cp=compile_harness((ROOT/'src/kernel.hpp').read_text(),new);assert cp.returncode==0,cp.stderr[-2000:]
        valid=[V.stage(td/'g','free',2,[0])/'L2/G0.txt'];groups=[]
        for sector in ('free','power'):
            for L in range(3,9):
                if not (ROOT/f'inputs/packs/{sector}_L{L}.pack').exists():continue
                ids=sorted({V.by_cost(sector,L)[0],V.by_cost(sector,L)[-1]});root=V.stage(td/sector,sector,L,ids)
                valid+=[root/f'L{L}/G{g}.txt'for g in ids];groups.append(f'{sector}_L{L}')
        got=load_all(new,valid)
        bad=[(f,l)for f,l in zip(valid,got)if not l.startswith(f'OK {f} ')]
        assert not bad,f'valid G-files refused: {[(str(f),l[:200])for f,l in bad]}'
        # every truncation of three G-files (L=2 with two terms, the heaviest free L3, the lightest free L7)
        sources=[valid[0],V.stage(td/'free','free',3,[])/f'L3/G{V.by_cost("free",3)[0]}.txt',V.stage(td/'free','free',7,[])/f'L7/G{V.by_cost("free",7)[-1]}.txt']
        trunc=[]
        for s in sources:
            for case,text in V.graph_truncations(s.read_text()).items():
                f=td/'trunc'/s.parent.name/f'{s.stem}_{case}.txt';f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text);trunc.append((case,f))
        res=load_all(new,[f for _,f in trunc])
        wrong=[(c,str(f),r)for (c,f),r in zip(trunc,res)if r!=f'ERR truncated graph: {f}']
        assert not wrong,f'truncations not refused as "truncated graph": {wrong[:6]}'
        # before the fix (OLD): byte-identical on every valid file; with a fixed pattern for its unassigned n, a mask
        # list that ends early is refused for the wrong reason
        before=None;okd=old_file('src/kernel.hpp')
        if okd is not None:
            old=td/'loader_old';cp=compile_harness(okd,old);assert cp.returncode==0,cp.stderr[-2000:]
            same=load_all(old,valid)==got;assert same,f'the old loader ({OLD}) prints another Graph for a valid file'
            before={'commit':OLD,'source':str(old_export()or'git'),'valid_files_byte_identical':same,'pattern_init':None}
            pat=td/'loader_old_pattern';cp=compile_harness(okd,pat,['-ftrivial-auto-var-init=pattern'])
            if cp.returncode==0:
                mask=[(c,f)for c,f in trunc if c in('mask_list','unreadable_mask')]
                r=load_all(pat,[f for _,f in mask]);before['pattern_init']={c:x.split(' ',1)[1]for (c,_),x in zip(mask,r)}
                assert all(x=='ERR bad denominator size'for x in r),f'the old loader with a pattern-initialized n: {r}'
            else:before['pattern_init']=f'not supported by {" ".join(cxx())}: {cp.stderr.strip().splitlines()[-1][:160] if cp.stderr.strip() else "?"}'
        ok('Z4_loader_valid_files_load_every_truncation_refused',valid_files=len(valid),groups=groups,truncations=len(trunc),
           cases=sorted({c for c,_ in trunc}),before_fix=before)

# ---------------------------------------------------------------- syntax
def brew_include()->Path|None:
    for d in [*(os.environ.get('CPATH','').split(':')),'/opt/homebrew/include','/usr/local/include']:
        if d and (Path(d)/'boost/version.hpp').exists()and (Path(d)/'gmp.h').exists():return Path(d)
    return None

def test_syntax():
    from common import REQUIRED_CXXFLAGS,gmp_prefix_words
    with tempfile.TemporaryDirectory(prefix='c8d2_syntax_')as td:
        td=Path(td)
        if MAC:
            inc=brew_include()
            if inc is None:return skipped('syntax','macOS without Homebrew Boost and gmp.h (brew install boost gmp)')
            base=['clang++','-target','x86_64-apple-macos13','-std=c++17','-fsyntax-only','-ffp-contract=off','-fno-fast-math','-Wno-keyword-macro',
                  '-Wno-unknown-attributes','-D__float128=long double','-D_OPENMP=201511','-I',str(stubs(td/'stub',False)),'-isystem',str(inc)]
            mode='macOS: x86_64 target, __float128 as long double, stub quadmath.h/omp.h'
        else:
            e=os.environ;sp=lambda k,d='':shlex.split(e.get(k,d));inc,_=gmp_prefix_words((e.get('GMP_PREFIX')or'').strip()or None)
            base=[*cxx(),*inc,*sp('CPPFLAGS'),*sp('OPTFLAGS','-O3'),*sp('CXXFLAGS'),*REQUIRED_CXXFLAGS,'-fsyntax-only']
            mode='Linux: the Makefile flags'
        done=[]
        for label,src,defs in units():  # the dd profile needs the fma on an x86_64 target (NX_FLAGS_dd)
            defs=[d for d in defs if d not in('-mavx2','-mfma')]+(['-mavx2','-mfma']if '-DC8_NUMERICS'in defs and (MAC or X86)else[])
            cp=subprocess.run([*base,*defs,str(ROOT/src)],capture_output=True,text=True,timeout=900)
            assert cp.returncode==0 and 'error:'not in cp.stderr,(label,cp.stderr[-3000:])
            done.append(label)
    ok('syntax_every_kernel_unit',mode=mode,units=done)

# ---------------------------------------------------------------- Stage-6 fix round 4 (W1, W22, W2): acceptance rules
import contextlib,glob,importlib
from unittest import mock
PY=sys.executable
STORED_QD=ROOT/'benchmarks/symmetry_2026-10-c8/stage5/s5val3.570029.0/quad_differential.json'
def _fresh(name):
    sys.modules.pop(name,None);return importlib.import_module(name)
def _refused(fn,needle,what):
    try:fn();raise AssertionError(f'accepted {what}')
    except (AssertionError,ValueError,SystemExit)as e:
        if str(e).startswith('accepted '):raise
        assert needle in str(e),(what,str(e)[-600:]);return str(e)

FAKE_DIFF=r"""import json,sys
a=sys.argv[1:];g=lambda k,d=None:a[a.index(k)+1]if k in a else d
n=int(g('--pairs','0'));k=int(g('--inject','0'));w=lambda s:[int(x)for x in s.split(':')]if s else[1,32766]
S={'add':('kernel','full','cancel','bits'),'sub':('kernel','full','cancel','bits'),'mul':('kernel','full','ties','bits')}
C={'add':('specials','align','cancel','carry','boundary','zeros'),'sub':('specials','align','cancel','carry','boundary','zeros'),'mul':('specials','mul_ties','mul_boundary','mul_carry')}
bad=lambda p:p//k if k else 0
rnd={op:{'streams':{s:{'pairs':n//4,'fast':n//4,'mismatches':bad(n//4)}for s in S[op]},'pairs':4*(n//4),'fast':4*(n//4),'mismatches':4*bad(n//4)}for op in S}
edges={op:{'categories':{c:{'pairs':0 if '--no-edges'in a else 10,'fast':0,'mismatches':0}for c in C[op]},'pairs':0 if '--no-edges'in a else 10*len(C[op]),'fast':0,'mismatches':0}for op in S}
print(json.dumps({'schema':'c8-d2-quad-differential-1','compiler':'fake','seed':int(g('--seed','0')),'threads':int(g('--threads','1')),'pairs_requested_per_op':n,
                  'inject':k,'kernel_add_window':w(g('--kernel-add')),'kernel_mul_window':w(g('--kernel-mul')),'random':rnd,'edges':edges,'first_mismatches':[],
                  'random_seconds':0,'edge_seconds':0,**({'bench':{'identical':True}}if '--bench'in a else{})}))
"""
FAKE_SANCXX=r"""import os,shutil,sys
a=sys.argv[1:];shutil.copyfile(os.environ['FAKE_DIFF_TOOL'],a[a.index('-o')+1]);os.chmod(a[a.index('-o')+1],0o755)
"""

def test_quad_coverage():
    QD=_fresh('quad_differential');stored=json.loads(STORED_QD.read_text())
    with tempfile.TemporaryDirectory(prefix='c8d2_qd_')as td:
        td=Path(td);diff=td/'diff';diff.write_text(f'#!{PY}\n'+FAKE_DIFF);diff.chmod(0o755);cxx=td/'sancxx';cxx.write_text(f'#!{PY}\n'+FAKE_SANCXX);cxx.chmod(0o755)
        def go(*args):
            out=td/f'qd{len(list(td.glob("qd*.json")))}.json'
            with mock.patch.object(QD,'DIFF',diff),mock.patch.object(QD,'RANGES',diff),mock.patch.object(QD,'ranges',lambda a,scratch:stored['ranges']['blocks']),\
                 mock.patch.object(QD,'exe_record',lambda p:{'path':str(p),'sha256':'0'*64,'build':None}),\
                 mock.patch.dict(os.environ,{'CXX':str(cxx),'FAKE_DIFF_TOOL':str(diff)}),mock.patch.object(sys,'argv',['quad_differential.py','--output',str(out),'--scratch',str(td),*args]),\
                 contextlib.redirect_stdout(open(os.devnull,'w')):
                code=QD.main()
            return code,out,json.loads(out.read_text())
        code,full,r=go()
        assert code==0 and r['status']=='passed'and r['coverage']=={'complete':True,'why':[]}and r['min_pairs']==10**9,(code,r['status'],r['coverage'])
        code,dev,r=go('--pairs','4','--ubsan-pairs','4','--no-ranges')
        assert code==3 and r['status'].startswith('development run (')and all(r['gates'].values())and 'random_pairs_per_op_at_least_min'not in r['gates'],(code,r['status'])
        why=' '.join(r['coverage']['why']);assert 'below MIN_PAIRS'in why and 'six default blocks'in why and 'sanitizer run on 4 random pairs'in why,why
        _refused(lambda:go('--pairs','4','--min-pairs','4','--ubsan-pairs','4'),'2','the finding\'s --min-pairs 4 run')  # argparse: unrecognized arguments (exit 2)
        forged=td/'forged.json';forged.write_text(json.dumps(dict(r,status='passed')))
        chk=lambda f:subprocess.run([PY,'-B',str(ROOT/'tests/quad_differential.py'),'--check',str(f)],capture_output=True,text=True,timeout=120).returncode
        stored_files=sorted(glob.glob(str(ROOT/'benchmarks/**/quad_differential.json'),recursive=True));assert len(stored_files)>=5,stored_files
        assert [chk(f)for f in stored_files]==[0]*len(stored_files)and (chk(full),chk(dev),chk(forged))==(0,1,1)
    def why(fn):
        x=json.loads(json.dumps(stored));fn(x);c=QD.coverage(x);assert not c['complete'];return ' '.join(c['why'])
    assert 'streams do not sum'in why(lambda x:x['differential']['result']['random']['add']['streams']['kernel'].update(pairs=1))
    assert 'kernel window'in why(lambda x:x['differential']['result'].update(kernel_add_window=[1,32766]))
    assert 'six default blocks'in why(lambda x:x['ranges']['blocks'].pop('heavy_free_L8'))
    assert 'not detected'in why(lambda x:x['inject']['mismatches'].update(mul=0))
    assert 'not every edge pair'in why(lambda x:x['sanitizer']['edges']['sub'].update(pairs=5))
    assert 'below MIN_PAIRS'in why(lambda x:[v.update(pairs=10**6)for v in x['differential']['result']['random'].values()])
    ok('W1_quad_differential_passed_only_with_full_coverage_check_cli',stored=len(stored_files),dev_status=r['status'][:120])

def _ti_block(td,backend,sector,threads,lanes,lane_threads,executable=None):
    x=Path(executable)if executable else ROOT/f'bin/c8d2_{backend}'
    runs={f'threads_{t}':{'integration_seconds':1.0,'sha256':'0'*64,'team_observed':t}for t in threads}
    runs[f'lanes_{lanes}x{lane_threads}']={'cpu_sets':[f'{i}-{i}'for i in range(lanes)],'teams_observed':[lane_threads]*lanes}
    return {'backend':backend,'executable':str(x),'executable_sha256':'0'*64,'sector':sector,'graphs':list(range(32)),'tasks':64,'points_per_task':256,
            'identical':True,'team_sizes_verified':True,'runs':runs,'quad':10,'mp':1}

def test_thread_coverage():
    TI=_fresh('thread_identity')
    with tempfile.TemporaryDirectory(prefix='c8d2_ti_')as td:
        td=Path(td);n=[0]
        def go(*args):
            n[0]+=1;out=td/f'ti{n[0]}.json'
            with mock.patch.object(TI,'block',_ti_block),mock.patch.object(TI,'require',lambda *x,**k:None),contextlib.redirect_stdout(open(os.devnull,'w')):
                code=TI.main(['--output',str(out),*args])
            return code,out,json.loads(out.read_text())
        code,full,r=go();assert code==0 and r['status']=='passed'and r['coverage']['complete'],(code,r['status'])
        devs={}
        for args,needle in ((('--backends','gmp'),'not one per (backend, sector)'),(('--threads','1','8'),'threads [1, 8]'),(('--lane-threads','4'),'lanes \'8x4\''),
                            (('--executable',str(td/'c8d2_gmp_dd'),'--threads','1','8'),'threads [1, 8]'),(('--executable',str(ROOT/'bin/c8d2_gmp')),'not one opt-in profile')):
            code,f,x=go(*args);assert code==3 and x['status'].startswith('development run (')and needle in x['status'],(args,code,x['status'][:300]);devs[' '.join(args)]=f
        # F5 (--executable, the opt-in profile's thread identity): complete, but never plain "passed" (not A-RPL-6 evidence)
        code,f5,x=go('--executable',str(td/'c8d2_gmp_dd'));assert code==0 and x['status']==TI.F5_STATUS and x['coverage']['gate']=='F5',(code,x['status'])
        forged=td/'forged.json';forged.write_text(json.dumps(dict(json.loads(devs['--backends gmp'].read_text()),status='passed')))
        f5p=td/'f5_as_passed.json';f5p.write_text(json.dumps(dict(x,status='passed')))
        chk=lambda f,*g:subprocess.run([PY,'-B',str(ROOT/'tests/thread_identity.py'),'--check',str(f),*g],capture_output=True,text=True,timeout=120).returncode
        assert chk(full)==0 and all(chk(f)==1 for f in [*devs.values(),forged,f5,f5p])and chk(f5,'--gate','F5')==0 and chk(full,'--gate','F5')==1
    stored={f:json.loads(Path(f).read_text())for f in sorted(glob.glob(str(ROOT/'benchmarks/**/thread_identity*.json'),recursive=True))}
    post=[f for f,x in stored.items()if x.get('team_sizes_verified')is True and 'omp_env'not in f];pre=[f for f,x in stored.items()if x.get('team_sizes_verified')is None]
    assert len(post)>=2 and len(pre)>=5
    assert all(TI.coverage(stored[f])['complete']for f in post)and all(not TI.coverage(stored[f])['complete']and TI.coverage(stored[f],teams=False)['complete']for f in pre)
    omp=[f for f in stored if f.endswith('thread_identity_omp_env.json')];assert len(omp)==1 and stored[omp[0]]['status']=='passed'
    c=TI.coverage(stored[omp[0]]);assert not c['complete']and 'not one per (backend, sector)'in c['why'][0],c   # the residual: a gmp-only run said "passed"
    x=json.loads(json.dumps(stored[post[0]]));x['blocks'][1]['runs']['threads_16']['team_observed']=1
    assert 'observed teams other than requested'in ' '.join(TI.coverage(x)['why'])
    ok('W22_thread_identity_passed_only_with_full_coverage_check_cli',stored_post_x3=len(post),stored_pre_x3=len(pre))

def _rows(L:int,uids,mp_every=3,order=8)->list:
    from decimal import Decimal as Dd
    out=[]
    for uid,rep,g,b,e,tot in uids:
        n=min(16,e-b);top=[str(Dd(100+uid)/Dd(10+j))for j in range(n)]
        out.append({'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':tot,'quad':3,'mp':1 if uid%mp_every==0 else 0,'seconds':0.1,
                    'max_abs':str(Dd(7)+Dd(uid)/1000),'values':[str(Dd(uid+1)/Dd(j+3))for j in range(2*(order-L+1))],
                    'tail_top':top,'tail_sum':str(sum(Dd(t)for t in top)*3),'tail_argmax':b+uid%(e-b)})
    return out
def _out(L,rows,backend):
    return {'schema':'c8-d2-hpc-native-1','order':8,'L':L,'seed':7738251,'layout':0,'bits':60,'rate':'0.8','sum_mode':'compensated','long_double_bits':64,
            'mp_backend':'gmp350'if backend=='gmp'else'decimal300','mp_digits10':350 if backend=='gmp'else 300,'rows':rows}

def test_bk8_compare():
    V=_fresh('validate')
    rows=_rows(8,V.task_rows([11,12,13],2,256));dec=_out(8,rows,'decimal')
    mp=next(r['uid']for r in rows if r['mp']>0);zero=next(r['uid']for r in rows if r['mp']==0)
    def gmp(fn=None,uid=None):
        g=json.loads(json.dumps(_out(8,rows,'gmp')))
        if fn:fn(next(r for r in g['rows']if r['uid']==uid))
        return g
    base=V.compare(dec,gmp(),'gmp',tails=True)
    assert base['mp_rows']==sum(r['mp']>0 for r in rows)and base['tail_rows_exact']==len(rows)-base['mp_rows']and base['tail_argmax_ties']==0,base
    bump=lambda v,e='1e-20':str(D(v)*(1+D(e)))
    from decimal import Decimal as D
    refusals={
        'max_abs (mp>0, W2)':(lambda r:r.update(max_abs=bump(r['max_abs'])),mp,'max_abs differs'),
        'tail_top[3] (mp>0)':(lambda r:r['tail_top'].__setitem__(3,bump(r['tail_top'][3],'1e-10')),mp,'tail fields differ'),
        'tail_sum (mp>0)':(lambda r:r.update(tail_sum=bump(r['tail_sum'])),mp,'tail fields differ'),
        'tail width (mp>0)':(lambda r:r['tail_top'].pop(),mp,'tail width'),
        'tail_argmax (mp>0, no tie)':(lambda r:r.update(tail_argmax=r['begin']+(r['tail_argmax']-r['begin']+1)%(r['end']-r['begin'])),mp,'without a near tie'),
        'tail_argmax outside the row':(lambda r:r.update(tail_argmax=r['end']),zero,'outside [begin, end)'),
        'tail_sum (mp=0)':(lambda r:r.update(tail_sum=bump(r['tail_sum'],'1e-40')),zero,'(mp=0) differ'),
        'an uncovered field':(lambda r:r.update(extra_field='1'),mp,'not covered by the comparison rule'),
        'a missing tail field':(lambda r:r.pop('tail_sum'),mp,'lacks field'),
        'values (mp>0)':(lambda r:r['values'].__setitem__(0,bump(r['values'][0],'1e-10')),mp,'differs by'),
    }
    for what,(fn,uid,needle)in refusals.items():_refused(lambda:V.compare(dec,gmp(fn,uid),'gmp',tails=True),needle,what)
    # within the tolerance: accepted
    tiny=lambda r:(r.update(max_abs=bump(r['max_abs'],'1e-33'),tail_sum=bump(r['tail_sum'],'1e-35')),r['tail_top'].__setitem__(0,bump(r['tail_top'][0],'1e-34')))
    ok_tiny=V.compare(dec,gmp(tiny,mp),'gmp',tails=True);assert D(ok_tiny['max_abs_max_normalized_difference_mp_rows'])>0 and D(ok_tiny['tail_max_normalized_difference_mp_rows'])>0,ok_tiny
    # a near tie (the two largest |t| equal within the tolerance in both rows): a moved argmax is accepted and counted
    tie_rows=json.loads(json.dumps(rows));t=next(r for r in tie_rows if r['uid']==mp);t['tail_top'][1]=t['tail_top'][0];tdec=_out(8,tie_rows,'decimal')
    tg=json.loads(json.dumps(_out(8,tie_rows,'gmp')));y=next(r for r in tg['rows']if r['uid']==mp);y['tail_argmax']=y['begin']+(y['tail_argmax']-y['begin']+1)%(y['end']-y['begin'])
    assert V.compare(tdec,tg,'gmp',tails=True)['tail_argmax_ties']==1
    # G-REF: the reference has no tail fields (accepted); one that has them, and another header seed, refused
    ref=json.loads(json.dumps(dec));[[r.pop(k)for k in V.TAIL]for r in ref['rows']];V.compare(ref,gmp(),'gmp')
    _refused(lambda:V.compare(dec,gmp(),'gmp'),'compare it with tails=True','a tail-carrying G-REF reference')
    _refused(lambda:V.compare(dec,dict(gmp(),seed=1),'gmp',tails=True),'header field seed','another seed')
    # compare_exact (G-C7) and compare_jet (G-JET) refuse uncovered fields
    c7=json.loads(json.dumps(ref));c7['rows'][0]['new_c7_field']=1
    _refused(lambda:V.compare_exact(c7,dec,'G-C7'),'not covered by the G-C7 rule','an uncovered G-C7 field')
    o7=_out(7,_rows(7,V.task_rows([11],2,256),order=7),'decimal');o7['order']=7;o8=json.loads(json.dumps(o7));o8['order']=8
    for r in o8['rows']:v=r['values'];r['values']=[v[0],'1',v[1],'1']   # K7=0, K8=1: b slot 0 and c slot 0 kept, the new slots finite
    V.compare_jet(o7,o8,7,'G-JET');o8['rows'][0]['new_field']=1
    _refused(lambda:V.compare_jet(o7,o8,7,'G-JET'),'not covered by the G-JET rule','an uncovered G-JET field')
    # G-BK8 end to end on stand-in outputs: the record carries the row rule and is accepted by coverage(); a tampered
    # max_abs of one mp>0 row in one gmp output fails the gate
    tamper={}
    def fresh(cmd,out,env=None,threads=None):
        lines=Path(cmd[4]).read_text().split('\n')[1:];L=int(Path(cmd[4]).read_text().split()[2])
        uids=[tuple(map(int,l.split()))for l in lines if l.strip()];b='gmp'if Path(str(cmd[0])).name=='c8d2_gmp'else'decimal'
        o=_out(L,_rows(L,uids),b)
        if b=='gmp'and tamper.get('on'):
            r=next(r for r in o['rows']if r['mp']>0);r['max_abs']=str(D(r['max_abs'])*(1+D('1e-25')))
        return o
    with tempfile.TemporaryDirectory(prefix='c8d2_bk8_')as td,mock.patch.object(V,'fresh_output',fresh),mock.patch.object(V,'stage',lambda root,s,L,ids:root),\
         mock.patch.object(V,'make_net',lambda *x,**k:{}),mock.patch.object(V,'require',lambda *x,**k:None),contextlib.redirect_stdout(open(os.devnull,'w')):
        tests=V.bk8(Path(td),2,1)
        rec={'status':'passed','bk8':True,'executed':['bk8'],'parts':['none'],'tests':tests}
        cov=V.coverage(json.loads(json.dumps(rec)),'G-BK8');assert cov['complete'],cov
        assert all(t['row_rule']==V.BK8_ROW_RULE and t['rows']==800 and t['mp_rows']>0 and t['tail_argmax_ties']==0 for t in tests),tests[0]
        old=json.loads(json.dumps(rec));[t.pop('row_rule')for t in old['tests']]
        assert not V.coverage(old,'G-BK8')['complete']and V.coverage(old,'G-BK8',row_rule=False)['complete']
        tamper['on']=True;_refused(lambda:V.bk8(Path(td),2,1),'max_abs differs','G-BK8 with a tampered max_abs on an mp>0 row')
    # A-RPL-6's chunk merge (W2's class): the chunks of a whole task must tile it and add up in quad and mp, the largest
    # chunk max_abs is the whole's; values within the caller's bound, tails merged exactly
    def chunk(uid,b,e,q,m,mx,top,arg):return {'uid':uid,'rep':0,'graph':5,'begin':b,'end':e,'total':256,'quad':q,'mp':m,'max_abs':mx,'values':['1.5','2.25'],
                                             'tail_top':top,'tail_sum':str(sum(D(t)for t in top)),'tail_argmax':arg}
    parts=[chunk(1,0,128,3,1,'4.5',['9','3','1'],17),chunk(2,128,256,2,0,'6.5',['8','7'],200)]
    whole=dict(chunk(0,0,256,5,1,'6.5',['9','8','7','3','1'],17),values=['3.0','4.50'])
    e,t=V.chunk_merge(whole,parts,'whole');assert e==0 and t==0,(e,t)
    for what,fn,needle in (('quad',lambda w:w.update(quad=4),'quad/mp'),('mp',lambda w:w.update(mp=2),'quad/mp'),('max_abs',lambda w:w.update(max_abs='6.4'),'max_abs'),
                           ('a gap',lambda w:w.update(end=300),'do not tile'),('tail_argmax',lambda w:w.update(tail_argmax=200),'tail merge')):
        w=json.loads(json.dumps(whole));fn(w);_refused(lambda:V.chunk_merge(w,parts,'whole'),needle,f'a whole task with another {what}')
    ok('W2_compare_every_row_field_tails_and_max_abs_of_mp_rows',refusals=len(refusals)+4+5,tests=[(t['sector'],t['L'],t['rows'],t['mp_rows'])for t in tests])

def test_summaries():
    import importlib.util as iu
    f=ROOT/'benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py';sp=iu.spec_from_file_location('summarize_final_t',f);SF=iu.module_from_spec(sp);sp.loader.exec_module(SF)
    F=ROOT/'benchmarks/expanse_2026-10-c8/stage4b/final';V3=next(F.glob('g4bval3.*'));V2=next(F.glob('g4bval2.*'))
    L=lambda p:json.loads(Path(p).read_text())
    qd,ti,bk,l8,l2,vf=(L(V3/'quad_differential.json'),L(V3/'thread_identity.json'),L(V3/'bk8.json'),L(V3/'l8self.json'),L(V3/'l2_control.json'),L(V2/'val2/validate_full.json'))
    got={'quad_differential':SF.quad_differential_verdict(qd)[0],'thread_identity':SF.thread_identity_verdict(ti)[0],'bk8':SF.validate_verdict(bk,'G-BK8',row_rule=False)[0],
         'l8self':SF.validate_verdict(l8,'G-L8SELF')[0],'l2_control':SF.validate_verdict(l2,'A-IN-6b')[0],'validate_full':SF.validate_verdict(vf,'J-VAL-2')[0]}
    assert set(got.values())=={'passed'},got
    small=json.loads(json.dumps(qd))
    for v in small['differential']['result']['random'].values():
        v['pairs']=4;[s.update(pairs=1)for s in v['streams'].values()]
    bad={'quad_differential':SF.quad_differential_verdict(small)[0],
         'thread_identity':SF.thread_identity_verdict(L(ROOT/'benchmarks/symmetry_2026-10-c8/s6fix1/s1build.570371.0/thread_identity_omp_env.json'))[0],
         'bk8':SF.validate_verdict(dict(bk,tests=bk['tests'][1:]),'G-BK8',row_rule=False)[0],
         'validate_full':SF.validate_verdict(dict(vf,executed=['describe'],parts=['describe']),'J-VAL-2')[0]}
    assert all(v.startswith('FAILED')for v in bad.values()),bad
    text=f.read_text()
    for call in ("quad_differential_verdict(qd)","thread_identity_verdict(ti)","validate_verdict(bk, 'G-BK8', row_rule=False)","validate_verdict(l8, 'G-L8SELF')",
                 "validate_verdict(vf, 'J-VAL-2')","validate_verdict(load(V3 / 'l2_control.json'), 'A-IN-6b')","forced_tiers_verdict(ft)"):
        assert call in text,call
    cp=subprocess.run([PY,'-B',str(f)],cwd=ROOT,capture_output=True,text=True,timeout=600);assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
    # the same consumers in stage5/exp/scripts/s5e_summary.py (fix round 4, integration; G1's note): its zen2 records are
    # judged by recomputed coverage too (G-BK8 without the pre-W2 row rule, G-L8SELF, J-VAL-2), with the same verdicts
    s5=ROOT/'benchmarks/expanse_2026-10-c8/stage5/exp/scripts/s5e_summary.py';t5=s5.read_text()
    for call in ("SF.validate_verdict(bk, 'G-BK8', row_rule=False)","SF.validate_verdict(load(E / 'vs_default_l8.json'), 'G-L8SELF')","SF.validate_verdict(vf, 'J-VAL-2')"):
        assert call in t5,call
    cp=subprocess.run([PY,'-B',str(s5),'--only','zen2'],cwd=ROOT,capture_output=True,text=True,timeout=600);z=json.loads(cp.stdout)['zen2']
    assert cp.returncode==0 and z['bk8']==z['vs_default_l8']==z['val2']['validate_full']=='passed'and z['bk8_coverage']['complete'],(cp.returncode,cp.stderr[-800:])
    # validate.py --check RECORD --gate NAME: J-VAL-1 of a symmetry record, refused for a record whose diagnostic part
    # was skipped (its status still says "passed"), J-VAL-2, G-BK8 (a pre-W2 record lacks the row rule)
    vchk=lambda rec,g:subprocess.run([PY,'-B',str(ROOT/'tests/validate.py'),'--check',str(rec),'--gate',g],capture_output=True,text=True,timeout=300).returncode
    j1=ROOT/'benchmarks/symmetry_2026-10-c8/s6fix3/s3val1.570534.0/test/validate.json';sk=ROOT/'benchmarks/expanse_2026-10-c8/stage3b/s3bval1.54643360.0/records/validate.json'
    assert L(sk)['status']=='passed'and any(t.get('status')=='skipped'for t in L(sk)['tests'])
    assert (vchk(j1,'J-VAL-1'),vchk(sk,'J-VAL-1'),vchk(j1,'J-VAL-2'),vchk(V2/'val2/validate_full.json','J-VAL-2'),vchk(V3/'bk8.json','G-BK8'))==(0,1,1,0,1)
    ok('W1_W22_W2_consumers_summarize_final_checks_recomputed_coverage',stored=got,edited={k:v[:90]for k,v in bad.items()})

TESTS=[('hooks',test_hooks),('loader',test_loader),('syntax',test_syntax),('quad_coverage',test_quad_coverage),('thread_coverage',test_thread_coverage),
       ('bk8_compare',test_bk8_compare),('summaries',test_summaries)]

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only')
    a=ap.parse_args();names=[n for n,_ in TESTS]
    sel=names if a.only is None else[s.strip()for s in a.only.split(',')if s.strip()]
    bad=[s for s in sel if s not in names]
    if not sel or bad:ap.error(f'--only: unknown test(s) {bad}; the tests are {", ".join(names)}'if bad else'--only: no test named')
    if shutil.which(cxx()[0])is None:raise SystemExit(f'no C++ compiler ({cxx()[0]}); these tests need one')
    failed=[]
    for n,fn in TESTS:
        if n not in sel:continue
        try:fn()
        except Exception as e:
            import traceback;traceback.print_exc();failed.append(n);RESULTS.append({'test':n,'status':'failed','error':f'{type(e).__name__}: {e}'[:3000]})
    rec={'passed':not failed,'tests':len(RESULTS),'failed':failed,'requested':sel,'results':RESULTS}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1,default=str)+'\n')
    print(json.dumps({k:rec[k]for k in ('passed','tests','failed')}));return 0 if not failed else 1

if __name__=='__main__':sys.exit(main())
