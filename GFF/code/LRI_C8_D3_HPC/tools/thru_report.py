#!/usr/bin/env python3
"""The throughput drill's report (J-SMK-4; PLAN A-PERF-3) from a lane campaign's own records, with A-ORC-13's real-Slurm
numbers and A-ORC-5's peak RSS when the external measurement hook's records are given (docs/HPC.md "Stage 5: the
throughput report").

  thru_report.py RUN [--job J] [--accounting ACC.json] [--sweep SWEEP_RUN]
                 [--reference-p4 P4.json [--reference-shape NxT]
                  | --reference-opt-speed OPT.json --reference-binary NAME [--reference-shape NxT]
                  | --reference-throughput X --reference-note TEXT]
                 [--hook-dir DIR] [--parts perf3,orc13,orc5] [--strict] --output OUT.json
  thru_report.py --rederive REPORT.json [--hook-dir DIR] --output OUT.json

Read-only on RUN; it calls no scheduler (the order is: `tools/accounting.py RUN --json > ACC.json` after the drill's
jobs ended, then this tool, in a short raw job `--role report` or on the Mac against a copy of the files below).
Inputs, exactly:
  (a) RUN/manifest.json (production.verify_base); RUN/cost_model.json, refused (65) unless the campaign is on the
      measured basis with the model at the manifest's pin; RUN/groups/<g>/config.json; the sizes of
      RUN/groups/<g>/tasks.sqlite, sobol.bin and the per-index task and blocks files; inputs/inventory.json (lengths);
  (b) every RUN/groups/<g>/checkpoints/<block>.json, validated against its frozen block (production.validate_checkpoint;
      65 on a mismatch): native.threads, integration_seconds, load_seconds, max_rss_kb, rows[].{seconds,begin,end,graph},
      runtime.fingerprint.{slurm.SLURM_JOB_ID, cpu_model}, runtime.fingerprint_bytes; a block belongs to the job its
      fingerprint names;
  (c) RUN/slurm_logs/lane-<J>.log ("C8 lanes: job J (restart R) on HOST (CPU); N lane(s) of [w,...] CPUs": host, CPU,
      the lane widths; required for perf3, 65) and RUN/lanes/logs/idx<index>.<job>.<restart>.<lane>.<ns>.log (the
      line "fingerprint <key> (<cpu>); fingerprint_bytes <N>" of production.py run, and its committed blocks);
  (d) --accounting ACC.json (tools/accounting.py RUN --json): W = the sum of ElapsedRaw over J's work attempts and the
      node's allocated cores = their alloc_cpus (sacct's AllocTRES cpu; every attempt the same, else 65); an ACC without
      alloc_cpus (an older accounting.py, or no TRES) falls back to the lane log's node CPU count, the sum of the widths
      (every physical core of the job's CPU set), unless the lane log shows a memory-guard cut (then 65) (required for
      perf3, 64);
  (e) --sweep SWEEP_RUN, the J-SWEEP-2 campaign the model was made from (65 unless sha256(SWEEP/manifest.json) equals
      the model's source.manifest_sha256);
  (f) the node-throughput reference: --reference-p4 (a benchmark.py --lane-shapes record, re-expressed in the campaign
      model's units over its workload: benchmark.workload_items on benchmarks/fixtures8, campaign-a keys; the shape
      --reference-shape or best_shape), --reference-opt-speed with --reference-binary (an opt_speed.json, D9 on
      symmetry: tests/validate.l8self_sample x replicates x points at campaign-a keys of the campaign model, over the
      median node_wall_seconds of NAME's runs at its shape; 65 for a smoke record or one whose status is not passed), or
      --reference-throughput X with --reference-note; more than one refuses (64); a reference of another binary than the
      campaign's leaves the throughput INCOMPLETE ("another binary");
  (g) --hook-dir DIR: one JSON per production.py run process of the external hook (schema c8-d3-host-io-hook-1: pid,
      host, job, argv, utc, io{rchar,...}, ru_maxrss_self_kb, ru_maxrss_children_kb; not a package file, user decision
      D7). A record counts when its argv runs `production.py run` on RUN (same path, or a campaign of the same name: a
      copy) with --index; others are foreign and ignored. A record pairs with the idx log of its (index, job); an index
      with more than one attempt in a job is listed as ambiguous and skipped.
Parts (default perf3, plus orc13 and orc5 with --hook-dir; a part without its inputs refuses, 64):
  perf3  A-PERF-3 over J's blocks and rows: busy = sum of row seconds / (allocated node cores x W) >= 0.90 (PLAN: "Σ
         task seconds/(128 × wall)"; lanes that leave cores idle count against it, the widths' sum is reported); OpenMP efficiency per
         block = row seconds / (threads x integration_seconds) >= 0.95 for EVERY block (PLAN: "per-block OpenMP
         efficiency ≥ 0.95"; S4-007), its time-weighted mean (weights threads x integration_seconds), min, P10, median
         and share >= 0.95 reported over all blocks and over L8 blocks; a block below is a SHORTFALL (the OpenMP and the
         A-PERF-3 verdict), listed with its cause analysis (omp_shortfall: wall, tasks per thread, idle core-seconds,
         the longest row's bound on balance; causes split into `established` by the records' numbers and `possible`,
         not measured (per-launch overhead, end-of-block imbalance; S4-R2-002); the job's configured lanes apart from
         their concurrent activity, which is not recorded; what the records cannot show); a block without valid timing
         (threads a positive integer, integration_seconds positive and finite, row seconds finite and >= 0; S4-R2-001)
         is not evaluated and keeps the OpenMP verdict from PASS (INCOMPLETE, or SHORTFALL if one is below); throughput = sum
         of spp[campaign:sector:L:graph] x points x production.mp_factor over J's rows / W >= 0.95 x the reference;
         per-task speed = cost-model seconds / row seconds, |median_L8 / reference - 1| <= 0.10 against the PLAN's
         comparator, the same median over the --sweep campaign's L8 rows under this model;
         without --sweep the ratio to 1.0 ("model definition") is reported for information only and the speed, so
         A-PERF-3, is INCOMPLETE (never PASS); a_perf_3.references records which reference each comparison used; the
         lane log's CPU equals the model's; sizing: L8 row seconds / allocated cores >= 3,600 s and busy core-h >= 140
         on 128 cores (PLAN) or 72 on 64 cores (A1 deviation, user decision 2026-10-05; other core counts INCOMPLETE).
         A shortfall is reported with its cause: native integration, native load and outside-native core-seconds and the
         load share. Verdict PASS iff every rule passes, FAIL if one fails, SHORTFALL if the OpenMP rule falls short
         and none fails, else INCOMPLETE.
  orc13  A-ORC-13 real Slurm: fingerprint_bytes, one value per fingerprint key (idx logs and checkpoints); per paired run
         the own bytes: those of the reading process (own_bytes_process: tasks file, blocks file, the group's
         sobol.bin, the inventory length of each distinct graph per committed block (the staging read) plus
         len(json.dumps(native)) for its native.json read back (an estimate), the checkpoint file of a block already
         present) and native_staged_reads, the reaped native children's reads of their staged copies (F13-d3,
         NATIVE_RULE: Linux adds a reaped child's I/O to the parent's /proc/self/io, so the hook's rchar holds them;
         modelled as the staged bytes of every block the run executed, the hook giving process totals only);
         non_own = rchar - own_bytes and non_own - fingerprint_bytes decide; non_own_raw = rchar - own_bytes_process
         (the Stage-5 model) is reported beside them. Between the smallest and the largest group by tasks.sqlite bytes
         (ratio > 10, else INCOMPLETE "not applicable") the medians agree within max(10%, 2,000,000 bytes), both;
         least-squares fits of rchar (slope near 2: staging plus the native's read) and of non_own (slope near 0) on
         the staged bytes are reported.
  orc5   A-ORC-5: per index (native max_rss_kb x 1024 + the Python ru_maxrss_self_kb x 1024) / est_peak_bytes <= 1.2;
         without the hook the native-only ratio, INCOMPLETE; ru_maxrss_children_kb is reported against max_rss_kb.
Output OUT.json (schema c8-d3-thru-report-2, the -1 of Stage 5 without native_staged_reads; never overwritten, 64):
inputs (paths and sha256s, hook counts), job, sizing, a_perf_3, a_orc_13, a_orc_5, block_detail, runs, notes,
made_utc, made_on; a short summary is printed.
--rederive REPORT.json (no RUN; only --hook-dir and --output): a committed report (-1 or -2) re-evaluated under the
Stage-6 rules on the Mac without the campaign (Stage 6: F13-d3, S4-007, S4-R2-001/002): A-PERF-3's OpenMP rule per
block from its block_detail (timing validity checked per block; the cause analysis without the per-row seconds, which
need the checkpoints) and the A-PERF-3 verdict
recombined; A-ORC-13's byte balance under NATIVE_RULE from its runs (the own bytes per category, groups,
tasks.sqlite sizes and fingerprint_bytes come from the report: they need the campaign's checkpoints, inventory and
logs; with --hook-dir each run's rchar is re-read from its hook record, named by hook_file, with schema, job and index
checked: 65 on a mismatch or a missing record). Everything else is the source's, unchanged; the output (schema
c8-d3-thru-report-2, never overwritten) names its source, what was recomputed and what was taken over (rederived).
Exit codes: 0 written (--strict: 1 when a requested criterion is not PASS), 64 usage, 65 refused inputs, 1 other errors.
"""
from __future__ import annotations
import argparse,json,math,os,re,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,digest,fingerprint_key,host_info,load,utc
import production as prod

