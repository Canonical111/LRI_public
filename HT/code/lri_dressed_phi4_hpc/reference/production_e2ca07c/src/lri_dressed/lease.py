"""Cross-node claims for filesystems whose flock is node-local (BeeGFS without global locks).

A claim on key K is the directory K.lease.d/. Generation g is the file named by g, published
atomically: complete JSON is written to a temp file and hard-linked to its final name
(link is atomic and fails if the name exists). Releasing generation g writes the
tombstone g.released. Nothing is deleted or renamed online, so generation numbers
increase strictly and a delayed reclaimer can only collide with an existing number.

The key is free when it has no generation, when the highest generation is tombstoned,
or when that generation's owner is confirmed dead. Same host: pid plus process start
time. Another host: the owner's Slurm job state. Unknown, unreadable or unverifiable
owners are alive; only an explicit fenced break may override them.
"""
from __future__ import annotations
import json,os,socket,subprocess,time
from pathlib import Path

LIVE_SLURM_STATES={'RUNNING','COMPLETING','SUSPENDED','CONFIGURING','STOPPED','SIGNALING','STAGE_OUT'}
WIDTH=12


class Claimed(RuntimeError):
    """The key is owned by a live, unknown or unidentifiable owner."""


def proc_start(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except (OSError,ValueError,IndexError):return None


def identity():
    pid=os.getpid()
    return {'nonce':os.urandom(12).hex(),'host':socket.gethostname(),'pid':pid,'proc_start':proc_start(pid),
            'slurm_job':os.environ.get('SLURM_JOB_ID'),'slurm_restart':int(os.environ.get('SLURM_RESTART_COUNT') or 0),
            'time':time.time()}


def identifiable(owner):
    """An owner record that names a process: nonce, host and integer pid."""
    return isinstance(owner,dict) and isinstance(owner.get('nonce'),str) and isinstance(owner.get('host'),str) \
        and isinstance(owner.get('pid'),int)


DEAD_SLURM_STATES={'PENDING','COMPLETED','CANCELLED','FAILED','TIMEOUT','NODE_FAIL','PREEMPTED','BOOT_FAIL',
    'DEADLINE','OUT_OF_MEMORY','REQUEUED','REQUEUE_HOLD','REQUEUE_FED','SPECIAL_EXIT','REVOKED'}


def slurm_job_alive(job,restart=None,timeout=60):
    """True/False when Slurm answers definitively, None when the state is unknown.

    A requeued (PENDING) job no longer runs the processes that wrote the lease, so it is dead here.
    A job that is running again after a requeue (Restarts above the recorded incarnation) is a new
    incarnation: the recorded one is dead.
    """
    try:p=subprocess.run(['scontrol','-o','show','job',str(job)],capture_output=True,text=True,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):return None
    if p.returncode!=0:
        return False if 'Invalid job id' in (p.stderr or '') else None
    fields=dict(kv.split('=',1) for kv in p.stdout.split() if '=' in kv)
    state=fields.get('JobState');restarts=fields.get('Restarts')
    if state in LIVE_SLURM_STATES:
        if restart is None:return True
        try:return int(restarts)==int(restart) if restarts is not None else None
        except ValueError:return None
    if state in DEAD_SLURM_STATES:return False
    return None


def owner_state(owner,slurm=None):
    """'alive', 'dead' or 'unknown'."""
    if not isinstance(owner,dict):return 'unknown'
    if owner.get('host')==socket.gethostname():
        try:os.kill(int(owner['pid']),0)
        except ProcessLookupError:return 'dead'
        except (PermissionError,KeyError,ValueError,TypeError):return 'unknown'
        now=proc_start(owner['pid'])
        if owner.get('proc_start') is not None and now is not None and now!=owner['proc_start']:return 'dead'
        return 'alive'
    if owner.get('slurm_job'):
        alive=(slurm or slurm_job_alive)(owner['slurm_job'],restart=owner.get('slurm_restart'))
        return 'unknown' if alive is None else ('alive' if alive else 'dead')
    return 'unknown'


class Lease:
    def __init__(self,path,slurm=None,attempts=16,hook=None):
        self.dir=Path(str(path)+'.lease.d');self.slurm=slurm;self.attempts=attempts
        self.hook=hook or (lambda stage:None);self.me=None;self.gen=None

    def name(self,g):return self.dir/f'{g:0{WIDTH}d}'

    def generations(self):
        try:return sorted(int(p.name) for p in self.dir.iterdir() if p.name.isdigit())
        except FileNotFoundError:return []

    def read(self,g):
        try:return json.loads(self.name(g).read_text())
        except (OSError,ValueError):return None

    def tombstoned(self,g):return Path(str(self.name(g))+'.released').exists()

    def holder(self):
        """(top generation, owner record or None, free?)."""
        gens=self.generations()
        if not gens:return 0,None,True
        top=gens[-1]
        if self.tombstoned(top):return top,None,True
        owner=self.read(top)
        return top,owner,owner_state(owner,self.slurm)=='dead'

    def publish(self,g,record):
        self.dir.mkdir(parents=True,exist_ok=True)
        tmp=self.dir/f'.tmp.{record["nonce"]}'
        with open(tmp,'w') as f:f.write(json.dumps(record));f.flush();os.fsync(f.fileno())
        try:os.link(tmp,self.name(g));return True
        except FileExistsError:return False
        finally:tmp.unlink(missing_ok=True)

    def acquire(self):
        me=identity()
        for _ in range(self.attempts):
            top,owner,free=self.holder()
            if not free:raise Claimed(f'{self.dir} generation {top} owned by {owner}')
            self.hook('decided')
            if not self.publish(top+1,me):continue
            if max(self.generations())!=top+1:
                self._tombstone(top+1,me);raise Claimed(f'{self.dir} taken concurrently')
            self.me=me;self.gen=top+1;return me
        raise Claimed(f'{self.dir} contended')

    def _tombstone(self,g,me):
        path=Path(str(self.name(g))+'.released')
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
            with os.fdopen(fd,'w') as f:f.write(me['nonce']);f.flush();os.fsync(f.fileno())
        except FileExistsError:pass

    def release(self):
        if self.gen is None:return
        if (self.read(self.gen) or {}).get('nonce')==self.me['nonce']:self._tombstone(self.gen,self.me)
        self.gen=None


def break_lease(path,generation,job,slurm=None):
    """Fenced online recovery of an identified dead owner.

    Refused unless `generation` is the highest untombstoned generation, its owner record is
    readable with slurm_job == job, and Slurm confirms that job dead. Generation numbers are
    never reused, so a delayed command cannot reach a newer owner.
    """
    slurm=slurm or slurm_job_alive;lease=Lease(path,slurm);gens=lease.generations()
    if not gens or gens[-1]!=int(generation):raise Claimed(f'generation {generation} is not the current one ({gens[-1:]})')
    if lease.tombstoned(generation):return 'already released'
    owner=lease.read(generation)
    if not identifiable(owner):raise Claimed('owner record unreadable or unidentifiable: use maintenance mode')
    rec=owner.get('slurm_job')
    if not isinstance(rec,str) or not rec.strip() or not str(job).strip() or rec!=str(job):
        raise Claimed(f'generation {generation} has Slurm job {rec!r}; online recovery needs that exact recorded job')
    if slurm(job,restart=owner.get('slurm_restart')) is not False:raise Claimed(f'job {job} (incarnation {owner.get("slurm_restart")}) is not confirmed dead')
    lease._tombstone(int(generation),{'nonce':f'break:{job}'})
    if lease.generations()[-1]!=int(generation):raise Claimed('a newer generation appeared during the break')
    return f'tombstoned generation {generation} of job {job}'


def break_unreadable(path,generation):
    """Maintenance-only recovery of an UNREADABLE owner record; the caller must hold the campaign
    maintenance marker with all writers stopped. Identifiable owners must use break_lease."""
    lease=Lease(path);gens=lease.generations()
    if not gens or gens[-1]!=int(generation):raise Claimed(f'generation {generation} is not the current one')
    if lease.tombstoned(int(generation)):return 'already released'
    if identifiable(lease.read(int(generation))):raise Claimed('owner record is identifiable: use break_lease with its job')
    lease._tombstone(int(generation),{'nonce':'maintenance'});return f'tombstoned generation {generation}'
