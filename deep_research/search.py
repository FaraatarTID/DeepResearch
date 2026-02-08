import asyncio
import aiohttp
import random
import time
from typing import List, Dict, Optional
from .utils import ExternalServiceError
from .config import (
    BRAVE_API_KEY,
    USER_AGENT,
    CONCURRENCY,
    MIN_CITATION_COUNT,
    MAX_URLS_PER_SOURCE,
    BRAVE_CONCURRENCY,
    BRAVE_MAX_RETRIES,
    BRAVE_QUERY_DELAY_S,
    BRAVE_MAX_DELAY_S,
    SEMANTIC_MAX_RETRIES,
    SEMANTIC_QUERY_DELAY_S,
    SEMANTIC_MAX_DELAY_S,
    SEMANTIC_SCHOLAR_API_KEY,
)
from .processing import Snippet, pdf_to_text, docx_to_text
from .utils import logger, gemini_complete

def _retry_after_seconds(headers: aiohttp.typedefs.LooseHeaders) -> Optional[float]:
    if not headers:
        return None
    retry_after = headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return None

async def _throttle_request(lock: asyncio.Lock, delay_s: float, state: Dict[str, float]) -> None:
    if delay_s <= 0:
        return
    async with lock:
        now = time.monotonic()
        last_time = state.get("last_request", 0.0)
        wait_time = last_time + delay_s - now
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        state["last_request"] = time.monotonic()

async def fetch_text(session: aiohttp.ClientSession, url: str, max_retries: int = 2) -> str:
    """Fetch text content from a URL."""
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(max_retries + 1):
        try:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    return ""
                
                content_type = resp.headers.get("Content-Type", "").lower()
                data = await resp.read()
                
                if "application/pdf" in content_type or url.endswith(".pdf"):
                    return pdf_to_text(data)
                elif "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in content_type:
                    return docx_to_text(data)
                else:
                    # Assume HTML/Text
                    return data.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.exception("Fetch attempt failed for %s: %s", url, e)
            if attempt == max_retries:
                # Raise structured error so callers can decide how to handle
                raise ExternalServiceError("fetch", f"{url} - {e}") from e
            await asyncio.sleep(1)
            
    return ""

