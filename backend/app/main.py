import uuid
from datetime import datetime
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Trace, Category
from .schemas import TraceCreate, TraceOut, AnalyticsOut
from .llm import llm_classify
from .seed import seed_if_empty
from .schemas import ChatIn, ChatOut
from .llm import chat_with_timing

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SupportLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    from .db import SessionLocal
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()

# Build a value→enum map once at startup (handles spaces in values safely)
_VALUE_TO_CATEGORY: dict[str, Category] = {c.value: c for c in Category}

@app.post("/traces", response_model=TraceOut)
def create_trace(payload: TraceCreate, db: Session = Depends(get_db)):
    category_str = llm_classify(payload.user_message, payload.bot_response)
    # Safe lookup — fall back to GeneralInquiry if something unexpected comes back
    cat = _VALUE_TO_CATEGORY.get(category_str, Category.GeneralInquiry)
    trace = Trace(
        id=str(uuid.uuid4()),
        user_message=payload.user_message,
        bot_response=payload.bot_response,
        category=cat,
        timestamp=datetime.utcnow(),
        response_time_ms=payload.response_time_ms,
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace

@app.get("/traces", response_model=list[TraceOut])
def list_traces(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Filter by keyword in user message or bot response"),
    db: Session = Depends(get_db),
):
    q = db.query(Trace)
    if category:
        cat = _VALUE_TO_CATEGORY.get(category)
        if cat:
            q = q.filter(Trace.category == cat)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            Trace.user_message.ilike(term) | Trace.bot_response.ilike(term)
        )
    return q.order_by(Trace.timestamp.desc()).all()

@app.get("/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db)):
    traces = db.query(Trace).all()
    total = len(traces)
    avg = (sum(t.response_time_ms for t in traces) / total) if total else 0.0

    cats = ["Billing", "Refund", "Account Access", "Cancellation", "General Inquiry"]
    counts = {c: 0 for c in cats}
    for t in traces:
        counts[t.category.value] += 1

    by_category = {}
    for c in cats:
        count = counts[c]
        by_category[c] = {
            "count": count,
            "percent": (count / total * 100.0) if total else 0.0
        }

    return {
        "total_traces": total,
        "avg_response_time_ms": round(avg, 2),
        "by_category": by_category,
    }

@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn):
    bot_response, response_time_ms = chat_with_timing(payload.user_message)
    return {"bot_response": bot_response, "response_time_ms": response_time_ms}