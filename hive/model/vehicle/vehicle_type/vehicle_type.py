from typing import NamedTuple

from hive.util.typealiases import PowertrainId, PowercurveId
from hive.util.units import KwH, Kw, Currency


class VehicleType(NamedTuple):
    powertrain_id: PowertrainId
    powercurve_id: PowercurveId
    capacity_kwh: KwH
    max_charge_acceptance: Kw
    operating_cost_km: Currency
