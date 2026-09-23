"""RSS and Atom feed adapter."""

import hashlib
import http.client
import json
import re
import sys
import tomllib
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from fashion_trends.models import Signal

_TIMEOUT_SECONDS = 15
_USER_AGENT = "fashion-trend-bot/0.1 (+RSS reader)"
_BLOCK_TAGS = {"br", "div", "li", "p", "tr"}


class _TextExtractor(HTMLParser):
    """Turn the HTML fragments commonly embedded in RSS fields into plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(element: ET.Element, *names: str) -> str:
    wanted = set(names)
    for child in element.iter():
        if child is element or _local_name(child.tag) not in wanted:
            continue
        if _local_name(child.tag) == "link" and child.attrib.get("href"):
            return child.attrib["href"].strip()
        value = _plain_text(" ".join(child.itertext()))
        if value:
            return value
    return ""


def _publication_date(value: str, fallback: date) -> date:
    if not value:
        return fallback
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.date()


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "rss-feed"


class RSSSource:
    """Fetch configured RSS/Atom feeds, isolating failures to each feed."""

    name = "rss"

    def __init__(self, feeds_path: str | Path = "feeds.toml") -> None:
        self.feeds_path = Path(feeds_path)

    def _load_feeds(self) -> list[dict[str, str]]:
        with self.feeds_path.open("rb") as stream:
            config = tomllib.load(stream)
        feeds = config.get("feeds", [])
        if not isinstance(feeds, list):
            raise ValueError("feeds.toml must contain [[feeds]] entries")
        normalized = []
        for index, feed in enumerate(feeds, start=1):
            if not isinstance(feed, dict) or not feed.get("url"):
                raise ValueError(f"Feed entry {index} must include a url")
            url = str(feed["url"])
            if urlparse(url).scheme not in {"http", "https"}:
                raise ValueError(f"Feed entry {index} must use an http or https URL")
            name = str(feed.get("name") or urlparse(url).netloc)
            normalized.append({"name": _slug(name), "url": url})
        return normalized

    def _fetch_feed(self, feed: dict[str, str], fallback_date: date) -> list[Signal]:
        request = urllib.request.Request(feed["url"], headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            root = ET.fromstring(response.read())

        entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
        signals = []
        for entry in entries:
            title = _child_text(entry, "title")
            summary = _child_text(entry, "summary", "description", "content", "encoded")
            link = _child_text(entry, "link")
            published = _child_text(entry, "pubdate", "published", "updated", "date")
            observed_on = _publication_date(published, fallback_date)
            # Keep the full summary in metadata, but normalize the shorter headline.
            text = title or summary
            if not text:
                continue
            identity = link or f"{title}|{published}"
            item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            metadata = json.dumps({"title": title, "summary": summary, "published": published})
            signals.append(
                Signal(feed["name"], item_id, observed_on, text, link or None, metadata=metadata)
            )
        return signals

    def fetch(self, observed_on: date) -> list[Signal]:
        signals = []
        for feed in self._load_feeds():
            try:
                signals.extend(self._fetch_feed(feed, observed_on))
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                TimeoutError,
                OSError,
                ET.ParseError,
                ValueError,
            ) as error:
                print(f"Warning: could not collect {feed['name']} ({feed['url']}): {error}", file=sys.stderr)
        return signals
