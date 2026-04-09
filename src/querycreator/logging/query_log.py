"""Query execution log — records every tool invocation to JSONL."""
from __future__ import annotations
import json, os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class LogEntry:
    user_question: str
    generated_sql: str
    tables_used: list[str]
    execution_time_ms: float
    success: bool
    row_count: int = 0
    error: str = ""
    timestamp: str = ""
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class QueryLog:
    def __init__(self, log_path: str) -> None:
        self._path = log_path
    def write(self, entry: LogEntry) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    def read_all(self) -> list[dict[str, Any]]:
        if not os.path.exists(self._path): return []
        entries = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line: entries.append(json.loads(line))
        return entries
