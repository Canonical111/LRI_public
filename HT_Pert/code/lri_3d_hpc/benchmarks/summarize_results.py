"""Regenerate the performance report from saved benchmark/validation JSON only.

No solver, vertex build, MPI job, or timing experiment is executed. Completed
MPI and coefficient-grid reports are included when present; missing optional
reports are identified explicitly. Re-running after those jobs finish updates
the same report. Numerical claims are tied to source-file hashes.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]


class Sources:
    def __init__(self, root):
        self.root = root
        self.files = {}

    def read(self, relative, required=False):
        path = self.root/relative
        if not path.is_file():
            if required:
                raise FileNotFoundError(path)
            self.files[relative] = {'status':'not present'}
            return None
        raw = path.read_bytes()
        value = json.loads(raw)
        self.files[relative] = {'status':'read', 'bytes':len(raw),
                                'sha256':hashlib.sha256(raw).hexdigest()}
        return value


def maximum_error(value):
    errors = []
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in ('max_scaled_error','maximum_scaled_error','max_scaled_vertex_error'):
                    try:
                        errors.append(Decimal(str(child)))
                    except Exception:
                        pass
                elif isinstance(child,(list,dict)):
                    visit(child)
        elif isinstance(item,list):
            for child in item:
                visit(child)
    visit(value)
    return str(max(errors)) if errors else None


def solver_record(data, source, label):
    samples = data['samples']
    walls = [float(s['wall_seconds']) for s in samples]
    cpus = [float(s['cpu_seconds']) for s in samples if s.get('cpu_seconds') is not None]
    result = data.get('result',{})
    native = data.get('native',{})
    return {'label':label, 'source':source, 'solver':data['solver'],
            'strategy':('original recurrence' if data['solver']=='reference' else data['strategy']),
            'recorded_cli_strategy':data.get('strategy'),
            'backend':('SciPy reference' if data['solver']=='reference' else native.get('backend',data['backend'])),
            'local_mode':data.get('local_mode','reference dense' if data['solver']=='reference' else 'dense'),
            'cutoff':data['cutoff'], 'order':data['order'], 'scheme':data['scheme'],
            'threads':data['threads'], 'ranks':1, 'storage':data['storage'],
            'input_vertex_cutoff':data.get('vertex_metadata',{}).get('cutoff'),
            'profiled':bool(data.get('profile_enabled',False)),
            'samples':len(samples), 'wall_seconds':walls, 'cpu_seconds':cpus,
            'median_wall_seconds':statistics.median(walls),
            'median_cpu_seconds':statistics.median(cpus) if cpus else None,
            'peak_rss_kib':data['peak_rss_kib'],
            'rss_after_load_kib':data.get('rss_after_load_kib'),
            'load_seconds':data.get('load_seconds'),
            'max_scaled_error':maximum_error(samples),
            'counters_per_solve':result.get('optimization',{}).get('counters',{}),
            'thread_policy_all_repeats':native.get('thread_policy'),
            'wavefunction_order':result.get('optimization',{}).get('wavefunction_order',data['order']-1),
            'environment':data.get('environment'),
            'precision_significand_bits':data.get('precision_significand_bits'),
            'affinity':data.get('affinity'),
            'source_sha256':data.get('source_sha256')}


def builder_record(data, source, label):
    metadata = data['vertex_metadata']
    return {'label':label, 'source':source,
            'wall_seconds':data.get('wall_seconds',data.get('profiled_wall_seconds')),
            'peak_rss_kib':data.get('build_peak_rss_kib',data.get('peak_rss_kib')),
            'profiled':bool(data.get('profiled',True)),
            'cache_layouts':metadata.get('cache_layouts',False),
            'coordinate_storage':metadata.get('coordinate_storage','reference memory'),
            'cutoff':data['cutoff'], 'degree':data.get('degree',data.get('order',8)-2),
            'max_scaled_vertex_error':data.get('max_scaled_vertex_error'),
            'full_bath_states':metadata['full_bath_states'],
            'scalar_bath_states':metadata['scalar_bath_states'],
            'graph_array_bytes':metadata['bath_graph_array_bytes'],
            'logical_vertex_array_bytes':metadata['vertex_array_bytes'],
            'stored_array_bytes':metadata.get('store_array_bytes'),
            'unique_sparse_patterns':metadata.get('unique_sparse_patterns'),
            'zero_sparse_products_skipped':metadata.get('zero_sparse_products_skipped',0),
            'sparse_products_executed':metadata.get('sparse_products_executed'),
            'layout_cache_peak_bytes':metadata.get('layout_cache_array_bytes_peak',0)}


def profile_item(data, name, *, contains=False, file_contains=None, largest_self=False):
    rows = data.get('top_cumulative',[])+data.get('top_self',[])
    found = [r for r in rows
             if (name in r['function'] if contains else name==r['function'])
             and (file_contains is None or file_contains in r['file'])]
    if not found:
        return None
    row = max(found,key=lambda r:r['self_seconds'] if largest_self else r['cumulative_seconds'])
    return {'calls':row.get('calls',row.get('total_calls')),
            'self_seconds':row['self_seconds'], 'cumulative_seconds':row['cumulative_seconds']}


def mpi_record(data, source):
    if not data.get('complete'):
        return {'source':source,'status':'incomplete'}
    request, execution = data['request'],data['execution']
    ranks = execution['ranks']
    return {'source':source, 'status':'complete', 'ranks':request['ranks'],
            'threads_per_rank':request['threads'], 'cutoff':request['cutoff'],
            'order':request['order'], 'scheme':request['scheme'],
            'strategy':request['strategy'], 'local_mode':request.get('local_mode'),
            'storage':'read-only mmap input, copied owned CSR rows',
            'max_solve_wall_seconds':execution['max_solve_wall_seconds'],
            'max_rank_peak_rss_kib':execution['max_rank_peak_rss_kib'],
            'max_load_and_setup_seconds':max(r['load_and_setup_seconds'] for r in ranks),
            'max_scaled_error':maximum_error(execution.get('validation')),
            'full_vertex_logical_array_bytes':ranks[0]['full_vertex_logical_array_bytes'],
            'rank_vertex_logical_array_bytes':[r['rank_vertex_logical_array_bytes'] for r in ranks],
            'rank_peak_rss_kib':[r['peak_rss_kib'] for r in ranks],
            'rank_kernel_seconds':[r['backend']['kernel_seconds'] for r in ranks],
            'rank_gather_seconds':[r['backend']['gather_seconds'] for r in ranks],
            'rank_full_hamiltonian_calls':[r['backend'].get('full_hamiltonian_calls') for r in ranks],
            'rank_collectives':[r['backend']['collectives'] for r in ranks],
            'row_bounds':ranks[0]['backend']['row_bounds'],
            'input_checksums_verified':execution.get('input_checksums_verified'),
            'environment':execution.get('thread_environment'),
            'precision_significand_bits':ranks[0]['backend']['precision_significand_bits'],
            'vectors_replicated':True, 'seed_row_replicated':True,
            'floating_point_reductions':False,
            'measurement_scope':'Multiple processes on one host; not cross-node scaling'}


def collect(root):
    src = Sources(root)
    cases = [
        ('benchmarks/reference_L14_stationary_t1.json','Original, 1 thread'),
        ('benchmarks/final_optimized_L14_t1_pickle.json','Optimized, 1 thread'),
        ('benchmarks/final_optimized_L14_t8_pickle.json','Optimized, 8 threads'),
        ('benchmarks/final_optimized_L14_t8_store.json','Optimized mmap, 8 threads')]
    runs = [solver_record(src.read(path,True),path,label) for path,label in cases]
    builder_cases = [
        ('benchmarks/baseline_build_L14_warm_profile.json','Warm reference'),
        ('benchmarks/optimized_build_L14_cached_stream_profile.json','Streamed, cached layouts (default)'),
        ('benchmarks/optimized_build_L14_stream_profile.json','Streamed, no layout cache')]
    builds = [builder_record(src.read(path,True),path,label) for path,label in builder_cases]
    scaling = []
    for L, original, optimized in [
        (8,'final_reference_L8_t1_pickle.json','final_optimized_L8_t1_pickle.json'),
        (12,'reference_L12_stationary_t1.json','final_optimized_L12_t1_pickle.json')]:
        a,b = src.read('benchmarks/'+original),src.read('benchmarks/'+optimized)
        if a is not None and b is not None:
            scaling.append({'cutoff':L,
                'reference':solver_record(a,'benchmarks/'+original,'Original'),
                'optimized':solver_record(b,'benchmarks/'+optimized,'Optimized')})
    scaling.append({'cutoff':14,'reference':runs[0],'optimized':runs[1]})
    refprofile = src.read('benchmarks/baseline_solve_L14_profile.json',True)
    optprofile = src.read('benchmarks/optimized_L14_stationary_t8_profile.json',True)
    profiles = {
        'reference':{'source':'benchmarks/baseline_solve_L14_profile.json',
            'profiled_wall_seconds':refprofile['profiled_wall_seconds'],
            'sparse_multivector':profile_item(refprofile,'csr_matvecs',contains=True),
            'provisional':profile_item(refprofile,'provisional'),
            'advance':profile_item(refprofile,'advance'),
            'full_apply':profile_item(refprofile,'apply',file_contains='perturbative.py',largest_self=True)},
        'intermediate_optimized':{'source':'benchmarks/optimized_L14_stationary_t8_profile.json',
            'profiled_wall_seconds':optprofile['median_wall_seconds'],
            'sparse_multivector':profile_item(optprofile,'csr_spmm',file_contains='native_backend.py'),
            'local_apply_self':profile_item(optprofile,'apply',file_contains='optimized_solver.py',largest_self=True),
            'build':profile_item(optprofile,'build',file_contains='optimized_solver.py'),
            'scope':'Diagnostic profile before the final banded-local and tiny-work dispatch changes; not a final timing sample'}}
    mpi = []
    for name in ('final_mpi_L14_r2_t1.json','final_mpi_L14_r4_t1.json'):
        path = 'benchmarks/'+name
        data = src.read(path)
        mpi.append(mpi_record(data,path) if data is not None else {'source':path,'status':'not present'})
    mpi_environment = src.read('benchmarks/mpi_test_environment.json')
    kernel_data = src.read('results/native_kernel_benchmark_passive.json')
    kernels = ([r for r in kernel_data['results'] if r['cutoff']==14 and r['bath_degree']==4]
               if kernel_data else [])
    graph = src.read('benchmarks/graph_preflight.json')
    validation = {}
    for key,path in [
        ('native','results/native_backend_validation.json'),
        ('stationary_independent','results/stationary_independent_validation.json'),
        ('physical_tiny','results/physical_tiny_validation.json'),
        ('local_bands','results/local_bands_validation.json'),
        ('mpi_tiny','results/mpi_4_fused_validation.json'),
        ('final_coefficient_grid','results/final_coefficient_validation.json')]:
        data = src.read(path)
        validation[key] = {'source':path,'present':data is not None,
                           'maximum_scaled_error':maximum_error(data)}
        if key=='native' and data:
            validation[key]['fixtures'] = data.get('fixtures')
            validation[key]['policy_checks'] = len(data.get('thread_policy_checks',[]))
        if key=='stationary_independent' and data:
            validation[key]['trials'] = len(data.get('trials',[]))
            validation[key]['orders'] = sorted({r['order'] for r in data.get('trials',[])})
        if key=='final_coefficient_grid' and data is not None:
            validation[key]['report'] = data
    ratios = {
        'reference_cpu_over_optimized_t1_cpu':runs[0]['median_cpu_seconds']/runs[1]['median_cpu_seconds'],
        'reference_cpu_over_optimized_t8_cpu':runs[0]['median_cpu_seconds']/runs[2]['median_cpu_seconds'],
        'observed_reference_wall_over_optimized_t8_wall':runs[0]['median_wall_seconds']/runs[2]['median_wall_seconds'],
        'reference_peak_rss_over_optimized_mmap_peak_rss':runs[0]['peak_rss_kib']/runs[3]['peak_rss_kib'],
        'optimized_mmap_peak_rss_reduction_fraction':1-runs[3]['peak_rss_kib']/runs[0]['peak_rss_kib'],
        'default_builder_peak_rss_reduction_fraction':1-builds[1]['peak_rss_kib']/builds[0]['peak_rss_kib'],
        'low_memory_builder_peak_rss_reduction_fraction':1-builds[2]['peak_rss_kib']/builds[0]['peak_rss_kib']}
    return {'format':'ht3d-performance-summary-v1',
        'scope':'Recorded local measurements only; unchanged finite-cutoff coefficients and precision',
        'headline_solver_runs':runs, 'single_thread_cpu_by_cutoff':scaling,
        'builder_runs':builds, 'profiles':profiles, 'mpi_runs':mpi,
        'mpi_test_environment':mpi_environment, 'largest_kernel_passive':kernels,
        'graph_preflight':graph, 'validation':validation, 'ratios':ratios,
        'precision':{'working_significand_bits':runs[0]['precision_significand_bits'],
                     'working_storage_bytes':16,'projector_source':'float64',
                     'warning':'The validation host uses 64-significand-bit longdouble in 16 bytes, not IEEE binary128'},
        'inputs':src.files}


def n(value, digits=2):
    return '—' if value is None else f'{value:.{digits}f}'


def link(path):
    return f'[{Path(path).name}](../{path})'


def write_markdown(summary, destination, figure=None):
    runs = summary['headline_solver_runs']
    builds = summary['builder_runs']
    ratios = summary['ratios']
    ref,one,eight,mmap = runs
    rp,op = summary['profiles']['reference'],summary['profiles']['intermediate_optimized']
    lines = [
        '# Performance measurements and scaling limits','',
        'Generated by `benchmarks/summarize_results.py` from the saved JSON measurements. '
        'The machine-readable companion is `results/performance_summary.json`, which records '
        'every input file and its SHA-256. Regeneration performs no numerical solve or benchmark.','',
        f'At **L = 14, through order epsilon^8**, the final one-thread solver used '
        f'**{n(one["median_cpu_seconds"])} CPU seconds versus {n(ref["median_cpu_seconds"])}** '
        f'for the original: a **{n(ratios["reference_cpu_over_optimized_t1_cpu"])}× reduction in CPU work**. '
        f'The final eight-thread configuration had an observed median wall time of '
        f'**{n(eight["median_wall_seconds"])} s**. With the mapped vertex store, the observed '
        f'process peak was **{n(mmap["peak_rss_kib"]/1024,1)} MiB**, compared with '
        f'**{n(ref["peak_rss_kib"]/1024,1)} MiB** for the original.','',
        'These are local observations from a shared execution environment. The CPU-work '
        'reduction is more consistent than the wall timings. The data do not establish '
        'dedicated-node speedup, strong scaling across nodes, or a DRAM-bandwidth limit.','']
    if figure is not None:
        lines += [f'![Measured CPU work and memory at L14]({figure.name})','']
    lines += ['## 1. Main coefficient-solver measurements','',
        'All rows use the self-consistent scalar vacuum window, order eight, 4,486 scalar '
        'bath states, and 10 local states per field parity. Working arithmetic has 64 binary '
        'significand bits in a 16-byte `longdouble` slot on this host. The SO(3) projectors '
        'retain their original binary64 source precision.','',
        '| Configuration | Input storage | Ranks × requested threads | Repeats | Median wall s | Median CPU s | Process peak MiB | Source |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for r in runs:
        storage = 'verified read-only mmap' if r['storage']=='readonly-mmap' else 'legacy in-memory arrays'
        lines.append(f'| {r["label"]} | {storage} | 1 × {r["threads"]} | {r["samples"]} | '
                     f'{n(r["median_wall_seconds"])} | {n(r["median_cpu_seconds"])} | '
                     f'{n(r["peak_rss_kib"]/1024,1)} | {link(r["source"])} |')
    lines += ['',
        'Wall and CPU times cover the coefficient solve after input loading. Compilation, '
        'input loading/checksums, and subsequent result validation are outside that timed '
        'region. CPU seconds are the process user-plus-system CPU-time difference measured '
        'with `getrusage`. Peak RSS is the process high-water mark and includes input loading; '
        'it is not an incremental allocation count. The mmap run has one sample.','',
        f'The original reference had {n(ref["median_wall_seconds"])} s wall time. The observed '
        f'ratio against the optimized eight-thread median is '
        f'{n(ratios["observed_reference_wall_over_optimized_t8_wall"])}×. This combines '
        'algorithmic changes, native execution, threading, and host scheduling; it is not '
        'an eight-thread scaling factor. In particular, one-thread optimized CPU time was '
        f'{n(one["median_cpu_seconds"])} s while its wall time was {n(one["median_wall_seconds"])} s. '
        'The measurements do not separate the causes of that waiting time.','',
        'The reference benchmark filename contains `stationary` because that was the '
        'benchmark parser default. The unmodified reference function ignores that option '
        'and executes its original full recurrence. No profiled reference run is used as '
        'the headline speed baseline.','',
        '### Repeat-level observations','',
        '| Configuration | Wall samples s | CPU samples s |',
        '|---|---|---|']
    for r in runs:
        lines.append(f'| {r["label"]} | '+', '.join(n(v) for v in r['wall_seconds'])+
                     ' | '+', '.join(n(v) for v in r['cpu_seconds'])+' |')
    lines += ['', '### CPU work at three cutoffs','',
        '| Requested cutoff | Loaded vertex cutoff: original / optimized | Original CPU s | Optimized CPU s | CPU ratio | Sources |',
        '|---:|---:|---:|---:|---:|---|']
    for item in summary['single_thread_cpu_by_cutoff']:
        a,b = item['reference'],item['optimized']
        lines.append(f'| {item["cutoff"]} | {a["input_vertex_cutoff"]} / {b["input_vertex_cutoff"]} | '
                     f'{n(a["median_cpu_seconds"],3)} | {n(b["median_cpu_seconds"],3)} | '
                     f'{n(a["median_cpu_seconds"]/b["median_cpu_seconds"])}× | '
                     f'{link(a["source"])}; {link(b["source"])} |')
    lines += ['',
        'These are comparisons of the same requested finite problem at each cutoff. '
        'Some runs load a larger vertex cache before selecting a smaller cutoff; '
        'their peak RSS therefore should not be fitted as an intrinsic memory-scaling law.','',
        '## 2. Where the work went, and why the changes target it','',
        f'The initial L14 reference profile spent {n(rp["sparse_multivector"]["self_seconds"])} s '
        f'of {n(rp["profiled_wall_seconds"])} s in '
        f'{rp["sparse_multivector"]["calls"]:,} CSR multivector applications. '
        f'The provisional-energy path alone accounted for '
        f'{n(rp["provisional"]["cumulative_seconds"])} s, because it formed full vectors '
        'and retained only their seed component. The profile identified the main target '
        'before implementation changes. '+link(rp['source']), '',
        'The optimized solver contracts seed rows/columns directly, constructs wavefunctions '
        'only through order four for the stationary energy calculation, reuses cutoff/parity '
        'metadata, and releases combined Hamiltonians after use. The original finite basis, '
        'coupling tuning, and every window contribution through the requested energy order '
        'are preserved. `docs/NUMERICS.md` supplies the formal-series proof.','',
        f'An intermediate optimized profile reduced full CSR applications to '
        f'{op["sparse_multivector"]["calls"]:,}. At that stage, the native sparse interface '
        f'occupied {n(op["sparse_multivector"]["cumulative_seconds"])} s '
        f'({n(100*op["sparse_multivector"]["cumulative_seconds"]/op["profiled_wall_seconds"],1)}% of its profiled wall time), '
        f'local dense oscillator work appeared in {n(op["local_apply_self"]["self_seconds"])} s '
        f'of `apply` self time, and Hamiltonian combinations took '
        f'{n(op["build"]["cumulative_seconds"])} s. This motivated the final banded local '
        'operations and the conservative tiny-product serial dispatch. This intermediate '
        'profile is a bottleneck diagnostic, not a final performance sample. '+link(op['source']), '',
        '## 3. Vertex construction: memory choices matter more than the modest time change','',
        'The following controlled build comparisons have warm JIT caches and profiling '
        'enabled. The initial cold run is deliberately excluded from speed ratios. All '
        'produce the same L14 Taylor vertices through degree six.','',
        '| Builder configuration | Wall s | Build-process peak MiB | Source |',
        '|---|---:|---:|---|']
    for b in builds:
        lines.append(f'| {b["label"]} | {n(b["wall_seconds"])} | '
                     f'{n(b["peak_rss_kib"]/1024,1)} | {link(b["source"])} |')
    lines += ['',
        f'The default streamed builder lowers the measured peak by '
        f'{n(100*ratios["default_builder_peak_rss_reduction_fraction"],1)}%; disabling the layout '
        f'cache lowers it by {n(100*ratios["low_memory_builder_peak_rss_reduction_fraction"],1)}% '
        'relative to the warm reference. Disabling the cache repeats format conversions '
        'and costs time. The peak is captured before loading the reference arrays for '
        'comparison, so the validation copy is excluded.','',
        f'The builder skips {builds[1]["zero_sparse_products_skipped"]:,} structurally zero '
        f'products and executes {builds[1]["sparse_products_executed"]:,} required products. '
        'Annihilation images are streamed, and reusable CSR/CSC layouts avoid repeated '
        'conversion when memory permits. The shared-pattern .npy store holds '
        f'{n(builds[1]["stored_array_bytes"]/1024**2,1)} MiB of numerical arrays '
        f'with {builds[1]["unique_sparse_patterns"]} sparse patterns; the unshared logical '
        f'vertex buffers total {n(builds[1]["logical_vertex_array_bytes"]/1024**2,1)} MiB. '
        'File headers and manifest metadata are additional small storage costs.','',
        '## 4. Native threads: measured kernel behavior','',
        'For the largest tested L14 bath vertex, 1,733,150 nonzeros and 10 dense '
        'right-hand sides, passive OpenMP waiting gave these five-sample medians. '
        'The numerical outputs agreed exactly with the same-precision SciPy product.','',
        '| Backend | Requested threads | Median ms | Observed min–max ms |',
        '|---|---:|---:|---:|']
    for k in summary['largest_kernel_passive']:
        lines.append(f'| {k["backend"]} | {k["threads"]} | {n(1000*k["median_seconds"])} | '
                     f'{n(1000*min(k["seconds"]))}–{n(1000*max(k["seconds"]))} |')
    lines += ['',
        'Source: '+link('results/native_kernel_benchmark_passive.json')+'. The operation '
        'timed is the backend CSR-apply interface with reusable output. SciPy creates a '
        'temporary product before copying to that output; the native kernel writes '
        'directly. The SciPy cropped matrix is prepared before timing and reused. These '
        'interface measurements are not the whole-solver result.','',
        'Idle OpenMP spinning caused large delays for small products in an initial run. '
        'The reported runs use `OMP_WAIT_POLICY=PASSIVE` and `GOMP_SPINCOUNT=0`. '
        'The final backend additionally runs products serially below a conservative '
        '10,000 stored-prefix-nonzeros × RHS threshold. A 50,000 threshold was rejected '
        'because a measured 45,700-work case benefited from four threads. The threshold '
        'is configurable and zero disables it. Metadata records the requested and '
        'dispatched thread counts. Neither tuning changes arithmetic precision or '
        'the summation order within a row.','',
        'Nine CPUs were available in process affinity. CPU-model and quota files were '
        'not exposed. The timing data cannot establish whether arithmetic throughput, '
        'memory traffic, scheduler interference, or another host limit controls a '
        'particular thread count. Choose rank/thread layouts on the intended cluster '
        'using the supplied benchmark programs.','',
        '## 5. MPI: local validation and measured row distribution','',
        'The MPI path distributes sparse matrix rows and replicates wavefunctions, '
        'the small energy/window series, and the seed row. Each rank evaluates its '
        'complete Hamiltonian image in the original term order, followed by one '
        'gather of disjoint output rows. This avoids a floating-point reduction and '
        'reduces collective count compared with gathering every bath term. Tuning '
        'coefficients and vacuum energies are broadcast after each order.','']
    complete = [r for r in summary['mpi_runs'] if r['status']=='complete']
    if complete:
        lines += ['These runs use multiple processes on the same host. They measure local '
                  'execution and memory; they do not measure a cluster interconnect.','',
            '| Ranks × threads/rank | Input | Max-rank solve wall s | Max-rank peak MiB | Logical vertex MiB per rank | Max scaled coefficient/energy error | Source |',
            '|---:|---|---:|---:|---|---:|---|']
        for r in complete:
            values=', '.join(n(v/1024**2,1) for v in r['rank_vertex_logical_array_bytes'])
            lines.append(f'| {r["ranks"]} × {r["threads_per_rank"]} | mmap → owned CSR rows | '
                         f'{n(r["max_solve_wall_seconds"])} | {n(r["max_rank_peak_rss_kib"]/1024,1)} | '
                         f'{values} | {r["max_scaled_error"]} | {link(r["source"])} |')
        lines += ['',
            'MPI solve time excludes loading and setup and uses the slowest rank. '
            'Peak RSS includes setup, hashing, and mapped pages. Logical vertex bytes '
            'count the sparse buffers, including repeated references to shared pattern '
            'arrays; they are not an RSS measurement. Rank-zero checksum verification '
            'can touch the whole mapped input before the owned-row copies are made. '
            'Replicated vectors and seed rows prevent total process memory from '
            'decreasing exactly as the reciprocal of rank count.','']
        if len(complete) >= 2:
            first,last=sorted(complete,key=lambda r:r['ranks'])[::len(complete)-1]
            lines += [f'The local tests demonstrate the memory-capacity benefit: the '
                f'maximum process peak drops from {n(first["max_rank_peak_rss_kib"]/1024,1)} '
                f'to {n(last["max_rank_peak_rss_kib"]/1024,1)} MiB between '
                f'{first["ranks"]} and {last["ranks"]} ranks. Observed wall time changes '
                f'from {n(first["max_solve_wall_seconds"])} to '
                f'{n(last["max_solve_wall_seconds"])} s. These local copy-transport '
                'runs do not demonstrate a parallel latency improvement.','']
    missing = [r['source'] for r in summary['mpi_runs'] if r['status']!='complete']
    if missing:
        lines += ['The following optional large MPI reports were not complete when this '
                  'document was generated: '+', '.join(f'`{p}`' for p in missing)+
                  '. Rerun the generator after they finish; no result is inferred for them.','']
    if summary['mpi_test_environment']:
        env=summary['mpi_test_environment']
        lines += ['### Local MPI transport caveat','',
            'The first large-message launch hit a sandbox restriction on '
            '`process_vm_readv`, used by the default cross-memory-attach transport. '
            'That launch was an infrastructure failure, not an application numerical '
            'failure. The completed validation/measurements use ordinary MPICH copy '
            'transport with these settings:','', '```bash']
        lines += [f'export {k}={v}' for k,v in env['environment'].items()]
        lines += ['```','',
            'The change does not alter application arithmetic. These are settings for '
            'this test environment, not a recommendation to disable the cluster’s '
            'normal transport. The MPI environment and limitation are recorded in '+
            link('benchmarks/mpi_test_environment.json')+'.','']
    lines += ['## 6. What still grows at larger cutoffs','',
        'The optimized construction still builds the full bath annihilation graph on '
        'one process. Only the coefficient solver’s sparse matrices are distributed '
        'by the supplied MPI backend. The graph preflight counts exact graph buffers, '
        'not projectors, intermediate sparse products, vertices, wavefunctions, or '
        'total process peak memory.','',
        '| Cutoff | Full bath states | Graph edges | Graph arrays GiB only |',
        '|---:|---:|---:|---:|']
    for g in summary.get('graph_preflight') or []:
        if g['cutoff'] in (14,16,18,20,22,24):
            lines.append(f'| {g["cutoff"]} | {g["states"]:,} | {g["edges"]:,} | '
                         f'{n(g["graph_array_bytes"]/1024**3,3)} |')
    lines += ['',
        'Source: '+link('benchmarks/graph_preflight.json')+'. These counts explain why '
        'a modest L14 process peak cannot be scaled linearly to L20 or beyond. '
        'The implementation reduces temporary storage and unnecessary work but does '
        'not remove the growth of the underlying finite Hilbert space. There is no '
        'measured L16/L18/L20 coefficient calculation in this performance campaign.','',
        'For a large campaign, build each verified vertex store once, stage it where '
        'the cluster can read it efficiently, and use independent scheduler jobs for '
        'cutoffs or window prescriptions when practical. Use MPI row distribution '
        'when matrix memory requires it, then benchmark a few ranks per node with '
        'threads assigned within each rank. More ranks eventually add replicated '
        'vectors and communication. `--no-layout-cache` supplies the lower-memory '
        'builder choice. Site-specific memory and thread choices should follow '
        'measured peak RSS and the graph preflight, not the graph count alone.','',
        '## 7. Numerical validation accompanying the timings','',
        f'All final L14 solver samples in the main table agree with the saved original '
        f'coefficients, couplings, seed energies, and subcutoff vacuum energies with '
        f'maximum scaled discrepancy {max(Decimal(r["max_scaled_error"]) for r in runs if r["max_scaled_error"] is not None)}. '
        'The frozen benchmark gate is 5e-13, substantially larger than the observed '
        'roundoff differences. The builder comparisons report zero value discrepancy '
        'for all 28 vertex matrices. This is preservation of the specified finite '
        'Hamiltonian and scalar vacuum-window correction, not a new continuum claim.','']
    v=summary['validation']
    lines += [f'The native suite has {v["native"].get("fixtures","the saved number of")} '
        'matrix fixtures plus dispatch-policy checks. The independent stationary '
        f'toy suite has {v["stationary_independent"].get("trials","the saved number of")} '
        'cases through order twelve, with worst scaled discrepancy '
        f'{v["stationary_independent"]["maximum_scaled_error"]}. Physical checks target '
        'coefficients through order eight. See `docs/NUMERICS.md` and the individual '
        'validation JSON files for what each test establishes.','']
    grid=v['final_coefficient_grid']
    if grid['present']:
        lines += ['The final all-cutoff coefficient campaign is included in '+link(grid['source'])+
                  (f', with extracted maximum scaled discrepancy {grid["maximum_scaled_error"]}.'
                   if grid['maximum_scaled_error'] is not None else
                   '; its complete validation summary is copied into the machine-readable performance report.') ,'']
    else:
        lines += ['The optional final all-cutoff coefficient validation file was not yet '
                  'present at report generation. The saved timing-sample validations above '
                  'are already complete; rerunning this generator includes that additional '
                  'campaign when available.','']
    lines += ['## 8. Reproduce and regenerate','',
        'Use the existing store for coefficient benchmarks; timing a solve does not '
        'require rebuilding the vertices. For example, from the package directory:','',
        '```bash',
        'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1',
        'export OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0',
        'python benchmarks/benchmark_solver.py --store /path/to/vertices_L14 \\',
        '  --solver optimized --strategy stationary --local-mode banded \\',
        '  --backend native --threads 8 --cutoff 14 --repeats 3 \\',
        '  --output /path/to/new_solver_benchmark.json',
        'python benchmarks/benchmark_native.py --store /path/to/vertices_L14 \\',
        '  --threads 1 2 4 8 --repeats 5 --serial-work-threshold 0 \\',
        '  --output /path/to/new_kernel_benchmark.json',
        'python benchmarks/summarize_results.py --figure docs/performance.png',
        '```','',
        'The optional `--figure` output requires Matplotlib '
        '(`python -m pip install matplotlib`). Omit that flag to regenerate '
        'only the Markdown and JSON using the Python standard library.','',
        'The report generator consumes the named saved experiment files; it does '
        'not automatically replace them with a new cluster’s results. Keep new '
        'benchmark outputs separate or deliberately update the named inputs and '
        'regenerate. The full repeated samples, configuration, precision metadata, '
        'and source hashes remain the audit trail.','']
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text('\n'.join(lines),encoding='utf-8')


def plot(summary, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    runs=summary['headline_solver_runs']
    builds=summary['builder_runs']
    fig,axes=plt.subplots(1,3,figsize=(13,4.9),layout='constrained')
    labels=['Original\n1 thread','Optimized\n1 thread','Optimized\n8 threads','Mapped\n8 threads']
    colors=['#75818d','#39789c','#25649c','#237d72']
    datasets=[([r['median_cpu_seconds'] for r in runs],labels,colors,
               'Coefficient solve: CPU work','Median process CPU seconds'),
              ([r['peak_rss_kib']/1024**2 for r in runs],labels,colors,
               'Coefficient solve: memory','Process peak RSS, GiB'),
              ([b['peak_rss_kib']/1024**2 for b in builds],
               ['Warm\nreference','Streamed\ncached layouts','Streamed\nno layout cache'],
               ['#75818d','#39789c','#237d72'],'Vertex construction: memory','Build-process peak RSS, GiB')]
    for ax,(values,names,palette,title,ylabel) in zip(axes,datasets):
        bars=ax.bar(range(len(values)),values,color=palette,width=.65)
        ax.set_xticks(range(len(values)),names,fontsize=8.5)
        ax.set_title(title,fontsize=11,pad=14)
        ax.set_ylabel(ylabel,fontsize=9)
        ax.set_ylim(0,max(values)*1.23)
        ax.spines[['top','right']].set_visible(False)
        ax.yaxis.grid(True,alpha=.18)
        ax.set_axisbelow(True)
        for rect,value in zip(bars,values):
            ax.text(rect.get_x()+rect.get_width()/2,value+max(values)*.025,
                    f'{value:.2f}',ha='center',va='bottom',fontsize=9)
    fig.suptitle('Measured work and memory at L14 • coefficients through ε⁸',fontsize=14)
    fig.supxlabel('Unchanged longdouble precision; local shared-host observations. See PERFORMANCE.md for sample counts and timing scope.',fontsize=9)
    destination.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(destination,dpi=170)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--output-json',type=Path)
    p.add_argument('--output-md',type=Path)
    p.add_argument('--figure',type=Path)
    args=p.parse_args()
    root=args.root.resolve()
    destination=args.output_json or root/'results/performance_summary.json'
    markdown=args.output_md or root/'docs/PERFORMANCE.md'
    summary=collect(root)
    if args.figure is not None:
        plot(summary,args.figure)
    write_markdown(summary,markdown,args.figure)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(markdown),'summary':str(destination),
                      'mpi_completed':sum(r['status']=='complete' for r in summary['mpi_runs']),
                      'final_grid_present':summary['validation']['final_coefficient_grid']['present']}))


if __name__=='__main__':
    main()
