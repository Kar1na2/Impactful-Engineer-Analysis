#!/usr/bin/env python3
"""
Pull merged PRs (+ commits + reviews) and issues from PostHog repos into SQLite.

Window: mergedAt / createdAt within [START, END] (90-day window).
Repos: PostHog/posthog, PostHog/posthog-js, PostHog/posthog-python

Design notes:
- Uses the GitHub GraphQL API (far fewer requests than REST for nested commits).
- PRs are fetched with state=MERGED, ordered by UPDATED_AT DESC. Since
  mergedAt <= updatedAt always, once a page's oldest updatedAt < START we can
  safely stop: no unseen PR can have merged inside the window.
- Resumable: a `checkpoints` table stores the last GraphQL cursor per repo so a
  re-run continues instead of restarting. Rows are UPSERTed so re-runs are safe.
- Rate-limit aware: watches rateLimit.remaining and sleeps until resetAt.
"""
import json, os, sqlite3, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

START = "2026-04-07T00:00:00Z"
END   = "2026-07-06T23:59:59Z"
REPOS = ["PostHog/posthog", "PostHog/posthog-js", "PostHog/posthog-python"]
DB = os.path.join(os.path.dirname(__file__), "..", "data", "posthog.db")
GQL = "https://api.github.com/graphql"

TOKEN = subprocess.check_output(["gh", "auth", "token"], text=True).strip()

def log(*a):
    print(f"[{datetime.now().strftime('%H:%M:%S')}]", *a, flush=True)

def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GQL, data=body, headers={
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "impactful-engineer-analysis",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read())
            if "errors" in payload:
                # Transient (timeout/complexity) errors -> back off and retry.
                msg = json.dumps(payload["errors"])[:300]
                log("GraphQL errors:", msg)
                time.sleep(5 * (attempt + 1))
                continue
            return payload["data"]
        except urllib.error.HTTPError as e:
            wait = 8 * (attempt + 1)
            if e.code in (502, 503, 403):
                log(f"HTTP {e.code}, retry in {wait}s")
                time.sleep(wait); continue
            raise
        except OSError as e:
            # Covers URLError, TimeoutError, ConnectionResetError and other
            # socket-level failures that occur on long-running pulls.
            log("net error, retry:", e); time.sleep(8 * (attempt + 1))
    raise GqlError("GraphQL failed after retries")

class GqlError(Exception):
    pass

def gql_adaptive(query, variables, sizes):
    """Try the query, shrinking (prFirst, commitFirst) on failure so heavy
    pages (PRs with huge commit/review counts) still complete."""
    last = None
    for prf, cmf in sizes:
        v = dict(variables, prFirst=prf, commitFirst=cmf)
        try:
            return gql(query, v)
        except GqlError as e:
            last = e
            log(f"shrinking page: prFirst={prf} commitFirst={cmf} failed, trying smaller")
    raise last

def respect_rate(rl):
    if rl and rl["remaining"] < 100:
        reset = datetime.fromisoformat(rl["resetAt"].replace("Z", "+00:00"))
        wait = max(0, (reset - datetime.now(timezone.utc)).total_seconds()) + 5
        log(f"rate limit low ({rl['remaining']}), sleeping {int(wait)}s")
        time.sleep(wait)

