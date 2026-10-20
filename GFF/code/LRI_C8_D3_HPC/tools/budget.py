#!/usr/bin/env python3
"""SU budget and slot accounting of LRI_C8_D3_HPC from scheduler truth plus durable submission intents (plan HD17,
D.11, D.12; host decisions H-e, H-f, H-g, H-h).

  budget.py [--json]    every line (dev, pilot, production): spent, live reservations, unresolved intents, totals

The numbers come from `squeue --all -u <user> -h -r --states=all -O ...` (queried first), then two `sacct` queries
since BUDGET_EPOCH (unfiltered, and state-selected), plus the ledger and intents/ (both copies of every intent); the
user is zzheng8 on Expanse and zzheng1 on symmetry (C8_SITE=symmetry; Amendment A1). No other file of the package is
opened. Standalone, this tool reads without the session lock and records nothing: it applies
the evidence rules in memory (an intent that terminal or never-started evidence resolves is shown resolved, at that
rule's charge); admission (tools/slurm_submit.py) calls the same code under the lock and records the resolutions.

One billing function (HD17) prices proposed jobs, intents and scheduler records: SU per hour = 128 per node on
`compute`, max(CPUs, ceil(mem_GiB/2)) on `shared` and `debug`; a reservation is that value x the time limit in hours.
On symmetry (A1.3) the unit is the allocated core-hour: whole nodes (every admitted partition is EXCLUSIVE), 64 per
AMD node and 80 per Intel node (Slurm's cpu= of AllocTRES), or the allocated cpu of a record when larger. Both units
count 1:1 in one dev line under one cap (5,000; stop and ask at 4,000), one pilot line and one production line (user
decision 2026-10-08: C8_BUDGET_LINE=production under the user-approved C8_PRODUCTION_SU_CAP, roles prod_<role>, the way
the pilot line has C8_PILOT_SU_CAP and pilot_<role>; LINE_PREFIX classifies a job by its name). The dev cap is enforced as
hard per-site sub-caps (SITE_CAPS: 2,500 on each site, S2-004), each from the site's own ledger and scheduler alone;
the joint checks add the other site's own line totals from C8_OTHER_SITE_SU and are soft, as fresh as that carry
(required on both real sites, C8_SITE=expanse and symmetry; an explicit dev=0;pilot=0 is allowed; at most 24 h old; its
production= key is optional, 0 when absent, so a carry of an older export still parses). The value to carry is this tool's `own` total (spent + live
reservations + unresolved intents, without the other site's), printed ready to paste as the `carry` line. Its `asof`
is the time of this tool's first read (the intent-file scan, before the ledger and the scheduler queries): every
submission of this site whose intent was written before `asof` is in the carry, so one it misses was written after
`asof`, which the refresh rule (refresh the carry after every submission on the other site) covers.

Exit codes: 64 invalid settings, 69 query failure or a ledger in need of repair. Python 3.10+ standard library only.
"""
from __future__ import annotations
import argparse,calendar,json,math,os,re,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse
import ledger
from ledger import NAME_RE,COMMENT_RE

BUDGET_EPOCH=1791000000   # 2026-10-03T00:00:00-04:00 (EDT) = 2026-10-02T21:00:00 PDT, the plan's start (HD17); tests replace it
SITE_USER='zzheng8'
SITE_ACCOUNT='yun124'
QUERY_TIMEOUT=60          # every scheduler query (D.11); sbatch runs under `timeout -s KILL 120`
DEV_ASK=4000.0            # U4: stop and ask (joint line, both sites: a soft check through the carry C8_OTHER_SITE_SU)
DEV_CAP=5000.0            # U4: hard cap of the joint line, enforced as the per-site sub-caps of SITE_CAPS (their sum)
# The hard per-site sub-caps of every line that spans both sites (S2-004; host decision 2026-10-06, per-site caps
# instead of a shared admission coordinator). Each site enforces its own as a HARD limit from its own ledger and
# scheduler (spent + live reservations + unresolved intents + the new jobs), with no carry involved, so neither a stale
# carry nor two concurrent admissions on the two sites can take the joint line over its cap: the dev line's 5,000
# (Expanse SU and symmetry core-hours count 1:1) is 2,500 on each site, their sum DEV_CAP. A transfer between the two
# sub-caps is a code change of this table. The pilot line has no value yet (C8_PILOT_SU_CAP is approved per pilot), so
# it has no split; it keeps its joint check through the carry. The production line (user decision 2026-10-08) likewise:
# C8_PRODUCTION_SU_CAP is approved per production, no split, its joint check through the carry's production= key.
SITE_CAPS={'dev':{'expanse':2500.0,'symmetry':2500.0},'pilot':None,'production':None}
# The budget lines and the role prefix of each non-dev line: the tool (tools/slurm_submit.py check_role) prefixes every
# role of a C8_BUDGET_LINE=pilot or production admission and refuses a caller's role that carries a prefix, so the name
# alone classifies a job (name_info): pilot_<role> -> pilot, prod_<role> -> production, any other parseable name -> dev.
LINES=('dev','pilot','production')
LINE_PREFIX={'pilot':'pilot_','production':'prod_'}
LINE_CAP_ENV={'pilot':'C8_PILOT_SU_CAP','production':'C8_PRODUCTION_SU_CAP'}   # the user-approved cap of each non-dev line
def line_of(role:str)->str:
    """The budget line of a (prefixed) role: the line whose prefix it carries, else dev."""
    return next((L for L,x in LINE_PREFIX.items()if (role or'').startswith(x)),'dev')
def base_role(role:str)->str:
    """A role without its line prefix (pilot_lane, prod_lane -> lane)."""
    r=role or'';x=LINE_PREFIX.get(line_of(r))
    return r[len(x):]if x else r
CLUSTER_SELECTORS=('SBATCH_CLUSTERS','SLURM_CLUSTERS','SQUEUE_CLUSTERS','SACCT_CLUSTERS')
LIVE=frozenset('PENDING RUNNING CONFIGURING COMPLETING SUSPENDED STOPPED REQUEUED REQUEUE_HOLD REQUEUE_FED RESIZING SIGNALING STAGE_OUT SPECIAL_EXIT'.split())
FINISHED=frozenset('COMPLETED CANCELLED FAILED TIMEOUT NODE_FAIL PREEMPTED BOOT_FAIL DEADLINE OUT_OF_MEMORY REVOKED REQUEUED'.split())
SACCT_LIVE=frozenset(('PENDING','RUNNING','SUSPENDED'))   # every other sacct state is a finished attempt (HD17 "Charges")
OTHERS_PENDING=frozenset(('PENDING','REQUEUE_HOLD','REQUEUE_FED','SPECIAL_EXIT'))  # not running: other users' jobs only
NO_START=frozenset(('N/A','NONE','UNKNOWN',''))
STATE_SELECT='CA,CD,F,TO,NF,OOM,PR,BF,DL,RQ'
LIVE_STATES_ARG='PD,R,CF,CG,S,ST,RQ,RH,RF,RS,SI,SO,SE'
ACCT_FMT='%i|%F|%u|%P|%q|%T|%100j|%D|%C|%m|%l|%r|%200k'
ACCT_KEYS=('jobid','base','user','partition','qos','state','name','nodes','cpus','minmem','timelimit','reason','comment')
USER_FIELDS=(('JobArrayID',40,'jobid'),('ArrayJobID',20,'base'),('UserName',30,'user'),('Partition',30,'partition'),('QOS',30,'qos'),('State',30,'state'),
             ('Name',200,'name'),('NumNodes',10,'nodes'),('NumCPUs',10,'cpus'),('MinMemory',20,'minmem'),('TimeLimit',20,'timelimit'),('Reason',100,'reason'),
             ('Comment',200,'comment'),('tres-alloc',200,'tres'),('StartTime',30,'start'),('TimeUsed',20,'used'),
             # the attempt fields: Slurm counts every requeue in RestartCnt, resets SubmitTime and delays EligibleTime to a
             # later begin time (rule (c) from this snapshot alone needs them; "Charges" counts the attempts sacct lacks)
             ('RestartCnt',10,'restarts'),('SubmitTime',30,'submit'),('EligibleTime',30,'eligible'))
