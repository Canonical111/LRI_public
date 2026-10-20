#!/usr/bin/env python3
"""Session lock, ledger and submission-intent files of LRI_C8_D3_HPC (plan D.11, D.12; host decisions H-e..H-h).

  ledger.py check                                   record check of the ledger (read-only; prints the verdict)
  ledger.py register DIR --role plan|sweep          inside a plan or sweep job: link the job to DIR's published plan
  ledger.py resolve T --user-decision REF           manual closing of a stuck intent (HD17 "Manual closing")
  ledger.py rebuild --reason TEXT [--user-decision REF --hold-su S --hold-line dev|pilot|production]
                                                    the only repair of the ledger (D.12)
  ledger.py lockprobe --probe FILE --side job|login --markers DIR [--job ID]   J-LOCK-0's two sides; each run uses
                                                    its own DIR/<job id> (the login side: --job ID, or the one fresh
                                                    run); a lock or mount failure on either side reaches the other

No writer creates a missing ledger but admission's first use on a new root (no intent file, no c8d3- job) and rebuild:
a missing ledger with intent files or c8d3- jobs is a repair block that only `rebuild --user-decision` ends (D.12), so
`register` and `resolve` refuse (69) on a missing ledger. After a failed or short append, a writer appends nothing more.

Fixed paths (a different C8_LOCK or C8_LEDGER refuses, 64): the session lock $C8_ROOT/locks/c8d3.lock (on symmetry
SYMMETRY_LOCK_DIR/c8d3.lock on the NFS home, Amendment A1 addendum L), the ledger
$C8_ROOT/ledger.jsonl, intent files $C8_ROOT/intents/<T>.json (resolved ones under intents/resolved/), evidence under
$C8_ROOT/ledger_evidence/. On Expanse (detected from /proc/self/mountinfo or SLURM_CLUSTER_NAME, whatever C8_SITE says)
C8_SITE must be `expanse` and C8_ROOT must resolve to EXPANSE_ROOT; there every lock acquisition first checks that the
lock file's mount is Lustre with the `flock` super option (D.11). On symmetry (a BeeGFS mount at /mnt/beegfs; Amendment
A1) C8_SITE must be `symmetry` and C8_ROOT must resolve to SYMMETRY_ROOT. BeeGFS there runs with tuneUseGlobalFileLocks
= 0 (flock() checked on the local node only), so the session lock lives on the NFS home instead (addendum L, user
decision 2026-10-05): every lock acquisition first checks that the lock file's mount is NFS with `local_lock=none` and
without `nolock` (flock() then becomes a whole-file POSIX lock held at the server through NLM, seen by every node), and
refuses (69) otherwise. Such a lock belongs to the process, not to the descriptor: a second acquisition in one process
is refused (69) there instead of silently succeeding.
REF is `PLAN-REVIEW-LOG.md:<line>`, a line of the decision log given by --decision-log (default
$C8_ROOT/decisions/PLAN-REVIEW-LOG.md, the copy of LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md) that records the user's
decision.

Exit codes: 64 invalid input or settings, 65 refused, 69 unknown state, damaged ledger or repair block, 74 write failure
(EDQUOT, ENOSPC, EIO, short write), 75 the session lock is held by another process past C8_LOCK_WAIT.
Python 3.10+ standard library only (runs on the login nodes of Expanse and symmetry and inside jobs).
"""
from __future__ import annotations
import argparse,errno,fcntl,hashlib,json,math,os,re,secrets,signal,socket,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse

SCHEMA='c8-d3-ledger-1'
EXPANSE_ROOT='/expanse/lustre/scratch/zzheng8/temp_project/c8d3'
SYMMETRY_ROOT='/mnt/beegfs/zzheng1/c8d3'  # Amendment A1: the symmetry C8_ROOT (BeeGFS, user zzheng1)
SYMMETRY_MOUNT='/mnt/beegfs'              # symmetry is detected from a BeeGFS mount here
MOUNTINFO='/proc/self/mountinfo'          # module constant; only the tests replace it
SYMMETRY_LOCK_DIR='/home/zzheng1/c8d3/locks'  # addendum L: symmetry's session lock directory (NFS home); only the tests replace it
IS_LINUX=sys.platform.startswith('linux')  # module constant; only the tests replace it
MAX_RECORD=65536                          # bytes per framed line, newline included (D.12)
INTENT_GRACE=1800                         # G: gates `resolve` and `rebuild --user-decision` only; frees nothing (HD17)
LOCK_POLL=0.2                             # LOCK_NB poll interval (D.11)
DEFAULT_LOCK_WAIT=1800.0
PROBE_MAX_INTERVAL=60.0                   # lockprobe --interval: 3 LOCK_NB attempts span 2 x --interval (J-LOCK-0: 30 s)
PROBE_MAX_WAIT=600.0                      # lockprobe --wait: J-LOCK-0's handshake bound (10 min)
PROBE_SQUEUE_POLL=5.0                     # lockprobe --job: the login side's squeue poll until the job is RUNNING
KINDS=('intent','submit','adopted','register','annotation','resolution','not_submitted')
TOKEN_RE=re.compile(r'[0-9a-f]{12}')
FRAME_START=b'{"rec":'
NAME_RE=re.compile(r'c8d3-([a-z][a-z0-9_]{0,37})-([0-9a-f]{12})-([0-9a-f]{12})')
COMMENT_RE=re.compile(r'c8d3:([0-9a-f]{12}):([0-9a-f]{12}):([0-9a-f]{12})')
SITES=('expanse','symmetry','fake')
def site_root(site:str)->str:
    """The fixed C8_ROOT of a real site (read at call time: the tests replace the constants)."""
    return {'expanse':EXPANSE_ROOT,'symmetry':SYMMETRY_ROOT}[site]

# ----------------------------------------------------------------------------------------------------------------
# Test seam. C8_TEST_HOOKS is honoured only under C8_SITE=fake (refused otherwise); in-process tests may replace HOOKS.
class Hooks:
    """No-op hooks: the production behaviour."""
    def point(self,name,**info):pass          # a named step (tests: yield, kill, stall, accept a delayed job)
    def event(self,name,**info):pass          # spy log only
    def write_fault(self,point,nbytes):return None  # None | {'errno':n} | {'short':k} | {'fsync_errno':n} | {'stall':s}
    def switch(self,name):return False        # test-only controls (lock off, intents off, r5 sighting rule)
    def offset(self):return 0.0               # clock offset in seconds (fake time)
    def setting(self,name,default):return default
HOOKS=Hooks()

class FileHooks(Hooks):
    """Hooks from a JSON file (C8_TEST_HOOKS): {"events": path, "clock": path, "kill_at": {point: n},
    "stall_at": {point: seconds}, "faults": {point: spec}, "switches": [...], "settings": {...}}. A kill or fault fires
    at the n-th occurrence of its point in this process (default 1)."""
    def __init__(self,path):
        self.path=path;self.cfg=json.loads(Path(path).read_text());self.seen={}
    def _hit(self,table,name):
        spec=self.cfg.get(table,{}).get(name)
        if spec is None:return None
        n=self.seen[(table,name)]=self.seen.get((table,name),0)+1
        want=spec.get('n',1)if isinstance(spec,dict)else 1
        return spec if n==want else None
    def event(self,name,**info):
        p=self.cfg.get('events')
        if p:
            line=json.dumps({'t':time.time(),'pid':os.getpid(),'event':name,**info},default=str)+'\n'
            with open(p,'a')as f:f.write(line)
    def point(self,name,**info):
        self.event('point:'+name,**info)
        st=self._hit('stall_at',name)
        if st is not None:self.advance(st['seconds']if isinstance(st,dict)else st)
        if self._hit('kill_at',name)is not None:
            self.event('killed',at=name);os.kill(os.getpid(),signal.SIGKILL)
    def write_fault(self,point,nbytes):
        spec=self._hit('faults',point)
        if spec is None:return None
        self.event('fault',point=point,spec=spec);return spec
    def switch(self,name):return name in self.cfg.get('switches',[])
    def offset(self):
        p=self.cfg.get('clock')
        if not p:return 0.0
        try:return float(json.loads(Path(p).read_text()).get('offset',0.0))
        except (OSError,ValueError):return 0.0
    def advance(self,seconds):
        p=self.cfg.get('clock')
        if not p:raise RuntimeError('stall hook needs a clock file')
        _advance_clock(p,seconds)
    def setting(self,name,default):return self.cfg.get('settings',{}).get(name,default)

_CLOCK_LOCK=threading.Lock()
def _advance_clock(path,seconds):
    with _CLOCK_LOCK:
        fd=os.open(path,os.O_RDWR|os.O_CREAT,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            raw=os.pread(fd,4096,0)
            cur=float(json.loads(raw).get('offset',0.0))if raw.strip()else 0.0
            data=json.dumps({'offset':cur+float(seconds)}).encode()
            os.ftruncate(fd,0);os.pwrite(fd,data,0)
        finally:os.close(fd)

def now()->float:return time.time()+HOOKS.offset()
def mono()->float:return time.monotonic()+HOOKS.offset()
def utc_iso(t:float|None=None)->str:return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now()if t is None else t))
def utc_stamp()->str:t=now();return time.strftime('%Y%m%dT%H%M%S',time.gmtime(t))+f'.{int((t%1)*1e6):06d}Z'

# ----------------------------------------------------------------------------------------------------------------
# Site and settings (D.11 "Session lock", "Site detection").
def _unescape_mount(s:str)->str:return re.sub(r'\\([0-7]{3})',lambda m:chr(int(m.group(1),8)),s)

def read_mountinfo()->list[dict]:
    """Parsed /proc/self/mountinfo (OSError propagates)."""
    out=[]
    for line in Path(MOUNTINFO).read_text().splitlines():
        f=line.split(' ')
        if '-' not in f[6:]:continue
        sep=f.index('-',6)
        if len(f)<sep+4:continue
        out.append({'line':line,'majmin':f[2],'mountpoint':_unescape_mount(f[4]),'fstype':f[sep+1],'source':f[sep+2],'superopts':f[sep+3]})
    return out

