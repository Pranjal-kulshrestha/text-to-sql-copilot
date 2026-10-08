"""Pick a chart type from the result shape. The frontend renders the returned spec."""


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def chart_spec(columns: list[str], rows: list[list]) -> dict | None:
    if not rows or len(columns) < 2:
        return None
    numeric = [i for i in range(len(columns)) if all(_is_number(r[i]) or r[i] is None for r in rows)]
    labels = [i for i in range(len(columns)) if i not in numeric]
    if not numeric or not labels:
        return None

    x, ys = labels[0], numeric[:3]
    x_name = columns[x].lower()
    if any(k in x_name for k in ("date", "month", "year", "day", "week")):
        kind = "line"
    elif len(rows) <= 6 and len(ys) == 1:
        kind = "pie"
    else:
        kind = "bar"
    return {"type": kind, "x": columns[x], "y": [columns[i] for i in ys]}
