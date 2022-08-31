from __future__ import annotations

from typing import NamedTuple

from returns.result import ResultE, Success, Failure

from hive.model.energy.charger.charger import Charger
from hive.util.typealiases import ChargerId
from hive.util.units import Currency, KwH
from hive.util.error_or_result import ErrorOr
from hive.runner.environment import Environment
from hive.util.exception import SimulationStateError

class ChargerState(NamedTuple):
    id: ChargerId
    charger: Charger
    total_chargers: int
    available_chargers: int
    price_per_kwh: Currency
    enqueued_vehicles: int

    @classmethod
    def build(cls,charger: Charger, count: int) -> ChargerState:
        """
        builds a ChargerState from a charger and some total count
        of this charger type at a station

        :param charger: an instance of a Charger to track the state of
        :param count: the count of this Charger at some station
        :return: initial ChargerState
        """
        return ChargerState(
            id=charger.id,
            charger=charger,
            total_chargers=count,
            available_chargers=count,
            price_per_kwh=0.0,
            enqueued_vehicles=0
        )

    def add_chargers(self, charger_count: int) -> ChargerState:
        """adds chargers to this ChargerState, updating the 
        total and available charger counts

        :param charger_count: count to add
        :return: updated ChargerState
        """
        return self._replace(
            total_chargers=self.total_chargers + charger_count,
            available_chargers=self.available_chargers + charger_count
        )

    def has_available_charger(self) -> bool:
        """
        whether there are chargers of this type available
        :return: true if there are available chargers
        """
        return self.available_chargers > 0

    def increment_available_chargers(self) -> ErrorOr[ChargerState]:
        """
        increments the number of chargers of this type that are available
        :return: updated charger state or an error
        """
        if self.available_chargers >= self.total_chargers:
            msg = (
                "increment called on charger where the available charger count "
                f"{self.available_chargers} would exceed total count {self.total_chargers}"
            )
            return ValueError(msg), None
        else:
            updated = self._replace(
                available_chargers=self.available_chargers + 1
            )
            return None, updated

    def decrement_available_chargers(self) -> ErrorOr[ChargerState]:
        """
        decrements the number of chargers of this type that are available
        :return: updated charger state or an error
        """
        if self.available_chargers == 0:
            msg = (
                "decrement called on charger where the available charger count "
                "would drop below zero"
            )
            return ValueError(msg), None
        else:
            updated = self._replace(
                available_chargers=self.available_chargers - 1
            )
            return None, updated

    def increment_enqueued_vehicles(self) -> ChargerState:
        """
        increments the number of vehicles enqueued to charge at this
        station with this charger type
        :return: updated charger state
        """
        return self._replace(
            enqueued_vehicles=self.enqueued_vehicles + 1
        )   

    def decrement_enqueued_vehicles(self) -> ErrorOr[ChargerState]:
        """
        decrements the number of vehicles enqueued to charge at this
        station with this charger type
        :return: updated charger state or an error
        """
        if self.enqueued_vehicles == 0:
            msg = (
                "decrement enqueued vehicles called on charger state "
                "where enqueued vehicles would become negative"
            )
            return ValueError(msg), None
        else:
            updated = self._replace(
                enqueued_vehicles=self.enqueued_vehicles - 1
            )
            return None, updated

    def set_charge_rate(self, value: KwH) -> ResultE[ChargerState]:
        """
        sets the charge rate to some provided KwH
        :param value: the value to set
        :return: the updated charger state or an error if the value
        does not fall in the range [0, factory_charge_rate]
        """
        if value < 0.0:
            msg = f"attempting to set charge rate with negative KwH value {value}"
            return Failure(ValueError(msg))
        elif self.charger.rate < value:
            msg = (
                f"attempting to set charge rate with KwH value {value} exceeding "
                f"the factory charge rate {self.charger.rate}"
            )
            return Failure(ValueError(msg))
        else:
            updated = self._replace(
                charger=self.charger._replace(
                    rate=value
                )
            )
            return Success(updated)

    def scale_charge_rate(self, factor: float) -> ResultE[ChargerState]:
        """
        scales the charge rate by a factor of the Charger's prototype rate.

        :param factor: the factor, a percentage value in [0, 1]
        :return: updated charger state or an error
        """
        if not 0.0 <= factor <= 1.0:
            msg = f"charge rate factor must be in range [0, 1], but found {factor}"
            return Failure(SimulationStateError(msg)) 
        else:
            updated = self._replace(
                charger=self.charger._replace(
                    rate=self.charger.rate * factor
                )
            )
            return Success(updated) 
    
    def reset_charge_rate(self) -> ChargerState:
        """
        resets the charge rate to the factory charge rate
        :return: updated charger state
        """
        return self._replace(
            current_charge_rate=self.charger.rate
        )
