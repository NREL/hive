#!/usr/bin/env bash

# exit on error
set -e

HIVEDOC=../../hive-docs/
cd $HIVEDOC || exit
git add ./*
git commit -m "publish docs"
git push