USER_FMT=','.join(f'{n}:{w}'+('|'if i<len(USER_FIELDS)-1 else'')for i,(n,w,_) in enumerate(USER_FIELDS))
SACCT_FIELDS='JobID,JobIDRaw,JobName,Partition,State,Submit,Start,ElapsedRaw,Timelimit,AllocTRES,ReqTRES'
SLOT_CLASSES=('normal_run','normal_sub','account','nodes','shared','debug')

class NotStarted(OSError):
    """The command was never started: creating its pipes, the fork or the exec failed (a missing or non-executable
    program, EAGAIN, ENOMEM). No process of it ran, so it did nothing (HD17 (b): a launch wrapper that never started
    launched no sbatch). Any OSError after the start is a plain OSError: the command may have run."""

def _run(argv,env,timeout):
    """subprocess.run(argv, capture_output=True, timeout=timeout), with a failure to start the command raised as
    NotStarted. Scheduler output is decoded as UTF-8 with replacement: a non-UTF-8 byte in any user's job name, comment
    or reason can neither crash admission nor skip a step after `sbatch`."""
    try:p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',env=env)
    except OSError as e:raise NotStarted(e.errno,f'cannot start {argv[0]}: {e.strerror or e}',e.filename)from e
    with p:
        try:out,err=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:p.kill();p.wait();raise
        except BaseException:p.kill();raise
        rc=p.poll()
    return subprocess.CompletedProcess(argv,rc,out,err)
RUNNER=_run   # module seam: the in-process fake Slurm of the tests replaces it

# ----------------------------------------------------------------------------------------------------------------
# Sites (Amendment A1). One profile per real site: who the snapshots name, the partitions admission admits, the billing
# function and the slot classes the reservation caps. C8_SITE=symmetry selects SYMMETRY; expanse, fake (the Mac fakes
# emulate Expanse) and unset select EXPANSE.
class SiteProfile:
    def __init__(self,**kw):self.__dict__.update(kw)
    # -- billing
    def billing_value(self,partition:str,nodes:int,cpus:int,mem:float)->float:
        if self.name=='expanse':
            parts=set(str(partition).split(','))
            v=0.0
            if 'compute'in parts:v=128.0*max(1,int(nodes or 1))
            if parts-{'compute'}or not parts:v=max(v,float(max(int(cpus or 0),math.ceil((mem or 0)/2048-1e-9))))
            return v
        # symmetry (A1.3): allocated cores x elapsed hours. Every admitted partition is EXCLUSIVE, so a job holds whole
        # nodes; a partition list is priced at its largest node (an unknown partition at 128 per node).
        v=float(int(cpus or 0))
        for p in str(partition).split(','):
            n=self.node_cpus.get(p,128)
            v=max(v,float(cpus or 0)if n is None else float(n*max(1,int(nodes or 1))))
        return v
    def tres_billing(self,partition,tres:dict)->float|None:
        """A scheduler record's billing value from its cpu, mem and node (Expanse: or billing/3600 when larger; symmetry:
        or its allocated cpu when larger, which a requested cpu=1 of a pending exclusive job never is)."""
        if not tres or not({'cpu','node','billing'}&set(tres)):return None
        v=self.billing_value(partition,tres.get('node',1),tres.get('cpu',0),tres.get('mem')or 0)
        if 'billing'in tres:v=max(v,tres['billing']/3600.0 if self.name=='expanse'else float(tres['billing']))
        return v
    # -- slots
    def classes(self,q)->dict:
        p=set(q.partition.split(','))
        out={}
        if self.name=='expanse':
            if 'compute'in p or q.qos=='normal':out.update(normal_run=1,normal_sub=1,account=1,nodes=q.nodes)
            if 'shared'in p:out['shared']=1
            if 'debug'in p or q.qos.startswith('debug'):out['debug']=1
            return out
        if p&self.amd_pool:out['amd_nodes']=q.nodes   # H7: amdq, amddebugq and amdpreq counted together
        return out

EXPANSE=SiteProfile(name='expanse',user='zzheng8',account='yun124',acct_query=('-A','yun124'),unit='SU',
    partitions={'compute':{'qos':'normal','time':48*3600,'mem':240*1024,'cores':128,'capped':True},
                'shared':{'qos':'shared-normal','time':48*3600,'mem':243*1024,'cores':128,'capped':False,'needs_nodes':True},
                'debug':{'qos':'debug-normal','time':30*60,'mem':240*1024,'cores':128,'capped':False}},
    refused={},slot_classes=('normal_run','normal_sub','account','nodes','shared','debug'),capped_classes=('normal_run','normal_sub','account','nodes'),
    drill_partitions=('shared','debug'),exclusive_ok=('compute',),node_cpus={},amd_pool=frozenset(),exclude_amd=None,cpu_exclude=(),
    lane_args='-A yun124 -p compute',merge_args='-A yun124 -p shared -c 24 --mem=48G -t 02:00:00',array_args='-A yun124 -p shared',lane_mem='240G',
    lane_time_max=47*3600+30*60,f_class={'compute':1.0},lane_partitions=('compute',),runbook_partition='shared',intel_roles=None)
AMD_POOL=frozenset(('amdq','amddebugq','amdpreq'))
SYMMETRY=SiteProfile(name='symmetry',user='zzheng1',account='zzheng1',acct_query=('-u','zzheng1'),unit='core-h',
    # admitted partitions (A1: amdq first, then defq; amddebugq and debugq for checks of at most 1 h); every one is
    # OverSubscribe=EXCLUSIVE, so a job gets and is charged whole nodes (AMD EPYC 64 cores; Intel Gold 6148 80 CPUs = 40
    # cores, billed as Slurm allocates them: cpu=80)
    partitions={'amdq':{'qos':'normal','time':24*3600,'mem':245*1024,'cores':64,'capped':True,'pool':'amd'},
                'amddebugq':{'qos':'normal','time':3600,'mem':245*1024,'cores':64,'capped':True,'pool':'amd'},
                'defq':{'qos':'normal','time':24*3600,'mem':180*1024,'cores':40,'capped':False,'pool':'intel'},
                'debugq':{'qos':'normal','time':3600,'mem':180*1024,'cores':40,'capped':False,'pool':'intel'}},
    refused={'longq':'longq is never used (user rule; A1)',
             'preq':'preq is preemptible (PreemptMode=REQUEUE) and every c8d3- job carries --no-requeue: no role of the plan is requeue-safe',
             'amdpreq':'amdpreq is preemptible (PreemptMode=REQUEUE) and every c8d3- job carries --no-requeue: no role of the plan is requeue-safe',
             'sharedq':'sharedq (oversubscribed, preemptible) is not an admitted partition'},
    slot_classes=('amd_nodes',),capped_classes=('amd_nodes',),drill_partitions=('amddebugq','debugq'),exclusive_ok=('amdq','amddebugq','defq','debugq'),
    node_cpus={'amdq':64,'amddebugq':64,'amdpreq':64,'amdreservedq':64,'defq':80,'debugq':80,'preq':80,'longq':80,'largememq':64,'sharedq':None},
    amd_pool=AMD_POOL,exclude_amd='cn112',   # cn112 (EPYC 8534P, AVX-512) is in amdq: bitwise gates hold on the AVX2 nodes only
    # The CPU pin (HD11: the plan host's CPU must equal the cost model's; one CPU model per speed measurement and per
    # campaign; PLAN-REVIEW-LOG 2026-10-05 "Fix package first"): every AMD-pool job also excludes the AMD nodes known
    # NOT to be 'AMD EPYC 7543 32-Core Processor' (tools/slurm_submit.py amd_exclusions; C8_AMD_EXCLUDE_EXTRA adds more
    # without a code change; slurm/site.sh c8_cpu_guard stops, 68, a job that lands on any other CPU). The AMD pool
    # (sinfo, the draft Stage-5 runbook): amdq = cn083-cn110 and cn112; amddebugq and amdpreq add cn079-cn082. Known EPYC
    # 7543: cn094-097, cn100-102, cn108, cn109, cn110. Unknown (no record; the job guard catches a non-7543 among them):
    # cn083, cn086, cn088-cn091, cn093 (the draft runbook's "cn084-087 are 7532" is unverified for 086), cn098, cn099,
    # cn103-cn107. This module is not a pinned tool: adding a node later leaves every existing plan valid.
    cpu_exclude=('cn079',   # EPYC 7532: J-E0-sym 570281 (benchmarks/symmetry_2026-10-c8/stage5_02963bc/val1/environment.txt); C7(3) pilot 566376
                 'cn080',   # EPYC 7532: C62d's node note (PLAN-REVIEW-LOG.md:402-407, amddebugq cn079-082)
                 'cn081',   # EPYC 7532: C62d's node note (PLAN-REVIEW-LOG.md:402-407)
                 'cn082',   # EPYC 7532: C62d's node note (PLAN-REVIEW-LOG.md:402-407)
                 'cn084',   # EPYC 7532: docs/NUMERICS.md:237 (the C7(3) run1 assembly)
                 'cn085',   # EPYC 7532: J-E1-sym 570273 (stage5_02963bc/run1/environment.txt); C7(3) validation_567197
                 'cn087',   # EPYC 7532: the CPU guard refused J-SMK-3 batch B's merge 570552 (exit 68; docs/HPC.md "Stage 5 results")
                 'cn092'),  # EPYC 7532: the CPU guard refused re-merge 570589 and report 570591 (exit 68; stage5_59d4922/wave45_logs/*_570591.out)
    # the merge takes the whole node's 64 cores (slurm/merge.sh sizes --jobs/--parse-jobs from SLURM_CPUS_PER_TASK)
    lane_args='-p amdq',merge_args='-p amdq -c 64 --mem=240G -t 02:00:00',array_args='-p amdq',lane_mem='240G',
    lane_time_max=23*3600+30*60,f_class={'amdq':1.0,'amddebugq':1.0},   # Intel: an unknown class, 1.5 (D.10)
    lane_partitions=('amdq','defq'),runbook_partition='amdq',
    # Intel Gold 6148 (defq, debugq) is AVX-512 like cn112: raw jobs there only under these role prefixes (an Intel cost
    # refresh or check named as such, drills); validation, bitwise gates, replays, builds, plans and reports run on the
    # AMD AVX2 pool. Campaign jobs (lane, merge, off<N>) run there only with every job of the campaign on Intel.
    intel_roles=('intel_','drill_'))
