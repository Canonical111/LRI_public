#!/usr/bin/env python3
"""The single guarded path for every Slurm submission of a campaign (slurm/submit.sh, slurm/resubmit.sh, and the
resubmission lines printed by `production.py status`, which call `slurm/submit.sh --window`). PLAN component D.

  slurm_submit.py submit [extra sbatch options]               incomplete work windows (arrays) + an afterok merge
  slurm_submit.py window OFFSET:ARRAY [extra sbatch options]  one work window (as printed by status)
  slurm_submit.py resubmit [extra sbatch options]             array recovery (production.py recover) + a dependent merge
  slurm_submit.py lanes N [extra sbatch options]              lane mode: N whole-node lane workers and ONE merge that
                                                              waits (afterany) on every live and new lane worker; a
                                                              superseded merge is cancelled only after the new merge
                                                              was accepted and only while the scheduler still holds it
                                                              PENDING (scontrol hold, then scancel --state=PENDING; a
                                                              merge that started is left alone; O08). N = 0: only that
                                                              merge.

Environment: C8_RUN, C8_PACKAGE (the package this file belongs to), C8_SBATCH_ARGS (one line, shell-lexed),
C8_MAX_ARRAY (1000), C8_THROTTLE (64), C8_TIME_POLICY (finite | unlimited), C8_LANE_TIME (24:00:00), C8_MERGE_TIME
(02:00:00), C8_LANE_MEM (180G; amdq-only 245G, Expanse compute 240G), C8_MERGE_MEM (64G), C8_MERGE_JOBS (24),
C8_SITE (expanse | symmetry | other), C8_AMDQ_CAP, C8_SITE_LOCK_DIR (default $HOME), C8_ACCOUNT, and in drill mode
(C8_LANE_DRILL=1) C8_LANE_CPUS (2-8). C8_ENV_SETUP/C8_PYTHON and the C8_LANE_* settings are passed on to the jobs.
Guarantees, independent of the caller's environment and arguments:
  * C8_SBATCH_ARGS and the extra options are each checked against the sbatch-option allowlist SEPARATELY; inherited
    cluster selectors are refused; other SBATCH_* inputs outside a small allowlist are removed from sbatch's
    environment, and SQUEUE_* inputs from squeue's; commands are argument lists (no shell splicing);
  * every job is named by this tool (c8d2-array, c8d2-lanes, c8d2-merge: the admission rules count by the c8d2- prefix)
    and tagged with the Slurm comment <campaign tag>:off=<offset>, :lane or :merge;
  * one submission at a time per campaign (the lock $C8_RUN/.c8_submit.lock, exit 75), from before the campaign
    snapshot through the last sbatch and its ledger line; queue snapshots use the real uid's account (IR2-01);
  * lane mode and array mode are never mixed while jobs are live (65); no duplicate live work from any entry point;
  * every job role has its own effective options (O04): work arrays and lane workers take C8_SBATCH_ARGS then the extra
    options; a merge takes the same options (partition, account, QOS and every other override included) except its own
    resources, memory and CPUs (C8_MERGE_MEM, C8_MERGE_JOBS), and its name; its time is the user's --time when one is
    given, else C8_MERGE_TIME, as for every job. Admission counts each new job on the partitions of its own role, and
    the ledger records each job's own partition and account. The account and partition are resolved once per role
    (user option, SBATCH_ACCOUNT/SBATCH_PARTITION, C8_ACCOUNT, Expanse's yun124 and shared) and passed to every sbatch
    explicitly (--account, --partition), so the job is charged to and runs on what admission counted (X12);
  * before every sbatch the effective options of the job (the script's #SBATCH directives, overridden by the SBATCH_*
    input variables, overridden by the command line) are checked against the role's contract (CK-K01/O05): a normal
    lane worker is exclusive with C8_LANE_MEM; a drill lane worker is never exclusive, has -c C8_LANE_CPUS, C8_LANE_MEM
    and --no-requeue; a merge is never exclusive and has C8_MERGE_JOBS CPUs and C8_MERGE_MEM; an array element is
    never exclusive; the partition is the one admission counted. A violation refuses (64) before the job exists;
  * admission counts EVERY new job, the merge included (R12): k = N + 1 for `lanes N`, the array elements plus the
    merge for submit/resubmit, the window's elements for window. Under C8_SITE=expanse the agreed disjoint
    reservation H7E-R (LRI_C8_shared/inventory/DECISIONS.md) applies: at most 11 running and 27 submitted normal-QOS
    c8d2-* jobs of this user, the whole account at most 32 running normal-QOS jobs, at most 32 live c8d2-* jobs on
    the shared partition and at most 4 compute nodes (compute and debug partitions) during development. A pilot
    window re-splits these through a DECISIONS line: C8_EXP_RUNNING, C8_EXP_SUBMITTED, C8_EXP_ACCOUNT_RUNNING,
    C8_EXP_SHARED and C8_EXP_NODES override them only together with C8_ADMISSION_REF (that line), which every ledger
    line records. Under C8_AMDQ_CAP=n (symmetry, H7) the live c8d2- jobs on any AMD partition (amdq, amddebugq,
    amdpreq, counted together; a job counts if any partition it lists is one of them) plus the new ones must not exceed
    n. A refusal exits 65 and prints the largest admissible N (lanes) or element count. A superseded merge stays
    counted until a snapshot shows it gone or CANCELLED. Decisions are serialized across campaigns by the per-user site
    lock $C8_SITE_LOCK_DIR/.c8_site_<site>.lock (exit 75), taken after the campaign lock, held from the admission
    snapshot through the last sbatch and its ledger line;
  * every submitted job is appended to the allocation ledger $C8_RUN/submissions.jsonl (schema c8-d2-ledger-1);
  * memory: lane workers take --mem only from C8_LANE_MEM and merges only from C8_MERGE_MEM (a --mem in the options is
    refused for lanes, 64); array elements take the plan's suggestion (1.5 x the largest est_peak_bytes + 1 GiB), and a
    user --mem below it is refused (64), a larger one used. The effective options follow sbatch's memory precedence
    (Z7, Stage-6 fix round 3; Slurm's slurm_opt.c, _validate_memory_options): a memory option of the job's command line
    or of its script's #SBATCH directives replaces an inherited SBATCH_MEM_PER_CPU / SBATCH_MEM_PER_NODE, which is
    then also removed from sbatch's environment; two memory options of different kinds on the command line and in the
    directives (e.g. a user --mem-per-cpu against the array script's #SBATCH --mem), or two inherited ones without
    either, are refused (64) as sbatch refuses them;
  * every job of a submission (the work arrays and the merge, the lane workers and the merge, a window's arrays) is
    built and checked against its role's contract BEFORE the first sbatch (preflight, Z7): a contract that only the
    merge breaks refuses (64) with nothing submitted, never after the work jobs were accepted;
  * drill mode (C8_LANE_DRILL=1, test-only plans; the lane drills on a shared partition): no --exclusive, -c from
    C8_LANE_CPUS (2-8), --mem from C8_LANE_MEM (required, at most 2,000 MB per CPU), --no-requeue; the merge takes
    -c C8_MERGE_JOBS (<= 8) and C8_MERGE_MEM under the same bound;
  * wall time: C8_TIME_POLICY=finite (default): work jobs the plan's suggestion (or the user's --time), lane workers
    C8_LANE_TIME, merges C8_MERGE_TIME. unlimited: every job gets --time=0 as its last option, any other --time is
    refused (64), and `scontrol show job` must report TimeLimit=UNLIMITED after each sbatch, else exit 70 at once: a job
    accepted without that verification stops the submission (no further worker, no merge, no cancellation of a
    superseded merge; O07), and the message lists every job accepted so far. The recovery then includes every live job:
    `submit.sh --lanes 0` submits a merge on every live lane worker, `resubmit.sh` one on every live element;
  * a pinned tool that differs from the plan refuses every submission (64);
  * before submitting it prints the idle-node count of each requested partition and sbatch --test-only's start
    estimate (informational).
Exit codes: 64 invalid input, 65 live work or merge of the campaign, or a full admission budget, 69 unknown or
uncertain state or failed squeue, 70 a job accepted without TimeLimit=UNLIMITED under the unlimited policy, 75 a lock
is held.
"""
from __future__ import annotations
import json,os,re,shlex,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import production as prod
import lanes
from common import ROOT,CampaignLock,DirLock,LOCK_NAME,Refuse,load,scheduler_user,utc
CLUSTER_SELECTORS=('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS')
SBATCH_ENV_ALLOWED=frozenset('SBATCH_ACCOUNT SBATCH_PARTITION SBATCH_QOS SBATCH_RESERVATION SBATCH_CONSTRAINT SBATCH_MEM_PER_CPU SBATCH_MEM_PER_NODE SBATCH_WCKEY SBATCH_REQUEUE SBATCH_NO_REQUEUE'.split())
POLICIES=('finite','unlimited')
AMD_PARTITIONS=frozenset({'amdq','amddebugq','amdpreq'})
EXPANSE_NODE_PARTITIONS=frozenset({'compute','debug'})
# H7E-R (DECISIONS.md, agreed 2026-10-03): this session's share of the yun124 budget.
H7E_R={'C8_EXP_RUNNING':11,'C8_EXP_SUBMITTED':27,'C8_EXP_ACCOUNT_RUNNING':32,'C8_EXP_SHARED':32,'C8_EXP_NODES':4}
RUNNING_LIKE=frozenset('RUNNING COMPLETING CONFIGURING STAGE_OUT SIGNALING RESIZING'.split())
LEDGER_SCHEMA='c8-d2-ledger-1'
JOB_NAMES={'array':'c8d2-array','lane':'c8d2-lanes','merge':'c8d2-merge'}
DRILL_MB_PER_CPU=2000
# The options a merge never takes from C8_SBATCH_ARGS or the extra options: its memory and CPUs (C8_MERGE_MEM,
# C8_MERGE_JOBS) and its name; a user --time comes back through time_args (the user's time, else C8_MERGE_TIME). Every
# other user option reaches the merge too (O04).
MERGE_OWN_OPTIONS=frozenset({'mem','mem-per-cpu','cpus-per-task','c','time','t','job-name','J'})
# Arities for reading a job's effective options: the allowlisted options and those the tools and scripts set.
EFF_LONG_VALUE=prod.SBATCH_LONG_VALUE|frozenset('nodes ntasks output error comment dependency array export chdir'.split())
EFF_LONG_FLAG=frozenset('exclusive oversubscribe requeue no-requeue hold parsable test-only'.split())
EFF_SHORT={'A':'account','p':'partition','q':'qos','C':'constraint','t':'time','c':'cpus-per-task','J':'job-name','x':'exclude','w':'nodelist',
           'L':'licenses','N':'nodes','n':'ntasks','o':'output','e':'error','d':'dependency','a':'array','D':'chdir'}