SCHEMA='c8-d3-thru-report-2';SCHEMA_V1='c8-d3-thru-report-1';HOOK_SCHEMA='c8-d3-host-io-hook-1'
BUSY_MIN=0.90;OMP_MIN=0.95;THROUGHPUT_MIN=0.95;SPEED_TOL=0.10;L8_WORK_MIN=3600.
MIN_BUSY_CORE_H={128:140.,64:72.}   # PLAN J-SMK-4 (128-core Expanse node); symmetry's 64-core node: A1 deviation (user, 2026-10-05)
AGREE_REL=0.10;AGREE_BYTES=2_000_000;SIZE_RATIO=10.;RSS_MAX=1.2
LANE_RE=re.compile(r'C8 lanes: job (\S+) \(restart (\S+)\) on (\S+) \((.*)\); (\d+) lane\(s\) of \[([0-9, ]*)\] CPUs')
FP_RE=re.compile(r'^fingerprint (\S+) \((.*)\); fingerprint_bytes (\d+)\s*$',re.M)
IDX_RE=re.compile(r'idx(\d+)\.([^.]+)\.([^.]+)\.([^.]+)\.(\d+)\.log')
DONE_RE=re.compile(r'^(committed|verified duplicate \(published concurrently by another run\)) (\S+)/(\S+)\s*$',re.M)
PARTS=('perf3','orc13','orc5')

def verdict(*vs)->str:
    """PASS iff every part passes; FAIL if one fails; SHORTFALL if one falls short with its cause listed (A-PERF-3's
    per-block OpenMP rule) and none fails; else INCOMPLETE (None or 'INCOMPLETE' = an input is missing)."""
    vs=[('PASS'if v else'FAIL')if isinstance(v,bool)else(v or'INCOMPLETE')for v in vs]
    return 'FAIL'if 'FAIL'in vs else 'SHORTFALL'if 'SHORTFALL'in vs else 'INCOMPLETE'if 'INCOMPLETE'in vs else 'PASS'

def pct(xs:list,q:float)->float|None:
    """The q-quantile (0..1) of xs by linear interpolation between order statistics (numpy's default)."""
    if not xs:return None
    s=sorted(xs);k=(len(s)-1)*q;lo=math.floor(k);hi=math.ceil(k)
    return s[lo]if lo==hi else s[lo]+(s[hi]-s[lo])*(k-lo)

def agree(a:float,b:float)->bool:
    """A-ORC-13's tolerance: |a - b| <= max(10% of the larger, 2 MB = 2,000,000 bytes)."""
    return abs(a-b)<=max(AGREE_REL*max(abs(a),abs(b)),AGREE_BYTES)

def _jnum(x):
    """A timing value as recorded: a finite JSON number unchanged, else None (never evaluated; S4-R2-001)."""
    return x if isinstance(x,(int,float))and not isinstance(x,bool)and math.isfinite(x)else None

def timing_problem(b:dict)->str|None:
    """Why a block's OpenMP efficiency cannot be evaluated, or None (S4-R2-001): threads must be a positive integer,
    integration_seconds a positive finite number and row_seconds a finite number >= 0."""
    th,ig,rs=b.get('threads'),b.get('integration_seconds'),b.get('row_seconds')
    if not(isinstance(th,int)and not isinstance(th,bool)and th>0):return f'threads {th!r} is not a positive integer'
    if _jnum(ig)is None or ig<=0:return f'integration_seconds {ig!r} is not a positive finite number'
    if _jnum(rs)is None or rs<0:return f'row_seconds {rs!r} is not a finite number >= 0'
    return None

def efficiency(b:dict)->float|None:
    """row seconds / (threads x integration_seconds) of a block with valid timing (timing_problem), else None."""
    return None if timing_problem(b)else b['row_seconds']/(b['threads']*b['integration_seconds'])

def omp_stats(blocks:list)->dict:
    """Per-block OpenMP efficiency (row seconds / (threads x integration_seconds)) of the blocks with valid timing and its
    time-weighted mean (weights threads x integration_seconds, i.e. the ratio of the sums), with min, P10, median, the
    share >= 0.95, the blocks below; the untimed blocks (timing_problem) are counted and listed, never evaluated."""
    eff=[(efficiency(b),b)for b in blocks];vals=[e for e,_ in eff if e is not None];tb=[b for e,b in eff if e is not None]
    w=sum(b['threads']*b['integration_seconds']for b in tb)
    return {'blocks':len(blocks),'time_weighted_mean':(sum(b['row_seconds']for b in tb)/w if w>0 else None),'min':min(vals)if vals else None,
            'p10':pct(vals,.1),'median':pct(vals,.5),'share_ge_0_95':(sum(e>=OMP_MIN for e in vals)/len(vals)if vals else None),'untimed':len(blocks)-len(vals),
            'untimed_blocks':[{**{k:b[k]for k in ('index','block','group')if k in b},'why':timing_problem(b)}for e,b in eff if e is None],
            'below_0_95':[{**{k:b[k]for k in ('index','block','group')if k in b},'tasks':b['tasks'],'threads':b['threads'],'efficiency':e,'wall_seconds':b['integration_seconds']}
                          for e,b in eff if e is not None and e<OMP_MIN]}

SHORT_WALL=1.0;FEW_TASKS=4   # the cause analysis's thresholds: a block wall below 1 s; at most 4 tasks per thread
def omp_part(blocks:list,ctx:dict)->dict:
    """A-PERF-3's OpenMP rule as the PLAN states it ("per-block OpenMP efficiency >= 0.95"; S4-007): EVERY block at or
    above OMP_MIN; the time-weighted mean is reported, never the gate. A block below is a SHORTFALL, listed with its
    cause analysis (omp_shortfall). A block without valid timing (S4-R2-001: timing_problem) is never evaluated and
    keeps the verdict from PASS: INCOMPLETE, or SHORTFALL when a timed block is below; no timed block: INCOMPLETE."""
    o_all=omp_stats(blocks);o_l8=omp_stats([b for b in blocks if b['L']==8])
    out={'all':o_all,'L8':o_l8,'rule':f'every block >= {OMP_MIN:g} (PLAN A-PERF-3: per-block OpenMP efficiency >= 0.95); the time-weighted mean is reported, '
                                     'not gated; a block below is a SHORTFALL with its cause; a block without valid timing is not evaluated and the verdict '
                                     'is then never PASS (INCOMPLETE, or SHORTFALL if a timed block is below)'}
    if o_all['below_0_95']:out['verdict']='SHORTFALL';out['shortfall']=omp_shortfall(blocks,ctx)
    elif o_all['min']is None or o_all['untimed']:out['verdict']='INCOMPLETE';out['why']=f'{o_all["untimed"]} of {o_all["blocks"]} blocks have no valid timing (untimed_blocks)'
    else:out['verdict']='PASS'
    return out

