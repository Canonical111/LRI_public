# LRI_C8_shared: shared work for C8(2) (session C62d, LRI_C8_D2_HPC) and C8(3) (session C63d, LRI_C8_D3_HPC)

Agreed 2026-10-03.

- **inventory/** (owner C62d; C63d verifies): the d-independent L7+L8 class and forest inventory and the d=2
  payloads, published as `inventory8_d2/` (handoff H1, pinned through `HANDOFF_inventory8_d2.json`; joint
  decisions in `inventory/DECISIONS.md`).
  - The payload pipeline has two stages (DECISIONS.md item C1, acknowledged by C63d on 2026-10-03). The builder
    bodies (masks, terms, forests, weights, statuses) do not depend on d. They come from C62d's
    `gen/build_free` and `gen/build_power` (LRI_C8_D2_HPC), which write the rate line at d=2 (parity rule) and
    take no d parameter.
  - The rate line is the only d-dependent part. C63d's `regenerate_rates.cpp` rewrites it for d=3 from the
    published d=2 G-files, and C63d verifies independently: counts against an independent enumeration, weight
    sums, and reproduction of the L<=7 C7 packs at d=2 and d=3.
- **assembly/** (owner C63d; C62d checks): the eighth-order general-d assembly (RG combinations, Laurent and jet
  orders through C8), specialized to d=2 and d=3, plus the power-sector reporting protocol (`POWER_PROTOCOL.md`).
  No analytic eighth-order power-sector compensation exists; both packages integrate the power sector explicitly.
  Delivered only through `assembly/HANDOFF_assembly.json`.
- **PERF_NOTES.md:** append-only profiling results and kernel ideas, with dates and session tags.
- **Codex:** one claudex loop per package (gpt-6-astra, xhigh), run in parallel.

Rules:
- Edit only your own subfolder.
- Append to PERF_NOTES.md; never rewrite another session's entries.
- Record md5s when you hand an artifact over.
