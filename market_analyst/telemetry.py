from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
import logging
from typing import Any

from market_analyst.config.settings import Settings, load_env_file

load_env_file()

try:
    from opik.integrations.langchain import OpikTracer
except ImportError:  # pragma: no cover - optional dependency fallback
    OpikTracer = None


def configure_notebook_logging(run_name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    logger = logging.getLogger(run_name)
    logger.info("notebook_run_started", extra={"run_name": run_name})
    return logger


def build_langchain_run_config(
    settings: Settings,
    *,
    run_name: str,
    tags: Sequence[str] = (),
    metadata: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Build a LangChain runnable config with Opik tracing when available."""

    config: dict[str, Any] = {
        "run_name": run_name,
        "tags": ["market-analyst", *[tag for tag in tags if tag]],
        "metadata": {"application": "market-analyst", **_compact_metadata(metadata)},
    }
    tracer = build_opik_tracer(settings, tags=config["tags"], metadata=config["metadata"])
    if tracer is not None:
        config["callbacks"] = [tracer]
    return config


def build_opik_tracer(
    settings: Settings,
    *,
    tags: Sequence[str] = (),
    metadata: Mapping[str, object] | None = None,
):
    if not is_opik_enabled(settings) or OpikTracer is None:
        return None
    _configure_opik_environment(settings)
    return OpikTracer(
        project_name=settings.opik_project_name,
        tags=list(tags),
        metadata=dict(_compact_metadata(metadata)),
    )


def invoke_agent_with_tracing(
    agent: Any,
    payload: Any,
    settings: Settings,
    *,
    run_name: str,
    tags: Sequence[str] = (),
    metadata: Mapping[str, object] | None = None,
) -> Any:
    return agent.invoke(
        payload,
        config=build_langchain_run_config(
            settings,
            run_name=run_name,
            tags=tags,
            metadata=metadata,
        ),
    )


def invoke_model_with_tracing(
    model: Any,
    payload: Any,
    settings: Settings,
    *,
    run_name: str,
    tags: Sequence[str] = (),
    metadata: Mapping[str, object] | None = None,
) -> Any:
    return model.invoke(
        payload,
        config=build_langchain_run_config(
            settings,
            run_name=run_name,
            tags=tags,
            metadata=metadata,
        ),
    )


def is_opik_enabled(settings: Settings) -> bool:
    return bool(settings.opik_api_key and settings.opik_workspace)


def _configure_opik_environment(settings: Settings) -> None:
    os.environ.setdefault("OPIK_API_KEY", settings.opik_api_key)
    os.environ.setdefault("OPIK_WORKSPACE", settings.opik_workspace)
    if settings.opik_url_override:
        os.environ.setdefault("OPIK_URL_OVERRIDE", settings.opik_url_override)


def _compact_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    if not metadata:
        return {}
    return {
        str(key): value
        for key, value in metadata.items()
        if value is not None and value != ""
    }
