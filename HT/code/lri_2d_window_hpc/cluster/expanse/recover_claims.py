"""Archive and remove stale claims whose owning Slurm job is CONFIRMED terminal by sacct.

Dry run by default. Claims with no recorded job id, an UNKNOWN sacct state, or a
live owner are never touched. With --owner-job only that job's claims qualify.

Recovery of one chain directory is serialized by an atomic `recovery.lock`
directory shared by the automatic (continuation) and manual entry points (F14).
Claim writers need not honor the lock: a claim is retired only if its owner token
is unchanged when re-read AFTER sacct confirmed the owner job terminal. A dead
owner cannot release its claim and no writer can acquire an existing claim
directory, so the atomic rename into claims_archive/ moves exactly the inspected
claim. The moved token is checked once more as a defence in depth.

Usage: python recover_claims.py --scope DIR [--owner-job ID] [--apply] [--require-none-left]
DIR is a chain directory or a campaign root (each chains/<c> is then processed).
Exit: 0 ok; 4 claims owned by --owner-job remain (with --require-none-left);
      75 a recovery lock is held (another recovery runs, or a stale lock needs a human).
"""
from __future__ import annotations
import argparse,json,os,shutil,socket,sys,time,uuid
from pathlib import Path
from common import TERMINAL,claims_under,sacct_state

LOCK='recovery.lock'


class RecoveryBusy(RuntimeError):pass


def owner_of(claim):
    """owner.json as a dict, or None if missing/unreadable/malformed (such claims are never touched; F26)."""
    try:o=json.loads((Path(claim)/'owner.json').read_text())
    except (OSError,ValueError):return None
    return o if isinstance(o,dict) else None


def chain_dirs(scope):
    scope=Path(scope)
    if (scope/'chains').is_dir():return sorted(p for p in (scope/'chains').iterdir() if p.is_dir())
    return [scope]


def _recover_chain(cdir,owner_job,apply,state_fn,log):
    archive=cdir/'claims_archive';removed=[];kept=[]
    for claim in claims_under(cdir):
        if archive in claim.parents:continue
        owner=owner_of(claim);job=(owner or {}).get('slurm_job_id');token=(owner or {}).get('token')
        if not job or not token:
            kept.append((claim,'no recorded job id/token (manual check)'));continue
        if owner_job is not None and str(job)!=str(owner_job):
            kept.append((claim,f'owned by job {job}, not {owner_job}'));continue
        state=state_fn(job)
        if state is None:kept.append((claim,f'owner {job} state UNKNOWN'));continue
        if state not in TERMINAL:kept.append((claim,f'owner {job} is {state}'));continue
        # Re-read AFTER the terminal confirmation (F14). If the token is unchanged now, the claim
        # belongs to a job that was already dead: it cannot release it, and no other writer can
        # create a claim whose directory exists. So the rename below retires exactly this claim.
        now=owner_of(claim)
        if (now or {}).get('token')!=token:
            kept.append((claim,f'ownership changed while {job} was queried; not touched'));continue
        if not apply:
            log(f'would remove {claim} (owner {job} {state})');removed.append(claim);continue
        archive.mkdir(parents=True,exist_ok=True)
        dest=archive/f'{time.strftime("%Y%m%dT%H%M%S")}_{job}_{uuid.uuid4().hex[:8]}_{claim.name}'
        os.rename(claim,dest)                      # atomic retirement of the directory we inspected
        moved=owner_of(dest)
        if (moved or {}).get('token')!=token:      # ownership changed between inspection and rename
            try:os.rename(dest,claim);msg='moved back'
            except OSError as exc:msg=f'could NOT move back ({exc}); manual check'
            kept.append((claim,f'ownership changed during recovery; {msg}'));continue
        (dest/'recovery.json').write_text(json.dumps({'claim':str(claim),'owner_job':job,'token':token,
                                                      'sacct_state':state,'unix':time.time(),'host':socket.gethostname()}))
        log(f'removed {claim} (owner {job} {state}); archived in {dest}');removed.append(claim)
    return removed,kept


def recover(scope,owner_job=None,apply=False,state_fn=sacct_state,log=print):
    removed=[];kept=[]
    for cdir in chain_dirs(scope):
        lock=cdir/LOCK
        try:lock.mkdir()
        except FileExistsError:raise RecoveryBusy(f'{lock} exists: another recovery is running or a stale lock needs a manual check')
        try:
            (lock/'owner.json').write_text(json.dumps({'host':socket.gethostname(),'pid':os.getpid(),
                                                       'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'unix':time.time()}))
            r,k=_recover_chain(cdir,owner_job,apply,state_fn,log);removed+=r;kept+=k
        finally:
            shutil.rmtree(lock,ignore_errors=True)
    for claim,why in kept:log(f'kept {claim}: {why}')
    return removed,kept


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scope',required=True)
    ap.add_argument('--owner-job');ap.add_argument('--apply',action='store_true')
    ap.add_argument('--require-none-left',action='store_true',help='with --owner-job: fail if that job still owns a claim')
    a=ap.parse_args(argv)
    try:removed,kept=recover(a.scope,a.owner_job,a.apply)
    except RecoveryBusy as exc:print(str(exc),file=sys.stderr);return 75
    if a.require_none_left and a.owner_job is not None:
        left=[c for c,_ in kept if str((owner_of(c) or {}).get('slurm_job_id'))==str(a.owner_job)]
        if left or (not a.apply and removed):
            print(f'claims owned by {a.owner_job} remain: {[str(c) for c in (left or removed)]}',file=sys.stderr);return 4
    return 0


if __name__=='__main__':raise SystemExit(main())
