"""Trend watcher service - monitors Instagram/News for hotwords.

Pluggable sources:
  - RSS feeds (news sites)
  - Instagram hashtag tracking (via public API or scraping)
  - Custom keyword lists

Emits 'trend_detected' events when hotwords are found.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import feedparser

from platform.core.config import get_config
from platform.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class TrendMatch:
    """A detected trend match."""
    keyword: str
    source: str
    title: str
    url: str
    detected_at: datetime = field(default_factory=datetime.utcnow)


class TrendWatcher:
    """Watches multiple sources for trending topics based on hotwords."""

    def __init__(self):
        config = get_config()
        self._hotwords: list[str] = config.get("trends", "hotwords", default=[])
        self._rss_feeds: list[str] = config.get("trends", "rss_feeds", default=[])
        self._check_interval: int = config.get("trends", "check_interval_minutes", default=120)
        self._matches: list[TrendMatch] = []
        self._running = False

    async def check_rss_feeds(self) -> list[TrendMatch]:
        """Check RSS feeds for hotword matches."""
        matches = []
        for feed_url in self._rss_feeds:
            try:
                feed = await asyncio.to_thread(feedparser.parse, feed_url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "").lower()
                    summary = entry.get("summary", "").lower()
                    text = f"{title} {summary}"

                    for keyword in self._hotwords:
                        if keyword.lower() in text:
                            match = TrendMatch(
                                keyword=keyword,
                                source=feed_url,
                                title=entry.get("title", ""),
                                url=entry.get("link", ""),
                            )
                            matches.append(match)
            except Exception as e:
                logger.error(f"Error checking feed {feed_url}: {e}")

        return matches

    async def check_all_sources(self) -> list[TrendMatch]:
        """Run all source checks and emit events for new matches."""
        bus = get_event_bus()
        new_matches = await self.check_rss_feeds()

        # Deduplicate against recent matches
        seen_urls = {m.url for m in self._matches[-100:]}
        unique_matches = [m for m in new_matches if m.url not in seen_urls]

        for match in unique_matches:
            self._matches.append(match)
            await bus.emit(
                "trend_detected",
                keyword=match.keyword,
                title=match.title,
                url=match.url,
                source=match.source,
            )
            logger.info(f"Trend detected: '{match.keyword}' in '{match.title}'")

        return unique_matches

    def get_recent_matches(self, limit: int = 20) -> list[TrendMatch]:
        """Get recent trend matches."""
        return self._matches[-limit:]

    def add_hotword(self, word: str):
        """Add a hotword to track."""
        if word not in self._hotwords:
            self._hotwords.append(word)

    def remove_hotword(self, word: str):
        """Remove a hotword."""
        if word in self._hotwords:
            self._hotwords.remove(word)

    @property
    def hotwords(self) -> list[str]:
        return list(self._hotwords)
