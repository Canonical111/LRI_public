#!/usr/bin/env python3
"""The single guarded path for every Slurm submission of a campaign (slurm/submit.sh, slurm/resubmit.sh, and the
resubmission lines printed by `production.py status`, which call `slurm/submit.sh --window`).

  slurm_submit.py submit [extra sbatch options]              incomplete work windows + an afterok merge
  slurm_submit.py window OFFSET:ARRAY [extra sbatch options] one work window (as printed by status)
  slurm_submit.py resubmit [extra sbatch options]            recovery (production.py recover) + a dependent merge

Environment: C8_RUN, C8_PACKAGE (the package this file belongs to), C8_SBATCH_ARGS (one line, shell-lexed),
C8_MAX_ARRAY (default 1000), C8_THROTTLE (default 64), C8_TIME_POLICY (finite | unlimited, default finite);
C8_ENV_SETUP/C8_PYTHON are passed on to the jobs.
Guarantees, independent of the caller's environment and arguments:
  * C8_SBATCH_ARGS and the extra options are each checked against the sbatch-option allowlist SEPARATELY, so neither
    can consume the other's tokens; C8_MAX_ARRAY and C8_THROTTLE must be positive integers;
  * inherited cluster selectors (SBATCH_CLUSTERS, SLURM_CLUSTERS, SQUEUE_CLUSTERS) are refused, so queries and
    submissions always address the same cluster; other SBATCH_* inputs outside a small allowlist are removed from
    sbatch's environment, and SQUEUE_* inputs from squeue's;
  * commands are argument lists (no shell splicing); campaign, package and window offset are set in sbatch's own
    environment (with --export=ALL an inherited value would otherwise win); merges carry no offset;
  * the queue snapshot is filtered by the account of the process's real uid (the identity sbatch submits under),
    never by USER/LOGNAME, so a stale or foreign USER cannot hide live jobs;
  * one submission at a time per campaign: submit, window and resubmit hold the lock directory $C8_RUN/.c8_submit.lock
    (atomic mkdir; flock is not relied on) from before the queue snapshot through the last sbatch, so a later call
    always sees an earlier call's jobs. A second call while the lock exists submits nothing (exit 75). A lock left by a
    killed process is never broken automatically: its owner.json names the holder; remove it by hand;
  * no duplicate live work from any entry point: every command first takes a complete squeue snapshot of the campaign
    tag. submit refuses (65) if any work or merge job of the campaign is live; window refuses (65) if any index of its
    window or a merge is live; resubmit refuses (65) while a merge is live and never resubmits a live index. Indices
    whose blocks are all committed are skipped; when none remain nothing is submitted (exit 0);
  * wall time: under C8_TIME_POLICY=finite work jobs get the plan's suggested time and merges 02:00:00 (MERGE_TIME),
    both overridden by a --time/-t in C8_SBATCH_ARGS or the extra options. Under unlimited every job gets --time=0 as
    its last option, any other --time is refused (64), and after each sbatch `scontrol show job` must report
    TimeLimit=UNLIMITED, else exit 70 (the job is left alone; job management stays with the user).
  * a pinned tool that differs from the plan refuses every submission (64): the work and merge jobs would refuse it.
Exit codes: 64 invalid input (nothing submitted), 65 live work or merge of the campaign, 69 unknown or uncertain state
or failed squeue, 70 a job was accepted without TimeLimit=UNLIMITED under the unlimited policy, 75 another submission
for the campaign holds the lock.
"""
from __future__ import annotations
import json,os,pwd,re,shlex,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import production as prod
from common import ROOT,load
CLUSTER_SELECTORS=('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS')
SBATCH_ENV_ALLOWED=frozenset('SBATCH_ACCOUNT SBATCH_PARTITION SBATCH_QOS SBATCH_RESERVATION SBATCH_CONSTRAINT SBATCH_MEM_PER_CPU SBATCH_MEM_PER_NODE SBATCH_WCKEY SBATCH_REQUEUE SBATCH_NO_REQUEUE'.split())
MERGE_TIME='02:00:00'
POLICIES=('finite','unlimited')

class Refuse(Exception):
    def __init__(self,code,msg):super().__init__(msg);self.code=code

