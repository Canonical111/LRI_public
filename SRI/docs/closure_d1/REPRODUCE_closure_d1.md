# Reproducing closure_d1

From `SRI/code/closure_d1/`:
1. `make -f public.mk test` (a few seconds; Python >= 3.10 and sympy for the last three rows): the dated snapshot
   (`public/SNAPSHOT.sha256`; files listed in `public/SCRUBBED.txt`: presence only), the independent checks of the
   closure argument's finite claims, the prescription archive (`prescription/MANIFEST.json`; the files in
   `public/NOT_SHIPPED.txt` must be absent), its checker rerun (`prescription/code/check_prescription.py`, 22 exact
   checks, compared with `prescription/verification/checks.json`), and an independent re-derivation of the beta
   recurrence b3..b9, h4..h8 from the finite-response system.
2. `make -f public.mk replay`: the same table; the package has no quoted number.

The analytic arguments (classification, power counting, the delta-log deformation, the forest/extension step, endpoint
power counting, scalar endpoint factors, separated probes, the normal-ordering audit, the uniqueness step) are to be
read in the SRI note, Appendix D; they are not computations to rerun. The closure argument's own companion script
(`code/check_closure_algebra.py`) was not supplied; it will be added with a `test` row if it is.
