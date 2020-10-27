#!/usr/bin/env bash

# exit on error
set -e

HIVEDOC=../../hive-docs/

# copy the readme into the source
cp ../README.md source/

# update image paths
sed "s|docs/source/||" source/README.md > source/tmp_README.md
mv source/tmp_README.md source/README.md

# build sphinx html files
make html

# update html files with emoji unicode
python emojize.py

# move files into the hive-doc repo
cp -r build/html/* $HIVEDOC


