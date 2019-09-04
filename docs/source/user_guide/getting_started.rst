Getting Started
===============

Welcome to the hive simulation platform. This software is designed to allow you to simulate the impacts and operations of mobility fleets with varying parameters.

Here are some of the parameters that you can modify to investigate the respective consequences:

* Locations and operating areas
* Vehicle types and fleet makeup
* Electric vehicle (EV) charging and fueling station networks
* Fleet operational behaviors and dispatching algorithms
* Economic factors and relevant policy considerations
* Customer behavior (i.e., willingness to pool or delay travel).

Inputs
------

Hive comes packaged with a set of default inputs that you can use to familiarize yourself with the platform. These default inputs are located in the :code:`inputs/library/` directory. Here you will find a series of subdirectories that house relevant input files.

charge_network
^^^^^^^^^^^^^^

This folder houses the fuel station networks that will be used for the simulation.

Hive recognizes two distinct types of FuelStations:

The first is the aptly titled "station" and this serves as a location for vehicles to charge or refuel on demand.

The second type is the "base" which represents a location to which the vehicle can return when not actively serving the trip population. These bases share all of the properties of a station and vehicles can charge while occupying a base.

Each station and base network file must be have at least the following columns:

* :code:`id`: The unique id for the FuelStation.
* :code:`longitude`: The longitude of the FuelStation.
* :code:`latitude`: The latitude of the FuelStation.
* :code:`plugs`: The number of plugs at the FuelStation.
* :code:`plug_type`: The type of plug at the FuelStation.
* :code:`plug_power_kw`: The power of the plug(s) at the FuelStation.

cost_of_electricity
^^^^^^^^^^^^^^^^^^^

TODO: Add description of this input subdirectory

fleet
^^^^^

This folder houses the parameters for a specific fleet of vehicles. Specifically, it defines the types of vehicles in a fleet and their respective quantities.

The fleet file must have at lease the following columns:

* :code:`VEHICLE_NAME`: This name refers to a vehicle in the vehicles input directory. It must match exactly.
* :code:`NUM_VEHICLES`: The number of vehicles for a particular vehicle type.

operating_area
^^^^^^^^^^^^^^

TODO: Add description of this input subdirectory

requests
^^^^^^^^

This folder houses the requests that hive will use as a ground truth for travel demand.

Each requests file represents a series of trip requests at a specific time and with a specific origin and destination.

The requests file must have at least the following columns:

* :code:`pickup_time`: The timestamp of the pickup time.
* :code:`dropoff_time`: The timestamp of the dropoff time.
* :code:`distance_miles`: The distance of the trip in miles.
* :code:`pickup_lat`: The latitude of the pickup location.
* :code:`pickup_lon`: The longitude of the pickup location.
* :code:`dropoff_lat`: The latitude of the dropoff location.
* :code:`dropoff_lon`: The longitude of the dropoff location.

The requests file may also have any of the following optional columns:

* :code:`passengers`: The number of passengers for a specific trip.

vehicles
^^^^^^^^

This folder houses unique vehicle definitions. Each vehicle file name must correspond to the VEHICLE_NAME field in the fleet file.

Each vehicle file represents a unique vehicle type and must have at least the following columns:

* :code:`BATTERY_CAPACITY_KWH`: The battery capacity of the vehicle in kilowatt-hours.
* :code:`PASSENGERS`: The maximum number of passengers the vehicle can hold.
* :code:`EFFICIENCY_WHMI`: The energy efficiency of the vehicle in watt-hours/mile.
* :code:`MAX_KW_ACCEPTANCE`: The maximum power acceptance of the vehicle in kilowatts.

Building scenarios from input library
-------------------------------------

In order to run a scenario, you need to generate a :code:`scenario.yaml` file. These files should be located in the :code:`inputs/scenarios` directory.

Hive comes with two sample scenario files but if you want to generate your own, you'll need to use the :code:`generate_scenarios.py` tool.

This tool looks at the :code:`scenario_generator.csv` file. For each row within this file, the tool will generate a unique scenario. The :code:`scenario_generator.csv` file must have at least the following columns:

* :code:`SCENARIO_NAME`: A unique name for the scenario.
* :code:`REQUESTS_FILE`: The name of the requests file for the scenario. Hive looks for this file in the :code:`inputs/library/requests/` directory.
* :code:`CHARGE_STATIONS_FILE`: The name of the station network file for the scenario. Hive looks for this file in the :code:`inputs/library/charge_network/` directory.
* :code:`VEH_BASES_FILE`: The name of the base network file for the scenario. Hive looks for this file in the :code:`inputs/library/charge_network/` directory.
* :code:`FLEET_FILE`: The name of the fleet file for the scenario. Hive looks for this file in the :code:`inputs/library/fleet/` directory.
* :code:`MAX_DISPATCH_MILES`: The maximum distance that a vehicle can travel to service a trip.
* :code:`MAX_ALLOWABLE_IDLE_MINUTES`: The maximum amount of time that a vehicle can idle after serving a trip before returning to its respective base.
* :code:`LOWER_SOC_THRESH_STATION`: The threshold for vehicle SOC that indicates when they should seek charging.
* :code:`UPPER_SOC_THRESH_STATION`: The threshold for which a vehicle will consider a full charge.
* :code:`MIN_ALLOWED_SOC`: The minimum allowable SOC for a vehicle to maintain. The dispatcher will not allow vehicles to take a trip if their SOC is projected to fall below this value.

Now, to generate the scenarios, simply run:

.. code-block::

    > python generate_scenarios.py

Running your first scenario
---------------------------

We're finally ready to run our first scenarios. We'll demonstrate this process with the two scenarios included with the package.

We can define the scenarios that hive will run in the :code:`config.py` file that lives in the root directory. Within it is a list titled :code:`SCENARIOS`. Here you should see the names of the two scenario files :code:`aus-test` and :code:`nyc-test`.

Now, simply navigate to the root directory and run the command:

.. code-block::

    > python run.py

If you've set the :code:`VERBOSE` flag to :code:`True` in :code:`config.py`, you'll see hive describing the runtime process.

Finding the outputs
-------------------------

After the two scenarios have finished running, we will find that the scenario names now appear in the :code:`outputs` directory. Within this directory we'll find two subdirectories: :code:`logs` and :code:`summaries`.

The :code:`logs` directory contains additional subdirectories for the bases, stations, dispatcher, and vehicles. Each of the objects within the simulation record their state at each time step. These steps are collected and written to csv at the end of the simulation.

The :code:`summaries` directory contains select aggregations that with respect to various metrics. While these are not exhaustive summaries, you can generate your own by running an analysis over the detailed logs.

.. warning::

    Each time hive runs a scenario it will overwrite its corresponding output subdirectory.

Congrats! You've made it to the end of Getting Started. You should be able to start using hive 🐝
