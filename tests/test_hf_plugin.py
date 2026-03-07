from __future__ import annotations

from src.sections.huggingface.plugins.huggingface import HuggingFacePlugin


class FakeInfo:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeHfApi:
    def __init__(self) -> None:
        self.model_kwargs = {}
        self.dataset_kwargs = {}

    def list_models(self, **kwargs):
        self.model_kwargs = kwargs
        return [
            FakeInfo(
                id="org/model-a",
                likes=100,
                downloads=8000,
                tags=["text-generation"],
                card_data={"likes7d": 40, "license": "apache-2.0", "pipeline_tag": "text-generation", "language": ["en"]},
            )
        ]

    def list_datasets(self, **kwargs):
        self.dataset_kwargs = kwargs
        return [
            FakeInfo(
                id="org/dataset-a",
                likes=50,
                downloads=2000,
                tags=["dataset"],
                card_data={"likes7d": 10, "license": "cc-by-4.0", "language": ["en"], "description": "dataset desc"},
            )
        ]


def test_hf_plugin_fetch_maps_models_and_datasets() -> None:
    api = FakeHfApi()
    plugin = HuggingFacePlugin(hf_api=api)
    items = plugin.fetch(since=None, until=None, config={"sort": "trending_score", "card_data": True, "models_limit": 2, "datasets_limit": 2})

    assert len(items) == 2
    model_item = items[0]
    dataset_item = items[1]

    assert model_item.section == "hf"
    assert model_item.source == "hf_model_trending"
    assert model_item.signals["kind"] == "model"
    assert model_item.signals["rank"] == 1
    assert model_item.signals["likes_7d"] == 40
    assert model_item.signals["likes_total"] == 100

    assert dataset_item.source == "hf_dataset_trending"
    assert dataset_item.signals["kind"] == "dataset"
    assert dataset_item.signals["rank"] == 1
    assert dataset_item.signals["likes_7d"] == 10
    assert dataset_item.signals["likes_total"] == 50

    assert api.model_kwargs.get("sort") == "trending_score"
    assert api.dataset_kwargs.get("sort") == "trending_score"
