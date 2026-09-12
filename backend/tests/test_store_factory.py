"""Covers Phase 8 SC1 and SC3: the store is chosen by configuration, and the
local file path survives Phase 8 existing at all.

SC3 is the one that matters most here. AgentCore is the roadmap's explicit
cut-first stretch, and Strands' own docs call the integration
community-maintained and unsupported (research Pitfall 10). So the tests below
assert not just that the file store still works, but that nothing on the file
path can even reach the optional package — an ImportError in
`bedrock_agentcore` must be incapable of taking the demo down.
"""
import ast
from pathlib import Path

import pytest

from store import factory
from store.engagement_store import EngagementStore
from store.factory import build_engagement_store
from store.file_engagement_store import FileEngagementStore

AGENTCORE_ENV = ("ENGAGEMENT_STORE", "AGENTCORE_MEMORY_ID", "AGENTCORE_ACTOR_ID")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in AGENTCORE_ENV + ("ENGAGEMENT_DATA_DIR",):
        monkeypatch.delenv(name, raising=False)


# --- SC3: the local path is the default and cannot be broken by AgentCore ---


def test_default_backend_is_the_local_file_store(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_DATA_DIR", str(tmp_path))
    assert isinstance(build_engagement_store(), FileEngagementStore)


def test_factory_does_not_import_bedrock_agentcore_at_module_scope():
    """The file path must not depend on the optional package being installed.
    An AST check, not a `sys.modules` probe, because another test importing it
    first would make a probe pass for the wrong reason."""
    tree = ast.parse(Path(factory.__file__).read_text())
    module_level = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = []
    for node in module_level:
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif node.module:
            names.append(node.module)
    assert not any(n.startswith("bedrock_agentcore") for n in names)
    assert not any(n.startswith("store.agentcore") for n in names)


def test_agentcore_store_module_is_importable_without_touching_aws():
    """Importing the adapter must not construct a client or resolve creds."""
    from store.agentcore_memory_store import AgentCoreMemoryStore

    assert issubclass(AgentCoreMemoryStore, EngagementStore)


def test_file_store_round_trip_still_works_unchanged(tmp_path, monkeypatch):
    """SC3 proper: Phase 1's behaviour, re-asserted after Phase 8 rewired the
    construction point."""
    from models.engagement_record import EngagementRecord, JobSlice

    monkeypatch.setenv("ENGAGEMENT_DATA_DIR", str(tmp_path))
    store = build_engagement_store()
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    store.create(record)
    assert store.get(record.engagement_id) == record


# --- SC1: swapping is configuration ---


def test_agentcore_backend_is_selected_by_env(monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_STORE", "agentcore")
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "mem-123")

    constructed = {}

    class FakeStore(EngagementStore):
        def __init__(self, **kwargs):
            constructed.update(kwargs)

        def create(self, record):
            return record

        def get(self, engagement_id):
            return None

        def save(self, record):
            return None

    import store.agentcore_memory_store as mod

    monkeypatch.setattr(mod, "AgentCoreMemoryStore", FakeStore)
    build_engagement_store()
    assert constructed["memory_id"] == "mem-123"


def test_agentcore_backend_without_a_memory_id_fails_with_a_readable_error(monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_STORE", "agentcore")
    with pytest.raises(ValueError, match="AGENTCORE_MEMORY_ID"):
        build_engagement_store()


def test_unknown_backend_names_the_valid_options(monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_STORE", "dynamodb")
    with pytest.raises(ValueError, match="file, agentcore"):
        build_engagement_store()


@pytest.mark.parametrize("value", ["FILE", " file ", "File"])
def test_backend_name_is_case_and_whitespace_tolerant(value, tmp_path, monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_STORE", value)
    monkeypatch.setenv("ENGAGEMENT_DATA_DIR", str(tmp_path))
    assert isinstance(build_engagement_store(), FileEngagementStore)


def test_api_obtains_its_store_from_the_factory():
    """SC1's "without any change to agent or API code": api.py names no
    concrete store class, so a new backend needs no edit there."""
    source = Path(__file__).resolve().parent.parent / "api.py"
    text = source.read_text()
    assert "build_engagement_store" in text
    assert "FileEngagementStore()" not in text


def test_local_path_works_end_to_end_with_bedrock_agentcore_uninstalled(tmp_path):
    """SC3's strongest form, and the reason it is a subprocess: the optional
    package is blocked at import time in a fresh interpreter, then api.py, the
    Runtime module and a real file round trip are all exercised. If Phase 8
    were ever abandoned and the dependency dropped, this is what would still
    have to pass.
    """
    import subprocess
    import sys
    from pathlib import Path as _Path

    program = f"""
import sys
class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] == 'bedrock_agentcore':
            raise ImportError('simulated: bedrock_agentcore not installed')
sys.meta_path.insert(0, Blocker())

import api, agentcore_runtime                      # must import cleanly
from store.factory import build_engagement_store
from models.engagement_record import EngagementRecord, JobSlice

store = build_engagement_store()
record = EngagementRecord(job=JobSlice(title='t', description='d'))
store.create(record)
assert store.get(record.engagement_id) == record
print('OK')
"""
    backend_dir = _Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=backend_dir,
        env={
            "PATH": "/usr/bin:/bin",
            "ENGAGEMENT_DATA_DIR": str(tmp_path),
            "PYTHONPATH": str(backend_dir),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
