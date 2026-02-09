import io
import re
import numpy as np
import trafilatura
import pdfplumber
import docx2txt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Optional, Dict
from .config import MAX_TOKENS_PER_URL, EST_CHAR_PER_TOKEN
import logging
from .utils import logger

# Suppress PDF and Trafilatura warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
logging.getLogger("trafilatura").setLevel(logging.CRITICAL)

# Regex patterns
HYPE_PATTERNS = {
    "buy now", "order now", "click here", "call now", "add to cart",
    "sign up today", "subscribe now", "book now", "limited offer"
}

# Heuristics for prompt-injection style instructions in untrusted sources
INJECTION_PATTERNS = (
    "ignore previous instructions",
    "disregard previous instructions",
    "system prompt",
    "developer message",
    "you are chatgpt",
    "act as",
    "do not follow",
    "follow these instructions",
    "tool output",
    "assistant:",
)

class Snippet:
    __slots__ = ("title", "body", "url", "ref_num", "source_type", "metadata", "abstract")
    def __init__(self, title: str, body: str, url: str, source_type: str = "web", 
                 metadata: Optional[dict] = None, abstract: Optional[str] = None):
        self.title = title
        self.body = body
        self.url = url
        self.ref_num = None
        self.source_type = source_type
        self.metadata = metadata or {}
        self.abstract = abstract

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "body": self.body[:2000],  # Truncate for display/logging
            "source_type": self.source_type,
            "metadata": self.metadata,
            "abstract": self.abstract
        }

def token_count(text: str) -> int:
    return len(text) // EST_CHAR_PER_TOKEN

def compress_text(html: str, max_tokens: int) -> str:
    """Extract main text from HTML and truncate to max_tokens."""
    if not html or len(html) < 10:
        return ""
    
    # If it doesn't look like HTML, treat as plain text
    if not ("<html" in html.lower() or "<body" in html.lower() or "<div" in html.lower()):
        text = html
    else:
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        
    if not text:
        # Fallback if extraction failed but there was content
        if len(html) > 0 and not ("<html" in html.lower()):
             text = html
        else:
             return ""
    
    text = sanitize_text(text)

    # Simple truncation based on estimated tokens
    if token_count(text) > max_tokens:
        return text[:max_tokens * EST_CHAR_PER_TOKEN]
    return text

def sanitize_text(text: str) -> str:
    """Remove common prompt-injection style lines from untrusted sources."""
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        low = line.strip().lower()
        if not low:
            continue
        if any(pat in low for pat in INJECTION_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

def _normalize_text(text: str) -> str:
    """Normalize untrusted text for LLM consumption."""
    if not text:
        return ""
    # Remove URLs inside the text; URL is provided separately
    text = re.sub(r"https?://\S+", "", text)
    # Collapse excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _sentence_candidates(text: str) -> List[str]:
    if not text:
        return []
    # Basic sentence split; avoid heavy NLP deps
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]

def extract_key_sentences(text: str, max_chars: int) -> str:
    """Heuristically keep more factual sentences and drop instruction-like text."""
    if not text:
        return ""
    sentences = _sentence_candidates(text)
    if not sentences:
        return text[:max_chars]

    def score(s: str) -> int:
        s_low = s.lower()
        points = 0
        if any(tok in s_low for tok in ("et al", "study", "research", "evidence", "analysis", "dataset")):
            points += 2
        if re.search(r"\b(19|20)\d{2}\b", s):
            points += 2
        if re.search(r"\[\d+\]", s) or re.search(r"\(\d{4}\)", s):
            points += 2
        if re.search(r"\d", s):
            points += 1
        return points

    ranked = sorted(sentences, key=score, reverse=True)
    picked = []
    total = 0
    for s in ranked:
        if total + len(s) + 1 > max_chars:
            continue
        picked.append(s)
        total += len(s) + 1
        if total >= max_chars:
            break
    if not picked:
        return text[:max_chars]
    return " ".join(picked)

def _safe_meta_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        return [str(v) for v in value][:20]
    return str(value)

