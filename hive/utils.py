import pandas as pd
import sys
import glob
import os
import pickle

def save_to_hdf(data, outfile):
    for key, val in data.items():
        val.to_hdf(outfile, key=key)

def save_to_pickle(data, outfile):
    with open(outfile, 'wb') as f:
        pickle.dump(data, f)
