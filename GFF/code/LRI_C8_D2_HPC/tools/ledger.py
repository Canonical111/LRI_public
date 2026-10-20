#!/usr/bin/env python3
"""The allocation ledger of a campaign, $C8_RUN/submissions.jsonl (schema <prefix>-ledger-1, c8-d2-ledger-1 for this
package's campaigns; PLAN component D, R10).

tools/slurm_submit.py appends every job it submits. An allocation that does campaign work WITHOUT slurm_submit
registers itself, so that tools/accounting.py sees every allocation:
  ledger.py register RUN --role ROLE [--job ID] [--restart N] [--note TEXT]
        ROLE: sweep (tools/sweep.py, right after its plan is published and before any index runs) or plan
        (slurm/plan.sh and every other job that publishes a campaign with production.py plan; plan jobs are overhead,
        not work). The job id and restart count default to SLURM_JOB_ID and SLURM_RESTART_COUNT. Idempotent under the
        campaign lock: a job id already in the ledger is not added again; a requeued job (a new restart count) adds
        an attempt note, which tools/accounting.py does not count as a job (sacct --duplicates gives its attempts).
  ledger.py list RUN
Both take --schema-prefix PREFIX (default c8-d2; checkpoint review O11): the schema prefix of the campaign, as for
tools/design.py and tools/accounting.py. The campaign's manifest must be a <prefix>-production-1 manifest, and every
ledger record is written and read as <prefix>-ledger-1: a record of another prefix (another package's ledger, or a
ledger read with the wrong prefix) is refused, never skipped, so the prefix used for a campaign must match its ledger.
"""
from __future__ import annotations
import argparse,json,os,re,socket,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import CampaignLock,Refuse,utc
OWN_PREFIX='c8-d2'
SCHEMA=f'{OWN_PREFIX}-ledger-1'  # this package's own campaigns (tools/slurm_submit.py writes the same schema)
ROLES=('sweep','plan','lane','array','merge')
WORK_ROLES=frozenset({'lane','array','sweep'})

class SchemaMismatch(ValueError):
    """The campaign or a ledger record is not of the schema prefix asked for (O11)."""

def check_prefix(prefix)->str:
    """A schema prefix c8-d<D> (the --schema-prefix of tools/design.py; O11)."""
    if not isinstance(prefix,str)or not re.fullmatch(r'c8-d[1-9]',prefix):raise SchemaMismatch(f'schema prefix {prefix!r} is not c8-d<dimension>')
    return prefix

def schema(prefix:str=OWN_PREFIX)->str:return f'{check_prefix(prefix)}-ledger-1'

def check_campaign(run:Path,prefix:str=OWN_PREFIX)->dict:
    """The manifest of the campaign at RUN, which must be a <prefix>-production-1 manifest (O11): the prefix used for a
    campaign is the prefix of its ledger and of its accounting."""
    f=Path(run)/'manifest.json';want=f'{check_prefix(prefix)}-production-1'
    try:m=json.loads(f.read_bytes())
    except (OSError,ValueError)as e:raise ValueError(f'{run} is not a planned campaign ({f}: {e})')
    if not isinstance(m,dict)or m.get('schema')!=want:
        raise SchemaMismatch(f'{run} is a {m.get("schema")if isinstance(m,dict)else None} campaign, not a {want} campaign: the schema prefix '
                         f'{prefix} is not the campaign\'s (--schema-prefix names the campaign\'s own prefix; its ledger is <prefix>-ledger-1)')
    return m

def path(run:Path)->Path:return Path(run)/'submissions.jsonl'

def read(run:Path,prefix:str=OWN_PREFIX)->list[dict]:
    """Every record of the ledger; each must be a <prefix>-ledger-1 record (O11), else SchemaMismatch."""
    p=path(run);want=schema(prefix)
    if not p.exists():return []
    out=[]
    for n,line in enumerate(p.read_text().splitlines(),1):
        if not line.strip():continue
        try:r=json.loads(line)
        except ValueError as e:raise ValueError(f'{p} line {n} is not JSON: {e}')
        if not isinstance(r,dict)or r.get('schema')!=want:
            raise SchemaMismatch(f'{p} line {n} is not a {want} record (schema {r.get("schema")if isinstance(r,dict)else None!r}): the ledger of a '
                             f'{prefix} campaign holds {want} records only (--schema-prefix must match the campaign and its ledger)')
        out.append(r)
    return out

def jobs(run:Path,prefix:str=OWN_PREFIX)->dict[str,dict]:
    """{job id: its first job record} (notes and attempt notes excluded)."""
    out={}
    for r in read(run,prefix):
        if r.get('type')in('note','attempt'):continue
        out.setdefault(str(r['jobid']),r)
    return out

def register(run:Path,role:str,job:str|None,restart:str|None,note:str|None=None,env=None,prefix:str=OWN_PREFIX)->str:
    env=os.environ if env is None else env;run=Path(run).resolve()
    if role not in ROLES:raise Refuse(64,f'--role must be one of {", ".join(ROLES)}')
    job=job or env.get('SLURM_JOB_ID');restart=str(restart if restart is not None else env.get('SLURM_RESTART_COUNT','0'))
    if not job or not str(job).isdigit():raise Refuse(64,'no job id: run inside a Slurm job (SLURM_JOB_ID) or pass --job')
    if not (run/'manifest.json').is_file():raise Refuse(64,f'{run} is not a planned campaign (no manifest.json)')
    try:check_campaign(run,prefix)
    except ValueError as e:raise Refuse(64,str(e))
    with CampaignLock(run,f'ledger register {role} {job}',wait=120):
        try:known=read(run,prefix)
        except ValueError as e:raise Refuse(64,str(e))
        mine=[r for r in known if str(r.get('jobid'))==str(job)]
        rec={'schema':schema(prefix),'jobid':str(job),'role':role,'time':utc(),'source':'self_register','host':socket.gethostname(),'restart_count':restart,
             'partition':env.get('SLURM_JOB_PARTITION'),'cpus_on_node':env.get('SLURM_CPUS_ON_NODE'),'account':env.get('SLURM_JOB_ACCOUNT'),**({'note':note}if note else{})}
        if not mine:state='added'
        elif any(str(r.get('restart_count','0'))==restart for r in mine):return 'present'
        else:rec={**rec,'type':'attempt'};state='attempt'
        with path(run).open('a')as f:f.write(json.dumps(rec,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    return state

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('register');q.add_argument('run',type=Path);q.add_argument('--role',required=True);q.add_argument('--job');q.add_argument('--restart');q.add_argument('--note')
    q.add_argument('--schema-prefix',default=OWN_PREFIX)
    q=s.add_parser('list');q.add_argument('run',type=Path);q.add_argument('--schema-prefix',default=OWN_PREFIX)
    a=p.parse_args(argv)
    try:
        if a.command=='register':print(json.dumps({'run':str(a.run),'state':register(a.run,a.role,a.job,a.restart,a.note,prefix=a.schema_prefix)}))
        else:check_campaign(a.run,a.schema_prefix);print(json.dumps(read(a.run,a.schema_prefix),indent=1))
        return 0
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code
    except ValueError as e:print('C8: '+str(e),file=sys.stderr);return 64
if __name__=='__main__':sys.exit(main())
