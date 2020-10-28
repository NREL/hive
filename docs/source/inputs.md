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



## GlobalConfig 

all of the inputs described above are scenario specific; hive also has global configuration values that will apply
to all scenarios. by default this file is loaded from [hive.resources.defaults..hive.yaml](https://github.nrel.gov/MBAP/hive/blob/master/hive/resources/defaults/.hive.yaml)

to override any of the default global config values, you can create your own `.hive.yaml` file.

when a hive scenario is loaded, hive will search for a `.hive.yaml` file to load; first, hive looks in the same
location that you called `hive <scenario_file.yaml>`; then, if it can't find it there it will step up to the parent
and keep stepping up all the way to the root of the file system; if there are no files in any of these locations,
it will look in the users home directory (i.e. `~/`); finally, if no `.hive.yaml` files exist in any of these locations,
the defaults are loaded.

the power of this method is that you can create your own set of global config values that you use most of the time;
but, if you have one scenario or set of scenarios that need a special config, just place a `.hive.yaml` file in
the scenario directory to override any other config.

as an example, we can write a new `.hive.yaml` file into our home directory (`touch ~/.hive.yaml`) that looks like this

```yaml
output_base_directory: "~/hive_results"
```

now, whenever we run a hive simulation, our results will get written to `~/hive_results`.

but, what if we want to run a scenario and only log certain things? we can create a new `.hive.yaml` file in
the scenario directory (`touch <path/to/scenario-dir/.hive.yaml`) that looks like:

```yaml
log_run: False 
log_states: False 
log_events: True 
log_stats: False 
log_station_capacities: False 
log_level: INFO
log_sim_config:
- 'vehicle_charge_event'
```

this would effectively turn off all logging except for vehicle charge events.

let's take a look at what the values are:

 - `output_base_directory`: where hive will write outputs
 - `log_run`: whether or not to log the run.log 
 - `log_states`: whether or not to log the state.log 
 - `log_events`: whether or not to log the event.log 
 - `log_stats`: whether or not to track stats during the simulation 
 - `log_level`: the python log level to use (i.e. INFO, DEBUG, ERROR, etc) 
 - `log_sim_config`: which report types to include in the logs see [outputs](outputs) 
 - `log_station_capacities`: whether or not to log station capacities
 - `local_parallelism`: not currently used (set aside for when we implement distributed computing)
 - `local_parallelism_timeout_sec`: not currently used (set aside for when we implement distributed computing)
 - `lazy_file_reading`: if true, hive will read files lazily (i.e. not read everything into memory) 
 - `wkt_x_y_ordering`: if true, hive will write wkt points as x,y (i.e. lon, lat) rather than y,x (lat, lon) 
 
