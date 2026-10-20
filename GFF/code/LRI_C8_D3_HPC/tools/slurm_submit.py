#!/usr/bin/env python3
"""The single guarded path for every Slurm submission of LRI_C8_D3_HPC (plan D.11; host decisions H-e, H-f, H-g, H-h).

  slurm_submit.py raw --role ROLE --dir DIR -- <sbatch options> [--wrap CMD | SCRIPT]
        every directly submitted job (validation, generation, plans, reports, profiles, sweeps, drills)

Admission, under the session lock ($C8_ROOT/locks/c8d3.lock, tools/ledger.py), in this order (D.11):
  1. snapshot: `squeue --all -A yun124 -r` (live states), `squeue --all -u zzheng8 -r --states=all -O ...`, then the two
     `sacct` queries of the budget (tools/budget.py); a failed or timed-out query refuses (69);
  2. ledger record check (a torn final record is truncated after its bytes are kept; anything else refuses, 69), the
     intents of both copies evaluated against the snapshot (each resolved by evidence gets its `resolution` record and
     its file renamed), then every c8d3- job no record names is adopted (an unattributable one refuses, 69);
  3. the shares of C8_RESERVATION (H7E-R: live c8d3- normal-QOS jobs + k <= run, non-terminal + k <= sub, account
     running + own pending + k <= acct_run, C8_COMPUTE_CAP nodes, live c8d3- shared jobs + k <= shared, debug <= 2 per
     account) and the detectors, with every unresolved intent counted as HD17 "Slots" states (65 on refusal);
  4. the SU gate of the line C8_BUDGET_LINE: this site's hard sub-cap from its own ledger and scheduler, no carry (dev:
     budget.SITE_CAPS, 2,500 each on Expanse and symmetry, S2-004), then the joint checks with the other site's carry
     C8_OTHER_SITE_SU, soft (dev: 4,000 without C8_SU_APPROVED, 5,000 always; pilot: C8_PILOT_SU_CAP; production:
     C8_PRODUCTION_SU_CAP); every --time
     is priced (and submitted) normalized up to whole minutes, what Slurm reserves (S2-003);
  5. per job: the intent (ledger record, then intents/<T>.json), the 60 s age check, then
     `timeout -s KILL 120 slurm/exec_guard.sh <utc+60> sbatch --parsable ...` with the token T in name and comment;
  6. one `submit` record per job;  7. a re-snapshot (pending normal-QOS jobs of the call cancelled on a violation, 65).
Every job is named c8d3-<role>-<C>-<T> with the comment c8d3:<C>:<P>:<T> and carries --no-requeue.

Campaign entry points (Stage 3a; C8_RUN = a planned campaign under $C8_ROOT/runs/, verified with its pinned tools):
  slurm_submit.py lanes N [--dry-run] [sbatch options]   N whole-node lane workers (compute, --exclusive) and one merge
        (shared, afterany on every live worker); a repeated `lanes N` releases stale claims, rebuilds the queue, cancels
        the superseded pending merge only after the re-snapshot passes; `lanes 0` submits a merge on the live workers.
        --dry-run prints the admission snapshot, the derived lane time, the reservation, the merge path and the
        projected line total and what the line admits, and submits nothing. Lane mode refuses (65) every plan that is
        not of role campaign on the measured basis (D.5). C8_LANE_TIME: auto (default, D.10) or an explicit time.
  slurm_submit.py submit [sbatch options]     array mode: windows of <= C8_MAX_ARRAY indices throttled %C8_THROTTLE (8)
        and an afterok merge; refused while lane workers of the campaign are live
  slurm_submit.py window OFF:RANGE            one array window (the form `production.py status` prints), no merge
  slurm_submit.py resubmit                    array-mode recovery (production.recovery_plan): the missing indices that
        are not live, and a merge afterok on them and on every live element
  slurm_submit.py release JOBID               a held lane worker or array task pending with `launch failed requeued
        held` (F40) is released once under the session lock: a missing or unusable ledger refuses before any scheduler
        call, a release_attempt record is fsynced before the scontrol `release` command, an ambiguous outcome counts as
        the attempt, and the result is reconciled with squeue (S2-006); a second hold is cancelled (lanes N
        resubmits); any other held c8d3- job is reported and left alone (D.9)
  Every campaign entry point checks the campaign's one CPU vendor (RUN/cpu_vendor.json, pinned exclusively under the
  lock at its first work admission, before the first sbatch; the new jobs and every live job of the campaign; 64
  otherwise; S2-001).
The inherited C7(3) code of these entry points (quarantined in c7_legacy/ during Stages 0-2) is deleted.

Sites (Amendment A1). Expanse is the description above. Under C8_SITE=symmetry (user zzheng1, no -A or -A zzheng1):
  * partitions amdq, amddebugq (AMD, 64 cores, 245G) and defq, debugq (Intel, 80 CPUs, 180G), one per job; longq is
    always refused, preq and amdpreq too (preemptible with REQUEUE, while every job carries --no-requeue), every other
    partition as well; every AMD-pool job gets --exclude=cn112 plus the CPU pin's nodes (amd_exclusions: the AMD nodes
    known not to be EPYC 7543, budget.SYMMETRY.cpu_exclude, and C8_AMD_EXCLUDE_EXTRA), merged into its own --exclude; a
    --nodelist naming any of them is refused (64): cn112 is AVX-512, and the bitwise gates hold on the AVX2 nodes
    only; the CPU pin keeps every AMD job on the cost model's CPU (HD11; one CPU model per speed measurement and per
    campaign; slurm/site.sh c8_cpu_guard stops, 68, a job that lands on another CPU anyway);
  * the snapshots are `squeue --all -u zzheng1 ...` in the same formats (Slurm 21.08 prints them alike), then the same
    two `sacct` queries;
  * the caps (H7, DECISIONS A5 and the 2026-10-05 H11 line): C8_RESERVATION="mode=reservation;id=H7;amd_nodes=4;
    amd_total=8" (base split) or a pilot re-split with its DECISIONS id and ;until=<UTC> (amd_nodes=5 for the pilot
    session, 3 for the other, amd_total=8): live c8d3- AMD-pool nodes (amdq + amddebugq + amdpreq, pending included) +
    unresolved intents + k <= amd_nodes (and C8_COMPUTE_CAP), and with the live c8d2- AMD-pool nodes <= amd_total;
    Intel defq/debugq jobs are outside the cap;
  * the unit is the allocated core-hour (whole nodes: 64 per AMD node, 80 per Intel node, or the record's allocated
    cpu when larger), counted 1:1 with Expanse SU in the same lines and caps (A1.3); C8_OTHER_SITE_SU carries the other
    site's own line totals (its budget.py `carry` line, at most 24 h old) and is required on both real sites (Expanse
    too); every intent and submit record names its site and unit;
  * Intel defq/debugq (AVX-512, like cn112) admit raw jobs only under the roles intel_* and drill_* (validation, bitwise
    gates, replays, builds, plans and reports run on the AMD AVX2 pool), array windows and merges (submit, window,
    resubmit) only for a plan of role campaign (validation, cost_sweep, cost_refresh and flag_check plans run on the AMD
    pool), and a campaign's merge must be on its workers' CPU vendor (64 otherwise; one vendor per campaign);
  * the session lock lives on the NFS home (/home/zzheng1/c8d3/locks; BeeGFS flock() is node-local there) and is refused
    (69) unless that mount is NFS with local_lock=none (tools/ledger.py; Amendment A1 addendum L).

Environment: C8_SITE, C8_ROOT, C8_BUDGET_LINE (dev|pilot|production; the tool prefixes every role pilot_ or prod_,
budget.LINE_PREFIX), C8_RESERVATION, C8_COMPUTE_CAP, C8_SU_APPROVED, C8_PILOT_SU_CAP, C8_PRODUCTION_SU_CAP, C8_LOCK_WAIT, C8_OTHER_SITE_SU, C8_AMD_EXCLUDE_EXTRA (symmetry: cnNNN[,cnNNN], more AMD nodes to exclude); C8_TEST_FAULT (kill_after_sbatch, kill_during_launch: drill_* roles on shared or debug
only; symmetry amddebugq or debugq). Exit codes: 64 invalid input, 65 refused by admission or the SU gate, 69 unknown state, 74 ledger or intent
write failure, 75 the session lock is held.
"""
from __future__ import annotations
import calendar,hashlib,json,math,os,re,shlex,signal,socket,subprocess,sys,time
from dataclasses import dataclass,field
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse
import budget,ledger

EXEC_GUARD=ROOT/'slurm'/'exec_guard.sh'
SBATCH_KILL_AFTER=120     # `timeout -s KILL 120 sbatch ...` (D.11 step 5)
AGE_LIMIT=60              # seconds from the intent's monotonic stamp to the launch (age check and exec guard)
LAUNCH_BACKSTOP=180       # Python-side backstop above the 120 s KILL; never reached in practice
DEBUG_LIMIT=2
DEFAULT_SHARED=32
ROLE_RE=re.compile(r'[a-z][a-z0-9_]{0,31}')
GUARD_LATE='c8d3-exec-guard: late'
TIMEOUT_FAILED='timeout: failed to run command'   # coreutils timeout could not exec its command (exit 125/126/127): nothing ran
# stderr of an sbatch that exited by itself, non-zero, before any job could exist (an option error raised before any
# request, or a slurmctld refusal): HD17 (b). Anything else (a socket timeout, a lost connection) is ambiguous.
REJECTIONS=('Invalid account or account/partition combination specified','Job violates accounting/QOS policy',
            'Requested node configuration is not available','Invalid partition name specified','Invalid qos specification',
            'Requested time limit is invalid','sbatch: unrecognized option','sbatch: invalid option','Unable to open file')
AMBIGUOUS=('timed out','Socket','Unable to contact','Connection','connection','Zero Bytes','retry','Communication')
PARTITIONS=budget.EXPANSE.partitions   # Expanse's admitted partitions; symmetry's are budget.SYMMETRY.partitions (Amendment A1)
FAULTS=('kill_after_sbatch','kill_during_launch')
STANDIN=['sh','-c','trap "" TERM HUP INT; exec sleep 600']   # J-DRL-10's stand-in for sbatch
TOOL_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
# The package commit: an Expanse export lives at $C8_ROOT/pkg/<commit sha12> (a git archive, no .git); else C8_PACKAGE_COMMIT.
PACKAGE_COMMIT=ROOT.name if re.fullmatch(r'[0-9a-f]{12}',ROOT.name)else os.environ.get('C8_PACKAGE_COMMIT')

# ----------------------------------------------------------------------------------------------------------------
# sbatch options (D.11 "raw"): the campaign allowlist (without --begin) plus --wrap, -o, --nodes=1, --ntasks=1,
# --exclusive (compute only), --no-requeue and a script path. Exact spellings only (no getopt abbreviations).
LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user signal exclude nodelist licenses wckey output wrap nodes ntasks dependency'.split())
LONG_FLAG=frozenset(('exclusive','no-requeue'))
SHORT={'A':'account','p':'partition','q':'qos','C':'constraint','t':'time','c':'cpus-per-task','x':'exclude','w':'nodelist','L':'licenses','o':'output',
       'N':'nodes','n':'ntasks','d':'dependency'}
REFUSED={'array':'an array (raw submits single jobs; arrays come from the campaign entry points)','job-name':'a job name (the tool sets it)',
         'comment':'a comment (the tool sets it)','hold':'--hold (no job is ever submitted held, H-e)','begin':'--begin (a job waiting for its begin time is not eligible, HD17)',
         'requeue':'--requeue (every job carries --no-requeue, D.11)'}
REFUSED_SHORT={'a':'array','J':'job-name','H':'hold','b':'begin'}
RAW_ALLOW=(LONG_VALUE,LONG_FLAG,SHORT)
# The campaign allowlist (C8_SBATCH_ARGS, C8_MERGE_SBATCH_ARGS; D.11): the inherited one (a6ce987 production.py
# SBATCH_LONG_VALUE/SBATCH_LONG_FLAG/SBATCH_SHORT_VALUE) without --begin, --job-name/-J, --hold and --requeue. No --wrap,
# --output/-o, --dependency/-d, --nodes/-N, --ntasks/-n or --exclusive: the tool and the campaign scripts own those.
CAMPAIGN_LONG_VALUE=frozenset('account partition qos reservation constraint mem mem-per-cpu time cpus-per-task gres tmp mail-type mail-user signal exclude nodelist licenses wckey'.split())
CAMPAIGN_LONG_FLAG=frozenset(('no-requeue',))
CAMPAIGN_SHORT={k:v for k,v in SHORT.items()if k in 'ApqCtcxwL'}
CAMPAIGN_ALLOW=(CAMPAIGN_LONG_VALUE,CAMPAIGN_LONG_FLAG,CAMPAIGN_SHORT)
SBATCH_ENV={'SBATCH_ACCOUNT':'account','SBATCH_PARTITION':'partition','SBATCH_QOS':'qos','SBATCH_RESERVATION':'reservation','SBATCH_CONSTRAINT':'constraint',
            'SBATCH_MEM_PER_CPU':'mem-per-cpu','SBATCH_MEM_PER_NODE':'mem','SBATCH_TIMELIMIT':'time','SBATCH_WCKEY':'wckey','SBATCH_NO_REQUEUE':'no-requeue'}