# The CPU each site's jobs and cost model run on (slurm/site.sh c8_site_cpu, C8_CPU_EXPECT; HD11): the pilot report's target
# CPU (tools/pilot_report.py target_site, S3-010). tests/test_pilot_report.py checks both against slurm/site.sh.
EXPANSE.cpu='AMD EPYC 7742 64-Core Processor';SYMMETRY.cpu='AMD EPYC 7543 32-Core Processor'
# symmetry's Intel pool (defq, debugq; outside the CPU pin, slurm/site.sh c8_cpu_guard): the /proc/cpuinfo model of its
# nodes as the Stage-5/6 Intel jobs recorded it (benchmarks/symmetry_2026-10-c8, lane logs and fingerprints).
INTEL_GOLD_6148='Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz'
def pool(prof:SiteProfile,partition:str)->str|None:
    """symmetry: the CPU vendor pool of a partition ('amd', 'intel'); None elsewhere or for an unknown partition."""
    return (prof.partitions.get(partition)or{}).get('pool')

def partition_cpu(prof:SiteProfile,partition:str)->str:
    """The CPU a partition's lanes run on (S3-R2-004; the pilot report's target CPU): INTEL_GOLD_6148 on symmetry's Intel
    pool (defq, debugq), else the site CPU (Expanse compute; symmetry's AMD pool through the CPU pin)."""
    return INTEL_GOLD_6148 if pool(prof,partition)=='intel'else prof.cpu

def profile(env)->SiteProfile:
    return SYMMETRY if (env or{}).get('C8_SITE')=='symmetry'else EXPANSE

# The other site's share of a budget line (A1.3: symmetry core-hours and Expanse SU count in one dev line under one cap).
# C8_OTHER_SITE_SU holds four fields joined by semicolons, dev=<x>, pilot=<y>, asof=<UTC YYYY-MM-DDTHH:MM:SSZ> and
# ref=<where the numbers come from>, and the optional production=<z> (2026-10-08; absent: 0, so the carry of an export
# without the production line still parses): the other site's OWN line totals (spent + live reservations + unresolved intents,
# without its own carry) at `asof`, from its own budget.py (the `carry` line it prints). Required on both real sites
# (C8_SITE=expanse and symmetry; 64 while unset; zeros for dev and pilot when the other site has no c8d3- job since the epoch),
# optional under C8_SITE=fake (the Mac fakes; 0 when unset). A carry older than OTHER_SITE_MAX_AGE (24 h) or later than
# now + OTHER_SITE_SKEW is refused (64): the other site's existing jobs are counted at their full reservations, and
# `asof` is stamped at the other site's first read (its intent-file scan, before its ledger read and its snapshot), so
# only submissions whose intent was written after `asof` are missing; the rule is to refresh the carry on this site
# after every submission on the other one (docs/HPC.md, "Symmetry (Amendment A1)").
OTHER_SITE_KEYS=('dev','pilot','asof','ref')   # required
OTHER_SITE_OPTIONAL=('production',)             # optional, 0 when absent
OTHER_SITE_MAX_AGE=24*3600
OTHER_SITE_SKEW=600
REAL_SITES=('expanse','symmetry')
def other_site(env)->dict:
    env=env or{};text=env.get('C8_OTHER_SITE_SU')
    site=env.get('C8_SITE')or None
    if text is None or text.strip()=='':
        if site in REAL_SITES:
            other='Expanse'if site=='symmetry'else'symmetry'
            raise Refuse(64,f'C8_OTHER_SITE_SU is required on {site} (A1.3: the budget lines count Expanse SU and symmetry core-hours together): '
                            f'set it to the `carry` line of {other}\'s `tools/budget.py` ("dev=<x>;pilot=<y>;production=<z>;asof=<UTC>;ref=<text>"; '
                            f'"dev=0;pilot=0;asof=<now>;ref=<why>" when {other} has no c8d3- job since the epoch), at most 24 h old')
        return {'dev':0.0,'pilot':0.0,'production':0.0,'asof':None,'ref':None,'text':None,'age_s':None}
    if '\n'in text:raise Refuse(64,'C8_OTHER_SITE_SU must be one line')
    kv={}
    for part in text.split(';'):
        k,eq,v=part.partition('=')
        if not eq or k in kv or k not in OTHER_SITE_KEYS+OTHER_SITE_OPTIONAL:
            raise Refuse(64,f'malformed C8_OTHER_SITE_SU {text!r}: keys {",".join(OTHER_SITE_KEYS)} and the optional {",".join(OTHER_SITE_OPTIONAL)}, each once')
        kv[k]=v
    if not set(OTHER_SITE_KEYS)<=set(kv):raise Refuse(64,f'malformed C8_OTHER_SITE_SU {text!r}: keys {",".join(OTHER_SITE_KEYS)} required')
    out={'text':text,'ref':kv['ref'].strip()}
    if not out['ref']:raise Refuse(64,'C8_OTHER_SITE_SU: ref must name where the numbers come from')
    for k in LINES:
        try:x=float(kv.get(k,'0'));assert math.isfinite(x)and x>=0
        except (ValueError,AssertionError):raise Refuse(64,f'C8_OTHER_SITE_SU {k}={kv[k]!r} is not a finite non-negative number')
        out[k]=x
    try:out['asof']=calendar.timegm(time.strptime(kv['asof'],'%Y-%m-%dT%H:%M:%SZ'))
    except ValueError:raise Refuse(64,f'C8_OTHER_SITE_SU asof={kv["asof"]!r} is not a UTC time YYYY-MM-DDTHH:MM:SSZ')
    age=ledger.now()-out['asof'];out['age_s']=round(age)
    if age>OTHER_SITE_MAX_AGE:
        raise Refuse(64,f'C8_OTHER_SITE_SU is {age/3600:.1f} h old (asof {kv["asof"]}; at most {OTHER_SITE_MAX_AGE//3600} h): refresh it from the other '
                        'site\'s `tools/budget.py` carry line (and after every submission there)')
    if age<-OTHER_SITE_SKEW:raise Refuse(64,f'C8_OTHER_SITE_SU asof {kv["asof"]} lies {-age/60:.0f} min in the future: a typo or a wrong clock; nothing done')
    return out

