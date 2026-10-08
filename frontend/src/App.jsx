import { useState } from "react";
import {
  Bar, BarChart, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const COLORS = ["#4f46e5", "#0891b2", "#d97706", "#db2777", "#16a34a", "#7c3aed"];
const EXAMPLES = [
  "Monthly revenue in 2025",
  "Top 5 cities by number of delivered orders",
  "Revenue share by product category",
  "Which customers spent the most?",
];

function Chart({ spec, columns, rows }) {
  if (!spec) return null;
  const data = rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
  if (spec.type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} dataKey={spec.y[0]} nameKey={spec.x} label>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip /><Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  const Wrapper = spec.type === "line" ? LineChart : BarChart;
  return (
    <ResponsiveContainer width="100%" height={300}>
      <Wrapper data={data}>
        <XAxis dataKey={spec.x} /><YAxis /><Tooltip /><Legend />
        {spec.y.map((y, i) =>
          spec.type === "line"
            ? <Line key={y} dataKey={y} stroke={COLORS[i]} dot={false} />
            : <Bar key={y} dataKey={y} fill={COLORS[i]} />
        )}
      </Wrapper>
    </ResponsiveContainer>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(q) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(await res.text());
      setResult(await res.json());
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Text-to-SQL Copilot</h1>
      <form onSubmit={(e) => { e.preventDefault(); if (question.trim()) ask(question); }}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)}
               placeholder="Ask a question about the shop database" />
        <button disabled={loading}>{loading ? "Thinking..." : "Ask"}</button>
      </form>
      <div className="examples">
        {EXAMPLES.map((q) => (
          <button key={q} type="button" onClick={() => { setQuestion(q); ask(q); }}>{q}</button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {result && (
        <section>
          <p className="summary">{result.summary}</p>
          <details open>
            <summary>SQL ({result.attempts} attempt{result.attempts === 1 ? "" : "s"})</summary>
            <pre>{result.sql}</pre>
          </details>
          <Chart spec={result.chart} columns={result.columns} rows={result.rows} />
          {result.rows.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>
                  {result.rows.slice(0, 50).map((r, i) => (
                    <tr key={i}>{r.map((v, j) => <td key={j}>{String(v)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
