# INTERFACES (build contract for lri_1d_c5_exact; see PLAN.md for the physics)

Conventions (identical to lri_1d_c4_exact = C4P unless stated): even-parity densities on index i ↔ chi level N = 2i;
all-parity intermediates on [0, N] with N = Λmax; MOFF = 3; physical shell index m = max_s(4N_s + δ_s + n_s) ∈ [−3, 4Λmax],
storage index i = m + MOFF; quarter grid cut4 = 0..4Λmax (nc = 4Λmax + 1); value for reference p at cutoff cut4 is the
cumulative shell sum at storage index cut4 − p + MOFF; references p = 0..3; functionals r = (1/2, −1/2, 0, 0),
g = (−2/3, 1, 0, −1/3), C = Π = (1/3, −1, 1, −1/3); ε-orders of vertices are TAYLOR coefficients [ε^j].

## Files and owners
| file | owner | content |
|---|---|---|
| `lib5/common.py`, `lib5/series.py`, `lib5/paths.py`, `lib5/density.py`, `lib5/shells.py`, `lib5/keys.py` | coordinator | core engine |
| `lib5/kernel5.py`, `validate/test_kernel5.py`, `tools/bench_kernel5.py` | builder K5 | five-vertex streaming kernel |
| `rs5.py`, `words5.py`, `assemble5.py`, `windows5.py`, `run5.py` | coordinator | assembly, windows, driver |
| `slurm/*` | builder SLURM | symmetry layer |
| `validate/v3_brute.py`, `validate/v4_ht.py`, `validate/v6_overlap.py`, `fits/fits_c5_1d.py` | builder VAL | validators, fits |
| `validate/v1_exact.py`, `validate/v5_windows.py`, `validate/v7_closed.py`, `validate/test_core.py` | coordinator | validators |

## lib5/kernel5.py (builder K5)
```python
def density5_stream(s, N, block=8):
    """Even-parity five-vertex (four-slice) density.
    s: dict {(i, j): 1D float64 array of length >= N+1} for all ten pairs 0 <= i < j <= 4 (bundle (i, j) crosses
       slices i..j-1); s[(i,j)][l] >= 0 is the bundle series at chi level l (a bundle with no lines is [1, 0, 0, ...]).
    Returns R, float64 array of shape (H, H, H, H), H = N//2 + 1, with
       R[i1, i2, i3, i4] = [z1^{2 i1} z2^{2 i2} z3^{2 i3} z4^{2 i4}] prod_{(i,j)} s[(i,j)](prod_{k=i}^{j-1} z_{k+1}).
    Memory: R plus O(block * H * (N+1)^2) temporaries (stream over blocks of even N2). Positive-term sums only."""
```
Algorithm: PLAN.md sec. 3.4 (middle split at vertex 2; crossing kernel C(x, y, t) in numba; Lft, Rgt; stages A, B1, B2
as GEMMs; stream over even-N2 blocks). Reference: `proto/k5_middle_split_proto.py` (`dense5`, `split5`).

## run5.py CLI (coordinator; builder SLURM writes the Slurm layer against it — same as C4P `c4_run1d.py`)
`python run5.py run --Lmax L --cache DIR --workers W --part i --nparts n --block B`;
`python run5.py assemble --Lmax L --cache DIR --out OUT.npz`; `python run5.py list --Lmax L`;
`python run5.py bench --Lmax L [--task k] [--block B]` (prints one JSON line: Lmax, task, chain, spec, seconds,
peak_rss_GB, block, keys, threads, host, snapshot_sha); `python run5.py sha [--kind numerics|snapshot]`.

## Result npz schema (assemble output)
* quarter grid: `cut4` (int, 0..4Λmax), `valid` (cut4 >= 3), `r2..r5`, `g2..g5`, `C2..C5` (NaN where not valid),
  `X2..X5` (shape (4, nc); X_p NaN where cut4 < p);
* even grid (`even_L` = 2, 4, …, Λmax): `even_C5raw`, `even_C5Dconn`, `even_dC5_Dconn`, `even_dC5_g2D`,
  `even_dC5_bubble`, `even_dC5_rows4`, `even_dC5_rows5`, `even_T1`, `even_T2`, `even_T3`, `even_T4`, `even_A4`,
  `even_B4`, `even_B5`, `even_dR4`, `even_dR5`, `even_fast_g2D`, plus `even_C4raw`, `even_C4Dconn`, `even_shift4`
  (C4P-compatible);
* `provenance` (JSON string: numerics_sha, snapshot_sha, Lmax, producers, snapshot_manifest, …).
