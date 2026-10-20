// Precision-preserving sparse kernels for the 3D formal-series solver.
// Compile without -ffast-math, -Ofast, or floating-point contraction.
// Rows are independent: threading never changes an individual row's sum order.
#include <algorithm>
#include <cfloat>
#include <cstdint>
#include <limits>
#include <new>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

extern "C" {
int ht_sparse_abi_version() { return 2; }
int ht_sizeof_long_double() { return static_cast<int>(sizeof(long double)); }
int ht_long_double_mantissa_bits() { return LDBL_MANT_DIG; }
int ht_long_double_max_exp() { return LDBL_MAX_EXP; }
int ht_sizeof_double() { return static_cast<int>(sizeof(double)); }
int ht_double_mantissa_bits() { return DBL_MANT_DIG; }
int ht_floating_radix() { return FLT_RADIX; }
int ht_little_endian() {
    const std::uint16_t one = 1;
    return *reinterpret_cast<const unsigned char*>(&one) == 1;
}
int ht_openmp_enabled() {
#ifdef _OPENMP
    return 1;
#else
    return 0;
#endif
}
int ht_openmp_max_threads() {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}
}

namespace {

template <typename Real, typename Index, typename Pointer>
int spmm(std::int64_t nrows, std::int64_t ncols, std::int64_t nrhs,
         std::int64_t nnz, const Pointer* indptr, const Index* indices,
         const Real* data, const Real* x, Real* y, bool accumulate,
         int threads, bool sorted_indices) {
    int invalid = 0;
    // Allocate outside the OpenMP region so allocation failures can propagate
    // to the C ABI's error handler instead of terminating a worker thread.
#ifdef _OPENMP
    const std::size_t work_threads = static_cast<std::size_t>(threads);
#else
    const std::size_t work_threads = 1;
#endif
    std::vector<Real> temporary;
    if (accumulate) {
        if (static_cast<std::uint64_t>(nrhs) > temporary.max_size() / work_threads)
            return 5;
        temporary.resize(work_threads * static_cast<std::size_t>(nrhs));
    }
    // Each thread owns complete output rows; no reductions of Real values occur.
    // A single small buffer per thread is needed only for accumulate=True.
#pragma omp parallel num_threads(threads) if(threads > 1) reduction(|:invalid)
    {
#ifdef _OPENMP
        const std::size_t thread = static_cast<std::size_t>(omp_get_thread_num());
#else
        const std::size_t thread = 0;
#endif
#pragma omp for schedule(static)
        for (std::int64_t row = 0; row < nrows; ++row) {
            const std::int64_t begin = static_cast<std::int64_t>(indptr[row]);
            const std::int64_t end = static_cast<std::int64_t>(indptr[row + 1]);
            if (begin < 0 || begin > end || end > nnz) {
                invalid |= 1;
                continue;
            }
            Real* result = accumulate ? temporary.data() + thread * nrhs : y + row * nrhs;
            std::fill(result, result + nrhs, Real(0));
            for (std::int64_t k = begin; k < end; ++k) {
                const std::int64_t column = static_cast<std::int64_t>(indices[k]);
                if (column < 0) {
                    invalid |= 1;
                    continue;
                }
                // Prefix cropping is a read-only view of the full CSR matrix.
                // Canonical inputs stop at the prefix boundary; unsorted inputs
                // remain supported, preserving duplicate entries and row order.
                if (column >= ncols) {
                    if (sorted_indices) break;
                    continue;
                }
                const Real a = data[k];
                const Real* input = x + column * nrhs;
                for (std::int64_t rhs = 0; rhs < nrhs; ++rhs)
                    result[rhs] += a * input[rhs];
            }
            if (accumulate) {
                Real* output = y + row * nrhs;
                for (std::int64_t rhs = 0; rhs < nrhs; ++rhs)
                    output[rhs] += result[rhs];
            }
        }
    }
    return invalid ? 4 : 0;
}

template <typename Real>
int dispatch_indices(int index_bits, int pointer_bits,
                     std::int64_t nrows, std::int64_t ncols,
                     std::int64_t nrhs, std::int64_t nnz,
                     const void* indptr, const void* indices,
                     const void* data, const void* x, void* y,
                     bool accumulate, int threads, bool sorted_indices) {
#define HT_DISPATCH(INDEX, POINTER) \
    return spmm<Real, INDEX, POINTER>(nrows, ncols, nrhs, nnz, \
        static_cast<const POINTER*>(indptr), static_cast<const INDEX*>(indices), \
        static_cast<const Real*>(data), static_cast<const Real*>(x), \
        static_cast<Real*>(y), accumulate, threads, sorted_indices)
    if (index_bits == 32 && pointer_bits == 32) {
        HT_DISPATCH(std::int32_t, std::int32_t);
    }
    if (index_bits == 32 && pointer_bits == 64) {
        HT_DISPATCH(std::int32_t, std::int64_t);
    }
    if (index_bits == 64 && pointer_bits == 32) {
        HT_DISPATCH(std::int64_t, std::int32_t);
    }
    if (index_bits == 64 && pointer_bits == 64) {
        HT_DISPATCH(std::int64_t, std::int64_t);
    }
#undef HT_DISPATCH
    return 2;
}

}  // namespace

extern "C" int ht_csr_spmm(
    int real_code, int index_bits, int pointer_bits,
    std::int64_t nrows, std::int64_t ncols, std::int64_t nrhs,
    std::int64_t nnz, const void* indptr, const void* indices,
    const void* data, const void* x, void* y, int accumulate, int threads,
    int sorted_indices) {
    if (nrows < 0 || ncols < 0 || nrhs < 0 || nnz < 0 || threads < 1)
        return 3;
    if (nrows == 0 || nrhs == 0) return 0;
    try {
        if (real_code == 0)
            return dispatch_indices<double>(index_bits, pointer_bits, nrows,
                ncols, nrhs, nnz, indptr, indices, data, x, y,
                accumulate != 0, threads, sorted_indices != 0);
        if (real_code == 1)
            return dispatch_indices<long double>(index_bits, pointer_bits, nrows,
                ncols, nrhs, nnz, indptr, indices, data, x, y,
                accumulate != 0, threads, sorted_indices != 0);
        return 1;
    } catch (const std::bad_alloc&) {
        return 5;
    } catch (...) {
        return 6;
    }
}
