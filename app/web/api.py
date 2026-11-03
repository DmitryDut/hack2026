from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.db import get_session
from app.models import Partner
from app.services import auth, export

router = APIRouter(prefix="/api/v1")


@router.get("/partners/{partner_id}/export")
def partner_export(request: Request, partner_id: str, db: Session = Depends(get_session)):
    user = auth.current_user(request)
    if not user:
        raise HTTPException(401, "Требуется вход")
    if (user["role"] == "partner" and user["partner_id"] != partner_id) or not db.get(
        Partner, partner_id
    ):
        raise HTTPException(404, "Партнёр не найден")
    return export.build(db, partner_id)
