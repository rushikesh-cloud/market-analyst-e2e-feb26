# News Analysis Agent

## Goal

Add a notebook-validated news analysis worker that uses Tavily Search through LangChain to collect recent company and sector news, classify favorable and adverse developments, and produce a sentiment score.

## Scope

- Add Tavily API configuration and provider construction.
- Add typed news-agent request/result objects.
- Add a LangChain `create_agent`-based news worker service using Tavily Search.
- Add `06_news_agent.ipynb` as the thin notebook runner.
- Add focused tests that avoid live Tavily and Azure calls.

## Verification

- Compile changed Python modules.
- Validate notebook JSON and code-cell syntax.
- Run focused news-agent tests.
