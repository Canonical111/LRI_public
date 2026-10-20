#!/usr/bin/env python3
"""Stage 4c framework (PLAN D1, A-FLAG-1..3, A-RPL-8): Mac-runnable tests of the pure logic. No native build: make runs
with -n, the workers are tests/fake_worker.py copies (bin/c8d2_gmp and bin/c8d2_gmp_<p>), lanes use --fake-topology.

  make_profiles  `make gmp NUMERICS=<p>[,<p>...]`: bin/c8d2_gmp_<canonical name> with -DC8_NUMERICS -DC8_NUMERICS_<P>
                 after -DC8_USE_GMP, the required flags last of the compile options, the build record given the command
                 that ran and C8B_NUMERICS the canonical name; every default command word for word as delivered
                 (test_gmp_prefix's expectations) with NUMERICS unset and NUMERICS=exact; the refusals (unknown,
                 mpconv, exact mixed in, a repeated or empty name, any goal but gmp); clean removes profile executables
  hooks          src/kernel.hpp and src/c8d2_integrate.cpp: numerics.hpp is included only under C8_NUMERICS (stages 1
                 and 2); with the hooks expanded by their defaults and the profile branches dropped, the two files are
                 token for token the final default binary's (git 700473a, when the checkout has it; kernel.hpp apart
                 from Stage-6 fix round 3's Z3 refusal block and Z4 loader checks, fix3_view); the stub headers
                 define the no-op tiers; the F1 tool reads only the build's own evaluate()
  pure           numerics_flags.py: F1 merging and verdicts (violations, level mismatches, *_violations checks, strict
                 identity), per-task normalized differences, quantiles, the doubling rule, development labels
  f2_self        F2 + F4 --self-test with the fake exact worker: dC8 = 0 exactly, every task difference 0, F3 changes
                 0, F4 rows repeatable and identical; a stub profile (fake c8d2_gmp_dd) is held to the same identity
  f2_profile     a fake profile with a relative change 1e-12: F2 passes; dC8 and SE_d equal an independent
                 recomputation from the per-row CSV (assemble.jacobians at the exact means), and the nonlinear dC8 of
                 the vendored coefficients agrees; a change of 1e-6 fails the per-task bound (exit 1); a change sized to
                 fail only by 3 SE_d doubles the replicates
  scripts        the Stage-4c job scripts: bash syntax, #SBATCH account, partition, --mem, -t, --no-requeue, names,
                 logs; the submit driver admits (h7_admit.py and the agent share) before its only sbatch
  overrides      (G4c D2) a profile-parameter override makes a development build: mp256.hpp and exp1.hpp, preprocessed
                 by the host compiler, print "development":true and the overridden macro only with -DC8_MP256_RATIO /
                 -DC8_EXP1_RANGE (without it the parameter text is the gate build's); `make -n gmp NUMERICS=<p>
                 CPPFLAGS=-D...` hands the override to the build record, where build_record.parameter_overrides finds
                 it (-D/-U, both spellings, C8_NX_* hooks) and finds none in the default, profile and diagnostic
                 commands
  f2_seeds       (G4c D3) F2 registers its campaign seeds in the seed log before it starts (base, and native and net
                 seeds of all 24 groups, fixed labels); a rerun adds nothing; a seed logged under another source, a
                 missing log and no log at all are refused before any output exists
  coverage       (Stage-6 fix round 1, X1) f1_coverage: both sectors, the prescribed L7/L8 graphs and points, the
                 promotion quotas, every baseline point evaluated (an omitted sector, unmet quotas, a false need_met,
                 other or fewer graphs, a range gap, scale, sample, a missing loop, a short profile pass refused); job
                 570210's baseline and F1 pass have the full coverage, its record is refused by design.check_gate for
                 exactly the missing X1/X2/X3 evidence; with the evidence added it is accepted, and every X1/X2/X3 field
                 removed or wrong is refused by its message
  binding        (X2) the source snapshot, bind() (reproduced byte for byte; a stale executable, a wrong numerics
                 pin and a non-Makefile command refused), the F1 tool compiled from the snapshot, with a fake compiler;
                 numerics_flags.py refuses a stale profile executable and an unbound reused baseline before any output
                 and records build_binding for current executables. Y1 (Stage-6 fix round 2), with a fake ldd: the F1
                 tool must resolve the libgmp its executable's build record names, as the executable must here
                 (compile_tool records it; a tool or an executable resolving another libgmp, no ldd answer and a record
                 without gmp_library.sha256 are refused), and the harness records tool_gmp_library. Z19 (Stage-6 fix
                 round 3): a reused baseline without tool_gmp_library, naming another libgmp (tool or want), not
                 matched, or whose exact executable now resolves another libgmp is refused before any output
  macro_overrides  (Z3, Stage-6 fix round 3) build_record: parameter_overrides names -DNO_SUM_SHARING, -Wp,-D, -include,
                 -imacros, -Xpreprocessor and @FILE; macro_overrides finds every injected C8_* macro and source switch
                 in the host compiler's own probe; such a record is "development" and refused by gmp_target, as is a
                 record without macro_overrides
  f5_team        (X3) the sanitized OpenMP environment (child_env), observed teams equal to the request under an
                 inherited OMP_THREAD_LIMIT=1 / OMP_DYNAMIC=true, a forced smaller team and an unobservable team
                 refused (run_one, run_lanes), f5_run's verdict on team_sizes_verified, run_native's environment
  w18_inputs     (W18, Stage-6 fix round 4) the gate's authenticated input set: input_identity (the inputs manifest's
                 sha256, every input hashed against it, missing L8 packs recorded), a changed gamma or two-loop file
                 refused, the end-of-run check, a self-test record carrying it; test_coverage: check_gate refuses 570536
                 for exactly its missing identity, every inputs field wrong, a gate of other inputs (a changed payload,
                 same counts and executables); test_binding: a reused baseline of other or no inputs refused
  w20_seeds      (W20) F2's seeds in one locked transaction: a production plan registering the base seed right after F2
                 read the log is refused (before: both registered), a plan first refuses F2, a derived C8 group seed of
                 a logged campaign is refused, a rerun is present
Usage: python3 -B tests/test_numerics_flags.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,math,os,re,shlex,shutil,subprocess,sys,tempfile
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)
S4C=ROOT/'benchmarks/expanse_2026-10-c8/stage4c/scripts'

# ---------------------------------------------------------------- make
def test_make_profiles():
    import test_gmp_prefix as G
    REQ=G.REQ
    # the profiles' own flags (NX_FLAGS_<p>, set by each profile's developer: dd has -mavx2 -mfma, A-FLAG-4)
    NXF={p:shlex.split(re.search(rf'^override NX_FLAGS_{p} =(.*)$',(ROOT/'Makefile').read_text(),re.M).group(1))for p in('dd','mp256','exp1')}
    assert NXF['dd']==['-mavx2','-mfma'],NXF
    for extra in ((),('NUMERICS=exact',)):
        cp=G.dry('CXX=g++',*extra);assert cp.returncode==0,cp.stderr[-500:]
        got=G.compiles(cp.stdout);want=G.expected_default('g++',[],['-O3'],[],[],[]);assert got==want,{k:got.get(k)for k in want if got.get(k)!=want[k]}
    cases=(('dd','dd',['-DC8_NUMERICS_DD']),('mp256','mp256',['-DC8_NUMERICS_MP256']),('exp1','exp1',['-DC8_NUMERICS_EXP1']),
           ('exp1,dd','dd+exp1',['-DC8_NUMERICS_DD','-DC8_NUMERICS_EXP1']),('exp1+mp256+dd','dd+mp256+exp1',['-DC8_NUMERICS_DD','-DC8_NUMERICS_MP256','-DC8_NUMERICS_EXP1']),
           ('dd,mp256,exp1','dd+mp256+exp1',['-DC8_NUMERICS_DD','-DC8_NUMERICS_MP256','-DC8_NUMERICS_EXP1']))
    for hooks in ({'CXX':'g++'},{'CXX':'g++-13','CPPFLAGS':'-I/x','OPTFLAGS':'-O2','CXXFLAGS':'-g','LDFLAGS':'-L/y','LDLIBS':'-lfoo'}):
        sp=lambda k,d='':shlex.split(hooks.get(k,d))
        for raw,name,defs in cases:
            cp=G.dry(*[f'{k}={v}'for k,v in hooks.items()],f'NUMERICS={raw}',targets=('gmp',));assert cp.returncode==0,(raw,cp.stderr[-500:])
            got=G.compiles(cp.stdout);exe=f'bin/c8d2_gmp_{name}';assert list(got)==[exe],(raw,list(got))
            nxf=[w for d in defs for w in NXF[d[len('-DC8_NUMERICS_'):].lower()]]   # each profile's NX_FLAGS_<p>, canonical order
            want=[hooks['CXX'],*sp('CPPFLAGS'),*sp('OPTFLAGS','-O3'),*sp('CXXFLAGS'),*nxf,*REQ,'-DC8_USE_GMP','-DC8_NUMERICS',*defs,'src/c8d2_integrate.cpp',
                  *sp('LDFLAGS'),'-lquadmath','-lgmp',*sp('LDLIBS'),'-o',exe]
            assert got[exe]==want,(raw,got[exe],want)
            assert G.records(cp.stdout)[exe]==want,raw   # the build record receives the command that ran
            assert 'tools/prepare_inputs.py'in cp.stdout   # `make gmp` still verifies the inputs
    show=lambda *args:subprocess.run(['make','-s','-C',str(ROOT),'-f','-',*args,'show'],input=(ROOT/'Makefile').read_text()+'\nshow:\n\t@echo "[$$C8B_NUMERICS]"\n',
                                     capture_output=True,text=True,env={k:v for k,v in os.environ.items()if k not in G.HOOKS},timeout=120)
    assert show().stdout.strip()=='[exact]'
    for raw,needle in (('foo','unknown profile(s) foo'),('mpconv','R4d (mpconv) is not implemented'),('dd,mpconv','not implemented'),('exact,dd','does not combine'),
                       ('dd,dd','named twice'),(',','name a profile')):
        cp=G.dry(f'NUMERICS={raw}',targets=('gmp',));assert cp.returncode!=0 and needle in cp.stderr,(raw,cp.stderr[-300:])
    for targets in (('all',),('decimal',),('profile',),('bin/c8d2_gmp',),('sanitize',),('test',)):
        cp=G.dry('NUMERICS=dd',targets=targets);assert cp.returncode!=0 and 'applies to `make gmp` only'in cp.stderr,(targets,cp.stderr[-300:])
    cp=G.dry('NUMERICS=dd',targets=('bin/c8d2_gmp_dd',));assert cp.returncode==0 and 'bin/c8d2_gmp_dd'in G.compiles(cp.stdout)
    cp=subprocess.run(['make','-s','-n','-C',str(ROOT),'clean'],capture_output=True,text=True,timeout=60)
    for p in ('dd','mp256','exp1'):assert f'bin/c8d2_gmp_{p} bin/c8d2_gmp_{p}.build.json bin/c8d2_gmp_{p}+*'in cp.stdout,cp.stdout[-400:]
    # the profile executable depends on src/numerics/ (the default ones do not)
    mk=(ROOT/'Makefile').read_text();assert 'override NX_DEPS = $(WORKER_DEPS) $(wildcard src/numerics/*.hpp)'in mk and 'src/numerics'not in mk.split('override WORKER_DEPS = ')[1].split('\n')[0]
    ok('make_profiles',cases=len(cases))

# ---------------------------------------------------------------- source hooks
def strip_comments(text:str)->str:
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    return '\n'.join(re.sub(r'//.*$','',l)if not l.lstrip().startswith('#include')else l for l in text.splitlines())

def default_view(text:str)->str:
    """The default build's view of a source: #ifdef C8_NUMERICS blocks resolved as undefined (their #else part kept),
    the #ifndef C8_NX_* default definitions dropped, the hook calls expanded by their defaults."""
    out=[];stack=[]
    lines=text.splitlines();i=0
    while i<len(lines):
        l=lines[i];s=l.strip()
        if s=='#ifdef C8_NUMERICS':stack.append('nx-if');i+=1;continue
        if re.fullmatch(r'#ifndef C8_NX_\w+',s):  # a default hook definition: #ifndef / #define / #endif
            assert lines[i+1].strip().startswith('#define C8_NX_')and lines[i+2].strip()=='#endif',lines[i:i+3];i+=3;continue
        if s.startswith('#if'):stack.append('other')
        elif s=='#else'and stack and stack[-1]in('nx-if','nx-else'):stack[-1]='nx-else';i+=1;continue
        elif s=='#endif':
            top=stack.pop()
            if top in('nx-if','nx-else'):i+=1;continue
        if 'nx-if'in stack:i+=1;continue
        out.append(l);i+=1
    t='\n'.join(out)
    t=re.sub(r'C8_NX_SHARED_BEGIN\(T\)','',t);t=re.sub(r'C8_NX_DESCRIBE\((?:std::cout|f)\)','',t)
    for m in ('C8_NX_XS_Q','C8_NX_XS_MP'):
        while m+'('in t:
            k=t.index(m+'(');j=k+len(m)+1;depth=1
            while depth:depth+={'(':1,')':-1}.get(t[j],0);j+=1
            t=t[:k]+t[k+len(m)+1:j-1]+t[j:]
    return t

