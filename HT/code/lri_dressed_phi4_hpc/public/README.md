# lri_dressed_phi4_hpc: the d = 1 finite-coupling HT solver

`HT/code/lri_dressed_phi4_hpc` is the solver behind every finite-coupling Hamiltonian-truncation number for the
one-dimensional long-range Ising model in the paper and the HT note. It ships at commit **33998bb**, the code the
production campaign `dens_v1` ran.

## What it computes

- **Hamiltonian.** The phi^4 Hamiltonian of the long-range Ising chain in radial quantization (HT note, Sections
  "Model" and "Zero mode and bath"). The field is split into the zero mode q = a0 + a0^† and a bath of the other
  modes.
- **Zero mode.** Kept as `nz` states per parity, each a superposition of many zero-mode quanta (the level cutoff does
  not cap them). The full Hamiltonian, including the couplings L_j W_j of the zero mode to the bath, is diagonalized
  on the product of these states with the bath. The `nz` states are either the lowest eigenstates of the zero-mode
  part H_z = (Ds/4) p^2 + A q^2 + (g/12) q^4 or, with `--local-basis`, a frozen state-averaged ("density") basis.
- **Bath.** Truncated at total level N (`--bath-cut`), with no particle cap.
- **Tuning.** The two couplings (r, g) are tuned so that the sigma gap equals Ds and the phi^3 gap equals 1 − Ds.
  The output is Delta_eps, the first excited reflection-even, field-even gap.
- **Window correction.** `--window vacuum --window-mode consistent` adds the full-vacuum window correction
  D(N) = Ev(cut) − Ev(cut − N) to every bath state. Ev is solved as a scalar fixed point at every coupling (HT note,
  Section "Window correction"; `docs/WINDOW.md`).
- **Density basis.** `train-basis` builds the density basis from the reduced density matrix of a larger "teacher"
  zero-mode space (`docs/DENSITY_BASIS.md`).
- **HPC layer.** Node-packing launcher, cross-node leases and checkpoints for symmetry (`cluster/symmetry/`).

The package's own documentation ships verbatim: `README.md` (release notes of the received package and of the
symmetry/window revision), `INTEGRATION.md` (the density basis), `docs/ALGORITHM.md`, `docs/WINDOW.md`,
`docs/DENSITY_BASIS.md`, `docs/HPC.md` and `cluster/symmetry/README.md`.

## Public targets (run from `HT/code/lri_dressed_phi4_hpc`)

| Command | What it does | Needs | Time |
|---|---|---|---|
| `make -f public.mk test` | The package's staged validation `scripts/validate_release.py` (see below) | Python 3.11, numpy 2.3.5, scipy 1.17.0, numba 0.65.1, pytest | about 2–3 min with THREADS=4, < 2 GB |
| `make -f public.mk replay` | Checks that this tree produced the shipped records (source and release fingerprints), then runs the package's own validator on all 881 shipped results | same | about 1 min, one core |
| `make -f public.mk smoke` | Reruns the production item N = 12, Ds = 0.2 (16 density states, consistent window) and compares it with its record to 1e-8. Basis artifacts are bound to the runtime that trained them, and the package refuses them on any other runtime. On a non-production runtime, smoke therefore first retrains the Ds = 0.2 basis with the production settings | same | 10 s on the production runtime; about 3.5 min (THREADS=4) otherwise |

**What `test` runs.** Six stages:

1. pytest: 104 tests.
2. Saved-seed regression.
3. `--window none` bit equality with the frozen baseline `reference/production_e637dfd`, the received code.
4. A calibration smoke run.
5. Window bit equality with `reference/production_e2ca07c`.
6. Density-basis validation.

The equality stages compare two runs on the same machine, so they hold on any CPU vendor. Receipt 570965 recorded
this validation on symmetry for the production install. It is in `HT/data/HT_1d/dens_v1/validation/570965/`.

The quoted numbers are not replayed here. `HT/code/lri_dressed_phi4_hpc_analysis` recomputes them from the shipped
records (`make -f public.mk replay` there).

## Notes on shipped files

- **Verbatim tree.** The whole commit ships unchanged (157 files). The release fingerprint `io.release_fingerprint`
  hashes `src/`, `scripts/`, `cluster/symmetry/`, `tests/`, `reference/`, `inputs/`, `pyproject.toml` and
  `requirements-tested.txt`. The replay checks it against the records, so these files keep their original bytes,
  including site paths in `cluster/symmetry/env.sh`.
- **`MANIFEST.sha256`.** This is the checksum list of the package as originally received (e637dfd). It has been
  stale since the symmetry revision (157a2c6), so `scripts/verify_manifest.py` fails on this tree as it did in
  production. No target uses it. The binding is the release fingerprint.
- **`benchmarks/`.** Timing measurements of the received package, cited in `PERFORMANCE.md`. Not used by any target.
- **`inputs/`.** Coupling seeds of the received package, used by the saved-seed test.
- **Runtime binding of bases.**
  - `lri_dressed.local_basis` accepts a basis artifact only on the exact runtime that trained it: Python 3.11.4, numpy
    2.3.5, scipy 1.17.0, numba 0.65.1 for the shipped ones.
  - On another runtime, `python -m lri_dressed run --local-basis` stops with "Basis source/runtime differs from this
    release: regenerate and revalidate on the target runtime". This is by design.
  - Retrain with `train-basis`, using the settings stored in the artifact's config (as `public/smoke.py` does).
  - Tested on symmetry with Python 3.12.9 and numba 0.68.0: the retrained Ds = 0.2 basis reproduces the record to
    1e-15.
