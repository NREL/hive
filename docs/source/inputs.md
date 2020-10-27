# Inputs

In order to introduce some of the inputs, we'll use our default denver demo scenario 
(`hive.resources.scenarios.denver_demo.yaml`). To start, let's take a look at the actual scenario configuration
which is defined in the `denver_demo.yaml` file:

```eval_rst
.. note::
   some inputs in hive are optional and will fall back to defaults if not specified; here we will denote whether the
   input is required or optional; take a look at `hive.resources.defaults.hive_config.yaml` for the optional fallbacks
```

```yaml
sim:
  sim_name: denver_demo
  timestep_duration_seconds: 60
  request_cancel_time_seconds: 600
  start_time: "1970-01-01T00:00:00"
  end_time: "1970-01-02T00:00:00"
network:
  network_type: osm_network
input:
  vehicles_file: denver_demo_vehicles.csv
  requests_file: denver_demo_requests.csv
  bases_file: denver_demo_bases.csv
  stations_file: denver_demo_stations.csv
  road_network_file: downtown_denver.xml
  geofence_file: downtown_denver.geojson
  rate_structure_file: rate_structure.csv
  charging_price_file: denver_charging_prices_by_geoid.csv
  demand_forecast_file: denver_demand.csv
dispatcher:
  valid_dispatch_states:
    - Idle
    - Repositioning
```

Okay, let's break it out by entry:

#### `sim`

 - `sim_name`: (required) any name you want to give your simulation (go ahead, be creative)
 - `timestep_duration_seconds`: (optional) how many seconds does a single hive time step represent; must be an integer; 
 generally, 60 seconds is the recommended value based on internal testing and validation.
 - `request_cancel_time_seconds`: (optional) represents how long a request will be active in the simulation; after this timeout
 the request is destroyed.
 - `start_time`: (required) the start time of the simulation.
 - `end_time`: (required) the end time of the simulation.
 

```eval_rst
.. note::
   hive will accept time as an epoch integer or an ISO timestring; time in hive is always represented in UTC 
   (i.e. no timezones) and any timezone information that is included will get ignored;  
```

#### `network`

 - `network_type`: (optional) the type of road network the simulation will use; see [api-docs](api-docs/hive.model.roadnetwork)
 for the available road networks.

#### `input`

 - `vehicles_file`: (required) the vehicles to use for this scenario 
 - `requests_file`: (required) the requests to use for this scenario
 - `bases_file`: (required) the bases to use for this scenario
 - `stations_file`: (required) the stations to use for this scenario
 - `road_network_file`: (optional) the file for the road network 
 - `geofence_file`: (optional) a file outlining an optional geofence 
 - `rate_structure_file`: (optional) a file with service prices
 - `charging_price_file`: (optional) a file with fuel prices 
 - `demand_forecast_file`: (optional) a demand forecast to be used for repositioning 
 
 #### `dispatcher`
 
  - `valid_dispatch_states`: (optional) the vehicle states that the dispatcher will consider when trying to match requests to vehicles





 