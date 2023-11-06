from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import functools as ft

import h3
import immutables
from returns.result import ResultE, Failure, Success
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.roadnetwork.link import Link
from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal
from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
from nrel.hive.model.roadnetwork.route import Route
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util.typealiases import GeoId, H3Resolution, LinkId, MechatronicsId
from nrel.hive.util.units import Kilometers, Ratio
from nrel.routee.compass.compass_app import CompassApp


# for each state type, the expected state vector index and unit type
DEFAULT_STATE_REPRESENTATION: List[Tuple[str, int, str]] = [
    ("distance", 0, "meters"),
    ("time", 1, "seconds"),
    ("energy", 2, "kwh"),
]


@dataclass(frozen=True)
class RouteeCompassRoadNetwork(RoadNetwork):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """

    compass_app: CompassApp
    mechatronics_mapping: immutables.Map[MechatronicsId, str]
    state_representation: List[str]
    energy_cost_coefficient: Ratio
    sim_h3_resolution: H3Resolution

    @classmethod
    def build(
        cls,
        config_file: Path,
        mechatronics_to_energy_model_mapping: Dict,
        state_representation=DEFAULT_STATE_REPRESENTATION,
        energy_cost_coefficient: Ratio = 1.0,
        sim_h3_resolution: H3Resolution = 15,
    ) -> RouteeCompassRoadNetwork:
        """builds a RouteE Compass Road Network instance from some configuration file.

        :param config_file: RouteE Compass configuration file to read from
        :type config_file: Path
        :param mechatronics_to_energy_model_mapping: maps engine names from HIVE to RouteE
        :type mechatronics_to_energy_model_mapping: mapping (Dict-like)
        :param state_representation: values stored in the state vector of a search result
        :type state_representation: Dict[str, int]
        :param energy_cost_coefficient: energy vs time preference (default 100% energy aka 1.0)
        :type energy_cost_coefficient: Ratio
        :param sim_h3_resolution: h3 resolution to run network on, by default 15
        :type sim_h3_resolution: int
        :return: a RoadNetwork running on Compass
        :rtype: RouteeCompassRoadNetwork
        """
        app = CompassApp.from_config_file(config_file)
        mapping = immutables.Map(mechatronics_to_energy_model_mapping)
        return cls(app, mapping, state_representation, energy_cost_coefficient, sim_h3_resolution)

    def set_energy_cost_coefficient(self, value: Ratio) -> RouteeCompassRoadNetwork:
        return replace(self, energy_cost_coefficient=value)

    def route(self, origin: EntityPosition, destination: EntityPosition) -> Route:
        """
        Returns a route between two road network property links


        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: A route.
        """
        hive_route = get_hive_route(
            origin.geoid,
            destination.geoid,
            self.compass_app,
            self.state_representation,
            self.sim_h3_resolution,
        )
        return hive_route.unwrap()

    def distance_by_geoid_km(self, origin: GeoId, destination: GeoId) -> Kilometers:
        """
        Returns the road network distance between two geoids

        :param origin: Link of the origin
        :param destination: Link of the destination
        :return: the distance in kilometers.
        """
        hive_route = get_hive_route(
            origin, destination, self.compass_app, self.state_representation, self.sim_h3_resolution
        )
        distance_km = ft.reduce(lambda acc, lt: acc + lt.distance_km, hive_route.unwrap(), 0.0)
        return distance_km

    def link_from_link_id(self, link_id: LinkId) -> Optional[Link]:
        """
        returns the Link with the corresponding LinkId
        :param link_id: the LinkId to look up
        :return: the Link with matching LinkId, or None if not valid/found
        """
        pass

    def link_from_geoid(self, geoid: GeoId) -> Optional[Link]:
        """
        finds the nearest link to a given GeoId

        :param geoid: a physical location
        :return: The nearest road network link to the provided GeoId
        """
        pass

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance


        :param geoid: an h3 geoid
        :return: True/False
        """
        pass

    def update(self, sim_time: SimTime) -> RoadNetwork:
        """
        requests an update to the road network state to refect the provided simulation time

        :param sim_time:
        :return:
        """
        pass


