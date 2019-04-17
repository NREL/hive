import pandas as pd
import sys
import glob
import os

def save_to_hdf(data, outfile):
    for key, val in data.items():
        val.to_hdf(outfile, key=key)
