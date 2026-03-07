from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from src.core.base_plugin import BaseSourcePlugin
from src.core.models import Item
from src.core.utils import build_dedup_key

LOGGER = logging.getLogger(__name__)


class HuggingFacePlugin(BaseSourcePlugin):
    section = "hf"
    name = "hf"
    models_source = "hf_model_trending"
    datasets_source = "hf_dataset_trending"

    def __init__(self, hf_api: Any | None = None, session: requests.Session | None = None, timeout: int = 20):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.hf_api = hf_api or self._build_hf_api()

    def fetch(self, since: datetime, until: datetime, config: dict) -> list[Item]:
        del since, until
        models_limit = max(1, int(config.get("models_limit", 40)))
        datasets_limit = max(1, int(config.get("datasets_limit", 40)))
        sort = str(config.get("sort", "trending_score"))
        use_card_data = bool(config.get("card_data", True))

        model_rows = self._fetch_models(limit=models_limit, sort=sort, use_card_data=use_card_data)
        dataset_rows = self._fetch_datasets(limit=datasets_limit, sort=sort, use_card_data=use_card_data)

        items: list[Item] = []
        for rank, row in enumerate(model_rows, start=1):
            item = self._to_item(row=row, kind="model", rank=rank)
            if item:
                items.append(item)
        for rank, row in enumerate(dataset_rows, start=1):
            item = self._to_item(row=row, kind="dataset", rank=rank)
            if item:
                items.append(item)
        return items

    def _fetch_models(self, limit: int, sort: str, use_card_data: bool) -> list[Any]:
        if self.hf_api:
            try:
                return list(self._list_models_with_hf_api(limit=limit, sort=sort, use_card_data=use_card_data))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("HF list_models via HfApi failed, fallback to REST: %s", exc)
        return self._list_models_with_rest(limit=limit, sort=sort)

    def _fetch_datasets(self, limit: int, sort: str, use_card_data: bool) -> list[Any]:
        if self.hf_api:
            try:
                return list(self._list_datasets_with_hf_api(limit=limit, sort=sort, use_card_data=use_card_data))
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("HF list_datasets via HfApi failed, fallback to REST: %s", exc)
        return self._list_datasets_with_rest(limit=limit, sort=sort)

    def _list_models_with_hf_api(self, limit: int, sort: str, use_card_data: bool) -> list[Any]:
        kwargs: dict[str, Any] = {"limit": limit, "sort": sort}
        if use_card_data:
            kwargs["cardData"] = True
        try:
            return list(self.hf_api.list_models(**kwargs))
        except TypeError:
            # Newer huggingface_hub may require `expand=["cardData"]`.
            if use_card_data:
                kwargs.pop("cardData", None)
                kwargs["expand"] = ["cardData"]
            return list(self.hf_api.list_models(**kwargs))

    def _list_datasets_with_hf_api(self, limit: int, sort: str, use_card_data: bool) -> list[Any]:
        kwargs: dict[str, Any] = {"limit": limit, "sort": sort}
        if use_card_data:
            kwargs["cardData"] = True
        try:
            return list(self.hf_api.list_datasets(**kwargs))
        except TypeError:
            if use_card_data:
                kwargs.pop("cardData", None)
                kwargs["expand"] = ["cardData"]
            return list(self.hf_api.list_datasets(**kwargs))

    def _list_models_with_rest(self, limit: int, sort: str) -> list[dict]:
        params = {"limit": str(limit), "sort": self._rest_sort(sort), "direction": "-1", "full": "true", "config": "true"}
        response = self.session.get(
            "https://huggingface.co/api/models",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": "NewsReporter/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _list_datasets_with_rest(self, limit: int, sort: str) -> list[dict]:
        params = {"limit": str(limit), "sort": self._rest_sort(sort), "direction": "-1", "full": "true"}
        response = self.session.get(
            "https://huggingface.co/api/datasets",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": "NewsReporter/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def _to_item(self, row: Any, kind: str, rank: int) -> Item | None:
        repo_id = str(self._get(row, "id") or self._get(row, "modelId") or "").strip()
        if not repo_id:
            return None

        source = self.models_source if kind == "model" else self.datasets_source
        url = f"https://huggingface.co/{repo_id}" if kind == "model" else f"https://huggingface.co/datasets/{repo_id}"
        card_data = self._to_dict(self._get(row, "card_data") or self._get(row, "cardData"))

        tags = self._to_list(self._get(row, "tags") or card_data.get("tags"))
        summary = self._first_non_empty(
            self._get(row, "description"),
            card_data.get("description"),
            card_data.get("model_description"),
            card_data.get("summary"),
            "",
        )

        likes_total = self._to_int(self._get(row, "likes"))
        likes_7d = self._to_int(
            card_data.get("likes7d")
            or card_data.get("likes_7d")
            or self._get(row, "likes7d")
            or self._get(row, "likes_7d")
        )
        downloads = self._to_int(self._get(row, "downloads") or card_data.get("downloads"))

        signals = {
            "kind": kind,
            "rank": rank,
            "likes_total": likes_total,
            "likes_7d": likes_7d,
            "downloads": downloads,
            "tags": tags,
            "pipeline_tag": self._get(row, "pipeline_tag") or card_data.get("pipeline_tag") or "",
            "license": card_data.get("license") or "",
            "language": card_data.get("language") or [],
        }

        return Item(
            section=self.section,
            source=source,
            source_id=repo_id,
            title=repo_id,
            url=url,
            published_at=None,
            summary_raw=str(summary or "").strip(),
            tags=tags,
            signals=signals,
            dedup_key=build_dedup_key(
                source=source,
                source_id=repo_id,
                url=url,
                title=repo_id,
                published_at=None,
                section=self.section,
            ),
        )

    @staticmethod
    def _build_hf_api() -> Any | None:
        try:
            from huggingface_hub import HfApi

            return HfApi()
        except Exception:
            return None

    @staticmethod
    def _rest_sort(sort_value: str) -> str:
        normalized = sort_value.strip().lower()
        if normalized == "trending_score":
            return "trendingScore"
        return sort_value

    @staticmethod
    def _get(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            return value.get(key)
        return getattr(value, key, None)

    @staticmethod
    def _to_dict(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        if value is None:
            return {}
        for method_name in ("to_dict", "dict"):
            method = getattr(value, method_name, None)
            if callable(method):
                try:
                    result = method()
                    if isinstance(result, dict):
                        return result
                except Exception:
                    return {}
        return {}

    @staticmethod
    def _to_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return []

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _first_non_empty(*values: Any) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""
