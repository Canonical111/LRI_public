#!/usr/bin/env python3
"""The append-only forbidden-seed log $C8_SEEDS (PLAN HD6): every base seed a campaign of this plan used.

  seeds.py init [--log FILE] [--from COPY]       create the log (refuses an existing one): empty, or with --from a byte
                                                  copy of COPY (a c8-d3-seeds-1 log holding every seed of the package
                                                  mirror); on symmetry --from is required (Amendment A1)
  seeds.py add RUN [--log FILE]                   append RUN's base seed (its manifest), source = RUN
  seeds.py add --seed S --label TEXT [--log FILE] append a seed that has no campaign (e.g. the L=2 control)
  seeds.py merge COPY [COPY ...] [--log FILE]     append every entry of each COPY (another site's log) that the log
                                                  lacks, verbatim and in order (the two-site sync, A1)
  seeds.py list [--log FILE]
  seeds.py check SEED [--log FILE]                exit 1 if the seed (or a derived group seed) is forbidden
  seeds.py mirror --log COPY [--to FILE]          FILE (default designs/forbidden_seeds.json of this package) := COPY,
                                                  byte for byte, after checking it extends FILE (append-only)
A plan reserves its seed itself (S2-002): `production.py plan --reserve-seed LOG` (slurm/plan.sh, tools/sweep.py and
native_job.sh's sweep steps pass $C8_SEEDS) rechecks and appends it under the lock before anything is built or
published (seeds.reserve), keyed by the campaign's resolved directory: a retry of that directory is idempotent, another
directory with the same seed is refused when the plan checks seeds, and the entry stays after an interrupted run. A plan
that checks seeds (--forbid-seeds-from) must reserve in one of those logs (65 otherwise).
The log is JSON (schema c8-d3-seeds-1) and is only ever extended. Every add and merge holds the C8 session lock (the
package's only lock, D.11; $C8_ROOT/locks/c8d3.lock, flock), re-reads the log, appends and replaces the file atomically,
so concurrent adds are serialized and none is lost (A-ORC-1). An identical (seed, source) entry is not added twice. add
and merge refuse (64) a missing log: a log is created only by init, so a site's log never starts empty by accident
(symmetry's starts as a copy of Expanse's log or of the package mirror). Every non-test `production.py plan` passes
--forbid-seeds-from $C8_SEEDS; on symmetry it also refuses a forbidden set that lacks a seed of the package mirror.
Two sites, two logs (Amendment A1): after every add on one site, `merge` a copy of that log into the other site's log
(docs/HPC.md, "Symmetry (Amendment A1)").
The mirror (HD6): at each evidence commit designs/forbidden_seeds.json is a byte copy of $C8_SEEDS, committed in a
data-only commit (then verify_delivery --write). COPY is $C8_SEEDS or a byte copy of it (the evidence's
forbidden_seeds.json, or `ssh expanse cat $C8_SEEDS`); `mirror` refuses (64) a COPY that is not a c8-d3-seeds-1 log or
that drops or changes an entry of the current mirror, and prints both sha256s.
"""
from __future__ import annotations
import argparse,json,os,socket,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,load,replace_file,utc
SCHEMA='c8-d3-seeds-1'

def default_log(env)->Path:
    v=env.get('C8_SEEDS')
    if not v:raise Refuse(64,'give --log or set C8_SEEDS to the forbidden-seed log')
    return Path(v)

def read_log(log:Path)->dict:
    doc=json.loads(Path(log).read_bytes())
    if doc.get('schema')!=SCHEMA or not isinstance(doc.get('seeds'),list):raise ValueError(f'{log} is not a {SCHEMA} seed log')
    return doc

MISSING=('{log} does not exist: create it first with `seeds.py init` (on symmetry: `seeds.py init --from <a copy of Expanse\'s '
         '$C8_SEEDS or designs/forbidden_seeds.json>`); add and merge never create a log (HD6, A1)')

def on_symmetry(env)->bool:
    """C8_SITE=symmetry, or a symmetry host (a BeeGFS mount at /mnt/beegfs), whatever C8_SITE says."""
    import ledger
    return (env or{}).get('C8_SITE')=='symmetry'or 'symmetry'in ledger.host_sites(env or{})

def mirror_gaps(seeds:set)->list:
    """The seeds of the package mirror (designs/forbidden_seeds.json) that `seeds` lacks."""
    return sorted({int(e['seed'])for e in read_log(MIRROR)['seeds']}-set(seeds))if MIRROR.exists()else[]

