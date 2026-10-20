"""Portable, validated NumPy-array storage for Taylor bath vertices.

Each sparse matrix uses uncompressed .npy arrays, so read-only loads can share
the operating system page cache across processes.  Equal CSR sparsity patterns
are stored once.  No pickle is read, no tolerance is applied, and floating-point
arrays are never narrowed.  A complete manifest is published last.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

import numpy as np
from scipy.sparse import csr_matrix, csc_matrix


FORMAT = "ht3d-taylor-csr-npy-v1"


def precision_fingerprint(dtype):
    """Distinguish, in particular, x87 and IEEE-quad long-double storage."""
    dt = np.dtype(dtype)
    if dt.kind != 'f':
        raise ValueError('Vertex precision must be a floating-point dtype')
    f = np.finfo(dt)
    return dict(dtype=dt.str, itemsize=dt.itemsize, nmant=int(f.nmant),
                nexp=int(f.nexp), maxexp=int(f.maxexp), byteorder=sys.byteorder)


def source_fingerprints():
    """Hash the builder and inherited basis implementation, not their path."""
    vendor = Path(__file__).resolve().parents[1] / 'vendor' / 'ht3d'
    if not vendor.is_dir():
        import ht3d.basis
        vendor = Path(ht3d.basis.__file__).parent
    files = {'taylor_vertices.py': Path(__file__).with_name('taylor_vertices.py'),
             'taylor_pipeline.py': Path(__file__).with_name('taylor_pipeline.py'),
             'vertex_store.py': Path(__file__)}
    files.update({'ht3d/' + p.name: p for p in vendor.glob('*.py')})
    return {name: sha256_file(path) for name, path in sorted(files.items())}


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as src:
        for block in iter(lambda: src.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def _jsonable(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def atomic_json(path, value):
    """Atomic single-file publication; caller owns the containing directory."""
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temp.open('x', encoding='utf8') as out:
            json.dump(value, out, indent=2, sort_keys=True, default=_jsonable,
                      allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def save_array(path, array):
    """Save without dtype conversion; include integrity and shape metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as out:
        np.save(out, np.asarray(array), allow_pickle=False)
    return dict(file=path.name, sha256=sha256_file(path),
                dtype=np.asarray(array).dtype.str,
                shape=list(np.asarray(array).shape), bytes=int(path.stat().st_size))


def load_array(folder, record, mmap_mode='r', verify=True):
    """Load an explicitly recorded relative file, rejecting path traversal."""
    name = record['file']
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError('Invalid array filename in vertex store')
    path = Path(folder) / name
    if verify and sha256_file(path) != record['sha256']:
        raise ValueError(f'Array checksum mismatch: {path}')
    a = np.load(path, mmap_mode=mmap_mode, allow_pickle=False)
    if list(a.shape) != record['shape'] or a.dtype.str != record['dtype']:
        raise ValueError(f'Array dtype/shape mismatch: {path}')
    return a


