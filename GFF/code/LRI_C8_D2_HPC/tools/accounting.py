#!/usr/bin/env python3
"""Allocated CPU time of a campaign from its ledger and Slurm accounting (PLAN component D, R10; A-ORC-9).

  accounting.py RUN [--json] [--output FILE] [--schema-prefix PREFIX]

* Schemas (checkpoint review O11): --schema-prefix (default c8-d2) is the campaign's schema prefix, the same as
  tools/design.py's --schema-prefix. The campaign must be a <prefix>-production-1 campaign and every ledger record a
  <prefix>-ledger-1 record (tools/ledger.py); its group configs and merged tables are read as <prefix>-group-1 and
  <prefix>-merged-1, and the result is a <prefix>-accounting-1 record. A campaign or ledger of another prefix is
  refused (exit 2), so a C8(3) pilot (c8-d3) is accounted from its own c8-d3-ledger-1 ledger.

* Every attempt counts: allocated core-seconds = sum of ElapsedRaw x physical cores over every
  `sacct -X --duplicates` record of every job id in the ledger ($C8_RUN/submissions.jsonl), requeued attempts and
  resubmissions included. Physical cores = AllocCPUS / ThreadsPerCore of the job's node (`scontrol show node`: 2 on
  symmetry's Intel nodes, 1 on AMD and Expanse).
* The ledger is checked for completeness: every checkpoint records the Slurm ids of the job that wrote it (its
  fingerprint's slurm field). A checkpoint naming a job id that is not in the ledger stops this tool with
  "allocation unknown" (exit 3), so a missing registration cannot understate the cost. A checkpoint without a Slurm
  id (a run outside Slurm) is reported as unaccounted local work; design.py freeze accepts that only for a
  --test-only bundle.
* eta_node (for design.py) = busy thread-seconds of the native blocks (sum over checkpoints of threads x
  integration_seconds; from the validated merged.json of each merged group) / allocated core-seconds of the work roles
  (lane, array, sweep). Plan and merge jobs are reported separately as overhead. A group that is not merged yet counts
  only the checkpoints production.validate_checkpoint accepts (W10's class, Stage-6 fix round 4); an invalid one makes
  the accounting incomplete.
* Fail closed (O06): the accounting is complete only when every sacct line parses (7 fields, integer ElapsedRaw and
  AllocCPUS) and the records cover the ledger: every job has a record; every element of a ledger array (its `array`
  spec) has one (a pending or never-started range `<id>_[a-b]` covers its elements with zero time); and every job and
  array element has at least as many records (attempts, `sacct --duplicates`) as the evidence shows: one more than the
  largest SLURM_RESTART_COUNT recorded by the ledger (requeue attempt notes) or by its checkpoints' fingerprints.
  Incomplete accounting is reported with its reasons and eta_node = null ("unavailable"), the allocated hours as
  lower bounds, and this tool exits 4; design.py refuses to freeze or report on it.
* Live allocations are incomplete too (X15, Stage-6 fix round 1): the current (last) sacct record of every job and
  array element must be in a terminal state (TERMINAL_STATES: COMPLETED, FAILED, CANCELLED, TIMEOUT, OUT_OF_MEMORY,
  NODE_FAIL, PREEMPTED, BOOT_FAIL, DEADLINE, REVOKED; "CANCELLED by <uid>" counts as CANCELLED). A RUNNING, PENDING,
  SUSPENDED, COMPLETING, REQUEUED or held current attempt, or a state this tool does not know, may still consume
  allocation: the hours are lower bounds and eta_node is unavailable. Earlier attempts (sacct --duplicates) stay in the
  sum; each must be terminal or a requeue state (REQUEUED, REQUEUE_FED, REQUEUE_HOLD) superseded by a later record. A
  pending array range record `<id>_[a-b]` counts for its elements by its own state: PENDING is live (incomplete), a
  terminal one (e.g. cancelled before start) covers the elements with zero time.
* Removed evidence is incomplete too (Y9, Stage-6 fix round 2): a merge needs every checkpoint of its group, so a
  checkpoint missing from a MERGED group (its merged.json present) was removed afterwards, and the Slurm ids and restart
  counts of the work it records can no longer be checked against the ledger (missing_checkpoints; reported as
  missing_checkpoints). A group that is not merged yet is work in progress: its missing checkpoints are work not done.
  design.py refuses a production design from such a pilot even without any Slurm id (no assumed efficiency).
Exit codes: 0 complete, 2 the campaign or its ledger is not of --schema-prefix, 3 allocation unknown, 4 incomplete accounting.
"""
from __future__ import annotations
import argparse,json,os,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ledger
from common import dump,load,slurm_ids,utc
OWN_PREFIX=ledger.OWN_PREFIX
SCHEMA=f'{OWN_PREFIX}-accounting-1'  # this package's own campaigns; another prefix's record is <prefix>-accounting-1
def schema(prefix:str=OWN_PREFIX)->str:return f'{ledger.check_prefix(prefix)}-accounting-1'

