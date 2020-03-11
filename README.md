# HIVE :honeybee:

**H**ighly  
**I**ntegrated  
**V**ehicle  
**E**cosystem  

HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.

## What is HIVE

HIVE is a complete autonomous ridehail simulator supporting charging infrastructure and fleet composition research, designed for ease-of-use, scalability, and co-simulation. HIVE employs powerful, community-driven deep reinforcement learning algorithms to synthesize an optimal fleet performance and for runs over HPC systems for large-scale problems. HIVE is designed to integrate with vehicle power and energy grid power models in real-time for accurate, high-fidelity playouts over arbitrary road networks and demand scenarios.
​
## Why is HIVE?

When the Mobility, Behavior, and Advanced Powertrains group began looking to answer questions related to fleet sizing, charging infrastructure, and dynamic energy pricing, we could not find a simulator which was right-sized for our research questions. Most modern models for mobility services have a large barrier-to-entry due to the complex interactions of mode choice, economics, and model tuning required to use the leading micro and mesoscopic transportation models (BEAM, POLARIS, MATSim, SUMO, AMoDeus, etc.). Additionally, they have heavyweight technical infrastructure demands where deployment of these models requires a specialized team. HIVE attempts to fill a gap for researchers seeking to study the economic and energy impacts of autonomous ride hail fleets by providing the following feature set:

- agent-based model (ABM)
- data-driven control interfaces for Model-Predicted Control and Reinforcement Learning research
- easy integration/co-simulation (can be called alongside other software tools)
- dynamic dispatch, trip energy, routing, and economics
- simple to define/share scenarios via configuration files and simulation snapshots
- 100% Python (v 3.8) code with a small(ish) set of dependencies

HIVE is not a fully-featured Activity-Based Model, does not simulate all vehicles on the network, and therefore does not simulate congestion. It also assumes demand is fixed. If these assumptions are too strong for your research question, then one of the other mesoscopic models capable of ridehail simulation may be a more appropriate fit. The following (opinionated) chart attempts to compare features of HIVE against LBNL's BEAM and ANL's POLARIS models.

| feature                                            | HIVE | BEAM | POLARIS |
| -------------------------------------------------- | ---- | ---- | ------- |
| Agent-Based Ridehail Model                         | √    | √    | √       |
| Designed for large-scale inputs                    | √    | √    | √       |
| Integrates with NREL energy models                 | √    | √    | √       |
| Charging infrastructure & charge events            | √    | √    | √       |
| Service pricing and income model                   | √    | √    | √       |
| Data-driven ridehail dispatcher                    | √    | x    | x       |
| Does not require socio-demographic data            | √    | x    | x       |
| Built-in example scenario                          | √    | √    | x       |
| Written entirely in Python, installed via pip      | √    | x    | x       |
| Activity-Based Demand Model                        | x    | √    | √       |
| Dynamic demand using behavioral models             | x    | √    | √       |
| Robust assignment of population demographics       | x    | √    | √       |
| Supports broad set of travel modes                 | x    | √    | √       |
| Congestion modeling via kinetic wave model         | x    | √    | √       |

The project is currently closed-source and in alpha development, with plans to open-source in summer of 2020.

## Dependencies

HIVE has four major dependencies. Uber H3 is a geospatial index which HIVE uses for positioning and search. PyYAML is used to load YAML-based configuration and scenario files. Immutables provides the implementation of an immutable map to replace the standard Python `Dict` type, which will (likely) be available in Python 3.9. NetworkX provides a graph library used as a road network.

