# Consolidation verification report

## Current status

The standalone main note has **60 pages**. The last supported result is the full
numerical eighth thermal coefficient and its proposed compact zeta expression.
The **complete analytic C8 period reduction has not been proved**. This package
does not convert numerical recognition or repeated integration into a certificate.

## Fresh checks performed for this distribution

All of the following actually executed successfully during consolidation:

1. Complete C5/D3 certificate, including 170 target words and 476 rational source rows.
2. Complete C6 certificate: 1,945 target words and 56,381 source rows.
3. Independent reconstruction of the C6 certificate target from the archived beta inputs.
4. Independent reconstruction of the C7 target from the 25 archived beta inputs.
5. Complete C7 free-word certificate, including the product terms: 25,212 target
   words, 588,878 source rows, and exact zero residual at every weight. Its
   weight-six calculation checks 141,765,281 expanded terms.
6. Latest saved P6 sum, using all 64 complete terminal outputs, and comparison with
   the supplied 66,404-term canonical expression.
7. The latest C8 full-Jacobian and scalar assemblies, and exact rational sums giving 88.
8. Exact P8/Kv and J9 scalar identities from the complete full-numerical package.
9. New independent summary algebra: branch-exchange invariants, C1–C8 registry,
   full rational fixed-point/Jacobian through fourth order, and the C8 candidate
   comparison against the recorded complete numerical result.
10. Both **fresh complete numerical P6 period evaluations**, at 70 and 100 working
    decimal digits with different matching points and truncation settings, run
    through the portable curated layout. These do not use an old period table or
    the candidate as input. Agreement is not a rigorous interval enclosure.
11. Standard-library top-level mathematical checks run from the curated layout.
12. A genuinely standalone LaTeX build: the single source was copied to a temporary
    directory and compiled three times without external inputs. No unresolved
    references, overfull boxes, or multiply defined labels remained.
13. All 60 PDF pages were rendered and visually reviewed in contact sheets, with
    eight detailed page checks. An automated scan found no text span beyond the
    physical page boundary.

The individual JSON results and stdout records are in `consolidation/` beside this
report. `pdf_quality.json` records the source/PDF hashes and layout checks. Proof
checks and numerical evaluations have distinct records; no numerical result is
represented as a proof.

Additional portable jobs also passed: the complete certificate workflow from the
curated `work/` layouts; the low-order analytic-integral comparison; and the
Gamma-exclusion/rational-prediction audits. Their reports are included.

## Reproduction levels

`python run_checks.py` checks immutable distribution hashes, materializes a
portable working layout, and verifies exact saved scalar sums and assemblies.
`python code/reproduce.py --task certificates` reruns the exact period proofs.
`python code/reproduce.py --task c8-numerical` reevaluates the complete P6 period
expression. Full raw ordered integration is a different, more expensive task;
its commands and required regeneration stages are in
`documentation/REPRODUCTION.md`.

The current distribution deliberately excludes transient logs/caches, binaries,
redundant ZIPs, duplicate files, and regenerable expanded intermediate stages.
Defining source expressions, necessary replay checkpoints, final integration
outputs, proof targets/certificates, and code are retained. The catalog and omission
records identify exactly which original paths are retained or intentionally omitted.

## Inherited information and unresolved limitations

* No complete reintegration of every original kink kernel was performed during
  consolidation. Fresh certificate verification tests exact identities of the
  archived expressions, not independent validity of the physical prescription.
* Six full C8 beta inputs enter the latest assembly as inherited numerical
  records; their separately restored complete exact unprojected expressions are
  not all available. Raw source/code may support regeneration, but a complete
  end-to-end proof chain for C8 has not been accepted.
* Historical F2 coverage metadata names 258 unavailable intermediate files. Its
  final U expression and numerical evaluations survive; all intermediate raw
  provenance is not restored by copying a coverage report.
* Inherited numerical records are not newly integrated merely because a current
  algebra checker reads them. The discrepancy near 3.1e-86 for C8 is not an interval
  bound and does not justify a claim about independence of real zeta constants.
* The physical duality, all-orders closure of the two-essential-coupling
  renormalization problem, and all-orders filtered-MZV conjecture are not proved by
  these finite checks.

## Main scientific conclusions preserved

C1 and C2 are the published baseline. C3–C7 have the specified analytic period
reductions in the archived matched calculation; C5–C7 have complete electronic
certificates. The rational C8 is 88. The full numerical C8 is approximately
247.3812048049935484073550747661, with a high-precision candidate but no complete
analytic C8 certificate. The simple rational trace guess predicting 160 is false.
Other fixed all-orders guesses have failed their stated tests; no replacement
arbitrary-order formula is established.
