# Development findings (not accepted scientific results)

1. A new strong-coupling backend-regression test initially used the generic
   weak-end initial guess at x=.126 and stalled with a large primary residual.
   The existing study already requires branch continuation. The comparison now
   uses the same supplied teacher-coupling seed for every backend. No convergence
   tolerance or physical target was changed; arbitrary-seed global convergence
   is not claimed.
2. Lowering the parallel sparse-work threshold exposed a square-output assumption
   in the inherited CSR kernel: `zeros_like(x)` is wrong for rectangular Gram
   factors. It caused segmentation faults in the unaccepted L16 parallel probes.
   Both serial and parallel kernels now allocate `(n_output_rows, block_width)`.
   Three dedicated tall/wide matrix tests, all-backend tests and the completed
   one/two/four-thread benchmark were rerun after the fix. Crashed probes do not
   enter the released accepted benchmark tables.
3. An initial benchmark orchestration command hit a tool execution limit. The
   final benchmark was launched as one monitored local driver and repeated from
   complete isolated subprocesses. No partial output is accepted or timed as a
   successful run.

These are development/debugging records. They are not new physical corrections,
new continuum values, or a claim of independent external code review.

4. After the timing campaign, resource guards were forwarded to every vacuum
   sub-cutoff and HPC manifests were hardened against default-seed edits, equals-
   form path arguments, invalid array indices and changes between launcher and
   consumer input reads. These changes do not alter the measured default numerical
   equations or contraction kernels. The original per-record benchmark hashes are
   retained; final pytest and an L=12 solve replay check the shipping tree.
