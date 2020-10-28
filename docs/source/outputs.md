# Outputs 

Let's take a look at the outputs from a single run of `denver_demo.yaml`; the program defaults to writing
outputs in the same location that you run the command `hive denver_demo.yaml` with the date appended

inside the output folder you should see a set of files:

 - `denver_demo.yaml`: a cached version of the original scenario config; useful if you need a historical copy
 - `event.log`: a log of all the events that occurred in the system
 - `run.log`: a hard copy of what was output to the stdout during the simulation 
 - `state.log`: a log of the state of certain entity at _each_ simulation time step 
 - `station_capacities.csv`: a summary of the total power rate at each station (since stations can have multiple plugs)
 - `summary_stats.json`: a file with various summary level statistics for the simulation

the main files of interest are the `event.log` and the `state.log` files; let's take a deeper look at each:

### `event.log`

this file captures events that take place during the simulation;

the events are written to this file as a single json line _per_ event; 

the recommended way to read this file is to use pandas like:

```python
log_df = pd.read_json("event.log", lines=True)
```

then, you can filter on the various events you want to look at like:
```python
move_events = log_df[log_df.report_type == 'vehicle_move_event'].dropna(axis=1, how="all")
```

what kind of events can I select from? great question! here's a long boring list of each report type and 
the data associated with it:

#### `add_request_event`
triggered when a request is added into the simulation

 - `request_id`: the id of the request
 - `departure_time`: when the request was introduced into the system

#### `pickup_request_event`
triggered when a request is picked up by a vehicle 

 - `request_id`: the id of the request
 - `vehicle_id`: the id of the vehicle that picked up the request 
 - `geoid`: geoid of where the request was picked up 
 - `lat`: latitude of where the request was picked up 
 - `lon`: longitude of where the request was picked up 
 - `pickup_time`: when the request was picked up 
 - `request_time`: when the request was made 
 - `wait_time_seconds`: how long, in seconds, it took to pick up the request 
 - `price`: the price of the request (in dollars) 

#### `cancel_request_event`
triggered when a request is canceled before being picked up

 - `request_id`: the id of the request
 - `departure_time`: when the request was introduced into the system
 - `cancel_time`: when the request was canceled 

#### `vehicle_charge_event`
triggered when a vehicle is charging; note that this event is logged for each timestep a vehicle is charging rather
than once for an entire charge event.

 - `station_id`: the id of the station where the vehicle was charging 
 - `vehicle_id`: the id of the vehicle that was charging 
 - `vehicle_state`: the state of the vehicle that was charging 
 - `sim_time_start`: the start time of the charge event 
 - `sim_time_end`: the end time of the charge event 
 - `energy`: how much energy was transferred during the charge event 
 - `energy_units`: the units of the energy that was transferred 
 - `geoid`: the geoid of the station where the vehicle was charging 
 - `lat`: the latitude of the station where the vehicle was charging 
 - `lon`: the longitude of the station where the vehicle was charging 
 - `price`: the cost of the charge event (in dollars) 
 - `charger_id`: the id of the charger that was used 

#### `vehicle_move_event`
triggered when a vehicle is moving; note that this event is logged for each timestep a vehicle is moving rather
than once for an entire move event.

 - `vehicle_id`: the id of the vehicle that was moving 
 - `vehicle_state`: the state of the vehicle that was moving 
 - `sim_time_start`: the start time of the move event 
 - `sim_time_end`: the end time of the move event 
 - `energy`: how much energy was expended during the move event 
 - `energy_units`: the units of the energy that was expended 
 - `geoid`: the geoid of where the vehicle was at the _end_ of the move event 
 - `lat`: the latitude of where the vehicle was at the _end_ of the move event 
 - `lon`: the longitude of where the vehicle was at the _end_ of the move event 
 - `distance_km`: how far the vehicle traveled during the move event (in kilometers) 
 - `route_wkt`: the well known text geometry of the route the vehicle traveled during the move event 

#### `station_load_event`
for each timestep, a station emits the total energy that was transferred via all plugs

 - `station_id`: the id of the station
 - `sim_time_start`: the start time of the load event 
 - `sim_time_end`: the end time of the load event 
 - `energy`: how much energy was transferred during the load event 
 - `energy_units`: the units of the energy that was transferred 

