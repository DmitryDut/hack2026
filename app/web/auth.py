from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.services import auth, config
from app.templating import render

router = APIRouter()


@router.get("/")
def index(request: Request):
    user = auth.current_user(request)
    if not user:
        return RedirectResponse("/login", 303)
    return RedirectResponse("/operator" if user["role"] == "operator" else "/cabinet", 303)


@router.get("/login")
def login_page(request: Request):
    cfg = config.load("accounts")
    return render(
        request,
        "login.html",
        demo=cfg["accounts"] if cfg.get("show_demo_hint") else [],
        info=request.query_params.get("info"),
    )


@router.post("/login")
def login(request: Request, login: str = Form(""), password: str = Form("")):
    account = auth.authenticate(login.strip(), password)
    if account is None:
        cfg = config.load("accounts")
        return render(
            request,
            "login.html",
            status_code=401,
            error="Неверный логин или пароль",
            login=login,
            demo=cfg["accounts"] if cfg.get("show_demo_hint") else [],
        )
    response = RedirectResponse("/operator" if account["role"] == "operator" else "/cabinet", 303)
    response.set_cookie(auth.COOKIE, auth.issue_session(account), httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", 303)
    response.delete_cookie(auth.COOKIE)
    response.delete_cookie("qod_embed")
    return response
