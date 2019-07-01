
"""
Functions for estimating charge curves
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

#TODO: Jake revisit

def construct_temporal_charge_template(unscaled_df, battery_kwh, battery_kw):
    
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

# @JH - refactor
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

def calc_const_charge_kwh(time_s, kw=6.6):
    """
    Calculates the energy (in kWh) added to battery in time_s seconds at 
    constant power, kw (default=6.6).

    Inputs
    ------
    time_s: double precision
        Seconds of charging
    kw: double precision
        Constant power received by battery, in kW (default: 6.6)

    Returns
    -------
    double precision
        kWh added to battery in time_s seconds

    Examples
    --------
    >>> calc_const_charge_kwh(7200)
    13.2
    """
    kwh = kw * (time_s / 3600.0)
    
    return kwh

def calc_const_charge_secs(init_energy_kwh, battery_capacity_kwh, kw=6.6, soc_f=1.0):
    """
    Calculates the time (in seconds) to charge from init_energy_kwh to 
    battery_capacity_kwh * soc_f at constant power, kw (default=6.6).

    Inputs
    ------
    init_energy_kwh: double precision
        Initial battery kWh
    battery_capacity_kwh: double precision
        Battery capacity, in kWh
    kw: double precision
        Constant power received by battery, in kW (default: 6.6)
    soc_f: double precision
        Fractional battery state of charge at completion of charge (default: 1.0)

    Returns
    -------
    double precision
        Seconds needed to charge from init_energy_kwh -> battery_capacity_kwh * soc_f

    Examples
    --------
    >>> calc_const_charge_secs(42, 60)
    9818.181818
    """
    energy_f = battery_capacity_kwh * soc_f
    secs = (energy_f - init_energy_kwh)/kw*3600
    
    return secs


#TODO (JH): build calc_dcfc_kwh() as referenced in dispatcher.py 202
def calc_dcfc_kwh(charge_template, init_energy_kwh, battery_capacity_kwh, kw, time_s):
    """
    Calculates energy added to the battery over a give charge duration, for a 
    DC fast charging at a specified average power.

    Parameters
    ----------
    charge_template : int
        Maximum charging power accepta as a function of current battery energy
    init_energy_kwh : float
        Initial battery energy, kilowatt-hours
    battery_capacity_kwh : float
        Second number to add
    kw : float
        Constant power recieved by battery, kilowatts
    time_s : float
        Charging duration, seconds

    Returns
    -------
    float
        Energy added to the battery in the give time_s, kilowatt-hours

    """


#TODO (JH): build calc_dcfc_secs() as referenced in dispatcher.py 218

