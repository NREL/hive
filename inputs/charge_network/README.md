## Charge Networks 
CSV files that are n-rows by 7-columns go here, where n is the number of stations and depots considered for a simulation. The 7 columns required to define a refueling network in HIVE include (in order):  
* __station_id__ - string identifier for a station/depot  
* __station_type__ - 'station' or 'depot'. Stations are used by active fleet vehicles who have dropped below a minimum state of charge threshold; Depots are used by inactive vehicles when demand is being sufficiently served by a subset of the fleet  
* __longitude__ - Longitude of station/depot location  
* __latitude__ - Latitude of station/depot locatiion  
* __plugs__ - Number of vehicles that are able to charge concurrently  
* __plug_type__ - 'AC' or 'DC'. With AC charging, there are loss factors present in the AC-DC conversion, thus the vehicle does not receive the maximum power reported but a fraction of it. With high voltage DC charging, as the pack is replentished, the power level tails off to minimize wear on the battery cells  
* __plug_power_kw__ - Maximum plug power, in kW (before losses)  
  
EX:  
| station_id | station_type | longitude | latitude | plugs | plug_type | plug_power_kw |
|:----------:|:------------:| :--------:| :-------:| :----:| :--------:| :------------:|
| d1 | depot | -97.75387 | 30.28957 | 40 | AC | 7.2 |
| s1 | station | -97.74171 | 30.44378 | 10 | DC | 150 |
| s2 | station | -97.77577 | 30.44356 | 4 | DC | 50 |