#!/usr/bin/env python3
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 s=json.loads((ROOT/'results/SUMMARY.json').read_text())
 refs=json.loads((ROOT/'results/extrapolation_reference.json').read_text())
 diag=json.loads((ROOT/'results/extrapolation_diagnostics.json').read_text())
 rows=list(csv.DictReader((ROOT/'results/coefficients.csv').open()))
 points={int(r['cutoff']):r for r in rows if r['scheme']=='raw'}
 shifts={int(r['cutoff']):r for r in csv.DictReader((ROOT/'results/partial_vacuum_shifts.csv').open())}
 full=json.loads((ROOT/'results/validation_full_recursion.json').read_text())
 rat=json.loads((ROOT/'results/exact_rational_validation.json').read_text())
 lines=['# Direct C8 from phi4 Hamiltonian truncation',
 '', '## Main result', '',
 'The coefficient is that of epsilon^8 with epsilon=2s-1 in the thermal dimension.',
 'It is not the eighth coefficient of the expansion about the short-range endpoint.',
 '', '**A new direct finite-cutoff calculation is complete. A matched physical C8 is not.**',
 f'There are {s["raw_points"]} accepted raw cutoffs, all even Lambda=2,...,50, and {s["vacuum_only_points"]} isolated-vacuum comparisons.',
 '', f'At the largest completed cutoff, C8_raw(50) = {s["C8_at_50"]:.13f}.',
 'Conditional linked-tail fits suggest a raw-Hamiltonian intercept near 8.1 million.',
 'That number is not a controlled continuum prediction or an uncertainty bound.',
 '', '## 1. Raw direct coefficients', '',
 '| Lambda | C4 | C6 | C7 | C8 |','|---:|---:|---:|---:|---:|']
 for L in (8,12,16,24,32,40,48,50):
  r=points[L];lines.append(f'| {L} | {float(r["C4"]):.9f} | {float(r["C6"]):.6f} | {float(r["C7"]):.6f} | {float(r["C8"]):.6f} |')
 lines+=['','Each coefficient is extracted by formal-series algebra, not by sampling epsilon.',
 'The production calculation uses fourth-order trial wavefunctions and their Rayleigh quotient.',
 'All mode-weight jets through epsilon^7 and coupling tuning through epsilon^8 are retained.',
 'The exact order-sufficient caps are P<=19 and Q<=16. The old seventh-order caps do not suffice.',
 '', 'The basis has 5,248,378 states at Lambda=50, including auxiliary parity sectors.',
 'No C8 at Lambda=52 was accepted: the local memory limit was exhausted. This is recorded separately.',
 '', '## 2. Validation', '',
 f'- Maximum lower-order discrepancy against the saved C0..C7 table: {max(s["max_abs_lower_order_differences"]):.6g}.',
 f'- Maximum exact C2 shell residual: {s["max_abs_shell_residual"]:.6g}.',
 f'- Maximum primary-gap tuning residual: {s["max_abs_tuning_residual"]:.6g}.',
 f'- Independent full eighth-order recursion, both prescriptions, Lambda=2,4,6,8,12: maximum C/r/g discrepancy {max(max(r["max_abs_residuals"].values()) for r in full):.6g}.',
 f'- Exact-rational nonorthogonal-basis recursion at Lambda=2,4,6,8,12: maximum C discrepancy {max(r["comparison_max_absolute_error"] for r in rat):.6g}.',
 '- Enlarging the sufficient caps to P<=23,Q<=20 passes the tested comparisons.',
 '', 'These are numerical implementation checks, not estimates of physical matching or cutoff error.',
 '', '## 3. Partial vacuum correction', '',
 'Only H_raw+g(epsilon)^2 D(epsilon) is included here. D is the previously isolated missing-vacuum-shell term.',
 'Both low-order wavefunctions and high-order couplings are recalculated. The calculation does NOT freeze the raw wavefunction.',
 'No connected Dconn extension is assumed or fitted.',
 '', '| Lambda | delta C4 | delta C7 | delta C8 |','|---:|---:|---:|---:|']
 for L in (12,24,40,48,50):
  r=shifts[L];lines.append(f'| {L} | {float(r["delta_C4"]):.12f} | {float(r["delta_C7"]):.9f} | {float(r["delta_C8"]):.9f} |')
 lines+=['', 'The C8 shifts do not bound missing connected-vacuum terms at orders three through eight or their subtraction iterations.',
 'The previously discussed +0.0187 connected boundary effect on C4 is not transplanted to C8.',
 'The cancellation of the isolated fourth-order logarithm against raw disconnected diagrams is not counted twice.',
 '', '## 4. Conditional extrapolation', '',
 'Assume a single leading channel Lambda^(-1/2) A(epsilon) exp[-log(Lambda) omega(epsilon)].',
 'C2 and C3 are known control inputs. C4 through C8 are fitted, not supplied as targets.',
 'Raw phi6 exponent inputs through omega5 are inherited from the prior study. omega6 is unknown and fitted at order eight.',
 'The highest log term is fixed to -117649/(93312 sqrt(pi)) * log(Lambda)^6/sqrt(Lambda).',
 '', '| Basis | fitted C8 intercept | fitted omega6 (nuisance) | eighth-order residual |',
 '|---|---:|---:|---:|']
 for r in refs:
  k=r['details'][-1];lines.append(f'| {r["model"]} | {r["limits"][8]:.6f} | {k["fitted_omega6"]:.3f} | {k["max_residual"]:.6g} |')
 lines+=['', 'Reference fits use 16<=Lambda<=50. The three bases differ by subleading powers and logarithms.',
 'Other linked-basis/window/cutoff-coordinate tests ending at 50 range roughly from 7.93 to 8.29 million.',
 'That spread does not include every possible asymptotic channel or matching error, and is not an uncertainty interval.',
 '', 'For withheld-cutoff testing, fits trained only through 40 predict all higher coefficients recursively at 42..50.',
 'Only C2 and C3 at the withheld cutoffs are supplied as controls.',
 '', '| Basis | maximum withheld C8 error |','|---|---:|']
 for r in diag['withheld']:lines.append(f'| {r["model"]} | {r["max_absolute_errors"][8]:.9f} |')
 lines+=['', 'Good nearby-cutoff prediction does not bound the extrapolated intercept.',
 '', '### Adverse extrapolation test', '',
 'Fitting C8 alone with the highest logarithm fixed, rather than linking lower-order tails, is unstable:',
 '', '| Additional subleading terms, window 16..50 | fitted C8 | residual | scaled condition |',
 '|---|---:|---:|---:|']
 for r in diag['standalone_fits']:
  if r and r['lo']==16:lines.append(f'| {r["extra"]} | {r["C8"]:.3f} | {r["residual"]:.6g} | {r["condition"]:.3g} |')
 lines+=['', 'These are not competing precise physical estimates. They demonstrate why the narrow linked-model spread cannot be promoted to a confidence interval.',
 'Arithmetic perturbation and 70-digit linear-solve checks do not correct an incomplete tail model.',
 '', '## 5. What is still required for a physical C8', '',
 'A consistently connected vacuum-window correction through order eight, including mixed and iterated contributions, is not supplied or derived here.',
 'Knowing C4 or its leading correction does not fix the new eighth-order vacuum and matching amplitudes.',
 'Possible nonvanishing cutoff artifacts must be removed before declaring the fitted intercept a genuine limit.',
 'The known lower-order coefficients and independent descendant identities provide acceptance tests for that matching.',
 'More large-cutoff data would then test the matched tail model; they cannot be replaced by coefficient ratios or a Padé estimate.',
 '', 'The general effective-Hamiltonian framework is discussed in J. Elias Miro and J. Ingoldby, arXiv:2212.07266.',
 'It does not provide this project-specific order-eight matching automatically.',
 '', '## Reproduction', '',
 'README.md lists all scripts and dependencies. docs/METHOD.md gives the mathematical construction.',
 'results/ contains the accepted points and adverse diagnostics. No fitted source C8 is used as an input.',
 'This research driver is not yet integrated with the private reviewed Expanse campaign layer.', '']
 (ROOT/'REPORT.md').write_text('\n'.join(lines))
 print('Wrote REPORT.md')
if __name__=='__main__':main()
