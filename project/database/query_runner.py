"""Database query execution utilities for OH MCD automation."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import pyodbc

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration required to connect and query SQL Server."""

    driver: str
    server: str
    database: str
    trusted_connection: bool
    query: str


class QueryRunner:
    """Run SQL queries and return Pandas DataFrames."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config

    def _build_connection_string(self) -> str:
        trusted = "yes" if self.config.trusted_connection else "no"
        return (
            f"DRIVER={{{self.config.driver}}};"
            f"SERVER={self.config.server};"
            f"DATABASE={self.config.database};"
            f"Trusted_Connection={trusted};"
        )

    def run_submission_query(self) -> pd.DataFrame:
        """Execute configured submission query and return DataFrame results."""
        connection_string = self._build_connection_string()
        LOGGER.info("Running submission query against %s/%s", self.config.server, self.config.database)

        try:
            with pyodbc.connect(connection_string, timeout=30) as connection:
                dataframe = pd.read_sql(self.config.query, connection)
                LOGGER.info("Retrieved %s rows from SQL Server", len(dataframe))
                return dataframe
        except Exception:
            LOGGER.exception("Failed to execute submission query")
            raise
