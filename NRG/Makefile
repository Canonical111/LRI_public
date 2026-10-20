# Makefile for the public NRG folder. Run every target from NRG/.
#
# The analysis scripts locate their inputs and outputs relative to the folder that contains code/ (two levels above
# code/analysis). Every target except `note` therefore runs inside a hidden workspace, .work/ (git-ignored): the analysis
# scripts are copied there, the solver, records, inputs and independent outputs are symlinked, and everything is
# written below .work/. Nothing under code/, inputs/, data/, results/, independent_check*/ or method_comparison/ is ever
# written. `make clean` removes .work/.
#
# Times are for one core of a recent laptop. Production (REPRODUCE.md §5) needs a Slurm cluster.
#
# WORK must be a direct subdirectory of NRG/ (the workspace links back with ../../). The workspace is rebuilt whenever a
# file of code/analysis/ changes. `make note` rebuilds note/lri_nrg_1d_note.pdf in place (the PDF bytes change; the text
# does not).

PY      ?= python3
WORK    ?= .work
MCSCAN  ?= ../MC/data/1d/scan_data/FIT_V3_SCAN.json
R        = $(WORK)/reproduced
STAMP    = $(WORK)/.assembled
CODE     = code/lri_spin_boson_hpc
export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: help test replay smoke note fetch-data verify clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/:/'

$(STAMP): $(wildcard code/analysis/*.py)
	rm -rf $(WORK) && mkdir -p $(WORK)/code $(WORK)/data $(R)
	cp -R code/analysis $(WORK)/code/analysis
	ln -s ../../$(CODE) $(WORK)/code/lri_spin_boson_hpc
	ln -s ../inputs $(WORK)/inputs
	ln -s ../independent_check $(WORK)/independent_check
	ln -s ../../data/records $(WORK)/data/records
	ln -s ../../data/lane_logs $(WORK)/data/lane_logs
	ln -s ../../data/job_accounting.txt $(WORK)/data/job_accounting.txt
	@touch $@

test:            ## fast tests (~75 s): 85 solver tests, code checksum list, 38 checks of the independent solver
	cd $(CODE) && $(PY) tests/verify_manifest.py
	cd $(CODE) && $(PY) -m pytest -q -p no:cacheprovider tests
	cd independent_check && $(PY) selftest.py

replay: $(STAMP) ## recompute every number of results/ and note/ from the records, then verify (~20 s; needs the ../MC scan table, see MCSCAN)
	$(PY) $(WORK)/code/analysis/summarize.py
	$(PY) $(WORK)/code/analysis/build_tables.py
	$(PY) $(WORK)/code/analysis/make_figures.py
	$(PY) independent_check_compare/compare.py --root $(WORK) --out $(WORK)/independent_check_compare > /dev/null
	$(PY) independent_check_compare/trusted_windows.py --root $(WORK) --out $(WORK)/independent_check_compare > /dev/null
	$(PY) method_comparison/compare_methods.py --root $(WORK) --mc $(MCSCAN) --out $(WORK)/method_comparison > /dev/null
	$(PY) $(WORK)/code/analysis/note_numbers.py --root $(WORK)
	$(PY) $(WORK)/code/analysis/check_figures.py --root $(WORK)
	$(MAKE) verify

verify:          ## compare .work/ with the released files, verify/expected.json and the paper's NRG numbers -> .work/reproduced/VERIFY.md
	$(PY) verify/verify.py --work $(WORK)

smoke: $(STAMP)  ## both solvers on a small critical search, compared with verify/smoke_expected.json (~15 s)
	rm -rf $(R)/smoke && mkdir -p $(R)/smoke
	cd $(CODE) && PYTHONPATH=src $(PY) -m lri_spin critical --s .8 --Lambda 3 --keep 16 --nb 6 --nsites 40 \
	   --memory-limit-gib 2 --output-dir $(CURDIR)/$(R)/smoke/production > $(CURDIR)/$(R)/smoke/production.log
	$(PY) independent_check/run_config.py toy40 --outdir $(R)/smoke/independent > $(R)/smoke/independent.log
	$(PY) verify/smoke_check.py $(R)/smoke

note:            ## rebuild note/lri_nrg_1d_note.pdf in place from the released tables and figures (three passes)
	cd note && for i in 1 2 3; do pdflatex -interaction=nonstopmode -halt-on-error lri_nrg_1d_note.tex >/dev/null || exit 1; done
	@rm -f note/*.aux note/*.log note/*.out note/*.toc

fetch-data:      ## nothing to fetch: every record is in git
	@echo "fetch-data: nothing to do. All 197 production records are in data/records (see data/DATA.md)."

clean:           ## remove the workspace and every reproduced output
	rm -rf $(WORK)
