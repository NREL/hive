# hive
Hive is a mobility services simulation platform.

### Input Descriptions
#### FLEET - Operating characteristics
- MAX_FLEET_SIZE: Max number of vehicles in fleet
- MAX_DISPATCH_MILES: Max miles allowed for dispatch

#### VEHICLE - Vehicle characteristics
- BATTERY_CAPACITY: kWh
- PASSENGERS: Max passenger capacity for fleet vehicles
- EFFICIENCY: Operating efficiency - Wh/mile
- CHARGE_ACCEPTANCE: Max charge acceptance - kW
- PCT_OF_FLEET: Fraction of fleet w/ vehicle characteristics

#### REFUEL - Operating characteristics
- CHARGING_SCENARIO: 'Constrained' = sited DC + L2 stations; 'Unconstrained' = Ubiquitous
- MIN_SOC_REMAINING: Min SOC that can remain after a request; Necessary for locating charger
- MINUTES_BEFORE_CHARGE: Minutes that a vehicle will remain idle before it begins to charge
- UBIQUITOUS_CHARGER_POWER: kW - Only used if CHARGING_SCENARIO = 'Unconstrained'
- STATION_LOWER_SOC_CHARGE_THRESH: Vehicle will travel to station to charge when SOC is detected below thresh
- STATION_UPPER_SOC_CHARGE_THRESH: Upper threshold for SOC when charging @ station; Vehicle will stop charging when thresh is met
