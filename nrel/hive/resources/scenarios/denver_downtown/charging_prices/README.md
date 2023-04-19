Charging prices are specified in a csv file and can be specified two different ways:

1. Price per station with the following fields:
    - `time`: the time when the price becomes valid (allows for varible price schemes) 
    - `station_id`: which station this pricing applies to 
    - `charger_id`: which charger this pricing applies to 
    - `price_kwh`: the cost (in dollars) per kilowatthour of energy 

1. Price per region
    - `time`: the time when the price becomes valid (allows for varible price schemes) 
    - `geoid`: the geoid of the region this pricing scheme applies to 
    - `charger_id`: which charger this pricing applies to 
    - `price_kwh`: the cost (in dollars) per kilowatthour of energy 