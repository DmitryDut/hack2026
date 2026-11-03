import json

from fastapi import APIRouter, Depends, Form, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import EntityDef
from app.services import auth, config, entities, schema_core
from app.services.sandbox import RuleError
from app.templating import render
from app.web.common import redirect

router = APIRouter()


def _entities_page(request, db, user, type_, status_code=200, **ctx):
    defs = entities.types(db)
    if type_ is None or type_ not in {d.type for d in defs}:
        type_ = defs[0].type
    return render(
        request,
        "entities.html",
        user=user,
        nav="entities",
        defs=defs,
        type_=type_,
        title=next(d.title for d in defs if d.type == type_),
        fields=schema_core.fields(db, type_),
        rows=entities.rows(db, type_),
        edit=request.query_params.get("edit"),
        status_code=status_code,
        **ctx,
    )


@router.get("/entities")
def entities_home(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _entities_page(request, db, user, request.query_params.get("type"))


@router.get("/entities/{type_}")
def entities_list(
    request: Request,
    type_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    return _entities_page(request, db, user, type_)


@router.post("/entities/{type_}")
async def entities_create(
    request: Request,
    type_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    raw = dict(await request.form())
    data, errors = entities.validate(db, type_, raw)
    if errors:
        return _entities_page(request, db, user, type_, 422, errors=errors, form=raw)
    try:
        entities.create(db, type_, data)
    except RuleError as exc:
        return _entities_page(request, db, user, type_, 422, errors={"_": str(exc)}, form=raw)
    return redirect(f"/entities/{type_}", ok="Запись добавлена")


@router.post("/entities/{type_}/{id_}")
async def entities_update(
    request: Request,
    type_: str,
    id_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    raw = dict(await request.form())
    data, errors = entities.validate(db, type_, raw)
    if errors:
        return _entities_page(request, db, user, type_, 422, errors=errors, form=raw)
    try:
        entities.update(db, type_, id_, data)
    except RuleError as exc:
        return redirect(f"/entities/{type_}", error=str(exc))
    return redirect(f"/entities/{type_}", ok="Запись сохранена")


@router.post("/entities/{type_}/{id_}/delete")
def entities_delete(
    type_: str, id_: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    try:
        entities.delete(db, type_, id_)
    except RuleError as exc:
        return redirect(f"/entities/{type_}", error=str(exc))
    return redirect(f"/entities/{type_}", ok="Запись удалена")


# ---- schema editor ---------------------------------------------------------


def _schemas_page(request, db, user, type_, status_code=200, **ctx):
    defs = db.exec(select(EntityDef).order_by(EntityDef.builtin.desc(), EntityDef.type)).all()
    if type_ not in {d.type for d in defs}:
        type_ = defs[0].type
    current = next(d for d in defs if d.type == type_)
    text = ctx.pop("text", None)
    count = (
        len(entities.rows(db, type_)) if type_ in entities.TABLES or not current.builtin else None
    )
    return render(
        request,
        "admin_schemas.html",
        user=user,
        nav="schemas",
        defs=defs,
        current=current,
        text=text
        if text is not None
        else json.dumps(current.json_schema, ensure_ascii=False, indent=2),
        count=count,
        status_code=status_code,
        **ctx,
    )


@router.get("/admin/schemas")
def schemas_home(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _schemas_page(request, db, user, request.query_params.get("type", "signature"))


@router.post("/admin/schemas/{type_}")
def schemas_save(
    request: Request,
    type_: str,
    schema_text: str = Form(""),
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    definition = db.get(EntityDef, type_)
    if definition is None:
        return redirect("/admin/schemas", error="Тип не найден")
    try:
        new = json.loads(schema_text)
    except ValueError as exc:
        return _schemas_page(
            request, db, user, type_, 422, text=schema_text, problems=[f"Некорректный JSON: {exc}"]
        )
    problems = schema_core.check_schema_edit(new, type_, definition.builtin)
    if problems:
        return _schemas_page(request, db, user, type_, 422, text=schema_text, problems=problems)
    definition.json_schema = new
    definition.title = new.get("title", definition.title)
    db.add(definition)
    db.commit()
    return redirect(
        f"/admin/schemas?type={type_}",
        ok="Схема сохранена. Формы обновятся после перезагрузки страницы.",
    )


@router.post("/admin/schemas")
def schemas_create(
    type_id: str = Form(""),
    title: str = Form(""),
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    try:
        entities.create_type(db, type_id.strip(), title.strip())
    except RuleError as exc:
        return redirect("/admin/schemas", error=str(exc))
    return redirect(
        f"/admin/schemas?type={type_id.strip()}", ok="Тип создан. Добавьте поля в схему."
    )


@router.post("/admin/schemas/{type_}/delete")
def schemas_delete(
    type_: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    try:
        entities.delete_type(db, type_)
    except RuleError as exc:
        return redirect(f"/admin/schemas?type={type_}", error=str(exc))
    return redirect("/admin/schemas", ok="Тип удалён")


@router.post("/admin/config/reload")
def reload_config(user=Depends(auth.require_operator)):
    config.reload()
    return redirect("/admin/schemas", ok="Конфигурация перечитана")
