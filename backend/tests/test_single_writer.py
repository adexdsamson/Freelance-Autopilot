"""Enforces REC-03 / D-05: no module under agents/ or tools/ may import the
store. Only FastAPI (the API layer, later phases) is allowed to call
EngagementStore.save — agents/tools return typed data and never touch
persistence directly. This is a static/import-graph check via Python's
`ast` module, not a regex/text search (a grep-equivalent would false-positive
on docstrings/comments that merely mention "store" and miss aliased or
dynamic imports).
"""
import ast
from pathlib import Path

FORBIDDEN_MODULE_PREFIXES = ("store", "backend.store")
SCAN_DIRS = ["agents", "tools"]


def _imported_module_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_agent_or_tool_module_imports_store():
    # backend/ — this test file's parent's parent.
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for dir_name in SCAN_DIRS:
        scan_dir = repo_root / dir_name
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            imported = _imported_module_names(py_file)
            for module in imported:
                if any(module == p or module.startswith(p + ".") for p in FORBIDDEN_MODULE_PREFIXES):
                    violations.append(f"{py_file}: imports '{module}'")
    assert not violations, (
        "REC-03 violation — agent/tool modules must never import the store "
        "directly:\n" + "\n".join(violations)
    )
