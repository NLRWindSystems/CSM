#!/usr/bin/env bash

# Build the CSM documentation site.
jupyter-book clean .

jupyter-book build . > build_log.txt

# Copy examples from the docs build to examples/ and run the linter on them.
cp -f _build/jupyter_execute/**/*.ipynb ../examples/
nb_file_names=$(find _build/jupyter_execute/**/*.ipynb -type f | awk -F/ 'BEGIN {ORS=" "} {print $NF}')

cd ../examples
python ../docs/clean_notebook.py $nb_file_names
pre-commit run --files $nb_file_names

cd ../docs
printf "\nCSM documentation built successfully, and updated examples have been copied into CSM/examples/ and validated\n"
tail -n 15 build_log.txt
rm -rf build_log.txt
