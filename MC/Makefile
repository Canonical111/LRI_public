# Makefile of the MC folder. Run every target from MC/ (see REPRODUCE.md).
#
# The evaluators bind themselves, calibrate_p1.py and the protocols by SHA-256, and find their inputs relative to the layout they ran in
# during production. Every target therefore runs inside a hidden workspace, .work/ (git-ignored), built by
# code/package_tools/assemble_workspace.py in that layout: code copied byte-identically, data and results linked. Outputs go to
# .work/reproduced/. Nothing under code/, data/, protocols/ or results/ is ever written. A change to any file under code/ or protocols/
# rebuilds the workspace and discards earlier outputs; `make clean` does the same by hand.
#
# Heavy targets (calibration, refit1d, smoke-pilots) belong on a cluster node, e.g. `srun -c 16 --mem=16G make calibration WORKERS=16`.

PY      ?= python3
WORK    ?= .work
WORKERS ?= 8
DS      ?= 0.05
CITED   ?= 0.05 0.0875 0.1727335
FETCH   ?= all
R        = $(WORK)/reproduced
STAMP    = $(WORK)/.assembled
SOURCES := $(shell find code protocols -type f ! -name '*.pyc' 2>/dev/null)
# --index-remap: the analysis records name the absolute histogram-index path of the machine that wrote them; read it from the records
IDX2     = $(shell $(PY) code/package_tools/index_prefix.py 2)
IDX3     = $(shell $(PY) code/package_tools/index_prefix.py 3)
AMD      = LRI_2d3d_reanalysis/AMENDMENT_PROFILED_SIGMA.md
CAL      = LRI_2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json
EV2      = --primary LRI_2d_MC/prod/analysis_b2000_s* --reblock LRI_2d_MC/prod/analysis_b1000_s* LRI_2d_MC/prod/analysis_b4000_s* \
           --plan LRI_2d_MC/FIT_MODEL_2D.md --manifest LRI_2d_MC/prod/manifest.json --centers LRI_2d_MC/production_centers.csv \
           --index-remap $(IDX2)=LRI_2d_MC/prod/
EV3      = --primary LRI_3d_MC/prod/analysis_54387089_b2000_s* --reblock LRI_3d_MC/prod/analysis_54387089_b1000_s* \
           LRI_3d_MC/prod/analysis_54387089_b4000_s* --plan LRI_3d_MC/FIT_MODEL_3D.md --manifest LRI_3d_MC/prod/manifest.json \
           --centers LRI_3d_MC/production_centers_3d.csv --snapshot 54387089 --index-remap $(IDX3)=LRI_3d_MC/prod/
export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

.PHONY: help test replay smoke smoke-pilots smoke-stat fetch-data note clean build eval-fixed eval-p1 calibration oned-xcheck \
        scan1d tables1d note-tables refit1d refit-cited verify

help:            ## list the targets
	@grep -E '^[a-z0-9-]+:.*##' Makefile | sed 's/:.*##/:/'

$(STAMP): $(SOURCES)
	$(PY) code/package_tools/assemble_workspace.py $(WORK) --force
	@touch $@

# ---------------------------------------------------------------- tiers
test: build      ## fast tests (2.5-8 min): 1D protocol tests and the 56 amendment-P1 tests
	cd $(WORK)/lri_cluster && $(PY) tests/test_fit_v3.py && $(PY) tests/test_union.py
	cd $(WORK) && $(PY) -m pytest -q -p no:cacheprovider LRI_2d3d_reanalysis/tests/

replay: $(STAMP) ## recompute every published number from data/ and compare with results/ (CI); VERIFY.md is always written
	@s=0; for t in eval-fixed eval-p1 scan1d tables1d oned-xcheck refit-cited; do $(MAKE) $$t || s=1; done; \
	  $(MAKE) verify || s=1; $(MAKE) note-tables || s=1; \
	  if [ $$s -ne 0 ]; then echo "replay: at least one step failed (see above and $(R)/VERIFY.md)"; fi; exit $$s

smoke: build     ## engine validation with expected output: 1D tiny campaign + bitwise resume; 2D/3D exact enumeration + bitwise restart (CI)
	cd $(WORK)/lri_cluster && $(PY) tests/test_runner.py && $(PY) tests/test_engine_1d.py
	$(MAKE) -C $(WORK)/LRI_2d_MC/code test

smoke-pilots: build   ## fresh 2D/3D pilots through prepare -> run -> pack -> analyse (minutes on WORKERS cores; no expected-output file yet)
	bash $(WORK)/LRI_2d_MC/code/reproduce_pilots.sh $(abspath $(R))/pilots $(WORKERS)

smoke-stat:      ## not implemented yet: short 1D/2D runs compared with production values (REPRODUCE.md §4, S3/S4)
	@echo "smoke-stat is not implemented yet (REPRODUCE.md §4, S3/S4)"; exit 2

