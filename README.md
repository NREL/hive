# HIVE :honeybee:

**H**ighly  
**I**ntegrated  
**V**ehicle  
**E**cosystem  

HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.

## What is HIVE

HIVE is a complete autonomous ridehail simulator supporting charging infrastructure and fleet composition research, designed for ease-of-use, scalability, and co-simulation. HIVE employs powerful, community-driven deep reinforcement learning algorithms to synthesize an optimal fleet performance and for runs over HPC systems for large-scale problems. HIVE is designed to integrate with vehicle power and energy grid power models in real-time for accurate, high-fidelity playouts over arbitrary road networks and demand scenarios.
​
## Why HIVE?

When the Mobility, Behavior, and Advanced Powertrains group began looking to answer questions related to fleet sizing, charging infrastructure, and dynamic energy pricing, we could not find a simulator which was right-sized for our research questions. Most modern models for mobility services have a large barrier-to-entry due to the complex interactions of mode choice, economics, and model tuning required to use the leading micro and mesoscopic transportation models (BEAM, POLARIS, MATSim, SUMO, AMoDeus, etc.). Additionally, they have heavyweight technical infrastructure demands where deployment of these models requires a specialized team. HIVE attempts to fill a gap for researchers seeking to study the economic and energy impacts of autonomous ride hail fleets by providing the following feature set:

- agent-based model (ABM)
- data-driven control interfaces for Model-Predicted Control and Reinforcement Learning research
- easy integration/co-simulation (can be called alongside other software tools)
- dynamic dispatch, trip energy, routing, and economics
- simple to define/share scenarios via configuration files and simulation snapshots
- 100% Python (v 3.7) code with a small(ish) set of dependencies

HIVE is not a fully-featured Activity-Based Model, does not simulate all vehicles on the network, and therefore does not simulate congestion. It also assumes demand is fixed. If these assumptions are too strong for your research question, then one of the other mesoscopic models capable of ridehail simulation may be a more appropriate fit. The following (opinionated) chart attempts to compare features of HIVE against LBNL's BEAM and ANL's POLARIS models.

| feature                                            | HIVE       | BEAM      | POLARIS |
| -------------------------------------------------- | ---------- | --------- | ------- |
| Agent-Based Ridehail Model                         | :honeybee: | :red_car: | :train: |
| Designed for large-scale inputs                    | :honeybee: | :red_car: | :train: |
| Integrates with NREL energy models                 | :honeybee: | :red_car: | :train: |
| Charging infrastructure & charge events            | :honeybee: | :red_car: | :train: |
| Service pricing and income model                   | :honeybee: | :red_car: | :train: |
| Data-driven ridehail dispatcher                    | :honeybee: |           |         |
| Does not require socio-demographic data            | :honeybee: |           |         |
| Built-in example scenario                          | :honeybee: | :red_car: |         |
| Written entirely in Python, installed via pip      | :honeybee: |           |         |
| Activity-Based Demand Model                        |            | :red_car: | :train: |
| Dynamic demand using behavioral models             |            | :red_car: | :train: |
| Robust assignment of population demographics       |            | :red_car: | :train: |
| Supports broad set of travel modes                 |            | :red_car: | :train: |
| Congestion modeling via kinetic wave model         |            | :red_car: | :train: |

The project is currently closed-source, pre-release, with plans to open-source in summer of 2020.

## Dependencies

HIVE has four major dependencies. Uber H3 is a geospatial index which HIVE uses for positioning and search. PyYAML is used to load YAML-based configuration and scenario files. Immutables provides the implementation of an immutable map to replace the standard Python `Dict` type, which will (likely) be available in Python 3.9. NetworkX provides a graph library used as a road network. SciPy provides some optimization algorithms used by HIVE dispatchers.

