"""The single construction point for the Engagement Record store (D-02).

Phase 1 promised that switching persistence would be "a config change, not a
rewrite". This module is where that promise is kept: callers ask for
`build_engagement_store()` and never name a concrete class, so Phase 8's
AgentCore backend arrives without a line changing in the agents or the API.

SC3 — the local path must survive this phase being abandoned — is why the
default is `file` and why nothing here imports `bedrock_agentcore` at module
scope. With `ENGAGEMENT_STORE` unset, or the optional package uninstalled,
this module behaves exactly as it did before Phase 8 existed.
"""
from __future__ import annotations

import os
from pathlib import Path

from store.engagement_store import EngagementStore
from store.file_engagement_store import FileEngagementStore

FILE_BACKEND = "file"
AGENTCORE_BACKEND = "agentcore"
VALID_BACKENDS = (FILE_BACKEND, AGENTCORE_BACKEND)

DEFAULT_BACKEND = FILE_BACKEND
DEFAULT_DATA_DIR = Path("data/engagements")


def build_engagement_store() -> EngagementStore:
    """Construct the configured store.

    Environment:
        ENGAGEMENT_STORE:     "file" (default) or "agentcore"
        ENGAGEMENT_DATA_DIR:  file backend only; defaults to data/engagements
        AGENTCORE_MEMORY_ID:  agentcore backend only; required
        AGENTCORE_ACTOR_ID:   agentcore backend only; optional
        AWS_REGION:           agentcore backend only; optional

    Raises:
        ValueError: on an unrecognised backend, or a missing memory id.
    """
    backend = os.environ.get("ENGAGEMENT_STORE", DEFAULT_BACKEND).strip().lower()

    if backend == FILE_BACKEND:
        return FileEngagementStore(
            base_dir=Path(os.environ.get("ENGAGEMENT_DATA_DIR", DEFAULT_DATA_DIR))
        )

    if backend == AGENTCORE_BACKEND:
        memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "").strip()
        if not memory_id:
            raise ValueError(
                "ENGAGEMENT_STORE=agentcore requires AGENTCORE_MEMORY_ID to be "
                "set to an existing AgentCore Memory resource id. Unset "
                "ENGAGEMENT_STORE to fall back to the local file store."
            )
        # Imported here, not at module scope: the file path must not depend on
        # the optional AgentCore package being installed (SC3).
        from store.agentcore_memory_store import AgentCoreMemoryStore

        kwargs = {"memory_id": memory_id, "region_name": os.environ.get("AWS_REGION")}
        actor_id = os.environ.get("AGENTCORE_ACTOR_ID", "").strip()
        if actor_id:
            kwargs["actor_id"] = actor_id
        return AgentCoreMemoryStore(**kwargs)

    raise ValueError(
        f"unknown ENGAGEMENT_STORE {backend!r}. Valid values: "
        f"{', '.join(VALID_BACKENDS)}."
    )