def host_sites(env)->set:
    """The real sites this host belongs to, independently of C8_SITE: Expanse from a mount under /expanse/lustre or
    SLURM_CLUSTER_NAME=expanse; symmetry from a BeeGFS mount at /mnt/beegfs (its ClusterName is the generic `slurm`).
    On Linux an unreadable mountinfo refuses (64): no site can be ruled out."""
    out=set()
    if env.get('SLURM_CLUSTER_NAME')=='expanse':out.add('expanse')
    try:mounts=read_mountinfo()
    except OSError as e:
        if IS_LINUX:raise Refuse(64,f'cannot read {MOUNTINFO} to detect the site ({e}); nothing done')
        return out
    if any(m['mountpoint']=='/expanse/lustre'or m['mountpoint'].startswith('/expanse/lustre/')for m in mounts):out.add('expanse')
    if any(m['mountpoint']==SYMMETRY_MOUNT and m['fstype']=='beegfs'for m in mounts):out.add('symmetry')
    return out

def on_expanse(env)->bool:return 'expanse'in host_sites(env)

class Settings:
    """The site, C8_ROOT and the fixed paths, checked fail-closed before anything is touched."""
    def __init__(self,env:dict):
        global HOOKS
        self.env=env;hosts=host_sites(env);site=env.get('C8_SITE')or None
        if site is not None and site not in SITES:raise Refuse(64,f'C8_SITE={site!r} is not a known site (expanse, symmetry, or fake for the Mac fakes)')
        if len(hosts)>1:raise Refuse(64,f'this host looks like several sites at once ({", ".join(sorted(hosts))}); nothing done')
        self.host_site=next(iter(hosts),None);self.expanse_host=self.host_site=='expanse'
        if self.host_site and site!=self.host_site:
            raise Refuse(64,f'this host is {self.host_site} but C8_SITE is {site!r}: source ~/c8d3/env.sh (C8_SITE={self.host_site}) first')
        self.site=site
        hooks=env.get('C8_TEST_HOOKS')
        if hooks:
            if site!='fake':raise Refuse(64,'C8_TEST_HOOKS is honoured only under C8_SITE=fake (the Mac fakes)')
            if not isinstance(HOOKS,FileHooks)or HOOKS.path!=hooks:HOOKS=FileHooks(hooks)
        root=env.get('C8_ROOT')
        if not root:raise Refuse(64,f'set C8_ROOT (on Expanse: {EXPANSE_ROOT}; on symmetry: {SYMMETRY_ROOT})')
        self.root=Path(os.path.realpath(root))
        if self.host_site and str(self.root)!=site_root(self.host_site):
            raise Refuse(64,f'C8_ROOT resolves to {self.root}, not the site constant {site_root(self.host_site)}: a second root would split the lock and the ledger')
        # on symmetry the lock is on the NFS home (addendum L: BeeGFS flock() is node-local there); elsewhere under C8_ROOT
        self.lock_path=(Path(os.path.realpath(SYMMETRY_LOCK_DIR))if self.host_site=='symmetry'else self.root/'locks')/'c8d3.lock';self.ledger_path=self.root/'ledger.jsonl'
        self.intents=self.root/'intents';self.resolved=self.intents/'resolved';self.evidence=self.root/'ledger_evidence'
        for var,fixed in (('C8_LOCK',self.lock_path),('C8_LEDGER',self.ledger_path)):
            v=env.get(var)
            if v and Path(os.path.realpath(v))!=fixed:raise Refuse(64,f'{var}={v} differs from the fixed path {fixed}; unset it')
        w=env.get('C8_LOCK_WAIT',str(DEFAULT_LOCK_WAIT))
        try:self.lock_wait=float(w);assert math.isfinite(self.lock_wait)and self.lock_wait>=0
        except (ValueError,AssertionError):raise Refuse(64,f'C8_LOCK_WAIT must be a finite non-negative number of seconds (got {w!r})')

def mount_check(path:Path,site:str='expanse')->dict:
    """D.11: the mount of the lock file (entry with its st_dev and the longest mount-point prefix of its real path) must
    give cross-node flock exclusion; anything else refuses (69), naming host, mount point and options.
      expanse:  Lustre with `flock` among the super options (not localflock or noflock; F44).
      symmetry: NFS (nfs or nfs4) with `local_lock=none` among the super options and without `nolock` (Amendment A1
                addendum L): flock() is then a whole-file POSIX lock held at the server (NLM), which every node sees.
                BeeGFS is refused there: its client runs with tuneUseGlobalFileLocks = 0, checking flock() on the
                local node only."""
    host=socket.gethostname();real=os.path.realpath(path)
    try:st=os.stat(path)
    except OSError as e:raise Refuse(69,f'mount check on {host}: cannot stat {path}: {e}')
    dev=f'{os.major(st.st_dev)}:{os.minor(st.st_dev)}'
    try:mounts=read_mountinfo()
    except OSError as e:raise Refuse(69,f'mount check on {host}: cannot read {MOUNTINFO}: {e}; the lock is not taken')
    best=None
    for m in mounts:
        mp=m['mountpoint']
        if m['majmin']==dev and (real==mp or real.startswith(mp.rstrip('/')+'/')):
            if best is None or len(mp)>len(best['mountpoint']):best=m
    if best is None:raise Refuse(69,f'mount check on {host}: no {MOUNTINFO} entry has device {dev} and a mount point above {real}; the lock is not taken')
    opts=best['superopts'].split(',')
    if site=='symmetry':
        kv=dict(o.split('=',1)if '='in o else(o,'')for o in opts)
        if best['fstype']not in('nfs','nfs4')or 'nolock'in kv or kv.get('local_lock')!='none':
            raise Refuse(69,f'mount check on {host}: {real} is on {best["mountpoint"]} (type {best["fstype"]}, super options {best["superopts"]}); '
                            'on symmetry the session lock needs NFS with server-side locks (local_lock=none, not nolock): BeeGFS there checks '
                            'flock() on this node only (tuneUseGlobalFileLocks = 0), so a holder on another node would not be excluded '
                            '(Amendment A1 addendum L, D.11); the lock is not taken')
        return best
    if site!='expanse':raise Refuse(64,f'mount check: no rule for site {site!r}')
    if best['fstype']!='lustre'or 'flock'not in opts:
        raise Refuse(69,f'mount check on {host}: {real} is on {best["mountpoint"]} (type {best["fstype"]}, super options {best["superopts"]}); '
                        'the session lock needs Lustre with the flock option (not localflock or noflock); the lock is not taken')
    return best

# ----------------------------------------------------------------------------------------------------------------
# Low-level writes with test fault points (EDQUOT/ENOSPC/EIO, short writes, failing fsync, stalls).
def _quota_msg(e:OSError,path)->str:
    if e.errno==errno.EDQUOT:return (f'disk quota exceeded (EDQUOT: user files, user bytes or group bytes; on Expanse see lfs quota -u zzheng8 and lfs quota -g yun124, '
                                     f'on symmetry beegfs-ctl --getquota --uid zzheng1) writing {path}')
    if e.errno==errno.ENOSPC:return f'no space left on device (ENOSPC) writing {path}'
    return f'{e.strerror or e} (errno {e.errno}) writing {path}'

class WriteFailed(Refuse):
    def __init__(self,msg,written=0):super().__init__(74,msg);self.written=written

def write_once(fd:int,data:bytes,point:str,path)->None:
    """One write() of the whole buffer, checked for a short write (no retry), then fsync."""
    spec=HOOKS.write_fault(point,len(data))or{}
    if 'stall'in spec:HOOKS.advance(spec['stall'])  # a stalled write that then succeeds (age-check tests)
    if 'errno'in spec:
        e=OSError(spec['errno'],os.strerror(spec['errno']));raise WriteFailed(_quota_msg(e,path))
    if 'short'in spec:
        k=spec['short'];k={'half':len(data)//2,'n-1':len(data)-1}.get(k,k);n=os.write(fd,data[:k])
        raise WriteFailed(f'short write ({n} of {len(data)} bytes) to {path}; nothing more is appended',n)
    try:n=os.write(fd,data)
    except OSError as e:raise WriteFailed(_quota_msg(e,path))
    if n!=len(data):raise WriteFailed(f'short write ({n} of {len(data)} bytes) to {path}; nothing more is appended',n)
    if 'fsync_errno'in spec:
        e=OSError(spec['fsync_errno'],os.strerror(spec['fsync_errno']));raise WriteFailed('fsync failed: '+_quota_msg(e,path),n)
    try:os.fsync(fd)
    except OSError as e:raise WriteFailed('fsync failed: '+_quota_msg(e,path),n)

def checked_open(path,flags:int,point:str,mode=0o600)->int:
    """os.open with a test fault point at creation (`<point>:create`). FileExistsError and FileNotFoundError pass
    through unchanged (callers decide what they mean); any other OSError, EDQUOT from Lustre's file (inode) quota at
    create included, becomes WriteFailed (74)."""
    spec=HOOKS.write_fault(point+':create',0)or{}
    try:
        if 'errno'in spec:raise OSError(spec['errno'],os.strerror(spec['errno']))
        return os.open(path,flags,mode)
    except (FileExistsError,FileNotFoundError):raise
    except OSError as e:raise WriteFailed(_quota_msg(e,path))

def checked_rename(src,dst,point:str)->None:
    """os.rename with a test fault point; an OSError becomes WriteFailed (74)."""
    spec=HOOKS.write_fault(point,0)or{}
    try:
        if 'errno'in spec:raise OSError(spec['errno'],os.strerror(spec['errno']))
        os.rename(src,dst)
    except OSError as e:raise WriteFailed('rename failed: '+_quota_msg(e,src))

def fsync_dir(path:Path,point='dir_fsync')->None:
    spec=HOOKS.write_fault(point,0)or{}
    if 'errno'in spec:raise WriteFailed(_quota_msg(OSError(spec['errno'],os.strerror(spec['errno'])),path))
    try:fd=os.open(path,os.O_RDONLY)
    except OSError as e:raise WriteFailed('directory open for fsync failed: '+_quota_msg(e,path))
    try:os.fsync(fd)
    except OSError as e:raise WriteFailed('directory fsync failed: '+_quota_msg(e,path))
    finally:os.close(fd)

def ensure_dir(path:Path)->None:
    if not path.is_dir():
        try:path.mkdir(mode=0o700,parents=True,exist_ok=True);fsync_dir(path.parent)
        except OSError as e:raise WriteFailed(_quota_msg(e,path))

def write_new_file(path:Path,data:bytes,point:str)->None:
    """Create path with O_CREAT|O_EXCL (0600), one write, fsync the file and its directory. FileExistsError passes
    through; every other failure, at create included, is WriteFailed (74)."""
    fd=checked_open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,point)
    try:write_once(fd,data,point,path)
    finally:os.close(fd)
    fsync_dir(path.parent,point+':dir')

