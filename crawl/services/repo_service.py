import asyncio
import logging
from typing import Any

import httpx

from crawl.helpers import GitHubClient, GitHubError, RateLimitError, extract_description
from crawl.models import Repo, UserRepos

logger = logging.getLogger(__name__)

# Max README requests in flight at once, to stay polite with GitHub.
MAX_CONCURRENCY = 10


class RepoService:
    """Business logic: turn raw GitHub data into domain models."""

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    async def get_user_repos(self, username: str) -> UserRepos:
        raw = await self._client.list_user_repos(username)
        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        repos = await asyncio.gather(*(self._build_repo(item, semaphore) for item in raw))
        return UserRepos(username=username, count=len(repos), repos=list(repos))

    async def _build_repo(self, item: dict[str, Any], semaphore: asyncio.Semaphore) -> Repo:
        async with semaphore:
            try:
                readme = await self._client.get_readme(item["full_name"])
            except RateLimitError:
                raise
            except (GitHubError, httpx.HTTPError) as exc:
                # One broken README must not fail the whole listing.
                logger.warning("README fetch failed for %s: %s", item["full_name"], exc)
                readme = None
        description = extract_description(readme) if readme else None
        return Repo(name=item["name"], readme_description=description)
