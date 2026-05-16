# Technical Agent V2

## Goal

Add a separate technical-analysis V2 path that uses LangChain `create_agent` plus chart-generation tools to build dynamic candlestick charts and summarize MACD, RSI, and Bollinger Bands without changing the current V1 worker.

## Scope

- Add separate V2 request/artifact/result contracts.
- Add a separate charting module for dynamic indicator computation and candlestick rendering.
- Add a separate LangChain technical V2 agent with tool-calling around chart generation and multimodal analysis.
- Add a thin `05_technical_agent_v2.ipynb` notebook for manual validation.
- Add focused tests that avoid live Azure and market-data calls.

## Verification

- Compile changed Python modules.
- Run focused V2 technical-agent tests.
- Validate the new notebook JSON and code-cell syntax.

## Notes

- V1 stays unchanged.
- V2 is a parallel evaluation surface intended for later replacement of V1 after parity validation.
