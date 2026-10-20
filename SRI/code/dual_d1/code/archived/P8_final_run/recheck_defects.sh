cd /mnt/data/P8_final_run/F3_six_kink_completion/engine
set -e
python -u fibration_defect.py Z 8
python -u fibration_defect.py A 9
python -u fibration_defect.py EA 7
python -u prepare_EZ6.py