- [H3](https://github.com/uber/h3)
- [PyYAML](https://github.com/yaml/pyyaml)
- [immutables](https://github.com/MagicStack/immutables)
- [networkx](https://github.com/networkx/networkx)

Uber H3 depends on an installation of [cmake](https://pypi.org/project/cmake/). See [this link](https://github.com/uber/h3-py#installing-on-windows) for windows installation instructions.

While HIVE is also dependent on the following libraries, there are plans to remove them. Numpy is being used to interpolate tabular data. Osmnx is being used to interact with open street maps.

- [numpy](https://www.numpy.org/)
- [osmnx](https://github.com/gboeing/osmnx)

## Setup

HIVE is currently available on [github.nrel.gov](github.nrel.gov). You must be connected (via LAN/VPN) to NREL and have an account with the correct access privileges to access it.

    > git clone https://github.nrel.gov/MBAP/hive

Installing can be completed either using [pip](https://pypi.org/project/pip/) or by running python at the command line:

#### install and run via pip

to load hive as a command line application via pip, tell pip to install hive by pointing to the directory that git downloaded:

    > python -m pip install -e <path/to/hive>

Then you can run hive as a command line application:

    > hive hive/resources/scenarios/denver_demo.yaml

#### run as a vanilla python module

To run from the console, run the module (along with a scenario file, such as `denver_demo.yaml`):
       
    > cd hive
    > python -m hive hive/resources/scenarios/denver_demo.yaml

#### build api documentation (optional)

The developer API is a [Sphinx](http://www.sphinx-doc.org/en/master/) project which can be built by installing Sphinx with type hints via `pip install sphinx-autodoc-typehints` and following the build instructions.

## Looking at a default scenario

![Map of Denver Downtown](docs/images/denver_demo.jpg?raw=true)

Running HIVE takes one argument, which is a configuration file. Hive comes packaged with a demo scenario  for Downtown Denver, located at `hive/resources/scenarios/denver_demo.yaml`. This file names the inputs and the configuration Parameters for running HIVE.

the Denver demo scenario is configured to log output to a folder named `denver_demo_outputs` which is also tagged with a timestamp. These output files can be parsed by Pandas using `pd.read_json(output_file.json, lines=True)` (for Pandas > 0.19.0). Additionally, some high-level stats are shown at the console.

Running this scenario should produce an output similar to the following:

```
[INFO] - hive.app.run -
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/

[INFO] - hive.app.run - successfully loaded config: resources/scenarios/denver_demo.yaml
[INFO] - hive.runner.local_simulation_runner - simulating 28800 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 32400 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 36000 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 39600 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 43200 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 46800 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 50400 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 54000 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 57600 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 61200 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 64800 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 68400 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 72000 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 75600 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 79200 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 82800 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 86400 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 90000 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 93600 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 97200 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 100800 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 104400 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 108000 of 111600 seconds
[INFO] - hive.runner.local_simulation_runner - simulating 111600 of 111600 seconds
[INFO] - hive.app.run -

[INFO] - hive.app.run - done! time elapsed: 28.43 seconds
[INFO] - hive.app.run -

[INFO] - hive.app.run - STATION  CURRENCY BALANCE:             $ 249.26
[INFO] - hive.app.run - FLEET    CURRENCY BALANCE:             $ 11509.16
[INFO] - hive.app.run -          VEHICLE KILOMETERS TRAVELED:    5089.59
[INFO] - hive.app.run -          AVERAGE FINAL SOC:              72.92%
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
- [ ] Support for Monte Carlo RL algorithms
- [ ] Charge Queueing
- [ ] Ridehail Pooling
- [ ] Gasoline vehicles
- [ ] Distributed HPC cluster implementation for large problem inputs

## License

Highly Integrated Vehicle Ecosystem (HIVE)  Copyright ©2020   Alliance for Sustainable Energy, LLC All Rights Reserved

This computer software was produced by Alliance for Sustainable Energy, LLC under Contract No. DE-AC36-08GO28308 with the U.S. Department of Energy. For 5 years from the date permission to assert copyright was obtained, the Government is granted for itself and others acting on its behalf a non-exclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, and perform publicly and display publicly, by or on behalf of the Government. There is provision for the possible extension of the term of this license. Subsequent to that period or any extension granted, the Government is granted for itself and others acting on its behalf a non-exclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, distribute copies to the public, perform publicly and display publicly, and to permit others to do so. The specific term of the license can be identified by inquiry made to Alliance for Sustainable Energy, LLC or DOE. NEITHER ALLIANCE FOR SUSTAINABLE ENERGY, LLC, THE UNITED STATES NOR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF THEIR EMPLOYEES, MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LEGAL LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS, OR USEFULNESS OF ANY DATA, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD NOT INFRINGE PRIVATELY OWNED RIGHT