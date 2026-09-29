"""Entry point for LangGraph Studio. `langgraph dev` loads `graph` from here (see langgraph.json)."""

from src.graph import build_graph
from src.vectorstore import ensure_index

ensure_index()  # build the Qdrant index on first start, reuse it after that
graph = build_graph()
