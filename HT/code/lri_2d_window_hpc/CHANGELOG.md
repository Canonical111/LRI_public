# 0.2.0rc1 — optimization of the 2D dressed-window research port

## Numerical representation, not physics changes

- Exact integer-ranked circle-bath graph replaces persistent Python occupation
  tuples and lookup dictionaries, preserving original state order and edges.
- New exact sparse annihilation-image/Gram backend; faster projected-tensor backend.
- Cached bath diagonals; batched sparse/local contractions; deterministic row-owned
  multithreading, with rectangular CSR support tested explicitly.
- Ground-only top vacuum iterations, followed by the requested excited roots and
  unchanged acceptance gates. Only exactly identical local matrices reuse a window.
- Cached small dense bare matrices and vectorized level/window lookup.
- Direct projected cross-angular diagnostic operators, avoiding full-space tuples.
- Original dense/ARPACK algorithms, normal ordering, float64, scalar calibration,
  window fixed-point tolerance, and diagnostic ambiguity flags remain.

## Runtime and deployment

- New single-point driver: atomic JSON publication, checksummed input/result
  identity, Newton-boundary checkpoints, fail-closed output claims.
- Frozen independent Slurm-array requests; consumer rechecks the exact input bytes;
  source identity also includes the default seed table.
- Basis dimensions/integer ranges/array allocations checked explicitly; resource
  guards forwarded to all vacuum sub-cutoffs. No automatic problem-size reduction.
- This is not a port of the full 1D reviewed generation-lease/release service, and
  is not yet tested on symmetry. No MPI-distributed eigenproblem or GPU code.

## Validation and provenance

- 16 original independent cases plus 38 new cases; 54 passed locally.
- 62 new benchmark records, independent large-matrix comparisons, and fresh
  original-spectrum checks. All timing records retain their measured source hashes.
- Post-timing guard forwarding and HPC integrity changes are documented separately;
  the shipping tree passed the final tests and a further full-solve replay.
- No fitting-tail, selected-tail, OPE, or physical counterterm research is added.