# ----------------------------------------------------------------------------------------------------------------
# The session lock (D.11): fcntl.flock on a fixed file, released by the kernel when its holder exits or dies.
# On symmetry's NFS home (addendum L) flock() is a POSIX lock: it belongs to the process (a second descriptor of the same
# process would "acquire" it too) and closing any descriptor of the file releases it. _HELD records the paths this process
# holds there, so a second acquisition in the same process is refused (69) instead of silently succeeding.
_HELD:set=set();_HELD_GUARD=threading.Lock()
class SessionLock:
    def __init__(self,s:Settings,command:str,path:Path|None=None):
        self.s=s;self.command=command;self.path=Path(path or s.lock_path);self.fd=None;self.lost=False
        self.disabled=HOOKS.switch('no_lock')  # test-only control (A-ORC-17 (c))
    def __enter__(self):self.acquire();return self
    def __exit__(self,*exc):self.release();return False
    def holder(self)->dict:
        return {'host':socket.gethostname(),'pid':os.getpid(),'slurm_job':os.environ.get('SLURM_JOB_ID'),'command':self.command,'utc':utc_iso()}
    def acquire(self):
        if self.disabled:HOOKS.event('lock_acquired',tid=threading.get_ident(),disabled=True);return
        ensure_dir(self.path.parent)
        self.posix=self.s.site=='symmetry';key=os.path.realpath(self.path)
        if self.posix:
            with _HELD_GUARD:
                if key in _HELD:raise Refuse(69,f'the session lock {self.path} is already held by this process ({self.command}): on symmetry\'s NFS '
                                              'it is a per-process POSIX lock, so a second acquisition would not exclude anything; nothing changed')
                _HELD.add(key)
            self.key=key
        try:fd=os.open(self.path,os.O_RDWR|os.O_CREAT|os.O_CLOEXEC,0o600)
        except OSError as e:
            self._unhold();raise Refuse(69 if e.errno not in(errno.EDQUOT,errno.ENOSPC)else 74,f'cannot open the session lock {self.path}: {e}')
        try:
            if self.s.site in('expanse','symmetry'):mount_check(self.path,self.s.site)
            deadline=time.monotonic()+self.s.lock_wait
            while True:
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()>=deadline:
                        try:held=os.pread(fd,4096,0).decode(errors='replace').strip()
                        except OSError:held='(unreadable)'
                        raise Refuse(75,f'the session lock {self.path} is held by another process ({held or "holder line not written yet"}); '
                                        f'waited {self.s.lock_wait:.0f} s (C8_LOCK_WAIT); nothing changed')
                    HOOKS.point('lock_wait');time.sleep(HOOKS.setting('lock_poll',LOCK_POLL))
        except BaseException:
            os.close(fd);self._unhold();raise
        self.fd=fd
        HOOKS.event('lock_acquired',tid=threading.get_ident(),command=self.command)
        try:self.check('acquisition')
        except BaseException:
            # __exit__ does not run when __enter__ raises: release here, so a failed acquisition check never leaves the
            # lock held for the rest of this process (in-process callers, tests, a second Call in one process)
            self.release();raise
    def check(self,what:str)->None:
        """Rewrite the holder line through the lock descriptor and fsync it. An evicted Lustre client's handle fails here
        (F44), so a holder that lost the lock stops (69) before the step named by `what`."""
        if self.disabled:return
        if self.lost:raise Refuse(69,f'the session lock failed an earlier fsync check; nothing more is written (before {what})')
        HOOKS.point('lock_check',what=what)
        line=(json.dumps(self.holder())+'\n').encode()
        spec=HOOKS.write_fault('lock_fsync:'+what.split(' ')[0],len(line))or HOOKS.write_fault('lock_fsync',len(line))or{}
        try:
            if 'stall'in spec:HOOKS.advance(spec['stall'])
            if 'errno'in spec or 'fsync_errno'in spec:
                n=spec.get('errno')or spec.get('fsync_errno');raise OSError(n,os.strerror(n))
            os.ftruncate(self.fd,0);os.pwrite(self.fd,line,0);os.fsync(self.fd)
        except OSError as e:
            self.lost=True   # a holder that may have lost the lock writes nothing more in this call
            raise Refuse(69,f'the session lock descriptor failed its fsync check before {what} ({e}): the lock may have been lost '
                            '(Lustre eviction); stopping before that step')
    def _unhold(self):
        k=getattr(self,'key',None)
        if k is not None:
            with _HELD_GUARD:_HELD.discard(k)
            self.key=None
    def release(self):
        if self.disabled:HOOKS.event('lock_released',tid=threading.get_ident(),disabled=True);return
        if self.fd is not None:
            HOOKS.event('lock_released',tid=threading.get_ident(),command=self.command)
            os.close(self.fd);self.fd=None
            self._unhold()

# ----------------------------------------------------------------------------------------------------------------
# Framing (D.12): {"rec":C,"sha256":"<sha256(C)>"}\n with C the canonical JSON of the payload.
def canonical(payload:dict)->str:
    return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)

def frame(payload:dict)->bytes:
    check_payload(payload)
    c=canonical(payload)
    line=('{"rec":'+c+',"sha256":"'+hashlib.sha256(c.encode('ascii')).hexdigest()+'"}\n').encode('ascii')
    if len(line)>MAX_RECORD:raise Refuse(64,f'ledger record of {len(line)} bytes exceeds {MAX_RECORD}')
    return line

def check_payload(p)->None:
    if not isinstance(p,dict)or p.get('schema')!=SCHEMA or p.get('kind')not in KINDS:raise ValueError('not a c8-d3-ledger-1 payload')
    toks=p.get('tokens')
    if not isinstance(toks,list)or not all(isinstance(t,str)and TOKEN_RE.fullmatch(t)for t in toks):raise ValueError('tokens must be a list of 12-hex tokens')

def _pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate key')
        d[k]=v
    return d
def _const(x):raise ValueError('non-finite number')

def unframe(line:bytes)->dict|None:
    """The payload of a valid line, else None: newline-terminated, strict JSON, exactly the keys rec and sha256, and
    re-framing rec reproduces the line byte for byte."""
    if not line.endswith(b'\n')or len(line)>MAX_RECORD:return None
    try:
        obj=json.loads(line[:-1].decode('ascii'),object_pairs_hook=_pairs,parse_constant=_const)
        if not isinstance(obj,dict)or set(obj)!={'rec','sha256'}:return None
        return obj['rec']if frame(obj['rec'])==line else None
    except (ValueError,UnicodeDecodeError,TypeError,Refuse,RecursionError):return None

def split_lines(data:bytes)->list[tuple[int,bytes]]:
    out=[];pos=0
    while pos<len(data):
        j=data.find(b'\n',pos);end=len(data)if j<0 else j+1;out.append((pos,data[pos:end]));pos=end
    return out

class Scan:
    """Record check of ledger bytes (D.12): status clean | torn (only the final line lacks its newline) | corrupt."""
    def __init__(self,data:bytes):
        self.data=data;self.records=[];self.lines=split_lines(data);self.status='clean';self.bad=None;self.valid_end=0
        for i,(off,line) in enumerate(self.lines):
            rec=unframe(line)
            if rec is not None and self.bad is None:self.records.append((off,len(line),rec));self.valid_end=off+len(line);continue
            if self.bad is None:self.bad=(i+1,off)
            last=i==len(self.lines)-1
            if self.bad==(i+1,off)and last and not line.endswith(b'\n'):self.status='torn'
            else:self.status='corrupt';break
    def tail(self)->bytes:return self.data[self.valid_end:]

def tokens_of_records(records)->set:
    out=set()
    for _,_,r in records:out.update(r.get('tokens',[]))
    return out

