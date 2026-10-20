"""Small checked I/O primitives shared by planning, execution, lanes, submission and assembly."""
from __future__ import annotations
import hashlib,json,os,platform,pwd,re,shlex,socket,subprocess,sys,tempfile,time
from pathlib import Path
if sys.version_info<(3,10):sys.exit('LRI_C8_D2_HPC requires Python >= 3.10 (found %d.%d); load a newer python module or venv'%sys.version_info[:2])
ROOT=Path(__file__).resolve().parents[1]
# Numerical build flags no user setting may drop (the Makefile's C8_REQUIRED, same order).
REQUIRED_CXXFLAGS=['-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math']
# The opt-in numerics profiles (PLAN D1, A-FLAG-1; Stage 4c) in their canonical order: the Makefile's NX_KNOWN and the
# name src/numerics/numerics.hpp builds. R4d (mpconv) is not implemented (host decision 2026-10-04).
NUMERICS_PROFILES=('dd','mp256','exp1')
def numerics_name(text:str)->str:
    """'exact', or the canonical name of an opt-in profile combination: the profiles of text (separated by '+' or ',')
    in the order of NUMERICS_PROFILES, joined by '+' (the executable is bin/c8d2_gmp_<name>). ValueError for an empty,
    unknown, repeated or mixed-with-exact name."""
    parts=[p for p in str(text).replace(',','+').split('+')]
    if parts==['exact']:return 'exact'
    if not parts or any(not p for p in parts):raise ValueError(f'numerics {text!r}: name exact or profiles of {"+".join(NUMERICS_PROFILES)}')
    if 'exact'in parts:raise ValueError(f'numerics {text!r}: exact does not combine with an opt-in profile')
    if 'mpconv'in parts:raise ValueError(f'numerics {text!r}: R4d (mpconv) is not implemented (host decision 2026-10-04)')
    bad=[p for p in parts if p not in NUMERICS_PROFILES]
    if bad:raise ValueError(f'numerics {text!r}: unknown profile(s) {", ".join(bad)}; the opt-in profiles are {", ".join(NUMERICS_PROFILES)}')
    if len(set(parts))!=len(parts):raise ValueError(f'numerics {text!r}: a profile is named twice')
    return '+'.join(p for p in NUMERICS_PROFILES if p in parts)
