#!/usr/bin/env python3
"""Y1 (Stage-6 fix round 2, S6A2-01): the precision tools are bound to the GMP of the worker they speak for. Mac-runnable:
a fake compiler (its --version line, the -dM -E probes with a real include search for gmp.h over -I and a fake system
include directory, and compile-and-link that writes a stub recording its words) and a fake ldd (DT_RPATH first: a
-Wl,-rpath,<dir> holding libgmp.so.10 wins, else the fake system libgmp; FAKE_LDD_MAP overrides one executable). The
worker records are written by tools/build_record.py main itself from the Makefile's command, as make does.

  cxx_layout     common.cxx_command: without gmp_prefix the command is unchanged word for word; with it, the GMP words
                 sit where the Makefile's GMP_COMPILE and GMP_LINK put them (equal to `make -n -B bin/c8d2_gmp
                 GMP_PREFIX=...`, with and without the user hooks); a relative prefix or one with a space is refused
  target         build_record.gmp_target: the binding target of a GMP_PREFIX worker (prefix, compiler, flags, gmp.h,
                 libgmp sha256); refused: a missing worker or record, a stale record, another backend, a numerics
                 profile, a diagnostic or development build, a record without the libgmp sha256 or gmp.h identity, and
                 a GMP_PREFIX in the environment other than the record's (the same one is accepted)
  bind           bound_tool_command gives the GMP_PREFIX words and passes bind_command; the command the tools used
                 before the fix (plain -lgmp) is refused (no prefix words, another gmp.h); other make flags, another
                 compiler version or __VERSION__ are refused
  linked         check_linked: the tool and the worker resolve the recorded libgmp (accepted); the pre-fix tool (no
                 rpath: the system libgmp), a worker resolving another libgmp here, and no ldd answer are refused;
                 a decimal tool has no library check
  forced_tiers   tests/forced_tiers.py compiles its tool with the worker's GMP_PREFIX words and verifies the resolved
                 libgmp before any point (in-process, stopped right after); a tool resolving another libgmp and a
                 conflicting GMP_PREFIX are refused (the command line exits with the reason, no record)
  check_points   tests/check_points.py binds both backends (decimal: flags and compiler; gmp: also the prefix and
                 gmp.h) and verifies the gmp tool's libgmp; on the command line a conflicting GMP_PREFIX is refused
                 before anything is staged
  class_b        tests/validate.py class_b binds its no-tail builds to bin/c8d2_{decimal,gmp} the same way
  sanitize       tests/sanitize.py's point_checks tool: the GMP_PREFIX of bin/c8d2_gmp_san's record where GMP_SAN_CMD puts
                 it, the recorded libgmp resolved; the pre-fix plain -lgmp tool and a conflicting GMP_PREFIX refused
  perf_twin      tools/perf_profile.py's debug-info twin: the worker's recorded command plus -g, GMP_PREFIX included
  docs           no paragraph of README.md or docs/*.md calls GMP_PREFIX (zen2) cleared for production without "NOT"
  source_binding Z1 (Stage-6 fix round 3): the tools compiled from a source snapshot in which the worker is reproduced
                 byte for byte; a stale worker, another Boost through CPATH and a patched Boost refused
  forced_tiers_coverage  Z2: "passed" only with both sectors, the prescribed sample and quotas, and the source binding;
                 --check for consumers
  c7ref_note     Z18: the Makefile no longer says make c7ref never links GMP
  relative_paths W3 (Stage-6 fix round 4, S6A4-03): a worker built in a package copy with a relative compiler, a
                 relative -I, a relative -L and a relative CPLUS_INCLUDE_PATH is reproduced byte for byte from the
                 snapshot (its record names its build_directory; the words are mirrored, not rewritten) and its tool
                 compiles; refused: the binding from another directory, and a record without build_directory; the real
                 host compiler shows why the words are not rewritten (an absolute -I changes the bytes of a header's
                 __FILE__) and that the mirror keeps them
Usage: python3 -B tests/test_gmp_binding.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,contextlib,hashlib,importlib,json,os,shlex,subprocess,sys,tempfile
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import build_record as BR  # noqa: E402
import common  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)
HOOKS=('CXX','CPPFLAGS','OPTFLAGS','CXXFLAGS','LDFLAGS','LDLIBS','GMP_PREFIX')
REQ=list(common.REQUIRED_CXXFLAGS)

FAKE_CXX=r'''import hashlib,json,os,re,sys
a=sys.argv[1:]
def find(h):
    dirs=[w[2:]for w in a if w.startswith('-I')]+[d for k in('CPATH','CPLUS_INCLUDE_PATH')for d in os.environ.get(k,'').split(':')if d]+[os.environ['FAKE_SYS_INCLUDE']]
    return next((os.path.join(d,h)for d in dirs if os.path.isfile(os.path.join(d,h))),None)
if a==['--version']:print(os.environ.get('FAKE_CXX_VERSION','g++ (GCC) 11.4.0'));print('Copyright (C) 2021');sys.exit(0)
if '-dM'in a and '-E'in a:
    text=sys.stdin.read();print('#define __VERSION__ "%s"'%os.environ.get('FAKE_CXX_MACRO','11.4.0'));print('#define _OPENMP 201511')
    if '-O3'in a or '-O2'in a:print('#define __OPTIMIZE__ 1')
    if '<boost/version.hpp>'in text:
        f=find('boost/version.hpp');print(open(f).read()if f else'#define BOOST_LIB_VERSION "1_74"\n#define BOOST_VERSION 107400')
    if '<gmp.h>'in text:
        f=find('gmp.h')
        if f is None:sys.exit(1)
        print(open(f).read())
    sys.exit(0)
out=a[a.index('-o')+1]
if os.environ.get('FAKE_CXX_LOG'):open(os.environ['FAKE_CXX_LOG'],'a').write(json.dumps(a)+'\n')
# deterministic in what a real compiler reads (Z1): the options without the output, the "..." include closure of the
# sources (paths as given, relative to the working directory) and the Boost header it finds
args=[w for i,w in enumerate(a)if w!='-o'and(i==0 or a[i-1]!='-o')];seen={};todo=[os.path.normpath(w)for w in a if w.endswith('.cpp')]
while todo:
    f=todo.pop()
    if f in seen or not os.path.isfile(f):continue
    t=open(f,'rb').read();seen[f]=hashlib.sha256(t).hexdigest()
    todo+=[os.path.normpath(os.path.join(os.path.dirname(f),m.group(1).decode()))for m in re.finditer(rb'#include "([^"]+)"',t)]
b=find('boost/version.hpp');boost=[b,hashlib.sha256(open(b,'rb').read()).hexdigest()]if b else None  # W3: the path as found, as a __FILE__ embeds it
ldirs=[w[2:]for w in a if w.startswith('-L')]+[d for d in os.environ.get('LIBRARY_PATH','').split(':')if d]
libs=[[d,sorted(os.listdir(d))if os.path.isdir(d)else None]for d in ldirs]   # W3: what the library search finds
h=hashlib.sha256(json.dumps([sorted(seen.items()),args,boost,libs]).encode()).hexdigest()
open(out,'w').write('#!/bin/sh\n# args '+json.dumps(args)+'\n# build '+h+'\nexit 0\n');os.chmod(out,0o755)
'''
FAKE_LDD=r'''import json,os,sys
f=os.path.realpath(sys.argv[-1]);m=json.loads(os.environ.get('FAKE_LDD_MAP','{}'))
try:args=json.loads(open(f).read().split('# args ',1)[1].splitlines()[0])
except Exception:args=[]
lib=m.get(f)
if lib is None and '-lgmp'in args:
    rp=[w[len('-Wl,-rpath,'):]for w in args if w.startswith('-Wl,-rpath,')]
    lib=next((os.path.join(d,'libgmp.so.10')for d in rp if os.path.isfile(os.path.join(d,'libgmp.so.10'))),os.environ.get('FAKE_LDD_GMP'))
print('\tlinux-vdso.so.1 (0x00007ffc00000000)')
if lib:print(f'\tlibgmp.so.10 => {lib} (0x00007f0000000000)')
'''
BOOST_H='#define BOOST_LIB_VERSION "{lib}"\n#define BOOST_VERSION {ver}\n{note}'
GMP_H='#define __GNU_MP_VERSION 6\n#define __GNU_MP_VERSION_MINOR 2\n#define __GNU_MP_VERSION_PATCHLEVEL 1\n#define __GMP_CC "gcc"\n#define __GMP_CFLAGS "{cflags}"\n'

class World:
    """A fake toolchain in td: the compiler, ldd, a system gmp.h and libgmp (Spack's, say), and a GMP_PREFIX (a zen2
    build of the same version: another gmp.h configuration and another libgmp)."""
    def __init__(self,td:Path):
        self.td=td=td.resolve();self.bin=td/'fakebin';self.bin.mkdir()
        for name,src in (('fakecxx',FAKE_CXX),('ldd',FAKE_LDD)):(self.bin/name).write_text(f'#!{PY}\n'+src);(self.bin/name).chmod(0o755)
        self.sysinc=td/'sys/include';self.sysinc.mkdir(parents=True);(self.sysinc/'gmp.h').write_text(GMP_H.format(cflags='-O2 -pedantic -m64'))
        (self.sysinc/'boost').mkdir();(self.sysinc/'boost/version.hpp').write_text(BOOST_H.format(lib='1_74',ver='107400',note=''))
        self.syslib=td/'sys/lib/libgmp.so.10';self.syslib.parent.mkdir(parents=True);self.syslib.write_bytes(b'spack libgmp 6.2.1\n')
        self.prefix=td/'opt/gmp-6.2.1-zen2';(self.prefix/'include').mkdir(parents=True);(self.prefix/'lib').mkdir()
        (self.prefix/'include/gmp.h').write_text(GMP_H.format(cflags='-O2 -pedantic -march=znver2'))
        (self.prefix/'lib/libgmp.so.10').write_bytes(b'zen2 libgmp 6.2.1\n');self.log=td/'cxx.log'
        self.cxx=str(self.bin/'fakecxx')
    def env(self,**kw)->dict:
        # hermetic (fix round 3, found by J-VAL-1 on symmetry, whose env.sh puts Boost 1.77 on CPATH): the include and
        # library search variables of the calling environment (build_record.INCLUDE_ENV) never reach the fake toolchain;
        # a test sets them explicitly with kw
        e={k:v for k,v in os.environ.items()if k not in HOOKS and k not in BR.INCLUDE_ENV and not k.startswith(('C8B_','FAKE_'))}
        e.update(PATH=f'{self.bin}:{os.environ["PATH"]}',CXX=self.cxx,FAKE_SYS_INCLUDE=str(self.sysinc),FAKE_LDD_GMP=str(self.syslib),FAKE_CXX_LOG=str(self.log))
        e.update({k:str(v)for k,v in kw.items()if v is not None})
        for k,v in kw.items():
            if v is None:e.pop(k,None)
        return e
    @contextlib.contextmanager
    def active(self,**kw):
        saved=dict(os.environ);e=self.env(**kw);os.environ.clear();os.environ.update(e)
        try:yield
        finally:os.environ.clear();os.environ.update(saved)
    def worker(self,name:str,backend:str='gmp',prefix:Path|None=None,extra=(),cwd:Path=ROOT,**env)->Path:
        """A worker built and recorded as make does it: the Makefile's command (cxx_command's layout, the GMP words with
        a prefix) compiled by the fake compiler in cwd (default: this package, i.e. its current sources), then
        tools/build_record.py main with the C8B_* variables, in cwd as make runs it (W3: the record's build_directory;
        the make hooks given in env are the record's flag variables too)."""
        d=self.td/'bin';d.mkdir(exist_ok=True);exe=d/name
        with self.active(**env):
            cmd=common.cxx_command(['src/c8d2_integrate.cpp'],exe,(['C8_USE_GMP']if backend=='gmp'else[])+list(extra),
                                   ('-lquadmath','-lgmp')if backend=='gmp'else('-lquadmath',),gmp_prefix=prefix)
            subprocess.run(cmd,check=True,cwd=cwd)
            h=lambda k,dflt='':str(env.get(k,dflt))
            os.environ.update(C8B_CXX=h('CXX',self.cxx),C8B_CPPFLAGS=h('CPPFLAGS'),C8B_OPTFLAGS=h('OPTFLAGS','-O3'),C8B_CXXFLAGS=h('CXXFLAGS'),C8B_LDFLAGS=h('LDFLAGS'),
                              C8B_LDLIBS=h('LDLIBS'),C8B_REQUIRED=' '.join(REQ),C8B_NUMERICS='exact',C8B_GMP_PREFIX=str(prefix or''))
            with contextlib.redirect_stderr(open(os.devnull,'w')),chdir(cwd):BR.main(exe,backend,cmd)
        return exe
    def compiles(self)->list:
        return [json.loads(l)for l in self.log.read_text().splitlines()]if self.log.exists()else[]

def sha(p)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
@contextlib.contextmanager
def chdir(d):
    old=os.getcwd();os.chdir(d)
    try:yield
    finally:os.chdir(old)
def refused(fn,needle,what):
    try:fn();raise AssertionError(f'accepted {what}')
    except (ValueError,SystemExit)as e:assert needle in str(e),(what,str(e)[-600:]);return str(e)

# ---------------------------------------------------------------- tests
def test_cxx_layout():
    import test_gmp_prefix as G
    with tempfile.TemporaryDirectory()as td:
        P=G.fake_prefix(Path(td).resolve())
        for hooks in ({'CXX':'g++'},{'CXX':'g++-13','CPPFLAGS':'-I/x -DFOO','OPTFLAGS':'-O2','CXXFLAGS':'-g','LDFLAGS':'-L/y -Wl,-z,now','LDLIBS':'-lfoo'}):
            with mock.patch.dict(os.environ,hooks):
                for k in HOOKS:
                    if k not in hooks:os.environ.pop(k,None)
                plain=common.cxx_command(['src/c8d2_integrate.cpp'],'bin/c8d2_gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'))
                for none in (None,''):assert common.cxx_command(['src/c8d2_integrate.cpp'],'bin/c8d2_gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'),gmp_prefix=none)==plain
                bound=common.cxx_command(['src/c8d2_integrate.cpp'],'bin/c8d2_gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'),gmp_prefix=P)
            sp=lambda k,d='':shlex.split(hooks.get(k,d))
            want=G.expected_default(hooks.get('CXX','g++'),sp('CPPFLAGS'),sp('OPTFLAGS','-O3'),sp('CXXFLAGS'),sp('LDFLAGS'),sp('LDLIBS'))['bin/c8d2_gmp']
            assert plain==want,(plain,want)
            cp=G.dry(*[f'{k}={v}'for k,v in hooks.items()],f'GMP_PREFIX={P}',targets=('bin/c8d2_gmp',));assert cp.returncode==0,cp.stderr[-600:]
            made=G.compiles(cp.stdout)['bin/c8d2_gmp'];assert bound==made,(bound,made)
        for bad in ('rel/gmp','/a b'):refused(lambda:common.cxx_command(['x.cpp'],'y',gmp_prefix=bad),'one absolute path without whitespace',bad)
    ok('cxx_command_gmp_words_equal_the_makefiles_default_unchanged')

