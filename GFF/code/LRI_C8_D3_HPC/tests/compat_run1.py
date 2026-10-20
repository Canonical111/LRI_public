#!/usr/bin/env python3
"""A-ASM-3: tools/assemble.py combine(order=7), the vendored order-8 assembly at order 7, applied to the 20 merged
replicate arrays of the C7(3) run1 production (reference/c7d3_run1_results/, byte copies of
LRI_C7_D3_HPC_production/results_run1-20260930-m4096/) reproduces its C7_result.json:
  * C7_full = -220.35448047392794, the SE 0.031818800575016494 and coefficients[0..7] to 1e-12 relative;
  * power_correction, power_differences[3..7] and power_free_correction_covariance (differences of numbers of size
    |C7| ~ 220, whose last bits are amplified; H2 order-7 evidence: 16,384 ulp in power_correction, 262,144 ulp in
    power_differences[5] on another platform) to the absolute bound 1e-12 |C7_full| (2.2e-10).
Each merged.json must be the one C7_result.json was assembled from (its sha256) with an intact payload hash. The ulp
offset of every compared field is recorded with the stack (Python, numpy, CPU, platform). Read-only; no bootstrap.
Usage: python3 -B tests/compat_run1.py [--run DIR] [--output FILE]"""
from __future__ import annotations
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from assemble import combine,two_loop  # noqa: E402
from common import cpu_model,object_hash  # noqa: E402

RUN=ROOT/'reference/c7d3_run1_results'
PUBLISHED_C7=-220.35448047392794;PUBLISHED_SE=0.031818800575016494
REL=1e-12;ABS_FACTOR=1e-12

def cpu_brand()->str:
    """The CPU model for the ulp table: /proc/cpuinfo's model name (common.cpu_model), else macOS's sysctl brand string."""
    c=cpu_model()
    if c not in('','arm','arm64','unknown')and c!=platform.machine():return c
    try:return subprocess.run(['sysctl','-n','machdep.cpu.brand_string'],capture_output=True,text=True,timeout=10).stdout.strip()or c
    except (OSError,subprocess.SubprocessError):return c

def ulp(x:float,y:float)->float:
    return abs(x-y)/float(np.spacing(abs(y)))if y else(0. if x==y else float('inf'))

def run(directory:Path)->dict:
    m=json.loads((directory/'manifest.json').read_bytes());res=json.loads((directory/'C7_result.json').read_bytes())
    if m['schema']!='c7-d3-production-1':raise ValueError('expected the C7(3) production plan (c7-d3-production-1)')
    if res['C7_full']!=PUBLISHED_C7 or res['sampling_standard_error']!=PUBLISHED_SE:raise ValueError('C7_result.json is not the published run1 result')
    if m.get('primitive_mode')!='recompute'or res.get('primitive_mode')!='recompute':raise ValueError('run1 recomputed the primitives (no retained offset)')
    ar={s:{t:{}for t in 'ab'}for s in ('free','power')};seen=set()
    for g in m['groups']:
        p=directory/'groups'/g['name'];cfg=json.loads((p/'config.json').read_bytes());raw=(p/'merged.json').read_bytes();d=json.loads(raw)
        if hashlib.sha256(raw).hexdigest()!=res['merged_sha256'][g['name']]:raise ValueError(f'{g["name"]}: merged.json is not the one C7_result.json was assembled from')
        if object_hash({k:v for k,v in d.items()if k!='payload_sha256'})!=d['payload_sha256']:raise ValueError(f'{g["name"]}: merged payload corruption')
        key=(cfg['sector'],cfg['campaign'],cfg['L'])
        if key in seen:raise ValueError(f'duplicate group {key}')
        seen.add(key);ar[cfg['sector']][cfg['campaign']][cfg['L']]=np.asarray(d['batches'],float)
    if len(seen)!=20:raise ValueError(f'expected 20 groups, got {len(seen)}')
    B2,_=two_loop(7);r=combine(ar,order=7,bootstrap=0,B2=B2)
    absb=ABS_FACTOR*abs(res['C7_full'])
    rel_fields={'C7_full':(r['C7_full'],res['C7_full']),'sampling_standard_error':(r['sampling_standard_error'],res['sampling_standard_error'])}
    rel_fields.update({f'coefficients[{i}]':(x,y)for i,(x,y)in enumerate(zip(r['coefficients'],res['coefficients']))})
    abs_fields={'power_correction':(r['power_correction'],res['power_correction']),
                'power_free_correction_covariance':(r['power_free_correction_covariance'],res['power_free_correction_covariance'])}
    abs_fields.update({f'power_differences[{i}]':(r['power_differences'][i],res['power_differences'][i])for i in range(3,8)})
    if len(r['coefficients'])!=8 or len(res['coefficients'])!=8:raise ValueError('coefficients[0..7] expected')
    table={};failures={}
    for k,(x,y)in rel_fields.items():
        e=abs(x-y)/abs(y)if y else abs(x);ok=e<=REL;table[k]=dict(value=x,published=y,relative_difference=e,bound=f'relative {REL}',ulp=ulp(x,y),passed=ok)
        if not ok:failures[k]=table[k]
    for k,(x,y)in abs_fields.items():
        e=abs(x-y);ok=e<=absb;table[k]=dict(value=x,published=y,absolute_difference=e,bound=f'absolute 1e-12 |C7_full| = {absb!r}',ulp=ulp(x,y),passed=ok)
        if not ok:failures[k]=table[k]
    return dict(schema='c8-d3-gate-1',gate='A-ASM-3 compat_run1',passed=not failures,run=str(directory.relative_to(ROOT))if directory.is_relative_to(ROOT)else str(directory),
                manifest_sha256=hashlib.sha256((directory/'manifest.json').read_bytes()).hexdigest(),
                result_sha256=hashlib.sha256((directory/'C7_result.json').read_bytes()).hexdigest(),
                C7_full=r['C7_full'],published_C7_full=res['C7_full'],bitwise_identical_C7=r['C7_full']==res['C7_full'],
                sampling_standard_error=r['sampling_standard_error'],ulp_table=table,max_ulp=max(v['ulp']for v in table.values()),
                hard_gates={k:(v if isinstance(v,str)else 'passed')for k,v in r['hard_gates'].items()},
                stack=dict(python=platform.python_version(),numpy=np.__version__,cpu=cpu_brand(),platform=platform.platform(),machine=platform.machine()),
                failures=failures)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--run',type=Path,default=RUN);ap.add_argument('--output',type=Path)
    a=ap.parse_args();out=run(a.run.resolve())
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=1,default=str)+'\n')
    print(json.dumps({k:out[k]for k in ('passed','C7_full','published_C7_full','bitwise_identical_C7','max_ulp','stack','failures')},indent=1))
    return 0 if out['passed']else 1
if __name__=='__main__':sys.exit(main())
