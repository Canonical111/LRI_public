#!/usr/bin/env python3
"""The append-only forbidden-seed log $C8_SEEDS (PLAN D9): every base seed a campaign of this plan used.

  seeds.py init [--log FILE]                      create an empty log (refuses an existing one)
  seeds.py add RUN [--log FILE]                   append RUN's base seed (its manifest), source = RUN
  seeds.py add --seed S --label TEXT [--log FILE] append a seed that has no campaign (e.g. the L=2 control)
  seeds.py list [--log FILE]
  seeds.py check SEED [--log FILE]                exit 1 if the seed (or a derived group seed) is forbidden
  seeds.py merge FROM [FROM ...] [--log FILE]     make the log the union of itself and the FROM logs
The log is JSON (schema c8-d2-seeds-1) and is only ever extended: every add holds the lock <log>.lock (an atomic
directory, waited for up to 120 s), re-reads the log, appends, and replaces the file atomically; concurrent adds
are therefore serialized and none is lost. An identical (seed, source) entry is not added twice. init holds the same
lock, re-checks under it that the log does not exist and publishes the empty log without overwriting (a hard link:
a log created meanwhile, by an add or a merge, is never replaced; Z11, Stage-6 fix round 3). Every non-test
`production.py plan` passes --forbid-seeds-from $C8_SEEDS and registers its base seed in that log itself (register:
under the lock, the fresh log re-checked and the seed appended before the campaign is published; Z15); the package
mirrors the log into designs/forbidden_seeds.json at each evidence commit. A writer that USES a set of seeds and must not
collide (the J-FLAG F2 campaign of tests/numerics_flags.py, a sweep of tools/sweep.py) registers them with reserve: one
transaction under the lock (re-read, check every seed against the fresh log, append every missing entry; W20, Stage-6
fix round 4), so no registration can land between its check and its append.
Two sites, two logs (docs/HPC.md, "The seed log"): symmetry's /mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json and
Expanse's $C8_DATA/forbidden_seeds.json. Every new seed is added to both logs and to the mirror; `merge` brings a log
up to the union (under the same lock): each FROM entry whose (seed, source) pair the log lacks is appended with its
own fields plus merged_from and merged_utc, nothing is removed or reordered, and the result is checked to hold every
seed of every input. The first symmetry log (2026-10-03) was written with an empty "entries" list instead of
"seeds"; that layout is read as a log (its entries are the seeds) and rewritten in the c8-d2-seeds-1 layout by merge.
"""
from __future__ import annotations
import argparse,json,os,socket,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import DirLock,Refuse,load,publish,replace_file,utc
SCHEMA='c8-d2-seeds-1'
LOCK_WAIT=120.  # seconds a writer waits for <log>.lock before refusing (75)

def log_lock(log:Path,command:str)->DirLock:
    """The lock of a seed log: the atomic directory <log>.lock, waited for up to LOCK_WAIT s (then Refuse 75). Every
    writer holds it: add, merge, init and production.py plan's registration (register)."""
    log=Path(log);return DirLock(log.with_name(log.name+'.lock'),command,'the seed log',wait=LOCK_WAIT)

def default_log()->Path:
    v=os.environ.get('C8_SEEDS')
    if not v:raise Refuse(64,'give --log or set C8_SEEDS to the forbidden-seed log')
    return Path(v)

def read_log(log:Path,legacy:bool=False)->dict:
    """The log; legacy=True also reads the first symmetry log's layout ("entries" instead of "seeds", 2026-10-03) and
    returns it in the c8-d2-seeds-1 layout (the entries become the seeds)."""
    doc=json.loads(Path(log).read_bytes())
    if legacy and isinstance(doc,dict)and doc.get('schema')==SCHEMA and 'seeds'not in doc and isinstance(doc.get('entries'),list):
        doc=dict(doc);doc['seeds']=doc.pop('entries')
    if not isinstance(doc,dict)or doc.get('schema')!=SCHEMA or not isinstance(doc.get('seeds'),list):raise ValueError(f'{log} is not a {SCHEMA} seed log')
    for e in doc['seeds']:
        if not isinstance(e,dict)or isinstance(e.get('seed'),bool)or not isinstance(e.get('seed'),int):raise ValueError(f'{log}: entry {e!r} has no integer seed')
    return doc

