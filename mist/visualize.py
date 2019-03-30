"""
Module generates a set of key figures highlighting outcomes from a simulation
"""

##### REFACTOR - Code from Honda ride pooling project, refactor for this work...

import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import warnings
warnings.filterwarnings('ignore')

#%% Import and process data, for running locally
def import_and_process(logs_name, requests_name):
    logs_path = '..//data//%s' % logs_name
    requests_path = '..//data//%s' % requests_name
    logs_df = pd.read_csv(logs_path)
    requests_df = pd.read_csv(requests_path)
    
    return logs_df, requests_df

#%% Returns an "activity dataframe" which describes what vehicles are doing by time of day
def create_temporal_df(logs_df, window_seconds, num_vehs):

    times = np.arange(0, 86400.0, window_seconds)
    trip_list = []
    idle_list = []
    dspt_list = []
    chrg_list = []
    oos_list = []
    time_list = []
    
    for idx, cur_time in enumerate(times):
                
        slice_df = logs_df[logs_df.otime_sss<=cur_time]
        grouped_df = slice_df[['activity', 'otime_sss', 'veh_id']].loc[slice_df.groupby('veh_id')['otime_sss'].idxmax()]
        
        num_trip = sum(grouped_df.activity>0)
        num_idle = sum(grouped_df.activity==-1)
        num_dspt = sum(grouped_df.activity==-2)
        num_chrg = sum(grouped_df.activity==-3)
        
        trip_list.append(num_trip)
        idle_list.append(num_idle)
        dspt_list.append(num_dspt)
        chrg_list.append(num_chrg)
        oos_list.append(num_vehs - num_chrg - num_dspt - num_idle - num_trip)
        time_list.append(idx * window_seconds)
    
    activity_df = pd.DataFrame({'time': time_list,
                                'trip': trip_list,
                                'idle': idle_list,
                                'dspt': dspt_list,
                                'chrg': chrg_list,
                                'oos': oos_list})

    return activity_df

#%% Visualizes the activity dataframe
def create_temporal_plot(activity_df, window_seconds, num_vehs, name=-1):

    fig, ax = plt.subplots(figsize=[10,8])
    x_axis = [x / (3600.0 / window_seconds) for x in activity_df.index]
    
    cur_low = [0]*len(activity_df)
    cur_high = activity_df.trip
    ax.fill_between(x_axis, cur_low, cur_high, label='Servicing a Trip', facecolor='#ca0020', edgecolor='k')
    
    cur_low = cur_high
    cur_high = cur_high + activity_df.dspt
    ax.fill_between(x_axis, cur_low, cur_high, label='Dispatching to a Trip', facecolor='#f4a582', edgecolor='k')
    
    cur_low = cur_high
    cur_high = cur_high + activity_df.idle
    ax.fill_between(x_axis, cur_low, cur_high, label='Idling, Awaiting Instruction', facecolor='#92c5de', edgecolor='k')
    
    cur_low = cur_high
    cur_high = cur_high + activity_df.chrg
    ax.fill_between(x_axis, cur_low, cur_high, label='Currently Charging', facecolor='#0571b0', edgecolor='k')
    
    cur_low = cur_high
    cur_high = cur_high + activity_df.oos
    ax.fill_between(x_axis, cur_low, cur_high, label='Out of Service', facecolor='k')              
                    
    ax.legend(loc=1)
    ax.set_xlabel('Hour Since Start of Data', fontsize=14)
    ax.set_ylabel('Number of Vehicles', fontsize=14)
    ax.set_title('Fleet Activity, %s Vehicles, %s Second Time Window' % (num_vehs, window_seconds), fontsize=18, fontweight='bold')
    
    ax.set_xlim([0,max(x_axis)])
    
    fig.savefig(name)
    
    return fig, ax

#%% 2) Successful & Unsuccessful Requests vs HOD and % Vehicles Charging
def eval_requests(logs_df, requests_df, seconds):
    
    requests_left = requests_df.merge(logs_df, how='left', left_on='trip_id', right_on='activity')
    requests_left['period'] = requests_left.pickup_sss.astype(int).floordiv(seconds)
    requests_left['success'] = (~requests_left.activity.isnull()).astype(int)
    requests_left['fail'] = (requests_left.activity.isnull()).astype(int)
    
    serviced_trips = requests_left.groupby('period')['success'].sum()
    failed_trips = requests_left.groupby('period')['fail'].sum()

    return serviced_trips, failed_trips

