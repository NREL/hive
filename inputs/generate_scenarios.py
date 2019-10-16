import csv
import yaml
import json
import os

import pandas as pd

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
LIB_PATH = os.path.join(THIS_DIR, 'library')
STATIC_PATH = os.path.join(LIB_PATH, '.static')
SCENARIO_PATH = os.path.join(THIS_DIR, 'scenarios')
GENERATOR_FILE = os.path.join(THIS_DIR, 'scenario_generator.csv')


def load_csv(filepath):
    result = []
    with open(filepath, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            result.append(dict(row))

    return result


def load_vehicles(fleet):
    vehicles = []
    for entry in fleet:
        veh_name = entry['VEHICLE_NAME']
        num_vehicles = entry['NUM_VEHICLES']
        vehicle_file = os.path.join(LIB_PATH, 'vehicles', f'{veh_name}.csv')
        with open(vehicle_file, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['NUM_VEHICLES'] = num_vehicles
                row['VEHICLE_NAME'] = veh_name
                vehicles.append(dict(row))

    return vehicles


def read_parameters(scenario):
    result = {}
    PARAMETERS = [
        'MAX_DISPATCH_MILES',
        'MAX_ALLOWABLE_IDLE_MINUTES',
        'LOWER_SOC_THRESH_STATION',
        'UPPER_SOC_THRESH_STATION',
        'MIN_ALLOWED_SOC',
    ]
    for param in PARAMETERS:
        result[param] = scenario[param]

    return result


def build_scenarios():
    with open(GENERATOR_FILE, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for scenario in reader:
            config = {}

            charge_profile_file = os.path.join(STATIC_PATH, 'raw_leaf_curves.csv')
            whmi_lookup_file = os.path.join(STATIC_PATH, 'wh_mi_lookup.csv')

            filepaths = {}
            requests_file = os.path.join(LIB_PATH,
                                         'requests',
                                         scenario['REQUESTS_FILE'])
            filepaths['requests_file_path'] = requests_file

            operating_area_file = os.path.join(LIB_PATH,
                                               'operating_area',
                                               scenario['OPERATING_AREA_FILE'])
            filepaths['operating_area_file_path'] = operating_area_file

            config['filepaths'] = filepaths

            charge_stations_file = os.path.join(LIB_PATH,
                                                'charge_network',
                                                scenario['CHARGE_STATIONS_FILE'])

            vehicle_bases_file = os.path.join(LIB_PATH,
                                              'charge_network',
                                              scenario['VEH_BASES_FILE'])

            fleet_file = os.path.join(LIB_PATH,
                                      'fleet',
                                      scenario['FLEET_FILE'])

            parameters = read_parameters(scenario)
            config['parameters'] = parameters

            fleet = load_csv(fleet_file)

            vehicles = load_vehicles(fleet)
            config['vehicles'] = vehicles

            bases = load_csv(vehicle_bases_file)
            config['bases'] = bases

            stations = load_csv(charge_stations_file)
            config['stations'] = stations

            charge_profile_df = pd.read_csv(charge_profile_file)
            config['charge_profile'] = {
                'soc': charge_profile_df.soc.to_list(),
                'kw': charge_profile_df.kw.to_list(),
            }

            whmi_df = pd.read_csv(whmi_lookup_file)
            config['whmi_lookup'] = {
                'mph': whmi_df.mph.to_list(),
                'wh_mi_factor': whmi_df.wh_mi_factor.to_list(),
            }

            config['ASSIGNMENT'] = scenario['ASSIGNMENT']
            config['REPOSITIONING'] = scenario['REPOSITIONING']

            name = scenario['SCENARIO_NAME']
            outfile = os.path.join(SCENARIO_PATH, f'{name}.yaml')
            with open(outfile, 'w+') as f:
                yaml.dump(config, f, sort_keys=False)


if __name__ == "__main__":
    build_scenarios()