LOCK_NAME='.c8_submit.lock'
class CampaignLock:
    """Campaign-scoped submission lock: an atomically created directory in the campaign, removed on exit."""
    def __init__(self,run:Path,command:str):self.path=run/LOCK_NAME;self.command=command;self.held=False
    def __enter__(self):
        try:os.mkdir(self.path,0o700)
        except FileExistsError:
            try:owner=(self.path/'owner.json').read_text().strip()
            except OSError:owner='unknown (owner.json not written yet or unreadable)'
            raise Refuse(75,f'another submission for this campaign holds {self.path} ({owner}); nothing submitted. Rerun when it has '
                            f'finished, or remove {self.path} by hand if no such process is running')
        self.held=True
        try:
            info={'host':socket.gethostname(),'pid':os.getpid(),'user':scheduler_user(),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'command':self.command}
            (self.path/'owner.json').write_text(json.dumps(info)+'\n')
        except BaseException:
            self.__exit__(None,None,None);raise  # __exit__ is not called when __enter__ raises: release our own lock here
        return self
    def __exit__(self,*exc):
        if self.held:
            try:(self.path/'owner.json').unlink()
            except FileNotFoundError:pass
            os.rmdir(self.path);self.held=False
        return False

def positive(env,name,default):
    v=env.get(name,str(default))
    if not v.isdigit()or int(v)<1:raise Refuse(64,f'{name} must be a positive integer (got {v!r})')
    return int(v)

def checked_options(tokens,what):
    why=prod.check_sbatch_args(tokens)
    if why:raise Refuse(64,f'{what}: {why}. Allowed: --'+' --'.join(sorted(prod.SBATCH_LONG_VALUE|prod.SBATCH_LONG_FLAG))+' and -'+' -'.join(sorted(prod.SBATCH_SHORT_VALUE)))
    return list(tokens)