def digest(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def canon(obj)->str:return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)
def object_hash(obj)->str:return hashlib.sha256(canon(obj).encode()).hexdigest()
_UMASK=os.umask(0);os.umask(_UMASK)  # read once at import; never toggled while files are published
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
def replace_file(path:Path,data:bytes)->None:
    """Atomic same-filesystem replacement (temporary file, fsync, rename), umask-respecting permissions."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.tmp.',dir=path.parent)
    try:
        os.fchmod(fd,umask_mode())
        with os.fdopen(fd,'wb')as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    except BaseException:
        try:os.unlink(tmp)
        except FileNotFoundError:pass
        raise
def dump(path:Path,obj)->None:publish(path,json.dumps(obj,indent=2,allow_nan=False)+'\n')
def checked(path:Path,expected:str)->None:
    if digest(path)!=expected:raise ValueError(f'Checksum mismatch: {path}')
def read_verified(path:Path,expected:str):
    """Parse JSON only from the bytes whose digest was checked (no check-then-reread race)."""
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError(f'Checksum mismatch: {path}')
    return json.loads(data)
def load(path:Path):return json.loads(Path(path).read_text())
def pow2(n:int)->bool:return n>0 and (n&(n-1))==0
def utc()->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())

def link_only(word:str)->bool:
    """A word allowed after the required flags (the Makefile's C8_LINK_ONLY): it cannot change compilation."""
    return (word.startswith(('-L','-l','-Wl,','-static','-fuse-ld='))or word in('-pthread','-rdynamic')
            or (not word.startswith('-')and word.endswith(('.a','.so','.o'))))

def gmp_prefix_words(gmp_prefix)->tuple[list[str],list[str]]:
    """The Makefile's GMP_INC and GMP_LINK words of a GMP_PREFIX: ([-I<p>/include], [-L<p>/lib -Wl,-rpath,<p>/lib
    -Wl,--disable-new-dtags]); ([], []) for None or ''; ValueError for a prefix that is not one absolute path without
    whitespace (the Makefile refuses it). cxx_command and tests/sanitize.py's point_checks tool place them as the
    Makefile does (Y1, Stage-6 fix round 2)."""
    if not gmp_prefix:return [],[]
    g=str(gmp_prefix)
    if not g.startswith('/')or any(c.isspace()for c in g):raise ValueError(f'GMP_PREFIX {g!r}: one absolute path without whitespace (the Makefile\'s rule)')
    return [f'-I{g}/include'],[f'-L{g}/lib',f'-Wl,-rpath,{g}/lib','-Wl,--disable-new-dtags']

def cxx_command(sources,output,defines=(),libs=('-lquadmath',),gmp_prefix=None):
    """Test/benchmark compile command with the Makefile's layout: CXX CPPFLAGS OPTFLAGS CXXFLAGS required-flags defines
    sources LDFLAGS libs LDLIBS. OPTFLAGS defaults to -O3, so default settings give the Makefile's default command.
    LDFLAGS and LDLIBS follow the required flags and may hold only link-only words, as in the Makefile.
    gmp_prefix (Y1, Stage-6 fix round 2): the GMP_PREFIX of the target worker's build record (tools/build_record.py
    gmp_target), placed as the Makefile's GMP_COMPILE and GMP_LINK place it: -I<prefix>/include right after CXX and
    -L<prefix>/lib -Wl,-rpath,<prefix>/lib -Wl,--disable-new-dtags ahead of LDFLAGS. None or '' (the default) gives
    the unchanged command; a prefix that is not one absolute path without whitespace is refused (ValueError), as the
    Makefile refuses it."""
    e=os.environ;sp=lambda k,d='':shlex.split(e.get(k,d))
    bad=[w for w in sp('LDFLAGS')+sp('LDLIBS')if not link_only(w)]
    if bad:raise ValueError(f'LDFLAGS/LDLIBS may hold only link options (-L* -l* -Wl,* -pthread -static* -rdynamic -fuse-ld=* *.a *.so *.o), not: {" ".join(bad)}')
    inc,link=gmp_prefix_words(gmp_prefix)
    return [*sp('CXX','g++'),*inc,*sp('CPPFLAGS'),*sp('OPTFLAGS','-O3'),*sp('CXXFLAGS'),*REQUIRED_CXXFLAGS,*[f'-D{d}'for d in defines],*map(str,sources),
            *link,*sp('LDFLAGS'),*libs,*sp('LDLIBS'),'-o',str(output)]

# ---------------------------------------------------------------- refusals, locks and the scheduler identity
class Refuse(Exception):
    """A refused submission or lane operation: nothing was submitted or changed. code: 64 invalid input, 65 conflicting
    live work or a full admission budget, 69 unknown or uncertain state, 70 a job accepted without TimeLimit=UNLIMITED
    under the unlimited policy, 75 another process holds the lock."""
    def __init__(self,code,msg):super().__init__(msg);self.code=code

def scheduler_user()->str:
    """The account sbatch submits under: the name of the process's real uid (never USER, LOGNAME or getpass, which
    follow the environment; C7(2) IR2-01); the numeric uid when the uid has no passwd entry (squeue -u accepts it)."""
    uid=os.getuid()
    try:return pwd.getpwuid(uid).pw_name
    except KeyError:return str(uid)

class DirLock:
    """A lock directory created atomically (mkdir; flock is not relied on) with an owner.json record, removed on exit.
    A lock left by a killed process is never broken automatically: its owner.json names the holder; remove it by hand.
    wait > 0 retries for that many seconds before refusing (75)."""
    def __init__(self,path:Path,command:str,what:str='this campaign',wait:float=0.):
        self.path=Path(path);self.command=command;self.what=what;self.wait=wait;self.held=False
    def __enter__(self):
        t0=time.time()
        while True:
            try:os.mkdir(self.path,0o700);break
            except FileExistsError:
                if time.time()-t0<self.wait:time.sleep(0.2);continue
                try:owner=(self.path/'owner.json').read_text().strip()
                except OSError:owner='unknown (owner.json not written yet or unreadable)'
                raise Refuse(75,f'another process for {self.what} holds {self.path} ({owner}); nothing changed. Rerun when it has '
                                f'finished, or remove {self.path} by hand if no such process is running')
        self.held=True
        try:
            info={'host':socket.gethostname(),'pid':os.getpid(),'user':scheduler_user(),'started_utc':utc(),'command':self.command}
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

LOCK_NAME='.c8_submit.lock'
class CampaignLock(DirLock):
    """The campaign-scoped lock $C8_RUN/.c8_submit.lock: held by every submission (snapshot through the last sbatch and
    ledger write), by lane queue rebuilds and stale-claim releases, and by ledger registrations (exit 75 when held)."""
    def __init__(self,run:Path,command:str,wait:float=0.):super().__init__(Path(run)/LOCK_NAME,command,'this campaign',wait)

def cpu_model_noprobe()->str|None:
    """The CPU model without starting any process: /proc/cpuinfo's model name (Linux), else platform.machine()."""
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):return line.split(':',1)[1].strip()
    except OSError:pass
    return platform.machine()or None

def host_info()->dict:
    """Where a piece of work ran (lane owner records, the lane deadline's CPU class). Recorded, never validated:
    results are not bit-reproducible across CPU types. Starts no process (the platform contract keeps probes to the
    claim's fingerprint)."""
    return {'node':socket.gethostname(),'cpu_model':cpu_model_noprobe()}

# ---------------------------------------------------------------- host and run-time library fingerprint
def _count(counter,n:int)->None:
    if counter is not None:counter['bytes']=counter.get('bytes',0)+int(n)

def _digest_counted(path:Path,counter)->str:
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block);_count(counter,len(block))
    return h.hexdigest()