def test_target():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix)
        with W.active():t=BR.gmp_target(w)
        rec=json.loads(w.with_name('c8d2_gmp.build.json').read_text())
        assert rec['GMP_PREFIX']==str(W.prefix)and rec['gmp_library']['sha256']==sha(W.prefix/'lib/libgmp.so.10')and 'znver2'in rec['gmp_header']['cflags'],rec
        assert t['GMP_PREFIX']==str(W.prefix)and t['gmp_library']['sha256']==sha(W.prefix/'lib/libgmp.so.10')and t['compiler']=='g++ (GCC) 11.4.0'and t['gmp_version']=='6.2.1'
        assert t['flags']['CXX']==[W.cxx]and t['flags']['OPTFLAGS']==['-O3']and t['worker_sha256']==sha(w)
        br=w.with_name('c8d2_gmp.build.json');r0=br.read_text()
        def edited(fn,needle,what):
            r=json.loads(r0);fn(r);br.write_text(json.dumps(r))
            try:
                with W.active():refused(lambda:BR.gmp_target(w),needle,what)
            finally:br.write_text(r0)
        edited(lambda r:r.update(executable_sha256='0'*64),'describes another executable','a stale record')
        edited(lambda r:r.update(backend='decimal'),"backend is 'decimal'",'another backend')
        edited(lambda r:r.update(NUMERICS='dd+mp256'),'numerics-profile build','a profile build')
        edited(lambda r:r.update(diagnostic='tier_timers'),'diagnostic build','a diagnostic build')
        edited(lambda r:r.update(parameter_overrides=['-DC8_MP256_RATIO=2']),'development build','a development build')
        edited(lambda r:r['gmp_library'].update(sha256=None),'no sha256 of the libgmp','no libgmp sha256')
        edited(lambda r:r.update(gmp_header={'cc':None,'cflags':None}),'no gmp.h version','no gmp.h identity')
        edited(lambda r:r.update(schema='other'),'not a c8-d2-build-record-1','another schema')
        with W.active(GMP_PREFIX='/other/gmp'):refused(lambda:BR.gmp_target(w),'this environment names GMP_PREFIX=/other/gmp','a conflicting GMP_PREFIX')
        with W.active(GMP_PREFIX=W.prefix):assert BR.gmp_target(w)['GMP_PREFIX']==str(W.prefix)
        d=W.worker('c8d2_default')  # no prefix: GMP_PREFIX in the environment conflicts, unset is fine
        with W.active(GMP_PREFIX=W.prefix):refused(lambda:BR.gmp_target(d),'built with GMP_PREFIX=(unset)','a prefix for a default worker')
        with W.active():assert BR.gmp_target(d)['GMP_PREFIX']is None
        with W.active():
            refused(lambda:BR.gmp_target(W.td/'bin/missing'),'does not exist','a missing worker')
            br.rename(br.with_suffix('.moved'))
            try:refused(lambda:BR.gmp_target(w),'no build record','a missing record')
            finally:br.with_suffix('.moved').rename(br)
    ok('gmp_target_from_the_record_refusals',refusals=13)