EFF_SHORT_FLAG={'s':'oversubscribe','H':'hold'}
EFF_ENV={'SBATCH_ACCOUNT':'account','SBATCH_PARTITION':'partition','SBATCH_QOS':'qos','SBATCH_RESERVATION':'reservation','SBATCH_CONSTRAINT':'constraint',
         'SBATCH_MEM_PER_CPU':'mem-per-cpu','SBATCH_MEM_PER_NODE':'mem','SBATCH_WCKEY':'wckey','SBATCH_REQUEUE':'requeue','SBATCH_NO_REQUEUE':'no-requeue'}

def tokens_of(pairs)->list[str]:
    """Allowlisted (name, value) pairs (prod.sbatch_options) back to sbatch tokens."""
    out=[]
    for n,v in pairs:
        if len(n)==1:out+=[f'-{n}',v]
        elif v is None:out.append(f'--{n}')
        else:out.append(f'--{n}={v}')
    return out

def option_pairs(tokens,where:str)->list[tuple[str,object]]:
    """(long name, value) pairs of sbatch option tokens in order (a flag gives True, --exclusive=MODE its MODE); a token
    that is not a known sbatch option refuses (64), so no option escapes the checks below."""
    out=[];i=0
    while i<len(tokens):
        t=tokens[i]
        if t.startswith('--'):
            n,eq,v=t[2:].partition('=')
            if n in EFF_LONG_FLAG:out.append((n,v if eq else True));i+=1;continue
            if n not in EFF_LONG_VALUE:raise Refuse(64,f'{where}: cannot read the sbatch option {t}')
            if eq:out.append((n,v));i+=1
            elif i+1<len(tokens):out.append((n,tokens[i+1]));i+=2
            else:raise Refuse(64,f'{where}: the sbatch option {t} has no value')
        elif t.startswith('-')and len(t)==2 and t[1]in EFF_SHORT_FLAG:out.append((EFF_SHORT_FLAG[t[1]],True));i+=1
        elif t.startswith('-')and len(t)>=2 and t[1]in EFF_SHORT:
            if len(t)>2:out.append((EFF_SHORT[t[1]],t[2:]));i+=1
            elif i+1<len(tokens):out.append((EFF_SHORT[t[1]],tokens[i+1]));i+=2
            else:raise Refuse(64,f'{where}: the sbatch option {t} has no value')
        else:raise Refuse(64,f'{where}: unexpected word {t!r}')
    return out

def script_directives(path:Path)->list[str]:
    """The option tokens of a batch script's #SBATCH lines as sbatch reads them: from the top of the script up to the
    first line that is neither blank nor a comment."""
    toks=[]
    for line in Path(path).read_text().splitlines():
        s=line.strip()
        if s.startswith('#SBATCH'):toks+=shlex.split(s[len('#SBATCH'):]);continue
        if not s or s.startswith('#'):continue
        break
    return toks

MEM_OPTIONS=('mem','mem-per-cpu')  # the memory options sbatch keeps mutually exclusive (--mem-per-gpu is not allowlisted)
MEM_ENV=('SBATCH_MEM_PER_CPU','SBATCH_MEM_PER_NODE')

def memory_kinds(args:list,env:dict)->tuple[list[str],list[str]]:
    """Z7: (the memory options set by the job's script directives or command line, those set by inherited SBATCH_*
    variables), each list in MEM_OPTIONS order without repeats."""
    given={n for n,_ in option_pairs(script_directives(args[-1]),f'{Path(args[-1]).name} #SBATCH directives')+option_pairs(args[:-1],'sbatch command line')}
    inherited={EFF_ENV[k]for k in MEM_ENV if env.get(k)}
    return [n for n in MEM_OPTIONS if n in given],[n for n in MEM_OPTIONS if n in inherited]

