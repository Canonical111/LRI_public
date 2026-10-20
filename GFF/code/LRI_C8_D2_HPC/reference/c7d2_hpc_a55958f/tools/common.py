"""Small checked I/O primitives shared by planning, execution and assembly."""
from __future__ import annotations
import hashlib,json,os,platform,shlex,socket,subprocess,sys,tempfile
from pathlib import Path
if sys.version_info<(3,10):sys.exit('LRI_C7_D2_HPC requires Python >= 3.10 (found %d.%d); load a newer python module or venv'%sys.version_info[:2])
ROOT=Path(__file__).resolve().parents[1]
# Numerical build flags no user setting may drop (the Makefile's C7_REQUIRED, same order).
REQUIRED_CXXFLAGS=['-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math']
def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def canon(obj)->str:return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
def object_hash(obj)->str:return hashlib.sha256(canon(obj).encode()).hexdigest()
_UMASK=os.umask(0);os.umask(_UMASK)  # read once at import; never toggled while files are published
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
def read_verified(path:Path,expected:str):
    """Parse JSON only from the bytes whose digest was checked (no check-then-reread race)."""
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {path}')
    return json.loads(data)
def load(path:Path):return json.loads(path.read_text())
def pow2(n:int)->bool:return n>0 and (n&(n-1))==0

def link_only(word:str)->bool:
    """A word allowed after the required flags (the Makefile's C7_LINK_ONLY): it cannot change compilation."""
    return (word.startswith(('-L','-l','-Wl,','-static','-fuse-ld='))or word in('-pthread','-rdynamic')
            or (not word.startswith('-')and word.endswith(('.a','.so','.o'))))

def cxx_command(sources,output,defines=(),libs=('-lquadmath',)):
    """Test/benchmark compile command with the Makefile's layout: CXX CPPFLAGS OPTFLAGS CXXFLAGS required-flags defines
    sources LDFLAGS libs LDLIBS. OPTFLAGS defaults to -O3, so default settings give the Makefile's default command.
    LDFLAGS and LDLIBS follow the required flags and may hold only link-only words, as in the Makefile."""
    e=os.environ;sp=lambda k,d='':shlex.split(e.get(k,d))
    bad=[w for w in sp('LDFLAGS')+sp('LDLIBS')if not link_only(w)]
    if bad:raise ValueError(f'LDFLAGS/LDLIBS may hold only link options (-L* -l* -Wl,* -pthread -static* -rdynamic -fuse-ld=* *.a *.so *.o), not: {" ".join(bad)}')
    return [*sp('CXX','g++'),*sp('CPPFLAGS'),*sp('OPTFLAGS','-O3'),*sp('CXXFLAGS'),*REQUIRED_CXXFLAGS,*[f'-D{d}'for d in defines],*map(str,sources),
            *sp('LDFLAGS'),*libs,*sp('LDLIBS'),'-o',str(output)]

def cpu_model()->str|None:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):return line.split(':',1)[1].strip()
    except OSError:pass
    return platform.processor()or None

def glibc_version()->str|None:
    try:return os.confstr('CS_GNU_LIBC_VERSION')
    except (ValueError,OSError,AttributeError):return None

def elf_interpreter(path:Path)->str|None:
    """PT_INTERP of a 64-bit little-endian ELF executable (the ld.so it requests), else None."""
    try:
        with open(path,'rb')as f:
            h=f.read(64)
            if h[:4]!=b'\x7fELF'or h[4]!=2 or h[5]!=1:return None
            phoff=int.from_bytes(h[32:40],'little');phentsize=int.from_bytes(h[54:56],'little');phnum=int.from_bytes(h[56:58],'little')
            for i in range(phnum):
                f.seek(phoff+i*phentsize);ph=f.read(phentsize)
                if int.from_bytes(ph[0:4],'little')==3:
                    off=int.from_bytes(ph[8:16],'little');size=int.from_bytes(ph[32:40],'little');f.seek(off);return f.read(size).rstrip(b'\0').decode()
    except OSError:return None
    return None

def fingerprint(exe:Path)->dict:
    """Host and run-time library identity of one executable on this node: host, CPU model, glibc, the ld.so
    interpreter and every library ldd resolves (path and sha256). Missing tools give null fields, never an error."""
    libs={};err=None
    try:
        cp=subprocess.run(['ldd',str(exe)],capture_output=True,text=True,timeout=120)
        if cp.returncode:err=(cp.stderr or cp.stdout).strip()[-300:]
        for line in cp.stdout.splitlines():
            parts=line.split()
            if '=>'in parts:
                name=parts[0];i=parts.index('=>');target=parts[i+1]if i+1<len(parts)else''
                if target.startswith('/'):
                    real=os.path.realpath(target);libs[name]={'path':target,'resolved':real,'sha256':digest(Path(real))}
                elif target!='':libs[name]={'path':None,'resolved':None,'sha256':None,'note':' '.join(parts[i+1:])}
    except (OSError,subprocess.SubprocessError)as e:err=str(e)
    interp=elf_interpreter(exe);ip=None
    if interp:
        real=os.path.realpath(interp)
        try:ip={'path':interp,'resolved':real,'sha256':digest(Path(real))}
        except OSError:ip={'path':interp,'resolved':real,'sha256':None}
    key=lambda n:next((v for k,v in libs.items()if k.startswith(n)),None)
    return {'host':socket.gethostname(),'cpu_model':cpu_model(),'glibc':glibc_version(),'interpreter':ip,'libraries':libs,
            'libgmp':key('libgmp'),'libquadmath':key('libquadmath'),'libgomp':key('libgomp'),'ldd_error':err,
            'slurm':{k:os.environ.get(k)for k in('SLURM_JOB_ID','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID')}}

def fingerprint_key(fp:dict|None)->str|None:
    """Digest of a fingerprint without its per-node fields (host, Slurm ids): equal keys mean the same library stack."""
    if not fp:return None
    return object_hash({k:v for k,v in fp.items()if k not in('host','slurm')})[:12]

def environment_record()->dict:
    """Host, interpreter and executable provenance for test and benchmark records (A-L7)."""
    out={'host':socket.gethostname(),'platform':platform.platform(),'cpu_model':cpu_model(),'glibc':glibc_version(),'python':platform.python_version(),
         'cpu_count':os.cpu_count(),'executables':{}}
    for mod in ('numpy','scipy'):
        try:out[mod]=__import__(mod).__version__
        except ImportError:out[mod]=None
    for name in ('c7d2_decimal','c7d2_gmp'):
        exe=ROOT/'bin'/name
        if not exe.exists():continue
        rec={'sha256':digest(exe)}
        try:rec['describe']=json.loads(subprocess.run([str(exe),'--describe'],capture_output=True,text=True,check=True,timeout=120).stdout)
        except Exception as e:rec['describe']=f'unavailable: {e}'
        br=exe.with_name(name+'.build.json')
        rec['build_record']=load(br)if br.exists()else None
        out['executables'][name]=rec
    return out
