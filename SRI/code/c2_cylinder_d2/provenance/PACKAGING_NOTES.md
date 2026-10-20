# Consolidation and verification record

This note records the distinction between preserved research outputs and work
actually repeated while assembling this distribution. The scientific snapshot
is dated 12 October 2026; individual run receipts retain their actual UTC
completion times.

## Source lineages

Four archives were used: the supplied final-method study, the independent
formula/elliptic/local review, the initial Hamiltonian diagnostic package, and
the completed numerical Hamiltonian package. Their names, sizes, SHA-256 hashes,
and retained member mappings are in `SOURCE_INVENTORY.json`.

The new LaTeX note consolidates the earlier derivations rather than requiring
those conversational reports as dependencies. The original supplied manuscript
is retained for attribution and comparison. The main note's bibliography is
embedded; external papers are not redistributed.

## Changes to code and analysis organization

The scientific solver modules were preserved, with one small robustness fix in
`code/hamiltonian/reproduce.py`: the cache test requires both a coefficient array
and its matching JSON metadata. Previously a metadata-only file could be
mistaken for a valid array cache. No matrix element, counterterm formula,
resolvent denominator, or physical conversion formula was changed.

New code in this bundle consists of `scripts/run.py`, `scripts/build_note.py`,
`scripts/verify_manifest.py`, `scripts/check_results.py`, and
`code/hamiltonian/bundle_helpers.py`. These organize existing modules, rebuild
recorded analyses, capture reports, or check the distribution. The runner stages
the original flat directory structure so that the source modules need not be
rewritten to match the new directory layout. It keeps input data read-only in
the distributed tree and exports outputs into a separate directory.

The helper reconstructs the large-lambda tail fits using the independently
fixed leading coefficient and the original subleading model family. It does
not substitute a generic free-leading-tail fit. It also provides reproducible
entry points for the cylinder-improved magnetic check, coupling-logarithm
sensitivity, and CSV tables.

The original recorded transseries-fit file has only eleven of the twelve
N=256 cases. Its missing order-3, lambda-0.35 point invokes the existing
raw-power fallback when the historical final analysis is run. The new
`analyze-recorded` command reproduces that original selection exactly in the
tested environment. The default `analyze` command regenerates all twelve
transseries fits consistently. The order-3 representative C2 changes from
-4.071269861562929 to -4.071252205780145; orders 1 and 2 are unchanged. This
1.77e-5 change is much smaller than the warranted numerical precision. Both
records are included; neither calculation uses the proposed C2 as an input.

## Rerun during consolidation

The following executed successfully from clean staged directories:

| Workflow | Retained output directory | What it tests |
|---|---|---|
| Finite validation suite | `results/validation/` | Form factors, Ward/shell identities, block sums, convolutions, local constants |
| Regenerated saved-data analysis | `results/hamiltonian/` | All available fixed-tail fits and regulator-model analysis from retained sequences |
| Recorded-selection analysis | `results/hamiltonian_recorded/` | Exact reproduction of the earlier model availability |
| Exact certificate | `results/certificate/` | Integer-interval formula enclosure and polynomial certificates |
| Second-order and magnetic checks | `results/second_order/` | Analytic formula, slope, finite matching, protected magnetic coefficient |
| Fresh small spectral example | `results/demo/` | New N=24 coefficient cube, regulator contractions, and mixed/collapsed sums |
| Independent analytic/numerical review | `results/formula_checks/` | Symbolic identities, complex-plane pairing, elliptic orders 96/192/384, local contacts |
| Original eight-stage pipeline | `results/original_study/` | Reproduction of the supplied study's own computational pipeline |
| Reporting regression | `results/reporting_regression.json` | Historical/fresh result distinction, finite-test status, certified rounding |
| Standalone LaTeX build | `results/document_build.json` | Three-pass compilation with only the single .tex source present |

Every calculation workflow has a `run_receipt.json` with the executed commands
and hashes of exported files. The LaTeX build report records the absence or
presence of undefined references/citations and overfull boxes. The final PDF
was rendered and its layout inspected; the render images are quality-control
scratch files and are not distributed.

**Not repeated during document preparation:** all N=256/N=384 production grids,
the entire expensive full-Hamiltonian run plan, every historical exploratory
run, or a proof of a uniform continuum error bound. The large raw numerical
sequences are retained as prior calculation records, and the full generation
code and parameter plan are supplied. Successful quick tests do not certify
untested resource-heavy runs or establish a rigorous physical uncertainty.

## Included and excluded material

Included input data consist of complete raw cube sequences, mixed-square
sequences, local/leading-tail auxiliary coefficients, historical model records,
prior validation diagnostics, exact Ising inputs, and the original study's
configuration. These are needed to repeat the reported analyses or audit their
provenance without repeating hours of spectral computation. CSV summaries and
execution receipts are intentional final verification outputs.

Excluded material includes numerical coefficient caches (`.npy`, `.npz`,
`.dat`), virtual environments, bytecode caches, LaTeX build intermediates,
rendered quality-control images, platform metadata, unused exploratory outputs,
and nested copies of the input ZIPs. The archive hashes preserve the identity
of those source ZIPs without duplicating their packaging.

The manifest covers shipped files, not future user outputs. Verification of a
checksum is an integrity check, not an authorship claim, an endorsement of all
original manuscript arguments, or a numerical error certificate.
