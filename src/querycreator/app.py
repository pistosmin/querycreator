"""Steel Agent app entry point."""
from __future__ import annotations
from typing import Any
from querycreator.config.db_config import DBConfig
from querycreator.config.safety_rules import SafetyRules
from querycreator.config.schema_config import get_target_schemas
from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter
from querycreator.core.query.validator import QueryValidator
from querycreator.core.tools.call_function import CallFunctionTool
from querycreator.core.tools.execute_query import ExecuteQueryTool
from querycreator.core.tools.get_metadata import GetMetadataTool
from querycreator.db.connection import DBConnection, OracleConnection

class QueryCreatorApp:
    def __init__(self, db: DBConnection, dict_dir: str, schema: str, common_code_table: str = "TB_COMMON_CODE") -> None:
        self._db = db
        rules = SafetyRules()
        dictionary = BusinessDictionary(dict_dir)
        dictionary.load()
        collector = MetadataCollector(db, schema=schema)
        catalog = MetadataCatalog(dictionary=dictionary, collector=collector, db=db, common_code_table=common_code_table)
        catalog.initialize()
        table_rows = {tbl: info["num_rows"] for tbl, info in collector.collect_tables().items()}
        validator = QueryValidator(rules=rules, table_row_counts=table_rows)
        executor = QueryExecutor(db=db, validator=validator, rules=rules)
        formatter = ResultFormatter()
        self.get_metadata = GetMetadataTool(catalog=catalog)
        self.execute_query = ExecuteQueryTool(executor=executor, formatter=formatter)
        self.call_function = CallFunctionTool(executor=executor, formatter=formatter, catalog=catalog)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [GetMetadataTool.tool_schema(), ExecuteQueryTool.tool_schema(), CallFunctionTool.tool_schema()]

    def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name == "get_metadata":
            return self.get_metadata.run(**arguments)
        elif tool_name == "execute_query":
            return self.execute_query.run(**arguments)
        elif tool_name == "call_function":
            return self.call_function.run(**arguments)
        else:
            return f"알 수 없는 도구입니다: {tool_name}"

def create_app_from_env(dict_dir: str = "data/dictionaries") -> QueryCreatorApp:
    config = DBConfig.from_env()
    schemas = get_target_schemas()
    schema = schemas[0] if schemas else "PROD"
    db = OracleConnection(dsn=config.dsn, user=config.user, password=config.password)
    return QueryCreatorApp(db=db, dict_dir=dict_dir, schema=schema)
