"""
Functions for estimating energy consumption from average speed
"""
##### REFACTOR - Code from Honda ride pooling, refactor for this work..

import pandas as pd
import numpy as np

#%%
def import_whmi_template(infile):
    whmi_template = pd.read_csv(infile)

    return whmi_template

#%%
def create_scaled_whmi(whmi_template, nominal_whmi):
    scaled_whmi_lookup = whmi_template
    scaled_whmi_lookup = dict()
    scaled_whmi_lookup['avg_spd_mph'] = np.asarray(whmi_template['mph'])
    scaled_whmi_lookup['whmi'] = np.asarray(whmi_template['wh_mi_factor'] * nominal_whmi)

    return scaled_whmi_lookup

#%%
def calc_trip_kwh(dist_mi, time_s, scaled_whmi_lookup):

    avg_spd_mph = float(dist_mi) / time_s * 3600
    trip_kwh_mi = (np.interp(avg_spd_mph, scaled_whmi_lookup['avg_spd_mph'],
                        scaled_whmi_lookup['whmi']))/1000.0

    trip_kwh = trip_kwh_mi * dist_mi

    return trip_kwh

#%%
def calc_idle_kwh(time_s):

    idle_kwh = 0.8 * (time_s / 3600.0)

    return idle_kwh

#%%
if __name__ == '__main__':
    whmi_template = whmi_template = pd.read_csv('../data/wh_mi_lookup.csv')
    nominal_whmi = 300
    scaled_whmi_lookup = create_scaled_whmi(whmi_template, nominal_whmi)

    trip_wh = calc_trip_kwh(100,3600, scaled_whmi_lookup)

    # Example, sweeping from 0 mph to 100 mph
    import matplotlib.pyplot as plt

    trip_wh_list = [0]*101
    mph_list = range(0, 101)
    for idx, distance in enumerate(mph_list):
        trip_wh_list[idx] = calc_trip_kwh(distance, 3600, scaled_whmi_lookup) * 1000

    # Plotting Results
    fig, ax = plt.subplots(figsize=[8,6])
    ax.plot(scaled_whmi_lookup['avg_spd_mph'], scaled_whmi_lookup['whmi'],
            c='r', linewidth=3, label='Template', zorder=10)
    ax.scatter(mph_list, trip_wh_list,
        c='k', linewidth=2, label='Swept Values', zorder=1)

    ax.set_xlabel('Trip Average Speed [mph]', fontsize=14)
    ax.set_ylabel('Powertrain Efficiency [Wh/mi]', fontsize=14)
    ax.legend(loc=1, fontsize=14)
    ax.set_title('Template Example: Nominal Wh/mi=%s' % nominal_whmi,
                 fontsize=16, fontweight='bold')