class Context:
    def __init__(self,env,extra):
        for n in CLUSTER_SELECTORS:
            if env.get(n):raise Refuse(64,f'{n} is set: cluster selection is not supported (queries and submissions must address the same cluster); unset it')
        text=env.get('C8_SBATCH_ARGS','')
        if '\n'in text:raise Refuse(64,'C8_SBATCH_ARGS must be a single line')
        try:site=shlex.split(text)
        except ValueError as e:raise Refuse(64,f'C8_SBATCH_ARGS cannot be parsed: {e}')
        self.site=checked_options(site,'C8_SBATCH_ARGS');self.extra=checked_options(extra,'extra sbatch arguments')
        self.max_array=positive(env,'C8_MAX_ARRAY',prod.MAX_ARRAY);self.throttle=positive(env,'C8_THROTTLE',64)
        self.policy=env.get('C8_TIME_POLICY')or'finite'
        if self.policy not in POLICIES:raise Refuse(64,f'C8_TIME_POLICY must be one of {", ".join(POLICIES)} (got {self.policy!r})')
        self.user_time=prod.time_option(self.site+self.extra)
        if self.policy=='unlimited'and self.user_time is not None:
            raise Refuse(64,f'C8_TIME_POLICY=unlimited submits every job with --time=0; remove --time/-t ({self.user_time}) from C8_SBATCH_ARGS and the extra options')
        if not env.get('C8_RUN'):raise Refuse(64,'set C8_RUN to the planned campaign directory')
        self.run=Path(env['C8_RUN']).resolve()
        if not (self.run/'manifest.json').is_file():raise Refuse(64,f'no manifest.json in C8_RUN={self.run}')
        try:
            self.m=load(self.run/'manifest.json')
            if self.m.get('schema')==prod.V1_SCHEMA:raise ValueError(prod.V1_MESSAGE.format(d=self.run))
            if self.m.get('schema')!=prod.SCHEMA:raise ValueError(f'schema {self.m.get("schema")} is not {prod.SCHEMA}')
            self.jobs=len(self.m['jobs']);self.threads=int(self.m['threads']);est=self.m['estimates'].get('suggested_time_seconds')
            self.merge_workers=min(positive(env,'C8_MERGE_WORKERS',1),len(self.m['groups']))
            self.suggested=prod.hms(est)if est else None
        except Exception as e:raise Refuse(64,f'cannot read the plan in {self.run}: {e}')
        changed=prod.tool_changes(self.run)
        if changed:raise Refuse(64,f'pinned tools differ from the plan ({", ".join(sorted(changed))}); run and the merge job would refuse them, so nothing is '
                                    f'submitted. Restore the planned tools, or merge/assemble by hand with --accept-tool-change')
        self.tag=prod.campaign_tag(self.run);self.logs=self.run/'slurm_logs';self.env=env
        self.logpat=str(self.logs).replace('%','%%')  # a literal '%' in the campaign path is not a Slurm filename pattern
        dropped=sorted(k for k in env if k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)
        if dropped:print('C8: ignoring inherited '+', '.join(dropped),file=sys.stderr)
    def work_time(self)->str:
        t=self.user_time or self.suggested
        if t is None:raise Refuse(64,'the plan has no wall-time estimate (no calibration for its backend); give --time in C8_SBATCH_ARGS or as an extra option, or set C8_TIME_POLICY=unlimited where the site requires it')
        return t
    def sbatch_env(self,offset=None):
        e={k:v for k,v in self.env.items()if not(k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)}
        e.update(C8_RUN=str(self.run),C8_PACKAGE=str(ROOT),C8_MERGE_WORKERS=str(self.merge_workers));e.pop('C8_ARRAY_OFFSET',None)
        if offset is None:e.pop('C8_INDEX_OFFSET',None)
        else:e['C8_INDEX_OFFSET']=str(offset)
        return e
    def sbatch(self,args,offset=None):
        cp=subprocess.run(['sbatch','--parsable',*args],capture_output=True,text=True,env=self.sbatch_env(offset))
        if cp.returncode:raise Refuse(cp.returncode or 1,'sbatch failed: '+(cp.stderr or cp.stdout).strip()[-800:])
        jid=cp.stdout.strip().split(';')[0]
        if self.policy=='unlimited':self.verify_unlimited(jid)
        return jid
    def verify_unlimited(self,jid):
        cp=subprocess.run(['scontrol','show','job',jid],capture_output=True,text=True,env={k:v for k,v in self.env.items()if not k.startswith('SQUEUE_')})
        limits=re.findall(r'TimeLimit=(\S+)',cp.stdout)
        if cp.returncode or not limits or any(x!='UNLIMITED'for x in limits):
            seen=','.join(sorted(set(limits)))or'unknown (scontrol failed)'
            raise Refuse(70,f'job {jid} was accepted with TimeLimit={seen}, not UNLIMITED, although C8_TIME_POLICY=unlimited submitted --time=0. '
                            f'It was NOT cancelled and nothing further was submitted: inspect it (scontrol show job {jid}) and scancel it yourself if needed')
    def time_args(self,merge=False)->list[str]:
        if self.policy=='unlimited':return['--time=0']
        return [f'--time={(self.user_time or MERGE_TIME)if merge else self.work_time()}']
    def work(self,offset,array):
        ids=expand(array)
        if any(offset+i>=self.jobs for i in ids)or any(i>=self.max_array for i in ids):raise Refuse(64,f'window {offset}:{array} is outside the plan ({self.jobs} jobs) or wider than C8_MAX_ARRAY')
        self.logs.mkdir(parents=True,exist_ok=True)
        # Defaults, then the user's (allowlisted) options, then the options this tool owns: the last occurrence wins.
        jid=self.sbatch([*self.site,f'--cpus-per-task={self.threads}',*self.extra,f'--array={array}%{self.throttle}',
                         f'--output={self.logpat}/work-%A_%a.log',f'--comment={self.tag}:off={offset}','--export=ALL',*self.time_args(),str(ROOT/'slurm/run_array.sh')],offset)
        print(f'array {jid}: C8_INDEX_OFFSET={offset}, indices {array} (%{self.throttle}); logs {self.logs}/work-{jid}_<i>.log',flush=True);return jid
    def merge(self,deps):
        self.logs.mkdir(parents=True,exist_ok=True)
        args=[*self.site]+([f'--dependency=afterok:{":".join(deps)}']if deps else[])+[f'--cpus-per-task={self.merge_workers}',f'--output={self.logpat}/merge-%j.log',f'--comment={self.tag}:merge','--export=ALL',*self.time_args(merge=True),str(ROOT/'slurm/merge.sh')]
        mid=self.sbatch(args);print(f'merge {mid} '+(f'(afterok:{":".join(deps)})'if deps else'(no dependency)')+f'; log {self.logs}/merge-{mid}.log',flush=True);return mid

def expand(spec:str)->list[int]:
    out=[]
    for part in spec.split(','):
        lo,_,hi=part.partition('-')
        if not lo.isdigit()or(hi and not hi.isdigit())or(hi and int(hi)<int(lo)):raise Refuse(64,f'invalid array range {spec!r}')
        out.extend(range(int(lo),int(hi or lo)+1))
    return out