def tokens(text:str)->str:return ''.join(strip_comments(text).split())

Z4_CHECK='if(!f)throw std::runtime_error("truncated graph: "+path);'
def fix3_view(text:str,new:bool)->str:
    """Stage-6 fix round 3's two source changes taken out of src/kernel.hpp, so that the rest can be compared with the
    final default binary's sources: (Z3) the #if defined(C8_NX_...) #error refusal block of the new file, (Z4) its
    initializers M=0, T=0, n=0, and every "truncated graph" check of load_graph, in the new and the old file alike
    (the old loader had one, at the end; the new one adds five, one after each section)."""
    if new:
        text,n=re.subn(r'#if defined\(C8_NX_STAGE\).*?\n#endif\n','',text,count=1,flags=re.S);assert n==1,'the Z3 refusal block'
        assert text.count('int M=0,T=0,n=0;')==1,'the Z4 initializers';text=text.replace('int M=0,T=0,n=0;','int M,T,n;')
    return text.replace(Z4_CHECK,'')

def test_hooks():
    k=(ROOT/'src/kernel.hpp').read_text();c=(ROOT/'src/c8d2_integrate.cpp').read_text()
    assert k.count('#include "numerics/numerics.hpp"')==2 and k.count('#define C8_NX_STAGE 1')==1 and k.count('#define C8_NX_STAGE 2')==1
    for m in re.finditer(r'#include "numerics/numerics.hpp"',k):
        before=k[:m.start()].splitlines()[-2:];assert before[0].strip()=='#ifdef C8_NUMERICS'and before[1].strip().startswith('#define C8_NX_STAGE'),before
    assert k.index('#define C8_NX_STAGE 1')<k.index('std::pair<T,T> calculate_shared(')<k.index('#define C8_NX_STAGE 2')<k.index('inline Eval evaluate(')
    assert '#include "numerics/'not in c,'c8d2_integrate.cpp includes no profile code itself'
    # the default view equals the final default binary's sources (token for token, comments ignored)
    have_git=(ROOT/'.git').exists()and subprocess.run(['git','-C',str(ROOT),'cat-file','-e','700473a:src/kernel.hpp'],capture_output=True).returncode==0
    if have_git:
        for path,new in (('src/kernel.hpp',k),('src/c8d2_integrate.cpp',c)):
            old=subprocess.run(['git','-C',str(ROOT),'show',f'700473a:{path}'],capture_output=True,text=True,check=True).stdout
            view=default_view(new)
            if path=='src/kernel.hpp':  # Stage-6 fix round 3 (Z3, Z4): the refusal block and the loader's checks, and nothing else
                assert new.count(Z4_CHECK)==6 and old.count(Z4_CHECK)==1,(new.count(Z4_CHECK),old.count(Z4_CHECK))
                view,old=fix3_view(view,True),fix3_view(old,False)
            assert tokens(view)==tokens(old),f'{path}: the default view differs from 700473a'
        for path in ('src/quadfast.hpp','src/diagnostics.hpp'):
            old=subprocess.run(['git','-C',str(ROOT),'show',f'700473a:{path}'],capture_output=True,text=True,check=True).stdout
            assert (ROOT/path).read_text()==old,f'{path} changed'
    # the profile headers (Stage 4c: dd, mp256 and exp1 implemented and merged on c8; the framework's stubs are gone)
    nx=ROOT/'src/numerics';assert sorted(p.name for p in nx.glob('*.hpp'))==['dd.hpp','exp1.hpp','mp256.hpp','numerics.hpp']
    dd=strip_comments((nx/'dd.hpp').read_text());mp=strip_comments((nx/'mp256.hpp').read_text());e1=strip_comments((nx/'exp1.hpp').read_text())
    # dd.hpp is implemented (R3b): its tier falls back to the exact binary128 tier and may route to the MP tier; it
    # defines its parameters and its F1 checks C8_NX_F1_CHECKS_DD only (tests/test_dd_profile.py checks it in detail)
    assert re.search(r'inline void tier\(.*\)\s*\{\s*tier_impl<0>\(g, lx, shift, f, lev\);\s*\}',dd)and 'quad_tier(g, lx, shift, f, lev)'in dd
    assert sorted(set(re.findall(r'#define (C8_NX_\w+)',dd)))==['C8_NX_F1_CHECKS_DD','C8_NX_PARAMS_DD'],re.findall(r'#define (C8_NX_\w+)',dd)
    # mp256 (R4b, implemented on flag-mp256): a gmp_float<77> evaluation with its error estimate, accepted at the
    # ratio 1e-63 and otherwise escalated to the exact 350-digit tier; it defines no calculate_shared hook (exp1's)
    assert all(s in mp for s in ('constexpr unsigned digits10 = 77;','gmp_float<digits10>','#define C8_MP256_RATIO 1e-63',
        'auto m = calculate_shared<MP77, true>(g, lx, shift);','if (absolute(m.first) < ratio() * m.second) {','mp_tier_exact(g, lx, shift, f, lev);',
        'f = m.first.convert_to<ld>(); lev = 2; last_tier = MP256;','#define C8_NX_PARAMS_MP256(os)','#define C8_NX_F1_CHECKS_MP256('))\
        and not re.search(r'#define C8_NX_(SHARED_BEGIN|XS_Q|XS_MP|DESCRIBE)\b',mp)
    e1s=e1.split('#elif C8_NX_STAGE == 2');assert len(e1s)==2 and '#define'not in e1s[1]and all(f'#define {m}'in e1s[0]for m in('C8_NX_SHARED_BEGIN(T)','C8_NX_XS_Q(e)','C8_NX_XS_MP(e)','C8_NX_PARAMS_EXP1(os)'))and '#define C8_NX_F1_CHECKS_EXP1('in e1s[0]and 'nx::exp1::mul_q(s.x[j], nx_exp1.f) : nx::exp1::exact_edge(e))'in e1 and 'return quadfast::mul(x, f);'in e1  # R4c exp1 (no longer a stub): the hooks at stage 1 only, the binary128 product through quadfast, the exact expression as the guard's fallback
    h=(nx/'numerics.hpp').read_text()
    for need in ('inline void mp_tier_exact(','inline void mp_tier(','inline void quad_tier(','inline void promote(','#define C8_NX_DESCRIBE(os) nx::describe(os);'):assert need in h,need
    assert h.index('inline void mp_tier_exact(')<h.index('#include "mp256.hpp"',h.index('#elif C8_NX_STAGE == 2'))<h.index('inline void mp_tier(')<h.index('inline void quad_tier(')\
        <h.index('#include "dd.hpp"',h.index('#elif C8_NX_STAGE == 2'))<h.index('inline void promote(')
    # F1 checks: only numerics.hpp defines C8_NX_F1_CHECKS, as nx::f1_checks running every profile's own checks in the order
    # exp1, mp256, dd (dd's re-evaluate the point) and then clearing the state those re-evaluations leave
    for s in (dd,mp,e1):assert not re.search(r'#define C8_NX_F1_CHECKS\(',s)
    fc=h[h.index('template<class Counts> inline void f1_checks('):h.index('#define C8_NX_F1_CHECKS(g, lx, shift, counts) nx::f1_checks(g, lx, shift, counts)')]
    assert h.index('inline void promote(')<h.index('template<class Counts> inline void f1_checks(')
    assert fc.index('C8_NX_F1_CHECKS_EXP1(g, lx, shift, counts);')<fc.index('C8_NX_F1_CHECKS_MP256(g, lx, shift, counts);')<fc.index('C8_NX_F1_CHECKS_DD(g, lx, shift, counts);')\
        <fc.index('mp256::reached = false;')<fc.index('exp1::counters = exp1::Counters{};')
    assert 'tf == QUAD || tf == MP256 || tf == MP350'in dd   # dd's forced guards may end in mp256's tier in a combination
    # the exact tier statements of numerics.hpp are the default evaluate()'s (tokens), apart from the tier code
    at=k.index('nx::promote(g,lx,shift,f,lev);}');ev=k[k.index('#else',at):k.index('#endif',at)]
    q=re.search(r'inline void quad_tier\([^)]*\)\s*\{(.*?)\n\}',h,re.S).group(1);m=re.search(r'inline void mp_tier_exact\([^)]*\)\s*\{(.*?)\n\}',h,re.S).group(1)
    norm=lambda s:''.join(s.replace('last_tier = QUAD;','').replace('last_tier = MP350;','').split())
    assert norm('auto q = calculate_shared<Q>(g, lx, shift); lev = 1; f = ld(q.first); C8_DIAG_TIER(1); C8_DIAG_QUAD(q);')in norm(ev)and norm(q).startswith(norm('auto q = calculate_shared<Q>(g, lx, shift); lev = 1; f = ld(q.first); C8_DIAG_TIER(1); C8_DIAG_QUAD(q);'))
    assert norm(m)==norm('auto m = calculate_shared<MP, C8_MP_NEED_ERROR>(g, lx, shift); f = m.first.convert_to<ld>(); lev = 2; C8_DIAG_TIER(2); C8_DIAG_MP(m);')
    assert norm('if(absolute(q.first)<Q(1e-23L)*q.second)')in norm(ev)and norm('if (absolute(q.first) < Q(1e-23L) * q.second) mp_tier(g, lx, shift, f, lev);')in norm(q)
    f1=(ROOT/'tests/numerics_f1.cpp').read_text();assert '#include "../src/kernel.hpp"'in f1 and 'evaluate(g,lx.data(),shift,s)'in f1 and 'calculate_shared'not in f1
    ok('hooks',default_view_checked_against_700473a=have_git)

# ---------------------------------------------------------------- pure logic
def f1_stats(points=10,viol=0,mismatch=0,identical=None,checks=None,rel='1.0e-20'):
    tiers={t:{'points':0,'violations':0,'max_relative_error':'0.0e+00','max_scaled_error':'0.0e+00','hist_relative':{},'hist_scaled':{}}for t in ('long_double','double_double','binary128','mp256','mp350')}
    tiers['long_double'].update(points=points-2,violations=viol,max_relative_error=rel,hist_relative={'-20':points-2});tiers['binary128'].update(points=2,hist_relative={'-30':2})
    d={'L':7,'graphs':1,'begin':0,'end':points,'mode':'read','numerics':'dd','points':points,'level':[points-2,2,0],'level_mismatch':mismatch,'nonmoderate':0,'nondirect':1,
       'tiers':tiers,'profile_checks':checks or{},'first_violations':['x']if viol else[]}
    d['paired']={'identical':points if identical is None else identical,'max_relative_difference':'0.0e+00','hist_relative_difference':{'zero_or_below':points},'transitions':{'binary128->binary128':2}}
    return d

def test_pure():
    import numerics_flags as NF
    a=f1_stats();b=f1_stats(points=6,rel='3.0e-19');m=NF.f1_merge(NF.f1_merge(None,a),b)
    assert m['points']==16 and m['level']==[12,4,0]and m['tiers']['long_double']['points']==12 and m['tiers']['long_double']['max_relative_error']=='3.0e-19'
    assert m['tiers']['long_double']['hist_relative']=={'-20':12}and m['paired']['identical']==16 and m['paired']['transitions']=={'binary128->binary128':4}
    assert NF.f1_verdict(m,True)['passed']and NF.f1_verdict(m)['passed']
    assert not NF.f1_verdict(NF.f1_merge(a,f1_stats(viol=1)))['passed']
    assert not NF.f1_verdict(f1_stats(mismatch=2))['passed']
    assert not NF.f1_verdict(f1_stats(checks={'dd_guard_violations':1,'dd_guard_points':7}))['passed']and NF.f1_verdict(f1_stats(checks={'dd_guard_points':7}))['passed']
    v=NF.f1_verdict(f1_stats(identical=9),True);assert not v['passed']and 'self-test'in v['why'][0];assert NF.f1_verdict(f1_stats(identical=9))['passed']
    e={'uid':1,'rep':0,'graph':5,'begin':0,'end':4,'total':4,'values':['0.5','-2','0','3']}
    p=dict(e,values=['0.5000000001','-2.000000002','1e-12','3'])
    nd,rd,dv=NF.task_normalized(e,p);assert nd==D('1e-9')and dv==[D('1e-10'),D('-2e-9'),D('1e-12'),D(0)]and rd==D('Infinity')
    try:NF.task_normalized(e,dict(p,graph=6));raise AssertionError('accepted')
    except AssertionError as x:assert 'row identity'in str(x)
    assert NF.task_normalized(e,dict(e))[0]==0
    q=NF.quantiles([D(0)]*90+[D('1e-12')]*10);assert q['p50']==0 and q['max']==D('1e-12')and q['zero']==90 and q['n']==100
    assert NF.hist_count([D(0),D('3e-12'),D('1e-12'),D('Infinity')])=={'zero':1,'-12':2,'inf':1}
    assert NF.num(float('inf'))=='inf'and NF.num(D('2'))==2.0
    g={'total':{'passed':False,'dC8':0.05},'free_L8':{'passed':False,'dC8':0.07},'power_L8':{'passed':True,'dC8':0.}};assert NF.unresolved(g)==['total']
    assert NF.numerics_name('exp1,dd')=='dd+exp1'
    ap=argparse.Namespace(f1_scale=1.0,f2_graphs=None,f2_loops='3,4,5,6,7,8',f2_replicates=4,f2_points=256,f4_sample=None,f4_loop=8,f4_repeats=3,f5_threads=[1,8,16,64],
                          f5_lanes=8,f5_lane_threads=8,fake_topology=None,sectors='free,power')
    assert NF.development(ap)==[]and NF.development(argparse.Namespace(**{**vars(ap),'sectors':'power, free'}))==[]
    for k,v in (('f1_scale',.5),('f2_graphs',8),('f2_loops','7,8'),('f2_points',64),('f4_sample',3),('f4_repeats',2),('f5_threads',[1,8]),('fake_topology','1x1x4'),
                ('sectors','free'),('sectors','power')):  # X1: F1 on one sector is a development run
        assert NF.development(argparse.Namespace(**{**vars(ap),k:v})),k
    ok('pure')

