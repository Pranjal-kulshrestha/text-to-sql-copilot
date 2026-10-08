import sqlite3

import pytest

from copilot.charts import chart_spec
from copilot.db import connect_readonly
from copilot.graph import MAX_ATTEMPTS, build_graph
from copilot.safety import UnsafeSQL, make_safe
from copilot.seed import seed


@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "shop.db"
    seed(str(path))
    return connect_readonly(path)


@pytest.mark.parametrize(
    "sql",
    ["DELETE FROM orders", "DROP TABLE orders", "SELECT 1; DROP TABLE orders",
     "UPDATE products SET price = 0", "PRAGMA writable_schema = 1"],
)
def test_rejects_unsafe(sql):
    with pytest.raises(UnsafeSQL):
        make_safe(sql)


def test_adds_and_caps_limit():
    assert "LIMIT 200" in make_safe("SELECT * FROM orders")
    assert "LIMIT 200" in make_safe("SELECT * FROM orders LIMIT 5000")
    assert "LIMIT 10" in make_safe("SELECT * FROM orders LIMIT 10")


def test_readonly_connection_blocks_writes(conn):
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM orders")


def test_chart_picks_line_for_dates():
    assert chart_spec(["month", "revenue"], [["2025-01", 10], ["2025-02", 12]])["type"] == "line"
    assert chart_spec(["city", "n"], [["A", 1], ["B", 2]])["type"] == "pie"
    assert chart_spec(["n"], [[1]]) is None


def test_agent_self_corrects(conn):
    calls = []

    def write_sql(question, schema, previous, error):
        calls.append(error)
        if not error:
            return "SELECT city, COUNT(*) AS n FROM customer GROUP BY city"  # wrong table name
        return "SELECT city, COUNT(*) AS n FROM customers GROUP BY city ORDER BY n DESC"

    graph = build_graph(conn, write_sql, lambda q, s, c, r: f"{len(r)} cities")
    out = graph.invoke({"question": "customers per city"})
    assert out["attempts"] == 2 and "no such table" in calls[1]
    assert out["columns"] == ["city", "n"] and len(out["rows"]) == 6
    assert out["chart"]["type"] == "pie"


def test_agent_gives_up(conn):
    graph = build_graph(conn, lambda *a: "DROP TABLE orders", lambda *a: "")
    out = graph.invoke({"question": "x"})
    assert out["attempts"] == MAX_ATTEMPTS and out["summary"].startswith("Could not")
