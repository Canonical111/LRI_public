#!/usr/bin/env python3
"""Planning calibration: native task seconds per inventory proxy unit per (backend, campaign, sector, L), and the
first sweep's preliminary proxy (PLAN component B/D, R13, R18).

  calibrate.py RUN [--host-regex RE] [--threads N] [--update FILE] [--note TEXT] [--run-label PATH]
        measure campaign-keyed rows from a finished campaign:
          seconds_per_proxy_unit = sum of per-task native seconds (checkpoint rows)
                                   / sum over the same tasks of (inventory proxy cost per point x points)
        with the proxy cost per point the inventory 'cost' field, max(1, terms x monomials), recomputed from the
        campaign's inputs/inventory.json, never the task table. --update merges the rows into a calibration file
        (schema c8-d2-calibration-1: backends -> backend -> campaign -> sector -> L); a C7(2)-format file (pooled rows
        keyed (backend, sector, L)) is converted: its rows are dropped, since only the pinned copy
        reference/c7d2_hpc_a55958f/tools/calibration.json keeps them (R18).
        W10 (Stage-6 fix round 4): every checkpoint is validated against its authenticated task block before its
        timings are read (production.validate_checkpoint, as the merge does); invalid timings refuse.
        W11: a file holds the rows of ONE measurement identity (numerics, rates identity; recorded as 'identity'), and
        tools/calibration.json only the exact path's default-rate rows: --update into a file of another identity, or
        rows of a profile or a rate map into tools/calibration.json, refuses before anything is written.
  calibrate.py --bootstrap [--output FILE]
        regenerate tools/bootstrap_proxy.json (schema c8-d2-bootstrap-proxy-1) from the pinned byte copy
        reference/c7d2_hpc_a55958f/tools/calibration.json ONLY: it is hashed against its reference/SHA256SUMS_c8 entry
        and only the hashed bytes are parsed (a mismatch refuses, naming the file). Rows per (backend, sector, L=3..8):
        C7(2)'s pooled-campaign row at L3..L7 and its L7 row for L8, each x 3. It never reads the active
        tools/calibration.json (which --update rewrites), opens nothing under .git and runs no git command, so it works
        in a `git archive` export at any point of the package's life. The output is labelled preliminary_proxy and
        bounds task lengths of the first sweep only; it is never a calibration row or a cost.
"""
from __future__ import annotations
import argparse,hashlib,json,math,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,digest,load,replace_file,utc
CAL_SCHEMA='c8-d2-calibration-1'
PINNED_C7=Path('c7d2_hpc_a55958f/tools/calibration.json')  # relative to reference/
BOOT_FACTOR=3
PRELIMINARY='preliminary_proxy (C7(2) pooled-campaign calibration, L8 from L7, x3; not a measurement)'

def bootstrap_doc()->tuple[dict,bytes]:
    ref=ROOT/'reference';entry=None
    for line in (ref/'SHA256SUMS_c8').read_text().splitlines():
        h,_,name=line.partition('  ')
        if name==PINNED_C7.as_posix():entry=h
    if entry is None:raise SystemExit(f'reference/SHA256SUMS_c8 has no entry for {PINNED_C7}')
    data=(ref/PINNED_C7).read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry:raise SystemExit(f'reference/{PINNED_C7} does not match its reference/SHA256SUMS_c8 entry {entry[:12]}...; refusing to derive the preliminary proxy')
    c7=json.loads(data);rows={}
    for backend,secs in sorted(c7['backends'].items()):
        for sector in ('free','power'):
            src=secs.get(sector)or{}
            for L in range(3,9):
                r=src.get(str(min(L,7)))
                if not r or not r.get('seconds_per_proxy_unit'):raise SystemExit(f'the pinned C7(2) calibration has no {backend} {sector} L{min(L,7)} row')
                rows.setdefault(backend,{}).setdefault(sector,{})[str(L)]=BOOT_FACTOR*float(r['seconds_per_proxy_unit'])
    doc={'schema':'c8-d2-bootstrap-proxy-1','label':PRELIMINARY,'factor':BOOT_FACTOR,'l8_from':'L7',
         'source':{'path':'reference/'+PINNED_C7.as_posix(),'sha256':entry,'bytes':len(data),'checksum_list':'reference/SHA256SUMS_c8'},
         'unit':'preliminary seconds per inventory proxy unit (max(1, M x T) per point)','rows':rows,
         'use':'bounds the task length of the first sweep (production.py plan --bootstrap-chunk, R13) against --max-task-seconds; '
               'never a calibration row, a cost, a time estimate or a lane deadline'}
    return doc,(json.dumps(doc,indent=1,sort_keys=True)+'\n').encode()