# ----------------------------------------------------------------------------------------------------------------
class Ledger:
    """The ledger and the intent files, opened only under the session lock (writers) or read without it (readers).

    An append never creates the ledger unless the writer allowed it (`create=True`, or `first_use` under admission:
    a missing ledger while intents/ holds a file or the scheduler shows a c8d3- job is a repair block, HD17/D.12, which
    only `rebuild --user-decision` ends). After a failed or short append (or a failed fsync) every later append of this
    object refuses (74): the ledger then ends in the torn bytes, which the next holder truncates (D.11 step 5)."""
    def __init__(self,s:Settings,lock:SessionLock|None=None,create:bool=False):
        self.s=s;self.lock=lock;self.path=s.ledger_path;self.records=[];self.missing=False;self.torn_skipped=False
        self.create_ok=create;self.failed=None

    # -- reading
    def read(self,writer:bool)->list[dict]:
        """Writers (under the lock): the record check, with a torn final record truncated after its evidence is kept.
        Readers (no lock): skip an incomplete final line. Interior corruption refuses (69) in both."""
        try:data=self.path.read_bytes();self.missing=False
        except FileNotFoundError:self.missing=True;self.records=[];return []
        except OSError as e:raise Refuse(69,f'cannot read the ledger {self.path}: {e}')
        sc=Scan(data)
        if sc.status=='corrupt':
            line,off=sc.bad
            raise Refuse(69,f'ledger {self.path}: interior corruption at line {line} (byte offset {off}); every writer and admission refuse '
                            'until `tools/ledger.py rebuild --reason ...` repairs it (D.12)')
        if sc.status=='torn':
            if writer:self._truncate_tail(sc)
            else:self.torn_skipped=True
        self.records=[r for _,_,r in sc.records];self.positions=[(o,n)for o,n,_ in sc.records]
        return self.records

    def _truncate_tail(self,sc:Scan):
        tail=sc.tail();HOOKS.point('torn_tail',bytes=len(tail))
        ensure_dir(self.s.evidence)
        ev=self.s.evidence/f'tail.{utc_stamp()}.{hashlib.sha256(tail).hexdigest()[:12]}'
        try:write_new_file(ev,tail,'evidence')
        except FileExistsError:
            try:same=ev.read_bytes()==tail
            except OSError as e:raise Refuse(74,f'evidence file {ev} exists and cannot be read ({e}); nothing truncated')
            if not same:raise Refuse(74,f'evidence file {ev} exists with other bytes; nothing truncated')
        except WriteFailed as e:
            try:ev.unlink()     # a partial evidence file is no evidence; the tail stays in the ledger
            except OSError:pass
            raise Refuse(74,f'cannot keep the torn ledger tail as evidence ({e}); nothing truncated')
        HOOKS.point('tail_evidence_written')
        if self.lock:self.lock.check('ledger truncation')
        try:fd=checked_open(self.path,os.O_WRONLY|os.O_CLOEXEC,'truncate')
        except FileNotFoundError as e:raise Refuse(69,f'the ledger {self.path} vanished before its truncation ({e}); nothing truncated')
        try:
            spec=HOOKS.write_fault('truncate',0)or{}
            if 'errno'in spec:raise WriteFailed(_quota_msg(OSError(spec['errno'],os.strerror(spec['errno'])),self.path))
            os.ftruncate(fd,sc.valid_end);os.fsync(fd)
        except OSError as e:raise WriteFailed('truncation failed: '+_quota_msg(e,self.path))
        finally:os.close(fd)
        print(f'C8: ledger: truncated a torn final record of {len(tail)} bytes at offset {sc.valid_end}; its bytes are kept in {ev}',file=sys.stderr)

    def first_use(self,scheduler_shows_ours:bool,who:str)->None:
        """HD17/D.12's repair condition, checked under the lock after read(writer=True): a missing ledger while intents/
        (with resolved/) holds a file or the scheduler shows a c8d3- job since the epoch refuses (69); otherwise (the
        first use on a new root) the ledger may be created by the first append."""
        if not self.missing:return
        if self.has_intent_files()or scheduler_shows_ours:
            raise Refuse(69,f'the ledger {self.path} is missing while intents/ holds files or the scheduler shows c8d3- jobs since the epoch: '
                            f'{who} refuses; run `tools/ledger.py rebuild --reason ...` (a missing ledger stays blocked until the user decides, D.12)')
        self.create_ok=True

    # -- appending
    def append(self,payload:dict)->tuple[int,int,int]:
        """Append one framed record (one write at the end, checked, fsynced; the directory too when the file is new).
        Returns (st_ino, offset, length). Any failure raises WriteFailed (74) and marks this ledger failed: no further
        append follows a failed or short one (D.11 step 5)."""
        data=frame(payload)
        if self.failed:raise WriteFailed(f'an earlier append of this call failed ({self.failed}); nothing more is appended')
        HOOKS.point('append',kind=payload['kind'])
        if self.lock:self.lock.check(f'ledger append ({payload["kind"]})')
        new=not self.path.exists()
        if new and not self.create_ok:
            raise Refuse(69,f'the ledger {self.path} is missing: nothing appended (a missing ledger is a repair block until the user decides, D.12)')
        try:
            try:fd=checked_open(self.path,os.O_WRONLY|os.O_APPEND|os.O_CLOEXEC|(os.O_CREAT if self.create_ok else 0),'ledger')
            except FileNotFoundError:raise Refuse(69,f'the ledger {self.path} vanished: nothing appended (a missing ledger is a repair block, D.12)')
            try:
                st=os.fstat(fd);off=st.st_size
                write_once(fd,data,'ledger:'+payload['kind'],self.path)
            finally:os.close(fd)
            if new:fsync_dir(self.path.parent,'ledger_dir')
        except WriteFailed as e:
            self.failed=str(e);HOOKS.event('ledger_append_failed',kind=payload['kind'],tokens=payload.get('tokens'),why=str(e))
            raise
        self.records.append(payload);self.missing=False
        HOOKS.event('ledger_append',kind=payload['kind'],tokens=payload.get('tokens'),tid=threading.get_ident())
        return st.st_ino,off,len(data)

    # -- intent files
    def intent_path(self,t:str)->Path:return self.s.intents/f'{t}.json'
    def resolved_path(self,t:str)->Path:return self.s.resolved/f'{t}.json'

    def write_intent_file(self,payload:dict,ino:int,off:int,length:int,point='intent_file')->None:
        ensure_dir(self.s.intents);ensure_dir(self.s.resolved)
        t=payload['token'];p={**payload,'ledger_st_ino':ino,'ledger_offset':off,'ledger_length':length}
        if self.lock:self.lock.check('intent file write')
        HOOKS.point('intent_file',token=t)
        write_new_file(self.intent_path(t),frame(p),point)
        HOOKS.event('intent_file',token=t,tid=threading.get_ident())

    def rename_resolved(self,t:str)->bool:
        """intents/<T>.json -> intents/resolved/<T>.json, both directories fsynced. Idempotent: a completed rename is
        never repeated. Returns True if a rename was made."""
        src=self.intent_path(t);dst=self.resolved_path(t)
        if not src.exists():return False
        ensure_dir(self.s.resolved)
        if self.lock:self.lock.check('intent rename')
        HOOKS.point('rename',token=t)
        if dst.exists():raise Refuse(69,f'both {src} and {dst} exist; nothing renamed (ledger.py rebuild)')
        spec=HOOKS.write_fault('rename',0)or{}
        try:
            if 'errno'in spec:raise OSError(spec['errno'],os.strerror(spec['errno']))
            os.rename(src,dst)
        except OSError as e:raise WriteFailed('rename failed: '+_quota_msg(e,src))
        fsync_dir(self.s.intents,'rename_dir');fsync_dir(self.s.resolved,'rename_dir')
        HOOKS.event('intent_renamed',token=t)
        return True

    def all_tokens(self)->set:
        out=set()
        for r in self.records:
            out.update(r.get('tokens',[]))
            if r.get('hold'):out.update(t for t in (r.get('covers')or[])if isinstance(t,str))
        for d in (self.s.intents,self.s.resolved):
            if d.is_dir():out.update(f.name[:12]for f in d.iterdir()if TOKEN_RE.fullmatch(f.name[:12]))
        return out

    def new_token(self)->str:
        """12 hex digits from secrets.token_hex(6), drawn again while the ledger or intents/ (with resolved/) holds it."""
        used=self.all_tokens()
        while True:
            t=secrets.token_hex(6)
            if t not in used and not self.intent_path(t).exists()and not self.resolved_path(t).exists():return t
            HOOKS.event('token_redrawn',token=t)

    def has_intent_files(self)->bool:
        return any(f.suffix=='.json'for d in (self.s.intents,self.s.resolved)if d.is_dir()for f in d.iterdir())

# ----------------------------------------------------------------------------------------------------------------
# Intent state: the union of both copies (HD17 "Intents"; H-g.4).
class Intent:
    def __init__(self,token):
        self.token=token;self.ledger=None;self.file=None;self.file_loc=None;self.file_error=None
        self.resolving=[];self.ambiguous=[];self.hold=False;self.in_memory=None
    @property
    def payload(self)->dict:return self.ledger or self.file
    @property
    def unresolved(self)->bool:
        if self.hold:return True
        if self.in_memory:return False
        return not self.resolving or self.file_loc=='pending'
    def resolve_in_memory(self,rule:str,charge:float,evidence)->None:
        """A standalone budget.py applies the evidence rules (a) and (c) as admission would, records nothing (HD17)."""
        self.in_memory={'kind':'resolution','token':self.token,'rule':rule,'charge_su':charge,'evidence':evidence,'by':'budget.py (in memory)'}
        self.resolving.append(self.in_memory)
    @property
    def resolved_in_ledger(self)->bool:return bool(self.resolving)
    def floor_su(self)->float:
        """SU floor of the token: the full reservation while unresolved (or a hold); after resolution the largest
        recorded charge_su (0 for a not_submitted)."""
        if self.unresolved:return float(self.payload.get('reservation_su',0.0))
        return max(float(r.get('charge_su',0.0))if r['kind']=='resolution'else 0.0 for r in self.resolving)
    @property
    def utc(self)->float:return float(self.payload.get('utc',0.0))

def read_intent_file(path:Path):
    try:data=path.read_bytes()
    except OSError as e:return None,f'unreadable: {e}'
    p=unframe(data)
    if p is None:return None,'invalid frame'
    if p.get('kind')!='intent'or p.get('token')!=path.name[:-5]:return None,'not the intent of its file name'
    return p,None

def scan_intent_files(s:Settings)->list:
    """(loc, path, payload or None, error or None) of every intent file in intents/ and intents/resolved/, read now.

    Readers without the lock (budget.py, `ledger.py check`) scan the files BEFORE they read the ledger: a file that
    exists was written after its ledger record was fsynced (D.11 step 5), so the later ledger read holds a copy of every
    intent whose file the scan saw, also one whose file was still being written or failed to write (D.12)."""
    out=[]
    for loc,d in (('pending',s.intents),('resolved',s.resolved)):
        if not d.is_dir():continue
        for f in sorted(d.iterdir()):
            if f.suffix=='.json'and TOKEN_RE.fullmatch(f.stem):
                p,err=read_intent_file(f);out.append((loc,f,p,err))
    return out

def intent_state(led:Ledger,files:list|None=None)->dict[str,Intent]:
    """Both copies of every intent, with resolving records. Refuses (69) when a token has no readable intent copy (an
    intent file that cannot be read without a valid ledger copy, or only resolving records left; D.12), unless a hold
    of `rebuild --user-decision` covers that token: the user's hold S then stands for whatever it held, and its
    leftovers are ignored here (they are evidence, moved out by that rebuild)."""
    out={}
    def get(t):return out.setdefault(t,Intent(t))
    for r in led.records:
        k=r['kind']
        if k=='intent':
            it=get(r['token']);it.ledger=r;it.hold=bool(r.get('hold'))
        elif k=='resolution':get(r['token']).resolving.append(r)
        elif k=='not_submitted':
            (get(r['token']).ambiguous if r.get('ambiguous')else get(r['token']).resolving).append(r)
    for loc,f,p,err in (scan_intent_files(led.s)if files is None else files):   # writers scan now; readers pass an earlier scan
        it=get(f.stem)
        if it.file_loc=='pending'and loc=='resolved':continue  # both present: the pending copy counts (union rule)
        it.file_loc=loc
        if p is not None:
            it.file={k:v for k,v in p.items()if not k.startswith('ledger_')};it.hold=it.hold or bool(p.get('hold'))
        else:it.file_error=f'{f}: {err}'
    covered=covered_tokens(out.values())
    bad=[it for it in out.values()if it.ledger is None and it.file is None and it.token not in covered]
    for it in [it for it in out.values()if it.ledger is None and it.file is None and it.token in covered]:del out[it.token]
    # A token known only from resolving records (its intent copies both lost) cannot be priced: repair needed.
    if bad:
        raise Refuse(69,'intent(s) without a readable copy: '+'; '.join(it.file_error or f'{it.token}: only resolving records survive'for it in bad)+
                        '; admission and budget.py refuse until `tools/ledger.py rebuild` (D.12)')
    return out

