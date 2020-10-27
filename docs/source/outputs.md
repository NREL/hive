# Outputs 

Let's take a look at the outputs from a single run of `denver_demo.yaml`; the program defaults to writing
outputs in the same location that you run the command `hive denver_demo.yaml` with the date appended

inside the output folder you should see a set of files:

 - `denver_demo.yaml`: a cached version of the original scenario config; useful if you need a historical copy
 - `event.log`: a log of all the events that occurred in the system
 - `run.log`: a hard copy of what was output to the stdout during the simulation 
 - `state.log`: a log of the state of _each_ entity at _each_ simulation time step 
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

#### `vehicle_move_event`

#### `station_load_event`

#### `refuel_search_event`

#### `driver_schedule_event`

#### `instruction`



