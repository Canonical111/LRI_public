First pass of the MSC-011 sector check (checker sha256 ccc0ab4b..., jobs 574531-574535, 574553-574554).
The checker's circle radii in the split variables used min(R_p, R_q) from the generator; after t_q = rho s this can
exceed the true analyticity radius (sector 141: rigorous bound 0.5 instead of 1), so the Taylor tables aliased:
sectors 141/180 differed from the engine by 1.8e-15 and 52/77 by 1.6e-18 at both levels 3 and 4; all other sectors
agreed to <= 2.4e-18 (most 1e-20..1e-22), sector 6 converged 3.6e-10 (level 2) -> 1.6e-20 (3) -> 1.1e-22 (4),
sector 73 2.1e-19 (3) -> 3.6e-23 (4). Superseded by the second pass with a rigorous (Rouche) radius bound.