def covered_tokens(intents)->set:
    """Tokens that a hold of `rebuild --user-decision` covers (its `covers` list, from either copy of the hold)."""
    out=set()
    for it in intents:
        for p in (it.ledger,it.file):
            if p and p.get('hold'):out.update(t for t in (p.get('covers')or[])if isinstance(t,str))
    return out

# ----------------------------------------------------------------------------------------------------------------
# Decision references (`--user-decision REF`): a line of the decision log that records the user's decision.
def decision_ref(ref:str,log:Path)->dict:
    m=re.fullmatch(r'PLAN-REVIEW-LOG\.md:(\d+)',ref or'')
    if not m:raise Refuse(64,f'--user-decision must be PLAN-REVIEW-LOG.md:<line> (got {ref!r})')
    if log.name!='PLAN-REVIEW-LOG.md':raise Refuse(64,f'the decision log must be a PLAN-REVIEW-LOG.md (got {log})')
    try:data=log.read_bytes()
    except OSError as e:raise Refuse(64,f'cannot read the decision log {log}: {e}')
    lines=data.split(b'\n')                     # lines as the file's bytes give them (b'\n' only, not str.splitlines)
    if lines and lines[-1]==b'':lines.pop()
    n=int(m.group(1))
    raw=lines[n-1]if 1<=n<=len(lines)else b''   # the line's bytes without its newline: what the sha256 covers
    text=raw.decode('utf-8',errors='replace').removesuffix('\r')
    if not raw.strip()or 'decision'not in text.lower():
        raise Refuse(64,f'{ref} does not resolve to a decision line of {log} (a non-empty line that records the user\'s decision)')
    return {'ref':ref,'log':str(log),'line':n,'text':text,'sha256':hashlib.sha256(raw).hexdigest()}

def default_decision_log(s:Settings)->Path:return s.root/'decisions'/'PLAN-REVIEW-LOG.md'

# ----------------------------------------------------------------------------------------------------------------
# Commands
def payload(kind:str,tokens,**fields)->dict:
    return {'schema':SCHEMA,'kind':kind,'tokens':sorted(set(tokens)),**fields,'host':socket.gethostname(),'utc':now(),'utc_iso':utc_iso()}

def plan_sha12(d:Path)->str:
    m=Path(d)/'manifest.json'
    try:return hashlib.sha256(m.read_bytes()).hexdigest()[:12]
    except FileNotFoundError:return '0'*12

def dir_sha12(d)->str:return hashlib.sha256(str(Path(os.path.realpath(d))).encode()).hexdigest()[:12]

def cmd_check(a,env)->int:
    s=Settings(env);files=scan_intent_files(s);HOOKS.point('reader_files_listed')   # files first, then the ledger (readers)
    led=Ledger(s);led.read(writer=False);HOOKS.point('reader_ledger_read');its=intent_state(led,files)
    pend=sorted(t for t,i in its.items()if i.unresolved)
    print(json.dumps({'ledger':str(s.ledger_path),'missing':led.missing,'records':len(led.records),'torn_final_line_skipped':led.torn_skipped,
                      'intents':len(its),'unresolved':pend}))
    return 0

def cmd_register(a,env)->int:
    s=Settings(env);job=env.get('SLURM_JOB_ID');name=env.get('SLURM_JOB_NAME','')
    if not job:raise Refuse(64,'ledger.py register runs inside a plan or sweep job (SLURM_JOB_ID is not set)')
    m=NAME_RE.fullmatch(name)
    if not m:raise Refuse(64,f'the job name {name!r} is not a c8d3-<role>-<C>-<T> name: submit plan and sweep jobs through tools/slurm_submit.py raw')
    d=Path(os.path.realpath(a.directory))
    if not (d/'manifest.json').is_file():raise Refuse(64,f'{d} holds no published plan (manifest.json)')
    restart=env.get('SLURM_RESTART_COUNT','0')
    with SessionLock(s,f'register {d}')as lock:
        led=Ledger(s,lock);led.read(writer=True)
        if led.missing:   # this job itself is a c8d3- job submitted through the ledger: HD17's repair condition holds
            raise Refuse(69,f'the ledger {s.ledger_path} is missing: nothing registered (a missing ledger is a repair block until the user decides; '
                            '`register` never creates it, D.12)')
        for r in led.records:
            if r['kind']=='register'and r.get('job_id')==job and r.get('dir')==str(d)and str(r.get('restart_count'))==restart:
                print(f'C8: job {job} (restart {restart}) is already registered for {d}');return 0
        led.append(payload('register',[m.group(3)],token=m.group(3),job_id=job,restart_count=restart,dir=str(d),c=dir_sha12(d),p=plan_sha12(d),role=a.role,
                           name=name,name_c=m.group(2)))
    print(f'C8: registered job {job} (restart {restart}) for {d}');return 0

def cmd_resolve(a,env)->int:
    import budget
    s=Settings(env);t=a.token
    if not TOKEN_RE.fullmatch(t or''):raise Refuse(64,f'{t!r} is not a 12-hex token')
    log=Path(a.decision_log)if a.decision_log else default_decision_log(s)
    dec=decision_ref(a.user_decision,log)
    budget.check_epoch(env)
    with SessionLock(s,f'resolve {t}')as lock:
        led=Ledger(s,lock);led.read(writer=True)
        if led.missing:   # the intent to resolve has a file in intents/: HD17's repair condition holds
            raise Refuse(69,f'the ledger {s.ledger_path} is missing: nothing resolved (a missing ledger is a repair block that only '
                            '`rebuild --user-decision` ends; `resolve` never creates it, D.12)')
        its=intent_state(led)
        it=its.get(t)
        if it is None:raise Refuse(64,f'no intent with token {t} (ledger or intents/)')
        if it.hold:raise Refuse(64,f'{t} is a hold of `rebuild --user-decision`; it is never resolved')
        if not it.unresolved:raise Refuse(64,f'intent {t} is already resolved')
        age=now()-it.utc
        if age<INTENT_GRACE:raise Refuse(64,f'intent {t} is {age:.0f} s old; `resolve` acts only from G = {INTENT_GRACE} s after the intent (HD17)')
        snap=budget.Snapshot.take(env,account=False)
        live=[q.jobid for q in snap.user if q.token==t and q.live]
        if live:raise Refuse(69,f'squeue shows live job(s) {",".join(live)} carrying {t}; nothing resolved')
        ev=budget.Evaluation(snap,its)
        rule,charge,evidence=ev.evidence(it)
        if rule is None:charge=float(it.payload.get('reservation_su',0.0))
        rec=payload('resolution',[t],token=t,rule='user_decision',evidence_rule=rule,evidence=evidence,charge_su=charge,decision=dec,age_seconds=age,
                    views={'squeue':[q.raw for q in snap.user if q.token==t],'sacct':[r.raw for r in snap.rows if r.token==t]})
        led.append(rec);led.rename_resolved(t)
    print(f'C8: intent {t} resolved by the user decision {dec["ref"]} (charge_su {charge:.4f}; its slots are free, its SU stays at least that)')
    return 0

# ----------------------------------------------------------------------------------------------------------------
# rebuild (D.12): keeps every valid record, restores every intent, matches every segment of every invalid line to a
# surviving intent copy, or stays blocked (69) until the user's decision; installs the new file by rename.
TOKEN_PATTERNS=(re.compile(rb'"token":"([0-9a-f]{12})"'),re.compile(rb'c8d3-[a-z][a-z0-9_]{0,37}-[0-9a-f]{12}-([0-9a-f]{12})'),
                re.compile(rb'c8d3:[0-9a-f]{12}:[0-9a-f]{12}:([0-9a-f]{12})'))
TOKENS_LIST=re.compile(rb'"tokens":\[([^\]]*)\]')

def readable_tokens(seg:bytes)->set:
    """Tokens readable where the record format puts one: "token", the "tokens" list, a job name or a job comment."""
    out={m.group(1).decode()for p in TOKEN_PATTERNS for m in p.finditer(seg)}
    for m in TOKENS_LIST.finditer(seg):out.update(x.decode()for x in re.findall(rb'"([0-9a-f]{12})"',m.group(1)))
    return out

def segments(off:int,line:bytes)->list[tuple[int,bytes]]:
    """A line split at its frame starts; bytes before the first frame start form a segment too."""
    cuts=[i for i in range(len(line))if line.startswith(FRAME_START,i)]
    if not cuts or cuts[0]!=0:cuts=[0]+cuts
    return [(off+a,line[a:b])for a,b in zip(cuts,cuts[1:]+[len(line)])]

def _evidence(s:Settings,name:str,data:bytes)->Path:
    ensure_dir(s.evidence);p=s.evidence/name
    try:write_new_file(p,data,'evidence')
    except FileExistsError:
        try:same=p.read_bytes()==data
        except OSError as e:raise Refuse(74,f'evidence file {p} exists and cannot be read ({e})')
        if not same:raise Refuse(74,f'evidence file {p} exists with other bytes')
    return p

def _block_since(s:Settings,current:set)->float|None:
    """utc from which every current blocking condition has been on record without a break: the oldest block record of
    the newest run of block records (written since the last successful rebuild) that each list every current
    condition. A condition that was absent from a later block record (it cleared, then came back) starts again, so an
    old block of another, cleared condition never shortens G."""
    if not s.evidence.is_dir()or not current:return None
    last_ok=0.0;blocks=[]
    for f in s.evidence.iterdir():
        try:
            if f.name.startswith('rebuild.')and f.name.endswith('.json'):last_ok=max(last_ok,float(json.loads(f.read_text())['utc']))
            elif f.name.startswith('block.')and f.name.endswith('.json'):
                b=json.loads(f.read_text());blocks.append((float(b['utc']),set(b.get('conditions')or[])))
        except (OSError,ValueError,KeyError,TypeError):continue
    since=None
    for utc,conds in sorted((b for b in blocks if b[0]>last_ok),key=lambda b:b[0],reverse=True):
        if current<=conds:since=utc
        else:break
    return since

