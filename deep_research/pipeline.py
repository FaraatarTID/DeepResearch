from dataclasses import dataclass
from typing import List, Optional, Callable, Dict
import time
import uuid

from .config import validate_config
from .core import generate_keywords, filter_snippets, save_bibliometrics, synthesise
from .processing import Snippet
from . import search as _search
from .utils import logger


@dataclass
class PipelineResult:
    report: Optional[str]
    biblio_text: Optional[str]
    snippets: List[Snippet]
    error: Optional[str] = None
    run_id: Optional[str] = None
    timings: Optional[Dict[str, float]] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.report)


def _notify(callback: Optional[Callable[[str], None]], message: str) -> None:
    if callback:
        callback(message)


async def run_research(
    subject: str,
    general_rounds: int,
    academic_rounds: int,
    status_callback: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> PipelineResult:
    """Run the research pipeline and return a structured result."""
    run_id = uuid.uuid4().hex[:8]
    timings: Dict[str, float] = {}
    start_ts = time.perf_counter()
    def finalize(
        *,
        report: Optional[str] = None,
        biblio_text: Optional[str] = None,
        snippets: Optional[List[Snippet]] = None,
        error: Optional[str] = None,
    ) -> PipelineResult:
        timings["total_s"] = time.perf_counter() - start_ts
        if error:
            logger.error("Pipeline error (run_id=%s): %s", run_id, error)
        if timings:
            logger.info("Pipeline timings (run_id=%s): %s", run_id, timings)
        return PipelineResult(
            report=report,
            biblio_text=biblio_text,
            snippets=snippets or [],
            error=error,
            run_id=run_id,
            timings=timings,
        )

    _notify(status_callback, f"🧾 Run ID: {run_id}")
    # Early cancellation check to avoid starting external calls when requested
    if cancel_check and cancel_check():
        error = "Cancelled"
        _notify(status_callback, error)
        return finalize(error=error)

    step_start = time.perf_counter()
    valid, msg = validate_config()
    timings["config_s"] = time.perf_counter() - step_start
    if not valid:
        error = f"Configuration Error: {msg}"
        _notify(status_callback, error)
        return finalize(error=error)

    try:
        _notify(status_callback, "📝 Generating keywords...")
        step_start = time.perf_counter()
        keywords = await generate_keywords(subject, general_rounds, academic_rounds)
        timings["keywords_s"] = time.perf_counter() - step_start
        _notify(status_callback, f"✅ Keywords: {keywords}")

        if cancel_check and cancel_check():
            error = "Cancelled"
            _notify(status_callback, error)
            return finalize(error=error)

        _notify(status_callback, "🔍 Searching sources...")
        step_start = time.perf_counter()
        # Consider search failures fatal for the pipeline and raise structured errors
        snippets = await _search.search_all(keywords, subject=subject, cancel_check=cancel_check, raise_on_error=True)
        timings["search_s"] = time.perf_counter() - step_start
        _notify(status_callback, f"📊 Found {len(snippets)} raw snippets")

        if not snippets:
            error = "No snippets found."
            _notify(status_callback, error)
            return finalize(error=error)

        _notify(status_callback, "🔄 Filtering and deduplicating...")
        step_start = time.perf_counter()
        snippets = await filter_snippets(snippets)
        timings["filter_s"] = time.perf_counter() - step_start
        _notify(status_callback, f"✅ Kept {len(snippets)} quality snippets")

        if cancel_check and cancel_check():
            error = "Cancelled"
            _notify(status_callback, error)
            return finalize(error=error)

        if not snippets:
            error = "No quality snippets left."
            _notify(status_callback, error)
            return finalize(error=error)

        _notify(status_callback, "📊 Generating bibliometrics...")
        step_start = time.perf_counter()
        biblio_text = save_bibliometrics(snippets)
        timings["bibliometrics_s"] = time.perf_counter() - step_start

        _notify(status_callback, "🧠 Synthesizing report...")
        step_start = time.perf_counter()
        report = await synthesise(snippets, subject, cancel_check=cancel_check)
        timings["synthesis_s"] = time.perf_counter() - step_start
        return finalize(report=report, biblio_text=biblio_text, snippets=snippets)
    except Exception as exc:
        logger.exception("Pipeline error (run_id=%s): %s", run_id, exc)
        error = f"Error: {exc}"
        _notify(status_callback, error)
        return finalize(error=error)