def row_seconds(r:dict,where:str)->float:
    """W10: a row's native seconds, a finite non-negative JSON number (not a boolean, a string or NaN), else ValueError."""
    s=r.get('seconds')
    if isinstance(s,bool)or not isinstance(s,(int,float))or not math.isfinite(s)or s<0:
        raise ValueError(f'{where}: row {r.get("uid")} has an invalid timing seconds = {s!r} (a finite non-negative number); nothing calibrated')
    return float(s)

def measure(run:Path,host_regex=None,threads=None,run_label=None)->dict:
    """Campaign-keyed rows from the validated checkpoints of a campaign (W10, Stage-6 fix round 4, S6D-R4-01): every
    existing checkpoint is validated against its authenticated task block before any timing is read, exactly as the
    merge validates it (production.validate_checkpoint: the campaign's manifest and group-config identity, executable,
    inputs, net and rates identity, the campaign's runtime identity, the payload digest, the native metadata, the task
    coordinates, jets, counters and tail fields of every row, the block streamed from the index's task file at its
    manifest pin); a checkpoint copied from another campaign, a timing changed without its checksum, a missing or
    reordered row are refused (ValueError), and every row's seconds must be a finite non-negative number, with a
    positive total per (campaign, sector, L). A gated profile campaign (W8) also needs every checkpoint's libgmp to be the
    one its J-FLAG gate validated (production.gate_gmp_binding), exactly as the merges check it."""
    import production as prod
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run,check_executable=False)
    inv=prod.load_inventory(I);acc={};rx=re.compile(host_regex)if host_regex else None;present=set()
    rates=prod.rate_map_for(run,m);rkey,_src=prod.campaign_runtime_key(run,m);T=m['checkpoint_tasks']
    gb=prod.gate_gmp_binding(m)  # W8 with W10 (fix round 4, integration): a gated campaign's checkpoints must show the gate's libgmp, as in the merges
    for j in m['jobs']:
        p,cfg=prod.group_of(run,m,j['group']);cost={r['id']:max(1,int(r['cost']))for r in inv[cfg['sector']][str(cfg['L'])]};key=(cfg['campaign'],cfg['sector'],cfg['L']);present.add(key)
        for k,block in enumerate(prod.iter_job_blocks(run,j,T)):  # the authenticated task rows, one block at a time
            f=p/'checkpoints'/f'{prod.block_name(j["shard"],k)}.json'
            if not f.exists():continue
            d=load(f);where=str(f.relative_to(run))
            try:n=prod.validate_checkpoint(d,block,cfg,m,mh,rates,rkey,gb)  # W10: before any timing is read
            except (ValueError,KeyError,TypeError,ArithmeticError)as e:raise ValueError(f'{where}: not a valid checkpoint of this campaign ({type(e).__name__}: {e}); nothing calibrated')from None
            fp=(d.get('runtime')or{}).get('fingerprint')or{}
            if (rx and not(fp.get('host')and rx.fullmatch(fp['host'])))or(threads and n['threads']!=threads):continue
            a=acc.setdefault(key,{'task_seconds':0.,'proxy_units':0,'tasks':0,'checkpoints':0,'job_ids':set(),'hosts':set(),'threads':set(),'cpu_models':set()})
            a['task_seconds']+=math.fsum(row_seconds(r,where)for r in n['rows']);a['proxy_units']+=sum(cost[r['graph']]*(r['end']-r['begin'])for r in n['rows'])
            a['tasks']+=len(n['rows']);a['checkpoints']+=1;a['threads'].add(n['threads'])
            s=fp.get('slurm')or{};jid=s.get('SLURM_ARRAY_JOB_ID')or s.get('SLURM_JOB_ID')
            if jid:a['job_ids'].add(str(jid))
            if fp.get('host'):a['hosts'].add(fp['host'])
            if fp.get('cpu_model'):a['cpu_models'].add(fp['cpu_model'])
    missing=sorted(present-set(acc))
    if missing:raise ValueError(f'the selection (host_regex={host_regex!r}, threads={threads!r}) has no checkpoints for {missing}; nothing calibrated')
    zero=sorted(k for k,a in acc.items()if not (a['task_seconds']>0 and a['proxy_units']>0))
    if zero:raise ValueError(f'no positive task seconds or proxy units for {zero}: no calibration row (seconds per proxy unit) can be formed; nothing calibrated')
    rows={}
    for (c,s,L),a in sorted(acc.items()):
        rows.setdefault(c,{}).setdefault(s,{})[str(L)]={'seconds_per_proxy_unit':a['task_seconds']/a['proxy_units'],'task_seconds':a['task_seconds'],'proxy_units':a['proxy_units'],
                                                        'tasks':a['tasks'],'checkpoints':a['checkpoints'],'job_ids':sorted(a['job_ids']),'hosts':sorted(a['hosts']),
                                                        'threads':sorted(a['threads']),'cpu_models':sorted(a['cpu_models'])}
    source={'run':run_label or str(run),'manifest_sha256':mh,'manifest_schema':m['schema'],'backend':m['backend'],'numerics':m['numerics'],
            'rates_identity':m['rates_identity'],'executable_sha256':m['executable_sha256'],'compiler':(m.get('build')or{}).get('compiler'),
            'mp_backend':(m.get('build')or{}).get('mp_backend'),'selection':{'host_regex':host_regex,'threads':threads},'derived_utc':utc(),'method':'tools/calibrate.py'}
    return {'backend':m['backend'],'source':source,'rows':rows}

