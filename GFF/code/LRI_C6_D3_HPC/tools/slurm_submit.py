#!/usr/bin/env python3
"""The single guarded path for every Slurm submission of a campaign (slurm/submit.sh, slurm/resubmit.sh, and the
resubmission lines printed by `production.py status`, which call `slurm/submit.sh --window`).

  slurm_submit.py submit [extra sbatch options]            all work windows + an afterok merge
  slurm_submit.py window OFFSET:ARRAY [extra sbatch options]  one work window (as printed by status)
  slurm_submit.py resubmit [extra sbatch options]           recovery (production.py recover) + a dependent merge

Environment: C6_RUN, C6_PACKAGE (the package this file belongs to), C6_SBATCH_ARGS (one line, shell-lexed),
C6_MAX_ARRAY (default 1000), C6_THROTTLE (default 64); C6_ENV_SETUP/C6_PYTHON are passed on to the jobs.
Guarantees, independent of the caller's environment and arguments:
  * C6_SBATCH_ARGS and the extra options are each checked against the sbatch-option allowlist SEPARATELY, so neither
    can consume the other's tokens; C6_MAX_ARRAY and C6_THROTTLE must be positive integers;
  * inherited cluster selectors (SBATCH_CLUSTERS, SLURM_CLUSTERS, SQUEUE_CLUSTERS) are refused, so queries and
    submissions always address the same cluster; other SBATCH_* inputs outside a small allowlist are removed from
    sbatch's environment, and SQUEUE_* inputs from squeue's;
  * commands are argument lists (no shell splicing); campaign, package and window offset are set in sbatch's own
    environment (with --export=ALL an inherited value would otherwise win); merges carry no offset.
  * one submission at a time per campaign: submit, window and resubmit hold the lock directory $C6_RUN/.c6_submit.lock
    (atomic mkdir; flock is not relied on) from before the recovery queue snapshot through the last sbatch, so a later
    call always sees an earlier call's jobs. A second call while the lock exists submits nothing (exit 75). A lock left
    by a killed process is never broken automatically: its owner.json names the holder; remove it by hand.
Exit codes: 64 invalid input (nothing submitted), 65 a merge of the campaign is live, 69 unknown or uncertain state,
75 another submission for the campaign holds the lock.
"""
from __future__ import annotations
import getpass,json,os,shlex,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import production as prod
from common import ROOT,load
CLUSTER_SELECTORS=('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS')
SBATCH_ENV_ALLOWED=frozenset('SBATCH_ACCOUNT SBATCH_PARTITION SBATCH_QOS SBATCH_RESERVATION SBATCH_CONSTRAINT SBATCH_MEM_PER_CPU SBATCH_MEM_PER_NODE SBATCH_TIMELIMIT SBATCH_WCKEY SBATCH_REQUEUE SBATCH_NO_REQUEUE'.split())

class Refuse(Exception):
    def __init__(self,code,msg):super().__init__(msg);self.code=code