def cpu_identity(data:bytes|None)->dict:
    """The CPU identity of a node (F5, Stage 5: native rows depend on the CPU vendor through the x87 expl/logl, so a
    campaign stays on one vendor): vendor, family, model and model name from the first processor block of
    /proc/cpuinfo's bytes (vendor_id, cpu family, model, model name; 'CPU implementer' on ARM, which has no vendor_id).
    Without /proc/cpuinfo (data None: macOS) the vendor is '<sys.platform>-<machine>' from os.uname(), which starts no
    process (the platform contract, R20)."""
    out={'vendor':None,'family':None,'model':None,'model_name':None}
    keys={'vendor_id':'vendor','cpu family':'family','model':'model','model name':'model_name'}
    for line in (data.decode(errors='replace').splitlines()if data is not None else[]):
        if not line.strip():
            if any(out.values()):break  # the end of the first processor block
            continue
        k,_,v=line.partition(':');k=k.strip();v=v.strip()
        if k=='CPU implementer'and out['vendor']is None:out['vendor']='arm-implementer-'+v
        elif k in keys and out[keys[k]]is None:out[keys[k]]=v
    if not out['vendor']:out['vendor']=f'{sys.platform}-{os.uname().machine}'
    return out

def read_cpu_identity()->dict:
    """This node's cpu_identity, from /proc/cpuinfo where it exists (the file the claim's fingerprint reads)."""
    try:data=Path('/proc/cpuinfo').read_bytes()
    except OSError:data=None
    return cpu_identity(data)

def cpu_model(counter=None,identity=None)->str|None:
    """CPU model: the 'model name' line of /proc/cpuinfo (Linux); without /proc/cpuinfo (macOS) platform.processor(),
    which CPython answers by running `uname -p` once per process and caching it. counter['bytes'] adds the bytes read
    in-process: /proc/cpuinfo, or the probe's output line read back through its pipe (counted when the cache was cold).
    identity (a dict) receives cpu_identity() of the same bytes, so the vendor costs no second read (F5)."""
    try:data=Path('/proc/cpuinfo').read_bytes();_count(counter,len(data))
    except OSError:data=None
    if identity is not None:identity.update(cpu_identity(data))
    for line in (data.decode(errors='replace').splitlines()if data is not None else[]):
        if line.startswith('model name'):return line.split(':',1)[1].strip()
    c=getattr(platform,'_uname_cache',None);cold=c is None or 'processor'not in getattr(c,'__dict__',{})
    p=platform.processor()
    if cold and p:_count(counter,len(p.encode())+1)  # the probe printed '<processor>\n'
    return p or None

def glibc_version()->str|None:
    try:return os.confstr('CS_GNU_LIBC_VERSION')
    except (ValueError,OSError,AttributeError):return None

def elf_interpreter(path:Path,counter=None)->str|None:
    """PT_INTERP of a 64-bit little-endian ELF executable (the ld.so it requests), else None. Reads only the ELF header,
    the program headers and the interpreter string."""
    try:
        with open(path,'rb')as f:
            h=f.read(64);_count(counter,len(h))
            if h[:4]!=b'\x7fELF'or h[4]!=2 or h[5]!=1:return None
            phoff=int.from_bytes(h[32:40],'little');phentsize=int.from_bytes(h[54:56],'little');phnum=int.from_bytes(h[56:58],'little')
            for i in range(phnum):
                f.seek(phoff+i*phentsize);ph=f.read(phentsize);_count(counter,len(ph))
                if int.from_bytes(ph[0:4],'little')==3:
                    off=int.from_bytes(ph[8:16],'little');size=int.from_bytes(ph[32:40],'little');f.seek(off);s=f.read(size);_count(counter,len(s))
                    return s.rstrip(b'\0').decode()
    except OSError:return None
    return None

# Z6 (S6-C-R3-01): the ldd lines without '=>'. glibc's loader traces an object whose name is the file it loaded as
# '\t<name> (0x<address>)' (elf/rtld.c): an object requested by an absolute path (an LD_PRELOAD library, a dependency
# named by path, the ELF interpreter) or the kernel's virtual DSO; a static executable gives 'statically linked' or
# 'not a dynamic executable'.
LDD_ADDRESS=re.compile(r'\(0x[0-9a-fA-F]+\)')
VDSO_NAME=re.compile(r'linux-(?:vdso|gate)[0-9]*\.so\.[0-9]+')
LDD_STATIC=('statically linked','not a dynamic executable')

