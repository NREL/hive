# HIVE :honeybee:

**H**ighly  
**I**ntegrated  
**V**ehicle  
**E**cosystem  
  
HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at
the National Renewable Energy Laboratory in Golden, Colorado, USA.

## What is HIVE

HIVE is model for evaluating the performance of ride hail fleets over
arbitrary supply/demand scenarios. Models for mobility services often have a large barrier-
to-entry due to the complex interactions of mode choice, economics, and model tuning required
to use the leading mesoscopic transportation models (BEAM, POLARIS, MATSim, etc.). HIVE attempts
to fill a gap for researchers seeking to study the economic and energy impacts of autonomous
ride hail fleets by providing the following features:

- agent-based model (ABM)
- data-driven control interfaces for Model-Predicted Control and Reinforcement Learning research
- easy integration/co-simulation (can be called alongside other software tools)
- dynamic dispatch, trip energy, routing, and economics
    - price signals limited to fleet and energy grid with exogenous request data
- simple to define/share scenarios via configuration files and simulation snapshots
- 100% Python (v 3.8) code with a small number of dependencies

The project is currently closed-source and in alpha development, with plans to open-source in summer of 2020.

## Dependencies

HIVE has only three major dependencies. Uber H3 is a geospatial index which HIVE uses for
positioning and search. PyYAML is used to load YAML-based configuration and scenario files.
Immutables provides the implementation of an immutable map to replace the standard Python 
Dictionary, which will be available in Python 3.9.

- [H3](https://github.com/uber/h3)
- [PyYAML](https://github.com/yaml/pyyaml)
- [immutables](https://github.com/MagicStack/immutables)

While HIVE is also dependent on the following libraries, there are plans to remove them.
Pint is a units library, Haversine provides the Haversine distance function. Numpy is being
used to interpolate tabular data.  

- [pint](https://pint.readthedocs.io/en/0.10/)
- [haversine](https://github.com/mapado/haversine)
- [numpy](https://www.numpy.org/)

## Setup

HIVE is currently available on [github.nrel.gov](github.nrel.gov). You must be connected
(via LAN/VPN) to NREL and have an account with the correct access privileges to access it.

    > git clone https://github.nrel.gov/MBAP/hive

#### install and run via pip

to load hive as a command line application via pip, tell pip to install hive by pointing to the directory
that git downloaded:

    > python -m pip install -e <path/to/hive>
   
Then you can run hive as a command line application:

    > hive hive/resources/scenarios/denver_demo.yaml

#### run as a vanilla python module

To run from the console, run the module (along with a scenario file, such as `denver_demo.yaml`):
       
    > cd hive
    > python -m hive hive/resources/scenarios/denver_demo.yaml 

#### build api documentation (optional)

The developer API is a [Sphinx](http://www.sphinx-doc.org/en/master/) project which can be built by installing 
Sphinx with type hints via `pip install sphinx-autodoc-typehints` and following the build instructions.

## Looking at a default scenario

![Map of Denver Downtown](docs/images/denver_demo.jpg?raw=true)

Running HIVE takes one argument, which is a configuration file. Hive comes packaged with a demo scenario 
for Downtown Denver, located at `hive/resources/scenarios/denver_demo.yaml`. This file names the inputs and the configuration
Parameters for running HIVE.

the Denver demo scenario is configured to log output to a folder named `denver_demo_outputs` which is also tagged
with a timestamp. These output files can be parsed by Pandas using `pd.read_json(output_file.json, lines=True)` (for Pandas > 0.19.0). 
Additionally, some high-level stats are shown at the console.

Running this scenario should produce an output similar to the following:

```
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/
    
attempting to load config: resources/scenarios/denver_demo.yaml
initializing scenario
running HIVE
simulating 28800 of 111600 seconds
simulating 32400 of 111600 seconds
simulating 36000 of 111600 seconds
simulating 39600 of 111600 seconds
simulating 43200 of 111600 seconds
simulating 46800 of 111600 seconds
simulating 50400 of 111600 seconds
simulating 54000 of 111600 seconds
simulating 57600 of 111600 seconds
simulating 61200 of 111600 seconds
simulating 64800 of 111600 seconds
simulating 68400 of 111600 seconds
simulating 72000 of 111600 seconds
simulating 75600 of 111600 seconds
simulating 79200 of 111600 seconds
simulating 82800 of 111600 seconds
simulating 86400 of 111600 seconds
simulating 90000 of 111600 seconds
simulating 93600 of 111600 seconds
simulating 97200 of 111600 seconds
simulating 100800 of 111600 seconds
simulating 104400 of 111600 seconds
simulating 108000 of 111600 seconds
simulating 111600 of 111600 seconds


done! time elapsed: 4.63 seconds


STATION  CURRENCY BALANCE:             $ 201.86
FLEET    CURRENCY BALANCE:             $ 11945.64
         VEHICLE KILOMETERS TRAVELED:    4450.54
         AVERAGE FINAL SOC:              34.61%

```
 
## Roadmap

HIVE intends to implement the following features:

- Routing from OSM networks with time-varying speeds
- Revised trip energy & recharging
- Fleet control algorithms from literature for more optimal control
- Gasoline vehicles
- Integration into vehicle and grid energy models
- Distributed HPC cluster implementation for large problem inputs

## License

Highly Integrated Vehicle Ecosystem (HIVE)  Copyright ©2020   Alliance for Sustainable Energy, LLC All Rights Reserved

This computer software was produced by Alliance for Sustainable Energy, LLC under Contract No. DE-AC36-08GO28308 with
the U.S. Department of Energy. For 5 years from the date permission to assert copyright was obtained, the Government is
granted for itself and others acting on its behalf a non-exclusive, paid-up, irrevocable worldwide license in this
software to reproduce, prepare derivative works, and perform publicly and display publicly, by or on behalf of the
Government. There is provision for the possible extension of the term of this license.
Subsequent to that period or any extension granted, the Government is granted for itself and others acting on its
behalf a non-exclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works,
distribute copies to the public, perform publicly and display publicly, and to permit others to do so. The specific
term of the license can be identified by inquiry made to Alliance for Sustainable Energy, LLC or DOE. NEITHER ALLIANCE
FOR SUSTAINABLE ENERGY, LLC, THE UNITED STATES NOR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF THEIR EMPLOYEES,
MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LEGAL LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS,
OR USEFULNESS OF ANY DATA, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD NOT INFRINGE
PRIVATELY OWNED RIGHT