set -e
python -u /mnt/data/P8_final_run/extend_F3_manifest.py
cd /mnt/data/P8_final_run/F3_six_kink_completion/numerical
python -u evaluate_set.py --manifest ../F3_final/full_manifest.json --out ../F3_final/eval70.json --dps 70 --radius 120 --taylor 260 --asymptotic 170 --step .25
python -u evaluate_set.py --manifest ../F3_final/full_manifest.json --out ../F3_final/eval100.json --dps 100 --radius 160 --taylor 320 --asymptotic 200 --step .23
