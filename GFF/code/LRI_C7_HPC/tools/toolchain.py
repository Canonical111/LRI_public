#!/usr/bin/env python3
"""One compile-command builder for every helper that compiles C++; it mirrors the Makefile.
Reads CXX (default g++), CPPFLAGS, CXXFLAGS (default -O3 -g, replaced by an explicit opt list) and LDFLAGS.
REQUIRED is always appended after the optimisation flags. GCC 8 gets -lstdc++fs; RPATH=1 embeds the libgomp directory.
"""
from __future__ import annotations
import functools, os, re, shlex, subprocess, sys
REQUIRED=['-std=c++17','-fopenmp','-fno-fast-math','-ffp-contract=off']

def cxx()->list[str]:return shlex.split(os.environ.get('CXX') or 'g++')
def _out(args:list[str])->str|None:
    try:return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,universal_newlines=True,check=True).stdout
    except (OSError,subprocess.CalledProcessError):return None
@functools.lru_cache(maxsize=None)
def _major(c:tuple)->int|None:
    v=_out(list(c)+['--version'])
    if v is None or 'clang' in v.lower():return None # -dumpversion is only meaningful for GCC.
    m=re.match(r'\s*(\d+)',_out(list(c)+['-dumpversion']) or '');return int(m.group(1)) if m else None
def gcc_major()->int|None:return _major(tuple(cxx()))
def rpath_flags()->list[str]:
    if os.environ.get('RPATH')!='1':return []
    so=(_out(cxx()+['-print-file-name=libgomp.so']) or '').strip()
    if not os.path.isabs(so):raise RuntimeError('RPATH=1: '+' '.join(cxx())+' -print-file-name=libgomp.so gave no absolute path')
    return ['-Wl,-rpath,'+os.path.dirname(so)]
def compile_cmd(sources,output,opt=None,extra=())->list[str]:
    m=gcc_major();env=os.environ.get
    return (cxx()+shlex.split(env('CPPFLAGS',''))+(list(opt) if opt is not None else shlex.split(env('CXXFLAGS','-O3 -g')))+REQUIRED+list(extra)
            +[str(s) for s in sources]+['-o',str(output)]+shlex.split(env('LDFLAGS',''))+['-lquadmath']+(['-lstdc++fs'] if m is not None and m<9 else [])+rpath_flags())
def compiler_version()->str:
    v=_out(cxx()+['--version'])
    if not v:raise RuntimeError('cannot run '+' '.join(cxx())+' --version')
    return v.splitlines()[0]
if __name__=='__main__':
    root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(compiler_version());print(' '.join(map(shlex.quote,compile_cmd([os.path.join(root,'src/c7_integrate.cpp')],os.path.join(root,'bin/c7_integrate')))));sys.exit(0)
