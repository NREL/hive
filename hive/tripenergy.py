"""
Functions for estimating energy consumption from average speed
"""

import pandas as pd
import numpy as np

def import_whmi_template(infile):
    whmi_template = pd.read_csv(infile)

    return whmi_template

def create_scaled_whmi(whmi_template, nominal_whmi):
    scaled_whmi_lookup = whmi_template
    scaled_whmi_lookup = dict()
    scaled_whmi_lookup['avg_spd_mph'] = np.asarray(whmi_template['mph'])
    scaled_whmi_lookup['whmi'] = np.asarray(whmi_template['wh_mi_factor'] * nominal_whmi)

    return scaled_whmi_lookup

def calc_trip_kwh(dist_mi, time_s, scaled_whmi_lookup):

    avg_spd_mph = float(dist_mi) / time_s * 3600
    trip_kwh_mi = (np.interp(avg_spd_mph, scaled_whmi_lookup['avg_spd_mph'],
                        scaled_whmi_lookup['whmi']))/1000.0

    trip_kwh = trip_kwh_mi * dist_mi

    return trip_kwh

def calc_idle_kwh(time_s):

    idle_kwh = 0.8 * (time_s / 3600.0)

    return idle_kwh
