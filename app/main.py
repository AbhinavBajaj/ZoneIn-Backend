"""FastAPI app entrypoint."""
import logging
import time
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api import auth, health, me, reports, leaderboard

logging.getLogger("app").setLevel(logging.INFO)

app = FastAPI(title="ZoneIn Backend", description="Aggregated focus session reports (privacy-first)")


@app.middleware("http")
async def log_every_request(request: Request, call_next: Callable):
    """Log every request to stdout so we always see when POST /reports hits the server."""
    client = request.client.host if request.client else "?"
    method = request.method
    path = request.url.path
    print(f"[Backend] {method} {path} <- {client}", flush=True)
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"[Backend] {method} {path} -> {response.status_code} ({elapsed:.0f}ms)", flush=True)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(reports.router)
app.include_router(leaderboard.router)
