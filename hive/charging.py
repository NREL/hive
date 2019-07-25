
"""
Functions for estimating charge curves
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def construct_temporal_charge_template(unscaled_df, battery_kwh, battery_kw):
    """
    Builds a scaled charging template based on battery specifications. 
    The original template is for a Nissan Leaf and was provided by Idaho 
    National Laboratory. 

    Inputs
    ------
    unscaled_df: DataFrame
        The DataFrame describes the charge template (likely from Nissan Leaf) 
        with columns [soc, kw]. Presently the source file for that profile is 
        here: '../inputs/.lib/raw_leaf_curves.csv'
    battery_kwh: double precision
        Battery capacity, in kWh
    battery_kw: double precision
        Maximum power that cna be received by battery, in kW

    Returns
    -------
    DataFrame
        Scaled charging template based on the input template, containing 
        columns: [time_i, soc_i, kwh_i, kw, soc_f, kwh_f]

    Examples
    --------
    >>> PATH_TO_LEAF = '../inputs/.lib/raw_leaf_curves.csv'
    >>> leaf_df = pd.read_csv(PATH_TO_LEAF)
    >>> construct_temporal_charge_template(leaf_df,
                                           battery_kwh = 30, 
                                           battery_kw = 100)

            time_i      soc_i      kwh_i         kw      soc_f      kwh_f
    0          1   0.000000   0.000000  20.000000   0.018519   0.005556
    1          2   0.018519   0.005556  20.430222   0.037435   0.011231
    2          3   0.037435   0.011231  20.869699   0.056759   0.017028
    3          4   0.056759   0.017028  21.318629   0.076499   0.022950
    4          5   0.076499   0.022950  21.777217   0.096663   0.028999
        ...
    """

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
    """
    Selects a portion of the scaled charging template that applies to a
    particular charge event based on initial conditions and event duration or 
    final state of charge. The function determines the appropriate calculation
    based on the set of inputs provided.

    Inputs
    ------
    charge_template: DataFrame
        Scaled charging template based on the input template, containing 
        columns: [time_i, soc_i, kwh_i, kw, soc_f, kwh_f]
    soc_i: double precision
        Initial battery state of charge, in percent (0 to 100)
    charge_time: double precision
        Charge event duration, in seconds (default = -1)
    soc_f: double precision
        Final state of charge, in percent (0 to 100, default = -1)

    Returns
    -------
    DataFrame
        The portion of the charge_template input DataFrame that characterizes
        the charging event described by the input conditions. 'abs_time' column
        is appended to the dataframe as well.

    Examples
    --------
    >>> PATH_TO_LEAF = '../inputs/.lib/raw_leaf_curves.csv'
    >>> leaf_df = pd.read_csv(PATH_TO_LEAF)
    >>> scaled_df = construct_temporal_charge_template(leaf_df,
                                           battery_kwh = 30, 
                                           battery_kw = 100)
    >>> construct_charge_profile(scaled_df,
                                 soc_i = 20,
                                 soc_f = 80)

            time_i      soc_i     kwh_i         kw      soc_f     kwh_f  abs_time
    293     294  20.028729  6.008619  86.258619  20.108598  6.032579         0
    294     295  20.108598  6.032579  86.282579  20.188489  6.056547         1
    295     296  20.188489  6.056547  86.306547  20.268403  6.080521         2
    296     297  20.268403  6.080521  86.330521  20.348338  6.104501         3
    297     298  20.348338  6.104501  86.354501  20.428296  6.128489         4
    """
    
    charge_df = charge_template[charge_template.soc_i > soc_i].copy()
    # start_row = np.argmax(charge_template.soc_i>soc_i)
    start_time = float(charge_df.iloc[0].time_i)
    
    if charge_time != -1:
        end_time = start_time + charge_time
        
        if end_time > charge_template.time_i.max():
            end_time = charge_template.time_i.max()
        else:
            end_time = start_time + charge_time
        
        charge_df = charge_df[charge_df.time_i <= end_time]
        # end_row = np.argmax(charge_template.time_i>=end_time)
        
        # charge_df = charge_template.iloc[start_row:end_row, :]
        charge_df['abs_time'] = range(len(charge_df))
        
    elif soc_f != -1:

        charge_df = charge_df[charge_df.soc_f <= soc_f]
        # end_row = np.argmax(charge_template.soc_f>=soc_f)
        # end_time = charge_template.time_i[end_row]
        # charge_time = end_time - start_time
        
        # charge_df = charge_template.iloc[start_row:end_row, :]
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


#TODO (JH): currently assuming DCFC can provide whatever max accepted battery power is, should allow DCFC power to be less (or more)
def calc_dcfc_kwh(battery_kwh, battery_kw, soc_i, charge_time):
    """
    Calculates energy added to the battery over a given charge duration, for a 
    DC fast charging event at a specified average power. The function uses assumptions
    to create a realistic charge profile with power tapering at higer SOC.

    Parameters
    ----------
    battery_kwh: double precision
        Battery capacity, in kWh
    battery_kw: double precision
        Maximum power that cna be received by battery, in kW
    soc_i: double precision
        Initial battery state of charge, in percent (0 to 100)
    charge_time: double precision
        Charge event duration, in seconds 

    Returns
    -------
    float
        Energy added to the battery in the give time_s, kilowatt-hours

    """

    PATH_TO_LEAF = '../inputs/.lib/raw_leaf_curves.csv'
    leaf_df = pd.read_csv(PATH_TO_LEAF)

    # TODO: move scaling into the dispatcher to only perform once per vehicle type
    scaled_df = construct_temporal_charge_template(leaf_df,
                                           battery_kwh, 
                                           battery_kw)

    charge_df = construct_charge_profile(scaled_df,
                                        soc_i = soc_i, 
                                        charge_time = charge_time)
    
    kwh_net = charge_df.iloc[-1]['kwh_f'] - charge_df.iloc[0]['kwh_i']

    return float(kwh_net)

def calc_dcfc_secs(battery_kwh, battery_kw, soc_i, soc_f):
    """
    Calculates time required to charge from initial to final soc, for a 
    DC fast charging event. The function uses assumptions to create a realistic 
    charge profile with power tapering at higer SOC.

    Parameters
    ----------
    battery_kwh: double precision
        Battery capacity, in kWh
    battery_kw: double precision
        Maximum power that cna be received by battery, in kW
    soc_i: double precision
        Initial battery state of charge, in percent (0 to 100)
    soc_i: double precision
        Initial battery state of charge, in percent (0 to 100)

    Returns
    -------
    float
        Energy added to the battery in the give time_s, kilowatt-hours

    """

    PATH_TO_LEAF = '../inputs/.lib/raw_leaf_curves.csv'
    leaf_df = pd.read_csv(PATH_TO_LEAF)

    # TODO: move scaling into the dispatcher to only perform once per vehicle type
    scaled_df = construct_temporal_charge_template(leaf_df,
                                           battery_kwh, 
                                           battery_kw)

    charge_df = construct_charge_profile(scaled_df,
                                        soc_i = soc_i, 
                                        soc_f = soc_f)
    
    time_secs = charge_df.iloc[-1]['abs_time']

    return float(time_secs)

