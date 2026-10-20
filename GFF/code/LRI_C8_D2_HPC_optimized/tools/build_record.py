#!/usr/bin/env python3
"""Write bin/<exe>.build.json after `make` links an executable (A-L13).

  build_record.py bin/c8d2_gmp gmp -- <the exact compile command the Makefile ran>

Records the command, the compiler version, the make flag variables (C8B_* exported by the Makefile, which cannot be
overridden from the command line), and what the compiler really does with the command: every compiler option of the
command, wherever it sits (all words except the source file, `-o` and its argument, and link-only words), is passed to
preprocessor probes for __OPTIMIZE__ (a warning and optimized:false for an unoptimized build), BOOST_LIB_VERSION, the
GMP version, _OPENMP, __FAST_MATH__ and __FINITE_MATH_ONLY__. required_flags_effective is true only if every required
numerical flag is present, -ffp-contract=off and -fno-fast-math are the last of their kind, _OPENMP is defined and no
fast-math macro is. `production.py plan` records the file.
"""
from __future__ import annotations
import json,os,re,shlex,socket,subprocess,sys,time
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

def main(exe:Path,backend:str,command:list[str])->dict:
    e=os.environ
    if not command or not any(w.endswith('c8d2_integrate.cpp')for w in command):raise SystemExit('build_record.py: the compile command (after --) must name src/c8d2_integrate.cpp')
    pre=compiler_options(command)
    def run(args,text=''):
        try:cp=subprocess.run(args,input=text,capture_output=True,text=True,timeout=300);return cp.stdout if cp.returncode==0 else None
        except (OSError,subprocess.SubprocessError):return None
    version=(run([pre[0],'--version'])or'').splitlines()[:1]
    probe=lambda text:run([*pre,'-dM','-E','-x','c++','-'],text)
    base,boost,gmph=probe(''),probe('#include <boost/version.hpp>\n'),probe('#include <gmp.h>\n')if backend=='gmp'else None
    macros='\n'.join(x for x in(base,boost,gmph)if x)
    mac=lambda n:(re.search(rf'^#define {n} (.*)$',macros,re.M)or[None,None])[1]
    gmp=None
    if gmph and mac('__GNU_MP_VERSION'):gmp='.'.join(mac(k)for k in('__GNU_MP_VERSION','__GNU_MP_VERSION_MINOR','__GNU_MP_VERSION_PATCHLEVEL'))
    present=all(f in pre for f in REQUIRED_CXXFLAGS)
    ordered=last(pre,('-ffp-contract=',))=='-ffp-contract=off'and last(pre,('-ffast-math','-fno-fast-math'))=='-fno-fast-math'
    macro_ok=None if base is None else (mac('_OPENMP')is not None and mac('__FAST_MATH__')is None and (mac('__FINITE_MATH_ONLY__')or'0')=='0')
    rec={'schema':'c8-d2-build-record-1','executable':exe.name,'backend':backend,'executable_sha256':digest(exe),
         'command':command,'compiler_options':pre,'compiler':version[0]if version else None,'compiler_macro_version':(mac('__VERSION__')or'').strip('"')or None,
         'CXX':e.get('C8B_CXX'),'CPPFLAGS':e.get('C8B_CPPFLAGS'),'OPTFLAGS':e.get('C8B_OPTFLAGS'),'CXXFLAGS':e.get('C8B_CXXFLAGS'),
         'required_flags':e.get('C8B_REQUIRED'),'LDFLAGS':e.get('C8B_LDFLAGS'),'LDLIBS':e.get('C8B_LDLIBS'),
         'required_flags_present':present and ordered and macro_ok is not False,
         'macros':{k:mac(k)for k in('_OPENMP','__FAST_MATH__','__FINITE_MATH_ONLY__','__OPTIMIZE__')},
         'BOOST_LIB_VERSION':(mac('BOOST_LIB_VERSION')or'').strip('"')or None,'BOOST_VERSION':mac('BOOST_VERSION'),'gmp_version':gmp,
         'optimized':(mac('__OPTIMIZE__')is not None)if base is not None else None,
         'preprocessor_probe':{'flags':base is not None,'boost':boost is not None,'gmp':gmph is not None if backend=='gmp'else None},
         'host':socket.gethostname(),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    if rec['optimized']is False:print(f'warning: {exe} is built without -O optimization ({shlex.join(pre)}); it is correct but several times slower',file=sys.stderr)
    if not rec['required_flags_present']:print(f'warning: {exe} was not compiled with the required flags {" ".join(REQUIRED_CXXFLAGS)} in effect ({shlex.join(pre)})',file=sys.stderr)
    out=exe.with_name(exe.name+'.build.json')
    if out.exists():out.unlink()
    out.write_text(json.dumps(rec,indent=2)+'\n');return rec

if __name__=='__main__':
    a=sys.argv[1:]
    if len(a)<4 or a[1]not in('decimal','gmp')or a[2]!='--':sys.exit('usage: build_record.py bin/<exe> decimal|gmp -- <compile command>')
    r=main(Path(a[0]),a[1],a[3:]);print(f'{a[0]}.build.json: {r["compiler"]}, Boost {r["BOOST_LIB_VERSION"]}, GMP {r["gmp_version"]}, optimized={r["optimized"]}')
