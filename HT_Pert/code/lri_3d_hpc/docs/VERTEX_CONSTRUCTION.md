# Taylor-vertex construction: profiling, memory, and cluster tasks

The optimized builder preserves the supplied bath-level regulator, scalar
SO(3) basis, inversion sector, analytic Taylor coefficients, and long-double
arithmetic. It provides a streamed single-process build and restartable
independent construction tasks for a cluster. Graph and projector preparation
still require one sufficiently large-memory process.

## Measured bottlenecks and improvements

The measurements below use cutoff **L = 14**, Taylor degree **6**, all four bath
vertices, Python 3.12.14, NumPy 2.5.3, and the same unchanged vendor basis. BLAS,
OpenMP, and Numba thread limits were one. These are fresh-process **profiled**
builds on the available shared execution host, not a multi-node scaling study.
The long-double format on this host has a **64-bit significand**, stored in
16 bytes; NumPy calls the dtype `float128`. No arithmetic was reduced to float64.

| Build | Whole build wall time | Vertex stage | Peak process RSS |
|---|---:|---:|---:|
| Frozen reference, warm Numba cache | 100.265 s | 89.345 s | 1,333,468 KiB |
| Streamed, without persistent CSR layout cache | 109.010 s | 90.907 s | 680,308 KiB |
| Streamed, with CSR layout cache: current default | 92.756 s | 75.609 s | 899,352 KiB |

The default reduced whole-build wall time by about **7.5%** and peak RSS by
about **32.6%** in these runs. Its vertex stage took about **15.4% less time**.
The lower-memory option used about **49.0% less peak RSS** than the warm
reference, with additional conversion work. These are measured observations,
not guaranteed speedups: unchanged projector setup varied from 9.11 s in the
warm reference to 15.18 s in the final optimized run. A separate cold reference
run took 166.47 s, including substantial Numba compilation; that cold time is
not used as the optimization baseline.

The final build used 40.650 s of process CPU time within the measured build,
and 41.546 s of total process CPU time including initialization. The warm
reference recorded 43.981 s of total process CPU time. The CPU/wall difference
also reflects the shared execution environment. RSS is a process measurement;
it does not include the complete kernel page cache used by temporary files.

The profiler identified sparse products and repeated sparse-format conversions
as the main vertex costs. The improvements remove redundant work without
changing nonzero arithmetic:

| Operation | Frozen reference | Final default |
|---|---:|---:|
| Sparse product dispatches in Taylor convolutions | 4,396 | 2,912 |
| Structurally zero products skipped | 0 | 1,484 |
| Nonempty `csr_matmat` kernel calls | 2,898 | 2,898 |
| CSR/CSC conversion-kernel calls | 4,783 | 402 |
| Conversion-kernel time | 11.859 s | 1.731 s |

The expensive nonempty products are still required. Skipping an exact zero
factor avoids dispatch, allocation, and addition work. Caching the required
CSR layouts removes repeated conversion of the same right operand. The final
profile still spends 41.815 s in `csr_matmat`, so further major speedups require
faster or distributed sparse products, or greater task parallelism.

The complete measurements and matrix comparisons are in:

- [Warm reference profile](../benchmarks/baseline_build_L14_warm_profile.json)
- [Streamed build without the layout cache](../benchmarks/optimized_build_L14_stream_profile.json)
- [Final cached-layout build](../benchmarks/optimized_build_L14_cached_stream_profile.json)

## What changed in the builder

For bath particle sectors `pa` and `pb`, the implementation retains the same
ordered Taylor convolution of annihilation images. In each product, the Taylor
index is accumulated in its original increasing order. A multiplication is
skipped only when one sparse operand has **exactly zero stored entries**.
There is no magnitude threshold, sparsification tolerance, or removal of a
physical state.

The default retains the original CSC images for transposed left factors and
caches CSR right factors only for annihilation layers 0, 1, and 2. The quartic
vertex does not require higher right layers. Forward image construction also
reuses CSR results. All products therefore use the same CSR multiplication
kernel and sum order as before; the change avoids repeated layout conversion.
The L = 14 run recorded 227,824,556 bytes of peak cached-layout arrays. Disabling
this cache is useful when process memory is the limiting resource.

When a final store is requested, particle-pair coordinates are appended to
temporary scratch files. The graph, projectors, and annihilation images are
released before final matrix assembly. Only one final matrix is assembled and
written at a time. Hermitian averaging remains exactly
`(W + W.T) * 0.5`, after canonical sparse assembly. No small matrix entry is
clipped.

All 28 final L = 14 matrices, their row pointers, and their column-index arrays
match the trusted previous construction exactly. The numerical differences are
zero at the stored working precision. This refers to floating-point values,
not unused padding bytes in an extended-precision storage word.

## Single-process build and memory choice

The project driver uses streaming by default:

```bash
export HT3D_SCRATCH=/path/to/node-local-scratch
export NUMBA_CACHE_DIR="$HT3D_SCRATCH/numba-cache"

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 \
python code/ht3d_coefficients.py build \
  --cutoff 14 --order 8 \
  --store "$HT3D_SCRATCH/vertices-L14" \
  --spill "$HT3D_SCRATCH"
```

Add `--no-layout-cache` when minimizing peak process memory is more useful
than avoiding repeated sparse conversions. The final store path must be new;
an existing store is never overwritten implicitly. Node-local scratch avoids
placing temporary coordinate traffic on a shared parallel filesystem. Budget
space for the temporary coordinates as well as the final store.

The Python API remains compatible with existing callers:

```python
from taylor_vertices import build_taylor_vertices

N, P, W, metadata = build_taylor_vertices(
    cutoff=14,
    degree=6,
    return_metadata=True,
    store_path="vertices-L14",
    spill_path="scratch",
    cache_layouts=True,
)
```