def omp_shortfall(blocks:list,ctx:dict)->dict:
    """The cause analysis of the blocks below OMP_MIN, from the records only (S4-R2-002): each block's wall
    (integration_seconds), tasks per thread, idle core-seconds (threads x wall - row seconds), its wall's rank among the
    job's timed blocks, its graphs, points and host and, when the per-row seconds are known (the checkpoints: report
    mode), the longest row's bound on balance (row seconds / (threads x max(row seconds / threads, longest row))) and the
    residual (efficiency / that bound). Each block's causes are split: `established` (what the records' numbers imply:
    fewer tasks than threads, the longest row's bound, one thread = no imbalance between threads) and `possible` (per-
    launch overhead and end-of-block imbalance, which no record measures). The job's configured lanes are described apart
    from their concurrent activity, which is not recorded (a single lane: none of the job's). A summary, what the
    records can and cannot show and a conclusion follow."""
    timed=[b for b in blocks if efficiency(b)is not None];bad=sorted((b for b in timed if efficiency(b)<OMP_MIN),key=efficiency);walls=sorted(b['integration_seconds']for b in timed)
    core=math.fsum(b['threads']*b['integration_seconds']for b in timed);per=[]
    for b in bad:
        e=efficiency(b);w=b['integration_seconds'];th=b['threads'];rs=b['row_seconds']
        x={**{k:b[k]for k in ('index','group','block','L','graphs','points')if b.get(k)is not None},'tasks':b['tasks'],'threads':th,'efficiency':e,
           'wall_seconds':w,'row_seconds':rs,'load_seconds':b.get('load_seconds'),'idle_core_seconds':th*w-rs,'tasks_per_thread':b['tasks']/th,
           'wall_rank':f'{walls.index(w)+1} of {len(walls)} (1 = the shortest)','host':b.get('host')or ctx.get('host')}
        if _jnum(b.get('max_row_seconds'))is not None and max(rs/th,b['max_row_seconds'])>0:
            cp=max(rs/th,b['max_row_seconds']);x.update(max_row_seconds=b['max_row_seconds'],balance_bound=rs/(th*cp),residual=e*th*cp/rs if rs>0 else None)
        est=[];pos=[]
        if th==1:est.append('one thread: no imbalance between threads is possible; the idle core-seconds are time of the launch outside its rows')
        elif b['tasks']<th:est.append(f'fewer tasks than threads: {b["tasks"]} on {th} threads, so {th-b["tasks"]} thread(s) had no task (efficiency at most {b["tasks"]/th:.3f})')
        if x.get('balance_bound')is not None and x['balance_bound']<OMP_MIN:est.append(f'tail: the longest row ({x["max_row_seconds"]:.3g} s) alone bounds the efficiency at {x["balance_bound"]:.3f}')
        if w<SHORT_WALL:pos.append(f'per-launch overhead (not measured): the wall {w:.3g} s is below {SHORT_WALL:g} s, so fixed costs of the launch\'s parallel region '
                                   '(thread team, scheduling, the final barrier), which the records do not time, could be a visible share')
        if th>1 and b['tasks']<=FEW_TASKS*th:pos.append(f'end-of-block imbalance (not measured): {b["tasks"]} tasks on {th} threads ({b["tasks"]/th:.3g} per thread), so '
                                                        'unequal task lengths could leave threads idle at the end; there are no per-thread times')
        x['established']=est;x['possible']=pos or['none of the analysis\'s candidates (a long block with many tasks per thread): not explained by these records']
        per.append(x)
    long_=[efficiency(b)for b in timed if b['integration_seconds']>=SHORT_WALL];short=[b for b in timed if b['integration_seconds']<SHORT_WALL]
    summ={'blocks_below':len(bad),'timed_blocks':len(timed),'untimed_blocks':len(blocks)-len(timed),'core_seconds_below':math.fsum(b['threads']*b['integration_seconds']for b in bad),
          'share_of_integration_core_seconds':(math.fsum(b['threads']*b['integration_seconds']for b in bad)/core if core>0 else None),
          'idle_core_seconds_below':math.fsum(x['idle_core_seconds']for x in per),'wall_median_all_blocks':pct(walls,.5),'wall_max_below':max(x['wall_seconds']for x in per),
          'short_blocks':len(short),'short_blocks_below':sum(1 for x in per if x['wall_seconds']<SHORT_WALL),
          'min_efficiency_short_blocks':min((efficiency(b)for b in short),default=None),'min_efficiency_blocks_ge_1s':min(long_,default=None),
          'all_below_short_and_few_tasks':all(x['wall_seconds']<SHORT_WALL and x['tasks']<=FEW_TASKS*x['threads']for x in per),
          'single_thread_blocks_below':sum(1 for x in per if x['threads']==1)}
    widths=ctx.get('widths');nl=len(widths)if isinstance(widths,list)else None
    node={'host':ctx.get('host'),'cpu':ctx.get('cpu'),'hosts_of_blocks_below':sorted({str(x['host'])for x in per}),'lanes':nl,'lane_widths':widths,
          'lane_cores':ctx.get('lane_cores'),'allocated_cores':ctx.get('cores'),'allocated_cores_source':ctx.get('cores_source')}
    cov=('covering all of its allocated cores'if ctx.get('cores')and ctx.get('cores')==ctx.get('lane_cores')else
         'not covering all of its allocated cores, or the allocation is unknown')
    co={'configured_capacity':(f'the job was configured with {nl} lane(s) of {widths} CPUs, {cov}; this is capacity, not activity'if nl else
                               'the job\'s lane configuration is unknown (no lane log in this record)'),
        'observed_concurrency':('a single lane: no other lane of this job ran beside these blocks'if nl==1 else
                                f'not recorded: the records have no per-block start and end times, and lanes start and finish independently, so whether any '
                                f'of the job\'s other {nl-1} lane(s) ran at the same moment as these blocks is unknown'if nl else'unknown'),
        'other_jobs':'another job on the node, if any, is not visible in these records'}
    rows=all(x.get('balance_bound')is not None and 'graphs'in x for x in per)
    can=['each block\'s wall, row seconds, threads and tasks, hence its efficiency, tasks per thread and idle core-seconds',
         'the wall\'s rank among the job\'s blocks and the efficiency of the long blocks','the node, its CPU and the job\'s configured lanes (capacity, not activity)',
         'each block\'s graphs and points and the longest row\'s bound on balance'+(''if rows else' (not here: they are in the checkpoints, not in this record)')]
    cannot=['per-thread start and stop times, so the OpenMP runtime\'s own costs (thread team, scheduling, barrier) cannot be measured or separated from the imbalance between tasks',
            'per-block start and end times, so the concurrent activity of the job\'s other lanes, and any memory-bandwidth or cache interference, cannot be observed or attributed',
            'operating-system noise, interrupts and the cores\' clock frequency during the block']
    effs=', '.join(format(x['efficiency'],'.3f')for x in per[:12])+(', ...'if len(per)>12 else'')
    multi=any(x['threads']>1 for x in per);tails=[x for x in per if any(s.startswith('tail')for s in x['established'])]
    expl='per-launch overhead'+(' and end-of-block imbalance between threads'if multi else'')
    lanes_txt=('The job had a single lane, so no other lane of it ran beside them'if nl==1 else
               'Interference from the job\'s other lanes can be neither confirmed nor excluded: their concurrent activity is not recorded'if nl else
               'The job\'s lanes are unknown')
    concl=(f'{len(bad)} of {len(timed)} timed blocks are below {OMP_MIN:g} (efficiencies {effs}); '
           f'they hold {summ["share_of_integration_core_seconds"]:.2e} of the integration core-seconds.'+
           (f' {summ["untimed_blocks"]} block(s) have no valid timing and are not evaluated.'if summ['untimed_blocks']else'')+' '+
           (f'Every one is a short block (wall at most {summ["wall_max_below"]:.3g} s, the job\'s median block wall {summ["wall_median_all_blocks"]:.3g} s) with at most '
            f'{FEW_TASKS} tasks per thread, and every block of {SHORT_WALL:g} s or more is at or above {math.floor(summ["min_efficiency_blocks_ge_1s"]*1e4)/1e4:.4f}. '
            f'POSSIBLE explanations, not measured: {expl}; no record times '+('them, so they cannot be confirmed or told apart'if multi else'it, so it cannot be confirmed')+
            (f'; established for {len(tails)} of them: the longest row alone bounds the efficiency below {OMP_MIN:g}'if tails else'')+'. '
            if summ['all_below_short_and_few_tasks']and summ['min_efficiency_blocks_ge_1s']is not None and summ['min_efficiency_blocks_ge_1s']>=OMP_MIN else
            'Not every block below is a short few-task block, or a long block is below too: see each block\'s established and possible causes. ')+
           lanes_txt+'; another job on the node, if any, is not visible.')
    return {'rule':f'per block: efficiency >= {OMP_MIN:g}; thresholds of the analysis: wall < {SHORT_WALL:g} s (short block), tasks <= {FEW_TASKS} x threads (few tasks); '
                   'causes are `established` only where the records\' numbers imply them, otherwise `possible` (not measured)',
            'blocks':per,'summary':summ,'node':node,'co_tenancy':co,'records_show':can,'records_cannot_show':cannot,'conclusion':concl}

