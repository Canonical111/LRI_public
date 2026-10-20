C62d -> C63d (2026-10-03): **H1 is handed off.** The shared L7+L8 d=2 inventory is published and pinned.

**Pin.** `LRI_C8_shared/inventory/HANDOFF_inventory8_d2.json` records `MANIFEST.json`:
- sha256 `46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099`
- md5 `a79eb5bf8090272cedefb83340d7bd82`

The HANDOFF file itself has sha256 `ad2e716cba51edc93591604e4bf84654879df069dbfc7684e359c8b9a12a9488` as written.
Your additions to its `c63d` block will change that.

**Verified copies.** Each passes all four steps of `src/gen/verify_inventory.py <tree> --pin <sha256>`. Use the
verifier inside the tree: it is the fixed one (below).
- Mac: `LRI_C8_shared/inventory/inventory8_d2/` (7.8 GB). Please do not browse it in Finder: a `.DS_Store` would be an
  unlisted file, and the verification would then fail.
- Expanse: `<SCRATCH>/temp_project/LRI_C8_shared/inventory/inventory8_d2`, for your jobs there.
  We both run as <USER>.
- Symmetry (`<SCRATCH>/LRI_C8_shared/inventory/inventory8_d2`): not made yet, because symmetry's compute
  nodes are down. It will be a verified byte copy of this tree, not a rebuild.

**Where and how it was built.** On Expanse (user decision U1: development compute moves there while symmetry is
down), from a `git archive` export of LRI_C8_D2_HPC `36043bb` (branch c8), with GCC 13.3.0 on AMD EPYC 7742.
- J-GEN-1, job 54631551: A-INV-2 passed. All 2,441 free L7 and all 840 power L3-L7 G-files are byte-identical to
  the frozen C7(2) files, the inventories are equal, 1 and 8 threads give identical outputs, and the free L3-L6
  differences are rate lines only (legacy tables, by design).
- J-GEN-2, job 54631552, 128 threads: every A-INV-3 gate passed with the plan's numbers.
  - (a) Sum w_A = 49985915/768 and sum w_B = 33994099/6912.
  - (b) The metadata equal your C8(1) `L8_inventory.txt`; 5,068 keys exceed 2^64.
  - (c) The zeros are 2,511 and 2,340.
  - (d) 248 primitives.
  - (e) 16,798 and 4,891 finite kernels; 734 and 555 of them with s_G = 4; selections 16,064 and 4,336.
  - (f) Coverage 2,254 / 3,886 / 248 / 15,816 / 4,336.
  - (g) Edge forests: 7,231 power classes, 0 failures.
  - (h) Kirchhoff exact on 144 kernels.
  - (i) M <= 4,032 and T <= 280.
  - (j) The rates obey the parity rule.
  - (k) Forests: 11,254,373 at L8 and 873,108 at L7, equal per class.
- A-INV-4, job 54631553: a second compute node (<NODE>, 64 threads) reproduced `MEMBERS.sha256` and both builder
  inventories byte for byte against <NODE> at 128 threads. On Expanse this is a node and thread-count check (same
  CPU model). The plan's architecture check (symmetry Intel, 40 threads) follows when symmetry is back.

**Two fixes since the fd8532e export.** Both were found by an independent verifier, before anything was published.
- **Rate-line bytes.** The free builder now writes the parity-rule rate line with no trailing space, exactly as the
  frozen C7(2) free L7 files have it. The power files keep the C7(2) power builder's trailing space. The tokens are
  unchanged. Your `regenerate_rates.cpp` rewrites that line for d=3 anyway. If your L3-L7 byte regression compares
  whole rate lines, read them as tokens.
- **The verifier.** `verify_inventory.py` now hashes `SHA256SUMS` from its bytes. Before the fix, a CR or CRLF change
  to it passed step 2.
- The symmetry chain 569661-569664 (fd8532e) is still queued, as the user asked. Its J-GEN-1 would fail on the free
  L7 rate lines, so the symmetry repetition will use a fresh export.

**Your assembly HANDOFF (f5ff6a35), vendored.**
- LRI_C8_D2_HPC commit `1769abc` vendors the 13 listed files, the HANDOFF copy and 50 pinned `LRI_ROOT` fixtures.
- `tests/check_vendored.py --standalone` passes 12/12.
- `tests/vendored_isolated.py` passes 11/11 on a `git archive` export outside <PROJECT>. It gives your counts in
  every mode: 30 passed with the fixtures, 21 passed and 9 skipped without `LRI_ROOT`, and 30 with
  `LRI_ROOT=<PROJECT>`. No file is read outside the export.
- My independent `tools/make_lowloop.py` regenerates C7(2)'s files byte for byte at order 7. At order 8 its
  `gamma_d2_8.txt` is byte-identical to your `inputs_d2_check/gamma_d2_8.txt`, and its 7 B2 strings equal yours.

**Requests.**
1. Pin the MANIFEST sha256 in your manifest.
2. Run your gates 1-7 and record them in the HANDOFF's `c63d` block: `pin_recorded`, `gates_1_7` and
   `gate_5_forest_certificate`. A negative gate 5 triggers the bare-series identity at L8 under the r2 procedure.
3. A defect found later goes through the r2 procedure: `inventory8_d2_r2/` with a `SUPERSEDES.json`. The published
   tree is never modified.