def save_sparse(folder, matrix, prefix='matrix', format='csr'):
    """Write one sparse matrix, for independent intermediate build tasks."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if format not in ('csr', 'csc'):
        raise ValueError('Sparse format must be csr or csc')
    matrix = matrix.tocsr(copy=False) if format == 'csr' else matrix.tocsc(copy=False)
    return dict(format=format, shape=list(matrix.shape),
                data=save_array(folder / (prefix + '.data.npy'), matrix.data),
                indices=save_array(folder / (prefix + '.indices.npy'), matrix.indices),
                indptr=save_array(folder / (prefix + '.indptr.npy'), matrix.indptr))


def load_sparse(folder, record, mmap_mode='r', verify=True):
    cls = {'csr': csr_matrix, 'csc': csc_matrix}.get(record['format'])
    if cls is None:
        raise ValueError('Unsupported sparse format')
    data = load_array(folder, record['data'], mmap_mode, verify)
    indices = load_array(folder, record['indices'], mmap_mode, verify)
    indptr = load_array(folder, record['indptr'], mmap_mode, verify)
    matrix = cls((data, indices, indptr), shape=record['shape'], copy=False)
    # scipy may narrow small int64 index arrays.  Keep the actual stored buffers
    # so a mmap load is genuinely zero-copy for both index widths.
    matrix.data, matrix.indices, matrix.indptr = data, indices, indptr
    return matrix


def _pattern_hash(matrix):
    h = hashlib.sha256()
    for a in (matrix.indices, matrix.indptr):
        h.update(a.dtype.str.encode('ascii'))
        h.update(memoryview(np.ascontiguousarray(a)).cast('B'))
    h.update(str(matrix.shape).encode('ascii'))
    return h.hexdigest()


class VertexStoreWriter:
    """Incremental, transactional writer; target must not already exist.

    A caller may add matrices in any order.  Each k=1..4, r=0..degree entry must
    be supplied exactly once before finish().  Readers cannot see a partial
    target, and independent jobs should use distinct task output directories.
    """
    def __init__(self, path, N, P, cutoff, degree, dtype, metadata=None):
        self.path = Path(path).resolve()
        if self.path.exists():
            raise FileExistsError(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stage = Path(tempfile.mkdtemp(prefix=self.path.name + '.partial-',
                                           dir=self.path.parent))
        self.degree = int(degree)
        self.n = len(N)
        self.dtype = np.dtype(dtype)
        self.patterns = {}
        self.matrices = {}
        self.done = False
        self.base = dict(format=FORMAT, cutoff=int(cutoff), degree=self.degree,
                         precision=precision_fingerprint(dtype),
                         source_hashes=source_fingerprints(),
                         N=save_array(self.stage / 'N.npy', N),
                         P=save_array(self.stage / 'P.npy', P),
                         metadata=dict(metadata or {}))

    def add(self, k, r, matrix):
        k, r = int(k), int(r)
        if not (1 <= k <= 4 and 0 <= r <= self.degree):
            raise ValueError('Matrix index out of range')
        key = f'{k}:{r}'
        if key in self.matrices:
            raise ValueError('Matrix already written: ' + key)
        matrix = matrix.tocsr(copy=False)
        if matrix.shape != (self.n, self.n) or matrix.dtype != self.dtype:
            raise ValueError('Matrix shape/precision does not match store')
        ph = _pattern_hash(matrix)
        if ph not in self.patterns:
            tag = 'pattern-' + ph
            self.patterns[ph] = dict(
                indices=save_array(self.stage / (tag + '.indices.npy'), matrix.indices),
                indptr=save_array(self.stage / (tag + '.indptr.npy'), matrix.indptr))
        self.matrices[key] = dict(shape=list(matrix.shape), pattern=ph,
                                 data=save_array(self.stage / f'W{k}_{r}.data.npy', matrix.data))

    def finish(self, metadata=None):
        expected = {f'{k}:{r}' for k in range(1, 5) for r in range(self.degree + 1)}
        if set(self.matrices) != expected:
            raise ValueError('Incomplete vertex store')
        if metadata:
            self.base['metadata'].update(metadata)
        self.base.update(patterns=self.patterns, matrices=self.matrices,
                         stored_array_bytes=sum(p.stat().st_size
                                                for p in self.stage.glob('*.npy')))
        atomic_json(self.stage / 'manifest.json', self.base)
        if self.path.exists():
            raise FileExistsError(self.path)
        os.rename(self.stage, self.path)
        self.done = True
        return self.path

    def abort(self):
        if not self.done:
            shutil.rmtree(self.stage, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.done:
            self.abort()


def save_vertex_store(path, N, P, W, metadata=None, *, cutoff=None, degree=None):
    """Save existing coefficients without changing their array values."""
    metadata = dict(metadata or {})
    cutoff = metadata.get('cutoff') if cutoff is None else cutoff
    degree = len(W[0]) - 1 if degree is None else int(degree)
    if cutoff is None:
        raise ValueError('cutoff is required, explicitly or in metadata')
    if len(W) != 4 or any(len(row) != degree + 1 for row in W):
        raise ValueError('Expected four complete Taylor vertex series')
    with VertexStoreWriter(path, N, P, cutoff, degree, W[0][0].dtype, metadata) as out:
        for k, series in enumerate(W, 1):
            for r, matrix in enumerate(series):
                out.add(k, r, matrix)
        out.finish()
    return Path(path)


def load_vertex_store(path, mmap_mode='r', cutoff=None, degree=None, *,
                      verify=True, check_sources=True):
    """Return (N, P, W, metadata), with array-backed read-only CSR by default.

    Checksums and numerical ABI are checked before use.  Source hashes are also
    checked by default; disabling that check is an explicit cache compatibility
    decision, never a silent fallback.  ``verify=False`` skips file hashing only
    (useful after a separate verified staging step), not shape/ABI/source checks.
    Requested degree must match the stored Taylor truncation exactly.
    """
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    if manifest.get('format') != FORMAT:
        raise ValueError('Unsupported vertex store format')
    if cutoff is not None and int(cutoff) != manifest['cutoff']:
        raise ValueError('Stored cutoff does not match request')
    if degree is not None and int(degree) != manifest['degree']:
        raise ValueError('Stored Taylor degree does not match request')
    dtype = np.dtype(manifest['precision']['dtype'])
    if precision_fingerprint(dtype) != manifest['precision']:
        raise ValueError('Stored floating-point format is incompatible with this machine')
    if check_sources and manifest['source_hashes'] != source_fingerprints():
        raise ValueError('Vertex cache source hashes do not match this code')
    N = load_array(path, manifest['N'], mmap_mode, verify)
    P = load_array(path, manifest['P'], mmap_mode, verify)
    if N.ndim != 1 or P.shape != N.shape:
        raise ValueError('Invalid basis metadata shape')
    patterns = {}
    for key, record in manifest['patterns'].items():
        patterns[key] = (load_array(path, record['indices'], mmap_mode, verify),
                         load_array(path, record['indptr'], mmap_mode, verify))
    W = []
    for k in range(1, 5):
        series = []
        for r in range(manifest['degree'] + 1):
            record = manifest['matrices'][f'{k}:{r}']
            data = load_array(path, record['data'], mmap_mode, verify)
            indices, indptr = patterns[record['pattern']]
            if record['shape'] != [len(N), len(N)] or data.dtype != dtype:
                raise ValueError('Invalid matrix shape or precision')
            if len(data) != len(indices) or len(indptr) != len(N) + 1:
                raise ValueError('Invalid CSR buffer lengths')
            if int(indptr[0]) != 0 or int(indptr[-1]) != len(data):
                raise ValueError('Invalid CSR row pointers')
            matrix = csr_matrix((data, indices, indptr), shape=record['shape'], copy=False)
            matrix.data, matrix.indices, matrix.indptr = data, indices, indptr
            series.append(matrix)
        W.append(series)
    metadata = dict(manifest['metadata'])
    metadata.update(vertex_store=str(path.resolve()), store_format=FORMAT,
                    store_array_bytes=manifest['stored_array_bytes'],
                    unique_sparse_patterns=len(patterns),
                    precision=manifest['precision'], store_verified=bool(verify))
    return N, P, W, metadata
