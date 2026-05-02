from fastapi import APIRouter

from app.models.schemas import Look
from app.services.history_store import history_store

router = APIRouter()


@router.get("/history/{user_id}", response_model=list[Look])
def get_history(user_id: str) -> list[Look]:
    return history_store.get(user_id)
