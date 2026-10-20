Minimal C7 native regression fixtures from the supplied LRI_C7_D3_HPC.zip.

The src files, gamma jets and graph payloads are unchanged. MANIFEST.json records
all SHA-256 hashes. inputs/inventory.json contains only the minimum- and
maximum-cost archived graphs at loops 3 through 7 in each forest sector.
These 19 graphs are test fixtures, not a complete scientific inventory.

Build with make reference and execute with make test-native.
To test a separately extracted complete upload instead, run:
python3 tests/test_native.py --c7-package /path/to/LRI_C7_D3_HPC
