from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.core.config import settings


def _normalized(
    text: str,
    author: str,
    url: str,
    timestamp: datetime,
    source: str,
) -> dict[str, Any]:
    return {
        "text": text,
        "author": author,
        "url": url,
        "timestamp": timestamp.isoformat(),
        "source": source,
    }


async def fetch_telegram_channels(
    channels: list[str],
    days: int = 7,
) -> list[dict[str, Any]]:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_string = os.getenv("TELEGRAM_SESSION_STRING")

    if not api_id or not api_hash:
        return []

    try:
        from telethon import TelegramClient
        from telethon.tl.types import Channel
    except ImportError:
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    results: list[dict[str, Any]] = []

    try:
        client = TelegramClient(
            session_string or "social_intel_session",
            int(api_id),
            api_hash,
        )
        await client.start()

        for channel_name in channels:
            try:
                entity = await client.get_entity(channel_name)
                messages = await client.get_messages(
                    entity,
                    limit=100,
                    offset_date=datetime.utcnow(),
                )
                for msg in messages:
                    if msg.date and msg.date.replace(tzinfo=None) < cutoff:
                        continue
                    if not msg.text:
                        continue
                    results.append(
                        _normalized(
                            text=msg.text,
                            author=channel_name,
                            url=f"https://t.me/{channel_name}/{msg.id}",
                            timestamp=msg.date,
                            source="telegram",
                        )
                    )
            except Exception:
                continue

        await client.disconnect()
    except Exception:
        return []

    return results


async def fetch_reddit_posts(
    subreddits: list[str],
    query: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for subreddit in subreddits:
            try:
                search_url = f"https://www.reddit.com/r/{subreddit}/search.json"
                response = await client.get(
                    search_url,
                    params={
                        "q": query,
                        "restrict_sr": "on",
                        "sort": "relevance",
                        "limit": 25,
                        "t": "week",
                    },
                    headers={"User-Agent": "GlobalIntelligence/1.0"},
                )
                if response.status_code != 200:
                    continue

                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for post_wrapper in posts:
                    post = post_wrapper.get("data", {})
                    created_utc = post.get("created_utc", 0)
                    timestamp = datetime.utcfromtimestamp(created_utc)
                    permalink = post.get("permalink", "")
                    selftext = post.get("selftext", "") or post.get("title", "")

                    results.append(
                        _normalized(
                            text=selftext,
                            author=post.get("author", "unknown"),
                            url=f"https://reddit.com{permalink}" if permalink else "",
                            timestamp=timestamp,
                            source="reddit",
                        )
                    )
            except Exception:
                continue

    return results


async def fetch_twitter_posts(
    query: str,
    count: int = 100,
) -> list[dict[str, Any]]:
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        return []

    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            search_url = "https://api.twitter.com/2/tweets/search/recent"
            response = await client.get(
                search_url,
                params={
                    "query": query,
                    "max_results": min(count, 100),
                    "tweet.fields": "created_at,author_id,public_metrics",
                },
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "User-Agent": "GlobalIntelligence/1.0",
                },
            )
            if response.status_code != 200:
                return []

            data = response.json()
            tweets = data.get("data", [])
            users_map: dict[str, str] = {}

            includes = data.get("includes", {})
            for user in includes.get("users", []):
                users_map[user["id"]] = user.get("username", "unknown")

            for tweet in tweets:
                created_at_str = tweet.get("created_at", "")
                try:
                    timestamp = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    timestamp = timestamp.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    timestamp = datetime.utcnow()

                author_id = tweet.get("author_id", "")
                author = users_map.get(author_id, "unknown")
                tweet_id = tweet.get("id", "")

                results.append(
                    _normalized(
                        text=tweet.get("text", ""),
                        author=f"@{author}",
                        url=f"https://twitter.com/{author}/status/{tweet_id}" if tweet_id else "",
                        timestamp=timestamp,
                        source="twitter",
                    )
                )
        except Exception:
            return []

    return results
