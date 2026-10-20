#!/usr/bin/env python3
"""Admission and submission of a site campaign: N whole-node runner jobs (slurm/node_runner.sh) and one merge job (the
unchanged slurm/merge.sh). The operator guide is docs/SITES.md.

  site_submit.py runners RUN --nodes N --time HH:MM:SS [--add] [--dry-run]   N runners and a merge (N = 0: a merge only)
  site_submit.py release RUN                                                 release stale claims (owner job not live)

Environment: C8_SITE (expanse | symmetry), C8_ENV_SETUP (the site env file, sourced by every job), C8_SBATCH_ARGS
(the runners' options) and C8_MERGE_SBATCH_ARGS (the merge's options), each one shell-lexed line and the ONLY source
of sbatch options; C8_SEEDS (this site's forbidden-seed log), C8_SEEDS_TOOL_DIR (our pinned seeds.py and common.py),
C8_REQUIRE_BACKEND (default gmp); Expanse: C8_EXP_NODES (default 4); symmetry: C8_AMD_CAP and C8_AMD_POOL_TOTAL
(both required, from the agreement with C63d in force); C8_SITE_LOCK_DIR (default $HOME, as in LRI_C8_D2_HPC).
Guarantees:
  * options: each role's options are resolved from its variable alone and must match the site profile (PROFILES):
    account, one partition, QoS, -N1 -n1, CPUs, memory, and on symmetry --exclude with cn112 and --requeue on amdpreq.
    Any other option (--exclusive, --array, --dependency, -w, --time, --job-name, --output, ...) is refused. This tool
    adds --time, --job-name (c8d2-ind-run, c8d2-ind-merge), --comment=c8ind:<campaign tag>, --output under
    $C8_RUN/slurm_logs, --open-mode=append, --export=ALL and the merge's --dependency=afterany:<every runner>;
  * --time is required for runners and at most the partition's limit (Expanse compute 48 h; symmetry amdq and amdpreq
    24 h, amddebugq 1 h); the merge gets 04:00:00 and C8_MERGE_WORKERS=8 (its -c 8);
  * sbatch runs without any inherited SBATCH_*, SALLOC_*, SLURM_* or *_CLUSTERS variable (each ignored one is
    printed and recorded in $C8_RUN/site_submissions.jsonl), except SLURM_CONF, which only locates the configuration
    (Expanse has no /etc/slurm/slurm.conf); every role is preflighted with sbatch --test-only before the first
    submission, so a refusal submits nothing;
  * the plan: pinned tools unchanged, backend C8_REQUIRE_BACKEND, and (cost-model plans) no block whose wall estimate
    x 1.5 + 600 s exceeds --time less a 120 s start-up allowance;
  * seeds: a test plan's seed must collide with nothing in C8_SEEDS; a non-test plan needs $C8_RUN/seed_receipt.json
    (tools/seed_sync.sh) for its seed and source, no older than the plan, and C8_SEEDS re-read under its lock must
    still show that source as the single owner of the seed and of its derived group seeds;
  * admission: under the campaign lock $C8_RUN/.c8_submit.lock (75 at once) and the site lock
    $C8_SITE_LOCK_DIR/.c8_site_<site>.lock (shared with LRI_C8_D2_HPC; waited for 120 s, then 75), from the snapshot
    through the last sbatch. Stale claims are released first. The campaign's live merge refuses (65); its live runners
    need --add. Budgets (one snapshot; production.py's LIVE/TERMINAL states; an uncertain state of a counted job: 69):
      expanse (squeue -A yun124): session c8d2-* normal-QOS running + N <= 11 and submitted + N <= 27; session nodes
      on compute and debug + N <= C8_EXP_NODES; session shared-partition jobs + 1 <= 32; the user's normal-QOS running
      + N <= 22 and submitted + N <= 54; the account's normal-QOS running + N <= 32;
      symmetry (squeue -u <user>): session c8d2-* AMD-pool nodes + N <= C8_AMD_CAP; c8d2-* plus c8d3-* AMD-pool nodes
      + N <= C8_AMD_POOL_TOTAL; the user's other jobs are listed, not counted.
Exit codes: 0 submitted (or nothing to do), 1 a submission failed after some job was accepted (named in the message),
64 invalid input (nothing submitted), 65 over budget or live campaign jobs, 69 scheduler state unknown or uncertain,
75 a lock is held.
"""
from __future__ import annotations
import argparse,json,os,re,shlex,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import node_runner as nr
import production as prod
from common import ROOT,load
from node_runner import Refuse