#### `refuel_search_event`
triggered each time a charge instruction is sent to a vehicle

 - `vehicle_id`: the id of the vehicle that was instructed to charge
 - `vehicle_state`: the state of the vehicle when it was instructed to charge
 - `sim_time_start`: the sim time boundary start when the charge instruction was issued 
 - `sim_time_end`: the sim time boundary end when the charge instruction was issued 
 - `geoid`: the geoid of where the vehicle was when the instruction was issued 
 - `lat`: the latitude of where the vehicle was when the instruction was issued 
 - `lon`: the longitude of where the vehicle was when the instruction was issued 
 - `wkt`: the well known text geometry of where the vehicle was when the instruction was issued 

#### `driver_schedule_event`
triggered when a vehicle goes on/off schedule

 - `vehicle_id`: the id of the vehicle that went on/off schedule 
 - `vehicle_state`: the state of the vehicle when it went on/off schedule
 - `sim_time_start`: the sim time boundary start when the vehicle went on/off schedule 
 - `sim_time_end`: the sim time boundary end when the vehicle went on/off schedule 
 - `geoid`: the geoid of where the vehicle was when the vehicle went on/off schedule 
 - `lat`: the latitude of where the vehicle was when the vehicle went on/off schedule 
 - `lon`: the longitude of where the vehicle was when the vehicle went on/off schedule 
 - `wkt`: the well known text geometry of where the vehicle was when the vehicle went on/off schedule 
 - `schedule_event`: indicates if the vehicle when on or off schedule


#### `instruction`
triggered when an instruction is generated in the system; note, some fields may be blank if they don't pertain
to the specific instruction

 - `vehicle_id`: the id of the vehicle to which the instruction is assigned 
 - `sim_time`: when the instruction was issued
 - `instruction_type`: the type of instruction
 - `request_id`: the id of the request (only used for DispatchTrip)
 - `base_id`: the id of the base (only used for DispatchBase, ChargeBase, ReserveBase)
 - `station_id`: the id of the station (only used for DispatchStation, ChargeStation)
 - `charger_id`: the id of the charger (only used for DispatchStation, ChargeStation, ChargeBase)
 - `destination`: the geoid of the destination (only used for Repositioning)



### `state.log`
the state log captures the state of certain entities for each timestep in the simulation

this is a lot of information but can be helpful for certain scenario debugging tasks

similar to the `event.log`, the recommended way to read these files is to use pandas like:

```python
log_df = pd.read_json("state.log", lines=True)
```

then, you can filter on the various events you want to look at like:
```python
vehicle_state = log_df[log_df.report_type == 'VEHICLE_STATE'].dropna(axis=1, how="all")
```

let's look at the included report types:

#### `VEHICLE_STATE`
records the state of each vehicle at each timestep of the simulation

 - `vehicle_id`: the id of the vehicle 
 - `vehicle_state`: the state of the vehicle 
 - `sim_time`: the sim time  
 - `balance`: how much money the vehicle has (in dollars)
 - `distance_traveled_km`: the vehicles cummulative distance travelled (in kilometers)
 - `energy_<ENERGY_TYPE>`: how much energy the vehicle has (postfixed by energy type)
 - `link_link_id`: the id of the link the vehicle is on
 - `link_start`: the geoid of the starting vertex of the link the vehicle is on
 - `link_end`: the geoid of the ending vertex of the link the vehicle is on
 - `link_distance_km`: the distance of the link the vehicle is on (in kilometers)
 - `link_speed_kmph`: the distance of the link the vehicle is on (in kilometers/hour)
 

#### `STATION_STATE`
records the state of each station at each timestep of the simulation

 - `station_id`: the id of the station 
 - `sim_time`: the sim time  
 - `balance`: how much money the station has (in dollars)
 - `enqueued_vehicles`: a set of vehicle ids that are queued at the station 
 - `memebership`: the set of membership ids that the station belongs to 
 - `link_id`: the id of the link the station is on
 - `geoid`: the geoid of where the station is located 
 - `total_chargers_<CHARGER_TYPE>`: how many chargers are at the station (postfixed by charger type)
 - `available_chargers_<CHARGER_TYPE>`: how many chargers are available at the station (postfixed by charger type)
 - `charger_prices_<CHARGER_TYPE>`: the price of the charger (postfixed by charger type)


phew, that's a lot of information.. luckily, hive has a way to turn off certain logs based on your needs,
check out [global config](inputs.html#globalconfig)


