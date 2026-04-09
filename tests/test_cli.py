"""Tests for admin CLI — dictionary validation and report generation."""
from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from querycreator.admin.cli import generate_report, validate_dictionary

VALID_DICT = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {"ORDER_NO": "주문번호"},
        },
        "TB_PROD_PROGRESS": {
            "business_name": "진행량",
            "description": "공정별 진행 현황",
            "key_columns": {"ORDER_NO": "주문번호"},
        },
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호 기준 합산",
            "parameters": {"P_ORDER_NO": "주문번호"},
        }
    },
}


def _write_yaml(data: dict, tmpdir: str, filename: str = "test.yaml") -> str:
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)
    return path


def test_validate_dictionary_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_yaml(VALID_DICT, tmpdir)
        errors = validate_dictionary(path)
    assert errors == []


def test_validate_dictionary_missing_schema():
    data = {k: v for k, v in VALID_DICT.items() if k != "schema"}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_yaml(data, tmpdir)
        errors = validate_dictionary(path)
    assert any("schema" in e for e in errors)


def test_validate_dictionary_missing_business_name():
    import copy
    data = copy.deepcopy(VALID_DICT)
    del data["tables"]["TB_ORDER"]["business_name"]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_yaml(data, tmpdir)
        errors = validate_dictionary(path)
    assert any("business_name" in e for e in errors)


def test_generate_report_from_logs():
    logs = [
        {"sql": "SELECT ORDER_NO FROM TB_ORDER WHERE ORDER_DATE = '2024-01-01'", "success": True, "execution_time_ms": 120, "tables_used": ["TB_ORDER"]},
        {"sql": "SELECT PROC_CD, WEIGHT FROM TB_PROD_PROGRESS WHERE ORDER_NO = 'ORD-001'", "success": True, "execution_time_ms": 350, "tables_used": ["TB_PROD_PROGRESS"]},
        {"sql": "DELETE FROM TB_ORDER", "success": False, "execution_time_ms": 0, "error": "SELECT 문만 허용됩니다.", "tables_used": ["TB_ORDER"]},
    ]
    report = generate_report(logs)
    assert "3건" in report
    assert "실패" in report
