from __future__ import annotations

from datetime import date

from src.core.models import Item
from src.core.summarizer import Summarizer
from src.core.utils import build_dedup_key
from src.sections.huggingface.pipeline import HuggingFaceSectionPipeline
from src.sections.huggingface.scorer import HuggingFaceScorer


class FakeHFPlugin:
    section = "hf"
    name = "hf"

    def fetch(self, since, until, config):  # noqa: ANN001, ANN201
        del since, until, config
        return [
            _build_item("hf_model_trending", "org/model-1", "model", 1, likes_7d=10),
            _build_item("hf_model_trending", "org/model-2", "model", 2, likes_7d=300),
            _build_item("hf_model_trending", "org/model-3", "model", 3, likes_7d=200),
            _build_item("hf_dataset_trending", "org/data-1", "dataset", 1, likes_7d=5),
            _build_item("hf_dataset_trending", "org/data-2", "dataset", 2, likes_7d=500),
            _build_item("hf_dataset_trending", "org/data-3", "dataset", 3, likes_7d=100),
        ]


def _build_item(source: str, source_id: str, kind: str, rank: int, likes_7d: int) -> Item:
    return Item(
        section="hf",
        source=source,
        source_id=source_id,
        title=source_id,
        url=f"https://huggingface.co/{source_id}",
        published_at=None,
        summary_raw=f"{source_id} summary",
        tags=[],
        signals={
            "kind": kind,
            "rank": rank,
            "likes_7d": likes_7d,
            "likes_total": likes_7d * 10,
            "downloads": likes_7d * 100,
        },
        dedup_key=build_dedup_key(source=source, source_id=source_id, url=f"https://huggingface.co/{source_id}", title=source_id, published_at=None, section="hf"),
    )


def test_hf_pipeline_selects_half_models_half_datasets_and_keeps_order() -> None:
    app_config = {
        "app": {"top_items": 5, "window_hours": 24},
        "scoring": {"hf": {"likes_7d_weight": 1.0, "likes_total_weight": 0.0, "downloads_weight": 0.0}},
    }
    pipeline = HuggingFaceSectionPipeline(
        app_config=app_config,
        source_config={"hf": {}},
        plugins=[FakeHFPlugin()],
        scorer=HuggingFaceScorer(app_config["scoring"]),
        summarizer=Summarizer(),
    )

    result = pipeline.run(digest_date=date(2026, 3, 7))
    selected_titles = [item.title for item in result.items]

    # top_items=5 -> each_n=2, and order follows API rank not score
    assert selected_titles == ["org/model-1", "org/model-2", "org/data-1", "org/data-2"]
    assert result.stats["selected_models_count"] == 2
    assert result.stats["selected_datasets_count"] == 2
    assert all("score" in item.signals for item in result.items)
