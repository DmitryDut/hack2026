from app.models import ServiceState


def priority_view(state: ServiceState | None) -> dict:
    """off | on: the service is either switched on (applied) or off. See docs/SPEC.md D16."""
    if state is None or state.status != "applied":
        return {"state": "off"}
    return {"state": "on", "since": state.applied_at}
