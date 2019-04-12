Drop one (or more) MaaS request .csv files here. If simulating multiple days
of operation, ensure that these days are sequential (it is not neccesary for
the files to be in order). Also ensure that data is only from the area of
interest - Hive is a single-fleet simulation platform and can't handle
simultaneous simulations over multiple operating areas. Files must contain the 
following fields (with the __exact__ headers and identical structures):  
* __pickup_time__, _str_, 'YYYY-MM-DD hh:mm:ss'  
* __dropoff_time__, _str_, 'YYYY-MM-DD hh:mm:ss'  
* __distance_miles__, _float_, distance travelled in miles  
* __pickup_lat__, _float_, latitude of pickup location  
* __pickup_lon__, _float_, longitude of pickup location  
* __dropoff_lat__, _float_, latitude of dropoff location  
* __dropoff_lon__, _float_, longitude of dropoff location  
* __passengers__, _int_, number of passengers (OPTIONAL)