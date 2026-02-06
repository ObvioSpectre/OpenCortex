from __future__ import annotations

from typing import Dict, Set

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


FORBIDDEN_TOKENS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "grant",
    "revoke",
    "create",
    "replace",
    "call",
    "execute",
}


class SQLValidationError(ValueError):
    pass


def validate_sql(sql: str, allowlist: Dict[str, Set[str]]) -> None:
    normalized = " ".join(sql.strip().lower().split())
    if not normalized.startswith("select"):
        raise SQLValidationError("Only SELECT queries are allowed")
    if ";" in normalized:
        raise SQLValidationError("Multiple statements are not allowed")
    if any(token in normalized for token in FORBIDDEN_TOKENS):
        raise SQLValidationError("Forbidden SQL token detected")

    try:
        ast = parse_one(sql, read="mysql")
    except ParseError as exc:
        raise SQLValidationError("SQL could not be parsed") from exc

    if not ast.find(exp.Select):
        raise SQLValidationError("Query must be a SELECT")

    _enforce_no_select_star(ast)

    tables = list(ast.find_all(exp.Table))
    if not tables:
        raise SQLValidationError("Query must reference at least one table")

    alias_to_table: Dict[str, str] = {}
    referenced_tables: set[str] = set()
    for t in tables:
        table_name = t.name
        db_name = t.db
        if not db_name:
            raise SQLValidationError("Tables must be fully qualified with database name")
        fq = f"{db_name}.{table_name}"
        if fq not in allowlist:
            raise SQLValidationError("Query references a table outside role permissions")
        referenced_tables.add(fq)

        alias = t.alias
        if alias and alias.name:
            alias_to_table[alias.name] = fq
        alias_to_table[table_name] = fq

    allowed_union_cols = set()
    for tbl in referenced_tables:
        allowed_union_cols.update(allowlist[tbl])

    for c in ast.find_all(exp.Column):
        if isinstance(c.this, exp.Star) or c.name == "*":
            raise SQLValidationError("SELECT * is not allowed")

        table_ref = c.table
        if table_ref:
            fq = alias_to_table.get(table_ref)
            if not fq:
                raise SQLValidationError("Unknown table alias in query")
            if c.name not in allowlist[fq]:
                raise SQLValidationError("Query references a column outside role permissions")
        else:
            if c.name not in allowed_union_cols:
                raise SQLValidationError("Query references a column outside role permissions")


def _enforce_no_select_star(ast: exp.Expression) -> None:
    for select_node in ast.find_all(exp.Select):
        for projection in select_node.expressions:
            if isinstance(projection, exp.Star):
                raise SQLValidationError("SELECT * is not allowed")
            if isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                raise SQLValidationError("SELECT * is not allowed")