def test_bind():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);out=W.td/'tool'
        with W.active():
            cmd,b=BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],out,w,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'))
            src=str(out.with_name(out.name+'.snapshot')/'tests/forced_tiers.cpp')  # Z1: compiled from the source snapshot
            P=str(W.prefix);assert cmd[:2]==[W.cxx,f'-I{P}/include']and cmd[cmd.index(src)+1:][:3]==[f'-L{P}/lib',f'-Wl,-rpath,{P}/lib','-Wl,--disable-new-dtags'],cmd
            assert b['compile']['gmp_header']['cflags']=='-O2 -pedantic -march=znver2'and b['compile']['GMP_PREFIX_words'],b['compile']
            t=BR.gmp_target(w);old=common.cxx_command([ROOT/'tests/forced_tiers.cpp'],out,['C8_USE_GMP'],('-lquadmath','-lgmp'))  # the command before the fix
            e=refused(lambda:BR.bind_command(old,t),'lacks the GMP_PREFIX','the pre-fix command');assert 'gmp_header'in e,e
        for kw,needle in (({'CXXFLAGS':'-march=znver3'},'CXXFLAGS is'),({'OPTFLAGS':'-O2'},'OPTFLAGS is'),({'FAKE_CXX_VERSION':'g++ (GCC) 13.2.0'},'compiler:'),
                          ({'FAKE_CXX_MACRO':'13.2.0'},'compiler_macro_version')):
            with W.active(**kw):refused(lambda:BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],out,w,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp')),needle,kw)
        dw=W.worker('c8d2_decimal','decimal')
        with W.active():
            dcmd,db=BR.bound_tool_command([ROOT/'tests/point_checks.cpp'],out,dw,'decimal',[],('-lquadmath',))
            assert not any(x.startswith(('-I','-L','-Wl,'))for x in dcmd)and db['GMP_PREFIX']is None and 'gmp_header'not in db['compile']
        with W.active(CPPFLAGS='-DX'):refused(lambda:BR.bound_tool_command([ROOT/'tests/point_checks.cpp'],out,dw,'decimal',[],('-lquadmath',)),'CPPFLAGS is','decimal flags')
    ok('bind_command_prefix_words_gmp_h_flags_compiler',refusals=6)

def test_linked():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);tool=W.td/'tool'
        with W.active():
            cmd,b=BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],tool,w,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'));subprocess.run(cmd,check=True)
            v=BR.verify_tool(tool,b)['linked'];zen2=sha(W.prefix/'lib/libgmp.so.10')
            assert v['match']and v['tool']['sha256']==v['worker_now']['sha256']==zen2==v['want_sha256'],v
            old=common.cxx_command([ROOT/'tests/forced_tiers.cpp'],W.td/'old_tool',['C8_USE_GMP'],('-lquadmath','-lgmp'));subprocess.run(old,check=True)
            refused(lambda:BR.check_linked(W.td/'old_tool',b),f'resolves libgmp {W.syslib}','the pre-fix tool (system libgmp)')
        with W.active(FAKE_LDD_MAP=json.dumps({str(w.resolve()):str(W.syslib)})):refused(lambda:BR.check_linked(tool,b),'the worker c8d2_gmp resolves libgmp','a worker resolving another libgmp here')
        with W.active(PATH=os.environ['PATH']):refused(lambda:BR.check_linked(tool,b),'(unresolved: no ldd','no ldd')
        dw=W.worker('c8d2_decimal','decimal')
        with W.active():
            dcmd,db=BR.bound_tool_command([ROOT/'tests/point_checks.cpp'],W.td/'dtool',dw,'decimal',[],('-lquadmath',));subprocess.run(dcmd,check=True)
            assert 'linked'not in BR.verify_tool(W.td/'dtool',db)
    ok('check_linked_tool_and_worker_resolve_the_recorded_libgmp',refusals=3)

