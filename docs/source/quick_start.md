# Quick Start

You can install hive with `pip install nrel.hive`
(see the [README](https://github.com/NREL/hive) for more detailed instructions)

HIVE is typically run using the command line interface (CLI) by calling the `hive` command.
For example, you can run either of the pre-packaged scenarios with `hive denver_demo.yaml` or `hive manhattan.yaml`.

The model takes in a single configuration file that specifies everything that makes up a single simulation (see the inputs page).

When the simulation is run (`hive denver_demo.yaml` for example), the model will write several output files that describe what happened during the simulation (see the outputs page).

You can also use hive as library for co-simulation or to implement custom control logic (see the customize page).

Lastly, if you're interested in contributing, checkout the developer page!
