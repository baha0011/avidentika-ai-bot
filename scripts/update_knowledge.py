#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.utils.logging import configure_logging  # noqa: E402

logger = logging.getLogger("knowledge_updater")
USER_AGENT = "AVIDENTIKA-Knowledge-Updater/1.0 (+https://avidentika.com.ua/)"
ALLOWED_PATH_PREFIXES = ("/contacts/", "/poslugy/", "/likar/")


@dataclass(slots=True)
class Report:
    status: str = "running"
    pages_found: int = 0
    pages_updated: int = 0
    pages_failed: int = 0
    chunks_saved: int = 0
    failed_urls: list[str] | None = None

    def __post_init__(self) -> None:
        self.failed_urls = [] if self.failed_urls is None else self.failed_urls


def clean_url(url: str) -> str:
    value = urldefrag(url)[0]
    parsed = urlparse(value)
    path = parsed.path or "/"
    if "." not in path.rsplit("/", 1)[-1] and not path.endswith("/"):
        path += "/"
    return parsed._replace(path=path, query="", fragment="").geturl()


def relevant(url: str, host: str) -> bool:
    parsed = urlparse(url)
    allowed_path = parsed.path == "/" or any(parsed.path.startswith(p) for p in ALLOWED_PATH_PREFIXES)
    return parsed.scheme in {"http", "https"} and parsed.netloc == host and allowed_path


def extract_page(html: str, url: str) -> tuple[str, str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(" ", strip=True) if soup.title else url)[:300]
    for tag in soup.select("script, style, noscript, svg, nav, footer, form, header, aside, .menu, .popup, .modal"):
        tag.decompose()
    main = soup.select_one("main, article, #main, .site-main") or soup.body or soup
    blocks: list[str] = []
    last = ""
    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()
        if len(text) < 2 or text == last:
            continue
        if text.lower() in {"запис на прийом", "записатися", "послуги", "контакти", "contact us"}:
            continue
        blocks.append(text)
        last = text
    links = [clean_url(urljoin(url, anchor.get("href", ""))) for anchor in soup.find_all("a", href=True)]
    return title, "\n".join(blocks), links


def chunk_text(text: str, *, max_chars: int = 2600, overlap_chars: int = 250) -> list[str]:
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if current and size + len(paragraph) + 1 > max_chars:
            chunk = "\n".join(current)
            chunks.append(chunk)
            tail = chunk[-overlap_chars:]
            current, size = [tail], len(tail)
        current.append(paragraph[:max_chars])
        size += len(paragraph) + 1
    if current:
        chunks.append("\n".join(current))
    return [chunk for chunk in chunks if len(chunk) >= 80]


def load_robots(client: httpx.Client, base_url: str) -> RobotFileParser:
    robots_url = urljoin(base_url, "/robots.txt")
    parser = RobotFileParser(robots_url)
    try:
        response = client.get(robots_url)
        response.raise_for_status()
        parser.parse(response.text.splitlines())
    except Exception as exc:
        logger.warning("robots.txt unavailable (%s); only known public pages will be crawled", type(exc).__name__)
        parser.parse([])
    return parser


def db_execute(builder):
    return builder.execute()


def main() -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    report = Report()
    started = datetime.now(UTC).isoformat()
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    openai = OpenAI(api_key=settings.openai_api_key, timeout=settings.http_timeout_seconds, max_retries=2)
    log_row = db_execute(supabase.table("knowledge_update_logs").insert({"status": "running", "started_at": started}).select("id")).data[0]
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    transport = httpx.HTTPTransport(retries=2)
    base_url = clean_url(settings.knowledge_base_url)
    host = urlparse(base_url).netloc
    try:
        with httpx.Client(headers=headers, timeout=settings.http_timeout_seconds, follow_redirects=True, transport=transport) as client:
            robots = load_robots(client, base_url)
            robots_delay = robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0
            delay = max(settings.crawl_delay_seconds, float(robots_delay))
            queue, seen = [base_url], set()
            while queue and len(seen) < settings.max_crawl_pages:
                url = queue.pop(0)
                if url in seen or not relevant(url, host):
                    continue
                seen.add(url)
                if not robots.can_fetch(USER_AGENT, url):
                    logger.info("Blocked by robots.txt: %s", url)
                    continue
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    if "text/html" not in response.headers.get("content-type", ""):
                        continue
                    title, text, links = extract_page(response.text, url)
                    for link in links:
                        if relevant(link, host) and link not in seen and link not in queue:
                            queue.append(link)
                    chunks = chunk_text(text)
                    if not chunks:
                        raise ValueError("No meaningful page text extracted")
                    # Deactivate previous chunks only after a successful fetch and extraction.
                    db_execute(supabase.table("knowledge_documents").update({"is_active": False}).eq("source_url", url))
                    now = datetime.now(UTC).isoformat()
                    for chunk in chunks:
                        digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                        embedding = openai.embeddings.create(model=settings.openai_embedding_model, input=chunk).data[0].embedding
                        payload = {
                            "source_url": url,
                            "page_title": title,
                            "content": chunk,
                            "content_hash": digest,
                            "language": "uk",
                            "embedding": embedding,
                            "is_active": True,
                            "scraped_at": now,
                            "updated_at": now,
                        }
                        db_execute(supabase.table("knowledge_documents").upsert(payload, on_conflict="source_url,content_hash"))
                        report.chunks_saved += 1
                    report.pages_updated += 1
                    logger.info("Updated %s (%d chunks)", url, len(chunks))
                except Exception as exc:
                    report.pages_failed += 1
                    report.failed_urls.append(url)
                    logger.error("Failed page %s: %s", url, type(exc).__name__)
                time.sleep(delay)
            report.pages_found = len(seen)
        report.status = "success" if report.pages_failed == 0 else "partial"
    except Exception as exc:
        report.status = "failed"
        logger.exception("Knowledge update failed")
        report.failed_urls.append(f"fatal:{type(exc).__name__}")
    finally:
        completed = datetime.now(UTC).isoformat()
        error_details = json.dumps(report.failed_urls, ensure_ascii=False) if report.failed_urls else None
        db_execute(supabase.table("knowledge_update_logs").update({
            "status": report.status,
            "pages_found": report.pages_found,
            "pages_updated": report.pages_updated,
            "pages_failed": report.pages_failed,
            "error_details": error_details,
            "completed_at": completed,
        }).eq("id", log_row["id"]))
        output = ROOT / "data" / "knowledge_update_report.json"
        output.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.status in {"success", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
