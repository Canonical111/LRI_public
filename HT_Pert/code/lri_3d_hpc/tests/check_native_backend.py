"""Small deterministic correctness fixtures; no performance campaign."""
import argparse
import json
import pathlib
import sys
import warnings

import numpy as np
from scipy.sparse import csr_matrix

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
from native_backend import load_backend, NativeBackendError, precision_metadata


def ordered_reference(matrix, dense, nr, nc):
    out = np.zeros((nr, dense.shape[1]), dtype=dense.dtype)
    for row in range(nr):
        for k in range(matrix.indptr[row], matrix.indptr[row+1]):
            col = matrix.indices[k]
            if col < nc:
                out[row] += matrix.data[k] * dense[col]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', '--native-cache', type=pathlib.Path, default=ROOT/'work/native-cache')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT/'results/native_backend_validation.json')
    args = parser.parse_args()
    cache = args.cache_dir
    # Force requested threads here so the correctness suite still exercises
    # parallel kernels even when production serializes a tiny product.
    backend = load_backend('native', threads=1, cache_dir=cache, serial_work_threshold=0)
    fallback = load_backend('scipy', threads=1)
    rng = np.random.default_rng(52907)
    checks = []
    for dtype in (np.float64, np.longdouble):
        n, nrhs = 31, 10
        # Preserve intentionally unsorted columns and duplicate entries.
        indices = rng.integers(0, n, size=7*n, dtype=np.int32)
        indptr = np.arange(0, 7*n+1, 7, dtype=np.int32)
        data = rng.standard_normal(7*n).astype(dtype)
        data += np.arange(7*n, dtype=dtype) * np.finfo(dtype).eps
        dense = rng.standard_normal((n, nrhs)).astype(dtype)
        for index_type in (np.int32, np.int64):
            for pointer_type in (np.int32, np.int64):
                matrix = csr_matrix((data.copy(), indices.copy(), indptr.copy()), shape=(n,n))
                matrix.indices = indices.astype(index_type)
                matrix.indptr = indptr.astype(pointer_type)
                for arr in (matrix.data, matrix.indices, matrix.indptr):
                    arr.flags.writeable = False
                for nr, nc in ((n,n), (19,19), (7,23), (0,0), (n,0)):
                    x = dense[:nc]
                    ref = ordered_reference(matrix, x, nr, nc)
                    serial = backend.csr_spmm(matrix, x, nrows=nr, ncols=nc)
                    if not np.array_equal(serial, ref):
                        raise AssertionError(('ordered reference mismatch', dtype, index_type, pointer_type, nr, nc))
                    for threads in (2,4):
                        threaded = backend.csr_spmm(matrix, x, nrows=nr, ncols=nc, threads=threads)
                        if not np.array_equal(serial, threaded):
                            raise AssertionError('thread count changed output')
                    scipy = fallback.csr_spmm(matrix, x, nrows=nr, ncols=nc)
                    scale = max(dtype(1), np.max(np.abs(ref), initial=dtype(0)))
                    err = np.max(np.abs(scipy-ref), initial=dtype(0)) / scale
                    if err > 10 * np.finfo(dtype).eps:
                        raise AssertionError(('SciPy mismatch', str(dtype), str(err)))
                    out = np.full(ref.shape, dtype('0.3141592653589793238'), dtype=dtype)
                    expected = out.copy() + ref
                    backend.csr_spmm(matrix, x, nrows=nr, ncols=nc, out=out, accumulate=True)
                    assert np.array_equal(out, expected)
                    checks.append({'dtype':str(np.dtype(dtype)), 'indices_bits':8*np.dtype(index_type).itemsize,
                                   'indptr_bits':8*np.dtype(pointer_type).itemsize, 'nrows':nr, 'ncols':nc,
                                   'scipy_max_scaled_error':str(err)})
        sorted_matrix = matrix.copy()
        sorted_matrix.sort_indices()
        assert sorted_matrix.has_sorted_indices
        for nr, nc in ((19,19), (7,23)):
            x = dense[:nc]
            expected = ordered_reference(sorted_matrix, x, nr, nc)
            for threads in (1,4):
                actual = backend.csr_spmm(sorted_matrix,x,nrows=nr,ncols=nc,threads=threads)
                assert np.array_equal(actual, expected)
            checks.append({'dtype':str(np.dtype(dtype)), 'sorted_prefix':True,
                           'nrows':nr, 'ncols':nc, 'bitwise_reference_agreement':True})
        # A float64 conversion would erase this signal on wider platforms.
        small = dtype(2) ** (-min(60, np.finfo(dtype).nmant))
        mat = csr_matrix((np.array([dtype(1)+small, -1], dtype=dtype),
                          np.array([0,1], dtype=np.int32), np.array([0,2],dtype=np.int32)), shape=(1,2))
        actual = backend.csr_spmm(mat, np.ones((2,3), dtype=dtype))
        assert np.all(actual == small), (str(dtype), actual, small)
        # Non-contiguous vectors are copied, not reinterpreted.
        mat = csr_matrix(np.eye(4, dtype=dtype))
        x = np.arange(24,dtype=dtype).reshape(4,6)[:,::2]
        assert not x.flags.c_contiguous
        assert np.array_equal(backend.csr_spmm(mat,x), x)
        try:
            backend.csr_spmm(mat, np.ones((4,3),dtype=np.float32))
        except TypeError:
            pass
        else:
            raise AssertionError('Implicit dtype change was accepted')
        x = np.ones((4,3),dtype=dtype)
        try:
            backend.csr_spmm(mat,x,out=x)
        except ValueError:
            pass
        else:
            raise AssertionError('Aliased output was accepted')
    # Auto may fall back if a compiler is absent; explicit native must fail.
    with warnings.catch_warnings(record=True) as caught:
        bad = load_backend('auto', cache_dir=cache/'absent', compiler='definitely-no-cxx-here')
        assert bad.backend_name == 'scipy' and caught
    try:
        load_backend('native', cache_dir=cache/'absent', compiler='definitely-no-cxx-here')
    except NativeBackendError:
        pass
    else:
        raise AssertionError('Explicit native did not fail for missing compiler')
    policy_checks = []
    threshold_backend = load_backend('native', threads=4, cache_dir=cache,
                                     serial_work_threshold=10000)
    matrix = csr_matrix(np.eye(4, dtype=np.longdouble))
    x = np.ones((4,3),dtype=np.longdouble)
    assert np.array_equal(threshold_backend.csr_spmm(matrix,x),x)
    policy = threshold_backend.metadata['thread_policy']
    assert policy['requested_thread_calls'] == {'4':1}
    assert policy['effective_thread_calls'] == {'1':1}
    assert policy['serial_dispatch_calls'] == int(bool(threshold_backend.metadata['openmp_enabled']))
    policy_checks.append({'tiny_serial_dispatch':True, 'policy':json.loads(json.dumps(policy))})
    matrix = csr_matrix(np.eye(101,dtype=np.longdouble))
    x = np.ones((101,100),dtype=np.longdouble)
    assert np.array_equal(threshold_backend.csr_spmm(matrix,x),x)
    if threshold_backend.metadata['openmp_enabled']:
        assert policy['effective_thread_calls']['4'] == 1
    else:
        assert policy['effective_thread_calls']['1'] == 2
    policy_checks.append({'above_threshold_parallel_dispatch':True})
    prefix_backend = load_backend('native',threads=4,cache_dir=cache,serial_work_threshold=100)
    matrix = csr_matrix(np.ones((1,40),dtype=np.longdouble))
    x = np.ones((1,3),dtype=np.longdouble)
    assert np.array_equal(prefix_backend.csr_spmm(matrix,x,nrows=1,ncols=1),x)
    # The stored-row bound is 120, despite the actual retained work being 3.
    actual = '4' if prefix_backend.metadata['openmp_enabled'] else '1'
    assert prefix_backend.metadata['thread_policy']['effective_thread_calls'] == {actual:1}
    policy_checks.append({'prefix_work_estimate_is_conservative':True})
    payload = {'pass':True, 'fixtures':len(checks), 'exact_value_thread_invariance':True,
               'comparison_method':'np.array_equal compares floating values exactly; unspecified longdouble storage-padding bytes are not compared',
               'precision':precision_metadata(), 'backend':backend.metadata, 'checks':checks,
               'thread_policy_checks':policy_checks}
    destination = args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'pass':True,'fixtures':len(checks),'backend':backend.backend_name,
                      'longdouble':precision_metadata()['longdouble'], 'result':str(destination)}))


if __name__ == '__main__':
    main()