DEFAULT_IDENTITY={'numerics':'exact','rates_identity':'default'}
PACKAGE_CALIBRATION=ROOT/'tools/calibration.json'
def row_identity(row:dict)->dict:
    src=row.get('source')if isinstance(row.get('source'),dict)else{}
    return {'numerics':src.get('numerics'),'rates_identity':src.get('rates_identity')}

def file_identity(cal:dict,where)->dict|None:
    """W11: the measurement identity (numerics, rates identity) of a c8-d2-calibration-1 file: its 'identity' key and that
    of every row's source, which must all agree (a file mixing measurements refuses, ValueError); None for a file with
    no rows and no identity (a new or converted file)."""
    ids=[]
    if cal.get('identity')is not None:ids.append(cal['identity'])
    for b in (cal.get('backends')or{}).values():
        for secs in (b or{}).values():
            for loops in (secs or{}).values():
                for row in (loops or{}).values():ids.append(row_identity(row)if isinstance(row,dict)else None)
    uniq=[]
    for x in ids:
        if x not in uniq:uniq.append(x)
    if len(uniq)>1:raise ValueError(f'{where} mixes calibration measurements of several numerics or rates identities ({uniq[:3]}); split it before updating')
    return uniq[0]if uniq else None

def check_destination(path:Path,identity:dict)->None:
    """W11 (Stage-6 fix round 4, S6D-R4-02): rows measured under `identity` (numerics, rates identity) may be written
    only into a calibration file of the same identity. The package's tools/calibration.json holds the exact path's
    default-rate rows (production.py plan reads it for every calibrated-proxy plan), so rows of another numerics profile
    or rate map need their own file (sweep.py --calibration FILE, calibrate.py --update FILE), and a file never mixes
    identities (a default-rate plan would otherwise be sized by measurements under another map or profile). ValueError,
    before anything is written."""
    path=Path(path)
    if path.resolve()==PACKAGE_CALIBRATION.resolve()and identity!=DEFAULT_IDENTITY:
        raise ValueError(f'tools/calibration.json holds the exact path\'s default-rate calibration rows (production.py plan reads it); rows measured under '
                         f'numerics {identity["numerics"]!r} and rates identity {identity["rates_identity"]!r} need their own file (--calibration FILE or --update FILE; W11)')
    if path.exists():
        cal=load(path)
        if cal.get('schema')!=CAL_SCHEMA:return  # a C7(2)-format file is converted: its pooled rows are dropped
        have=file_identity(cal,path)
        if have is not None and have!=identity:
            raise ValueError(f'{path} holds calibration rows measured under numerics {have["numerics"]!r} and rates identity {have["rates_identity"]!r}; '
                             f'these were measured under {identity["numerics"]!r} and {identity["rates_identity"]!r}: write them into another file (W11)')

