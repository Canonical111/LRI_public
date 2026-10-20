"""Submit frozen chains to Expanse `shared` (one non-array job per chain).

Usage: python submit.py --spec SPEC [--chains A B ...] [--dry-run]

Verifies the spec, the release tar/manifest, the receipt and the frozen environment;
prints a scheduler survey; refuses a chain whose job name is already pending/running;
defers seed_from chains until their predecessor validates; renders the job script from
the VERIFIED release tar; submits with every frozen resource given EXPLICITLY on the
command line and with SBATCH_* variables removed from the environment (IR-02); appends
to SUBMITTED.jsonl and prints the log paths to tail.
"""
from __future__ import annotations
import argparse,hashlib,io,json,os,subprocess,sys,tarfile,time
from pathlib import Path
from common import EnvUnavailable,SpecError,check_predecessor,load_spec,verify_runtime


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_body(spec):
    rel=spec['release']
    data=Path(rel['tar']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=rel['tar_sha256']:raise SpecError('Release tar changed')
    if sha(rel['manifest'])!=rel['manifest_sha256']:raise SpecError('Release manifest changed')
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        body=tf.extractfile('ht2d/cluster/expanse/chain.sbatch').read()
    want=None
    for line in Path(rel['manifest']).read_text().splitlines():
        h,_,p=line.partition('  ')
        if p.strip()=='ht2d/cluster/expanse/chain.sbatch':want=h
    if want!=hashlib.sha256(body).hexdigest():raise SpecError('chain.sbatch differs from the release manifest')
    return body.decode()


def job_name(spec,chain):return f"ht2d-{spec['campaign']}-{chain}"


def resource_options(spec,chain):
    """Frozen resources as explicit sbatch options (command line beats env and script directives)."""
    s=spec['chains'][chain]['slurm']
    return ['-A',s['account'],'-p',s['partition'],'--nodes=1','--ntasks-per-node=1',f"--cpus-per-task={int(s['cpus'])}",
            f"--mem={int(s['mem_gb'])}G",'-t',s['time'],f"--signal=B:USR1@{int(s['lead_s'])}",
            '-J',job_name(spec,chain),'-o',f"{spec['logs']}/%x_%j.out"]


def clean_env(env=None):
    """Drop every SBATCH_* input variable so nothing overrides the frozen options (IR-02)."""
    return {k:v for k,v in (env or os.environ).items() if not k.startswith('SBATCH_')}


def render(spec,chain,body):
    # The authoritative resource values are the explicit command-line options; this is a record.
    header=['#!/bin/bash',f'# frozen sbatch options: {" ".join(resource_options(spec,chain))}']
    lines=body.splitlines()
    if lines and lines[0].startswith('#!'):lines=lines[1:]
    return '\n'.join(header+lines)+'\n'


def sbatch_command(spec,chain,script,spec_path,spec_sha):
    s=spec['chains'][chain]['slurm']
    env=(f"ALL,HT2D_SPEC={spec_path},HT2D_SPEC_SHA256={spec_sha},HT2D_CHAIN={chain},HT2D_CONT=0,"
         f"HT2D_MAX_CONT={int(s['max_cont'])}")
    return ['sbatch','--parsable',*resource_options(spec,chain),'--export',env,str(script)]


def survey(run=subprocess.run):
    from collections import Counter
    p=run(['sinfo','-h','-p','shared','-o','%t %D'],capture_output=True,text=True,env=clean_env())
    print('shared nodes:',' '.join(l.strip() for l in p.stdout.splitlines() if l.strip()))
    p=run(['squeue','-A','<ACCOUNT>','-h','-o','%u %T'],capture_output=True,text=True,env=clean_env())
    print('<ACCOUNT> jobs:',dict(Counter(l.strip() for l in p.stdout.splitlines() if l.strip())))


def active(name,run=subprocess.run):
    p=run(['squeue','-h','-u',os.environ.get('USER',''),'-n',name,'-o','%i %T'],capture_output=True,text=True,env=clean_env())
    if p.returncode!=0:raise SpecError('squeue failed; refusing to submit blind')
    return [l for l in p.stdout.splitlines() if l.strip()]


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',required=True)
    ap.add_argument('--chains',nargs='*');ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args(argv)
    spec_path=Path(a.spec).resolve();spec_sha=sha(spec_path)
    try:
        spec=load_spec(spec_path,spec_sha);verify_runtime(spec);body=verified_body(spec)
    except (SpecError,EnvUnavailable) as exc:print(f'submit: verification failed: {exc}',file=sys.stderr);return 74
    chains=a.chains or list(spec['chains'])
    for c in chains:
        if c not in spec['chains']:raise SpecError(f'unknown chain {c}')
    survey()
    jobs=Path(spec['root'])/'jobs';jobs.mkdir(parents=True,exist_ok=True);Path(spec['logs']).mkdir(parents=True,exist_ok=True)
    deferred=[]
    for c in chains:
        ref=spec['chains'][c].get('seed_from')
        if ref:
            # A chain seeded from another chain's record waits until that record validates (F16).
            try:check_predecessor(spec,ref)
            except (SpecError,ValueError,KeyError,OSError) as exc:
                print(f'{c}: DEFERRED until {ref} validates ({exc}); resubmit later with --chains {c}');deferred.append(c);continue
        name=job_name(spec,c);busy=active(name)
        if busy:print(f'{c}: refusing, {name} already queued/running: {busy}');continue
        script=jobs/f'{c}.sbatch';script.write_text(render(spec,c,body))
        cmd=sbatch_command(spec,c,script,spec_path,spec_sha)
        if a.dry_run:print('DRY',' '.join(cmd));continue
        p=subprocess.run(cmd,capture_output=True,text=True,env=clean_env())
        if p.returncode!=0 or not p.stdout.strip():print(f'{c}: sbatch failed: {p.stderr.strip()}');continue
        jid=p.stdout.strip().split(';')[0]
        rec={'chain':c,'job':jid,'name':name,'spec_sha256':spec_sha,'unix':time.time(),
             'log':f"{spec['logs']}/{name}_{jid}.out",'chain_logs':f"{spec['root']}/chains/{c}/logs/"}
        with open(Path(spec['root'])/'SUBMITTED.jsonl','a') as fh:fh.write(json.dumps(rec)+'\n')
        print(f"{c}: job {jid}  tail -f {rec['log']}")
    if deferred:
        with open(Path(spec['root'])/'DEFERRED.jsonl','a') as fh:fh.write(json.dumps({'chains':deferred,'unix':time.time()})+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
