"""Optional OpenMP CSR kernels with the same precision as the NumPy inputs.

``load_backend('auto', threads=4)`` builds the included C++ source locally and
checks its floating-point ABI before use. Compiler failure selects SciPy;
``load_backend('native')`` instead fails explicitly. ``'scipy'`` never compiles.
The native path can read the leading principal block of a larger (including
read-only memory-mapped) CSR matrix without allocating a CSR slice.

The compiler flags deliberately exclude fast-math, CPU-specific instruction
selection, and fused multiply-add contraction. OpenMP divides output rows only,
so changing the thread count does not change a row's summation order. Long
double means the platform's NumPy long-double precision, verified against the
compiled ``long double`` representation; it is not a promise of IEEE binary128.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import warnings

import numpy as np


class NativeBackendError(RuntimeError):
    """The optional compiler, library, or floating-point ABI is unavailable."""


_SOURCE = Path(__file__).with_name('native_kernels.cpp')
_LOADED: dict[tuple, tuple[ctypes.CDLL, dict]] = {}
_LOAD_LOCK = threading.Lock()
_FLAGS = ('-O3', '-std=c++17', '-fPIC', '-shared',
          '-fno-fast-math', '-ffp-contract=off')


def precision_metadata() -> dict:
    """Portable description also suitable for numerical cache manifests."""
    ans = {'byteorder': sys.byteorder}
    for name, dtype in [('float64', np.float64), ('longdouble', np.longdouble)]:
        f = np.finfo(dtype)
        ans[name] = {'dtype': str(np.dtype(dtype)),
                     'itemsize': np.dtype(dtype).itemsize,
                     'mantissa_bits': int(f.nmant) + 1,
                     'max_exp': int(f.maxexp)}
    return ans


def _cache_root(cache_dir) -> Path:
    if cache_dir is not None:
        return Path(cache_dir).expanduser().resolve()
    # HPC jobs may set this to node-local scratch. It is never a source tree.
    explicit = os.environ.get('HT3D_NATIVE_CACHE')
    if explicit:
        return Path(explicit).expanduser().resolve()
    base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    return base / 'lri_3d_hpc' / 'native'


def _compiler_command(compiler) -> tuple[list[str], str]:
    cmd = shlex.split(compiler or os.environ.get('CXX', 'c++'))
    if not cmd:
        raise NativeBackendError('The C++ compiler command is empty')
    try:
        version = subprocess.run(cmd + ['--version'], check=True,
                                 capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        raise NativeBackendError(f'Cannot run C++ compiler {cmd!r}: {exc}') from exc
    return cmd, (version.stdout + version.stderr).strip()


def _bind_and_check(path: Path) -> tuple[ctypes.CDLL, dict]:
    try:
        lib = ctypes.CDLL(str(path))
    except OSError as exc:
        raise NativeBackendError(f'Cannot load native kernel {path}: {exc}') from exc
    names = ('sparse_abi_version', 'sizeof_long_double', 'long_double_mantissa_bits',
             'long_double_max_exp', 'sizeof_double', 'double_mantissa_bits',
             'floating_radix', 'little_endian', 'openmp_enabled', 'openmp_max_threads')
    info = {}
    for name in names:
        fn = getattr(lib, 'ht_' + name)
        fn.argtypes, fn.restype = [], ctypes.c_int
        info[name] = int(fn())
    precision = precision_metadata()
    expected = {
        'sparse_abi_version': 2,
        'sizeof_long_double': precision['longdouble']['itemsize'],
        'long_double_mantissa_bits': precision['longdouble']['mantissa_bits'],
        'long_double_max_exp': precision['longdouble']['max_exp'],
        'sizeof_double': precision['float64']['itemsize'],
        'double_mantissa_bits': precision['float64']['mantissa_bits'],
        'floating_radix': 2,
        'little_endian': int(sys.byteorder == 'little'),
    }
    mismatch = {key: {'compiled': info[key], 'numpy_expected': value}
                for key, value in expected.items() if info[key] != value}
    if mismatch:
        raise NativeBackendError('Native floating-point ABI mismatch: ' + json.dumps(mismatch))
    lib.ht_csr_spmm.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.ht_csr_spmm.restype = ctypes.c_int
    info['numpy_precision'] = precision
    return lib, info


def _build_variant(cache_root, cmd, banner, openmp):
    flags = list(_FLAGS) + (['-fopenmp'] if openmp else [])
    source_bytes = _SOURCE.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    build = {'source_sha256': source_hash, 'compiler_command': cmd,
             'compiler_version': banner, 'compiler_flags': flags,
             'platform': platform.platform(), 'machine': platform.machine(),
             'numpy_precision': precision_metadata()}
    key = hashlib.sha256(json.dumps(build, sort_keys=True).encode()).hexdigest()[:24]
    target = cache_root / ('ht_sparse_' + key + '.so')
    started = time.perf_counter()
    cache_root.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        # One compiler per shared cache. An interrupted process releases flock;
        # finished libraries are atomically published, never partially loaded.
        try:
            import fcntl
        except ImportError as exc:
            raise NativeBackendError('This compiler backend requires a POSIX platform') from exc
        with (cache_root / ('ht_sparse_' + key + '.lock')).open('a+b') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if not target.exists():
                with tempfile.TemporaryDirectory(prefix='ht_sparse_build_', dir=cache_root) as scratch:
                    destination = Path(scratch) / target.name
                    command = cmd + flags + [str(_SOURCE), '-o', str(destination)]
                    try:
                        proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
                    except (OSError, subprocess.SubprocessError) as exc:
                        raise NativeBackendError(f'C++ build failed: {exc}') from exc
                    if proc.returncode:
                        raise NativeBackendError('C++ build failed: ' +
                            (proc.stderr or proc.stdout)[-8000:])
                    # Refuse incompatible output before publishing to other jobs.
                    _bind_and_check(destination)
                    os.replace(destination, target)
    lib, abi = _bind_and_check(target)
    build.update(abi)
    build.update({'shared_library': str(target),
                  'load_or_build_seconds': time.perf_counter() - started})
    return lib, build


def _load_native(cache_dir=None, compiler=None, openmp=True):
    cache_root = _cache_root(cache_dir)
    key = (str(cache_root), compiler or os.environ.get('CXX', 'c++'), bool(openmp))
    with _LOAD_LOCK:
        if key in _LOADED:
            return _LOADED[key]
        try:
            cmd, banner = _compiler_command(compiler)
            try:
                result = _build_variant(cache_root, cmd, banner, bool(openmp))
            except NativeBackendError as exc:
                if not openmp:
                    raise
                result = _build_variant(cache_root, cmd, banner, False)
                result[1]['openmp_build_failure'] = str(exc)
        except (OSError, subprocess.SubprocessError) as exc:
            raise NativeBackendError(f'Native backend setup failed: {exc}') from exc
        _LOADED[key] = result
        return result


def _validate_inputs(matrix, dense, nrows, ncols, out, accumulate):
    if getattr(matrix, 'format', None) != 'csr' or len(matrix.shape) != 2:
        raise TypeError('matrix must be a SciPy CSR matrix or CSR array')
    x = np.asarray(dense)
    if x.ndim != 2:
        raise ValueError('dense must be two-dimensional (bath rows, right-hand sides)')
    if ((nrows is not None and int(nrows) != nrows) or
            (ncols is not None and int(ncols) != ncols)):
        raise ValueError('CSR prefix dimensions must be integers')
    nrows = matrix.shape[0] if nrows is None else int(nrows)
    ncols = x.shape[0] if ncols is None else int(ncols)
    if not 0 <= nrows <= matrix.shape[0] or not 0 <= ncols <= matrix.shape[1]:
        raise ValueError('Requested CSR prefix is outside matrix.shape')
    if x.shape[0] != ncols:
        raise ValueError('dense.shape[0] must equal ncols')
    dtype = np.dtype(matrix.dtype)
    if dtype not in (np.dtype(np.float64), np.dtype(np.longdouble)) or not dtype.isnative:
        raise TypeError('Only native-endian float64 and longdouble are supported')
    if x.dtype != dtype:
        raise TypeError('CSR and dense dtypes must match; implicit precision changes are forbidden')
    for name in ('indptr', 'indices'):
        arr = getattr(matrix, name)
        if arr.dtype not in (np.dtype(np.int32), np.dtype(np.int64)) or not arr.dtype.isnative:
            raise TypeError(f'{name} must contain native-endian int32 or int64')
        if arr.ndim != 1 or not arr.flags.c_contiguous or not arr.flags.aligned:
            raise ValueError(f'{name} must be a contiguous aligned vector')
    if matrix.data.ndim != 1 or not matrix.data.flags.c_contiguous or not matrix.data.flags.aligned:
        raise ValueError('CSR data must be a contiguous aligned vector')
    if len(matrix.indptr) != matrix.shape[0] + 1 or len(matrix.indices) != len(matrix.data):
        raise ValueError('Invalid CSR buffer lengths')
    if int(matrix.indptr[0]) != 0 or int(matrix.indptr[-1]) != len(matrix.data):
        raise ValueError('Invalid CSR row-pointer endpoints')
    x = np.require(x, dtype=dtype, requirements=['C', 'A'])
    shape = (nrows, x.shape[1])
    if out is None:
        y = np.zeros(shape, dtype=dtype) if accumulate else np.empty(shape, dtype=dtype)
    else:
        y = np.asarray(out)
        if y.shape != shape or y.dtype != dtype:
            raise ValueError('out shape and dtype must match the CSR product')
        if not y.flags.c_contiguous or not y.flags.aligned or not y.flags.writeable:
            raise ValueError('out must be a writable, contiguous, aligned array')
        if (np.shares_memory(y, x) or any(np.shares_memory(y, arr)
                for arr in (matrix.data, matrix.indices, matrix.indptr))):
            raise ValueError('out may not alias dense or any CSR buffer')
    return x, y, nrows, ncols


class SparseBackend:
    """Reusable per-solver sparse backend; no process-global thread changes."""

    def __init__(self, name='auto', threads=1, cache_dir=None, compiler=None,
                 openmp=True, serial_work_threshold=None):
        if name not in ('auto', 'native', 'scipy'):
            raise ValueError('backend must be auto, native, or scipy')
        if int(threads) != threads or int(threads) < 1:
            raise ValueError('threads must be a positive integer')
        if serial_work_threshold is None:
            serial_work_threshold = int(os.environ.get('HT3D_SERIAL_WORK_THRESHOLD', '10000'))
        if (int(serial_work_threshold) != serial_work_threshold or
                int(serial_work_threshold) < 0):
            raise ValueError('serial_work_threshold must be a nonnegative integer')
        self.threads = int(threads)
        self.serial_work_threshold = int(serial_work_threshold)
        self.lib = None
        self.metadata = {'requested_backend': name, 'threads': self.threads,
                         'numpy_precision': precision_metadata(),
                         'thread_policy': {
                             'serial_work_threshold': self.serial_work_threshold,
                             'work_metric': 'stored prefix nonzeros times right-hand sides; upper bound before column cropping',
                             'thread_counts_meaning': 'num_threads arguments before and after dispatch; the OpenMP runtime may further limit a team',
                             'requested_thread_calls': {},
                             'effective_thread_calls': {},
                             'serial_dispatch_calls': 0}}
        if name != 'scipy':
            try:
                self.lib, meta = _load_native(cache_dir, compiler, openmp)
                self.metadata.update(meta)
            except NativeBackendError as exc:
                if name == 'native':
                    raise
                self.metadata['native_unavailable_reason'] = str(exc)
                warnings.warn('Native sparse backend unavailable; using unchanged-precision '
                              f'SciPy: {exc}', RuntimeWarning, stacklevel=2)
        if self.lib is None:
            self.backend_name = 'scipy'
        else:
            self.backend_name = ('native-openmp' if self.metadata['openmp_enabled']
                                 else 'native-serial')
            if self.threads > 1 and not self.metadata['openmp_enabled']:
                warnings.warn('The compiler lacks OpenMP support; native kernels run serially',
                              RuntimeWarning, stacklevel=2)
        self.name = self.backend_name
        self.metadata['backend'] = self.backend_name

    def csr_spmm(self, matrix, dense, *, nrows=None, ncols=None,
                 threads=None, out=None, accumulate=False):
        """Return ``matrix[:nrows,:ncols] @ dense`` without a native CSR copy.

        Optional ``out`` is reused. ``accumulate=True`` adds the completed
        product to ``out``, matching separate matrix multiplication and addition.
        CSR buffers are never modified; unsorted indices and duplicates retain
        their input order. Dense strided inputs may require a contiguous copy.

        Very small products run serially when their work upper bound is below
        ``serial_work_threshold`` (default 10,000 nonzeros times right-hand
        sides). Set the threshold to zero to disable this policy. Per-call
        requested/effective thread counts are recorded in backend metadata.
        """
        x, y, nr, nc = _validate_inputs(matrix, dense, nrows, ncols, out, accumulate)
        nth = self.threads if threads is None else threads
        if int(nth) != nth or int(nth) < 1:
            raise ValueError('threads must be a positive integer')
        requested = int(nth)
        effective = requested if self.lib is not None and self.metadata['openmp_enabled'] else 1
        policy = self.metadata['thread_policy']
        if (effective > 1 and self.serial_work_threshold and
                int(matrix.indptr[nr]) * x.shape[1] < self.serial_work_threshold):
            # Counting all stored columns is a conservative O(1) upper bound:
            # no scan or CSR slice is introduced just to decide how to thread.
            effective = 1
            policy['serial_dispatch_calls'] += 1
        requested_counts = policy['requested_thread_calls']
        requested_counts[str(requested)] = requested_counts.get(str(requested), 0) + 1
        effective_counts = policy['effective_thread_calls']
        effective_counts[str(effective)] = effective_counts.get(str(effective), 0) + 1
        if self.lib is None:
            m = matrix if (nr, nc) == matrix.shape else matrix[:nr, :nc]
            product = m @ x
            if accumulate:
                y += product
            else:
                y[...] = product
            return y
        code = 0 if x.dtype == np.dtype(np.float64) else 1
        status = self.lib.ht_csr_spmm(code, matrix.indices.dtype.itemsize * 8,
            matrix.indptr.dtype.itemsize * 8, nr, nc, x.shape[1], len(matrix.data),
            matrix.indptr.ctypes.data, matrix.indices.ctypes.data,
            matrix.data.ctypes.data, x.ctypes.data, y.ctypes.data,
            int(bool(accumulate)), effective, int(bool(matrix.has_sorted_indices)))
        if status:
            error = {1: 'Unsupported real dtype', 2: 'Unsupported CSR index dtype',
                     3: 'Invalid dimensions or thread count', 4: 'Invalid CSR structure',
                     5: 'Native temporary allocation failed', 6: 'Native kernel exception'}
            raise NativeBackendError(error.get(status, f'Native kernel error {status}'))
        return y


def load_backend(name='auto', *, threads=1, cache_dir=None, compiler=None,
                 openmp=True, serial_work_threshold=None):
    """Create a solver backend. ``auto`` falls back; ``native`` requires success.

    ``serial_work_threshold`` defaults to ``HT3D_SERIAL_WORK_THRESHOLD`` or
    10,000 when that environment variable is absent. Zero disables the policy.
    """
    return SparseBackend(name, threads, cache_dir, compiler, openmp, serial_work_threshold)


def available(*, cache_dir=None, compiler=None, openmp=True):
    """Check whether a compatible native library can be loaded or built."""
    try:
        _load_native(cache_dir, compiler, openmp)
        return True
    except NativeBackendError:
        return False


def csr_spmm(matrix, dense, *, nrows=None, ncols=None, threads=1,
             out=None, accumulate=False, backend='auto', cache_dir=None,
             serial_work_threshold=None):
    """Convenience interface; solvers should reuse a ``SparseBackend`` instance."""
    obj = (backend if isinstance(backend, SparseBackend)
           else load_backend(backend, threads=threads, cache_dir=cache_dir,
                             serial_work_threshold=serial_work_threshold))
    return obj.csr_spmm(matrix, dense, nrows=nrows, ncols=ncols, threads=threads,
                        out=out, accumulate=accumulate)
