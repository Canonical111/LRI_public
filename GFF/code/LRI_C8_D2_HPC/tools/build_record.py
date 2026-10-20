#!/usr/bin/env python3
"""Write bin/<exe>.build.json after `make` links an executable (A-L13).

  build_record.py bin/c8d2_gmp gmp -- <the exact compile command the Makefile ran>

Records the command, the compiler version, the make flag variables (C8B_* exported by the Makefile, which cannot be
overridden from the command line), and what the compiler really does with the command: every compiler option of the
command, wherever it sits (all words except the source file, `-o` and its argument, and link-only words), is passed to
preprocessor probes for __OPTIMIZE__ (a warning and optimized:false for an unoptimized build), BOOST_LIB_VERSION, the
GMP version, _OPENMP, __FAST_MATH__ and __FINITE_MATH_ONLY__. required_flags_effective is true only if every required
numerical flag is present, -ffp-contract=off and -fno-fast-math are the last of their kind, _OPENMP is defined and no
fast-math macro is. C8(2) (PLAN component C) adds the numerics profile (the Makefile's NUMERICS) and the diagnostic
kind: "tier_timers" (-DC8_TIER_TIMERS), "ratio_histogram" (-DC8_RATIO_HISTOGRAM), "sanitize" (-fsanitize=... or
-D_GLIBCXX_ASSERTIONS), "no_tail_fields" (-DC8_NO_TAIL_FIELDS, test-only), "order_trace" (-DC8_ORDER_TRACE, test-only:
A-KER-5's execution-order trace) or null, from the command, together with the executable's own --describe when it runs. `production.py plan` records the file and refuses diagnostic executables.
Opt-in numerics builds (Stage 4c, -DC8_NUMERICS from `make gmp NUMERICS=<p>`) also record the profile macros of the
command and the sha256 of every src/numerics/*.hpp, the code those builds alone include (numerics_sources; null for
the default build, which includes none of it).
Every record lists the profile-parameter overrides of the command (parameter_overrides: each -D/-U option naming a C8_*
macro other than the Makefile's build macros C8_USE_GMP, C8_NUMERICS and C8_NUMERICS_<P> and the diagnostic macros
above, e.g. -DC8_MP256_RATIO=..., -DC8_EXP1_RANGE=..., -DC8_DD_DEVELOPMENT, or a C8_NX_* hook given on the command
line) and "development": true when there is any; `production.py plan` refuses such a build (A-FLAG-1), as it refuses
an executable whose --describe marks a profile "development":true. Z3 (Stage-6 fix round 3): parameter_overrides also
names a source switch (-DNO_SUM_SHARING), -D/-U words inside -Wp,..., and every -include, -imacros, -Xpreprocessor
option and response file @FILE; and macro_overrides lists the C8_* macros and source switches the compiler's own probe
of the options shows in effect (however they were set) beyond the build and diagnostic macros the command's plain -D
words give; either makes "development": true. src/kernel.hpp itself refuses any C8_NX_* hook defined from outside
src/numerics/ at compile time, so such a command no longer builds at all.
GMP builds (Stage 4b R4f) also record the Makefile's GMP_PREFIX, the configuration gmp.h was built with (__GMP_CC,
__GMP_CFLAGS) and the libgmp the executable resolves here (ldd under this environment): its path, realpath, sha256 and
whether it is a fat build (defines __gmpn_cpuvec_init), and the executable's RPATH/RUNPATH (readelf -d).
W3 (Stage-6 fix round 4, S6A4-03): every record names its build_directory, the working directory the compile command
ran in (make's), so that the relative words of the command (a relative compiler, -I../boost_1_77_0, -L lib, a link
input) and of the include environment (CPATH=..., LIBRARY_PATH=...) keep their meaning when the command is reproduced
elsewhere (reproduce_worker, below).
"""
from __future__ import annotations
import hashlib,json,os,re,shlex,shutil,socket,subprocess,sys,time
from pathlib import Path
from common import REQUIRED_CXXFLAGS,digest,link_only

def compiler_options(command:list[str])->list[str]:
    """The compiler and every compile option of a compile-and-link command, in order."""
    out=[command[0]];skip=False
    for w in command[1:]:
        if skip:skip=False;continue
        if w=='-o':skip=True;continue
        if w.startswith('-o')and len(w)>2:continue
        if not w.startswith('-')and w.endswith(('.cpp','.cc','.cxx','.c')):continue
        if link_only(w):continue
        out.append(w)
    return out

def last(opts:list[str],prefixes:tuple)->str|None:
    return next((w for w in reversed(opts)if w.startswith(prefixes)),None)

def diagnostic_kind(opts:list[str])->str|None:
    """The diagnostic build a compile command makes (PLAN component C), from its compiler options; None for a
    production build."""
    if '-DC8_TIER_TIMERS'in opts:return 'tier_timers'
    if '-DC8_RATIO_HISTOGRAM'in opts:return 'ratio_histogram'
    if any(w.startswith('-fsanitize=')for w in opts)or '-D_GLIBCXX_ASSERTIONS'in opts:return 'sanitize'
    if '-DC8_NO_TAIL_FIELDS'in opts:return 'no_tail_fields'
    if '-DC8_ORDER_TRACE'in opts:return 'order_trace'
    return None

