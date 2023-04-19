# Inputs

## Scenario Config

Scenarios are run by reading a YAML file describing the parameters of the simulation. The files list all scenario-specific parameters but can fall back to defaults set [here](https://github.com/NREL/hive/blob/main/nrel/hive/resources/defaults/hive_config.yaml).

Scenario YAML files organize a list of resource files to use as input. If a file resource is listed which doesn't resolve to a local file path, HIVE will search for a default resource [here](nrel/hive/resources). By default, HIVE expects file resources stored in a directory matching their resource type.

```{note}
some inputs in hive are optional and will fall back to defaults if not specified; here we will denote whether the
input is (required) or (optional); take a look at `nrel.hive.resources.defaults.hive_config.yaml` for the optional fallbacks
```

```{literalinclude} ../../nrel/hive/resources/scenarios/denver_downtown/denver_demo.yaml
:language: yaml
```

## Scenario Files

In addition to the scenario config yaml file, each scenario has several other files used to describe the scenario.

### Bases

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/bases/README.md
```

### Chargers

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/chargers/README.md
```

### Charging Prices

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/charging_prices/README.md
```

### Fleets

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/fleets/README.md
```

### Mechatronics

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/mechatronics/README.md
```

### Requests

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/requests/README.md
```

### Road Network

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/road_network/README.md
```

### Service Prices

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/service_prices/README.md
```

### Stations

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/stations/README.md
```

### Stations

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/stations/README.md
```

### Vehicles

```{include} ../../nrel/hive/resources/scenarios/denver_downtown/vehicles/README.md
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
