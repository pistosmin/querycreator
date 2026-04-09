"""Tests for knowledge.py."""
from __future__ import annotations
import os
import pytest
import yaml
from querycreator.core.metadata.knowledge import KnowledgeBase

SAMPLE_KNOWLEDGE = {
    "schema": "TEST",
    "table_hints": {
        "TB_ORDER": {
            "index_hints": ["ORDER_NO has an index"],
            "warnings": ["Large table - use WHERE clause"],
            "sample_queries": [
                {
                    "description": "Orders by date",
                    "sql": "SELECT * FROM tb_order WHERE order_date = :date",
                }
            ],
        },
        "TB_PRODUCT": {
            "index_hints": ["PROD_CD has an index"],
            "warnings": [],
            "sample_queries": [],
        },
    },
    "join_rules": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "hint": "Join on ORDER_NO",
        }
    ],
    "forbidden_patterns": ["CROSS JOIN", "SELECT *"],
}


@pytest.fixture
def knowledge_dir(tmp_path):
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()
    yaml_file = kb_dir / "test_knowledge.yaml"
    yaml_file.write_text(yaml.dump(SAMPLE_KNOWLEDGE, allow_unicode=True), encoding="utf-8")
    return str(kb_dir)


def test_load_knowledge(knowledge_dir):
    kb = KnowledgeBase(knowledge_dir)
    kb.load()
    hints = kb.get_table_hints("TB_ORDER")
    assert hints is not None
    assert "index_hints" in hints
    assert hints["index_hints"] == ["ORDER_NO has an index"]


def test_get_sample_queries(knowledge_dir):
    kb = KnowledgeBase(knowledge_dir)
    kb.load()
    queries = kb.get_sample_queries("TB_ORDER")
    assert len(queries) == 1
    assert queries[0]["description"] == "Orders by date"
    assert ":date" in queries[0]["sql"]


def test_get_join_rules(knowledge_dir):
    kb = KnowledgeBase(knowledge_dir)
    kb.load()
    rules = kb.get_join_rules("TB_ORDER", "TB_PROD_PROGRESS")
    assert len(rules) == 1
    assert rules[0]["hint"] == "Join on ORDER_NO"
    # Also works with single table that is part of a rule
    rules_single = kb.get_join_rules("TB_ORDER")
    assert len(rules_single) == 1


def test_get_forbidden_patterns(knowledge_dir):
    kb = KnowledgeBase(knowledge_dir)
    kb.load()
    patterns = kb.get_forbidden_patterns()
    assert "CROSS JOIN" in patterns
    assert "SELECT *" in patterns


def test_no_hints_for_unknown_table(knowledge_dir):
    kb = KnowledgeBase(knowledge_dir)
    kb.load()
    hints = kb.get_table_hints("TB_NONEXISTENT")
    assert hints is None
    queries = kb.get_sample_queries("TB_NONEXISTENT")
    assert queries == []