SITE_LOCK_WAIT=120.;STARTUP_ALLOWANCE=120.
MERGE_TIME='04:00:00';MERGE_WORKERS=8
H=3600
# Site profiles. partitions: {name: wall-time limit in seconds (None: the merge's fixed MERGE_TIME)}; cpus: required
# -c (None: the plan's threads, at most max_cpus); mem: required --mem.
PROFILES={
    'expanse':{'run':{'partitions':{'compute':48*H},'account':'yun124','qos':(None,'normal'),'cpus':None,'max_cpus':128,'mem':'240G'},
               'merge':{'partitions':{'shared':None},'account':'yun124','qos':(None,),'cpus':8,'max_cpus':8,'mem':'32G'}},
    'symmetry':{'run':{'partitions':{'amdq':24*H,'amddebugq':1*H,'amdpreq':24*H},'account':None,'qos':(None,),'cpus':64,'max_cpus':64,'mem':'245G',
                       'exclude':'cn112','requeue':('amdpreq',)},
                'merge':{'partitions':{'sharedq':None},'account':None,'qos':(None,),'cpus':8,'max_cpus':8,'mem':'16000M'}}}
EXPANSE_NODE_PARTITIONS=frozenset({'compute','debug'})  # as LRI_C8_D2_HPC's admission counts development nodes
EXPANSE_CAPS={'session_running':11,'session_submitted':27,'session_shared':32,'user_running':22,'user_submitted':54,'account_running':32}
VARIABLE={'run':'C8_SBATCH_ARGS','merge':'C8_MERGE_SBATCH_ARGS'}
SCRIPT={'run':ROOT/'slurm/node_runner.sh','merge':ROOT/'slurm/merge.sh'}

# ---------------------------------------------------------------- option resolution
OPTIONS={'-A':'account','--account':'account','-p':'partition','--partition':'partition','-q':'qos','--qos':'qos','-N':'nodes','--nodes':'nodes',
         '-n':'ntasks','--ntasks':'ntasks','-c':'cpus','--cpus-per-task':'cpus','--mem':'mem','-x':'exclude','--exclude':'exclude',
         '--mail-type':'mail_type','--mail-user':'mail_user'}
FLAGS={'--requeue':True,'--no-requeue':False}

def parse_options(text:str,what:str)->dict:
    """The allowed options of one shell-lexed line, {key: value}; anything else, or an option given twice, refuses."""
    if '\n'in text:raise Refuse(64,f'{what} must be a single line')
    try:tokens=shlex.split(text)
    except ValueError as x:raise Refuse(64,f'{what} cannot be parsed: {x}')
    out={};i=0
    while i<len(tokens):
        t=tokens[i]
        if t in FLAGS:k,v,i='requeue',FLAGS[t],i+1
        elif t.startswith('--')and'='in t and t.partition('=')[0]in OPTIONS:k,v,i=OPTIONS[t.partition('=')[0]],t.partition('=')[2],i+1
        elif t in OPTIONS:
            if i+1>=len(tokens):raise Refuse(64,f'{what}: {t} needs a value')
            k,v,i=OPTIONS[t],tokens[i+1],i+2
        elif not t.startswith('--')and t[:2]in OPTIONS and len(t)>2:k,v,i=OPTIONS[t[:2]],t[2:],i+1
        else:raise Refuse(64,f'{what}: {t!r} is not allowed. Allowed: '+' '.join(sorted(OPTIONS))+' '+' '.join(FLAGS)+'; this tool sets the time, name, comment, output, export and dependency itself')
        if k in out:raise Refuse(64,f'{what}: {k} is given twice')
        out[k]=v
    return out