def effective_options(args:list,env:dict)->dict:
    """The options a submission takes effect with (sbatch's precedence): the script's #SBATCH directives (args[-1]),
    overridden by the SBATCH_* input variables it receives, overridden by the command line (args[:-1]). A flag set by
    any source stays set: sbatch has no option that cancels --exclusive (CK-K01/O05). Memory (Z7, S6-C-R3-02) follows
    sbatch's own rule (slurm_opt.c, _validate_memory_options): when the directives or the command line set a memory
    option, the inherited ones (SBATCH_MEM_PER_CPU, SBATCH_MEM_PER_NODE) are reset and do not take effect; two different
    memory options among the directives and the command line, or among the inherited variables without either, make
    sbatch stop ("mutually exclusive"), and are refused here (64) before any job exists."""
    given,inherited=memory_kinds(args,env)
    if len(given)>1:
        raise Refuse(64,f'--{" and --".join(given)} are both set for this job (the script {Path(args[-1]).name}\'s #SBATCH directives and the command line): '
                        'sbatch refuses mutually exclusive memory options; give --mem (the scripts set --mem)')
    if not given and len(inherited)>1:raise Refuse(64,f'{" and ".join(MEM_ENV)} are both set: sbatch refuses mutually exclusive memory options; unset one')
    eff={}
    for pairs in (option_pairs(script_directives(args[-1]),f'{Path(args[-1]).name} #SBATCH directives'),
                  [(n,env[k])for k,n in EFF_ENV.items()if env.get(k)and not(given and n in MEM_OPTIONS)],option_pairs(args[:-1],'sbatch command line')):
        for n,v in pairs:eff[n]=v
    return eff

class Unverified(Refuse):
    """A job sbatch ACCEPTED whose TimeLimit is not UNLIMITED under C8_TIME_POLICY=unlimited (exit 70). It is in the
    ledger and live; the submission stops at once, no further job and no cancellation (O07)."""
    def __init__(self,msg:str,jobid:str,role:str):super().__init__(70,msg);self.jobid=jobid;self.role=role

def positive(env,name,default):
    v=env.get(name,str(default))
    if not v.isdigit()or int(v)<1:raise Refuse(64,f'{name} must be a positive integer (got {v!r})')
    return int(v)

def checked_options(tokens,what):
    why=prod.check_sbatch_args(tokens)
    if why:raise Refuse(64,f'{what}: {why}. Allowed: --'+' --'.join(sorted(prod.SBATCH_LONG_VALUE|prod.SBATCH_LONG_FLAG))+' and -'+' -'.join(sorted(prod.SBATCH_SHORT_VALUE)))
    return list(tokens)

def slurm_time(env,name,default)->str:
    t=env.get(name,default)
    if not t or not all(c.isdigit()or c in ':-'for c in t)or t.startswith('-'):raise Refuse(64,f'{name} must be a Slurm time such as 01:00:00 or 1-00:00:00 (got {t!r})')
    return t

def mem_mb(text:str)->int:
    """A Slurm memory size (default unit M; K, M, G, T suffixes) in MB."""
    m=re.fullmatch(r'(\d+)([KMGTkmgt]?)[Bb]?',text.strip())
    if not m:raise Refuse(64,f'cannot read the memory size {text!r}')
    n=int(m.group(1));u=(m.group(2)or'M').upper();return {'K':n/1024,'M':n,'G':n*1024,'T':n*1024*1024}[u]

def expand(spec:str)->list[int]:
    out=[]
    for part in spec.split(','):
        lo,_,hi=part.partition('-')
        if not lo.isdigit()or(hi and not hi.isdigit())or(hi and int(hi)<int(lo)):raise Refuse(64,f'invalid array range {spec!r}')
        out.extend(range(int(lo),int(hi or lo)+1))
    return out

