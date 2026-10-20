# Public targets of lri_3d_window_indep: the clean-room re-implementation of the d = 3 window HT, written from the
# definition of the model without the production code (HT note, \HTnpDthreeIndep). Run from this folder:
# make -f public.mk <target>   (HT/Makefile runs make -C code/lri_3d_window_indep -f public.mk <target>).
# The session's scripts ship unchanged; everything public-specific is in public/.
#
# Python >= 3.10, numpy, scipy >= 1.15 (scipy.special.sph_harm_y). No numba, no compiler.
#
#   target    what                                                              measured runtime and node
#   test      structural checks + one fixed-coupling production point           10 s (symmetry AMD 8534P, Intel 6148)
#             (public/test_indep.py)
#   replay    the quoted agreement from the 23 shipped comparison records,      ~1 s, any OS (standard library)
#             checked against the production records in ../../data/HT_3d
#             (public/replay_indep.py); PASS/FAIL table
#   rerun     one full comparison (setup, fixed couplings, independent tuning)  L = 8: 1-3 min; L = 10: 1-4 min;
#             with run_compare.py; the 23 shipped ones are listed in tasks.txt  L = 12: 9 min to 3.1 h (Expanse shared,
#                                                                              4-8 cores, 16-24 GB requested)
#   clean     remove .work/
PY    ?= python3
WORK  ?= .work
DATA  ?= ../../data/HT_3d
L     ?= 8
X     ?= 0.7
MODE  ?= window

.PHONY: help test replay rerun clean

help:     ## list the targets
	@grep -E '^[a-z-]+:.*##' public.mk | sed 's/:.*##/:/'

test:     ## structural checks and one fixed-coupling comparison
	$(PY) -B public/test_indep.py

replay:   ## recompute the quoted agreement from results/cmp_*.json; PASS/FAIL table in .work/replay/
	$(PY) -B public/replay_indep.py --campaigns $(DATA)/campaigns --out $(WORK)/replay

rerun:    ## one comparison, e.g. make -f public.mk rerun L=10 X=0.6 MODE=window (writes .work/cmp_*.json)
	@mkdir -p $(WORK)
	$(PY) -B run_compare.py --L $(L) --x $(X) --mode $(MODE) --out $(WORK)/cmp_L$(L)_$(MODE)_x$(X).json

clean:    ## remove .work/
	rm -rf $(WORK)
