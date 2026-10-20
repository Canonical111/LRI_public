#!/usr/bin/env python3
"""Exercise real C8 checkpoints, coverage guards, resume, merge and test labelling."""
from __future__ import annotations
import argparse
import copy
from decimal import Decimal
import json
import itertools
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import production as prod
from common import digest,load


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--backend',choices=['decimal','gmp'],default='gmp')
    args=ap.parse_args()
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    records=[]
    def run(script,*words,ok=True):
        cmd=[sys.executable,'-B',str(ROOT/'tools'/script),*map(str,words)]
        p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        if (p.returncode==0)!=ok:
            raise AssertionError(f'Unexpected exit {p.returncode}: {cmd}\n{p.stdout}\n{p.stderr}')
        return p
    with tempfile.TemporaryDirectory(prefix='c8_workflow_',dir=ROOT/'verification') as td:
        base=Path(td)
        scratch=base/'scratch';scratch.mkdir()
        plans=[]
        for chunk in (4,8):
            directory=base/f'chunk{chunk}'
            run('production.py','plan',directory,'--seed','2853748594021','--backend',args.backend,
                '--replicates','4','--points','8','--test-graphs','1','--shards','1',
                '--threads','2','--checkpoint-tasks','4','--chunk-points',chunk)
            manifest=load(directory/'manifest.json')
            if len(manifest['groups'])!=24:raise AssertionError('Missing C8 campaign/sector/loop group')
            run('production.py','merge',directory,'--scratch',scratch,ok=False)
            stage=base/f'staged{chunk}'
            run('stage_runtime.py',directory,stage,'--index','0','--pack-cache',base/'pack_cache')
            stage_info=load(stage/'staging.json')['pack_cache']
            if stage_info['copied']!=(chunk==4):raise AssertionError('Node cache did not publish once and reuse the same pack')
            run(stage/'tools/production.py','run',directory,'--index','0','--threads','2','--scratch',scratch,'--max-blocks','1')
            shutil.rmtree(stage)
            if not Path(stage_info['path']).is_file():raise AssertionError('Job cleanup removed the shared cache pack')
            checkpoints=list((directory/'groups').glob('*/checkpoints/*.json'))
            if len(checkpoints)!=1:raise AssertionError('Expected one committed resumable block')
            first=checkpoints[0];original=digest(first)
            run('production.py','run',directory,'--index','0','--threads','2','--scratch',scratch)
            if digest(first)!=original:raise AssertionError('Resume changed an existing checkpoint')
            run('run_local.py',directory,'--workers','2','--threads','2','--scratch',scratch)
            # A malformed checkpoint must fail before a result can be assembled.
            m,im,mh,changes=prod.verify_base(directory)
            job=m['jobs'][0];p,cfg=prod.group_of(directory,m,job['group'])
            db=prod.dbopen(p/'tasks.sqlite',True)
            block=next(prod.task_blocks(db,job['shard'],m['checkpoint_tasks']))
            doc=load(first);damaged=copy.deepcopy(doc)
            damaged['native']['rows'][0]['values'][0]='0'
            try:prod.validate_checkpoint(damaged,block,cfg,m,mh)
            except ValueError:pass
            else:raise AssertionError('Changed checkpoint payload accepted')
            db.close()
            run('production.py','merge',directory,'--scratch',scratch)
            # Rebuild from the same committed checkpoints with independent
            # group workers: every published byte must match serial merging.
            merged_files=[p for entry in m['groups']for p in
                          (directory/'groups'/entry['name']/'merged.json',directory/'groups'/entry['name']/'graph_replicates.csv')]
            serial_hashes={p:digest(p)for p in merged_files}
            for p in merged_files:p.unlink()
            run('production.py','merge',directory,'--scratch',scratch,'--workers','2')
            if any(digest(p)!=checksum for p,checksum in serial_hashes.items()):raise AssertionError('Parallel group merge changed published bytes')
            run('production.py','merge',directory,'--scratch',scratch)
            run('assemble.py',directory,'--bootstrap','16')
            result=load(directory/'C8_test_result.json')
            if result['C8_full'] is not None or result['coefficients'] is not None or not result['test_only']:
                raise AssertionError('Incomplete graph test presented as a physical coefficient')
            if not result['test_partial']:raise AssertionError('Missing explicitly labelled test data')
            plans.append(directory)
            records.append({'chunk_points':chunk,'groups':len(m['groups']),'jobs':len(m['jobs']),
                            'resume_preserved_checkpoint':True,'missing_coverage_rejected':True,
                            'corrupt_payload_rejected':True,'merge_idempotent':True,
                            'serial_and_parallel_merge_bytes_identical':True,
                            'verified_cached_stage_native_run':True,'stage_cleanup_preserved_cache':True,
                            'physical_result_keys_null':True})
        largest=Decimal(0)
        for group in load(plans[0]/'manifest.json')['groups']:
            arrays=[load(p/'groups'/group['name']/'merged.json')['batches'] for p in plans]
            for ra,rb in zip(*arrays):
                for a,b in zip(ra,rb):
                    a,b=Decimal(str(a)),Decimal(str(b))
                    e=abs(a-b)/max(Decimal(1),abs(a))
                    largest=max(largest,e)
        if largest>Decimal('5e-16'):raise AssertionError(f'Chunking changed the estimator: {largest}')
        report={'status':'passed','order':8,'backend':args.backend,'campaigns':records,
                'native_executable_sha256':digest(prod.exe_for(args.backend)),
                'split_vs_unsplit_max_normalized_difference':str(largest),
                'scope':'Real native integration on an explicitly incomplete selection; no physical coefficient.'}
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))


if __name__=='__main__':main()
