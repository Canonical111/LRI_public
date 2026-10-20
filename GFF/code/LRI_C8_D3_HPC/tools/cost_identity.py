#!/usr/bin/env python3
"""Read-only cost-model identity checker (PLAN B, D.14, HD11; G5, G6, A-PIL-1) and J-BLD's data-only check.

  cost_identity.py check --model M --exe BIN [--host-cpu] [--mp-check MODE]
                                                 the model's executable sha256 equals sha256(BIN); with --host-cpu its
                                                 cpu_model also equals this host's (common.cpu_model, compared after
                                                 production.norm_cpu), with --mp-check its mp_check is MODE or it holds a
                                                 measured overhead factor for MODE (production.identity_problems): with
                                                 both flags exactly HD11's check of `production.py plan` on this host
  cost_identity.py check RUN [RUN ...]           each published campaign planned on the measured basis, with its
                                                 cost_model.json at the manifest's pin and that model's executable
                                                 sha256 equal to the manifest's executable_sha256
  cost_identity.py data-only --base DIR --data DIR [--output FILE]
                                                 J-BLD (PLAN J-BLD row; D.14): every regular file of both trees by
                                                 sha256, and the paths only one of them has; ok iff every difference is
                                                 under cost_models/ or benchmarks/, or is in the carry set (docs/,
                                                 README.md, CHANGELOG.md, designs/forbidden_seeds.json,
                                                 DELIVERY_MANIFEST.json, SHA256SUMS; user decision 2026-10-05), where
                                                 designs/forbidden_seeds.json (the HD6 mirror) may only grow: the data
                                                 tree's file is a c8-d3-seeds-1 log whose entries begin with every entry
                                                 of the base's, exactly and in order (tools/seeds.py mirror's rule); a
                                                 removed file or a dropped, changed or reordered entry refuses. Skipped:
                                                 the top-level bin/ and bin.bld_failed_*/, inputs/packs/free_L8.pack,
                                                 inputs/packs/power_L8.pack, and every __pycache__/ or .pytest_cache/

It prints both sha256s (and, with the flags, every other pair) of every comparison and exits 1 on any mismatch (2 on
unreadable input). A campaign on any other basis (bootstrap, synthetic, prior_model; the non-measured roles, a
validation plan) fails: it has no measured model of its own binary. Without --host-cpu and --mp-check a `check
--model` record is the same as before them.
"""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path

def sha(p:Path)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def check_model(model:Path,exe:Path,host_cpu:bool=False,mp_check:str|None=None)->dict:
    m=json.loads(Path(model).read_bytes());want=m.get('executable_sha256');have=sha(exe)
    rec={'model':str(model),'model_executable_sha256':want,'executable':str(exe),'executable_sha256':have,'ok':bool(m.get('measured'))and want==have}
    if not(host_cpu or mp_check):return rec
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import production as prod
    from common import cpu_model
    host=cpu_model();prob=prod.identity_problems(m,have,host,mp_check or m.get('mp_check'))
    if host_cpu:
        rec.update(cpu_model=m.get('cpu_model'),host_cpu_model=host)
        if 'cpu_model'in prob:rec['ok']=False
    if mp_check:
        rec.update(mp_check=mp_check,model_mp_check=m.get('mp_check'),model_mp_check_overhead=(m.get('mp_check_overhead')or{}).get(mp_check))
        if 'mp_check'in prob:rec['ok']=False
    asked={'executable_sha256',*(['cpu_model']if host_cpu else[]),*(['mp_check']if mp_check else[])}
    rec['problems']={k:list(v)for k,v in prob.items()if k in asked}   # every compared pair that differs
    return rec

