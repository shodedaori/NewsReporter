from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.models import Item


class BaseSourcePlugin(ABC):
    section: str
    name: str

    @abstractmethod
    def fetch(self, since: datetime, until: datetime, config: dict) -> list[Item]:
        raise NotImplementedError