# ---------------------------------------------------------------- schema
def init_db(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS pull_requests(
        repo TEXT, number INTEGER, title TEXT, body TEXT,
        author_login TEXT, author_name TEXT,
        created_at TEXT, merged_at TEXT, updated_at TEXT,
        additions INTEGER, deletions INTEGER, changed_files INTEGER,
        comments INTEGER, commits_count INTEGER, reviews_count INTEGER,
        labels TEXT, url TEXT,
        PRIMARY KEY(repo, number));
    CREATE TABLE IF NOT EXISTS commits(
        repo TEXT, pr_number INTEGER, oid TEXT, message TEXT,
        author_login TEXT, author_name TEXT, author_email TEXT,
        committed_date TEXT, additions INTEGER, deletions INTEGER,
        PRIMARY KEY(repo, pr_number, oid));
    CREATE TABLE IF NOT EXISTS reviews(
        repo TEXT, pr_number INTEGER, reviewer_login TEXT,
        state TEXT, submitted_at TEXT);
    CREATE TABLE IF NOT EXISTS issues(
        repo TEXT, number INTEGER, title TEXT, body TEXT,
        author_login TEXT, created_at TEXT, closed_at TEXT, state TEXT,
        comments INTEGER, labels TEXT, url TEXT,
        PRIMARY KEY(repo, number));
    CREATE TABLE IF NOT EXISTS checkpoints(
        repo TEXT, kind TEXT, cursor TEXT, done INTEGER DEFAULT 0,
        PRIMARY KEY(repo, kind));
    CREATE INDEX IF NOT EXISTS idx_pr_author ON pull_requests(author_login);
    CREATE INDEX IF NOT EXISTS idx_commit_author ON commits(author_login);
    """)
    con.commit()

PR_QUERY = """
query($owner:String!,$name:String!,$cursor:String,$prFirst:Int!,$commitFirst:Int!){
 repository(owner:$owner,name:$name){
  pullRequests(first:$prFirst,states:MERGED,orderBy:{field:UPDATED_AT,direction:DESC},after:$cursor){
   pageInfo{hasNextPage endCursor}
   nodes{
    number title body createdAt mergedAt updatedAt
    additions deletions changedFiles url
    author{login ... on User{name}}
    labels(first:20){nodes{name}}
    comments{totalCount}
    reviews(first:30){nodes{author{login} state submittedAt}}
    commits(first:$commitFirst){totalCount nodes{commit{
      oid message additions deletions committedDate
      author{name email user{login}}}}}
   }}}
 rateLimit{remaining cost resetAt}}
"""
# Adaptive page sizes: normal first, then progressively lighter for heavy pages.
PR_SIZES = [(15, 50), (6, 30), (3, 15), (1, 15)]

def pull_prs(con, owner, name):
    repo = f"{owner}/{name}"
    row = con.execute("SELECT cursor,done FROM checkpoints WHERE repo=? AND kind='pr'",
                      (repo,)).fetchone()
    if row and row[1]:
        log(f"{repo}: PRs already complete"); return
    cursor = row[0] if row else None
    page = 0
    while True:
        data = gql_adaptive(PR_QUERY, {"owner": owner, "name": name, "cursor": cursor}, PR_SIZES)
        conn = data["repository"]["pullRequests"]
        oldest_updated = None
        for pr in conn["nodes"]:
            oldest_updated = pr["updatedAt"]
            if not (START <= (pr["mergedAt"] or "") <= END):
                continue
            au = pr["author"] or {}
            con.execute("""INSERT OR REPLACE INTO pull_requests VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                repo, pr["number"], pr["title"], pr["body"],
                au.get("login"), au.get("name"),
                pr["createdAt"], pr["mergedAt"], pr["updatedAt"],
                pr["additions"], pr["deletions"], pr["changedFiles"],
                pr["comments"]["totalCount"],
                pr["commits"]["totalCount"], len(pr["reviews"]["nodes"]),
                json.dumps([l["name"] for l in pr["labels"]["nodes"]]),
                pr["url"]))
            for rv in pr["reviews"]["nodes"]:
                ra = rv["author"] or {}
                con.execute("INSERT INTO reviews VALUES (?,?,?,?,?)",
                    (repo, pr["number"], ra.get("login"), rv["state"], rv["submittedAt"]))
            for c in pr["commits"]["nodes"]:
                cm = c["commit"]; ca = cm["author"] or {}; cu = ca.get("user") or {}
                con.execute("INSERT OR REPLACE INTO commits VALUES (?,?,?,?,?,?,?,?,?,?)", (
                    repo, pr["number"], cm["oid"], cm["message"],
                    cu.get("login"), ca.get("name"), ca.get("email"),
                    cm["committedDate"], cm["additions"], cm["deletions"]))
        cursor = conn["pageInfo"]["endCursor"]
        con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)",
                    (repo, "pr", cursor, 0))
        con.commit()
        page += 1
        prcount = con.execute("SELECT COUNT(*) FROM pull_requests WHERE repo=?",(repo,)).fetchone()[0]
        log(f"{repo}: PR page {page}, oldest updated {oldest_updated}, stored={prcount}")
        respect_rate(data["rateLimit"])
        # Stop when we've paged past the window or run out.
        if not conn["pageInfo"]["hasNextPage"] or (oldest_updated and oldest_updated < START):
            break
    con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)", (repo,"pr",cursor,1))
    con.commit()
    log(f"{repo}: PRs DONE")

ISSUE_QUERY = """
query($owner:String!,$name:String!,$cursor:String){
 repository(owner:$owner,name:$name){
  issues(first:50,orderBy:{field:CREATED_AT,direction:DESC},after:$cursor){
   pageInfo{hasNextPage endCursor}
   nodes{number title body createdAt closedAt state url
    author{login} labels(first:20){nodes{name}} comments{totalCount}}}}
 rateLimit{remaining cost resetAt}}
"""

def pull_issues(con, owner, name):
    repo = f"{owner}/{name}"
    row = con.execute("SELECT cursor,done FROM checkpoints WHERE repo=? AND kind='issue'",
                      (repo,)).fetchone()
    if row and row[1]:
        log(f"{repo}: issues already complete"); return
    cursor = row[0] if row else None
    page = 0
    while True:
        data = gql(ISSUE_QUERY, {"owner": owner, "name": name, "cursor": cursor})
        conn = data["repository"]["issues"]
        oldest = None
        for iss in conn["nodes"]:
            oldest = iss["createdAt"]
            if not (START <= iss["createdAt"] <= END):
                continue
            au = iss["author"] or {}
            con.execute("INSERT OR REPLACE INTO issues VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                repo, iss["number"], iss["title"], iss["body"], au.get("login"),
                iss["createdAt"], iss["closedAt"], iss["state"],
                iss["comments"]["totalCount"],
                json.dumps([l["name"] for l in iss["labels"]["nodes"]]), iss["url"]))
        cursor = conn["pageInfo"]["endCursor"]
        con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)", (repo,"issue",cursor,0))
        con.commit()
        page += 1
        log(f"{repo}: issue page {page}, oldest {oldest}")
        respect_rate(data["rateLimit"])
        if not conn["pageInfo"]["hasNextPage"] or (oldest and oldest < START):
            break
    con.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)", (repo,"issue",cursor,1))
    con.commit()
    log(f"{repo}: issues DONE")

def main():
    con = sqlite3.connect(DB)
    init_db(con)
    for full in REPOS:
        owner, name = full.split("/")
        log(f"=== {full} ===")
        pull_issues(con, owner, name)
        pull_prs(con, owner, name)
    log("ALL DONE")
    for t in ("pull_requests","commits","reviews","issues"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        log(f"  {t}: {n}")
    con.close()

if __name__ == "__main__":
    main()
