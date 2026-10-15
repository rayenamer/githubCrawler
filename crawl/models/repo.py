from pydantic import BaseModel


class Repo(BaseModel):
    name: str
    readme_description: str | None = None


class UserRepos(BaseModel):
    username: str
    count: int
    repos: list[Repo]
