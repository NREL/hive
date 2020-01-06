# HIVE :honeybee:

**H**ighly  
**I**ntegrated  
**V**ehicle  
**E**cosystem  
  
HIVE is a mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at
the National Renewable Energy Laboratory in Golden, Colorado, USA.

## What is HIVE

HIVE is an agent-based model (ABM) for modeling the performance of ride hail fleets over
arbitrary supply/demand scenarios. Models for mobility services often have a large barrier-
to-entry due to the complex interactions of mode choice, economics, and model tuning required
to use the leading mesoscopic transportation models (BEAM, POLARIS, MATSim, etc.). HIVE attempts
to fill a gap for researchers seeking to study the economic and energy impacts of autonomous
ride hail fleets by providing the following features:

- dynamic dispatch, trip energy, routing, and economics
    - price signals limited to fleet and energy grid with exogenous request data
- simple to define/share scenarios
- easy integration/co-simulation (can be called alongside other software tools)
- 100% Python code

The project is currently closed-source and in alpha development, with plans to open-source in summer of 2020.
The developer API can be found at [docs/index.html](/docs/index.html).

## Dependencies

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

## Running a Scenario

Hive v0.3.0 comes packaged with a demo scenario for Downtown Denver. In order
to run our demo scenario we just need to navigate to the app/ sub directory
and run:

    > python run.py scenarios/denver_demo.yaml

This runs the demo scenario and writes outputs to `app/denver_demo_outputs`

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