from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from crawl.api import router
from crawl.helpers import GitHubClient

# Load GITHUB_TOKEN (and any other settings) from .env; real env vars win.
load_dotenv()


"""
- async def lifespan(app): FastAPI calls this function itself, because it's passed in with FastAPI(..., lifespan=lifespan) lower in the file.
- app.state.github_client = GitHubClient(): creates one GitHub client and stores it on app.state, a place on the app where you can keep shared objects.
- yield: splits the function in two. Everything before it runs at startup. Then FastAPI serves requests for as long as the server is up. Everything after it runs at shutdown, for example when you press Ctrl+C or when start_all.sh stops the server.
- await ...aclose(): closes the client cleanly, releasing its open network connections.
- @asynccontextmanager: turns this "setup, yield, cleanup" function into an object with a start and an end, which is the form FastAPI expects.
"""
"""
GitHubClient wraps an httpx.AsyncClient, which keeps a pool of open connections to api.github.com:
- It's faster. Making a secure connection to GitHub costs a few network round trips. With one shared client, the 57 README requests for rayenamer reuse existing connections instead of opening 57 new ones.
- Nothing is left open. Creating a client for each request and forgetting to close it leaves connections hanging. Here the client is created once and closed once.
- Startup work happens once. Reading GITHUB_TOKEN and building the request headers happens a single time.
"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.github_client = GitHubClient()
    yield
    await app.state.github_client.aclose()


app = FastAPI(title="GitHub Crawler", lifespan=lifespan)
app.include_router(router)
