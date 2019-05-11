## Requests  
CSV files that are n-rows by (7 or 8)-columns go here, where n is the number of requests for a simulation. The 7 columns required (plus one optional column) in order, include:  
* __pickup_time__ - Timestamp of pickup in format: '%Y-%m-%d %H:%M:%S'  
* __dropoff_time__ - Timestamp of dropoff in format: '%Y-%m-%d %H:%M:%S'
* __distance_miles__ - Trip VMT  
* __pickup_lat__ - Latitude of pickup location  
* __pickup_lon__ - Longitude of pickup location  
* __dropoff_lat__ - Latitude of dropoff location  
* __dropoff_lon__ - Longitude of dropoff location  
* __passengers__ - Number of passengers (Optional)  
  
EX:  
| pickup_time | dropoff_time | distance_miles | pickup_lat | pickup_lon | dropoff_lat | dropoff_lon | passengers |
|:-----------:|:------------:|:--------------:|:----------:|:----------:|:-----------:|:-----------:|:---------:|
| 2017-02-01 23:22:01 | 2017-02-01 23:28:21 | 1.95 | 30.2640 | -97.7453 | 30.2542 | -97.7160 | 2 |
| 2017-02-01 18:01:40 | 2017-02-01 18:44:26 | 28.76 | 30.2031 | -97.6672 | 30.3470 | -98.0169 | 1 |
| 2017-02-01 18:02:07 | 2017-02-01 18:12:51 | 1.85 | 30.2660 | -97.7434 | 30.2791 | -97.7572 | 1 |