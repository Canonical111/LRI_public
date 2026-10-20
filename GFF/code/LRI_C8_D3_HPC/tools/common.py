"""Small checked I/O primitives shared by planning, execution and assembly."""
from __future__ import annotations
import hashlib,json,os,platform,shlex,socket,sys,tempfile
from pathlib import Path
if sys.version_info<(3,10):sys.exit('LRI_C8_D3_HPC requires Python >= 3.10 (int.bit_count, dict union, zip(strict=))')
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
def verified_bytes(path:Path,expected:str)->bytes:
    """Exactly the bytes whose sha256 was checked, read once (no check-then-reread window). With digest, the only way
    the input tools open a vendored file (PLAN E.1 "One read rule"; tests/check_vendored.py's spy)."""
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {path}')
    return data
def read_verified(path:Path,expected:str)->dict:
    """JSON from exactly the bytes whose sha256 was checked (no check-then-reread window)."""
    return json.loads(verified_bytes(path,expected))
PREAD_CHUNK=1<<30  # one os.pread call reads at most this (macOS refuses a single read above INT_MAX bytes)
def read_member(fd:int,offset:int,length:int)->bytes:
    """Exactly the `length` bytes at `offset` of the open file descriptor `fd`, and nothing else (F12, ported from
    LRI_C8_D2_HPC d5dfd38): os.pread in a loop over short reads, with no Python buffer and no shared file position. A
    buffered reader (`open(pack,'rb')`) sizes its buffer by the file system's st_blksize (524,288 bytes on BeeGFS) and,
    after a seek outside its buffer, refills one whole buffer behind the bytes asked for: up to st_blksize of
    neighbouring pack data per member (0.7 bytes per staged byte at L8 on symmetry, C62d's real-Slurm run of 2026-10-05).
    Fewer than `length` bytes come back only at the end of the file; the callers' length and sha256 checks refuse that."""
    if length<=0:return b''
    parts=[];got=0
    while got<length:
        b=os.pread(fd,min(length-got,PREAD_CHUNK),offset+got)
        if not b:break
        parts.append(b);got+=len(b)
    return parts[0]if len(parts)==1 else b''.join(parts)
