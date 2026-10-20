#!/usr/bin/env python3
"""Replay the ARCHIVED d=3 production streams with the built worker and rebuild C7(3) (make test-replay; D3-2).

C8(3) (PLAN.md A-RPL-7, HD3; Stage 3a): the worker is the C8 worker in order-7 mode (default bin/c8d3_gmp; --exe
bin/ref/c7d3_gmp gives the toolchain baseline of J-E1). The archived C7D3TASKS1 task files are fed unchanged (HD3: the
C8 worker reads C7D3TASKS1 as an order-7 task file) with inputs/order7/gamma_d3_7.txt, checked against the archived
gamma_sha256, and C7 is rebuilt from the replayed rows with assemble.combine(order=7) (PLAN A-RPL-7: the vendored
order-8 assembly at order 7, as tests/compat_run1.py uses it) on inputs/order7/two_loop.json, checked against its
pinned sha256 (3dddb802...).
For each of the 160 records of reference/records/production_{a,b} the worker runs the archived task file on the
archived Sobol net with the archived driver's native seed (config seed, +348612 for power; tests/archived_replay.py),
layout and rate, from the unpacked reference graphs. Every input is identified before use:
records, tasks and nets against the record manifests; the gamma table against the manifests' gamma_sha256; every graph
payload against the member hash of the verified inventory (inputs/manifest.json -> inputs/inventory.json).
Requirements:
  * every row's task coordinates and binary128/GMP promotion counters equal the archive;
  * per-row jets agree to normalized |x-y|/max(1,|x|) <= 1e-10 (CPU-dependent last bits of glibc's long-double
    expl/logl amplified by accepted cancellation; measured <= 1.0e-11 on symmetry AMD EPYC 7532);
  * C7(3) and its SE rebuilt from the replayed rows (summed as reference/code/analyze.py does) with
    assemble.combine(order=7, bootstrap=0) equal the published values to relative <= 1e-12.
The fraction of bitwise-identical rows is recorded. Everything is written to a temporary directory; nothing in the
package changes (an optional --output record is written only where asked). About 2 minutes at 64 threads.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,subprocess,sys,tempfile,time
from decimal import Decimal as D
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import assemble
from common import digest,dump,host_info
R=ROOT/'reference';ROW_TOL=D('1e-10');C7_TOL=1e-12;POWER_SEED_OFFSET=348612
GAMMA7=ROOT/'inputs/order7/gamma_d3_7.txt';TWO_LOOP7=ROOT/'inputs/order7/two_loop.json'
TWO_LOOP7_SHA256='3dddb80233989e2397ede19d575a80437297d3d59c70e444a67daf3a0df34aca'   # a6ce987 inputs/two_loop.json (HD4)

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def verified_graphs()->dict:
    """{(sector, L, graph): sha256} from inputs/inventory.json, itself verified against inputs/manifest.json."""
    im=json.loads((ROOT/'inputs/manifest.json').read_text());inv=ROOT/'inputs/inventory.json'
    if digest(inv)!=im['sha256']['inventory.json']:raise AssertionError('inputs/inventory.json differs from inputs/manifest.json')
    d=json.loads(inv.read_text())   # the C8(3) inventory also holds the top-level flag "inspect_complete"
    return {(s,int(L),r['id']):r['sha256']for s in ('free','power')for L,rows in d[s].items()for r in rows}

def run(threads:int,exe:Path):
    members=verified_graphs();checked_graphs=set();gamma=digest(GAMMA7)
    report={'test':'archived_stream_replay','executable':str(exe),'executable_sha256':digest(exe),'threads':threads,'host':host_info(),'groups':{},'rows':0,'bitwise_rows':0}
    maxerr=D(0);ar={s:{t:{}for t in ('a','b')}for s in ('free','power')};t0=time.time()
    with tempfile.TemporaryDirectory(prefix='c7d3_stream_replay_')as td:
        for tag,camp in (('production_a','a'),('production_b','b')):
            cfg=json.loads((R/'records'/tag/'config.json').read_text());man=json.loads((R/'records'/tag/'manifest.json').read_text());B=man['args']['replicates']
            if gamma!=man['gamma_sha256']or digest(R/'inputs/gamma_d3_7.txt')!=man['gamma_sha256']:raise AssertionError(f'{tag}: gamma table differs from the archived gamma_sha256')
            for rec in man['records']:
                src=R/rec['file'];tasks=src.with_suffix('.tasks');net=R/'records'/tag/f'{rec["sector"]}_L{rec["L"]}.net'
                for p,h in ((src,rec['sha256']),(tasks,rec['tasks_sha256']),(net,rec['net_sha256'])):
                    if sha(p)!=h:raise AssertionError('archived input hash mismatch: '+str(p))
                for line in tasks.read_text().splitlines()[1:]:
                    key=(rec['sector'],rec['L'],int(line.split()[2]))
                    if key not in checked_graphs:
                        if sha(R/'inputs'/rec['sector']/f'L{rec["L"]}'/f'G{key[2]}.txt')!=members[key]:raise AssertionError(f'graph payload differs from the inventory: {key}')
                        checked_graphs.add(key)
                seed=cfg['seed']+(POWER_SEED_OFFSET if rec['sector']=='power'else 0);out=Path(td)/'out.json'
                cmd=[str(exe),str(R/'inputs'/rec['sector']),str(GAMMA7),str(net),str(tasks),str(out),str(seed),str(cfg['layout']),str(cfg['rate']),str(threads),'compensated','-']
                cp=subprocess.run(cmd,capture_output=True,text=True)
                if cp.returncode:raise RuntimeError(f'{src.name}: worker failed: {cp.stderr[-2000:]}')
                old=json.loads(src.read_text());new=json.loads(out.read_text());out.unlink()
                if new['seed']!=old['seed']or new['mp_backend']!=old['mp_backend']or new['L']!=old['L']or new.get('order',7)!=7 or len(new['rows'])!=len(old['rows']):raise AssertionError('metadata mismatch '+src.name)
                g=report['groups'].setdefault(f'{tag}:{rec["sector"]}:L{rec["L"]}',{'rows':0,'quad':0,'mp':0,'max_normalized_difference':'0'})
                arr=ar[rec['sector']][camp].setdefault(rec['L'],np.zeros((B,2*(8-rec['L'])),dtype=np.longdouble));gerr=D(g['max_normalized_difference'])
                for x,y in zip(old['rows'],new['rows'],strict=True):
                    if any(x[k]!=y[k]for k in ('uid','rep','graph','begin','end','total')):raise AssertionError('task coordinates differ in '+src.name)
                    if x['quad']!=y['quad']or x['mp']!=y['mp']:raise AssertionError(f'promotion counters differ in {src.name} row {x["uid"]}: {x["quad"]},{x["mp"]} vs {y["quad"]},{y["mp"]}')
                    e=max(abs(D(u)-D(v))/max(D(1),abs(D(u)))for u,v in zip(x['values'],y['values'],strict=True))
                    gerr=max(gerr,e);report['rows']+=1;report['bitwise_rows']+=x['values']==y['values'];g['rows']+=1;g['quad']+=y['quad'];g['mp']+=y['mp']
                    arr[y['rep']]+=np.array(y['values'],dtype=np.longdouble)
                g['max_normalized_difference']=str(gerr);maxerr=max(maxerr,gerr)
    if maxerr>ROW_TOL:raise AssertionError(f'replayed rows differ from the archive by {maxerr} > {ROW_TOL}')
    arrays={s:{t:{L:np.asarray(x,dtype=float)for L,x in v.items()}for t,v in ar[s].items()}for s in ar}
    two=TWO_LOOP7.read_bytes()
    if hashlib.sha256(two).hexdigest()!=TWO_LOOP7_SHA256:raise AssertionError(f'{TWO_LOOP7}: sha256 differs from {TWO_LOOP7_SHA256}')
    low=json.loads(two)
    if (low.get('dimension'),low.get('order'),len(low.get('B2',[])))!=(3,7,6):raise AssertionError(f'{TWO_LOOP7}: not the d=3 order-7 jet')
    r=assemble.combine(arrays,order=7,bootstrap=0,B2=np.asarray(low['B2'],float));base=json.loads((R/'verification/C7_full_result.json').read_text())
    for k in ('C7_full','sampling_standard_error'):
        if not math.isclose(r[k],base[k],rel_tol=C7_TOL):raise AssertionError(f'replayed {k} {r[k]!r} vs published {base[k]!r}')
    report.update(status='passed',rows_expected=168528,input_identity={'gamma_sha256':gamma,'graph_payloads_verified':len(checked_graphs),'inventory_sha256':digest(ROOT/'inputs/inventory.json'),
                  'inputs_manifest_sha256':digest(ROOT/'inputs/manifest.json')},max_normalized_difference=str(maxerr),bitwise_fraction=report['bitwise_rows']/report['rows'],replayed_C7=r['C7_full'],replayed_SE=r['sampling_standard_error'],
                  published=[base['C7_full'],base['sampling_standard_error']],relative_C7_difference=abs(r['C7_full']-base['C7_full'])/abs(base['C7_full']),
                  tolerances={'row_normalized':str(ROW_TOL),'C7_relative':C7_TOL},wall_seconds=round(time.time()-t0,1))
    if report['rows']!=168528:raise AssertionError(f'{report["rows"]} rows replayed, expected 168528')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--threads',type=int,default=int(os.environ.get('SLURM_CPUS_PER_TASK')or os.cpu_count()or 4));p.add_argument('--exe',type=Path,default=ROOT/'bin/c8d3_gmp');p.add_argument('--output',type=Path)
    a=p.parse_args();x=run(a.threads,a.exe.resolve())
    if a.output:dump(a.output,x)  # optional record; nothing in the package is written otherwise
    print(json.dumps({k:v for k,v in x.items()if k!='groups'},indent=2))
