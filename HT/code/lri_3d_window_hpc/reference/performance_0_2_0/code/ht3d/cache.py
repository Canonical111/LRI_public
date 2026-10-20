"""Optional immutable numerical cache; atomic publication, content verification.

The cache contains no couplings, eigenvectors or self-consistent vacuum tables.
It is safe to share geometry and bare vertices between different local sizes at
identical x and cutoff. A private temporary directory is published by atomic
rename on the same filesystem. A corrupt published entry fails closed.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json,os,platform,shutil,tempfile
from functools import lru_cache
import numpy as np
import scipy
import numba

SCHEMA='ht3d-static-arrays-v1'
COUNTERS={'hits':0,'misses':0,'published':0,'races':0}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()

def sparse_hash(matrix):
    """Bind cached vertices to the exact multiplicity-space gauge/order."""
    h=hashlib.sha256()
    h.update(repr(matrix.shape).encode())
    for a in (matrix.indptr,matrix.indices,matrix.data):
        h.update(a.dtype.str.encode());h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()

@lru_cache(maxsize=1)
def implementation():
    p=Path(__file__).resolve().parent
    return {'schema':SCHEMA,'files':{name:file_hash(p/name) for name in
            ('basis.py','rotational_vertices.py','block_vertices.py','operators.py','cache.py')},
            'runtime':{'numpy':np.__version__,'scipy':scipy.__version__,'numba':numba.__version__,
                       'python':platform.python_version(),'machine':platform.machine()}}

class ArrayCache:
    def __init__(self,directory):
        self.root=Path(directory).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def request(self,kind,parameters):
        return {'kind':kind,'parameters':parameters,'implementation':implementation()}
    def path(self,kind,parameters):
        return self.root/(kind+'-'+digest(self.request(kind,parameters)))
    def load(self,kind,parameters):
        dest=self.path(kind,parameters)
        if not dest.exists():COUNTERS['misses']+=1;return None
        try:
            meta=json.loads((dest/'manifest.json').read_text())
            sig=meta.pop('manifest_sha256')
            if sig!=digest(meta) or meta['request']!=self.request(kind,parameters):
                raise ValueError('manifest identity mismatch')
            arrays={}
            for name,record in meta['arrays'].items():
                if not name.isidentifier():raise ValueError('invalid array name')
                p=dest/(name+'.npy')
                if not p.is_file() or file_hash(p)!=record['sha256']:raise ValueError(f'array hash mismatch: {name}')
                a=np.load(p,allow_pickle=False,mmap_mode='r')
                if list(a.shape)!=record['shape'] or a.dtype.str!=record['dtype'] or a.dtype.hasobject:
                    raise ValueError('array shape/dtype mismatch')
                arrays[name]=a
            COUNTERS['hits']+=1
            return arrays,meta.get('metadata',{})
        except (OSError,ValueError,KeyError,TypeError) as e:
            raise ValueError(f'Invalid immutable cache entry {dest}: {e}. Verify offline; do not silently reuse it.') from e
    def save(self,kind,parameters,arrays,metadata=None):
        dest=self.path(kind,parameters)
        # Validate an existing entry instead of overwriting it.
        if dest.exists():self.load(kind,parameters);return
        stage=Path(tempfile.mkdtemp(prefix='.ht3d-building-',dir=self.root))
        try:
            records={}
            for name,arr in arrays.items():
                if not name.isidentifier():raise ValueError('invalid array name')
                a=np.asarray(arr)
                if a.dtype.hasobject:raise ValueError('object arrays not allowed')
                p=stage/(name+'.npy')
                with p.open('wb') as f:
                    np.save(f,a,allow_pickle=False);f.flush();os.fsync(f.fileno())
                records[name]={'sha256':file_hash(p),'shape':list(a.shape),'dtype':a.dtype.str}
            meta={'request':self.request(kind,parameters),'arrays':records,'metadata':metadata or {}}
            meta['manifest_sha256']=digest(meta)
            with (stage/'manifest.json').open('w') as f:
                json.dump(meta,f,sort_keys=True,allow_nan=False);f.flush();os.fsync(f.fileno())
            try:
                stage.rename(dest);COUNTERS['published']+=1
                fd=os.open(self.root,os.O_RDONLY)
                try:os.fsync(fd)
                finally:os.close(fd)
            except OSError:
                if not dest.is_dir():raise
                self.load(kind,parameters);COUNTERS['races']+=1
        finally:
            if stage.exists():shutil.rmtree(stage)
