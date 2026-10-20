# Public-release edit (2026-10-17): the target 'note' and its builder are removed (the note is not shipped; it is
# the SRI note's Appendices A to C). public/RE-PINNED.json records the original and published sha256.
.PHONY: check algebra certificates numerical tables
check:
	python run_checks.py
algebra:
	python run_checks.py --algebra
certificates:
	python code/reproduce.py --task certificates
numerical:
	python code/reproduce.py --task c8-numerical
tables:
	python code/reproduce_summary.py
