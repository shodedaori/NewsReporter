from __future__ import annotations

from datetime import date

from src.core.base_pipeline import SectionResult, deduplicate_items
from src.core.publisher import Publisher
from src.core.store import Store
from src.web.renderer import Renderer


class DailyOrchestrator:
    def __init__(
        self,
        store: Store,
        renderer: Renderer,
        publisher: Publisher,
        app_config: dict,
        section_pipelines: list,
    ):
        self.store = store
        self.renderer = renderer
        self.publisher = publisher
        self.app_config = app_config
        self.section_pipelines = section_pipelines

    def run(self, digest_date: date, dry_run: bool, publish: bool) -> dict:
        print(f"[progress] orchestrator start date={digest_date.isoformat()} dry_run={dry_run} publish={publish}", flush=True)
        run_id = self.store.start_run(digest_date.isoformat(), dry_run=dry_run)
        output_root = self.app_config["paths"]["output_preview"] if dry_run or not publish else self.app_config["paths"]["output_site"]
        digest_status = "preview" if dry_run or not publish else "published"

        try:
            section_results: dict[str, SectionResult] = {}
            total_failures = 0
            total_items = 0
            total_unique = 0
            total_published = 0

            for section_pipeline in self.section_pipelines:
                print(f"[progress] run section={section_pipeline.section}", flush=True)
                result = section_pipeline.run(digest_date=digest_date)
                section_results[result.section] = result
                total_items += int(result.stats.get("item_count", 0))
                total_unique += int(result.stats.get("unique_count", 0))
                total_published += int(result.stats.get("published_count", 0))
                total_failures += int(result.stats.get("failures", 0))
                self.store.upsert_items(result.items)
                print(f"[progress] section={result.section} completed", flush=True)

            stats = {
                "item_count": total_items,
                "unique_count": total_unique,
                "published_count": total_published,
                "failures": total_failures,
                "sections": {section: result.stats for section, result in section_results.items()},
            }
            generated_at = next(iter(section_results.values())).generated_at if section_results else ""

            news_items = self._section_items_payload(section_results, "news")
            arxiv_items = self._section_items_payload(section_results, "arxiv")
            daily_context = {
                "site_name": self.app_config["app"]["site_name"],
                "page_title": f"{digest_date.isoformat()} News Digest",
                "page_description": "Latest 24-hour company news digest",
                "digest_date": digest_date.isoformat(),
                "generated_at": generated_at,
                "stats": stats,
                "items": news_items,
                "sections": {
                    "news": {"items": news_items, "stats": section_results.get("news").stats if section_results.get("news") else {}},
                    "arxiv": {"items": arxiv_items, "stats": section_results.get("arxiv").stats if section_results.get("arxiv") else {}},
                },
            }
            daily_html = self.renderer.render_daily(daily_context)
            print("[progress] daily page rendered", flush=True)

            recent_digests = self.store.list_recent_digests(limit=14, include_preview=digest_status == "preview")
            current_digest = {
                "digest_date": digest_date.isoformat(),
                "status": digest_status,
                "output_path": f"{output_root}/daily/{digest_date.isoformat()}/index.html",
                "generated_at": generated_at,
                "stats": stats,
            }
            digests = [current_digest] + [item for item in recent_digests if item["digest_date"] != current_digest["digest_date"]]
            digests = digests[:14]
            index_context = {
                "site_name": self.app_config["app"]["site_name"],
                "page_title": "NewsReporter Daily Digest",
                "page_description": "Daily static briefings from latest 24-hour news",
                "latest": digests[0] if digests else None,
                "digests": digests,
            }
            index_html = self.renderer.render_index(index_context)
            print("[progress] homepage rendered", flush=True)

            paths = self.publisher.publish(
                digest_date=digest_date.isoformat(),
                daily_html=daily_html,
                index_html=index_html,
                output_root=output_root,
                static_root=self.app_config["paths"]["static"],
            )
            print(f"[progress] publish done root={paths['root']}", flush=True)
            self.store.save_digest(
                digest_date=digest_date.isoformat(),
                status=digest_status,
                output_path=paths["daily_path"],
                stats=stats,
            )

            run_status = "partial_success" if total_failures else "success"
            self.store.finish_run(run_id=run_id, status=run_status, message="daily orchestration finished", stats=stats)
            print(f"[progress] orchestrator finished status={run_status}", flush=True)
            return {
                "status": run_status,
                "digest_date": digest_date.isoformat(),
                "mode": digest_status,
                "paths": paths,
                "stats": stats,
            }
        except Exception as exc:  # noqa: BLE001
            self.store.finish_run(run_id=run_id, status="failed", message=str(exc), stats={})
            raise

    def _section_items_payload(self, section_results: dict[str, SectionResult], section: str) -> list[dict]:
        result = section_results.get(section)
        if not result:
            return []
        return [
            {
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "summary_short": item.summary_short or "",
                "summary_raw": item.summary_raw or "",
                "signals": item.signals,
                "section": item.section,
            }
            for item in result.items
        ]


class NewsPipeline:  # compatibility shim
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("NewsPipeline has been replaced by section pipelines + DailyOrchestrator")
