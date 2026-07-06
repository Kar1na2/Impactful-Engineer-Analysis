#!/usr/bin/env python3
"""
Aggregate-first impact scorecard for PostHog engineers (90-day window).

Architecture (fetch -> score -> tiny JSON):
  1. FETCH  /repos/{repo}/stats/contributors  (1 call/repo) -> per-author weekly
            commits/additions/deletions. Filter to the 90-day window.
            Then a handful of targeted `search` calls per *candidate* only.
  2. SCORE  composite impact = weighted blend of commits, sqrt(lines changed),
            PRs merged, reviews GIVEN to others, issues opened, and a bonus for
            PRs merged during the download-spike windows (customer-visible impact).
  3. EMIT   data/scorecard.json  (a few KB) -> baked into the static dashboard.

Honours README.md: impact != raw output. Reviews-given and download-spike
activity are weighted to reward cross-team leverage and customer-visible value,
and npm-SDK (posthog-js) vs Python-SDK (posthog-python) work is kept distinct.
"""
import json, math, os, subprocess, time
from datetime import datetime, timezone

REPOS = ["PostHog/posthog", "PostHog/posthog-js", "PostHog/posthog-python"]
SDK_OF = {"PostHog/posthog-js": "npm", "PostHog/posthog-python": "python"}
START = "2026-04-07"
END = "2026-07-06"
WIN_START_TS = datetime(2026, 4, 5, tzinfo=timezone.utc).timestamp()   # week of Apr 7
WIN_END_TS = datetime(2026, 7, 7, tzinfo=timezone.utc).timestamp()
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "scorecard.json")

# Download-spike windows from README (repo -> list of (start, end) merge windows).
SPIKE_WINDOWS = {
    "PostHog/posthog-js": [("2026-05-31", "2026-06-14")],           # sharp npm incline
    "PostHog/posthog-python": [("2026-06-13", "2026-06-17"),        # python growth
                               ("2026-06-25", "2026-06-28")],       # python growth
}

BOT_MARKERS = ("[bot]", "-bot", "dependabot", "github-actions", "posthog-bot",
               "renovate", "snyk", "sweep")
def is_bot(login):
    if not login:
        return True
    l = login.lower()
    return l == "claude" or any(m in l for m in BOT_MARKERS)

def api(args):
    return json.loads(subprocess.check_output(["gh", "api"] + args, text=True))

_last_search = [0.0]
def search_count(q):
    """search/issues total_count, throttled to stay under 30 req/min."""
    dt = time.time() - _last_search[0]
    if dt < 2.2:
        time.sleep(2.2 - dt)
    _last_search[0] = time.time()
    for attempt in range(5):
        try:
            out = api(["-X", "GET", "search/issues", "--raw-field", f"q={q}",
                       "--jq", ".total_count"])
            return int(out)
        except subprocess.CalledProcessError:
            time.sleep(5 * (attempt + 1))
    return 0

def stats_contributors(repo):
    """Fetch weekly contributor stats, retrying while GitHub computes (202)."""
    for attempt in range(15):
        raw = subprocess.check_output(["gh", "api", f"repos/{repo}/stats/contributors"], text=True)
        data = json.loads(raw)
        if data:
            return data
        print(f"  {repo}: stats computing (202), retry...", flush=True)
        time.sleep(4)
    return []

# ------------------------------------------------------------------ FETCH
def collect():
    eng = {}   # login -> aggregate record
    for repo in REPOS:
        print(f"[fetch] {repo} stats/contributors", flush=True)
        for c in stats_contributors(repo):
            login = (c.get("author") or {}).get("login")
            if is_bot(login):
                continue
            commits = adds = dels = 0
            for w in c["weeks"]:
                if WIN_START_TS <= w["w"] <= WIN_END_TS:
                    commits += w["c"]; adds += w["a"]; dels += w["d"]
            if commits == 0 and adds == 0 and dels == 0:
                continue
            e = eng.setdefault(login, {"login": login, "commits": 0, "adds": 0,
                "dels": 0, "repos": {}, "prs": 0, "reviews_given": 0, "issues": 0,
                "spike_prs": 0})
            e["commits"] += commits; e["adds"] += adds; e["dels"] += dels
            e["repos"][repo] = {"commits": commits, "adds": adds, "dels": dels}
    return eng

