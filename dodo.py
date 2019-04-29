import subprocess
import os
import sys
import glob
import re
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

SCENARIO_PATH = os.path.join(cfg.IN_PATH, '.scenarios')
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

#TODO: Add functionality that only reruns simulation if the corresponding
#row in main.csv has changed. Right now the .to_hdf function is producing
#unique md5 checksums for repeated runs of this fucntion with the same input.
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

        # Path to requests dir
        reqs_dir = row['REQUESTS_DIR']
        reqs_path = os.path.join(cfg.IN_PATH, 'requests', reqs_dir)

        req_files = glob.glob(reqs_path+'/*.csv')
        for req_file in req_files:
            file_deps.append(req_file)

        # Path to charge network file
        network_file = row['CHARGE_NET_FILE']
        charge_net_file = os.path.join(cfg.IN_PATH, 'charge_network', network_file)

        file_deps.append(charge_net_file)

        vehicle_ids = [{'name': c.replace("_NUM_VEHICLES", ""),
                        'num': row[c]} for c in row.index if 'VEH' in c]

        num_veh_types = len(vehicle_ids)
        assert num_veh_types > 0, 'Must have at least one vehicle type to run simulation.'
        row['NUM_VEHICLE_TYPES'] = str(num_veh_types)
        num_vehicles = 0
        veh_keys = []

        for veh in vehicle_ids:
            num_vehicles += int(veh['num'])
            veh_keys.append(veh['name'])
            veh_file = os.path.join(cfg.IN_PATH, 'vehicles', '{}.csv'.format(veh['name']))
            file_deps.append(veh_file)
            veh_df = pd.read_csv(veh_file)
            veh_df['VEHICLE_TYPE'] = veh['name']
            veh_df['NUM_VEHICLES'] = veh['num']
            data[veh['name']] = veh_df.iloc[0]

        assert num_vehicles > 0, "Must have at least one vehicle to run simulation."
        row['TOTAL_NUM_VEHICLES'] = str(num_vehicles)
        row['VEH_KEYS'] = veh_keys

        data['requests'] = pp.load_requests(reqs_path)
        data['charge_network'] = pd.read_csv(charge_net_file)
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
    if not os.path.isdir(sim_output):
        clean_msg('creating simulation output directory..')
        os.makedirs(sim_output)

    scenario_files = glob.glob(os.path.join(SCENARIO_PATH, '*.pickle'))
    simulations = [(s, basename_stem(s)[:-7]) for s in scenario_files]

    for src, tag in simulations:
        print(src)
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
