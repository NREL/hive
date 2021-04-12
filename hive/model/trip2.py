from __future__ import annotations

from typing import NamedTuple, Tuple

from hive.model.passenger import Passenger
from hive.model.request import Request
from hive.model.sim_time import SimTime


Trip2 = Request

# class Trip2(NamedTuple):
#     """
#     models an active trip.
#
#     :param request: The request which ordered the trip
#     :type request: :py:obj:`Request`
#
#     :param departure_time: The time at which the vehicle picked up the request
#     :type departure_time: :py:obj:`SimTime`
#
#     :param route: The path in the road network to the request's destination
#     :type route: :py:obj:`Route`
#
#     :param passengers: The passenger entities taking the trip
#     :type route: :py:obj:`Tuple[Passenger]`
#     """
#     request: Request
#     departure_time: SimTime
#     passengers: Tuple[Passenger, ...]

