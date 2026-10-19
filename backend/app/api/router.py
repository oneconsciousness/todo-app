"""Everything under /api/v1. The Origin guard runs on every route, before the body is validated."""

from fastapi import APIRouter, Depends

from app.api.auth import auth_router
from app.api.deps import require_trusted_origin
from app.api.schemas import ErrorEnvelope
from app.api.tasks import tasks_router

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_trusted_origin)],
    responses={403: {"model": ErrorEnvelope}},
)
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
