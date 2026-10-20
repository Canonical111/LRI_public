# Public targets of the review

`REVIEW.md` is the review report (8 October 2026) and `checks/` holds its check scripts with their recorded
outputs, as written for the review. The public targets work on copies under `.work/`:

    make -f public.mk test     # scripts compile, recorded outputs present           (seconds)
    make -f public.mk replay   # the review's agreements from its recorded outputs   (seconds)
    make -f public.mk rerun    # all 49 check commands afresh, then the same replay  (10-25 min; cluster node)

The review reads the package records of `../C6_research_note/` and the quoted numbers in
`../../results/C6_1/analytic/quoted_numbers.json`. The command list of `rerun` is reconstructed from the names of
the recorded outputs (`public/rerun_checks.py`); the review itself did not record its command lines.
