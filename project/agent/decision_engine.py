"""Decision engine for expected and unexpected batch detection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DecisionResult:
    should_run: bool
    reason: str
    newest_transmission: str | None


class DecisionEngine:
    """Determine when the reporting workflow should execute."""

    def __init__(self, state_file: str) -> None:
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        if not self.state_file.exists():
            return {}
        with self.state_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_state(self, state: dict) -> None:
        with self.state_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

    @staticmethod
    def _extract_newest_transmission(dataframe: pd.DataFrame) -> str | None:
        if dataframe.empty or "transmissionfilename" not in dataframe.columns:
            return None
        return str(sorted(dataframe["transmissionfilename"].dropna().astype(str).unique())[-1])

    def evaluate(self, dataframe: pd.DataFrame, force_run: bool = False) -> tuple[DecisionResult, int | None]:
        """Evaluate if workflow should run based on new transmissions."""
        state = self._load_state()
        last_transmission = state.get("last_transmission")
        previous_total = state.get("last_encounter_count")
        newest = self._extract_newest_transmission(dataframe)

        if force_run:
            reason = "Scheduled batch window"
            should_run = True
        elif newest and newest != last_transmission:
            reason = "Unexpected new transmission detected"
            should_run = True
            LOGGER.info("New transmission detected: %s (prev: %s)", newest, last_transmission)
        else:
            reason = "No new transmissions"
            should_run = False

        if should_run and newest:
            state["last_transmission"] = newest
            state["last_run_utc"] = datetime.utcnow().isoformat(timespec="seconds")
            self._save_state(state)

        decision = DecisionResult(should_run=should_run, reason=reason, newest_transmission=newest)
        return decision, previous_total

    def store_encounter_total(self, encounter_total: int) -> None:
        """Persist latest encounter total for anomaly detection baseline."""
        state = self._load_state()
        state["last_encounter_count"] = encounter_total
        self._save_state(state)
