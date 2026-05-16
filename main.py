from __future__ import annotations

import uvicorn

from market_analyst.api.app import app


def main() -> None:
    uvicorn.run("market_analyst.api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
