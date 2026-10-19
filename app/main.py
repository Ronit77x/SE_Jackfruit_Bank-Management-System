"""Application entry point. Owner: Member 3 (Ronit).

Run:   uvicorn app.main:app --reload     then open http://127.0.0.1:8000/docs
Each member only edits their own router/service files (see DEVELOPMENT.md); this file rarely changes.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (makes sure all tables are registered)
from app.database import Base, engine
from app.routers import accounts, admin, auth, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Bank Management System", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(admin.router)


@app.get("/health", tags=["platform"])
def health():
    """Health check (BMS-NF-002)."""
    return {"status": "ok"}
