#!/usr/bin/env bash

# exit on error
set -e

HIVEDOC=../../hive-docs/

# copy the readme into the source
cp ../README.md source/

# build sphinx html files
make html

# update html files with emoji unicode
python emojize.py

# move files into the hive-doc repo
cp -r build/html/* $HIVEDOC

cd $HIVEDOC || exit
git add ./*
git commit -m "publish docs"
git push
