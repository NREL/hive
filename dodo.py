import subprocess
import os
import sys
import glob
import re
import shutil
import pandas as pd

import run
import config as cfg

from hive import utils
import hive.preprocess as pp

if not cfg.DEBUG:
    import warnings
    warnings.filterwarnings("ignore")

VERBOSE = 2 if cfg.VERBOSE else 0

PROFILE_OUT_PATH = os.path.join('tests', 'profile_output')
PROFILE_FILES = ['run.py']

SCENARIO_PATH = os.path.join(cfg.IN_PATH, '.scenarios', cfg.SIMULATION_NAME.replace(" ", "_"))
LIB_PATH = os.path.join(cfg.IN_PATH, '.lib')

DOIT_CONFIG = {
        'default_tasks': [
            'build_input_files',
            'run_simulation',
            ],
        }

def basename_stem(path):
    return os.path.splitext(os.path.basename(path))[0]

def clean_msg(msg):
    print(msg)
    print()

def run_actions(actions, target=None):
    if target == None:
        subprocess.run(actions)
    else:
        with open(target, 'w') as f:
            subprocess.run(actions, stdout=f)

def task_update_deps():
    """
    Update conda environment.yml file
    """
    for target, actions in [
            ('environment.yml', ['conda', 'env', 'export', '-n', 'hive']),
            ]:
        yield {
                'name': target,
                'actions': [(run_actions, [actions, target])],
                'targets': [target],
                'clean': True,
                }


def task_profile():
    """
    Profile each component using cProfile.
    """
    #TODO: Add functionality to generate svg call graph. gprof2dot, grpahviz
    #python gprof2dot.py -f pstats output.pstats | dot -Tsvg -o profile_graph.svg
    for filepath in PROFILE_FILES:
        name = re.split('[./]', filepath)[-2]
        output_file = PROFILE_OUT_PATH + name + '.pstats'
        yield {
                'name': filepath,
                'actions': ['python -m cProfile -o {} {}'.format(output_file, filepath)],
                'file_dep': [filepath],
                'targets': [output_file],
                }


def task_build_input_files():
    """
    Build input files.
    """
    main_file = os.path.join(cfg.IN_PATH, 'main.csv')
    charge_file = os.path.join(LIB_PATH, 'raw_leaf_curves.csv')
    whmi_lookup_file = os.path.join(LIB_PATH, 'wh_mi_lookup.csv')
    charge_df = pd.read_csv(charge_file)
    sim_df = pd.read_csv(main_file)
    whmi_df = pd.read_csv(whmi_lookup_file)
    for i, row in sim_df.iterrows():
        row["SCENARIO_NAME"] = row["SCENARIO_NAME"].strip().replace(" ", "_")
        data = {}
        file_deps = [main_file, charge_file, whmi_lookup_file]
        outfile = os.path.join(SCENARIO_PATH, '{}_inputs.pickle'.format(row['SCENARIO_NAME']))

        req_file = os.path.join(cfg.IN_PATH, 'requests', row['REQUESTS_FILE'])
        file_deps.append(req_file)

        # Path to charge network file
        charge_stations_file = os.path.join(cfg.IN_PATH, 'charge_network', row['CHARGE_STATIONS_FILE'])
        veh_bases_file = os.path.join(cfg.IN_PATH, 'charge_network', row['VEH_BASES_FILE'])
        file_deps.append(charge_stations_file)

        fleet_file = os.path.join(cfg.IN_PATH, 'fleets', row['FLEET_FILE'])
        file_deps.append(fleet_file)

        fleet_df = pd.read_csv(fleet_file)
        assert fleet_df.shape[0] > 0, 'Must have at least one vehicle type to run simulation.'
        row['TOTAL_NUM_VEHICLES'] = fleet_df.NUM_VEHICLES.sum()
        row['NUM_VEHICLE_TYPES'] = fleet_df.shape[0]

        veh_keys = []

        for i, veh in fleet_df.iterrows():
            veh_file = os.path.join(cfg.IN_PATH, 'vehicles', '{}.csv'.format(veh.VEHICLE_NAME))
            veh_df = pd.read_csv(veh_file)
            veh_df['VEHICLE_NAME'] = veh.VEHICLE_NAME
            veh_df['NUM_VEHICLES'] = veh.NUM_VEHICLES
            data[veh.VEHICLE_NAME] = veh_df.iloc[0]
            veh_keys.append(veh.VEHICLE_NAME)

        row['VEH_KEYS'] = veh_keys

        data['requests'] = pp.load_requests(req_file)
        data['stations'] = pd.read_csv(charge_stations_file)
        data['bases'] = pd.read_csv(veh_bases_file)
        data['main'] = row
        data['charge_curves'] = charge_df
        data['whmi_lookup'] = whmi_df

        yield {
            'name': row['SCENARIO_NAME'],
            'actions': [(
                utils.save_to_pickle,
                [data, outfile]
                )],
            'file_dep': file_deps,
            'targets': [outfile],
            'verbosity': VERBOSE,
        }


def task_run_simulation():
    """
    Run full simulation.
    """
    sim_output = os.path.join(cfg.OUT_PATH, cfg.SIMULATION_NAME.replace(" ", "_"))
    if not os.path.isdir(cfg.OUT_PATH):
        clean_msg('creating base output directory..')
        os.makedirs(cfg.OUT_PATH)

    clean_msg('creating simulation output directory..')
    if not os.path.isdir(sim_output):
        os.makedirs(sim_output)
    else:
        shutil.rmtree(sim_output)
        os.makedirs(sim_output)

    scenario_files = glob.glob(os.path.join(SCENARIO_PATH, '*.pickle'))
    simulations = [(s, basename_stem(s)[:-7]) for s in scenario_files]

    for src, tag in simulations:
        outfiles = [
                    os.path.join(
                            sim_output,
                            tag,
                            'logs',
                            'vehicle_log.csv'),
                    os.path.join(
                            sim_output,
                            tag,
                            'logs',
                            'stations_log.csv'),
                    os.path.join(
                            sim_output,
                            tag,
                            'logs',
                            'depots_log.csv'),
                    ]
        yield {
                'name': tag,
                'actions' : [
                    (run.run_simulation, [src, tag]),
                    ],
                'file_dep': [src],
                # 'targets': outfiles,
                'verbosity': VERBOSE,
                }