def ref_opt_speed(rec:dict,name:str,shape:str|None,spp:dict,inv:dict,mpf:float,sample_fn)->dict:
    """--reference-opt-speed: the record's workload (sample_fn(inv, sizes) x replicates x points) in the campaign model's
    campaign-a seconds x mp factor, over the median node_wall_seconds of NAME's runs at its shape."""
    if rec.get('schema')!='c8-d3-stage4b-opt-speed-1':raise Refuse(65,f'--reference-opt-speed: schema {rec.get("schema")!r} is not c8-d3-stage4b-opt-speed-1')
    if rec.get('smoke')or rec.get('status')!='passed':raise Refuse(65,f'--reference-opt-speed: a smoke record or one that did not pass (smoke {rec.get("smoke")}, status {rec.get("status")!r}) is never a reference')
    if name not in (rec.get('binaries')or{}):raise Refuse(65,f'--reference-binary {name!r} is not a binary of the record ({", ".join(rec.get("binaries")or{})})')
    shape=shape or rec['shapes'][name];walls=[r['node_wall_seconds']for r in rec.get('runs',[])if r['binary']==name and r['shape']==shape]
    if not walls:raise Refuse(65,f'--reference-opt-speed: no run of {name} at shape {shape}')
    w=rec['workload'];sample=sample_fn(inv,w['sizes']);keys=[f'a:{s}:8:{g}'for s,ids in sorted(sample.items())for g in ids]
    miss=[k for k in keys if k not in spp]
    if miss:raise Refuse(65,f'--reference-opt-speed: the campaign model has no entry for {len(miss)} sample kernels, e.g. {miss[:3]}')
    cms=sum(float(spp[k])for k in keys)*w['replicates']*w['points']*mpf;wall=statistics.median(walls)
    return {'kind':'opt_speed','binary':name,'shape':shape,'runs':len(walls),'median_node_wall_seconds':wall,'workload_cost_model_seconds':cms,
            'throughput_per_node_second':cms/wall,'binary_sha256':rec['binaries'][name]['sha256'],'mp_check':w.get('mp_check')}

def ref_p4(rec:dict,shape:str|None,items:list,parts:dict,spp:dict,mpf:float)->dict:
    """--reference-p4: the shape's throughput (fixture cost-model seconds per node-second) re-expressed in the campaign
    model's campaign-a seconds x mp factor over the same workload."""
    if rec.get('schema')!='c8-d3-prof-p4-1':raise Refuse(65,f'--reference-p4: schema {rec.get("schema")!r} is not c8-d3-prof-p4-1')
    shape=shape or rec.get('best_shape');s=next((x for x in rec.get('shapes',[])if x.get('shape')==shape and not x.get('errors')),None)
    if s is None:raise Refuse(65,f'--reference-p4: no error-free shape {shape!r} in the record')
    fix=math.fsum(it[0]for it in items);want=float(rec['workload']['cost_model_seconds'])
    if abs(fix-want)>1e-9*max(1.,want):raise Refuse(65,f'--reference-p4: the fixture workload has {fix} cost-model seconds, the record {want}: another fixture')
    keys=[f'a:{parts[it[1][0]]["sector"]}:{parts[it[1][0]]["L"]}:{it[2][2]}'for it in items];miss=sorted({k for k in keys if k not in spp})
    if miss:raise Refuse(65,f'--reference-p4: the campaign model has no entry for {len(miss)} workload graphs, e.g. {miss[:3]}')
    camp=math.fsum(float(spp[k])*(it[2][4]-it[2][3])for k,it in zip(keys,items))*mpf
    thr=float(s['throughput_cost_model_s_per_node_s'])
    exe=((rec.get('identity')or{}).get('executables')or{}).get('worker')or{}
    return {'kind':'p4','shape':shape,'fixture_throughput_per_node_second':thr,'fixture_cost_model_seconds':fix,'workload_cost_model_seconds':camp,
            'throughput_per_node_second':thr*camp/fix,'binary_sha256':exe.get('sha256'),'mp_check':(rec.get('settings')or{}).get('mp_check')}

def compare_groups(runs:list,sizes:dict)->dict:
    """A-ORC-13: the smallest and the largest group (tasks.sqlite bytes) with a paired run; medians of non_own and of
    non_own without fingerprint_bytes agree (agree()); a size ratio of 10 or less is "not applicable"."""
    groups=sorted({r['group']for r in runs},key=lambda g:(sizes[g],g))
    if len(groups)<2:return {'verdict':'INCOMPLETE','why':'not applicable: fewer than two groups with a paired run','groups':groups}
    small,large=groups[0],groups[-1];ratio=sizes[large]/sizes[small]if sizes[small]else math.inf
    out={'smallest':{'group':small,'tasks_sqlite_bytes':sizes[small]},'largest':{'group':large,'tasks_sqlite_bytes':sizes[large]},'size_ratio':ratio}
    raw=all('non_own_raw'in r for r in runs)
    for g,k in ((small,'smallest'),(large,'largest')):
        rs=[r for r in runs if r['group']==g];out[k].update(runs=len(rs),median_non_own=statistics.median(r['non_own']for r in rs),
                                                             median_non_own_wo_fp=statistics.median(r['non_own_wo_fp']for r in rs))
        if raw:out[k].update(median_non_own_raw=statistics.median(r['non_own_raw']for r in rs),median_non_own_raw_wo_fp=statistics.median(r['non_own_raw_wo_fp']for r in rs))
    a,b=out['smallest'],out['largest']
    out['agree_non_own']=agree(a['median_non_own'],b['median_non_own']);out['agree_non_own_wo_fp']=agree(a['median_non_own_wo_fp'],b['median_non_own_wo_fp'])
    if raw:out['raw_model']={'agree_non_own_raw':agree(a['median_non_own_raw'],b['median_non_own_raw']),'agree_non_own_raw_wo_fp':agree(a['median_non_own_raw_wo_fp'],b['median_non_own_raw_wo_fp']),
                             'note':'non_own_raw = rchar - own_bytes_process, the Stage-5 model without the native child\'s reads (F13-d3): reported, never the verdict'}
    out['rule']=f'|a - b| <= max({AGREE_REL:g} x max(a, b), {AGREE_BYTES} bytes), both; size ratio > {SIZE_RATIO:g}'
    if ratio<=SIZE_RATIO:out.update(verdict='INCOMPLETE',why=f'not applicable: the tasks.sqlite size ratio {ratio:.2f} is not above {SIZE_RATIO:g}')
    else:out['verdict']=verdict(out['agree_non_own']and out['agree_non_own_wo_fp'])
    return out

def lsq(xs:list,ys:list)->dict:
    n=len(xs)
    if n<2 or len(set(xs))<2:return {'points':n,'slope':None,'intercept':None}
    mx=sum(xs)/n;my=sum(ys)/n;sxx=sum((x-mx)**2 for x in xs);sxy=sum((x-mx)*(y-my)for x,y in zip(xs,ys))
    return {'points':n,'slope':sxy/sxx,'intercept':my-sxy/sxx*mx}

# F13-d3: the hook's rchar is /proc/self/io of `production.py run` at its exit, which includes every reaped child's reads.
NATIVE_RULE=('native_staged_reads = the staged bytes (the inventory lengths of the distinct graphs) of every block the run executed '
             '(committed or verified duplicate): each native launch reads the staged copy of its block\'s graph members once, and '
             'Linux adds a reaped child\'s I/O to its parent\'s /proc/self/io, so the hook\'s rchar of `production.py run` holds '
             'those reads (own work; F13-d3, J-SMK-4: rchar = 2.00 x staged + 32.8 MB). The hook gives process totals only, so '
             'the reads are modelled, not measured; the native\'s other per-launch reads (its copies of the net and gamma, the '
             'block\'s tasks.txt, library headers) are not modelled and stay in non_own')
OWN_MODEL=('own_bytes = own_bytes_process + native_staged_reads; own_bytes_process = tasks file + blocks file + the group\'s '
           'sobol.bin + per committed block the inventory lengths of its distinct graphs (the staging read) and '
           'len(json.dumps(native)) (estimate) + the checkpoint file of each block already present; non_own = rchar - '
           'own_bytes decides, non_own_raw = rchar - own_bytes_process (the Stage-5 model) is reported')

def run_bytes(rchar:int,own:dict,native:int,fpb:int)->dict:
    """A paired run's byte balance (A-ORC-13, OWN_MODEL): the process's own bytes (the sum of own), the modelled native
    reads (NATIVE_RULE), their sum, and non_own (the verdict's) and non_own_raw (the Stage-5 model), each also without
    fingerprint_bytes."""
    p=sum(own.values());t=p+native
    return {'own_bytes_process':p,'native_staged_reads':native,'own_bytes':t,'non_own':rchar-t,'non_own_wo_fp':rchar-t-fpb,
            'non_own_raw':rchar-p,'non_own_raw_wo_fp':rchar-p-fpb}

def orc13_part(fp:dict,runs:list,sizes:dict,amb:list)->dict:
    """A-ORC-13's block from the fingerprint part and the paired runs (report and --rederive-orc13)."""
    cmpg=compare_groups(runs,sizes)if runs else{'verdict':'INCOMPLETE','why':'no paired run'};st=[r['own']['staged_bytes']for r in runs]
    o={'fingerprint_bytes':fp,'non_own':cmpg,'paired_runs':len(runs),'ambiguous':amb,
       'fit_rchar_on_staged_bytes':{**lsq(st,[r['rchar']for r in runs]),'note':'slope near 2: the run reads each staged graph member once (staging) and its reaped native child reads the staged copy once more, both own work (F13-d3)'},
       'fit_non_own_on_staged_bytes':{**lsq(st,[r['non_own']for r in runs]),'note':'slope near 0: the own-bytes model holds every read that grows with the staged bytes'},
       'own_bytes_model':OWN_MODEL,'native_child_reads':NATIVE_RULE}
    o['verdict']=verdict(fp['verdict'],cmpg['verdict']);return o