def update(path:Path,result:dict,note:str|None=None)->None:
    """Merge campaign-keyed rows into a calibration file (a C7(2)-format file is converted, its pooled rows dropped). The
    destination must be of the rows' measurement identity (check_destination, W11), which the file records as
    'identity'."""
    if not result['rows']:raise ValueError('no measured rows; calibration file not changed')
    identity={'numerics':result['source']['numerics'],'rates_identity':result['source']['rates_identity']}
    check_destination(path,identity)
    cal=load(path)if Path(path).exists()else{}
    if cal.get('schema')!=CAL_SCHEMA:
        cal={'schema':CAL_SCHEMA,'unit':"native task seconds per inventory proxy unit; proxy cost per point = max(1, terms x monomials), the inventory 'cost' field",
             'definition':'sum of per-task native seconds (checkpoint rows) / sum over the same tasks of (inventory proxy cost per point x points); tools/calibrate.py',
             'use':'planning estimates and chunking of test-only plans (production.py plan, calibrated-proxy basis); never sample counts or estimator weights. '
                   'A missing (backend, campaign, sector, L) row leaves that group without a cost basis; another backend\'s or campaign\'s row is never substituted.',
             'c7_rows':'the C7(2) pooled rows (keyed backend, sector, L) are kept only in the pinned copy reference/c7d2_hpc_a55958f/tools/calibration.json (R18)',
             'backends':{}}
    cal['identity']=identity  # W11: the file's one measurement identity
    b=cal['backends'].setdefault(result['backend'],{})
    for c,secs in result['rows'].items():
        for s,loops in secs.items():
            for L,row in loops.items():b.setdefault(c,{}).setdefault(s,{})[L]={**row,'source':result['source'],**({'note':note}if note else{})}
    replace_file(Path(path),(json.dumps(cal,indent=1)+'\n').encode())

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path,nargs='?')
    p.add_argument('--bootstrap',action='store_true');p.add_argument('--output',type=Path,help='--bootstrap: output (default tools/bootstrap_proxy.json)')
    p.add_argument('--host-regex');p.add_argument('--threads',type=int);p.add_argument('--update',type=Path);p.add_argument('--note');p.add_argument('--run-label')
    a=p.parse_args(argv)
    if a.bootstrap:
        if a.run:p.error('--bootstrap takes no RUN')
        doc,data=bootstrap_doc();out=a.output or ROOT/'tools/bootstrap_proxy.json';replace_file(out,data)
        print(json.dumps({'output':str(out),'sha256':hashlib.sha256(data).hexdigest(),'source':doc['source']},indent=1));return 0
    if not a.run:p.error('give RUN or --bootstrap')
    try:
        r=measure(a.run,a.host_regex,a.threads,a.run_label)
        if a.update:update(a.update,r,a.note)
    except ValueError as e:print(f'calibrate: {e}',file=sys.stderr);return 2  # W10, W11: refused, nothing written
    print(json.dumps(r,indent=1));return 0
if __name__=='__main__':sys.exit(main())
