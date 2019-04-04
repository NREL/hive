
"""
Functions for estimating charge curves
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

#%%
def construct_temporal_charge_template(unscaled_df,
                                       battery_kwh,
                                       battery_kw):
    
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

#%%
def construct_charge_profile(charge_template, soc_i, charge_time=-1, soc_f=-1):
    
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

#%%
def query_charge_stats(charge_template, soc_i, charge_time=-1, soc_f=-1):
    
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
    kwh = kw * (time_s / 3600.0)
    
    return kwh

def calc_const_charge_secs_to_full(energy_remaining, battery_capacity, kw=7.2):
    secs_to_full = (battery_capacity - energy_remaining)/kw*3600
    
    return secs_to_full

#%%
if __name__=='__main__':
    
    plt.close('all')
    
    battery_kwh = 60
    battery_kw = 50 
    unscaled_df = pd.read_csv('..//data//raw_leaf_curves.csv')
    charge_template = construct_temporal_charge_template(unscaled_df,
                                       battery_kwh,
                                       battery_kw)
    soc_i = 20
    soc_f = 80
    charge_df = construct_charge_profile(charge_template, soc_i, soc_f=soc_f)
    
    fig, ax = plt.subplots(figsize=[8,6])
    ax.plot(unscaled_df.soc, unscaled_df.kw, linewidth=3.0, c='k')
    ax.set_xlabel('State of Charge [%]', fontsize=14)
    ax.set_ylabel('Battery Charge Acceptance [kW]', fontsize=14)
    ax.set_xlim([unscaled_df.soc.min(), unscaled_df.soc.max()])
    ax.set_title('Variable Power Based on Battery SOC*', fontsize=16,
                 fontweight='bold')
    
    fig, ax = plt.subplots(figsize=[8,6])
    ax.plot(charge_df.abs_time, charge_df.kw, c='k', linewidth=3.0)
    ax.set_xlabel('Charge Time [s]', fontsize=14)
    ax.set_ylabel('Instantaneous Charge Power [kW]', fontsize=14)
    ax.set_xlim([charge_df.abs_time.min(), charge_df.abs_time.max()])
    ax.set_title('Example Charge: 60kWh Battery, 50kW Max Charge\n20% SOC to 80% SOC', 
                 fontsize=16, fontweight='bold')
    
    
    ax2 = ax.twinx()
    ax2.plot(charge_df.abs_time, charge_df.soc_i, c='orange', linewidth=3.0)
    ax2.set_ylabel('Battery SOC [%]', fontsize=14)
    
    
    
    
