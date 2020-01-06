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

At this point, HIVE 

HIVE has only two major dependencies. Uber H3 is a geospatial index which HIVE uses for
positioning and search. PyYAML is used to load YAML-based configuration and scenario files.

- [H3](https://github.com/uber/h3)
- [PyYAML](https://github.com/yaml/pyyaml)

While HIVE is also dependent on the following libraries, there are plans to remove them.
Pint is a units library, Haversine provides the Haversine distance function. Numpy is being
used to interpolate tabular data.  

- [pint](https://pint.readthedocs.io/en/0.10/)
- [haversine](https://github.com/mapado/haversine)
- [numpy](https://www.numpy.org/)

## Setup

Setting up hive can be accomplished in a couple steps. First you need to 
make sure you have the right packages installed. An easy way to do this 
is to use conda which can be obtained here:

- [https://www.anaconda.com/download/](https://www.anaconda.com/download/) (anaconda)
- [https://conda.io/miniconda.html](https://conda.io/miniconda.html) (miniconda)

To build the environment simply run:

    > conda env create -f environment.yml
    
Then, activate the environment with:

    > conda activate hive
    
The developer API is a [Sphinx](http://www.sphinx-doc.org/en/master/) project which can be built by installing 
Sphinx with type hints via `pip install sphinx-autodoc-typehints` and following the build instructions.

## Running a Scenario

![Map of Denver Downtown](app/scenarios/denver_demo.jpg?raw=true)

Running HIVE takes one argument, which is a configuration file. Hive v0.3.0 comes packaged with a demo scenario 
for Downtown Denver, located at `app/scenarios/denver_demo.yaml`. This file names the inputs and the configuration
Parameters for running HIVE. Additional parameters exist with default values assigned, which will be documented in 
a future version of HIVE.

In order to run our demo scenario we just need to navigate to the `app/` sub directory and run HIVE:

    > cd app
    > python run.py scenarios/denver_demo.yaml

This runs the demo scenario and writes outputs to `app/denver_demo_outputs`. These output files can be parsed 
by Pandas using `pd.read_json(output_file.json, lines=True)` (for Pandas > 0.19.0).

## Roadmap

HIVE intends to implement the following features:

- Routing from OSM networks with time-varying speeds
- Revised trip energy & recharging
- Economics
- Fleet control algorithms from literature for more optimal control
- Gasoline vehicles
- Integration into vehicle and grid energy models
- Dynamic energy pricing
- Distributed HPC cluster implementation for large problem inputs

## License

Highly Integrated Vehicle Ecosystem (HIVE)  Copyright ©2019   Alliance for Sustainable Energy, LLC All Rights Reserved

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