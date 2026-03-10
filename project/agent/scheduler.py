"""Schedule orchestration for OH MCD automation."""

from __future__ import annotations

import logging
import time
from typing import Callable

import schedule

LOGGER = logging.getLogger(__name__)


class SchedulerService:
    """Register expected schedule and continuous polling loop."""

    def __init__(self, weekly_runs: list[dict[str, str]], poll_interval_minutes: int) -> None:
        self.weekly_runs = weekly_runs
        self.poll_interval_minutes = poll_interval_minutes

    def register_jobs(self, scheduled_workflow: Callable[[], None], polling_workflow: Callable[[], None]) -> None:
        """Create schedule jobs for fixed windows and for unexpected batch polling."""
        for run in self.weekly_runs:
            day = run["day"].lower().strip()
            clock_time = run["time"].strip()
            schedule_day = getattr(schedule.every(), day)
            schedule_day.at(clock_time).do(scheduled_workflow)
            LOGGER.info("Registered scheduled run: %s at %s", day, clock_time)

        schedule.every(self.poll_interval_minutes).minutes.do(polling_workflow)
        LOGGER.info("Registered polling run every %s minutes", self.poll_interval_minutes)

    @staticmethod
    def run_forever() -> None:
        """Start infinite scheduler loop."""
        LOGGER.info("Scheduler started")
        while True:
            schedule.run_pending()
            time.sleep(10)