BUILD_MACROS=('C8_USE_GMP','C8_NUMERICS','C8_NUMERICS_DD','C8_NUMERICS_MP256','C8_NUMERICS_EXP1')
DIAGNOSTIC_MACROS=('C8_TIER_TIMERS','C8_RATIO_HISTOGRAM','C8_NO_TAIL_FIELDS','C8_ORDER_TRACE')
# Z3 (Stage-6 fix round 3): the package's own source switches outside the C8_ namespace (src/kernel.hpp: NO_SUM_SHARING
# replaces the shared long-double sums by the unshared ones); setting one makes a development build as a C8_* one does.
SOURCE_SWITCHES=('NO_SUM_SHARING',)
# Options that bring macros or options in other than as a -D/-U word of the command (Z3): a forced header, a macro
# file, a preprocessor pass-through, a response file. The Makefile never writes one; each makes a development build.
INJECTION_OPTIONS=('-include','-imacros','-Xpreprocessor')

def _overridden(name:str)->bool:
    return (name.startswith('C8_')and name not in BUILD_MACROS+DIAGNOSTIC_MACROS)or name in SOURCE_SWITCHES

def parameter_overrides(opts:list[str])->list[str]:
    """The -D/-U options (either spelling: -DNAME[=v] or -D NAME[=v], also inside -Wp,...) that name a C8_* macro other
    than the Makefile's build macros and the diagnostic macros: profile-parameter overrides (-DC8_MP256_RATIO=...,
    -DC8_EXP1_RANGE=..., -DC8_DD_*) and command-line C8_NX_* hooks (which src/kernel.hpp now refuses at compile time,
    Z3), or a source switch (SOURCE_SWITCHES); and (Z3) every -include, -imacros, -Xpreprocessor option with its
    argument and every response file @FILE, whose macros the words do not show. Any of them makes the build a
    development build. tools/production.py recomputes this from a record's compiler_options."""
    out=[];i=0
    while i<len(opts):
        w=opts[i]
        if w in INJECTION_OPTIONS:out.append(' '.join(opts[i:i+2]));i+=2;continue
        if w.startswith('@')or w.startswith(('-include','-imacros'))and w not in INJECTION_OPTIONS:out.append(w);i+=1;continue
        if w.startswith('-Wp,'):
            out+=[f'-Wp,{p}'for p in w[4:].split(',')if p.startswith(('-D','-U'))and _overridden(re.split(r'[=(]',p[2:],1)[0])or p.startswith(('-include','-imacros'))]
            i+=1;continue
        if w in('-D','-U')and i+1<len(opts):arg=opts[i+1];flag=w;i+=2
        elif w.startswith(('-D','-U'))and len(w)>2:arg=w[2:];flag=w[:2];i+=1
        else:i+=1;continue
        if _overridden(re.split(r'[=(]',arg,1)[0]):out.append(flag+arg)
    return out

def macro_overrides(opts:list[str],probe:str|None)->list[str]|None:
    """Z3 (Stage-6 fix round 3, S6A3-03): the macros really in effect for the compile options, from the compiler's own
    `-dM -E` probe of them (toolchain()['base']), whatever spelling or vector set them (-D, -Wp,-D, -include,
    -imacros, a response file, CXX itself): every C8_* macro and source switch defined there, except a build or
    diagnostic macro that a plain -DNAME word of the command gives. Any makes a development build. None when the probe
    did not run (no compiler here)."""
    if probe is None:return None
    given=set();i=0
    while i<len(opts):
        w=opts[i]
        if w=='-D'and i+1<len(opts):given.add(re.split(r'[=(]',opts[i+1],1)[0]);i+=2;continue
        if w.startswith('-D')and len(w)>2:given.add(re.split(r'[=(]',w[2:],1)[0])
        i+=1
    names=sorted(set(re.findall(r'^#define ((?:C8_\w+)|(?:'+'|'.join(SOURCE_SWITCHES)+r'))\b',probe,re.M)))
    return [n for n in names if not (n in BUILD_MACROS+DIAGNOSTIC_MACROS and n in given)]

def numerics_sources(opts:list[str])->dict|None:
    """{'defines': the -DC8_NUMERICS* options, 'files': {src/numerics/<f>: sha256}} of an opt-in profile build; None for
    a build without -DC8_NUMERICS."""
    if '-DC8_NUMERICS'not in opts:return None
    root=Path(__file__).resolve().parents[1]
    return {'defines':[w for w in opts if w.startswith('-DC8_NUMERICS')],
            'files':{str(f.relative_to(root)):digest(f)for f in sorted((root/'src/numerics').glob('*.hpp'))}}

def _stdout(args)->str|None:
    try:cp=subprocess.run(args,capture_output=True,text=True,timeout=300);return cp.stdout if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError):return None

def parse_ldd(text:str,prefix:str='libgmp.so')->dict|None:
    """The `ldd` line of the shared library whose name starts with prefix: {'soname', 'path'} (path None when the
    loader does not find it), or None when the executable does not need it."""
    for line in text.splitlines():
        s=line.strip()
        if not s.startswith(prefix):continue
        name,arrow,rest=s.partition('=>');rest=rest.strip()
        path=rest.split(' (')[0].strip()if arrow and rest and not rest.startswith('not found')else None
        return {'soname':name.strip(),'path':path or None}
    return None

