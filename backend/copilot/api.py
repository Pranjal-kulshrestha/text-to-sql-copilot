import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from copilot.db import connect_readonly
from copilot.graph import build_graph, llm_sql_writer, llm_summarizer
from copilot.seed import seed

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/shop.db")

app = FastAPI(title="Text-to-SQL Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_graph():
    if not Path(DB_PATH).exists():
        seed(DB_PATH)
    llm = init_chat_model(os.getenv("LLM_MODEL", "anthropic:claude-sonnet-5-5"))
    return build_graph(connect_readonly(DB_PATH), llm_sql_writer(llm), llm_summarizer(llm))


class AskIn(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(body: AskIn):
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    try:
        s = get_graph().invoke({"question": body.question})
    except Exception as e:  # surface provider errors (missing key, rate limit) to the UI
        raise HTTPException(502, f"LLM call failed: {e}") from e
    return {
        "sql": s.get("sql", ""),
        "attempts": s.get("attempts", 0),
        "columns": s.get("columns", []),
        "rows": s.get("rows", []),
        "summary": s.get("summary", ""),
        "chart": s.get("chart"),
    }
