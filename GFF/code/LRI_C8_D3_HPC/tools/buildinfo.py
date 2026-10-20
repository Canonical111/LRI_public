#!/usr/bin/env python3
"""Build helper called by the Makefile (PLAN.md C.8).

  buildinfo.py check TOKEN...                                     refuse user flags that override the strict
                                                                  numerical flags
  buildinfo.py write BINARY CXX CPPFLAGS BOOST_ACCEPT -- CMD...   write <BINARY>.buildinfo.json after a build

The record (schema c8-d3-buildinfo-1), for bin/c8d3_* and bin/ref/c7d3_* alike: the binary's name and path, the exact
compile command, the compiler's first --version line, boost_version (an integer, e.g. 107700, probed with the build's
CXX and CPPFLAGS) and boost_accept (the BOOST_ACCEPT the build was given, or null), --describe, sha256, "backend" and
"libprobe" (tools/libprobe.py; Linux only). "backend" is gmp when the command carries -DC7_USE_GMP and decimal
otherwise; it must agree with --describe's mp_backend (gmp350 or decimal300, kernel.hpp) or the write fails (exit 2,
and make's .DELETE_ON_ERROR removes the binary).

Arguments are positional and parsed by hand, so flag values that start with '-' (CPPFLAGS=-I...) are data.
"""
from __future__ import annotations
import json,shlex,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import digest,host_info,strict_conflicts
import libprobe

SCHEMA='c8-d3-buildinfo-1'
BACKEND_OF_MP={'gmp350':'gmp','decimal300':'decimal'}

def out(c,stdin=None):
    try:cp=subprocess.run(c,input=stdin,capture_output=True,text=True,timeout=120);return cp.stdout if cp.returncode==0 else None
    except (OSError,subprocess.SubprocessError):return None

def backend_of(cmd)->str:return 'gmp' if '-DC7_USE_GMP' in cmd else 'decimal'

def main(argv)->int:
    if argv[:1]==['check']:
        bad=strict_conflicts(argv[1:])
        if bad:print('C8: refusing compiler/linker flags that override the strict numerical flags (-std=c++17 -fopenmp -ffp-contract=off -fno-fast-math): '+' '.join(bad),file=sys.stderr);return 2
        return 0
    if argv[:1]==['write']and len(argv)>=6 and argv[5]=='--':
        binary=Path(argv[1]);cxx=shlex.split(argv[2]);cppflags=shlex.split(argv[3]);accept=argv[4]or None;cmd=argv[6:]
        ver=out([*cxx,'--version']);boost=out([*cxx,*cppflags,'-x','c++','-E','-P','-'],'#include <boost/version.hpp>\nBOOST_VERSION\n')
        last=boost.split()[-1]if boost and boost.split()else''
        try:
            cp=subprocess.run([str(binary.resolve()),'--describe'],capture_output=True,text=True,timeout=120)
            desc=json.loads(cp.stdout)if cp.returncode==0 else None
        except (OSError,ValueError,subprocess.SubprocessError):desc=None
        if desc is None:print(f'C8: {binary} --describe failed',file=sys.stderr);return 2
        backend=backend_of(cmd);mp=desc.get('mp_backend')
        if BACKEND_OF_MP.get(mp)!=backend:
            print(f'C8: {binary}: the command says backend {backend} but --describe reports mp_backend {mp!r}',file=sys.stderr);return 2
        info={'schema':SCHEMA,'binary':binary.name,'path':str(binary),'command':cmd,'compiler_version':ver.splitlines()[0]if ver else None,
              'boost_version':int(last)if last.isdigit()else None,'boost_accept':accept,'describe':desc,'sha256':digest(binary),'backend':backend,
              'libprobe':libprobe.probe(binary),'host':host_info()}
        binary.with_name(binary.name+'.buildinfo.json').write_text(json.dumps(info,indent=2)+'\n');return 0
    print(__doc__,file=sys.stderr);return 64
if __name__=='__main__':sys.exit(main(sys.argv[1:]))
