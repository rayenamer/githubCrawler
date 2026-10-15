from fastapi import APIRouter, Depends, HTTPException, Path, Request

from crawl.helpers import GitHubError, RateLimitError, UserNotFoundError
from crawl.models import UserRepos
from crawl.services import RepoService

router = APIRouter()

# GitHub usernames: alphanumerics and hyphens, no leading/trailing hyphen, max 39 chars.
USERNAME_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$"


def get_repo_service(request: Request) -> RepoService:
    return RepoService(request.app.state.github_client)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/users/{username}/repos", response_model=UserRepos)
async def list_repos(
    username: str = Path(..., pattern=USERNAME_PATTERN),
    service: RepoService = Depends(get_repo_service),
) -> UserRepos:
    try:
        return await service.get_user_repos(username)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    except RateLimitError as exc:
        reset = f" Resets at unix time {exc.reset_at}." if exc.reset_at else ""
        raise HTTPException(
            status_code=429,
            detail=f"GitHub rate limit exceeded.{reset} Set GITHUB_TOKEN to raise the limit.",
        )
    except GitHubError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