def carry_line(site:str,lines:dict,utc:float)->str:
    """The C8_OTHER_SITE_SU value the other site sets from this site's report: its own line totals (without the carry it
    holds itself), rounded up to the cent. `utc` is the time of the report's FIRST read, the intent-file scan (taken
    before the ledger read and the four scheduler queries): an admission whose intent is appended after the scan can be
    missing from `own` (its job accepted after the unfiltered sacct, its intent after the ledger read), and such an
    intent is always later than `asof`, so the refresh-after-every-submission rule covers it. Stamping the snapshot
    time instead would date such a miss before `asof` (A1 repair round 2)."""
    up=lambda x:math.ceil(round(x*100,6))/100
    stamp=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(utc))
    return (f'dev={up(lines["dev"]["own"]):.2f};pilot={up(lines["pilot"]["own"]):.2f};production={up(lines["production"]["own"]):.2f};asof={stamp};'
            f'ref={site} tools/budget.py own totals at {stamp}')

# ----------------------------------------------------------------------------------------------------------------
# Settings checks
def check_epoch(env)->int:
    v=env.get('C8_BUDGET_EPOCH')
    if v is not None and v!=str(BUDGET_EPOCH):
        raise Refuse(64,f'C8_BUDGET_EPOCH={v} differs from the package constant BUDGET_EPOCH={BUDGET_EPOCH}: the epoch is fixed (HD17); unset it')
    return BUDGET_EPOCH

def check_env(env)->None:
    for n in CLUSTER_SELECTORS:
        if env.get(n):raise Refuse(64,f'{n} is set: cluster selection is not supported (queries and submissions must address the same cluster); unset it')

def pacific(epoch:float)->str:
    """The local time of America/Los_Angeles (Expanse's clock, F41) for `sacct -S`, from US DST rules (second Sunday of
    March 10:00 UTC to first Sunday of November 09:00 UTC); tests cross-check it against zoneinfo."""
    y=time.gmtime(epoch).tm_year
    def sunday(month,nth):
        first=calendar.weekday(y,month,1);day=1+(6-first)%7+7*(nth-1);return calendar.timegm((y,month,day,0,0,0))
    start=sunday(3,2)+10*3600;end=sunday(11,1)+9*3600
    off=-7*3600 if start<=epoch<end else -8*3600
    return time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(epoch+off))

# ----------------------------------------------------------------------------------------------------------------
# The billing function (HD17)
def mem_mib(text:str|None,default_unit='M')->float|None:
    """Slurm memory sizes: a number with an optional K/M/G/T suffix (default MiB); per-node or per-CPU flags dropped."""
    if text is None:return None
    m=re.fullmatch(r'(\d+(?:\.\d+)?)([KMGTP]?)[nc]?',str(text).strip(),re.I)
    if not m:return None
    unit=(m.group(2)or default_unit).upper()
    return float(m.group(1))*{'K':1/1024,'M':1,'G':1024,'T':1024**2,'P':1024**3}[unit]

def billing_value(partition:str,nodes:int,cpus:int,mem:float,prof:SiteProfile|None=None)->float:
    """Expanse SU per hour: 128 per node on compute; max(CPUs, ceil(mem_GiB/2)) on shared and debug (F39; G is GiB).
    symmetry (prof=SYMMETRY): allocated cores per hour, whole nodes (A1.3)."""
    return (prof or EXPANSE).billing_value(partition,nodes,cpus,mem)

def parse_tres(text:str|None)->dict:
    out={}
    for part in (text or'').split(','):
        k,_,v=part.partition('=')
        if not v:continue
        k=k.strip().lower()
        if k=='mem':out['mem']=mem_mib(v)
        elif k in('cpu','node','billing'):
            try:out[k]=int(float(v))
            except ValueError:pass
    return out

def tres_billing(partition,tres:dict,prof:SiteProfile|None=None)->float|None:
    """A scheduler record's billing value from its cpu, mem and node, or billing/3600 when present and larger (Expanse;
    symmetry: SiteProfile.tres_billing)."""
    return (prof or EXPANSE).tres_billing(partition,tres)

def parse_duration(text:str|None)->int|None:
    """Slurm times: M, M:S, H:M:S, D-H, D-H:M, D-H:M:S; None for UNLIMITED, INVALID, N/A or anything else."""
    t=(text or'').strip()
    m=re.fullmatch(r'(?:(\d+)-)?(\d+)(?::(\d+))?(?::(\d+))?',t)
    if not m:return None
    d,a,b,c=m.groups()
    if d is not None:  # D-H[:M[:S]]
        return ((int(d)*24+int(a))*60+int(b or 0))*60+int(c or 0)
    if c is not None:return (int(a)*60+int(b))*60+int(c)
    if b is not None:return int(a)*60+int(b)
    return int(a)*60

def parse_squeue_duration(text:str|None)->int|None:
    """squeue %l/%M/%L: [D-]H:M:S, M:S; UNLIMITED/INVALID/NOT_SET -> None."""
    t=(text or'').strip()
    m=re.fullmatch(r'(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)',t)
    if not m:return None
    d,h,mi,s=(int(x)if x else 0 for x in m.groups());return ((d*24+h)*60+mi)*60+s

def parse_sacct_limit(text:str|None)->int|None:
    t=(text or'').strip()
    return parse_squeue_duration(t)if ':'in t else (parse_duration(t)if t.isdigit()else None)

# ----------------------------------------------------------------------------------------------------------------
# Scheduler records
def name_info(name:str)->dict:
    """role, C, T and budget line of a c8d3- job name: the line of its role's prefix (line_of; an unparseable c8d3- name
    counts in every line, HD17)."""
    m=NAME_RE.fullmatch(name or'')
    if not m:return {'parsed':False,'role':None,'c':None,'token':None,'lines':LINES}
    role=m.group(1)
    return {'parsed':True,'role':role,'c':m.group(2),'token':m.group(3),'lines':(line_of(role),)}

class QLine:
    """One squeue line (account snapshot: -o; user snapshot: -O with tres-alloc, StartTime, TimeUsed, RestartCnt,
    SubmitTime and EligibleTime; the account snapshot has no restart count, None)."""
    def __init__(self,d:dict,raw:str,source:str,prof:SiteProfile|None=None):
        self.raw=raw;self.source=source;self.prof=prof or EXPANSE
        self.jobid=d.get('jobid')or'';self.base=d.get('base')or self.jobid.split('_')[0];self.user=d.get('user')or''
        self.partition=d.get('partition')or'';self.qos=d.get('qos')or'';self.state=(d.get('state')or'').upper();self.name=d.get('name')or''
        self.comment=d.get('comment');self.reason=d.get('reason')or''
        try:self.nodes=int(d.get('nodes')or 1)
        except ValueError:self.nodes=1
        try:self.cpus=int(d.get('cpus')or 0)
        except ValueError:self.cpus=0
        self.timelimit=parse_squeue_duration(d.get('timelimit'));self.tres=parse_tres(d.get('tres'))if d.get('tres')is not None else None
        self.start=(d.get('start')or'').strip();self.used=parse_squeue_duration(d.get('used'))if d.get('used')is not None else None
        rc=(d.get('restarts')or'').strip();self.restarts=int(rc)if rc.isdigit()else None   # None: not printed or not a count
        self.submit=(d.get('submit')or'').strip();self.eligible=(d.get('eligible')or'').strip()
        _,_,task=self.jobid.partition('_');self.task=int(task)if task.isdigit()else None
        info=name_info(self.name);self.ours=self.name.startswith('c8d3-');self.token=info['token']if self.ours else None;self.info=info
    @property
    def finished(self)->bool:return self.state in FINISHED and self.state!='REQUEUED'
    @property
    def live(self)->bool:
        """Every state but a finished one is live (squeue's REQUEUED is a transition; an unknown state errs towards
        counting more)."""
        return not self.finished
    def classes(self)->dict:return self.prof.classes(self)

def split_fields(line:str,n:int)->list|None:
    parts=line.split('|')
    if len(parts)==n:return [p.strip()for p in parts]
    return None

def parse_account(text:str,prof:SiteProfile|None=None)->list[QLine]:
    prof=prof or EXPANSE;out=[]
    for raw in text.splitlines():
        if not raw.strip():continue
        f=split_fields(raw,len(ACCT_KEYS))
        if f is None:
            parts=[p.strip()for p in raw.split('|')]
            if len(parts)>=6 and parts[2]!=prof.user:  # another user's job with '|' in its name: the left fields suffice
                out.append(QLine(dict(zip(ACCT_KEYS[:6],parts[:6])),raw,'acct',prof));continue
            raise Refuse(69,f'unparseable account squeue line {raw!r}; nothing submitted')
        out.append(QLine(dict(zip(ACCT_KEYS,f)),raw,'acct',prof))
    return out