def parse_dynamic(text:str)->dict:
    """RPATH and RUNPATH of `readelf -d` output (None when absent)."""
    out={'RPATH':None,'RUNPATH':None}
    for line in text.splitlines():
        m=re.search(r'\((RPATH|RUNPATH)\)\s+Library (?:rpath|runpath): \[(.*)\]',line)
        if m:out[m[1]]=m[2]
    return out

def gmp_library(exe:Path)->dict:
    """The libgmp the executable loads in this environment (ldd honours LD_LIBRARY_PATH, as the worker will), with
    its realpath, sha256 and fat flag, and the executable's RPATH/RUNPATH. Fields stay None where ldd, readelf or nm
    are missing (macOS)."""
    rec={'soname':None,'path':None,'realpath':None,'sha256':None,'fat':None,'rpath':None,'runpath':None,
         'LD_LIBRARY_PATH':os.environ.get('LD_LIBRARY_PATH')}
    ldd=_stdout(['ldd',str(exe)])
    hit=parse_ldd(ldd)if ldd else None
    if hit:
        rec['soname']=hit['soname'];rec['path']=hit['path']
        if hit['path']and Path(hit['path']).is_file():
            real=Path(hit['path']).resolve();rec['realpath']=str(real);rec['sha256']=digest(real)
            tables=[t for t in (_stdout(['nm','-D','--defined-only',str(real)]),_stdout(['nm','--defined-only',str(real)]))if t is not None]
            if tables:rec['fat']=any(re.search(r'\s__gmpn_cpuvec_init$',t,re.M)for t in tables)
    dyn=_stdout(['readelf','-d',str(exe)])
    if dyn is not None:d=parse_dynamic(dyn);rec['rpath'],rec['runpath']=d['RPATH'],d['RUNPATH']
    return rec

def describe(exe:Path):
    """The executable's own --describe record, or None if it does not run here."""
    try:
        cp=subprocess.run([str(exe),'--describe'],capture_output=True,text=True,timeout=120)
        return json.loads(cp.stdout)if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError,ValueError):return None

def _run_text(args,text=''):
    try:cp=subprocess.run(args,input=text,capture_output=True,text=True,timeout=300);return cp.stdout if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError):return None

def toolchain(pre:list[str],backend:str)->dict:
    """What the compiler does with the compile options pre (compiler_options of a command): its --version line and the
    macros of three preprocessor probes (the options alone, <boost/version.hpp> and, for gmp, <gmp.h>). The build
    record (main) and the precision-tool binding (bind_command, Y1) read the compiler and gmp.h the same way."""
    version=(_run_text([pre[0],'--version'])or'').splitlines()[:1]
    probe=lambda text:_run_text([*pre,'-dM','-E','-x','c++','-'],text)
    base,boost,gmph=probe(''),probe('#include <boost/version.hpp>\n'),probe('#include <gmp.h>\n')if backend=='gmp'else None
    macros='\n'.join(x for x in(base,boost,gmph)if x)
    mac=lambda n:(re.search(rf'^#define {n} (.*)$',macros,re.M)or[None,None])[1]
    gmp=None
    if gmph and mac('__GNU_MP_VERSION'):gmp='.'.join(mac(k)for k in('__GNU_MP_VERSION','__GNU_MP_VERSION_MINOR','__GNU_MP_VERSION_PATCHLEVEL'))
    return dict(version=version,base=base,boost=boost,gmph=gmph,mac=mac,gmp=gmp)

# ---------------------------------------------------------------- Y1 (Stage-6 fix round 2): precision tools bound to the worker
# A precision tool (tests/forced_tiers.py, tests/check_points.py, tests/validate.py's class-B build) compiles kernel code
# of its own. Its evidence speaks for a worker only when it is built like that worker and runs with that worker's GMP:
# the same make flag variables and compiler, the worker's GMP_PREFIX words (common.cxx_command), the same gmp.h, and at
# run time the same libgmp (sha256). Before Stage-6 fix round 2 the tools linked plain -lgmp whatever GMP_PREFIX the
# worker was built with (S6A2-01), so their records did not speak for a GMP_PREFIX worker.
GMP_BINDING_SCHEMA='c8-d2-gmp-binding-1'
FLAG_VARS=(('CXX','g++'),('CPPFLAGS',''),('OPTFLAGS','-O3'),('CXXFLAGS',''),('LDFLAGS',''),('LDLIBS',''))  # common.cxx_command's defaults
_SHA=re.compile(r'[0-9a-f]{64}')

class BindingRefused(ValueError):
    """A precision tool that cannot be bound to its target worker: nothing is compiled, or the compiled tool is not run."""

def worker_record(exe:Path)->dict:
    """exe's build record (bin/<exe>.build.json), which must describe exe itself (executable_sha256)."""
    exe=Path(exe);br=exe.with_name(exe.name+'.build.json')
    if not exe.is_file():raise BindingRefused(f'{exe}: the target worker does not exist (build it with make)')
    if not br.is_file():raise BindingRefused(f'{exe}: no build record {br.name} (build the worker with make)')
    try:rec=json.loads(br.read_bytes())
    except ValueError as e:raise BindingRefused(f'{br}: not JSON ({e})')
    if not isinstance(rec,dict)or rec.get('schema')!='c8-d2-build-record-1':raise BindingRefused(f'{br}: not a c8-d2-build-record-1 build record')
    if rec.get('executable_sha256')!=digest(exe):raise BindingRefused(f'{br} describes another executable than {exe} (sha256 differs): rebuild the worker (make -B)')
    return rec

