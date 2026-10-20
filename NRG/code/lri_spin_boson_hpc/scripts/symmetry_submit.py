"""Submit packed lanes to symmetry; the only tool that creates or reclaims item owners.

Runs only on the configured login host and holds <campaign>/.submit.lock, which
is a valid mutex there (BeeGFS flock is node-local). An owner is reclaimed only
when its job is confirmed dead: absent from squeue and terminal in sacct; any
query failure or unknown state refuses. Every reclaim starts a new generation.

  init      mark a campaign root
  submit    new items only (owned items are refused)
  resubmit  new items plus items whose previous job is confirmed dead
  validate  submit the compute-node validation job
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from symmetry_common import (ROOT,TERMINAL,SlurmError,load_site,short_host,require_login_host,require_frozen,
                             submit_lock,user_jobs,sacct_state,jobs_by_name)
from lri_spin.io import read_record,source_hash,_atomic
from lri_spin.manifest import load_manifest,reservation_gib,cost,contained,result_checker
from lri_spin.campaign import (OWNER,OwnershipError,init_campaign,read_owner,create_owner,replace_owner,
                               remove_owner,generations,classify_results,is_campaign_root,item_digest,gen_name)

ORPHAN_MIN_AGE=900.   # seconds; an accepted job may not be visible to squeue/sacct at once


def append_record(campaign,record):
    record['time']=time.time()
    with open(Path(campaign)/'SUBMITTED.jsonl','a') as f:
        f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())


def snapshot(source,dest):
    """Immutable copy that admission and execution both use; returns its sha256."""
    blob=Path(source).read_bytes()
    _atomic(dest,lambda f:f.write(blob));os.chmod(dest,0o444)
    return hashlib.sha256(blob).hexdigest()


def check_inputs(manifest,receipt,campaign,site):
    m=load_manifest(manifest,campaign)
    if m.get('source_sha256')!=source_hash():raise SystemExit('Manifest was frozen for another solver source')
    r=read_record(receipt)
    if not r.get('passed') or r.get('source_sha256')!=source_hash():raise SystemExit('Receipt is not a passed receipt for this source')
    budget=site['mem_gib']-site['headroom_gib']
    for item in m['items']:
        if item.get('backend','ordered')!='ordered':raise SystemExit(f'{item["id"]}: only the ordered backend is used on symmetry')
        threads=item['config'].get('threads',1)
        if threads>site['cores']:raise SystemExit(f'{item["id"]}: {threads} threads exceed {site["cores"]} cores')
        if reservation_gib(item)>budget:raise SystemExit(f'{item["id"]}: reservation {reservation_gib(item):.1f} GiB exceeds {budget} GiB')
    return m,r


def classify(item,folder,args,live,now,check):
    """('skip'|'new'|'reclaim', reason, old owner, adopted job id)."""
    matching,conflicting=classify_results(folder,check)
    if conflicting:
        g,_,why=conflicting[0]
        return 'skip',f'conflicting result in {gen_name(g)} (not this item definition/runtime: {why}); resolve by hand or use a new ID',None,None
    if matching:return 'skip','done',None,None
    if not (folder/OWNER).exists():return 'new','',None,None
    try:owner=read_owner(folder)
    except OwnershipError as exc:return 'skip',f'malformed owner ({exc}); fix by hand',None,None
    if owner.get('item_sha256')!=item_digest(item):
        return 'skip','item definition differs from the one first submitted under this ID; use a new ID',None,None
    if args.cmd=='submit':return 'skip','owned (use resubmit)',None,None
    job=owner.get('job_id');adopted=None
    if not job:
        matches=jobs_by_name(owner['job_name'],owner['created']-3600,live)
        if len(matches)>1:return 'skip',f'ambiguous jobs {matches} for {owner["job_name"]}',owner,None
        if len(matches)==1:job=adopted=matches[0]
        else:
            age=now-owner['created']
            if not args.reclaim_orphans:return 'skip','orphan owner (no job found); needs --reclaim-orphans',owner,None
            if not age>=ORPHAN_MIN_AGE:return 'skip',f'orphan owner only {age:.0f} s old (minimum {ORPHAN_MIN_AGE:.0f} s)',owner,None
            return 'reclaim','orphan',owner,None
    if job in live:return 'skip',f'job {job} is {live[job][1]}',owner,adopted
    state=sacct_state(job)
    if state not in TERMINAL:return 'skip',f'job {job} state {state!r} is not terminal',owner,adopted
    return 'reclaim',f'job {job} {state}',owner,adopted


def pack(todo,lanes):
    lanes=max(1,min(lanes,len(todo)));out=[[] for _ in range(lanes)];load=[0.]*lanes
    for t in sorted(todo,key=lambda t:-t['cost']):
        k=load.index(min(load));out[k].append(t);load[k]+=t['cost']
    return [l for l in out if l]


def sbatch_command(site,args,spec,job_name,dry):
    logs=Path(site['base'])/'logs'
    return ['sbatch','--test-only' if dry else '--parsable','-p',site['partition'],'--exclude',site['exclude'],
            '-N','1','--exclusive','--mem',site['mem'],'-t',args.time,'--signal',site['signal'],'--no-requeue',
            '-J',job_name,'--comment',job_name,'-o',str(logs/'slurm-%j.out'),
            '--export',f'ALL,LRI_SPIN_CODE={ROOT},LRI_SPIN_BASE={site["base"]}',
            str(ROOT/'cluster'/'symmetry'/'lane.sbatch'),'--spec',str(spec),'--logs',str(logs)]


def check_time(value,site):
    def secs(t):
        d,_,hms=t.rpartition('-');h,m,s=(int(x) for x in hms.split(':'))
        return (int(d) if d else 0)*86400+h*3600+m*60+s
    if secs(value)>secs(site['max_time']):raise SystemExit(f'Time {value} exceeds {site["max_time"]}')


def submit(args,site):
    campaign=Path(args.campaign).resolve();args.campaign=campaign
    if not is_campaign_root(campaign):raise SystemExit(f'{campaign} is not a campaign root; run init first')
    require_login_host(site,campaign);require_frozen(site);check_time(args.time,site)
    check_inputs(args.manifest,args.receipt,campaign,site)   # invalid input writes nothing at all
    submission=uuid.uuid4().hex;subdir=campaign/'lanes'/submission
    if args.dry_run:manifest,receipt=args.manifest,args.receipt
    else:
        # Validate the snapshots themselves: what was checked is exactly what lanes run.
        subdir.mkdir(parents=True)
        manifest,receipt=subdir/'manifest.json',subdir/'receipt.json'
        hashes={'manifest_sha256':snapshot(args.manifest,manifest),'receipt_sha256':snapshot(args.receipt,receipt)}
    try:return _submit(args,site,campaign,submission,subdir,manifest,receipt,None if args.dry_run else hashes)
    finally:
        if not args.dry_run and not any(subdir.glob('lane*.json')):shutil.rmtree(subdir,ignore_errors=True)


def _submit(args,site,campaign,submission,subdir,manifest,receipt,hashes):
    m,r=check_inputs(manifest,receipt,campaign,site)
    print('Note: the receipt runtime is checked on the compute node by the lane and by every item.',file=sys.stderr)
    items={i['id']:(n,i) for n,i in enumerate(m['items'])}
    chosen=args.ids or list(items)
    unknown=[i for i in chosen if i not in items]
    if unknown:raise SystemExit(f'Unknown IDs {unknown}')
    if not args.dry_run:(Path(site['base'])/'logs').mkdir(parents=True,exist_ok=True)
    with submit_lock(campaign):
        now=time.time()
        try:live=user_jobs()
        except SlurmError as exc:raise SystemExit(f'Refusing: {exc}')
        todo=[]
        for name in chosen:
            index,item=items[name];folder=contained(campaign,name)
            check=result_checker(item,m['source_sha256'],r['runtime'])
            try:action,reason,owner,adopted=classify(item,folder,args,live,now,check)
            except SlurmError as exc:action,reason,owner,adopted='skip',f'query failed ({exc})',None,None
            if adopted and not args.dry_run:
                replace_owner(folder,{**owner,'job_id':adopted,'adopted':now});owner=read_owner(folder)
            if action=='skip':print(f'{name}: skipped, {reason}');continue
            gens=[g for g,_ in generations(folder)]
            generation=max([owner['generation'] if owner else 0]+gens)+1
            todo.append({'id':name,'index':index,'folder':folder,'old':owner,'generation':generation,
                         'cost':cost(item),'reason':reason or 'new','item_sha256':item_digest(item)})
        if not todo:print('Nothing to submit');return 0
        failures=0
        for k,lane in enumerate(pack(todo,args.lanes)):
            job_name=f'lrisb-{submission[:12]}-{k}'
            spec=subdir/f'lane{k}.json'
            cmd=sbatch_command(site,args,spec,job_name,args.dry_run)
            for t in lane:t['token']=f'{submission}:{t["id"]}:g{t["generation"]:04d}'
            if args.dry_run:
                r=subprocess.run(cmd,capture_output=True,text=True)
                print(f'lane {k}: {[t["id"] for t in lane]} -> rc {r.returncode} {(r.stderr or r.stdout).strip()}')
                failures+=r.returncode!=0;continue
            _atomic(spec,lambda f:f.write(json.dumps({'schema':2,'submission':submission,'lane':k,'job_name':job_name,
                'campaign':str(campaign),'manifest':str(manifest),'receipt':str(receipt),**hashes,
                'items':[{'index':t['index'],'id':t['id'],'token':t['token'],'generation':t['generation']} for t in lane]},indent=2).encode()))
            done=[]
            try:
                for t in lane:
                    data={'token':t['token'],'generation':t['generation'],'submission':submission,'lane':k,
                          'job_name':job_name,'created':time.time(),'job_id':None,'item_sha256':t['item_sha256'],
                          'previous':None if t['old'] is None else {'token':t['old']['token'],'job_id':t['old'].get('job_id'),'reason':t['reason']}}
                    if t['old'] is None:create_owner(t['folder'],data)
                    else:
                        if read_owner(t['folder'])['token']!=t['old']['token']:raise OwnershipError(f'{t["id"]}: owner changed under the lock')
                        replace_owner(t['folder'],data)
                    t['data']=data;done.append(t)
                r=subprocess.run(cmd,capture_output=True,text=True)
                job_id=r.stdout.strip().split(';')[0] if r.returncode==0 else ''
                if not job_id.isdigit():raise RuntimeError(f'sbatch failed ({r.returncode}): {r.stderr.strip()}')
            except (OSError,OwnershipError,RuntimeError) as exc:
                for t in done:
                    if t['old'] is None:remove_owner(t['folder'],t['token'])
                    else:replace_owner(t['folder'],t['old'])
                append_record(campaign,{'submission':submission,'lane':k,'job_name':job_name,'error':str(exc),
                                        'items':[t['id'] for t in lane]})
                print(f'lane {k}: FAILED, owners restored: {exc}',file=sys.stderr);failures+=1;continue
            for t in lane:replace_owner(t['folder'],{**t['data'],'job_id':job_id})
            append_record(campaign,{'submission':submission,'lane':k,'job_name':job_name,'job_id':job_id,'command':cmd,
                'items':[{'id':t['id'],'generation':t['generation'],'token':t['token'],'reason':t['reason']} for t in lane]})
            print(f'lane {k}: job {job_id} {job_name}: {[t["id"] for t in lane]}')
        return 1 if failures else 0


def validate(args,site):
    require_login_host(site);require_frozen(site);check_time(args.time,site)
    out=Path(site['base'])/'validation';out.mkdir(parents=True,exist_ok=True)
    cmd=['sbatch','--test-only' if args.dry_run else '--parsable','-p',site['partition'],'--exclude',site['exclude'],
         '-N','1','--exclusive','--mem','32G','-t',args.time,'--no-requeue','-J','lri-spin-validate',
         '-o',str(out/'validate-%j.log'),'--export',f'ALL,LRI_SPIN_CODE={ROOT},LRI_SPIN_BASE={site["base"]}',
         str(ROOT/'cluster'/'symmetry'/'validate.sbatch')]
    r=subprocess.run(cmd,capture_output=True,text=True)
    print((r.stdout+r.stderr).strip());return r.returncode


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--site');sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('init');i.add_argument('--campaign',required=True)
    for name in ('submit','resubmit'):
        s=sub.add_parser(name);s.add_argument('--campaign',required=True);s.add_argument('--manifest',required=True)
        s.add_argument('--receipt',required=True);s.add_argument('--lanes',type=int,default=1);s.add_argument('--ids',nargs='+')
        s.add_argument('--time');s.add_argument('--dry-run',action='store_true')
        s.add_argument('--reclaim-orphans',action='store_true')
    v=sub.add_parser('validate');v.add_argument('--time',default='01:00:00');v.add_argument('--dry-run',action='store_true')
    args=p.parse_args(argv);site=load_site(args.site)
    if getattr(args,'time',None) is None:args.time=site['max_time']
    if args.cmd=='init':
        require_login_host(site);init_campaign(args.campaign,short_host());print('Campaign root:',Path(args.campaign).resolve());return 0
    if args.cmd=='validate':return validate(args,site)
    try:return submit(args,site)
    except ValueError as exc:raise SystemExit(f'Invalid input: {exc}')


if __name__=='__main__':
    raise SystemExit(main())