class AllocationUnknown(Exception):pass

def first_node(nodelist:str)->str|None:
    """The first host of a Slurm NodeList (cn083, cn[083-085,090], exp-2-[01-02]) or None."""
    s=nodelist.strip()
    if not s or s in('None assigned','(null)'):return None
    m=re.match(r'([^\[,]+)(?:\[([^\]]+)\])?',s)
    if not m:return None
    head,inner=m.groups()
    if not inner:return head
    first=inner.split(',')[0].split('-')[0];return head+first

def threads_per_core(node:str,cache:dict,env)->int:
    if node not in cache:
        try:
            cp=subprocess.run(['scontrol','show','node',node],capture_output=True,text=True,timeout=60,env=env)
            m=re.search(r'ThreadsPerCore=(\d+)',cp.stdout);cache[node]=int(m.group(1))if cp.returncode==0 and m else None
        except (OSError,subprocess.SubprocessError):cache[node]=None
    return cache[node]

SACCT_FIELDS='JobIDRaw,JobID,ElapsedRaw,AllocCPUS,NodeList,State,Partition'

def parse_sacct(text:str)->tuple[list[dict],list[str]]:
    """(records, malformed lines) of `sacct -X -n -P -o SACCT_FIELDS` output. A line that is not exactly 7 fields with an
    integer ElapsedRaw and AllocCPUS is malformed: it is reported, never skipped silently (O06)."""
    out=[];bad=[]
    for line in text.splitlines():
        if not line.strip():continue
        f=line.split('|')
        if len(f)!=7 or not f[2].isdigit()or not f[3].isdigit():bad.append(line[:200]);continue
        raw,jid,el,cpus,nodes,state,part=f
        out.append({'jobid_raw':raw,'jobid':jid,'elapsed':int(el),'alloc_cpus':int(cpus),'nodelist':nodes,'state':state,'partition':part})
    return out,bad

def sacct(ids:list[str],env)->tuple[list[dict],list[str]]:
    if not ids:return [],[]
    cp=subprocess.run(['sacct','-X','--duplicates','-n','-P','-j',','.join(ids),'-o',SACCT_FIELDS],capture_output=True,text=True,timeout=600,env=env)
    if cp.returncode:raise RuntimeError(f'sacct failed: {(cp.stderr or cp.stdout).strip()[-300:]}')
    return parse_sacct(cp.stdout)

def _int_or(x,default=0)->int:
    try:return int(x)
    except (TypeError,ValueError):return default

def checkpoint_slurm(run:Path,m:dict)->tuple[set,int,int,dict]:
    """(Slurm job ids named by the campaign's checkpoints, checkpoints with a Slurm id, checkpoints without one, and the
    attempt evidence {(job id, array task id or None): 1 + the largest SLURM_RESTART_COUNT seen})."""
    import production as prod
    ids=set();with_id=0;local=0;need={}
    for j in m['jobs']:
        d=run/'groups'/j['group']/'checkpoints'
        for k in range(j['blocks']):
            f=d/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():continue
            fp=(prod.checkpoint_runtime(f)or{}).get('fingerprint');got=slurm_ids(fp)
            if not got:local+=1;continue
            ids.update(got);with_id+=1;s=(fp or{}).get('slurm')or{}
            key=(str(s['SLURM_ARRAY_JOB_ID']),_int_or(s.get('SLURM_ARRAY_TASK_ID'),None))if s.get('SLURM_ARRAY_JOB_ID')else(str(s.get('SLURM_JOB_ID')),None)
            need[key]=max(need.get(key,0),_int_or(s.get('SLURM_RESTART_COUNT'))+1)
    return ids,with_id,local,need

