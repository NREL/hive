Vehicles are specified as one vehicle per csv line with the following fields:

- `vehicle_id`: a unique id for the vehicle
- `lat`: the latitude of the vehicle starting location
- `lon`: the longitude of the vehicle starting location
- `mechatronics_id`: the identifier of the mechatronics that this vehicle is using
- `initial_soc`: the initial state of charge for the vehicle
- `schedule_id`: (optional) the schedule this vehicle should follow (human driver)
- `home_base_id`: (optional) the base id for the home base location (human driver)
