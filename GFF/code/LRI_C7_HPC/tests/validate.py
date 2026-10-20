#!/usr/bin/env python3
"""Small, real-integrand regression suite. No production graph integrations.

The tolerances compare raw Laurent jets. Near-zero pole coefficients require an
absolute scale floor. High-precision point tests are separate from Monte Carlo SE.
"""
from __future__ import annotations
import argparse, decimal, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from workloads import files
from campaign import digest
import toolchain
D=decimal.Decimal
ENV=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')

def call(cmd,log,success=True):
    with log.open('w') as f:p=subprocess.run(list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,env=ENV)
    if (p.returncode==0)!=success:raise AssertionError(f'Unexpected exit {p.returncode}; see {log}')

def read(p):return json.loads(p.read_text(),parse_float=D)
def arr(p):
    d=read(p)
    return {(r['replicate'],r['graph'],r['begin'],r['end']):r['value'] for r in d['rows']}
def difference(a,b):
    with decimal.localcontext() as c:
        c.prec=50
        return float(max((abs(D(x)-D(y))/max(D(1),abs(D(x)),abs(D(y))) for x,y in zip(a,b)),default=D(0)))
def compare_reference(ref,new,tol):
    r=read(ref);n=read(new);mx=0
    for v in n['rows']:
        x=r['graph_batches'][v['replicate']][v['graph']];mx=max(mx,difference(x,v['value']))
    assert mx<tol,(str(ref),str(new),mx,tol)
    return mx

