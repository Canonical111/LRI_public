#!/usr/bin/env python3
"""Campaign progress and fenced lease recovery.

    status.py --campaign DIR                      done/failed/running/pending items, live leases, Slurm jobs
    status.py --campaign DIR --break-lease KEY --generation G --job J
        online recovery of an identified dead owner (refused unless G is current, owned by job J, J dead)
    status.py --campaign DIR --maintenance --break-unreadable KEY --generation G
        offline recovery of an unreadable owner: publishes MAINTENANCE (blocks launchers and submit),
        requires that no lri-<campaign> job is queued or running, tombstones, removes the marker
KEY is a lease base path, e.g. DIR/items/leases/<item> or DIR/results/claims/<key>.lock.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
CODE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(CODE/'src'))
from lri_dressed.lease import Lease,break_lease,break_unreadable,owner_state,Claimed
from lri_dressed.pack import completion_valid


def campaign_jobs(cid):
    p=subprocess.run(['squeue','-h','-u',os.environ.get('USER',''),'-n',f'lri-{cid}','-o','%i %T %N %L'],capture_output=True,text=True,timeout=60)
    if p.returncode:raise RuntimeError('squeue failed: '+p.stderr)
    return [l.split() for l in p.stdout.splitlines() if l.strip()]


def campaign_key(campaign,key):
    """Resolve a lease base path and require that it belongs to THIS campaign's lease namespaces."""
    k=Path(key);d=Path(str(k)+'.lease.d').resolve()
    roots=[(campaign/'items'/'leases').resolve(),(campaign/'results'/'claims').resolve()]
    if not d.is_dir() or not any(d.parent==r for r in roots):
        raise SystemExit(f'{key} is not a lease of campaign {campaign} (allowed: {[str(r) for r in roots]})')
    return d.parent/d.name[:-len('.lease.d')]


def summary(campaign):
    m=json.loads((campaign/'manifest.json').read_text());items={i['id']:i for i in m['items']}
    done=set();invalid=[]
    for p in (campaign/'items/done').glob('*.json'):
        try:ok=p.stem in items and completion_valid(items[p.stem],json.loads(p.read_text()),m['source_sha256'])
        except (OSError,ValueError):ok=False
        (done.add if ok else invalid.append)(p.stem)
    failed={p.stem for p in (campaign/'items/failed').glob('*.json')}-done
    leased={}
    for d in (campaign/'items/leases').glob('*.lease.d'):
        iid=d.name[:-len('.lease.d')];lease=Lease(d.parent/iid);top,owner,free=lease.holder()
        if not free:leased[iid]={'generation':top,'owner':owner,'state':owner_state(owner)}
    pending=[i for i in items if i not in done and i not in failed and i not in leased]
    try:jobs=campaign_jobs(m['campaign'])
    except Exception as exc:jobs=[['unknown',str(exc)]]
    core_h=sum(items[i]['est_seconds']*items[i]['threads'] for i in pending+list(leased))/3600
    return {'campaign':m['campaign'],'items':len(items),'done':len(done),'invalid_completions':sorted(invalid),
            'failed':sorted(failed),'running_or_leased':leased,
            'pending':len(pending),'remaining_estimate_core_hours':round(core_h,2),'slurm_jobs':jobs,
            'maintenance':(campaign/'MAINTENANCE').exists()}


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--campaign',required=True);ap.add_argument('--break-lease');ap.add_argument('--generation',type=int);ap.add_argument('--job')
    ap.add_argument('--maintenance',action='store_true');ap.add_argument('--break-unreadable');a=ap.parse_args()
    campaign=Path(a.campaign).resolve()
    if a.break_lease:
        if a.generation is None or not a.job:ap.error('--break-lease needs --generation and --job')
        print(break_lease(campaign_key(campaign,a.break_lease),a.generation,a.job));return 0
    if a.break_unreadable:
        if not a.maintenance or a.generation is None:ap.error('--break-unreadable needs --maintenance and --generation')
        target=campaign_key(campaign,a.break_unreadable)
        cid=json.loads((campaign/'manifest.json').read_text())['campaign'];marker=campaign/'MAINTENANCE'
        tmp=campaign/f'.MAINTENANCE.{os.getpid()}';tmp.write_text(json.dumps({'pid':os.getpid(),'host':os.uname().nodename}))
        try:os.link(tmp,marker)
        except FileExistsError:raise SystemExit('Another maintenance operation holds the marker')
        finally:tmp.unlink(missing_ok=True)
        try:
            jobs=campaign_jobs(cid)
            if jobs:raise SystemExit(f'Campaign jobs still queued or running: {jobs}')
            print(break_unreadable(target,a.generation))   # refuses a readable (identifiable) owner
        finally:marker.unlink(missing_ok=True)
        return 0
    print(json.dumps(summary(campaign),indent=1,default=str));return 0

if __name__=='__main__':sys.exit(main())