- [H3](https://github.com/uber/h3)
- [PyYAML](https://github.com/yaml/pyyaml)
- [immutables](https://github.com/MagicStack/immutables)
- [networkx](https://github.com/networkx/networkx)
- [SciPy](https://www.scipy.org/)

_note: Uber H3 depends on an installation of [cmake](https://pypi.org/project/cmake/) which can cause issues on Windows. If you encounter errors when attempting the standard Hive installation instructions below, then consider first running `conda install -c conda-forge h3-py`._

While HIVE is also dependent on the following libraries, there are plans to remove them. Numpy is being used to interpolate tabular data. Pandas is being used to interact with open street maps. Rtree is used for quick node lookup on the road network.

- [numpy](https://www.numpy.org/)
- [pandas](https://pandas.pydata.org/)
- [rtree](https://pypi.org/project/Rtree/)

## Setup

HIVE is currently available on [github.nrel.gov](github.nrel.gov). You must be connected (via LAN/VPN) to NREL and have an account with the correct access privileges to access it.

    > git clone https://github.nrel.gov/MBAP/hive

Installing can be completed either using [pip](https://pypi.org/project/pip/) and [conda](https://www.anaconda.com/) or by running python at the command line:

#### install and run via pip/conda

first, create a new conda environment running:

    > conda env create -f <path/to/hive>/environment.yml

then, to load hive as a command line application via pip, tell pip to install hive by pointing to the directory that git downloaded:

    > python -m pip install -e <path/to/hive>

Then you can run hive as a command line application. For example, to run the built-in Denver scenario, type:

    > hive denver_demo.yaml
   
Note: the program will automatically look for the default scenarios, listed below. If you want
the program to use a file outside of this location, just specify the optional `--path` argument:

    > hive some_other_directory/my_scenario.yaml

#### run as a vanilla python module

To run from the console, run the module (along with a scenario file, such as `denver_demo.yaml`):
       
    > cd hive
    > python -m hive denver_demo.yaml


#### available scenarios

The following built-in scenario files come out-of-the-box, and available directly by name:

scenario | description
---------|------------
denver_demo.yaml | default demo scenario with 20 vehicles and 2.5k requests synthesized with uniform time/location sampling
denver_rl_toy.yaml | extremely simple scenario for testing RL
denver_demo_constrained_charging.yaml | default scenario with limited charging supply
manhattan.yaml | larger test scenario with 200 vehicles and 20k requests sampled from the NY Taxi Dataset

#### global configuration

Some values are set by a global configuration file. The defaults are set at hive/resources/defaults/.hive.yaml. If you want
to override any entries in this file, you can create a new one by the same name `.hive.yaml` and place it in your working
directory or a parent directory. Hive will also check your base user directory for this file (aka `~/.hive.yaml`).

#### build api documentation (optional)

The developer API is a [Sphinx](http://www.sphinx-doc.org/en/master/) project which can be built by installing Sphinx with type hints via `pip install sphinx-autodoc-typehints` and following the build instructions.

## Looking at a default scenario

![Map of Denver Downtown](docs/images/denver_demo.jpg?raw=true)

Running HIVE takes one argument, which is a configuration file. Hive comes packaged with a demo scenario for Downtown Denver, located at `hive/resources/scenarios/denver_demo.yaml`. This file names the inputs and the configuration Parameters for running HIVE.

the Denver demo scenario is configured to log output to a folder named `denver_demo_outputs` which is also tagged with a timestamp. These output files can be parsed by Pandas using `pd.read_json(output_file.json, lines=True)` (for Pandas > 0.19.0). Additionally, some high-level stats are shown at the console.

Running this scenario should produce an output similar to the following:

```
[INFO] - hive -
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/

[INFO] - hive.config.hive_config - global hive configuration loaded from /Users/rfitzger/dev/nrel/hive/hive/.hive.yaml
[INFO] - hive.config.hive_config -   global_settings_file_path: /Users/rfitzger/dev/nrel/hive/hive/.hive.yaml
[INFO] - hive.config.hive_config -   output_base_directory: /Users/rfitzger/data/hive/outputs
[INFO] - hive.config.hive_config -   local_parallelism: 1
[INFO] - hive.config.hive_config -   local_parallelism_timeout_sec: 60
[INFO] - hive.config.hive_config -   log_run: True
[INFO] - hive.config.hive_config -   log_sim: True
[INFO] - hive.config.hive_config -   log_level: INFO
[INFO] - hive.config.hive_config -   log_sim_config: {'vehicle_report', 'dispatcher', 'cancel_request', 'add_request', 'charge_event', 'station_report', 'request_report'}
[INFO] - hive.config.hive_config -   log_period_seconds: 60
[INFO] - hive.config.hive_config -   lazy_file_reading: False
[INFO] - hive.config.hive_config - output directory set to /Users/rfitzger/dev/nrel/hive/hive/hive/resources/scenarios/denver_downtown
[INFO] - hive.config.hive_config - hive config loaded from /Users/rfitzger/dev/nrel/hive/hive/hive/resources/scenarios/denver_downtown/denver_demo.yaml
[INFO] - hive.config.hive_config -
dispatcher:
  active_states:
  - idle
  - repositioning
  - dispatchtrip
  - servicingtrip
  - dispatchstation
  - chargingstation
  base_charging_range_km_threshold: 100
  charging_range_km_threshold: 20
  default_update_interval_seconds: 600
  ideal_fastcharge_soc_limit: 0.8
  matching_range_km_threshold: 20
  max_search_radius_km: 100.0
  valid_dispatch_states:
  - Idle
  - Repositioning
input:
  bases_file: denver_demo_bases.csv
  charging_price_file: denver_charging_prices_by_geoid.csv
  demand_forecast_file: denver_demand.csv
  geofence_file: downtown_denver.geojson
  mechatronics_file: mechatronics.csv
  rate_structure_file: rate_structure.csv
  requests_file: denver_demo_requests.csv
  road_network_file: downtown_denver.xml
  stations_file: denver_demo_stations.csv
  vehicles_file: denver_demo_vehicles.csv
network:
  default_speed_kmph: 40.0
  network_type: osm_network
sim:
  end_time: '1970-01-02T00:00:00-07:00'
  request_cancel_time_seconds: 600
  sim_h3_resolution: 15
  sim_h3_search_resolution: 7
  sim_name: denver_demo
  start_time: '1970-01-01T00:00:00-07:00'
  timestep_duration_seconds: 60

[INFO] - hive - creating run log at /Users/rfitzger/data/hive/outputs/denver_demo_2020-06-01_17-13-58/run.log with log level INFO
[INFO] - hive - running simulation for time 25200 to 111600:
100%|██████████| 1440/1440 [00:05<00:00, 242.69it/s]
[INFO] - hive - done! time elapsed: 5.94 seconds
[INFO] - hive - STATION  CURRENCY BALANCE:             $ 277.21
[INFO] - hive - FLEET    CURRENCY BALANCE:             $ 12032.24
[INFO] - hive -          VEHICLE KILOMETERS TRAVELED:    6428.65
[INFO] - hive -          AVERAGE FINAL SOC:              53.29%

Process finished with exit code 0
```

## Data-Driven Control

HIVE is designed to answer questions about data-driven optimal fleet control. An interface for OpenAI Gym is provided in a separate repo, [gym-hive](https://github.nrel.gov/MBAP/gym-hive). For more information on OpenAI Gym, please visit the [OpenAI Gym website](https://gym.openai.com/).

## Roadmap
_Updated March 11, 2020_

HIVE intends to implement the following features:

- [x] Routing from OSM networks
- [x] Integration into OpenAI Gym for RL-based control
- [ ] Time-varying network speeds
- [ ] Integration into vehicle powertrain, grid energy, smart charging models
- [ ] Support for state-of-the-art RL control algorithms
- [x] Charge Queueing
- [ ] Ridehail Pooling
- [ ] Gasoline vehicles
- [ ] Distributed HPC cluster implementation for large problem inputs

## License

Highly Integrated Vehicle Ecosystem (HIVE)  Copyright ©2020   Alliance for Sustainable Energy, LLC All Rights Reserved

This computer software was produced by Alliance for Sustainable Energy, LLC under Contract No. DE-AC36-08GO28308 with the U.S. Department of Energy. For 5 years from the date permission to assert copyright was obtained, the Government is granted for itself and others acting on its behalf a non-exclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, and perform publicly and display publicly, by or on behalf of the Government. There is provision for the possible extension of the term of this license. Subsequent to that period or any extension granted, the Government is granted for itself and others acting on its behalf a non-exclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, distribute copies to the public, perform publicly and display publicly, and to permit others to do so. The specific term of the license can be identified by inquiry made to Alliance for Sustainable Energy, LLC or DOE. NEITHER ALLIANCE FOR SUSTAINABLE ENERGY, LLC, THE UNITED STATES NOR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF THEIR EMPLOYEES, MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LEGAL LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS, OR USEFULNESS OF ANY DATA, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD NOT INFRINGE PRIVATELY OWNED RIGHT