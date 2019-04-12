
"""
Functions for estimating charge curves
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def construct_temporal_charge_template(unscaled_df, battery_kwh, battery_kw):
    """Function needs docstring"""
    
    unscaled_df.kw = unscaled_df.kw * battery_kw / 50.0

    time_i = 0
    soc_i = 0
    kwh_i = 0
    kw_i = 0
    soc_f = 0
    kwh_f = 0
    
    charge_template = pd.DataFrame({'time_i': [time_i],
                                  'soc_i': [soc_i],
                                  'kwh_i': [kwh_i],
                                  'kw': [kw_i],
                                  'soc_f': [soc_f],
                                  'kwh_f': [kwh_f]})

    time_i_lst, soc_i_lst, kwh_i_lst, kw_lst, soc_f_lst, kwh_f_lst = [], [], [], [], [], []
    
    while soc_i <= 99.50:
               
        time_i = time_i + 1
        
        soc_i = soc_f
        kwh_i = kwh_f
        
        kw = np.interp(soc_i, unscaled_df.soc, unscaled_df.kw)
        
        kwh_f = kwh_i + kw/3600.0
        soc_f = kwh_f / battery_kwh * 100.0
        
        time_i_lst.append(time_i)
        soc_i_lst.append(soc_i)
        kwh_i_lst.append(kwh_i)
        kw_lst.append(kw)
        soc_f_lst.append(soc_f)
        kwh_f_lst.append(kwh_f)
        
    charge_template = pd.DataFrame(data={'time_i': time_i_lst,
                                         'soc_i': soc_i_lst,
                                         'kwh_i': kwh_i_lst,
                                         'kw': kw_lst,
                                         'soc_f': soc_f_lst,
                                         'kwh_f': kwh_f_lst
                                        })
                              
    return charge_template

def construct_charge_profile(charge_template, soc_i, charge_time=-1, soc_f=-1):
    """Function needs docstring"""
    
    start_row = np.argmax(charge_template.soc_i>soc_i)
    start_time = charge_template.time_i[start_row]
    
    if charge_time != -1:
        end_time = start_time + charge_time
        
        if end_time > charge_template.time_i.max():
            end_time = charge_template.time_i.max()
        else:
            end_time = start_time + charge_time
        
        end_row = np.argmax(charge_template.time_i>=end_time)
        
        charge_df = charge_template.iloc[start_row:end_row, :]
        charge_df['abs_time'] = range(len(charge_df))
        
    elif soc_f != -1:
        
        end_row = np.argmax(charge_template.soc_f>=soc_f)
        end_time = charge_template.time_i[end_row]
        charge_time = end_time - start_time
        
        charge_df = charge_template.iloc[start_row:end_row, :]
        charge_df['abs_time'] = range(len(charge_df))        
    
    return charge_df

def query_charge_stats(charge_template, soc_i, charge_time=-1, soc_f=-1):
    """Function needs docstring"""
    
    start_row = np.argmax(charge_template.soc_i>soc_i)
    start_time = charge_template.time_i[start_row]
    
    if charge_time != -1:
        end_time = start_time + charge_time
        
        if end_time > charge_template.time_i.max():
            end_time = charge_template.time_i.max()
        else:
            end_time = start_time + charge_time
        
        end_row = np.argmax(charge_template.time_i>=end_time)
        
        charge_df = charge_template.iloc[start_row:end_row, :]
        
        kwh = charge_df.kwh_f.iloc[-1] - charge_df.kwh_i.iloc[0]
        soc_f = charge_df.soc_f.iloc[-1]
        avg_kw = kwh / (end_time - start_time) * 3600
        
    elif soc_f != -1:
        
        end_row = np.argmax(charge_template.soc_f>=soc_f)
        end_time = charge_template.time_i[end_row]
        charge_time = end_time - start_time
        
        charge_df = charge_template.iloc[start_row:end_row, :]
        kwh = charge_df.kwh_f.iloc[-1] - charge_df.kwh_i.iloc[0]
        avg_kw = kwh / (end_time - start_time) * 3600
        
    return kwh, soc_f, charge_time, avg_kw


def calc_const_charge_kwh(time_s, kw=7.2):
    """Function needs docstring"""
    kwh = kw * (time_s / 3600.0)
    
    return kwh

def calc_const_charge_secs_to_full(energy_remaining, battery_capacity, kw=7.2):
    """Function needs docstring"""
    secs_to_full = (battery_capacity - energy_remaining)/kw*3600
    
    return secs_to_full