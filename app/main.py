"""Application entry point. Owner: Member 3 (Ronit).

Run:   uvicorn app.main:app --reload     then open http://127.0.0.1:8000/docs
Each member only edits their own router/service files (see DEVELOPMENT.md); this file rarely changes.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


from fastapi import FastAPI

from app import models  # noqa: F401  (makes sure all tables are registered)
from app.database import Base, engine
from app.errors import register_error_handlers
from app.routers import accounts, admin, auth, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Bank Management System", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(admin.router)

app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/index.html")

@app.get("/health", tags=["platform"])
def health():
    """Health check (BMS-NF-002)."""
    return {"status": "ok"}