def parse_user(text:str,prof:SiteProfile|None=None)->list[QLine]:
    out=[];keys=[k for _,_,k in USER_FIELDS]
    for raw in text.splitlines():
        if not raw.strip():continue
        f=split_fields(raw,len(keys))
        if f is None:raise Refuse(69,f'unparseable user squeue line {raw!r}; state unknown')
        out.append(QLine(dict(zip(keys,f)),raw,'user',prof))
    return out

def parse_tasks(spec:str)->list[int]:
    """Array task lists: '14-19%8', '1,3,5-7', '0-9:2'."""
    body=spec.split('%')[0];out=[]
    for part in body.split(','):
        if not part:continue
        rng,_,step=part.partition(':');lo,_,hi=rng.partition('-')
        if not lo.isdigit()or(hi and not hi.isdigit())or(step and not step.isdigit()):raise ValueError(f'bad task list {spec!r}')
        out.extend(range(int(lo),int(hi or lo)+1,int(step or 1)))
    return out

class SRow:
    """One sacct -X --duplicates -P row."""
    def __init__(self,f:list,raw:str,query:str):
        self.raw=raw;self.query=query
        self.jobid,self.jobid_raw,self.name,self.partition,state,self.submit,self.start,el,tl,alloc,req=f
        self.state=(state.split()[0]if state.strip()else'').upper()
        try:self.elapsed=int(el)
        except ValueError:self.elapsed=0
        self.timelimit=parse_sacct_limit(tl);self.alloc=parse_tres(alloc);self.req=parse_tres(req)
        base,_,task=self.jobid.partition('_');self.base=re.match(r'\d*',base).group(0)or base
        self.task=int(task)if task.isdigit()else None;self.collapsed=None
        if task.startswith('['):
            try:self.collapsed=parse_tasks(task.strip('[]'))
            except ValueError:self.collapsed=[]
        info=name_info(self.name);self.ours=self.name.startswith('c8d3-');self.token=info['token']if self.ours else None;self.info=info
    @property
    def live(self)->bool:return self.state in SACCT_LIVE
    @property
    def finished(self)->bool:return not self.live
    @property
    def no_start(self)->bool:return self.start.strip().upper()in NO_START
    def tres(self)->dict:return self.alloc or self.req

def parse_sacct(text:str,query:str)->list[SRow]:
    out=[]
    for raw in text.splitlines():
        if not raw.strip():continue
        parts=raw.split('|')
        if len(parts)<11:raise Refuse(69,f'unparseable sacct line {raw!r}; state unknown')
        if len(parts)>11:parts=parts[:2]+['|'.join(parts[2:len(parts)-8])]+parts[len(parts)-8:]  # a '|' in a job name
        out.append(SRow(parts,raw,query))
    return out

# ----------------------------------------------------------------------------------------------------------------
def sched_env(env:dict)->dict:
    e={k:v for k,v in env.items()if not k.startswith(('SQUEUE_','SACCT_','SINFO_','SPRIO_','SCANCEL_','SCONTROL_'))}
    e['TZ']='America/Los_Angeles';e['SLURM_TIME_FORMAT']='standard'
    return e

def query(argv:list,env:dict,what:str,timeout:float|None=None)->str:
    """One scheduler query with its timeout (60 s); a failure or timeout refuses (69)."""
    t=timeout or ledger.HOOKS.setting('query_timeout',QUERY_TIMEOUT)
    ledger.HOOKS.event('query',argv=argv)
    try:cp=RUNNER(argv,sched_env(env),t)
    except subprocess.TimeoutExpired:raise Refuse(69,f'{what}: `{" ".join(argv[:3])} ...` timed out after {t:g} s; state unknown, nothing done')
    except OSError as e:raise Refuse(69,f'{what}: cannot run {argv[0]}: {e}; state unknown, nothing done')
    except UnicodeDecodeError as e:raise Refuse(69,f'{what}: {argv[0]} printed undecodable output ({e}); state unknown, nothing done')
    if cp.returncode:raise Refuse(69,f'{what}: {argv[0]} failed (exit {cp.returncode}): {(cp.stderr or cp.stdout).strip()[-400:]}; state unknown, nothing done')
    return cp.stdout

def q_account(env)->list[QLine]:
    """The account snapshot: Expanse `-A yun124` (the account caps); symmetry `-u zzheng1` (H7 caps per session; no
    shared account rule), in the same format."""
    prof=profile(env)
    return parse_account(query(['squeue','--all',*prof.acct_query,'-h','-r',f'--states={LIVE_STATES_ARG}','-o',ACCT_FMT],env,'account snapshot'),prof)
def q_user(env)->list[QLine]:
    prof=profile(env)
    return parse_user(query(['squeue','--all','-u',prof.user,'-h','-r','--states=all','-O',USER_FMT],env,'user snapshot'),prof)
def q_sacct(env,state_selected:bool)->list[SRow]:
    prof=profile(env)
    argv=['sacct','-u',prof.user,'-X','--duplicates','-S',pacific(BUDGET_EPOCH),'-P','-n','-o',SACCT_FIELDS]
    # symmetry's Slurm 21.08 returns no row for `-s <states> -S <start>` without an end time (checked 2026-10-05: 0
    # rows, against 476 with `-E now`), so the state-selected query names its end there; Expanse's 23.02 ends at now
    if state_selected:argv[7:7]=['-s',STATE_SELECT]+(['-E','now']if prof.name=='symmetry'else[])
    return parse_sacct(query(argv,env,'sacct (state-selected)'if state_selected else'sacct'),'s'if state_selected else'u')

def union_rows(a:list[SRow],b:list[SRow])->list[SRow]:
    """One row per attempt (JobID, Submit); the finished row when the two queries differ; ordered by Submit."""
    rows={}
    for r in a+b:
        k=(r.jobid,r.submit);o=rows.get(k)
        if o is None or(o.live and r.finished):rows[k]=r
    return sorted(rows.values(),key=lambda r:(r.submit,r.jobid))

class Snapshot:
    """squeue first (account, then user), then the two sacct queries (HD17 "Query order")."""
    def __init__(self,acct,user,s_u,s_s,prof:SiteProfile|None=None):
        self.acct=acct;self.user=user;self.s_u=s_u;self.s_s=s_s;self.rows=union_rows(s_u,s_s);self.utc=ledger.now();self.prof=prof or EXPANSE
    @classmethod
    def take(cls,env,account=True):
        check_env(env);check_epoch(env)
        H=ledger.HOOKS
        acct=None
        if account:acct=q_account(env);H.point('snapshot_account')
        user=q_user(env);H.point('snapshot_user')
        s_u=q_sacct(env,False);H.point('sacct_unfiltered')
        s_s=q_sacct(env,True);H.point('sacct_state_selected')
        return cls(acct,user,s_u,s_s,profile(env))
    def ours_seen(self)->bool:
        return any(q.ours for q in self.user)or any(r.ours for r in self.rows)or any(q.ours for q in (self.acct or[]))
    def live_lines(self)->list[QLine]:
        """Live lines of the account snapshot plus the user snapshot's live lines it lacks (deduplicated by job id)."""
        out={};
        for q in (self.acct or[]):
            if q.live:out[q.jobid]=q
        for q in self.user:
            if q.live and q.jobid not in out:out[q.jobid]=q
        return list(out.values())

# ----------------------------------------------------------------------------------------------------------------
# Charges, per attempt and per array task (HD17 "Charges")
class Charge:
    def __init__(self,kind,su,name,jobid,base,billing,hours,partition,note=None):
        self.kind=kind;self.su=su;self.name=name;self.jobid=jobid;self.base=base;self.billing=billing;self.hours=hours;self.partition=partition;self.note=note
        info=name_info(name);self.token=info['token'];self.lines=info['lines'];self.ours=name.startswith('c8d3-')
    @property
    def spent(self)->bool:return self.kind in('finished_attempt','finished_unaccounted')
    def as_dict(self):return {'kind':self.kind,'su':round(self.su,6),'job':self.jobid,'name':self.name,'billing':self.billing,'hours':self.hours,'note':self.note}