def _module(name:str):
    sys.modules.pop(name,None);return importlib.import_module(name)

class Stop(Exception):pass

def test_forced_tiers():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);FT=_module('forced_tiers');P=str(W.prefix)
        def run(**env):
            W.log.unlink(missing_ok=True)
            with W.active(**env),mock.patch.object(sys,'argv',['forced_tiers.py','--worker',str(w),'--scale','0.01']),mock.patch.object(FT,'heavy_and_random',side_effect=Stop):
                FT.main()
        try:run();raise AssertionError('forced_tiers went past the first sector')
        except Stop:pass
        c=[x for x in W.compiles()if any(w.endswith('.snapshot/tests/forced_tiers.cpp')for w in x)];assert len(c)==1,W.compiles()  # Z1: from the snapshot
        assert c[0][:1]==[f'-I{P}/include']and f'-Wl,-rpath,{P}/lib'in c[0]and f'-L{P}/lib'in c[0],c[0]   # argv[1:] of the fake compiler
        refused(lambda:run(FAKE_LDD_GMP=str(W.syslib),FAKE_LDD_MAP=json.dumps({str(w.resolve()):str(W.syslib)})),'forced_tiers: the precision tool does not run with',
                'a worker resolving another libgmp')
        cp=subprocess.run([PY,'-B',str(ROOT/'tests/forced_tiers.py'),'--worker',str(w),'--output',str(W.td/'ft.json')],capture_output=True,text=True,env=W.env(GMP_PREFIX='/other/gmp'),timeout=300)
        assert cp.returncode and 'this environment names GMP_PREFIX=/other/gmp'in cp.stderr and not (W.td/'ft.json').exists(),cp.stderr[-600:]
    ok('forced_tiers_bound_to_the_worker_gmp_refusals')

def test_check_points():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));gw=W.worker('c8d2_gmp',prefix=W.prefix);dw=W.worker('c8d2_decimal','decimal');CP=_module('check_points');P=str(W.prefix)
        with W.active():
            for b,wk in (('decimal',dw),('gmp',gw)):
                exe=W.td/f'pc_{b}';cmd,binding=CP.tool_build(b,exe,wk);subprocess.run(cmd,check=True);CP.verify_tool(exe,binding)
                assert (f'-I{P}/include'in cmd)is(b=='gmp')and ('linked'in binding)is(b=='gmp')and binding['worker']==str(wk.resolve()),(b,cmd)
            refused(lambda:CP.tool_build('gmp',W.td/'x',dw),"backend is 'decimal'",'a decimal worker for the gmp tool')
        cp=subprocess.run([PY,'-B',str(ROOT/'tests/check_points.py'),'--gmp-worker',str(gw),'--decimal-worker',str(dw),'--output',str(W.td/'pc.json')],
                          capture_output=True,text=True,env=W.env(GMP_PREFIX='/other/gmp'),timeout=300)
        assert cp.returncode and 'check_points (gmp)'in cp.stderr and 'GMP_PREFIX=/other/gmp'in cp.stderr and not (W.td/'pc.json').exists(),cp.stderr[-600:]
        assert not any('point_checks.cpp'in ' '.join(x)for x in W.compiles()if str(W.td/'pc_')not in ' '.join(x)),'compiled before refusing'
    ok('check_points_both_backends_bound_refused_before_staging')

def test_class_b():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));gw=W.worker('c8d2_gmp',prefix=W.prefix);dw=W.worker('c8d2_decimal','decimal');V=_module('validate');P=str(W.prefix)
        with W.active(),mock.patch.object(V,'exe',lambda b:{'gmp':gw,'decimal':dw}[b]),mock.patch.object(V,'run',side_effect=Stop):
            W.log.unlink(missing_ok=True)
            try:V.class_b(W.td,('gmp',));raise AssertionError('class_b went past the build')
            except Stop:pass
            c=[x for x in W.compiles()if '-DC8_NO_TAIL_FIELDS'in x];assert len(c)==1 and c[0][0]==f'-I{P}/include'and f'-Wl,-rpath,{P}/lib'in c[0],c
            with mock.patch.dict(os.environ,{'FAKE_LDD_MAP':json.dumps({str(gw.resolve()):str(W.syslib)})}):
                refused(lambda:V.class_b(W.td,('gmp',)),'class B (gmp)','a worker resolving another libgmp')
    ok('validate_class_b_bound_to_the_workers')

def test_sanitize():
    """Y1's defect class in tests/sanitize.py (Stage-6 fix round 2, integration): the point_checks sanitizer tool of the
    gmp backend gets the GMP_PREFIX of bin/c8d2_gmp_san's build record, word for word where the Makefile's GMP_SAN_CMD
    puts it (`make -n -B bin/c8d2_gmp_san GMP_PREFIX=...`, the source and output exchanged), and must resolve the
    libgmp that record names; the command before the fix (plain -lgmp) resolves the system libgmp and is refused, a
    conflicting GMP_PREFIX in the environment is refused before anything is compiled, a decimal tool has no GMP."""
    import test_gmp_prefix as G
    S=_module('sanitize')
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp_san',prefix=W.prefix);dw=W.worker('c8d2_decimal_san','decimal');P=str(W.prefix);tool=W.td/'pc_gmp'
        with W.active():
            cmd,b=S.pc_tool('gmp',tool,w);subprocess.run(cmd,check=True);v=S.verify_pc_tool(tool,b)['linked']
            assert v['match']and v['tool']['sha256']==sha(W.prefix/'lib/libgmp.so.10')and b['GMP_PREFIX']==P,(cmd,b)
            old=S.san_command([ROOT/'tests/point_checks.cpp'],W.td/'pc_old',defines=['C8_USE_GMP'],libs=('-lquadmath','-lgmp'));subprocess.run(old,check=True)
            refused(lambda:BR.check_linked(W.td/'pc_old',b),f'resolves libgmp {W.syslib}','the pre-fix point_checks tool')
            dcmd,db=S.pc_tool('decimal',W.td/'pc_dec',dw);assert not any(x.startswith(('-I','-L','-Wl,'))for x in dcmd)and 'linked'not in S.verify_pc_tool(W.td/'pc_dec',db)
        cp=G.dry(f'GMP_PREFIX={P}',targets=('bin/c8d2_gmp_san',));assert cp.returncode==0,cp.stderr[-600:]
        made=G.compiles(cp.stdout)['bin/c8d2_gmp_san'];sub={'src/c8d2_integrate.cpp':str(ROOT/'tests/point_checks.cpp'),'bin/c8d2_gmp_san':str(tool),made[0]:W.cxx}
        assert [sub.get(x,x)for x in made]==cmd,(made,cmd)
        with W.active(GMP_PREFIX='/other/gmp'):refused(lambda:S.pc_tool('gmp',tool,w),'this environment names GMP_PREFIX=/other/gmp','a conflicting GMP_PREFIX')
    ok('sanitize_point_checks_tool_bound_to_the_sanitizer_worker_gmp')

