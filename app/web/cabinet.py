import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    Duration,
    EventLog,
    NetworkRequest,
    Offer,
    Service,
    ServiceState,
    Signature,
    Tariff,
)
from app.services import (
    auth,
    export,
    gates,
    offers,
    pricing,
    sandbox,
    schema_core,
    signatures,
)
from app.services.sandbox import RuleError
from app.templating import render
from app.web.common import own_service, parse_details, redirect, view

router = APIRouter(prefix="/cabinet")


def _tab_url(service_id: str, tab: str) -> str:
    return f"/cabinet/services/{service_id}?tab={tab}"


@router.get("")
def dashboard(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    services = db.exec(
        select(Service).where(Service.partner_id == user["partner_id"]).order_by(Service.name)
    ).all()
    items = [view(db, s) for s in services]
    on = [i for i in items if i["priority"]["state"] == "on"]
    running = sum(i["price"] or 0 for i in on)
    total = sum(i["price"] or 0 for i in items)
    signatures_on = sum(i["sig_count"] for i in on)
    return render(
        request,
        "cabinet/dashboard.html",
        user=user,
        nav="cabinet",
        items=items,
        on_count=len(on),
        total_count=len(items),
        running=running,
        total=total,
        drafts=total - running,
        signatures_on=signatures_on,
    )


@router.get("/services/new")
def new_service_page(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    return render(
        request,
        "cabinet/new_service.html",
        user=user,
        nav="cabinet",
        fields=schema_core.fields(db, "service"),
        values={},
        errors={},
    )


@router.post("/services/new")
async def create_service(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    sch = schema_core.schema(db, "service")
    raw = dict(await request.form())
    data = schema_core.coerce_all(sch, raw)
    errors = schema_core.validate(sch, data)
    if errors:
        return render(
            request,
            "cabinet/new_service.html",
            user=user,
            nav="cabinet",
            status_code=422,
            fields=schema_core.fields(db, "service"),
            values=raw,
            errors=errors,
        )
    core, extra = schema_core.split("service", data)
    numbers = [
        int(s.id.split("-")[-1]) for s in db.exec(select(Service)) if s.id.split("-")[-1].isdigit()
    ]
    service = Service(
        id=f"svc-{max(numbers, default=0) + 1}",
        partner_id=user["partner_id"],
        name=core["name"],
        description=core.get("description", ""),
        extra=extra,
    )
    db.add(service)
    db.add(ServiceState(service_id=service.id))
    db.commit()
    return redirect(_tab_url(service.id, "data"), ok="Услуга создана. Добавьте сигнатуры трафика.")


@router.get("/services/{service_id}")
def service_card(
    request: Request,
    service_id: str,
    tab: str = "data",
    edit: str | None = None,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    return _render_card(request, db, user, service_id, tab, edit)


def _render_card(request, db, user, service_id, tab="data", edit=None, status_code=200, **ctx):
    service = own_service(db, user, service_id)
    v = view(db, service)
    status = v["state"].status
    sigs = sandbox.signatures(db, service.id)
    tabs = gates.tabs()
    locked = {tab_id: gates.reason(db, service, tab_id) for tab_id, _ in tabs}
    if tab not in dict(tabs) or locked.get(tab):
        tab = tabs[0][0]
    tariffs = db.exec(
        select(Tariff).where(Tariff.status == "ACTIVE").order_by(Tariff.bitrate_mbps)
    ).all()
    durations = db.exec(select(Duration).order_by(Duration.hours)).all()
    extra = {}
    if tab == "tariff":
        extra["rows"] = [
            {
                "t": t,
                "base": t.bitrate_mbps * 100 * t.price_multiplier,
                "price": pricing.price(t, v["duration"]) if v["duration"] else None,
            }
            for t in tariffs
        ]
        if v["tariff"] and v["duration"]:
            extra["breakdown"] = pricing.breakdown(v["tariff"], v["duration"])
    if tab == "test":
        step_rows = {s.signature_id: s for s in sandbox.steps(db, service.id)}
        extra["step_rows"] = [(sig, step_rows.get(sig.id)) for sig in sigs if sig.id in step_rows]
        extra["failed_step"] = next((s for s in step_rows.values() if s.result == "error"), None)
        extra["summary"] = sandbox.metrics_summary(list(step_rows.values()))
    if tab == "launch":
        extra["summary"] = sandbox.metrics_summary(sandbox.steps(db, service.id))
        if status == "passed":
            extra["payload"] = json.dumps(
                sandbox.preview(db, service), ensure_ascii=False, indent=2
            )
        extra["session_net"] = db.exec(
            select(NetworkRequest)
            .where(
                NetworkRequest.partner_id == service.partner_id,
                NetworkRequest.kind == "gsma_session",
            )
            .order_by(NetworkRequest.id.desc())
        ).first()
    return render(
        request,
        "cabinet/service.html",
        user=user,
        nav="cabinet",
        v=v,
        tab=tab,
        tabs=tabs,
        price_gates_test="price_confirmed" in gates.gates("test"),
        locked=locked,
        sigs=sigs,
        edit=edit,
        sig_fields=schema_core.fields(db, "signature"),
        svc_fields=schema_core.fields(db, "service"),
        value_of=schema_core.value_of,
        tariffs=tariffs,
        durations=durations,
        status_code=status_code,
        **extra,
        **ctx,
    )


@router.post("/services/{service_id}/signatures")
async def add_signature(
    request: Request,
    service_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    service = own_service(db, user, service_id)
    raw = dict(await request.form())
    data, errors = signatures.validate(db, service.id, raw)
    if errors:
        return _render_card(
            request, db, user, service_id, "data", status_code=422, sig_errors=errors, sig_form=raw
        )
    try:
        signatures.add(db, service, data)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "data"), error=str(exc))
    return redirect(_tab_url(service_id, "data"), ok="Сигнатура добавлена")


@router.post("/services/{service_id}/signatures/{sig_id}")
async def update_signature(
    request: Request,
    service_id: str,
    sig_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    service = own_service(db, user, service_id)
    sig = db.get(Signature, sig_id)
    if sig is None or sig.service_id != service.id:
        return redirect(_tab_url(service_id, "data"), error="Сигнатура не найдена")
    raw = dict(await request.form())
    data, errors = signatures.validate(db, service.id, raw, exclude_id=sig_id)
    if errors:
        return _render_card(
            request,
            db,
            user,
            service_id,
            "data",
            edit=sig_id,
            status_code=422,
            sig_errors=errors,
            sig_form=raw,
        )
    try:
        signatures.update(db, service, sig, data)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "data"), error=str(exc))
    reset = sandbox.state_of(db, service).status == "draft"
    return redirect(
        _tab_url(service_id, "data"),
        ok="Сигнатура изменена" + (". Тестирование сброшено" if reset else ""),
    )


@router.post("/services/{service_id}/params")
async def update_params(
    request: Request,
    service_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    service = own_service(db, user, service_id)
    sch = schema_core.schema(db, "service")
    raw = dict(await request.form())
    data = schema_core.coerce_all(sch, raw)
    errors = schema_core.validate(sch, data)
    if errors:
        return _render_card(
            request, db, user, service_id, "data", status_code=422, svc_errors=errors, svc_form=raw
        )
    try:
        sandbox.guard_change(db, service)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "data"), error=str(exc))
    core, extra = schema_core.split("service", data)
    service.name, service.description = core.get("name", service.name), core.get("description", "")
    service.extra = extra
    db.add(service)
    db.commit()
    sandbox.log(db, service, "service_updated", fields=sorted(data))
    db.commit()
    return redirect(_tab_url(service_id, "data"), ok="Параметры услуги сохранены")


@router.post("/services/{service_id}/signatures/{sig_id}/delete")
def delete_signature(
    service_id: str,
    sig_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    service = own_service(db, user, service_id)
    sig = db.get(Signature, sig_id)
    try:
        if sig and sig.service_id == service.id:
            signatures.delete(db, service, sig)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "data"), error=str(exc))
    return redirect(_tab_url(service_id, "data"), ok="Сигнатура удалена")


