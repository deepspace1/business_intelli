import json
from typing import Any, Dict
import pandas as pd

# LangChain imports
try:
    from langchain.llms.base import LLM
    from langchain.tools import Tool
    from langchain.agents import initialize_agent, AgentType
except Exception:
    LLM = None
    Tool = None
    initialize_agent = None
    AgentType = None

from app.monday_client import fetch_deals, fetch_work_orders, fetch_deals_columns, fetch_work_orders_columns
from app.llm import model as gemini_model, GEMINI_MODEL, GEMINI_API_KEY
from app.cleaner import clean_deals, clean_work_orders
from app.metrics import compute_deals_metrics, compute_work_orders_metrics


def get_context(limit: int = 20):
    """Module-level helper to build cleaned samples + metrics payload."""
    deals = fetch_deals()
    wo = fetch_work_orders()
    deals_cols = fetch_deals_columns()
    wo_cols = fetch_work_orders_columns()
    cleaned_deals = clean_deals(deals, deals_cols)
    cleaned_wo = clean_work_orders(wo, wo_cols)
    deals_metrics = compute_deals_metrics(cleaned_deals)
    wo_metrics = compute_work_orders_metrics(cleaned_wo)

    return {
        "sample_deals": cleaned_deals[:limit],
        "sample_work_orders": cleaned_wo[:limit],
        "deals_columns": deals_cols,
        "work_orders_columns": wo_cols,
        "deals_metrics": deals_metrics,
        "work_orders_metrics": wo_metrics,
    }


def get_deals_df():
    """Return a pandas DataFrame of cleaned deals."""
    deals = fetch_deals()
    cols = fetch_deals_columns()
    cleaned = clean_deals(deals, cols)
    try:
        df = pd.DataFrame(cleaned)
    except Exception:
        df = pd.DataFrame(cleaned)
    return df


if LLM is not None:
    class GeminiLangchainLLM(LLM):
        """Minimal LangChain-compatible LLM wrapper around the existing Gemini model.
        This implements the small surface LangChain expects: `_call(prompt)` and
        `_identifying_params`.
        """

        @property
        def _identifying_params(self) -> Dict[str, Any]:
            return {"model": GEMINI_MODEL}

        def _call(self, prompt: str, stop: Any = None) -> str:
            # Use the same `model` object configured in app.llm
            try:
                resp = gemini_model.generate_content(prompt)
                return resp.text
            except Exception as e:
                return f"[LLM error] {e}"
else:
    # LangChain not available; provide a stub run_agent to surface a clear error
    def run_agent(question: str) -> str:
        return "[agent error] LangChain not installed or failed to import"


