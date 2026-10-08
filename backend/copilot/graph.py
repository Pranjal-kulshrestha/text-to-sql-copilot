"""LangGraph agent: generate SQL -> validate -> execute -> (retry with error) -> summarize."""

import sqlite3
from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from copilot.charts import chart_spec
from copilot.db import describe_schema, run_query
from copilot.safety import UnsafeSQL, make_safe

MAX_ATTEMPTS = 3

# (question, schema, previous_sql, error) -> sql
SqlWriter = Callable[[str, str, str, str], str]
# (question, sql, columns, rows) -> summary
Summarizer = Callable[[str, str, list, list], str]


class SqlState(TypedDict, total=False):
    question: str
    schema: str
    sql: str
    error: str
    attempts: int
    columns: list[str]
    rows: list[list]
    summary: str
    chart: dict | None


def build_graph(conn: sqlite3.Connection, write_sql: SqlWriter, summarize: Summarizer):
    def load_schema(state: SqlState):
        return {"schema": describe_schema(conn), "attempts": 0, "error": ""}

    def generate(state: SqlState):
        sql = write_sql(state["question"], state["schema"], state.get("sql", ""), state.get("error", ""))
        return {"sql": sql, "attempts": state["attempts"] + 1}

    def validate_and_run(state: SqlState):
        try:
            safe = make_safe(state["sql"])
            columns, rows = run_query(conn, safe)
        except (UnsafeSQL, sqlite3.Error) as e:
            return {"error": str(e)}
        return {"sql": safe, "columns": columns, "rows": rows, "error": ""}

    def route(state: SqlState):
        if not state["error"]:
            return "summarize"
        return "generate" if state["attempts"] < MAX_ATTEMPTS else "fail"

    def summarize_node(state: SqlState):
        return {
            "summary": summarize(state["question"], state["sql"], state["columns"], state["rows"]),
            "chart": chart_spec(state["columns"], state["rows"]),
        }

    def fail(state: SqlState):
        return {"summary": f"Could not build a valid query after {MAX_ATTEMPTS} attempts: {state['error']}",
                "columns": [], "rows": [], "chart": None}

    g = StateGraph(SqlState)
    g.add_node("load_schema", load_schema)
    g.add_node("generate", generate)
    g.add_node("validate_and_run", validate_and_run)
    g.add_node("summarize", summarize_node)
    g.add_node("fail", fail)
    g.add_edge(START, "load_schema")
    g.add_edge("load_schema", "generate")
    g.add_edge("generate", "validate_and_run")
    g.add_conditional_edges("validate_and_run", route, ["generate", "summarize", "fail"])
    g.add_edge("summarize", END)
    g.add_edge("fail", END)
    return g.compile()


def llm_sql_writer(llm) -> SqlWriter:
    def write(question, schema, previous_sql, error):
        retry = (
            f"\n\nYour previous query failed.\nQuery: {previous_sql}\nError: {error}\nFix it."
            if error else ""
        )
        text = llm.invoke(
            "You write SQLite SELECT queries. Return only the SQL, no explanation, no code fence.\n\n"
            f"Schema:\n{schema}\n\nQuestion: {question}{retry}"
        ).content
        return text.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()

    return write


def llm_summarizer(llm) -> Summarizer:
    def summarize(question, sql, columns, rows):
        preview = [columns] + rows[:20]
        return llm.invoke(
            "Answer the question in 1-3 sentences using the query result. Mention key numbers.\n\n"
            f"Question: {question}\nSQL: {sql}\nResult (first rows): {preview}"
        ).content

    return summarize