def test_perf_twin():
    """Y1's defect class in tools/perf_profile.py (Stage-6 fix round 2, integration): the debug-info twin of a GMP_PREFIX
    worker is the worker's own recorded command plus -g (the GMP_PREFIX words included), so same_code() can accept it;
    before, it linked plain -lgmp. Without a usable record (missing or stale) the twin is built without a prefix and
    the reason is recorded."""
    PP=_module('perf_profile')
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);twin=W.td/'twin';P=str(W.prefix)
        with W.active():
            r=PP.build_twin(twin,exe=w);assert r['returncode']==0 and r['GMP_PREFIX']==P,r
            want=json.loads(w.with_name('c8d2_gmp.build.json').read_text())['command'];want=[str(twin)if x==str(w)else x for x in want]
            want.insert(want.index(REQ[0]),'-g');assert r['command']==want,(r['command'],want)
            br=w.with_name('c8d2_gmp.build.json');br.rename(br.with_suffix('.moved'))
            try:r=PP.build_twin(W.td/'twin2',exe=w);assert r['GMP_PREFIX']is None and 'no build record'in r['gmp_prefix_note']and f'-I{P}/include'not in r['command'],r
            finally:br.with_suffix('.moved').rename(br)
    ok('perf_profile_twin_bound_to_the_worker_gmp_prefix')

def test_docs():
    """Y1's host note (Stage-6 fix round 2): until the precision checks are re-run on Expanse with the tools bound to the
    zen2 library (with the A-EXP-3 J-EXP-1 rerun), GMP_PREFIX is NOT cleared for production. No paragraph or table row
    of README.md or docs/*.md that speaks of GMP_PREFIX or zen2 as cleared may omit that (the history in CHANGELOG.md
    is exempt); each such paragraph says "NOT cleared" or "not cleared"."""
    import re
    bad=[];seen=0
    for f in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
        for k,para in enumerate(re.split(r'\n\s*\n|\n(?=\|)|\n(?=- )',f.read_text())):
            if re.search(r'\bcleared\b',para,re.I)and re.search(r'GMP_PREFIX|zen2',para):
                seen+=1
                if not re.search(r'\b(NOT|not) cleared\b',para):bad.append(f'{f.relative_to(ROOT)} block {k}: {para.strip()[:160]}')
    assert seen and not bad,f'documents that still call GMP_PREFIX cleared: {bad}'
    ok('docs_gmp_prefix_not_cleared_until_the_bound_rerun',paragraphs=seen)

def test_source_binding():
    """Z1 (Stage-6 fix round 3, S6A3-01): bound_tool_command compiles the tool from a read-only snapshot of src/ and the
    tool's sources, in which the worker is rebuilt with its build record's command and must come out byte for byte. The
    fake compiler is deterministic in what a real one reads (options without the output, the include closure, the
    Boost header found through -I, CPATH, CPLUS_INCLUDE_PATH). Accepted: a worker built from the current sources
    (snapshot files equal to the package's and read-only; the tool's command names the snapshot's sources, both
    backends). Refused: a stale worker (built before src/kernel.hpp changed, i.e. also an older --worker of the same
    flags and GMP), through bound_tool_command, tests/forced_tiers.py and tests/check_points.py (no record); another
    Boost version through CPATH (bind_command, nothing compiled); the same Boost version with other content through
    CPLUS_INCLUDE_PATH (the reproduction differs). The World is hermetic: an inherited CPATH (symmetry's Boost module)
    does not reach the fake toolchain (with one, the worker's Boost was the host's and the refusals named it)."""
    import shutil
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);dw=W.worker('c8d2_decimal','decimal');out=W.td/'tool'
        bind=lambda wk=w:BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],out,wk,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'))
        with W.active():cmd,b=bind()
        sb=b['source_binding'];snap=Path(sb['snapshot_dir']);files=sb['snapshot']['files']
        assert sb['schema']=='c8-d2-source-binding-1'and sb['reproduction']['reproduced']and sb['reproduction']['sha256']==sha(w)==b['worker_sha256'],sb
        assert sb['tool_sources']==['tests/forced_tiers.cpp']and {'src/c8d2_integrate.cpp','src/kernel.hpp','src/quadfast.hpp','src/numerics/dd.hpp','tests/forced_tiers.cpp'}<=set(files)
        assert all(files[k]==sha(ROOT/k)and not (snap/k).stat().st_mode&0o222 for k in files)and str(snap/'tests/forced_tiers.cpp')in cmd and str(ROOT/'tests/forced_tiers.cpp')not in cmd
        with W.active():dcmd,db=BR.bound_tool_command([ROOT/'tests/point_checks.cpp'],W.td/'dtool',dw,'decimal',[],('-lquadmath',))
        assert db['source_binding']['reproduction']['sha256']==sha(dw)and any(x.endswith('dtool.snapshot/tests/point_checks.cpp')for x in dcmd),dcmd
        # a stale worker: its kernel.hpp is not the current one
        old=W.td/'old';shutil.copytree(ROOT/'src',old/'src');(old/'src/kernel.hpp').write_text((old/'src/kernel.hpp').read_text()+'\n// an older kernel\n')
        sw=W.worker('c8d2_gmp_old',prefix=W.prefix,cwd=old);sdw=W.worker('c8d2_decimal_old','decimal',cwd=old)
        with W.active():refused(lambda:bind(sw),'the worker is stale','a stale gmp worker')
        cp=subprocess.run([PY,'-B',str(ROOT/'tests/forced_tiers.py'),'--worker',str(sw),'--output',str(W.td/'ft.json')],capture_output=True,text=True,env=W.env(),timeout=300)
        assert cp.returncode and 'forced_tiers:'in cp.stderr and 'the worker is stale'in cp.stderr and not (W.td/'ft.json').exists(),cp.stderr[-600:]
        cp=subprocess.run([PY,'-B',str(ROOT/'tests/check_points.py'),'--gmp-worker',str(w),'--decimal-worker',str(sdw),'--output',str(W.td/'pc.json')],
                          capture_output=True,text=True,env=W.env(),timeout=300)
        assert cp.returncode and 'check_points (decimal)'in cp.stderr and 'the worker is stale'in cp.stderr and not (W.td/'pc.json').exists(),cp.stderr[-600:]
        # Boost through the include environment
        for d,lib,ver,note in (('boost183','1_83','108300',''),('boost174p','1_74','107400','// patched\n')):
            (W.td/d/'boost').mkdir(parents=True);(W.td/d/'boost/version.hpp').write_text(BOOST_H.format(lib=lib,ver=ver,note=note))
        W.log.unlink(missing_ok=True)
        with W.active(CPATH=W.td/'boost183'):refused(bind,"BOOST_VERSION: '108300' for the tool, '107400' for the worker",'another Boost version through CPATH')
        assert not W.compiles(),'compiled before refusing another Boost version'
        with W.active(CPLUS_INCLUDE_PATH=W.td/'boost174p'):refused(bind,'the worker is stale','the same Boost version, other content, through CPLUS_INCLUDE_PATH')
    ok('Z1_tools_bound_to_the_worker_sources_stale_and_boost_refused',refusals=6)

