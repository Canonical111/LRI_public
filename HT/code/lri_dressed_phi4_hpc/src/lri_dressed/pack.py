"""Pack-campaign items (schema lri-dressed-pack-v1): identity, CLI command and result binding.

An item id ends with a digest of its complete numerical configuration, so a regenerated
manifest with other tolerances, backend, seeds or deltas can never reuse old completion
records. A completion record lists the checksummed result envelopes it produced, and is
accepted only if they still validate and match the item.
"""
from __future__ import annotations
import json,math,sys
from pathlib import Path
from .io import digest,read_envelope,validate_result,runtime

NUMERIC_KEYS=('bath_cut','nz','osc','backend','window','window_mode','window_tol','window_maxiter','deltas','seed_dir',
    'eig_tol','residual_tol','tuning_tol','maxiter','max_eig_iter','ncv')
RESOURCE_KEYS=('threads','mem_gib','est_seconds','resource_origin','plan_envelope_gib')


BASIS_KEYS=('local_basis_path','local_basis_sha256')

def item_digest(item):
    cfg={k:item[k] for k in NUMERIC_KEYS}
    if any(k in item for k in BASIS_KEYS):
        if not all(k in item for k in BASIS_KEYS):raise ValueError('Incomplete basis binding in item')
        cfg.update({k:item[k] for k in BASIS_KEYS})
    return digest(cfg)


def item_id(item):
    tag='raw' if item['window']=='none' else f"win{item['window_mode'][:3]}"
    ds=item['deltas'];span='x%.8f'%ds[0] if len(ds)==1 else f'lane{len(ds)}'
    return f"N{item['bath_cut']}_z{item['nz']}_o{item['osc']}_{tag}_{span}_{item_digest(item)[:12]}"


def check_item(item):
    """Manifest-time invariants: id bound to the numerics, memory reservation passes the CLI guard."""
    missing=[k for k in NUMERIC_KEYS+RESOURCE_KEYS if k not in item]
    if missing:raise ValueError(f"item {item.get('id')}: missing {missing}")
    if item['id']!=item_id(item):raise ValueError(f"item {item['id']}: id is not bound to its numerical configuration")
    if not item['mem_gib']>=item['plan_envelope_gib']:raise ValueError(f"item {item['id']}: mem_gib below the planner envelope")
    if item['seed_dir'] is not None and not Path(item['seed_dir']).is_absolute():raise ValueError(f"item {item['id']}: seed_dir must be absolute")
    if any(k in item for k in BASIS_KEYS):
        from .local_basis import load_basis,for_configuration,density_plan
        from .planning import plan
        if not all(k in item for k in BASIS_KEYS) or len(item['deltas'])!=1:
            raise ValueError('Density-basis pack items require a full basis binding and exactly one delta')
        if not Path(item['local_basis_path']).is_absolute():raise ValueError('Basis path must be absolute')
        rec=load_basis(item['local_basis_path'],item['local_basis_sha256'])
        for_configuration(rec,delta=item['deltas'][0],nz=item['nz'],osc=item['osc'],
                          window=item['window'],window_mode=item['window_mode'])
        required=density_plan(plan(item['bath_cut'],item['nz'],item['osc'],item['backend'],item['ncv'],item['window']),rec)
        if item['mem_gib']<required['memory_envelope_gib']:
            raise ValueError('Density item memory reservation is below its actual planner envelope')



def command(item,results,python=sys.executable):
    cmd=[python,'-m','lri_dressed','run','--bath-cut',str(item['bath_cut']),'--nz',str(item['nz']),'--osc',str(item['osc']),
         '--backend',item['backend'],'--deltas',*map(repr,item['deltas']),'--threads',str(item['threads']),
         '--memory-limit-gib',repr(float(item['mem_gib'])),'--output-dir',str(results),'--resume',
         '--eig-tol',repr(item['eig_tol']),'--residual-tol',repr(item['residual_tol']),'--tuning-tol',repr(item['tuning_tol']),
         '--maxiter',str(item['maxiter']),'--max-eig-iter',str(item['max_eig_iter']),'--ncv',str(item['ncv']),'--window',item['window']]
    if item['window']!='none':
        cmd+=['--window-mode',item['window_mode'],'--window-tol',repr(item['window_tol']),'--window-maxiter',str(item['window_maxiter'])]
    if item.get('seed_dir'):cmd+=['--seed-dir',item['seed_dir']]
    if item.get('local_basis_path'):
        cmd+=['--local-basis',item['local_basis_path'],'--local-basis-sha256',item['local_basis_sha256']]
    return cmd