def scheduler_user()->str:
    """The account sbatch submits under: the name of the process's real uid (never USER, LOGNAME or getpass, which
    follow the environment); the numeric uid when the uid has no passwd entry (squeue -u accepts it)."""
    uid=os.getuid()
    try:return pwd.getpwuid(uid).pw_name
    except KeyError:return str(uid)

def snapshot(env)->str:
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')}
    cp=subprocess.run(['squeue','--all','--states=all','-u',scheduler_user(),'-h','-r','-o','%200k|%K|%T|%i'],capture_output=True,text=True,env=e)
    if cp.returncode:raise Refuse(69,'squeue failed; job state unknown, nothing submitted')
    return cp.stdout

def queue(c:Context)->dict:
    q=prod.queue_state(c.run,snapshot(c.env))
    if q['refuse']:raise Refuse(q['refuse']['code'],q['refuse']['message'])
    return q

def main(argv,env)->int:
    if not argv or argv[0]not in('submit','window','resubmit'):print(__doc__,file=sys.stderr);return 64
    cmd=argv[0];rest=argv[1:]
    try:
        if cmd=='window':
            if not rest or ':'not in rest[0]:raise Refuse(64,'usage: window OFFSET:ARRAY [sbatch options]')
            off,_,arr=rest[0].partition(':')
            if not off.isdigit():raise Refuse(64,f'invalid window offset {off!r}')
            c=Context(env,rest[1:]);ids=[int(off)+i for i in expand(arr)]
            if any(i>=c.jobs for i in ids)or any(i>=c.max_array for i in expand(arr)):raise Refuse(64,f'window {rest[0]} is outside the plan ({c.jobs} jobs) or wider than C8_MAX_ARRAY')
            with CampaignLock(c.run,'window '+rest[0]):
                q=queue(c)
                if q['live_merges']:raise Refuse(65,f'merge job(s) {",".join(q["live_merges"])} of this campaign are live; scancel them first, or use slurm/resubmit.sh')
                live=sorted(set(ids)&set(q['live_indices']))
                if live:raise Refuse(65,f'indices {prod.ranges(live)} of this window are still queued or running; nothing submitted. Wait for them, or run slurm/resubmit.sh, which resubmits only indices that are not live')
                missing=set(prod.status_report(c.run,(),c.max_array,fingerprints=False)['missing_jobs']);todo=[i for i in ids if i in missing];done=[i for i in ids if i not in missing]
                if done:print(f'C8: skipping indices {prod.ranges(done)}: every block is committed')
                if not todo:print('C8: nothing to submit: every block of this window is committed');return 0
                c.work(int(off),prod.ranges([i-int(off)for i in todo]))
            print('C8: submit the merge once the campaign is complete (slurm/resubmit.sh does both and waits on live work)');return 0
        c=Context(env,rest)
        with CampaignLock(c.run,cmd):
            if cmd=='submit':
                q=queue(c)
                if q['live_work']or q['live_merges']:
                    raise Refuse(65,f'this campaign already has live jobs (indices {prod.ranges(q["live_indices"])or"none"}; merges {",".join(q["live_merges"])or"none"}); nothing submitted. Use slurm/resubmit.sh, which submits only what is missing and not live')
                st=prod.status_report(c.run,(),c.max_array,fingerprints=False)
                if not st['missing_jobs']:print('C8: nothing to submit: every checkpoint block is committed (slurm/resubmit.sh submits a merge-only job)');return 0
                ids=[c.work(w['offset'],w['array'])for w in st['resubmit']]
                c.merge(ids);print(f'status: {sys.executable} {ROOT/"tools/production.py"} status {c.run}   (recovery: slurm/resubmit.sh)');return 0
            d=prod.recovery_plan(c.run,snapshot(env),c.max_array)
            if d['refuse']:raise Refuse(d['refuse']['code'],d['refuse']['message'])
            if d['live_missing_not_resubmitted']:print(f'C8: missing indices {prod.ranges(d["live_missing_not_resubmitted"])} are still live; not resubmitted')
            ids=[c.work(w['offset'],w['array'])for w in d['arrays']]+d['merge_waits_on_live_tasks']
            if not ids:print('C8: no work to resubmit and no live elements; submitting the merge only')
            c.merge(ids);return 0
    except Refuse as r:
        print('C8: '+str(r),file=sys.stderr);return r.code

if __name__=='__main__':sys.exit(main(sys.argv[1:],dict(os.environ)))
