from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.middleware import AuthContextMiddleware
from backend.api.routes_admin import router as admin_router
from backend.api.routes_chat import router as chat_router
from backend.db.session import init_metadata_db

app = FastAPI(title="Conversational BI Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthContextMiddleware)


@app.on_event("startup")
def startup_event() -> None:
    init_metadata_db()


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


app.include_router(admin_router)
app.include_router(chat_router)
