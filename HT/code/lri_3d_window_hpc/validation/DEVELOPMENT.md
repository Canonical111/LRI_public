# Development record and rejected optimizations

Only finalized numerical operators are used for the headline comparisons. Timed
processes are serial; data contain actual source hashes rather than rewritten
fingerprints. Early full-root results are retained under
`results/development/full_root_ablation/` as an intermediate implementation, not
combined with final-release speed claims.

1. The initial north-pole CSR builder shared graph index arrays and then called
   eliminate_zeros, mutating the underlying graph. Independent projector tests
   detected this immediately. The final builder allocates its own compact CSR
   buffers; graph immutability and all magnetic sectors are tested.
2. A contiguous one-thread local contraction and a previously available fully
   fused local/sparse action were slower on the tested problems. The original
   serial local contraction remains active at one thread. Repacking is used only
   for sufficiently large threaded operations.
3. A preliminary L12 profiled subprocess exceeded its execution allowance and did
   not produce an accepted result. Final workers explicitly set environment and
   threadpoolctl BLAS limits before measurement. The interrupted attempt is not a
   timing or numerical success.
4. Early profiles included compiler warmup or intermediate source stages. Only
   final fresh-process warmed profiles are interpreted in PERFORMANCE.md. Earlier
   profiles, where retained, are labelled development evidence.
5. Concurrent cache publication originally could leave a writer's local SVD gauge
   different from the published projector. Final code reloads the published winner
   and additionally binds vertex keys to the exact projector arrays. Cache tests
   include deliberate gauge changes and competing writers.

No issue was resolved by changing the physical Hamiltonian, float precision,
normal-ordering rule, field/rotation symmetry, rank of the retained Hilbert space,
nullspace tolerance, or numerical acceptance threshold. Final test/benchmark
inventories specify which checks were actually run.

Two foreground validation invocations exceeded the tool execution allowance. No
partial output from them was treated as passing. The complete numerical
checks were rerun as locally monitored subprocesses, with progress logs; both
original/Gram/weak tests and the larger latest-reference/retuned angular tests
completed successfully. Progress-print and BLAS-control changes were in the
validation driver only, not timed numerical modules.