def init(log:Path,src:Path|None,env)->dict:
    log=Path(log)
    if log.exists():raise Refuse(64,f'{log} exists')
    if src is None:
        if on_symmetry(env):raise Refuse(64,'on symmetry the seed log starts as a copy of Expanse\'s $C8_SEEDS or of the package mirror: '
                                            f'seeds.py init --from <copy> (an empty log would forget every Expanse seed; HD6, A1); {MIRROR} is the mirror')
        data=(json.dumps({'schema':SCHEMA,'seeds':[]},indent=1)+'\n').encode()
    else:
        data=Path(src).read_bytes()
        try:doc=json.loads(data)
        except ValueError as e:raise Refuse(64,f'{src}: not JSON ({e})')
        if doc.get('schema')!=SCHEMA or not isinstance(doc.get('seeds'),list):raise Refuse(64,f'{src} is not a {SCHEMA} seed log')
        if on_symmetry(env)and not MIRROR.exists():raise Refuse(64,f'the package mirror {MIRROR} is missing (a broken export?): the copy cannot be checked')
        gaps=mirror_gaps({int(e['seed'])for e in doc['seeds']})
        if gaps:raise Refuse(64,f'{src} lacks {len(gaps)} seed(s) of the package mirror {MIRROR} (e.g. {gaps[:5]}): not a copy of a current log')
    replace_file(log,data)
    import hashlib
    return {'log':str(log),'state':'created','from':str(src)if src else None,'sha256':hashlib.sha256(data).hexdigest(),'seeds':len(json.loads(data)['seeds'])}

def merge(log:Path,srcs:list,env=None)->dict:
    """Append every entry of each source log that the log lacks (identity: seed and source), verbatim and in the
    sources' order, under the session lock; the log must exist."""
    import hashlib,ledger
    log=Path(log);env=dict(os.environ)if env is None else env;docs=[]
    for f in srcs:
        try:docs.append((f,read_log(f)))
        except (OSError,ValueError)as e:raise Refuse(64,f'{f}: {e}')
    with ledger.SessionLock(ledger.Settings(env),'seeds merge'):
        if not log.exists():raise Refuse(64,MISSING.format(log=log))
        doc=read_log(log);old=list(doc['seeds']);have={(e['seed'],e.get('source'))for e in old};added=0
        for f,d in docs:
            for e in d['seeds']:
                if (e['seed'],e.get('source'))not in have:doc['seeds'].append(e);have.add((e['seed'],e.get('source')));added+=1
        if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
        if added:replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())
        data=log.read_bytes()
    return {'log':str(log),'sources':[str(f)for f in srcs],'added':added,'seeds':len(doc['seeds']),'sha256':hashlib.sha256(data).hexdigest()}

def add(log:Path,seed:int,source:str,env=None)->str:
    import ledger
    if isinstance(seed,bool)or not isinstance(seed,int)or not 0<=seed<2**64:raise Refuse(64,f'invalid seed {seed!r}')
    log=Path(log);env=dict(os.environ)if env is None else env
    with ledger.SessionLock(ledger.Settings(env),f'seeds add {seed}'):
        if not log.exists():raise Refuse(64,MISSING.format(log=log))
        doc=read_log(log)
        if any(e['seed']==seed and e.get('source')==source for e in doc['seeds']):return 'present'
        old=list(doc['seeds']);doc['seeds'].append({'seed':seed,'source':source,'added_utc':utc(),'host':socket.gethostname()})
        if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
        replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())
    return 'added'