def _read_intent_files(s:Settings)->dict:
    files={}
    for loc,d in (('pending',s.intents),('resolved',s.resolved)):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.suffix=='.json'and TOKEN_RE.fullmatch(f.stem)and f.stem not in files:
                    p,err=read_intent_file(f);files[f.stem]=(loc,p,err,f)
    return files

def _hold_covers(payloads)->set:
    out=set()
    for p in payloads:
        if p and p.get('kind')=='intent'and p.get('hold'):out.update(t for t in (p.get('covers')or[])if isinstance(t,str))
    return out

def cmd_rebuild(a,env)->int:
    import budget
    s=Settings(env)
    if not a.reason:raise Refuse(64,'rebuild needs --reason TEXT (it is recorded as provenance; it unblocks nothing)')
    ud=[a.user_decision,a.hold_su,a.hold_line]
    if any(x is not None for x in ud)and not all(x is not None for x in ud):
        raise Refuse(64,'--user-decision, --hold-su and --hold-line go together (D.12)')
    if a.hold_su is not None and not(isinstance(a.hold_su,(int,float))and math.isfinite(a.hold_su)and a.hold_su>=0):   # direct callers too
        raise Refuse(64,f'--hold-su must be a finite number >= 0 (got {a.hold_su!r})')
    dec=None
    if a.user_decision:
        dec=decision_ref(a.user_decision,Path(a.decision_log)if a.decision_log else default_decision_log(s))
    budget.check_env(env);budget.check_epoch(env)
    with SessionLock(s,'rebuild')as lock:
        for f in s.root.glob('ledger.jsonl.tmp.*'):   # a stale temporary of an interrupted rebuild
            try:f.unlink()
            except OSError as e:raise WriteFailed(f'cannot remove the stale rebuild temporary {f} ({e}); nothing rebuilt')
        snap=budget.Snapshot.take(env,account=False)
        try:data=s.ledger_path.read_bytes();missing=False;ino=os.stat(s.ledger_path).st_ino
        except FileNotFoundError:data=b'';missing=True;ino=None
        kept=[];invalid=[];torn=None;lines=split_lines(data)
        for i,(off,line) in enumerate(lines):
            rec=unframe(line)
            if rec is not None:kept.append((off,line,rec))
            elif i==len(lines)-1 and not line.endswith(b'\n'):torn=(off,line)
            else:invalid.append((off,line))
        files=_read_intent_files(s)
        led_intents={r['token']for _,_,r in kept if r['kind']=='intent'}
        readable={t for t,(_,p,_,_) in files.items()if p is not None}
        surviving=led_intents|readable
        # tokens that an earlier decision's hold already covers (its leftovers are evidence, not a block)
        covered=_hold_covers([r for _,_,r in kept]+[p for _,(_,p,_,_) in files.items()])
        ranges={(p['ledger_offset'],p['ledger_length'])for _,(_,p,_,_) in files.items()if p is not None and ino is not None and p.get('ledger_st_ino')==ino}
        blocks=[];conditions=set();lost_tokens=set();matched=[];stamp=utc_stamp()
        def block(key,msg,tokens=()):blocks.append(msg);conditions.add(key);lost_tokens.update(tokens)
        for off,line in invalid:
            for so,seg in segments(off,line):
                if (so,len(seg))in ranges:matched.append({'offset':so,'length':len(seg),'by':'byte_range'});continue
                toks=readable_tokens(seg)
                if toks and toks<=surviving:matched.append({'offset':so,'length':len(seg),'by':'token','tokens':sorted(toks)});continue
                block(f'segment:{so}:{hashlib.sha256(seg).hexdigest()[:16]}',
                      f'unmatched segment at byte {so} ({len(seg)} bytes; readable tokens {sorted(toks)or "none"}, '
                      f'without a surviving intent copy: {sorted(toks-surviving)})',toks-surviving)
        for t,(loc,p,err,f) in files.items():
            if p is None and t not in led_intents and t not in covered:
                block(f'unreadable_intent_file:{t}',f'intent file {f} cannot be read ({err}) and no valid intent record carries {t}',[t])
        # A token with resolving or not_submitted records but no intent copy (both copies lost, resolved or not): the
        # same refusal as intent_state's, so whatever admission refuses, rebuild repairs or reports as a block.
        resolving={r['token']for _,_,r in kept if r['kind']in('resolution','not_submitted')and isinstance(r.get('token'),str)}
        for t in sorted(resolving-surviving-covered):
            block(f'resolving_records_without_intent:{t}',f'token {t} has resolving or not_submitted records but no intent copy (record and file both lost)',[t])
        if missing:
            block('ledger_missing',f'the ledger {s.ledger_path} is missing: a missing ledger is always a repair block (D.12, R20)')
            lost=sorted(({q.token for q in snap.user if q.token}|{r.token for r in snap.rows if r.token})-set(files))
            for t in lost:block(f'scheduler_token_without_file:{t}',f'the scheduler shows a c8d3- job whose token {t} has no intent file',[t])
        for off,line in invalid:_evidence(s,f'invalid.{stamp}.{off}.{len(line)}',line)
        if torn:_evidence(s,f'tail.{stamp}.{hashlib.sha256(torn[1]).hexdigest()[:12]}',torn[1])
        HOOKS.point('rebuild_evidence_written')
        if blocks:
            since=_block_since(s,conditions)
            if dec is None or since is None:
                _evidence(s,f'block.{stamp}.json',(json.dumps({'utc':now(),'blocks':blocks,'conditions':sorted(conditions),'reason':a.reason},indent=1)+'\n').encode())
                if dec is not None:raise Refuse(64,f'repair block recorded now; --user-decision is accepted no earlier than G = {INTENT_GRACE} s after it')
                raise Refuse(69,'repair block; nothing written but evidence (in '+str(s.evidence)+'): '+'; '.join(blocks)+
                                '. Admission and budget.py stay blocked; the host stops and asks the user. Only the user\'s decision ends it: '
                                'ledger.py rebuild --reason ... --user-decision PLAN-REVIEW-LOG.md:<line> --hold-su S --hold-line dev|pilot|production (from G after the block)')
            if now()-since<INTENT_GRACE:
                raise Refuse(64,f'--user-decision is accepted no earlier than G = {INTENT_GRACE} s after the blocking evidence '
                                f'(every current condition on record for {now()-since:.0f} s)')
        elif dec is not None:raise Refuse(64,'no repair block: --user-decision is not needed (run rebuild with --reason only)')
        # The new file: every valid record of the old file, in order, then what no kept record covers.
        recs=[r for _,_,r in kept];new=[l for _,l,_ in kept];added=[]
        for t,(loc,p,err,f) in sorted(files.items()):
            if p is not None and t not in led_intents:
                q={k:v for k,v in p.items()if not k.startswith('ledger_')};q.update(by='rebuild',restored_from=str(f),restored_utc=now())
                added.append(q)
        if dec is not None:
            covers=sorted(lost_tokens-surviving)
            ht=secrets.token_hex(6)
            while ht in surviving or ht in tokens_of_records(kept)or ht in covers or ht in covered:ht=secrets.token_hex(6)
            added.append(payload('intent',[ht],token=ht,hold=True,reservation_su=float(a.hold_su),line=a.hold_line,slots={},role='hold',decision=dec,
                                 reason=a.reason,blocks=blocks,conditions=sorted(conditions),covers=covers,by='rebuild'))
            covered|=set(covers)
        ad,notes,bad=budget.adoption(snap,recs+added,s.root,by='rebuild')
        added+=ad+notes
        for b in bad:added.append(payload('adopted',sorted(readable_tokens(' '.join(b['names']).encode())),job_id=b['job_id'],attribution=None,why=b['why'],
                                         names=b['names'],reason=a.reason,by='rebuild',dir=None))
        body=b''.join(new)+b''.join(frame(p)for p in added)
        tmp=s.root/f'ledger.jsonl.tmp.{os.getpid()}'
        lock.check('rebuild write')
        fd=checked_open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,'rebuild_tmp')
        try:write_once(fd,body,'rebuild_tmp',tmp)
        finally:os.close(fd)
        HOOKS.point('rebuild_before_rename')
        if not missing:_evidence(s,f'ledger.{stamp}.{hashlib.sha256(data).hexdigest()[:12]}.jsonl',data)
        lock.check('rebuild rename')
        checked_rename(tmp,s.ledger_path,'rebuild_rename');fsync_dir(s.root,'rebuild_dir')
        HOOKS.point('rebuild_after_rename')
        # Only now, with the new ledger (and a decision's hold that covers them) installed, does an unreadable intent
        # file without a ledger copy leave intents/ as evidence: a crash or a write failure before this point leaves the
        # repair block in place, never a missing condition without the hold (D.12: the old file or the new one).
        moved=[]
        for t,(loc,p,err,f) in sorted(files.items()):
            if p is None and t not in led_intents and t in covered and f.exists():
                ensure_dir(s.evidence);lock.check('intent file move');HOOKS.point('rebuild_move',token=t)
                checked_rename(f,s.evidence/f'unreadable_intent.{stamp}.{t}.json','rebuild_move');fsync_dir(f.parent,'rebuild_move_dir');fsync_dir(s.evidence,'rebuild_move_dir')
                moved.append(t)
        # Every unresolved intent leaves with both copies: a missing or unreadable file is re-written from its record.
        newino=os.stat(s.ledger_path).st_ino;led=Ledger(s,lock);led.read(writer=True);pos={}
        off=0
        for line in split_lines(s.ledger_path.read_bytes()):
            r=unframe(line[1])
            if r is not None and r['kind']=='intent':pos[r['token']]=(off,len(line[1]))
            off+=len(line[1])
        its=intent_state(led);rewritten=[]
        for t,it in its.items():
            if not it.unresolved or it.ledger is None:continue
            ent=files.get(t);loc=ent[0]if ent else None
            if ent is not None and ent[1]is not None:continue
            if ent is not None:   # keep what the unreadable file holds; when even that read fails, the error text
                try:old=ent[3].read_bytes()if ent[3].exists()else b''
                except OSError as e:old=f'unreadable intent file {ent[3]}: {e}\n'.encode()
                _evidence(s,f'intentfile.{stamp}.{t}',old)
            dest=(led.resolved_path(t)if loc=='resolved'else led.intent_path(t))
            ensure_dir(dest.parent);o,n=pos[t]
            body=frame({**it.ledger,'ledger_st_ino':newino,'ledger_offset':o,'ledger_length':n})
            tmpf=dest.parent/f'.{t}.json.tmp.{os.getpid()}'
            lock.check('intent file rewrite');HOOKS.point('rebuild_rewrite',token=t)
            fd=checked_open(tmpf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,'intent_file')
            try:write_once(fd,body,'intent_file',tmpf)
            finally:os.close(fd)
            checked_rename(tmpf,dest,'rebuild_rewrite');fsync_dir(dest.parent);rewritten.append(t)
        HOOKS.point('rebuild_files_done')
        summary={'utc':now(),'reason':a.reason,'decision':dec,'kept':len(kept),'invalid_lines':len(invalid),'segments_matched':matched,'torn_tail':bool(torn),
                 'restored_intents':[p['token']for p in added if p['kind']=='intent'],'adopted':[p.get('job_id')for p in added if p['kind']=='adopted'],
                 'intent_files_rewritten':rewritten,'unreadable_files_moved':moved,'blocks_overridden':blocks,'conditions_overridden':sorted(conditions)}
        _evidence(s,f'rebuild.{stamp}.json',(json.dumps(summary,indent=1,default=str)+'\n').encode())
    print('C8: ledger rebuilt: '+json.dumps({k:summary[k]for k in('kept','invalid_lines','restored_intents','adopted','intent_files_rewritten','unreadable_files_moved')}))
    return 0

