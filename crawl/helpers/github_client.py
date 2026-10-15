"""Thin HTTP client around the public GitHub REST API."""

import os
from typing import Any

import httpx

GITHUB_API_URL = "https://api.github.com"
PER_PAGE = 100


class GitHubError(Exception):
    """Raised when GitHub returns an unexpected response."""


class UserNotFoundError(GitHubError):
    """Raised when the requested GitHub user does not exist."""


class RateLimitError(GitHubError):
    """Raised when the GitHub API rate limit is exhausted."""

    def __init__(self, reset_at: int | None) -> None:
        self.reset_at = reset_at
        super().__init__("GitHub API rate limit exceeded")


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: float = 10.0) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        # Optional: a token raises the rate limit from 60 to 5000 req/h.
        token = token or os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_URL, headers=headers, timeout=timeout
        )

    async def list_user_repos(self, username: str) -> list[dict[str, Any]]:
        """Return every public repo of `username`, following pagination."""
        repos: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await self._client.get(
                f"/users/{username}/repos",
                params={"per_page": PER_PAGE, "page": page, "type": "owner"},
            )
            if response.status_code == 404:
                raise UserNotFoundError(username)
            _raise_for_status(response)

            batch = response.json()
            repos.extend(batch)
            if len(batch) < PER_PAGE:
                return repos
            page += 1

    async def get_readme(self, full_name: str) -> str | None:
        """Return the raw README of `owner/repo`, or None if it has none."""
        response = await self._client.get(
            f"/repos/{full_name}/readme",
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        if response.status_code == 404:
            return None
        _raise_for_status(response)
        return response.text

    async def aclose(self) -> None:
        await self._client.aclose()


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 200:
        return
    if response.status_code in (403, 429) and (
        response.headers.get("x-ratelimit-remaining") == "0"
        or "rate limit" in response.text.lower()
    ):
        reset = response.headers.get("x-ratelimit-reset")
        raise RateLimitError(int(reset) if reset and reset.isdigit() else None)
    raise GitHubError(f"GitHub API {response.status_code}: {response.text[:200]}")