def check_run(run:Path)->dict:
    run=Path(run);data=(run/'manifest.json').read_bytes();m=json.loads(data);out={'run':str(run),'manifest_sha256':hashlib.sha256(data).hexdigest(),
                                                                                    'cost_basis':m.get('cost_basis'),'plan_role':m.get('plan_role'),'executable_sha256':m.get('executable_sha256')}
    if m.get('cost_basis')!='measured'or not m.get('cost_model_sha256'):return {**out,'ok':False,'why':f'cost basis {m.get("cost_basis")!r}: no measured model of this binary'}
    f=run/'cost_model.json'
    if not f.is_file():return {**out,'ok':False,'why':'cost_model.json is missing'}
    h=sha(f);cm=json.loads(f.read_bytes())
    out.update(cost_model_sha256=h,model_executable_sha256=cm.get('executable_sha256'))
    if h!=m['cost_model_sha256']:return {**out,'ok':False,'why':f'cost_model.json sha256 {h} differs from the manifest pin {m["cost_model_sha256"]}'}
    if cm.get('executable_sha256')!=m.get('executable_sha256'):return {**out,'ok':False,'why':'the model was measured on another executable'}
    return {**out,'ok':True}

# J-BLD's data-only check: what a data-only commit may change (the PLAN J-BLD row: cost_models/ and benchmarks/; the
# carry set of the user's Stage-5 decision of 2026-10-05) and what the comparison skips (build outputs and caches)
DATA_DIRS=('cost_models','benchmarks')
CARRY_DIRS=('docs',)
CARRY_FILES=('README.md','CHANGELOG.md','designs/forbidden_seeds.json','DELIVERY_MANIFEST.json','SHA256SUMS')
SKIP_FILES=('inputs/packs/free_L8.pack','inputs/packs/power_L8.pack')
SKIP_PARTS=('__pycache__','.pytest_cache')

def skipped(rel:str)->bool:
    parts=rel.split('/')
    return parts[0]=='bin'or parts[0].startswith('bin.bld_failed_')or rel in SKIP_FILES or any(p in SKIP_PARTS for p in parts)

SEED_LOG='designs/forbidden_seeds.json';SEEDS_SCHEMA='c8-d3-seeds-1'   # tools/seeds.py SCHEMA

def seed_log_growth(old:bytes|None,new:bytes|None)->tuple[str|None,list]:
    """(why the data tree's designs/forbidden_seeds.json is not an append-only extension of the base's, or None; the
    seeds it adds). tools/seeds.py mirror's rule (HD6: production.py plan on symmetry refuses a forbidden set lacking a
    seed of this mirror, so a data-only commit must never lower that floor): the new file is a c8-d3-seeds-1 log and its
    entries begin with every entry of the base's, exactly and in order; None for a side means the file is absent."""
    if new is None:return 'removed: the HD6 seed mirror is append-only (tools/seeds.py mirror)',[]
    def entries(b:bytes,side:str)->list:
        try:doc=json.loads(b)
        except ValueError as e:raise ValueError(f'the {side} tree\'s {SEED_LOG} is not JSON ({e})')
        if not isinstance(doc,dict)or doc.get('schema')!=SEEDS_SCHEMA or not isinstance(doc.get('seeds'),list):raise ValueError(f'the {side} tree\'s {SEED_LOG} is not a {SEEDS_SCHEMA} seed log')
        return doc['seeds']
    try:n=entries(new,'data');o=entries(old,'base')if old is not None else[]
    except ValueError as e:return str(e),[]
    if n[:len(o)]!=o:
        k=next((i for i,(x,y)in enumerate(zip(o,n))if x!=y),len(n))
        return (f'not append-only: the base\'s {len(o)} entries are not a prefix of the data tree\'s {len(n)} (first difference at entry {k}: '
                f'an entry was dropped, changed or reordered; tools/seeds.py mirror refuses the same)'),[]
    return None,[e.get('seed')if isinstance(e,dict)else e for e in n[len(o):]]

def path_class(rel:str)->str:
    top=rel.split('/',1)[0]
    if top in DATA_DIRS:return top
    if top in CARRY_DIRS or rel in CARRY_FILES:return 'carry'
    return 'outside'

def tree(root:Path)->dict:
    """{relative path: sha256 or 'symlink:<target>'} of every file of root but the skipped ones; refuses a missing root."""
    root=Path(root)
    if not root.is_dir():raise FileNotFoundError(f'{root} is not a directory')
    out={}
    def boom(e):raise e
    for d,dirs,files in os.walk(root,onerror=boom):
        rd=os.path.relpath(d,root);rd=''if rd=='.'else rd+'/'
        links=[x for x in dirs if os.path.islink(os.path.join(d,x))]   # a symlinked directory is an entry, never followed
        dirs[:]=sorted(x for x in dirs if x not in links and not skipped(rd+x))
        for f in sorted(files+links):
            rel=rd+f;p=os.path.join(d,f)
            if skipped(rel):continue
            out[rel]='symlink:'+os.readlink(p)if os.path.islink(p)else sha(Path(p))
    return out

