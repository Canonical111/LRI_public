#!/usr/bin/env python3
"""Read measured checkpoint task costs to improve future shard load balancing.

This never changes integration weights or sample allocations. A cost model from
an independent pilot can be frozen into a new plan. Use the same hardware/backend.
"""
from pathlib import Path
import argparse,math
from common import load,dump,digest,object_hash
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args();m=load(a.run/'manifest.json');cost={};nfiles=0;mh=digest(a.run/'manifest.json')
for group in m['groups']:
    d=a.run/'groups'/group['name'];cfg=load(d/'config.json')
    for f in (d/'checkpoints').glob('*.json'):
        doc=load(f)
        if doc['manifest_sha256']!=mh or doc['config_hash']!=object_hash(cfg) or doc['payload_sha256']!=object_hash(doc['native']):raise ValueError('Invalid run checkpoint')
        for r in doc['native']['rows']:
            k=f'{cfg["sector"]}:{cfg["L"]}:{r["graph"]}';t,n=cost.get(k,(0.,0));cost[k]=(t+r['seconds'],n+r['end']-r['begin'])
        nfiles+=1
out=dict(schema='c8-d2-cost-model-1',dimension=2,order=8,backend=m['backend'],source_manifest_sha256=digest(a.run/'manifest.json'),checkpoint_files=nfiles,seconds_per_point={k:max(1e-12,t/n)for k,(t,n)in cost.items()},scope='Placement only; sample counts and random streams unchanged. Wall cost per task, not isolated hardware cycle count.')
dump(a.output,out)
