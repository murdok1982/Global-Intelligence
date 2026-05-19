# OSINT Provider Plugins (P3 — not yet implemented)

`OSINTAgent` orchestrates a collection of plugins, each adapting one
public data source to the platform's signal schema. None of these
plugins ship yet — the agent raises `NotImplementedError` rather
than returning mock data, because fabricated intelligence is worse
than no intelligence.

## Planned plugin layout

```
app/agents/providers/osint/
    __init__.py          # plugin registry
    newsapi.py           # https://newsapi.org
    rss.py               # generic RSS / Atom feeds
    gdelt.py             # https://www.gdeltproject.org
    worldbank.py         # macro indicators
    imf.py               # IMF SDMX API
```

Every plugin must:

* Subclass a small `BaseOSINTProvider` abstract class (to be added
  in P3) and implement `async def fetch(country_iso: str) -> list[Signal]`.
* Be configurable purely through environment variables — no
  credentials checked into source control.
* Return signals tagged with `classification=PUBLIC` and a real
  source URL.

## Why this is gated to P3

Real OSINT plugins require source-by-source legal review (terms of
service, robots.txt, rate limits, licensing of the resulting
dataset). Mocking that with stub data risks shipping fabricated
intelligence behind a "real" looking endpoint.