def get_hive_route(
    src: GeoId,
    dst: GeoId,
    app: CompassApp,
    state_repr: List[Tuple[str, int, str]],
    h3_resolution: H3Resolution,
) -> ResultE[Route]:
    """convenience method for creating a query, running a RouteE Compass search,
    and converting the result to a HIVE Route.

    :param src: source location
    :type src: GeoId
    :param dst: destination location
    :type dst: GeoId
    :param app: instance of a RouteE Compass App
    :type app: CompassApp
    :param state_repr: information about state representation
    :type state_repr: List[Tuple[str, int, str]]
    :param h3_resolution: h3 resolution of simulation
    :type h3_resolution: H3Resolution
    :return: _description_
    :rtype: ResultE[Route]
    """
    q = query_from_origin_destination(src, dst)
    result = app.run(q)
    if result.get("error") is not None:
        return Failure(Exception(result["error"]))
    routee_route = result.get("route")
    if routee_route is None:
        return Failure(Exception(f"no 'route' attribute on Compass result object"))
    hive_route = unpack_route(routee_route, state_repr, h3_resolution)
    return Success(hive_route)


def query_from_origin_destination(src: GeoId, dst: GeoId) -> Dict:
    """builds a RouteE Compass query from an h3 od pair

    :param src: origin
    :type src: GeoId
    :param dst: destination
    :type dst: GeoId
    :return: a RouteE Compass query
    :rtype: Dict
    """
    o_lat, o_lon = h3.h3_to_geo(src)
    d_lat, d_lon = h3.h3_to_geo(dst)
    query = {"origin_x": o_lon, "origin_y": o_lat, "destination_x": d_lon, "destination_y": d_lat}
    return query


def unpack_route(
    routee_route: List,
    state_representation: List[Tuple[str, int, str]],
    h3_resolution: H3Resolution,
) -> ResultE[Route]:
    """converts back from a RouteE Compass route into a HIVE route.

    :param routee_route: _description_
    :type routee_route: List
    :param state_representation: _description_
    :type state_representation: List[Tuple[str, int, str]]
    :param h3_resolution: _description_
    :type h3_resolution: H3Resolution
    :return: either a HIVE route or an error while building it
    :rtype: ResultE[Route]
    """
    route = []
    acc_dist = 0
    acc_time = 0
    acc_enrg = 0
    for row in routee_route["features"]:
        props = row["properties"]
        edge_id = props.get("edge_id")
        values = {"edge_id": edge_id}
        units = {n: u for n, _, u in state_representation}
        state = props.get("result_state", [])

        # extract/flatten the state values
        for state_name, state_idx, _ in state_representation:
            if len(state) < state_idx:
                return Failure(
                    Exception(
                        f"result_state missing entry for {state_name} "
                        f"at index {state_idx} for edge {edge_id}"
                    )
                )
            values[state_name] = state[state_idx]
        if values.get("distance") is None or values.get("time") is None:
            return Failure(
                Exception(
                    f"unable to compute speed with missing time or distance from "
                    f"Compass row {row}"
                )
            )

        # convert units and calculate marginal state values from accumulated
        # extension point to support other units here
        if units["distance"] == "meters":
            distance_km_raw = values["distance"] / 1000.0
            distance_km = distance_km_raw - acc_dist
            acc_dist = distance_km_raw
        else:
            return Failure(ArithmeticError(f"unsupported distance unit {units['distance']}"))
        if units["time"] == "seconds":
            time_hrs_raw = values["seconds"] / 3600.0
            time_hrs = time_hrs_raw - acc_time
            acc_time = time_hrs_raw
        else:
            return Failure(ArithmeticError(f"unsupported time unit {units['time']}"))
        if units["energy"] == "kwh":
            energy_kwh_raw = values["energy"]
            energy_kwh = energy_kwh_raw - acc_enrg
            acc_enrg = energy_kwh_raw
        else:
            return Failure(ArithmeticError(f"unsupported energy unit {units['energy']}"))
        speed_kmph = distance_km / time_hrs

        # grab the link start and end location
        if len(row["geometry"]["coordinates"]) < 2:
            return Failure(TypeError(f"linestring must have at least 2 coords"))
        src_point = row["geometry"]["coordinates"][0]
        dst_point = row["geometry"]["coordinates"][-1]
        src_geoid = h3.geo_to_h3(src_point[1], src_point[0], h3_resolution)
        dst_geoid = h3.geo_to_h3(dst_point[1], dst_point[0], h3_resolution)

        lt = LinkTraversal(
            link_id=str(edge_id),
            start=src_geoid,
            end=dst_geoid,
            distance_km=distance_km,
            speed_kmph=speed_kmph,
        )
        route.append(lt)

    return Success(route)
