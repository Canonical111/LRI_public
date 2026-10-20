# Public targets of LRI_C5_general_d: the generic-dimensional reduction of the nonprimitive masters L_d and Z_d and the
# reduced C5(d) (note Section 20, session C62d), and the master K_d at generic d (note Section 21, K_general/, session C63d),
# with the end-to-end C5(1), C5(2), C5(3) and the independent checks of the top-mode theorem. The package is shipped as
# it was on 2026-10-03 (no git; files unchanged since). Run from this folder: make -f public.mk <target>. Paths are
# relative. Shipped files are never modified; outputs go to public/out/ (scripts that write their own records run in
# public/out/work*/). Reads ../LRI_C5_d3 (sibling package) and, if present, ../../note/ and
# ../../results/closed_forms_general/reduction_d/.
#
#   test           the package's own quick checks (jet engine, closed-form coefficients, sympy derivations, P4/L_d and Z_d at
#                  20-30 digits, the product-form top-mode check); about 90 s on one core; Python >= 3.10, mpmath, sympy
#   replay         Section 20 (public/replay.py: every quoted number from the records, plus a fast recompute of C5(1..3)
#                  end to end, the three-node K_d column, the d = 3 dictionary, the d = 1, 2 identities, the D_L identity,
#                  the top-mode summaries; about 45 s) and Section 21 (public/replay_K_d.py, C63d: every quoted K_d number
#                  from the records; about 2 s). Both run; the target fails if either fails.
#   replay-records the record part of the Section 20 replay only, and the K_d replay (a few seconds)
#   replay-Kd      the K_d replay alone (C63d)
#   smoke-Kd       the K_d replay plus a rerun of the position-space code kmb_flint.py at 40 digits (about 15 s; python-flint)
#   replay-full    recompute the Section 20 records with the package's scripts (60-digit samples, five-Horn and two-node
#                  codes at 50-90 digits, the C5 assembly at 8 dimensions, the pole-node check); about 1 core-hour, run on
#                  a cluster node (see CLUSTER_CHECKS.md of the release notes); PSLQ=1 adds the two PSLQ probes

PY      ?= python3
RESULTS ?= ../../results/closed_forms_general/reduction_d
NOTE    ?= ../../note/long_range_ising_condensed.tex
OUT     ?= public/out
PSLQ    ?=
export PYTHONDONTWRITEBYTECODE := 1
export OPENBLAS_NUM_THREADS := 1

.PHONY: help test replay replay-records replay-Kd smoke-Kd replay-full clean

help:            ## list the targets
	@grep -E '^[a-zA-Z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:            ## the package's quick checks, PASS/FAIL table (public/out/test.json)
	$(PY) -B public/run_tests.py

replay:          ## Sections 20 and 21: all quoted numbers from the records + fast recompute (public/out/)
	@rc=0; \
	$(PY) -B public/replay.py --results $(RESULTS) --note $(NOTE) --out $(OUT) || rc=1; \
	$(PY) -B public/replay_K_d.py --work $(OUT) || rc=1; \
	exit $$rc

replay-records:  ## the record part only (Section 20) and the K_d replay
	@rc=0; \
	$(PY) -B public/replay.py --results $(RESULTS) --note $(NOTE) --out $(OUT) --records-only || rc=1; \
	$(PY) -B public/replay_K_d.py --work $(OUT) || rc=1; \
	exit $$rc

replay-Kd:       ## Section 21 (K_d) from the records (C63d; public/out/replay_K_d/REPLAY_K_d.md)
	$(PY) -B public/replay_K_d.py --work $(OUT)

smoke-Kd:        ## the K_d replay plus kmb_flint.py at 40 digits for d = 1, 2, 3 (python-flint)
	$(PY) -B public/replay_K_d.py --work $(OUT) --recompute

replay-full:     ## recompute the Section 20 records (about 1 core-hour; cluster node; SLURM_CPUS_PER_TASK workers)
	$(PY) -B public/replay_full.py --out $(OUT) $(if $(PSLQ),--pslq,)

clean:
	rm -rf $(OUT)
