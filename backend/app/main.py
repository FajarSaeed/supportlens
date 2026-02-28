import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, check_db, engine, get_db
from .llm import _USE_REAL_LLM, chat_with_timing, llm_classify
from .models import Category, Trace
from .schemas import AnalyticsOut, ChatIn, ChatOut, TraceCreate, TraceOut
from .seed import seed_if_empty

# ── Logging setup ─────────────────────────────────────────────────────────────
# Emit structured JSON to stdout. One line per record.

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra fields attached to the record
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
            }:
                payload[key] = val
        return json.dumps(payload)


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # Silence uvicorn's own access log — we emit our own
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger("supportlens")

# ── App startup time (for uptime reporting) ───────────────────────────────────
_START_TIME = time.monotonic()

# ── DB + app init ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SupportLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = int((time.perf_counter() - start) * 1000)
    path = request.url.path

    # Suppress health-check noise — orchestrators poll every few seconds
    if path == "/health":
        return response

    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "query": str(request.url.query),
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
        },
    )
    return response


# ── Category lookup map ───────────────────────────────────────────────────────
_VALUE_TO_CATEGORY: dict[str, Category] = {c.value: c for c in Category}


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """
    Probes real dependencies and returns system state.

    LLM mode design decision:
      - "real"  → OPENAI_API_KEY is set; GPT-4o-mini is used
      - "mock"  → no key; keyword fallback is active
    A missing API key is NOT unhealthy — the app degrades gracefully.
    Only the database being unreachable makes the service unhealthy.
    """
    db_ok = check_db()
    uptime_s = round(time.monotonic() - _START_TIME, 1)

    llm_mode = "real" if _USE_REAL_LLM else "mock"

    status = "healthy" if db_ok else "unhealthy"

    return {
        "status": status,
        "uptime_seconds": uptime_s,
        "checks": {
            "database": "ok" if db_ok else "unreachable",
            "llm": {
                "mode": llm_mode,
                "status": "ok",
                # mock mode is fully functional — not a failure
                "note": (
                    "Using GPT-4o-mini" if llm_mode == "real"
                    else "No API key — keyword fallback active (fully functional)"
                ),
            },
        },
    }


# ── Traces endpoints ──────────────────────────────────────────────────────────
@app.post("/traces", response_model=TraceOut)
def create_trace(payload: TraceCreate, db: Session = Depends(get_db)):
    category_str = llm_classify(payload.user_message, payload.bot_response)
    cat = _VALUE_TO_CATEGORY.get(category_str, Category.GeneralInquiry)

    if category_str not in _VALUE_TO_CATEGORY:
        logger.warning(
            "llm_unexpected_category",
            extra={
                "raw_category": category_str,
                "fallback": cat.value,
                "user_message_preview": payload.user_message[:120],
            },
        )

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


# ── Analytics endpoint ────────────────────────────────────────────────────────
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
            "percent": (count / total * 100.0) if total else 0.0,
        }

    return {
        "total_traces": total,
        "avg_response_time_ms": round(avg, 2),
        "by_category": by_category,
    }


# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn):
    bot_response, response_time_ms = chat_with_timing(payload.user_message)
    return {"bot_response": bot_response, "response_time_ms": response_time_ms}