def mebibytes(text:str)->int|None:
    m=re.fullmatch(r'(\d+)([KMGT]?)',(text or'').strip().upper())
    return None if not m else -(-int(m.group(1))*{'K':1,'':1024,'M':1024,'G':1024**2,'T':1024**3}[m.group(2)]//1024)

def hostlist(spec:str)->set:
    """Host names of a Slurm host list such as cn112 or cn[079-082,112]."""
    items=[];depth=0;cur=''
    for ch in spec or'':
        depth+=(ch=='[')-(ch==']')
        if ch==','and depth==0:items.append(cur);cur=''
        else:cur+=ch
    items.append(cur);out=set()
    for it in filter(None,items):
        m=re.fullmatch(r'([^\[\]]*)\[([^\[\]]+)\]([^\[\]]*)',it)
        if not m:out.add(it);continue
        pre,body,suf=m.groups()
        for r in body.split(','):
            lo,_,hi=r.partition('-')
            if not lo.isdigit()or(hi and not hi.isdigit()):out.add(it);break
            out.update(f'{pre}{n:0{len(lo)}d}{suf}'for n in range(int(lo),int(hi or lo)+1))
    return out

def resolve(site:str,role:str,opts:dict,threads:int)->dict:
    """The role's resolved request, checked against PROFILES[site][role]; any deviation refuses (64)."""
    P=PROFILES[site][role];w=f'{VARIABLE[role]} ({site} {"runners"if role=="run"else"merge"})'
    part=opts.get('partition')
    if not part or','in part:raise Refuse(64,f'{w}: give exactly one partition, one of {", ".join(P["partitions"])} (got {part!r})')
    if part not in P['partitions']:
        raise Refuse(64,f'{w}: partition {part} is not allowed; use one of {", ".join(P["partitions"])}'+(' (never an Intel partition: a campaign stays on one CPU vendor)'if site=='symmetry'and role=='run'else''))
    if opts.get('account')!=P['account']:raise Refuse(64,f'{w}: '+(f'-A {P["account"]} is required'if P['account']else'no -A (symmetry jobs use the default account)')+f' (got {opts.get("account")!r})')
    if opts.get('qos')not in P['qos']:raise Refuse(64,f'{w}: -q {opts.get("qos")} is not allowed; '+('only -q normal or none'if 'normal'in P['qos']else'give no -q'))
    for k,flag in (('nodes','-N'),('ntasks','-n')):
        if opts.get(k,'1')!='1':raise Refuse(64,f'{w}: {flag} {opts[k]}: every job is one node and one task')
    c=opts.get('cpus')
    if not c or not c.isdigit():raise Refuse(64,f'{w}: -c is required'+(f' (the plan\'s --threads, {threads})'if role=='run'else f' ({P["cpus"]})'))
    c=int(c);want=P['cpus']if P['cpus']is not None else threads
    if role=='run'and want!=threads:raise Refuse(64,f'{w}: a {site} runner uses all {want} cores of its node; the plan has --threads {threads}: re-plan with --threads {want}')
    if c!=want:raise Refuse(64,f'{w}: -c {c} is not allowed; '+(f'it must equal the plan\'s --threads {threads}'if role=='run'else f'the merge takes -c {want}'))
    if c>P['max_cpus']:raise Refuse(64,f'{w}: -c {c} exceeds the {P["max_cpus"]} cores of a {part} node')
    mem=opts.get('mem')
    if mebibytes(mem)!=mebibytes(P['mem']):raise Refuse(64,f'{w}: --mem {P["mem"]} is required (got {mem!r})'+(' (sharedq allows at most 8 CPUs x 2,000 MB)'if part=='sharedq'else''))
    if P.get('exclude')and P['exclude']not in hostlist(opts.get('exclude','')):raise Refuse(64,f'{w}: --exclude must name {P["exclude"]} (got {opts.get("exclude")!r})')
    if part in P.get('requeue',())and opts.get('requeue')is not True:raise Refuse(64,f'{w}: {part} is preemptible; --requeue is required there')
    return {'role':role,'site':site,'partition':part,'account':opts.get('account'),'qos':opts.get('qos'),'cpus':c,'mem':mem,'exclude':opts.get('exclude'),
            'requeue':opts.get('requeue'),'mail_type':opts.get('mail_type'),'mail_user':opts.get('mail_user'),'max_time':P['partitions'][part]}

def wall_seconds(text:str)->int:
    m=re.fullmatch(r'(?:(\d+)-)?(\d{1,2}):(\d{2}):(\d{2})',text or'')
    if not m or int(m.group(3))>59 or int(m.group(4))>59:raise Refuse(64,f'--time {text!r}: give HH:MM:SS or D-HH:MM:SS')
    s=int(m.group(1)or 0)*86400+int(m.group(2))*3600+int(m.group(3))*60+int(m.group(4))
    if s<=0:raise Refuse(64,'--time must be positive')
    return s

def sbatch_argv(r:dict,time_text:str,comment:str,logs:Path,deps=())->list:
    a=([f'--account={r["account"]}']if r['account']else[])+[f'--partition={r["partition"]}']+([f'--qos={r["qos"]}']if r['qos']else[])+\
      ['--nodes=1','--ntasks=1',f'--cpus-per-task={r["cpus"]}',f'--mem={r["mem"]}']+([f'--exclude={r["exclude"]}']if r['exclude']else[])+\
      ({True:['--requeue'],False:['--no-requeue']}.get(r['requeue'],[]))+([f'--mail-type={r["mail_type"]}']if r['mail_type']else[])+\
      ([f'--mail-user={r["mail_user"]}']if r['mail_user']else[])+\
      [f'--time={time_text}',f'--job-name={nr.JOB_NAMES[r["role"]]}',f'--comment={comment}',f'--output={str(logs).replace("%","%%")}/{r["role"]}-%j.log','--open-mode=append','--export=ALL']
    return a+([f'--dependency=afterany:{":".join(deps)}']if deps else[])+[str(SCRIPT[r['role']])]

def sbatch_env(env:dict,extra:dict)->tuple[dict,list]:
    """sbatch's environment: no inherited SBATCH_*, SALLOC_*, SLURM_* or *_CLUSTERS variable except SLURM_CONF (it sets no
    option; without it sbatch on Expanse finds no configuration); plus extra."""
    drop=sorted(k for k in env if(k.startswith(('SBATCH_','SALLOC_','SLURM_'))or k.endswith('_CLUSTERS'))and k!='SLURM_CONF')
    e={k:v for k,v in env.items()if k not in drop and k!='C8_INDEX_OFFSET'};e.update(extra);return e,drop

def sbatch(argv:list,env:dict,test:bool)->str:
    cmd=['sbatch','--test-only',*argv]if test else['sbatch','--parsable',*argv]
    try:cp=subprocess.run(cmd,capture_output=True,text=True,errors='replace',env=env,timeout=300)
    except (OSError,subprocess.SubprocessError)as x:raise Refuse(64 if test else 1,f'sbatch could not run: {x}')
    msg=(cp.stderr or cp.stdout).strip()
    if cp.returncode:raise Refuse(64 if test else 1,f'sbatch{" --test-only"if test else""} refused the {argv[-1].rsplit("/",1)[-1]} request (exit {cp.returncode}): {msg[-600:]}')
    if test:return' | '.join(x.strip()for x in msg.splitlines()if x.strip())[-600:]if msg else'ok'  # every line: the estimate may precede 'Preempts:'
    jid=cp.stdout.strip().split(';')[0]
    if not jid.isdigit():raise Refuse(1,f'sbatch printed no job id ({cp.stdout.strip()[:200]!r}); check squeue before resubmitting')
    return jid

# ---------------------------------------------------------------- admission
def nodes_of(rs:list)->int:
    bad=[r['jobid']for r in rs if r['nodes']is None]
    if bad:raise Refuse(69,f'admission: node count of job(s) {", ".join(bad)} does not parse; UNKNOWN, nothing submitted')
    return sum(r['nodes']for r in rs)

def admission(site:str,records:list,me:str,n:int,env:dict)->dict:
    """Admit n runners and one merge, or refuse (65) naming every limit and the largest admissible n."""
    live=lambda r:nr.state_class(r)=='live'
    if site=='expanse':
        cap=env.get('C8_EXP_NODES')or'4'
        if not cap.isdigit():raise Refuse(64,f'C8_EXP_NODES must be a non-negative integer (got {cap!r})')
        nr.settled(records,lambda r:r['qos']=='normal'or(r['user']==me and nr.named(r,nr.SESSION)),'admission')
        L=[r for r in records if live(r)];sess=[r for r in L if r['user']==me and nr.named(r,nr.SESSION)];norm=lambda r:r['qos']=='normal'
        limits=[('session c8d2-* normal-QOS running',EXPANSE_CAPS['session_running'],sum(norm(r)and nr.is_running(r)for r in sess),n),
                ('session c8d2-* normal-QOS submitted',EXPANSE_CAPS['session_submitted'],sum(map(norm,sess)),n),
                ('session c8d2-* nodes on compute/debug (C8_EXP_NODES)',int(cap),nodes_of([r for r in sess if set(r['partitions'])&EXPANSE_NODE_PARTITIONS]),n),
                ('session c8d2-* shared-partition jobs',EXPANSE_CAPS['session_shared'],sum('shared'in r['partitions']for r in sess),1),
                (f'user {me} normal-QOS running',EXPANSE_CAPS['user_running'],sum(r['user']==me and norm(r)and nr.is_running(r)for r in L),n),
                (f'user {me} normal-QOS submitted',EXPANSE_CAPS['user_submitted'],sum(r['user']==me and norm(r)for r in L),n),
                ('account yun124 normal-QOS running',EXPANSE_CAPS['account_running'],sum(norm(r)and nr.is_running(r)for r in L),n)];other=[]
    else:
        vals={}
        for k in ('C8_AMD_CAP','C8_AMD_POOL_TOTAL'):
            v=env.get(k,'')
            if not v.isdigit():raise Refuse(64,f'{k} must be set explicitly on symmetry, from the agreement with C63d in force (LRI_C8_shared/inventory/DECISIONS.md; got {v!r})')
            vals[k]=int(v)
        pool=lambda r:r['user']==me and bool(set(r['partitions'])&nr.AMD_POOL)and(nr.named(r,nr.SESSION)or nr.named(r,nr.OTHER_SESSION))
        nr.settled(records,pool,'admission')
        L=[r for r in records if live(r)];ours=[r for r in L if pool(r)and nr.named(r,nr.SESSION)];theirs=[r for r in L if pool(r)and nr.named(r,nr.OTHER_SESSION)]
        limits=[('session c8d2-* AMD-pool nodes (C8_AMD_CAP)',vals['C8_AMD_CAP'],nodes_of(ours),n),
                ('c8d2-* and c8d3-* AMD-pool nodes (C8_AMD_POOL_TOTAL)',vals['C8_AMD_POOL_TOTAL'],nodes_of(ours)+nodes_of(theirs),n)]
        other=[f'{r["jobid"]} {r["name"]} {",".join(r["partitions"])} {r["state"]}'for r in L if r['user']==me and not pool(r)]
    rec={'site':site,'user':me,'new_runners':n,'new_merge':1,'limits':{name:{'cap':cap,'counted':used,'new':new}for name,cap,used,new in limits},'listed_not_counted':other}
    print('C8: admission '+json.dumps(rec,sort_keys=True),flush=True)
    # A limit binds only the jobs it counts: the runner limits N, the shared-partition limit the merge.
    over=[f'{name}: {used} counted + {new} new > {cap}'for name,cap,used,new in limits if new and used+new>cap]
    if over:
        merge_fits=all(used+1<=cap for name,cap,used,new in limits if 'shared'in name)
        best=max(0,min([cap-used for name,cap,used,new in limits if 'shared'not in name]+[n]))if merge_fits else None
        raise Refuse(65,'admission refused: '+'; '.join(over)+'. '+(f'Largest admissible --nodes now: {best}'if merge_fits else'The merge itself does not fit')+'; nothing submitted')
    return rec

# ---------------------------------------------------------------- seeds at submission
def seed_gate(env:dict,run:Path,m:dict)->dict:
    sm=nr.seed_tools(env);log=nr.seed_log(env);S=int(m['seed'])
    if m.get('test_only'):
        clash=nr.collisions(S,nr.read_seed_log(sm,log)['seeds'])
        if clash:raise Refuse(64,f'test plan seed {S} collides with {log}: '+'; '.join(clash[:4])+'; re-plan with a fresh seed')
        return {'mode':'test plan: checked, never reserved','seed':S,'log':str(log)}
    src=nr.seed_source(run);f=run/'seed_receipt.json'
    try:rc=load(f)
    except (OSError,ValueError)as x:raise Refuse(64,f'a non-test campaign needs its seed receipt {f} (node_runner.py seed reserve, then tools/seed_sync.sh --owner {src} --seed {S}; docs/SITES.md): {x}')
    if rc.get('schema')!=nr.RECEIPT_SCHEMA or rc.get('seed')!=S or rc.get('owner')!=src:
        raise Refuse(64,f'{f} does not belong to this plan (seed {rc.get("seed")} owner {rc.get("owner")}; the plan has seed {S}, source {src})')
    try:made=nr.utc_epoch(rc.get('utc',''))
    except (TypeError,ValueError):raise Refuse(64,f'{f} has no valid utc time')
    if made<int((run/'manifest.json').stat().st_mtime):raise Refuse(64,f'{f} ({rc["utc"]}) is older than the plan; rerun tools/seed_sync.sh --owner ... --seed {S}')
    try:
        with sm.log_lock(log,f'c8ind site_submit: ownership re-check of seed {S}'):probs=nr.ownership(S,src,nr.read_seed_log(sm,log)['seeds'])
    except sm.Refuse as x:raise Refuse(x.code,str(x))from None
    if probs:raise Refuse(64,f'{log} no longer shows {src} as the single owner of seed {S}: '+'; '.join(probs[:4])+'; nothing submitted. Re-plan with a new seed')
    return {'mode':'receipt and single ownership re-checked under the log lock','seed':S,'source':src,'log':str(log),'receipt_utc':rc['utc']}

# ---------------------------------------------------------------- commands
def site_of(env:dict)->str:
    s=env.get('C8_SITE','')
    if s not in PROFILES:raise Refuse(64,f'C8_SITE must be one of {", ".join(PROFILES)} (got {s!r}); source slurm/env_<site>.sh')
    return s

def site_lock(env:dict,site:str)->nr.DirLock:
    d=Path(env.get('C8_SITE_LOCK_DIR')or env.get('HOME')or str(Path.home()))
    return nr.DirLock(d/f'.c8_site_{site}.lock','c8ind site_submit admission','admission on this site',wait=SITE_LOCK_WAIT)

def unschedulable(run:Path,m:dict,threads:int,limit:int)->list:
    if not m.get('cost_model_sha256'):return []
    bad=[]
    for x in nr.layouts(run,m,True):
        for k,b in enumerate(x['blocks']):
            need=nr.block_wall(b,threads)*nr.DEADLINE_FACTOR+nr.DEADLINE_MARGIN
            if need>limit-STARTUP_ALLOWANCE:bad.append(f'index {x["index"]} ({x["group"]} shard {x["shard"]}) block {k}: {need:.0f} s')
    return bad

def append_log(run:Path,rec:dict)->None:
    fd=os.open(run/'site_submissions.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o666)
    try:os.write(fd,(json.dumps(rec,sort_keys=True)+'\n').encode());os.fsync(fd)
    finally:os.close(fd)

def cmd_runners(a,env:dict)->int:
    site=site_of(env);run=Path(a.directory).resolve();m=nr.read_plan(run);n=a.nodes;me=nr.scheduler_user()
    if n<0:raise Refuse(64,'--nodes must be non-negative')
    changed=prod.tool_changes(run)
    if changed:raise Refuse(64,f'pinned tools differ from the plan ({", ".join(sorted(changed))}); nothing submitted')
    want=env.get('C8_REQUIRE_BACKEND')or'gmp'
    if m['backend']!=want:raise Refuse(64,f'the plan\'s backend is {m["backend"]}, not C8_REQUIRE_BACKEND={want} (production.py plan defaults to decimal: pass --backend gmp)')
    es=env.get('C8_ENV_SETUP')
    if not es or not os.access(es,os.R_OK):raise Refuse(64,f'C8_ENV_SETUP must name the readable site env file (slurm/env_{site}.sh); got {es!r}')
    threads=int(m['threads'])
    for role in ('run','merge')if n else('merge',):
        if not env.get(VARIABLE[role],'').strip():raise Refuse(64,f'{VARIABLE[role]} is not set: give the {site} profile options (docs/SITES.md)')
    rr=resolve(site,'run',parse_options(env[VARIABLE['run']],VARIABLE['run']),threads)if n else None
    mr=resolve(site,'merge',parse_options(env[VARIABLE['merge']],VARIABLE['merge']),threads)
    if n:
        if a.time is None:raise Refuse(64,'--time HH:MM:SS is required for runners')
        t=wall_seconds(a.time)
        if t>rr['max_time']:raise Refuse(64,f'--time {a.time} exceeds the {rr["partition"]} limit {prod.hms(rr["max_time"])}')
        bad=unschedulable(run,m,threads,t)
        if bad:raise Refuse(64,f'{len(bad)} frozen block(s) cannot finish within --time {a.time} (wall estimate x {nr.DEADLINE_FACTOR} + {nr.DEADLINE_MARGIN:.0f} s, '
                                f'{STARTUP_ALLOWANCE:.0f} s start-up): '+'; '.join(bad[:5])+'. Re-plan with a smaller --checkpoint-tasks or --checkpoint-seconds, or raise --time')
    seeds=seed_gate(env,run,m);comment=nr.campaign_comment(run);logs=run/'slurm_logs'
    print('C8: seeds '+json.dumps(seeds,sort_keys=True),flush=True)
    with nr.DirLock(run/nr.CAMPAIGN_LOCK,f'c8ind site_submit runners {n}','this campaign'),site_lock(env,site):
        claims=nr.claims_of(run)  # read before the snapshot: a claim older than it has a live owner in it
        records=nr.squeue(env,['-A','yun124']if site=='expanse'else['-u',me],'admission snapshot')
        camp=nr.campaign_jobs(records,run,me)
        if camp['merges']:raise Refuse(65,f'merge job(s) {",".join(camp["merges"])} of this campaign are live; scancel them (or let them finish) first; nothing submitted')
        if camp['runners']and not a.add:raise Refuse(65,f'runner job(s) {",".join(camp["runners"])} of this campaign are live; add runners with --add (counted the same way); nothing submitted')
        rel=nr.release_stale(run,records,claims,'site_submit.py runners',dry=a.dry_run)
        held=set(nr.claims_of(run))-(set(rel['stale'])if a.dry_run else set())  # a dry run released nothing
        st=nr.status(run);eligible=[i for i in st['remaining']if i not in held]
        print(f'C8: campaign {run}: {len(st["done"])}/{st["indices"]} indices done, {len(eligible)} eligible, exhausted {st["exhausted"]or"none"}; '
              f'live runners {camp["runners"]or"none"}; stale claims {"to release"if a.dry_run else"released"}: {rel["stale"]or"none"}',flush=True)
        if n>len(eligible):raise Refuse(64,f'--nodes {n} exceeds the {len(eligible)} eligible indices; nothing submitted')
        adm=admission(site,records,me,n,env)
        extra={'C8_RUN':str(run),'C8_PACKAGE':str(ROOT),'C8_SITE':site}
        renv,ignored=sbatch_env(env,extra);menv,_=sbatch_env(env,{**extra,'C8_MERGE_WORKERS':str(MERGE_WORKERS)})
        if ignored:print('C8: ignoring inherited '+', '.join(ignored),file=sys.stderr,flush=True)
        ra=sbatch_argv(rr,a.time,comment,logs)if n else None
        mpre=sbatch_argv(mr,MERGE_TIME,comment,logs)
        pre={'run':sbatch(ra,renv,True)}if n else{}
        pre['merge']=sbatch(mpre,menv,True)  # its dependency ids do not exist yet; the rest of the request is checked
        for k,v in pre.items():print(f'C8: preflight {k}: {v}',flush=True)
        rec={'utc':nr.utc(),'command':'runners','site':site,'nodes':n,'add':a.add,'time':a.time,'campaign_comment':comment,'admission':adm,'seed':seeds,
             'ignored_environment':ignored,'released_stale_claims':rel,'live_runners_before':camp['runners'],'runner_argv':ra,'preflight':pre}
        if a.dry_run:
            print('C8: dry run; nothing submitted.'+(f'\n  runners x{n}: sbatch '+shlex.join(ra)if n else'')+'\n  merge: sbatch '+shlex.join(sbatch_argv(mr,MERGE_TIME,comment,logs,camp['runners']+['<new runner ids>']if n else camp['runners'])),flush=True)
            return 0
        logs.mkdir(exist_ok=True);ids=[];err=None
        try:
            for _ in range(n):ids.append(sbatch(ra,renv,False));print(f'C8: runner {ids[-1]}; log {logs}/run-{ids[-1]}.log',flush=True)
        except Refuse as x:err=x
        deps=camp['runners']+ids;ma=sbatch_argv(mr,MERGE_TIME,comment,logs,deps);mid=None
        if err is None or ids:
            try:mid=sbatch(ma,menv,False);print(f'C8: merge {mid} '+(f'(afterany:{":".join(deps)})'if deps else'(no dependency)')+f'; log {logs}/merge-{mid}.log',flush=True)
            except Refuse as x:err=err or x
        append_log(run,{**rec,'runner_ids':ids,'merge_id':mid,'merge_argv':ma,'error':str(err)if err else None})
        if err:raise Refuse(1 if ids or mid else err.code,f'{err} (accepted so far: runners {ids or "none"}, merge {mid or "none"})')
    print(f'C8: monitor with {sys.executable} {ROOT/"tools/node_runner.py"} status {run} and {sys.executable} {ROOT/"tools/production.py"} status {run}',flush=True)
    return 0

def cmd_release(a,env:dict)->int:
    run=Path(a.directory).resolve();nr.read_plan(run);me=nr.scheduler_user()
    with nr.DirLock(run/nr.CAMPAIGN_LOCK,'c8ind site_submit release','this campaign'):
        claims=nr.claims_of(run);records=nr.squeue(env,['-u',me],'stale-claim release')
        rel=nr.release_stale(run,records,claims,'site_submit.py release')
    print(json.dumps(rel));return 0

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=nr.Parser(prog='site_submit.py',description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('runners');q.add_argument('directory',type=Path);q.add_argument('--nodes',type=int,required=True);q.add_argument('--time')
    q.add_argument('--add',action='store_true',help='add runners to a campaign whose runners are live');q.add_argument('--dry-run',action='store_true')
    q=s.add_parser('release');q.add_argument('directory',type=Path)
    try:
        a=p.parse_args(argv)
        return cmd_runners(a,env)if a.command=='runners'else cmd_release(a,env)
    except Refuse as r:print(f'C8: {r}',file=sys.stderr,flush=True);return r.code

if __name__=='__main__':sys.exit(main())
