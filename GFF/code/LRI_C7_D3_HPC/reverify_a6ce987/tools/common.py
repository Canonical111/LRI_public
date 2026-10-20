"""Small checked I/O primitives shared by planning, execution and assembly."""
from __future__ import annotations
import hashlib,json,os,platform,shlex,socket,sys,tempfile
from pathlib import Path
if sys.version_info<(3,10):sys.exit('LRI_C7_D3_HPC requires Python >= 3.10 (int.bit_count, dict union, zip(strict=))')
ROOT=Path(__file__).resolve().parents[1]
# Numerical build flags that no user flags may drop (the Makefile's STRICT, same order).
STRICT_CXXFLAGS=['-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math']
def digest(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def canon(obj)->str:return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
def object_hash(obj)->str:return hashlib.sha256(canon(obj).encode()).hexdigest()
_UMASK=os.umask(0);os.umask(_UMASK)  # read once at import (single-threaded); never toggled while files are published
def umask_mode(mode:int=0o666)->int:return mode&~_UMASK
def publish(path:Path,text:str)->None:
    """Atomic, same-filesystem, no-clobber publication (POSIX hard link), with umask-respecting permissions."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        os.fchmod(fd,umask_mode())
        with os.fdopen(fd,'w')as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
    finally:os.unlink(tmp)
def dump(path:Path,obj)->None:publish(path,json.dumps(obj,indent=2,allow_nan=False)+'\n')
def checked(path:Path,expected:str)->None:
    if digest(path)!=expected:raise ValueError(f'Checksum mismatch: {path}')
def read_verified(path:Path,expected:str)->dict:
    """JSON from exactly the bytes whose sha256 was checked (no check-then-reread window)."""
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {path}')
    return json.loads(data)
def load(path:Path):return json.loads(Path(path).read_text())
def pow2(n:int)->bool:return n>0 and (n&(n-1))==0
def cpu_model()->str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):return line.split(':',1)[1].strip()
    except OSError:pass
    return platform.processor()or platform.machine()
def host_info()->dict:
    """Where a piece of work ran. Recorded, never validated: results are not bit-reproducible across CPU types
    (last bits of glibc's long-double expl/logl; docs/NUMERICS.md)."""
    return {'node':socket.gethostname(),'cpu_model':cpu_model()}
def compiler_identity(cmd)->dict:
    """The compile command and the first line of its compiler's --version (the compiler actually invoked)."""
    import subprocess
    try:cp=subprocess.run([cmd[0],'--version'],capture_output=True,text=True,timeout=60);ver=cp.stdout.splitlines()[0]if cp.returncode==0 and cp.stdout else None
    except (OSError,subprocess.SubprocessError):ver=None
    return {'command':[str(x)for x in cmd],'compiler_version':ver}
def exe_identity(path)->dict:
    """sha256, --describe and make's build info (bin/<binary>.buildinfo.json) of a worker executable."""
    import subprocess
    path=Path(path);desc=None
    try:
        cp=subprocess.run([str(path),'--describe'],capture_output=True,text=True,timeout=60)
        if cp.returncode==0:desc=json.loads(cp.stdout)
    except (OSError,ValueError,subprocess.SubprocessError):pass
    bi=path.with_name(path.name+'.buildinfo.json')
    return {'path':str(path),'sha256':digest(path),'describe':desc,'buildinfo':json.loads(bi.read_text())if bi.exists()else None}
def strict_conflicts(tokens)->list[str]:
    """User compiler/linker tokens that would override the strict numerical flags (they reach the same compiler call,
    LDFLAGS and LDLIBS after STRICT): fast-math family, other -ffp-contract/-std values, -mfpmath, -fexcess-precision,
    -fno-openmp. Refused in every user flag variable (inspection C7I-07)."""
    exact={'-ffast-math','-Ofast','-funsafe-math-optimizations','-fassociative-math','-freciprocal-math','-fno-signed-zeros',
           '-fno-trapping-math','-ffinite-math-only','-fcx-limited-range','-fno-openmp'}
    bad=[]
    for t in tokens:
        if t in exact or(t.startswith('-ffp-contract=')and t!='-ffp-contract=off')or(t.startswith('-std=')and t!='-std=c++17')\
           or t.startswith('-mfpmath=')or t.startswith('-fexcess-precision='):bad.append(t)
    return bad
def cxx_command(sources,output,defines=(),libs=('-lquadmath',)):
    """Compiler command for test/benchmark builds, matching the Makefile: CXX, CPPFLAGS, OPTFLAGS (default -O3) and
    CXXFLAGS from the environment, then the flags no environment may drop, then LDFLAGS, the libraries and LDLIBS."""
    env=os.environ;sp=lambda k,d='':shlex.split(env.get(k,d))
    bad=strict_conflicts([t for k,d in (('CPPFLAGS',''),('OPTFLAGS','-O3'),('CXXFLAGS',''),('LDFLAGS',''),('LDLIBS',''))for t in sp(k,d)])
    if bad:raise ValueError('compiler flags conflicting with the strict numerical flags: '+' '.join(bad))
    return [*sp('CXX','g++'),*sp('CPPFLAGS'),*sp('OPTFLAGS','-O3'),*sp('CXXFLAGS'),*STRICT_CXXFLAGS,*[f'-D{d}'for d in defines],
            *map(str,sources),*sp('LDFLAGS'),*libs,*sp('LDLIBS'),'-o',str(output)]

class Refuse(Exception):
    """A refused submission or lane operation: nothing was submitted or changed. code: 64 invalid input, 65 conflicting
    live work, 69 unknown or uncertain state, 75 another submission holds the campaign lock."""
    def __init__(self,code,msg):super().__init__(msg);self.code=code

LOCK_NAME='.c7_submit.lock'
class CampaignLock:
    """Campaign-scoped submission lock: an atomically created directory $C7_RUN/.c7_submit.lock, removed on exit.
    Held by every submission and by lane queue/stale-claim maintenance. A lock left by a killed process is never broken
    automatically: its owner.json names the holder; remove it by hand."""
    def __init__(self,run:Path,command:str):self.path=Path(run)/LOCK_NAME;self.command=command;self.held=False
    def __enter__(self):
        import getpass,time
        try:os.mkdir(self.path,0o700)
        except FileExistsError:
            try:owner=(self.path/'owner.json').read_text().strip()
            except OSError:owner='unknown (owner.json not written yet or unreadable)'
            raise Refuse(75,f'another submission for this campaign holds {self.path} ({owner}); nothing submitted. Rerun when it has '
                            f'finished, or remove {self.path} by hand if no such process is running')
        self.held=True
        try:
            info={'host':socket.gethostname(),'pid':os.getpid(),'user':getpass.getuser(),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'command':self.command}
            (self.path/'owner.json').write_text(json.dumps(info)+'\n')
        except BaseException:
            self.__exit__(None,None,None);raise  # __exit__ is not called when __enter__ raises: release our own lock here
        return self
    def __exit__(self,*exc):
        if self.held:
            try:(self.path/'owner.json').unlink()
            except FileNotFoundError:pass
            os.rmdir(self.path);self.held=False
        return False
