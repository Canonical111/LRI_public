"""Site settings and read-only Slurm queries shared by the symmetry tools.

Every query failure raises SlurmError; callers treat it as "unknown" and refuse.
"""
import fcntl
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
DEFAULT_SITE=ROOT/'cluster'/'symmetry'/'site.json'
TERMINAL={'COMPLETED','FAILED','TIMEOUT','CANCELLED','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','DEADLINE','BOOT_FAIL'}
FINISHED_OK={0,73,75,76}


class SlurmError(RuntimeError):pass


def load_site(path=None):
    site=json.loads(Path(path or DEFAULT_SITE).read_text())
    for key in ('login_host','base','partition','exclude','mem','mem_gib','cores','headroom_gib','max_time','signal'):
        if key not in site:raise SystemExit(f'site file lacks {key}')
    return site


def short_host():
    return socket.gethostname().split('.')[0]


def require_login_host(site,campaign=None):
    """The submit flock is a valid mutex only if every submitter runs on one host."""
    host=short_host()
    if host!=site['login_host']:
        raise SystemExit(f'Refusing: run this on {site["login_host"]}, not {host} (BeeGFS flock is node-local)')
    if campaign is not None:
        mark=json.loads((Path(campaign)/'.campaign').read_text())
        if mark.get('login_host')!=host:raise SystemExit(f'Refusing: campaign belongs to login host {mark.get("login_host")}')


def require_frozen(site):
    if site.get('require_frozen',True) and not (ROOT/'GIT_SHA').is_file():
        raise SystemExit(f'Refusing: {ROOT} has no GIT_SHA; submit only from a frozen code copy')


@contextmanager
def submit_lock(campaign):
    path=Path(campaign)/'.submit.lock'
    with open(path,'a+') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Waiting for the campaign submit lock ...',file=sys.stderr,flush=True)
            fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)


def _run(cmd):
    try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    except (OSError,subprocess.TimeoutExpired) as exc:raise SlurmError(f'{cmd[0]}: {exc}') from None
    if r.returncode:raise SlurmError(f'{" ".join(cmd)} failed ({r.returncode}): {r.stderr.strip()}')
    return r.stdout


def user_jobs():
    """Live jobs of this user: {job id: (name, state)}."""
    user=os.environ.get('USER') or os.environ.get('LOGNAME') or ''
    out={}
    for line in _run(['squeue','-h','-u',user,'-o','%i|%j|%T']).splitlines():
        if line.strip():
            jid,name,state=line.strip().split('|',2);out[jid]=(name,state)
    return out


def sacct_state(job_id):
    """Accounting state of the job allocation, or None when sacct has no record."""
    rows=[l.split('|') for l in _run(['sacct','-X','-n','-P','-j',str(job_id),'-o','JobID,JobName,State']).splitlines() if l.strip()]
    rows=[r for r in rows if r[0]==str(job_id)]
    if not rows:return None
    return rows[-1][2].split()[0]


def sacct_by_name(name,since):
    start=time.strftime('%Y-%m-%dT%H:%M:%S',time.localtime(since))
    rows=[l.split('|') for l in _run(['sacct','-X','-n','-P','--name',name,'-S',start,'-o','JobID,JobName,State']).splitlines() if l.strip()]
    return {r[0]:r[2].split()[0] for r in rows if len(r)>=3 and r[1]==name}


def jobs_by_name(name,since,live):
    found={jid for jid,(n,_) in live.items() if n==name}
    found|=set(sacct_by_name(name,since))
    return sorted(found)


def execution_dirs(logs,job_id):
    return sorted(Path(logs).glob(f'{job_id}.r*'))


def last_events(logs,job_id):
    """Last end event per item for all executions of a job."""
    out={}
    for d in execution_dirs(logs,job_id):
        p=d/'events.jsonl'
        if not p.is_file():continue
        for line in p.read_text().splitlines():
            try:e=json.loads(line)
            except ValueError:continue
            if e.get('event')=='end':out[e['id']]=e
    return out