def tool_flags()->dict:
    """The make flag variables a common.cxx_command command takes from this environment, as words."""
    return {k:shlex.split(os.environ.get(k,d))for k,d in FLAG_VARS}

def gmp_target(exe:Path,backend:str='gmp')->dict:
    """Y1: what a precision tool must share with the target worker exe, from exe's build record. The worker must be a
    production build of the exact path of that backend (NUMERICS exact, no diagnostic kind, no development option) and
    the record must name its compiler; for gmp also GMP_PREFIX (None when unset), the gmp.h version and configuration
    (__GMP_CC, __GMP_CFLAGS) and the sha256 of the libgmp the worker resolved when it was built. A GMP_PREFIX in this
    environment (make test-full GMP_PREFIX=..., which make does not track) must be the record's. BindingRefused
    otherwise, before anything is compiled."""
    rec=worker_record(exe);why=[]
    if rec.get('backend')!=backend:why.append(f'its backend is {rec.get("backend")!r}, not {backend}')
    if (rec.get('NUMERICS')or'exact')!='exact':why.append(f'it is a numerics-profile build ({rec.get("NUMERICS")}); the precision tools test the exact path')
    if rec.get('diagnostic'):why.append(f'it is a diagnostic build ({rec.get("diagnostic")})')
    if rec.get('development')or rec.get('parameter_overrides')or rec.get('macro_overrides'):why.append('it is a development build (parameter or macro overrides)')
    if not isinstance(rec.get('macro_overrides'),list):why.append('its record does not show the macros in effect (macro_overrides: a record written before Stage-6 fix '
                                                                 'round 3, or the compiler probe did not run; Z3): rebuild the worker with make')
    if not rec.get('compiler'):why.append('its record names no compiler version')
    prefix=rec.get('GMP_PREFIX')or None;lib=hdr=None
    if backend=='gmp':
        lib=rec.get('gmp_library')if isinstance(rec.get('gmp_library'),dict)else{};hdr=rec.get('gmp_header')if isinstance(rec.get('gmp_header'),dict)else{}
        if not _SHA.fullmatch(str(lib.get('sha256')or'')):why.append('its record names no sha256 of the libgmp it resolves (gmp_library.sha256: ldd was unavailable at build time)')
        if not rec.get('gmp_version')or not hdr.get('cc'):why.append('its record names no gmp.h version and configuration (gmp_version, gmp_header)')
        envp=(os.environ.get('GMP_PREFIX')or'').strip()or None
        if envp is not None and envp!=prefix:why.append(f'this environment names GMP_PREFIX={envp}, the worker was built with GMP_PREFIX={prefix or "(unset)"} '
                                                       '(make does not track the knob: rebuild with make -B gmp GMP_PREFIX=..., or unset it)')
    if why:raise BindingRefused(f'{exe}: the precision tool cannot be bound to this worker (Y1): '+'; '.join(why))
    return {'schema':GMP_BINDING_SCHEMA,'worker':str(Path(exe).resolve()),'worker_sha256':rec['executable_sha256'],'backend':backend,
            'GMP_PREFIX':prefix if backend=='gmp'else None,'compiler':rec['compiler'],'compiler_macro_version':rec.get('compiler_macro_version'),
            'flags':{k:shlex.split(rec.get(k)or'')for k,_ in FLAG_VARS},'BOOST_VERSION':rec.get('BOOST_VERSION'),'gmp_version':rec.get('gmp_version')if backend=='gmp'else None,
            'gmp_header':{k:hdr.get(k)for k in('cc','cflags')}if backend=='gmp'else None,
            'gmp_library':{k:lib.get(k)for k in('soname','realpath','sha256')}if backend=='gmp'else None}

def bind_command(command:list[str],target:dict)->dict:
    """Y1: the precision tool's compile command (common.cxx_command with gmp_prefix=target['GMP_PREFIX']) against the
    target (gmp_target): the make flag variables of this environment equal the worker's, the command carries the
    GMP_PREFIX words, and its own compile options give the worker's compiler (--version line, __VERSION__), the
    worker's Boost (BOOST_VERSION, Z1: Boost through CPATH or CPLUS_INCLUDE_PATH is not in the flags) and, for gmp, the
    worker's gmp.h (version, __GMP_CC, __GMP_CFLAGS). Returns the evidence; BindingRefused (nothing compiled)."""
    why=[];fl=tool_flags()
    for k,_ in FLAG_VARS:
        if fl[k]!=target['flags'][k]:why.append(f'{k} is {" ".join(fl[k])!r} here, {" ".join(target["flags"][k])!r} in the worker\'s build')
    p=target['GMP_PREFIX']
    if p and not (f'-I{p}/include'in command and f'-Wl,-rpath,{p}/lib'in command):why.append(f'the command lacks the GMP_PREFIX={p} include and rpath words')
    tc=toolchain(compiler_options(command),target['backend']);mac=tc['mac']
    got={'compiler':tc['version'][0]if tc['version']else None,'compiler_macro_version':(mac('__VERSION__')or'').strip('"')or None,'BOOST_VERSION':mac('BOOST_VERSION')}
    if target['backend']=='gmp':got.update(gmp_version=tc['gmp'],gmp_header={'cc':(mac('__GMP_CC')or'').strip('"')or None,'cflags':(mac('__GMP_CFLAGS')or'').strip('"')or None})
    for k in got:
        if got[k]!=target[k]:why.append(f'{k}: {got[k]!r} for the tool, {target[k]!r} for the worker')
    if why:raise BindingRefused(f'the precision tool is not built like {target["worker"]} (Y1): '+'; '.join(why))
    return dict(got,flags=fl,GMP_PREFIX_words=bool(p))