def merge(log:Path,sources:list)->dict:
    """Make `log` the union of itself and the `sources` logs (see the module docstring); never drops an entry."""
    log=Path(log);srcs=[(Path(s),read_log(s,legacy=True))for s in sources]
    with log_lock(log,'seeds merge'):
        doc=read_log(log,legacy=True)if log.exists()else{'schema':SCHEMA,'seeds':[]}
        old=[dict(e)for e in doc['seeds']];have={(e['seed'],e.get('source'))for e in doc['seeds']};added=0
        for p,d in srcs:
            for e in d['seeds']:
                if (e['seed'],e.get('source'))in have:continue
                doc['seeds'].append({**e,'merged_from':str(p.resolve()),'merged_utc':utc()});have.add((e['seed'],e.get('source')));added+=1
        if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
        want={e['seed']for e in old}|{e['seed']for _,d in srcs for e in d['seeds']}
        if {e['seed']for e in doc['seeds']}!=want:raise RuntimeError('the merged log does not hold every seed')
        replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())
    return {'log':str(log),'sources':[str(p)for p,_ in srcs],'added':added,'entries':len(doc['seeds']),'distinct_seeds':len(want)}

def _append(log:Path,doc:dict,seed:int,source:str)->None:
    """Append (seed, source) to doc and replace the log (the caller holds the lock and re-read doc under it)."""
    old=list(doc['seeds']);doc['seeds'].append({'seed':seed,'source':source,'added_utc':utc(),'host':socket.gethostname()})
    if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
    replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())

def _valid_seed(seed)->None:
    if isinstance(seed,bool)or not isinstance(seed,int)or not 0<=seed<2**64:raise Refuse(64,f'invalid seed {seed!r}')

def add(log:Path,seed:int,source:str)->str:
    _valid_seed(seed);log=Path(log)
    with log_lock(log,f'seeds add {seed}'):
        doc=read_log(log)if log.exists()else{'schema':SCHEMA,'seeds':[]}
        if any(e['seed']==seed and e.get('source')==source for e in doc['seeds']):return 'present'
        _append(log,doc,seed,source)
    return 'added'

def register(log:Path,seed:int,source:str,check,then=None)->dict:
    """Z15 (S6R3-F-02, Stage-6 fix round 3): production.py plan's registration of a non-test campaign's base seed in an
    EXISTING seed log, atomically: under the log's lock the log is re-read (a log that is missing or not a
    c8-d2-seeds-1 log refuses), check(doc) re-checks the seed against it (its refusal text, or None: a seed that a
    concurrent plan or add registered after the plan read the log is refused here, Refuse 64, nothing written), the
    entry (seed, source) is appended, and then() (the campaign's publication) runs while the lock is still held, so
    no other registration interleaves. An exception of then() leaves the seed registered (never used twice).
    Returns {'log', 'seed', 'source', 'state': 'added', 'entries', 'added_utc'}."""
    _valid_seed(seed);log=Path(log)
    with log_lock(log,f'production.py plan: register seed {seed}'):
        if not log.is_file():raise Refuse(64,f'the seed log {log} does not exist (tools/seeds.py init creates it); nothing planned')
        doc=read_log(log)
        why=check(doc)
        if why:raise Refuse(64,f'{why} (re-checked under the seed log\'s lock {log}.lock: registered meanwhile); nothing planned')
        _append(log,doc,seed,source);rec={'log':str(log),'seed':seed,'source':source,'state':'added','entries':len(doc['seeds']),'added_utc':doc['seeds'][-1]['added_utc']}
        if then is not None:then()
    return rec

