# Public targets for lri_2d_coeff_independent_check (d = 2: independent check of the coefficient solver, exact C2..C5(L),
# window corrections, descendant identities). Snapshot of 2026-10-14 (no git); public/SNAPSHOT.sha256 lists its files.
# Usage: make -f public.mk <target>   (run from HT_Pert/code/lri_2d_coeff_independent_check; relative paths only)
PYTHON ?= python3
WORKERS ?= 4
.PHONY: help verify-snapshot test smoke replay replay-full fetch-data clean

help:
	@echo "verify-snapshot  sha256 of every snapshot file (public/SNAPSHOT.sha256; scrubbed files in public/SCRUBBED.txt: presence only)"
	@echo "test             verify-snapshot + rerun every code at small cutoff and compare with the shipped outputs (public/test_p2.py, ~2-3 min; needs python-flint)"
	@echo "smoke            the two fastest exact reruns of test (rs_exact L = 4, ce_wc L = 4; ~30 s)"
	@echo "replay           recompute every quoted d = 2 number from the shipped records (public/replay_p2.py, p2.*, ~10 s)"
	@echo "replay-full      rerun the shipped fit/check scripts on a scratch copy and compare their outputs (~1 min)"
	@echo "fetch-data       nothing is hosted for this package"

verify-snapshot:
	$(PYTHON) public/verify_snapshot.py

test: verify-snapshot
	$(PYTHON) public/test_p2.py --workers $(WORKERS)

smoke:
	$(PYTHON) public/test_p2.py --workers $(WORKERS) --only rs_exact,ce_wc

replay:
	$(PYTHON) public/replay_p2.py

replay-full:
	$(PYTHON) public/replay_full.py

fetch-data:
	@echo "Nothing to fetch: every record the replays read is in git (largest file 3.4 MiB)."

clean:
	rm -rf .work