def _make_tools():
    """Create LangChain Tool wrappers around mondayClient fetch functions.
    Each tool returns a JSON-serializable structure.
    """
    tools = []

    def t_fetch_deals(limit: int = 50, page: int = 1, sector: str = None, **kwargs):
        items = fetch_deals()
        cols = fetch_deals_columns()
        cleaned = clean_deals(items, cols)
        sk = (sector or '')
        if sk and sk.lower().strip() not in ("", "all", "none"):
            sk = sk.lower().strip()
            cleaned = [d for d in cleaned if d.get('sector') == sk]
        return cleaned

    def t_fetch_work_orders(limit: int = 50, page: int = 1, status: str = None, **kwargs):
        items = fetch_work_orders()
        cols = fetch_work_orders_columns()
        cleaned = clean_work_orders(items, cols)
        if status:
            st = status.lower().strip()
            cleaned = [w for w in cleaned if w.get('status') and w.get('status').lower() == st]
        return cleaned

    def t_fetch_deals_columns(**kwargs):
        return fetch_deals_columns()

    def t_fetch_work_orders_columns(**kwargs):
        return fetch_work_orders_columns()

    def t_compute_deals_metrics(**kwargs):
        items = fetch_deals()
        cols = fetch_deals_columns()
        cleaned = clean_deals(items, cols)
        return compute_deals_metrics(cleaned)

    def t_compute_work_orders_metrics(**kwargs):
        items = fetch_work_orders()
        cols = fetch_work_orders_columns()
        cleaned = clean_work_orders(items, cols)
        return compute_work_orders_metrics(cleaned)

    def t_capabilities(**kwargs):
        return {
            "capabilities": [
                "fetch_deals(limit,page,sector)",
                "fetch_work_orders(limit,page,status)",
                "fetch_deals_columns()",
                "fetch_work_orders_columns()",
                "compute_deals_metrics()",
                "compute_work_orders_metrics()",
                "You can ask about pipeline, revenue, counts, sectors, and date ranges for both boards."
            ]
        }

    def t_get_context(limit: int = 20, **kwargs):
        """Return small context payload: sample rows, columns, and aggregated metrics."""
        deals = fetch_deals()
        wo = fetch_work_orders()
        deals_cols = fetch_deals_columns()
        wo_cols = fetch_work_orders_columns()
        cleaned_deals = clean_deals(deals, deals_cols)
        cleaned_wo = clean_work_orders(wo, wo_cols)
        deals_metrics = compute_deals_metrics(cleaned_deals)
        wo_metrics = compute_work_orders_metrics(cleaned_wo)

        return {
            "sample_deals": cleaned_deals[:limit],
            "sample_work_orders": cleaned_wo[:limit],
            "deals_columns": deals_cols,
            "work_orders_columns": wo_cols,
            "deals_metrics": deals_metrics,
            "work_orders_metrics": wo_metrics,
        }

    def t_fetch_deals_df(**kwargs):
        """Return cleaned deals as a JSON-serializable list via pandas (records)."""
        df = get_deals_df()
        return df.to_dict(orient='records')

    def t_group_by_sector(**kwargs):
        """Return pipeline sum and count grouped by sector using pandas."""
        df = get_deals_df()
        if df.empty or 'sector' not in df.columns or 'amount' not in df.columns:
            return {}
        gb = df.groupby('sector').agg({'amount': 'sum', 'name': 'count'}).reset_index()
        return {row['sector']: {'pipeline': float(row['amount']), 'count': int(row['name'])} for _, row in gb.iterrows()}

    def t_filter_deals(sector: str = None, min_amount: float = None, stage: str = None, **kwargs):
        df = get_deals_df()
        if sector:
            df = df[df['sector'] == sector.lower().strip()]
        if stage:
            df = df[df['stage'].str.lower().str.contains(stage.lower().strip(), na=False)]
        if min_amount is not None:
            df = df[df['amount'].astype(float) >= float(min_amount)]
        return df.to_dict(orient='records')

    # Wrap as LangChain Tool objects if available; otherwise return callables
    if Tool is not None:
        tools.append(Tool.from_function(t_fetch_deals, name="fetch_deals", description="Fetch deals items from Monday"))
        tools.append(Tool.from_function(t_fetch_work_orders, name="fetch_work_orders", description="Fetch work orders from Monday"))
        tools.append(Tool.from_function(t_fetch_deals_columns, name="fetch_deals_columns", description="Fetch deals board column metadata"))
        tools.append(Tool.from_function(t_fetch_work_orders_columns, name="fetch_work_orders_columns", description="Fetch work orders board column metadata"))
        tools.append(Tool.from_function(t_compute_deals_metrics, name="compute_deals_metrics", description="Compute deals metrics like pipeline and by_sector"))
        tools.append(Tool.from_function(t_compute_work_orders_metrics, name="compute_work_orders_metrics", description="Compute work orders metrics like revenue and active_count"))
        tools.append(Tool.from_function(t_capabilities, name="capabilities", description="Return agent capabilities and available tool names"))
        tools.append(Tool.from_function(t_get_context, name="get_context", description="Return a small cleaned data + metrics context payload"))
        tools.append(Tool.from_function(t_fetch_deals_df, name="fetch_deals_df", description="Return cleaned deals as JSON records via pandas"))
        tools.append(Tool.from_function(t_group_by_sector, name="group_by_sector", description="Return pipeline and counts grouped by sector"))
        tools.append(Tool.from_function(t_filter_deals, name="filter_deals", description="Filter deals by sector, min_amount, stage and return matching rows"))
    else:
        tools = [t_fetch_deals, t_fetch_work_orders, t_fetch_deals_columns, t_fetch_work_orders_columns, t_compute_deals_metrics, t_compute_work_orders_metrics, t_capabilities, t_get_context, t_fetch_deals_df, t_group_by_sector, t_filter_deals]

    return tools


_agent_executor = None


def _init_agent():
    global _agent_executor
    if _agent_executor is not None:
        return _agent_executor

    tools = _make_tools()
    if initialize_agent is None or LLM is None:
        raise RuntimeError("LangChain is not installed or could not be imported")

    llm = GeminiLangchainLLM()
    _agent_executor = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=False)
    return _agent_executor


def run_agent(question: str) -> str:
    """Run the LangChain agent on the question. Returns the agent answer (string).
    The agent may call the provided tools to fetch data as needed.
    """
    # quick-help before initializing LangChain
    ql = (question or '').lower()
    # quick sector listing shortcut
    if ("sector" in ql or "sectors" in ql) and any(p in ql for p in ["list", "available", "show", "all"]):
        try:
            items = fetch_deals()
            cols = fetch_deals_columns()
            cleaned = clean_deals(items, cols)
            metrics = compute_deals_metrics(cleaned)
            available = [k for k in metrics.get('by_sector', {}).keys() if k and k != 'unknown']
            if not available:
                return "No sectors available"
            return f"Available sectors: {', '.join(sorted(available))}"
        except Exception as e:
            return f"[agent error] could not list sectors: {e}"

    # quick context shortcut
    if any(p in ql for p in ["context", "show data", "show context", "data snapshot", "sample data"]):
        try:
            ctx = get_context(limit=20)
            return json.dumps(ctx, default=str, indent=2)
        except Exception as e:
            return f"[agent error] could not build context: {e}"
    if any(p in ql for p in ["what questions", "what can you", "help", "capabilities", "what do you know"]):
        caps = {
            "description": "I can fetch deals and work orders, list columns, and compute metrics (pipeline, revenue, counts) for both boards.",
            "tools": ["fetch_deals", "fetch_work_orders", "fetch_deals_columns", "fetch_work_orders_columns", "compute_deals_metrics", "compute_work_orders_metrics"]
        }
        return json.dumps(caps, indent=2)

    try:
        agent = _init_agent()
        result = agent.run(question)
        return str(result)
    except Exception as e:
        return f"[agent error] {e}"