#%%
def create_requests_plot(logs_df, serviced_trips, failed_trips, seconds,
                         title, name=-1):

    logs_copy = logs_df[(logs_df.activity != -1) & (logs_df.activity != -2)]
    logs_copy['period'] = logs_copy.otime_sss.astype(float).floordiv(seconds)
    logs_copy['not_charging'] = (logs_copy.activity != -3).astype(int)
    logs_copy['charging'] = (logs_copy.activity == -3).astype(int)
    
    num_not_charging = logs_copy.groupby('period')['not_charging'].sum()
    num_charging = logs_copy.groupby('period')['charging'].sum()
    pct_charging = num_charging / (num_charging + num_not_charging)
    
    fig, ax = plt.subplots(figsize=[10,8])

    ax.fill_between(failed_trips.index / 4.0, 0, failed_trips, label='Failed Requests', facecolor='k')
    ax.fill_between(failed_trips.index / 4.0, failed_trips, serviced_trips+failed_trips, label='Serviced Requests', facecolor='r')
    ax.plot(serviced_trips.index / 4.0, serviced_trips+failed_trips, c='k', label='Total Request Population')
    ax.set_xlabel('Hour Since Start of Data', fontsize=14)
    ax.set_ylabel('Frequency', fontsize=14)
    ax.set_xlim([0,24])
    lims = ax.get_ylim()
    ax.set_ylim([0, lims[1]])
    ax.legend(loc=1, fontsize=14)
    ax.set_title(title, fontsize=18, fontweight='bold')
    
    ax2 = ax.twinx()
    ax2.plot(pct_charging.index / 4.0, pct_charging, c='orange', label=None)
    ax2.set_ylabel('Percentage of Fleet Currently Charging [%]', fontsize=14)
    vals = ax2.get_yticks()
    ax2.set_yticklabels(['{:,.0%}'.format(x) for x in vals])
    
    fig.savefig(name)
    
    return fig, ax

#%% 3) Vehicle-day Bar Summaries
def create_vehday_summary_df(logs_df):

    veh_id_list = logs_df.veh_id.unique()
    logs_df['activity_time'] = logs_df.dtime_sss - logs_df.otime_sss
    total_time = logs_df.dtime_sss.max()
    
    veh_id_col = []
    perc_trip_col = []
    perc_idle_col = []
    perc_dspt_col = []
    perc_chrg_col = []
    
    for veh_id in veh_id_list:
        
        veh_slice = logs_df[logs_df.veh_id==veh_id]
        tot_trip_time = veh_slice.activity_time[veh_slice.activity>=0].sum()
        tot_idle_time = veh_slice.activity_time[veh_slice.activity == -1].sum()
        tot_dspt_time = veh_slice.activity_time[veh_slice.activity == -2].sum()
        tot_chrg_time = veh_slice.activity_time[veh_slice.activity == -3].sum()
        
        total_time = veh_slice.dtime_sss.max()
        
        veh_id_col.append(veh_id)
        perc_trip_col.append(tot_trip_time / float(total_time))
        perc_idle_col.append(tot_idle_time / float(total_time))
        perc_dspt_col.append(tot_dspt_time / float(total_time))
        perc_chrg_col.append(tot_chrg_time / float(total_time))
                
    vehday_summary_df = pd.DataFrame({'veh_id': veh_id_col,
                                      'perc_trip': perc_trip_col,
                                      'perc_idle': perc_idle_col,
                                      'perc_dspt': perc_dspt_col,
                                      'perc_chrg': perc_chrg_col})
        
    return vehday_summary_df

#%% Mode by Mode Visualization
def create_mode_histograms(vehday_summary_df, title, name=-1):
    fig, axes = plt.subplots(figsize=[12,10], ncols=2, nrows=2)
    
    sorted_vehday_df = vehday_summary_df.sort_values(by='perc_trip', ascending=False)
    
    bins = range(100)
    
    axes[0,0].hist(sorted_vehday_df.perc_trip*100, bins=bins, normed=True, facecolor='#ca0020')
    axes[0,0].set_xlabel('Time-Based Percentage of Day', fontsize=10)
    axes[0,0].set_ylabel('Percentage of Vehicle-Days', fontsize=10)
    axes[0,0].set_title('Servicing a Trip', fontsize=12)
    vals = axes[0,0].get_xticks() / 100.0
    axes[0,0].set_xticklabels(['{:,.0%}'.format(x) for x in vals])
    
    axes[0,1].hist(sorted_vehday_df.perc_dspt*100, bins=bins, normed=True, facecolor='#f4a582')
    axes[0,1].set_xlabel('Time-Based Percentage of Day', fontsize=10)
    axes[0,1].set_ylabel('Percentage of Vehicle-Days', fontsize=10)
    axes[0,1].set_title('Dispatching to a Trip', fontsize=12)
    vals = axes[0,1].get_xticks() / 100.0
    axes[0,1].set_xticklabels(['{:,.0%}'.format(x) for x in vals])
    
    axes[1,0].hist(sorted_vehday_df.perc_idle*100, bins=bins, normed=True, facecolor='#92c5de')
    axes[1,0].set_xlabel('Time-Based Percentage of Day', fontsize=10)
    axes[1,0].set_ylabel('Percentage of Vehicle-Days', fontsize=10)
    axes[1,0].set_title('Idling, Awaiting Instruction', fontsize=12)
    vals = axes[1,0].get_xticks() / 100.0
    axes[1,0].set_xticklabels(['{:,.0%}'.format(x) for x in vals])
    
    axes[1,1].hist(sorted_vehday_df.perc_chrg*100, bins=bins, normed=True, facecolor='#0571b0')
    axes[1,1].set_xlabel('Time-Based Percentage of Day', fontsize=10)
    axes[1,1].set_ylabel('Percentage of Vehicle-Days', fontsize=10)
    axes[1,1].set_title('Charging', fontsize=12)
    vals = axes[1,1].get_xticks() / 100.0
    axes[1,1].set_xticklabels(['{:,.0%}'.format(x) for x in vals])
    
    fig.suptitle(title, fontsize=18, fontweight='bold')
    
    fig.savefig(name)
      
    return fig, axes

