while kill -0 4870 2>/dev/null; do sleep 2; done
cd /mnt/data/P8_final_run/old_C7/C7_completion/engine
OPENBLAS_NUM_THREADS=1 python -u assemble_J9_full_lower.py