# ------------------------------------------------------------------ ENRICH
def enrich(eng, top_n=18, sdk_n=8):
    # Candidate pool = top by TOTAL commits (platform-heavy) UNION the top
    # contributors WITHIN each SDK repo. The union guarantees SDK specialists get
    # scored even though the monorepo dwarfs the SDKs in raw commit volume --
    # essential because the README treats SDK work as customer-visible impact.
    ranked = sorted(eng.values(), key=lambda e: e["commits"], reverse=True)
    pool = {e["login"]: e for e in ranked[:top_n]}
    for repo in SDK_OF:
        sdk_ranked = sorted((e for e in eng.values() if repo in e["repos"]),
                            key=lambda e: e["repos"][repo]["commits"], reverse=True)
        for e in sdk_ranked[:sdk_n]:
            pool[e["login"]] = e
    candidates = list(pool.values())
    print(f"[enrich] {len(candidates)} candidates via targeted search", flush=True)
    for i, e in enumerate(candidates, 1):
        u = e["login"]
        for repo in e["repos"]:
            e["prs"] += search_count(f"repo:{repo} author:{u} is:pr is:merged merged:{START}..{END}")
            e["reviews_given"] += search_count(f"repo:{repo} reviewed-by:{u} is:pr is:merged merged:{START}..{END} -author:{u}")
            e["issues"] += search_count(f"repo:{repo} author:{u} is:issue created:{START}..{END}")
            for (s, en) in SPIKE_WINDOWS.get(repo, []):
                e["spike_prs"] += search_count(f"repo:{repo} author:{u} is:pr is:merged merged:{s}..{en}")
        e["enriched"] = True
        print(f"  ({i}/{len(candidates)}) {u}: prs={e['prs']} reviews={e['reviews_given']} issues={e['issues']} spike={e['spike_prs']}", flush=True)
    return candidates

# ------------------------------------------------------------------ SCORE
WEIGHTS = {"commits": 0.15, "lines": 0.15, "prs": 0.20,
           "reviews_given": 0.25, "issues": 0.10, "spike": 0.15}

def score(candidates):
    def raw(e):
        return {"commits": e["commits"], "lines": math.sqrt(e["adds"] + e["dels"]),
                "prs": e["prs"], "reviews_given": e["reviews_given"],
                "issues": e["issues"], "spike": e["spike_prs"]}
    raws = {e["login"]: raw(e) for e in candidates}
    maxes = {k: max((r[k] for r in raws.values()), default=0) or 1 for k in WEIGHTS}
    for e in candidates:
        r = raws[e["login"]]
        comp = {k: (r[k] / maxes[k]) for k in WEIGHTS}
        e["components"] = comp                       # normalized 0..1 per metric
        e["contrib"] = {k: round(WEIGHTS[k] * comp[k] * 100, 2) for k in WEIGHTS}
        e["impact"] = round(sum(e["contrib"].values()), 2)
        # Primary area (README step 4): tie the SDK label to where the engineer
        # actually spends most of their commits, so platform engineers who merely
        # touch an SDK aren't mislabelled as SDK owners.
        e["primary_repo"] = max(e["repos"], key=lambda r: e["repos"][r]["commits"])
        e["primary_sdk"] = SDK_OF.get(e["primary_repo"])           # None => platform
        # Secondary signal: did they contribute to an SDK at all this window?
        e["sdk_touched"] = sorted({SDK_OF[r] for r in e["repos"] if r in SDK_OF})
    candidates.sort(key=lambda e: e["impact"], reverse=True)
    return candidates

def main():
    eng = collect()
    print(f"[fetch] {len(eng)} non-bot contributors with in-window activity", flush=True)
    candidates = enrich(eng)
    ranked = score(candidates)
    clean = []
    for rank, e in enumerate(ranked, 1):
        clean.append({
            "rank": rank, "login": e["login"], "impact": e["impact"],
            "commits": e["commits"], "additions": e["adds"], "deletions": e["dels"],
            "prs_merged": e["prs"], "reviews_given": e["reviews_given"],
            "issues_opened": e["issues"], "spike_prs": e["spike_prs"],
            "primary_sdk": e["primary_sdk"], "primary_repo": e["primary_repo"],
            "sdk_touched": e["sdk_touched"],
            "components": e["components"], "contrib": e["contrib"],
            "repos": e["repos"],
        })
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start": START, "end": END},
        "repos": REPOS,
        "weights": WEIGHTS,
        "spike_windows": SPIKE_WINDOWS,
        "engineers": clean,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[emit] {OUT}  ({os.path.getsize(OUT)} bytes)")
    print("\nTOP 10:")
    for e in clean[:10]:
        print(f"  {e['rank']:2}. {e['login']:24} impact={e['impact']:6}  "
              f"commits={e['commits']:4} prs={e['prs_merged']:3} "
              f"revs={e['reviews_given']:3} spike={e['spike_prs']:2} sdk={e['primary_sdk']}")

if __name__ == "__main__":
    main()