@router.post("/services/{service_id}/delete")
def delete_service(
    service_id: str, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    service = own_service(db, user, service_id)
    try:
        sandbox.guard_change(db, service)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "data"), error=str(exc))
    for model in (Signature, sandbox.TestStep):
        for row in db.exec(select(model).where(model.service_id == service.id)):
            db.delete(row)
    state = db.get(ServiceState, service.id)
    if state:
        db.delete(state)
    db.delete(service)
    db.commit()
    return redirect("/cabinet", ok="Услуга удалена")


@router.post("/services/{service_id}/tariff")
def set_tariff(
    service_id: str,
    tariff_code: str = Form(""),
    duration_code: str = Form(""),
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    service = own_service(db, user, service_id)
    try:
        sandbox.set_tariff(db, service, tariff_code, duration_code)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "tariff"), error=str(exc))
    return redirect(_tab_url(service_id, "tariff"), ok="Тариф и срок применены. Подтвердите цену.")


@router.post("/services/{service_id}/confirm-price")
def confirm_price(
    service_id: str, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    service = own_service(db, user, service_id)
    v = view(db, service)
    try:
        sandbox.confirm_price(db, service, v["price"])
    except RuleError as exc:
        return redirect(_tab_url(service_id, "tariff"), error=str(exc))
    return redirect(
        _tab_url(service_id, "tariff"), ok="Цена подтверждена. Можно переходить к тестированию."
    )


def _action(service_id: str, tab: str, fn, ok: str, user, db, *args):
    service = own_service(db, user, service_id)
    try:
        fn(db, service, *args)
    except RuleError as exc:
        return redirect(_tab_url(service_id, tab), error=str(exc))
    return redirect(_tab_url(service_id, tab), ok=ok)


@router.post("/services/{service_id}/test/start")
def test_start(
    service_id: str, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    return _action(service_id, "test", sandbox.start, "Тестирование начато", user, db)


@router.post("/services/{service_id}/test/check/{sig_id}")
def test_check(
    service_id: str,
    sig_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    return _action(service_id, "test", sandbox.check, "Сигнатура проверена", user, db, sig_id)


@router.post("/services/{service_id}/test/confirm/{sig_id}")
def test_confirm(
    service_id: str,
    sig_id: str,
    user=Depends(auth.require_partner),
    db: Session = Depends(get_session),
):
    return _action(service_id, "test", sandbox.confirm, "Результат подтверждён", user, db, sig_id)


@router.post("/services/{service_id}/test/back")
def test_back(
    service_id: str, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    service = own_service(db, user, service_id)
    try:
        sandbox.back(db, service)
    except RuleError as exc:
        return redirect(_tab_url(service_id, "test"), error=str(exc))
    return redirect(
        _tab_url(service_id, "data"),
        ok="Вы вернулись к настройке. Исправьте сигнатуру и начните тест заново.",
    )


@router.post("/services/{service_id}/apply")
def apply(service_id: str, user=Depends(auth.require_partner), db: Session = Depends(get_session)):
    return _action(service_id, "launch", sandbox.apply, "Приоритет включён", user, db)


@router.get("/offer")
def offer_page(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    table = offers.table(db, user["partner_id"])
    confirmed = sum(1 for s in offers.services_of(db, user["partner_id"]) if s.price_confirmed)
    return render(
        request, "cabinet/offer.html", user=user, nav="offer", table=table, confirmed=confirmed
    )


@router.post("/offer/variants")
def save_variant(
    name: str = Form(""), user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    try:
        offers.save_variant(db, user["partner_id"], name)
    except RuleError as exc:
        return redirect("/cabinet/offer", error=str(exc))
    return redirect("/cabinet/offer", ok="Вариант сохранён")


def _own_offer(db, user, offer_id: int):
    offer = db.get(Offer, offer_id)
    if offer is None or offer.partner_id != user["partner_id"]:
        raise HTTPException(404, "Вариант не найден")
    return offer


@router.post("/offer/variants/{offer_id}/apply")
def apply_variant(
    offer_id: int, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    done, skipped = offers.apply(db, user["partner_id"], _own_offer(db, user, offer_id))
    note = f"Вариант применён к услугам: {done}. Подтвердите цену заново."
    if skipped:
        return redirect("/cabinet/offer", ok=note + f" Пропущено (приоритет включён): {skipped}.")
    return redirect("/cabinet/offer", ok=note)


@router.post("/offer/variants/{offer_id}/delete")
def delete_variant(
    offer_id: int, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    db.delete(_own_offer(db, user, offer_id))
    db.commit()
    return redirect("/cabinet/offer", ok="Вариант удалён")


@router.get("/export")
def export_page(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    payload = export.build(db, user["partner_id"])
    return render(
        request,
        "cabinet/export.html",
        user=user,
        nav="export",
        payload=json.dumps(payload, ensure_ascii=False, indent=2),
        count=len(payload["services"]),
    )


@router.get("/journal")
def journal(
    request: Request, user=Depends(auth.require_partner), db: Session = Depends(get_session)
):
    return _journal(request, db, user, user["partner_id"], "/cabinet/journal")


def _journal(request, db, user, partner_id, base):
    ev = select(EventLog).order_by(EventLog.id.desc()).limit(120)
    nr = select(NetworkRequest).order_by(NetworkRequest.id.desc()).limit(60)
    if partner_id:
        ev, nr = (
            ev.where(EventLog.partner_id == partner_id),
            nr.where(NetworkRequest.partner_id == partner_id),
        )
    names = {s.id: s.name for s in db.exec(select(Service))}
    events = [(e, parse_details(e.details)) for e in db.exec(ev)]
    return render(
        request,
        "journal.html",
        user=user,
        nav="journal",
        events=events,
        calls=db.exec(nr).all(),
        names=names,
    )
