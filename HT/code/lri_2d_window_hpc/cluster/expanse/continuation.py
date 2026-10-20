"""Guard for a wall-time continuation job (HT2D_PREV set). Runs after release verification.

Exit 0: resume the chain. 10: chain already complete (records validated). 11: the
predecessor recorded a failure (human needed). 12: another job of this chain is
pending/running. 75: UNKNOWN scheduler state or unrecoverable claim (manual check).
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from common import EnvUnavailable,SpecError,TERMINAL,chain_dir,check_predecessor,load_object,load_spec,sacct_state,steps,verify_runtime
import recover_claims


def squeue_ids(name,tries=3,pause=30,run=subprocess.run):
    for k in range(tries):
        try:
            p=run(['squeue','-h','-u',os.environ.get('USER',''),'-n',name,'-o','%i'],capture_output=True,text=True,timeout=60)
            if p.returncode==0:return [l.strip() for l in p.stdout.splitlines() if l.strip()]
        except (OSError,subprocess.TimeoutExpired):pass
        if k<tries-1:time.sleep(pause)
    return None


def read_state(path):
    """PREV's state as a validated dict; {'status':'missing'} if absent; None if malformed (F26)."""
    path=Path(path)
    if not path.exists():return {'status':'missing'}
    try:_,_,st=load_object(path,'Chain state')
    except SpecError:return None
    fc=st.get('failed_checks',[])
    if st.get('status') not in ('complete','stopped','failed') or not isinstance(fc,list):return None
    if not all(isinstance(f,dict) and isinstance(f.get('L'),int) and isinstance(f.get('nz'),int) for f in fc):return None
    return st


def chain_complete(spec,chain,failed_checks):
    """Completion from the RECORDS (F3, F10): every main record validates; every check has a
    validating record or an entry in the predecessor's failed_checks list."""
    failed={(int(f['L']),int(f['nz'])) for f in failed_checks or []}
    for s in steps(spec,chain):
        try:
            check_predecessor(spec,{'chain':chain,'L':s['L'],'nz':s['nz']});continue
        except (SpecError,ValueError,KeyError,OSError):pass
        if s['role']=='check' and (s['L'],s['nz']) in failed:continue
        return False
    return True


def guard(spec,chain,prev,me,name,state_fn=sacct_state,queue_fn=squeue_ids,log=print):
    state=state_fn(prev)
    if state is None:log(f'continuation: predecessor {prev} state UNKNOWN after retries; manual check');return 75
    if state not in TERMINAL:log(f'continuation: predecessor {prev} is {state}, not terminal; refusing');return 75
    ids=queue_fn(name)
    if ids is None:log('continuation: squeue failed; duplicate status UNKNOWN; manual check');return 75
    others=[i for i in ids if i!=str(me)]
    if others:log(f'continuation: other jobs of {name} exist: {others}; not resuming');return 12
    cdir=chain_dir(spec,chain)
    # Always recover PREV's claims first: a predecessor killed after writing its state may
    # still hold chain.claim or a point claim (F2, F10). Only PREV-owned claims qualify.
    try:removed,kept=recover_claims.recover(cdir,owner_job=prev,apply=True,state_fn=lambda j:state,log=log)
    except recover_claims.RecoveryBusy as exc:log(f'continuation: {exc}');return 75
    left=[c for c,_ in kept if str((recover_claims.owner_of(c) or {}).get('slurm_job_id'))==str(prev)]
    if left:log(f'continuation: claims of {prev} could not be removed: {left}');return 75
    sfile=cdir/'state'/f'{prev}.json'
    st=read_state(sfile)
    if st is None:log(f'continuation: state {sfile} is malformed; manual check');return 75     # F26
    status=st['status']
    log(f'continuation: predecessor {prev} ended {state}; its chain state is {status}')
    if status=='complete':
        if chain_complete(spec,chain,st.get('failed_checks')):log('continuation: chain complete; records validate');return 10
        log('continuation: state says complete but records do not; resuming');return 0
    if status=='failed':log('continuation: predecessor recorded a failure; not resuming (human needed)');return 11
    return 0


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec',required=True);ap.add_argument('--chain',required=True);ap.add_argument('--prev',required=True)
    a=ap.parse_args(argv)
    spec=load_spec(a.spec,os.environ.get('HT2D_SPEC_SHA256'))
    try:verify_runtime(spec)
    except (SpecError,EnvUnavailable) as exc:print(f'continuation: runtime verification failed: {exc}');return 75
    return guard(spec,a.chain,a.prev,os.environ.get('SLURM_JOB_ID',''),os.environ.get('SLURM_JOB_NAME',''))


if __name__=='__main__':raise SystemExit(main())