def missing_checkpoints(run:Path,m:dict)->list[str]:
    """Y9: the checkpoints (paths relative to RUN) of MERGED groups (groups/<group>/merged.json present) that do not
    exist. A merge reads every checkpoint of its group, so each was removed after the merge: the accounting evidence it
    carried (the Slurm ids and restart count of the job that wrote it) is gone. Checkpoints of unmerged groups are
    work in progress and never listed."""
    import production as prod
    out=[]
    for j in m['jobs']:
        p=run/'groups'/j['group']
        if not (p/'merged.json').exists():continue
        for k in range(j['blocks']):
            f=p/'checkpoints'/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():out.append(str(f.relative_to(run)))
    return out

def checkpoint_ids(run:Path,m:dict)->tuple[set,int,int]:
    """(Slurm job ids named by the campaign's checkpoints, checkpoints with a Slurm id, checkpoints without one)."""
    return checkpoint_slurm(run,m)[:3]

def array_elements(spec)->list[int]|None:
    """The element indices of an array spec ('0-3,7', a '%N' throttle ignored), None when there is none or it does not
    parse."""
    if not isinstance(spec,str)or not spec:return None
    out=[]
    for part in spec.split('%')[0].split(','):
        lo,_,hi=part.partition('-')
        if not lo.isdigit()or(hi and not hi.isdigit()):return None
        out.extend(range(int(lo),int(hi or lo)+1))
    return out

TERMINAL_STATES=frozenset(('COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'))
REQUEUE_STATES=frozenset(('REQUEUED','REQUEUE_FED','REQUEUE_HOLD'))  # an earlier attempt superseded by a later record

def state_of(text:str)->str:
    """The sacct state word: 'CANCELLED by 123' -> 'CANCELLED', a truncation '+' dropped, upper case."""
    w=(text or'').split();return w[0].rstrip('+').upper()if w else''

def live_states(states:dict)->list[str]:
    """X15: why the attempts {(job, element or None): [state, ...] in sacct order} are not all over: the current (last)
    attempt not terminal, or an earlier one neither terminal nor a requeue state."""
    out=[]
    for (jid,e),sts in sorted(states.items(),key=lambda t:(len(t[0][0]),t[0][0],-1 if t[0][1]is None else t[0][1])):
        what=f'job {jid}'if e is None else f'array job {jid} element {e}'
        if sts[-1]not in TERMINAL_STATES:out.append(f'{what}: its current attempt is {sts[-1] or "(no state)"}, not terminal (a live or pending allocation: hours are lower bounds)')
        early=[s for s in sts[:-1]if s not in TERMINAL_STATES|REQUEUE_STATES]
        if early:out.append(f'{what}: an earlier attempt is {early[0]}, neither terminal nor requeued')
    return out

def coverage(run:Path,known:dict,recs:list,need:dict,prefix:str=OWN_PREFIX)->list[str]:
    """Why the sacct records do not cover the ledger (empty when they do): a job without a record, an array element
    without one, fewer records than recorded attempts (O06), an attempt that is not over (X15: live_states)."""
    import ledger as L
    count={};states={}
    for r in recs:
        base,_,task=r['jobid'].split('.')[0].partition('_');st=state_of(r.get('state',''))
        if not task:count[(base,None)]=count.get((base,None),0)+1;states.setdefault((base,None),[]).append(st)
        elif task.startswith('['):  # a pending or never-started range of array elements: covered, with zero time, by its own state
            for t in (array_elements(task.strip('[]'))or[]):count[(base,t)]=count.get((base,t),0)+1;states.setdefault((base,t),[]).append(st)
        elif task.isdigit():count[(base,int(task))]=count.get((base,int(task)),0)+1;states.setdefault((base,int(task)),[]).append(st)
    attempts={}
    for r in L.read(run,prefix):  # ledger attempt evidence: every recorded restart count of a job
        if r.get('type')in('note',):continue
        jid=str(r.get('jobid'));attempts[(jid,None)]=max(attempts.get((jid,None),0),_int_or(r.get('restart_count'))+1)
    out=[]
    for jid,rec in sorted(known.items(),key=lambda t:(len(t[0]),t[0])):
        if rec.get('role')=='array':
            els=array_elements(rec.get('array'))
            if els is None:els=sorted({t for (b,t)in count if b==jid and t is not None})or[None]
            for e in els:
                if e is None:out.append(f'array job {jid}: no sacct record of any element');continue
                want=max(1,need.get((jid,e),0))
                if count.get((jid,e),0)<want:out.append(f'array job {jid} element {e}: {count.get((jid,e),0)} sacct record(s), {want} attempt(s) recorded')
        else:
            want=max(1,need.get((jid,None),0),attempts.get((jid,None),0))
            if count.get((jid,None),0)<want:out.append(f'job {jid}: {count.get((jid,None),0)} sacct record(s), {want} attempt(s) recorded')
    for (jid,e),want in sorted(need.items(),key=lambda t:(t[0][0],t[0][1]if t[0][1]is not None else -1)):
        if jid in known and known[jid].get('role')=='array'and e is not None and array_elements(known[jid].get('array'))is not None and e not in array_elements(known[jid]['array']):
            out.append(f'array job {jid}: checkpoints name element {e}, which its ledger record does not list')
    return out+live_states(states)

