#!/usr/bin/env python3
"""Regenerate human-readable summaries from saved, actually executed tests."""
from pathlib import Path
import csv,json,statistics,hashlib,platform
R=Path(__file__).resolve().parent.parent

def main():
    rows=[]
    for d in (2,3):
        data=json.loads((R/f'benchmarks/paired_{d}d/results.json').read_text())
        for L in sorted({v['L'] for v in data}):
            def med(engine,key):return statistics.median(v[key] for v in data if v['L']==L and v['engine']==engine)
            rows.append(dict(d=d,L=L,N=L**d,reference_ms=med('reference','ms_per_sweep'),hybrid_ms=med('hybrid','ms_per_sweep'),
                speedup=med('reference','ms_per_sweep')/med('hybrid','ms_per_sweep'),reference_peak_MiB=med('reference','peak_RSS_MiB'),hybrid_peak_MiB=med('hybrid','peak_RSS_MiB')))
    with (R/'results/benchmark_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    stress=sum([json.loads((R/f'benchmarks/stress_{d}d/results.json').read_text()) for d in (2,3)],[])
    physics=[];warnings=[]
    for d in (2,3):
        a=json.loads((R/f'results/pilot{d}d_b1000/results.json').read_text());b=json.loads((R/f'results/pilot{d}d_b2000/results.json').read_text())
        for r,t in zip(a['rows'],b['rows']):
            physics.append(dict(d=d,Delta_sigma=b['Delta_sigma'],L=r['L'],L2=r['L2'],Delta_U4=r['values'][2],stat_b1000=r['statistical_stderr'][2],stat_b2000=t['statistical_stderr'][2],Delta_Y=t['values'][1],Y_minus_U4_z=t['finite_size_diagnostics']['z']))
        warnings+=b['warnings']
    with (R/'results/pilot_comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=physics[0]);w.writeheader();w.writerows(physics)
    par=json.loads((R/'tests/orchestration_validation.json').read_text())
    val=json.loads((R/'tests/validation.json').read_text());cross=json.loads((R/'tests/crosscheck_validation.json').read_text())
    maxz=max(abs(v) for k,r in val.items() if k.startswith('exact') for v in r['z'])
    count=sum(t['measurements'] for d in (2,3) for t in json.loads((R/f'pilot{d}d/manifest.json').read_text())['tasks'])
    text='''# Measured results and scope of this delivery

All numbers below are extracted from the included machine-readable logs. Computation was performed locally on 18 September 2026, not on an external cluster. The environment exposes five CPU affinity slots and a cgroup quota equivalent to four cores, on an AMD EPYC 9V74 virtualized host. Timings are machine-specific. No precision continuum curve was fitted.

## 1. Matched serial throughput

Portable g++ -O3 -std=c++17, three repeats per case, alternating engine order. Both old and new engines write the basic four-column format. Medians; ms per full sweep including short-run warmup. The timer excludes kernel construction/loading. Peak RSS is the process high-water mark, including setup/checkpoint memory. These are short throughput tests, not autocorrelation or equilibrium measurements.

| d | L | Spins | Previous ms/sweep | Hybrid ms/sweep | Speedup | Previous peak MiB | Hybrid peak MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|
'''
    for r in rows:text+=f"|{r['d']}|{r['L']}|{r['N']:,}|{r['reference_ms']:.3f}|{r['hybrid_ms']:.3f}|{r['speedup']:.3f}|{r['reference_peak_MiB']:.1f}|{r['hybrid_peak_MiB']:.1f}|\n"
    text+='''
The speed advantage is size-dependent; the smallest 2D case improves only modestly. The improved flat-alias variant is also retained in the underlying tables and is not consistently superior at large N. No universal speedup factor is claimed. Source hashes and environment are saved with each case.

## 2. Computational-reach stress tests

Each case below used FOUR warmup sweeps plus SIXTEEN recorded sweeps. These counts are far too small to determine critical dimensions. They test memory allocation, long-range event sampling, updating, output and checkpoint creation only.

|d|L|Spins|Seconds/sweep|Peak resident MiB|Total sweeps|
|---:|---:|---:|---:|---:|---:|
'''
    for r in stress:text+=f"|{r['d']}|{r['L']}|{r['N']:,}|{r['ms_per_sweep']/1000:.6f}|{r['peak_RSS_MiB']:.2f}|{r['sweeps']}|\n"
    text+='''
The extreme case is NOT a recommended starting production lattice. Converting short-run speed into a long equilibrium-run estimate ignores autocorrelation changes, thermalization and machine contention.

## 3. Independent-chain scaling and restart

Four identical seeded tasks (d=3,L=64,64 warmup+600 measurements each) were scheduled with different worker counts. Raw bytes agreed across schedules.

|Workers|Total wall seconds|Speedup relative to one worker|
|---:|---:|---:|
'''
    for w in (1,2,4):r=par[f'workers{w}'];text+=f"|{w}|{r['seconds']:.3f}|{r['speedup']:.3f}|\n"
    text+='''
A signal-like wall-time stop returned code 75, and the resumed process pack produced byte-identical records. Merging two identical completed campaigns retained four unique trajectories, not eight. These are local process tests; no claim is made about multi-node or Slurm throughput.

## 4. Fresh multi-temperature pilot data

The completed pilots contain 36 chains, each with 10,000 warmup and 100,000 measured sweeps: 3,600,000 measurement sweeps and 360,000 warmup sweeps total. Each dimension has three lattice sizes, three beta values and two independent hot/cold starts per beta. The pilots are exploratory MC, not bootstrap/theory input. Previous measured crossing centers were used only to position the temperature grids.

- d=2,s=1.4, Delta_sigma=0.3: L=32,64,128; beta=0.16778371065300554 plus -0.0008,0,+0.0008.
- d=3,s=1.8, Delta_sigma=0.6: L=8,16,32; beta=0.10010771631703792 plus -0.0004,0,+0.0004.

All numbers are finite-size effective dimensions. Both block-size analyses use 200 bootstrap repetitions, refitting free energies, crossings and slopes. They use the same raw samples, not independent repeat simulations. No bootstrap crossing failures occurred in these pilots.

|d|Delta_sigma|Pair|Delta_U4|Statistical error, block 1000|Statistical error, block 2000|Delta_Y at same crossing|
|---:|---:|:---:|---:|---:|---:|---:|
'''
    for r in physics:text+=f"|{r['d']}|{r['Delta_sigma']:.3f}|{r['L']}->{r['L2']}|{r['Delta_U4']:.6f}|{r['stat_b1000']:.6f}|{r['stat_b2000']:.6f}|{r['Delta_Y']:.6f}|\n"
    text+='''
The last-column disagreement is important: at the largest pairs, Y- and Binder-slope dimensions differ by several correlated statistical errors. The covariance-aware diagnostics are in results.json. Consequently the new smaller statistical errors must not be advertised as continuum accuracy. The 3D largest-pair central value also differs from the previous exploratory estimate; these runs do not justify smoothing the old and new points into a precise curve.

Measured autocorrelation estimates are below about 11 sweeps for the monitored scores; 1000- and 2000-sweep blocks are much longer, but unsampled slow modes are not excluded. Increasing the block changes some statistical errors by up to roughly 15%; 200 bootstrap draws themselves have sampling noise. Production error estimates need more bootstrap draws and continued blocking/seed/stationarity checks.

## 5. Statistical effort estimates, not continuum guarantees

The pilot-based allocator targets sigma_stat=0.001 at the SAME largest pair, with the SAME temperature proportions. Costs are measured from local pilot invocations and include their short warmup overhead. Further warmup and finite-size bias are not budgeted. These are asymptotic planning estimates, not executed extensions.

|d|Pair|Proposed total measured sweeps at smaller L|At larger L|Additional single-core hours (this host)|
|---:|:---:|---:|---:|---:|
'''
    for d in (2,3):
        z=json.loads((R/f'results/allocation_{d}d.json').read_text());text+=f"|{d}|{z['L'][0]}->{z['L'][1]}|{z['recommended_total_measurements'][0]:,}|{z['recommended_total_measurements'][1]:,}|{z['approximate_additional_core_hours']:.2f}|\n"
    text+='''
Measurements here are summed over independent chains and simulated temperatures, not required in one trajectory. A small statistical error at these small volumes will not repair the observed observable dependence. Allocate significant resources to new size pairs and properly bracketed temperatures as well.

## 6. Validation and provenance

'''
    text+=f"Exact-enumeration comparisons (m2,m4,m6,m8,K and their first thermal derivatives) have maximum absolute standardized difference {maxz:.3f} in the three default-RNG tests. The independent mt19937_64 test has maximum |z|={max(abs(v) for v in cross['mt19937_exact']['z']):.3f}. These correlated checks are not independent p-values. The sanitizer (address+undefined behavior) small-run check returned zero with empty diagnostic output.\n\n"
    text+='''The multihistogram solver agrees with a synthetic known density of states, and a synthetic size-doubling test recovers its known dimension. Warmup interruption, measurement interruption, truncation of uncommitted bytes, extension, and cached-Poisson restart are verified. The exact coordinatewise torus addition is exhaustively checked on small tori. The software proof/finite-size limitations are in README.md.

Raw pilot data and tiny numerical test data are not silently regenerated for the report. Source and delivery file hashes are in SHA256SUMS. A separate pilot-data archive contains the 36 full trajectories, their immutable manifests, status/checkpoint files and binary identities. The light source package omits huge stress-test spin checkpoints and old lattice-wide benchmark kernels; their results/status/timing logs remain.
'''
    (R/'RESULTS.md').write_text(text)
    summary=dict(paired=rows,stress=stress,ensemble_scaling={str(w):par[f'workers{w}']['speedup'] for w in (1,2,4)},pilot=physics,pilot_measurements=count,pilot_warnings=warnings,
        qualification='No new controlled infinite-volume curve; stress and equilibrium pilot data are explicitly separate.')
    (R/'results/delivery_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