def check_linked(tool:Path,target:dict,worker_now:bool=True)->dict:
    """Y1: the libgmp the compiled tool resolves here (gmp_library: ldd in this environment, as the tool runs) must be
    the one the worker's build record names (sha256), and, with worker_now, the worker itself must resolve that library
    here too (an environment that swaps libgmp is refused). BindingRefused when ldd cannot tell (no ldd, as on macOS),
    or either differs."""
    want=target['gmp_library']['sha256'];why=[]
    def seen(exe,what):
        g=gmp_library(Path(exe))
        if g.get('sha256')!=want:
            why.append(f'{what} resolves libgmp {g.get("realpath")or g.get("path")or "(unresolved: no ldd, or no libgmp)"} '
                       f'(sha256 {str(g.get("sha256"))[:12]}...), not the worker\'s recorded {want[:12]}...')
        return {k:g.get(k)for k in('soname','path','realpath','sha256','rpath','runpath','LD_LIBRARY_PATH')}
    out={'tool':seen(tool,f'the tool {Path(tool).name}')}
    if worker_now:out['worker_now']=seen(target['worker'],f'the worker {Path(target["worker"]).name}')
    if why:raise BindingRefused('the precision tool does not run with the worker\'s GMP (Y1): '+'; '.join(why))
    return dict(out,want_sha256=want,match=True)

# ---------------------------------------------------------------- Z1 (Stage-6 fix round 3): precision tools bound to the worker's sources
# Y1 bound the flags, compiler and GMP, not the code: forced_tiers.py and check_points.py compiled the kernel of the
# current checkout, so after an edit of src/ without a rebuild, or with an older --worker of the same flags and GMP,
# their records named a worker whose code they had not tested (S6A3-01). Now the tool is compiled from a read-only
# snapshot of src/ and its own sources, and the worker is first rebuilt in that snapshot with its build record's
# command, in this environment, and must come out byte for byte (sha256) as the worker: the snapshot's sources and this
# environment's compiler, headers (Boost through CPATH included) and libraries are then the ones that made the worker,
# and the tool is compiled from the same files in the same environment (the approach of tests/numerics_flags.py's X2).
SOURCE_BINDING_SCHEMA='c8-d2-source-binding-1'
INCLUDE_ENV=('CPATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH','LIBRARY_PATH','GCC_EXEC_PREFIX','COMPILER_PATH')
PACKAGE=Path(__file__).resolve().parents[1]

def package_path(src)->str:
    """src (absolute, or relative to the package) as a package-relative path; BindingRefused outside the package."""
    p=Path(src);p=p if p.is_absolute()else PACKAGE/p
    try:return p.resolve().relative_to(PACKAGE.resolve()).as_posix()
    except ValueError:raise BindingRefused(f'{src}: a precision-tool source outside the package {PACKAGE}')

