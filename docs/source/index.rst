Welcome to hive's documentation!
================================

HIVE™ is an open-source mobility services research platform developed by the Mobility and Advanced Powertrains (MBAP) group at the National Renewable Energy Laboratory in Golden, Colorado, USA.

HIVE supports researchers who explore Electric Vehicle (EV) fleet control, Electric Vehicle Supply Equipment (EVSE) siting, and fleet composition problems, and is designed for ease-of-use, scalability, and co-simulation. 
Out-of-the-box, it provides a baseline set of algorithms for fleet dispatch, but provides a testbed for exploring alternatives from leading research in model-predictive control (MPC) and deep reinforcement learning. 
HIVE is designed to integrate with vehicle power and energy grid power models in real-time for accurate, high-fidelity energy estimation over arbitrary road networks and demand scenarios.

Quickstart
----------

You can install hive with `pip install nrel.hive`
(see the `README <https://github.com/NREL/hive>` for more detailed instructions)

HIVE is typically run using the command line interface (CLI) by calling the `hive` command.
For example, you can run either of the pre-packaged scenarios with `hive denver_demo.yaml` or `hive manhattan.yaml`.

The model takes in a single configuration file that specifies everything that makes up a single simulation (see the inputs page).  

When the simulation is run (`hive denver_demo.yaml` for example), the model will write several output files that describe what happened during the simulation (see the outputs page).

You can also use hive as library for co-simulation or to implement custom control logic (see the customize page).

Lastly, if you're interested in contributing, checkout the developer page!

.. toctree::
   :maxdepth: 1 
   
   example
   inputs
   outputs
   customize
   developer/index




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
