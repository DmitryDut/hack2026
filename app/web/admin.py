import json

from fastapi import APIRouter, Depends, Form, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import Duration, EntityDef, Service, Tariff
from app.services import auth, config, entities, field_editor, pricing, schema_core
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
        nav="admin",
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
    if type_ in entities.TABLES:
        raw[entities.TABLES[type_][1]] = (
            id_  # the key field is shown disabled, so it is not submitted
        )
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
        nav="admin",
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


# ---- administration hub: tariffs, durations, traffic passport ------------------

PAGES = {"tariff": "/admin/tariffs", "duration": "/admin/durations"}
FIELD_PAGES = {"signature": "/admin/passport", "service": "/admin/service-fields"}


@router.get("/admin")
def admin_home(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    custom = [d for d in db.exec(select(EntityDef)) if not d.builtin]
    return render(
        request,
        "admin_home.html",
        user=user,
        nav="admin",
        custom=custom,
        tariffs=len(entities.rows(db, "tariff")),
        durations=len(entities.rows(db, "duration")),
        sig_fields=len(field_editor.describe(db, "signature")),
        svc_fields=len(field_editor.describe(db, "service")),
    )


def _dict_page(request, db, user, type_, status_code=200, **ctx):
    rows = entities.rows(db, type_)
    column = Service.tariff_code if type_ == "tariff" else Service.duration_code
    usage = {r["id"]: len(db.exec(select(Service).where(column == r["id"])).all()) for r in rows}
    extra = {}
    if type_ == "tariff":
        tariffs = db.exec(select(Tariff).order_by(Tariff.bitrate_mbps)).all()
        durations = db.exec(select(Duration).order_by(Duration.hours)).all()
        extra["durations"] = durations
        extra["matrix"] = [(t, [pricing.price(t, d) for d in durations]) for t in tariffs]
        extra["factors"] = config.load("pricing")["factors"]
    return render(
        request,
        "admin_dict.html",
        user=user,
        nav="admin",
        type_=type_,
        title="Градации и тарифы" if type_ == "tariff" else "Сроки и коэффициенты",
        fields=schema_core.fields(db, type_),
        rows=rows,
        usage=usage,
        edit=request.query_params.get("edit"),
        status_code=status_code,
        **extra,
        **ctx,
    )


@router.get("/admin/tariffs")
def admin_tariffs(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _dict_page(request, db, user, "tariff")


@router.get("/admin/durations")
def admin_durations(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _dict_page(request, db, user, "duration")


@router.post("/admin/data/{type_}")
async def data_create(
    request: Request,
    type_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    raw = dict(await request.form())
    data, errors = entities.validate(db, type_, raw)
    if not errors:
        try:
            entities.create(db, type_, data)
        except RuleError as exc:
            errors = {"_": str(exc)}
    if errors:
        return _dict_page(request, db, user, type_, 422, errors=errors, form=raw)
    return redirect(PAGES[type_], ok="Запись добавлена")


@router.post("/admin/data/{type_}/{id_}")
async def data_update(
    request: Request,
    type_: str,
    id_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    raw = dict(await request.form())
    raw["code"] = id_
    data, errors = entities.validate(db, type_, raw)
    if errors:
        return _dict_page(request, db, user, type_, 422, errors=errors, form=raw)
    try:
        entities.update(db, type_, id_, data)
    except RuleError as exc:
        return redirect(PAGES[type_], error=str(exc))
    return redirect(PAGES[type_], ok="Изменения сохранены")


@router.post("/admin/data/{type_}/{id_}/toggle")
def data_toggle(
    type_: str, id_: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    row = db.get(Tariff, id_) if type_ == "tariff" else None
    if row is None:
        return redirect(PAGES.get(type_, "/admin"), error="Запись не найдена")
    row.status = "INACTIVE" if row.status == "ACTIVE" else "ACTIVE"
    db.add(row)
    db.commit()
    note = (
        "Тариф скрыт у партнёров" if row.status == "INACTIVE" else "Тариф снова доступен партнёрам"
    )
    return redirect(PAGES[type_], ok=note)


@router.post("/admin/data/{type_}/{id_}/delete")
def data_delete(
    type_: str, id_: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    try:
        entities.delete(db, type_, id_)
    except RuleError as exc:
        return redirect(PAGES[type_], error=str(exc))
    return redirect(PAGES[type_], ok="Запись удалена")


def _fields_page(request, db, user, type_, status_code=200, **ctx):
    return render(
        request,
        "admin_fields.html",
        user=user,
        nav="admin",
        type_=type_,
        base=FIELD_PAGES[type_],
        title="Паспорт трафика" if type_ == "signature" else "Поля услуги",
        rows=field_editor.describe(db, type_),
        types=field_editor.TYPES,
        formats=field_editor.FORMATS,
        edit=request.query_params.get("edit"),
        status_code=status_code,
        **ctx,
    )


@router.get("/admin/passport")
def admin_passport(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _fields_page(request, db, user, "signature")


@router.get("/admin/service-fields")
def admin_service_fields(
    request: Request, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    return _fields_page(request, db, user, "service")


@router.post("/admin/fields/{type_}")
async def field_add(
    request: Request,
    type_: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    form = dict(await request.form())
    form["required"] = form.get("required") == "on"
    try:
        field_editor.add_field(db, type_, form)
    except RuleError as exc:
        return _fields_page(request, db, user, type_, 422, error=str(exc), form=form)
    return redirect(FIELD_PAGES[type_], ok="Поле добавлено — оно сразу видно в формах партнёра")


@router.post("/admin/fields/{type_}/{name}")
async def field_update(
    request: Request,
    type_: str,
    name: str,
    user=Depends(auth.require_operator),
    db: Session = Depends(get_session),
):
    form = dict(await request.form())
    form["required"] = form.get("required") == "on"
    try:
        field_editor.update_field(db, type_, name, form)
    except RuleError as exc:
        return redirect(FIELD_PAGES[type_], error=str(exc))
    return redirect(FIELD_PAGES[type_], ok="Поле сохранено")


@router.post("/admin/fields/{type_}/{name}/delete")
def field_delete(
    type_: str, name: str, user=Depends(auth.require_operator), db: Session = Depends(get_session)
):
    try:
        field_editor.delete_field(db, type_, name)
    except RuleError as exc:
        return redirect(FIELD_PAGES[type_], error=str(exc))
    return redirect(FIELD_PAGES[type_], ok="Поле удалено")