LOCK_NAME='.c6_submit.lock'
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
            info={'host':socket.gethostname(),'pid':os.getpid(),'user':getpass.getuser(),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'command':self.command}
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
        text=env.get('C6_SBATCH_ARGS','')
        if '\n'in text:raise Refuse(64,'C6_SBATCH_ARGS must be a single line')
        try:site=shlex.split(text)
        except ValueError as e:raise Refuse(64,f'C6_SBATCH_ARGS cannot be parsed: {e}')
        self.site=checked_options(site,'C6_SBATCH_ARGS');self.extra=checked_options(extra,'extra sbatch arguments')
        self.max_array=positive(env,'C6_MAX_ARRAY',prod.MAX_ARRAY);self.throttle=positive(env,'C6_THROTTLE',64)
        if not env.get('C6_RUN'):raise Refuse(64,'set C6_RUN to the planned campaign directory')
        self.run=Path(env['C6_RUN']).resolve()
        if not (self.run/'manifest.json').is_file():raise Refuse(64,f'no manifest.json in C6_RUN={self.run}')
        try:self.m=load(self.run/'manifest.json');self.jobs=len(self.m['jobs']);self.threads=int(self.m['threads']);self.wall=prod.hms(self.m['estimates']['suggested_time_seconds'])
        except Exception as e:raise Refuse(64,f'cannot read the plan in {self.run}: {e}')
        if self.jobs<1:raise Refuse(64,'the plan has no jobs')
        self.tag=prod.campaign_tag(self.run);self.logs=self.run/'slurm_logs';self.env=env
        self.logpat=str(self.logs).replace('%','%%')  # a literal '%' in the campaign path is not a Slurm filename pattern
        dropped=sorted(k for k in env if k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)
        if dropped:print('C6: ignoring inherited '+', '.join(dropped),file=sys.stderr)
    def sbatch_env(self,offset=None):
        e={k:v for k,v in self.env.items()if not(k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)}
        e.update(C6_RUN=str(self.run),C6_PACKAGE=str(ROOT))
        if offset is None:e.pop('C6_INDEX_OFFSET',None)
        else:e['C6_INDEX_OFFSET']=str(offset)
        return e
    def sbatch(self,args,offset=None):
        cp=subprocess.run(['sbatch','--parsable',*args],capture_output=True,text=True,env=self.sbatch_env(offset))
        if cp.returncode:raise Refuse(cp.returncode or 1,'sbatch failed: '+(cp.stderr or cp.stdout).strip()[-800:])
        return cp.stdout.strip().split(';')[0]
    def work(self,offset,array):
        ids=expand(array)
        if any(offset+i>=self.jobs for i in ids)or any(i>=self.max_array for i in ids):raise Refuse(64,f'window {offset}:{array} is outside the plan ({self.jobs} jobs) or wider than C6_MAX_ARRAY')
        self.logs.mkdir(parents=True,exist_ok=True)
        # Defaults, then the user's (allowlisted) options, then the options this tool owns: the last occurrence wins.
        jid=self.sbatch([*self.site,f'--cpus-per-task={self.threads}',f'--time={self.wall}',*self.extra,f'--array={array}%{self.throttle}',
                         f'--output={self.logpat}/work-%A_%a.log',f'--comment={self.tag}:off={offset}','--export=ALL',str(ROOT/'slurm/run_array.sh')],offset)
        print(f'array {jid}: C6_INDEX_OFFSET={offset}, indices {array} (%{self.throttle}); logs {self.logs}/work-{jid}_<i>.log',flush=True);return jid
    def merge(self,deps):
        self.logs.mkdir(parents=True,exist_ok=True)
        args=[*self.site]+([f'--dependency=afterok:{":".join(deps)}']if deps else[])+[f'--output={self.logpat}/merge-%j.log',f'--comment={self.tag}:merge','--export=ALL',str(ROOT/'slurm/merge.sh')]
        mid=self.sbatch(args);print(f'merge {mid} '+(f'(afterok:{":".join(deps)})'if deps else'(no dependency)')+f'; log {self.logs}/merge-{mid}.log',flush=True);return mid

def expand(spec:str)->list[int]:
    out=[]
    for part in spec.split(','):
        lo,_,hi=part.partition('-')
        if not lo.isdigit()or(hi and not hi.isdigit())or(hi and int(hi)<int(lo)):raise Refuse(64,f'invalid array range {spec!r}')
        out.extend(range(int(lo),int(hi or lo)+1))
    return out

def snapshot(env)->str:
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')}
    import getpass
    cp=subprocess.run(['squeue','--all','--states=all','-u',env.get('USER')or getpass.getuser(),'-h','-r','-o','%200k|%K|%T|%i'],capture_output=True,text=True,env=e)
    if cp.returncode:raise Refuse(69,'squeue failed; job state unknown, nothing submitted')
    return cp.stdout

def main(argv,env)->int:
    if not argv or argv[0]not in('submit','window','resubmit'):print(__doc__,file=sys.stderr);return 64
    cmd=argv[0];rest=argv[1:]
    try:
        if cmd=='window':
            if not rest or ':'not in rest[0]:raise Refuse(64,'usage: window OFFSET:ARRAY [sbatch options]')
            off,_,arr=rest[0].partition(':')
            if not off.isdigit():raise Refuse(64,f'invalid window offset {off!r}')
            c=Context(env,rest[1:]);expand(arr)
            with CampaignLock(c.run,'window '+rest[0]):c.work(int(off),arr)
            print('C6: submit the merge once the campaign is complete (slurm/resubmit.sh does both and waits on live work)');return 0
        c=Context(env,rest)
        with CampaignLock(c.run,cmd):
            if cmd=='submit':
                ids=[c.work(off,f'0-{min(c.max_array,c.jobs-off)-1}')for off in range(0,c.jobs,c.max_array)]
                c.merge(ids);print(f'status: {sys.executable} {ROOT/"tools/production.py"} status {c.run}   (recovery: slurm/resubmit.sh)');return 0
            d=prod.recovery_plan(c.run,snapshot(env),c.max_array)
            if d['refuse']:raise Refuse(d['refuse']['code'],d['refuse']['message'])
            if d['live_missing_not_resubmitted']:print(f'C6: missing indices {prod.ranges(d["live_missing_not_resubmitted"])} are still live; not resubmitted')
            ids=[c.work(w['offset'],w['array'])for w in d['arrays']]+d['merge_waits_on_live_tasks']
            if not ids:print('C6: no work to resubmit and no live elements')
            c.merge(ids);return 0
    except Refuse as r:
        print('C6: '+str(r),file=sys.stderr);return r.code

if __name__=='__main__':sys.exit(main(sys.argv[1:],dict(os.environ)))
