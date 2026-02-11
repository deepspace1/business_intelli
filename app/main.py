from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from monday import fetch_deals, fetch_work_orders
from cleaner import clean_deals, clean_work_orders
from metrics import compute_deals_metrics, compute_work_orders_metrics, get_leadership_summary
from llm import parse_intent, generate_summary, generate_leadership_summary

app = FastAPI(title="Monday.com BI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    question = request.message.lower()
    
    if any(word in question for word in ["summary", "leadership", "board"]):
        deals_raw = fetch_deals()
        wo_raw = fetch_work_orders()
        deals_df = clean_deals(deals_raw)
        wo_df = clean_work_orders(wo_raw)
        
        summary_data = get_leadership_summary(deals_df, wo_df)
        answer = generate_leadership_summary(summary_data)
        return ChatResponse(answer=answer)
    
    intent = parse_intent(request.message)
    if "error" in intent:
        return ChatResponse(answer=intent["error"])
    
    deals_raw = fetch_deals()
    wo_raw = fetch_work_orders()
    deals_df = clean_deals(deals_raw)
    wo_df = clean_work_orders(wo_raw)
    
    board = intent.get("board", "deals")
    sector = intent.get("sector")
    
    if board == "deals":
        metrics = compute_deals_metrics(deals_df)
        if sector:
            metrics = metrics.get("by_sector", {}).get(sector, {})
    else:
        metrics = compute_work_orders_metrics(wo_df)
    
    answer = generate_summary(request.message, metrics)
    return ChatResponse(answer=answer)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