def parse_options(tokens:list,what:str,positional=True,allow=RAW_ALLOW)->tuple[list,list]:
    """[(name, value or None)], [positional words]; refuses (64) anything outside the allowlist (raw's by default, or
    CAMPAIGN_ALLOW for the campaign option sets)."""
    long_value,long_flag,short=allow
    opts=[];pos=[];i=0;tokens=list(tokens)
    while i<len(tokens):
        tok=tokens[i]
        if tok.startswith('--')and len(tok)>2:
            name,eq,val=tok[2:].partition('=')
            if name in REFUSED:raise Refuse(64,f'{what}: {tok} refused: {REFUSED[name]}')
            if name in long_flag:
                if eq:raise Refuse(64,f'{what}: {tok} takes no value')
                opts.append((name,None));i+=1;continue
            if name not in long_value:raise Refuse(64,f'{what}: sbatch option {tok} is not allowed (allowed: --'+' --'.join(sorted(long_value|long_flag))+')')
            if not eq:
                if i+1>=len(tokens):raise Refuse(64,f'{what}: {tok} needs a value')
                val=tokens[i+1];i+=1
            opts.append((name,val));i+=1;continue
        if tok.startswith('-')and len(tok)>=2 and tok!='-':
            c=tok[1]
            if c in REFUSED_SHORT:raise Refuse(64,f'{what}: {tok} refused: {REFUSED[REFUSED_SHORT[c]]}')
            if c not in short:raise Refuse(64,f'{what}: sbatch option {tok} is not allowed (allowed: -'+' -'.join(sorted(short))+')')
            if len(tok)>2:val=tok[2:]
            else:
                if i+1>=len(tokens):raise Refuse(64,f'{what}: {tok} needs a value')
                val=tokens[i+1];i+=1
            opts.append((short[c],val));i+=1;continue
        if not positional:raise Refuse(64,f'{what}: unexpected word {tok!r} (only sbatch options are allowed)')
        pos.append(tok);i+=1
    return opts,pos

FOREIGN_DIRECTIVES=('#SLURM','#PBS','#BSUB')   # sbatch applies #SLURM like #SBATCH, and #PBS/#BSUB unless --ignore-pbs

def script_options(path:Path)->list:
    """The #SBATCH lines of a batch script, read as sbatch reads them, with the allowlist: a directive counts only at
    column 0 (an indented `#SBATCH` is a comment to sbatch), blank lines and comment lines (leading blanks allowed) are
    skipped, and the first command line ends the scan. A `#SLURM`, `#PBS` or `#BSUB` line anywhere in the script is
    refused (64): sbatch would apply it (time, hold, begin, array) without this tool pricing it. A script that is not
    UTF-8 is refused (64)."""
    try:data=path.read_bytes()
    except OSError as e:raise Refuse(64,f'cannot read the batch script {path}: {e}')
    try:text=data.decode('utf-8')
    except UnicodeDecodeError as e:raise Refuse(64,f'the batch script {path} is not UTF-8 ({e}); its directives cannot be checked')
    # sbatch itself refuses these two before any request; refusing here keeps them from becoming ambiguous submissions
    if not text.startswith('#!'):raise Refuse(64,f'the batch script {path} does not start with #! (sbatch refuses it)')
    if '\r\n'in text:raise Refuse(64,f'the batch script {path} has DOS line breaks (sbatch refuses it)')
    lines=text.split('\n')
    for n,line in enumerate(lines,1):
        if line.startswith(FOREIGN_DIRECTIVES):
            raise Refuse(64,f'{path}:{n}: {line.split()[0]} directives are refused (sbatch would apply them unpriced); use #SBATCH lines only')
    opts=[]
    for n,line in enumerate(lines,1):
        if line.startswith('#SBATCH'):
            try:toks=shlex.split(line[len('#SBATCH'):],comments=True)
            except ValueError as e:raise Refuse(64,f'{path}:{n}: cannot parse #SBATCH line: {e}')
            opts+=parse_options(toks,f'{path}:{n} (#SBATCH)',positional=False)[0];continue
        s=line.lstrip()
        if not s or s.startswith('#'):continue   # a blank or comment line (an indented #SBATCH included) does not end the scan
        break                                     # the first command line ends it, as in sbatch
    return opts

def env_options(env:dict)->list:
    if env.get('SBATCH_REQUEUE'):raise Refuse(64,'SBATCH_REQUEUE is set: every job carries --no-requeue (D.11); unset it')
    return [(o,env[k]if o!='no-requeue'else None)for k,o in SBATCH_ENV.items()if env.get(k)]

def sbatch_env(env:dict,extra:dict|None=None)->dict:
    """sbatch's environment: SBATCH_* inputs outside the allowlist are removed, so sbatch reads only what was priced."""
    e={k:v for k,v in env.items()if not(k.startswith('SBATCH_')and k not in SBATCH_ENV)}
    e.update(extra or{})
    return e

def site_profile(site)->budget.SiteProfile:
    """A SiteProfile, or the profile of a C8_SITE value (symmetry; anything else Expanse's, as the Mac fakes)."""
    if isinstance(site,budget.SiteProfile):return site
    return budget.SYMMETRY if site=='symmetry'else budget.EXPANSE

def hostlist_has(spec:str,node:str)->bool:
    """Whether a Slurm host list (cn100,cn112 or cn[100-112] forms) names `node`."""
    m=re.fullmatch(r'([a-z]+)(\d+)',node);name,num=m.group(1),int(m.group(2))
    for part in re.findall(r'[a-z]+\[[^\]]*\]|[^,]+',spec or''):
        b=re.fullmatch(r'([a-z]+)\[([^\]]*)\]',part.strip())
        if not b:
            if part.strip()==node:return True
            continue
        if b.group(1)!=name:continue
        for r in b.group(2).split(','):
            lo,_,hi=r.partition('-')
            if lo.isdigit()and int(lo)<=num<=int(hi if hi.isdigit()else lo):return True
    return False

NODE_RE=re.compile(r'cn[0-9]{3}')
def amd_exclusions(prof,env:dict)->list:
    """The nodes every AMD-pool job of the site excludes: [prof.exclude_amd] (cn112, AVX-512), then prof.cpu_exclude
    (the CPU pin: the AMD nodes known not to be the cost model's CPU, EPYC 7543; HD11), then C8_AMD_EXCLUDE_EXTRA
    (a comma list of cnNNN, nodes found later: a 68 refusal of slurm/site.sh c8_cpu_guard or a probe), duplicates dropped
    in first order. It can only add nodes. Refuses (64) a malformed item and any non-empty C8_AMD_EXCLUDE_EXTRA under
    the Expanse profile."""
    prof=site_profile(prof);extra=(env or{}).get('C8_AMD_EXCLUDE_EXTRA')
    if prof.name!='symmetry':
        if extra:raise Refuse(64,f'C8_AMD_EXCLUDE_EXTRA={extra!r}: C8_AMD_EXCLUDE_EXTRA applies to symmetry\'s AMD pool only')
        return []
    items=[]
    if extra is not None and extra!='':
        for x in extra.split(','):
            if not NODE_RE.fullmatch(x):raise Refuse(64,f'C8_AMD_EXCLUDE_EXTRA={extra!r}: item {x!r} is not a node name cnNNN (a comma list of cnNNN, no spaces)')
            items.append(x)
    out=[]
    for x in [prof.exclude_amd,*prof.cpu_exclude,*items]:
        if x and x not in out:out.append(x)
    return out

