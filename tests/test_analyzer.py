"""Tests for analyzer.py."""
from __future__ import annotations
import pytest
from querycreator.logging.analyzer import QueryAnalyzer

SAMPLE_LOGS = [
    {"tables_used": ["TB_ORDER", "TB_PROD_PROGRESS"], "execution_time_ms": 1500.0, "success": True},
    {"tables_used": ["TB_ORDER", "TB_PROD_PROGRESS"], "execution_time_ms": 2000.0, "success": True},
    {"tables_used": ["TB_PRODUCT"], "execution_time_ms": 800.0, "success": True},
    {"tables_used": ["TB_PRODUCT"], "execution_time_ms": 600.0, "success": False},
    {"tables_used": ["TB_ORDER"], "execution_time_ms": 300.0, "success": True},
    {"tables_used": ["TB_ORDER"], "execution_time_ms": 400.0, "success": False},
]


def test_slow_query_patterns():
    analyzer = QueryAnalyzer(threshold_ms=1000)
    slow = analyzer.find_slow_patterns(SAMPLE_LOGS)
    # TB_ORDER+TB_PROD_PROGRESS avg = 1750ms should be in slow list
    assert len(slow) >= 1
    patterns = [s["tables"] for s in slow]
    assert "TB_ORDER+TB_PROD_PROGRESS" in patterns
    # TB_PRODUCT avg = 700ms should NOT be in slow list
    assert "TB_PRODUCT" not in patterns
    # Verify sorting: highest avg first
    if len(slow) > 1:
        assert slow[0]["avg_time_ms"] >= slow[1]["avg_time_ms"]
    top = next(s for s in slow if s["tables"] == "TB_ORDER+TB_PROD_PROGRESS")
    assert top["avg_time_ms"] == 1750.0
    assert top["max_time_ms"] == 2000.0
    assert top["count"] == 2


def test_failure_rate():
    analyzer = QueryAnalyzer()
    report = analyzer.failure_report(SAMPLE_LOGS)
    assert report["total"] == 6
    assert report["failed"] == 2
    assert report["success_rate"] == round(4 / 6 * 100, 1)


def test_table_usage_ranking():
    analyzer = QueryAnalyzer()
    ranking = analyzer.table_usage_ranking(SAMPLE_LOGS)
    # TB_ORDER appears in 4 logs (2 with TB_PROD_PROGRESS + 2 solo)
    table_dict = dict(ranking)
    assert table_dict["TB_ORDER"] == 4
    assert table_dict["TB_PROD_PROGRESS"] == 2
    assert table_dict["TB_PRODUCT"] == 2
    # Most common first
    assert ranking[0][0] == "TB_ORDER"