def source_snapshot(dest:Path,tool_sources=())->dict:
    """Z1: a read-only copy of every file of src/ (recursively) and of tool_sources (package paths) in dest, in the
    package layout (dest is replaced). {'files': {path: sha256}, 'sha256': the digest of that map} (the form of
    tests/numerics_flags.py's snapshot)."""
    dest=Path(dest)
    if dest.exists():shutil.rmtree(dest)
    rels=sorted({*(f.relative_to(PACKAGE).as_posix()for f in (PACKAGE/'src').rglob('*')if f.is_file()and '__pycache__'not in f.parts and f.name!='.DS_Store'),
                 *map(package_path,tool_sources)})
    files={}
    for rel in rels:
        d=dest/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PACKAGE/rel,d);d.chmod(0o444);files[rel]=digest(d)
    return {'files':files,'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}

# W3 (Stage-6 fix round 4, S6A4-03): the build record's command ran in its build_directory B, and reproduce_worker runs it
# in the snapshot, so a relative word (CXX=../gcc/bin/g++, CPPFLAGS=-I../boost_1_77_0, LDFLAGS=-Llib, a relative link
# input, CPATH=../boost_1_77_0/include) named something else there and a supported build could not be reproduced. The
# words are NOT rewritten to absolute paths (a real compiler embeds the include path it found, e.g. in the __FILE__ of
# a Boost assertion, so the bytes would change): instead the snapshot gets the parents those words climb to ('..'),
# private directories inside the snapshot root, and every name a relative word reaches outside the snapshot's src/ and
# tool sources becomes a symlink to the same name under B. Each relative word then resolves from the snapshot to the
# file it named in B, word for word, and the byte-identity requirement is unchanged. The precision tool itself is
# compiled in the caller's working directory, so a binding whose make flags or include environment hold relative words
# is refused unless that directory is B (bound_tool_command).
PATH_OPTIONS=tuple(sorted(('-isystem','-iquote','-idirafter','-iprefix','-iwithprefixbefore','-iwithprefix','-isysroot','-imultilib','-include','-imacros',
                           '--sysroot=','-I','-L','-B','-F'),key=len,reverse=True))  # options whose glued value is a path (longest first)
def list_env(compiler:str)->tuple:
    """The colon lists a compile searches relative to its working directory: the include and library variables, and
    PATH when the compiler is named without '/'."""
    return INCLUDE_ENV+(()if '/'in str(compiler)else('PATH',))
SNAPSHOT_UP='.c8d2-snapshot-parent'   # the private parent directories of a nested snapshot

def _relative(v:str)->bool:
    """A relative path that names something other than the working directory itself ('.', './')."""
    return bool(v)and not v.startswith('/')and bool(Path(v).parts)

def relative_words(words,compiler:int=1)->list[str]:
    """The relative paths a compile command's words name, in order and once: the first `compiler` words (CXX, e.g.
    'ccache g++') only when they contain '/' (else a program found through PATH), every other word that is not an
    option (a source, a link input, the value of a separated option such as -I DIR), the value of a glued path option
    (-I, -isystem, -iquote, -idirafter, -L, -B, --sysroot=, -include, ...), the parts of -Wl,/-Wp,/-Wa, lists, a value
    after '=' that contains '/', and a response file @FILE."""
    out=[]
    def take(v):
        if _relative(v)and v not in out:out.append(v)
    def word(w):
        if not w.startswith('-'):take(w[1:]if w.startswith('@')else w);return
        if w.startswith(('-Wl,','-Wp,','-Wa,')):
            for part in w.split(',')[1:]:word(part)if part.startswith('-')else take(part)
            return
        for pre in PATH_OPTIONS:
            if w.startswith(pre)and len(w)>len(pre):take(w[len(pre):]);return
        if '='in w and '/'in w.split('=',1)[1]:take(w.split('=',1)[1])
    words=[str(w)for w in words]
    for i,w in enumerate(words):
        if i<compiler:
            if '/'in w:take(w)
            continue
        word(w)
    return out

def compiler_words(rec:dict)->int:
    """How many leading words of the record's command are CXX (C8B_CXX, as the Makefile exported it); 1 without it."""
    try:return max(1,len(shlex.split(rec.get('CXX')or'')))
    except ValueError:return 1

def relative_env(env=None,names=INCLUDE_ENV)->dict:
    """{variable: its relative entries} of the colon lists names (empty and '.' entries skipped)."""
    e=os.environ if env is None else env
    out={k:[d for d in (e.get(k)or'').split(os.pathsep)if _relative(d)]for k in names}
    return {k:v for k,v in out.items()if v}

def climb(rel:str)->int:
    """How far above its start a relative path climbs lexically ('a/../../b' climbs 1)."""
    depth=up=0
    for c in Path(rel).parts:
        if c=='.':continue
        depth+=-1 if c=='..'else 1;up=max(up,-depth)
    return up

def build_directory(rec:dict)->Path|None:
    """The directory the record's command ran in (W3), physical; None for a record written before fix round 4."""
    d=rec.get('build_directory')
    return Path(os.path.realpath(d))if isinstance(d,str)and d.startswith('/')else None

def snapshot_root(snap:Path,levels:int)->Path:
    """The package-layout root of a snapshot in snap that relative words may climb `levels` parents above: snap itself
    for 0, else snap/SNAPSHOT_UP/.../SNAPSHOT_UP (levels deep), whose parents up to snap are private."""
    return Path(snap).joinpath(*[SNAPSHOT_UP]*levels)

def mirror(root:Path,top:Path,base:Path,rel:str)->str|None:
    """W3: make rel, resolved from the snapshot root (the reproduction's working directory), name what it names from
    base (the build directory B): walk its leading components through the snapshot (root, its private parents up to
    top for '..', and the tool-source directories) and symlink the first name that leaves the snapshot to the same name
    under base. src/ is the snapshot's own (every file copied); a path into it is left alone. Returns the link made (a
    path relative to top) or None. BindingRefused for a path that climbs above top or names a private parent."""
    cur,cb=Path(root),Path(base);top=Path(top);first=True
    for c in Path(rel).parts:
        if c=='.':continue
        if c=='..':
            if cur==top:raise BindingRefused(f'the relative word {rel!r} climbs above the snapshot\'s private parents (W3)')
            cur,cb,first=cur.parent,cb.parent,False;continue
        if c==SNAPSHOT_UP:raise BindingRefused(f'the relative word {rel!r} names the snapshot\'s private directory {SNAPSHOT_UP} (W3)')
        q=cur/c
        if q.is_symlink():return None
        if q.exists():
            if not q.is_dir()or(first and cur==root and c=='src'):return None   # the snapshot's own sources
            cur,cb,first=q,cb/c,False;continue
        t=cb/c
        if not os.path.lexists(t):return None   # nothing there from B either
        q.symlink_to(t);return q.relative_to(top).as_posix()
    return None

def reproduce_worker(exe:Path,snap:Path,out:Path,top:Path|None=None)->dict:
    """Z1: exe rebuilt in the snapshot snap (cwd) with its build record's command, the output exchanged for out, must be
    byte-identical to exe (sha256). BindingRefused for a record whose command is not a Makefile build of
    src/c8d2_integrate.cpp (relative, one -o), a failed rebuild, or another sha256: a stale worker (src/ changed since it
    was built), or an environment that compiles differently (another compiler, other headers, other libraries).
    W3: the relative words of the command and of the include environment (list_env) keep the meaning they had in the
    record's build_directory: each is mirrored into the snapshot (mirror; top: the private root the snapshot's parents
    lie in, default snap itself, i.e. no climbing). A record without build_directory (written before fix round 4) is
    reproduced only when it holds no relative word besides its source."""
    exe=Path(exe);rec=worker_record(exe);cmd=list(rec.get('command')or[])
    src=[i for i,w in enumerate(cmd)if str(w).endswith('c8d2_integrate.cpp')]
    if len(src)!=1 or cmd[src[0]]!='src/c8d2_integrate.cpp'or cmd.count('-o')!=1 or cmd.index('-o')+2>len(cmd):
        raise BindingRefused(f'{exe}: its build record\'s command is not a Makefile build of src/c8d2_integrate.cpp (relative, one -o), so it cannot be '
                             f'reproduced from the sources (Z1): {cmd}')
    o=cmd.index('-o');rest=[w for i,w in enumerate(cmd)if i not in(src[0],o,o+1)]
    rel=relative_words(rest,compiler_words(rec))+[d for v in relative_env(names=list_env(cmd[0])).values()for d in v];links=[]
    if rel:
        B=build_directory(rec)
        if B is None:raise BindingRefused(f'{exe}: its build record names no build_directory (a record written before Stage-6 fix round 4) and its command or '
                                          f'the include environment holds relative paths {rel[:6]}, whose meaning is then unknown (W3): rebuild the worker with make')
        for r in rel:
            m=mirror(snap,Path(top)if top else snap,B,r)
            if m:links.append({'link':m,'word':r})
    cmd[o+1]=str(out);t0=time.time()
    try:cp=subprocess.run(cmd,cwd=snap,capture_output=True,text=True)
    except OSError as e:raise BindingRefused(f'{exe}: rebuilding it from the source snapshot failed to start (Z1): {e}')
    if cp.returncode:raise BindingRefused(f'{exe}: rebuilding it from the source snapshot with its build record\'s command failed (Z1): {cp.stderr[-1500:]}')
    got=digest(out);Path(out).unlink()
    if got!=rec['executable_sha256']:
        raise BindingRefused(f'{exe}: its build record\'s command on the current sources, in this environment, gives sha256 {got[:12]}..., not the worker\'s '
                             f'{rec["executable_sha256"][:12]}... (Z1): the worker is stale (src/ changed since it was built: rebuild it with make) or this '
                             'environment compiles differently (another compiler, other headers such as a Boost through CPATH or CPLUS_INCLUDE_PATH, other '
                             'libraries); the precision tool would not test the worker\'s code')
    return {'executable':str(exe.resolve()),'sha256':got,'reproduced_sha256':got,'reproduced':True,'seconds':round(time.time()-t0,1),
            'command':cmd[:o+1]+['<reproduced>']+cmd[o+2:],'build_directory':rec.get('build_directory'),'relative_words':rel,'mirrored':links}

def bound_tool_command(sources,output,worker:Path,backend:str,defines=(),libs=('-lquadmath',),snapshot=None)->tuple[list[str],dict]:
    """Y1 + Z1: (the compile command of a precision tool bound to worker, the binding record): gmp_target, the command
    with the worker's GMP_PREFIX words (common.cxx_command) and bind_command (flags, compiler, Boost, gmp.h; nothing is
    compiled before these pass); then (Z1) the read-only source snapshot (default: <output>.snapshot beside output) of
    src/ and the tool's sources, which the command compiles, and the worker reproduced there byte for byte
    (reproduce_worker). The binding gains source_binding. Compile the command, then verify_tool.
    W3: the tool is compiled (and bind_command probes the compiler) in the caller's working directory, so when the make
    flags or the include environment hold relative words the caller must run in the worker's build_directory, where
    they meant what the worker's build read; anywhere else the binding is refused before anything is compiled. The
    snapshot is nested (snapshot_root) as deep as the worker's relative words climb, so their parents are private."""
    from common import cxx_command
    t=gmp_target(worker,backend);output=Path(output);rels=[package_path(s)for s in sources];rec=worker_record(worker);B=build_directory(rec)
    fl=tool_flags();trel=relative_words([w for k,_ in FLAG_VARS for w in fl[k]],len(fl['CXX']))+[d for v in relative_env().values()for d in v]
    if trel and (B is None or Path(os.path.realpath(os.getcwd()))!=B):
        raise BindingRefused(f'the make flags or the include environment hold relative paths {trel[:6]}, which the worker {Path(worker).name} was built with in '
                             f'{rec.get("build_directory")or "(a build directory its record does not name: rebuild it with make)"}; this process runs in {os.getcwd()}, '
                             'where they name other files (W3): run the precision tool from the worker\'s build directory')
    rc=list(rec.get('command')or['']);levels=max([climb(r)for r in relative_words(rc,compiler_words(rec))+[d for v in relative_env(names=list_env(rc[0])).values()for d in v]]+[0])
    snap=Path(snapshot)if snapshot else output.with_name(output.name+'.snapshot');root=snapshot_root(snap,levels)
    if snap.exists():shutil.rmtree(snap)
    cmd=cxx_command([root/r for r in rels],output,defines,libs,gmp_prefix=t['GMP_PREFIX']);comp=bind_command(cmd,t)
    info=source_snapshot(root,rels);rep=reproduce_worker(worker,root,root.with_name(root.name+'.reproduced'),top=snap)
    return cmd,dict(t,compile=comp,source_binding={'schema':SOURCE_BINDING_SCHEMA,'snapshot':info,'tool_sources':rels,'snapshot_dir':str(root),'reproduction':rep,
                                                   'snapshot_parent_levels':levels,'include_environment':{k:os.environ.get(k)for k in INCLUDE_ENV},
                                                   'rule':'the worker rebuilt in the read-only source snapshot with its build record\'s command, in this environment, is '
                                                          'byte-identical to it (sha256); the tool is compiled from the same snapshot in the same environment; '
                                                          'relative words keep the meaning they had in the worker\'s build directory (W3)'})

def verify_tool(tool:Path,binding:dict)->dict:
    """Y1: after the compile: a gmp tool must resolve the worker's libgmp (check_linked); the binding record gains
    'linked'. A decimal tool links no GMP and is returned unchanged."""
    if binding['backend']=='gmp':binding['linked']=check_linked(tool,binding)
    return binding

def main(exe:Path,backend:str,command:list[str])->dict:
    e=os.environ
    if not command or not any(w.endswith('c8d2_integrate.cpp')for w in command):raise SystemExit('build_record.py: the compile command (after --) must name src/c8d2_integrate.cpp')
    pre=compiler_options(command)
    tc=toolchain(pre,backend);version,base,boost,gmph,mac,gmp=(tc[k]for k in('version','base','boost','gmph','mac','gmp'))
    present=all(f in pre for f in REQUIRED_CXXFLAGS)
    ordered=last(pre,('-ffp-contract=',))=='-ffp-contract=off'and last(pre,('-ffast-math','-fno-fast-math'))=='-fno-fast-math'
    macro_ok=None if base is None else (mac('_OPENMP')is not None and mac('__FAST_MATH__')is None and (mac('__FINITE_MATH_ONLY__')or'0')=='0')
    mo=macro_overrides(pre,base)  # Z3: the C8_* macros and source switches really in effect, however they were set
    rec={'schema':'c8-d2-build-record-1','executable':exe.name,'backend':backend,'executable_sha256':digest(exe),
         'command':command,'compiler_options':pre,'compiler':version[0]if version else None,'compiler_macro_version':(mac('__VERSION__')or'').strip('"')or None,
         'CXX':e.get('C8B_CXX'),'CPPFLAGS':e.get('C8B_CPPFLAGS'),'OPTFLAGS':e.get('C8B_OPTFLAGS'),'CXXFLAGS':e.get('C8B_CXXFLAGS'),
         'required_flags':e.get('C8B_REQUIRED'),'LDFLAGS':e.get('C8B_LDFLAGS'),'LDLIBS':e.get('C8B_LDLIBS'),
         'NUMERICS':e.get('C8B_NUMERICS'),'numerics_sources':numerics_sources(pre),'parameter_overrides':parameter_overrides(pre),
         'macro_overrides':mo,'development':bool(parameter_overrides(pre))or bool(mo),'GMP_PREFIX':e.get('C8B_GMP_PREFIX'),'diagnostic':diagnostic_kind(pre),'describe':describe(exe),
         'required_flags_present':present and ordered and macro_ok is not False,
         'macros':{k:mac(k)for k in('_OPENMP','__FAST_MATH__','__FINITE_MATH_ONLY__','__OPTIMIZE__')},
         'BOOST_LIB_VERSION':(mac('BOOST_LIB_VERSION')or'').strip('"')or None,'BOOST_VERSION':mac('BOOST_VERSION'),'gmp_version':gmp,
         'gmp_header':{'cc':(mac('__GMP_CC')or'').strip('"')or None,'cflags':(mac('__GMP_CFLAGS')or'').strip('"')or None}if backend=='gmp'else None,
         'gmp_library':gmp_library(exe)if backend=='gmp'else None,
         'optimized':(mac('__OPTIMIZE__')is not None)if base is not None else None,
         'preprocessor_probe':{'flags':base is not None,'boost':boost is not None,'gmp':gmph is not None if backend=='gmp'else None},
         'build_directory':os.getcwd(),  # W3: where the command ran (make's directory): its relative words are relative to it
         'host':socket.gethostname(),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    if rec['optimized']is False:print(f'warning: {exe} is built without -O optimization ({shlex.join(pre)}); it is correct but several times slower',file=sys.stderr)
    if mo:print(f'warning: {exe} is a development build: macros {mo} are in effect beyond the Makefile\'s own -D words (Z3); plan refuses it',file=sys.stderr)
    if mo is None:print(f'warning: {exe}: the compiler probe did not run here, so macro_overrides is unknown (null)',file=sys.stderr)
    if not rec['required_flags_present']:print(f'warning: {exe} was not compiled with the required flags {" ".join(REQUIRED_CXXFLAGS)} in effect ({shlex.join(pre)})',file=sys.stderr)
    out=exe.with_name(exe.name+'.build.json')
    if out.exists():out.unlink()
    out.write_text(json.dumps(rec,indent=2)+'\n');return rec

if __name__=='__main__':
    a=sys.argv[1:]
    if len(a)<4 or a[1]not in('decimal','gmp')or a[2]!='--':sys.exit('usage: build_record.py bin/<exe> decimal|gmp -- <compile command>')
    r=main(Path(a[0]),a[1],a[3:]);lib=(r.get('gmp_library')or{}).get('realpath')
    print(f'{a[0]}.build.json: {r["compiler"]}, Boost {r["BOOST_LIB_VERSION"]}, GMP {r["gmp_version"]}{f" ({lib})"if lib else""}, optimized={r["optimized"]}')
