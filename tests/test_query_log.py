"""Tests for query_log.py."""
from __future__ import annotations
import os
import pytest
from querycreator.logging.query_log import LogEntry, QueryLog


def test_log_entry_creation():
    entry = LogEntry(
        user_question="What is the total production?",
        generated_sql="SELECT SUM(qty) FROM tb_prod",
        tables_used=["TB_PROD"],
        execution_time_ms=250.0,
        success=True,
        row_count=1,
    )
    assert entry.user_question == "What is the total production?"
    assert entry.success is True
    assert entry.row_count == 1
    assert entry.error == ""
    assert entry.timestamp != ""


def test_log_write_and_read(tmp_path):
    log_path = str(tmp_path / "logs" / "query.jsonl")
    log = QueryLog(log_path)
    entry = LogEntry(
        user_question="Show all orders",
        generated_sql="SELECT * FROM tb_order",
        tables_used=["TB_ORDER"],
        execution_time_ms=100.0,
        success=True,
        row_count=10,
    )
    log.write(entry)
    entries = log.read_all()
    assert len(entries) == 1
    assert entries[0]["user_question"] == "Show all orders"
    assert entries[0]["tables_used"] == ["TB_ORDER"]
    assert entries[0]["success"] is True


def test_log_multiple_entries(tmp_path):
    log_path = str(tmp_path / "logs" / "query.jsonl")
    log = QueryLog(log_path)
    for i in range(3):
        entry = LogEntry(
            user_question=f"Question {i}",
            generated_sql=f"SELECT {i} FROM dual",
            tables_used=["DUAL"],
            execution_time_ms=float(i * 100),
            success=True,
        )
        log.write(entry)
    entries = log.read_all()
    assert len(entries) == 3
    assert entries[0]["user_question"] == "Question 0"
    assert entries[2]["user_question"] == "Question 2"


def test_log_failed_entry(tmp_path):
    log_path = str(tmp_path / "logs" / "query.jsonl")
    log = QueryLog(log_path)
    entry = LogEntry(
        user_question="Bad query",
        generated_sql="SELECT * FROM nonexistent",
        tables_used=[],
        execution_time_ms=50.0,
        success=False,
        error="Table not found",
    )
    log.write(entry)
    entries = log.read_all()
    assert len(entries) == 1
    assert entries[0]["success"] is False
    assert entries[0]["error"] == "Table not found"
    assert entries[0]["row_count"] == 0