# ---------------------------------------------------------------- fake end-to-end runs
def fakes(td:Path,names=('c8d2_gmp','c8d2_gmp_dd'))->dict:
    out={}
    for n in names:
        p=td/n;p.write_text(f'#!{PY} -S\n'+(ROOT/'tests/fake_worker.py').read_text());p.chmod(0o755)
        (td/(n+'.build.json')).write_text(json.dumps({'executable_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'command':['g++','src/c8d2_integrate.cpp','-o',f'bin/{n}']}))
        out[n]=p
    return out

SMALL=['--parts','F2,F4','--shape','2x2','--fake-topology','1x2x2','--f2-loops','3,4,7','--f2-graphs','4','--f2-points','16','--f4-loop','7','--f4-sample','3','--f4-repeats','2']
def flags(td:Path,out:str,*args,env=None,seeds=True)->tuple[subprocess.CompletedProcess,dict]:
    """numerics_flags.py in a clean environment; F2 registers its seeds (PLAN D9), so a seed log td/auto_seeds.json is
    given through C8_SEEDS unless the call names one (--seeds-log or env) or seeds=False."""
    e={k:v for k,v in os.environ.items()if not k.startswith('C8_')};e.update(env or{})
    if seeds and 'C8_SEEDS'not in e and '--seeds-log'not in map(str,args):
        auto=td/'auto_seeds.json'
        if not auto.exists():auto.write_text(json.dumps({'schema':'c8-d2-seeds-1','seeds':[]})+'\n')
        e['C8_SEEDS']=str(auto)
    cp=subprocess.run([PY,'-B',str(ROOT/'tests/numerics_flags.py'),'--output',str(td/out),'--scratch',str(td),*map(str,args)],capture_output=True,text=True,env=e,timeout=900)
    rec=json.loads((td/out/'numerics_flags.json').read_text())if (td/out/'numerics_flags.json').exists()else None
    return cp,rec

def test_f2_self():
    with tempfile.TemporaryDirectory(prefix='c8d2_nf_')as td:
        td=Path(td);x=fakes(td)
        cp,r=flags(td,'self','--self-test','--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        assert r['mode']=='self-test'and r['strict_identity']['required']and r['status']=='development run (would pass)'and r['development']
        f=r['F2'];assert f['total']['dC8']==0.0 and f['self_test']['dC8_exactly_zero']and f['nonlinear']['dC8']==0.0
        assert f['per_task']['normalized']['zero']==f['per_task']['normalized']['n']>0 and f['per_task']['over_bound']==0
        assert set(f['gates'])=={'free_L7','power_L7','total'}and all(v['passed']for v in f['gates'].values())
        assert all(v['quad_change']==0 and v['mp_change']==0 for v in r['F3_counters'].values())and len(r['F3_counters'])==12
        assert r['F4']['rows_repeatable']and r['F4']['rows_identical_between_binaries']and set(r['F4']['speedup_exact_over_profile'])=={'total','free','power'}
        rows=list(csv.reader(gzip.open(td/'self/f2/rows.csv.gz','rt')));assert len(rows)-1==sum(v['tasks']for v in f['per_task']['by_group'].values())
        # a stub profile copy is held to the same identity
        cp,r=flags(td,'stub','--profile','dd','--profile-exe',x['c8d2_gmp_dd'],'--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode==0,cp.stdout[-1500:]
        assert r['strict_identity']=={'required':True,'why':'every profile of the executable is a stub'}and r['F2']['self_test']['dC8_exactly_zero']and 'stub'in r['note']
        # refusals: a non-canonical name, a missing build record, a profile executable reporting another profile
        cp,_=flags(td,'bad1','--profile','exp1+dd','--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode and "canonical name is 'dd+exp1'"in cp.stderr
        cp,_=flags(td,'bad2','--profile','mp256','--profile-exe',x['c8d2_gmp_dd'],'--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode and "reports numerics 'dd', expected 'mp256'"in cp.stderr
        (td/'c8d2_gmp_dd.build.json').write_text(json.dumps({'executable_sha256':'0'*64,'command':[]}))
        cp,_=flags(td,'bad3','--profile','dd','--profile-exe',x['c8d2_gmp_dd'],'--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode and 'describes another executable'in cp.stderr
        cp,_=flags(td,'self','--self-test','--exact',x['c8d2_gmp'],*SMALL);assert cp.returncode and 'exists'in cp.stderr
    ok('f2_f4_self_test_and_stub_identity')

def recompute(td:Path,out:str,reps:int)->dict:
    """dC8 and SE_d per (sector, L) and total, independently from rows.csv.gz: the exact loop means, the vendored
    Jacobians (assemble.jacobians) and the per-replicate sums of the differences."""
    import numpy as np
    import assemble as asm
    S={};dS={}
    with gzip.open(td/out/'f2/rows.csv.gz','rt')as f:
        rd=csv.reader(f);head=next(rd);bar=head.index('|')
        for r in rd:
            c,s,L,rep=r[0],r[1],int(r[2]),int(r[4]);i=r.index('|');ex=[float(v)for v in r[13:i]];df=[float(v)for v in r[i+1:]]
            S.setdefault((c,s,L),np.zeros((reps,len(ex))))[rep]+=ex;dS.setdefault((c,s,L),np.zeros((reps,len(ex))))[rep]+=df
    loops=sorted({L for _,_,L in S});m={L:sum(S[(c,s,L)].mean(0)for c in 'ab'for s in ('free','power'))/2 for L in loops}
    J=asm.jacobians(m,8);J8={L:np.asarray(J[L])[8].real for L in loops};out_={}
    def st(keys):
        mean=var=0.
        for c in 'ab':
            d=sum(dS[k]@J8[k[2]]for k in keys if k[0]==c);mean+=.5*d.mean();var+=.25*d.var(ddof=1)/reps
        return mean,math.sqrt(var)
    for s in ('free','power'):
        for L in loops:out_[f'{s}_L{L}']=st([k for k in dS if k[1]==s and k[2]==L])
    out_['total']=st(list(dS));return out_

def test_f2_profile():
    with tempfile.TemporaryDirectory(prefix='c8d2_nf_')as td:
        td=Path(td);x=fakes(td);args=['--profile','dd','--profile-exe',x['c8d2_gmp_dd'],'--exact',x['c8d2_gmp'],*SMALL,'--parts','F2']
        cp,r=flags(td,'d12',*args,env={'C8_FAKE_PROFILE_DELTA':'1e-12'});assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        f=r['F2'];assert not r['strict_identity']['required']and f['passed']and f['total']['dC8']!=0 and f['per_task']['over_bound']==0
        ind=recompute(td,'d12',4)
        for k,(mu,se)in ind.items():
            g=json.loads((td/'d12/f2/f2.json').read_text())['per_sector_L'].get(k)or f['gates'][k]
            assert math.isclose(g['dC8'],mu,rel_tol=1e-9)and math.isclose(float(g['se']),se,rel_tol=1e-9),(k,g,mu,se)
        assert math.isclose(f['nonlinear']['dC8'],f['total']['dC8'],rel_tol=1e-6),(f['nonlinear']['dC8'],f['total']['dC8'])
        assert 1e-14<float(f['per_task']['max_normalized'])<=1e-12*1.01 and f['projection']['points_per_graph_mini']==64
        assert all(v['within']for v in f['projection']['by_points']['32768'].values())
        # a 1e-6 change fails the per-task bound
        cp,r=flags(td,'d6',*args,env={'C8_FAKE_PROFILE_DELTA':'1e-6'});assert cp.returncode==1 and r['status']=='failed'and r['F2']['per_task']['over_bound']>0
        # a change sized to fail only by 3 SE_d: the replicates double
        mu,se=ind['total'];delta=float(1e-12*0.062/(abs(mu)+1.5*se))   # |dC8| < 0.062 < |dC8| + 3 SE_d at 4 replicates
        # repr of a plain float (F3, Stage 5): under NumPy >= 2 repr(numpy.float64) is 'np.float64(...)', which the fake worker cannot parse
        cp,r=flags(td,'dse',*args,'--f2-max-doublings','1',env={'C8_FAKE_PROFILE_DELTA':repr(float(delta))})
        f=r['F2'];assert f['doublings']==1 and f['replicates']==8,(f['doublings'],f['replicates'],f['gates']['total'])
        rows=list(csv.reader(gzip.open(td/'dse/f2/rows.csv.gz','rt')));assert {int(x[4])for x in rows[1:]}==set(range(8))
        assert len({(x[0],x[1],x[2],x[3])for x in rows[1:]})==len(rows)-1   # unique uids per group across the doubling
    ok('f2_profile_dC8_recomputed_bounds_doubling',delta_se_case=delta)

# ---------------------------------------------------------------- scripts
def test_scripts():
    names=sorted(p.name for p in S4C.glob('*.slurm'));assert names==['s4c_build.slurm','s4c_flags_node.slurm','s4c_flags_shared.slurm','s4c_precheck.slurm'],names
    for n in names:
        t=(S4C/n).read_text();assert subprocess.run(['bash','-n',str(S4C/n)]).returncode==0,n
        sb=' '.join(l for l in t.splitlines()if l.startswith('#SBATCH'))
        assert '-A yun124'in sb and '--mem='in sb and re.search(r'(?:^| )-t \d\d:\d\d:\d\d',sb)and '--no-requeue'in sb,n
        assert re.search(r'#SBATCH -J c8d2-s4c-\w+',t)and '#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out'in t,n
        assert 'source "$HOME/c8d2/env_expanse.sh"'in t and 'set -uo pipefail'in t,n
        if '-p compute'in sb:assert '--exclusive'in sb and '-N 1'in sb,n
        else:assert '-p shared'in sb and '--nodes=1'in sb,n
    sub=(S4C/'submit_s4c.sh').read_text();assert subprocess.run(['bash','-n',str(S4C/'submit_s4c.sh')]).returncode==0
    assert sub.count('sbatch --parsable')==1 and 'Master running'in sub and 'h7_admit.py'in sub
    body=sub[sub.index('sub() {'):];body=body[:body.index('\n}\n')]
    assert body.index('admit "$name"')<body.index('sbatch --parsable'),'the admission precedes the sbatch'
    assert "C8_S4C_MAX_NODES:-1"in sub and "C8_S4C_MAX_SHARED:-8"in sub and 'PFX=c8d2-s4c-$TAGN-'in sub
    assert (ROOT/'benchmarks/expanse_2026-10-c8/stage4a/scripts/h7_admit.py').is_file()and (ROOT/'benchmarks/expanse_2026-10-c8/ckpt_fix/scripts/export_check.py').is_file()
    import warnings
    with warnings.catch_warnings():   # syntax only, nothing written; a SyntaxWarning (e.g. `0.and`, Python 3.11) fails
        warnings.simplefilter('error',SyntaxWarning)
        for f in (S4C/'s4c_identity.py',ROOT/'tests/numerics_flags.py',ROOT/'tests/thread_identity.py'):compile(f.read_text(),str(f),'exec')
    ok('s4c_scripts',scripts=len(names)+1)

# ---------------------------------------------------------------- G4c fixes: development overrides (D2), F2 seeds (D3)
def preprocess(src:str,defines=())->str|None:
    import shutil
    c=next((x for x in (os.environ.get('CXX'),'c++','clang++','g++')if x and shutil.which(x)),None)
    if c is None:return None
    cp=subprocess.run([c,'-std=c++17','-E','-P','-x','c++',*defines,'-'],input=src,capture_output=True,text=True,timeout=120)
    assert cp.returncode==0,cp.stderr[-1500:]
    return cp.stdout

def test_overrides():
    import test_gmp_prefix as G
    import build_record as BR
    nx=ROOT/'src/numerics';head='#define C8_NUMERICS\n#define C8_USE_GMP\n#define C8_NX_STAGE 1\n'
    mp=head+'#define C8_NUMERICS_MP256\n#include "'+str(nx/'mp256.hpp')+'"\n'
    e1=head+'#define C8_NUMERICS_EXP1\n#include <ostream>\nusing ld = long double;\n#include "'+str(nx/'exp1.hpp')+'"\nvoid probe(std::ostream& os) { C8_NX_PARAMS_EXP1(os); }\n'
    out=preprocess(mp);pre=out is not None
    if pre:
        dev='\\"development\\":true'
        assert 'development'not in out and '"1e-63"'in out,'the default mp256 build prints no development field'
        o2=preprocess(mp,['-DC8_MP256_RATIO=1e-60']);assert dev in o2 and '\\"overrides\\":[\\"C8_MP256_RATIO\\"]'in o2 and '"1e-60"'in o2,o2[-800:]
        o3=preprocess(mp,['-DC8_MP256_RATIO=1e-63']);assert dev in o3,'an override to the default value is still a development build'
        p1=preprocess(e1);seg=p1[p1.index('void probe'):];assert 'development'not in seg and '<< 5000'in seg,seg
        p2=preprocess(e1,['-DC8_EXP1_RANGE=4000']);seg=p2[p2.index('void probe'):];assert dev in seg and '\\"overrides\\":[\\"C8_EXP1_RANGE\\"]'in seg and '<< 4000'in seg,seg
        # the profile's default text is the gate build's: tokens of params() / the macro without the override equal
        # the commit the gate built (5569c53), when the checkout has it
        have=(ROOT/'.git').exists()and subprocess.run(['git','-C',str(ROOT),'cat-file','-e','5569c53:src/numerics/mp256.hpp'],capture_output=True).returncode==0
        if have:
            import tempfile as tf
            with tf.TemporaryDirectory()as d:
                for f in ('mp256.hpp','exp1.hpp'):
                    (Path(d)/f).write_text(subprocess.run(['git','-C',str(ROOT),'show',f'5569c53:src/numerics/{f}'],capture_output=True,text=True,check=True).stdout)
                assert tokens(preprocess(mp.replace(str(nx),d)))==tokens(out),'mp256.hpp without the override no longer preprocesses to the gate build'
                assert tokens(preprocess(e1.replace(str(nx),d)))==tokens(p1),'exp1.hpp without the override no longer preprocesses to the gate build'
    # the Makefile hands the override to the build record; parameter_overrides finds exactly it
    for prof,extra in (('mp256','-DC8_MP256_RATIO=1e-60'),('exp1','-DC8_EXP1_RANGE=4000'),('dd','-DC8_DD_DEVELOPMENT -DC8_DD_RATIO=1e-21')):
        cp=G.dry('CXX=g++',f'NUMERICS={prof}',f'CPPFLAGS={extra}',targets=('gmp',));assert cp.returncode==0,cp.stderr[-500:]
        cmd=G.records(cp.stdout)[f'bin/c8d2_gmp_{prof}'];assert BR.parameter_overrides(BR.compiler_options(cmd))==extra.split(),(prof,cmd)
        cp=G.dry('CXX=g++',f'NUMERICS={prof}',targets=('gmp',));assert BR.parameter_overrides(BR.compiler_options(G.records(cp.stdout)[f'bin/c8d2_gmp_{prof}']))==[]
    cp=G.dry('CXX=g++');rec=G.records(cp.stdout);assert rec and all(BR.parameter_overrides(BR.compiler_options(c))==[]for c in rec.values()),rec
    cp=G.dry('CXX=g++',targets=('profile','ratiohist'));rec=G.records(cp.stdout)
    assert {BR.diagnostic_kind(BR.compiler_options(c))for c in rec.values()}=={'tier_timers','ratio_histogram'}and all(BR.parameter_overrides(BR.compiler_options(c))==[]for c in rec.values())
    po=BR.parameter_overrides
    assert po(['g++','-D','C8_EXP1_RANGE=1','-UC8_MP256_RATIO','-DC8_NX_XS_Q(e)=e','-DNDEBUG','-DC8_USE_GMP','-DC8_NUMERICS_DD','-DC8_NO_TAIL_FIELDS'])==['-DC8_EXP1_RANGE=1','-UC8_MP256_RATIO','-DC8_NX_XS_Q(e)=e']
    ok('overrides_mark_development_builds',preprocessed=pre)

def test_f2_seeds():
    import seeds as SL
    import numerics_flags as NF
    with tempfile.TemporaryDirectory(prefix='c8d2_nf_')as td:
        td=Path(td);x=fakes(td);log=td/'seeds.json';SL.add(log,1,'initial entry')
        cp,r=flags(td,'s1','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F2','--seeds-log',log);assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        want=NF.f2_seed_entries(820262401);doc=json.loads(log.read_text())
        assert len(want)==49 and len({v for v,_ in want})==49 and r['f2_seeds']['added']==49 and r['f2_seeds']['present']==0
        assert [(e['seed'],e['source'])for e in doc['seeds'][1:]]==want and want[0][0]==820262401
        g=r['F2'];nat={k:v for k,v in json.loads((td/'s1/f2/f2.json').read_text())['native_seeds'].items()}
        assert all((v,f'J-FLAG F2 native seed {k} of base 820262401 (tests/numerics_flags.py)')in want for k,v in nat.items())and nat
        # a rerun of the same F2 campaign (the gates pair every profile on one base seed) adds nothing
        cp,r=flags(td,'s2','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F2',env={'C8_SEEDS':str(log)});assert cp.returncode==0
        assert r['f2_seeds']['added']==0 and r['f2_seeds']['present']==49 and len(json.loads(log.read_text())['seeds'])==50
        # a seed logged under another source, a missing log and no log: refused before any output, the log unchanged
        other=NF.f2_seed_entries(5);SL.add(log,other[7][0],'a production campaign');before=log.read_bytes()
        cp,_=flags(td,'s3','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F2','--seed',5,'--seeds-log',log)
        assert cp.returncode and 'collide'in cp.stderr and 'a production campaign'in cp.stderr and not (td/'s3').exists()and log.read_bytes()==before,cp.stderr[-500:]
        cp,_=flags(td,'s4','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F2','--seeds-log',td/'none.json');assert cp.returncode and 'does not exist'in cp.stderr and not (td/'s4').exists()
        cp,_=flags(td,'s5','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F2',seeds=False);assert cp.returncode and 'C8_SEEDS'in cp.stderr and not (td/'s5').exists()
        # F4 alone runs no campaign and needs no log
        cp,r=flags(td,'s6','--self-test','--exact',x['c8d2_gmp'],*SMALL,'--parts','F4');assert cp.returncode==0 and 'f2_seeds'not in r
    ok('f2_seeds_registered_rerun_present_collision_refused',entries=49)

# ---------------------------------------------------------------- Stage-6 fix round 1: X1 coverage, X2 binding, X3 teams
GATE570210=ROOT/'benchmarks/symmetry_2026-10-c8/stage5/close/clflag.570210.0/jflag_dd+mp256'

def synthetic_baseline(dbl=0,quad=6000,mp=600)->dict:
    """An F1 baseline document of the prescribed sample (f1_ids graphs, contiguous ranges, 2^dbl doublings) whose stats
    give `quad` binary128-accepted and `mp` MP points per (sector, L), need_met consistent with them."""
    import numerics_flags as NF
    B={'schema':NF.BASELINE_SCHEMA,'exact':{'sha256':'0'*64},'scale':1.0,'sample':{str(L):{'heaviest':h,'random':r,'points':n}for L,(h,r,n)in NF.F1_SAMPLE.items()},
       'need':{'binary128_accepted':NF.F1_NEED[0],'mp_promoted':NF.F1_NEED[1]},'sectors':{}}
    for s in NF.SECTORS:
        byL={}
        for L,(h,r,n)in NF.F1_SAMPLE.items():
            ids=NF.f1_ids(s,L,h,r);ppg=n<<dbl;pts=len(ids)*ppg
            byL[str(L)]={'graphs':ids,'points_per_graph':ppg,'ranges':[{'begin':0,'end':n}]+[{'begin':n<<i,'end':n<<(i+1)}for i in range(dbl)],
                         'stats':{'points':pts,'level':[pts-quad-mp,quad,mp]}}
        B['sectors'][s]={'doublings':dbl,'binary128_accepted':2*quad,'mp_promoted':2*mp,'need_met':2*quad>=NF.F1_NEED[0]and 2*mp>=NF.F1_NEED[1],'by_L':byL}
    return B

def profile_points(B:dict,cut:tuple|None=None)->dict:
    """f1_profile's {sector: {L: {'profile': {'points'}}}} evaluating every baseline point (cut = (sector, L): one short)."""
    return {s:{L:{'profile':{'points':x['stats']['points']-(1 if cut==(s,L)else 0)}}for L,x in sb['by_L'].items()}for s,sb in B['sectors'].items()}

def gate_evidence(rec:dict,cov:dict,snap:str='5'*64)->dict:
    """rec (a gate record) with the evidence check_gate requires since fix round 1: F1.coverage (X1), the build binding of
    both executables to one snapshot and of the F1 tools (X2), F5.team_sizes_verified (X3)."""
    ex,pr=rec['exact']['sha256'],rec['profile']['sha256']
    b=lambda sha:{'sha256':sha,'reproduced_sha256':sha,'reproduced':True,'snapshot_sha256':snap}
    rec['F1'].update(coverage=cov,tool_snapshot_sha256=snap,baseline_binding=b(ex))
    rec['build_binding']={'schema':'c8-d2-build-binding-1','snapshot':{'sha256':snap,'files':{}},'executables':{'exact':b(ex),'profile':b(pr)}}
    rec.setdefault('F5',{})['team_sizes_verified']=True;return rec

def gate_libraries(rec:dict)->dict:
    """rec with the libgmp provenance check_gate requires since fix round 3 (Z19 downstream): the profile's F1 tool and
    the fresh baseline's exact tool each matched to its executable's recorded libgmp (both build records name it)."""
    lib=lambda w:{'tool':{'sha256':w},'worker_now':{'sha256':w},'want_sha256':w,'match':True}
    we=rec['exact']['build_record']['gmp_library']['sha256'];wp=rec['profile']['build_record']['gmp_library']['sha256']
    rec['F1']['tool_gmp_library']=lib(wp);rec['f1_baseline'].update(reused=False,reused_gmp_library=None,tool_gmp_library=lib(we));return rec

def pkg_inputs()->str:return hashlib.sha256((ROOT/'inputs/manifest.json').read_bytes()).hexdigest()

def gate_inputs(rec:dict,manifest:str|None=None)->dict:
    """rec with the authenticated input set check_gate requires since fix round 4 (W18): numerics_flags.input_identity's
    block for the inputs manifest `manifest` (default the package's own), verified at the start and at the end, complete,
    and the F1 baseline made from the same manifest."""
    m=manifest or pkg_inputs()
    rec['inputs']={'schema':'c8-d2-gate-inputs-1','folder':'inputs','manifest_sha256':m,'verified':True,'verified_at_end':True,'skipped':[],'complete':True}
    rec.setdefault('f1_baseline',{})['inputs_manifest_sha256']=m;return rec

def test_coverage():
    """X1 (S6A-01, S6D-01): f1_coverage requires both sectors, the prescribed L7/L8 graphs and points, the promotion
    quotas and every baseline point evaluated by the profile; --sectors is a development option; job 570210's own
    baseline and F1 pass have the full coverage, but its record carries none of the fix round's evidence, so the new
    check_gate refuses it (no F1 coverage, no build binding, no F5 team sizes and, since fix round 3, no libgmp
    provenance of the F1 tools: exactly these reasons, so the integrator re-runs the gate); the same record with the evidence added is accepted, and every X1/X2/X3 field
    removed or wrong is refused by its message. design.GATE_F1_SAMPLE / GATE_F1_NEED equal numerics_flags'."""
    import numerics_flags as NF
    import design as Dz
    assert Dz.GATE_F1_SAMPLE=={str(L):(h+r,n)for L,(h,r,n)in NF.F1_SAMPLE.items()}and Dz.GATE_F1_NEED==NF.F1_NEED and Dz.BINDING_SCHEMA==NF.BINDING_SCHEMA
    B=synthetic_baseline();c=NF.f1_coverage(B,profile_points(B))
    assert c['complete']and c['profile_checked']and c['sectors']['free']['binary128_accepted']==12000 and c['sectors']['power']['by_L']['8']=={'graphs':400,'points_per_graph':64,'points_baseline':25600,'points_profile':25600},c
    assert NF.f1_coverage(B)['complete']and not NF.f1_coverage(B)['profile_checked']
    B1=synthetic_baseline(dbl=1);assert NF.f1_coverage(B1,profile_points(B1))['complete']
    def bad(name,B,res=None,needle=''):
        c=NF.f1_coverage(B,res if res is not None else profile_points(B))
        assert not c['complete']and any(needle in w for w in c['why']),(name,c['why'])
    import copy
    x=copy.deepcopy(B);del x['sectors']['power'];bad('omitted sector',x,needle='sectors')
    bad('unmet MP quota',synthetic_baseline(mp=100),needle='below the need')
    bad('unmet binary128 quota',synthetic_baseline(quad=4000),needle='below the need')
    x=synthetic_baseline(mp=100);x['sectors']['free']['need_met']=True;bad('need_met claimed',x,needle='need_met')
    x=copy.deepcopy(B);x['sectors']['free']['by_L']['8']['graphs'][0]+=10**6;bad('another graph',x,needle='prescribed')
    x=copy.deepcopy(B);x['sectors']['power']['by_L']['7']['graphs'].pop();bad('a graph fewer',x,needle='prescribed')
    x=copy.deepcopy(B);x['sectors']['free']['by_L']['7']['ranges']=[{'begin':0,'end':128}];bad('a range gap',x,needle='do not cover')
    x=copy.deepcopy(B);x['scale']=.5;bad('scale',x,needle='scale')
    x=copy.deepcopy(B);x['sample']['8']['points']=32;bad('sample',x,needle='sample')
    x=copy.deepcopy(B);del x['sectors']['free']['by_L']['8'];bad('a loop missing',x,needle='not in the baseline')
    bad('a profile point short',B,profile_points(B,('power','8')),needle='the profile evaluated')
    # job 570210 (the dd+mp256 gate): its baseline and F1 pass have the full coverage ...
    G=GATE570210;B0=json.loads((G/'f1_baseline/baseline.json').read_text());f1=json.loads((G/'f1/f1.json').read_text())
    c0=NF.f1_coverage(B0,f1['by_sector_L']);assert c0['complete'],c0['why']
    assert {s:(x['binary128_accepted'],x['mp_promoted'])for s,x in c0['sectors'].items()}=={'free':(29284,3541),'power':(50625,12568)}
    # ... but the record lacks the fix round's evidence: check_gate refuses it for exactly these three reasons
    inv=json.loads((ROOT/'inputs/inventory.json').read_text())
    try:Dz.check_gate(G/'numerics_flags.json','dd+mp256',inv);raise AssertionError('check_gate accepted the 570210 record')
    except ValueError as e:
        why=str(e).split('production build of dd+mp256: ',1)[1].split('; ')
        # X1, X2, (fix round 3, Z19 downstream) the libgmp provenance of both F1 tools and the reuse flag, (fix round 4,
        # W18) the input-set identity, X3
        assert len(why)==7 and why[0].startswith('no F1 coverage record')and why[1].startswith('no build binding')and why[2].startswith("the profile's F1 tool is not shown")\
            and why[3].startswith("the F1 baseline's exact tool is not shown")and why[4].startswith('f1_baseline does not say whether')\
            and why[5].startswith('no authenticated input-set identity')and why[6].startswith('F5 records no verified OpenMP team sizes'),why
    with tempfile.TemporaryDirectory(prefix='c8d2_nfg_')as td:
        td=Path(td);rec0=gate_inputs(gate_libraries(gate_evidence(json.loads((G/'numerics_flags.json').read_text()),c0)))
        def gate(name,fn=None):
            x=copy.deepcopy(rec0)
            if fn:fn(x)
            p=td/f'clflag.99077{len(list(td.iterdir()))}.0/jflag_dd+mp256/numerics_flags.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(x));return p
        g=Dz.check_gate(gate('ok'),'dd+mp256',inv)
        assert g['F1_coverage']=={'free':{'binary128_accepted':29284,'mp_promoted':3541},'power':{'binary128_accepted':50625,'mp_promoted':12568}}
        assert g['source_snapshot_sha256']=='5'*64 and g['F5_team_sizes_verified']is True and g['profile_executable_sha256'].startswith('d5df32ac')and g['slurm_job']=='990770'
        assert g['gmp_library']['exact']==g['gmp_library']['profile']==rec0['exact']['build_record']['gmp_library']['sha256']and g['gmp_library']['f1_baseline_reused']is False
        assert g['inputs_manifest_sha256']==pkg_inputs()  # W18: preserved in the bundle's gate entry
        cv=lambda x:x['F1']['coverage']
        cases=[('no_coverage',lambda x:x['F1'].pop('coverage'),'no F1 coverage record'),
               ('omitted_sector',lambda x:cv(x)['sectors'].pop('power'),'not free and power'),
               ('unmet_quota',lambda x:cv(x)['sectors']['free'].update(mp_promoted=999,need_met=False),'not the need'),
               ('need_met_false',lambda x:cv(x)['sectors']['power'].update(need_met=False),'not the need'),
               ('incomplete',lambda x:cv(x).update(complete=False,why=['free: x']),'F1 coverage incomplete'),
               ('few_graphs',lambda x:cv(x)['sectors']['free']['by_L']['8'].update(graphs=399),'not 400 graphs'),
               ('few_points',lambda x:cv(x)['sectors']['power']['by_L']['7'].update(points_per_graph=128,points_baseline=25600,points_profile=25600),'not 200 graphs x >= 256'),
               ('profile_short',lambda x:cv(x)['sectors']['power']['by_L']['7'].update(points_profile=51199),'every point evaluated'),
               ('scale',lambda x:cv(x).update(scale=.5),'F1 coverage at scale'),
               ('baseline_only',lambda x:cv(x).update(profile_checked=False),'profile pass checked'),
               ('no_binding',lambda x:x.pop('build_binding'),'no build binding'),
               ('exact_unreproduced',lambda x:x['build_binding']['executables']['exact'].update(reproduced=False),'the exact executable'),
               ('profile_other',lambda x:x['build_binding']['executables']['profile'].update(reproduced_sha256='f'*64),'the profile executable'),
               ('other_snapshot',lambda x:x['build_binding']['executables']['profile'].update(snapshot_sha256='6'*64),'the profile executable'),
               ('tool_snapshot',lambda x:x['F1'].update(tool_snapshot_sha256='a'*64),'F1 tool of the profile'),
               ('baseline_unbound',lambda x:x['F1'].pop('baseline_binding'),"baseline's exact tool"),
               ('baseline_other',lambda x:x['F1']['baseline_binding'].update(sha256='f'*64),"baseline's exact tool"),
               ('baseline_snapshot',lambda x:x['F1']['baseline_binding'].update(snapshot_sha256='6'*64),'another source snapshot than the binding'),
               ('baseline_no_snapshot',lambda x:x['F1']['baseline_binding'].pop('snapshot_sha256'),'another source snapshot than the binding'),
               ('f5_team',lambda x:x['F5'].update(team_sizes_verified=False),'OpenMP team sizes'),
               ('f5_none',lambda x:x['F5'].pop('team_sizes_verified'),'OpenMP team sizes'),
               ('tool_lib',lambda x:x['F1'].pop('tool_gmp_library'),"the profile's F1 tool is not shown"),
               ('tool_lib_other',lambda x:x['F1']['tool_gmp_library'].update(want_sha256='9'*64),"the profile's F1 tool is not shown"),
               ('baseline_lib',lambda x:x['f1_baseline'].pop('tool_gmp_library'),"the F1 baseline's exact tool is not shown"),
               ('baseline_lib_now',lambda x:x['f1_baseline']['tool_gmp_library']['worker_now'].update(sha256='9'*64),"the F1 baseline's exact tool is not shown"),
               ('reused_unchecked',lambda x:x['f1_baseline'].update(reused=True),"the reused F1 baseline's libgmp is not checked"),
               ('reused_flag',lambda x:x['f1_baseline'].update(reused='no'),'f1_baseline does not say whether'),
               # W18 (fix round 4): the authenticated input set
               ('no_inputs',lambda x:x.pop('inputs'),'no authenticated input-set identity'),
               ('inputs_schema',lambda x:x['inputs'].update(schema='other'),'no authenticated input-set identity'),
               ('inputs_sha',lambda x:x['inputs'].update(manifest_sha256='F'*64),'no authenticated input-set identity'),
               ('inputs_other',lambda x:x['inputs'].update(manifest_sha256='7'*64),'not '+pkg_inputs()[:12]),
               ('inputs_unverified',lambda x:x['inputs'].update(verified=False),'not verified at the start and at the end'),
               ('inputs_changed_during_run',lambda x:x['inputs'].update(verified_at_end=False),'not verified at the start and at the end'),
               ('inputs_incomplete',lambda x:x['inputs'].update(complete=False,skipped=['packs/free_L8.pack']),'incomplete input set'),
               ('inputs_skipped',lambda x:x['inputs'].update(skipped=['packs/power_L8.pack']),'incomplete input set'),
               ('baseline_inputs',lambda x:x['f1_baseline'].update(inputs_manifest_sha256='7'*64),'the F1 baseline was made from inputs manifest'),
               ('baseline_no_inputs',lambda x:x['f1_baseline'].pop('inputs_manifest_sha256'),'the F1 baseline was made from inputs manifest')]
        for name,fn,needle in cases:
            try:Dz.check_gate(gate(name,fn),'dd+mp256',inv);raise AssertionError(f'check_gate accepted {name}')
            except ValueError as e:assert needle in str(e),(name,str(e)[-600:])
    # the re-run gate (job 570373, fix round 1): its baseline was made in the same run, from the binding's source
    # snapshot (X1-X3 hold), but it predates Y1's tool_gmp_library, so since fix round 3 (Z19 downstream) the current
    # check_gate refuses it for exactly the missing libgmp provenance of both F1 tools and of the baseline's reuse flag
    G1=ROOT/'benchmarks/symmetry_2026-10-c8/s6fix1/s1flag.570373.0/jflag_dd+mp256/numerics_flags.json';r1=json.loads(G1.read_text())
    assert r1['F1']['baseline_binding']['snapshot_sha256']==r1['build_binding']['snapshot']['sha256']
    assert not Dz.gate_f1_coverage(r1)and not Dz.gate_binding(r1)and r1['F5']['team_sizes_verified']is True
    try:Dz.check_gate(G1,'dd+mp256',inv);raise AssertionError('check_gate accepted the 570373 record (no libgmp provenance)')
    except ValueError as e:
        why=str(e).split('production build of dd+mp256: ',1)[1].split('; ')
        assert [w.split(' (')[0]for w in why]==["the profile's F1 tool is not shown to run with the profile executable's recorded libgmp",
                                                "the F1 baseline's exact tool is not shown to run with the exact executable's recorded libgmp",
                                                'f1_baseline does not say whether the baseline was reused','no authenticated input-set identity'],why
    # with the provenance a fix-round-3 gate run records added, the same record passes
    G1b=Path(tempfile.mkdtemp(prefix='c8d2_nfg1_'))/'s3flag.990771.0/jflag_dd+mp256/numerics_flags.json';G1b.parent.mkdir(parents=True)
    G1b.write_text(json.dumps(gate_inputs(gate_libraries(json.loads(G1.read_text())))));g1=Dz.check_gate(G1b,'dd+mp256',inv)
    assert g1['slurm_job']=='990771'and g1['source_snapshot_sha256']==r1['build_binding']['snapshot']['sha256'],g1
    shutil.rmtree(G1b.parents[2])
    # W18 (Stage-6 fix round 4, S6H4-01): job 570536's record (the fix-round-3 gate of the current dd+mp256 build) has every
    # earlier piece of evidence and is refused for exactly the missing input-set identity; with the identity of the
    # package's inputs added it passes, and it is refused for a pilot or plan on revised inputs: a changed kernel payload
    # (one pack's bytes) with the same graph counts and executables gives another inputs manifest
    G3=ROOT/'benchmarks/symmetry_2026-10-c8/s6fix3/s3flag.570536.0/jflag_dd+mp256/numerics_flags.json';r3=json.loads(G3.read_text())
    try:Dz.check_gate(G3,'dd+mp256',inv);raise AssertionError('check_gate accepted the 570536 record (no input-set identity)')
    except ValueError as e:
        why=str(e).split('production build of dd+mp256: ',1)[1].split('; ');assert [w.split(' (')[0]for w in why]==['no authenticated input-set identity'],why
    G3b=Path(tempfile.mkdtemp(prefix='c8d2_nfg3_'))/'s4flag.990772.0/jflag_dd+mp256/numerics_flags.json';G3b.parent.mkdir(parents=True)
    G3b.write_text(json.dumps(gate_inputs(r3)));g3=Dz.check_gate(G3b,'dd+mp256',inv)
    assert g3['inputs_manifest_sha256']==pkg_inputs()and g3['profile_executable_sha256']==r3['profile']['sha256']and g3['slurm_job']=='990772'
    assert Dz.check_gate(G3b,'dd+mp256',inv,pkg_inputs())['sha256']==g3['sha256']  # the explicit expectation, as freeze passes the pilot's
    man=json.loads((ROOT/'inputs/manifest.json').read_text());man['sha256']['packs/free_L7.pack']='0'*64  # revised payloads, same counts
    revised=hashlib.sha256((json.dumps(man,indent=1)+'\n').encode()).hexdigest();assert revised!=pkg_inputs()and man['counts']==json.loads((ROOT/'inputs/manifest.json').read_text())['counts']
    try:Dz.check_gate(G3b,'dd+mp256',inv,revised);raise AssertionError('check_gate accepted a gate of other inputs')
    except ValueError as e:assert f'the gate ran on inputs manifest {pkg_inputs()[:12]}..., not {revised[:12]}...'in str(e),str(e)
    shutil.rmtree(G3b.parents[2])
    # the re-run of fix round 4 on symmetry (job 570574, benchmarks/symmetry_2026-10-c8/s6fix4/; the same build a46f3060, a
    # fresh F1 baseline): its record carries the input set and passes as it is, for the package's inputs only, with the
    # same libgmp provenance as 570536's
    G4=ROOT/'benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json';r4=json.loads(G4.read_text())
    g4=Dz.check_gate(G4,'dd+mp256',inv);assert g4==Dz.check_gate(G4,'dd+mp256',inv,pkg_inputs())
    assert g4['slurm_job']=='570574'and g4['inputs_manifest_sha256']==pkg_inputs()==r4['f1_baseline']['inputs_manifest_sha256']and r4['f1_baseline']['reused']is False,g4
    assert g4['profile_executable_sha256']==r3['profile']['sha256']and g4['gmp_library']['profile']==r3['profile']['build_record']['gmp_library']['sha256'],g4
    try:Dz.check_gate(G4,'dd+mp256',inv,revised);raise AssertionError('check_gate accepted the 570574 record for other inputs')
    except ValueError as e:assert 'the gate ran on inputs manifest'in str(e),str(e)
    ok('X1_coverage_570210_refused_for_missing_evidence_only_gate_evidence_refusals_570373_refused_for_libgmp_provenance_only_570536_for_W18_only',
       refusals=len(cases)+15)

FAKE_LDD=r'''import json,os,sys
m=json.loads(os.environ.get('FAKE_LDD_MAP','{}'));f=os.path.realpath(sys.argv[-1]);lib=m.get(f,os.environ.get('FAKE_LDD_GMP'))
print('\tlinux-vdso.so.1 (0x00007ffc00000000)')
if lib:print(f'\tlibgmp.so.10 => {lib} (0x00007f0000000000)')
'''
def fake_ldd(td:Path)->tuple[Path,Path,Path]:
    """(directory holding a fake ldd, the fake libgmp it names by default (FAKE_LDD_GMP), another fake libgmp): Y1 tests
    put the directory first on PATH; FAKE_LDD_MAP {realpath of an executable: library} overrides per executable."""
    d=td/'fakeldd';d.mkdir();(d/'ldd').write_text(f'#!{PY}\n'+FAKE_LDD);(d/'ldd').chmod(0o755)
    lib=td/'libgmp.so.10';lib.write_bytes(b'fake libgmp 6.2.1\n');other=td/'other_libgmp.so.10';other.write_bytes(b'another libgmp\n')
    return d,lib,other

FAKE_CXX=r'''import hashlib,json,os,re,sys
a=sys.argv[1:];out=a[a.index('-o')+1];src=[w for w in a if w.endswith('.cpp')][0]
seen={};todo=[os.path.normpath(src)]
while todo:
    f=todo.pop()
    if f in seen:continue
    text=open(f,'rb').read();seen[f]=hashlib.sha256(text).hexdigest()
    todo+=[os.path.normpath(os.path.join(os.path.dirname(f),m.group(1).decode()))for m in re.finditer(rb'#include "([^"]+)"',text)]
opts=[w for i,w in enumerate(a)if w!='-o'and(i==0 or a[i-1]!='-o')and w!=src]
body=open(os.environ['FAKE_CXX_WORKER']).read()if src.endswith('c8d2_integrate.cpp')else'import sys\nsys.exit(0)\n'
h=hashlib.sha256(json.dumps([sorted(seen.items()),opts]).encode()).hexdigest()
open(out,'w').write(f'#!{sys.executable} -S\n'+body+f'\n# fake build {h}\n# closure {json.dumps(sorted(seen.items()))}\n');os.chmod(out,0o755)
'''

def test_binding():
    """X2 (S6A-02): a fake compiler (deterministic in the include closure of its source and its options) builds the fake
    workers. snapshot() copies src/ and tests/numerics_f1.cpp read-only; bind() accepts an executable its build
    record's command rebuilds byte for byte from the snapshot and refuses a stale one (built before src/kernel.hpp
    changed), a build record pinning another src/numerics file and a command that is not a Makefile build; the F1 tool
    is compiled from the snapshot (its closure is the snapshot's). numerics_flags.py itself refuses a stale profile
    executable and a reused baseline without a binding, or bound through another source snapshot, before anything is
    written, and records build_binding (both executables reproduced from one snapshot) for current ones."""
    import numerics_flags as NF
    with tempfile.TemporaryDirectory(prefix='c8d2_nfb_')as td:
        td=Path(td);cxx=td/'fakecxx';cxx.write_text(f'#!{PY}\n'+FAKE_CXX);cxx.chmod(0o755);(td/'bin').mkdir()
        ldd_dir,lib,other=fake_ldd(td);saved={k:os.environ.get(k)for k in('PATH','FAKE_LDD_GMP','FAKE_LDD_MAP')}
        os.environ.update(PATH=f'{ldd_dir}:{os.environ["PATH"]}',FAKE_LDD_GMP=str(lib));os.environ.pop('FAKE_LDD_MAP',None)
        libsha=hashlib.sha256(lib.read_bytes()).hexdigest()
        env={**os.environ,'FAKE_CXX_WORKER':str(ROOT/'tests/fake_worker.py')};os.environ['FAKE_CXX_WORKER']=env['FAKE_CXX_WORKER']
        def build(name,opts=(),cwd=ROOT,rec_extra=None):
            exe=td/'bin'/name;subprocess.run([str(cxx),'-O3',*opts,'src/c8d2_integrate.cpp','-o',str(exe)],cwd=cwd,check=True,env=env)
            (td/'bin'/(name+'.build.json')).write_text(json.dumps({'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
                                                                   'command':[str(cxx),'-O3',*opts,'src/c8d2_integrate.cpp','-o',f'bin/{name}'],
                                                                   'gmp_library':{'sha256':libsha},**(rec_extra or{})}))
            return exe
        exact=build('c8d2_gmp');dd=build('c8d2_gmp_dd',('-DC8_NUMERICS','-DC8_NUMERICS_DD'),
                                         rec_extra={'numerics_sources':{'files':{'src/numerics/dd.hpp':hashlib.sha256((ROOT/'src/numerics/dd.hpp').read_bytes()).hexdigest()}}})
        old=td/'old';(old/'tests').mkdir(parents=True);import shutil;shutil.copytree(ROOT/'src',old/'src');shutil.copy2(ROOT/'tests/numerics_f1.cpp',old/'tests')
        (old/'src/kernel.hpp').write_text((old/'src/kernel.hpp').read_text()+'\n// an older kernel\n')
        stale=build('c8d2_gmp_dd+mp256',('-DC8_NUMERICS','-DC8_NUMERICS_DD','-DC8_NUMERICS_MP256'),cwd=old)
        snap=td/'snap';info=NF.snapshot(snap)
        assert {'src/c8d2_integrate.cpp','src/kernel.hpp','src/quadfast.hpp','src/diagnostics.hpp','src/numerics/dd.hpp','tests/numerics_f1.cpp'}<=set(info['files'])
        assert all(info['files'][k]==hashlib.sha256((ROOT/k).read_bytes()).hexdigest()and not (snap/k).stat().st_mode&0o222 for k in info['files'])
        assert info==NF.snapshot(td/'snap2')
        b=NF.bind(exact,snap,info,td,'exact');assert b['reproduced']and b['reproduced_sha256']==b['sha256']==hashlib.sha256(exact.read_bytes()).hexdigest()and b['snapshot_sha256']==info['sha256']
        assert NF.bind(dd,snap,info,td,'profile')['reproduced']
        def refused(exe,needle):
            try:NF.bind(exe,snap,info,td,'x');raise AssertionError(f'bind accepted {exe.name}')
            except SystemExit as e:assert needle in str(e),str(e)
        refused(stale,'is stale')
        br=td/'bin/c8d2_gmp_dd.build.json';r0=br.read_text();rb=json.loads(r0)
        rb['numerics_sources']['files']['src/numerics/dd.hpp']='0'*64;br.write_text(json.dumps(rb));refused(dd,'pins src/numerics/dd.hpp')
        rb=json.loads(r0);rb['command'][rb['command'].index('src/c8d2_integrate.cpp')]=str(ROOT/'src/c8d2_integrate.cpp');br.write_text(json.dumps(rb));refused(dd,'unexpected build command')
        br.write_text(r0)
        cmd,glib=NF.compile_tool(dd,td/'tool',snap);assert cmd[cmd.index('-o')-1]=='tests/numerics_f1.cpp'
        clos=dict(json.loads((td/'tool').read_text().rsplit('# closure ',1)[1]));assert clos['src/kernel.hpp']==info['files']['src/kernel.hpp']and 'tests/numerics_f1.cpp'in clos
        assert glib['match']and glib['want_sha256']==libsha==glib['tool']['sha256']==glib['worker_now']['sha256']and glib['tool']['realpath']==str(lib.resolve()),glib
        # Y1: a tool or an executable resolving another libgmp, no ldd answer, and a record naming no libgmp are refused
        def lib_refused(what,needle,tool=None,exe=None,unset=False):
            m={str((tool or td/'tool').resolve()):str(other)}if tool is not None else({str(exe.resolve()):str(other)}if exe is not None else{})
            os.environ['FAKE_LDD_MAP']=json.dumps(m)
            if unset:os.environ.pop('FAKE_LDD_GMP')
            try:NF.compile_tool(dd,td/'tool',snap);raise AssertionError(f'compile_tool accepted {what}')
            except SystemExit as e:assert needle in str(e),(what,str(e))
            finally:os.environ.pop('FAKE_LDD_MAP',None);os.environ['FAKE_LDD_GMP']=str(lib)
        lib_refused('a tool resolving another libgmp','the tool tool resolves libgmp',tool=td/'tool')
        lib_refused('an executable resolving another libgmp here',f'the worker {dd.name} resolves libgmp',exe=dd)
        lib_refused('no ldd answer','(unresolved: no ldd, or no libgmp)',unset=True)
        rb=json.loads(br.read_text());rb.pop('gmp_library');br.write_text(json.dumps(rb))
        try:NF.compile_tool(dd,td/'tool',snap);raise AssertionError('compile_tool accepted a record without gmp_library')
        except SystemExit as e:assert 'names no libgmp sha256'in str(e),str(e)
        br.write_text(r0)
        # the harness: a stale profile executable and an unbound reused baseline are refused before any output
        cp,_=flags(td,'b_stale','--profile','dd+mp256','--profile-exe',stale,'--exact',exact,'--parts','F1','--f1-scale','0.01',env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER']})
        assert cp.returncode and 'is stale'in cp.stderr and not (td/'b_stale').exists(),cp.stderr[-800:]
        ob=td/'oldbase';ob.mkdir();(ob/'baseline.json').write_text(json.dumps({'schema':NF.BASELINE_SCHEMA,'exact':{'sha256':b['sha256']},'scale':1.0,'sectors':{}}))
        cp,_=flags(td,'b_old','--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-baseline',ob,env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER']})
        assert cp.returncode and 'no build binding'in cp.stderr and not (td/'b_old').exists(),cp.stderr[-800:]
        # fix-round-1 residual: a reused baseline bound to the exact executable, but whose exact tool was compiled from
        # another source snapshot (src/ or tests/numerics_f1.cpp changed since), is refused before any output; the same
        # baseline from this snapshot gets past the check (and fails later here: it has no sectors)
        good_lib={'match':True,'want_sha256':libsha,'tool':{'sha256':libsha},'worker_now':{'sha256':libsha}}  # Z19: the baseline's library evidence
        for name,ssha,refused_ in (('b_snap','6'*64,True),('b_snap_none',None,True),('b_snap_ok',info['sha256'],False)):
            bd=td/f'base_{name}';bd.mkdir()
            (bd/'baseline.json').write_text(json.dumps({'schema':NF.BASELINE_SCHEMA,'exact':{'sha256':b['sha256']},'scale':1.0,'sectors':{},
                                                         'binding':dict(b,snapshot_sha256=ssha),'tool_gmp_library':good_lib,'inputs':{'manifest_sha256':pkg_inputs()}}))
            cp,_=flags(td,name,'--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-baseline',bd,env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER']})
            hit='compiled from source snapshot'in cp.stderr
            assert cp.returncode and hit is refused_ and (td/name).exists()is not refused_,(name,cp.stderr[-800:])
        # Z19 (Stage-6 fix round 3, S6H3-01): a reused baseline bound to this snapshot must also name the exact
        # executable's libgmp (tool_gmp_library: match, want, tool and worker_now that sha256), and the exact executable
        # must resolve it here now; missing, mismatched and changed-runtime bindings are refused before any output
        othersha=hashlib.sha256(other.read_bytes()).hexdigest();z19=0
        for name,tl,extra_env,needle in (('b_lib_missing',None,{},'records no tool_gmp_library'),
                                         ('b_lib_other_tool',dict(good_lib,tool={'sha256':othersha}),{},'compute a fresh baseline (Z19)'),
                                         ('b_lib_other_want',dict(good_lib,want_sha256=othersha),{},'compute a fresh baseline (Z19)'),
                                         ('b_lib_no_match',dict(good_lib,match=False),{},'compute a fresh baseline (Z19)'),
                                         ('b_lib_runtime',good_lib,{'FAKE_LDD_MAP':json.dumps({str(exact.resolve()):str(other)})},'does not run with its recorded libgmp here')):
            bd=td/f'base_{name}';bd.mkdir();body={'schema':NF.BASELINE_SCHEMA,'exact':{'sha256':b['sha256']},'scale':1.0,'sectors':{},'binding':dict(b,snapshot_sha256=info['sha256'])}
            if tl is not None:body['tool_gmp_library']=tl
            (bd/'baseline.json').write_text(json.dumps(body))
            cp,_=flags(td,name,'--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-baseline',bd,env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER'],**extra_env})
            assert cp.returncode and needle in cp.stderr and not (td/name).exists(),(name,cp.stderr[-800:]);z19+=1
        # W18 (Stage-6 fix round 4): a reused baseline must have been made from this run's inputs manifest (its 450-digit
        # references describe those payloads); one without an input identity, or of another manifest, is refused before any output
        w18=0
        for name,inp in (('b_inputs_missing',None),('b_inputs_other',{'manifest_sha256':'7'*64}),('b_inputs_not_dict',pkg_inputs())):
            bd=td/f'base_{name}';bd.mkdir();body={'schema':NF.BASELINE_SCHEMA,'exact':{'sha256':b['sha256']},'scale':1.0,'sectors':{},
                                                   'binding':dict(b,snapshot_sha256=info['sha256']),'tool_gmp_library':good_lib}
            if inp is not None:body['inputs']=inp
            (bd/'baseline.json').write_text(json.dumps(body))
            cp,_=flags(td,name,'--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-baseline',bd,env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER']})
            assert cp.returncode and 'compute a fresh baseline (W18)'in cp.stderr and not (td/name).exists(),(name,cp.stderr[-800:]);w18+=1
        r_ok=json.loads((td/'b_snap_ok/numerics_flags.json').read_text())  # the accepted reuse records its library check
        assert r_ok['f1_baseline']['inputs_manifest_sha256']==r_ok['inputs']['manifest_sha256']==pkg_inputs()and r_ok['inputs']['verified_at_end']is True,r_ok.get('inputs')
        assert r_ok['f1_baseline']['reused_gmp_library']['want_sha256']==libsha==r_ok['f1_baseline']['reused_gmp_library']['exact_now']['sha256'],r_ok.get('f1_baseline')
        # Z19 downstream (integration): the record also says the baseline was reused and copies its tool_gmp_library (design.check_gate reads both)
        assert r_ok['f1_baseline']['reused']is True and r_ok['f1_baseline']['tool_gmp_library']==good_lib,r_ok.get('f1_baseline')
        # current executables: both reproduced from one snapshot and recorded (F1 then runs on, and fails here: the fake tool
        # computes nothing, and the Mac has no L8 pack)
        cp,r=flags(td,'b_ok','--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-scale','0.01',env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER']})
        bb=r['build_binding'];ex=bb['executables']
        assert bb['schema']=='c8-d2-build-binding-1'and bb['snapshot']['sha256']==info['sha256']and ex['exact']['sha256']==b['sha256']and ex['profile']['reproduced']
        assert ex['profile']['sha256']==r['profile']['sha256']and ex['exact']['snapshot_sha256']==ex['profile']['snapshot_sha256']==info['sha256']and r['status']=='failed'
        bl=json.loads((td/'b_ok/f1_baseline/baseline.json').read_text())if (td/'b_ok/f1_baseline/baseline.json').exists()else None
        assert bl is None or (bl['tool_gmp_library']['want_sha256']==libsha and bl['inputs']['manifest_sha256']==pkg_inputs()),bl
        assert r['inputs']['manifest_sha256']==pkg_inputs()and r['inputs']['verified']is True  # W18: recorded before anything was built
        # Y1 in the harness: an F1 tool resolving another libgmp stops the run before the tool evaluates a point
        cp,r=flags(td,'b_lib','--profile','dd','--profile-exe',dd,'--exact',exact,'--parts','F1','--f1-scale','0.01',
                    env={'FAKE_CXX_WORKER':env['FAKE_CXX_WORKER'],'FAKE_LDD_MAP':json.dumps({str(exact.resolve()):str(other)})})
        assert cp.returncode and "does not run with the worker's GMP"in cp.stderr and not (td/'b_lib/numerics_flags.json').exists(),cp.stderr[-800:]
        for k,v in saved.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
    os.environ.pop('FAKE_CXX_WORKER',None)
    ok('X2_snapshot_bind_reproduced_stale_pins_command_refused_tool_from_snapshot_harness_refusals_Y1_libgmp_Z19_reused_baseline_libgmp_W18_inputs',
       z19_refusals=z19,w18_refusals=w18)

FAKE_TEAM=r'''import json,os,sys,threading,time
a=sys.argv[1:];out=a[4];req=int(a[8]);lim=os.environ.get('OMP_THREAD_LIMIT')
team=min(req,int(lim))if lim else req
if os.environ.get('OMP_DYNAMIC','').lower()in('true','1'):team=max(1,team//2)
team=int(os.environ.get('C8_FAKE_TEAM',team));ev=threading.Event();ts=[threading.Thread(target=ev.wait)for _ in range(team-1)]
for t in ts:t.start()
time.sleep(float(os.environ.get('C8_FAKE_TEAM_SECONDS','0.4')))
open(out,'w').write(json.dumps({'order':8,'L':7,'rows':[],'team':team,'omp_thread_limit':lim,'omp_dynamic':os.environ.get('OMP_DYNAMIC')}))
ev.set()
for t in ts:t.join()
'''

def ps_threads(pid:int):
    """The thread count of a live process on macOS (one `ps -M` line per thread; the Linux harness reads /proc)."""
    cp=subprocess.run(['ps','-M','-p',str(pid)],capture_output=True,text=True)
    return len([l for l in cp.stdout.splitlines()[1:]if l.strip()])or None

def test_f5_team():
    """X3 (S6A-03): a fake worker that, like libgomp, shrinks its team under an inherited OMP_THREAD_LIMIT=1 or
    OMP_DYNAMIC=true (C8_FAKE_TEAM forces a team: a runtime ignoring the request). child_env removes every OMP_*, GOMP_*
    and KMP_* control and sets OMP_DYNAMIC=false; run_one and run_lanes observe the team (here with ps -M on macOS,
    /proc on Linux) and require the requested size: with the restrictive inherited environment the runs get their
    full teams; a team other than the request, and a team that cannot be observed, fail. f5_run passes only with
    every block's team_sizes_verified; F2/F4's run_native passes no inherited OMP_THREAD_LIMIT to the worker."""
    import thread_identity as TI
    import numerics_flags as NF
    from unittest import mock
    assert TI.child_env({'OMP_THREAD_LIMIT':'1','OMP_DYNAMIC':'true','OMP_NUM_THREADS':'2','GOMP_SPINCOUNT':'0','KMP_AFFINITY':'x','PATH':'/bin'})=={'PATH':'/bin','OMP_DYNAMIC':'false'}
    with tempfile.TemporaryDirectory(prefix='c8d2_nft_')as td:
        td=Path(td);w=td/'team_worker';w.write_text(f'#!{PY} -S\n'+FAKE_TEAM);w.chmod(0o755)
        cmd=lambda o,th:[w,'root','gamma','net','tasks',o,1,0,'.8',th,'compensated','-']
        native=Path('/proc/self/task').is_dir();count=TI.task_count if native else ps_threads
        if not native:  # no /proc: unobservable teams fail closed
            o=td/'u.json'
            try:TI.run_one(cmd(o,2),o,2);raise AssertionError('an unobservable team was accepted')
            except AssertionError as e:assert 'cannot be observed'in str(e),str(e)
        with mock.patch.object(TI,'task_count',count),mock.patch.dict(os.environ,{'OMP_THREAD_LIMIT':'1','OMP_DYNAMIC':'true'}):
            o=td/'a.json';d,team=TI.run_one(cmd(o,4),o,4,label='four')
            assert team==4 and d['team']==4 and d['omp_thread_limit']is None and d['omp_dynamic']=='false',(team,d)
            o=td/'one.json';d,team=TI.run_one(cmd(o,1),o,1);assert team==1
            docs,teams=TI.run_lanes([(cmd(td/f'l{i}.json',3),td/f'l{i}.json',None)for i in range(3)],3);assert teams==[3,3,3]and [x['team']for x in docs]==[3,3,3]
            with mock.patch.dict(os.environ,{'C8_FAKE_TEAM':'1'}):
                try:TI.run_one(cmd(o,4),o,4,label='forced');raise AssertionError('a 1-thread team accepted for 4 requested threads')
                except AssertionError as e:assert '4 threads requested, the run had 1'in str(e),str(e)
            with mock.patch.dict(os.environ,{'C8_FAKE_TEAM':'2'}):
                try:TI.run_lanes([(cmd(td/f'm{i}.json',3),td/f'm{i}.json',None)for i in range(2)],3);raise AssertionError('lanes of 2 threads accepted for 3')
                except AssertionError as e:assert '3 threads requested, the run had 2'in str(e),str(e)
            # F2/F4's worker environment: no inherited OMP_THREAD_LIMIT, OMP_DYNAMIC false
            n,_=NF.run_native(w,'root',td/'net',td/'tasks',td/'rn.json',1,'.8',2,[0,1],False,td/'rn.log',7)
            assert n['omp_thread_limit']is None and n['omp_dynamic']=='FALSE'and n['team']==2,n
        # F5's verdict needs every block's team_sizes_verified
        a=argparse.Namespace(f5_threads=[1,8],f5_lanes=2,f5_lane_threads=4)
        blk=lambda s,v:{'sector':s,'identical':True,'team_sizes_verified':v,'runs':{'threads_1':{'team_observed':1},'lanes_2x4':{'teams_observed':[4,4]}}}
        for v,want in ((True,True),(False,False)):
            with mock.patch.object(TI,'block',lambda td_,b,s,*x,**k:blk(s,v)):r=NF.f5_run(a,w,td/f'f5_{v}',td)
            assert r['passed']is want and r['team_sizes_verified']is want and r['teams']['free']=={'threads_1':1,'lanes_2x4':[4,4]},r
    ok('X3_sanitized_omp_environment_observed_teams_required_f5_verdict_run_native_env',observed_with='/proc'if native else'ps -M')

def test_macro_overrides():
    """Z3 (Stage-6 fix round 3, S6A3-03), the build-record side: parameter_overrides (also what production.py recomputes
    from a record's compiler_options) names a source switch (-DNO_SUM_SHARING), -D words inside -Wp,..., every
    -include, -imacros, -Xpreprocessor option and response file, and nothing for the Makefile's own commands;
    macro_overrides reads the compiler's own -dM -E probe of the options: the host compiler shows a C8_NX_* hook, a
    source switch or a build macro set through -include, -imacros, -Wp,-D or @FILE, and a build macro given as a plain
    -D word is no override. build_record.main records macro_overrides with "development": true, gmp_target refuses that
    worker, accepts the same command without the injection, and refuses a record without macro_overrides."""
    import contextlib,shutil
    import build_record as BR
    po=BR.parameter_overrides
    assert po(['g++','-O3','-DNO_SUM_SHARING','-DC8_USE_GMP'])==['-DNO_SUM_SHARING']
    assert po(['g++','-Wp,-DC8_NX_XS_Q(e)=e,-DFOO,-UNO_SUM_SHARING','-Wp,-MD,x.d'])==['-Wp,-DC8_NX_XS_Q(e)=e','-Wp,-UNO_SUM_SHARING']
    assert po(['g++','-include','x.h','-imacros','y.h','@opts.rsp','-Xpreprocessor','-DC8_X'])==['-include x.h','-imacros y.h','@opts.rsp','-Xpreprocessor -DC8_X']
    assert po(['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','-DC8_USE_GMP','-DC8_NUMERICS','-DC8_NUMERICS_DD','-DC8_TIER_TIMERS','-I/x'])==[]
    probe='#define __VERSION__ "x"\n#define C8_USE_GMP 1\n#define C8_NX_XS_Q(e) e\n#define NO_SUM_SHARING 1\n#define C8_TIER_TIMERS 1\n#define C8_NUMERICS 1\n'
    assert BR.macro_overrides(['g++','-DC8_USE_GMP','-D','C8_NUMERICS'],probe)==['C8_NX_XS_Q','C8_TIER_TIMERS','NO_SUM_SHARING']and BR.macro_overrides(['g++'],None)is None
    cxx=next((x for x in (os.environ.get('CXX'),'c++','clang++','g++')if x and shutil.which(x)),None);vectors=0
    with tempfile.TemporaryDirectory(prefix='c8d2_mo_')as td:
        td=Path(td);hdr=td/'inject.h';hdr.write_text('#define C8_NX_XS_Q(e) (e)\n#define C8_USE_GMP 1\n');rsp=td/'inject.rsp';rsp.write_text('-DNO_SUM_SHARING\n')
        if cxx is not None:
            for words,want in ((['-include',str(hdr)],['C8_NX_XS_Q','C8_USE_GMP']),(['-imacros',str(hdr)],['C8_NX_XS_Q','C8_USE_GMP']),
                               (['-Wp,-DC8_NX_DESCRIBE(os)='],['C8_NX_DESCRIBE']),([f'@{rsp}'],['NO_SUM_SHARING']),(['-DC8_USE_GMP','-DC8_ORDER_TRACE'],[])):
                opts=[cxx,'-std=c++17',*words];got=BR.macro_overrides(opts,BR.toolchain(opts,'decimal')['base']);vectors+=1
                assert got==want,(words,got)
            exe=td/'c8d2_decimal';exe.write_text('#!/bin/sh\necho {}\n');exe.chmod(0o755)
            with contextlib.redirect_stderr(open(os.devnull,'w')):
                rec=BR.main(exe,'decimal',[cxx,'-O3','-std=c++17','-include',str(hdr),'src/c8d2_integrate.cpp','-o',str(exe)])
            assert rec['macro_overrides']==['C8_NX_XS_Q','C8_USE_GMP']and rec['development']is True and rec['parameter_overrides']==[f'-include {hdr}'],rec
            try:BR.gmp_target(exe,'decimal');raise AssertionError('gmp_target accepted a worker with injected macros')
            except BR.BindingRefused as e:assert 'development build'in str(e),str(e)
            with contextlib.redirect_stderr(open(os.devnull,'w')):rec=BR.main(exe,'decimal',[cxx,'-O3','-std=c++17','src/c8d2_integrate.cpp','-o',str(exe)])
            assert rec['macro_overrides']==[]and rec['development']is False and BR.gmp_target(exe,'decimal')['worker_sha256']==rec['executable_sha256']
            br=exe.with_name(exe.name+'.build.json');r=json.loads(br.read_text());r.pop('macro_overrides');br.write_text(json.dumps(r))
            try:BR.gmp_target(exe,'decimal');raise AssertionError('gmp_target accepted a record without macro_overrides')
            except BR.BindingRefused as e:assert 'does not show the macros in effect'in str(e),str(e)
    ok('Z3_build_record_macro_overrides_any_vector_development',host_compiler=cxx,vectors=vectors)


# ---------------------------------------------------------------- Stage-6 fix round 4: W18 input identity, W20 seed transaction
def link_pack(src:Path,dst:Path)->None:
    """A pack in a test's copy of inputs/: a hard link (no 7.5 GB copy of the L8 packs), else, where the copy lies on
    another file system (a cluster export on BeeGFS, the copy on node-local /tmp: EXDEV, found by J-VAL-1 on symmetry,
    job 570573), a symbolic link to the pack (prepare_inputs.verify follows it and hashes the bytes)."""
    try:os.link(src,dst)
    except OSError:os.symlink(Path(src).resolve(),dst)

def test_w18_inputs():
    """W18 (S6H4-01): numerics_flags.input_identity is the sha256 of the inputs manifest bytes with every listed input,
    pack and vendored pin hashed against it (tools/prepare_inputs.py verify); a missing L8 pack is recorded (skipped,
    complete false: check_gate refuses it); a changed input stops the run before anything is written; inputs_unchanged
    fails the record when the input set at the end is not the one at the start. A self-test run records the identity,
    verified at the end. (check_gate's side: test_coverage; the reused baseline's: test_binding.)"""
    import numerics_flags as NF
    import prepare_inputs as PI
    x=NF.input_identity();man=json.loads((ROOT/'inputs/manifest.json').read_text())
    l8=[n for n in PI.L8_PACKS if not (ROOT/'inputs'/n).is_file()]
    assert x['schema']=='c8-d2-gate-inputs-1'and x['manifest_sha256']==pkg_inputs()and x['verified']is True and x['skipped']==l8 and x['complete']is(not l8)
    assert x['files']==man['sha256']and x['vendored_assembly_handoff_sha256']==man['vendored_assembly']['handoff_sha256']and x['vendored_assembly_files']==man['vendored_assembly']['files']
    with tempfile.TemporaryDirectory(prefix='c8d2_nfi_')as td:
        td=Path(td);real=NF.ROOT
        for f in (ROOT/'inputs').rglob('*'):
            if f.is_file():
                d=td/'inputs'/f.relative_to(ROOT/'inputs');d.parent.mkdir(parents=True,exist_ok=True)
                if f.suffix=='.pack':link_pack(f,d)
                else:shutil.copy2(f,d)
        try:
            NF.ROOT=td;y=NF.input_identity();assert y['manifest_sha256']==x['manifest_sha256']  # an identical copy: the same identity
            g=td/'inputs/gamma_d2_8.txt';g.write_text(g.read_text().replace('1','2',1))  # one changed input
            try:NF.input_identity();raise AssertionError('input_identity accepted a changed gamma table')
            except SystemExit as e:assert 'do not verify against inputs/manifest.json'in str(e)and 'gamma_d2_8.txt'in str(e),str(e)
            shutil.copy2(ROOT/'inputs/gamma_d2_8.txt',g);(td/'inputs/two_loop.json').write_text('{}')
            try:NF.input_identity();raise AssertionError('input_identity accepted a changed two-loop file')
            except SystemExit as e:assert 'two_loop.json'in str(e),str(e)
        finally:NF.ROOT=real
    orig=NF.input_identity
    try:
        NF.input_identity=lambda:dict(x,manifest_sha256='7'*64);u=NF.inputs_unchanged(x);assert u['unchanged']is False and '777777777777'in u['why'],u
        def gone():raise SystemExit('the gate\'s inputs do not verify (test)')
        NF.input_identity=gone;u=NF.inputs_unchanged(x);assert u['unchanged']is False and 'do not verify'in u['why'],u
        NF.input_identity=lambda:dict(x);assert NF.inputs_unchanged(x)=={'unchanged':True,'why':None}
    finally:NF.input_identity=orig
    with tempfile.TemporaryDirectory(prefix='c8d2_nf_')as td:
        td=Path(td);f=fakes(td)
        cp,r=flags(td,'w18','--self-test','--exact',f['c8d2_gmp'],*SMALL,'--parts','F2');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        assert r['inputs']['manifest_sha256']==pkg_inputs()and r['inputs']['verified_at_end']is True and 'inputs_unchanged'not in r['verdicts'],r['inputs']
    ok('W18_input_identity_verified_changed_input_refused_end_check_recorded',manifest=pkg_inputs()[:12],skipped=l8)

def test_w20_seeds():
    """W20 (S6H4-03): register_f2_seeds reads, checks and appends in ONE transaction under the seed log's lock. The
    interleaving regression: right after F2 reads the log (a hook on seeds.read_log, at the point where the read used to
    be unlocked), a production plan registers F2's base seed (production.register_seed, in a thread). Before the fix the
    plan's registration landed between F2's check and its appends: both succeeded and the log held the base seed under
    two sources. Now the plan waits for the lock, finds the seed F2 registered and is refused; F2 holds every one of its
    49 seeds, alone. Also: a seed logged first by a plan is refused (and nothing written), a derived C8 group seed of a
    logged campaign is refused, a rerun under the identical labels is 'present', and a missing log is refused."""
    import threading
    from unittest import mock
    import seeds as SL
    import production as prod
    import numerics_flags as NF
    with tempfile.TemporaryDirectory(prefix='c8d2_nfs_')as td:
        td=Path(td);log=td/'seeds.json';SL.init(log);base=777000123;entries=NF.f2_seed_entries(base);real=SL.read_log;st={}
        def plan():
            try:st['plan']=prod.register_seed(log,base,td/'campaign_X',{},lambda:None)
            except ValueError as e:st['plan_refused']=str(e)
        def hook(path,legacy=False):
            doc=real(path,legacy)
            if threading.current_thread()is threading.main_thread()and 'thread'not in st:
                th=threading.Thread(target=plan);st['thread']=th;th.start();th.join(3.0)  # the plan runs now, or waits for F2's lock
            return doc
        with mock.patch.object(SL,'read_log',hook):
            try:r=NF.register_f2_seeds(log,base);st['f2']=r
            except SystemExit as e:st['f2_refused']=str(e)
        st['thread'].join(60)
        doc=real(log);srcs=[e['source']for e in doc['seeds']if e['seed']==base]
        assert 'f2'in st and st['f2']['added']==49 and 'plan_refused'in st and 'plan'not in st,{k:v for k,v in st.items()if k!='thread'}
        assert srcs==[entries[0][1]]and [(e['seed'],e['source'])for e in doc['seeds']]==entries,srcs
        assert 'is a forbidden seed'in st['plan_refused']and "re-checked under the seed log's lock"in st['plan_refused'],st['plan_refused']
        # the other order: a plan registered first; F2 is refused, the log unchanged
        log2=td/'seeds2.json';SL.init(log2);prod.register_seed(log2,base,td/'campaign_Y',{},lambda:None);before=log2.read_bytes()
        try:NF.register_f2_seeds(log2,base);raise AssertionError('F2 accepted a base seed a plan registered first')
        except SystemExit as e:assert 'collide'in str(e)and 'campaign_Y'in str(e),str(e)
        assert log2.read_bytes()==before
        # a derived C8 group seed of a logged campaign (production.derive_seeds) is a stream of that campaign
        g=prod.derive_seeds(424242,'b','power',8)['native'];log3=td/'seeds3.json';SL.init(log3);SL.add(log3,424242,'a production campaign')
        with mock.patch.object(NF,'f2_seed_entries',lambda s:[(s,'J-FLAG F2 base seed test'),(g,'J-FLAG F2 native seed test')]):
            try:NF.register_f2_seeds(log3,5);raise AssertionError('F2 accepted a derived group seed of a logged campaign')
            except SystemExit as e:assert f'{g} (J-FLAG F2 native seed test): equals the native seed of b_power_L8 of 424242'in str(e),str(e)
        assert len(real(log3)['seeds'])==1
        # a rerun under the identical labels: present, nothing added; a missing log: refused
        r2=NF.register_f2_seeds(log,base);assert r2['added']==0 and r2['present']==49 and len(real(log)['seeds'])==49
        try:NF.register_f2_seeds(td/'none.json',base);raise AssertionError('accepted a missing log')
        except SystemExit as e:assert 'does not exist'in str(e)
    ok('W20_f2_seeds_one_locked_transaction_interleaved_plan_refused_derived_seed_refused')

TESTS=(('make_profiles',test_make_profiles),('hooks',test_hooks),('pure',test_pure),('f2_self',test_f2_self),('f2_profile',test_f2_profile),('scripts',test_scripts),
       ('overrides',test_overrides),('f2_seeds',test_f2_seeds),('coverage',test_coverage),('binding',test_binding),('f5_team',test_f5_team),
       ('macro_overrides',test_macro_overrides),('w18_inputs',test_w18_inputs),('w20_seeds',test_w20_seeds))
def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only')
    a=ap.parse_args();names=[n for n,_ in TESTS]
    sel=names if a.only is None else[s.strip()for s in a.only.split(',')if s.strip()]
    bad=[s for s in sel if s not in names]
    if not sel or bad:ap.error(f'--only: unknown test(s) {bad}; the tests are {", ".join(names)}'if bad else'--only: no test named')
    failed=[]
    for n,fn in TESTS:
        if n not in sel:continue
        try:fn()
        except Exception as e:
            import traceback;traceback.print_exc();failed.append(n);RESULTS.append({'test':n,'status':'failed','error':f'{type(e).__name__}: {e}'})
    rec={'passed':not failed,'tests':len(RESULTS),'failed':failed,'requested':sel,'results':RESULTS}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({k:rec[k]for k in ('passed','tests','failed')}));return 0 if not failed else 1

if __name__=='__main__':sys.exit(main())