#%% Bar Graph Visualization
def create_mode_bargraph(vehday_summary_df, title, name=-1):

    fig, ax = plt.subplots(figsize=[10,8])
    
    sorted_vehday_df = vehday_summary_df.sort_values(by='perc_trip', ascending=False)

    ax.bar(range(len(sorted_vehday_df)), sorted_vehday_df.perc_trip, width=1, facecolor='#ca0020', label='Servicing a Trip')
    
    bottom = sorted_vehday_df.perc_trip
    ax.bar(range(len(sorted_vehday_df)), sorted_vehday_df.perc_dspt, bottom=bottom, width=1, facecolor='#f4a582', label='Dispatching to a Trip')
    
    bottom = sorted_vehday_df.perc_trip + sorted_vehday_df.perc_dspt
    ax.bar(range(len(sorted_vehday_df)), sorted_vehday_df.perc_idle, bottom=bottom, width=1, facecolor='#92c5de', label='Idling, Awaiting Instruction')
    
    bottom = sorted_vehday_df.perc_trip + sorted_vehday_df.perc_dspt + sorted_vehday_df.perc_idle
    ax.bar(range(len(sorted_vehday_df)), sorted_vehday_df.perc_chrg, 
           bottom=bottom, width=1, facecolor='#0571b0', label='Charging')
           
    vals = ax.get_xticks()
    ax.set_xticklabels(['{:,.0%}'.format(x) for x in vals])
    ax.legend(loc=1, fontsize=12)
    ax.set_xlabel('Rank, Percentage of Day Servicing Trips', fontsize=12)
    ax.set_ylabel('Percentage of Day Performing an Activity', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    fig.savefig(name)
    
    return fig, ax

#%%
def generate_figs(logs_name=[], logs_df=[], requests_df=[], path=-1, scenario=''):

    # Seconds since start
    logs_df['otime_sss'] = logs_df.otime - logs_df.otime.iloc[0]
    logs_df['dtime_sss'] = logs_df.dtime - logs_df.otime.iloc[0]
    requests_df['pickup_sss'] = requests_df.pickup_time_unix - requests_df.pickup_time_unix.min()
    requests_df['dropoff_sss'] = requests_df.dropoff_time_unix - requests_df.pickup_time_unix.min()
    
    # If path is passed, create a folder for the images if there is not one already
    if path != -1:
        if not os.path.exists(path):
            os.makedirs(path)
        fig_path = path
        
    # If path is not passed, create a folder for the images in the relative ../img/ directory
    else: 
        if not os.path.exists('../img/%s' % scenario):
            os.makedirs(('../img/%s' % scenario))
        fig_path = '../img/%s/' % scenario
        
    num_vehs = len(logs_df.veh_id.unique())     
        
    # Section 1
    print('Section 1: Temporal Activity Plot')
    window_seconds = 1200
    activity_df = create_temporal_df(logs_df, window_seconds, num_vehs)
    name = fig_path+'temporal_activity.png'
    fig, ax = create_temporal_plot(activity_df, window_seconds, num_vehs, name=name)
    
    # Section 2
    print('Section 2: Requests Plot')
    window_size = 15 # minutes
    seconds = window_size * 60
    serviced_trips, failed_trips = eval_requests(logs_df, requests_df, seconds)
    
    title = 'Fleet Performance, n=%s Vehicles' % num_vehs
    name = fig_path+'fleet_performance.png'
    fig, ax = create_requests_plot(logs_df, serviced_trips, failed_trips, seconds,
                             title, name=name)
    
    # Section 3
    print('Section 3: Vehicle-Day Mode Summary Plots')
    plt.close('all')
    vehday_summary_df = create_vehday_summary_df(logs_df)
    
    title = 'Mode Histograms, n=%s Vehicles' % num_vehs
    name = fig_path+'mode_hist.png'
    fig, ax = create_mode_histograms(vehday_summary_df, title, name=name)
    
    title = 'Day Summaries, n=%s Vehicles' % num_vehs
    name = fig_path+'day_summaries.png'
    fig, ax = create_mode_bargraph(vehday_summary_df, title, name=name)
    
    return

if __name__ == '__main__':
    #logs_name = 'no_pool-3000veh.txt'
    #logs_name = 'no_pool-6000veh.txt'
    logs_name = 'no_pool-12000veh.txt'
    
    generate_figs(logs_name=logs_name)
    