class Bad(Exception):pass   # usage (64)

def alloc_cores(att:list,lane:dict,lane_text:str)->tuple[int,str]:
    """The node's allocated cores of J (busy's denominator, PLAN A-PERF-3 "Σ task seconds/(128 × wall)"): the
    accounting's alloc_cpus (sacct AllocTRES cpu) of J's work attempts, one value; without it the lane log's node CPU
    count (the sum of the lane widths: every physical core of the job's CPU set) unless a memory-guard cut left some idle."""
    vals={x.get('alloc_cpus')for x in att}
    if None not in vals:
        if len(vals)!=1 or not all(isinstance(v,int)and v>0 for v in vals):raise Refuse(65,f'the accounting gives job {lane["job"]}\'s work attempts allocated CPUs {sorted(vals)}: not one node allocation')
        return vals.pop(),'accounting alloc_cpus (sacct AllocTRES cpu)'
    if vals-{None}:raise Refuse(65,f'the accounting gives alloc_cpus for some of job {lane["job"]}\'s work attempts only: {sorted(map(str,vals))}')
    if 'C8 lanes: memory guard:'in lane_text:raise Refuse(65,'the allocated cores are unknown: the accounting has no alloc_cpus (an older tools/accounting.py?) '
                                                           'and the lane log shows a memory-guard cut (its lanes do not cover the node); rerun accounting.py RUN --json')
    return sum(lane['widths']),'lane log (the sum of the lane widths: the job\'s physical cores; the accounting has no alloc_cpus)'

def sizing_of(l8sec:float,rsec:float,cores:int)->dict:
    """J-SMK-4's size (PLAN A-PERF-3: >= 1 h of L8 work, >= 140 busy core-h on a 128-core node; 64 cores: >= 72, A1)."""
    l8work=l8sec/cores;bch=rsec/3600.;need=MIN_BUSY_CORE_H.get(cores)
    out={'L8_row_seconds':l8sec,'L8_work_seconds_per_core':l8work,'L8_work_rule':f'>= {L8_WORK_MIN:g} s','L8_work_verdict':verdict(l8work>=L8_WORK_MIN),
         'busy_core_hours':bch,'busy_core_hours_rule':(f'>= {need:g} on {cores} cores'if need else f'no rule for {cores} cores (128: 140, PLAN; 64: 72, A1)'),
         'busy_core_hours_verdict':verdict(bch>=need)if need else'INCOMPLETE'}
    out['verdict']=verdict(out['L8_work_verdict'],out['busy_core_hours_verdict']);return out

def parse_lane_log(p:Path,job:str)->list:
    if not p.is_file():raise Refuse(65,f'{p} is missing: the lane worker\'s log (host, CPU, lane widths) is required for perf3')
    out=[]
    for m in LANE_RE.finditer(p.read_text(errors='replace')):
        if m.group(1)==job:out.append({'job':m.group(1),'restart':m.group(2),'host':m.group(3),'cpu':m.group(4),'lanes':int(m.group(5)),
                                       'widths':[int(x)for x in m.group(6).replace(' ','').split(',')if x]})
    if not out:raise Refuse(65,f'{p} has no "C8 lanes: job {job} ..." line')
    return out

def read_hooks(d:Path,run:Path)->tuple[list,dict]:
    keep=[];count={'files':0,'kept':0,'foreign':0,'unreadable':0}
    rp=os.path.realpath(run)
    for f in sorted(Path(d).glob('*.json')):
        count['files']+=1
        try:r=json.loads(f.read_text())
        except (OSError,ValueError):count['unreadable']+=1;count['foreign']+=1;continue
        a=r.get('argv')if isinstance(r,dict)else None
        ok=isinstance(r,dict)and r.get('schema')==HOOK_SCHEMA and isinstance(a,list)and len(a)>=3 and str(a[0]).endswith('production.py')and a[1]=='run'and '--index'in a
        if ok:
            target=str(a[2]);ok=os.path.realpath(target)==rp or Path(target).name==run.name
        if not ok:count['foreign']+=1;continue
        try:idx=int(a[a.index('--index')+1])
        except (ValueError,IndexError):count['foreign']+=1;continue
        keep.append({**r,'index':idx,'file':f.name,'match':'path'if os.path.realpath(str(a[2]))==rp else'name'});count['kept']+=1
    return keep,count

