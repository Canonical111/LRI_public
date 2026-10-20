from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parents[1]

def main():
    s=json.loads((ROOT/'results/SUMMARY.json').read_text());v=json.loads((ROOT/'results/validation.json').read_text());a=json.loads((ROOT/'results/phase_overlap_asymptotics.json').read_text())
    r=[]
    for mu in [2,8,16,28]:
        for ch in ['phi6','full']:
            x=json.loads((ROOT/f'results/dconn_{ch}_L{mu}_d8.json').read_text());r.append((mu,ch,x['response']))
    table='| Low cutoff mu | Source operator | Response at order 6 | Order 7 | Order 8 |\n|---:|---|---:|---:|---:|\n'
    for mu,ch,x in r:table+=f'| {mu} | {ch} | {x[6]:+.9f} | {x[7]:+.9f} | {x[8]:+.9f} |\n'
    text=f'''# Progress on complete high-order tails: low-bath mixing and overlap subtractions

## Main result

A missing part of the previous calculation has been resolved: the leading
three-line high kernel is extended from zero-mode external states to general
fixed low bath states, and its **complete low-state linear response** is now
calculated through epsilon^8 with consistent vacuum feedback and primary retuning.
The response is not a cutoff-independent number. An explicit phase-response
calculation has sqrt(mu), log(mu)^2 and log(mu) overlap divergences, whose
coefficients and finite part are derived without a thermal target or cutoff fit.

The calculation does NOT yet provide complete physical C6,C7,C8 leading-tail
polynomials. It determines a low-state response and the necessary overlap
subtractions, not every higher high-state Wilson coefficient. The auxiliary
low cutoff mu must not be identified with outer Lambda in a fixed-low-state
asymptotic expansion.

## 1. A new same-power operator in the general low-bath kernel

Let M=:q^2:, N be low total mode level, P particle number, and
A=sum_low u_n^2. For reflection nu, d_nu(p)=2+nu-2ceil[(p+4nu)/8]. The correct
operator is

    J_nu^bath = q d_nu(P+3) q - A d_nu(P+4) - {{N,M}}/2.

The last term was absent in the earlier zero-mode-external formula because N=0
there. It enters at the SAME outer Lambda^-1/2 power at epsilon=0. The derivation
keeps the actual frozen cutoff phases and both high-state subtraction terms.

For a finite annulus Lambda..2Lambda, alpha=1/2, reflection even:

| Lambda | Error without the bath-level term | Error with it |
|---:|---:|---:|
| 64 | 0.511091892 | 0.012191234 |
| 256 | 0.260162207 | 0.001479356 |
| 1024 | 0.130637193 | 0.000183589 |

The old omission is O(Lambda^-1/2); the new discrepancy is O(Lambda^-3/2), as
predicted. Thirty-six finite-annulus cases and exact threshold identities test
the formula. These are kernel tests, not physical spectrum fits.

## 2. Complete response arrays, not just reference diagonals

For H -> H+eta*g(epsilon)^2*O, the new direct Taylor engine differentiates the
entire Dconn vacuum grid, source, r/g calibration and reference wavefunctions.
The output is partial_eta Delta_E at eta=0. O is Phi6, the phase operator, the
bath anticommutator, or their full sum. The thermal C6/C7/C8 values never enter.

{table}

**These table entries are derivatives with respect to a source strength, NOT
estimates of C6,C7,C8.** Their mu dependence has to be canceled in a complete
high/low matching calculation. The table is useful because it replaces unknown
low-response amplitudes by actual independently validated calculations.

There are {s['complete_low_response_records']} new response/control records,
Dconn cutoffs {s['Dconn_low_cutoffs']} and raw checks at {s['raw_low_cutoffs']}.
Mass and quartic source directions are separately checked: primary retuning
absorbs them as reparametrizations. The full bath source equals the sum of its
phase and anticommutator parts.

## 3. The first phase response is fully reduced

The prior tagged zero-mode calculation gave 4375/729=6.001371742... for the first
phase response. Summing ALL low bath states changes it. The new exact Wick
reduction has 38 positive rational weights and one-dimensional convolutions.
Its large-mu behavior is

    R_phase,4(mu) = A sqrt(mu) + (log(mu))^2/81 + B log(mu) + C + o(1),
    A = 32(pi-2)/(729 pi^(3/2)) = {a['numeric'][0]:.16g},
    B = [41+42pi+12gamma_E+24log2+48log(1+sqrt2)]/486
      = {a['numeric'][2]:.16g},
    C = 8.094227411788686348... .

The power term is a Dirichlet bulk integral; the squared logarithm comes from
an overlapping endpoint sum; the remaining logarithm comes from explicitly
summed harmonic channels. Their coefficients are computed from the rational
weights, not selected by fitting the data.

The finite part C is independently evaluated from convergent Gamma/Beta sums,
explicit endpoint integrals and controlled asymptotic summation tails. The
256- and 512-term evaluation splits differ by about 7.34e-18. This is not an
interval-arithmetic proof for every displayed digit.

| mu | Direct complete response | After the three analytic subtractions |
|---:|---:|---:|
| 32 | 9.267151973 | 7.364569... |
| 1024 | 12.218015375 | 7.930838426 |
| 16384 | 15.129147453 | 8.046192785 |
| 262144 | 20.740751293 | 8.080411451 |

The exact CSV carries all values. The finite-mu remainder is still visibly
nonzero: no all-mu numeric error constant is claimed. Large mu here is ONLY the
phase-response convolution, not a full eighth-order spectrum calculation.

## 4. Why this changes the matching problem

The response of a regulator-phase operator is not a constant amplitude that can
be assigned the physical phi6 exponent by assertion. It has overlapping power
and logarithmic dependence even before the high kernel is completed.
A finite physical result must compensate this arbitrary low/high split in the
other matching pieces. This identifies actual subtraction terms rather than
merely adding another fitted s5 or omega parameter.

The low response is in the retuned low-coupling convention. High-to-low coupling
conversion and the corresponding hard graphs must be carried together; evaluating
the old high prefactor at mu=Lambda and multiplying these responses is not a
valid completion. Nor should these pieces be added twice to a spectral sum that
already contains their paths.

## 5. Independent checks

| Check | Largest observed discrepancy |
|---|---:|
| Exact rational versus numerical full source recursion | {v['exact_rational_scaled_error']:.3g} scaled |
| Phase-source shell sum versus independent Fock recursion | {v['phase_response4_shell_error']:.3g} absolute |
| Phi6 third-order finite-response identity | {v['phi6_response3_identity_error']:.3g} absolute |
| Sum of separate sources versus full source | {v['source_linearity_scaled_error']:.3g} scaled |
| Fresh response replay versus saved record | {v['fresh_saved_scaled_error']:.3g} |
| Direct versus FFT phase convolutions | {v['convolution_backend_error']:.3g} at exported precision |

The finite-epsilon test constructs unexpanded oscillator matrices and solves
vacuum equations by Schur complements. Exact source derivatives versus the
eighth-order Taylor series have a ninth-order remainder; halving epsilon tends
to a factor 512. No finite-epsilon fit extracts the coefficients.

## Status

This replaces two limitations of the earlier work: external-zero-mode-only
kernels, and guessed low-state response amplitudes. It also derives an explicit
complete overlap asymptotic expression, including its finite part.
The genuinely higher hard matching and complete recombination still determine
whether a physical high-order leading tail exists in the assumed form and what
its finite coefficients are. Consequently this report publishes no new physical
C6,C7,C8 intercept or error bar. It supplies calculable inputs and strong checks
for that completion rather than another target-calibrated extrapolation.
'''
    # Always render numerical table entries from the actual record.
    with (ROOT/'results/phase_overlap_convergence.csv').open() as f:tab={int(x['mu']):x for x in csv.DictReader(f)}
    text=text.replace('7.364569...',f"{float(tab[32]['renormalized_finite_part']):.9f}")
    (ROOT/'REPORT.md').write_text(text)
if __name__=='__main__':main()
