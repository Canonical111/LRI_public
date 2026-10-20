# Fixed state-averaged basis: numerical definition and checks

This numerical subspace follows the supplied `lri_d1_basis_connected` experiment.
It is not an individual-mode UV parent or a new matching counterterm. The only
physical Hamiltonian is the uploaded consistent full-vacuum-window model.

For training bath cutoff L=2m, define

    rho = (rho_vac,L + rho_sigma,L + rho_shadow,L)/6
          + sum_(M=0,2,...,L-2) rho_vac,M/(2m).

Each reduced density is obtained by tracing the complete retained bath state.
Select the largest k eigenvectors separately in local field parity. Thermal
states have zero role in the selection and its stopping rules. The selected
primitive isometry U obeys U^T U=I and exact parity support. It and the primitive
oscillator scale t are frozen within an inner solve. An internal diagonalization
of U^T h_z U rotates coordinates only, not the span.

Using the existing dimensionless oscillator Q and positive matrix pp, project

    q_j = U^T (t^j Q^j) U, j=1,...,4,
    kinetic = U^T pp U/(4t^2).

The powers are formed in the original primitive basis BEFORE projection, with
the original +4 auxiliary padding. Powers of the compressed q_1 are not used.
For x=Delta_sigma and the original theta=(kappa,log e),

    g=192 e^3/x^2, A=4 e^2 kappa/x, r=A+g/2-x/4,
    h_z=x*kinetic + A*q_2 + g*q_4/12,
    L1=(2A-x/2)q_1 + g*q_3/3,
    L2=(A-x/4)I + g*q_2/2,
    L3=g*q_1/3, L4=g*I/12.

The local even ground-energy shift and its derivative are retained, giving
Ev(0)=0 in precisely the original convention. All sublevel vacua use the same
fixed span. The nonlinear table D_L(N)=Ev(L)-Ev(L-N) is solved again at each
changed coupling; fixed basis does not mean frozen windows.

## Derivative and coordinate transport

Inside the fixed span, dA/dkappa=4e^2/x, dA/dlog(e)=2A, dg/dlog(e)=3g.
For an eigenvector represented in the current local eigenbasis,

    dE_raw = Tr(rho_local * dh_z) + sum_j Tr(corr_j * dL_j),

with full off-diagonal rho_local, and with the local scalar energy shift
subtracted in dh_z. Local eigenvector-response terms are coordinate effects
inside the same span; keeping only diagonal dh_z would lose the invariant
physical derivative. The existing window.derivative performs the additional
implicit fixed-point response. Its absolute 1e-11 fixed-point gate is unchanged.

Warm vectors are rotated with U_old^T U_new within each local parity. Scalar
warm-start guesses for the vacuum fixed point are only initial guesses. They do
not permit acceptance of a stale window table.

For descendants, project the actual primitive annihilator,

    a0 = U^T [t(a+a^dagger) - (a^dagger-a)/t] U / 2.

Reconstructing a0 from compressed local-energy differences assumes an invariant
subspace and is generally wrong. The same fixed span and D table are used in all
reflection sectors. These remain free-generator ancestry tests, not exact
interacting conformal generators.

## Training and artifact acceptance

The separate training job repeats density selection and an inner primary-gap
solve. It stops only when the change in theta is below `basis_tol` and the
larger teacher's two primary residuals are below `teacher_tol`. At least two
outer sweeps are required. It also checks normalization, positivity/trace of
the density, full training-vector residuals and every vacuum fixed-point residual.
The discarded density weight is recorded, not interpreted as a bound on the
held-out thermal gap or higher levels.

Default `basis_tol=2e-8` and `teacher_tol=1e-7` are NEW training-quality gates.
They do not relax the original production tuning/eigensolver/window gates.
Changing these explicitly changes artifact provenance. They do not certify the
teacher's own oscillator or bath convergence. Independent references remain
necessary.

A checkpoint records the current outer sweep, candidate U/t, selected theta,
inner Newton theta/history and finished outer history. The final complete
checkpoint contains the accepted artifact, allowing recovery without retraining.
No Krylov vector from a different span is silently reused. Training saves use
the same atomic, fsynced checksummed-envelope helper and claim/lease as point runs.

A final artifact holds the maximum kept basis. Taking the first k columns in
each parity gives a nested smaller span, but this is a numerical comparison,
not a proof it meets any accuracy target. Cross-cutoff use is allowed. Cross-x,
source/runtime, oscillator-size, or window-prescription mismatch is rejected.

## Current evidence, not a universal guarantee

Fresh integration tests compare projected operators, same-span parent spectra,
full window Jacobians, warm coordinate rotations, actual projected a0, training
and run restart paths, corrupted/stale artifacts, embedded diagnostics, manifests
and completion identities. Pinned source comparisons protect the unchanged path.

An overly small local space can pass primary retuning and still miss excited
levels. The new numerical validation deliberately detects this; the README
requires separate low-spectrum convergence. This is why no universal default
of 16 optimized states is advertised for the strong-coupling HPC grid.

The implementation does not eliminate bath-cutoff or physical matching errors.
It introduces neither float32 nor fast-math, and no amplitude threshold is used.