def test_forced_tiers_coverage():
    """Z2 (Stage-6 fix round 3, S6A3-02): tests/forced_tiers.py says "passed" only with the complete A-RPL-5 coverage.
    The tool is bound and compiled on the fake toolchain; graphs, nets and the tool's runs are stand-ins (every run:
    6,000 binary128-accepted and 600 MP points, no violation). Both sectors: passed, coverage complete. A --sectors
    subset and a --scale run: "development run (...)" naming what is missing. forced_tiers.py --check exits 0 only for
    the complete record (also when a record's status is edited to "passed"), and coverage() names a missing source
    binding, an unmet quota, another graph count and a violation counter."""
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));w=W.worker('c8d2_gmp',prefix=W.prefix);n=[0]
        fake={'points':6600,'nonmoderate':0,'nondirect':0,'decision_mismatch':0,'ld_violations':0,'quad_violations':0,'mp_violations':0,'decimal300_violations':0,
              'level':[0,6000,600],'max_ld':'0','hist_ld':{},'first_violations':[],'end':0}
        def go(*args):
            FT=_module('forced_tiers');n[0]+=1;out=W.td/f'ft{n[0]}.json'
            with W.active(),mock.patch.object(sys,'argv',['forced_tiers.py','--worker',str(w),'--output',str(out),*args]),\
                 mock.patch.object(FT,'heavy_and_random',lambda s,L,h,r,seed:list(range(h+r))),mock.patch.object(FT,'stage',lambda root,s,L,ids:root),\
                 mock.patch.object(FT,'make_net',lambda *x,**k:{}),mock.patch.object(FT,'run',lambda cmd,threads=None:subprocess.CompletedProcess(cmd,0,json.dumps(fake),'')),\
                 contextlib.redirect_stdout(open(os.devnull,'w')):
                FT.main()
            return out,json.loads(out.read_text())
        full,r=go();assert r['status']=='passed'and r['coverage']=={'complete':True,'why':[],'source_binding_checked':True},r['coverage']
        sub,r1=go('--sectors','free');assert r1['status'].startswith('development run (')and 'not both of'in r1['status']and not r1['coverage']['complete'],r1['status']
        sc,r2=go('--scale','0.01');assert r2['status'].startswith('development run (')and 'scale 0.01'in r2['status'],r2['status']
        chk=lambda p:subprocess.run([PY,'-B',str(ROOT/'tests/forced_tiers.py'),'--check',str(p)],capture_output=True,text=True,env=W.env(),timeout=120).returncode
        forged=W.td/'forged.json';forged.write_text(json.dumps(dict(r1,status='passed')))
        assert (chk(full),chk(sub),chk(sc),chk(forged))==(0,1,1,1)
        FT=_module('forced_tiers')
        def why(fn):x=json.loads(json.dumps(r));fn(x);c=FT.coverage(x);assert not c['complete'];return ' '.join(c['why'])
        assert 'not bound to the worker'in why(lambda x:x['gmp_binding'].pop('source_binding'))
        assert 'below 10000 and 1000'in why(lambda x:x['sectors']['power']['by_L']['8'].update(level=[0,0,0]))
        assert 'graphs, not 400'in why(lambda x:x['sectors']['free']['by_L']['8'].update(graphs=399))
        assert 'violation counters'in why(lambda x:x['sectors']['free']['by_L']['7'].update(quad_violations=1))
    ok('Z2_forced_tiers_passed_only_with_full_coverage_check_cli',records=3)

def test_forced_tiers_consumers():
    """Z2 consumers (fix round 3 integration, S6A3-02's "make acceptance consumers validate the coverage fields"): the
    stored-record summaries benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py and
    stage5/exp/scripts/s5e_summary.py judge forced_tiers.json by forced_tiers_verdict: status 'passed' AND coverage()
    complete (these records predate Z1, so without the source-binding condition). Every stored forced_tiers record made
    before Z1 is complete but for the Z1 binding (so --check refuses it, as G1 found on 570416 and 570029), and one made
    since (fix round 3's symmetry validation, s6fix3, job 570535) is complete with it; a record of one sector
    with its status edited to 'passed', and a --scale record so edited, are FAILED by the summaries' rule (before: passed)."""
    import glob,importlib.util as iu
    sp=iu.spec_from_file_location('summarize_final',ROOT/'benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py');SF=iu.module_from_spec(sp);sp.loader.exec_module(SF)
    FT=_module('forced_tiers');stored=sorted(glob.glob(str(ROOT/'benchmarks/**/forced_tiers.json'),recursive=True));assert len(stored)>=5,stored
    old=[]
    for f in stored:
        r=json.loads(Path(f).read_text());v,c=SF.forced_tiers_verdict(r)
        assert v=='passed'and c['complete']and c['source_binding_checked']is False,(f,v)
        full=FT.coverage(r)
        if (r.get('gmp_binding')or{}).get('source_binding'):assert full['complete'],(f,full)  # a record made since Z1 (s6fix3): acceptance evidence
        else:assert not full['complete']and len(full['why'])==1 and 'not bound to the worker'in full['why'][0],(f,full);old.append(f)
    assert len(old)>=5,old
    r=json.loads(Path(old[0]).read_text())
    one=dict(r,sectors={'free':r['sectors']['free']},status='passed');v,_=SF.forced_tiers_verdict(one);assert v.startswith('FAILED')and 'not both of'in v,v
    sc=dict(r,scale=0.5,status='passed');v,_=SF.forced_tiers_verdict(sc);assert v.startswith('FAILED')and 'scale 0.5'in v,v
    st=dict(r,status='development run (--scale)');v,_=SF.forced_tiers_verdict(st);assert v.startswith('FAILED')and 'development run'in v,v
    for f in ('benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py','benchmarks/expanse_2026-10-c8/stage5/exp/scripts/s5e_summary.py'):
        assert 'forced_tiers_verdict(ft)'in (ROOT/f).read_text(),f
    ok('Z2_consumers_summaries_check_recomputed_coverage',stored=len(stored))

def test_c7ref_note():
    """Z18 (Stage-6 fix round 3, S6G3-01): make c7ref builds the reference GMP worker with the reference Makefile's
    -lgmp, so the Makefile's GMP_PREFIX comment must not say that c7ref never links GMP; it says that c7ref ignores
    GMP_PREFIX and links GMP. (docs/NUMERICS.md is the documentation group's.)"""
    import re
    ref=(ROOT/'reference/c7d2_hpc_a55958f/Makefile').read_text();assert re.search(r'^override GMP_CMD = .*-lgmp',ref,re.M)and 'bin/c7d2_gmp'in(ROOT/'Makefile').read_text()
    text=' '.join(l.lstrip('#').strip()for l in(ROOT/'Makefile').read_text().splitlines()if l.startswith('#'))
    assert not re.search(r'c7ref never links? GMP',text),'the Makefile still says make c7ref never links GMP'
    assert 'make c7ref ignores it too, but it does link GMP'in text and 'plain -lgmp'in text
    ok('Z18_makefile_c7ref_links_gmp')

