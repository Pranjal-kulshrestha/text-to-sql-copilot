"""SQL safety: parse with sqlglot, allow a single SELECT only, and force a row limit."""

import sqlglot
from sqlglot import exp

FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command, exp.Pragma)


class UnsafeSQL(ValueError):
    pass


def make_safe(sql: str, max_rows: int = 200, dialect: str = "sqlite") -> str:
    sql = sql.strip().strip("`").removeprefix("sql").strip().rstrip(";")
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except sqlglot.errors.ParseError as e:
        raise UnsafeSQL(f"Could not parse SQL: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSQL("Exactly one statement is allowed.")
    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union, exp.With)) and not tree.find(exp.Select):
        raise UnsafeSQL("Only SELECT queries are allowed.")
    if any(tree.find(node) for node in FORBIDDEN):
        raise UnsafeSQL("Query contains a write or DDL operation.")

    if isinstance(tree, exp.Select):
        limit = tree.args.get("limit")
        current = int(limit.expression.name) if limit and limit.expression.is_int else None
        if current is None or current > max_rows:
            tree = tree.limit(max_rows)
    return tree.sql(dialect=dialect)
