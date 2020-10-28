from __future__ import annotations

from typing import TYPE_CHECKING, List

from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from hive.reporting.reporter import Report
    from hive.runner.runner_payload import RunnerPayload


class Handler(ABC):
    """
    A reporting.Handler handles simulation reports in varying ways.
    """

    @abstractmethod
    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        called at each log step.


        :param reports:

        :param runner_payload:
        :return:
        """

    @abstractmethod
    def close(self, runner_payload: RunnerPayload):
        """
        wrap up anything here. called at the end of the simulation

        :return:
        """