def test_relative_paths():
    """W3 (Stage-6 fix round 4, S6A4-03): reproduce_worker ran the record's command in the snapshot, so a relative word
    of a supported build named something else there and the binding refused an unchanged worker ("stale"). A package
    copy pkg/ (this src/) beside boost_rel/ (Boost 1.77) and the fake toolchain: four workers, each built in pkg/ with
    one relative hook (CXX=../fakebin/fakecxx, CPPFLAGS=-I../boost_rel, LDFLAGS=-Llib, CPLUS_INCLUDE_PATH=../boost_rel;
    the fake compiler's bytes depend on the Boost path as found and on the -L listing, as a real compiler's __FILE__ and
    library search do). Bound from pkg/ (the tool's output and snapshot elsewhere, out/): each is reproduced byte for
    byte (the record's build_directory is pkg/, the relative word mirrored into the snapshot's private parent, src/
    untouched) and its tool compiles from pkg/. Refused: the same binding from another directory (nothing compiled), and
    a record without build_directory. relative_words, climb and mirror's own refusals. With the real host compiler: an
    absolute -I changes the bytes of a header's __FILE__ (why the words are not rewritten), the mirror keeps them."""
    import shutil
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));pkg=W.td/'pkg';shutil.copytree(ROOT/'src',pkg/'src');out=W.td/'out';out.mkdir()
        (W.td/'boost_rel/boost').mkdir(parents=True);(W.td/'boost_rel/boost/version.hpp').write_text(BOOST_H.format(lib='1_77',ver='107700',note=''))
        (pkg/'lib').mkdir();(pkg/'lib/libextra.a').write_bytes(b'extra\n')
        cases={'compiler':({'CXX':os.path.relpath(W.cxx,pkg)},'fakebin'),'include':({'CPPFLAGS':'-I../boost_rel'},'boost_rel'),
               'library':({'LDFLAGS':'-Llib'},'lib'),'include_env':({'CPLUS_INCLUDE_PATH':'../boost_rel'},'boost_rel')}
        done={}
        for name,(env,link) in cases.items():
            wk=W.worker(f'c8d2_gmp_{name}',prefix=W.prefix,cwd=pkg,**env);rec=json.loads(wk.with_name(wk.name+'.build.json').read_text())
            assert rec['build_directory']==str(pkg),rec.get('build_directory')
            bind=lambda:BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],out/f'tool_{name}',wk,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp'))
            with W.active(**env),chdir(pkg):
                cmd,b=bind();subprocess.run(cmd,check=True);BR.verify_tool(out/f'tool_{name}',b)
            sb=b['source_binding'];rep=sb['reproduction'];root=Path(sb['snapshot_dir'])
            assert rep['reproduced']and rep['sha256']==sha(wk)==b['worker_sha256']and rep['build_directory']==str(pkg),rep
            assert [m['link'].split('/')[-1]for m in rep['mirrored']]==[link]and sb['snapshot_parent_levels']==(0 if name=='library'else 1),(rep['mirrored'],sb['snapshot_parent_levels'])
            assert all(sb['snapshot']['files'][k]==sha(ROOT/k)and not (root/k).is_symlink()for k in sb['snapshot']['files']),'the snapshot changed'
            W.log.unlink(missing_ok=True)
            with W.active(**env),chdir(W.td):refused(bind,'run the precision tool from the worker',f'{name}: a binding from another directory')
            assert not W.compiles(),f'{name}: compiled before refusing'
            done[name]=rep['mirrored'][0]['word']
        # a record without build_directory (written before fix round 4) and relative words: refused, not guessed
        wk=pkg.parent/'bin'/'c8d2_gmp_include';br=wk.with_name(wk.name+'.build.json');r0=br.read_text();r=json.loads(r0);r.pop('build_directory');br.write_text(json.dumps(r))
        try:
            with W.active(CPPFLAGS='-I../boost_rel'),chdir(pkg):
                refused(lambda:BR.bound_tool_command([ROOT/'tests/forced_tiers.cpp'],out/'tool_old',wk,'gmp',['C8_USE_GMP'],('-lquadmath','-lgmp')),
                        'a build directory its record does not name','a pre-W3 record with a relative -I')
                snap=out/'old.snapshot';BR.source_snapshot(snap)
                refused(lambda:BR.reproduce_worker(wk,snap,out/'old.reproduced'),'names no build_directory','reproduce_worker on a pre-W3 record')
        finally:br.write_text(r0)
    # the helpers
    words=['../gcc/bin/g++','-I../boost','-isystem','inc','-isystemsys2','-Llib','-Wl,-rpath,../rp','-Wl,-L,lib2','@rsp','-std=c++17','-fprofile-use=prof/x',
           '-O3','-lgmp','-DX=1','/abs/x.a','rel.a','-o','bin/x','-I.','-I/abs']
    assert BR.relative_words(words)==['../gcc/bin/g++','../boost','inc','sys2','lib','../rp','lib2','rsp','prof/x','rel.a','bin/x'],BR.relative_words(words)
    assert BR.relative_words(['ccache','g++','-Ix'],2)==['x']and BR.relative_words(['ccache','../bin/g++','-O3'],2)==['../bin/g++']
    assert BR.compiler_words({'CXX':'ccache g++'})==2 and BR.compiler_words({})==1
    assert [BR.climb(x)for x in('../a','a/../../b','./x','x/y/../..','../../../c')]==[1,1,0,0,3]
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);top=td/'snap';root=BR.snapshot_root(top,1);(root/'src').mkdir(parents=True);(td/'B').mkdir();(td/'x').mkdir()
        refused(lambda:BR.mirror(root,top,td/'B','../../x'),'climbs above','a word climbing above the private parents')
        refused(lambda:BR.mirror(root,top,td/'B',f'../{BR.SNAPSHOT_UP}'),'private directory','a word naming the private parent')
        assert BR.mirror(root,top,td/'B','src/kernel.hpp')is None and BR.mirror(root,top,td/'B','../x')=='x'and (top/'x').resolve()==(td/'x').resolve()
    real=_real_compiler_check()
    ok('W3_relative_words_reproduced_from_the_build_directory_refusals',cases=done,refusals=4+2,real_compiler=real)