def load(path:Path):return json.loads(Path(path).read_text())
def pow2(n:int)->bool:return n>0 and (n&(n-1))==0
def cpu_model(counter=None)->str:
    """The CPU model: /proc/cpuinfo's 'model name' (Linux), else platform.processor() (macOS: one `uname -p` process
    per interpreter, the platform contract of A-ORC-13). counter (a dict) receives the bytes read."""
    try:
        data=Path('/proc/cpuinfo').read_bytes();_count(counter,len(data))
        for line in data.decode(errors='replace').splitlines():
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
    live work or refused by admission, 69 unknown or uncertain state, 74 a write failure, 75 the session lock is held."""
    def __init__(self,code,msg):super().__init__(msg);self.code=code
    def __reduce__(self):return (Refuse,(self.code,str(self)))   # picklable across a process pool (the merge workers)

# ---------------------------------------------------------------------------------------------------------------------
# C8(3) Stage 3a additions (PLAN D.4, D.7, D.8, A-ORC-13, A-ORC-15).
import errno,re,struct,time
def utc(t:float|None=None)->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()if t is None else t))
def _count(counter,n:int)->None:
    if counter is not None:counter['bytes']=counter.get('bytes',0)+int(n)
def _digest_counted(path:Path,counter)->str:
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block);_count(counter,len(block))
    return h.hexdigest()
def glibc_version()->str|None:
    try:return os.confstr('CS_GNU_LIBC_VERSION')
    except (ValueError,OSError,AttributeError):return None
def elf_interpreter(exe:Path,counter=None)->str|None:
    """PT_INTERP of a 64-bit little-endian ELF executable (read from its program headers), else None."""
    try:
        with Path(exe).open('rb')as f:
            h=f.read(64);_count(counter,len(h))
            if len(h)<64 or h[:4]!=b'\x7fELF'or h[4]!=2 or h[5]!=1:return None
            phoff,=struct.unpack_from('<Q',h,32);phentsize,phnum=struct.unpack_from('<HH',h,54)
            f.seek(phoff);ph=f.read(phentsize*phnum);_count(counter,len(ph))
            for i in range(phnum):
                typ,=struct.unpack_from('<I',ph,i*phentsize)
                if typ==3:
                    off,=struct.unpack_from('<Q',ph,i*phentsize+8);size,=struct.unpack_from('<Q',ph,i*phentsize+32)
                    f.seek(off);b=f.read(size);_count(counter,len(b));return b.rstrip(b'\0').decode(errors='replace')
    except (OSError,struct.error):return None
    return None
def fingerprint(exe:Path,counter=None)->dict:
    """Host and run-time library identity of one executable on this node (PLAN D.8; recorded, never validated): host,
    CPU model, glibc, the ELF interpreter and every library `ldd` resolves (path and sha256). Platform contract
    (A-ORC-13, C62d's R17/R20): the one probe it starts is `ldd` on the executable; on macOS that launch fails (ENOENT,
    recorded as ldd_error) and cpu_model() starts `uname -p` through platform. counter['bytes'] receives the bytes this
    process reads for the fingerprint (the platform class), kept outside the returned record."""
    import subprocess
    libs={};err=None
    try:
        cp=subprocess.run(['ldd',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        out=cp.stdout or b'';_count(counter,len(out));text=out.decode(errors='replace')
        if cp.returncode:err=text.strip()[-300:]
        for line in text.splitlines():
            parts=line.split()
            if '=>'in parts:
                i=parts.index('=>');name=parts[0];target=parts[i+1]if i+1<len(parts)else''
                if target.startswith('/'):
                    real=os.path.realpath(target)
                    try:libs[name]={'path':target,'resolved':real,'sha256':_digest_counted(Path(real),counter)}
                    except OSError:libs[name]={'path':target,'resolved':real,'sha256':None}
                elif target:libs[name]={'path':None,'resolved':None,'sha256':None,'note':' '.join(parts[i+1:])}
    except (OSError,subprocess.SubprocessError)as e:err=str(e)
    interp=elf_interpreter(exe,counter);ip=None
    if interp:
        real=os.path.realpath(interp)
        try:ip={'path':interp,'resolved':real,'sha256':_digest_counted(Path(real),counter)}
        except OSError:ip={'path':interp,'resolved':real,'sha256':None}
    key=lambda n:next((v for k,v in libs.items()if k.startswith(n)),None)
    return {'host':socket.gethostname(),'cpu_model':cpu_model(counter),'glibc':glibc_version(),'interpreter':ip,'libraries':libs,
            'libgmp':key('libgmp'),'libquadmath':key('libquadmath'),'libgomp':key('libgomp'),'ldd_error':err,
            'slurm':{k:os.environ.get(k)for k in('SLURM_JOB_ID','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID','SLURM_RESTART_COUNT')}}
def fingerprint_key(fp:dict|None)->str|None:
    """Digest of a fingerprint without its per-node fields (host, Slurm ids): equal keys mean the same library stack."""
    if not fp:return None
    return object_hash({k:v for k,v in fp.items()if k not in('host','slurm')})[:12]
def scheduler_user()->str:
    """The scheduler user of this process: the real uid's name (never $USER)."""
    import pwd
    return pwd.getpwuid(os.getuid()).pw_name
