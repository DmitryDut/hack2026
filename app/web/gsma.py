from fastapi import APIRouter, Request

from app.mocks import gsma

router = APIRouter(prefix="/mock-gsma", tags=["mock-gsma"])


@router.post("/validate")
async def validate(request: Request):
    return gsma.validate(await request.json())


@router.post("/qod/sessions", status_code=201)
async def create_session(request: Request):
    return gsma.create_session(await request.json())