# W7 (S6-C-R4-01, Stage-6 fix round 4): dynamic-loader overrides. The runtime identity is the content of the loaded
# libraries, so it must also fix WHICH implementation of an interposed symbol runs. Without a loader override that is
# decided by the libraries' bytes (the DT_NEEDED order of the executable and of each hashed library). These variables
# change it without changing any library's bytes: LD_PRELOAD (preloaded objects interpose ahead of everything, in the
# list's order: 'A.so:B.so' and 'B.so:A.so' load the same files), LD_AUDIT (audit modules can rebind any symbol),
# LD_DYNAMIC_WEAK (weak definitions in later objects are no longer overridden; glibc honours it when merely set) and
# their macOS counterparts. A campaign worker refuses to run with any of them set (production.py run and the lane
# worker: exit 64, nothing pinned or run); unset them (`env -u LD_PRELOAD ...`). GLIBC_TUNABLES can select other
# CPU-specific (IFUNC) implementations inside libc and libm: it is recorded in the fingerprint and, when set, is part
# of the runtime identity (loader_env), so a campaign never mixes values. An object preloaded through /etc/ld.so.preload
# is listed by ldd by its path; the ORDER of such path entries is recorded too (preload_order).
LOADER_REFUSED=('LD_PRELOAD','LD_AUDIT','LD_DYNAMIC_WEAK','DYLD_INSERT_LIBRARIES','DYLD_FORCE_FLAT_NAMESPACE')
LOADER_RECORDED=('GLIBC_TUNABLES',)

def loader_overrides(env=None)->dict:
    """W7: the dynamic-loader overrides of LOADER_REFUSED that `env` (default os.environ) sets, with their values; set
    means present, even empty (glibc acts on LD_DYNAMIC_WEAK's presence alone). Empty when none is set."""
    e=os.environ if env is None else env
    return {k:e[k]for k in LOADER_REFUSED if k in e}

def loader_refusal(found:dict,what:str='the native worker')->str:
    """The refusal text for the loader overrides `found` (loader_overrides)."""
    return (f'the environment sets the dynamic-loader override(s) {", ".join(f"{k}={str(v)[:120]!r}" for k,v in found.items())}: they would decide which '
            f'implementation of an interposed numerical function {what} runs (preload order, audit rebinding, weak-symbol resolution), which the '
            'runtime identity of the loaded libraries does not show (W7). Campaign workers never run under a loader override: unset '
            + ' '.join(sorted(found))+' in the job environment (e.g. `env -u LD_PRELOAD ...`, or remove it from the site env script) and resubmit')

def loader_recorded(env=None)->dict:
    """W7: the loader-tuning variables of LOADER_RECORDED that `env` (default os.environ) sets, recorded in the
    fingerprint (loader_env) and, when any is set, in the runtime identity."""
    e=os.environ if env is None else env
    return {k:str(e[k])for k in LOADER_RECORDED if k in e}