def newcmd(a,w,L,mode,dest,threads=1,N=3,tile=128):
    cmd=[ROOT/'bin/c7_integrate','--mode',mode,'--inputs',a,'--L',L,'--tasks',w['tasks'],'--seed',41927510,'--rate','.8','--output',dest,'--threads',threads,'--tile',tile]
    return cmd+(['--net',w['net']] if mode=='qmc' else ['--degree',N])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,default=ROOT/'build/validation');a=p.parse_args();out=a.output_dir.resolve()
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use an empty validation directory: '+str(out))
    os.umask(0o022);out.mkdir(parents=True,exist_ok=True);inputs=ROOT/'reference/inputs';report={'scope':'actual graph subset replays, endpoint/oracle tests, deterministic scheduling, distribution/checkpoint safety and archived-data reassembly; no full new C7 integration','checks':[]}
    def record(name,**kw):report['checks'].append(dict(name=name,**kw));print('PASS',name,flush=True)
    if not (ROOT/'bin/reference_qmc').exists():call([sys.executable,ROOT/'tools/build_reference.py'],out/'build_reference.log')
    for L in (5,6,7):
        for mode in ('qmc','power'):
            w=files(out/f'{mode}{L}',inputs,L,mode,256 if mode=='qmc' else 2,2,6);base=out/f'ref_{mode}{L}.json';new=out/f'new_{mode}{L}.json'
            if mode=='qmc':cmd=[ROOT/'bin/reference_qmc',inputs,L,256,2,41927510,w['net'],base,'.8','free',w['counts']]
            else:cmd=[ROOT/'bin/reference_power',inputs,L,3,2,2,41927510,base,'power','.8',w['counts']]
            call(cmd,base.with_suffix('.log'));call(newcmd(inputs,w,L,mode,new),new.with_suffix('.log'))
            tol=2e-9 if mode=='power' else 1e-18;mx=compare_reference(base,new,tol) # continuous rows agree to the 21-digit print floor
            extra={}
            if mode=='qmc':
                d=read(new);r=read(base);extra={'quad_calls':sum(v['quad_calls'] for v in d['rows']),'mp_calls':sum(v['mp_calls'] for v in d['rows'])}
                assert extra['quad_calls']==sum(r['quads']) and extra['mp_calls']==sum(r['mps'])
            record(f'original_vs_optimized_{mode}_L{L}',max_normalized_jet_difference=mx,tolerance=tol,**extra)
        for N in (1,5): # The degree-1 integer tables and the generic degree-5 path, both used in production.
            w=files(out/f'power{L}_N{N}',inputs,L,'power',2,2,6);base=out/f'ref_power{L}_N{N}.json';new=out/f'new_power{L}_N{N}.json'
            call([ROOT/'bin/reference_power',inputs,L,N,2,2,41927510,base,'power','.8',w['counts']],base.with_suffix('.log'));call(newcmd(inputs,w,L,'power',new,N=N),new.with_suffix('.log'))
            record(f'original_vs_optimized_power_L{L}_N{N}',max_normalized_jet_difference=compare_reference(base,new,2e-9),tolerance=2e-9)
    w=files(out/'schedule',inputs,7,'qmc',256,2,6);baseline=out/'schedule_q1.json';call(newcmd(inputs,w,7,'qmc',baseline),baseline.with_suffix('.log'))
    for nt in (2,4):
        f=out/f'schedule_q{nt}.json';call(newcmd(inputs,w,7,'qmc',f,threads=nt),f.with_suffix('.log'));assert arr(f)==arr(baseline)
        assert [(r['quad_calls'],r['mp_calls']) for r in read(f)['rows']]==[(r['quad_calls'],r['mp_calls']) for r in read(baseline)['rows']]
    record('qmc_thread_count_invariance',threads=[1,2,4],values_and_fallback_counts='exact decimal identity')
    wp=files(out/'tiles',inputs,7,'power',2,2,4);base=out/'tile128.json';call(newcmd(inputs,wp,7,'power',base),base.with_suffix('.log'))
    for tile,nt in [(1,1),(7,2),(512,4)]:
        f=out/f'tile{tile}.json';call(newcmd(inputs,wp,7,'power',f,threads=nt,tile=tile),f.with_suffix('.log'));assert arr(f)==arr(base)
    record('power_tile_and_thread_invariance',tiles=[1,7,128,512],threads=[1,2,4],values='exact decimal identity')
    call(newcmd(inputs,w,7,'qmc',baseline),out/'refuse_overwrite.log',success=False)
    bad=out/'duplicate.tasks';lines=w['tasks'].read_text().splitlines();bad.write_text(lines[0]+'\n'+lines[1]+'\n'+lines[1]+'\n'+'\n'.join(lines[3:])+'\n');ww={**w,'tasks':bad}
    call(newcmd(inputs,ww,7,'qmc',out/'bad.json'),out/'duplicate.log',success=False)
    record('fail_closed_output_clobber_and_duplicate_task')
    # Actual distributed lifecycle, with the same full Sobol net split across jobs.
    camp=out/'campaign_qmc';cmd=[sys.executable,ROOT/'tools/campaign.py']
    call(cmd+['plan','--out',camp,'--mode','qmc','--L',7,'--counts',w['counts'],'--replicates',2,'--seed',41927510,'--net',w['net'],'--rate','.8','--shards',3,'--threads',2,'--chunk-points',64,'--checkpoint-tasks',7],out/'plan_qmc.log')
    call(cmd+['run',camp,'--index',0],out/'run0.log');call(cmd+['merge',camp],out/'missing_checkpoint.log',success=False)
    before={str(p):digest(p) for p in (camp/'checkpoints').glob('*.json')};call(cmd+['run',camp,'--index',0],out/'resume0.log');assert before=={str(p):digest(p) for p in (camp/'checkpoints').glob('*.json')}
    for i in (1,2):call(cmd+['run',camp,'--index',i],out/f'run{i}.log')
    call(cmd+['merge',camp,'--legacy'],out/'merge_qmc.log');merged=read(camp/'merged/N0.json');mx=0
    for ck in (camp/'checkpoints').glob('*.json'):d=read(ck);assert d['provenance']['payload_sha256'] and d['provenance']['runtime_libraries'] is not None
    call(cmd+['verify',camp],out/'verify_qmc.log');outs={str(p):digest(p) for p in (camp/'merged').glob('N*.json')};(camp/'merged/audit.json').unlink()
    call(cmd+['merge',camp,'--legacy'],out/'remerge_qmc.log');assert outs=={str(p):digest(p) for p in (camp/'merged').glob('N*.json')}
    assert all(oct(p.stat().st_mode&0o777)=='0o644' for p in [camp/'manifest.json',camp/'merged/N0.json',camp/'merged/audit.json',*list((camp/'checkpoints').glob('*.json'))[:3]])
    for r in read(baseline)['rows']:mx=max(mx,difference(r['value'],merged['graph_batches'][r['replicate']][r['graph']]))
    assert mx<2e-12
    call(cmd+['run',camp,'--index',-1],out/'negative_index.log',success=False)
    checkpoint=next((camp/'checkpoints').glob('*.json'));original=checkpoint.read_text();checkpoint.write_text(original.replace('"seed":41927510','"seed":41927511',1));shard=int(checkpoint.name[1:7])
    call(cmd+['run',camp,'--index',shard],out/'wrong_checkpoint.log',success=False);checkpoint.write_text(original)
    record('distributed_qmc_complete_merge_restart_and_corruption_checks',shards=3,chunk_points=64,max_normalized_chunk_difference=mx)
    # Pairwise N1/N3 must preserve tree draws and covariance; chunks are not replicates.
    camp=out/'campaign_power';wp=files(out/'paired',inputs,7,'power',4,2,4)
    call(cmd+['plan','--out',camp,'--mode','power','--L',7,'--counts',wp['counts'],'--replicates',2,'--seed',41927510,'--degrees',1,3,'--rate','.8','--shards',2,'--threads',2,'--chunk-points',2,'--checkpoint-tasks',5],out/'plan_power.log')
    for i in (0,1):call(cmd+['run',camp,'--index',i],out/f'paired{i}.log')
    call(cmd+['merge',camp,'--legacy'],out/'merge_power.log')
    mx=0
    for n in (1,3):
        f=out/f'paired_whole{n}.json';call(newcmd(inputs,wp,7,'power',f,N=n),f.with_suffix('.log'));mg=read(camp/f'merged/N{n}.json')
        for row in read(f)['rows']:mx=max(mx,difference(row['value'],mg['graph_batches'][row['replicate']][row['graph']]))
    assert mx<2e-12
    audit=json.loads((camp/'merged/audit.json').read_text());pstat=audit['statistics']['paired_difference'];assert pstat['independent_replicates']==2
    aa=np.array(read(camp/'merged/N3.json')['batches'],float)-np.array(read(camp/'merged/N1.json')['batches'],float)
    assert np.allclose(np.cov(aa,rowvar=False)/2,pstat['covariance_of_mean'],rtol=1e-10,atol=1e-18)
    record('paired_multilevel_chunk_merge_and_replica_covariance',max_normalized_difference=mx,independent_replicates=2)
    # Compile literal independent point comparison and run endpoint stress cases.
    call(toolchain.compile_cmd([ROOT/'tests/test_points.cpp'],ROOT/'bin/test_points',opt=['-O2']),out/'build_points.log')
    call([ROOT/'bin/test_points',inputs,out/'point_checks.json'],out/'point_checks.log');record('point_oracle_stress',**json.loads((out/'point_checks.json').read_text()))
    # Portable decimal inputs match the original native weights on this platform.
    portable=out/'portable';portable.mkdir()
    for name in ['L7_coord.txt','L7_coord.txt.idx','cgamma_L7.txt','cw_L7_N3.bin']:os.symlink(inputs/name,portable/name)
    call([sys.executable,ROOT/'tools/prepare_inputs.py',portable,'--portable-weights'],out/'prepare_portable.log')
    pp=out/'portable.json';call(newcmd(portable,wp,7,'power',pp),out/'portable.log');whole=out/'paired_whole3.json';assert arr(pp)==arr(whole)
    record('portable_weight_roundtrip',result='exact decimal identity')
    call([sys.executable,ROOT/'tools/assemble.py','--original','--output',out/'reassembled.json'],out/'reassembled.log')
    now=json.loads((out/'reassembled.json').read_text());old=json.loads((ROOT/'reference/verification/C7_assembled_result.json').read_text());assert now['C7_full']==old['C7_full'] and now['sampling_se']==old['sampling_se']
    mx=0;rel=lambda a,b:abs(a-b)/max(1,abs(b))
    for lev in ['coarse','refine3','refine5','refine6']:mx=max([mx]+[rel(now['power_levels'][lev][k][i],old['power_levels'][lev][k][i]) for k in ('mean','sampling_se') for i in range(8)])
    for x,y in zip(now['resolution_sequence'],old['resolution_sequence']):assert x['degree']==y['degree'];mx=max([mx]+[rel(x[k][i],y[k][i]) for k in ('mean','sampling_se') for i in range(8)])
    for x,y in zip(now['lower_order_checks'],old['lower_order_checks']):mx=max(mx,rel(x['value'],y['value']),rel(x['sampling_se'],y['sampling_se']))
    assert [(x['L'],x['column']) for x in now['spurious_pole_checks']]==[(y['L'],y['column']) for y in old['spurious_pole_checks']]
    mx=max([mx]+[rel(x['z_score'],y['z_score']) for x,y in zip(now['spurious_pole_checks'],old['spurious_pole_checks'])]+[rel(a,b) for x,y in zip(now['half_splits'],old['half_splits']) for a,b in zip(x[:8],y[:8])])
    mx=max(mx,rel(now['raw_uncontrolled_C7'],old['raw_uncontrolled_C7']),rel(now['applied_zero_pole_control_C7'],old['applied_zero_pole_control_C7']))
    assert mx<1e-9 and now['allowance']['archived_ceil1000']==old['empirical_allowance']==now['allowance']['headline_2sf'] and abs(now['bootstrap_se']/old['bootstrap_sampling_se'][7]-1)<.05,(mx,now['allowance'])
    record('complete_archived_C7_reassembly',C7=now['C7_full'],sampling_se=now['sampling_se'],exact_match=True,max_relative_diagnostic_difference=mx,allowance=now['allowance']['headline_2sf'])
    report['passed']=True;(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print('ALL CHECKS PASSED:',out/'validation.json')
if __name__=='__main__':main()