def resolve(script:list,envo:list,cmd:list,site,exclude:list|None=None)->dict:
    """HD17's option resolution, in sbatch's precedence (command line, then SBATCH_*, then #SBATCH lines), and the
    billing value of the resolved job. Refuses (64): both memory forms or neither, --mem=0, a missing time or partition.
    Expanse: --exclusive off compute, a partition other than compute/shared/debug, a missing -A yun124. symmetry
    (site 'symmetry', Amendment A1): a partition other than amdq, amddebugq, defq, debugq (longq always, preq and
    amdpreq because every job carries --no-requeue), an account other than the default zzheng1, more CPUs than a node,
    and an excluded node (cn112 or the CPU pin's, amd_exclusions) named in --nodelist of an AMD-pool job; an AMD-pool
    job gets --exclude=<its own value>,<every excluded node it does not name> (cn112, then the CPU pin's nodes, then
    C8_AMD_EXCLUDE_EXTRA's), returned in site_tokens. exclude: amd_exclusions(prof, env) of the caller; None means the
    package constants alone (amd_exclusions(prof, {})). The time limit is normalized up to whole minutes, what Slurm
    reserves (S2-003): time_s is that value, and a request with a seconds part gets --time=<it> in site_tokens."""
    prof=site_profile(site);PART=prof.partitions
    merged={};seen=set()
    for src in (script,envo,cmd):
        for name,val in src:merged[name]=val;seen.add(name)
    if 'mem'in seen and 'mem-per-cpu'in seen:raise Refuse(64,'both --mem and --mem-per-cpu are given (from the command line, SBATCH_* or #SBATCH lines); give exactly one')
    part=merged.get('partition')
    if not part:raise Refuse(64,f'no partition (-p {"|".join(PART)}) is given')
    if part in prof.refused:raise Refuse(64,f'partition {part!r} is refused on {prof.name}: {prof.refused[part]}')
    if part not in PART:raise Refuse(64,f'partition {part!r} is not allowed on {prof.name} ({", ".join(PART)}; one partition per job)')
    acct=merged.get('account')
    if prof.name=='expanse':
        if acct!=prof.account:raise Refuse(64,f'-A {prof.account} is required (got {acct!r})')
    elif acct is not None and acct!=prof.account:raise Refuse(64,f'-A {acct} is not allowed on {prof.name} (omit -A, or give the default account {prof.account})')
    q=merged.get('qos')
    if q and q!=PART[part]['qos']:raise Refuse(64,f'--qos {q} is not allowed on {part} (only its default {PART[part]["qos"]})')
    excl='exclusive'in seen
    if excl and part not in prof.exclusive_ok:raise Refuse(64,f'--exclusive on {part}: an exclusive {part} job gets and is billed the whole node; --exclusive is allowed on {", ".join(prof.exclusive_ok)} only (HD17)')
    def ival(name,default):
        v=merged.get(name,default)
        try:n=int(v);assert n>=1
        except (TypeError,ValueError,AssertionError):raise Refuse(64,f'--{name} must be a positive integer (got {v!r})')
        return n
    nodes=ival('nodes',1);ntasks=ival('ntasks',1);cpt=ival('cpus-per-task',1)
    if nodes!=1 or ntasks!=1:raise Refuse(64,'only --nodes=1 and --ntasks=1 are allowed')
    if PART[part].get('needs_nodes')and 'nodes'not in seen:raise Refuse(64,f'{part} jobs need --nodes=1 (Expanse requires the nodes parameter)')
    cpus=ntasks*cpt
    site_tokens=[]
    if prof.name=='symmetry':
        if cpus>prof.node_cpus[part]:raise Refuse(64,f'{cpus} CPUs exceed a {part} node ({prof.node_cpus[part]})')
        xs=amd_exclusions(prof,{})if exclude is None else list(exclude)
        if part in prof.amd_pool and xs:
            nl=merged.get('nodelist')or''
            for x in xs:
                if not hostlist_has(nl,x):continue
                if x==prof.exclude_amd:raise Refuse(64,f'--nodelist names {x} on {part}: {x} (AVX-512) is excluded from every AMD-pool job (bitwise gates on AVX2 nodes)')
                raise Refuse(64,f'{x} is not AMD EPYC 7543 (symmetry\'s pinned CPU; HD11; slurm/site.sh c8_cpu_guard): remove it from --nodelist')
            ex=merged.get('exclude')
            site_tokens=['--exclude='+','.join(([ex]if ex else[])+[x for x in xs if not(ex and hostlist_has(ex,x))])]
    if 'mem'in seen:
        mem=budget.mem_mib(merged['mem'])
        if mem is None:raise Refuse(64,f'--mem={merged["mem"]} is not a memory size')
    elif 'mem-per-cpu'in seen:
        per=budget.mem_mib(merged['mem-per-cpu'])
        if per is None:raise Refuse(64,f'--mem-per-cpu={merged["mem-per-cpu"]} is not a memory size')
        mem=per*cpus
    else:raise Refuse(64,'no memory request: give --mem (or --mem-per-cpu)')
    if mem<=0:raise Refuse(64,'--mem=0 (all of a node\'s memory) is refused: give an explicit size')
    if mem>PART[part]['mem']:raise Refuse(64,f'memory {mem/1024:.1f} GiB exceeds the {part} ceiling {PART[part]["mem"]//1024}G')
    if 'time'not in seen:raise Refuse(64,'no time limit: give --time')
    t=budget.parse_duration(merged['time'])
    if t is None or t<=0:raise Refuse(64,f'--time {merged["time"]!r} is not a finite Slurm time')
    # S2-003: Slurm reserves whole minutes (a seconds part rounds up), so the limit is normalized up to the minute before
    # the partition check, the pricing and the intent, and that value is submitted (a --time token after the user's,
    # which overrides #SBATCH and SBATCH_TIMELIMIT too); a whole-minute request is submitted as given
    tn=-(-t//60)*60
    if tn>PART[part]['time']:raise Refuse(64,f'--time {merged["time"]} exceeds the {part} limit')
    if tn!=t:site_tokens=site_tokens+[f'--time={hms(tn)}']
    t=tn
    return {'partition':part,'account':acct,'nodes':nodes,'cpus':cpus,'mem_mib':mem,'time_s':t,'exclusive':excl,'dependency':merged.get('dependency'),
            'billing':prof.billing_value(part,nodes,cpus,mem),'site':prof.name,'unit':prof.unit,'capped':bool(PART[part]['capped']),'site_tokens':site_tokens}

def spec_slots(r:dict,ntasks:int)->dict:
    p=r['partition']
    if r.get('site')=='symmetry':return {'amd_nodes':r['nodes']*ntasks}if p in budget.AMD_POOL else{}   # H7; Intel is outside the cap
    if p=='compute':return {'normal_run':ntasks,'normal_sub':ntasks,'account':ntasks,'nodes':r['nodes']*ntasks}
    return {p:ntasks}

# ----------------------------------------------------------------------------------------------------------------
BASE_ID='H7E-R'
BASE_SPLIT={'run':11,'sub':27,'acct_run':32,'shared':DEFAULT_SHARED,'dev_nodes':4}   # the agreed H7E-R split (F43; DECISIONS.md:87)
# symmetry (Amendment A1; DECISIONS A5 "H7" and the 2026-10-05 line "H11 pilot window on symmetry"): at most 4 AMD-pool
# nodes per session in development (amdq, amddebugq, amdpreq together), 8 for both sessions; a pilot window gives the
# pilot session 5 (the other 3), still 8 in total, through its own DECISIONS line.
SYM_BASE_ID='H7'
SYM_BASE_SPLIT={'amd_nodes':4,'amd_total':8}
SYM_AMD_TOTAL_MAX=8
# An agreed production window (DECISIONS 2026-10-06, the C8(2) production: 9 + 3) may re-split up to 12 in total; only a
# re-split that carries an until key (after it, amd_total_now falls back to the base 8), and the base split stays at 8.
SYM_AMD_WINDOW_MAX=12

class Reservation:
    """C8_RESERVATION (D.11 "Cross-session admission mode"): one line, parsed strictly.

    Expanse: only the base split `mode=reservation;id=H7E-R;run=11;sub=27;acct_run=32;shared=32;dev_nodes=4` may omit
    `until`. symmetry (prof=SYMMETRY): only `mode=reservation;id=H7;amd_nodes=4;amd_total=8` may omit it (amd_nodes <=
    amd_total <= 8; a re-split with `until`, an agreed DECISIONS window, up to SYM_AMD_WINDOW_MAX 12). Every re-split names its DECISIONS item and carries `;until=<UTC>`. A malformed value (an invalid
    line, an unknown or withdrawn mode, or a re-split without `until`) refuses every capped job (Expanse normal-QOS,
    symmetry AMD-pool; 64) and still admits the others (Expanse `shared` under the base share (32) and `debug` (2);
    symmetry Intel defq/debugq) (A-ORC-11); `mode=none` or unset refuses capped jobs (65). After `until`, capped
    admission refuses (65) and the `shared` share falls back to at most the base split's, so an expired window never
    keeps a larger share."""
    KEYS=('mode','id','run','sub','acct_run','shared','dev_nodes')
    SYM_KEYS=('mode','id','amd_nodes','amd_total')
    def __init__(self,text:str|None,prof:budget.SiteProfile|None=None):
        self.prof=prof or budget.EXPANSE;sym=self.prof.name=='symmetry'
        self.keys=self.SYM_KEYS if sym else self.KEYS;self.base_id=SYM_BASE_ID if sym else BASE_ID;self.base=SYM_BASE_SPLIT if sym else BASE_SPLIT
        self.text=text;self.mode='none';self.shared=DEFAULT_SHARED;self.until=None;self.id=None;self.error=None
        try:self._parse(text)
        except Refuse as r:
            self.mode='malformed';self.error=str(r);self.shared=DEFAULT_SHARED;self.until=None;self.id=None
    def _parse(self,text):
        if text is None or text.strip()=='':return
        if '\n'in text:raise Refuse(64,'C8_RESERVATION must be one line')
        kv={}
        for part in text.split(';'):
            k,eq,v=part.partition('=')
            if not eq or not k or k in kv:raise Refuse(64,f'malformed C8_RESERVATION {text!r}')
            kv[k]=v
        mode=kv.get('mode')
        if mode=='none':
            if set(kv)!={'mode'}:raise Refuse(64,f'malformed C8_RESERVATION {text!r} (mode=none takes no other key)')
            return
        if mode!='reservation':raise Refuse(64,f'C8_RESERVATION mode {mode!r} is unknown (reservation or none; common-lock and turn were withdrawn in r2)')
        if set(kv)-set(self.keys)-{'until'}or set(self.keys)-set(kv):raise Refuse(64,f'malformed C8_RESERVATION {text!r}: keys {",".join(self.keys)}[,until] required on {self.prof.name}')
        if not re.fullmatch(r'[A-Za-z0-9._-]+',kv['id']):raise Refuse(64,f'malformed C8_RESERVATION id {kv["id"]!r}')
        try:vals={k:int(kv[k])for k in self.keys[2:]}
        except ValueError:raise Refuse(64,f'malformed C8_RESERVATION {text!r}: counts must be integers')
        if any(v<0 for v in vals.values()):raise Refuse(64,f'C8_RESERVATION {text!r}: inconsistent counts')
        if self.prof.name=='symmetry':
            cap=SYM_AMD_WINDOW_MAX if 'until'in kv else SYM_AMD_TOTAL_MAX   # a dated re-split (a DECISIONS window) up to 12; else 8
            if vals['amd_nodes']>vals['amd_total']or vals['amd_total']>cap:
                raise Refuse(64,f'C8_RESERVATION {text!r}: inconsistent counts (amd_nodes <= amd_total <= {cap}, H7/H11; a re-split with '
                                f';until= may reach {SYM_AMD_WINDOW_MAX}, the base split {SYM_AMD_TOTAL_MAX})')
        elif vals['run']>vals['sub']or vals['acct_run']>32:raise Refuse(64,f'C8_RESERVATION {text!r}: inconsistent counts')
        until=None
        if 'until'in kv:
            try:until=calendar.timegm(time.strptime(kv['until'],'%Y-%m-%dT%H:%M:%SZ'))
            except ValueError:raise Refuse(64,f'C8_RESERVATION until={kv["until"]!r} is not a UTC time YYYY-MM-DDTHH:MM:SSZ')
        elif not(kv['id']==self.base_id and vals==self.base):
            raise Refuse(64,f'C8_RESERVATION {text!r}: a re-split names its DECISIONS item and carries ;until=<UTC>; only the base split '
                            f'id={self.base_id} with ' + ';'.join(f'{k}={v}'for k,v in self.base.items())+' may omit it')
        self.mode='reservation';self.id=kv['id'];self.until=until
        for k,v in vals.items():setattr(self,k,v)
    def expired(self)->bool:return self.mode=='reservation'and self.until is not None and ledger.now()>=self.until
    def normal_refusal(self)->str|None:
        what='AMD-pool'if self.prof.name=='symmetry'else'normal-QOS'
        if self.mode=='malformed':return f'{self.error}: no {what} job is admitted'
        if self.mode!='reservation':return f'no agreed reservation (C8_RESERVATION unset or mode=none): no {what} job is admitted (D.11)'
        if self.expired():
            return f'the re-split {self.id} expired at {ledger.utc_iso(self.until)}: reset C8_RESERVATION to the base split ({self.base_id})'
        return None
    def shared_share(self)->int:
        """The live c8d3- shared share: after `until`, at most the base split's (an expired window keeps no larger share)."""
        return min(self.shared,BASE_SPLIT['shared'])if self.expired()else self.shared
    def amd_total_now(self)->int:
        """symmetry: both sessions' AMD-pool total (after `until`, at most the base split's)."""
        return min(self.amd_total,SYM_BASE_SPLIT['amd_total'])if self.expired()else self.amd_total

def compute_cap(env:dict,res:Reservation)->int:
    """The development node cap (Expanse compute nodes; symmetry AMD-pool nodes): C8_COMPUTE_CAP, never above the
    active reservation's dev_nodes (symmetry: amd_nodes; after `until`, the base split's), so a cap left at a pilot
    window's count cannot raise the share of the agreed split; 0 without a reservation."""
    v=env.get('C8_COMPUTE_CAP')
    if v is not None and not v.isdigit():raise Refuse(64,f'C8_COMPUTE_CAP must be a non-negative integer (got {v!r})')
    if res.mode!='reservation':return 0
    key='amd_nodes'if res.prof.name=='symmetry'else'dev_nodes'
    agreed=res.base[key]if res.expired()else getattr(res,key)
    if v is None:return agreed
    if int(v)>agreed:say(f'C8_COMPUTE_CAP={v} exceeds the reservation\'s {key}={agreed} ({res.id}{", expired" if res.expired() else ""}): the cap is {agreed}')
    return min(int(v),agreed)

def budget_line(env:dict)->str:
    line=env.get('C8_BUDGET_LINE')
    if line not in budget.LINES:raise Refuse(64,f'C8_BUDGET_LINE must be {", ".join(budget.LINES[:-1])} or {budget.LINES[-1]} (got {line!r})')
    budget.line_cap(line,env)
    return line

# ----------------------------------------------------------------------------------------------------------------
@dataclass
class JobSpec:
    """One sbatch call (a job or an array). user_tokens pass through to sbatch unchanged (raw's --wrap byte for byte);
    tool_tokens are the options the tool owns."""
    role:str
    cdir:Path
    resolved:dict
    user_tokens:list=field(default_factory=list)
    script:str|None=None
    tool_tokens:list=field(default_factory=list)
    array:dict|None=None
    depends:list=field(default_factory=list)     # job ids or ('spec', i)
    dep_kind:str|None=None
    kind:str='raw'
    env_extra:dict=field(default_factory=dict)
    job_id:str|None=None
    token:str|None=None
    @property
    def ntasks(self)->int:return len(self.array['tasks'])if self.array else 1
    @property
    def c(self)->str:return ledger.dir_sha12(self.cdir)
    @property
    def p(self)->str:return ledger.plan_sha12(self.cdir)
    @property
    def slots(self)->dict:return spec_slots(self.resolved,self.ntasks)
    @property
    def reservation_su(self)->float:return self.resolved['billing']*self.resolved['time_s']/3600.0*self.ntasks
    @property
    def normal(self)->bool:
        """A job under the reservation's caps: Expanse normal QOS (compute), symmetry the AMD pool (H7)."""
        return self.resolved.get('capped',self.resolved['partition']=='compute')

CAMPAIGN_ROLE_RE=re.compile(r'lane|merge|off[0-9]+')   # campaign jobs only (D.11 "Names"): a lane worker, a merge, an array window

def check_role(role:str,line:str,raw=True)->str:
    if not ROLE_RE.fullmatch(role or''):raise Refuse(64,f'role {role!r} must match [a-z][a-z0-9_]{{0,31}}')
    for L,x in budget.LINE_PREFIX.items():   # under every line: a prefixed name is classified to that line (budget.name_info)
        if raw and role.startswith(x):raise Refuse(64,f'role {role!r}: the {x} prefix is set by the tool (C8_BUDGET_LINE={L}), never by the caller')
    if raw and CAMPAIGN_ROLE_RE.fullmatch(role):
        raise Refuse(64,f'role {role!r} is a campaign role (lane, merge, off<N>; D.11): a raw job carrying it would look like a lane worker, merge or '
                        'array window of its campaign; choose another role')
    return budget.LINE_PREFIX.get(line,'')+role

def check_dir(d:str,s:ledger.Settings)->Path:
    """--dir: $C8_ROOT/runs/<name> or $C8_ROOT/evidence/<sha12>/<name> (it need not exist yet); anything else 64."""
    p=Path(os.path.realpath(d));rel=None
    try:rel=p.relative_to(s.root).parts
    except ValueError:pass
    ok=rel is not None and(len(rel)==2 and rel[0]=='runs'or len(rel)==3 and rel[0]=='evidence'and re.fullmatch(r'[0-9a-f]{12}',rel[1]))
    if not ok or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*',rel[-1]):
        raise Refuse(64,f'--dir {d} must be $C8_ROOT/runs/<name> or $C8_ROOT/evidence/<sha12>/<name> (C8_ROOT={s.root})')
    return p

def raw_spec(role:str,d:str,tokens:list,env:dict,s:ledger.Settings,line:str)->JobSpec:
    opts,pos=parse_options(tokens,'raw sbatch options')
    wraps=[v for n,v in opts if n=='wrap']
    if len(pos)>1:raise Refuse(64,f'raw takes one batch script at most (got {pos})')
    if bool(wraps)==bool(pos):raise Refuse(64,'raw needs exactly one of --wrap CMD and a batch script')
    script=pos[0]if pos else None
    sopts=script_options(Path(script))if script else[]
    if any(n=='wrap'for n,_ in sopts):raise Refuse(64,'--wrap in #SBATCH lines is refused')
    prof=site_profile(s.site);r=resolve(sopts,env_options(env),opts,prof,exclude=amd_exclusions(prof,env))
    full=check_role(role,line)
    if prof.intel_roles and budget.pool(prof,r['partition'])=='intel'and not role.startswith(prof.intel_roles):
        raise Refuse(64,f'role {role!r} on {r["partition"]} refused: Intel Gold 6148 nodes are AVX-512 (the float64 assembly differs there by 4 ulp, as on '
                        f'cn112), so validation, bitwise gates, replays, builds, plans and reports run on the AMD AVX2 pool (amdq, amddebugq; cn112 '
                        f'excluded); a raw job on Intel needs a role starting with {" or ".join(prof.intel_roles)} (A1)')
    dep=r['dependency']
    if dep is not None:
        if not(role.startswith('drill_')and r['partition']in prof.drill_partitions and re.fullmatch(r'afterany:\d+',dep)):
            raise Refuse(64,f'--dependency={dep} refused: raw allows only --dependency=afterany:<job id>, for a drill_* role on {" or ".join(prof.drill_partitions)} (J-DRL-10)')
    user=[t for t in tokens if t!=script]if script else list(tokens)
    return JobSpec(role=full,cdir=check_dir(d,s),resolved=r,user_tokens=user,script=script,tool_tokens=list(r['site_tokens']),kind='raw')

# ----------------------------------------------------------------------------------------------------------------
# Spec builders for the campaign entry points (lanes N, submit), which Stage 3 wires to campaign directories.
def one_vendor(prof:budget.SiteProfile,worker_parts:list,merge_part:str,what:str)->None:
    """symmetry: a campaign's workers and its merge run on one CPU vendor (A1; docs/HPC.md "Symmetry"): the merge's
    float64 assembly differs by 4 ulp on the AVX-512 Intel nodes, so an AMD campaign merged on defq (or the reverse)
    breaks the bitwise gates. Refuses (64) a merge partition of another pool than any worker's."""
    if prof.name!='symmetry':return
    m=budget.pool(prof,merge_part)
    bad=sorted({p for p in worker_parts if budget.pool(prof,p)!=m})
    if bad:raise Refuse(64,f'the merge on {merge_part} ({m}) and the {what} on {",".join(bad)} ({",".join(sorted({str(budget.pool(prof,p))for p in bad}))}) are of '
                           'different CPU vendors: one vendor per campaign (A1); set C8_MERGE_SBATCH_ARGS to a partition of the workers\' pool '
                           '(`c8_profile` sets both); nothing submitted')

def array_vendor(env:dict,prof:budget.SiteProfile,plan_role,site_tokens:list,merge_tokens:list,script_work:str,script_merge:str)->None:
    """symmetry: array mode (submit, window, resubmit) puts its windows and merge on Intel defq/debugq (AVX-512, like
    cn112: the float64 assembly differs there by 4 ulp) only for a plan of role campaign, mirroring raw's intel_/drill_
    rule. validation, cost_sweep, cost_refresh and flag_check plans (D.5 sends them to array mode) carry the bitwise and
    calibration work and run on the AMD AVX2 pool; `c8_profile intel` would otherwise send them to defq outside the
    H7 cap. Refuses (64) before the session lock and any query; Expanse is unaffected (A1 repair round 2)."""
    if prof.name!='symmetry'or plan_role=='campaign':return
    parts=[]
    for toks,what,script in ((site_tokens,'C8_SBATCH_ARGS',script_work),(merge_tokens,'C8_MERGE_SBATCH_ARGS',script_merge)):
        o,_=parse_options(toks,what,positional=False,allow=CAMPAIGN_ALLOW)
        parts.append((what,resolve(script_options(Path(script)),env_options(env),o,prof,exclude=amd_exclusions(prof,env))['partition']))
    bad=[(w,p)for w,p in parts if budget.pool(prof,p)=='intel']
    if bad:raise Refuse(64,f'array mode on {", ".join(f"{p} ({w})"for w,p in bad)} refused for a plan of role {plan_role!r}: the Intel Gold 6148 nodes are AVX-512 '
                           '(the float64 assembly differs there by 4 ulp, as on cn112), so only campaign plans may run their windows or merge on Intel; '
                           'validation, cost_sweep, cost_refresh and flag_check plans run on the AMD AVX2 pool (amdq or amddebugq, cn112 excluded; '
                           '`c8_profile lanes` or `c8_profile debug`) (A1); nothing submitted')

# S2-001: one CPU vendor per campaign, pinned at its first work admission. RUN/cpu_vendor.json is written once, under the
# session lock, exclusively (O_EXCL, fsynced), by the first `lanes N` (lanes 0 included), `submit`, `window` or
# `resubmit` that passes admission, before its first sbatch; every later admission of the campaign refuses (64) jobs of
# another vendor, live jobs of the campaign included, and every job script refuses (68) a node of another vendor
# (slurm/site.sh c8_vendor_guard); the merge refuses checkpoints of mixed vendors (production.py merge).
VENDOR_PIN='cpu_vendor.json';VENDOR_SCHEMA='c8-d3-cpu-vendor-1'
def campaign_vendor(prof:budget.SiteProfile,partition:str)->str:
    """The CPU vendor of a partition: symmetry its pool (amd: amdq, amddebugq; intel: defq, debugq; anything else
    'unknown'); Expanse 'amd' (every admitted partition is EPYC 7742)."""
    if prof.name!='symmetry':return 'amd'
    return budget.pool(prof,partition)or'unknown'

def vendor_pin(cdir:Path)->dict|None:
    """The campaign's pinned CPU vendor record, None before its first work admission; 69 when unreadable."""
    p=Path(cdir)/VENDOR_PIN
    try:doc=json.loads(p.read_bytes())
    except FileNotFoundError:return None
    except (OSError,ValueError)as e:raise Refuse(69,f'the CPU vendor record {p} is unreadable ({e}); nothing submitted')
    if not isinstance(doc,dict)or doc.get('schema')!=VENDOR_SCHEMA or doc.get('vendor')not in('amd','intel'):
        raise Refuse(69,f'{p} is not a {VENDOR_SCHEMA} record naming amd or intel; nothing submitted')
    return doc

def vendor_check(prof:budget.SiteProfile,cdir:Path,specs:list,live:list)->str:
    """The one CPU vendor of an admission (S2-001): every new job and every live job of the campaign (snapshot lines)
    on one vendor, and that the campaign's pinned one when a pin exists; refuses (64) otherwise, naming both. Returns it."""
    got={campaign_vendor(prof,sp.resolved['partition'])for sp in specs}|{campaign_vendor(prof,q.partition)for q in live}
    where=', '.join(sorted({f'{sp.resolved["partition"]} ({sp.kind})'for sp in specs}|{f'{q.partition} (live {q.jobid})'for q in live}))
    if len(got)!=1:raise Refuse(64,f'this admission would put the campaign on several CPU vendors ({", ".join(sorted(got))}: {where}): one vendor per campaign '
                                   '(S2-001); nothing submitted')
    v=next(iter(got));pin=vendor_pin(cdir)
    if pin is not None and pin['vendor']!=v:
        raise Refuse(64,f'the campaign {cdir} is pinned to CPU vendor {pin["vendor"]} ({VENDOR_PIN}, its first work admission: '
                        f'{(pin.get("first_admission")or{}).get("command")} at {(pin.get("first_admission")or{}).get("utc")}), but this admission is {v} ({where}): '
                        'native rows and the float64 assembly differ between vendors, so a campaign never changes vendor (S2-001); choose the '
                        f'profile of {pin["vendor"]} (C8_SBATCH_ARGS, C8_MERGE_SBATCH_ARGS; `c8_profile`); nothing submitted')
    return v

def pin_vendor(cdir:Path,vendor:str,prof:budget.SiteProfile,label:str,lock,mh:str|None=None)->dict:
    """RUN/cpu_vendor.json at the campaign's first work admission (S2-001): created exclusively under the session lock
    (O_EXCL, one write, file and directory fsynced; 74 on a write failure, nothing submitted); an existing one must name
    `vendor` (64 otherwise)."""
    p=Path(cdir)/VENDOR_PIN
    for _ in range(2):
        have=vendor_pin(cdir)
        if have is not None:
            if have['vendor']!=vendor:raise Refuse(64,f'the campaign {cdir} is pinned to CPU vendor {have["vendor"]} ({VENDOR_PIN}), not {vendor}; nothing submitted')
            return have
        doc={'schema':VENDOR_SCHEMA,'vendor':vendor,'site':prof.name,'campaign_c':ledger.dir_sha12(cdir),'manifest_sha256':mh,
             'first_admission':{'command':label,'utc':ledger.utc_iso(),'host':socket.gethostname(),'pid':os.getpid()},
             'rule':'every job of this campaign runs on this CPU vendor: admission refuses (64) another one, every job script refuses (68) a node of '
                    'another one (slurm/site.sh c8_vendor_guard), the merge refuses checkpoints of mixed vendors (S2-001)'}
        lock.check('cpu vendor pin')
        try:ledger.write_new_file(p,(json.dumps(doc,indent=1)+'\n').encode(),'vendor_pin')
        except FileExistsError:continue   # written meanwhile: compare (under the session lock this is another tool's file)
        say(f'campaign CPU vendor pinned: {vendor} ({p}; first work admission; S2-001)');return doc
    raise Refuse(69,f'{p} appeared and vanished during the pin; nothing submitted')

def lane_specs(cdir:Path,n:int,lane_time:str,site_tokens:list,lane_mem:str,merge_tokens:list,env:dict,line:str,
               live_workers:list,script_worker:str,script_merge:str,log_dir:Path|None=None,job_env:dict|None=None,drill_cpus:int|None=None,
               live_partitions:list|None=None,exclude:list|None=None)->list:
    """N whole-node lane workers (compute, --exclusive --nodes=1 --ntasks=1) and one merge afterany on every live
    worker of the campaign and the new ones (D.11 "Merges"). Drill mode (drill_cpus, D.9): workers on shared or debug
    with --nodes=1 --ntasks=1 -c drill_cpus and no --exclusive. symmetry: the merge's CPU vendor must be the workers'
    (the new ones and live_partitions, the partitions of the campaign's live workers; one_vendor). exclude: the
    caller's amd_exclusions(prof, env), computed before the session lock (None: computed here from env)."""
    specs=[]
    wtoks=[*site_tokens,f'--mem={lane_mem}',f'--time={lane_time}']
    wopts,_=parse_options(wtoks,'C8_SBATCH_ARGS',positional=False,allow=CAMPAIGN_ALLOW)
    own=['--exclusive','--nodes=1','--ntasks=1']if drill_cpus is None else['--nodes=1','--ntasks=1',f'--cpus-per-task={drill_cpus}']
    oopts=[('exclusive',None),('nodes','1'),('ntasks','1')]if drill_cpus is None else[('nodes','1'),('ntasks','1'),('cpus-per-task',str(drill_cpus))]
    prof=budget.profile(env);xs=amd_exclusions(prof,env)if exclude is None else exclude
    for _ in range(n):
        r=resolve(script_options(Path(script_worker)),env_options(env),wopts+oopts,prof,exclude=xs)
        specs.append(JobSpec(role=check_role('lane',line,raw=False),cdir=cdir,resolved=r,user_tokens=wtoks,script=script_worker,
                             tool_tokens=own+r['site_tokens']+log_tokens(log_dir,'lane-%j.log'),kind='lane',env_extra=dict(job_env or{})))
    mopts,_=parse_options(merge_tokens,'C8_MERGE_SBATCH_ARGS',positional=False,allow=CAMPAIGN_ALLOW)
    r=resolve(script_options(Path(script_merge)),env_options(env),mopts,prof,exclude=xs)
    if prof.name=='symmetry':   # the workers' partition from their options (lanes 0 too) and the live workers'
        rw=resolve(script_options(Path(script_worker)),env_options(env),wopts+oopts,prof,exclude=xs)
        one_vendor(prof,[rw['partition']]+list(live_partitions or[]),r['partition'],'lane workers')
    specs.append(JobSpec(role=check_role('merge',line,raw=False),cdir=cdir,resolved=r,user_tokens=list(merge_tokens),script=script_merge,
                         tool_tokens=r['site_tokens']+log_tokens(log_dir,'merge-%j.log'),depends=list(live_workers)+[('spec',i)for i in range(n)],dep_kind='afterany',kind='merge',
                         env_extra=dict(job_env or{})))
    return specs

def log_tokens(log_dir:Path|None,pattern:str)->list:
    """--output into the campaign's slurm_logs/ (a literal '%' of the path escaped as '%%', D.16)."""
    return [f'--output={str(log_dir).replace("%","%%")}/{pattern}']if log_dir is not None else[]

def array_specs(cdir:Path,windows:list,site_tokens:list,merge_tokens:list,env:dict,line:str,script_work:str,script_merge:str,
                log_dir:Path|None=None,job_env:dict|None=None,merge_depends:list|None=None,exclude:list|None=None)->list:
    """Work arrays (one per window offset, '--array=<range>%<throttle>') and one afterok merge on all of them. exclude:
    the caller's amd_exclusions(prof, env), computed before the session lock (None: computed here from env)."""
    specs=[];prof=budget.profile(env);xs=amd_exclusions(prof,env)if exclude is None else exclude
    topts,_=parse_options(site_tokens,'C8_SBATCH_ARGS',positional=False,allow=CAMPAIGN_ALLOW)
    for off,rng in windows:
        r=resolve(script_options(Path(script_work)),env_options(env),topts,prof,exclude=xs)
        tasks=budget.parse_tasks(rng)
        specs.append(JobSpec(role=check_role(f'off{off}',line,raw=False),cdir=cdir,resolved=r,user_tokens=list(site_tokens),script=script_work,
                             tool_tokens=[f'--array={rng}']+r['site_tokens']+log_tokens(log_dir,'work-%A_%a.log'),array={'spec':rng,'tasks':tasks},kind='array',
                             env_extra={**(job_env or{}),'C8_INDEX_OFFSET':str(off)}))
    mopts,_=parse_options(merge_tokens,'C8_MERGE_SBATCH_ARGS',positional=False,allow=CAMPAIGN_ALLOW)
    r=resolve(script_options(Path(script_merge)),env_options(env),mopts,prof,exclude=xs)
    one_vendor(prof,[sp.resolved['partition']for sp in specs],r['partition'],'array windows')
    specs.append(JobSpec(role=check_role('merge',line,raw=False),cdir=cdir,resolved=r,user_tokens=list(merge_tokens),script=script_merge,
                         tool_tokens=r['site_tokens']+log_tokens(log_dir,'merge-%j.log'),depends=list(merge_depends or[])+[('spec',i)for i in range(len(windows))],dep_kind='afterok',
                         kind='merge',env_extra=dict(job_env or{})))
    return specs

# ----------------------------------------------------------------------------------------------------------------
# Rules (D.11 step 3; HD13; HD17 "Slots")
LIMIT_NAMES={'normal_run':'own normal-QOS live share (C8_RESERVATION run)','normal_sub':'own normal-QOS submitted share (sub)',
             'account':'account running normal-QOS total (acct_run)','nodes':'development compute nodes (C8_COMPUTE_CAP)',
             'shared':'own live shared jobs (C8_RESERVATION shared)','debug':'debug jobs per account',
             'amd_nodes':'own live AMD-pool nodes, amdq + amddebugq + amdpreq (H7; C8_RESERVATION amd_nodes, C8_COMPUTE_CAP)'}

def counts(snap:budget.Snapshot,ev:budget.Evaluation,unresolved:dict)->dict:
    """Scheduler counts per slot class plus the unresolved intents' excess (HD17 "Slots")."""
    prof=getattr(snap,'prof',budget.EXPANSE)
    if prof.name=='symmetry':
        c={'amd_nodes':0};det={'c8d2_amd':[],'c8d2_amd_nodes':0}
        for q in snap.live_lines():
            n=q.classes().get('amd_nodes',0)
            if q.ours:c['amd_nodes']+=n
            elif n and q.user==prof.user and q.name.startswith('c8d2-'):det['c8d2_amd'].append(q.jobid);det['c8d2_amd_nodes']+=n
        extras,per=ev.slot_extras(unresolved)if not ledger.HOOKS.switch('no_intents')else({},{})
        for k,v in extras.items():c[k]+=v
        return {'classes':c,'extras':dict(extras),'per_token':per,'detectors':det}
    c={k:0 for k in budget.SLOT_CLASSES};det={'c8d2_run':[],'c8d2_live':[],'foreign':[],'user_run':0,'user_live':0,'user_shared':0}
    for q in snap.live_lines():
        cl=q.classes()
        if q.ours:
            for k in ('normal_run','normal_sub','nodes','shared'):c[k]+=cl.get(k,0)
        if cl.get('account')and(q.ours or q.state not in budget.OTHERS_PENDING):c['account']+=1
        if cl.get('debug'):c['debug']+=1
        if q.user==prof.user:
            if cl.get('shared'):det['user_shared']+=1
            if cl.get('account'):
                det['user_live']+=1
                if q.state not in budget.OTHERS_PENDING:det['user_run']+=1
                if q.name.startswith('c8d2-'):
                    det['c8d2_live'].append(q.jobid)
                    if q.state not in budget.OTHERS_PENDING:det['c8d2_run'].append(q.jobid)
                elif not q.ours:det['foreign'].append(f'{q.jobid} ({q.name})')
    extras,per=ev.slot_extras(unresolved)if not ledger.HOOKS.switch('no_intents')else({},{})
    for k,v in extras.items():c[k]+=v
    return {'classes':c,'extras':dict(extras),'per_token':per,'detectors':det}

def limits(res:Reservation,cap:int)->dict:
    if res.prof.name=='symmetry':return {'amd_nodes':cap}
    run=res.run if res.mode=='reservation'else 0;sub=res.sub if res.mode=='reservation'else 0;acct=res.acct_run if res.mode=='reservation'else 0
    return {'normal_run':run,'normal_sub':sub,'account':acct,'nodes':cap,'shared':res.shared_share(),'debug':DEBUG_LIMIT}

def violations(cnt:dict,lim:dict,res:Reservation,k:dict,normal:bool,classes:set|None=None)->list:
    out=[]
    if normal:
        why=res.normal_refusal()
        if why:out.append(('reservation',why))
    for cl,used in cnt['classes'].items():
        if classes is not None and cl not in classes:continue
        if k.get(cl,0)==0 and classes is None:continue
        if used+k.get(cl,0)>lim[cl]:out.append((cl,f'{LIMIT_NAMES[cl]}: {used} counted + {k.get(cl,0)} new > {lim[cl]}'))
    if normal and res.prof.name=='symmetry':
        d=cnt['detectors']
        if res.mode=='reservation':
            tot=res.amd_total_now();ours=cnt['classes']['amd_nodes']+k.get('amd_nodes',0)
            if d['c8d2_amd_nodes']+ours>tot:
                out.append(('detector',f'both sessions\' AMD-pool nodes would exceed {tot} (H7/H11): c8d2- {d["c8d2_amd_nodes"]} ({",".join(d["c8d2_amd"])}) + c8d3- {ours}'))
        return out
    if normal:
        d=cnt['detectors']
        if len(d['c8d2_run'])>11 or len(d['c8d2_live'])>27:out.append(('detector',f'c8d2- jobs exceed C62d\'s 11/27: running {d["c8d2_run"]}, live {d["c8d2_live"]}'))
        if d['foreign']:out.append(('detector','live zzheng8 normal-QOS job(s) outside both prefixes: '+', '.join(d['foreign'])))
        add=k.get('normal_run',0)+cnt['extras'].get('normal_run',0)
        if d['user_run']+add>22 or d['user_live']+add>54:out.append(('detector',f'the user\'s normal-QOS total would exceed 22 running / 54 submitted ({d["user_run"]}+{add} / {d["user_live"]}+{add})'))
    return out

def sum_slots(specs)->dict:
    k={}
    for sp in specs:
        for cl,v in sp.slots.items():k[cl]=k.get(cl,0)+v
    return k

def largest(family,nmax:int,ok)->int:
    for n in range(nmax,-1,-1):
        if ok(family(n)):return n
    return 0

# ----------------------------------------------------------------------------------------------------------------
def say(*a):print('C8:',*a,flush=True)

def not_submitted(t,launched,ambiguous,reason,rc=None,stderr=''):
    return ledger.payload('not_submitted',[t],token=t,launched=launched,ambiguous=ambiguous,reason=reason,exit_status=rc,stderr=(stderr or'')[-2000:])

def classify(rc:int,out:str,err:str)->tuple[str|None,bool,bool,str]:
    """(job id, launched, ambiguous, reason) of the launch wrapper's result."""
    if rc==0:
        m=re.fullmatch(r'(\d+)(;\S+)?',(out.strip().splitlines()or[''])[0].strip())
        if m:return m.group(1),True,False,'submitted'
        return None,True,True,f'sbatch exited 0 without a job id ({out.strip()[:200]!r})'
    if rc==86 and GUARD_LATE in err:return None,False,False,'exec guard: later than the intent utc + 60 s; sbatch not started'
    if rc in(125,126,127)and TIMEOUT_FAILED in err:return None,False,False,'the launch wrapper could not start the exec guard; sbatch not started: '+err.strip()[-300:]
    if rc in(124,137)or rc<0:return None,True,True,f'sbatch killed by `timeout -s KILL {SBATCH_KILL_AFTER}` (exit {rc}); the job may exist'
    if any(r in err for r in REJECTIONS)and not any(a in err for a in AMBIGUOUS):return None,True,False,'rejected before any job existed: '+err.strip()[-300:]
    return None,True,True,f'sbatch exited {rc} with an unlisted error; the job may exist: '+err.strip()[-300:]

def guard_preflight()->None:
    """The exec guard must be an executable file before any intent is written: `timeout` runs it through its exec bit,
    and a guard that cannot run would make every submission ambiguous (64, nothing written)."""
    if not(EXEC_GUARD.is_file()and os.access(EXEC_GUARD,os.X_OK)):
        raise Refuse(64,f'the exec guard {EXEC_GUARD} is missing or not executable (an export that dropped file modes?): nothing written and no '
                        'sbatch; restore it (chmod 755) or re-export the package')

def launch_argv(sp:JobSpec,name:str,comment:str,deadline:int,standin=False)->list:
    dep=[]
    if sp.depends:
        ids=[str(x)for x in sp.depends]
        dep=[f'--dependency={sp.dep_kind}:{":".join(ids)}']
    sb=['sbatch','--parsable',*([t for t in sp.user_tokens])]+sp.tool_tokens+[f'--job-name={name}',f'--comment={comment}','--no-requeue',*dep]+([sp.script]if sp.script else[])
    return ['timeout','-s','KILL',str(SBATCH_KILL_AFTER),str(EXEC_GUARD),str(deadline)]+(STANDIN if standin else sb)

class Call:
    """One admission decision and its submissions (D.11 steps 1-7), under the session lock."""
    def __init__(self,env:dict,label:str):
        self.env=env;self.label=label;self.s=ledger.Settings(env);budget.check_env(env);budget.check_epoch(env)
        self.prof=budget.profile(env);self.other=budget.other_site(env)
        self.line=budget_line(env);self.res=Reservation(env.get('C8_RESERVATION'),self.prof);self.cap=compute_cap(env,self.res)
        self.fault=env.get('C8_TEST_FAULT')or None;self.H=ledger.HOOKS

    def check_fault(self,specs):
        if self.fault is None:return
        if self.fault not in FAULTS:raise Refuse(64,f'C8_TEST_FAULT={self.fault!r} is unknown ({", ".join(FAULTS)})')
        for sp in specs:
            if not(budget.base_role(sp.role).startswith('drill_')and sp.resolved['partition']in self.prof.drill_partitions):
                raise Refuse(64,f'C8_TEST_FAULT is honoured only for drill_* roles on {" or ".join(self.prof.drill_partitions)} (role {sp.role} on {sp.resolved["partition"]})')

    def malformed_check(self,specs)->None:
        """A malformed C8_RESERVATION refuses every normal-QOS job (64); shared and debug jobs are still admitted."""
        if self.res.mode=='malformed'and any(sp.normal for sp in specs):
            if self.prof.name=='symmetry':raise Refuse(64,f'{self.res.error}: every AMD-pool submission is refused until C8_RESERVATION is fixed (Intel defq and debugq jobs are still admitted)')
            raise Refuse(64,f'{self.res.error}: every normal-QOS submission is refused until C8_RESERVATION is fixed (shared and debug jobs are still admitted)')

    def run(self,plan,family=None,nmax=None,dry_run=False,pin=None)->int:
        """plan(snapshot) -> (specs, supersedes); family(n) -> the specs of N jobs (for the largest admissible N);
        pin(lock): a campaign's first-work-admission record (S2-001), written under the lock after every check and
        before the first sbatch (never on a dry run)."""
        if not dry_run:guard_preflight()
        with ledger.SessionLock(self.s,self.label)as lock:
            self.lock=lock;self.H.point('locked')
            snap=budget.Snapshot.take(self.env,account=True)                       # step 1
            led=ledger.Ledger(self.s,lock);led.read(writer=True);self.H.point('ledger_checked')   # step 2
            led.first_use(snap.ours_seen(),'admission')   # a missing ledger with intent files or c8d3- jobs: 69 (HD17, D.12)
            its=ledger.intent_state(led)
            for t,it in its.items():
                if it.file_error:say(f'intent {t}: {it.file_error}; counted from its ledger copy (rebuild re-writes the file)')
                elif it.ledger is not None and it.file_loc is None and it.unresolved:say(f'intent {t}: no intent file; counted from its ledger copy')
            for t,it in its.items():                                                # interrupted resolutions first
                if it.resolving and it.file_loc=='pending':
                    led.rename_resolved(t);it.file_loc='resolved';say(f'completed the interrupted resolution of intent {t}')
            ev=budget.Evaluation(snap,its,self.other)
            for t,it in sorted(its.items()):
                if it.unresolved and not it.hold:
                    rule,charge,evd=ev.evidence(it)
                    if rule:
                        rec=ledger.payload('resolution',[t],token=t,rule=rule,charge_su=charge,evidence=evd,by='admission')
                        led.append(rec);it.resolving.append(rec);led.rename_resolved(t);it.file_loc='resolved'
                        say(f'intent {t} resolved ({rule}; charge {charge:.4f} SU)')
            self.H.point('resolutions')
            adopted,notes,bad=budget.adoption(snap,led.records,self.s.root,by='admission')
            if bad:raise Refuse(69,'unattributable c8d3- job(s): '+'; '.join(f'{b["job_id"]}: {b["why"]}'for b in bad)+
                                   '. Admission is blocked until `tools/ledger.py rebuild --reason ...` records them or the host decides; no tool cancels them')
            for p in adopted+notes:
                led.append(p);say(f'{p["kind"]} {p.get("job_id")} ({p.get("name","")}; dir {p.get("dir")})')
            self.H.point('adopted')
            unresolved={t:i for t,i in its.items()if i.unresolved and not i.hold}
            for t,i in unresolved.items():say(f'unresolved intent {t} ({i.payload.get("role")}, {i.payload.get("partition")}): counted at its planned slots and {float(i.payload.get("reservation_su",0)):.2f} SU')
            specs,supersedes=plan(snap)
            self.H.point('planned')
            self.check_fault(specs);self.malformed_check(specs)
            cnt=counts(snap,ev,unresolved);lim=limits(self.res,self.cap);k=sum_slots(specs);normal=any(sp.normal for sp in specs)
            if self.prof.name=='symmetry':
                say('counts '+json.dumps({cl:f'{cnt["classes"][cl]}+{k.get(cl,0)}/{lim[cl]}'for cl in self.prof.slot_classes})+
                    f'; c8d2- AMD-pool nodes {cnt["detectors"]["c8d2_amd_nodes"]}; both sessions at most '
                    f'{self.res.amd_total_now()if self.res.mode=="reservation"else "-"} (H7/H11); Intel defq/debugq outside the cap')
            else:
                say('counts '+json.dumps({cl:f'{cnt["classes"][cl]}+{k.get(cl,0)}/{lim[cl]}'for cl in budget.SLOT_CLASSES})+
                    f'; user shared jobs {cnt["detectors"]["user_shared"]} (Slurm per-user limit 64)')
            v=violations(cnt,lim,self.res,k,normal)                                 # step 3
            if v:
                n=largest(family,nmax if nmax is not None else len(specs),lambda f:not violations(cnt,lim,self.res,sum_slots(f),any(x.normal for x in f)))if family else 0
                raise Refuse(65,'refused by admission: '+'; '.join(m for _,m in v)+f'. Largest admissible N = {n}; binding share: {", ".join(sorted({c for c,_ in v}))}')
            self.H.point('rules')
            lines=ev.lines();cur=lines[self.line]['total'];own=lines[self.line]['own'];new=sum(sp.reservation_su for sp in specs);proj=cur+new   # step 4
            sub=budget.site_cap(self.line,self.prof)
            say(f'{self.line} line: spent {lines[self.line]["spent"]:.2f}, live reservations {lines[self.line]["live"]:.2f}, unresolved intents '
                f'{lines[self.line]["intents"]:.2f}'+(f', other site {lines[self.line]["other_site"]:.2f} (C8_OTHER_SITE_SU as of {ledger.utc_iso(self.other["asof"])})'
                if self.other.get('text')else'')+f'; new reservations {new:.2f}; projected {proj:.2f} ({self.prof.unit} on {self.prof.name}; A1.3: SU and core-h count 1:1)'+
                (f'; this site\'s own {own+new:.2f} of its hard sub-cap {sub:.0f} (S2-004)'if sub is not None else''))
            why=budget.gate(self.line,proj,self.env,own=own+new,prof=self.prof)
            if why:
                extra=self.su_hint(family,nmax if nmax is not None else len(specs),specs,cur,own)
                raise Refuse(65,'refused by the SU gate: '+why+(f'; {extra}'if extra else''))
            self.H.point('su_gate')
            if dry_run:
                say('dry run: the line admits '+self.su_hint(family,nmax if nmax is not None else len(specs),specs,cur,own));say('dry run: nothing submitted');return 0
            self.estimates(specs)                                                   # step 5
            if pin is not None:pin(lock)   # S2-001: the campaign's first work admission pins its CPU vendor before any sbatch
            done=[]
            for i,sp in enumerate(specs):
                try:self.submit_one(led,sp,specs,i,snap)
                except Refuse:
                    if done:
                        if led.failed or lock.lost:
                            # A failed or short ledger append (or a lost lock) is followed by no further append (D.11
                            # step 5): the ledger keeps its torn bytes for the next holder to truncate, and these jobs,
                            # counted through their intents meanwhile, are adopted at the next admission (as in step 6).
                            say('job(s) '+', '.join(f'{x.job_id} ({x.role}, token {x.token})'for x in done)+' were submitted; their `submit` records '
                                'are not written because a ledger write failed (or the lock check did): the next admission adopts them')
                        else:   # provenance of the jobs already submitted (a failure here exits 74; they are adopted later)
                            self.records(led,done,specs,cnt,proj)
                        if any(x.kind=='lane'for x in done)and not any(x.kind=='merge'for x in done):
                            say('lane worker(s) '+','.join(x.job_id for x in done if x.kind=='lane')+' are live without a merge: run `lanes 0` once the problem is fixed')
                    raise
                done.append(sp)
            self.records(led,done,specs,cnt,proj)                                   # step 6
            self.H.point('submit_records')
            return self.resnapshot(led,done,supersedes,its)                         # step 7

    def su_hint(self,family,nmax,specs,cur,own=None)->str:
        cap,ask=budget.line_cap(self.line,self.env);room=(ask if ask is not None else cap)-cur;sub=budget.site_cap(self.line,self.prof)
        if sub is not None and own is not None:room=min(room,sub-own)   # this site's hard sub-cap (S2-004)
        if family is None:return f'room left in the line: {max(0.0,room):.2f} SU'
        n=largest(family,nmax,lambda f:sum(x.reservation_su for x in f)<=room+1e-9)
        lanes=[x for x in specs if x.kind=='lane'];merge=sum(x.reservation_su for x in specs if x.kind=='merge')
        if lanes:
            per=lanes[0].resolved['billing'];t=max(0.0,(room-merge)/(per*len(lanes)));q=int(t*4)/4
            return f'largest N at this lane time = {n}; largest lane time at N = {len(lanes)}: {int(q):d}:{int(round((q%1)*60)):02d}:00'
        return f'largest admissible N = {n}'

    def estimates(self,specs):
        """The partition's idle-node count and sbatch --test-only's start estimate (a failure ends the call, 69)."""
        for part in sorted({sp.resolved['partition']for sp in specs}):
            out=budget.query(['sinfo','-h','-p',part,'-o','%t %D'],self.env,'sinfo')
            idle=sum(int(l.split()[1])for l in out.splitlines()if len(l.split())==2 and l.split()[0]=='idle'and l.split()[1].isdigit())
            say(f'{part}: {idle} idle nodes')
        for sp in specs[:1]:
            argv=['sbatch','--test-only',*sp.user_tokens,*sp.tool_tokens,'--no-requeue']+([sp.script]if sp.script else[])
            env=budget.sched_env(sbatch_env(self.env,sp.env_extra))
            self.H.event('query',argv=argv)
            try:cp=budget.RUNNER(argv,env,self.H.setting('query_timeout',budget.QUERY_TIMEOUT))
            except (subprocess.TimeoutExpired,OSError)as e:raise Refuse(69,f'sbatch --test-only failed ({e}); nothing submitted')
            if cp.returncode:raise Refuse(69,f'sbatch --test-only failed (exit {cp.returncode}): {(cp.stderr or cp.stdout).strip()[-300:]}; nothing submitted')
            self.estimate=(cp.stderr or cp.stdout).strip()[-300:];say('start estimate: '+self.estimate)

    def submit_one(self,led,sp,specs,i,snap):
        guard_preflight()   # before the intent: a guard that cannot run leaves nothing written (64)
        t=led.new_token();sp.token=t;c=sp.c;p=sp.p
        name=f'c8d3-{sp.role}-{c}-{t}';comment=f'c8d3:{c}:{p}:{t}'
        deps=[]
        for d in sp.depends:
            if isinstance(d,tuple):
                j=specs[d[1]].job_id
                if j is None:continue
                deps.append(j)
            else:deps.append(str(d))
        sp.depends=deps
        r=sp.resolved
        intent=ledger.payload('intent',[t],token=t,name=name,comment=comment,role=sp.role,c=c,p=p,dir=str(sp.cdir),partition=r['partition'],nodes=r['nodes'],
                              cpus=r['cpus'],mem_mib=r['mem_mib'],time_s=r['time_s'],array=sp.array,task_count=sp.ntasks,billing=r['billing'],
                              reservation_su=sp.reservation_su,slots=sp.slots,line=self.line,pid=os.getpid(),mono=ledger.mono(),command=self.label,
                              kind_of_job=sp.kind,depends=deps,reservation=self.res.text,site=self.prof.name,unit=self.prof.unit)
        self.H.point('before_intent',role=sp.role)
        ino,off,n=led.append(intent)                                  # a failure exits 74; the torn bytes stay for the next holder
        self.H.point('intent_record',token=t)
        try:led.write_intent_file(intent,ino,off,n)
        except FileExistsError:raise Refuse(74,f'intent file {led.intent_path(t)} already exists; no sbatch for {t}')
        except ledger.WriteFailed as e:
            try:
                led.append(not_submitted(t,False,False,f'intent file write failed: {e}'))
                if led.intent_path(t).exists():led.rename_resolved(t)
            except Refuse:pass
            raise Refuse(74,f'{e}; no sbatch for {t}')
        self.H.point('intent_file',token=t)
        self.lock.check('sbatch')
        age=ledger.mono()-intent['mono']
        if age>AGE_LIMIT:
            led.append(not_submitted(t,False,False,f'age check: {age:.1f} s since the intent > {AGE_LIMIT} s'))
            led.rename_resolved(t)
            raise Refuse(69,f'{age:.0f} s passed between the intent of {t} and its launch (> {AGE_LIMIT} s, a stalled write or fsync); no sbatch')
        self.H.point('age_checked',token=t)
        deadline=int(intent['utc']-self.H.offset()+AGE_LIMIT)
        argv=launch_argv(sp,name,comment,deadline,standin=self.fault=='kill_during_launch')
        env=sbatch_env(self.env,sp.env_extra)
        self.H.event('launch',token=t,argv=argv)
        if self.fault=='kill_during_launch':
            subprocess.Popen(argv,env=env,stdin=subprocess.DEVNULL)
            time.sleep(5);os.kill(os.getpid(),signal.SIGKILL)
        self.H.point('launch',token=t)
        try:
            cp=budget.RUNNER(argv,env,LAUNCH_BACKSTOP);rc,out,err=cp.returncode,cp.stdout,cp.stderr
            jid,launched,amb,why=classify(rc,out or'',err or'')
        except subprocess.TimeoutExpired:
            rc,out,err=-9,'',f'launch backstop {LAUNCH_BACKSTOP} s expired';jid,launched,amb,why=classify(rc,out,err)
        except budget.NotStarted as e:   # HD17 (b): the wrapper never started (fork or exec failed), so no sbatch ran
            rc,out,err=None,'',str(e);jid,launched,amb,why=None,False,False,f'the launch wrapper `timeout` could not be started ({e}); no process ran, so sbatch was not started'
        except OSError as e:             # after the wrapper started: sbatch may have reached slurmctld
            rc,out,err=None,'',str(e);jid,launched,amb,why=None,True,True,f'the launch wrapper failed after it started ({e}); the job may exist'
        if jid is None:
            led.append(not_submitted(t,launched,amb,why,rc,err))
            if not amb:led.rename_resolved(t)
            raise Refuse(69,f'{sp.role}: {why}'+('; its intent stays unresolved and counted (slots until evidence or the user\'s decision, SU until evidence)'if amb else
                                                 '; its intent is resolved at zero cost'))
        sp.job_id=jid;say(f'submitted {name} as job {jid} ({sp.resolved["partition"]}, {sp.reservation_su:.2f} {self.prof.unit} reserved)')
        self.H.point('after_sbatch',token=t,job=jid)
        if self.fault=='kill_after_sbatch':os.kill(os.getpid(),signal.SIGKILL)

    def records(self,led,done,specs,cnt,proj):
        for sp in done:
            r=sp.resolved
            led.append(ledger.payload('submit',[sp.token],token=sp.token,job_id=sp.job_id,task_range=sp.array['tasks']if sp.array else None,
                                      name=f'c8d3-{sp.role}-{sp.c}-{sp.token}',comment=f'c8d3:{sp.c}:{sp.p}:{sp.token}',role=sp.role,c=sp.c,p=sp.p,dir=str(sp.cdir),
                                      partition=r['partition'],cpus=r['cpus'],mem_mib=r['mem_mib'],time_s=r['time_s'],reservation_su=sp.reservation_su,line=self.line,
                                      reservation=self.res.text,counts=cnt['classes'],su_projected=proj,su_approved=self.env.get('C8_SU_APPROVED'),
                                      depends=sp.depends,kind_of_job=sp.kind,start_estimate=getattr(self,'estimate',None),site=self.prof.name,unit=self.prof.unit,
                                      other_site=self.other.get('text'),
                                      package={'root':str(ROOT),'commit':PACKAGE_COMMIT,'slurm_submit_sha256':TOOL_SHA256}))

    def resnapshot(self,led,done,supersedes,its)->int:
        """Step 7: a fresh squeue re-evaluates step 3 with the call's jobs and intents counted."""
        acct=budget.q_account(self.env);user=budget.q_user(self.env)
        self.H.point('resnapshot')
        snap=budget.Snapshot(acct,user,[],[],self.prof)
        led_its=ledger.intent_state(led);unresolved={t:i for t,i in led_its.items()if i.unresolved and not i.hold}
        ev=budget.Evaluation(snap,led_its,self.other)
        cnt=counts(snap,ev,unresolved);lim=limits(self.res,self.cap)
        classes=set()
        for sp in done:classes|=set(sp.slots)
        normal=any(sp.normal for sp in done)or bool(supersedes)   # a superseded merge is cancelled only after the full re-check passes
        if normal:classes|=set(self.prof.capped_classes)
        v=violations(cnt,lim,self.res,{},normal,classes=classes)
        ids=[sp.job_id for sp in done]
        if not v:
            failed=[]
            for m in supersedes:
                if self.cancel_pending([m]):say(f'superseded pending merge {m} cancelled (it never became eligible)')
                else:failed.append(m)
            self.print_start(led,ids,done)
            if failed:   # a failed query ends the call (D.11): the superseded merge stays pending and counted
                raise Refuse(69,f'scancel of the superseded pending merge(s) {",".join(failed)} failed: they may still be pending (counted through '
                                'their intents until they resolve); the call\'s jobs were submitted; rerun `lanes 0` to retry')
            return 0
        say('re-snapshot violation: '+'; '.join(m for _,m in v))
        unknown=[]   # failed scancel or re-query: the state is unknown, so nothing is claimed cancelled (D.11: a failed query ends the call)
        normal_ids=[sp.job_id for sp in done if sp.normal and sp.kind!='merge']
        if normal_ids and not self.cancel_pending(normal_ids):unknown.append('scancel --state=PENDING '+','.join(normal_ids))
        state,ok=self.requery(ids)
        if not ok:unknown.append('the re-query (squeue, sacct -j)')
        for sp in done:
            if not(sp.normal and sp.kind!='merge'):continue
            st=state.get(sp.job_id,{})
            if unknown:
                say(f'job {sp.job_id} ({sp.role}): state after the failed cancel or re-query unknown (last seen {st.get("state")or "not seen"}); it may still be pending over the share')
            elif st.get('live')and st.get('state')!='PENDING':say(f'job {sp.job_id} ({sp.role}) had started: reported, left running')
            elif st.get('started'):say(f'job {sp.job_id} ({sp.role}) started, then cancelled')
            elif st.get('state')=='CANCELLED'or not st.get('live'):say(f'job {sp.job_id} ({sp.role}) cancelled while pending')
            else:
                unknown.append(f'job {sp.job_id} is {st.get("state")} after its cancel')
                say(f'job {sp.job_id} ({sp.role}) is still {st.get("state")} after `scancel --state=PENDING`: it may still be pending over the share')
        for sp in done:
            if sp.kind!='merge':continue
            live_deps=[]
            for d in sp.depends:
                if state.get(d,{}).get('live'):live_deps.append(d);continue
                lv=self.is_live(d)
                if lv is None:unknown.append(f'the live check of worker {d}');live_deps.append(d)   # unknown: keep the merge
                elif lv:live_deps.append(d)
            if live_deps:say(f'merge {sp.job_id} kept: worker(s) {",".join(live_deps)} live or of unknown state depend on it')
            elif self.cancel_pending([sp.job_id]):say(f'merge {sp.job_id} cancelled (no live worker depends on it)')
            else:unknown.append(f'scancel of merge {sp.job_id}');say(f'merge {sp.job_id}: scancel failed; it may still be pending')
        if not self.no_merge_check(done):unknown.append('the merge-coverage query')
        self.print_start(led,ids,done)
        if unknown:
            pend=[sp.job_id for sp in done if state.get(sp.job_id,{}).get('state')in(None,'PENDING')]
            raise Refuse(69,'the re-snapshot found a share violated after submission, and '+'; '.join(unknown)+' failed or left a job pending: state unknown. '
                            'Job(s) of this call that may still be pending: '+(', '.join(pend)or'none seen')+'; nothing is claimed cancelled. '
                            f'Check `squeue --all -u {self.prof.user}` and cancel them (scancel --state=PENDING <ids>) before any new submission')
        raise Refuse(65,'the re-snapshot found a share violated after submission; pending normal-QOS jobs of this call were cancelled')

    def cancel_pending(self,ids)->bool:
        try:budget.query(['scancel','--state=PENDING',*ids],self.env,'scancel');return True
        except Refuse as r:say(f'scancel failed: {r}');return False

    def requery(self,ids)->tuple[dict,bool]:
        """(state per job id, whether every query succeeded)."""
        out={}
        try:
            for q in budget.q_account(self.env)+budget.q_user(self.env):
                for i in ids:
                    if q.jobid==i or q.base==i:out.setdefault(i,{}).update(live=q.live or out.get(i,{}).get('live',False),state=q.state)
            txt=budget.query(['sacct','-X','-j',','.join(ids),'-P','-n','-o','JobID,State,Start'],self.env,'sacct -j')
            for line in txt.splitlines():
                f=line.split('|')
                if len(f)>=3 and f[0]in ids:
                    st=out.setdefault(f[0],{});st['started']=f[2].strip().upper()not in budget.NO_START;st.setdefault('state',f[1].split()[0]if f[1].strip()else'')
        except Refuse as r:say(f're-query failed: {r}');return out,False
        return out,True

    def is_live(self,jid)->bool|None:
        """True or False from the account snapshot; None when the query fails (state unknown)."""
        try:return any((q.jobid==jid or q.base==jid)and q.live for q in budget.q_account(self.env))
        except Refuse:return None

    def no_merge_check(self,done)->bool:
        """A live lane worker of the campaign on which no pending or running merge depends: say so (inherited). False
        when the query fails."""
        camps={sp.c for sp in done if sp.kind in('lane','merge')}
        if not camps:return True
        try:txt=budget.query(['squeue','--all','-u',self.prof.user,'-h','-r','-o','%i|%j|%T|%E'],self.env,'squeue dependencies')
        except Refuse as r:say(f'cannot check merges: {r}');return False
        rows=[l.split('|')for l in txt.splitlines()if l.count('|')>=3]
        for c in camps:
            workers=[r[0]for r in rows if budget.name_info(r[1])['c']==c and budget.base_role(budget.name_info(r[1])['role'])=='lane'and r[2]not in budget.FINISHED]
            covered=set()
            for r in rows:
                info=budget.name_info(r[1])
                if info['c']==c and budget.base_role(info['role'])=='merge'and r[2]in('PENDING','RUNNING','CONFIGURING'):covered|=set(re.findall(r'(\d+)',r[3]))
            bare=[w for w in workers if w not in covered]
            if bare:say(f'lane worker(s) {",".join(bare)} are live without a merge: run `lanes 0`')
        return True

    def print_start(self,led,ids,done):
        txt={}
        for what,argv in (('squeue --start',['squeue','--all','--start','-h','-j',','.join(ids)]),('sprio',['sprio','-j',','.join(ids)])):
            try:txt[what]=budget.query(argv,self.env,what).strip()
            except Refuse as r:txt[what]=f'failed (not fatal): {r}'
            say(f'{what}: {txt[what][-400:]}')
        try:led.append(ledger.payload('annotation',[sp.token for sp in done],about='start_estimate',job_ids=ids,**{k.replace(' ','_').replace('-',''):v for k,v in txt.items()}))
        except Refuse as r:say(f'annotation not recorded: {r}')

def run_raw(argv:list,env:dict)->int:
    import argparse
    p=ledger.Parser(prog='slurm_submit.py raw');p.add_argument('--role',required=True);p.add_argument('--dir',required=True)
    p.add_argument('--dry-run',action='store_true');p.add_argument('sbatch',nargs=argparse.REMAINDER)
    a=p.parse_args(argv)
    toks=a.sbatch[1:]if a.sbatch[:1]==['--']else a.sbatch
    call=Call(env,'raw '+a.role)
    spec=raw_spec(a.role,a.dir,toks,env,call.s,call.line);call.check_fault([spec]);call.malformed_check([spec])   # input checks before the lock (64)
    return call.run(lambda snap:([spec],[]),family=lambda n:[spec][:n],dry_run=a.dry_run)


# ================================================================================================================
# Campaign entry points (Stage 3a; PLAN D.9, D.10, D.11): `lanes N`, `submit`, `window`, `resubmit`, `release`.
CAMPAIGN_COMMANDS=('submit','window','resubmit','lanes','release')
LANE_TIME_MAX=47*3600+30*60
LANE_NODE_CORES=128

class Campaign:
    """The planned campaign C8_RUN ($C8_ROOT/runs/<name>), verified against its pinned tools and inputs."""
    def __init__(self,env:dict,s:ledger.Settings):
        run=env.get('C8_RUN')
        if not run:raise Refuse(64,'set C8_RUN to the planned campaign directory ($C8_ROOT/runs/<name>)')
        self.cdir=check_dir(run,s)
        if not (self.cdir/'manifest.json').is_file():raise Refuse(64,f'no manifest.json in C8_RUN={self.cdir}')
        import production as prod
        self.prod=prod
        try:self.m,self.I,self.mh,_=prod.verify_base(self.cdir,check_executable=False)
        except (ValueError,OSError)as e:raise Refuse(64,f'cannot verify the plan in {self.cdir}: {e}')
        self.c=ledger.dir_sha12(self.cdir);self.logs=self.cdir/'slurm_logs'
        self.job_env={'C8_RUN':str(self.cdir),'C8_PACKAGE':str(ROOT)}
        if env.get('C8_ENV_SETUP'):self.job_env['C8_ENV_SETUP']=env['C8_ENV_SETUP']
    def mine(self,snap):return [q for q in snap.live_lines()if q.ours and q.info['c']==self.c]

def base_role(q)->str:return budget.base_role(q.info['role'])

def tokens_of(env:dict,name:str,default:str)->list:
    text=env.get(name,default)
    if '\n'in text:raise Refuse(64,f'{name} must be a single line')
    try:return shlex.split(text)
    except ValueError as e:raise Refuse(64,f'{name} cannot be parsed: {e}')

def hms(sec:float)->str:
    sec=int(math.ceil(sec));d,r=divmod(sec,86400);h,r=divmod(r,3600);m,s_=divmod(r,60)
    return (f'{d}-'if d else'')+f'{h:02d}:{m:02d}:{s_:02d}'

def auto_lane_time(m:dict,entries:list,n:int,cores:int=LANE_NODE_CORES,f:float=1.0,tmax:int=LANE_TIME_MAX)->dict:
    """D.10: T = the plan's predicted wall at the requested N, rounded up to 15 min: max(1.5 W + 0.25 h, need_max + 0.25 h),
    W = sum est x f_class / (N x cores x 0.9) over the remaining indices, need_max the largest index's deadline need
    (est x f_class / (w x 0.9) x 1.5 + 300 s, w the plan's lane width). f_class = 1 on the cost model's own CPU (Expanse:
    the compute nodes, EPYC 7742; an unknown class is 1.5 at the lane's own deadline). At most 47:30:00 on Expanse (128
    cores per node); on symmetry (lane_shape) 64 cores per AMD node with f_class 1, which holds because the CPU pin
    (amd_exclusions; slurm/site.sh c8_cpu_guard) puts every amdq lane on the model's CPU (EPYC 7543), and 40 per Intel
    node with 1.5, at most 23:30:00."""
    import lanes
    w=m['threads']
    W=sum(e*f for _,e in entries)/(max(1,n)*cores*lanes.EFFICIENCY)if entries else 0.
    need=max((e*f/(w*lanes.EFFICIENCY)*1.5+300 for _,e in entries),default=0.)
    T=max(1.5*W+900,need+900);T=math.ceil(T/900)*900
    return {'seconds':min(T,tmax),'W':W,'need_max':need,'capped':T>tmax}

def lane_shape(prof:budget.SiteProfile,site_tokens:list)->dict:
    """The lane node of C8_SBATCH_ARGS's partition: physical cores, f_class (1 on the model's CPU: Expanse compute, and
    symmetry amdq/amddebugq through the CPU pin, amd_exclusions; 1.5 for a class the cost model has not measured) and
    the longest lane time (Expanse 47:30:00, symmetry 23:30:00)."""
    opts,_=parse_options(site_tokens,'C8_SBATCH_ARGS',positional=False,allow=CAMPAIGN_ALLOW)
    part=next((v for n_,v in reversed(opts)if n_=='partition'),None)
    info=prof.partitions.get(part)or{}
    return {'partition':part,'cores':int(info.get('cores',LANE_NODE_CORES)),'f':float(prof.f_class.get(part,1.5)),'tmax':prof.lane_time_max}

def snapshot_text(snap)->str:
    """'%200k|%K|%T|%i' lines of the user's jobs from the admission snapshot (lanes.release_stale's input)."""
    return '\n'.join(f'{q.comment or ""}|{q.task if q.task is not None else "N/A"}|{q.state}|{q.jobid}'for q in snap.user)+'\n'

def queue_text(snap)->str:
    """production.parse_queue's '%i|%K|%T|%200j|%200k' lines from the admission snapshot."""
    return '\n'.join(f'{q.jobid}|{q.task if q.task is not None else "N/A"}|{q.state}|{q.name}|{q.comment or ""}'for q in snap.user)+'\n'

def merge_path(m:dict)->str:
    return 'subset-check (no coefficient assembly)'if m['campaign_role']=='pilot_subset'else 'assemble'

def split_flags(argv:list,flags=('--dry-run',))->tuple[list,set]:
    """The tool's own flags may stand anywhere before a '--'; everything else is positional or an sbatch option."""
    if '--'in argv:i=argv.index('--');head,tail=argv[:i],argv[i:]
    else:head,tail=argv,[]
    return [x for x in head if x not in flags]+tail,{x for x in head if x in flags}

def cmd_lanes(argv:list,env:dict)->int:
    import argparse,lanes
    argv,fl=split_flags(argv)
    p=ledger.Parser(prog='slurm_submit.py lanes');p.add_argument('n',type=int)
    p.add_argument('sbatch',nargs=argparse.REMAINDER);a=p.parse_args(argv);a.dry_run='--dry-run'in fl
    if a.n<0:raise Refuse(64,'lanes N needs N >= 0')
    call=Call(env,f'lanes {a.n}');camp=Campaign(env,call.s);m=camp.m
    why=lanes.lane_refusal(m)
    if why:raise Refuse(65,why+'; nothing submitted')
    prog=camp.prod.job_progress(camp.cdir,m);entries=lanes.queue_entries(camp.cdir,m,prog)
    prof=call.prof;extra=a.sbatch[1:]if a.sbatch[:1]==['--']else a.sbatch
    site=tokens_of(env,'C8_SBATCH_ARGS',prof.lane_args)+list(extra);merge=tokens_of(env,'C8_MERGE_SBATCH_ARGS',prof.merge_args)
    shape=lane_shape(prof,site);xs=amd_exclusions(prof,env)   # 64 before the session lock: nothing written
    lt=env.get('C8_LANE_TIME','auto');auto=auto_lane_time(m,entries,a.n,shape['cores'],shape['f'],shape['tmax'])
    if lt=='auto':lane_time=hms(auto['seconds'])
    else:
        t=budget.parse_duration(lt)
        if t is None or t<=0:raise Refuse(64,f'C8_LANE_TIME={lt!r} is not a Slurm time')
        if t>shape['tmax']:raise Refuse(64,f'C8_LANE_TIME={lt} exceeds {hms(shape["tmax"])} on {prof.name}')
        if t<auto['need_max']:say(f'warning: C8_LANE_TIME={lt} is below the largest index need {hms(auto["need_max"])}: lanes skip indices that do not fit')
        lane_time=lt
    mem=env.get('C8_LANE_MEM',prof.lane_mem);drill=None
    if env.get('C8_LANE_DRILL')=='1':
        # D.9 drill mode: test-only plans, Expanse shared or debug (symmetry amddebugq or debugq), no --exclusive,
        # -c C8_LANE_CPUS (2-16), --mem <= 2G x CPUs, --no-requeue
        if not m['test_only']:raise Refuse(64,'C8_LANE_DRILL=1 is for test-only plans only (the lane drills)')
        c=env.get('C8_LANE_CPUS','')
        if not c.isdigit()or not 2<=int(c)<=16:raise Refuse(64,f'drill mode needs C8_LANE_CPUS in 2..16 (got {c!r})')
        drill=int(c);part=shape['partition']
        if part not in prof.drill_partitions:raise Refuse(64,f'drill mode runs on {" or ".join(prof.drill_partitions)} (C8_SBATCH_ARGS partition {part!r})')
        mm=budget.mem_mib(mem)
        if mm is None or mm>2048*drill:raise Refuse(64,f'drill mode: C8_LANE_MEM={mem} exceeds 2G x {drill} CPUs')
    say(f'lanes {a.n}: {len(entries)} incomplete indices, {sum(e for _,e in entries)/3600:.1f} estimated core-hours; lane time {lane_time} '
        f'({"auto: " if lt=="auto"else""}W {auto["W"]/3600:.2f} h, largest index need {auto["need_max"]/3600:.2f} h); reservation {call.res.text}; '
        f'the merge will take the path: {merge_path(m)}')
    worker=str(ROOT/'slurm/lane_worker.sh');mscript=str(ROOT/'slurm/merge.sh');state={}
    def plan(snap):
        mine=camp.mine(snap)
        arrays=sorted({q.base for q in mine if base_role(q).startswith('off')})
        if arrays:raise Refuse(65,f'array element(s) {",".join(arrays)} of this campaign are live: lane mode and array mode are not mixed; wait for them, or use resubmit')
        live=sorted({q.jobid for q in mine if base_role(q)=='lane'})
        sup=sorted({q.jobid for q in mine if base_role(q)=='merge'and q.state=='PENDING'})
        ents=entries
        if not a.dry_run:
            d=lanes.release_stale(camp.cdir,snapshot_text(snap),snap.utc)
            for idx,job,st in d['release']:say(f'released stale claim of index {idx} (job {job}, {st})')
            ents,bad=lanes.rebuild_queue(camp.cdir,m)
            if bad:say(f'done markers of incomplete indices removed: {bad} (lanes/done_invalidated.jsonl)')
            camp.logs.mkdir(parents=True,exist_ok=True)
        k=a.n if ents else 0
        if not ents:say('every index is complete; submitting only the merge')
        state['specs']=lane_specs(camp.cdir,k,lane_time,site,mem,merge,env,call.line,live,worker,mscript,camp.logs,
                                  {**camp.job_env,**({'C8_LANE_DRILL':'1','C8_LANES':env.get('C8_LANES','1')}if drill else{})},drill,
                                  live_partitions=sorted({q.partition for q in mine if base_role(q)=='lane'}),exclude=xs)
        state['k']=k;state['vendor']=vendor_check(prof,camp.cdir,state['specs'],mine)   # S2-001 (64 on another vendor)
        return state['specs'],sup
    family=lambda k:[sp for sp in state['specs']if sp.kind=='lane'][:k]+[sp for sp in state['specs']if sp.kind=='merge']
    rc=call.run(plan,family=family,nmax=a.n,dry_run=a.dry_run,pin=lambda lock:pin_vendor(camp.cdir,state['vendor'],prof,call.label,lock,camp.mh))
    if not a.dry_run:say(f'status: {sys.executable} -B {ROOT/"tools/production.py"} status {camp.cdir}   (more workers: slurm_submit.py lanes N)')
    return rc

def array_site(env:dict,m:dict,extra:list)->list:
    """The array element options: C8_SBATCH_ARGS (default -A yun124 -p shared on Expanse, -p amdq on symmetry; slurm/run_array.sh sets --nodes=1
    --ntasks=1 in its #SBATCH lines, D.10) and the caller's, then the
    plan's lane width, memory suggestion (1.5 x max est_peak_bytes + 1 GB; a smaller user value is refused, a larger one
    accepted; A-ORC-5) and suggested time (a bootstrap plan has none: --time must be given)."""
    toks=tokens_of(env,'C8_SBATCH_ARGS',budget.profile(env).array_args)+list(extra)
    opts,_=parse_options(toks,'array options',positional=False,allow=CAMPAIGN_ALLOW)
    names={n for n,_ in opts};sug=int(m['estimates']['mem_suggestion_mb'])
    for n,v in opts:
        if n=='mem':
            got=budget.mem_mib(v)
            if got is None or got<sug:raise Refuse(64,f'--mem={v} is below the plan\'s suggestion {sug}M (1.5 x the largest est_peak_bytes + 1 GB, A-ORC-5)')
        if n=='mem-per-cpu':raise Refuse(64,'array elements take --mem (the plan\'s suggestion or more), not --mem-per-cpu')
    add=[]
    if 'cpus-per-task'not in names:add.append(f'--cpus-per-task={m["threads"]}')
    if 'mem'not in names:add.append(f'--mem={sug}M')
    if 'time'not in names:
        t=m['estimates'].get('suggested_time_seconds')
        if not t:raise Refuse(64,'the plan has no suggested wall time (bootstrap basis): give --time in C8_SBATCH_ARGS or as an option')
        add.append(f'--time={hms(t)}')
    return toks+add

def array_call(env:dict,label:str,mode:str,argv:list)->int:
    import argparse
    argv,fl=split_flags(argv)
    p=ledger.Parser(prog=f'slurm_submit.py {mode}')
    if mode=='window':p.add_argument('window')
    p.add_argument('sbatch',nargs=argparse.REMAINDER);a=p.parse_args(argv);a.dry_run='--dry-run'in fl
    call=Call(env,label);camp=Campaign(env,call.s);m=camp.m;prod=camp.prod
    extra=a.sbatch[1:]if a.sbatch[:1]==['--']else a.sbatch
    site=array_site(env,m,extra);merge=tokens_of(env,'C8_MERGE_SBATCH_ARGS',call.prof.merge_args)
    size=int(env.get('C8_MAX_ARRAY',prod.MAX_ARRAY));thr=int(env.get('C8_THROTTLE','8'))
    if size<1 or thr<1:raise Refuse(64,'C8_MAX_ARRAY and C8_THROTTLE must be positive')
    work=str(ROOT/'slurm/run_array.sh');mscript=str(ROOT/'slurm/merge.sh');state={}
    xs=amd_exclusions(call.prof,env)   # the AMD-pool exclusions (64 before the session lock: nothing written)
    array_vendor(env,call.prof,m.get('plan_role'),site,merge,work,mscript)   # symmetry: Intel only for campaign plans (64, before the lock)
    def plan(snap):
        mine=camp.mine(snap)
        live=sorted({q.jobid for q in mine if base_role(q)=='lane'})
        if live:raise Refuse(65,f'lane worker job(s) {",".join(live)} of this campaign are live: lane mode and array mode are not mixed; add workers with lanes N, or wait')
        deps=[]
        if mode=='submit':wins=[{'offset':off,'array':f'0-{min(size,len(m["jobs"])-off)-1}'}for off in range(0,len(m['jobs']),size)]
        elif mode=='window':
            off,_,rng=a.window.partition(':')
            if not off.isdigit()or not rng:raise Refuse(64,'usage: window OFFSET:ARRAY')
            ids=budget.parse_tasks(rng)
            if any(int(off)+i>=len(m['jobs'])or i>=size for i in ids):raise Refuse(64,f'window {a.window} is outside the plan ({len(m["jobs"])} jobs) or wider than C8_MAX_ARRAY')
            wins=[{'offset':int(off),'array':rng}]
        else:
            d=prod.recovery_plan(camp.cdir,queue_text(snap),size)
            if d['refuse']:raise Refuse(d['refuse']['code'],d['refuse']['message'])
            if d['live_missing_not_resubmitted']:say(f'missing indices {prod.ranges(d["live_missing_not_resubmitted"])} are still live; not resubmitted')
            wins=d['arrays'];deps=d['merge_waits_on_live_tasks']
            if not wins:say('no work to resubmit; the merge waits for the live elements')
        if not a.dry_run:camp.logs.mkdir(parents=True,exist_ok=True)
        specs=array_specs(camp.cdir,[(w['offset'],f'{w["array"]}%{thr}')for w in wins],site,merge,env,call.line,work,mscript,camp.logs,camp.job_env,deps,exclude=xs)
        if mode=='window':specs=[sp for sp in specs if sp.kind!='merge']
        # S2-001: the new windows and merge, and every live job of the campaign (the elements a resubmit's merge waits on,
        # also when it brings no new window), on the campaign's one CPU vendor (64 otherwise)
        state['vendor']=vendor_check(call.prof,camp.cdir,specs,mine)
        state['specs']=specs;return specs,[]
    family=lambda k:([sp for sp in state['specs']if sp.kind=='array'][:k]+[sp for sp in state['specs']if sp.kind=='merge'])if k else[]
    return call.run(plan,family=family,nmax=None,dry_run=a.dry_run,pin=lambda lock:pin_vendor(camp.cdir,state['vendor'],call.prof,call.label,lock,camp.mh))

def cmd_release(argv:list,env:dict)->int:
    """D.9 held jobs, released at most once, under the session lock (S2-006): the ledger must exist and read clean (with a
    readable intent state) before any scheduler call (69, 74 otherwise: nothing released); a `release_attempt`
    annotation is appended and fsynced BEFORE the scontrol `release` command (a failed append: 74, nothing released);
    the outcome is then reconciled with squeue and recorded (`released`, or `release_unconfirmed` when the job still
    shows the hold or the re-query fails); an ambiguous `scontrol` (a failure or timeout) is recorded as
    `release_unknown` and counts as the one allowed attempt (69). Any later hold of a job with an attempt on record is cancelled, never released again (it
    never ran; lanes N resubmits); any other held c8d3- job is reported and left alone."""
    import lanes
    if len(argv)!=1 or not re.fullmatch(r'\d+(_\d+)?',argv[0]):raise Refuse(64,'usage: slurm_submit.py release JOBID')
    jid=argv[0];s=ledger.Settings(env);budget.check_env(env)
    with ledger.SessionLock(s,f'release {jid}')as lock:
        led=ledger.Ledger(s,lock);led.read(writer=True)
        if led.missing:raise Refuse(69,f'the ledger {s.ledger_path} is missing: no scheduler command was run and nothing released (a missing ledger is a '
                                       'repair block until the user decides, D.12; `tools/ledger.py rebuild`)')
        ledger.intent_state(led)   # an unusable intent state refuses (69) here too, before any scheduler call
        sq=['squeue','--all','-u',budget.profile(env).user,'-h','-r','--states=all','-o','%i|%T|%r|%j']
        txt=budget.query(sq,env,'squeue (held jobs)')
        held={h['jobid']:h for h in lanes.held_jobs(txt)}
        line=next((l for l in txt.splitlines()if l.split('|')[0].strip()==jid),None)
        if line is None:raise Refuse(69,f'job {jid} is not in squeue; nothing done')
        f=[x.strip()for x in line.split('|')]
        if not f[3].startswith('c8d3-'):raise Refuse(64,f'job {jid} ({f[3]}) is not a c8d3- job; this package never touches it')
        tok=(budget.name_info(f[3])['token']or'');role=budget.base_role(budget.name_info(f[3])['role']);toks=[tok]if tok else[]
        if jid not in held:
            say(f'job {jid} ({f[3]}) is {f[1]} with reason {f[2]!r}: not a `{lanes.HELD_REASON}` hold; reported, nothing done');return 69 if 'held'in f[2].lower()else 0
        if not(role=='lane'or role.startswith('off')):raise Refuse(64,f'job {jid} is a {role} job: only lane workers and array tasks are released')
        prior=[r for r in led.records if r['kind']=='annotation'and r.get('about')=='held_release'and r.get('job_id')==jid]
        if not prior:   # the one allowed release: its attempt is durable before the scheduler is touched
            led.append(ledger.payload('annotation',toks,about='held_release',job_id=jid,action='release_attempt',reason=f[2]))
            try:budget.query(['scontrol','release',jid],env,'scontrol: release of a held job')
            except Refuse as r:
                try:led.append(ledger.payload('annotation',toks,about='held_release',job_id=jid,action='release_unknown',error=str(r)[-500:]))
                except Refuse as w:say(f'outcome not recorded ({w}); the release_attempt record already counts')
                raise Refuse(69,f'the scontrol `release` of {jid} failed or timed out ({r}): its outcome is unknown and counts as the one allowed release; a '
                                'later hold of this job is cancelled')
            try:   # reconcile: the job must no longer show the hold
                again=next((h for h in lanes.held_jobs(budget.query(sq,env,'squeue (after the release)'))if h['jobid']==jid),None)
                act,why=('release_unconfirmed',f'squeue still shows it held ({again["reason"]})')if again else('released',None)
            except Refuse as r:act,why='release_unconfirmed',f'the re-query failed ({r})'
            led.append(ledger.payload('annotation',toks,about='held_release',job_id=jid,action=act,reason=f[2],**({'why':why}if why else{})))
            say(f'released held job {jid} ({f[3]})'+(f'; {why}'if why else'')+'; the attempt is recorded, and a second hold of it is cancelled');return 0
        budget.query(['scancel',jid],env,'scancel (second hold)')
        led.append(ledger.payload('annotation',toks,about='held_release',job_id=jid,action='cancelled',reason=f[2],
                                  prior=[r.get('action')for r in prior]))
        say(f'job {jid} was held again after a release attempt ({", ".join(str(r.get("action"))for r in prior)}): cancelled (it never ran); resubmit with lanes N');return 0

def main(argv,env)->int:
    if not argv or (argv[0]!='raw'and argv[0]not in CAMPAIGN_COMMANDS):print(__doc__,file=sys.stderr);return 64
    try:
        if argv[0]=='raw':return run_raw(argv[1:],env)
        if argv[0]=='lanes':return cmd_lanes(argv[1:],env)
        if argv[0]=='release':return cmd_release(argv[1:],env)
        return array_call(env,argv[0]+(' '+argv[1]if argv[0]=='window'and len(argv)>1 else''),argv[0],argv[1:])
    except Refuse as r:
        print('C8: '+str(r),file=sys.stderr);return r.code
    except OSError as e:return ledger.os_error_exit(e)

if __name__=='__main__':sys.exit(main(sys.argv[1:],dict(os.environ)))
