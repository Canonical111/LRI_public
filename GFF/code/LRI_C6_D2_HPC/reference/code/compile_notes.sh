set -e
cd "$(dirname "$0")/.."
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex > logs/build_long_range_ising_complete_1.log
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex > logs/build_long_range_ising_complete_2.log
pdflatex -interaction=nonstopmode -halt-on-error C6_numerical_methods.tex > logs/build_C6_numerical_methods_1.log
pdflatex -interaction=nonstopmode -halt-on-error C6_numerical_methods.tex > logs/build_C6_numerical_methods_2.log
touch verification/latex_build_complete
