# Public targets of LRI_C5_d3 (C5(3) and the d = 3 masters). Added for the public release; the research package
# itself has no Makefile. Run from this folder:  make -f public.mk test | replay | smoke | clean
# GFF/Makefile calls  make -C code/LRI_C5_d3 -f public.mk <target>.
#
# Every target works in .work/ (git-ignored) and never writes into the shipped files.
# Node: any machine with Python >= 3.8 and mpmath (sympy for test/replay, python-flint for smoke); one core.
#   test    ~5 s    exact d = 3 identities and Horn arrays (inputs/general_d3/check_exact.py, unchanged, in a copy),
#                   symbolic d = 3 specialization of gs:C5 (SymPy)
#   replay  ~10 s   reruns pslq_d3.py, compute_c5.py, hp_combine.py, wf_L3/final_form.py, wf_L3/tdform.py,
#                   wf_Z3/derive.py on the shipped records and recomputes every quoted number
#                   (../../results/closed_forms_3/LRI_C5_d3_quoted.json); PASS/FAIL table in .work/replay/REPLAY_c5_d3.md
#   smoke   ~25 s   fresh computations: Q3, P4(3), P5(3) at 90 digits (inputs/general_d3/d3_reduction.py) and K3 to about
#                   100 digits (wf_K3/k3flint.py, Arb); compared with the shipped 90-digit and 430-digit values
# The production runs (spectral masters at 50-110 digits, 160/250/430-digit masters) are in public/REPRODUCE.md.

PY     ?= python3
WORK   ?= .work
QUOTED ?= ../../results/closed_forms_3/LRI_C5_d3_quoted.json

export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1

.PHONY: test replay smoke clean

test:
	@rm -rf $(WORK)/test && mkdir -p $(WORK)/test/pkg/inputs/general_d3
	cp inputs/general_d3/*.py inputs/general_d3/horn_arrays.json $(WORK)/test/pkg/inputs/general_d3/
	cd $(WORK)/test/pkg && $(PY) inputs/general_d3/check_exact.py
	cmp $(WORK)/test/pkg/verification/general_d3/horn_arrays.json inputs/general_d3/horn_arrays.json
	@echo "test: check_exact.py passed and regenerated horn_arrays.json byte-identically"
	$(PY) public/replay_c5_d3.py --work $(WORK)/test --quoted $(QUOTED) --symbolic-only

replay:
	$(PY) public/replay_c5_d3.py --work $(WORK) --quoted $(QUOTED)

smoke:
	$(PY) public/smoke_c5_d3.py --work $(WORK)

clean:
	rm -rf $(WORK)