def latest(rows:list[SRow])->dict:
    out={}
    for r in rows:out[r.jobid]=r   # rows are ordered by Submit: the last one is the latest attempt
    return out

def same_attempt(q:QLine,r:SRow)->bool:
    """Whether sacct row r records the attempt that squeue line q shows. A requeued job keeps its job id, so the attempt
    is told by its start: the same StartTime/Start, or both never started (no start time or zero elapsed time). A start
    printed differently by the two commands only over-counts, for as long as squeue lists the line (MinJobAge)."""
    qs=q.start.strip()
    if qs.upper()not in NO_START and qs==r.start.strip():return True
    return (qs.upper()in NO_START or(q.used is not None and q.used==0))and(r.no_start or r.elapsed==0)

def no_other_attempt(q:QLine)->bool:
    """Whether squeue line q proves by itself that its job (or task) had no other attempt, as rule (c) needs when it
    is applied from the user snapshot alone: RestartCnt is 0 (Slurm counts every requeue there) and, when the line has
    an eligible time, its submit time equals it (a requeue resets SubmitTime and delays EligibleTime to a later begin
    time). An eligible time N/A (a dependency never satisfied) leaves RestartCnt alone. Anything else (a RestartCnt that
    is not 0 or not printed, a submit time other than the eligible time) proves nothing, and (c) waits for sacct."""
    if q.restarts!=0:return False
    if q.eligible.upper()in NO_START:return True
    return q.submit.upper()not in NO_START and q.submit==q.eligible

def earlier_finished(q:QLine,rows:list[SRow])->int:
    """The finished sacct rows of q's job id other than the attempt q shows: the attempts before it that sacct has."""
    return sum(1 for r in rows if r.finished and not(q.finished and same_attempt(q,r)))

def missing_attempts(q:QLine,rows:list[SRow])->int:
    """Earlier attempts that squeue's RestartCnt shows and sacct has not delivered as finished rows (a requeue despite
    --no-requeue while sacct lags); 0 when the count is not printed."""
    return max(0,q.restarts-earlier_finished(q,rows))if q.restarts else 0

def accounted(q:QLine,rows:list[SRow])->bool:
    """A finished squeue line is accounted when sacct holds a finished row of the same attempt (HD17 "Charges"); an
    older attempt's finished row does not account for it (a requeue whose last attempt sacct has not delivered yet)."""
    return any(r.finished and same_attempt(q,r)for r in rows)

def charges(user:list[QLine],rows:list[SRow],reversed_order_control=False,prof:SiteProfile|None=None)->list[Charge]:
    """Per attempt and per task; Expanse SU or symmetry core-hours (prof.unit), one value per hour (prof's billing)."""
    prof=prof or EXPANSE
    def tres_billing(part,tres):return prof.tres_billing(part,tres)
    out=[];by_jobid=defaultdict(list)
    for r in rows:by_jobid[r.jobid].append(r)
    lat=latest(rows);listed_bases={q.base for q in user}
    for r in rows:
        if r.finished:
            b=tres_billing(r.partition,r.tres());note=None
            if b is None:b=128.0;note='no TRES in sacct: priced at 128/h'
            out.append(Charge('finished_attempt',b*r.elapsed/3600.0,r.name,r.jobid,r.base,b,r.elapsed/3600.0,r.partition,note))
        elif r.base not in listed_bases:   # a live row that squeue does not list at all: its full reservation, per task
            b=tres_billing(r.partition,r.tres());note=None
            if b is None:b=128.0;note='no TRES in sacct: priced at 128/h'
            n=len(r.collapsed)if r.collapsed is not None else 1;h=(r.timelimit or 0)/3600.0
            if r.timelimit is None:note=(note or'')+' no time limit: 48 h assumed';h=48.0
            out.append(Charge('sacct_live_unlisted',b*h*n,r.name,r.jobid,r.base,b,h*n,r.partition,note))
    for q in user:
        b=None;note=None
        lr=lat.get(q.jobid)
        if lr is not None:b=tres_billing(q.partition,lr.tres())
        if b is None and q.tres:b=tres_billing(q.partition,q.tres)
        if b is None:b=128.0;note='no sacct row and no tres-alloc: priced at 128/h (reported)'
        h=(q.timelimit if q.timelimit is not None else 48*3600)/3600.0
        if q.live:out.append(Charge('live_reservation',b*h,q.name,q.jobid,q.base,b,h,q.partition,note))
        elif not accounted(q,by_jobid.get(q.jobid,[])):   # sacct lags on THIS attempt (an older attempt's row does not count)
            if q.used is not None:out.append(Charge('finished_unaccounted',b*q.used/3600.0,q.name,q.jobid,q.base,b,q.used/3600.0,q.partition,note))
            else:out.append(Charge('finished_unaccounted',b*h,q.name,q.jobid,q.base,b,h,q.partition,(note or'')+' no elapsed time: full reservation'))
        m=missing_attempts(q,by_jobid.get(q.jobid,[]))
        if m:   # earlier attempts (RestartCnt) without a finished sacct row: each at its full reservation until sacct delivers it
            out.append(Charge('finished_unaccounted',b*h*m,q.name,q.jobid,q.base,b,h*m,q.partition,
                              ((note+'; ')if note else'')+f'{m} earlier attempt(s) shown by RestartCnt, not yet in sacct: full reservation each'))
    return out

