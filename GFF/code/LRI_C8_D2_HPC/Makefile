CXX ?= g++
# User-adjustable hooks. OPTFLAGS keeps -O3 when CXXFLAGS or CPPFLAGS add include paths; the numerical flags in
# C8_REQUIRED are always appended and, like the compile commands below, cannot be overridden from the command line.
# Default settings give exactly C7(2)'s delivered commands with the C8 names
# (g++ -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math src/c8d2_integrate.cpp -lquadmath [-lgmp] -o ...).
OPTFLAGS ?= -O3
CPPFLAGS ?=
CXXFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
# Numerics profile (PLAN D1, A-FLAG-1; Stage 4c). NUMERICS=exact (the default) is the exact path: every default target
# and command below is unchanged word for word, and no file of src/numerics/ is ever included. `make gmp
# NUMERICS=<p>[,<p>...]` (or <p>+<p>...) builds ONLY the opt-in executable bin/c8d2_gmp_<name>, where <name> is the
# named profiles in the canonical order dd, mp256, exp1 joined by '+' (NUMERICS=exp1,dd -> bin/c8d2_gmp_dd+exp1; the
# all-profile combination is bin/c8d2_gmp_dd+mp256+exp1). It is the gmp command plus -DC8_NUMERICS and one
# -DC8_NUMERICS_<P> per profile (src/kernel.hpp then includes src/numerics/numerics.hpp, which includes <p>.hpp) and
# the profile's own flags NX_FLAGS_<p>, placed before the required numerical flags so that those stay last. Its
# --describe and native JSON say "numerics":"<name>", the name `production.py plan --numerics` requires. R4d (mpconv)
# is not implemented (host decision 2026-10-04: <= 0.11% of the time measured). Profiles exist for the gmp backend only.
NUMERICS ?= exact
override NX_KNOWN = dd mp256 exp1
override NX_MACRO_dd = DD
override NX_MACRO_mp256 = MP256
override NX_MACRO_exp1 = EXP1
# Per-profile compiler flags, set by the profile's developer: dd needs the hardware fma of its error-free products
# (A-FLAG-4: AVX2/FMA in this profile only; -ffp-contract=off stays in force, so every fma is an explicit one).
override NX_FLAGS_dd = -mavx2 -mfma
override NX_FLAGS_mp256 =
override NX_FLAGS_exp1 =
ifeq ($(NUMERICS),exact)
override NX_NAME = exact
else
override NX_comma = ,
override NX_empty =
override NX_space = $(NX_empty) $(NX_empty)
override NX_RAW = $(strip $(subst +, ,$(subst $(NX_comma), ,$(NUMERICS))))
ifeq ($(NX_RAW),)
$(error NUMERICS='$(NUMERICS)': name a profile ($(NX_KNOWN)) or leave NUMERICS unset for the exact path)
endif
ifneq ($(filter exact,$(NX_RAW)),)
$(error NUMERICS=$(NUMERICS): exact is the default path and does not combine with an opt-in profile)
endif
ifneq ($(filter mpconv,$(NX_RAW)),)
$(error NUMERICS=$(NUMERICS): R4d (mpconv) is not implemented (host decision 2026-10-04, <= 0.11% measured); the combination is dd,mp256,exp1)
endif
ifneq ($(filter-out $(NX_KNOWN),$(NX_RAW)),)
$(error NUMERICS=$(NUMERICS): unknown profile(s) $(filter-out $(NX_KNOWN),$(NX_RAW)); the opt-in profiles are $(NX_KNOWN) (PLAN A-FLAG-1))
endif
ifneq ($(words $(NX_RAW)),$(words $(sort $(NX_RAW))))
$(error NUMERICS=$(NUMERICS): a profile is named twice)
endif
override NX_LIST = $(filter $(NX_RAW),$(NX_KNOWN))
override NX_NAME = $(subst $(NX_space),+,$(NX_LIST))
override NX_EXE = bin/c8d2_gmp_$(NX_NAME)
override NX_DEFS = -DC8_NUMERICS $(foreach p,$(NX_LIST),-DC8_NUMERICS_$(NX_MACRO_$(p)))
override NX_FLAGS = $(strip $(foreach p,$(NX_LIST),$(NX_FLAGS_$(p))))
# A profile changes the gmp worker only: every other goal (the default `all`, decimal, the diagnostic, sanitizer and
# test targets) would silently build the exact path, so it is refused.
ifneq ($(filter-out gmp $(NX_EXE) inputs clean,$(or $(MAKECMDGOALS),all)),)
$(error NUMERICS=$(NUMERICS) applies to `make gmp` only (it builds $(NX_EXE)); build the exact path without NUMERICS)
endif
endif
override C8_REQUIRED = -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math
# LDFLAGS and LDLIBS follow the required flags in the compile-and-link command, so they may hold link-only words;
# a compiler option there (e.g. -O0 or -ffast-math) would override the required flags.
override C8_LINK_ONLY = -L% -l% -Wl,% -pthread -static% -rdynamic -fuse-ld=% %.a %.so %.o
override C8_BAD_LINK = $(strip $(filter-out $(C8_LINK_ONLY),$(LDFLAGS) $(LDLIBS)))
ifneq ($(C8_BAD_LINK),)
$(error LDFLAGS/LDLIBS may hold only link options (-L* -l* -Wl,* -pthread -static* -rdynamic -fuse-ld=* *.a *.so *.o), not: $(C8_BAD_LINK). Put compiler options in CPPFLAGS, OPTFLAGS or CXXFLAGS)
endif
PYTHON ?= python3
# GMP_PREFIX (Stage 4b R4f; opt-in, unset by default): build the GMP-linked executables (bin/c8d2_gmp, the gmp
# diagnostic and sanitizer builds, the probe) against the GMP installed under this absolute prefix, for example a
# node-tuned build of the same GMP version (docs/PERFORMANCE.md, "R4f"). It puts -I$(GMP_PREFIX)/include ahead of
# CPPFLAGS and -L$(GMP_PREFIX)/lib -Wl,-rpath,$(GMP_PREFIX)/lib -Wl,--disable-new-dtags ahead of LDFLAGS. The rpath
# is a DT_RPATH (on Expanse joined by the lib64 that Spack's GCC adds to every executable), which the dynamic loader
# searches before LD_LIBRARY_PATH, so an environment that lists another libgmp.so.10 (slurm/env_expanse.sh lists
# Spack's) cannot swap the library at run time. Unset, every command is the
# default one, word for word. bin/c8d2_decimal and bin/c8d2_inspect never link GMP and ignore it. make c7ref ignores
# it too, but it does link GMP: it builds C7(2)'s reference workers bin/ref/c7d2_decimal and bin/ref/c7d2_gmp, the
# latter with the reference Makefile's plain -lgmp, resolved by the toolchain's normal library search (and at run time
# by the loader's), so its library provenance matters to the replay (Z18, Stage-6 fix round 3). The build record
# names the libgmp the executable resolves (path, sha256, fat or not) and the gmp.h configuration.
GMP_PREFIX ?=
ifneq ($(strip $(GMP_PREFIX)),)
ifneq ($(words $(GMP_PREFIX)),1)
$(error GMP_PREFIX='$(GMP_PREFIX)': one absolute path without spaces)
endif
ifneq ($(patsubst /%,,$(GMP_PREFIX)),)
$(error GMP_PREFIX=$(GMP_PREFIX): must be an absolute path (the rpath is resolved at run time))
endif
ifeq ($(wildcard $(GMP_PREFIX)/include/gmp.h),)
$(error GMP_PREFIX=$(GMP_PREFIX): $(GMP_PREFIX)/include/gmp.h does not exist)
endif
ifeq ($(wildcard $(GMP_PREFIX)/lib/libgmp.*),)
$(error GMP_PREFIX=$(GMP_PREFIX): no libgmp library in $(GMP_PREFIX)/lib)
endif
override GMP_INC = -I$(GMP_PREFIX)/include
override GMP_LINK = -L$(GMP_PREFIX)/lib -Wl,-rpath,$(GMP_PREFIX)/lib -Wl,--disable-new-dtags
else
override GMP_INC =
override GMP_LINK =
endif
override COMPILE = $(strip $(CXX) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(C8_REQUIRED))
# The GMP-linked commands: with GMP_PREFIX unset, GMP_COMPILE is COMPILE and GMP_LINK is empty.
override GMP_COMPILE = $(strip $(CXX) $(GMP_INC) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(C8_REQUIRED))
override DECIMAL_CMD = $(COMPILE) $< $(strip $(LDFLAGS) -lquadmath $(LDLIBS)) -o $@
override GMP_CMD = $(GMP_COMPILE) -DC8_USE_GMP $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
# Diagnostic builds (never accepted by plan; --describe says "diagnostic":true): per-tier timers, ratio histograms,
# and the sanitizer builds (A-KER-4: -O1 -g ASan/UBSan/_GLIBCXX_ASSERTIONS plus the required flags).
override PROFILE_CMD = $(GMP_COMPILE) -DC8_USE_GMP -DC8_TIER_TIMERS $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
override RATIOHIST_CMD = $(GMP_COMPILE) -DC8_USE_GMP -DC8_RATIO_HISTOGRAM $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
override SAN_FLAGS = -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -D_GLIBCXX_ASSERTIONS
override SAN_COMPILE = $(strip $(CXX) $(CPPFLAGS) $(SAN_FLAGS) $(CXXFLAGS) $(C8_REQUIRED))
override GMP_SAN_COMPILE = $(strip $(CXX) $(GMP_INC) $(CPPFLAGS) $(SAN_FLAGS) $(CXXFLAGS) $(C8_REQUIRED))
override DECIMAL_SAN_CMD = $(SAN_COMPILE) $< $(strip $(LDFLAGS) -lquadmath $(LDLIBS)) -o $@
override GMP_SAN_CMD = $(GMP_SAN_COMPILE) -DC8_USE_GMP $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
# tools/build_record.py receives the exact compile command as arguments; the make variables are recorded as well.
override C8B_CXX = $(CXX)
override C8B_CPPFLAGS = $(CPPFLAGS)
override C8B_OPTFLAGS = $(OPTFLAGS)
override C8B_CXXFLAGS = $(CXXFLAGS)
override C8B_REQUIRED = $(C8_REQUIRED)
override C8B_LDFLAGS = $(LDFLAGS)
override C8B_LDLIBS = $(LDLIBS)
override C8B_NUMERICS = $(NX_NAME)
override C8B_GMP_PREFIX = $(GMP_PREFIX)
export C8B_CXX C8B_CPPFLAGS C8B_OPTFLAGS C8B_CXXFLAGS C8B_REQUIRED C8B_LDFLAGS C8B_LDLIBS C8B_NUMERICS C8B_GMP_PREFIX
override WORKER_DEPS = src/c8d2_integrate.cpp src/kernel.hpp src/quadfast.hpp src/diagnostics.hpp Makefile
# The opt-in profile executable (NUMERICS=<p>...): the gmp command with the profile macros and flags; it also depends
# on src/numerics/, which no default target reads.
override NX_CMD = $(strip $(CXX) $(GMP_INC) $(CPPFLAGS) $(OPTFLAGS) $(CXXFLAGS) $(NX_FLAGS) $(C8_REQUIRED)) -DC8_USE_GMP $(NX_DEFS) $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
override NX_DEPS = $(WORKER_DEPS) $(wildcard src/numerics/*.hpp)
# A failed build-record step removes the executable, so the next make rebuilds both.
.DELETE_ON_ERROR:
.PHONY: all decimal gmp inputs inputs-l8 inspect profile ratiohist probes quaddiff sanitize c7ref test test-python test-full clean
all: decimal inputs
# Distinct filenames make changing the arithmetic backend explicit and auditable.
decimal: bin/c8d2_decimal
ifeq ($(NUMERICS),exact)
gmp: bin/c8d2_gmp inputs
else
gmp: $(NX_EXE) inputs
$(NX_EXE): $(NX_DEPS)
	@mkdir -p bin
	$(NX_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(NX_CMD)
endif
bin/c8d2_decimal: $(WORKER_DEPS)
	@mkdir -p bin
	$(DECIMAL_CMD)
	$(PYTHON) -B tools/build_record.py $@ decimal -- $(DECIMAL_CMD)
bin/c8d2_gmp: $(WORKER_DEPS)
	@mkdir -p bin
	$(GMP_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(GMP_CMD)
profile: bin/c8d2_gmp_prof
bin/c8d2_gmp_prof: $(WORKER_DEPS)
	@mkdir -p bin
	$(PROFILE_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(PROFILE_CMD)
ratiohist: bin/c8d2_gmp_ratiohist
bin/c8d2_gmp_ratiohist: $(WORKER_DEPS)
	@mkdir -p bin
	$(RATIOHIST_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(RATIOHIST_CMD)
# Stage-4a probe (PLAN "Performance plan", P2 fallback): a micro-benchmark outside the worker that includes the unchanged
# src/kernel.hpp and times its calculate_products against 2 and 4 points in lock-step (tools/benchmark.py
# --interleave-probe). Built with the worker's gmp flags; never a worker, never accepted by plan.
override PROBE_CMD = $(GMP_COMPILE) -DC8_USE_GMP $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
probes: bin/c8d2_interleave_probe
bin/c8d2_interleave_probe: benchmarks/probes/interleave_probe.cpp src/kernel.hpp src/quadfast.hpp Makefile
	@mkdir -p bin
	$(PROBE_CMD)
	@{ echo "command: $(PROBE_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt
# Stage-4b R3a proof (PLAN "Performance plan"): bin/c8d2_quad_differential checks src/quadfast.hpp's binary128 add, sub
# and mul against libgcc bit for bit (random pairs and edge lists); bin/c8d2_quad_ranges records the operand ranges of
# the kernel's binary128 tier through kernel.hpp's own sample(). Built with the worker's flags; never workers.
# tests/quad_differential.py drives both.
override QUADDIFF_CMD = $(COMPILE) $< -o $@
override QUADRANGES_CMD = $(GMP_COMPILE) -DC8_USE_GMP $< $(strip $(GMP_LINK) $(LDFLAGS) -lquadmath -lgmp $(LDLIBS)) -o $@
quaddiff: bin/c8d2_quad_differential bin/c8d2_quad_ranges
bin/c8d2_quad_differential: tests/quad_differential.cpp src/quadfast.hpp Makefile
	@mkdir -p bin
	$(QUADDIFF_CMD)
	@{ echo "command: $(QUADDIFF_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt
bin/c8d2_quad_ranges: tests/quad_ranges.cpp src/kernel.hpp src/quadfast.hpp Makefile
	@mkdir -p bin
	$(QUADRANGES_CMD)
	@{ echo "command: $(QUADRANGES_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; } > $@.build.txt
sanitize: bin/c8d2_decimal_san bin/c8d2_gmp_san
bin/c8d2_decimal_san: $(WORKER_DEPS)
	@mkdir -p bin
	$(DECIMAL_SAN_CMD)
	$(PYTHON) -B tools/build_record.py $@ decimal -- $(DECIMAL_SAN_CMD)
bin/c8d2_gmp_san: $(WORKER_DEPS)
	@mkdir -p bin
	$(GMP_SAN_CMD)
	$(PYTHON) -B tools/build_record.py $@ gmp -- $(GMP_SAN_CMD)
# The C7(2) reference executables for the order-7 replay (A-RPL-2): reference/c7d2_hpc_a55958f/ is copied to
# build/c7ref/ and built there with C7(2)'s own Makefile, relative paths and commands, so the 2026 production hashes
# (decimal e696d7f3..., gmp 7e3c8c92...) reproduce on symmetry's AMD nodes with GCC 11.4; other toolchains give other
# hashes, recorded with the replay. CXX, CPPFLAGS, OPTFLAGS, CXXFLAGS, LDFLAGS and LDLIBS pass through unchanged.
c7ref:
	rm -rf build/c7ref
	@mkdir -p build bin/ref
	cp -R reference/c7d2_hpc_a55958f build/c7ref
	$(MAKE) -C build/c7ref bin/c7d2_decimal bin/c7d2_gmp
	cp build/c7ref/bin/c7d2_decimal build/c7ref/bin/c7d2_gmp build/c7ref/bin/c7d2_decimal.build.json build/c7ref/bin/c7d2_gmp.build.json bin/ref/
# C8(2) inputs (PLAN component B): `make inputs` verifies the L3-L7 packs, the small inputs and the vendored pins (a
# missing L8 pack is SKIPPED); `make inputs-l8 INVENTORY=<inventory8_d2 tree>` builds the two L8 packs (not in git) from
# the frozen tree and verifies them against inputs/manifest.json.
inputs:
	$(PYTHON) -B tools/prepare_inputs.py
inputs-l8:
	@test -n "$(INVENTORY)" || { echo "usage: make inputs-l8 INVENTORY=<path of inventory8_d2>"; exit 2; }
	$(PYTHON) -B tools/prepare_inputs.py --l8 --inventory "$(INVENTORY)"
# bin/c8d2_inspect: per-graph kernel table sizes from the worker's own load_graph/prepare (inputs/inventory.json fields).
override INSPECT_CMD = $(COMPILE) $< $(strip $(LDFLAGS) -lquadmath $(LDLIBS)) -o $@
inspect: bin/c8d2_inspect
bin/c8d2_inspect: src/c8d2_inspect.cpp src/kernel.hpp src/quadfast.hpp Makefile
	@mkdir -p bin
	$(INSPECT_CMD)
	@{ echo "command: $(INSPECT_CMD)"; echo "compiler: $$($(CXX) --version | head -1)"; echo "BOOST_LIB_VERSION: $$(echo '#include <boost/version.hpp>' | $(CXX) $(CPPFLAGS) -E -dM -x c++ - | sed -n 's/^#define BOOST_LIB_VERSION //p')"; } > $@.build.txt
# Records: with OUTPUT=<new directory>, every test writes its JSON record there (records go only to --output).
override REC = $(if $(OUTPUT),--output $(OUTPUT)/$(1).json,)
# The A-ASM-1 review record lives beside the package on the Mac (LRI_C8_shared); a cluster export has no such sibling.
override VENDORED_REVIEW = $(if $(wildcard ../LRI_C8_shared/inventory/reviews),,--no-review-record)
# vendored_isolated.py makes its own git-archive export from a checkout, and runs in place in an export (C8_PACKAGE).
override VENDORED_PLACE = $(if $(wildcard .git),,--in-place)
# Pure Python, no native binary (also run on the packaging host): the orchestration, pipeline, scan, merge-scale,
# vendored-assembly and delivery tests (the fake worker), A-INV-2's comparison logic, check_inputs, the profiling tools,
# the GMP_PREFIX knob (make -n), the precision tools' binding to the worker's GMP (Y1, on a fake toolchain), the test
# harnesses' controlled OpenMP environment (R1, R2: tests/test_omp_launch.py, on a stand-in worker), the Stage-4c
# numerics-profile framework (make -n, the F-gate harness on fakes), the dd profile's arithmetic against mpmath
# (tests/test_dd_profile.py: the header's stage 1, compiled with the host compiler) and the native guards of Stage-6
# fix round 3 (tests/test_native_guards.py, host compiler: Z3's refusal of external C8_NX_* hooks, Z4's loader on real
# and truncated G-files against the fix base, and -fsyntax-only of every kernel translation unit).
test-python: inputs
	@$(if $(OUTPUT),mkdir -p $(OUTPUT),true)
	$(PYTHON) -B tests/check_venv.py $(call REC,check_venv)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/unit_orchestration.py $(call REC,unit_orchestration)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_pipeline.py $(call REC,test_pipeline)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/ast_scan.py $(call REC,ast_scan)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/ast_scan.py gen/*.py tests/*.py $(call REC,ast_scan_gen_tests)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B gen/test_regress.py $(call REC,test_regress)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B gen/test_handoff_inventory.py $(call REC,test_handoff_inventory)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/merge_scale.py --rows 20000 $(call REC,merge_scale)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_vendored.py $(VENDORED_REVIEW) $(call REC,check_vendored)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/vendored_isolated.py $(VENDORED_PLACE) $(call REC,vendored_isolated)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_delivery_verifier.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_inputs.py $(call REC,check_inputs)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_profiling.py $(call REC,test_profiling)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_gmp_prefix.py $(call REC,test_gmp_prefix)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_gmp_binding.py $(call REC,test_gmp_binding)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_omp_launch.py $(call REC,test_omp_launch)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_numerics_flags.py $(call REC,test_numerics_flags)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_dd_profile.py $(call REC,test_dd_profile)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/test_native_guards.py $(call REC,test_native_guards)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/sanitize.py --capture-check $(call REC,sanitize_capture)
# J-VAL-1: the replay subset (G-REF, G-C7, G-JET on the first 8 and 8 heaviest kernels per (sector, L)), the native
# refusals, the pure-Python tests above (unit_orchestration runs the A-ORC-13 claim with the real bin/c8d2_gmp on
# Linux), then the real-worker workflow and staging tests. tests/validate.py needs bin/ref/ (make c7ref) and
# bin/c8d2_inspect (make inspect) and fails, naming them, without.
test: all gmp
	@$(if $(OUTPUT),mkdir -p $(OUTPUT),true)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py $(call REC,validate)
	$(MAKE) --no-print-directory test-python
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py $(call REC,workflow)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py $(call REC,staging)
# J-VAL-2: the full replay (all 3,773 L3-L7 kernels and the L=2 graph, both backends) and the point checks L3-L8.
test-full: all gmp
	@$(if $(OUTPUT),mkdir -p $(OUTPUT),true)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/validate.py --full $(call REC,validate_full)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_points.py $(call REC,point_checks)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/check_inputs.py
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/workflow.py $(call REC,workflow)
	OPENBLAS_NUM_THREADS=1 $(PYTHON) -B tests/staging.py $(call REC,staging)
clean:
	rm -f bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_decimal.build.json bin/c8d2_gmp.build.json bin/c8d2_inspect bin/c8d2_inspect.build.txt
	rm -f bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_decimal_san bin/c8d2_gmp_san bin/*_prof.build.json bin/*_ratiohist.build.json bin/*_san.build.json
	rm -f bin/c8d2_interleave_probe bin/c8d2_interleave_probe.build.txt
	rm -f bin/c8d2_quad_differential bin/c8d2_quad_differential.build.txt bin/c8d2_quad_ranges bin/c8d2_quad_ranges.build.txt
	rm -rf bin/ref build/c7ref
	rm -f $(foreach p,$(NX_KNOWN),bin/c8d2_gmp_$(p) bin/c8d2_gmp_$(p).build.json bin/c8d2_gmp_$(p)+*)
