#!/usr/bin/env bash
# Starts the crawl API, asks for a GitHub username, prints its public repos, then stops the API.
# Usage: ./start_all.sh [username]
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
BASE_URL="http://127.0.0.1:${PORT}"
VENV=".venv"

# 1. Environment
if [ ! -x "$VENV/bin/uvicorn" ]; then
  echo "Setting up virtualenv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r requirements.txt
fi

# 2. Start the API in the background, stop it when the script exits
"$VENV/bin/uvicorn" crawl.main:app --port "$PORT" > .server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

echo -n "Starting API on port $PORT"
for _ in $(seq 30); do
  if curl -sf "$BASE_URL/health" > /dev/null; then break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo; echo "API failed to start, see .server.log:"; cat .server.log; exit 1
  fi
  echo -n "."; sleep 0.5
done
echo " ready."

# 3. Ask for the username (or take it from the first argument)
USERNAME="${1:-}"
while [ -z "$USERNAME" ]; do
  read -rp "GitHub username to scrape: " USERNAME
done

# 4. Query and print
RESPONSE=$(curl -s -w '\n%{http_code}' "$BASE_URL/users/$USERNAME/repos")
STATUS=$(tail -n1 <<< "$RESPONSE")
BODY=$(sed '$d' <<< "$RESPONSE")

if [ "$STATUS" != "200" ]; then
  echo "Error ($STATUS): $BODY"
  exit 1
fi

"$VENV/bin/python" -c '
import json, sys, textwrap
data = json.loads(sys.argv[1])
print("\n%s has %d public repos:\n" % (data["username"], data["count"]))
for repo in data["repos"]:
    print("  - " + repo["name"])
    desc = repo.get("readme_description") or "(no README description)"
    print(textwrap.fill(desc, width=90, initial_indent="      ", subsequent_indent="      "))
    print()
' "$BODY"