# ----------------------------------------------------------------------------------------------------------------
# lockprobe (J-LOCK-0): an ordered handshake between a job on a compute node and the login node, on a probe file in
# the session lock's directory (never the live lock). Each run has its own marker directory, MARKERS/<run id> (the
# job's SLURM_JOB_ID, or a fresh id off Slurm), so a repeated probe never reads an earlier run's markers. A side whose
# own lock call or mount check fails writes `failed.<side>` there and its --out before it exits 69; the other side
# records that as the peer's lock or mount failure (the host STOPS), never as an expired handshake.
class PeerFailed(Exception):
    def __init__(self,info):super().__init__(str(info));self.info=info
class ProbeFailed(Exception):
    def __init__(self,step,error,errno_=None,**info):super().__init__(error);self.step=step;self.error=error;self.errno=errno_;self.info=info

def _mark(rd:Path,name:str,**info)->None:
    p=rd/name;tmp=rd/f'.{name}.{os.getpid()}'
    tmp.write_text(json.dumps({'t':time.time(),'host':socket.gethostname(),**info}));os.replace(tmp,p)

def _await(rd:Path,name:str,wait:float,peer:str)->dict:
    end=time.time()+wait
    while time.time()<end:
        p=rd/name
        if p.exists():
            try:return json.loads(p.read_text())
            except ValueError:pass
        f=rd/f'failed.{peer}'
        if f.exists():
            try:raise PeerFailed(json.loads(f.read_text()))
            except ValueError:pass
        time.sleep(0.05)
    raise Refuse(69,f'lockprobe: marker {name} did not appear within {wait:.0f} s (handshake expired: repeat the probe; not a lock result)')

def _nb(fd,step)->bool:
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);return True
    except BlockingIOError:return False
    except OSError as e:raise ProbeFailed(step,f'flock(LOCK_EX|LOCK_NB) failed: {e}',e.errno)

def _unlock(fd,step)->None:
    try:fcntl.flock(fd,fcntl.LOCK_UN)
    except OSError as e:raise ProbeFailed(step,f'flock(LOCK_UN) failed: {e}',e.errno)

def _blocking(fd,wait,step)->float:
    end=time.time()+wait
    while time.time()<end:
        if _nb(fd,step):return time.time()
        time.sleep(0.02)
    raise ProbeFailed(step,f'the blocking wait for the probe lock expired after {wait:.0f} s')

def _lustre_version()->str|None:
    for p in ('/sys/fs/lustre/version','/proc/fs/lustre/version'):
        try:return Path(p).read_text().strip()
        except OSError:pass
    try:return subprocess.run(['lctl','get_param','-n','version'],capture_output=True,text=True,errors='replace',timeout=20).stdout.strip()or None
    except (OSError,subprocess.SubprocessError):return None

def _beegfs_version()->str|None:
    try:return Path('/sys/module/beegfs/version').read_text().strip()or None
    except OSError:return None

def _site_record(s:Settings,probe:Path)->dict:
    """Host, filesystem client version, the site's mountinfo lines and the D.11 mount check of the probe file."""
    rec={'host':socket.gethostname(),'site':s.site}
    if s.site=='symmetry':rec['beegfs_version']=_beegfs_version();prefix=(SYMMETRY_MOUNT,'/home')   # the lock is on the NFS home (addendum L)
    else:rec['lustre_version']=_lustre_version();prefix=('/expanse/lustre/scratch',)
    try:rec['mountinfo']=[m['line']for m in read_mountinfo()if m['mountpoint'].startswith(prefix)]
    except OSError as e:rec['mountinfo']=f'unreadable: {e}'
    if s.site in('expanse','symmetry'):
        try:m=mount_check(probe,s.site);rec['mount_check']=m['line'];rec['mount_check_ok']=True
        except Refuse as e:rec['mount_check']=str(e);rec['mount_check_ok']=False
    else:rec['mount_check']='skipped (C8_SITE is neither expanse nor symmetry)';rec['mount_check_ok']=None
    return rec

CHILD=r'''
import fcntl,json,os,sys,time
fd=os.open(sys.argv[1],os.O_RDWR);fcntl.flock(fd,fcntl.LOCK_EX)
p=sys.argv[2];open(p+'.tmp','w').write(json.dumps({'t':time.time(),'pid':os.getpid()}));os.replace(p+'.tmp',p)
time.sleep(3600)
'''

def _run_dir(a,env,markers:Path)->Path:
    """The job side creates MARKERS/<run id> (64 if it exists); the login side takes MARKERS/<--job> or else the one
    fresh run directory (its `ready` marker younger than --wait and no `login_start` yet)."""
    if a.side=='job':
        rid=env.get('SLURM_JOB_ID')or f'{socket.gethostname()}-{os.getpid()}-{secrets.token_hex(3)}'
        rd=markers/rid;markers.mkdir(parents=True,exist_ok=True)
        try:rd.mkdir()
        except FileExistsError:raise Refuse(64,f'lockprobe: the marker directory {rd} of this run exists already (a repeat needs a new job)')
        return rd
    if a.job:return markers/a.job
    end=time.time()+a.wait
    while True:
        fresh=[]
        if markers.is_dir():
            for d in markers.iterdir():
                r=d/'ready'
                if d.is_dir()and r.exists()and not (d/'login_start').exists():
                    try:t=float(json.loads(r.read_text())['t'])
                    except (OSError,ValueError,KeyError):continue
                    if time.time()-t<a.wait:fresh.append(d)
        if len(fresh)==1:return fresh[0]
        if len(fresh)>1:raise Refuse(64,f'lockprobe: several fresh runs under {markers} ({", ".join(sorted(d.name for d in fresh))}): pass --job ID')
        if time.time()>end:raise Refuse(69,f'lockprobe: no fresh run under {markers} within {a.wait:.0f} s (handshake expired: repeat the probe; not a lock result)')
        time.sleep(0.05)

