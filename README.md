# <img src="docs/source/images/hive-icon.png" alt="drawing" width="100"/>

**H**ighly
**I**ntegrated
**V**ehicle
**E**cosystem

HIVE™ is an open-source mobility services research platform developed by the Mobility, Behavior, and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.

HIVE supports researchers who explore **Electric Vehicle (EV) fleet control**, **Electric Vehicle Supply Equipment (EVSE) siting**, and **fleet composition** problems, and is designed for _ease-of-use_, _scalability_, and _co-simulation_.
Out-of-the-box, it provides a baseline set of algorithms for fleet dispatch, but provides a testbed for exploring alternatives from leading research in model-predictive control (MPC) and deep reinforcement learning.
HIVE is designed to integrate with vehicle power and energy grid power models in real-time for accurate, high-fidelity energy estimation over arbitrary road networks and demand scenarios.

For more information about HIVE, please visit the [HIVE website](https://www.nrel.gov/hive).

For technical details about the HIVE platform, please see the [Technical Report](https://www.nrel.gov/docs/fy21osti/80682.pdf).

For more documentation on how to use HIVE, please see the [HIVE documentation](https://nrelhive.readthedocs.io/en/latest/).

## Installation

HIVE depends on a Python installation [3.8, 3.9, 3.10, 3.11] and the pip package manager ( [python.org](https://www.python.org/downloads/).
In our installation example we use [conda](https://www.anaconda.com/products/distribution) | for managing a HIVE Python environment.

### (optional) set up a virtual environment using conda

We recommend setting up a virtual environment to install HIVE.
This helps avoiding conflicts with other Python dependencies.
Conda compared to other virtualenv managers like Poetry or Pipenv can be better at managing projects such as this one that use large dependencies (such as SciPy).
One way to do this is to use Anaconda:

1. Install [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
1. Open a terminal or Anaconda Prompt.
1. Create a new virtual environment with the desired Python version: `conda create --name hive python=3.11`
1. Activate the virtual environment `conda activate hive`
1. Continue with the installation instructions below.
   Now your dependencies will be stored within the new virtual environment.

### via pip

    > pip install nrel.hive

### build from source

Clone the repository and install the code via pip:

    > git clone <https://github.com/NREL/hive.git>
    > cd hive
    > pip install -e .

## Run HIVE

run a test of hive using a [built-in scenario](#built-in-scenarios), which are hardcoded:

    > hive denver_demo.yaml

if you want the program to use a file that is not built-in, provide a valid path:

    > hive some_other_directory/my_scenario.yaml

## Built-In Scenarios

The following built-in scenario files come out-of-the-box, and available directly by name:

| scenario                              | description                                                                                              |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| denver_demo.yaml                      | default demo scenario with 20 vehicles and 2.5k requests synthesized with uniform time/location sampling |
| denver_rl_toy.yaml                    | extremely simple scenario for testing RL                                                                 |
| denver_demo_constrained_charging.yaml | default scenario with limited charging supply                                                            |
| denver_demo_fleets.yaml               | default scenario with two competing TNC fleets                                                           |
| manhattan.yaml                        | larger test scenario with 200 vehicles and 20k requests sampled from the NY Taxi Dataset                 |

For more information on how to build your own scenario, please see the [HIVE documentation](https://nrelhive.readthedocs.io/en/latest/inputs.html).

## Dependencies

HIVE attempts to rely on as few dependencies as possible. For the most part, these dependencies are obvious choices from the open-source Python analysis ecosystem:

- [scipy](https://www.scipy.org/) (bipartite matching optimization)
- [numpy](https://numpy.org) (linear interpolation of energy lookup tables)
- [pandas](https://pandas.pydata.org) (file IO)
- [networkx](https://networkx.org) (underlying network model)
- [pyyaml](https://github.com/yaml/pyyaml)
- [tqdm](https://github.com/tqdm/tqdm) (command line progress bars)

Beyond these, HIVE uses Uber H3, a geospatial index which HIVE uses for positioning and search, and MagicStack Immutables, which provides the implementation of an immutable Map to replace the standard Python `Dict` type. The Returns library provides Python-approximations for functional containers. Links provided here:

- [h3](https://github.com/uber/h3) (spatial index)
- [immutables](https://github.com/MagicStack/immutables) ([HAMT](https://en.wikipedia.org/wiki/Hash_array_mapped_trie) implementation for "immutable dict")
- [returns](https://github.com/dry-python/returns) (functional containers)

## Developer documentation

Documentation can be found [here](https://nrelhive.readthedocs.io/en/latest/developer/index.html).

## Why HIVE?

When the Mobility, Behavior, and Advanced Powertrains group began looking to answer questions related to fleet sizing, charging infrastructure, and dynamic energy pricing, we could not find a simulator which was right-sized for our research questions. Most modern models for mobility services have a large barrier-to-entry due to the complex interactions of mode choice, economics, and model tuning required to use the leading micro and mesoscopic transportation models (BEAM, POLARIS, MATSim, SUMO, AMoDeus, etc.). Additionally, they have heavyweight technical infrastructure demands where deployment of these models requires a specialized team. HIVE attempts to fill a gap for researchers seeking to study the economic and energy impacts of autonomous ride hail fleets by providing the following feature set:

- agent-based model (ABM)
- data-driven control interfaces for Model-Predicted Control and Reinforcement Learning research
- easy integration/co-simulation (can be called alongside other software tools)
- dynamic dispatch, trip energy, routing, and economics
- simple to define/share scenarios via configuration files and simulation snapshots
- 100% Python (v 3.7) code with a small(ish) set of dependencies and well-documented code

HIVE is _not_ a fully-featured [Activity-Based Model](https://en.wikipedia.org/wiki/Transportation_forecasting#Activity-based_models), does _not_ simulate all vehicles on the network, and does not simulate congestion. It also assumes demand is fixed. If these assumptions are too strong for your research question, then one of the other mesoscopic models capable of ridehail simulation may be a more appropriate fit. The following (opinionated) chart attempts to compare features of HIVE against LBNL's BEAM and ANL's POLARIS models.

| feature                                       | HIVE       | BEAM      | POLARIS |
| --------------------------------------------- | ---------- | --------- | ------- |
| Agent-Based Ridehail Model                    | :honeybee: | :red_car: | :train: |
| Designed for large-scale inputs               | :honeybee: | :red_car: | :train: |
| Integrates with NREL energy models            | :honeybee: | :red_car: | :train: |
| Charging infrastructure & charge events       | :honeybee: | :red_car: | :train: |
| Service pricing and income model              | :honeybee: | :red_car: | :train: |
| Data-driven ridehail dispatcher               | :honeybee: |           |         |
| Does not require socio-demographic data       | :honeybee: |           |         |
| Built-in example scenario                     | :honeybee: | :red_car: |         |
| Written entirely in Python, installed via pip | :honeybee: |           |         |
| Activity-Based Demand Model                   |            | :red_car: | :train: |
| Dynamic demand using behavioral models        |            | :red_car: | :train: |
| Robust assignment of population demographics  |            | :red_car: | :train: |
| Supports broad set of travel modes            |            | :red_car: | :train: |
| Endogenous traffic congestion modeling        |            | :red_car: | :train: |

## Looking at a default scenario

![Manhattan Animation](docs/source/images/manhattan.gif?raw=true)

Running HIVE takes one argument, which is a configuration file. Hive comes packaged with a demo scenario for Manhattan, located at `hive/resources/scenarios/manhattan/manhattan.yaml`. This file names the inputs and the configuration Parameters for running HIVE.

One the scenario is finished, the console will indicate where the output files have been written and you can load them using pandas:

```python
import pandas as pd
# log files store JSON rows, like a document store
output_file = "manhattan_2021-02-08_11-00-07/state.log"
pd.read_json(output_file, lines=True)
```

By default, these outputs are generated:

| file name               | file type | description                                                               |
| ----------------------- | --------- | ------------------------------------------------------------------------- |
| \<config\>.yaml         | YAML      | the input configuration serialized (can be read back by HIVE)             |
| run.log                 | text      | console log output                                                        |
| event.log               | JSON rows | events that occur, such as vehicle movement, pickup + dropoff events, etc |
| instruction.log         | JSON rows | instructions sent from dispatcher to drivers                              |
| state.log               | JSON rows | entity states at every time step                                          |
| station_capacities.csv  | CSV       | energy load capacity for each station                                     |
| summary_stats.json      | JSON      | summary stats as displayed in run.log but in JSON format                  |
| time_step_stats_all.csv | CSV       | aggregated data across a fleet (or all fleets) by time step               |

Running this scenario should also feed some logging into the console.
First, HIVE announces where it is loading configuration from.
It then dumps the global and scenario configuration to the console.
Finally, after around 65 lines, it begins running the simulation with a progress bar.
After, it prints the summary stats to the console and exits.

## Roadmap

_Updated October, 2022_

HIVE intends to implement the following features in the near-term:

- [ ] Time-varying network speeds
- [ ] Integration into vehicle powertrain, grid energy, smart charging models
- [ ] Ridehail Pooling
- [ ] Improved network modeling (turn costs, signal costs)
- [ ] Support for wiring in choice models
- [ ] Baseline multi-objective dispatcher

## Citation

If you have found HIVE useful for your research, please cite our [technical report](https://www.nrel.gov/docs/fy21osti/80682.pdf) as follows:

```
@techreport{fitzgerald2021highly,
  title={The Highly Integrated Vehicle Ecosystem (HIVE): A Platform for Managing the Operations of On-Demand Vehicle Fleets},
  author={Fitzgerald, Robert and Reinicke, Nicholas and Moniot, Matthew},
  year={2021},
  institution={National Renewable Energy Lab.(NREL), Golden, CO (United States)}
}
```

## Contributors

HIVE is currently maintained by Nick Reinicke ([@nreinicke](https://github.com/nreinicke)) and Rob Fitzgerald ([@robfitzgerald](https://github.com/robfitzgerald)). It would not be what it is today without the support of:

- Brennan Borlaug
- Thomas Grushka
- Jacob Holden
- Joshua Hoshiko
- Eleftheria Kontou
- Matthew Moniot
- Eric Wood
- Clement Raimes

## Notice

Copyright © 2022 Alliance for Sustainable Energy, LLC, Inc. All Rights Reserved

This computer software was produced by Alliance for Sustainable Energy, LLC under Contract No. DE-AC36-08GO28308 with the U.S. Department of Energy. For 5 years from the date permission to assert copyright was obtained, the Government is granted for itself and others acting on its behalf a nonexclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, and perform publicly and display publicly, by or on behalf of the Government. There is provision for the possible extension of the term of this license. Subsequent to that period or any extension granted, the Government is granted for itself and others acting on its behalf a nonexclusive, paid-up, irrevocable worldwide license in this software to reproduce, prepare derivative works, distribute copies to the public, perform publicly and display publicly, and to permit others to do so. The specific term of the license can be identified by inquiry made to Contractor or DOE. NEITHER ALLIANCE FOR SUSTAINABLE ENERGY, LLC, THE UNITED STATES NOR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF THEIR EMPLOYEES, MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LEGAL LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS, OR USEFULNESS OF ANY DATA, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD NOT INFRINGE PRIVATELY OWNED RIGHTS.