def reserve(log:Path,seed:int,source:str,exclusive:bool,refusal=None,env=None)->str:
    """HD6 at plan time (S2-002; `production.py plan --reserve-seed`): under the seed log's own lock (the session lock,
    D.11; on symmetry the NFS home's), re-read the log and reserve `seed` for the campaign `source` (its resolved
    directory, a stable identity) before anything is built or published. 'present' when that source already holds the
    seed (a retry: idempotent, nothing written), else 'reserved' (one entry appended, the file replaced atomically and
    fsynced). exclusive (a plan that checks seeds): refuses (65) a seed the log holds for another source, or one that
    refusal({seed: why} of the log's other entries) rejects (production.seed_refusal: derived-seed collisions); without
    it (a test-only plan that checks no seed: twins, prefix checks) the seed is registered unchecked. The entry is never
    removed: an interrupted plan, sweep or run keeps its reservation."""
    import ledger
    if isinstance(seed,bool)or not isinstance(seed,int)or not 0<=seed<2**64:raise Refuse(64,f'invalid seed {seed!r}')
    log=Path(log);env=dict(os.environ)if env is None else env
    with ledger.SessionLock(ledger.Settings(env),f'seeds reserve {seed}')as lock:
        if not log.exists():raise Refuse(64,MISSING.format(log=log))
        try:doc=read_log(log)
        except (OSError,ValueError)as e:raise Refuse(64,f'{log}: {e}')
        if any(e['seed']==seed and e.get('source')==source for e in doc['seeds']):return 'present'
        if exclusive:
            held=[e.get('source')for e in doc['seeds']if e['seed']==seed]
            if held:raise Refuse(65,f'seed {seed} is held in {log} by {held[0]!r}: one seed per campaign (HD6, S2-002); nothing built or published, '
                                    'choose a fresh random seed (python3 -c "import secrets;print(secrets.randbits(63))")')
            why=refusal({e['seed']:f'{log} ({e.get("source")or"listed"})'for e in doc['seeds']if e.get('source')!=source})if refusal else None
            if why:raise Refuse(65,f'{why} (rechecked under the lock; HD6, S2-002); nothing built or published, choose a fresh random seed')
        old=list(doc['seeds']);doc['seeds'].append({'seed':seed,'source':source,'added_utc':utc(),'host':socket.gethostname(),'by':'production.py plan --reserve-seed'})
        if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
        lock.check('seed reservation')
        replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())
    return 'reserved'

MIRROR=Path(__file__).resolve().parents[1]/'designs'/'forbidden_seeds.json'

def mirror(src:Path,dest:Path=MIRROR)->dict:
    """dest := the bytes of src (a c8-d3-seeds-1 log that extends dest's entries, if dest exists); atomic."""
    import hashlib
    data=Path(src).read_bytes()
    try:new=json.loads(data)
    except ValueError as e:raise Refuse(64,f'{src}: not JSON ({e})')
    if new.get('schema')!=SCHEMA or not isinstance(new.get('seeds'),list):raise Refuse(64,f'{src} is not a {SCHEMA} seed log')
    dest=Path(dest);old=read_log(dest)['seeds']if dest.exists()else[]
    if new['seeds'][:len(old)]!=old:raise Refuse(64,f'{src} does not extend the mirror {dest} (an entry was dropped or changed): the log is append-only')
    state='identical'if dest.exists()and dest.read_bytes()==data else 'written'
    if state=='written':dest.parent.mkdir(parents=True,exist_ok=True);replace_file(dest,data)
    return {'mirror':str(dest),'source':str(src),'sha256':hashlib.sha256(data).hexdigest(),'seeds':len(new['seeds']),'added':len(new['seeds'])-len(old),'state':state}

def main(argv=None,env=None)->int:
    env=dict(os.environ)if env is None else env
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('init');q.add_argument('--log',type=Path);q.add_argument('--from',dest='src',type=Path)
    q=s.add_parser('merge');q.add_argument('sources',type=Path,nargs='+');q.add_argument('--log',type=Path)
    q=s.add_parser('add');q.add_argument('run',type=Path,nargs='?');q.add_argument('--seed',type=int);q.add_argument('--label');q.add_argument('--log',type=Path)
    q=s.add_parser('list');q.add_argument('--log',type=Path)
    q=s.add_parser('check');q.add_argument('seed',type=int);q.add_argument('--log',type=Path)
    q=s.add_parser('mirror');q.add_argument('--log',type=Path);q.add_argument('--to',type=Path,default=MIRROR)
    a=p.parse_args(argv)
    try:
        log=a.log or default_log(env)
        if a.command=='mirror':print(json.dumps(mirror(log,a.to)));return 0
        if a.command=='init':print(json.dumps(init(log,a.src,env)));return 0
        if a.command=='merge':print(json.dumps(merge(log,a.sources,env)));return 0
        if a.command=='add':
            if (a.run is None)==(a.seed is None):raise Refuse(64,'give RUN or --seed S --label TEXT')
            if a.run is not None:m=load(Path(a.run)/'manifest.json');seed=int(m['seed']);source=str(Path(a.run).resolve())
            else:
                if not a.label:raise Refuse(64,'--seed needs --label')
                seed=a.seed;source=a.label
            print(json.dumps({'log':str(log),'seed':seed,'source':source,'state':add(log,seed,source,env)}));return 0
        if a.command=='list':print(json.dumps(read_log(log),indent=1));return 0
        import production as prod
        forbidden=prod.read_seed_file(log)if log.exists()else{}
        why=prod.seed_refusal(a.seed,forbidden)
        print(json.dumps({'seed':a.seed,'forbidden':bool(why),'why':why}));return 1 if why else 0
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code
if __name__=='__main__':sys.exit(main())
