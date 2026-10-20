"""Read-only campaign status: one line per manifest item.

done | conflict | running/pending | interrupted | failed | orphan | owned | not started,
with generation, owner job and token, last exit code and peak RSS. A result counts
as done only if its identity matches the manifest item on the receipt's runtime
and its payload passes the gates; anything else is reported as a conflict.
"""
import argparse
import json
import sys
from pathlib import Path

from symmetry_common import (TERMINAL,FINISHED_OK,SlurmError,load_site,user_jobs,sacct_state,last_events)
from lri_spin.io import read_record
from lri_spin.manifest import load_manifest,contained,result_checker
from lri_spin.campaign import OWNER,OwnershipError,read_owner,classify_results,gen_name,item_digest


def has_checkpoint(folder):
    return folder.is_dir() and any(p.name in ('state.npz','tuning.json') for p in folder.rglob('*'))


def status(item,folder,logs,live,slurm,check):
    row={'id':item['id'],'kind':item['kind']}
    results,conflicts=classify_results(folder,check)
    owner=None
    if (folder/OWNER).exists():
        try:owner=read_owner(folder)
        except OwnershipError as exc:row.update(state='owner unreadable',detail=str(exc));return row
        row.update(generation=owner['generation'],job=owner.get('job_id'),token=owner['token'])
        if owner.get('item_sha256')!=item_digest(item):
            row.update(state='conflict',detail='this ID was submitted with a different item definition; its progress is not reported')
            return row
        if owner.get('job_id'):
            e=last_events(logs,owner['job_id']).get(item['id'])
            if e:row.update(last_rc=e.get('rc'),peak_rss_kib=e.get('peak_rss_kib'))
    if conflicts:
        g,p,why=conflicts[0]
        row.update(state='conflict',result=str(p),detail=f'{gen_name(g)} does not match this item: {why}');return row
    if results:
        gens=[g for g,_ in results];current=owner['generation'] if owner else None
        g,path=next(((g,p) for g,p in results if g==current),results[-1])
        row.update(state='done',result=str(path),result_generation=g)
        if current is not None and g!=current:row['detail']=f'result from older generation {gen_name(g)}'
        return row
    if owner is None:row['state']='not started';return row
    job=owner.get('job_id')
    if not job:row['state']='orphan (no job id)';return row
    if not slurm:row['state']='owned (slurm not queried)';return row
    if job in live:row['state']=live[job][1].lower();return row
    try:st=sacct_state(job)
    except SlurmError as exc:row.update(state='unknown',detail=str(exc));return row
    row['job_state']=st
    if st not in TERMINAL:row['state']=f'unknown ({st})';return row
    rc=row.get('last_rc')
    if rc is not None and rc not in FINISHED_OK:row['state']='failed'
    elif has_checkpoint(folder/gen_name(owner['generation'])):row['state']='interrupted'
    else:row['state']='ended without checkpoint'
    return row


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site');p.add_argument('--campaign',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--receipt',required=True,help='validation receipt: its runtime defines which results count as done')
    p.add_argument('--logs');p.add_argument('--no-slurm',action='store_true');p.add_argument('--json',action='store_true')
    a=p.parse_args(argv);site=load_site(a.site)
    campaign=Path(a.campaign).resolve();logs=Path(a.logs or Path(site['base'])/'logs')
    try:m=load_manifest(a.manifest,campaign)
    except ValueError as exc:raise SystemExit(f'Invalid manifest: {exc}')
    runtime=read_record(a.receipt)['runtime']
    live={}
    if not a.no_slurm:
        try:live=user_jobs()
        except SlurmError as exc:raise SystemExit(f'squeue failed: {exc}')
    rows=[status(i,contained(campaign,i['id']),logs,live,not a.no_slurm,result_checker(i,m['source_sha256'],runtime))
          for i in m['items']]
    if a.json:print(json.dumps(rows,indent=2))
    else:
        for r in rows:
            extra=' '.join(f'{k}={r[k]}' for k in ('generation','job','token','last_rc','peak_rss_kib','result','detail') if r.get(k) is not None)
            print(f'{r["id"]:<28} {r["state"]:<26} {extra}')
        counts={}
        for r in rows:counts[r['state']]=counts.get(r['state'],0)+1
        print('Summary:',', '.join(f'{v} {k}' for k,v in sorted(counts.items())))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
