Mechatronics refers to the vehicle level parameters and is specified with a yaml file.

Each key in this file refers to a mechatronics id and each sub key is a specific parameter of that mechatronics type.

For example, let’s say we have this mechatronics file:


```yaml
leaf_50:
  mechatronics_type: bev
  powercurve_file: 'normalized.yaml'
  powertrain_file: 'normalized-electric.yaml'
  battery_capacity_kwh: 50
  nominal_max_charge_kw: 50
  charge_taper_cutoff_kw: 10
  nominal_watt_hour_per_mile: 225
  idle_kwh_per_hour: 0.8
  
toyota_corolla:
  mechatronics_type: ice
  tank_capacity_gallons: 10
  idle_gallons_per_hour: 0.2
  powertrain_file: 'normalized-gasoline.yaml'
  nominal_miles_per_gallon: 30
```

There are currently two supported mechatronics types: `bev` (battery electric vehicle) and `ice` (internal combustion engine). In this case, the `leaf_50` is a `bev` and requires the following sub keys:

- `mechatronics_type`: the mechatronics type for this vehicle is `bev`
- `powercurve_file`: the powercurve file that contains the power curve for this vehicle
- `powertrain_file`: the powertrain file that contains the energy consumption model for this vehicle
- `battery_capacity_kwh`: the battery capacity in kilowatt-hours
- `nominal_max_charge_kw`: the nominal max charge in kilowatts
- `charge_taper_cutoff_kw`: the charge taper cuttoff in kilowatts
- `nominal_watt_hour_per_mile`: the nominal watt-hours per mile 
- `idle_kwh_per_hour`: the amount of kilowatt-hours used per hour while idling

The `toyota_corolla` in this case is an `ice` and requires the following sub keys:

- `mechatronics_type`: the mechatronics type for this vehicle is `ice`
- `tank_capacity_gallons`: the vehicle's tank capacity in gallons
- `idle_gallons_per_hour`: the amount of gallons used per hour while the vehicle is idling 
- `powertrain_file`: the powertrain file that contains the energy consumption model for this vehicle
- `nominal_miles_per_gallon`: the nominal miles per gallon

A scenario can have multiple mechatronics types and each vehicle in the simulation can be assigned a mechatronics type in the vehicles file.