def report(a)->dict:
    run=a.run.resolve();notes=[]
    # ---- (a) the campaign and its measured model
    try:mbytes=(run/'manifest.json').read_bytes();m=json.loads(mbytes)
    except (OSError,ValueError)as e:raise Refuse(65,f'{run}/manifest.json: {e}')
    if m.get('cost_basis')!='measured'or not m.get('cost_model_sha256'):raise Refuse(65,f'{run}: cost basis {m.get("cost_basis")!r}: the report needs a campaign on the measured basis (its model is the unit)')
    cmf=run/'cost_model.json'
    if not cmf.is_file()or digest(cmf)!=m['cost_model_sha256']:raise Refuse(65,f'{cmf} is missing or differs from the manifest pin {m["cost_model_sha256"][:12]}...')
    try:
        m,I,mh,changes=prod.verify_base(run,check_executable=False,accept_tool_change=True)
        model,_=prod.read_cost_model(cmf,m['backend'])
    except (ValueError,OSError)as e:raise Refuse(65,f'{run}: {e}')
    spp=model['seconds_per_point'];mpf=prod.mp_factor(model,m['mp_check']);inv=prod.load_inventory(I)
    lens={(s,int(L),r['id']):int(r['length'])for s in ('free','power')for L,rows in inv[s].items()for r in rows}
    groups={};blocks=[];rows=[]
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name']);groups[g['name']]={'cfg':cfg,'tasks_sqlite_bytes':(p/'tasks.sqlite').stat().st_size,'sobol_bytes':(p/'sobol.bin').stat().st_size}
    # ---- (b) every checkpoint, validated against its frozen block
    by_idx={}
    for j in m['jobs']:
        p=run/'groups'/j['group'];cfg=groups[j['group']]['cfg']
        try:bl=prod.blocks_of_rows(prod.job_rows(run,j),j['blocks'])
        except (ValueError,OSError)as e:raise Refuse(65,f'index {j["id"]}: {e}')
        for part,block in enumerate(bl):
            name=prod.block_name(j['shard'],part);f=p/'checkpoints'/f'{name}.json'
            if not f.exists():continue
            try:doc=load(f);n=prod.validate_checkpoint(doc,block,cfg,m,mh)
            except (ValueError,KeyError,TypeError)as e:raise Refuse(65,f'{f}: {e}')
            rt=doc.get('runtime')or{};fp=rt.get('fingerprint')or{};jid=str((fp.get('slurm')or{}).get('SLURM_JOB_ID'))
            rs=_jnum(float(math.fsum(float(r['seconds'])for r in n['rows'])))   # S4-R2-001: timing taken as recorded; a block without valid timing is never evaluated
            b={'index':j['id'],'group':j['group'],'block':name,'campaign':cfg['campaign'],'sector':cfg['sector'],'L':cfg['L'],'job':jid,'tasks':len(n['rows']),
               'threads':_jnum(n.get('threads')),'integration_seconds':_jnum(n.get('integration_seconds')),'load_seconds':_jnum(n.get('load_seconds')),'max_rss_kb':n.get('max_rss_kb'),
               'row_seconds':rs,'fingerprint_key':fingerprint_key(fp),'fingerprint_bytes':rt.get('fingerprint_bytes'),'cpu_model':fp.get('cpu_model'),
               'checkpoint_bytes':f.stat().st_size,'native_json_bytes':len(json.dumps(n)),'host':fp.get('host'),'graphs':sorted({r['graph']for r in n['rows']}),
               'points':sum(r['end']-r['begin']for r in n['rows']),'max_row_seconds':_jnum(max((float(r['seconds'])for r in n['rows']),default=0.)),
               'staged_bytes':sum(lens[(cfg['sector'],cfg['L'],g_)]for g_ in sorted({r['graph']for r in n['rows']}))}
            blocks.append(b);by_idx.setdefault(j['id'],[]).append(b)
            for r in n['rows']:
                k=f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{r["graph"]}'
                if k not in spp:raise Refuse(65,f'the campaign model has no key {k} (row {r["uid"]} of {f})')
                pts=r['end']-r['begin'];rows.append({'job':jid,'L':cfg['L'],'seconds':float(r['seconds']),'model_seconds':float(spp[k])*pts*mpf})
    # ---- which job
    acc=None;accp=a.accounting
    if accp:
        try:acc=load(accp)
        except (OSError,ValueError)as e:raise Refuse(65,f'--accounting {accp}: {e}')
    work=sorted({str(x['job'])for x in (acc or{}).get('attempts',[])if x.get('class')=='work'})
    J=a.job
    if J is None and 'perf3'in a.parts:
        if len(work)!=1:raise Bad(f'--job is required: the accounting names {len(work)} work jobs ({", ".join(work)or "none"})')
        J=work[0]
    if J is not None and not any(b['job']==J for b in blocks):raise Refuse(65,f'job {J} committed no checkpoint of {run}')
    jb=[b for b in blocks if J is None or b['job']==J];jr=[r for r in rows if J is None or r['job']==J]
    out={'schema':SCHEMA,'run':str(run),'job':{'id':J},'notes':notes}
    inputs={'run':{'path':str(run),'manifest_sha256':mh,'accepted_tool_changes':changes},'cost_model':{'path':str(cmf),'sha256':m['cost_model_sha256'],'cpu_model':model.get('cpu_model'),
            'mp_check':model.get('mp_check'),'mp_factor':mpf},'checkpoints':len(blocks)}
    out['inputs']=inputs
    if accp:inputs['accounting']={'path':str(accp),'sha256':digest(accp)}
    # ---- perf3
    if 'perf3'in a.parts:
        lp=run/'slurm_logs'/f'lane-{J}.log';ll=parse_lane_log(lp,J);lane=ll[-1];lane_cores=sum(lane['widths'])
        inputs['lane_log']={'path':str(lp),'sha256':digest(lp)}
        att=[x for x in acc.get('attempts',[])if str(x['job'])==J and x.get('class')=='work'];W=float(sum(x['elapsed']for x in att))
        if W<=0:raise Refuse(65,f'the accounting has no elapsed work attempt of job {J}')
        cores,csrc=alloc_cores(att,lane,lp.read_text(errors='replace'))   # the node's allocated cores, not the lanes' widths
        if lane_cores!=cores:notes.append(f'the lanes cover {lane_cores} of the {cores} allocated cores ({csrc}): the idle cores count against busy (PLAN: task seconds / (node cores x wall))')
        out['job'].update(host=lane['host'],cpu=lane['cpu'],lanes=lane['lanes'],widths=lane['widths'],lane_cores=lane_cores,cores=cores,cores_source=csrc,W=W,attempts=att,lane_log_lines=ll)
        rsec=math.fsum(r['seconds']for r in jr);busy=rsec/(cores*W)
        omp=omp_part(jb,{'host':lane['host'],'cpu':lane['cpu'],'widths':lane['widths'],'lane_cores':lane_cores,'cores':cores,'cores_source':csrc})
        cms=math.fsum(r['model_seconds']for r in jr);thr=cms/W
        ref=None;ref_v=None;refrec=None
        if a.reference_throughput is not None:refrec={'kind':'given','throughput_per_node_second':a.reference_throughput,'note':a.reference_note}
        elif a.reference_p4:
            import benchkit as bk,benchmark as bm
            r4=load(a.reference_p4);fm=bk.load_fixtures();items,parts=bm.workload_items(fm,r4['workload']['name'],float(r4['workload']['fraction']))
            refrec=ref_p4(r4,a.reference_shape,items,parts,spp,prod.mp_factor(model,(r4.get('settings')or{}).get('mp_check')or m['mp_check']))
            inputs['reference']={'path':str(a.reference_p4),'sha256':digest(a.reference_p4),'fixtures_manifest_sha256':fm['_manifest_sha256']}
        elif a.reference_opt_speed:
            sys.path.insert(0,str(ROOT/'tests'));import validate as V
            ro=load(a.reference_opt_speed)
            refrec=ref_opt_speed(ro,a.reference_binary,a.reference_shape,spp,inv,prod.mp_factor(model,ro['workload'].get('mp_check')or m['mp_check']),V.l8self_sample)
            inputs['reference']={'path':str(a.reference_opt_speed),'sha256':digest(a.reference_opt_speed)}
        if refrec is not None:
            ref=float(refrec['throughput_per_node_second'])
            if refrec.get('binary_sha256')and refrec['binary_sha256']!=m['executable_sha256']:
                ref_v='INCOMPLETE';notes.append(f'throughput reference measured another binary ({str(refrec["binary_sha256"])[:12]}..., campaign {m["executable_sha256"][:12]}...): not compared')
            else:ref_v=verdict(thr>=THROUGHPUT_MIN*ref)
        else:notes.append('no throughput reference (--reference-p4, --reference-opt-speed or --reference-throughput): throughput not compared')
        speed=[r['model_seconds']/r['seconds']for r in jr if r['seconds']>0];s8=[r['model_seconds']/r['seconds']for r in jr if r['seconds']>0 and r['L']==8]
        sref=1.0;slabel='model definition (information only: A-PERF-3 compares with the sweep\'s median; give --sweep)';skind='model_definition'
        if a.sweep:
            sw=a.sweep.resolve();sh=digest(sw/'manifest.json')
            if sh!=(model.get('source')or{}).get('manifest_sha256'):raise Refuse(65,f'--sweep {sw}: its manifest sha256 {sh[:12]}... is not the model\'s source campaign\'s')
            sm,_,smh,_=prod.verify_base(sw,check_executable=False,accept_tool_change=True);sf=prod.mp_factor(model,sm['mp_check']);sv=[];sv8=[]
            for j in sm['jobs']:
                p,cfg=prod.group_of(sw,sm,j['group'])
                for part,block in enumerate(prod.blocks_of_rows(prod.job_rows(sw,j),j['blocks'])):
                    f=p/'checkpoints'/f'{prod.block_name(j["shard"],part)}.json'
                    if not f.exists():continue
                    try:n=prod.validate_checkpoint(load(f),block,cfg,sm,smh)
                    except (ValueError,KeyError,TypeError)as e:raise Refuse(65,f'--sweep {f}: {e}')
                    for r in n['rows']:
                        k=f'{cfg["campaign"]}:{cfg["sector"]}:{cfg["L"]}:{r["graph"]}'
                        if float(r['seconds'])>0 and k in spp:
                            x=float(spp[k])*(r['end']-r['begin'])*sf/float(r['seconds']);sv.append(x);(sv8.append(x)if cfg['L']==8 else None)
            if not sv8:raise Refuse(65,f'--sweep {sw}: no L8 row')
            sref=statistics.median(sv8);slabel='the --sweep campaign\'s L8 median';skind='sweep';inputs['sweep']={'path':str(sw),'manifest_sha256':sh,'median_all':statistics.median(sv),'median_L8':sref}
        else:notes.append('no --sweep: the median per-task speed is compared with 1.0 (model definition) for information only; A-PERF-3\'s comparator is the '
                          'sweep\'s median (PLAN), so the speed and A-PERF-3 are INCOMPLETE')
        med8=statistics.median(s8)if s8 else None
        l8sec=math.fsum(r['seconds']for r in jr if r['L']==8)
        sizing=sizing_of(l8sec,rsec,cores)
        tj=[b for b in jb if timing_problem(b)is None]   # S4-R2-001: the native sums over the blocks with valid timing only; the rest are counted
        integ=math.fsum(b['threads']*b['integration_seconds']for b in tj);ld=math.fsum(b['threads']*b['load_seconds']for b in tj if b['load_seconds']is not None and b['load_seconds']>=0)
        cpu_ok=prod.norm_cpu(lane['cpu'])==prod.norm_cpu(model.get('cpu_model'))
        p3={'busy':{'value':busy,'row_seconds':rsec,'cores':cores,'cores_source':csrc,'lane_cores':lane_cores,'W':W,'rule':f'>= {BUSY_MIN:g} (row seconds / (allocated cores x W))','verdict':verdict(busy>=BUSY_MIN)},
            'openmp':omp,
            'throughput':{'cost_model_seconds':cms,'per_node_second':thr,'per_node_hour':thr*3600,'reference':refrec,
                          'ratio_to_reference':(thr/ref if ref else None),'rule':f'>= {THROUGHPUT_MIN:g} x the reference','verdict':ref_v or'INCOMPLETE'},
            'speed':{'median_all':statistics.median(speed)if speed else None,'median_L8':med8,'L8_p10':pct(s8,.1),'L8_p90':pct(s8,.9),'reference':sref,'reference_label':slabel,
                     'reference_kind':skind,'ratio':(med8/sref if med8 is not None else None),'rule':f'|median_L8 / the sweep\'s median_L8 - 1| <= {SPEED_TOL:g} (PLAN; INCOMPLETE without --sweep)',
                     'verdict':(verdict(abs(med8/sref-1)<=SPEED_TOL)if skind=='sweep'else'INCOMPLETE')if med8 is not None else'INCOMPLETE'},
            'cpu_matches_model':{'lane_log_cpu':lane['cpu'],'model_cpu':model.get('cpu_model'),'verdict':verdict(cpu_ok)},
            'references':{'throughput':(refrec or{}).get('kind'),'speed':skind,'cores':csrc},
            'sizing':sizing,
            'causes':{'native_integration_core_seconds':integ,'native_load_core_seconds':ld,'outside_native_core_seconds':cores*W-integ-ld,
                      'allocated_core_seconds':cores*W,'load_share_of_native':(ld/(ld+integ)if ld+integ>0 else None),'load_share_of_node':ld/(cores*W),
                      'outside_native_share_of_node':(cores*W-integ-ld)/(cores*W),'untimed_blocks':len(jb)-len(tj)}}
        p3['verdict']=verdict(*(p3[k]['verdict']for k in ('busy','openmp','throughput','speed','cpu_matches_model','sizing')))
        out['sizing']=sizing;out['a_perf_3']=p3
    # ---- hook records and idx logs (orc13, orc5)
    logs={}
    for f in sorted((run/'lanes'/'logs').glob('idx*.log'))if (run/'lanes'/'logs').is_dir()else[]:
        mm=IDX_RE.fullmatch(f.name)
        if not mm:continue
        t=f.read_text(errors='replace');fp=FP_RE.search(t)
        logs.setdefault((int(mm.group(1)),mm.group(2)),[]).append({'file':f.name,'fingerprint_key':fp.group(1)if fp else None,'fingerprint_bytes':int(fp.group(3))if fp else None,
                                                                    'done':[(x.group(2),x.group(3),x.group(1)=='committed')for x in DONE_RE.finditer(t)]})
    hooks=[];hc=None
    if a.hook_dir:
        hooks,hc=read_hooks(a.hook_dir,run);inputs['hook']={'dir':str(a.hook_dir),'schema':HOOK_SCHEMA,**hc}
    pairs={};amb=[]
    for h in hooks:pairs.setdefault((h['index'],str(h.get('job'))),[]).append(h)
    runs=[]
    for (idx,job),hs in sorted(pairs.items()):
        if J is not None and job!=J:continue
        lg=logs.get((idx,job),[])
        if len(hs)!=1 or len(lg)!=1:amb.append({'index':idx,'job':job,'hook_records':len(hs),'idx_logs':len(lg)});continue
        h=hs[0];L=lg[0];j=m['jobs'][idx];g=groups[j['group']];committed={(gr,nm)for gr,nm,_ in L['done']}
        own={'tasks_bytes':int(j['tasks_bytes']),'blocks_file_bytes':(run/j['blocks_file']).stat().st_size,'sobol_bytes':g['sobol_bytes'],
             'staged_bytes':0,'native_json_bytes_estimate':0,'checkpoint_bytes':0};native=0
        for b in by_idx.get(idx,[]):
            if (b['group'],b['block'])in committed:   # the run staged the block and its native worker ran (NATIVE_RULE)
                own['staged_bytes']+=b['staged_bytes'];own['native_json_bytes_estimate']+=b['native_json_bytes'];native+=b['staged_bytes']
                if not next(c for gr,nm,c in L['done']if (gr,nm)==(b['group'],b['block'])):own['checkpoint_bytes']+=b['checkpoint_bytes']   # a verified duplicate reads the existing one too
            else:own['checkpoint_bytes']+=b['checkpoint_bytes']
        rchar=int((h.get('io')or{}).get('rchar',0));fpb=L['fingerprint_bytes']or 0
        runs.append({'index':idx,'job':job,'group':j['group'],'tasks_sqlite_bytes':g['tasks_sqlite_bytes'],'hook_file':h['file'],'idx_log':L['file'],'rchar':rchar,
                     'own':own,**run_bytes(rchar,own,native,fpb),'fingerprint_bytes':fpb,
                     'ru_maxrss_self_kb':h.get('ru_maxrss_self_kb'),'ru_maxrss_children_kb':h.get('ru_maxrss_children_kb'),'host':h.get('host'),'match':h['match']})
    out['runs']=runs
    if 'orc13'in a.parts:
        keys={}
        for (idx,job),lg in logs.items():
            if J is not None and job!=J:continue
            for L in lg:
                if L['fingerprint_key']:keys.setdefault(L['fingerprint_key'],{'idx_logs':set(),'checkpoints':set()})['idx_logs'].add(L['fingerprint_bytes'])
        for b in jb:
            if b['fingerprint_key']is not None:keys.setdefault(b['fingerprint_key'],{'idx_logs':set(),'checkpoints':set()})['checkpoints'].add(b['fingerprint_bytes'])
        fpk={k:{'idx_logs':sorted(v['idx_logs']),'checkpoints':sorted(v['checkpoints']),'values':sorted(v['idx_logs']|v['checkpoints'])}for k,v in sorted(keys.items())}
        fpv=verdict(all(len(v['values'])==1 for v in fpk.values()))if fpk else'INCOMPLETE'
        out['a_orc_13']=orc13_part({'per_key':fpk,'rule':'one value per fingerprint key (idx logs and checkpoints)','verdict':fpv},runs,
                                   {n:g['tasks_sqlite_bytes']for n,g in groups.items()},amb)
    if 'orc5'in a.parts:
        idxs=sorted({b['index']for b in jb});per=[]
        for idx in idxs:
            nat=max(int(b['max_rss_kb']or 0)for b in by_idx[idx]if J is None or b['job']==J)*1024;est=int(m['jobs'][idx]['est_peak_bytes'])
            hr=[r for r in runs if r['index']==idx]
            py=max((int(r['ru_maxrss_self_kb']or 0)*1024 for r in hr),default=None);ch=max((int(r['ru_maxrss_children_kb']or 0)*1024 for r in hr),default=None)
            e={'index':idx,'native_peak_bytes':nat,'python_peak_bytes':py,'est_peak_bytes':est,'native_only_ratio':nat/est,
               'ratio':((nat+py)/est if py is not None else None),'children_peak_bytes':ch,'children_minus_native_bytes':(ch-nat if ch is not None else None)}
            e['verdict']=verdict(e['ratio']<=RSS_MAX)if e['ratio']is not None else'INCOMPLETE';per.append(e)
        o5={'indices':per,'rule':f'(native max_rss_kb + Python ru_maxrss_self_kb) x 1024 / est_peak_bytes <= {RSS_MAX:g} for every index',
            'max_ratio':max((e['ratio']for e in per if e['ratio']is not None),default=None),'max_native_only_ratio':max((e['native_only_ratio']for e in per),default=None),
            'verdict':verdict(*(e['verdict']for e in per))if per else'INCOMPLETE'}
        if not a.hook_dir:notes.append('A-ORC-5 without the hook: the native-only ratio is reported; the Python part needs --hook-dir')
        out['a_orc_5']=o5
    out['block_detail']=[{k:b[k]for k in ('index','group','block','job','tasks','threads','integration_seconds','load_seconds','row_seconds','max_rss_kb','fingerprint_bytes',
                                          'points','max_row_seconds','host')}|{'distinct_graphs':len(b['graphs'])}
                         |{'omp_efficiency':efficiency(b)}for b in jb]
    out['made_on']=host_info();out['made_utc']=utc()
    return out