def test_flags_relative():
    """W3's class outside tools/build_record.py (Stage-6 fix round 4, integration; G1's note): tests/numerics_flags.py X2
    ran a worker's build-record command (and the F1 tool's, the same words) with the source snapshot as its working
    directory, so a relative word named something else there and bind() refused an unchanged worker as stale; and
    tools/perf_profile.py compiled the debug-info twin in the package root from relative make flags, whatever the
    worker's build directory. With the fake toolchain (its bytes depend on the Boost path as found and on the -L
    listing): workers built in pkg/ with one relative hook each (a relative CXX, CPPFLAGS=-I../boost_rel, LDFLAGS=-Llib,
    CPLUS_INCLUDE_PATH=../boost_rel) are reproduced byte for byte by numerics_flags.bind from a snapshot nested as deep
    as their words climb (the word mirrored, src/ untouched), and the F1 tool compiles there and resolves the worker's
    libgmp. Refused before anything is compiled: a record without build_directory; two executables whose build
    directories give one relative word different meanings. perf_profile.build_twin with a relative -I compiles in the
    worker's build directory (the twin equals the command built there and differs from the package-root build of
    before), is not built for a record without build_directory (error W3), and stays in the package root without
    relative words."""
    import shutil
    NF=_module('numerics_flags');PP=_module('perf_profile');n=0
    line=lambda f:[l for l in Path(f).read_text().splitlines()if l.startswith('# build ')][0]
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));pkg=W.td/'pkg';shutil.copytree(ROOT/'src',pkg/'src')
        for d,ver in ((W.td/'boost_rel',('1_77','107700')),(W.td/'other/boost_rel',('1_76','107600'))):
            (d/'boost').mkdir(parents=True);(d/'boost/version.hpp').write_text(BOOST_H.format(lib=ver[0],ver=ver[1],note=''))
        (pkg/'lib').mkdir();(pkg/'lib/libextra.a').write_bytes(b'extra\n')
        cases={'compiler':({'CXX':os.path.relpath(W.cxx,pkg)},1),'include':({'CPPFLAGS':'-I../boost_rel'},1),'library':({'LDFLAGS':'-Llib'},0),
               'include_env':({'CPLUS_INCLUDE_PATH':'../boost_rel'},1)}
        wks={}
        for name,(env,levels)in cases.items():
            wk=wks[name]=W.worker(f'c8d2_gmp_{name}',prefix=W.prefix,cwd=pkg,**env)
            with W.active(**env):
                assert NF.snapshot_levels([wk])==levels,(name,NF.relative_of(wk))
                top=W.td/f'snap_{name}';snap=BR.snapshot_root(top,levels);info=NF.snapshot(snap)
                b=NF.bind(wk,snap,info,W.td,name,top)
                assert b['reproduced']and b['sha256']==b['reproduced_sha256']==sha(wk)and b['build_directory']==str(pkg)and len(b['mirrored'])==1,(name,b)
                assert all(not (snap/k).is_symlink()and sha(snap/k)==v for k,v in info['files'].items()),'the snapshot changed'
                cmd,lib=NF.compile_tool(wk,W.td/f'f1_{name}',snap);assert lib['match']and 'tests/numerics_f1.cpp'in cmd and 'src/c8d2_integrate.cpp'not in cmd,(name,lib,cmd)
                n+=1
        # refused before anything is compiled: a record without build_directory, and one word with two meanings
        wk=wks['include'];br=wk.with_name(wk.name+'.build.json');r0=br.read_text();r=json.loads(r0);r.pop('build_directory');br.write_text(json.dumps(r))
        try:
            with W.active(CPPFLAGS='-I../boost_rel'):
                top=W.td/'snap_old';snap=BR.snapshot_root(top,1);info=NF.snapshot(snap);W.log.unlink(missing_ok=True)
                refused(lambda:NF.bind(wk,snap,info,W.td,'old',top),'names no build_directory','a pre-W3 record with a relative -I (numerics_flags)')
                assert not W.compiles(),'compiled before refusing';n+=1
        finally:br.write_text(r0)
        pkg2=W.td/'other/pkg2';shutil.copytree(ROOT/'src',pkg2/'src');w2=W.worker('c8d2_gmp_other',prefix=W.prefix,cwd=pkg2,CPPFLAGS='-I../boost_rel')
        with W.active(CPPFLAGS='-I../boost_rel'):
            top=W.td/'snap_two';snap=BR.snapshot_root(top,NF.snapshot_levels([wk,w2]));info=NF.snapshot(snap)
            assert NF.bind(wk,snap,info,W.td,'exact',top)['reproduced'];W.log.unlink(missing_ok=True)
            refused(lambda:NF.bind(w2,snap,info,W.td,'profile',top),'another executable\'s build directory claimed','one relative word, two build directories')
            assert not W.compiles();n+=1
        # perf_profile's twin
        with W.active(CPPFLAGS='-I../boost_rel'),chdir(W.td):
            r=PP.build_twin(W.td/'twin_rel',exe=wk);assert r['returncode']==0 and r['cwd']==str(pkg)and r['relative_words']==['../boost_rel'],r
            ref=list(r['command']);ref[ref.index('-o')+1]=str(W.td/'twin_ref');subprocess.run(ref,cwd=pkg,check=True)
            ref[ref.index('-o')+1]=str(W.td/'twin_root');subprocess.run(ref,cwd=ROOT,check=True)
            assert line(W.td/'twin_rel')==line(W.td/'twin_ref')!=line(W.td/'twin_root'),'the twin is not the build-directory compile';n+=1
            r=json.loads(r0);r.pop('build_directory');br.write_text(json.dumps(r))
            try:
                W.log.unlink(missing_ok=True);r=PP.build_twin(W.td/'twin_old',exe=wk)
                assert r['returncode']is None and 'W3'in r['error']and not W.compiles()and not (W.td/'twin_old').exists(),r;n+=1
            finally:br.write_text(r0)
        with W.active():assert PP.twin_directory(wk)==(ROOT,[],None),PP.twin_directory(wk)  # no relative word: the package root, as before
    ok('W3_class_numerics_flags_X2_and_perf_twin_relative_words',cases=len(cases),checks=n)

def _real_compiler_check():
    """The host compiler (c++ or CXX): a header's __FILE__ found through -I../inc, compiled once in the build directory,
    once with the -I made absolute (different bytes: why W3 does not rewrite words) and once from a snapshot whose
    private parent mirrors ../inc (the same bytes). None when no compiler runs here."""
    import shutil
    cxx=shlex.split(os.environ.get('C8_HOST_CXX')or('c++'if sys.platform=='darwin'else'g++'))
    if shutil.which(cxx[0])is None:return None
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);B=td/'pkg';(B/'src').mkdir(parents=True);(td/'inc').mkdir()
        (td/'inc/h.hpp').write_text('#pragma once\ninline const char*where(){return __FILE__;}\n')
        (B/'src/t.cpp').write_text('#include <cstdio>\n#include "h.hpp"\nint main(){std::puts(where());}\n')
        def build(cwd,inc,out):
            cp=subprocess.run([*cxx,'-O1',f'-I{inc}','src/t.cpp','-o',str(out)],cwd=cwd,capture_output=True,text=True,timeout=300)
            assert cp.returncode==0,cp.stderr[-600:];return subprocess.run([str(out)],capture_output=True,text=True).stdout.strip()
        rel=build(B,'../inc',td/'a.out');ab=build(B,str(td/'inc'),td/'b.out')
        top=td/'snap';root=BR.snapshot_root(top,1);(root/'src').mkdir(parents=True);shutil.copyfile(B/'src/t.cpp',root/'src/t.cpp')
        assert BR.mirror(root,top,B,'../inc')=='inc';mir=build(root,'../inc',td/'c.out')
        assert rel=='../inc/h.hpp'and ab==f'{td/"inc"}/h.hpp'and mir==rel,(rel,ab,mir)
        return {'compiler':cxx[0],'relative':rel,'absolute':ab,'mirrored':mir}

TESTS=[('cxx_layout',test_cxx_layout),('target',test_target),('bind',test_bind),('linked',test_linked),('forced_tiers',test_forced_tiers),
       ('check_points',test_check_points),('class_b',test_class_b),('sanitize',test_sanitize),('perf_twin',test_perf_twin),('docs',test_docs),
       ('source_binding',test_source_binding),('forced_tiers_coverage',test_forced_tiers_coverage),('c7ref_note',test_c7ref_note),
       ('forced_tiers_consumers',test_forced_tiers_consumers),('relative_paths',test_relative_paths),('flags_relative',test_flags_relative)]

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
