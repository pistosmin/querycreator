"""Query log analyzer — finds slow patterns and usage stats."""
from __future__ import annotations
from collections import Counter
from typing import Any

class QueryAnalyzer:
    def __init__(self, threshold_ms: float = 1000) -> None:
        self._threshold_ms = threshold_ms
    def find_slow_patterns(self, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pattern_times: dict[str, list[float]] = {}
        for log in logs:
            tables = sorted(log.get("tables_used", []))
            key = "+".join(tables) if tables else "UNKNOWN"
            pattern_times.setdefault(key, []).append(log.get("execution_time_ms", 0))
        slow = []
        for pattern, times in pattern_times.items():
            avg = sum(times) / len(times)
            if avg >= self._threshold_ms:
                slow.append({"tables": pattern, "avg_time_ms": round(avg, 1), "max_time_ms": round(max(times), 1), "count": len(times)})
        return sorted(slow, key=lambda x: x["avg_time_ms"], reverse=True)
    def failure_report(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(logs)
        failed = sum(1 for l in logs if not l.get("success", True))
        return {"total": total, "failed": failed, "success_rate": round((total - failed) / total * 100, 1) if total else 0}
    def table_usage_ranking(self, logs: list[dict[str, Any]]) -> list[tuple[str, int]]:
        counter: Counter[str] = Counter()
        for log in logs:
            for tbl in log.get("tables_used", []): counter[tbl] += 1
        return counter.most_common()