def reserve(log:Path,entries:list,check,command:str='seeds reserve')->dict:
    """W20 (Stage-6 fix round 4, S6H4-03): reserve a SET of (seed, source) entries in an EXISTING seed log in one
    transaction under its lock, for a writer that uses those seeds (the J-FLAG F2 campaign of tests/numerics_flags.py,
    a sweep of tools/sweep.py): the log is re-read under the lock (missing, or not a c8-d2-seeds-1 log: Refuse 64),
    check(doc) returns the collisions of the entries with that fresh log (a list of texts; any refuses, Refuse 64, and
    nothing is written), then every entry the log lacks is appended and the log replaced once, before the lock is
    released. An entry already present with the identical (seed, source) is 'present' (an intentional reuse under the
    same label, e.g. a gate re-run on the same base seed). So no registration can land between the check and the
    append, and a seed another writer registered first is refused here. Returns {'log', 'entries', 'added',
    'present', 'log_entries'}."""
    entries=[(int(v),str(s))for v,s in entries]
    for v,_ in entries:_valid_seed(v)
    log=Path(log)
    with log_lock(log,command):
        if not log.is_file():raise Refuse(64,f'the seed log {log} does not exist (tools/seeds.py init creates it); nothing registered')
        doc=read_log(log)
        clash=list(check(doc)or[])
        if clash:raise Refuse(64,f'{len(clash)} seed collision(s) with {log} (checked under its lock {log}.lock): '+'; '.join(map(str,clash[:4]))
                                 +(f' (and {len(clash)-4} more)'if len(clash)>4 else'')+'; nothing registered')
        have={(e['seed'],e.get('source'))for e in doc['seeds']};old=[dict(e)for e in doc['seeds']];new=[]
        for v,s in entries:
            if (v,s)in have:continue
            have.add((v,s));new.append((v,s))
        if new:
            now=utc();host=socket.gethostname()
            doc['seeds'].extend({'seed':v,'source':s,'added_utc':now,'host':host}for v,s in new)
            if doc['seeds'][:len(old)]!=old:raise RuntimeError('seed log would lose entries')
            replace_file(log,(json.dumps(doc,indent=1)+'\n').encode())
    return {'log':str(log),'entries':len(entries),'added':len(new),'present':len(entries)-len(new),'log_entries':len(doc['seeds'])}

def init(log:Path)->dict:
    """Z11 (S6D-R3-04): create an empty log under the lock add and merge hold: re-checked under it, published with a
    hard link (common.publish), which never replaces a file; a log that exists (or appears meanwhile) refuses (64)."""
    log=Path(log)
    with log_lock(log,'seeds init'):
        if log.exists():raise Refuse(64,f'{log} exists')
        try:publish(log,json.dumps({'schema':SCHEMA,'seeds':[]},indent=1)+'\n')
        except FileExistsError:raise Refuse(64,f'{log} exists (created meanwhile; nothing overwritten)')from None
    return {'log':str(log),'state':'created'}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('init');q.add_argument('--log',type=Path)
    q=s.add_parser('add');q.add_argument('run',type=Path,nargs='?');q.add_argument('--seed',type=int);q.add_argument('--label');q.add_argument('--log',type=Path)
    q=s.add_parser('list');q.add_argument('--log',type=Path)
    q=s.add_parser('check');q.add_argument('seed',type=int);q.add_argument('--log',type=Path)
    q=s.add_parser('merge');q.add_argument('sources',type=Path,nargs='+');q.add_argument('--log',type=Path)
    a=p.parse_args(argv)
    try:
        log=a.log or default_log()
        if a.command=='init':print(json.dumps(init(log)));return 0
        if a.command=='add':
            if (a.run is None)==(a.seed is None):raise Refuse(64,'give RUN or --seed S --label TEXT')
            if a.run is not None:
                m=load(Path(a.run)/'manifest.json');seed=int(m['seed']);source=str(Path(a.run).resolve())
            else:
                if not a.label:raise Refuse(64,'--seed needs --label')
                seed=a.seed;source=a.label
            print(json.dumps({'log':str(log),'seed':seed,'source':source,'state':add(log,seed,source)}));return 0
        if a.command=='list':print(json.dumps(read_log(log),indent=1));return 0
        if a.command=='merge':print(json.dumps(merge(log,a.sources)));return 0
        import production as prod
        forbidden=prod.read_seed_file(log)if log.exists()else{}
        why=prod.seed_refusal(a.seed,forbidden)
        print(json.dumps({'seed':a.seed,'forbidden':bool(why),'why':why}));return 1 if why else 0
    except Refuse as r:print('C8: '+str(r),file=sys.stderr);return r.code
    except (ValueError,RuntimeError)as e:print(f'C8: {e}',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
