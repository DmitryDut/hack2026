from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.services.auth import NeedLogin, current_user
from app.templating import render
from app.web import admin, api, auth, cabinet, operator, subscriber

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Качество связи по требованию (POC)", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
for module in (auth, cabinet, operator, subscriber, admin, api):
    app.include_router(module.router)


@app.exception_handler(NeedLogin)
async def need_login(_: Request, exc: NeedLogin):
    return RedirectResponse(exc.url, 303)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_ui")
def ui_sample(request: Request):
    return render(request, "ui.html", user=current_user(request))
