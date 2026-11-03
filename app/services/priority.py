from app.models import ServiceState, now


def _remaining(seconds: int) -> str:
    hours, rest = divmod(max(seconds, 0), 3600)
    return f"{hours} ч {rest // 60} мин"


def priority_view(state: ServiceState | None) -> dict:
    """off | on | expired — see docs/SPEC.md D16. Derived at read time, DB is not touched."""
    if state is None or state.status != "applied" or state.expires_at is None:
        return {"state": "off"}
    left = int((state.expires_at - now()).total_seconds())
    if left > 0:
        return {
            "state": "on",
            "until": state.expires_at,
            "since": state.applied_at,
            "remaining": _remaining(left),
        }
    return {"state": "expired", "until": state.expires_at}