Without `store_path`, the function returns in-memory CSR matrices.
`spill_path` can still be supplied to reduce temporary coordinate memory in
that case. The matrix objects returned from a store-backed build contain
read-only memory-mapped arrays.

## Independent construction tasks across nodes

`code/taylor_pipeline.py` separates construction into four dependency stages:

1. **Prepare once.** `prepare_vertex_inputs(path, cutoff, degree, dtype, ...)`
   constructs the unchanged graph and projectors, then saves scalar blocks and
   analytic annihilator arrays. This stage is still a single-process setup.
2. **Build particle images independently.**
   `build_particle_images(path, particle, ...)` writes all required annihilation
   images for one bath particle sector. Only adjacent forward layers are kept
   in memory. Different particle tasks may run on different nodes.
3. **Assemble matrix tasks independently.**
   `assemble_vertex_task(path, k, r, ...)` assembles one vertex power `k = 1..4`
   and Taylor degree `r = 0..degree`. Once the image stage is complete, these
   jobs have no dependencies on each other. There are 28 matrix jobs for the
   degree-6 calculation. `cache_layouts=False` is also available here.
4. **Finalize once.** `finalize_vertex_store(path, output_path, ...)` validates
   all matrix tasks and writes the final shared-pattern CSR store.

The corresponding commands are:

```bash
python code/taylor_pipeline.py prepare --path prepared-L14 --cutoff 14 --degree 6
python code/taylor_pipeline.py tasks --path prepared-L14
python code/taylor_pipeline.py images --path prepared-L14 --particle "$HT3D_PARTICLE"
python code/taylor_pipeline.py matrix --path prepared-L14 --k "$HT3D_VERTEX" --r "$HT3D_DEGREE"
python code/taylor_pipeline.py finalize --path prepared-L14 --output vertices-L14
```

Use the task inventory to assign valid particle IDs and matrix indices to a
scheduler. The inventory is authoritative; do not assume every integer particle
sector is present for every possible cutoff. All particle jobs must complete
before the matrix stage starts. Jobs use distinct output directories and
publish their completion manifests last. A task's manifest contains the exact
prepared-input manifest hash, which prevents mixing results from different
preparations. Completed tasks can be retained across a restart after validation;
partial directories are never accepted as completed work.

Task intermediates may be staged on node-local disks, provided that each task
sees the same prepared inputs and completed image directories. The stored array
references are relative filenames. Hash validation should be performed before
using `--trust-staged-arrays`; that option skips file-content checksums only.
Numerical ABI and source compatibility checks remain enabled.

## Store format, precision, and validation

`vertex_store.py` exposes:

```python
from vertex_store import load_vertex_store, save_vertex_store

N, P, W, metadata = load_vertex_store(
    "vertices-L14", mmap_mode="r", cutoff=14, degree=6
)
save_vertex_store("another-new-store", N, P, W, metadata)
```

The format uses uncompressed NumPy `.npy` arrays, with `allow_pickle=False`.
Each matrix has its own data array. Exactly equal index and row-pointer
patterns are stored once and shared on load. The L = 14 output contains
**15 unique patterns**: 341,642,656 bytes of stored array files, versus
374,904,784 bytes when counting every matrix's CSR buffers separately. Sharing
patterns requires exact equality; no approximate sparsity pattern is imposed.

The loader verifies file checksums, recorded array shapes and dtypes, requested
cutoff and Taylor degree, source hashes, and the floating-point representation.
The representation records storage size, significand and exponent properties,
and byte order. Thus an x87 long-double store is rejected on a machine whose
long double is IEEE quadruple precision, even if both use 16-byte arrays.
No implicit narrowing, byte reinterpretation, or precision fallback occurs.
Projector source precision remains float64, exactly as in the inherited code.

Checksums are computed with bounded file-read buffers rather than by copying
all memory-mapped arrays into process memory. Source hashes cover the Taylor
builder, pipeline, store implementation, and unchanged vendor Python sources.
A complete store manifest is published only after all matrices are present.
Corrupted, incomplete, incompatible, and stale stores fail explicitly.

The small fixture in [fixtures/vertices_L4](../fixtures/vertices_L4) contains
L = 4, degree-6 vertices from the final source version. It is convenient for
CLI and restart tests on a matching long-double ABI. Regenerate a small store
locally if the fixture's numerical ABI differs from the target machine.

[The store-validation report](../results/vertex_store_validation.json) records
zero differences against the frozen reference at L = 0, 2, and 4; zero
differences between cached and uncached layouts, streamed loads, and the staged
L = 4 pipeline; read-only mmap verification; and rejection tests for corrupted
checksums, stale sources, mismatched precision, wrong cutoff/degree, incomplete
stores, and missing construction tasks. Reproduce those checks with:

```bash
python tests/check_vertex_store.py
```

## Remaining scaling limits

The full ranked Fock graph and the original species-block SO(3) SVD construction
are unchanged. Their state count grows rapidly with cutoff. Preparation still
requires one process to hold that graph and its projector workspaces, and a
matrix-assembly task still needs the workspace for its own sparse products and
one output matrix. The staged interface distributes independent work; it does
not distribute those individual graph/SVD or sparse-product operations.

The preflight graph-array estimate excludes projectors, SVD workspaces, images,
coordinate files, final vertices, and the solver. Raising `--max-states` or
`--max-bytes` is an explicit resource-budget choice, not a way to reduce the
physical state space. No particle cap, energy-window approximation, or reduced
numerical precision has been introduced. Multi-node speedups should be measured
on the target cluster, particularly when many tasks share filesystem bandwidth.
