# Inputs

## Scenario Config

The main simulation input is a yaml file that contains a bunch of parameters for running a scenario.
On example of a scenario file can be found at `nrel.hive.resources.scenarios.denver_demo.yaml`:

```{note}
some inputs in hive are optional and will fall back to defaults if not specified; here we will denote whether the
input is (required) or (optional); take a look at `nrel.hive.resources.defaults.hive_config.yaml` for the optional fallbacks
```

```{literalinclude} ../../nrel/hive/resources/scenarios/denver_downtown/denver_demo.yaml
:language: yaml
```

## Global Config

All of the inputs described above are scenario specific.
Hive also has global configuration values that will apply to all scenarios.
By default, if no config file is found the simulation will use the defaults specified at `nrel.hive.resources.default..hive.yaml`:

```{literalinclude} ../../nrel/hive/resources/defaults/.hive.yaml
:language: yaml
```

To override any of the default global config values, you can create your own `.hive.yaml` file.

When a hive scenario is loaded, hive will search for a `.hive.yaml` file to load.
First, hive looks in the same location that you called `hive <scenario_file.yaml>`.
Then, if it can't find it there it will step up to the parent and keep stepping up all the way to the root of the file system.
If there are no files in any of these locations, it will look in the users home directory (i.e. `~/`).
Finally, if no `.hive.yaml` files exist in any of these locations, the defaults are loaded.

As an example, we can write a new `.hive.yaml` file into our home directory (`touch ~/.hive.yaml`) that looks like this:

```yaml
output_base_directory: "~/hive_results"
```

Now, whenever we run a hive simulation, our results will get written to `~/hive_results`.

But, what if we want to run a scenario and only log certain things?
We can create a new `.hive.yaml` file in the scenario directory (`touch <path/to/scenario-dir/.hive.yaml`) that looks like:

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

This would turn off all logging except for vehicle charge events.