def schemas_of(prefix:str=OWN_PREFIX)->tuple[str,str]:
    """(group config schema, merged schema) of a <prefix>-production-1 campaign (H6: another package's; O11)."""
    ledger.check_prefix(prefix);return f'{prefix}-group-1',f'{prefix}-merged-1'

def busy_thread_seconds(run:Path,m:dict,prefix:str=OWN_PREFIX)->tuple[float,str,list[str]]:
    """(busy thread-seconds, their source, why some could not be counted). A merged group: its validated merged.json.
    A group that is not merged yet (W10's class, Stage-6 fix round 4, integration; before, its checkpoints' native
    integration_seconds were summed unread): each existing checkpoint counts only after production.validate_checkpoint
    accepted it against its authenticated task block, exactly as the merges and calibrate.measure validate it (identity,
    the campaign's runtime key, a gated campaign's libgmp, payload digest, native metadata, rows); one that fails is not
    counted and makes the accounting incomplete (eta_node unavailable), as does an unmerged group of a campaign of
    another schema prefix, whose checkpoints only that package's merge validates."""
    import production as prod
    mh=prod.digest(run/'manifest.json');tot=0.;src='merged.json thread_seconds_sum';gs,ms=schemas_of(prefix);why=[];ctx=None
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name'],gs)
        if (p/'merged.json').exists():tot+=float(prod.validate_merged(p,cfg,m,mh,ms)['thread_seconds_sum']);continue
        src='checkpoints (some groups not merged)'
        if prefix!=OWN_PREFIX:
            why.append(f'group {g["name"]} is not merged: the checkpoints of a {prefix} campaign are validated only by its own package\'s merge, so their '
                       'busy time is not counted (W10)');continue
        if ctx is None:
            try:ctx=(prod.rate_map_for(run,m),prod.campaign_runtime_key(run,m)[0],prod.gate_gmp_binding(m))
            except (ValueError,KeyError,TypeError,OSError)as e:why.append(f'the checkpoints cannot be validated ({type(e).__name__}: {e}); their busy time is not counted (W10)'[:400]);break
        for j in (j for j in m['jobs']if j['group']==g['name']):
            for k,block in enumerate(prod.iter_job_blocks(run,j,m['checkpoint_tasks'])):
                f=p/'checkpoints'/f'{prod.block_name(j["shard"],k)}.json'
                if not f.exists():continue
                try:n=prod.validate_checkpoint(load(f),block,cfg,m,mh,*ctx)
                except (ValueError,KeyError,TypeError,ArithmeticError)as e:
                    why.append(f'{f.relative_to(run)}: not a valid checkpoint of this campaign ({type(e).__name__}: {e}); its busy time is not counted (W10)'[:400]);continue
                tot+=float(n['integration_seconds'])*int(n['threads'])
    return tot,src,why

