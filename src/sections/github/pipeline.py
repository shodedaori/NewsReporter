from __future__ import annotations

from datetime import date

from src.core.base_pipeline import BaseSectionPipeline, SectionResult


class GitHubSectionPipeline(BaseSectionPipeline):
    section = "github"

    def run(self, digest_date: date) -> SectionResult:
        return SectionResult(section=self.section, items=[], stats={"item_count": 0, "unique_count": 0, "published_count": 0, "failures": 0}, generated_at="")
