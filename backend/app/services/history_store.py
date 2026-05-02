from typing import Dict, List

from app.models.schemas import Look


class HistoryStore:
    def __init__(self) -> None:
        self._by_user: Dict[str, List[Look]] = {}

    def save(self, user_id: str, looks: List[Look]) -> None:
        self._by_user.setdefault(user_id, [])
        self._by_user[user_id].extend(looks)

    def get(self, user_id: str) -> List[Look]:
        return self._by_user.get(user_id, [])


history_store = HistoryStore()