# ----------------------------------------------------------------------------------------------------------------
# Intents against the scheduler (HD17 "Intents", "Slots", "SU")
class Evaluation:
    def __init__(self,snap:Snapshot,intents:dict,other:dict|None=None):
        """other: the other site's line totals (other_site(env), A1.3), added to each line as `other_site`."""
        self.snap=snap;self.intents=intents;self.other=other or{}
        self.entries=[c for c in charges(snap.user,snap.rows,prof=getattr(snap,'prof',None))if c.ours]
        self.sched=defaultdict(float)
        for c in self.entries:
            if c.token:self.sched[c.token]+=c.su

    # -- resolution evidence
    def _jobs_of(self,t):
        lines=[q for q in self.snap.user+(self.snap.acct or[])if q.token==t]
        rows=[r for r in self.snap.rows if r.token==t]
        return lines,rows

    def evidence(self,it)->tuple:
        """(rule, charge_su, evidence) with rule 'never_started' (c), 'terminal' (a) or None (unresolved)."""
        if it.hold:return None,None,None
        t=it.token;p=it.payload;lines,rows=self._jobs_of(t)
        if any(q.live for q in lines):return None,None,None
        bases=sorted({q.base for q in lines}|{r.base for r in rows})
        if not bases:return None,None,None
        tasks=(p.get('array')or{}).get('tasks')
        units=[]   # (base, task or None)
        for b in bases:units+=[(b,k)for k in tasks]if tasks is not None else[(b,None)]
        by_job=defaultdict(list)
        for r in rows:by_job[r.jobid].append(r)
        coll=[r for r in rows if r.collapsed is not None and r.finished and r.state!='REQUEUED']
        def unit_rows(b,k):return by_job.get(b if k is None else f'{b}_{k}',[])
        def lagging(b,k):
            """A finished squeue line of this job or task without a finished sacct row of its own attempt: sacct has not
            delivered the attempt squeue shows (e.g. the second attempt of a requeued job), so no older row is terminal."""
            jid=b if k is None else f'{b}_{k}';rs=unit_rows(b,k)+[r for r in coll if k is not None and r.base==b and k in r.collapsed]
            return any(q.jobid==jid and q.finished and(not accounted(q,rs)or missing_attempts(q,unit_rows(b,k)))for q in lines)
        def covered(b,k,rowsel):
            if lagging(b,k):return False
            if k is not None and any(r.base==b and k in r.collapsed and rowsel(r)for r in coll):return True
            rs=unit_rows(b,k);return bool(rs)and rowsel(rs[-1])
        # (c) never started: the user snapshot or the state-selected sacct shows every job/task finished, not REQUEUED,
        # with no start time, zero elapsed and no other attempt. The user snapshot alone proves "no other attempt" only
        # through RestartCnt 0 and an unchanged submit time (no_other_attempt); a line whose RestartCnt shows a requeue
        # rules (c) out whatever sacct shows (a lagging sacct may not list the attempt that ran).
        s_rows=defaultdict(list);s_coll=[]
        for r in self.snap.s_s:
            if r.token==t:
                s_rows[r.jobid].append(r)
                if r.collapsed is not None and r.state!='REQUEUED'and r.no_start and r.elapsed==0:s_coll.append(r)
        def never(b,k):
            jid=b if k is None else f'{b}_{k}';rs=unit_rows(b,k)
            if len(rs)>1:return False   # another attempt
            if rs and(rs[-1].live or rs[-1].state=='REQUEUED'or not rs[-1].no_start or rs[-1].elapsed>0):return False
            mine=[q for q in lines if q.jobid==jid]
            if any(q.restarts for q in mine):return False   # squeue counts a requeue: another attempt
            if any(q.finished and q.start.upper()in NO_START and(q.used or 0)==0 and no_other_attempt(q)for q in mine):return True
            sr=s_rows.get(jid,[])
            if len(sr)==1 and sr[0].state!='REQUEUED'and sr[0].no_start and sr[0].elapsed==0:return True
            return k is not None and any(r.base==b and k in r.collapsed for r in s_coll)
        if all(never(b,k)for b,k in units):
            return 'never_started',0.0,{'jobs':[f'{b}'+('' if k is None else f'_{k}')for b,k in units],'rows':[r.raw for r in rows],'lines':[q.raw for q in lines]}
        if all(covered(b,k,lambda r:r.finished and r.state!='REQUEUED')for b,k in units):
            return 'terminal',self.sched.get(t,0.0),{'rows':[r.raw for r in rows]}
        return None,None,None

    # -- slots
    def live_by_token(self)->dict:
        out=defaultdict(lambda:defaultdict(int))
        for q in self.snap.live_lines():
            if q.token:
                for k,v in q.classes().items():out[q.token][k]+=v
        return out

    def slot_extras(self,unresolved:dict)->dict:
        """Per class, the excess of unresolved intents over their own live lines: max(planned, live lines of T) - live.
        A token's live lines are already in the scheduler counts, so the intent adds only what they lack."""
        live=self.live_by_token();out=defaultdict(int);per={}
        seen={q.token for q in self.snap.user+(self.snap.acct or[])if q.token}|{r.token for r in self.snap.rows if r.token}
        for t,it in unresolved.items():
            planned=it.payload.get('slots')or{}
            if ledger.HOOKS.switch('sighting_rule_r5')and t in seen:per[t]={};continue   # withdrawn r5 rule: test control only
            ex={k:max(0,int(planned.get(k,0))-live[t].get(k,0))for k in getattr(self.snap,'prof',EXPANSE).slot_classes}
            per[t]=ex
            for k,v in ex.items():out[k]+=v
        return out,per

    # -- SU per line
    def lines(self,unresolved_only=False)->dict:
        acc={L:{'spent':0.0,'live':0.0,'intents':0.0,'own':0.0,'other_site':float(self.other.get(L)or 0.0),'total':0.0,'unpriced':[]}for L in LINES}
        for c in self.entries:
            for L in c.lines:
                acc[L]['spent' if c.spent else 'live']+=c.su
                if c.note:acc[L]['unpriced'].append(c.as_dict())
        for t,it in self.intents.items():
            if ledger.HOOKS.switch('no_intents'):break
            L=it.payload.get('line','dev');L=L if L in acc else'dev'
            acc[L]['intents']+=max(0.0,it.floor_su()-self.sched.get(t,0.0))
        for L in acc:   # own: this site's total, the value the other site carries (A1.3); total: own + the carried other site
            acc[L]['own']=acc[L]['spent']+acc[L]['live']+acc[L]['intents'];acc[L]['total']=acc[L]['own']+acc[L]['other_site']
        return acc

    def repeated_attempts(self)->list:
        n=defaultdict(int)
        for r in self.snap.rows:
            if r.ours:n[r.jobid]+=1
        return sorted(j for j,k in n.items()if k>1)

# ----------------------------------------------------------------------------------------------------------------
# Attribution and adoption (D.11 step 2; D.12 rebuild)
def scheduler_jobs(snap:Snapshot)->dict:
    """Every c8d3- job of the snapshot (live, or in sacct since the epoch), keyed by its array job id (or job id)."""
    jobs=defaultdict(lambda:{'lines':[],'rows':[]})
    for q in (snap.acct or[])+snap.user:
        if q.ours:jobs[q.base]['lines'].append(q)
    for r in snap.rows:
        if r.ours:jobs[r.base]['rows'].append(r)
    return jobs

def attribution(job:dict)->tuple[bool,str]:
    """(attributable, why): the name parses as c8d3-<role>-<C>-<T> and, while live, the comment parses as
    c8d3:<C>:<P>:<T> with the same C and T."""
    names={q.name for q in job['lines']}|{r.name for r in job['rows']}
    for n in names:
        if not NAME_RE.fullmatch(n):return False,f'name {n!r} does not parse'
    if len({NAME_RE.fullmatch(n).group(3)for n in names})>1:return False,'entries carry different tokens'
    for q in job['lines']:
        if not q.live:continue
        m=COMMENT_RE.fullmatch((q.comment or'').strip());nm=NAME_RE.fullmatch(q.name)
        if not m:return False,f'live job {q.jobid}: comment {q.comment!r} is missing or does not parse'
        if (m.group(1),m.group(3))!=(nm.group(2),nm.group(3)):return False,f'live job {q.jobid}: comment {q.comment!r} disagrees with name {q.name!r}'
    return True,'name+comment'if any(q.live for q in job['lines'])else'name'

def named_jobs(records)->set:
    return {str(r.get('job_id'))for r in records if r['kind']in('submit','adopted')and r.get('job_id')is not None}

def resolve_dir(c:str|None,records,root:Path)->str|None:
    """Best effort (D.11 step 2): an existing directory that a ledger record with the same C names, or an existing
    directory under $C8_ROOT/runs/ or $C8_ROOT/evidence/*/ whose C matches."""
    if not c:return None
    for r in records:
        d=r.get('dir')
        if r.get('c')==c and d and Path(d).is_dir():return d
    cands=[]
    for base in [root/'runs']+([p for p in (root/'evidence').iterdir()if p.is_dir()]if(root/'evidence').is_dir()else[]):
        if base.is_dir():cands+=[p for p in base.iterdir()if p.is_dir()]
    for p in cands:
        if ledger.dir_sha12(p)==c:return str(p)
    return None

def adoption(snap:Snapshot,records,root:Path,by:str)->tuple[list,list,list]:
    """(adopted payloads, resolving annotations, unattributable jobs). A job is adopted when no submit or adopted record
    names its (array) job id; an unattributable job is returned instead unless a record already names it."""
    named=named_jobs(records);adopt=[];notes=[];bad=[]
    for base,job in sorted(scheduler_jobs(snap).items()):
        if base in named:continue
        ok,why=attribution(job)
        if not ok:bad.append({'job_id':base,'why':why,'names':sorted({q.name for q in job['lines']}|{r.name for r in job['rows']})});continue
        live=[q for q in job['lines']if q.live];src=(live or job['lines']or[None])[0];row=job['rows'][-1]if job['rows']else None
        name=src.name if src else row.name;nm=NAME_RE.fullmatch(name);m=COMMENT_RE.fullmatch((src.comment or'').strip())if src and src.comment else None
        tasks=sorted({q.task for q in job['lines']if q.task is not None}|{r.task for r in job['rows']if r.task is not None}|
                     {k for r in job['rows']if r.collapsed for k in r.collapsed})or None
        tres=(row.tres()if row else None)or(src.tres if src and src.tres else{})
        adopt.append(ledger.payload('adopted',[nm.group(3)],token=nm.group(3),job_id=base,task_range=tasks,name=name,comment=src.comment if src else None,
                                    role=nm.group(1),c=nm.group(2),p=m.group(2)if m else None,partition=(src.partition if src else row.partition),
                                    cpus=(src.cpus if src else tres.get('cpu')),tres=tres,time_s=(src.timelimit if src else(row.timelimit if row else None)),
                                    state=(src.state if src else row.state),sources=sorted({q.source for q in job['lines']}|({'sacct'}if job['rows']else set())),
                                    dir=resolve_dir(nm.group(2),records,root),attribution=why,by=by))
    done={r.get('job_id')for r in records if r['kind']=='annotation'and r.get('about')=='dir'}
    for r in records:
        if r['kind']=='adopted'and r.get('dir')is None and r.get('c')and r.get('job_id')not in done:
            d=resolve_dir(r['c'],records,root)
            if d:notes.append(ledger.payload('annotation',r.get('tokens',[]),about='dir',job_id=r.get('job_id'),dir=d,by=by))
    return adopt,notes,bad

