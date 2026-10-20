| Target | Route | SE (target) | r: free L8 / power L8 | s: free L8 / prim / power L8 | Start kept | Core-h (freeze, η 0.306) | **Lane core-h** (η 0.915) | 570241 (23540b2) | Mac (77fab71 test) | Plan: tasks / checkpoints / indices | Plan wall, RSS | Caps |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|---|---|
| 1e-3 | exact | 46.00 (46.00) | 32 / 32 | 1 / 1 / 1 | smallest | 5,083 | **1,702** | 1,738 | 1,702 | 2,111,808 / 8,324 / 161 | 173 s, 0.40 GiB | all hold |
| 1e-3 | route (b) `dd+mp256` (reoptimized) | 46.00 (46.00) | 32 / 32 | 1 / 8 / 1 | smallest | 1,906 | **638** | 923 | 638 | 2,135,296 / 8,378 / 70 | 132 s, 0.40 GiB | all hold |
| 5e-4 | exact | 23.00 (23.00) | 128 / 32 | 1 / 4 / 1 | smallest | 17,139 | **5,740** | 5,856 | 5,740 | 5,365,152 / 21,148 / 496 | 366 s, 0.84 GiB | all hold |
| 5e-4 | route (b) `dd+mp256` (kept exact allocation) | 23.00 (23.00) | 128 / 32 | 1 / 4 / 1 | smallest | 6,690 | **2,241** | 3,322 | 2,241 | 5,356,096 / 21,035 / 205 | 510 s, 0.84 GiB | all hold |
| 2.5e-4 | exact | 11.50 (11.50) | 128 / 64 | 4 / 16 / 2 | smallest | 68,556 | **22,961** | 23,423 | 22,961 | 5,890,112 / 23,793 / 1,937 | 475 s, 0.89 GiB | all hold |
| 2.5e-4 | route (b) `dd+mp256` (kept exact allocation) | 11.50 (11.50) | 128 / 64 | 4 / 16 / 2 | smallest | 26,761 | **8,963** | 13,289 | 8,963 | 5,652,416 / 22,513 / 767 | 548 s, 0.84 GiB | all hold |
| 1.35e-4 | exact | 6.21 (6.21) | 128 / 128 | 16 / 64 / 2 | smallest | 222,654 | **74,573** | 76,623 | 74,573 | 8,511,360 / 36,207 / 6,254 | 641 s, 1.31 GiB | all hold |
| 1.35e-4 | route (b) `dd+mp256` (kept exact allocation) | 6.21 (6.21) | 128 / 128 | 16 / 64 / 2 | smallest | 87,564 | **29,328** | 33,978 | 29,328 | 6,395,520 / 26,191 / 2,470 | 595 s, 0.90 GiB | all hold |

| Target | Route (b): re-optimized (SE) | Exact design kept, re-costed (SE) | Chosen | 570241 route (b) (SE) | 570241 exact allocation kept | Mac: re-optimized / kept / chosen |
|---|---:|---:|---|---:|---:|---|
| 1e-3 | 638 (46.00) | 646 (46.00) | reoptimized | 923 (35.83) | 669 | 638 / 646 / reoptimized |
| 5e-4 | 2,554 (23.00) | 2,241 (23.00) | kept exact allocation | 3,322 (18.53) | 2,309 | 2,554 / 2,241 / kept exact allocation |
| 2.5e-4 | 10,215 (11.50) | 8,963 (11.50) | kept exact allocation | 13,289 (9.26) | 9,236 | 10,215 / 8,963 / kept exact allocation |
| 1.35e-4 | 31,371 (6.21) | 29,328 (6.21) | kept exact allocation | 33,978 (5.91) | 30,067 | 31,371 / 29,328 / kept exact allocation |

| Target | Route | Start | Greedy: lane core-h (SE) | Final: lane core-h (SE) | Prune steps | Lattice boxes / moves | Caps |
|---|---|---|---:|---:|---:|---|---|
| 1e-3 | exact | smallest (kept) | 1,738 (44.21) | 1,702 (46.00) | 25 | 2 / 0 | ok |
| 1e-3 | exact | largest | 3,963 (32.63) | 1,702 (46.00) | 14 | 3 / 2 | ok |
| 1e-3 | route (b), re-optimized | smallest (kept) | 923 (35.83) | 638 (46.00) | 32 | 2 / 1 | ok |
| 1e-3 | route (b), re-optimized | largest | 835 (40.12) | 638 (46.00) | 29 | 2 / 1 | ok |
| 5e-4 | exact | smallest (kept) | 5,856 (22.61) | 5,740 (23.00) | 9 | 2 / 1 | ok |
| 5e-4 | exact | largest | 5,856 (22.61) | 5,740 (23.00) | 9 | 2 / 1 | ok |
| 2.5e-4 | exact | smallest (kept) | 23,423 (11.31) | 22,961 (11.50) | 9 | 2 / 1 | ok |
| 2.5e-4 | exact | largest | 23,423 (11.31) | 22,961 (11.50) | 9 | 2 / 1 | ok |
| 1.35e-4 | exact | smallest (kept) | 76,623 (6.08) | 74,573 (6.21) | 9 | 4 / 3 | ok |
| 1.35e-4 | exact | largest | 76,623 (6.08) | 74,573 (6.21) | 9 | 4 / 3 | ok |

A route-(b) bundle that keeps the exact design records the exact search (the exact rows of the same target); its re-optimized branch is recorded in route_b_choice by cost and SE only (the second table).