def cmd_lockprobe(a,env)->int:
    iv,W=a.interval,a.wait   # finite and in range (the parser's types check it too, with the option's name)
    if not(math.isfinite(iv)and math.isfinite(W)and 0<=iv<=PROBE_MAX_INTERVAL and 0<W<=PROBE_MAX_WAIT):
        raise Refuse(64,f'lockprobe: --interval must be finite in [0, {PROBE_MAX_INTERVAL:g}] s and --wait finite in (0, {PROBE_MAX_WAIT:g}] s (got {iv!r}, {W!r})')
    if iv*4>W:   # every marker wait (W) must outlast the 3 LOCK_NB attempts (2 x --interval) and the holder's --interval
        # hold, or a sound lock would fail its step (the host STOPS) for want of time
        raise Refuse(64,f'lockprobe: --wait ({W:g} s) must be at least 4 x --interval ({iv:g} s)')
    if a.job is not None and not re.fullmatch(r'[0-9]+',a.job):raise Refuse(64,f'lockprobe: --job {a.job!r} is not a Slurm job id')
    s=Settings(env);probe=Path(os.path.realpath(a.probe));markers=Path(a.markers)
    if probe==s.lock_path:raise Refuse(64,f'lockprobe never touches the live session lock; use a probe file such as {s.lock_path.parent}/probe.lock')
    if probe.parent!=s.lock_path.parent:raise Refuse(64,f'the probe file must sit in the session lock\'s directory {s.lock_path.parent}')
    ensure_dir(probe.parent)
    side=a.side;peer='login'if side=='job'else'job'
    if side=='login'and a.job:   # the job must be RUNNING before the login side starts (a queue wait is no lock result)
        import budget   # its scheduler environment: SQUEUE_* of the login shell (SQUEUE_STATES, ...) would hide the job
        qenv=budget.sched_env(env);poll=HOOKS.setting('squeue_poll',PROBE_SQUEUE_POLL);end=time.time()+W
        while True:
            try:cp=subprocess.run(['squeue','--all','-h','-j',a.job,'-o','%T'],capture_output=True,text=True,errors='replace',timeout=60,env=qenv)
            except (OSError,subprocess.SubprocessError)as e:raise Refuse(69,f'lockprobe: squeue failed ({e}); not a lock result')
            if cp.returncode==0 and cp.stdout.strip()=='RUNNING':break
            if time.time()>end:raise Refuse(69,f'lockprobe: job {a.job} is not RUNNING after {W:.0f} s (a queue wait, not a lock result)')
            time.sleep(poll)
    rd=_run_dir(a,env,markers)
    res={'side':side,'run_dir':str(rd),'steps':{}};ok=True;cur=['setup']
    def step(name,passed,**info):
        nonlocal ok;ok=ok and bool(passed);res['steps'][name]={'pass':bool(passed),**info}
    def mount(name):
        cur[0]=name;res['site']=_site_record(s,probe);good=res['site']['mount_check_ok']is not False
        step(name,good)
        if not good:raise ProbeFailed(name,res['site']['mount_check'],mount_check_ok=False)
    fd=None
    try:
        fd=os.open(probe,os.O_RDWR|os.O_CREAT|os.O_CLOEXEC,0o600)
        if side=='job':
            _mark(rd,'ready',pid=os.getpid(),slurm_job=env.get('SLURM_JOB_ID'));_await(rd,'login_start',W,peer)
            # (i) the login side holds the lock; three LOCK_NB attempts fail, then the blocking wait returns only after its
            # release: the holder keeps the lock for --interval after our NB-failed marker and writes its release marker
            # BEFORE it unlocks, so the marker must exist when our acquisition returns (a causal check; the timestamps,
            # from two clocks, are compared with 1 s of skew only as a second check)
            cur[0]='i_login_holds';_await(rd,'login_holds',W,peer);tries=[]
            for k in range(3):
                tries.append(_nb(fd,cur[0]))
                if tries[-1]:_unlock(fd,cur[0])
                if k<2:time.sleep(iv)
            _mark(rd,'job_nb_failed',attempts=tries);t_acq=_blocking(fd,W,cur[0]);seen=(rd/'login_released').exists();rel=_await(rd,'login_released',W,peer)
            step('i_login_holds',not any(tries)and seen and t_acq>=rel['t']-1.0,nb=tries,acquired=t_acq,released=rel['t'],release_marker_at_acquisition=seen)
            _unlock(fd,cur[0]);_mark(rd,'job_i_done')
            # (ii) the reverse
            cur[0]='ii_job_holds';_await(rd,'login_i_ack',W,peer);_blocking(fd,W,cur[0]);_mark(rd,'job_holds');_await(rd,'login_nb_failed',W,peer)
            time.sleep(iv)   # keep holding while the login side's blocking wait runs (an early grant would be caught there)
            t=time.time();_mark(rd,'job_released',t_release=t);_unlock(fd,cur[0]);step('ii_job_holds',True,released=t)
            # (iii) mount check, host, mountinfo, Lustre version
            mount('iii_mount')
            # (iv) a child holds the lock; SIGKILL it; the login side gets the lock within 5 s of the recorded kill
            cur[0]='iv_sigkill';_await(rd,'login_ii_done',W,peer);ch=subprocess.Popen([sys.executable,'-B','-c',CHILD,str(probe),str(rd/'child_holds')])
            try:
                _await(rd,'child_holds',W,peer);_await(rd,'login_nb_failed_iv',W,peer)
            finally:
                os.kill(ch.pid,signal.SIGKILL);t=time.time();ch.wait()
            _mark(rd,'child_killed',t_kill=t)
            done=_await(rd,'login_iv_done',W,peer);step('iv_sigkill',done.get('pass'),killed=t)
        else:
            _await(rd,'ready',W,peer);_mark(rd,'login_start')
            cur[0]='i_login_holds';got=_nb(fd,cur[0]);_mark(rd,'login_holds');_await(rd,'job_nb_failed',W,peer)
            time.sleep(iv)   # keep holding while the job's blocking wait runs (an early grant would be caught there)
            t=time.time();_mark(rd,'login_released',t_release=t);_unlock(fd,cur[0]);step('i_login_holds',got,released=t)
            _await(rd,'job_i_done',W,peer);_mark(rd,'login_i_ack')
            cur[0]='ii_job_holds';_await(rd,'job_holds',W,peer);tries=[]
            for k in range(3):
                tries.append(_nb(fd,cur[0]))
                if tries[-1]:_unlock(fd,cur[0])
                if k<2:time.sleep(iv)
            _mark(rd,'login_nb_failed',attempts=tries);t_acq=_blocking(fd,W,cur[0]);seen=(rd/'job_released').exists();rel=_await(rd,'job_released',W,peer)
            step('ii_job_holds',not any(tries)and seen and t_acq>=rel['t']-1.0,nb=tries,acquired=t_acq,released=rel['t'],release_marker_at_acquisition=seen)
            _unlock(fd,cur[0])
            mount('iii_mount');_mark(rd,'login_ii_done')
            cur[0]='iv_sigkill';_await(rd,'child_holds',W,peer);nb=_nb(fd,cur[0])
            if nb:_unlock(fd,cur[0])
            _mark(rd,'login_nb_failed_iv',nb=nb);kill=_await(rd,'child_killed',W,peer)
            t_ok=None;end=time.time()+W
            while time.time()<end:
                if _nb(fd,cur[0]):t_ok=time.time();_unlock(fd,cur[0]);break
                time.sleep(0.05)
            passed=(not nb)and t_ok is not None and t_ok-kill['t']<=5.0
            step('iv_sigkill',passed,nb_while_child_held=nb,killed=kill['t'],acquired=t_ok);_mark(rd,'login_iv_done',**{'pass':passed})
        res['verdict']='pass'if ok else'lock check failed: the host STOPS and revises the plan with the user (D.11)'
    except ProbeFailed as e:
        ok=False;res['steps'][e.step]={**res['steps'].get(e.step,{}),'pass':False,'error':e.error,'errno':e.errno,**e.info}
        res['verdict']=f'the {side} side failed its lock or mount check at {e.step}: the host STOPS and revises the plan with the user (D.11)'
        try:_mark(rd,f'failed.{side}',step=e.step,error=e.error,errno=e.errno,**e.info)
        except OSError as m:res['failed_marker_error']=str(m)
    except PeerFailed as e:
        ok=False;res['peer_failed']=e.info
        res['verdict']=f'the {peer} side failed its lock or mount check at {e.info.get("step")}: the host STOPS and revises the plan with the user (D.11)'
    except Refuse as e:   # an expired handshake: no lock result
        ok=False;res['expired']=str(e);res['verdict']='handshake expired: repeat the probe (a new job); not a lock result'
    except OSError as e:  # the probe file itself cannot be opened
        ok=False;res['steps'][cur[0]]={'pass':False,'error':str(e),'errno':e.errno}
        res['verdict']=f'the {side} side failed at {cur[0]} ({e}): the host STOPS and revises the plan with the user (D.11)'
        try:_mark(rd,f'failed.{side}',step=cur[0],error=str(e),errno=e.errno)
        except OSError:pass
    finally:
        if fd is not None:os.close(fd)
    res['pass']=ok
    if a.out:Path(a.out).write_text(json.dumps(res,indent=1,default=str)+'\n')
    print(json.dumps(res,default=str))
    if not ok:print('C8: lockprobe: '+res['verdict'],file=sys.stderr)
    return 0 if ok else 69

class Parser(argparse.ArgumentParser):
    """Usage errors exit 64 (invalid input), like every other refusal of these tools."""
    def error(self,message):raise Refuse(64,f'{self.prog}: {message}')

def finite(lo:float,hi:float|None=None,lo_open=False):
    """An argparse type: a finite number in [lo, hi] ((lo, hi] when lo_open). nan, inf and 1e999 (which float() reads
    as inf) are refused (64) before anything is done, never carried into a record or a sleep."""
    def conv(text:str)->float:
        try:v=float(text)
        except ValueError:raise argparse.ArgumentTypeError(f'{text!r} is not a number')
        if not math.isfinite(v):raise argparse.ArgumentTypeError(f'{text!r} is not finite')
        if v<lo or(lo_open and v==lo)or(hi is not None and v>hi):
            raise argparse.ArgumentTypeError(f'{text!r} is outside {"(" if lo_open else "["}{lo:g}, {hi:g}]'if hi is not None else f'{text!r} must be {">" if lo_open else ">="} {lo:g}')
        return v
    conv.__name__='finite number';return conv

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=Parser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sp=p.add_subparsers(dest='command',required=True,parser_class=Parser)
    q=sp.add_parser('check');q.set_defaults(func=cmd_check)
    q=sp.add_parser('register');q.add_argument('directory');q.add_argument('--role',choices=['plan','sweep'],required=True);q.set_defaults(func=cmd_register)
    q=sp.add_parser('resolve');q.add_argument('token');q.add_argument('--user-decision',required=True);q.add_argument('--decision-log');q.set_defaults(func=cmd_resolve)
    q=sp.add_parser('rebuild');q.add_argument('--reason');q.add_argument('--user-decision');q.add_argument('--hold-su',type=finite(0.0));q.add_argument('--hold-line',choices=['dev','pilot','production'])
    q.add_argument('--decision-log');q.set_defaults(func=cmd_rebuild)
    q=sp.add_parser('lockprobe');q.add_argument('--probe',required=True);q.add_argument('--side',choices=['job','login'],required=True);q.add_argument('--markers',required=True)
    q.add_argument('--job');q.add_argument('--interval',type=finite(0.0,PROBE_MAX_INTERVAL),default=15.0)
    q.add_argument('--wait',type=finite(0.0,PROBE_MAX_WAIT,lo_open=True),default=PROBE_MAX_WAIT);q.add_argument('--out');q.set_defaults(func=cmd_lockprobe)
    try:a=p.parse_args(argv);return a.func(a,env)or 0
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code
    except OSError as e:return os_error_exit(e)

WRITE_ERRNOS=frozenset((errno.EDQUOT,errno.ENOSPC,errno.EIO,errno.EROFS,errno.EFBIG))
def os_error_exit(e:OSError,who='C8')->int:
    """The backstop for an OSError that no step mapped: 74 for a write failure (EDQUOT, ENOSPC, EIO, EROFS, EFBIG), else
    69 (the state is unknown), with the path, never a traceback."""
    code=74 if e.errno in WRITE_ERRNOS else 69
    path=' '.join(str(x)for x in (e.filename,e.filename2)if x)
    print(f'{who}: unexpected OS error{" on "+path if path else ""}: {e.strerror or e} (errno {e.errno}); exit {code}: '
          +('a write failed' if code==74 else 'state unknown')+'; nothing further was done',file=sys.stderr)
    return code

if __name__=='__main__':sys.exit(main())
