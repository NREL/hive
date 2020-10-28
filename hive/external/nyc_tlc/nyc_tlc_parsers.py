from datetime import datetime
from typing import Dict, Union

import h3

from hive.model.passenger import Passenger, create_passenger_id
from hive.model.request import Request
from hive.model.roadnetwork.link import Link


def parse_yellow_tripdata_row(row: Dict[str, str],
                              id_number: int,
                              cancel_time: int,
                              sim_h3_location_resolution: int,
                              default_passengers: int = 1,
                              use_date_in_request_id: bool = False) -> Union[Exception, Request]:
    """
    takes a row (via a DictReader) from a Yellow Cab Taxi Company data source and
    converts it to a Request, unless it is missing a required field.

    it uses provided id_number (and optionally the date) to construct an id, and
    uses the time to construct a departure time (dropping the notion of "day",
    so that all requests occur on the same day). passengers default to 1.

    see https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page


    :param row: a row from a TLC Trip Record file

    :param id_number: a unique number to add to this request's name

    :param cancel_time: the duration_seconds that the request will be active, in seconds, before it cancels

    :param sim_h3_location_resolution: the h3 spatial resolution requests are stored at

    :param default_passengers: the fill value to use when passengers is missing from the row

    :param use_date_in_request_id: if True, adds the date as part of the Request's name,
    to make it easier to trace back to the source data, at the cost of a larger (unnecessary) memory footprint
    :return: a Request, or an exception if row is invalid
    """
    try:
        # time
        date_time = datetime.strptime(row['pickup_datetime'], '%Y-%m-%d %H:%M:%S')
        start_of_day = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
        time_diff = date_time - start_of_day
        departure_time = time_diff.seconds
        cancel_time = min(departure_time + cancel_time, 86399)  # 11:59:59

        # agent id
        agent_id = f"{id_number}#{date_time.date()}" if use_date_in_request_id else id_number

        # locations
        o_lat, o_lon = float(row['pickup_latitude']), float(row['pickup_longitude'])
        d_lat, d_lon = float(row['dropoff_latitude']), float(row['dropoff_longitude'])
        origin = h3.geo_to_h3(o_lat, o_lon, sim_h3_location_resolution)
        destination = h3.geo_to_h3(d_lat, d_lon, sim_h3_location_resolution)

        origin_link = Link('o', origin, origin, 0, 0)
        destination_link = Link('d', destination, destination, 0, 0)

        # passengers (
        passengers = int(row['passengers']) if 'passengers' in row else default_passengers

        request_as_passengers = [
            Passenger(
                create_passenger_id(agent_id, pass_idx),
                origin_link.start,
                destination_link.end,
                departure_time
            )
            for pass_idx in range(0, passengers)
        ]

        return Request(
            id=agent_id,
            origin_link=origin_link,
            destination_link=destination_link,
            departure_time=departure_time,
            cancel_time=cancel_time,
            passengers=tuple(request_as_passengers)
        )

    except Exception as e:
        return e
