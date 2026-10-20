"""Node-local checkpoints published to shared storage as one tar file per task (cluster jobs).

The solver (src/lri_coeff, unchanged) writes each checkpoint generation as a directory of .npy files under
ROOT/<identity>/ and then points ROOT/<identity>/latest.json at it. In a cluster job ROOT is node-local, and
this module
  - restores the task's published archive into ROOT before the solver starts (the solver's --resume then
    verifies every array checksum);
  - runs the solver as a child, forwarding USR1/TERM/INT to it;
  - every POLL seconds, and once more after the solver exits, publishes a new generation as ONE tar file:
    hard-link snapshot of the generation (immune to the solver deleting it), tar written to a temporary name
    next to the archive (.<archive>.partial-<jobid>), fsync, every file read back and checked against the
    SHA-256 digests the solver recorded (as --resume will), atomic rename, directory fsync. The previous
    archive stays valid until the rename and is never replaced by one that fails these checks;
  - if, after the solver stopped, its newest generation still cannot be published (three attempts), writes
    the marker file UNPUBLISHED next to ROOT (cluster/job.sbatch then keeps the node-local directory and says
    so) and turns exit 75 ("checkpoint saved") into 76 ("checkpoint NOT saved");
  - removes the archive after a successful run (exit 0: the result exists), and partial archives left by
    hard-killed earlier jobs of the task once Slurm reports those jobs ended.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,signal,subprocess,sys,tarfile,time

FORWARDED=(signal.SIGUSR1,signal.SIGTERM,signal.SIGINT)
TERMINAL={'BOOT_FAIL','CANCELLED','COMPLETED','DEADLINE','FAILED','NODE_FAIL','OUT_OF_MEMORY','PREEMPTED','REVOKED','TIMEOUT'}
NOT_PUBLISHED=76
RETRY_WAITS=(0,10,30)   # seconds before each final publication attempt

def latest(root):
    """(identity directory, latest.json bytes, generation name) of the newest identity under root, or None."""
    best=None
    if root.is_dir():
        for d in root.iterdir():
            f=d/'latest.json'
            if d.is_dir() and not d.is_symlink() and f.is_file() and (best is None or f.stat().st_mtime>best[0]):best=(f.stat().st_mtime,d)
    if best is None:return None
    d=best[1];raw=(d/'latest.json').read_bytes();gen=json.loads(raw)['payload']['generation']
    if Path(gen).name!=gen or not gen.startswith('generation-'):raise ValueError(f'unsafe generation name {gen!r}')
    return d,raw,gen

class PublishError(Exception):
    """A generation could not be published; the previous archive is untouched."""
    def __init__(self,msg,local_key=None):super().__init__(msg);self.local_key=local_key

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def envelope_ok(raw):
    w=json.loads(raw)
    return w.get('schema')=='lri-coeff-v1' and hashlib.sha256(canonical(w['payload'])).hexdigest()==w.get('sha256')
def sha_stream(f):
    h=hashlib.sha256()
    for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()

def publish(root,archive,tag,last,skip=None):
    """Publish the newest complete generation if it differs from `last` (and from `skip`, a generation whose
    local files failed verification); return what is now published. Raises PublishError (or OSError,
    tarfile.TarError) without touching the previous archive."""
    cur=latest(root)
    if cur is None:return last
    d,raw,gen=cur;key=(d.name,gen)
    if key in (last,skip):return last
    snap=root.parent/f'.snapshot-{tag}';shutil.rmtree(snap,ignore_errors=True)
    try:
        src=d/gen;meta=json.loads((src/'metadata.json').read_text())['payload']
        dst=snap/d.name/gen;dst.mkdir(parents=True)
        for name in [n+'.npy' for n in meta['files']]+['metadata.json']:os.link(src/name,dst/name)
        (snap/d.name/'latest.json').write_bytes(raw)
    except (FileNotFoundError,KeyError,ValueError):
        # The solver replaced this generation meanwhile (or it is incomplete); the next poll publishes the new one.
        shutil.rmtree(snap,ignore_errors=True);return last
    archive.parent.mkdir(parents=True,exist_ok=True)
    tmp=archive.with_name(f'.{archive.name}.partial-{tag}')
    try:
        # Exactly what the solver's --resume will verify: the envelope digests of latest.json and metadata.json
        # and the SHA-256 that metadata.json records for every array. Check the snapshot first, then every
        # byte of the archive read back from shared storage; only then replace the previous archive.
        meta_raw=(dst/'metadata.json').read_bytes()
        if not (envelope_ok(raw) and envelope_ok(meta_raw)):raise PublishError(f'{d.name[:12]}/{gen}: metadata or latest.json fails its digest',key)
        files=json.loads(meta_raw)['payload']['files']
        want={f'{d.name}/{gen}/{n}.npy':files[n]['sha256'] for n in files}
        want[f'{d.name}/{gen}/metadata.json']=hashlib.sha256(meta_raw).hexdigest();want[f'{d.name}/latest.json']=hashlib.sha256(raw).hexdigest()
        for name,h in want.items():
            with open(snap/name,'rb') as f:
                if sha_stream(f)!=h:raise PublishError(f'local checkpoint file {name} does not match its recorded SHA-256',key)
        with open(tmp,'wb') as f:
            with tarfile.open(fileobj=f,mode='w',format=tarfile.PAX_FORMAT) as t:t.add(snap/d.name,arcname=d.name)
            f.flush();os.fsync(f.fileno())
        with tarfile.open(tmp) as t:got={m.name:sha_stream(t.extractfile(m)) for m in t.getmembers() if m.isfile()}
        if got!=want:raise PublishError(f'{tmp} read back from shared storage differs from the checkpoint')
        os.replace(tmp,archive)
        fd=os.open(archive.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        tmp.unlink(missing_ok=True);shutil.rmtree(snap,ignore_errors=True)
    print(f'ckpt_sync: published {d.name[:12]}/{gen} -> {archive}',flush=True)
    return key

def attempt(root,archive,tag,last,skip,what):
    """publish() that never raises: returns (published, skip) and reports failures."""
    try:return publish(root,archive,tag,last,skip),skip
    except Exception as exc:
        print(f'ckpt_sync: {what} failed ({exc!r})',file=sys.stderr,flush=True)
        return last,(getattr(exc,'local_key',None) or skip)

def unpublished(root,last):
    """True if root holds a newer generation than the published one (or cannot be read)."""
    try:cur=latest(root)
    except Exception:return True
    return cur is not None and (cur[0].name,cur[2])!=last

def job_live(jid):
    """False only if Slurm reports job jid ended or unknown to the controller; any doubt counts as live."""
    try:p=subprocess.run(['squeue','-h','-j',jid,'-o','%T'],capture_output=True,text=True,timeout=60)
    except (OSError,subprocess.TimeoutExpired):return True
    if p.returncode:return 'Invalid job id' not in p.stderr
    st=p.stdout.split()
    return bool(st) and st[0] not in TERMINAL

def clean_partials(archive,tag):
    """Remove partial archives of this task left by hard-killed jobs that have ended (and our own)."""
    for f in archive.parent.glob(f'.{archive.name}.partial-*'):
        jid=f.name.rsplit('-',1)[1]
        if jid==tag or (jid.isdigit() and not job_live(jid)):
            f.unlink(missing_ok=True);print(f'ckpt_sync: removed stale {f.name}',flush=True)

def restore(archive,root):
    """Unpack a published archive into root; return its (identity, generation) or None."""
    if not archive.is_file():return None
    root.mkdir(parents=True,exist_ok=True)
    with tarfile.open(archive) as t:
        members=t.getmembers();names={m.name.split('/')[0] for m in members}
        if len(names)!=1 or not re.fullmatch(r'[0-9a-f]{64}',next(iter(names))):raise ValueError(f'{archive}: expected one identity directory, got {sorted(names)}')
        for m in members:
            p=Path(m.name)
            if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()):raise ValueError(f'{archive}: unsafe member {m.name!r}')
        t.extractall(root,members=members,**({'filter':'data'} if hasattr(tarfile,'data_filter') else {}))
    ident=names.pop();gen=json.loads((root/ident/'latest.json').read_text())['payload']['generation']
    print(f'ckpt_sync: restored {ident[:12]}/{gen} from {archive}',flush=True)
    return (ident,gen)

def supervise(cmd,env,root,archive,tag,poll=60.0):
    """Run cmd with checkpoints in node-local root and publication to archive; return its exit status."""
    state={'child':None,'pending':[]}
    def forward(sig,frame):
        if state['child'] is None:state['pending'].append(sig)
        else:
            try:state['child'].send_signal(sig)
            except ProcessLookupError:pass
    for s in FORWARDED:signal.signal(s,forward)
    last=restore(archive,root)
    try:clean_partials(archive,tag)
    except OSError as exc:print(f'ckpt_sync: partial cleanup failed ({exc})',file=sys.stderr,flush=True)
    state['child']=child=subprocess.Popen(cmd,env=env)
    for s in state['pending']:child.send_signal(s)
    skip=None
    try:
        while True:
            try:rc=child.wait(timeout=poll);break
            except subprocess.TimeoutExpired:pass
            last,skip=attempt(root,archive,tag,last,skip,'publish')
        rc=rc if rc>=0 else 128-rc
        if rc==0:
            archive.unlink(missing_ok=True);clean_partials(archive,tag)
            return 0
        for wait in RETRY_WAITS:
            time.sleep(wait)
            last,skip=attempt(root,archive,tag,last,skip,'final publish')
            if not unpublished(root,last):return rc
    except Exception as exc:
        # The supervisor itself failed: keep managing the solver until it ends, then keep its checkpoints.
        print(f'ckpt_sync: supervisor error ({exc!r}); waiting for the solver',file=sys.stderr,flush=True)
        rc=child.wait();rc=rc if rc>=0 else 128-rc
        if rc==0:return 0
    try:(root.parent/'UNPUBLISHED').write_text(f'{root}\n')
    except OSError as exc:print(f'ckpt_sync: cannot write the UNPUBLISHED marker ({exc})',file=sys.stderr,flush=True)
    print(f'ckpt_sync: the newest checkpoint in {root} could NOT be published to {archive}; a resubmission '
          'resumes from the previous archive, if any',file=sys.stderr,flush=True)
    return NOT_PUBLISHED if rc==75 else rc