def account(run:Path,env=None,prefix:str=OWN_PREFIX)->dict:
    """The accounting of the <prefix>-production-1 campaign at RUN from its <prefix>-ledger-1 ledger (O11: a campaign or
    a ledger record of another prefix raises ledger.SchemaMismatch, a ValueError)."""
    env=dict(os.environ if env is None else env);env={k:v for k,v in env.items()if not k.startswith('SQUEUE_')}
    run=Path(run).resolve();m=ledger.check_campaign(run,prefix);known=ledger.jobs(run,prefix)
    ids,with_id,local,need=checkpoint_slurm(run,m)
    unknown=sorted(ids-set(known),key=lambda x:(len(x),x))
    if unknown:raise AllocationUnknown(f'allocation unknown: checkpoints name Slurm job(s) {", ".join(unknown[:10])} that are not in {ledger.path(run)}; '
                                       'register the allocation (tools/ledger.py register RUN --role ROLE --job ID) before designing from this campaign')
    recs,malformed=sacct(sorted(known,key=lambda x:(len(x),x)),env);cache={};per={};rows=[]
    for r in recs:
        base=r['jobid'].split('_')[0].split('.')[0];role=known.get(base,known.get(r['jobid_raw'],{})).get('role','unknown')
        node=first_node(r['nodelist']);tpc=threads_per_core(node,cache,env)if node else None
        if r['elapsed']>0 and not tpc:raise RuntimeError(f'cannot read ThreadsPerCore of node {node} (job {r["jobid"]}); physical cores unknown')
        cores=r['alloc_cpus']/(tpc or 1);cs=r['elapsed']*cores
        rows.append({**r,'role':role,'threads_per_core':tpc,'physical_cores':cores,'core_seconds':cs});per[role]=per.get(role,0.)+cs
    work=sum(v for k,v in per.items()if k in ledger.WORK_ROLES);over=sum(v for k,v in per.items()if k not in ledger.WORK_ROLES)
    busy,bsrc,busy_why=busy_thread_seconds(run,m,prefix)
    missing=sorted(set(known)-{r['jobid'].split('_')[0].split('.')[0]for r in recs},key=lambda x:(len(x),x))
    incomplete=[f'{len(malformed)} sacct line(s) do not parse (first: {malformed[0]!r})']if malformed else[]
    incomplete+=coverage(run,known,recs,need,prefix)
    incomplete+=busy_why  # W10's class: busy time only from validated checkpoints
    gone=missing_checkpoints(run,m)  # Y9: evidence removed after the merge
    if gone:incomplete.append(f'{len(gone)} checkpoint(s) of merged groups are missing (first: {gone[0]}): the Slurm ids of the work they record '
                              'can no longer be checked against the ledger (removed evidence; restore them)')
    complete=not incomplete
    return {'schema':schema(prefix),'schema_prefix':prefix,'ledger_schema':ledger.schema(prefix),'campaign':str(run),'manifest_sha256':__import__('common').digest(run/'manifest.json'),'derived_utc':utc(),'ledger_jobs':len(known),
            'sacct_records':len(rows),'jobs_without_sacct_record':missing,'records':rows,'complete':complete,'incomplete':incomplete,'malformed_sacct_lines':malformed[:20],
            'core_hours_by_role':{k:v/3600 for k,v in sorted(per.items())},'hours_are':'exact'if complete else'lower bounds (incomplete accounting)',
            'allocated_core_hours':(work+over)/3600,'work_core_hours':work/3600,'overhead_core_hours':over/3600,'busy_thread_core_hours':busy/3600,'busy_source':bsrc,
            'eta_node':busy/work if work>0 and complete else None,
            'eta_node_unavailable':None if complete else 'incomplete accounting: '+'; '.join(incomplete[:5]),
            'checkpoints_with_slurm_id':with_id,'unaccounted_local_checkpoints':local,'missing_checkpoints':len(gone),
            'rule':'every sacct -X --duplicates attempt of every ledger job, physical cores = AllocCPUS/ThreadsPerCore; eta_node over the work roles lane, array, '
                   'sweep, only when every sacct line parses, the records cover every ledger job, array element and recorded attempt, every current '
                   'attempt is in a terminal state (X15), and no checkpoint of a merged group is missing (Y9)'}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path)
    p.add_argument('--json',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--schema-prefix',default=OWN_PREFIX,help='the campaign\'s schema prefix (c8-d2; c8-d3 for a C8(3) campaign)');a=p.parse_args(argv)
    try:r=account(a.run,prefix=a.schema_prefix)
    except AllocationUnknown as e:print(f'C8: {e}',file=sys.stderr);return 3
    except ledger.SchemaMismatch as e:print(f'C8: {e}',file=sys.stderr);return 2
    if a.output:dump(a.output,r)
    if a.json:print(json.dumps(r,indent=1))
    else:print(json.dumps({k:v for k,v in r.items()if k!='records'},indent=1))
    if not r['complete']:print(f'C8: {r["eta_node_unavailable"]}; eta_node unavailable',file=sys.stderr);return 4
    return 0
if __name__=='__main__':sys.exit(main())