def check_record(item,path,source_sha256):
    """Validate one result envelope and its agreement with the item; return (delta, record sha256)."""
    rec=read_envelope(path,'result');cfg=rec['config'];validate_result(rec['payload'],cfg)
    want={'bath_cut':item['bath_cut'],'nz':item['nz'],'osc':item['osc'],'resolved_backend':item['backend'],
          'window':item['window'],'window_mode':item['window_mode'],'window_tol':item['window_tol'],
          'window_maxiter':item['window_maxiter'],'eig_tol':item['eig_tol'],'residual_tol':item['residual_tol'],
          'tuning_tol':item['tuning_tol'],'maxiter':item['maxiter'],'max_eig_iter':item['max_eig_iter'],'ncv':item['ncv'],
          'source_sha256':source_sha256,'runtime':runtime()}
    if item.get('local_basis_path'):
        from .local_basis import BASIS_SCHEMA
        want['local_basis']={'mode':'density','schema':BASIS_SCHEMA,'sha256':item['local_basis_sha256']}
    elif cfg.get('local_basis') is not None:
        raise ValueError('Density result cannot complete a legacy lowest-energy-basis item')
    bad={k:(cfg.get(k),v) for k,v in want.items() if cfg.get(k)!=v}
    if bad:raise ValueError(f'{path}: configuration differs from item {item["id"]}: {bad}')
    if not any(abs(cfg['delta']-d)<=1e-12 for d in item['deltas']):raise ValueError(f'{path}: delta {cfg["delta"]} not in item')
    return cfg['delta'],rec['sha256']


def result_stamp(record):
    """Cheap change detector for the files a completion record references."""
    out=[]
    for r in record.get('results',[]):
        try:st=Path(r['path']).stat();out.append((r['path'],st.st_mtime_ns,st.st_size))
        except (OSError,KeyError,TypeError):out.append((str(r.get('path')),None,None))
    return tuple(out)


def results_from_log(text):
    """Result paths reported by the CLI ('completed' or 'reused' JSON lines)."""
    out=[]
    for line in text.splitlines():
        line=line.strip()
        if line.startswith('{') and '"path"' in line:
            try:r=json.loads(line)
            except ValueError:continue
            if r.get('status') in ('completed','reused'):out.append(r['path'])
    return out


def completion(item,paths,source_sha256):
    """Completion record for an item, or ValueError if its results do not cover/validate."""
    seen={}
    for p in paths:
        d,sha=check_record(item,p,source_sha256);seen[round(d,12)]={'path':str(Path(p).resolve()),'delta':d,'record_sha256':sha}
    if sorted(seen)!=sorted(round(d,12) for d in item['deltas']):raise ValueError(f'item {item["id"]}: results do not cover its deltas')
    return {'item':item['id'],'config_digest':item_digest(item),'source_sha256':source_sha256,'runtime':runtime(),
            'results':list(seen.values())}


def completion_valid(item,record,source_sha256):
    """A stored completion record still stands: same numerics and runtime, results present, unchanged and valid."""
    try:
        if record.get('config_digest')!=item_digest(item) or record.get('source_sha256')!=source_sha256 \
           or record.get('runtime')!=runtime():return False
        for r in record['results']:
            d,sha=check_record(item,r['path'],source_sha256)
            if sha!=r['record_sha256'] or abs(d-r['delta'])>1e-12:return False
        return sorted(round(r['delta'],12) for r in record['results'])==sorted(round(d,12) for d in item['deltas'])
    except (OSError,ValueError,KeyError,TypeError):return False
