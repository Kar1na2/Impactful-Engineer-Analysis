# Findings — Most Impactful PostHog Engineers (Apr 7 → Jul 6, 2026)

**Interactive dashboard:** [`dashboard.html`](./dashboard.html) — a single self-contained
file (no network calls, loads in <1s). Hosted copy served via GitHub Pages.

> **Impact ≠ raw output.** Lines of code and commit counts don't tell the full story
> (per the [README](./README.md)). Every signal below is normalized against the strongest
> contributor (0–100%), then weighted so that **cross-team leverage** (reviews given to
> teammates) and **customer-visible value** (work merged during real SDK download-growth
> windows) count more than sheer volume.

---

## TL;DR — Top 5

| # | Engineer | Impact /100 | What made them impactful |
|---|----------|:-----------:|--------------------------|
| 1 | **[pauldambra](https://github.com/pauldambra)** | 62.6 | The org's connective tissue — 276 reviews given *and* 633 PRs merged; sustained top-tier output across the platform while still shipping 11 PRs during the npm download surge. |
| 2 | **[marandaneto](https://github.com/marandaneto)** | 60.4 | The SDK anchor. Highest reviews-given (282) of anyone, and **24 PRs merged inside the download-spike windows** — more than 2× anyone else. The single strongest link between engineering work and customer-visible growth. |
| 3 | **[Gilbert09](https://github.com/Gilbert09)** | 58.0 | Sheer platform throughput: 972 merged PRs / 907 commits, paired with 259 reviews. Volume that is also reviewed and shipped, not just committed. |
| 4 | **[andrewm4894](https://github.com/andrewm4894)** | 42.2 | High cross-team leverage (242 reviews) plus the most **issues opened** (12) of the leaders — strong at *identifying and documenting problems*, a README impact criterion. Touches both SDKs. |
| 5 | **[richardsolomou](https://github.com/richardsolomou)** | 32.6 | Largest code footprint of all candidates (~112k lines changed, √-weighted) with solid review engagement; contributed to both SDKs during spike windows. |

---

## Methodology

### Data (fetch layer)
- **Source:** GitHub `GET /repos/{repo}/stats/contributors` (one call per repo → per-author
  weekly commits / additions / deletions) plus targeted `search` queries per candidate.
  This replaces pulling ~10,000 individual PRs with a handful of aggregate calls.
- **Repos:** `PostHog/posthog` (platform monorepo), `PostHog/posthog-js` (npm SDK),
  `PostHog/posthog-python` (PyPI SDK). The SDK repos are included because the download
  trends the README analyzes come from the SDKs, not the platform monorepo.
- **Window:** 2026-04-07 → 2026-07-06 (90 days). Bots excluded
  (`github-actions`, `dependabot`, `posthog-bot`, `renovate`, Claude, etc.).
- **Pool:** 188 non-bot contributors were active in-window; the top 27 were deep-enriched.
  The candidate pool is the union of *top-by-total-commits* **and** *top contributors within
  each SDK repo*, so SDK specialists aren't drowned out by the far larger monorepo.

### Impact score (scoring layer)
`impact = Σ (weightₖ · normalizedₖ) · 100`, where each metric is divided by the max across
candidates. Weights:

| Signal | Weight | Rationale |
|--------|:------:|-----------|
| Reviews given to others | **25%** | Impact "in the lens of another engineer" — unblocking teammates is leverage, not solo output. |
| PRs merged | 20% | Shipped, review-approved changes. |
| Commits | 15% | Authored work in-window. |
| Lines changed (√-weighted) | 15% | `√(add+del)` so a 3,000-line refactor doesn't automatically beat ten sharp 50-line fixes. |
| **Download-spike PRs** | 15% | PRs merged inside the README's SDK download-growth windows — the customer-visible-impact signal. |
| Issues opened | 10% | Concretely identifying/documenting problems. |

### Presentation layer
The scored result is a ~29 KB `data/scorecard.json`, baked directly into a single
self-contained `dashboard.html`. No live GitHub calls happen on load — that's the
difference between a 10-second and a sub-1-second dashboard.

---

## Step 1–2 — Download-trend correlation

Engineers with PRs merged inside the README's SDK download-growth windows
(npm posthog-js: May 31 → Jun 14; PyPI posthog-python: Jun 13 → Jun 17 & Jun 25 → Jun 28):

| Engineer | Spike-window PRs | Primary area |
|----------|:----------------:|--------------|
| **marandaneto** | 24 | npm SDK |
| pauldambra | 11 | platform |
| dustinbyrne | 8 | npm SDK |
| turnipdabeets | 7 | npm SDK |
| ioannisj | 5 | npm SDK |
| lucasheriques | 5 | platform |

**Takeaway:** the download surges correlate most strongly with **marandaneto** and a cluster
of **npm-SDK specialists** (dustinbyrne, turnipdabeets, ioannisj). This is the clearest
engineering→customer-value link in the dataset and is why marandaneto ranks #2 overall
despite a fraction of Gilbert09's raw commit count.

---

## Step 4 — npm SDK vs Python SDK (kept separate)

**npm SDK (`posthog-js`) — has dedicated specialists:**

| Engineer | Impact | PRs merged | Spike PRs |
|----------|:------:|:----------:|:---------:|
| marandaneto | 60.4 | 213 | 24 |
| dustinbyrne | 25.7 | 48 | 8 |
| ioannisj | 25.7 | 35 | 5 |
| turnipdabeets | 23.1 | 61 | 7 |

**Python SDK (`posthog-python`) — active, but no dedicated maintainer.** 23 non-bot engineers
committed to `posthog-python` in-window (it was *not* idle), but none has it as their *primary*
repo. Work is concentrated in **marandaneto (73 commits — the most, and he's npm-first)**, then a
long tail of 1–7 commits each. **This is itself a finding:** the Python SDK is maintained
opportunistically rather than owned, a candidate area for the README's "notable exceptions"
(future-development risk) — worth a dedicated owner.

### A note on MCP
The standalone **`PostHog/mcp`** repo (the official MCP server) is **dormant** — 0 commits / 0
merged PRs in-window, last touched 2026-01-19. But MCP is very much active: it's built **inside
the monorepo**, with **641 merged MCP-titled PRs** in the window and a dedicated `team-mcp-analytics`.
Top MCP authors: **skoob13 (81)**, pauldambra (50), **gesh (48)**, mp-hog (37), sampennington (32).
MCP is *not* broken out as its own lane in this analysis — those PRs are counted under "Platform" —
so MCP specialists like **skoob13** and **gesh** are under-credited relative to their customer-facing
impact. Treating MCP as a distinct area (like the SDKs) is the clearest next iteration.

---

## Caveats & data-quality notes

- **GitHub `stats/contributors` returns 0 additions/deletions for some contributors** (a known
  API quirk on very large repos). Gilbert09 and rnegron show 0 lines despite 900+/200+ commits,
  so their `lines` signal is understated. Because `lines` is only 15% and normalized, the
  overall ranking is unaffected at the top, but their true code volume is higher than shown.
- **The platform monorepo dwarfs the SDKs in raw commit volume**, so an unadjusted top-by-commits
  list is platform-heavy. The SDK-inclusive candidate pool and the review/spike weighting correct
  for this.
- **`reviews given` uses `reviewed-by:<user> -author:<user>`** (reviews on *other people's* PRs),
  approximating cross-team help rather than self-review.
- Impact scores are *relative* to this candidate pool and window — they rank engineers against
  each other, not on an absolute scale.

---

## Reproducibility

```bash
# 1. Fetch aggregate stats + targeted search, compute scores -> data/scorecard.json
python3 scripts/build_scorecard.py

# 2. Bake scorecard.json into the self-contained dashboard
python3 scripts/build_dashboard.py
```

Raw download data: `posthog_downloads.json` (PyPI) and npmtrends (see README).
Requires an authenticated `gh` CLI.
