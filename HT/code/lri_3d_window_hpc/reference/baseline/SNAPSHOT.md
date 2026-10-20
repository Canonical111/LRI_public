# Preserved latest-source comparison snapshot

This directory preserves the code, relevant original inputs/teachers/results and
validation fixtures from `lri_3d_dressed_window_hpc.zip` (SHA256 in
`validation/INPUT.json` at the release root). Its `code/` modules are byte-identical
to the latest supplied package, not the older raw spherical oracle. Benchmarks run
these modules in separate Python processes with a verified import path.

Original research README/drivers are preserved for attribution. This snapshot is
not itself a new production release, and some full-study assets such as original
figures or redundant oracle copies are intentionally not duplicated. Current
reproduction commands are at the release root. Historical JSONs retain original
checksums and source identifiers, rather than being relabelled as new outputs.
