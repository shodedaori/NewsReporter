from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import requests

from src.core.models import Item
from src.core.summarizer import Summarizer
from src.core.utils import clip_text, strip_html

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class LLMSummaryConfig:
    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 20
    max_input_chars: int = 4000
    max_output_chars: int = 280


class NewsLLMSummarizer:
    def __init__(
        self,
        prompt_system: str,
        prompt_user_template: str,
        config: LLMSummaryConfig,
        fallback: Summarizer | None = None,
        session: requests.Session | None = None,
    ):
        self.prompt_system = prompt_system
        self.prompt_user_template = prompt_user_template
        self.config = config
        self.fallback = fallback or Summarizer()
        self.session = session or requests.Session()

    def summarize_item(self, item: Item) -> Item:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return self.fallback.summarize_item(item)

        content = strip_html(item.summary_raw)[: self.config.max_input_chars]
        prompt_user = self.prompt_user_template.format(
            title=item.title,
            url=item.url,
            source=item.source,
            content=content,
        )

        try:
            payload = self._call_llm(api_key=api_key, prompt_user=prompt_user)
            parsed = self._parse_payload(payload)
            tldr = clip_text(parsed.get("tldr", "").strip(), self.config.max_output_chars)
            keypoints = self._clip_list(parsed.get("keypoints", []), 5)
            takeaways = self._clip_list(parsed.get("takeaways", []), 3)
            if not tldr:
                return self.fallback.summarize_item(item)
            item.summary_short = tldr
            item.signals["keypoints"] = keypoints
            item.signals["takeaways"] = takeaways
            item.signals["summary_mode"] = "llm"
            return item
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("LLM summarize failed, fallback to extractive: %s", exc)
            return self.fallback.summarize_item(item)

    def summarize_items(self, items: list[Item]) -> list[Item]:
        return [self.summarize_item(item) for item in items]

    def _call_llm(self, api_key: str, prompt_user: str) -> str:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        endpoint = f"{base_url}/chat/completions"
        response = self.session.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self.prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                "temperature": 0.2,
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                chunks = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = str(part.get("text", "")).strip()
                        if text:
                            chunks.append(text)
                if chunks:
                    return "\n".join(chunks)
        return json.dumps(data, ensure_ascii=False)

    def _parse_payload(self, payload: str) -> dict:
        # Prefer direct JSON response; if model wrapped text, extract first JSON object.
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            start = payload.find("{")
            end = payload.rfind("}")
            if start >= 0 and end > start:
                return json.loads(payload[start : end + 1])
            raise

    @staticmethod
    def _clip_list(values: list, limit: int) -> list[str]:
        result: list[str] = []
        for value in values[:limit]:
            text = str(value).strip()
            if text:
                result.append(text)
        return result


def build_news_summarizer(app_config: dict, prompts_config: dict) -> Summarizer | NewsLLMSummarizer:
    summarizer_config = app_config.get("summarizer", {})
    mode = str(summarizer_config.get("mode", "extractive")).lower()
    fallback = Summarizer()
    if mode != "llm":
        return fallback

    llm_config = summarizer_config.get("llm", {})
    config = LLMSummaryConfig(
        model=str(llm_config.get("model", "gpt-4.1-mini")),
        timeout_seconds=int(llm_config.get("timeout_seconds", 20)),
        max_input_chars=int(llm_config.get("max_input_chars", 4000)),
        max_output_chars=int(llm_config.get("max_output_chars", 280)),
    )
    return NewsLLMSummarizer(
        prompt_system=str(prompts_config.get("news_llm_summary_system", "")),
        prompt_user_template=str(prompts_config.get("news_llm_summary_user", "")),
        config=config,
        fallback=fallback,
    )
