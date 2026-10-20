"""Atomic uncompressed rank-local basis cache. Disk storage is optional.

.npy files can be memory mapped. The cache is a performance cache, not an
integrity certificate. Invalid schemas/configs/shapes are refused. Store on
node-local scratch for a large campaign, not an overloaded shared filesystem.
"""
import json,os,shutil,tempfile
from pathlib import Path
import numpy as np
from .basis import Edges

SCHEMA=1
ARRAYS=('P','N','C_ptr','C_index','C_mode','C_occ','B_ptr','B_index','B_mode','B_occ')

def key_dir(root,cutoff,pmax,qmax,rank,size):
    return Path(root)/f'basis-v{SCHEMA}-L{cutoff}-P{pmax}-Q{qmax}'/f'rank{rank:06d}-of-{size:06d}'

def load_basis(obj,path):
    path=Path(path);meta_path=path/'metadata.json'
    if not meta_path.exists():return False
    meta=json.loads(meta_path.read_text())
    expected={'schema':SCHEMA,'cutoff':obj.cutoff,'pmax':obj.pmax,'qmax':obj.qmax,'rank':obj.rank,'size':obj.size}
    if any(meta.get(k)!=v for k,v in expected.items()):raise ValueError('Basis cache metadata mismatch')
    arrays={name:np.load(path/(name+'.npy'),mmap_mode='r',allow_pickle=False) for name in ARRAYS}
    for k,a in arrays.items():
        if list(a.shape)!=meta['arrays'][k]['shape'] or str(a.dtype)!=meta['arrays'][k]['dtype']:
            raise ValueError(f'Invalid cached array {k}')
    obj.global_dim=meta['global_dim'];obj.begin=meta['begin'];obj.end=meta['end'];obj.dim=obj.end-obj.begin
    obj.P=arrays['P'];obj.N=arrays['N']
    obj.creation=Edges(*(arrays['C_'+k] for k in ('ptr','index','mode','occ')))
    obj.annihilation=Edges(*(arrays['B_'+k] for k in ('ptr','index','mode','occ')))
    obj.estimated_working_bytes=meta['estimated_working_bytes'];obj.table_bytes=meta['table_bytes']
    return True

def save_basis(obj,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if (path/'metadata.json').exists():return
    temp=Path(tempfile.mkdtemp(prefix=path.name+'.tmp.',dir=path.parent))
    try:
        arrays={'P':obj.P,'N':obj.N}
        for tag,e in [('C',obj.creation),('B',obj.annihilation)]:
            arrays.update({tag+'_'+k:getattr(e,{'ptr':'ptr','index':'index','mode':'mode','occ':'occ'}[k]) for k in ('ptr','index','mode','occ')})
        for k,a in arrays.items():np.save(temp/(k+'.npy'),a,allow_pickle=False)
        meta={'schema':SCHEMA,'cutoff':obj.cutoff,'pmax':obj.pmax,'qmax':obj.qmax,'rank':obj.rank,'size':obj.size,
              'global_dim':obj.global_dim,'begin':obj.begin,'end':obj.end,
              'estimated_working_bytes':obj.estimated_working_bytes,'table_bytes':obj.table_bytes,
              'arrays':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in arrays.items()}}
        (temp/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
        try:os.rename(temp,path)
        except FileExistsError:
            if not (path/'metadata.json').exists():raise
    finally:
        if temp.exists():shutil.rmtree(temp)
