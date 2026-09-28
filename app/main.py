"""Agent service — điểm ráp nối của cả lab (CP1, CP3, CP4).

Luồng một request tới /ask:

    client ──► verify_api_key ──► rate_limiter ──► cost_guard
                                                       │
                              store.get_history ◄──────┘
                                       │
                                    ask_llm
                                       │
                              store.append × 2 ──► cost_guard.record ──► log_event
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from utils.mock_llm import ask_llm

from .auth import verify_api_key
from .config import get_settings
from .cost_guard import CostGuard
from .lifecycle import lifecycle
from .logging_utils import log_event
from .rate_limiter import RateLimiter
from .store import ConversationStore, get_redis_client

SERVICE_NAME = "day12-agent"
SERVICE_VERSION = "1.0.0"


# ─────────────────────────────────────────────────────────────
# Providers — CHO SẴN
# Tách ra thành hàm để test có thể thay bằng Redis giả qua
# app.dependency_overrides, và để kết nối Redis chỉ tạo khi thật sự cần.
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_store() -> ConversationStore:
    return ConversationStore(get_redis_client())


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis_client(), get_settings().rate_limit_per_minute)


@lru_cache(maxsize=1)
def get_cost_guard() -> CostGuard:
    return CostGuard(get_redis_client(), get_settings().monthly_budget_usd)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """CHO SẴN — chạy lúc app khởi động và lúc tắt."""
    lifecycle.install()
    log_event("service_started", service=SERVICE_NAME, version=SERVICE_VERSION)
    yield
    log_event("service_stopped", service=SERVICE_NAME)


app = FastAPI(title="Day 12 Production Agent", version=SERVICE_VERSION, lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


HTML_LANDING_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Day 12 Production Agent — Live on Cloud</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #22c55e;
      --code-bg: #090d16;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
    }
    .container { max-width: 860px; margin: 0 auto; }
    .header { text-align: center; margin-bottom: 2.5rem; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(34, 197, 94, 0.15);
      color: var(--success);
      border: 1px solid rgba(34, 197, 94, 0.3);
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.875rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }
    .badge-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); }
    h1 { font-size: 2.25rem; font-weight: 800; margin-bottom: 0.5rem; color: #fff; }
    .subtitle { color: var(--text-muted); font-size: 1.05rem; }
    .author-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem 1.75rem;
      margin-bottom: 2rem;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 1rem;
    }
    .author-item { display: flex; flex-direction: column; }
    .author-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; }
    .author-value { font-size: 1.1rem; font-weight: 600; color: var(--primary); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      transition: transform 0.2s, border-color 0.2s;
      text-decoration: none;
      color: inherit;
      display: block;
    }
    .card:hover { transform: translateY(-3px); border-color: var(--primary); }
    .card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 0.4rem; display: flex; align-items: center; justify-content: space-between; }
    .card-desc { font-size: 0.875rem; color: var(--text-muted); }
    .section-title { font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem; color: #fff; }
    .code-box {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      overflow-x: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.875rem;
      color: #38bdf8;
      line-height: 1.5;
    }
    footer { text-align: center; margin-top: 3rem; color: var(--text-muted); font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="badge"><span class="badge-dot"></span> System Live & Operational</div>
      <h1>Day 12 Production Agent</h1>
      <p class="subtitle">Cloud Services & Deployment — VinUni AI Engineering Lab</p>
    </div>

    <div class="author-card">
      <div class="author-item">
        <span class="author-label">Học viên</span>
        <span class="author-value">Hoàng Minh Tuấn</span>
      </div>
      <div class="author-item">
        <span class="author-label">Mã học viên (MSSV)</span>
        <span class="author-value">2A202602758</span>
      </div>
      <div class="author-item">
        <span class="author-label">Hạ tầng</span>
        <span class="author-value">Render Cloud + Redis Key-Value</span>
      </div>
    </div>

    <div class="section-title">Khám Phá Endpoints & Tài Liệu</div>
    <div class="grid">
      <a href="/docs" class="card">
        <div class="card-title"><span>Interactive Docs</span> <span>↗</span></div>
        <div class="card-desc">Swagger UI cho phép test trực tiếp các endpoint, schema request và authentication.</div>
      </a>
      <a href="/health" class="card">
        <div class="card-title"><span>Liveness Probe</span> <span>↗</span></div>
        <div class="card-desc">Kiểm tra tiến trình service (/health) theo chuẩn Kubernetes & Cloud Native.</div>
      </a>
      <a href="/ready" class="card">
        <div class="card-title"><span>Readiness Probe</span> <span>↗</span></div>
        <div class="card-desc">Kiểm tra kết nối phụ thuộc tới Redis cluster trước khi nhận traffic.</div>
      </a>
      <a href="/redoc" class="card">
        <div class="card-title"><span>ReDoc Reference</span> <span>↗</span></div>
        <div class="card-desc">Giao diện tài liệu API chi tiết chuẩn OpenAPI 3.1 cho lập trình viên.</div>
      </a>
    </div>

    <div class="section-title">Hướng Dẫn Gọi API Xác Thực (POST /ask)</div>
    <div class="code-box">curl -X POST https://day12-agent-mxmr.onrender.com/ask \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: &lt;YOUR_API_KEY&gt;" \\
  -H "X-User-Id: sv-test" \\
  -d '{"question": "Kể tên các ưu điểm của kiến trúc Stateless Agent?"}'</div>

    <footer>
      VinUni AI Engineering Course • Day 12 Lab: Cloud Services & Deployment
    </footer>
  </div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# Root landing & Health/readiness probes
# ─────────────────────────────────────────────────────────────
@app.get("/", tags=["General"])
def root(request: Request):
    """Root endpoint — Trang thông tin dịch vụ hoặc JSON API summary."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=HTML_LANDING_PAGE)
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "online",
        "author": "Hoàng Minh Tuấn",
        "student_id": "2A202602758",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "ready": "/ready",
            "ask": "POST /ask",
        },
    }


@app.get("/health")
def health():
    """Liveness probe — process còn sống không?"""
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/ready")
def ready(store: ConversationStore = Depends(get_store)):
    """Readiness probe — đã sẵn sàng nhận traffic chưa?"""
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    if not store.ping():
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}


# ─────────────────────────────────────────────────────────────
# Endpoint chính
# ─────────────────────────────────────────────────────────────
@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: str = Depends(verify_api_key),
    store: ConversationStore = Depends(get_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    guard: CostGuard = Depends(get_cost_guard),
):
    """Hỏi agent một câu."""
    limiter.check(user_id)
    guard.check(user_id)
    history = store.get_history(user_id)
    result = ask_llm(payload.question, history)
    store.append(user_id, "user", payload.question)
    store.append(user_id, "assistant", result["answer"])
    guard.record(user_id, result["cost_usd"])
    log_event(
        "ask_completed",
        user_id=user_id,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost_usd=result["cost_usd"],
    )
    return {
        "answer": result["answer"],
        "user_id": user_id,
        "history_length": len(history),
        "cost_usd": result["cost_usd"],
        "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
