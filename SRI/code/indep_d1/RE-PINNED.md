# Records scrubbed after the results and re-pinned (indep_d1)

By the author's decision of 2026-10-15, files of this package that named the personal desktop (the machine that ran C8 tier A, the tier-B/C runs on a personal desktop (directory suffix `_can`), most strict re-checks and the C8 archive-free assembly job) were scrubbed before publication. In the two hash-bound result records only the machine word was replaced; inside the re-pinned set every SHA-256 of another re-pinned file (the `.sha256` files, the comparison files, the reports and documents that quote them) was replaced by its new value, so that `assembly/compare_archive_C8.py` and `make test` pass on the published bytes. No number changed: every json file was compared value by value. The reports `RESULTS.md` and `RESULTS_C8.md` are the outputs of the published `make_report*.py` on the published json files (checked by `make replay`); `RESULTS_C8_tierA.md` also keeps its hand-added status note. Documents and code that used the word as the machine name were pre-scrubbed here (machine word, data path, the public scrub rules); technical terms that share the word are unchanged. `public/SNAPSHOT.sha256` keeps the original pins; `make test` accepts a file that matches its original pin or the published SHA-256 of `RE-PINNED.json`. The project's own reports quote the original hashes where they were not re-pinned.

| published file | kind | original SHA-256 | published SHA-256 | substitutions | re-pinned hashes | changed lines |
|---|---|---|---|---|---|---|
| `RESULTS_C8_independent.json` | hash-bound record | `83065f0a874a1288…` | `6265093dc6f8b709…` | 4 | 1 | 5 of 8552 |
| `RESULTS_C8_independent_tierA.json` | hash-bound record | `493a0c93797f0195…` | `f80e0e6d6adcc128…` | 4 | 0 | 2 of 3636 |
| `RESULTS_C8_independent.json.sha256` | hash cascade | `1547dd2bf71647ca…` | `87f35a9ea2981668…` | 0 | 1 | 1 of 1 |
| `RESULTS_C8_independent_tierA.json.sha256` | hash cascade | `4d28ad77b9c59cd9…` | `628812723be0a0b5…` | 0 | 1 | 1 of 1 |
| `RESULTS_C8_archive_comparison.json` | hash cascade | `9e87370293de4204…` | `5439d4dd8dc6c610…` | 0 | 1 | 1 of 535 |
| `RESULTS_C8_archive_comparison_tierA.json` | hash cascade | `7522b81d7eb648e0…` | `e4f36124aa293b3e…` | 0 | 1 | 1 of 339 |
| `RESULTS.md` | report | `2a64f945f06189f5…` | `e8a2872a062d7212…` | 1 | 0 | 1 of 365 |
| `RESULTS_C8.md` | report | `a3d3dc117d2daf01…` | `614db0406972b79d…` | 14 | 1 | 12 of 415 |
| `RESULTS_C8_tierA.md` | report | `3ad1ea7be5137dc8…` | `6d7c610c0dfb2578…` | 10 | 1 | 9 of 327 |
| `assembly/out/compute.json` | report | `cffe83ecfbc065b2…` | `e82f8590cf8a18f8…` | 1 | 0 | 1 of 11 |
| `assembly/README.md` | doc/code (pre-scrubbed) | `abd3878c6606b032…` | `a908ecf0e03db5d9…` | 8 | 2 | 8 of 219 |
| `assembly/make_report_C8.py` | doc/code (pre-scrubbed) | `d4c54b031f67e39d…` | `8f0682ad0074e1c5…` | 14 | 0 | 12 of 635 |
| `assembly/make_report_C8_tierA.py` | doc/code (pre-scrubbed) | `d015109fa299ed13…` | `52545dc1b3085c37…` | 10 | 0 | 9 of 473 |
| `assembly/run_assembly_C8.py` | doc/code (pre-scrubbed) | `f18f0d47351a07e9…` | `94228639c1ec16ba…` | 3 | 0 | 3 of 987 |
| `assembly/run_assembly_C8_tierA.py` | doc/code (pre-scrubbed) | `32ac094a77cd1c9b…` | `54abdd4cac8b576e…` | 4 | 0 | 3 of 583 |
| `engine/README.md` | doc/code (pre-scrubbed) | `7c8f49514e79123c…` | `90735f124db1d9e0…` | 68 | 0 | 56 of 932 |
| `engine/PRODUCTION_TIER1.md` | doc/code (pre-scrubbed) | `6f9bbdfae9cba18e…` | `b26834041f266ad2…` | 5 | 0 | 5 of 218 |
| `engine/PRODUCTION_C8.md` | doc/code (pre-scrubbed) | `668249b52f83f0d7…` | `5bf080b253f31319…` | 103 | 1 | 92 of 857 |
| `engine/py/make_spec_C8.py` | doc/code (pre-scrubbed) | `0c3a36380a550d4f…` | `bcde10ae1f70aa6a…` | 3 | 0 | 3 of 312 |
| `engine/py/plan_C8.py` | doc/code (pre-scrubbed) | `841658ccd120aa66…` | `5f0469e433b0b87a…` | 3 | 0 | 2 of 470 |
| `engine/py/split_C8BC.py` | doc/code (pre-scrubbed) | `6a6bc16555c4928d…` | `4abd58ef5a647d4a…` | 1 | 0 | 1 of 62 |
| `engine/specs/production_C8_tierB_topup1.json` | doc/code (pre-scrubbed) | `d5f3b69e2b1da963…` | `9b622a42fa1a72d5…` | 2 | 0 | 1 of 32 |

Full hashes and per-file substitution counts: `RE-PINNED.json`.
