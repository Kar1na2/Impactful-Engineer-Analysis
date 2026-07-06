## Events 

From notable dates addressed in `README.md` 

we have npm trend highlighting these 2 date ranges
- May 17 - 31 
- May 31 - June 14 

from PyPI we have
- June 13 - 17 
- June 25 - 28

Using good friend Claude (mainly because of time constraints, by the time I'm writing this I'm past the 45 minute point), I ran a correlation from version releases and change logs to the dates and for npm we have the following 

- **May 17 - 31** 
    - "Nothing that stands out as note-worthy — a steady stream of routine patch/minor releases: dead-click CSS opt-out, `flag_keys` scoping, tracing-header fixes for XHR, rrweb package exposure, session-recording polling fix, cookieless request-queue fix. On the node side: local-flag-evaluation edge case fixes, `identifyImmediate` await fix, exception-capture unification. All normal maintenance cadence, no major feature or breaking change."

- **May 31 - June 14** 
    - "Same pattern — `persistence_save_debounce_ms`, browser-detection additions (Brave, Vivaldi, Yandex, etc.), `$sdk_dist_channel` property, `split_storage` config, `tracing_headers` promoted to public API, `$is_server` property on node. Again: incremental, nothing that reads as a hook for a download surge."

and for PyPI we have 

- **June 13 - 17** 
    - we have 2 releases on June 15 with the following features 
        - adds opt-in client-side rate limiting for exception autocapture (bringing Python in line with posthog-js / posthog-node) 
        - typing / annotation cleanup (no functional change) 
    - 1 release on June 17, v7.19.2 
        - bumped default background flush interval to 5s 

- **June 25 - 28** 
    - on June 26 with version 7.21.0, `posthog.mcp` has been added as a dedicated Python SDK for PostHog MCP analytics 


## **Next steps** 

With this information I'll be moving to step 3 immediately for npm contributors whereas for Python Package contributors I'll closely examine the contributors for the MCP as well as those that worked on v7.19.0 and v7.19.1 

## **Isssues and fixes** 

A hindsight I had was wanting to aggregate the entire PRs and Issues from the repo within the last 90 days which costed me about 10 minutes before realizing how barbaric that approach was, I'm going to instead have 3 different layers. 
- It'll be divded using Fetch, Aggregation, and Presentation layer 

Even though the MCP for Python SDK was released for the Python Package, the actual development of MCP was done in the monorepo instead of on the specific MCP repo nor in the Python repository. 
- addressed in the website on why engineers are not presented in the Python SDK group 