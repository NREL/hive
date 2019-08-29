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