def fsync_tree(root:Path)->None:
    """fsync every regular file and directory under root (deepest first), then root (D.4: the copy on the shared path)."""
    root=Path(root)
    for dp,dns,fns in os.walk(root,topdown=False):
        for n in fns:
            fd=os.open(os.path.join(dp,n),os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        fd=os.open(dp,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
def fsync_dir(path:Path)->None:
    fd=os.open(str(path),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
QUOTA_ERRNOS=(errno.EDQUOT,errno.ENOSPC)
IO_FAULT_POINTS=('plan_rename','checkpoint_publish','merge_output','result_publish')
def io_fault(point:str)->None:
    """Test-only EDQUOT injection at a publish point (A-ORC-15): C8_TEST_IO_FAULT=<point>[,<point>...], honoured only off
    Expanse (C8_SITE unset or fake, and SLURM_CLUSTER_NAME not expanse)."""
    v=os.environ.get('C8_TEST_IO_FAULT')
    if not v or os.environ.get('C8_SITE')not in(None,'','fake')or os.environ.get('SLURM_CLUSTER_NAME')=='expanse':return
    if point in v.split(','):raise OSError(errno.EDQUOT,f'Disk quota exceeded (test fault {point})')
class QuotaRefused(Refuse):
    """EDQUOT or ENOSPC at a publish point: the tool stops with 74, naming the quota and the path (PLAN D.7)."""
    def __init__(self,e:OSError,path,what:str):
        q='a disk quota (user files, user bytes or group bytes: lfs quota -u zzheng8, lfs quota -g yun124)'if e.errno==errno.EDQUOT else 'free space (ENOSPC)'
        super().__init__(74,f'{what} failed: {os.strerror(e.errno)} at {path}: {q} is exhausted; the previous published state is intact')
def quota_guard(e:BaseException,path,what:str):
    """Re-raise an EDQUOT/ENOSPC OSError as QuotaRefused (74); anything else unchanged."""
    if isinstance(e,OSError)and e.errno in QUOTA_ERRNOS:raise QuotaRefused(e,path,what)from e
    raise e
def publish_bytes(path:Path,data:bytes,point:str|None=None)->None:
    """publish() for bytes, with the test-only fault point and quota handling (74)."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    try:
        if point:io_fault(point)
        fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    except OSError as e:
        quota_guard(e,path,'publication');raise   # quota_guard always raises; the raise keeps the flow explicit
    try:
        os.fchmod(fd,umask_mode())
        with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
    except FileExistsError:raise
    except OSError as e:quota_guard(e,path,'publication')
    finally:
        try:os.unlink(tmp)
        except OSError:pass
def dump_point(path:Path,obj,point:str)->None:publish_bytes(path,(json.dumps(obj,indent=2,allow_nan=False)+'\n').encode(),point)
def replace_file(path:Path,data:bytes)->None:
    """Atomic replacement (temporary file, fsync, rename, directory fsync)."""
    path=Path(path);fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        os.fchmod(fd,umask_mode())
        with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path);fsync_dir(path.parent)
    except BaseException:
        try:os.unlink(tmp)
        except OSError:pass
        raise
def supersede(dest:Path,data:bytes,old:bytes,point:str='result_publish')->str|None:
    """Replace a published dest, whose bytes were `old` when the caller read them and decided that only provenance
    changed, by `data`; the old bytes stay as <stem>.superseded.<sha256(old)[:12]><suffix> (a hard link) (F8-d3: a
    group re-merged after a recovered index). Returns the kept file's name, or None when dest changed since `old` was
    read (the caller decides again on its current bytes). EDQUOT/ENOSPC exits 74 (QuotaRefused), as every publish point."""
    dest=Path(dest);sha=hashlib.sha256(old).hexdigest();keep=dest.with_name(f'{dest.stem}.superseded.{sha[:12]}{dest.suffix}')
    try:
        io_fault(point)
        try:os.link(dest,keep);created=True
        except FileExistsError:created=False   # superseded before (the same old bytes)
        if digest(keep)!=sha:
            if not created:raise ValueError(f'{keep} exists and is not the file it names; {dest} not superseded')
            keep.unlink();return None
        replace_file(dest,data)
    except OSError as e:quota_guard(e,dest,'publication')   # 74 on EDQUOT/ENOSPC; anything else re-raised
    return keep.name
def rename_noreplace(src:Path,dst:Path)->str:
    """Rename the directory src to dst atomically, failing with FileExistsError when dst exists, whatever it is (an empty
    directory included, which a plain rename(2) replaces): the publication of a staged campaign (S2-005). Linux
    renameat2(RENAME_NOREPLACE), macOS renamex_np(RENAME_EXCL). Where the call or the file system lacks that flag
    (EINVAL, ENOSYS, ENOTSUP): recheck_rename. Returns the method used."""
    import ctypes
    s,d=os.fsencode(str(src)),os.fsencode(str(dst));call=None
    try:
        libc=ctypes.CDLL(None,use_errno=True)
        if sys.platform.startswith('linux')and hasattr(libc,'renameat2'):
            f=libc.renameat2;f.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];call=lambda:f(-100,s,-100,d,1)   # AT_FDCWD, RENAME_NOREPLACE
        elif sys.platform=='darwin'and hasattr(libc,'renamex_np'):
            f=libc.renamex_np;f.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];call=lambda:f(s,d,4)   # RENAME_EXCL
    except OSError:call=None
    if call is not None:
        if call()==0:return 'noreplace'
        e=ctypes.get_errno()
        if e in(errno.EEXIST,errno.ENOTEMPTY):raise FileExistsError(e,os.strerror(e),str(dst))
        if e not in(errno.EINVAL,errno.ENOSYS,errno.ENOTSUP,errno.EOPNOTSUPP):raise OSError(e,os.strerror(e),str(dst))
    return recheck_rename(src,dst)
def recheck_rename(src:Path,dst:Path)->str:
    """rename_noreplace's fallback: dst rechecked (FileExistsError when it exists), then rename(2), which still fails on
    any non-empty destination (ENOTEMPTY, EEXIST: every published campaign, every staged copy), raised as
    FileExistsError; only an empty directory made between the recheck and the rename could be replaced, and it holds
    nothing. (No claim directory: one that a SIGKILL leaves behind would block the directory, A-ORC-17 (k).)"""
    if os.path.lexists(dst):raise FileExistsError(errno.EEXIST,os.strerror(errno.EEXIST),str(dst))
    try:os.rename(src,dst)
    except OSError as e:
        if e.errno in(errno.EEXIST,errno.ENOTEMPTY):raise FileExistsError(e.errno,os.strerror(e.errno),str(dst))from e
        raise
    return 'recheck_rename'