def build_llm_payload(
    snippets: List["Snippet"],
    total_char_budget: int,
    per_snippet_min: int = 400,
    per_snippet_max: int = 2000,
) -> List[Dict[str, object]]:
    """Create a structured, size-capped payload for LLM consumption."""
    if not snippets:
        return []
    total_char_budget = max(per_snippet_min, total_char_budget)
    per_snippet_budget = total_char_budget // max(1, len(snippets))
    per_snippet_budget = max(per_snippet_min, min(per_snippet_budget, per_snippet_max))

    payload = []
    for s in snippets:
        text = sanitize_text(s.body or "")
        text = _normalize_text(text)
        if len(text) > per_snippet_budget:
            text = extract_key_sentences(text, per_snippet_budget)

        # Whitelist metadata fields to avoid leaking large/unsafe blobs
        meta = {
            "year": _safe_meta_value(s.metadata.get("year")),
            "journal": _safe_meta_value(s.metadata.get("journal")),
            "citations": _safe_meta_value(s.metadata.get("citations")),
            "authors": _safe_meta_value(s.metadata.get("authors")),
            "description": _safe_meta_value(s.metadata.get("description")),
            "has_open_access": _safe_meta_value(s.metadata.get("has_open_access")),
        }
        payload.append(
            {
                "title": s.title,
                "url": s.url,
                "source_type": s.source_type,
                "metadata": meta,
                "excerpt": text,
            }
        )
    return payload

def is_quality_page(text: str, source_type: str = "web") -> bool:
    """Check if the text content is of sufficient quality."""
    if not text:
        return False

    # Academic papers might be just abstracts, so we allow shorter text
    if source_type == "semantic_scholar":
        return len(text) >= 100

    if len(text) < 500:
        return False
        
    # Check for hype words
    text_lower = text.lower()
    if any(p in text_lower for p in HYPE_PATTERNS):
        return False
        
    return True

def pdf_to_text(data: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text
    except Exception as e:
        logger.exception("PDF parsing failed: %s", e)
        return ""

def docx_to_text(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        return docx2txt.process(io.BytesIO(data))
    except Exception as e:
        logger.exception("DOCX parsing failed: %s", e)
        return ""

def semantic_dedup(texts: List[str], max_keep: int = 100) -> List[int]:
    """Deduplicate texts using TF-IDF and Cosine Similarity."""
    if not texts:
        return []
    
    if len(texts) <= 1:
        return [0]

    # Cap inputs to reduce O(n^2) cost on large runs
    if len(texts) > max_keep * 3:
        # Keep the longest texts as a heuristic for information density
        ranked = sorted(range(len(texts)), key=lambda i: len(texts[i]), reverse=True)
        keep_seed = ranked[: max_keep * 3]
        texts = [texts[i] for i in keep_seed]
        index_map = {new_i: old_i for new_i, old_i in enumerate(keep_seed)}
    else:
        index_map = {i: i for i in range(len(texts))}
        
    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError: # Empty vocabulary
        return list(range(min(len(texts), max_keep)))
        
    # Calculate similarity
    sim_matrix = cosine_similarity(tfidf_matrix)
    
    # Greedy selection to maximize diversity (simplified approach)
    # Here we just keep the most distinct ones, or rather, we filter out very similar ones.
    # The original code used a specific logic, let's replicate a robust version.
    
    keep_indices = []
    seen_indices = set()
    
    # Sort by length (preference for longer content) as a heuristic? 
    # Or just process in order. Let's process in order but skip if similar to already kept.
    
    for i in range(len(texts)):
        if i in seen_indices:
            continue
            
        keep_indices.append(i)
        seen_indices.add(i)
        
        if len(keep_indices) >= max_keep:
            break
            
        # Mark similar items as seen
        for j in range(i + 1, len(texts)):
            if j not in seen_indices and sim_matrix[i, j] > 0.85: # Threshold
                seen_indices.add(j)
                
    return [index_map[i] for i in keep_indices]
