import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "contributions.json"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(login, token):
    now = datetime.now(timezone.utc)
    variables = {
        "login": login,
        "from": (now - timedelta(days=364)).strftime("%Y-%m-%dT00:00:00Z"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def main():
    login = os.environ.get("GH_USER", "Walterldk")
    calendar = fetch(login, os.environ["GITHUB_TOKEN"])
    today = datetime.now(timezone.utc).date().isoformat()
    days = [
        {"date": d["date"], "count": d["contributionCount"]}
        for week in calendar["weeks"]
        for d in week["contributionDays"]
        if d["date"] <= today
    ]
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data["total"] = calendar["totalContributions"]
    data["days"] = days
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