async def brave_search(
    query: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    throttle_lock: asyncio.Lock,
    throttle_state: Dict[str, float],
    cancel_check: Optional[callable] = None,
    raise_on_error: bool = False,
) -> List[Snippet]:
    """Search using Brave Search API."""
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {"q": query, "count": 10}
    
    snippets = []
    backoff = 1
    max_retries = BRAVE_MAX_RETRIES
    data = None
    # A separate semaphore for fetching content to avoid unbounded concurrent fetches
    fetch_semaphore = asyncio.Semaphore(CONCURRENCY)

    # Retry loop for API call
    for attempt in range(max_retries + 1):
        try:
            async with semaphore:
                current_delay = max(0.0, throttle_state.get("delay_s", BRAVE_QUERY_DELAY_S))
                await _throttle_request(throttle_lock, current_delay, throttle_state)
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 429:
                        if attempt < max_retries:
                            retry_after = _retry_after_seconds(resp.headers)
                            wait_time = retry_after or (backoff * (2 ** attempt) + random.uniform(0, 0.5))
                            # Update throttle_state under lock to avoid races
                            async with throttle_lock:
                                if retry_after:
                                    throttle_state["delay_s"] = min(
                                        max(current_delay, retry_after),
                                        BRAVE_MAX_DELAY_S,
                                    )
                                else:
                                    throttle_state["delay_s"] = min(
                                        max(current_delay * 2, BRAVE_QUERY_DELAY_S),
                                        BRAVE_MAX_DELAY_S,
                                    )
                            logger.warning(f"Brave API rate limit (429). Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            msg = "Brave API rate limit exceeded after retries."
                            if raise_on_error:
                                raise ExternalServiceError("brave", msg)
                            logger.error(msg)
                            return []
                            
                    if resp.status != 200:
                        logger.error(f"Brave API error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    break # Success
        except Exception as e:
            logger.exception("Brave search connection error for query '%s': %s", query, e)
            if attempt == max_retries:
                if raise_on_error:
                    raise ExternalServiceError("brave", str(e)) from e
                return []
            await asyncio.sleep(1)

    if not data:
        return []

    try:     
        results = data.get("web", {}).get("results", [])
        
        # Fetch content for each result with bounded concurrency
        async def bounded_fetch(u: str):
            if cancel_check and cancel_check():
                return ""
            async with fetch_semaphore:
                try:
                    return await fetch_text(session, u)
                except ExternalServiceError as exc:
                    logger.warning("Fetch failed for %s: %s", u, exc)
                    return ""

        fetch_tasks = []
        for r in results:
            u = r.get("url")
            if not u:
                continue
            fetch_tasks.append(bounded_fetch(u))

        contents = await asyncio.gather(*fetch_tasks)
        
        for r, content in zip(results, contents):
            if not content: continue
            
            s = Snippet(
                title=r.get("title", "No Title"),
                body=content, # We will compress/filter later
                url=r.get("url"),
                source_type="web",
                metadata={"description": r.get("description")}
            )
            snippets.append(s)
            
    except Exception as e:
        logger.exception("Brave search processing failed for '%s': %s", query, e)
        if raise_on_error:
            raise ExternalServiceError("brave", str(e)) from e

    return snippets

async def check_relevance(subject: str, title: str, abstract: str) -> bool:
    """Check if a paper is relevant to the subject using Gemini."""
    if not abstract:
        return False
        
    prompt = f"""
    Topic: "{subject}"
    
    Paper Title: "{title}"
    Abstract: "{abstract}"
    
    Is this paper relevant to the topic? 
    Answer strictly with YES or NO.
    """
    
    response = await gemini_complete(prompt, max_tokens=10)
    return "YES" in response.upper()

async def semantic_search(
    query: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    throttle_lock: asyncio.Lock,
    throttle_state: Dict[str, float],
    subject: str,
    limit: int = 20,
    cancel_check: Optional[callable] = None,
    raise_on_error: bool = False,
) -> List[Snippet]:
    """Search using Semantic Scholar API."""
    limit = min(limit, MAX_URLS_PER_SOURCE)
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,url,year,venue,authors,citationCount,openAccessPdf"
    }
    
    snippets = []
    backoff = 2
    max_retries = SEMANTIC_MAX_RETRIES
    data = None

    for attempt in range(max_retries + 1):
        try:
            async with semaphore:
                current_delay = max(0.0, throttle_state.get("delay_s", SEMANTIC_QUERY_DELAY_S))
                await _throttle_request(throttle_lock, current_delay, throttle_state)
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 429:
                        if attempt < max_retries:
                            retry_after = _retry_after_seconds(resp.headers)
                            wait_time = retry_after or (backoff * (2 ** attempt) + random.uniform(0.5, 1.5))
                            # Update throttle_state under lock
                            async with throttle_lock:
                                if retry_after:
                                    throttle_state["delay_s"] = min(
                                        max(current_delay, retry_after),
                                        SEMANTIC_MAX_DELAY_S,
                                    )
                                else:
                                    throttle_state["delay_s"] = min(
                                        max(current_delay * 2, SEMANTIC_QUERY_DELAY_S),
                                        SEMANTIC_MAX_DELAY_S,
                                    )
                            logger.warning(f"Semantic Scholar rate limit (429). Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            msg = "Semantic Scholar rate limit exceeded after retries."
                            if raise_on_error:
                                raise ExternalServiceError("semantic_scholar", msg)
                            logger.error(msg)
                            return []

                    if resp.status != 200:
                        logger.error(f"Semantic Scholar error: {resp.status}")
                        return []
                    data = await resp.json()
                    break # Success
        except Exception as e:
            logger.exception("Semantic search connection error for query '%s': %s", query, e)
            if attempt == max_retries:
                if raise_on_error:
                    raise ExternalServiceError("semantic_scholar", str(e)) from e
                return []
            await asyncio.sleep(1)
            
    if not data:
        return []

    async def process_paper(session, p):
        try:
            if cancel_check and cancel_check():
                return None
            # Filter by citation count
            citation_count = p.get("citationCount", 0)
            if citation_count < MIN_CITATION_COUNT:
                logger.debug(f"Filtered paper '{p.get('title', 'Unknown')}' - citations: {citation_count} < {MIN_CITATION_COUNT}")
                return None
            
            # Check relevance
            title = p.get("title", "No Title")
            abstract = p.get("abstract")
            
            if subject:
                is_relevant = await check_relevance(subject, title, abstract)
                if not is_relevant:
                    logger.debug(f"Filtered paper '{title}' - Not relevant to '{subject}'")
                    return None
                else:
                    logger.info(f"Paper '{title}' is relevant to '{subject}'")
            
            # Construct metadata
            meta = {
                "year": p.get("year"),
                "journal": p.get("venue"),
                "citations": citation_count,
                "authors": [a["name"] for a in p.get("authors", [])],
                "has_open_access": bool(p.get("openAccessPdf"))
            }
            
            url = (p.get("openAccessPdf") or {}).get("url") or p.get("url") or ""
            abstract = p.get("abstract")
            
            body = ""
            # If abstract is decent length, use it. Otherwise try to fetch full text.
            if abstract and len(abstract) >= 200:
                body = abstract
            elif url:
                # Try to fetch full text
                try:
                    fetched = await fetch_text(session, url)
                    if fetched and len(fetched) > len(abstract or ""):
                        body = fetched
                except ExternalServiceError as exc:
                    logger.warning("Failed to fetch full text for %s: %s", url, exc)
            
            # Fallback
            if not body:
                body = abstract or "Abstract not available."

            return Snippet(
                title=p.get("title", "No Title"),
                body=body,
                url=url,
                source_type="semantic_scholar",
                metadata=meta,
                abstract=abstract
            )
        except Exception as e:
            logger.exception("Error processing paper %s: %s", p.get('title'), e)
            return None

    try:
        papers = data.get("data", [])
        tasks = [process_paper(session, p) for p in papers]
        results = await asyncio.gather(*tasks)
        snippets = [r for r in results if r is not None]
            
    except Exception as e:
        logger.exception("Semantic search processing failed for '%s': %s", query, e)
        if raise_on_error:
            raise ExternalServiceError("semantic_scholar", str(e)) from e

    return snippets

async def search_all(keywords_dict: Dict[str, List[str]], subject: str = "", cancel_check: Optional[callable] = None, raise_on_error: bool = False) -> List[Snippet]:
    """Orchestrate search across all sources."""
    all_snippets = []
    brave_semaphore = asyncio.Semaphore(BRAVE_CONCURRENCY)
    semantic_semaphore = asyncio.Semaphore(1) # Limit Semantic Scholar to 1 concurrent request
    brave_throttle_lock = asyncio.Lock()
    brave_throttle_state = {"last_request": 0.0, "delay_s": BRAVE_QUERY_DELAY_S}
    semantic_throttle_lock = asyncio.Lock()
    semantic_throttle_state = {"last_request": 0.0, "delay_s": SEMANTIC_QUERY_DELAY_S}
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        # Brave Search Tasks
        for q in keywords_dict.get("general", []):
            tasks.append(brave_search(q, session, brave_semaphore, brave_throttle_lock, brave_throttle_state, cancel_check=cancel_check, raise_on_error=raise_on_error))
            
        # Semantic Scholar Tasks (serialize to reduce rate limiting pressure)
        brave_results = await asyncio.gather(*tasks)
        semantic_results = []
        for q in keywords_dict.get("academic", []):
            semantic_results.append(
                await semantic_search(
                    q,
                    session,
                    semantic_semaphore,
                    semantic_throttle_lock,
                    semantic_throttle_state,
                    subject,
                    cancel_check=cancel_check,
                    raise_on_error=raise_on_error,
                )
            )
        
        for res in brave_results:
            all_snippets.extend(res)
        for res in semantic_results:
            all_snippets.extend(res)
            
    return all_snippets