def data_only(base:Path,data:Path)->dict:
    a=tree(base);b=tree(data);diff=[]
    for rel in sorted(set(a)|set(b)):
        if a.get(rel)==b.get(rel):continue
        change='added'if rel not in a else'removed'if rel not in b else'changed'
        x={'path':rel,'change':change,'class':path_class(rel),'base_sha256':a.get(rel),'data_sha256':b.get(rel)}
        if rel==SEED_LOG:   # the HD6 mirror may only grow (a symlink on either side refuses)
            if any(str(v).startswith('symlink:')for v in (a.get(rel),b.get(rel))):why,added='a symlink: the seed mirror must be a regular file',[]
            else:why,added=seed_log_growth(*((Path(t)/rel).read_bytes()if rel in d else None for t,d in ((base,a),(data,b))))
            if why:x.update({'class':'refused','why':why})
            else:x['seeds_added']=added
        diff.append(x)
    out=[x for x in diff if x['class']=='outside'];ref=[x for x in diff if x['class']=='refused']
    return {'schema':'c8-d3-data-only-1','base':str(base),'data':str(data),'files_base':len(a),'files_data':len(b),'differences':diff,
            'outside':[x['path']for x in out],'refused':[{'path':x['path'],'why':x['why']}for x in ref],
            'allowed':{'dirs':list(DATA_DIRS)+[d+'/'for d in CARRY_DIRS],'files':list(CARRY_FILES),'append_only':[SEED_LOG]},
            'skipped':['bin/','bin.bld_failed_*/',*SKIP_FILES,'any __pycache__/ or .pytest_cache/ component'],
            'rule':'ok iff every difference is under cost_models/ or benchmarks/ (PLAN J-BLD row) or in the carry set (docs/, README.md, CHANGELOG.md, '
                   'designs/forbidden_seeds.json, DELIVERY_MANIFEST.json, SHA256SUMS; user decision 2026-10-05), and designs/forbidden_seeds.json only '
                   'grows (the base\'s entries an exact prefix of the data tree\'s; tools/seeds.py mirror)','ok':not(out or ref)}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('check');q.add_argument('runs',nargs='*',type=Path);q.add_argument('--model',type=Path);q.add_argument('--exe',type=Path)
    q.add_argument('--host-cpu',action='store_true');q.add_argument('--mp-check',choices=('on','off','stride16'))
    q=s.add_parser('data-only');q.add_argument('--base',type=Path,required=True);q.add_argument('--data',type=Path,required=True);q.add_argument('--output',type=Path)
    a=p.parse_args(argv)
    try:
        if a.cmd=='data-only':
            if a.output and a.output.exists():print(f'cost_identity: {a.output} exists (never overwritten)',file=sys.stderr);return 2
            r=data_only(a.base,a.data)
            if a.output:
                with open(a.output,'x')as f:f.write(json.dumps(r,indent=1)+'\n')
            print(json.dumps({k:r[k]for k in('base','data','files_base','files_data','outside','refused','ok')}|{'differences':[(x['path'],x['change'],x['class'])for x in r['differences']]}))
            return 0 if r['ok']else 1
        if a.model or a.exe:
            if not(a.model and a.exe)or a.runs:print('cost_identity: give --model M --exe BIN, or RUN...',file=sys.stderr);return 2
            recs=[check_model(a.model,a.exe,a.host_cpu,a.mp_check)]
        else:
            if a.host_cpu or a.mp_check:print('cost_identity: --host-cpu and --mp-check go with --model M --exe BIN',file=sys.stderr);return 2
            if not a.runs:print('cost_identity: nothing to check',file=sys.stderr);return 2
            recs=[check_run(r)for r in a.runs]
    except (OSError,ValueError)as e:print(f'cost_identity: {e}',file=sys.stderr);return 2
    for r in recs:print(json.dumps(r))
    return 0 if all(r['ok']for r in recs)else 1
if __name__=='__main__':sys.exit(main())
