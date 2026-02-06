from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


_ENGINE_CACHE: dict[str, Engine] = {}


def get_mysql_engine(data_source_id: str, mysql_uri: str) -> Engine:
    engine = _ENGINE_CACHE.get(data_source_id)
    if engine is None:
        engine = create_engine(mysql_uri, future=True, pool_pre_ping=True)
        _ENGINE_CACHE[data_source_id] = engine
    return engine


def introspect_schema(engine: Engine) -> Dict[str, Any]:
    inspector = inspect(engine)
    schema_names = [s for s in inspector.get_schema_names() if s not in {"information_schema", "performance_schema", "mysql", "sys"}]

    result: Dict[str, Any] = {"databases": []}
    for schema in schema_names:
        tables: List[Dict[str, Any]] = []
        for table_name in inspector.get_table_names(schema=schema):
            columns = inspector.get_columns(table_name, schema=schema)
            pk = inspector.get_pk_constraint(table_name, schema=schema)
            fks = inspector.get_foreign_keys(table_name, schema=schema)

            date_columns = []
            normalized_columns = []
            for col in columns:
                col_type = str(col.get("type", ""))
                col_name = col["name"]
                if any(token in col_type.lower() for token in ["date", "time", "timestamp", "year"]):
                    date_columns.append(col_name)
                normalized_columns.append(
                    {
                        "name": col_name,
                        "type": col_type,
                        "nullable": bool(col.get("nullable", True)),
                        "default": col.get("default"),
                        "comment": col.get("comment"),
                    }
                )

            tables.append(
                {
                    "table_name": table_name,
                    "columns": normalized_columns,
                    "primary_keys": pk.get("constrained_columns", []) if pk else [],
                    "foreign_keys": [
                        {
                            "constrained_columns": fk.get("constrained_columns", []),
                            "referred_schema": fk.get("referred_schema"),
                            "referred_table": fk.get("referred_table"),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                        for fk in fks
                    ],
                    "date_time_columns": date_columns,
                }
            )
        result["databases"].append({"database_name": schema, "tables": tables})

    return result


def execute_readonly_query(engine: Engine, sql: str) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
