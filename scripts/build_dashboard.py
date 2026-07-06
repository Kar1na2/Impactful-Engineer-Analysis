#!/usr/bin/env python3
"""Bake data/scorecard.json into a single self-contained dashboard.html.

No external JS/CSS/network calls -> opens instantly (<1s), works offline, and
is a single file you can drop onto GitHub Pages / Netlify as-is.
"""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = json.load(open(os.path.join(ROOT, "data", "scorecard.json")))
OUT = os.path.join(ROOT, "dashboard.html")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PostHog — Most Impactful Engineers (90 days)</title>
<style>
  :root{
    --bg:#0f0f14; --panel:#1a1a23; --panel2:#22222e; --line:#2e2e3d;
    --txt:#eef0f5; --muted:#9aa0b4; --accent:#1d4aff; --gold:#f5c518;
    --npm:#cb3837; --python:#ffd343; --platform:#8b5cf6;
    --c-commits:#4f7cff; --c-lines:#22b8cf; --c-prs:#20c997;
    --c-reviews:#f5c518; --c-issues:#e64980; --c-spike:#ff922b;
  }
  *{box-sizing:border-box} html,body{margin:0}
  body{background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
    line-height:1.5;-webkit-font-smoothing:antialiased}
  a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
  .wrap{max-width:1160px;margin:0 auto;padding:28px 20px 80px}
  header h1{font-size:30px;margin:0 0 6px} .hog{font-size:30px}
  .sub{color:var(--muted);font-size:15px;max-width:760px}
  .pill{display:inline-block;background:var(--panel2);border:1px solid var(--line);
    border-radius:999px;padding:3px 11px;font-size:12px;color:var(--muted);margin:2px 4px 2px 0}
  section{margin-top:34px}
  h2{font-size:19px;margin:0 0 4px} .h2note{color:var(--muted);font-size:13px;margin:0 0 16px}
  /* method strip */
  .method{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
  .m{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px}
  .m .w{font-size:20px;font-weight:700} .m .k{font-size:12px;color:var(--muted);margin-top:2px}
  .m .d{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.35}
  .swatch{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px;vertical-align:middle}
  /* top5 */
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;position:relative}
  .card.r1{border-color:var(--gold);box-shadow:0 0 0 1px var(--gold) inset}
  .rank{position:absolute;top:14px;right:16px;font-size:13px;color:var(--muted)}
  .who{display:flex;align-items:center;gap:12px}
  .ava{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:18px;color:#fff;flex:0 0 46px}
  .name{font-size:18px;font-weight:700} .name a{color:var(--txt)}
  .tag{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:600;margin-left:6px}
  .tag.npm{background:rgba(203,56,55,.18);color:#ff8b8b}
  .tag.python{background:rgba(255,211,67,.16);color:var(--python)}
  .tag.platform{background:rgba(139,92,246,.18);color:#c4b5fd}
  .impact{font-size:34px;font-weight:800;margin:12px 0 2px}
  .impact small{font-size:13px;color:var(--muted);font-weight:500}
  .stack{display:flex;height:16px;border-radius:6px;overflow:hidden;margin:12px 0 6px;background:#000}
  .stack span{height:100%} .leg{font-size:11px;color:var(--muted);margin-bottom:12px}
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}
  .stat{background:var(--panel2);border-radius:8px;padding:8px 9px}
  .stat b{font-size:16px;display:block} .stat span{font-size:11px;color:var(--muted)}
  .why{font-size:13px;color:var(--muted);margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
  /* ranking chart */
  .filters{margin-bottom:12px}
  .fbtn{background:var(--panel2);border:1px solid var(--line);color:var(--muted);
    border-radius:999px;padding:5px 13px;font-size:13px;cursor:pointer;margin-right:6px}
  .fbtn.on{background:var(--accent);border-color:var(--accent);color:#fff}
  .bars{display:flex;flex-direction:column;gap:7px}
  .row{display:grid;grid-template-columns:150px 1fr 52px;align-items:center;gap:10px;font-size:13px}
  .row .nm{color:var(--muted);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .row.top .nm{color:var(--txt);font-weight:600}
  .track{background:var(--panel2);border-radius:6px;height:22px;overflow:hidden}
  .fill{height:100%;display:flex;align-items:center;justify-content:flex-end;
    padding-right:7px;font-size:11px;color:#fff;border-radius:6px;transition:width .4s}
  .sc{text-align:right;font-variant-numeric:tabular-nums;color:var(--muted)}
  /* two col */
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
  .panel h3{margin:0 0 4px;font-size:15px}
  .panel .note{color:var(--muted);font-size:12px;margin:0 0 12px}
  .mini{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--line);font-size:14px}
  .mini:last-child{border-bottom:0} .mini .v{color:var(--muted);font-variant-numeric:tabular-nums}
  .spikebox{background:var(--panel2);border-radius:8px;padding:9px 11px;margin-bottom:8px;font-size:13px}
  .spikebox b{color:var(--c-spike)}
  footer{margin-top:44px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}
  code{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:12px}
  @media(max-width:820px){.method{grid-template-columns:repeat(3,1fr)}.cols{grid-template-columns:1fr}
    .row{grid-template-columns:110px 1fr 46px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1><span class="hog">🦔</span> PostHog — Most Impactful Engineers</h1>
  <div class="sub" id="sub"></div>
  <div style="margin-top:10px" id="pills"></div>
</header>

<section>
  <h2>How impact is scored</h2>
  <p class="h2note">Impact ≠ raw output. Each signal is normalized against the strongest
    contributor (0–100%), then weighted and summed. Reviews-given and download-spike
    activity are weighted to reward cross-team leverage and customer-visible value.</p>
  <div class="method" id="method"></div>
</section>

<section>
  <h2>Top 5 — and why</h2>
  <p class="h2note">Bar under each score shows what the impact is <em>made of</em>.</p>
  <div class="cards" id="cards"></div>
</section>

<section>
  <h2>Full ranking</h2>
  <p class="h2note">All enriched candidates by composite impact. Filter by SDK.</p>
  <div class="filters" id="filters"></div>
  <div class="bars" id="bars"></div>
</section>

<section>
  <div class="cols">
    <div class="panel">
      <h3>npm SDK vs Python SDK</h3>
      <p class="note">Kept distinct per the brief — different codebases, different customers.</p>
      <div id="npmlist"></div>
      <div style="height:14px"></div>
      <div id="pylist"></div>
    </div>
    <div class="panel">
      <h3>Download-spike correlation</h3>
      <p class="note">PRs merged inside the SDK download-growth windows from the README —
        the customer-visible-impact signal.</p>
      <div id="spikes"></div>
    </div>
  </div>
</section>

<footer id="foot"></footer>
</div>

<script>
const DATA = __DATA__;
const CMETA = [
  ["reviews_given","Reviews given","var(--c-reviews)","Reviewed teammates' PRs — cross-team leverage"],
  ["prs","PRs merged","var(--c-prs)","Shipped, review-approved changes"],
  ["commits","Commits","var(--c-commits)","Authored commits in window"],
  ["lines","Code volume","var(--c-lines)","√-weighted lines changed (so big refactors don't dominate)"],
  ["spike","Download-spike PRs","var(--c-spike)","PRs merged during SDK download growth"],
  ["issues","Issues opened","var(--c-issues)","Problems identified & documented"],
];
const CKEY = {reviews_given:"var(--c-reviews)",prs:"var(--c-prs)",commits:"var(--c-commits)",
  lines:"var(--c-lines)",spike:"var(--c-spike)",issues:"var(--c-issues)"};
const SDKCOL = {npm:"var(--npm)",python:"var(--python)",null:"var(--platform)"};
const AVA = ["#1d4aff","#20c997","#f5c518","#e64980","#ff922b","#22b8cf","#8b5cf6"];
const fmt = n => n.toLocaleString();
const sdkClass = s => s ? s : "platform";
const sdkLabel = s => s==="npm"?"npm SDK":s==="python"?"Python SDK":"Platform";

// header
const eng = DATA.engineers, w = DATA.window;
document.getElementById("sub").innerHTML =
  `Ranking PostHog contributors by <b>engineering impact</b> over the 90-day window
   <b>${w.start} → ${w.end}</b>, across the platform monorepo and both SDKs. Impact is a
   composite of shipped work, cross-team review, and correlation with real customer
   download growth — not lines of code.`;
document.getElementById("pills").innerHTML =
  DATA.repos.map(r=>`<span class="pill">${r}</span>`).join("") +
  `<span class="pill">${eng.length} candidates scored</span>`;

// method strip
document.getElementById("method").innerHTML = CMETA.map(([k,label,col,desc])=>{
  const wt = Math.round((DATA.weights[k]||0)*100);
  return `<div class="m"><div class="w">${wt}%</div>
    <div class="k"><span class="swatch" style="background:${col}"></span>${label}</div>
    <div class="d">${desc}</div></div>`;
}).join("");

// top 5 cards
document.getElementById("cards").innerHTML = eng.slice(0,5).map((e,i)=>{
  const stack = CMETA.map(([k])=>{
    const v = e.contrib[k]||0;
    return v>0?`<span title="${k}: ${v} pts" style="width:${v}%;background:${CKEY[k]}"></span>`:"";
  }).join("");
  const top = [...CMETA].map(([k,label])=>[label,e.contrib[k]||0]).sort((a,b)=>b[1]-a[1]);
  const why = whyText(e, top);
  return `<div class="card ${i===0?'r1':''}">
    <div class="rank">#${e.rank}${i===0?' · 🏆':''}</div>
    <div class="who">
      <div class="ava" style="background:${AVA[i%AVA.length]}">${e.login.slice(0,2).toUpperCase()}</div>
      <div><div class="name"><a href="https://github.com/${e.login}" target="_blank">${e.login}</a>
        <span class="tag ${sdkClass(e.primary_sdk)}">${sdkLabel(e.primary_sdk)}</span></div>
        <div style="font-size:12px;color:var(--muted)">${e.primary_repo}</div></div>
    </div>
    <div class="impact">${e.impact}<small> / 100 impact</small></div>
    <div class="stack">${stack}</div>
    <div class="leg">${top.filter(t=>t[1]>0).slice(0,3).map(t=>t[0]+" "+t[1]+"pts").join(" · ")}</div>
    <div class="stats">
      <div class="stat"><b>${fmt(e.prs_merged)}</b><span>PRs merged</span></div>
      <div class="stat"><b>${fmt(e.reviews_given)}</b><span>reviews given</span></div>
      <div class="stat"><b>${fmt(e.commits)}</b><span>commits</span></div>
      <div class="stat"><b>${fmt(e.additions+e.deletions)}</b><span>lines changed</span></div>
      <div class="stat"><b>${e.spike_prs}</b><span>spike-window PRs</span></div>
      <div class="stat"><b>${e.issues_opened}</b><span>issues opened</span></div>
    </div>
    <div class="why">${why}</div>
  </div>`;
}).join("");

function whyText(e, top){
  const lead = top[0][0].toLowerCase();
  const bits = [];
  if(e.spike_prs>=5) bits.push(`merged <b>${e.spike_prs} PRs during the SDK download-growth windows</b> — directly tied to customer-visible value`);
  if(e.reviews_given>=200) bits.push(`gave <b>${fmt(e.reviews_given)} reviews</b>, unblocking teammates across the org`);
  if(e.prs_merged>=300) bits.push(`shipped <b>${fmt(e.prs_merged)} merged PRs</b>`);
  if(e.primary_sdk) bits.push(`anchors the <b>${sdkLabel(e.primary_sdk)}</b>`);
  if(!bits.length) bits.push(`strongest on <b>${lead}</b>`);
  return "Why: " + bits.slice(0,3).join("; ") + ".";
}

// ranking chart
const maxImpact = Math.max(...eng.map(e=>e.impact));
function drawBars(filter){
  const list = eng.filter(e=> filter==="all" ? true :
    filter==="platform" ? !e.primary_sdk : e.primary_sdk===filter);
  document.getElementById("bars").innerHTML = list.map(e=>{
    const wpct = (e.impact/maxImpact)*100;
    const col = SDKCOL[e.primary_sdk];
    return `<div class="row ${e.rank<=5?'top':''}">
      <div class="nm">${e.rank}. ${e.login}</div>
      <div class="track"><div class="fill" style="width:${wpct}%;background:${col}">${e.impact}</div></div>
      <div class="sc">${sdkLabel(e.primary_sdk).replace(' SDK','')}</div></div>`;
  }).join("") || `<div style="color:var(--muted)">No engineers in this group.</div>`;
}
const FILTERS=[["all","All"],["npm","npm SDK"],["python","Python SDK"],["platform","Platform"]];
document.getElementById("filters").innerHTML = FILTERS.map(([k,l],i)=>
  `<button class="fbtn ${i===0?'on':''}" data-f="${k}">${l}</button>`).join("");
document.querySelectorAll(".fbtn").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".fbtn").forEach(x=>x.classList.remove("on"));
  b.classList.add("on"); drawBars(b.dataset.f);
});
drawBars("all");

// SDK lists
function miniList(sdk,title,emptyNote){
  const l = eng.filter(e=>e.primary_sdk===sdk).slice(0,5);
  const head = `<div style="font-weight:600;margin-bottom:4px">${title}</div>`;
  if(!l.length) return head + `<div class="note" style="margin:0">${emptyNote}</div>`;
  return head + l.map(e=>`<div class="mini"><span>${e.login}</span>
      <span class="v">${e.impact} · ${fmt(e.prs_merged)} PRs</span></div>`).join("");
}
document.getElementById("npmlist").innerHTML = miniList("npm","🔴 npm — posthog-js","");
document.getElementById("pylist").innerHTML  = miniList("python","🟡 Python — posthog-python",
  "23 engineers committed in-window, but <b>no dedicated maintainer</b>: " +
  "<a href='https://github.com/marandaneto' target='_blank'>marandaneto</a> led with 73 commits " +
  "(npm-first), then a long tail of 1–7 commits each. A future-development risk — worth a dedicated owner.");
// MCP clarification: active area that lives in the monorepo, not the dormant standalone repo.
document.getElementById("pylist").innerHTML +=
  `<div class="note" style="margin:12px 0 0;border-top:1px solid var(--line);padding-top:10px">
   <b>Note on MCP:</b> the standalone <code>PostHog/mcp</code> repo is dormant (last commit Jan 2026),
   but MCP is actively built <i>inside the monorepo</i> — <b>641 merged MCP PRs</b> in-window
   (top authors: skoob13 81, pauldambra 50, gesh 48, mp-hog 37). It's folded into "Platform" here,
   not broken out as its own lane.</div>`;

// spikes
const sw = DATA.spike_windows;
let spikeHTML = "";
for(const repo in sw){
  const wins = sw[repo].map(x=>x[0]+"→"+x[1]).join(", ");
  spikeHTML += `<div style="font-size:12px;color:var(--muted);margin:4px 0 6px">${repo}: <b>${wins}</b></div>`;
}
const spikers = eng.filter(e=>e.spike_prs>0).sort((a,b)=>b.spike_prs-a.spike_prs).slice(0,6);
spikeHTML += spikers.map(e=>`<div class="spikebox">
  <b>${e.spike_prs}</b> spike-window PRs — <a href="https://github.com/${e.login}" target="_blank">${e.login}</a>
  <span class="tag ${sdkClass(e.primary_sdk)}">${sdkLabel(e.primary_sdk)}</span></div>`).join("");
document.getElementById("spikes").innerHTML = spikeHTML;

// footer
document.getElementById("foot").innerHTML =
  `Data: GitHub <code>stats/contributors</code> + targeted <code>search</code> queries across
   ${DATA.repos.join(", ")}. Window ${w.start}→${w.end}. Bots excluded.
   Generated ${new Date(DATA.generated_at).toISOString().slice(0,16).replace('T',' ')} UTC.
   Impact = Σ(weightₖ · normalizedₖ)·100. Self-contained static file — no network calls on load.`;
</script>
</body>
</html>
"""

def main():
    html = HTML.replace("__DATA__", json.dumps(DATA, separators=(",", ":")))
    with open(OUT, "w") as f:
        f.write(html)
    print(f"wrote {OUT}  ({os.path.getsize(OUT)} bytes)")

if __name__ == "__main__":
    main()
