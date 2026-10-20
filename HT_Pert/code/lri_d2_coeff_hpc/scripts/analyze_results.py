"""Summarize completed measurements only, preserving ranges and all failures."""
from pathlib import Path
import csv,json,statistics,sys,platform,subprocess,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_coeff.storage import source_digest,read_envelope,file_sha
from lri_coeff.basis import plan
import numpy as np,scipy,numba

def writecsv(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def main():
    results=ROOT/'results';records=[]
    for p in sorted((results/'benchmarks').glob('*.json')):
        if 'failed' in p.stem:continue
        d=json.loads(p.read_text())
        if d['source_digest']!=source_digest():raise ValueError('Benchmark source differs from release: '+str(p))
        records.append((p,d))
    rows=[]
    for L in [16,20]:
        for backend,threads in [('reference',1),('optimized',1),('optimized',4)]:
            group=[(p,d) for p,d in records if d['result']['cutoff']==L and d['backend']==backend and d['threads']==threads]
            if len(group)!=3:raise ValueError(('Need all three repetitions',L,backend,threads,len(group)))
            sec=[d['total_seconds'] for p,d in group];rss=[d['peak_rss_KiB']/2**20 for p,d in group]
            rows.append(dict(L=L,backend=backend,threads=threads,repetitions=len(group),median_seconds=statistics.median(sec),min_seconds=min(sec),max_seconds=max(sec),median_peak_rss_GiB=statistics.median(rss),max_peak_rss_GiB=max(rss),median_basis_seconds=statistics.median([d['basis_and_init'] for p,d in group]),warmup_included=False))
    for row in rows:
        base=next(r for r in rows if r['L']==row['L'] and r['backend']=='reference')
        row['speedup_vs_reference_1thread']=base['median_seconds']/row['median_seconds']
        row['rss_reduction_vs_reference']=1-row['median_peak_rss_GiB']/base['median_peak_rss_GiB']
    writecsv(results/'benchmark_summary.csv',rows)
    maxerr={}
    for name in ['C','r','g','energies','vacuum_coefficients']:
        maxerr[name]={'absolute':max(d['errors'][name]['absolute'] for p,d in records),'scaled':max(d['errors'][name]['scaled'] for p,d in records)}
    for v in maxerr.values():assert v['scaled']<5e-11
    # Thread consistency: exact equality in the current deterministic implementation.
    for L in [16,20]:
        group=[d['result'] for p,d in records if d['result']['cutoff']==L and d['backend']=='optimized']
        for k in maxerr:
            for a in group[1:]:assert np.array_equal(a[k],group[0][k]),(L,k)
    plans=[plan(L) for L in [16,18,20,22,24,26,28,30]]
    writecsv(results/'resource_plan.csv',[{k:v for k,v in p.items() if not isinstance(v,(list,dict))} for p in plans])
    pilots=[]
    for p in sorted((results/'scale_pilot').glob('*.json')):
        d=read_envelope(p);r=d['result'];ex=d['execution']
        row=dict(path=str(p.relative_to(ROOT)),scheme=r['scheme'],degree=r['degree'],L=r['cutoff'],states=r['auxiliary_states'],seconds=ex['seconds'],peak_rss_GiB=ex['peak_rss_KiB']/2**20,cache_hit=ex['cache_hit'])
        row.update({f'C{k}':v for k,v in enumerate(r['C'])});pilots.append(row)
    pilot_checks={}
    if len(pilots)==3:
        b={ (r['scheme'],r['degree']):r for r in pilots}
        a=b['consistent',8];c=b['consistent',7];raw=b['raw',8]
        err=max(abs(a[f'C{k}']-c[f'C{k}'])/max(1,abs(a[f'C{k}'])) for k in range(8));assert err<5e-11
        sys.path.insert(0,str(ROOT/'reference/lri_d2_perturbative_C8/code'))
        from analytic_checks import c2,window4
        e2=max(abs(r['C2']-float(c2(22))) for r in pilots);e4=abs(a['C4']-raw['C4']-float(window4(22)))
        assert e2<1e-12 and e4<1e-10
        pilot_checks=dict(degree7_vs_degree8_scaled=err,C2_exact_absolute=e2,window4_exact_absolute=e4,scope='New L22 finite-cutoff pilot; C8 lacks an independent same-cutoff original-engine replay due to its larger memory cost. Lower-order and separate-support checks are independent.')
    if pilots:writecsv(results/'scale_pilot.csv',pilots)
    environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,numba=numba.__version__,platform=platform.platform(),cpu_affinity_count=len(os.sched_getaffinity(0)),cgroup_cpu_quota=Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else None,cgroup_memory_limit=Path('/sys/fs/cgroup/memory.max').read_text().strip() if Path('/sys/fs/cgroup/memory.max').exists() else None,compiler=subprocess.check_output(['c++','--version'],text=True).splitlines()[0],longdouble_explicit_mantissa_bits=int(np.finfo(np.longdouble).nmant))
    (results/'ENVIRONMENT.json').write_text(json.dumps(environment,indent=2)+'\n')
    summary=dict(source_digest=source_digest(),benchmark_processes=len(records),maximum_reference_discrepancy=maxerr,thread_replays_bitwise_equal=True,completed_scale_pilots=len(pilots),pilot_checks=pilot_checks,benchmarks=rows,scope='Fresh local benchmarks and implementation tests; no physical precision, distributed-memory matvec or cluster-validation claim.')
    (results/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
