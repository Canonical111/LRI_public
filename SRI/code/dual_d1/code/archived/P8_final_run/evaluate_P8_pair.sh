set -e
while [ ! -f /mnt/data/P8_final_run/F3_six_kink_completion/F3_final/manifest.json ]; do sleep 3; done
cd /mnt/data/P8_final_run/F3_six_kink_completion/numerical
python -u evaluate_set.py --manifest ../F3_final/manifest.json --out ../F3_final/eval70.json --dps 70 --radius 120 --taylor 260 --asymptotic 170 --step .25
python -u evaluate_set.py --manifest ../F3_final/manifest.json --out ../F3_final/eval100.json --dps 100 --radius 160 --taylor 320 --asymptotic 200 --step .23
