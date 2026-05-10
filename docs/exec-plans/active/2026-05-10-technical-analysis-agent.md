# Technical Analysis Agent

## Goal

Add a separate notebook-validated technical analysis agent that fetches ticker price history, generates a technical chart, and sends that chart to an Azure OpenAI multimodal chat deployment to answer chart-specific questions.

## Scope

- Add typed technical-analysis request/artifact/result objects.
- Add a market-data provider using `yfinance`.
- Add indicator and chart generation services using Pandas and Matplotlib.
- Add a multimodal technical agent service.
- Add `05_technical_agent.ipynb` as the thin notebook runner.
- Add focused tests that avoid live market-data and Azure calls.

## Verification

- Compile changed Python modules.
- Validate notebook JSON and code-cell syntax.
- Run focused technical-agent tests.
