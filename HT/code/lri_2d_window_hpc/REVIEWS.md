# Reviews of lri_2d_window_hpc (summary; raw review logs are not published)

Roles: the Expanse layer, fixes and campaigns were planned and built by a Claude Code session (Claude Opus 5.5). Plan
reviews and final-code inspections were done by OpenAI GPT-6 astra through the Codex CLI (effort xhigh), each
inspection in a fresh session. The numerical package was delivered before this work as `lri_2d_window_hpc_optimized.zip`
(baseline commit 4afd379), written by OpenAI GPT-6 astra (model stated by the author, 2026-10-14); its `reference/` port
and `upstream/` implementation come from the earlier delivery `lri_2d_dressed_window_basis.zip`, also written by OpenAI
GPT-6 astra via ChatGPT (model stated by the author, 2026-10-14). See PROVENANCE.

## Plan review (2026-10-07), 7 rounds
| Round | Verdict | Findings |
|---|---|---|
| 1 | REVISE | 8 (1 high, 6 medium, 1 low) |
| 2 | REVISE | 4 (3 medium, 1 low) |
| 3 | REVISE | 7 (3 high, 4 medium), on the plan and the draft code |
| 4 | REVISE | 8 (2 high, 5 medium, 1 low) |
| 5 | REVISE | 2 medium (malformed persisted values; graceful-stop drill) |
| 6 | **APPROVED** | none (plan revision 6) |
| 7 | REVISE | 1 medium (malformed claim/owner readers), fixed; not re-reviewed (round budget used) |

The planned budget was 5 rounds; the author granted two more after round 5.

## Final-code inspections (fresh sessions)
| Inspection | Code | Verdict | Findings | Fixed in |
|---|---|---|---|---|
| 1 | 914141f | REVISE | 8 (1 high: IR-01; 6 medium; 1 low) | 62b0c45 |
| 2 | 62b0c45 | REVISE | 6 (1 high; 4 medium; 1 low) | a0eb92f |
| 3 | a0eb92f | REVISE | 4 (1 high: release/receipt binding; 3 medium: Jacobian-condition checkpoint, basis integrity exit code, drills) | **889a968** |

The author granted the third inspection. **The fix-round-3 edits (889a968, the production code) were not inspected by
Codex.** They touch the release/receipt binding, the checkpoint of the Jacobian condition before the line search (iterates
and stopping decisions unchanged), the exit code of a basis-integrity failure, and the drill scripts. 110 tests and a
replay of the package's reference points (max |Δ| ≤ 1.1e-12, including x = 0.35, N = 8) passed on Expanse for this
release (validation receipt of 2026-10-07).

## Host finding HF-01 (numerics)
The optimized package's ground-only top-window fixed point, followed by a re-check, aborted deterministically at
x = 0.35, N = 8 (any thread count). Fix (62b0c45): when the re-check misses the unchanged gate, continue with the
reference algorithm's k0-root iteration. The acceptance gate is unchanged; x = 0.35, N = 8 then reproduces the reference
to 3e-13. Reviewed in inspection 2.

## Opt-in finite-difference Jacobian (afe69ab; shipped as public/afe69ab.diff)
Built after the production Newton solves at N = 24, Δσ = 0.125 and 0.126 stalled. Codex inspection: REVISE (2 findings:
metadata of the executed Jacobian; order of the metrics writer), fixed in afe69ab, then **APPROVED** by a fresh
inspection. It changes only the Newton direction when `--jacobian fd` is given; `DensitySolver.spectrum`, the residual,
the gates and every production record are unaffected. The valley scan ran on this release but calls only `spectrum`.

## Overruled recommendations
None. Every plan and inspection finding was accepted and fixed.

## Not reviewed by Codex
- The fix-round-3 edits of 889a968 (above).
- `public/scan_valley.py` (the N = 24 valley scan), `public/valley_expanse/`, and the public layer (`public.mk`,
  `public/replay_d2.py`, `public/smoke_check.py`, `public/verify_manifest.py`). The valley scan's smoke run at N = 8
  recovered the production root to 1e-11 with f1 = −4e-12; at N = 24 its first evaluation at the best Newton point
  reproduced the residual of the stalled FD-Newton run (|f2| bit-identical at Δσ = 0.126).
- The results: the finite-N statements and the fold estimate were not given a separate results review.