fetch-data:      ## download and unpack what is not in git (data/HOSTED.json): FETCH=refit (1D block archives + merged summaries), fits, all
	$(PY) code/package_tools/fetch_data.py --what $(FETCH)

note:            ## compile note/lri_mc_note.pdf (three passes settle the cross-references)
	cd note && for i in 1 2 3; do pdflatex -interaction=nonstopmode -halt-on-error lri_mc_note.tex >/dev/null || exit 1; done
	@rm -f note/*.aux note/*.log note/*.out note/*.toc

clean:           ## remove the workspace and every reproduced output
	rm -rf $(WORK)

# ---------------------------------------------------------------- specialist targets
build: $(STAMP)  ## compile the engines (1D reference and specialised engines; 2D/3D sampler and the old reference engine)
	$(MAKE) -C $(WORK)/lri_cluster
	$(MAKE) -C $(WORK)/LRI_2d_MC/code bin/lri_mc bin/lri_reference

eval-fixed: $(STAMP)   ## 2D/3D labels under the frozen rule -> reproduced/eval_fixed_{2d,3d}
	rm -rf $(R)/eval_fixed_2d $(R)/eval_fixed_3d
	cd $(WORK) && $(PY) LRI_2d_MC/evaluate_2d.py $(EV2) --out reproduced/eval_fixed_2d
	cd $(WORK) && $(PY) LRI_3d_MC/evaluate_3d.py $(EV3) --out reproduced/eval_fixed_3d

eval-p1: $(STAMP)      ## 2D/3D labels under amendment P1 with the released calibration -> reproduced/eval_p1_{2d,3d}
	rm -rf $(R)/eval_p1_2d $(R)/eval_p1_3d
	cd $(WORK) && $(PY) LRI_2d_MC/evaluate_2d.py $(EV2) --sigma-rule profiled --calibration $(CAL) --amendment $(AMD) --out reproduced/eval_p1_2d
	cd $(WORK) && $(PY) LRI_3d_MC/evaluate_3d.py $(EV3) --sigma-rule profiled --calibration $(CAL) --amendment $(AMD) --out reproduced/eval_p1_3d

calibration: $(STAMP)  ## amendment-P1 calibration from scratch (1780 tasks, ~7 min on 16 cores) -> reproduced/calibration
	rm -rf $(R)/calibration
	cd $(WORK) && $(PY) LRI_2d3d_reanalysis/calibrate_p1.py reproduced/calibration --workers $(WORKERS) --sets 2000 --draws 500

oned-xcheck: $(STAMP)  ## 1D cross-check study at Delta_sigma = 0.15, 0.175 (note Table 8) -> reproduced/oned_xcheck
	rm -rf $(R)/oned_xcheck
	cd $(WORK) && $(PY) LRI_2d3d_reanalysis/oned_xcheck/check_1d_xcheck.py lri_cluster reproduced/oned_xcheck

scan1d: $(STAMP)       ## the 20-point 1D table from the per-coupling records -> reproduced/1d_scan
	mkdir -p $(R)/1d_scan
	cd $(WORK)/lri_cluster && $(PY) scan_v3_report.py scanA_exp/scan_data --out ../reproduced/1d_scan/FIT_V3_SCAN.md

tables1d: $(STAMP)     ## 1D table rows and figures -> .work/LRI_1d_MC_report/{tables,figures}
	cd $(WORK)/LRI_1d_MC_report && $(PY) scripts/make_tables_and_figure.py

note-tables: $(STAMP)  ## regenerate every table body and plot coordinate of the note and check each appears verbatim in it
	$(PY) code/package_tools/make_note_tables.py $(R)/note_tables --check note/lri_mc_note.tex

refit1d: $(STAMP)      ## full 1D fitting stage for one coupling: make refit1d DS=0.05 WORKERS=16 (needs fetch-data; 6-156 s on 20 cores)
	PY=$(PY) bash code/package_tools/refit_1d_point.sh $(WORK) $(DS) $(WORKERS)

refit-cited: $(STAMP)  ## refit the couplings cited in the paper if their block archives and merged summaries are present; otherwise skip
	@for ds in $(CITED); do \
	  ok=1; for b in 2048 4096 8192; do ls -d data/1d/scan_data/ds$$ds/stage*_an_b$${b}_* data/1d/scan_data/ds$$ds/merged_b$${b}_* >/dev/null 2>&1 || ok=0; done; \
	  if [ $$ok -eq 1 ]; then \
	    [ -d $(R)/1d_refit/ds$$ds ] || PY=$(PY) bash code/package_tools/refit_1d_point.sh $(WORK) $$ds $(WORKERS) || exit 1; \
	  else echo "refit-cited: ds$$ds inputs not fetched (make fetch-data), skipped"; fi; done

verify:          ## compare everything reproduced so far with results/ and data/ -> .work/reproduced/VERIFY.md (FAIL exits non-zero)
	$(PY) code/package_tools/compare_outputs.py $(WORK)