def line_cap(line:str,env:dict)->tuple[float,float|None]:
    """(hard cap, ask threshold) of a budget line: dev's constants; pilot and production from their user-approved caps
    (LINE_CAP_ENV), required."""
    if line=='dev':return DEV_CAP,(None if env.get('C8_SU_APPROVED')else DEV_ASK)
    if line not in LINE_CAP_ENV:raise Refuse(64,f'unknown budget line {line!r} ({", ".join(LINES)})')
    n=LINE_CAP_ENV[line];v=env.get(n)
    try:cap=float(v);assert math.isfinite(cap)and cap>0   # nan, inf and 1e999 would leave the line without a cap
    except (TypeError,ValueError,AssertionError):raise Refuse(64,f'the {line} line needs {n}, a finite positive number (the user-approved SU; got {v!r})')
    return cap,None

def site_cap(line:str,prof:SiteProfile|None)->float|None:
    """This site's hard sub-cap of a line (SITE_CAPS, S2-004), None for a line without a split or no profile."""
    caps=SITE_CAPS.get(line)
    return None if caps is None or prof is None else caps.get(prof.name)

def gate(line:str,projected:float,env:dict,own:float|None=None,prof:SiteProfile|None=None)->str|None:
    """None if the line admits, else the refusal text (HD17, D.11 step 4). own (with prof): this site's own projected
    total (spent + live + intents + the new jobs, from its own ledger and scheduler; no carry), checked first against the
    site's HARD sub-cap (SITE_CAPS, S2-004). projected: own + the other site's carry: the joint cap and the dev line's ask
    are SOFT checks, as fresh as the carry."""
    cap,ask=line_cap(line,env);sub=site_cap(line,prof)
    if sub is not None and own is not None and own>sub+1e-9:
        return (f'this site\'s {line} sub-cap: {prof.name} would reach {own:.2f} {prof.unit} of its own (spent + live reservations + unresolved intents + the new '
                f'jobs, from its own ledger and scheduler), above its hard sub-cap {sub:.0f} (budget.SITE_CAPS: {line} split per site, no carry; S2-004)')
    soft=' (joint, with the other site\'s carry C8_OTHER_SITE_SU: a soft check)'if prof is not None else''
    if projected>cap+1e-9:return f'the {line} line would reach {projected:.2f} SU, above its cap {cap:.0f}{soft}'
    if ask is not None and projected>ask+1e-9:return f'the dev line would reach {projected:.2f} SU, above {ask:.0f}{soft}; the user must approve (C8_SU_APPROVED="<approval reference>")'
    return None

# ----------------------------------------------------------------------------------------------------------------
def report(env:dict)->dict:
    s=ledger.Settings(env);check_env(env);check_epoch(env);prof=profile(env);other=other_site(env)
    # Without the lock: the intent files are scanned BEFORE the ledger is read, so every file seen has its ledger copy in
    # the later read (a file being written, or a failed write renamed to resolved/, counts from its ledger copy; D.12).
    # The carry's asof is stamped here, before the first read (carry_line).
    first_read=ledger.now()
    files=ledger.scan_intent_files(s);ledger.HOOKS.point('reader_files_listed')
    led=ledger.Ledger(s);led.read(writer=False);ledger.HOOKS.point('reader_ledger_read')
    snap=Snapshot.take(env,account=False)
    if led.missing and(led.has_intent_files()or snap.ours_seen()):
        raise Refuse(69,f'the ledger {s.ledger_path} is missing while intents/ holds files or the scheduler shows c8d3- jobs since the epoch; '
                        'run `tools/ledger.py rebuild` (it stays blocked until the user decides, D.12)')
    its=ledger.intent_state(led,files);ev=Evaluation(snap,its,other)
    # HD17: a standalone budget.py applies the same evidence rules as admission, in memory, and records nothing. An
    # intent without a resolving record that (a) terminal rows or (c) never-started evidence resolves is counted as
    # resolved at that rule's charge_su (the scheduler charge for (a), 0 for (c)) and leaves the slot counts. An
    # interrupted resolution (a resolving record while its file is still in intents/) stays counted until admission
    # completes its rename (D.12; over-count only).
    by_evidence={}
    for t,it in sorted(its.items()):
        if it.unresolved and not it.hold and not it.resolving:
            rule,charge,evd=ev.evidence(it)
            if rule:
                it.resolve_in_memory(rule,charge,evd)
                by_evidence[t]={'rule':rule,'charge_su':round(charge,6),'line':it.payload.get('line'),'reservation_su':it.payload.get('reservation_su'),
                                'role':it.payload.get('role'),'file':it.file_loc}
    unresolved={t:i for t,i in its.items()if i.unresolved and not i.hold}
    pend={}
    for t,it in unresolved.items():
        rule,charge,_=ev.evidence(it);pend[t]={'line':it.payload.get('line'),'reservation_su':it.payload.get('reservation_su'),'scheduler_su':round(ev.sched.get(t,0.0),6),
                                               'age_s':round(ledger.now()-it.utc),'evidence_now':rule,'role':it.payload.get('role'),'file':it.file_loc,'file_error':it.file_error,
                                               'resolved_in_ledger':it.resolved_in_ledger}
    extras,_=ev.slot_extras(unresolved);lines=ev.lines()
    return {'locked':False,'note':'read without the session lock; nothing recorded','epoch':BUDGET_EPOCH,'epoch_pacific':pacific(BUDGET_EPOCH),
            'site':prof.name,'unit':prof.unit,'other_site':{k:other[k]for k in LINES+('asof','ref','text','age_s')},
            'carry':carry_line(env.get('C8_SITE')or prof.name,lines,first_read),'carry_asof_utc':first_read,
            'site_caps':{L:site_cap(L,prof)for L in lines},'lines':lines,'unresolved_intents':pend,'resolved_by_evidence_now':by_evidence,'holds':{t:i.payload.get('reservation_su')for t,i in its.items()if i.hold},
            'slot_extras':dict(extras),'repeated_attempts':ev.repeated_attempts(),'torn_final_line_skipped':led.torn_skipped}

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=ledger.Parser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--json',action='store_true')
    try:a=p.parse_args(argv);r=report(env)
    except Refuse as e:print('C8: '+str(e),file=sys.stderr);return e.code
    except OSError as e:return ledger.os_error_exit(e)
    if a.json:print(json.dumps(r,indent=1,default=str));return 0
    print(f'C8 budget on {r["site"]} (read without the session lock; nothing recorded; this site\'s unit: {r["unit"]}, counted 1:1 with the other site\'s, A1.3)')
    o=r['other_site']
    if o['text']:print(f'  other site (C8_OTHER_SITE_SU, as of {ledger.utc_iso(o["asof"])}, {o["age_s"]/3600:.1f} h old): dev {o["dev"]:.2f}, pilot {o["pilot"]:.2f}, '
                       f'production {o["production"]:.2f} ({o["ref"]})')
    for L,v in r['lines'].items():
        print(f'  {L:10s} spent {v["spent"]:10.2f}  live reservations {v["live"]:10.2f}  intents {v["intents"]:9.2f}  own {v["own"]:10.2f}  '
              f'other site {v["other_site"]:9.2f}  total {v["total"]:10.2f}'+
              (f'  (own against this site\'s hard sub-cap {r["site_caps"][L]:.0f}, S2-004)'if r['site_caps'].get(L)is not None else''))
        for u in v['unpriced']:print(f'        reported: {u}')
    for t,v in r['resolved_by_evidence_now'].items():print(f'  intent {t} resolved by evidence now (not recorded; the next admission records it): {v}')
    for t,v in r['unresolved_intents'].items():print(f'  unresolved intent {t}: {v}')
    for t,v in r['holds'].items():print(f'  hold {t}: {v} SU for good')
    if r['repeated_attempts']:print('  jobs with more than one attempt (requeued): '+', '.join(r['repeated_attempts']))
    print(f'  carry (set on the other site, A1.3; own totals only): C8_OTHER_SITE_SU="{r["carry"]}"')
    return 0

if __name__=='__main__':sys.exit(main())
