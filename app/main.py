from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.services.auth import NeedLogin, current_user
from app.templating import render
from app.web import admin, api, auth, cabinet, gsma, landing, operator, px, subscriber

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Качество связи по требованию (POC)", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
for module in (auth, cabinet, operator, subscriber, admin, api, px, gsma, landing):
    app.include_router(module.router)


@app.middleware("http")
async def frame_policy(request: Request, call_next):
    """The cabinet may be framed only by pages of this origin (the PX storefront mock)."""
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
    return response


@app.exception_handler(NeedLogin)
async def need_login(_: Request, exc: NeedLogin):
    return RedirectResponse(exc.url, 303)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_ui")
def ui_sample(request: Request):
    return render(request, "ui.html", user=current_user(request))