def snapshot(env)->str:
    """The campaign-tag snapshot: every job of the real uid's account, all states, array elements expanded."""
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')}
    try:cp=subprocess.run(['squeue','--all','--states=all','-u',scheduler_user(),'-h','-r','-o','%200k|%K|%T|%i'],capture_output=True,text=True,env=e,timeout=300)
    except (OSError,subprocess.SubprocessError):cp=None
    if cp is None or cp.returncode:raise Refuse(69,'squeue failed; job state unknown, nothing submitted')
    return cp.stdout

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
            if str(self.m.get('schema','')).startswith('c7-'):raise ValueError(prod.C7_MESSAGE.format(d=self.run,s=self.m.get('schema')))
            if self.m.get('schema')!=prod.SCHEMA:raise ValueError(f'schema {self.m.get("schema")} is not {prod.SCHEMA}')
            self.jobs=len(self.m['jobs']);self.threads=int(self.m['threads']);est=self.m['estimates'].get('suggested_time_seconds')
            self.suggested=prod.hms(est)if est else None;self.mem_suggestion=int(self.m['estimates']['mem_suggestion_mb'])
        except Exception as e:raise Refuse(64,f'cannot read the plan in {self.run}: {e}')
        changed=prod.tool_changes(self.run)
        if changed:raise Refuse(64,f'pinned tools differ from the plan ({", ".join(sorted(changed))}); run and the merge job would refuse them, so nothing is '
                                    f'submitted. Restore the planned tools, or merge/assemble by hand with --accept-tool-change')
        self.tag=prod.campaign_tag(self.run);self.logs=self.run/'slurm_logs';self.env=env
        self.logpat=str(self.logs).replace('%','%%')  # a literal '%' in the campaign path is not a Slurm filename pattern
        self.merge_time=slurm_time(env,'C8_MERGE_TIME','02:00:00');self.lane_time=slurm_time(env,'C8_LANE_TIME','24:00:00')
        self.site_name=env.get('C8_SITE')or'other'
        if self.site_name not in('expanse','symmetry','other'):raise Refuse(64,f'C8_SITE must be expanse, symmetry or other (got {self.site_name!r})')
        cap=env.get('C8_AMDQ_CAP')
        if cap is not None and not cap.isdigit():raise Refuse(64,f'C8_AMDQ_CAP must be a non-negative integer (got {cap!r})')
        self.amd_cap=int(cap)if cap is not None else None
        self.caps={k:positive(env,k,v)for k,v in H7E_R.items()}
        self.admission_ref=env.get('C8_ADMISSION_REF')
        if self.site_name=='expanse'and any(self.caps[k]!=v for k,v in H7E_R.items())and not self.admission_ref:
            raise Refuse(64,'an Expanse admission cap differs from H7E-R; a pilot window re-splits the budget only through a DECISIONS line: set C8_ADMISSION_REF to it')
        self.drill=env.get('C8_LANE_DRILL')=='1'
        self.merge_jobs=positive(env,'C8_MERGE_JOBS',24)
        if self.drill:
            if not self.m['test_only']:raise Refuse(64,'C8_LANE_DRILL=1 is for test-only plans only (the lane drills)')
            self.lane_cpus=positive(env,'C8_LANE_CPUS',0)if env.get('C8_LANE_CPUS')else None
            if self.lane_cpus is None or not 2<=self.lane_cpus<=8:raise Refuse(64,'drill mode needs C8_LANE_CPUS between 2 and 8')
            if not env.get('C8_LANE_MEM'):raise Refuse(64,'drill mode needs C8_LANE_MEM (at most 2,000 MB per CPU)')
            if mem_mb(env['C8_LANE_MEM'])>DRILL_MB_PER_CPU*self.lane_cpus:raise Refuse(64,f'C8_LANE_MEM={env["C8_LANE_MEM"]} exceeds 2,000 MB x C8_LANE_CPUS={self.lane_cpus}')
            if self.merge_jobs>8:raise Refuse(64,'drill mode needs C8_MERGE_JOBS <= 8')
            if mem_mb(env.get('C8_MERGE_MEM','64G'))>DRILL_MB_PER_CPU*self.merge_jobs:raise Refuse(64,f'C8_MERGE_MEM exceeds 2,000 MB x C8_MERGE_JOBS={self.merge_jobs} (drill mode)')
        self.lane_mem=env.get('C8_LANE_MEM','180G');self.merge_mem=env.get('C8_MERGE_MEM','64G');mem_mb(self.lane_mem);mem_mb(self.merge_mem)
        dropped=sorted(k for k in env if k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)
        if dropped:print('C8: ignoring inherited '+', '.join(dropped),file=sys.stderr)
        self.submitted=[]
    # ---- options (per job role, O04)
    def user_tokens(self,role:str='array')->list[str]:
        """The user's sbatch options effective for one job role: C8_SBATCH_ARGS, then the extra options (a later value
        wins). Work arrays and lane workers take them as given; a merge takes every one of them (partition, account, QOS,
        constraints, exclusions ...) except MERGE_OWN_OPTIONS: memory and CPUs from C8_MERGE_MEM and C8_MERGE_JOBS, its
        own name, and the time of time_args('merge')."""
        toks=self.site+self.extra
        if role!='merge':return list(toks)
        return tokens_of([(n,v)for n,v in prod.sbatch_options(toks)if n not in MERGE_OWN_OPTIONS])
    def opts(self,role:str='array'):return prod.sbatch_options(self.user_tokens(role))
    def partitions(self,role:str='array')->list[str]:
        v=None
        for n,x in self.opts(role):
            if n in('partition','p'):v=x
        v=v or self.env.get('SBATCH_PARTITION')or('shared'if self.site_name=='expanse'else'')
        return [p for p in v.split(',')if p]
    def account(self,role:str='array')->str|None:
        v=None
        for n,x in self.opts(role):
            if n in('account','A'):v=x
        return v or self.env.get('SBATCH_ACCOUNT')or self.env.get('C8_ACCOUNT')or('yun124'if self.site_name=='expanse'else None)
    def selection(self,role:str='array')->list[str]:
        """The account and partition admission and the ledger use for this role, as explicit sbatch options (X12): the
        resolved partition list (user option, SBATCH_PARTITION, Expanse's 'shared') and account (user option,
        SBATCH_ACCOUNT, C8_ACCOUNT, Expanse's yun124). Every sbatch of the role gets them, so a selection that came from
        C8_ACCOUNT or a site default is the one the job is charged to and runs on, never the scheduler's default."""
        out=[];parts=self.partitions(role);acct=self.account(role)
        if parts:out.append('--partition='+','.join(parts))
        if acct:out.append(f'--account={acct}')
        return out
    def user_mem(self)->int|None:
        mem=None
        for n,x in self.opts():
            if n=='mem':mem=mem_mb(x)
            elif n=='mem-per-cpu':mem=mem_mb(x)*self.threads
        return mem
    def has_mem_option(self)->bool:return any(n in('mem','mem-per-cpu')for n,_ in self.opts())
    def check_time(self)->None:
        if self.policy!='unlimited':self.work_time()
    def work_time(self)->str:
        t=self.user_time or self.suggested
        if t is None:raise Refuse(64,'the plan has no wall-time estimate (first-sweep bootstrap or no cost basis); give --time in C8_SBATCH_ARGS or as an extra option')
        return t
    def time_args(self,kind)->list[str]:
        if self.policy=='unlimited':return['--time=0']
        return [f'--time={self.work_time()if kind=="array"else(self.user_time or(self.lane_time if kind=="lane"else self.merge_time))}']
    # ---- sbatch with ledger
    def sbatch_env(self,offset=None,args=None):
        """sbatch's environment: the inherited one without the SBATCH_* inputs outside SBATCH_ENV_ALLOWED, with C8_RUN,
        C8_PACKAGE and the window offset. Z7: for a job (args) whose script directives or command line set its memory,
        the inherited SBATCH_MEM_PER_CPU and SBATCH_MEM_PER_NODE are removed too (sbatch would reset them)."""
        e={k:v for k,v in self.env.items()if not(k.startswith('SBATCH_')and k not in SBATCH_ENV_ALLOWED)}
        if args is not None and memory_kinds(args,e)[0]:
            for k in MEM_ENV:e.pop(k,None)
        e.update(C8_RUN=str(self.run),C8_PACKAGE=str(ROOT))
        if offset is None:e.pop('C8_INDEX_OFFSET',None)
        else:e['C8_INDEX_OFFSET']=str(offset)
        return e
    def prepare(self,args,role,offset=None)->tuple[list,dict,dict]:
        """(the sbatch arguments, environment and effective options) of one job, checked against its role's contract:
        refuses (64) before the job exists. X12: the account and partition admission counted, explicitly: after the
        user's options (whose last values they repeat) and before the trailing time option and the script, so that
        --time stays the last option; check_effective verifies them."""
        tail=2 if len(args)>=2 and str(args[-2]).startswith('--time=')else 1
        args=[*args[:-tail],*self.selection(role),*args[-tail:]]
        env=self.sbatch_env(offset,args);eff=effective_options(args,env)
        self.check_effective(role,eff)  # CK-K01/O05/O04/X12/Z7
        return args,env,eff
    def preflight(self,jobs)->None:
        """Z7 (S6-C-R3-02): every job a submission will make, [(role, sbatch arguments, offset)], prepared and checked
        before the first sbatch, so that a contract only a later job (the merge) breaks refuses (64) with nothing
        submitted. The merge is checked with a placeholder dependency (the real one names jobs not submitted yet)."""
        for role,args,offset in jobs:self.prepare(args,role,offset)
    def sbatch(self,args,role,offset=None,**info):
        args,env,eff=self.prepare(args,role,offset)
        cp=subprocess.run(['sbatch','--parsable',*args],capture_output=True,text=True,env=env)
        if cp.returncode:raise Refuse(cp.returncode or 1,'sbatch failed: '+(cp.stderr or cp.stdout).strip()[-800:])
        jid=cp.stdout.strip().split(';')[0]
        if not jid.isdigit():raise Refuse(69,f'sbatch gave no job id ({cp.stdout.strip()[-200:]!r}); check squeue before resubmitting')
        self.ledger({'jobid':jid,'role':role,**({'offset':offset}if offset is not None else{}),**info},eff)
        self.submitted.append(jid)
        if self.policy=='unlimited':
            try:self.verify_unlimited(jid)
            except Refuse as r:raise Unverified(f'{r}. Jobs accepted in this submission so far: {", ".join(self.submitted)}',jid,role)from None
        return jid
    def check_effective(self,role:str,eff:dict)->None:
        """The role's resource contract on a job's effective options (script directives, SBATCH_* inputs, command line;
        CK-K01/O05), and the partition admission counted for the role (O04). Refuse (64), nothing submitted."""
        bad=[]
        def want(n,v):
            if str(eff.get(n))!=str(v):bad.append(f'{n} is {eff.get(n)!r}, the contract is {v}')
        if role in('lane','merge'):
            want('nodes',1);want('ntasks',1)
            if 'mem-per-cpu'in eff:bad.append(f'mem-per-cpu is set ({eff["mem-per-cpu"]}); a {role} takes its memory from C8_{role.upper()}_MEM only')
        if role=='lane':
            want('mem',self.lane_mem)
            if self.drill:
                if eff.get('exclusive'):bad.append('exclusive is set: a drill lane worker shares its node (an #SBATCH --exclusive directive, which no command-line option cancels, or an option)')
                want('cpus-per-task',self.lane_cpus)
                if not eff.get('no-requeue'):bad.append('no-requeue is missing (drill mode)')
            elif not eff.get('exclusive'):bad.append('exclusive is missing: a normal lane worker owns its whole node')
        elif role=='merge':
            want('cpus-per-task',self.merge_jobs);want('mem',self.merge_mem)
            if eff.get('exclusive'):bad.append('exclusive is set: a merge never takes a whole node')
            if self.drill and not eff.get('no-requeue'):bad.append('no-requeue is missing (drill mode)')
        elif eff.get('exclusive'):bad.append(f'exclusive is set on a {role} job')
        parts=[p for p in (eff.get('partition')or self.env.get('SBATCH_PARTITION')or('shared'if self.site_name=='expanse'else'')).split(',')if p]
        if parts!=self.partitions(role):bad.append(f'partition {",".join(parts)} differs from the {",".join(self.partitions(role))} admission counted')
        acct=self.account(role)  # X12: the account admission queried and the ledger records is the one the job is charged to
        if acct is not None and str(eff.get('account'))!=acct:bad.append(f'account is {eff.get("account")!r}, admission counted {acct}')
        if bad:raise Refuse(64,f'{role} job refused before submission: its effective options break the {role} contract: '+'; '.join(bad))
    def ledger(self,rec:dict,eff:dict|None=None)->None:
        """One ledger line; for a submitted job (eff: its effective options, checked by check_effective) the partition
        and account it was submitted with (X12), else the role's resolved selection."""
        role=rec.get('role')or'array'
        part=(eff.get('partition')if eff else None)or','.join(self.partitions(role))or None;acct=(eff.get('account')if eff else None)or self.account(role)
        line={'schema':LEDGER_SCHEMA,**rec,'site':self.site_name,'partition':part,'account':acct,'time':utc(),
              'source':'slurm_submit','host':socket.gethostname(),'admission_ref':self.admission_ref}
        with (self.run/'submissions.jsonl').open('a')as f:f.write(json.dumps(line,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    def job_state(self,jid:str)->str|None:
        """JobState of one job from `scontrol show job` (None when unknown)."""
        try:cp=subprocess.run(['scontrol','show','job',jid],capture_output=True,text=True,timeout=120,env={k:v for k,v in self.env.items()if not k.startswith(('SQUEUE_','SCONTROL_'))})
        except (OSError,subprocess.SubprocessError):return None
        m=re.search(r'JobState=(\S+)',cp.stdout)if cp.returncode==0 else None
        return m.group(1)if m else None
    def cancel_if_pending(self,jid:str)->dict:
        """Cancel a superseded merge only while the scheduler still holds it PENDING (O08): `scontrol hold` keeps a pending
        job from starting and refuses one that started; the state is then read again (a job found started is released
        and left alone), and only then `scancel --state=PENDING` cancels it, the state read once more for the record.
        A snapshot taken earlier never decides. Returns the outcome (recorded in the ledger)."""
        env={k:v for k,v in self.env.items()if not k.startswith(('SQUEUE_','SCANCEL_','SCONTROL_'))}
        def run(cmd):
            try:return subprocess.run(cmd,capture_output=True,text=True,timeout=120,env=env)
            except (OSError,subprocess.SubprocessError)as e:return subprocess.CompletedProcess(cmd,127,'',str(e))
        h=run(['scontrol','hold',jid])
        if h.returncode:
            return {'held':False,'cancelled':False,'scontrol_hold_exit':h.returncode,
                    'outcome':f'not pending any more (scontrol hold refused: {(h.stderr or h.stdout).strip()[-200:] or "exit "+str(h.returncode)}); left alone'}
        st=self.job_state(jid)
        if st!='PENDING':
            r=run(['scontrol','release',jid])
            return {'held':True,'cancelled':False,'state':st,'scontrol_release_exit':r.returncode,'outcome':f'{st} when held; hold released, left alone'}
        c=run(['scancel','--state=PENDING',jid]);after=self.job_state(jid)
        done=after in(None,'CANCELLED')and c.returncode==0
        return {'held':True,'cancelled':done,'scancel_exit':c.returncode,'state_after':after,
                'outcome':'cancelled while pending (held, then scancel --state=PENDING)'if done else
                          f'held but not cancelled (scancel exit {c.returncode}, state {after}); scancel {jid} by hand'}
    def verify_unlimited(self,jid):
        cp=subprocess.run(['scontrol','show','job',jid],capture_output=True,text=True,env={k:v for k,v in self.env.items()if not k.startswith('SQUEUE_')})
        limits=re.findall(r'TimeLimit=(\S+)',cp.stdout)
        if cp.returncode or not limits or any(x!='UNLIMITED'for x in limits):
            seen=','.join(sorted(set(limits)))or'unknown (scontrol failed)'
            raise Refuse(70,f'job {jid} was accepted with TimeLimit={seen}, not UNLIMITED, although C8_TIME_POLICY=unlimited submitted --time=0. '
                            f'It was NOT cancelled and nothing further was submitted: inspect it (scontrol show job {jid}) and scancel it yourself if needed')
    # ---- the three job kinds: their sbatch arguments (also used by preflight) and their submission
    def work_args(self,offset,array)->list:
        ids=expand(array)
        if any(offset+i>=self.jobs for i in ids)or any(i>=self.max_array for i in ids):raise Refuse(64,f'window {offset}:{array} is outside the plan ({self.jobs} jobs) or wider than C8_MAX_ARRAY')
        mem=[]if self.has_mem_option()else[f'--mem={self.mem_suggestion}M']
        return [*self.site,f'--cpus-per-task={self.threads}',*mem,*self.extra,'--nodes=1','--ntasks=1',f'--array={array}%{self.throttle}',
                f'--output={self.logpat}/work-%A_%a.log',f'--comment={self.tag}:off={offset}',f'--job-name={JOB_NAMES["array"]}','--export=ALL',
                *self.time_args('array'),str(ROOT/'slurm/run_array.sh')]
    def lane_args(self)->list:
        shape=(['--nodes=1','--ntasks=1',f'--cpus-per-task={self.lane_cpus}',f'--mem={self.lane_mem}','--no-requeue']if self.drill
               else['--exclusive','--nodes=1','--ntasks=1',f'--mem={self.lane_mem}'])
        return [*self.site,*self.extra,*shape,f'--output={self.logpat}/lane-%j.log',f'--comment={self.tag}:lane',f'--job-name={JOB_NAMES["lane"]}','--export=ALL',
                *self.time_args('lane'),str(ROOT/'slurm/lane_worker.sh')]
    def merge_args(self,deps,kind='afterok')->list:
        # The merge's memory, CPUs and name are its own (C8_MERGE_MEM, C8_MERGE_JOBS), never the work jobs' options; its
        # time is time_args('merge'); its partition, account and every other user option are the ones admission counted
        # for it (O04).
        return [*self.user_tokens('merge'),'--nodes=1','--ntasks=1',f'--cpus-per-task={self.merge_jobs}',f'--mem={self.merge_mem}']+(['--no-requeue']if self.drill else[])+\
               ([f'--dependency={kind}:{":".join(deps)}']if deps else[])+[f'--output={self.logpat}/merge-%j.log',f'--comment={self.tag}:merge',f'--job-name={JOB_NAMES["merge"]}',
                                                                        '--export=ALL',*self.time_args('merge'),str(ROOT/'slurm/merge.sh')]
    def work(self,offset,array):
        args=self.work_args(offset,array);self.logs.mkdir(parents=True,exist_ok=True)
        jid=self.sbatch(args,'array',offset,elements=len(expand(array)),array=array)
        print(f'array {jid}: C8_INDEX_OFFSET={offset}, indices {array} (%{self.throttle}); logs {self.logs}/work-{jid}_<i>.log',flush=True);return jid
    def lane(self):
        args=self.lane_args();self.logs.mkdir(parents=True,exist_ok=True)
        jid=self.sbatch(args,'lane',drill=self.drill)
        print(f'lane worker {jid}{" (drill mode)"if self.drill else""}; log {self.logs}/lane-{jid}.log',flush=True);return jid
    def merge(self,deps,kind='afterok'):
        args=self.merge_args(deps,kind);self.logs.mkdir(parents=True,exist_ok=True)
        mid=self.sbatch(args,'merge',dependency=(f'{kind}:{":".join(deps)}'if deps else None))
        print(f'merge {mid} '+(f'({kind}:{":".join(deps)})'if deps else'(no dependency)')+f'; log {self.logs}/merge-{mid}.log',flush=True);return mid

# ---------------------------------------------------------------- admission (R12, H7, H7E-R)
# The job name is the only free-text field (a user may put '|' in it), so it comes last and the line is split at the
# first six '|': job id, state, partitions, QOS, node count and user never contain one.
SQUEUE_ADMISSION_FORMAT='%i|%T|%P|%q|%D|%u|%j'
def _squeue_records(env,args)->list[dict]:
    """Admission snapshot. A line that does not parse refuses admission (fail closed); it is never skipped."""
    e={k:v for k,v in env.items()if not k.startswith('SQUEUE_')}
    try:cp=subprocess.run(['squeue',*args,'-h','-r','-o',SQUEUE_ADMISSION_FORMAT],capture_output=True,text=True,env=e,timeout=300)
    except (OSError,subprocess.SubprocessError):cp=None
    if cp is None or cp.returncode:raise Refuse(69,'squeue failed during admission; nothing submitted')
    out=[]
    for line in cp.stdout.splitlines():
        if not line.strip():continue
        f=[x.strip()for x in line.split('|',6)]
        if len(f)!=7 or not all(f[i]for i in (0,1,2,5)):
            raise Refuse(69,f'admission refused: squeue line does not parse as {SQUEUE_ADMISSION_FORMAT!r} (7 fields; job id, state, partition '
                            f'and user non-empty): {line[:300]!r}; nothing submitted')
        jid,state,part,qos,nodes,user,name=f
        out.append({'jobid':jid,'name':name,'state':state,'partitions':[p for p in part.split(',')if p],'qos':qos,'nodes':int(nodes)if nodes.isdigit()else 1,'user':user})
    return out

def live(r)->bool:return r['state']in prod.LIVE_STATES or r['state']in RUNNING_LIKE

def admission(c:Context,items:list,unit:str)->dict:
    """Admit the new jobs `items` = [(role, count)], each counted on the partitions of its OWN role's effective options
    (O04: a merge with another partition than its workers is counted there), or refuse (65), printing the largest
    admissible count. unit: 'lanes' (items: N lane workers and one merge; print N) or 'jobs'."""
    new=[(role,int(n),c.partitions(role))for role,n in items];k=sum(n for _,n,_ in new)
    parts=sorted({p for _,n,ps in new if n for p in ps})
    rec={'k':k,'partitions':parts,'site':c.site_name,'new_jobs':{role:{'count':n,'partitions':ps}for role,n,ps in new}};limits=[]
    def on(pred)->dict:return {role:(n if pred(ps)else 0)for role,n,ps in new}  # new jobs per role in one category
    if c.site_name=='expanse':
        accts=sorted({c.account(role)or''for role,n,_ in new if n})
        if '' in accts:raise Refuse(64,'C8_SITE=expanse needs an account (-A in C8_SBATCH_ARGS or C8_ACCOUNT)')
        if len(accts)!=1:raise Refuse(64,f'the new jobs of this submission name different accounts ({", ".join(accts)}); one submission charges one account')
        acct=accts[0]
        snap=_squeue_records(c.env,['-A',acct]);me=scheduler_user()
        mine=[r for r in snap if r['user']==me and r['name'].startswith('c8d2-')and live(r)]
        acc_run=sum(1 for r in snap if r['qos']=='normal'and r['state']in RUNNING_LIKE)
        my_run=sum(1 for r in mine if r['qos']=='normal'and r['state']in RUNNING_LIKE);my_sub=sum(1 for r in mine if r['qos']=='normal')
        my_shared=sum(1 for r in mine if 'shared'in r['partitions']);my_nodes=sum(r['nodes']for r in mine if set(r['partitions'])&EXPANSE_NODE_PARTITIONS)
        rec.update(account=acct,account_running_normal=acc_run,my_running_normal=my_run,my_submitted_normal=my_sub,my_shared_live=my_shared,my_compute_nodes_live=my_nodes,
                   caps=c.caps,admission_ref=c.admission_ref)
        normal=on(lambda ps:'compute'in ps)
        limits+=[('c8d2 running normal-QOS',c.caps['C8_EXP_RUNNING']-my_run,normal),('c8d2 submitted normal-QOS',c.caps['C8_EXP_SUBMITTED']-my_sub,normal),
                 ('yun124 running normal-QOS',c.caps['C8_EXP_ACCOUNT_RUNNING']-acc_run,normal),
                 ('c8d2 compute nodes',c.caps['C8_EXP_NODES']-my_nodes,on(lambda ps:bool(set(ps)&EXPANSE_NODE_PARTITIONS))),
                 ('c8d2 shared-partition jobs',c.caps['C8_EXP_SHARED']-my_shared,on(lambda ps:'shared'in ps))]
    if c.amd_cap is not None:
        snap=_squeue_records(c.env,['-u',scheduler_user()])
        amd=[r for r in snap if r['name'].startswith('c8d2-')and live(r)and set(r['partitions'])&AMD_PARTITIONS]
        rec.update(amd_cap=c.amd_cap,amd_live=len(amd),amd_live_jobs=[r['jobid']for r in amd])
        limits.append(('c8d2 AMD-pool jobs (amdq, amddebugq, amdpreq)',c.amd_cap-len(amd),on(lambda ps:bool(set(ps)&AMD_PARTITIONS))))
    limits=[(name,room,cnt)for name,room,cnt in limits if any(cnt.values())]  # a category none of the new jobs lands in
    room=min((v for _,v,_ in limits),default=None);rec['room']=room
    rec['limits']={name:{'room':v,'new':sum(cnt.values())}for name,v,cnt in limits}
    print('C8: admission '+json.dumps(rec,sort_keys=True),flush=True)
    over=[(name,v,cnt)for name,v,cnt in limits if sum(cnt.values())>v]
    if over:
        if unit=='lanes':  # the largest N whose N lane workers and one merge fit every category the workers land in
            best=min([v-cnt.get('merge',0)for _,v,cnt in limits if cnt.get('lane')]+[10**9])
            if any(v<cnt.get('merge',0)for _,v,cnt in limits):best=-1
            best=max(-1,min(best,sum(n for role,n,_ in new if role=='lane')))
        else:best=max(0,min(v for _,v,_ in limits))
        why='; '.join(f'{n}: room {v}'for n,v,_ in limits)
        raise Refuse(65,f'admission refused: {k} new job(s) on {",".join(parts)} exceed the budget ({why}). Largest admissible '
                        +(f'N for lanes N: {best}'if unit=='lanes'else f'job count: {best}')+('; nothing submitted'))
    return rec

def site_lock(c:Context):
    if c.site_name=='expanse'or c.amd_cap is not None:
        d=Path(c.env.get('C8_SITE_LOCK_DIR')or c.env.get('HOME')or str(Path.home()))
        return DirLock(d/f'.c8_site_{c.site_name}.lock',f'admission for {c.run}','admission on this site')
    return _NoLock()

class _NoLock:
    def __enter__(self):return self
    def __exit__(self,*a):return False

def preview(c:Context,args_for_test:list|None=None)->None:
    """Idle nodes of each requested partition and sbatch --test-only's start estimate (informational, never a gate)."""
    e={k:v for k,v in c.env.items()if not k.startswith('SQUEUE_')}
    for p in c.partitions():
        try:
            cp=subprocess.run(['sinfo','-h','-p',p,'-t','idle','-o','%D'],capture_output=True,text=True,env=e,timeout=60)
            n=sum(int(x)for x in cp.stdout.split()if x.isdigit())if cp.returncode==0 else'unknown'
        except (OSError,subprocess.SubprocessError):n='unknown'
        print(f'C8: partition {p}: {n} idle node(s)',flush=True)
    if args_for_test:
        try:
            cp=subprocess.run(['sbatch','--test-only',*args_for_test],capture_output=True,text=True,env=c.sbatch_env(None,args_for_test),timeout=120)
            msg=(cp.stderr or cp.stdout).strip().splitlines()
            print('C8: sbatch --test-only: '+(msg[-1]if msg else f'exit {cp.returncode}'),flush=True)
        except (OSError,subprocess.SubprocessError)as x:print(f'C8: sbatch --test-only unavailable ({x})',flush=True)

# ---------------------------------------------------------------- the entry points
def queue(c:Context)->dict:
    q=prod.queue_state(c.run,snapshot(c.env))
    if q['refuse']:raise Refuse(q['refuse']['code'],q['refuse']['message'])
    return q

def lanes_command(c:Context,n:int)->int:
    if c.has_mem_option():raise Refuse(64,'lane mode takes --mem only from C8_LANE_MEM (workers) and C8_MERGE_MEM (merges); remove --mem from C8_SBATCH_ARGS and the extra options')
    run=c.run;m,_,_,_=prod.verify_base(run,check_executable=False)
    lanes.queue_entries(run,m,{j['id']:(0,1)for j in m['jobs']})  # refuses (64) plans without per-index estimates
    text=snapshot(c.env);t=time.time();q=prod.queue_state(run,text)
    if q['refuse']:raise Refuse(q['refuse']['code'],q['refuse']['message'])
    if q['live_work']:raise Refuse(65,f'array element(s) {",".join(sorted({w["jobid"]for w in q["live_work"]}))} of this campaign are live: lane mode and array mode are not mixed. '
                                       'Wait for them, or use slurm/resubmit.sh')
    d=lanes.release_stale(run,text,t)
    for idx,job,st in d['release']:print(f'C8: released stale claim of index {idx} (job {job}, {st})')
    entries,bad=lanes.rebuild_queue(run,m)
    if bad:print(f'C8: done markers removed for incomplete indices {prod.ranges(bad)} (lanes/done_invalidated.jsonl)')
    if not entries:print('C8: every index is complete; submitting only the merge')
    elif n==0:print('C8: --lanes 0: no new workers; submitting a merge that waits for the live lane workers')
    print(f'C8: queue {lanes.lanes_dir(run)/"queue.txt"}: {len(entries)} incomplete indices, {sum(e for _,e in entries)/3600:.1f} estimated core-hours')
    nw=n if entries else 0;deps=list(q['live_lanes']);old=[j for j in q['live_merges']]
    c.preflight(([('lane',c.lane_args(),None)]if nw else[])+[('merge',c.merge_args(sorted(set(deps))or['0'],'afterany'),None)])  # Z7: before any sbatch
    with site_lock(c):
        admission(c,[('lane',nw),('merge',1)],'lanes')
        preview(c,[*c.site,*c.extra,'--exclusive'if not c.drill else'--no-requeue','--nodes=1','--ntasks=1','--job-name=c8d2-lanes',*c.time_args('lane'),*c.selection('lane'),
                   str(ROOT/'slurm/lane_worker.sh')]if nw else None)
        new=[];failure=None
        for _ in range(nw):
            try:new.append(c.lane())
            except Refuse as r:failure=r;break
        if isinstance(failure,Unverified):
            # O07: a worker sbatch accepted without the verification stops everything at once: no further worker, no merge
            # (it would not wait for that worker), no cancellation.
            raise Refuse(70,f'{failure}. Submission stopped: no merge was submitted and no superseded merge was cancelled. Lane workers accepted now: '
                            f'{", ".join(new+[failure.jobid])} (job {failure.jobid} unverified); live before: {", ".join(sorted(set(deps)))or"none"}. Inspect '
                            f'job {failure.jobid} (scontrol show job {failure.jobid}; scancel it if its limit is wrong), then run slurm/submit.sh --lanes 0: '
                            'its merge waits (afterany) on every live lane worker of the campaign, these included')
        if failure and not(deps or new):raise failure
        try:mid=c.merge(sorted(set(deps))+new,'afterany')
        except Unverified as r:
            raise Refuse(70,f'{r}. Submission stopped: merge {r.jobid} was accepted and waits (afterany) on lane worker(s) {",".join(sorted(set(deps))+new)or"none"}; '
                            'no superseded merge was cancelled. Inspect it; if you cancel it, slurm/submit.sh --lanes 0 submits a merge on every live lane worker')from None
        except Refuse as r:
            alive=sorted(set(deps))+new
            raise Refuse(r.code,f'{r}; lane worker(s) {",".join(alive)} are live without a new merge: once the problem is fixed, run slurm/submit.sh --lanes 0 to submit one')if alive else r
    # Only now that the new merge is accepted: cancel every superseded merge, but only while the scheduler still holds it
    # PENDING (O08; the snapshot state above is old by now). One that started finds the campaign incomplete (exit 65) or
    # merges it, and is left alone.
    for jid in old:
        st=q['merge_states'].get(jid)
        if st=='PENDING':
            out=c.cancel_if_pending(jid)
            c.ledger({'type':'note','jobid':jid,'role':'merge','note':f'superseded by merge {mid}: {out["outcome"]}','cancel':out})
            print(f'C8: superseded merge {jid}: {out["outcome"]}'+('; it stays counted by admission until squeue shows it gone'if out['cancelled']else''))
        else:print(f'C8: superseded merge {jid} is {st}; left alone (the new merge {mid} covers it)')
    if failure:raise Refuse(failure.code,f'{failure}; {len(new)} of {nw} lane workers were submitted, and merge {mid} waits for them and for {len(set(deps))} live worker(s)')
    print(f'status: {sys.executable} {ROOT/"tools/production.py"} status {run}   (more workers: slurm/submit.sh --lanes N)');return 0

def main(argv,env)->int:
    if not argv or argv[0]not in('submit','window','resubmit','lanes'):print(__doc__,file=sys.stderr);return 64
    cmd=argv[0];rest=argv[1:]
    try:
        if cmd=='lanes':
            if not rest or not rest[0].isdigit():raise Refuse(64,'usage: lanes N [sbatch options] (N lane worker jobs; 0: only a merge on the live workers)')
            c=Context(env,rest[1:])
            with CampaignLock(c.run,'lanes '+rest[0]):return lanes_command(c,int(rest[0]))
        if cmd=='window':
            if not rest or ':'not in rest[0]:raise Refuse(64,'usage: window OFFSET:ARRAY [sbatch options]')
            off,_,arr=rest[0].partition(':')
            if not off.isdigit():raise Refuse(64,f'invalid window offset {off!r}')
            c=Context(env,rest[1:]);ids=[int(off)+i for i in expand(arr)]
            if any(i>=c.jobs for i in ids)or any(i>=c.max_array for i in expand(arr)):raise Refuse(64,f'window {rest[0]} is outside the plan ({c.jobs} jobs) or wider than C8_MAX_ARRAY')
            check_array_mem(c);c.check_time()
            with CampaignLock(c.run,'window '+rest[0]):
                q=queue(c)
                if q['live_merges']:raise Refuse(65,f'merge job(s) {",".join(q["live_merges"])} of this campaign are live; scancel them first, or use slurm/resubmit.sh')
                if q['live_lanes']:raise Refuse(65,f'lane worker job(s) {",".join(q["live_lanes"])} of this campaign are live: lane mode and array mode are not mixed')
                live_=sorted(set(ids)&set(q['live_indices']))
                if live_:raise Refuse(65,f'indices {prod.ranges(live_)} of this window are still queued or running; nothing submitted. Wait for them, or run slurm/resubmit.sh, which resubmits only indices that are not live')
                missing=set(prod.status_report(c.run,(),c.max_array,fingerprints=False,verify_db=False)['missing_jobs']);todo=[i for i in ids if i in missing];done=[i for i in ids if i not in missing]
                if done:print(f'C8: skipping indices {prod.ranges(done)}: every block is committed')
                if not todo:print('C8: nothing to submit: every block of this window is committed');return 0
                c.preflight([('array',c.work_args(int(off),prod.ranges([i-int(off)for i in todo])),int(off))])  # Z7
                with site_lock(c):
                    admission(c,[('array',len(todo))],'jobs');preview(c)
                    c.work(int(off),prod.ranges([i-int(off)for i in todo]))
            print('C8: submit the merge once the campaign is complete (slurm/resubmit.sh does both and waits on live work)');return 0
        c=Context(env,rest);check_array_mem(c)
        with CampaignLock(c.run,cmd):
            if cmd=='submit':
                q=queue(c)
                if q['live_work']or q['live_merges']or q['live_lanes']:
                    raise Refuse(65,f'this campaign already has live jobs (indices {prod.ranges(q["live_indices"])or"none"}; merges {",".join(q["live_merges"])or"none"}; '
                                    f'lane workers {",".join(q["live_lanes"])or"none"}); nothing submitted. Use slurm/resubmit.sh (arrays) or slurm/submit.sh --lanes N (lanes)')
                st=prod.status_report(c.run,(),c.max_array,fingerprints=False,verify_db=False)
                if not st['missing_jobs']:print('C8: nothing to submit: every checkpoint block is committed (slurm/resubmit.sh submits a merge-only job)');return 0
                c.check_time()
                c.preflight([('array',c.work_args(w['offset'],w['array']),w['offset'])for w in st['resubmit']]+[('merge',c.merge_args(['0']),None)])  # Z7: before any sbatch
                with site_lock(c):
                    admission(c,[('array',len(st['missing_jobs'])),('merge',1)],'jobs');preview(c)
                    ids=[c.work(w['offset'],w['array'])for w in st['resubmit']]  # an unverified array (70) stops here, no merge (O07)
                    try:c.merge(ids)
                    except Unverified as r:raise Refuse(70,f'{r}. Submission stopped: merge {r.jobid} was accepted and waits (afterok) on work array(s) {",".join(ids)}')from None
                    except Refuse as r:raise Refuse(r.code,f'{r}; work array(s) {",".join(ids)} are live without a merge: once the problem is fixed, run slurm/resubmit.sh (it submits a merge that waits for them)')
                print(f'status: {sys.executable} {ROOT/"tools/production.py"} status {c.run}   (recovery: slurm/resubmit.sh)');return 0
            d=prod.recovery_plan(c.run,snapshot(env),c.max_array)
            if d['refuse']:raise Refuse(d['refuse']['code'],d['refuse']['message'])
            if d['live_missing_not_resubmitted']:print(f'C8: missing indices {prod.ranges(d["live_missing_not_resubmitted"])} are still live; not resubmitted')
            k=sum(len(expand(w['array']))for w in d['arrays'])
            if d['arrays']:c.check_time()
            c.preflight([('array',c.work_args(w['offset'],w['array']),w['offset'])for w in d['arrays']]+[('merge',c.merge_args(['0']),None)])  # Z7: before any sbatch
            with site_lock(c):
                admission(c,[('array',k),('merge',1)],'jobs');preview(c)
                ids=[c.work(w['offset'],w['array'])for w in d['arrays']]+d['merge_waits_on_live_tasks']
                if not ids:print('C8: no work to resubmit and no live elements; submitting the merge only')
                c.merge(ids)
            return 0
    except Refuse as r:
        print('C8: '+str(r),file=sys.stderr);return r.code

def check_array_mem(c:Context)->None:
    """Array elements take the plan's memory suggestion; a user --mem below it is refused (64), a larger one is used."""
    um=c.user_mem()
    if um is not None and um<c.mem_suggestion:
        raise Refuse(64,f'--mem of {um} MB is below the plan\'s suggestion of {c.mem_suggestion} MB (1.5 x the largest est_peak_bytes + 1 GiB); raise it or remove it')

if __name__=='__main__':sys.exit(main(sys.argv[1:],dict(os.environ)))
