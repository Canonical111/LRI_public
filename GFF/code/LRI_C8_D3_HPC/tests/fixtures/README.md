# Test fixtures

- **`delivered_tools/`.** `tools/production.py`, `assemble.py`, `common.py` and `prepare_inputs.py` exactly as
  delivered (git baseline 4de9412). Their sha256 values equal the `tool_sha256` of the run1 manifest (schema
  `c7-d3-production-1`). `tests/check_inputs.py` reads `prepare_inputs.py`; they are never used for production.
- **`run1_groups.json`.** Seeds, net seeds, net headers and net sha256 of the 20 groups of the C7(3) run1 campaign
  (symmetry, 2026-09-30, planned with the delivered tools and base seed 4805754955154533039), copied from its group
  configs. `tools/production.py`'s HD6 seed registry refuses each of them (`tests/unit_orchestration.py`, A-ORC-1);
  the C8(3) package has no legacy seed scheme, so C7(3)'s `tests/legacy_seeds.py` was removed in Stage 3a.
- **`c7_inputs/`.** `manifest.json`, `inventory.json` and `primitive_reference.json` of `LRI_C7_D3_HPC@a6ce987`
  (= `c8-base`) `inputs/`, byte copies (sha256 `5048b336…`, `7893ea62…`, `ea83fd45…`). `tests/check_inputs.py`
  compares the C8(3) inventory and packs with them. (Until Stage 3a, `tests/c7_view.py` rebuilt the C7(3) input layout
  from them for the inherited tests; the port removed it.)
- **`c7_tools/assemble_a6ce987.py`.** A byte copy of `LRI_C7_D3_HPC@a6ce987:tools/assemble.py` (sha256
  `f11cdfcb2ba4e6989a6d8681292a924fe1a5b839398d38624211978770163f98`, pinned in `tests/assembly_checks.py`): the
  order-7 reference of A-ASM-2.
- **`cost_model_synthetic.json`.** The labelled synthetic cost fixture (`"synthetic": true`, campaign b at 3x a):
  admitted only by `--plan-role validation` (D.5); `tests/staging.py` freezes it, `tests/unit_orchestration.py`
  tests its refusals under every other role.
- **`exact_check_keys.json`.** The classification of every leaf of the vendored `exact_check_results.json`
  (`tests/exact_keys.py`; A-ASM-1, A-ASM-4 `--exact`).
- **`zero_channel_tails.json`.** Real worker rows (schema `c8-d3-zero-channel-tails-1`) of the four zero-channel kernels
  of A-KER-6 (e), power L3 G7, free L6 G26 and the new L7 kernels free G1487 and power G1601 (d=3 payload 46341a3c0f11),
  each in the pilot shape (campaigns a and b, 8 replicates x 32,768 points nested at 4,096, `--mp-check on`), written
  by `tests/class_b.py --parts e --zero-channel-tails` in Expanse job 54672564 (`repair3b` on 592fb7f2aa4f;
  `bin/c8d3_gmp` 24adff54…), a byte copy of its evidence file (sha256 `df30569d…`, pinned in
  `tests/test_pilot_report.py`). The Mac run feeds them to `pilot_report` (A-DES-3's zero-channel part).
- **`inputs_mini/`** (Stage 2b; PLAN B, A-IN-3). The 8 smallest real L8 kernels per sector of the d=3 payload
  (46341a3c0f11, `MANIFEST_d3.json` 70af9d22…; by bytes, then id), written by `make inputs-mini`
  (`tools/prepare_inputs.py mini`) in J-IN-1 from the package's L8 packs: `packs/{free,power}_L8.pack` (those members,
  ascending id), `inventory.json` (the package's L3–L7 rows and those L8 rows, offsets in the mini packs) and
  `manifest.json` (schema `c8-d3-hpc-inputs-1`, labelled `test_inputs`, pinning the package's other inputs under
  `package_files`). `tools/members.py mini --to DIR` (`prepare_inputs.materialize_mini`) assembles a `C8_INPUTS`
  directory from it, hard-linking the package files; `verify()` accepts it and any plan on it is test-only.
  `tests/check_inputs.py` checks it against the package (and, with the L8 packs present, regenerates it byte for
  byte); `tests/members_test.py` extracts its members.
