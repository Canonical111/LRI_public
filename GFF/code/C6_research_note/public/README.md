# Public targets of this package

**The package's note is not shipped.** The delivered `README.md` says to start with `note/C6_progress_note.pdf` and
describes how to build it. That note is merged into the GFF condensed note (`GFF/note/`, Appendix B, "Derivation of the
special-function representation of C6(1)", with Sections 1.2 and 22.9), as the author asked: one TeX note per
direction. Read the derivation there; `note/` is listed in `public/dropped_paths.txt`.

The files outside `public/` and `public.mk` are the delivered package, byte for byte (see `MANIFEST.sha256`;
the dropped historical stages are listed in `public/dropped_paths.txt`). Its own commands in `README.md`
(`python code/reproduce_final.py`, `python code/make_outputs.py`, ...) rewrite `outputs/` in place, which
`MANIFEST.sha256` binds. Use the public targets instead; they work on copies under `.work/`:

    make -f public.mk test          # integrity + three exact tasks           (seconds)
    make -f public.mk replay        # every quoted number from the records    (seconds)
    make -f public.mk rerun-final   # fresh run of the 22 final-method tasks  (minutes; cluster node)

Each target prints a PASS/FAIL table and writes it to `.work/<target>_report.txt`. The independent review of
this package and its check scripts are in `../LRI_C6_closed_form_review/`.
