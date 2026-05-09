from __future__ import annotations

import logging


def configure_notebook_logging(run_name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    logger = logging.getLogger(run_name)
    logger.info("notebook_run_started", extra={"run_name": run_name})
    return logger