def fingerprint(exe:Path,counter=None,identity=None)->dict:
    """Host and run-time library identity of one executable on this node: host, CPU model, glibc, the ld.so
    interpreter and every library ldd lists (path and sha256). Missing tools give null fields, never an error.
    Platform contract (PLAN R20): the one probe it starts is `ldd` on the executable (Linux); on macOS cpu_model() runs
    `uname -p` through platform and the `ldd` launch fails with ENOENT (recorded as ldd_error). counter (a dict)
    receives counter['bytes']: the bytes this process reads for the fingerprint (/proc/cpuinfo, the ELF headers, every
    hashed library and the interpreter, and the probe output read back through its pipe), kept OUTSIDE the returned
    fingerprint so that fingerprint_key() does not depend on it. identity (a dict) receives the node's cpu_identity()
    from the same /proc/cpuinfo read (F5), also outside the fingerprint.
    Z6 (S6-C-R3-01, Stage-6 fix round 3): every line of a successful probe is accounted for. 'name => /path (0x...)' is
    a resolved library (keyed by its name); an entry without '=>' listed by an absolute path ('/opt/x.so (0x...)': an
    LD_PRELOAD library, which omp_child_env keeps, or a dependency named by path) is hashed the same way and keyed by
    that path, so a preloaded library that interposes numerical functions is part of the runtime identity; the same
    form naming the executable's ELF interpreter (PT_INTERP, by path or realpath) is the interpreter, hashed once as
    'interpreter'; the kernel's virtual DSO ('linux-vdso.so.1 (0x...)', also 'linux-gate') is no file and is left out,
    as are a static executable's 'statically linked' and 'not a dynamic executable'. Any other line is recorded as an
    unexplained entry (no path, no sha256, its text as the note), which fingerprint_problems refuses for a dynamic ELF
    worker.
    W7 (S6-C-R4-01, Stage-6 fix round 4): preload_order lists the path-keyed entries (an object preloaded through
    /etc/ld.so.preload; LD_PRELOAD itself is refused before any fingerprint, loader_overrides) in the order ldd prints
    them, which is the order the loader maps them, so two nodes preloading the same objects in another order differ;
    loader_env records the loader-tuning variables that are set (LOADER_RECORDED: GLIBC_TUNABLES). runtime_identity
    includes each only when it is not empty, so the identity of an ordinary node is unchanged."""
    libs={};err=None;order=[]
    interp=elf_interpreter(exe,counter);ip=None
    real_interp=os.path.realpath(interp)if interp else None
    try:
        # One pipe for stdout and stderr: the output is read back by the file object of that pipe.
        cp=subprocess.run(['ldd',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        out=cp.stdout or b'';_count(counter,len(out));text=out.decode(errors='replace')
        if cp.returncode:err=text.strip()[-300:]
        for line in text.splitlines():
            parts=line.split()
            if not parts:continue
            if '=>'in parts:
                name=parts[0];i=parts.index('=>');target=parts[i+1]if i+1<len(parts)else''
                if target.startswith('/'):
                    real=os.path.realpath(target);libs[name]={'path':target,'resolved':real,'sha256':_digest_counted(Path(real),counter)}
                elif target!='':libs[name]={'path':None,'resolved':None,'sha256':None,'note':' '.join(parts[i+1:])}
                continue
            if cp.returncode:continue  # a failed probe is ldd_error already; its messages are no entries
            if len(parts)==2 and LDD_ADDRESS.fullmatch(parts[1]):
                name=parts[0]
                if name.startswith('/'):
                    real=os.path.realpath(name)
                    if interp and (name==interp or real==real_interp):continue  # the ELF interpreter: hashed below
                    libs[name]={'path':name,'resolved':real,'sha256':_digest_counted(Path(real),counter)};order.append(name);continue  # W7: in load order
                if VDSO_NAME.fullmatch(name):continue  # the kernel's virtual DSO: no file
            if line.strip()in LDD_STATIC:continue
            libs['unexplained: '+line.strip()[:200]]={'path':None,'resolved':None,'sha256':None,'note':'unexplained ldd line: '+line.strip()[:200]}
    except (OSError,subprocess.SubprocessError)as e:err=str(e)
    if interp:
        try:ip={'path':interp,'resolved':real_interp,'sha256':_digest_counted(Path(real_interp),counter)}
        except OSError:ip={'path':interp,'resolved':real_interp,'sha256':None}
    key=lambda n:next((v for k,v in libs.items()if k.startswith(n)),None)
    return {'host':socket.gethostname(),'cpu_model':cpu_model(counter,identity),'glibc':glibc_version(),'interpreter':ip,'libraries':libs,
            'libgmp':key('libgmp'),'libquadmath':key('libquadmath'),'libgomp':key('libgomp'),'ldd_error':err,
            'preload_order':order,'loader_env':loader_recorded(),
            'slurm':{k:os.environ.get(k)for k in('SLURM_JOB_ID','SLURM_ARRAY_JOB_ID','SLURM_ARRAY_TASK_ID','SLURM_RESTART_COUNT')}}

def fingerprint_key(fp:dict|None)->str|None:
    """Digest of a fingerprint without its per-node fields (host, Slurm ids): a summary key for status reports (it
    still includes the CPU model and the library paths). The identity that run-skip and merge enforce is
    runtime_identity_key()."""
    if not fp:return None
    return object_hash({k:v for k,v in fp.items()if k not in('host','slurm')})[:12]

RUNTIME_IDENTITY_SCHEMA='c8-d2-runtime-identity-1'
def runtime_identity(fp:dict|None)->dict|None:
    """The campaign runtime COMPATIBILITY identity of a fingerprint (X8, PLAN component D: run-skip and merge reject
    mismatches): the content of the loaded run-time library stack, without the host-specific fields. It holds the glibc
    version, the sha256 of the ELF interpreter and of every library ldd resolves (by soname; the content, not the path,
    so a library at another path with the same bytes is the same), and whether ldd answered. It leaves out the host,
    the Slurm ids and the CPU model (one campaign stays on one CPU vendor through the F5 pin; Zen 2 and Zen 3 nodes with
    identical libraries are compatible). None for no fingerprint.
    W7 (Stage-6 fix round 4): the library map is sorted (the content decides the load order of the DT_NEEDED
    libraries), but the ORDER of path-keyed (preloaded) objects is not implied by their content: 'preload_order' (the
    fingerprint's list; for a fingerprint without one, its path-keyed library entries in their recorded order) is part
    of the identity when it is not empty, and so is 'loader_env' (the recorded GLIBC_TUNABLES) when set. Both are left
    out when empty, so the identity, and its key, of a node without either is the one of the tools before the fix."""
    if not fp:return None
    lib_map=fp.get('libraries')or{}
    libs={str(n):(v.get('sha256')if isinstance(v,dict)else None)for n,v in sorted(lib_map.items())}
    ip=fp.get('interpreter');ip=ip.get('sha256')if isinstance(ip,dict)else None
    out={'schema':RUNTIME_IDENTITY_SCHEMA,'glibc':fp.get('glibc'),'interpreter_sha256':ip,'libraries':libs,'ldd':'unavailable'if fp.get('ldd_error')else'ok'}
    po=fp.get('preload_order')
    po=[str(x)for x in po]if isinstance(po,list)else[str(n)for n in (lib_map if isinstance(lib_map,dict)else{})if str(n).startswith('/')]
    if po:out['preload_order']=po
    le=fp.get('loader_env')
    if isinstance(le,dict)and le:out['loader_env']={str(k):str(v)for k,v in sorted(le.items())}
    return out

def runtime_identity_key(fp:dict|None)->str|None:
    """sha256 of runtime_identity(fp) (canonical JSON): equal keys mean a compatible library stack; None without one."""
    r=runtime_identity(fp)
    return object_hash(r)if r is not None else None

def slurm_ids(fp:dict|None)->list[str]:
    """The Slurm job ids a checkpoint's fingerprint names (the array job id for array elements, else the job id)."""
    s=(fp or{}).get('slurm')or{}
    return [str(x)for x in (s.get('SLURM_ARRAY_JOB_ID')or s.get('SLURM_JOB_ID'),)if x]

def environment_record()->dict:
    """Host, interpreter and executable provenance for test and benchmark records (A-L7)."""
    out={'host':socket.gethostname(),'platform':platform.platform(),'cpu_model':cpu_model(),'glibc':glibc_version(),'python':platform.python_version(),
         'cpu_count':os.cpu_count(),'executables':{}}
    for mod in ('numpy','scipy'):
        try:out[mod]=__import__(mod).__version__
        except ImportError:out[mod]=None
    for name in ('c8d2_decimal','c8d2_gmp'):
        exe=ROOT/'bin'/name
        if not exe.exists():continue
        rec={'sha256':digest(exe)}
        try:rec['describe']=json.loads(subprocess.run([str(exe),'--describe'],capture_output=True,text=True,check=True,timeout=120).stdout)
        except Exception as e:rec['describe']=f'unavailable: {e}'
        br=exe.with_name(name+'.build.json')
        rec['build_record']=load(br)if br.exists()else None
        out['executables'][name]=rec
    return out

# ---------------------------------------------------------------- fingerprint completeness (Y6) and form (Y8)
def elf_kind(path:Path)->str|None:
    """What the run-time identity of an executable can rest on (Y6): 'dynamic' for a 64-bit little-endian ELF file
    with a PT_INTERP segment (it loads libraries at run time: the production workers), 'static' for one without
    (nothing is loaded but the executable, whose sha256 the plan pins), 'elf' for any other ELF (another class or byte
    order, or program headers that cannot be read), None for a file that is not ELF (the test stand-in scripts of
    tests/fake_worker.py, a macOS Mach-O build). Reads the ELF header and the program headers' type words only; an
    unreadable file raises OSError."""
    with open(path,'rb')as f:
        h=f.read(64)
        if h[:4]!=b'\x7fELF':return None
        if len(h)<64 or h[4]!=2 or h[5]!=1:return 'elf'
        phoff=int.from_bytes(h[32:40],'little');phentsize=int.from_bytes(h[54:56],'little');phnum=int.from_bytes(h[56:58],'little')
        if phentsize<56:return 'elf'
        for i in range(phnum):
            f.seek(phoff+i*phentsize);t=f.read(4)
            if len(t)<4:return 'elf'
            if int.from_bytes(t,'little')==3:return 'dynamic'
    return 'static'

def virtual_dso(entry)->bool:
    """Whether a fingerprint library entry is the kernel's virtual DSO as older glibc's ldd lists it ('linux-vdso.so.1
    =>  (0x00007ffd...)': no path, the note an address only); it is mapped by the kernel, not loaded from a file."""
    if not isinstance(entry,dict)or entry.get('resolved')or entry.get('sha256'):return False
    note=str(entry.get('note')or'').strip()
    return len(note)>4 and note.startswith('(0x')and note.endswith(')')and all(c in '0123456789abcdefABCDEF'for c in note[3:-1])

def fingerprint_problems(fp:dict|None,kind:str|None,cpu:dict|None=None)->list[str]:
    """Y6 (S6-C-R2-01): why the fingerprint of a worker cannot be its campaign's runtime identity; [] when it can. For a
    dynamic ELF worker (elf_kind 'dynamic', every production build) the ldd probe must have answered (no ldd_error: an
    unavailable, failed or timed-out probe leaves the library map empty or partial, and two nodes whose probes both
    fail would get the same identity whatever their libgmp), list at least one library, and resolve every library it
    lists to a file with a sha256; the ELF interpreter must be hashed too. Another kind of ELF is refused. A static ELF
    loads nothing at run time, and a worker that is not ELF (None: the test stand-in scripts; a macOS build, where
    there is no ldd) keeps the identity as probed: the explicit handling of macOS and the test workers. The kernel's
    virtual DSO is no file: older glibc's ldd lists it as 'linux-vdso.so.1 =>  (0x...)' (an address only), which is not
    an unresolved library (virtual_dso). An unexplained ldd line (fingerprint, Z6) is an entry without a sha256 and is
    refused like an unresolved library. The same rule for the CPU vendor pin (F5): with cpu (the claim's
    cpu_identity), a dynamic ELF worker on Linux needs the vendor read from /proc/cpuinfo, not the '<platform>-<machine>'
    fallback that nodes of either vendor would share."""
    if kind is None or kind=='static':return []
    if kind!='dynamic':return ['the worker is not a 64-bit little-endian ELF executable: its run-time library stack cannot be identified']
    out=[];fp=fp if isinstance(fp,dict)else{}
    if fp.get('ldd_error'):out.append(f'the ldd probe failed ({str(fp["ldd_error"])[-160:]})')
    libs=fp.get('libraries')
    if not isinstance(libs,dict)or not libs:out.append('ldd listed no library')
    else:
        for n,v in sorted(libs.items()):
            if virtual_dso(v):continue
            if not isinstance(v,dict)or not v.get('sha256')or not v.get('resolved'):
                out.append(f'library {n} is not resolved to a hashed file ({(v or{}).get("note")if isinstance(v,dict)else v!r})')
    ip=fp.get('interpreter')
    if not isinstance(ip,dict)or not ip.get('sha256'):out.append('the ELF interpreter (ld.so) is not hashed')
    if cpu is not None and sys.platform.startswith('linux')and cpu.get('vendor')in(None,f'{sys.platform}-{os.uname().machine}'):
        out.append('the CPU vendor could not be read from /proc/cpuinfo')
    return out

def fingerprint_malformed(fp)->str|None:
    """Y8 (S6E-R2-01): why fp is not a fingerprint record as fingerprint() writes it (None when it is one): a dict with
    the keys glibc, interpreter, libraries and ldd_error, libraries a dict whose entries are dicts with a sha256 key,
    interpreter None or a dict with a sha256 key. A checkpoint without such a record carries no runtime identity."""
    if not isinstance(fp,dict):return 'no runtime fingerprint'if fp is None else f'the runtime fingerprint is a {type(fp).__name__}, not a record'
    miss=[k for k in ('glibc','interpreter','libraries','ldd_error')if k not in fp]
    if miss:return 'the runtime fingerprint lacks '+', '.join(miss)
    libs=fp['libraries']
    if not isinstance(libs,dict)or any(not isinstance(v,dict)or 'sha256'not in v for v in libs.values()):return 'the runtime fingerprint\'s library map is malformed'
    ip=fp['interpreter']
    if ip is not None and (not isinstance(ip,dict)or 'sha256'not in ip):return 'the runtime fingerprint\'s interpreter record is malformed'
    return None

# ---------------------------------------------------------------- the controlled OpenMP environment and the team check (Y2)
OMP_CONTROL_PREFIXES=('OMP_','GOMP_','KMP_')
def omp_child_env(threads:int,base=None,wait_policy:str|None=None,bind:bool=True)->dict:
    """Y2 (S6A2-02, S6-C-R2-02): the environment of EVERY native worker launch (production.py run's blocks, so the lane,
    array, sweep and direct entry points alike; the P4 lane shapes and the profilers through benchkit.omp_env), of
    the claim processes that lanes and sweeps start, and (R1, R2: Stage-6 residuals) of the test harnesses' native
    launches (tests/validate.py, sanitize.py, forced_tiers.py, quad_differential.py, numerics_flags.py's F1 tool,
    tools/prepare_inputs.py's inspector). The inherited environment WITHOUT any OpenMP runtime control (OMP_*,
    GOMP_*, KMP_*: an inherited OMP_THREAD_LIMIT=1, OMP_DYNAMIC=true or OMP_NUM_THREADS shrinks the team the worker's
    num_threads(threads) clause asks for, while its JSON still reports the request), then the controlled settings:
    OMP_NUM_THREADS=threads, OMP_DYNAMIC=FALSE, OMP_PROC_BIND=close, OMP_PLACES=cores, one BLAS thread
    (OPENBLAS_NUM_THREADS, MKL_NUM_THREADS) and OMP_WAIT_POLICY when given. Thread binding never changes a result
    (A-RPL-6). bind=False leaves OMP_PROC_BIND and OMP_PLACES unset (the inherited ones are still removed) for
    launches that run concurrently WITHOUT disjoint CPU sets (validate.py's --jobs batches, quad_differential's ranges
    jobs): each such process would otherwise bind its team to the first cores of the same affinity mask."""
    if isinstance(threads,bool)or not isinstance(threads,int)or threads<1:raise ValueError(f'OpenMP team size {threads!r}: a positive integer')
    e={k:v for k,v in (os.environ if base is None else base).items()if not k.startswith(OMP_CONTROL_PREFIXES)}
    e.update(OMP_NUM_THREADS=str(threads),OMP_DYNAMIC='FALSE')
    if bind:e.update(OMP_PROC_BIND='close',OMP_PLACES='cores')
    e.update(OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')  # the key order of the bound form is the one Y2 introduced
    if wait_policy:e['OMP_WAIT_POLICY']=wait_policy
    return e

def omp_inherited(base=None)->dict:
    """The inherited OpenMP controls that omp_child_env removes (for the logs)."""
    return {k:v for k,v in sorted((os.environ if base is None else base).items())if k.startswith(OMP_CONTROL_PREFIXES)}

TEAM_POLL_SECONDS=(0.001,0.05)  # the team watch's first and largest sampling interval (doubling)
TEAM_DEADLINE_SECONDS=60.       # by then a worker has started its first parallel region (graph loading follows the input reads)
TEAM_CPU_SECONDS=30.            # ... and a worker without its team that has used this much CPU time is computing (a stall uses none)

def proc_task_count(pid:int)->int|None:
    """The number of threads of a live process (Linux /proc/<pid>/task); None when it cannot be read (no /proc)."""
    try:return len(os.listdir(f'/proc/{pid}/task'))
    except OSError:return None

def proc_cpu_seconds(pid:int)->float|None:
    """The CPU time (user + system, all its threads) of a live process: /proc/<pid>/stat fields 14 and 15 in clock
    ticks (Linux); None when it cannot be read."""
    try:
        with open(f'/proc/{pid}/stat','rb')as f:data=f.read()
        rest=data[data.rindex(b')')+2:].split()  # after the command name, which may hold spaces: field 3 (state) onwards
        return (int(rest[11])+int(rest[12]))/os.sysconf('SC_CLK_TCK')
    except (OSError,ValueError,IndexError):return None

def team_observable()->bool:
    """Whether this platform shows a process's threads (/proc/self/task: Linux); macOS does not."""
    return proc_task_count(os.getpid())is not None

class TeamWatch:
    """Y2: the live check of a native worker's OpenMP team (as tests/thread_identity.py checks it, X3). The worker
    reports the thread count it was asked for, not the team the runtime gave it; libgomp keeps a parallel region's
    threads until the process exits and the worker starts no other thread, so once its first parallel region (the
    graph loading, right after it reads its inputs) has begun, the worker's thread count (/proc/<pid>/task) is its
    team. A thread samples that count (every 1 ms at first, doubling to 50 ms) and stops as soon as the requested team
    is seen. Verdicts (record()): 'verified' (the requested team was seen); 'smaller' (the deadline, TEAM_DEADLINE_SECONDS
    of wall time, passed without it AND the worker has used at least TEAM_CPU_SECONDS of CPU time, or its CPU time
    cannot be read: it is computing with a smaller team; on_smaller(proc) is called once, e.g. to stop the worker);
    'unverified' (the worker exited without showing it: a run too short to observe, or one that stalled before its
    first parallel region, e.g. on a file system, and never computed past TEAM_CPU_SECONDS); 'unavailable' (check
    False: a worker that is not ELF, i.e. a test stand-in; or no /proc, i.e. macOS). The CPU condition keeps a worker
    that waits (I/O, library loading) from being taken for a serial one: its serial work before the first parallel
    region (reading its task, net, gamma and rate files) takes well under a second. Before the deadline sampling
    reads a directory listing only (no file bytes: claim_io's rchar is unchanged); after it, each sample also reads the
    worker's /proc/<pid>/stat (a few hundred bytes; only for a worker that has not shown its team for a minute)."""
    def __init__(self,proc,requested:int,check:bool=True,on_smaller=None,deadline:float|None=None,cpu_deadline:float|None=None):
        import threading
        self.proc=proc;self.requested=int(requested);self.max=None;self.samples=0;self.on_smaller=on_smaller;self.cpu=None
        self.deadline=TEAM_DEADLINE_SECONDS if deadline is None else float(deadline)
        self.cpu_deadline=TEAM_CPU_SECONDS if cpu_deadline is None else float(cpu_deadline);self.t0=time.monotonic();self.state='unavailable'
        self._stop=threading.Event();self._thread=None
        if check and team_observable():
            self.state='watching';self._thread=threading.Thread(target=self._run,name='c8-team-watch',daemon=True);self._thread.start()
    def _run(self)->None:
        wait=TEAM_POLL_SECONDS[0]
        while not self._stop.is_set():
            n=proc_task_count(self.proc.pid)
            if n is not None:
                self.samples+=1;self.max=n if self.max is None else max(self.max,n)
                if self.max>=self.requested:self.state='verified';return
            if time.monotonic()-self.t0>=self.deadline:
                self.cpu=proc_cpu_seconds(self.proc.pid)
                if self.cpu is None or self.cpu>=self.cpu_deadline:
                    self.state='smaller'
                    if self.on_smaller is not None:
                        try:self.on_smaller(self.proc)
                        except Exception:pass
                    return
            self._stop.wait(wait);wait=min(2*wait,TEAM_POLL_SECONDS[1])
    def stop(self)->dict:
        """End the watch (after the worker was reaped, or on an error) and return record()."""
        self._stop.set()
        if self._thread is not None:self._thread.join()
        if self.state=='watching':self.state='unverified'
        return self.record()
    def record(self)->dict:
        return {'requested':self.requested,'observed':self.max,'verdict':self.state,'samples':self.samples,'seconds':round(time.monotonic()-self.t0,3),
                'cpu_seconds':self.cpu,'deadline_seconds':self.deadline,'cpu_deadline_seconds':self.cpu_deadline}

def team_message(rec:dict,what:str='the native worker')->str:
    """The refusal text of a 'smaller' team record."""
    cpu=rec.get('cpu_seconds')
    return (f'{what} asked for an OpenMP team of {rec["requested"]} threads but showed at most {rec["observed"]} after '
            f'{rec.get("deadline_seconds",TEAM_DEADLINE_SECONDS):g} s, with '+(f'{cpu:.1f} s of CPU time'if cpu is not None else'its CPU time unreadable')+
            ' (an OpenMP runtime control or limit outside the controlled environment, Y2): its deadline estimates and core reservation would be wrong; '
            'the worker was stopped and nothing of it was kept')
