"""Small checked I/O primitives shared by planning, execution and assembly."""
from __future__ import annotations
import hashlib,json,os,shlex,sys,tempfile
from pathlib import Path
if sys.version_info<(3,10):sys.exit('LRI_C6_D3_HPC requires Python >= 3.10 (int.bit_count, dict union)')
ROOT=Path(__file__).resolve().parents[1]
# Numerical build flags that no user CXXFLAGS may drop (same order as the Makefile's C6_REQUIRED).
REQUIRED_CXXFLAGS=['-fopenmp','-ffp-contract=off','-fno-fast-math']
def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def canon(obj)->str:return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
def object_hash(obj)->str:return hashlib.sha256(canon(obj).encode()).hexdigest()
_UMASK=os.umask(0);os.umask(_UMASK)  # read once at import (single-threaded); never toggled while files are published
def umask_mode(mode:int=0o666)->int:return mode&~_UMASK
def publish(path:Path,text:str)->None:
    """Atomic, same-filesystem, no-clobber publication (POSIX hard link), with umask-respecting permissions."""
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        os.fchmod(fd,umask_mode())
        with os.fdopen(fd,'w')as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
    finally:os.unlink(tmp)
def dump(path:Path,obj)->None:publish(path,json.dumps(obj,indent=2,allow_nan=False)+'\n')
def checked(path:Path,expected:str)->None:
    if digest(path)!=expected:raise ValueError(f'Checksum mismatch: {path}')
def load(path:Path):return json.loads(path.read_text())
def pow2(n:int)->bool:return n>0 and (n&(n-1))==0
def cxx_command(sources,output,defines=(),shared=False,libs=('-lquadmath',)):
    """Compiler command for test/benchmark builds: CXX, CPPFLAGS and CXXFLAGS from the environment (as make does),
    defaulting CXXFLAGS to the Makefile's '-O3 -std=c++17', then the flags no environment may drop."""
    env=os.environ
    cxx=shlex.split(env.get('CXX','g++'));cpp=shlex.split(env.get('CPPFLAGS',''));flags=shlex.split(env.get('CXXFLAGS','-O3 -std=c++17'))
    return [*cxx,*cpp,*flags,*REQUIRED_CXXFLAGS,*[f'-D{d}'for d in defines],*(['-shared','-fPIC']if shared else[]),*map(str,sources),*libs,'-o',str(output)]
