# Reviews of lri_3d_hpc (d = 3 perturbative HT)

Raw review logs and transcripts are not published; this is their summary.

## Code review of the Expanse/symmetry port (Codex, OpenAI GPT-6 astra, effort xhigh; 2026-10-08)

The port (`cluster/` layer and the changes around the solver) was inspected by Codex in 11 rounds against the
package at each fix commit. Rounds 1 to 10 returned REVISE with 1 to 11 findings each; every finding was fixed in the
commit named in `PROVENANCE.md`. Round 11 APPROVED commit `7c8a67e`, the release of the production campaign.

The findings concerned the cluster workflow, not the arithmetic of the solver:

- **Release identity:** tarball authentication before any script is sourced, member-by-member checks against the
  release manifest, receipts bound to the tarball's sha256 and fingerprint (R2, REV-007, REV-008).
- **Result identity:** an existing result or gate is reused only for the exact case and solver source; production
  solves require both cutoff-14 gates of the current store validated against the shipped reference at 5e-13
  (F1, R3, REV-003).
- **Store integrity:** every consuming job re-hashes the store; the verify stage always re-hashes; a padding-free value
  fingerprint of the store (R11, REV-006, REV-009, REV-011, REV-012).
- **Environment identity:** campaigns frozen to the receipt's interpreter, packages, compiler, mpi4py build and the MPI
  runtime libraries by path and sha256 (F2, REV-002, REV-013, REV-016).
- **Comparisons:** crosscheck and MPI comparisons count only with a passing record bound to both results' sha256
  (R1, R4).
- **Scheduler safety:** array semantics, dependency checks against accounting, the Expanse job-count guard, lane stop
  on SIGTERM, memory limits from the whole cgroup chain (F3-F5, R5-R10, REV-001, REV-004, REV-005, REV-010,
  REV-014, REV-015).

None of the findings changed a coefficient: the L14 gates and the 32-case L14 grid were rerun in the validation
receipts of every release on both sites.

## Results

The production results were not reviewed by a separate AI. Their checks are internal and are replayed by
`make replay`:

- the cutoff-14 gate of every production store against the supplier's reference results (scaled error at most
  1.25e-14, tolerance 5e-13);
- the recursion residual of every result (at most 5.1e-19, limit 1e-16);
- the recurrence strategy against the stationary strategy at L = 16 (at most 4.1e-16);
- the L = 16 and 18 coefficients re-solved from the L20 store against the L16 and L18 stores (at most 9.8e-15).

## Not reviewed

- The supplied archive itself (the original calculation and the optimized solver, `14b10e2`) was reviewed only
  through the port: Codex inspected the port's changes and their interaction with the solver, not the derivation of
  the coefficients. The supplier's validation (`results/*.json`) compares the optimized solver with the original code
  for L <= 14.
- This public overlay (`public.mk`, `public/`) was written on 2026-10-14 and was not reviewed by Codex. It reads
  records and runs the package's own checks; it changes nothing in the package.
