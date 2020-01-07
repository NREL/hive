#!/bin/bash

for i in {6..8}
do
  echo "scenario nyc${i}.yaml running"
  python run.py scenarios/nyc${i}.yaml
done