def rederive(src:Path,hook_dir:Path|None)->dict:
    """--rederive REPORT.json: a committed report re-evaluated under the Stage-6 rules (F13-d3, S4-007), everything else
    the source's; see the module docstring."""
    try:rec=load(src)
    except (OSError,ValueError)as e:raise Refuse(65,f'--rederive {src}: {e}')
    if not isinstance(rec,dict)or rec.get('schema')not in(SCHEMA_V1,SCHEMA)or not('a_perf_3'in rec or 'a_orc_13'in rec):
        raise Refuse(65,f'--rederive {src}: not a thru_report record ({SCHEMA_V1} or {SCHEMA}) with an a_perf_3 or a_orc_13 part')
    out=json.loads(json.dumps(rec));out['schema']=SCHEMA;done=[];taken=[];hc=None;J=(rec.get('job')or{}).get('id')
    was={k:(rec.get(k)or{}).get('verdict')for k in ('a_perf_3','a_orc_13','a_orc_5')if k in rec}
    if 'a_perf_3'in rec:
        if not rec.get('block_detail'):raise Refuse(65,f'--rederive {src}: a_perf_3 without block_detail')
        bl=[{**b,'L':int(str(b['group']).rsplit('_L',1)[1])}for b in rec['block_detail']if J is None or str(b.get('job'))==str(J)]
        jb=rec['job'];p3=out['a_perf_3']
        p3['openmp']=omp_part(bl,{k:jb.get(k)for k in ('host','cpu','widths','lane_cores','cores','cores_source')})
        p3['verdict']=verdict(*(p3[k]['verdict']for k in ('busy','openmp','throughput','speed','cpu_matches_model','sizing')))
        done.append('a_perf_3.openmp (the per-block rule with each block\'s timing validity, and its cause analysis, from block_detail) and the a_perf_3 verdict')
        taken.append('a_perf_3 busy, throughput, speed, cpu_matches_model, sizing and causes; block_detail; job; inputs; sizing')
    if 'a_orc_13'in rec:
        if not rec.get('runs'):raise Refuse(65,f'--rederive {src}: a_orc_13 without paired runs')
        hooks=None
        if hook_dir:
            hooks={};hc={'dir':str(hook_dir),'files':0,'used':0}
            for f in sorted(Path(hook_dir).glob('*.json')):
                hc['files']+=1
                try:hooks[f.name]=json.loads(f.read_text())
                except (OSError,ValueError):pass
        runs=[]
        for r in rec['runs']:
            rchar=int(r['rchar'])
            if hooks is not None:
                h=hooks.get(r.get('hook_file'));a=(h or{}).get('argv')or[]
                try:hidx=int(a[a.index('--index')+1])
                except (ValueError,IndexError):hidx=None
                if not isinstance(h,dict)or h.get('schema')!=HOOK_SCHEMA or str(h.get('job'))!=str(r['job'])or hidx!=r['index']:
                    raise Refuse(65,f'--hook-dir {hook_dir}: no {HOOK_SCHEMA} record {r.get("hook_file")} of job {r["job"]} index {r["index"]}')
                rchar=int((h.get('io')or{}).get('rchar'));hc['used']+=1
                if rchar!=int(r['rchar']):raise Refuse(65,f'{r["hook_file"]}: rchar {rchar} but the report has {r["rchar"]} for index {r["index"]}')
            nat=r.get('native_staged_reads',r['own']['staged_bytes'])   # NATIVE_RULE on a -1 record: the staged bytes of its committed blocks
            keep={k:v for k,v in r.items()if k not in('own_bytes','non_own','non_own_wo_fp','own_bytes_process','native_staged_reads','non_own_raw','non_own_raw_wo_fp')}
            runs.append({**keep,'rchar':rchar,**run_bytes(rchar,r['own'],nat,int(r['fingerprint_bytes']))})
        old=rec['a_orc_13'];out['runs']=runs
        out['a_orc_13']=orc13_part(old['fingerprint_bytes'],runs,{r['group']:r['tasks_sqlite_bytes']for r in runs},old.get('ambiguous',[]))
        done.append('a_orc_13 (native_staged_reads, non_own and non_own_raw with and without fingerprint_bytes, the group comparison, both fits, the verdict) and '
                    'the byte fields of runs, '+('from each rchar re-read from its hook record'if hooks is not None else'from the report\'s rchar'))
        taken.append('per run: own (bytes per category), group, tasks_sqlite_bytes, fingerprint_bytes, index, job, hook and idx-log names, peak RSS; the '
                     'fingerprint_bytes part and the ambiguous list (they need the campaign\'s checkpoints, inventory and idx logs)')
    if 'a_orc_5'in rec:taken.append('a_orc_5')
    out['rederived']={'from':{'path':str(src),'sha256':digest(src),'schema':rec['schema'],'made_utc':rec.get('made_utc'),'made_on':rec.get('made_on'),'verdicts':was},
                      'rules':'Stage 6: A-PERF-3 OpenMP per block (S4-007), untimed blocks never PASS (S4-R2-001), causes established or possible (S4-R2-002); '
                              'A-ORC-13 own bytes with the native child\'s reads (F13-d3, NATIVE_RULE)',
                      'recomputed':done,'taken_from_source':taken,'hook':hc,'verdicts':{k:(out.get(k)or{}).get('verdict')for k in was},
                      'made_on':host_info(),'made_utc':utc()}
    return out

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run',type=Path,nargs='?');p.add_argument('--rederive',type=Path)
    p.add_argument('--job');p.add_argument('--accounting',type=Path);p.add_argument('--sweep',type=Path)
    p.add_argument('--reference-p4',type=Path);p.add_argument('--reference-opt-speed',type=Path);p.add_argument('--reference-binary');p.add_argument('--reference-shape')
    p.add_argument('--reference-throughput',type=float);p.add_argument('--reference-note');p.add_argument('--hook-dir',type=Path);p.add_argument('--parts')
    p.add_argument('--strict',action='store_true');p.add_argument('--output',type=Path,required=True)
    try:a=p.parse_args(argv)
    except SystemExit as e:return 64 if e.code else 0
    try:
        if a.rederive:
            other=[n for n in ('run','job','accounting','sweep','reference_p4','reference_opt_speed','reference_binary','reference_shape','reference_throughput',
                               'reference_note','parts')if getattr(a,n)is not None]+(['--strict']if a.strict else[])
            if other:raise Bad(f'--rederive takes only --hook-dir and --output (not {", ".join(other)})')
            if a.hook_dir and not a.hook_dir.is_dir():raise Bad(f'--hook-dir {a.hook_dir} is not a directory')
            if a.output.exists():raise Bad(f'{a.output} exists: a report is never overwritten')
            rec=rederive(a.rederive,a.hook_dir);a.output.parent.mkdir(parents=True,exist_ok=True)
            with open(a.output,'x')as f:f.write(json.dumps(rec,indent=1,allow_nan=False)+'\n')
            print(json.dumps({'output':str(a.output),'was':rec['rederived']['from']['verdicts'],'now':rec['rederived']['verdicts'],
                              **({'openmp':rec['a_perf_3']['openmp']['verdict']}if 'a_perf_3'in rec else{})}))
            return 0
        if a.run is None:raise Bad('RUN is required (or --rederive REPORT.json)')
        refs=[x for x in (a.reference_p4,a.reference_opt_speed,a.reference_throughput)if x is not None]
        if len(refs)>1:raise Bad('give one reference: --reference-p4, --reference-opt-speed or --reference-throughput')
        if a.reference_opt_speed and not a.reference_binary:raise Bad('--reference-opt-speed needs --reference-binary NAME')
        if a.reference_binary and not a.reference_opt_speed:raise Bad('--reference-binary goes with --reference-opt-speed')
        if a.reference_throughput is not None and not(a.reference_note or'').strip():raise Bad('--reference-throughput needs --reference-note TEXT')
        if a.reference_shape and not(a.reference_p4 or a.reference_opt_speed):raise Bad('--reference-shape goes with --reference-p4 or --reference-opt-speed')
        a.parts=[x.strip()for x in a.parts.split(',')if x.strip()]if a.parts else ['perf3']+(['orc13','orc5']if a.hook_dir else[])
        bad=[x for x in a.parts if x not in PARTS]
        if bad or not a.parts:raise Bad(f'--parts: unknown {bad}; choose from {",".join(PARTS)}')
        if 'perf3'in a.parts and not a.accounting:raise Bad('perf3 needs --accounting ACC.json (tools/accounting.py RUN --json): W, the work job\'s elapsed time')
        if 'orc13'in a.parts and not a.hook_dir:raise Bad('orc13 needs --hook-dir (the external hook\'s records of rchar per production.py run)')
        if a.hook_dir and not a.hook_dir.is_dir():raise Bad(f'--hook-dir {a.hook_dir} is not a directory')
        if a.output.exists():raise Bad(f'{a.output} exists: a report is never overwritten')
        rec=report(a)
        if a.output.exists():raise Bad(f'{a.output} exists: a report is never overwritten')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with open(a.output,'x')as f:f.write(json.dumps(rec,indent=1,allow_nan=False)+'\n')
    except Bad as e:print(f'thru_report: {e}',file=sys.stderr);return 64
    except Refuse as e:print(f'thru_report: {e}',file=sys.stderr);return e.code
    except (ValueError,OSError,KeyError,TypeError,ZeroDivisionError)as e:print(f'thru_report: {type(e).__name__}: {e}',file=sys.stderr);return 1
    summ={k:rec[k]['verdict']for k in ('a_perf_3','a_orc_13','a_orc_5')if k in rec}
    if 'a_perf_3'in rec:
        x=rec['a_perf_3'];summ.update(busy=x['busy']['value'],omp_all=x['openmp']['all']['time_weighted_mean'],omp_min=x['openmp']['all']['min'],openmp=x['openmp']['verdict'],throughput_per_node_hour=x['throughput']['per_node_hour'],
                                      throughput_ratio=x['throughput']['ratio_to_reference'],speed_ratio=x['speed']['ratio'],sizing=x['sizing']['verdict'])
    print(json.dumps({'output':str(a.output),**summ}))
    return 1 if a.strict and any(v!='PASS'for k,v in summ.items()if k in('a_perf_3','a_orc_13','a_orc_5'))else 0
if __name__=='__main__':sys.exit(main())
