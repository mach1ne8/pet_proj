from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes.chat import router as chat_router
from api.routes.scenarios import router as scenarios_router
from api.routes.sessions import router as sessions_router
from api.routes.profile_reports import router as profile_reports_router
from core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Negotiation Arena API",
    lifespan=lifespan,
)

app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(scenarios_router)
app.include_router(profile_reports_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
    }
