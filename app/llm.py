import json
import google.generativeai as genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


def parse_intent(question):
    template = """
You are an intent parser. Parse the user's question into a single JSON object with these keys:
- `board`: either "deals" or "work_orders" (default to "deals" if unclear)
- `metric`: one of (deal_count, pipeline_value, revenue, active_count, columns, leadership)
- `sector`: string or null
- `timeframe`: optional string (e.g., "current quarter", "last month") or null

Return ONLY valid JSON and nothing else.

Examples:
Q: "How many deals do we have?"
-> {{"board":"deals","metric":"deal_count","sector":null,"timeframe":null}}

Q: "What's total revenue this quarter from energy?"
-> {{"board":"work_orders","metric":"revenue","sector":"energy","timeframe":"current quarter"}}

Question: {}
"""
    prompt = template.format(question)
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception:
        # simple deterministic fallback
        q = question.lower()
        result = {"board": "deals", "metric": None, "sector": None, "timeframe": None}
        if "work" in q or "work order" in q or "revenue" in q and "work" in q:
            result["board"] = "work_orders"
        if any(w in q for w in ["pipeline", "pipeline value", "total pipeline"]):
            result["metric"] = "pipeline_value"
        if any(w in q for w in ["deal", "deals", "number of deals"]):
            result["metric"] = "deal_count"
        if "revenue" in q:
            result["metric"] = "revenue"
        if any(w in q for w in ["column", "columns"]):
            result["metric"] = "columns"
        if any(w in q for w in ["summary", "leadership", "board"]):
            result["metric"] = "leadership"
        # sector detection: pick last word as potential sector if it's short
        # Improved fallback sector detection:
        # - ignore common stopwords and metric words
        # - prefer the last non-stopword token that's not a metric keyword
        stopwords = set(["is", "are", "the", "a", "an", "in", "from", "for", "of", "by", "what", "how", "much", "do", "we", "our", "please"])
        metric_words = set(["revenue", "pipeline", "deal", "deals", "count", "columns", "summary", "leadership", "work", "orders", "work_orders", "total"])
        tokens = [w.strip('?,.!"\'') for w in q.split()]
        for t in reversed(tokens):
            if not t:
                continue
            tl = t.lower()
            if tl in stopwords or tl in metric_words:
                continue
            if tl.isdigit():
                continue
            if len(tl) < 2:
                continue
            # treat 'all'/'any'/'none' as no-sector (leave None)
            if tl in ("all", "any", "none", "overall", "total"):
                break
            # accept as sector candidate
            result['sector'] = tl
            break
        if result["metric"] is None:
            return {"error": "Could not understand the question"}
        return result


def generate_summary(question, metrics):
    # Keep LLM-based summary as a fallback for complex questions
    prompt = f"""You are a business assistant. Answer this question based on the data.

Question: {question}
Data: {json.dumps(metrics, default=str)}

Respond in 2-3 sentences, be specific with numbers."""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Could not generate answer"


def answer_from_metrics(intent, metrics):
    # Deterministic, fast answers for common metrics
    if not intent or not metrics:
        return None

    metric = intent.get('metric')
    board = intent.get('board', 'deals')
    sector = intent.get('sector')

    try:
        # normalize metric synonyms
        if metric in (None, ''):
            return None

        m = metric.lower()
        if m in ('deal_count', 'deals', 'count', 'number_of_deals'):
            c = metrics.get('deal_count') if isinstance(metrics, dict) else None
            if c is not None:
                return f"Total deals: {int(c):,}"
            return None

        if m in ('pipeline', 'pipeline_value', 'total_pipeline'):
            # prefer sector-specific response when sector requested
            if sector and isinstance(metrics, dict) and 'pipeline' in metrics:
                p = metrics.get('pipeline', 0)
                cnt = metrics.get('count', 0)
                return f"Sector '{sector}': {int(cnt):,} deals; pipeline ${float(p):,.0f}"
            # support both total and sector-level metrics (which may have 'pipeline')
            v = None
            if isinstance(metrics, dict):
                v = metrics.get('total_pipeline')
                if v is None and 'pipeline' in metrics:
                    v = metrics.get('pipeline')
            elif isinstance(metrics, (int, float)):
                v = metrics
            if v is not None:
                return f"Total pipeline value: ${float(v):,.0f}"
            return None

        # treat 'revenue' intelligently: if metrics contain total_revenue use it,
        # otherwise for deals interpret revenue request as pipeline (support sector-level 'pipeline')
        if m in ('revenue', 'total_revenue'):
            if isinstance(metrics, dict) and 'total_revenue' in metrics:
                v = metrics.get('total_revenue')
                return f"Total revenue: ${float(v):,.0f}"
            # if metrics include sector-level pipeline, prefer that (and include count)
            if isinstance(metrics, dict) and 'pipeline' in metrics:
                p = metrics.get('pipeline', 0)
                cnt = metrics.get('count', 0)
                if cnt:
                    return f"Sector '{sector}': {int(cnt):,} deals; revenue (interpreted from pipeline) ${float(p):,.0f}"
                return f"Revenue (interpreted from pipeline): ${float(p):,.0f}"
            # if dealing with aggregate deals metrics, fall back to total_pipeline
            if isinstance(metrics, dict) and 'total_pipeline' in metrics:
                v = metrics.get('total_pipeline')
                return f"Total pipeline (interpreted as revenue): ${float(v):,.0f}"
            if isinstance(metrics, (int, float)):
                return f"Total revenue: ${float(metrics):,.0f}"
            return None

        if metric == 'active_count':
            v = metrics.get('active_count') if isinstance(metrics, dict) else None
            if v is not None:
                return f"Active work orders: {int(v):,}" if board == 'work_orders' else f"Active deals: {int(v):,}"

        if metric == 'columns':
            # metrics here expected to be list of columns
            if isinstance(metrics, list):
                names = [c.get('title') or c.get('name') or c.get('id') for c in metrics]
                return f"Board has {len(names)} columns: {', '.join(names[:10])}{'...' if len(names) > 10 else ''}"

        # sector-specific metrics: metrics may be {'pipeline': x, 'count': y}
        if sector and isinstance(metrics, dict):
            if 'pipeline' in metrics or 'count' in metrics:
                p = metrics.get('pipeline', 0)
                cnt = metrics.get('count', 0)
                return f"Sector '{sector}': {int(cnt):,} deals; pipeline ${float(p):,.0f}"

    except Exception:
        return None

    return None


def generate_leadership_summary(summary_data):
    prompt = f"""Create a brief leadership summary with bullet points from this data:
    
{json.dumps(summary_data, default=str)}

Keep it short and clear."""
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Could not generate summary"

