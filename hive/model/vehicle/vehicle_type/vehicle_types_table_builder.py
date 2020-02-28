from __future__ import annotations

import functools as ft
from csv import DictReader
from typing import NamedTuple, Dict, Tuple, Optional, Union, Iterator

import immutables

from hive.util.typealiases import VehicleTypeId
from hive.model.vehicle import VehicleType


class VehicleTypesTableBuilder(NamedTuple):
    errors: Tuple[Exception, ...] = ()
    result: immutables.Map[VehicleTypeId, VehicleType] = immutables.Map()

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def add_errors(self, errors: Tuple[Exception, ...]) -> VehicleTypesTableBuilder:
        return self._replace(errors=self.errors + errors)

    def add_row(self, vehicle_type_id: VehicleTypeId, vehicle_type: VehicleType) -> VehicleTypesTableBuilder:
        return self._replace(
            result=self.result.update({vehicle_type_id: vehicle_type})
        )

    @classmethod
    def build(cls, source: Union[str, Iterator[Dict[str, str]]]) -> VehicleTypesTableBuilder:
        """
        builds the vehicle types lookup table
        :param source: the source of the vehicle types
        :return: a tabular lookup of vehicle type data, along with errors:
                 IOError if the file is invalid
                 KeyError if any required columns are missing
                 RuntimeError if non-unique ids were found
        """

        def parse_row(acc: VehicleTypesTableBuilder, row: Dict[str, str]) -> VehicleTypesTableBuilder:
            # grab string values from row
            v_err, vehicle_type_id = safe_get('vehicle_type_id', row)
            pt_err, powertrain_id = safe_get('powertrain_id', row)
            pc_err, powercurve_id = safe_get('powercurve_id', row)
            cap_err1, cap_str = safe_get('capacity_kwh', row)
            iel_err1, iel_str = safe_get('ideal_energy_limit_kwh', row)
            mca_err1, mca_str = safe_get('max_charge_acceptance_kw', row)
            oc_err1, oc_str = safe_get('operating_cost', row)

            # convert strings to floating point values
            cap_err2, cap_val = to_float(cap_str, "capacity_kwh")
            iel_err2, iel_val = to_float(iel_str, "ideal_energy_limit_kwh")
            mca_err2, mca_val = to_float(mca_str, "max_charge_acceptance_kw")
            oc_err2, oc_val = to_float(oc_str, "operating_cost")

            errors = ft.reduce(
                lambda t, err: t + err if err else t,
                (v_err, pt_err, pc_err, cap_err1, iel_err1, mca_err1, oc_err1, cap_err2, iel_err2, mca_err2, oc_err2),
                ()
            )

            if len(errors) > 0:
                return acc.add_errors(errors)
            else:
                vehicle_type = VehicleType(
                    powertrain_id=powertrain_id,
                    powercurve_id=powercurve_id,
                    capacity_kwh=cap_val,
                    ideal_energy_limit_kwh=iel_val,
                    max_charge_acceptance=mca_val,
                    operating_cost=oc_val
                )
                return acc.add_row(vehicle_type_id=vehicle_type_id, vehicle_type=vehicle_type)

        def safe_get(col: str, row: Dict[str, str]) -> Tuple[Optional[Exception], Optional[str]]:
            try:
                return None, row[col]
            except KeyError as err:
                return err, None

        def to_float(value: Optional[str], column_name: str) -> Tuple[Optional[Exception], Optional[float]]:
            if not value:
                return None, None  # error already reported above
            else:
                try:
                    return None, float(value)
                except ValueError:
                    detailed = ValueError(f"could not parse {column_name} value {value} as a number")
                    return detailed, None

        if isinstance(source, str):
            with open(source, 'r') as f:
                reader = DictReader(f)
                return ft.reduce(parse_row, reader, VehicleTypesTableBuilder())
        elif isinstance(source, Dict):
            return ft.reduce(parse_row, source, VehicleTypesTableBuilder())
        else:
            return VehicleTypesTableBuilder(
                errors=(IOError(f"building vehicle types table but source has unexpected type {type(source)}, value {source} where it should be a string or an iterator"), )
            )
