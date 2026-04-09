"""Oracle DB connection configuration via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    """Oracle DB connection parameters."""

    host: str
    port: int
    service_name: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return f"{self.host}:{self.port}/{self.service_name}"

    @classmethod
    def from_env(cls) -> DBConfig:
        """Load config from environment variables.

        Required env vars:
            QC_DB_HOST, QC_DB_PORT, QC_DB_SERVICE,
            QC_DB_USER, QC_DB_PASSWORD
        """
        host = os.environ["QC_DB_HOST"]
        port = int(os.environ.get("QC_DB_PORT", "1521"))
        service = os.environ["QC_DB_SERVICE"]
        user = os.environ["QC_DB_USER"]
        password = os.environ["QC_DB_PASSWORD"]
        return cls(
            host=host, port=port, service_name=service,
            user=user, password=password,
        )
