"""Run one frozen continuation chain: L ladder, main step then nested checks per L.

Usage: python -E -s cluster/expanse/chain.py --spec SPEC --chain NAME

Exit codes: 0 complete; 65 seed/predecessor refused; 66 main step failed;
73 chain (or a point) owned by another writer; 74 release/spec/env check;
75 safe stop (resumable). The point driver is unchanged; every step is the
ordinary one-writer `code/hpc_run.py ... --resume` with frozen input hashes.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,signal,socket,subprocess,sys,time,uuid
from pathlib import Path
from common import (RELEASE,EXIT_SEED,EXIT_MAIN,EXIT_STAGE,EXIT_CLAIMED,EXIT_STOP,SpecError,
                    EnvUnavailable,atomic_json,check_initial_seed,check_predecessor,chain_dir,frozen_inputs,full_argv,
                    load_spec,source_hash,steps,verify_runtime)

STOP={'requested':False,'child':None}


def on_signal(sig,frame):
    STOP['requested']=True
    child=STOP['child']
    if child is not None and child.poll() is None:
        try:child.send_signal(signal.SIGUSR1)
        except ProcessLookupError:pass


def job_id():return os.environ.get('SLURM_JOB_ID') or f'local-{os.getpid()}'


class ChainClaim:
    """Exclusive chain ownership: atomic mkdir; removed only by its owner (or recover_claims)."""
    def __init__(self,directory):
        self.lock=Path(directory)/'chain.claim';self.token=uuid.uuid4().hex;self.held=False
    def __enter__(self):
        self.lock.parent.mkdir(parents=True,exist_ok=True)
        self.lock.mkdir()  # FileExistsError -> caller exits 73 without writing state
        self.held=True
        atomic_json(self.lock/'owner.json',{'token':self.token,'slurm_job_id':os.environ.get('SLURM_JOB_ID'),
            'host':socket.gethostname(),'pid':os.getpid(),'created_unix':time.time(),'kind':'chain'})
        return self
    def __exit__(self,*exc):
        try:
            owner=json.loads((self.lock/'owner.json').read_text())
            if isinstance(owner,dict) and owner.get('token')==self.token:
                (self.lock/'owner.json').unlink();self.lock.rmdir()
        except (OSError,ValueError):pass        # anything unexpected stays fail-closed for recovery
        return False


def write_state(cdir,status,**extra):
    atomic_json(Path(cdir)/'state'/f'{job_id()}.json',{'status':status,'job_id':job_id(),'unix':time.time(),**extra})


def archive_checkpoint(cdir,output):
    cp=Path(output+'.checkpoint.json')
    if cp.exists():
        hist=Path(cdir)/'history';hist.mkdir(parents=True,exist_ok=True)
        n=len(list(hist.glob(Path(output).stem+'.*.checkpoint.json')))
        shutil.copy2(cp,hist/f'{Path(output).stem}.{job_id()}.{n}.checkpoint.json')


def seed_for(spec,chain,step,cache=None):
    """(path, sha256 of the validated bytes) or (None, None). Predecessors are validated with their
    whole seed lineage against the frozen requests (F15); `cache` memoizes this within one run."""
    kind=step['seed']['kind']
    if kind=='none':return None,None
    if kind=='initial':return check_initial_seed(spec,chain)
    return check_predecessor(spec,step['seed'],cache=cache)


def run_step(spec,chain,step,python,cache=None):
    """Returns the child's exit code. Seeds are validated BEFORE the child is launched."""
    cdir=chain_dir(spec,chain)
    seed,seed_sha=seed_for(spec,chain,step,cache)      # raises on refusal (exit 65 for any step)
    argv=full_argv(spec,chain,step)+['--resume']
    # The child verifies that the seed bytes it reads hash to the VALIDATED value (F13).
    inputs=frozen_inputs(spec,chain,step,seed_sha)
    archive_checkpoint(cdir,step['output'])
    env={**os.environ,'HT2D_FROZEN_SOURCE':spec['release']['source_sha256'],
         'HT2D_FROZEN_INPUTS':json.dumps(inputs,sort_keys=True)}
    log=cdir/'logs'/f"{Path(step['output']).stem}.{job_id()}.log";log.parent.mkdir(parents=True,exist_ok=True)
    print(json.dumps({'event':'launch','chain':chain,'L':step['L'],'nz':step['nz'],'role':step['role'],
                      'seed':str(seed) if seed else None,'log':str(log),'time':time.strftime('%F %T')}),flush=True)
    with open(log,'ab') as fh:
        child=subprocess.Popen([python,'-E','-s',str(RELEASE/'code/hpc_run.py'),*argv],env=env,stdout=fh,stderr=subprocess.STDOUT)
        STOP['child']=child
        if STOP['requested']:on_signal(signal.SIGUSR1,None)
        rc=child.wait();STOP['child']=None
    print(json.dumps({'event':'exit','chain':chain,'L':step['L'],'nz':step['nz'],'rc':rc,'time':time.strftime('%F %T')}),flush=True)
    return rc


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',required=True);ap.add_argument('--chain',required=True)
    ap.add_argument('--spec-sha256',default=os.environ.get('HT2D_SPEC_SHA256'))
    a=ap.parse_args(argv)
    for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):signal.signal(sig,on_signal)
    try:
        spec=load_spec(a.spec,a.spec_sha256)
        if a.chain not in spec['chains']:raise SpecError(f'Unknown chain {a.chain}')
        if source_hash()!=spec['release']['source_sha256']:raise SpecError('Staged source differs from the frozen release')
        python=verify_runtime(spec)     # receipt + frozen env + release, BEFORE any claim (IR-03)
    except (SpecError,EnvUnavailable,OSError,ValueError) as exc:
        print(f'chain: verification failed: {exc}',file=sys.stderr);return EXIT_STAGE
    cdir=chain_dir(spec,a.chain)
    try:
        claim=ChainClaim(cdir).__enter__()
    except FileExistsError:
        print(f'chain: {cdir}/chain.claim exists; another job owns this chain (no state written)',file=sys.stderr)
        return EXIT_CLAIMED
    try:
        failed_checks=[];last=None;cache={}
        for step in steps(spec,a.chain):
            if STOP['requested']:
                write_state(cdir,'stopped',last_step=last,failed_checks=failed_checks);return EXIT_STOP
            try:rc=run_step(spec,a.chain,step,python,cache)
            except (SpecError,ValueError,KeyError,OSError) as exc:
                # Seed/integrity refusal is never a "failed check" (F19): stop the chain.
                print(f'chain: seed refused for L={step["L"]} nz={step["nz"]}: {exc}',file=sys.stderr)
                write_state(cdir,'failed',last_step=last,error=str(exc),exit=EXIT_SEED,failed_checks=failed_checks);return EXIT_SEED
            last={'L':step['L'],'nz':step['nz'],'rc':rc}
            if rc==EXIT_SEED:
                # The child refused changed/corrupt inputs, checkpoint or output: integrity, not numerics (F19).
                write_state(cdir,'failed',last_step=last,error='integrity refusal in the point driver',exit=EXIT_SEED,
                            failed_checks=failed_checks);return EXIT_SEED
            if rc==EXIT_STOP or (rc!=0 and STOP['requested']):
                write_state(cdir,'stopped',last_step=last,failed_checks=failed_checks);return EXIT_STOP
            if rc==EXIT_CLAIMED:
                write_state(cdir,'failed',last_step=last,error='point claim held (stale?)',exit=EXIT_CLAIMED,failed_checks=failed_checks)
                return EXIT_CLAIMED
            if rc!=0:
                if step['role']=='check':failed_checks.append({'L':step['L'],'nz':step['nz'],'rc':rc});continue
                write_state(cdir,'failed',last_step=last,exit=EXIT_MAIN,failed_checks=failed_checks);return EXIT_MAIN
        write_state(cdir,'complete',last_step=last,failed_checks=failed_checks)
        return 0
    finally:
        claim.__exit__(None,None,None)


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    raise SystemExit(main())
