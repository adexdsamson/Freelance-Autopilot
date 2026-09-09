"""Covers CAP-01/CAP-02 as *structural* guarantees, not conventions.

Lives in the backend suite because that is the project's only test runner and
these checks need no JS toolchain — adding one to assert four facts about a
static manifest would cost more than it returns.

The point of these tests is the ToS constraint from PROJECT.md: capture must
be paste-based, with no live DOM scraping. An extension that never *happens*
to scrape is one code change away from scraping; an extension that holds no
`tabs`/`activeTab`/`scripting` permission structurally cannot, because Chrome
will not let it. That is the property under test.
"""
import json
import re
from pathlib import Path

import pytest

EXTENSION_DIR = Path(__file__).resolve().parent.parent.parent / "extension"

# Permissions that would make reading a live page possible. None may appear.
SCRAPING_PERMISSIONS = {"tabs", "activeTab", "scripting", "webNavigation", "debugger"}


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((EXTENSION_DIR / "manifest.json").read_text())


def test_manifest_is_v3_with_a_service_worker_background(manifest):
    assert manifest["manifest_version"] == 3
    assert manifest["background"]["service_worker"] == "background.js"


def test_extension_holds_no_permission_that_could_read_a_live_page(manifest):
    """CAP-01's no-scraping constraint, enforced by absence of capability."""
    declared = set(manifest.get("permissions", [])) | set(
        manifest.get("optional_permissions", [])
    )
    assert declared & SCRAPING_PERMISSIONS == set()


def test_no_content_scripts_are_declared(manifest):
    """A content script is the other way to read a page's DOM."""
    assert "content_scripts" not in manifest


def test_host_permissions_are_scoped_to_the_backend_origin_only(manifest):
    """CAP-02. `<all_urls>` would trigger Chrome's broad-permission warning
    and grant reach far beyond the one localhost target that is needed."""
    hosts = manifest["host_permissions"]
    assert hosts == ["http://localhost:8000/*"]
    assert "<all_urls>" not in hosts


@pytest.mark.parametrize("filename", ["popup.html", "popup.js", "background.js", "styles.css"])
def test_every_file_the_prd_specifies_exists(filename):
    assert (EXTENSION_DIR / filename).is_file()


def test_popup_html_has_no_inline_script_or_handlers():
    """MV3's content security policy rejects both outright, so a popup that
    relies on either silently does nothing when loaded as an extension."""
    html = (EXTENSION_DIR / "popup.html").read_text()
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "inline <script> block"
    assert not re.search(r"\son[a-z]+\s*=", html), "inline event handler attribute"


def _strip_js_comments(source: str) -> str:
    """Drop // line and /* */ block comments so a comment that merely names a
    forbidden API does not read as a use of it."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def test_popup_never_writes_untrusted_text_as_markup():
    """The posting is untrusted paste and the reasoning is model output;
    both reach the DOM only via textContent."""
    code = _strip_js_comments((EXTENSION_DIR / "popup.js").read_text())
    assert "innerHTML" not in code
    assert "insertAdjacentHTML" not in code


def test_background_registers_its_message_listener_at_the_top_level():
    """The MV3 cold-start rule (Phase 4 SC2): a listener registered after an
    await, or inside another callback, is not attached when the worker
    respawns to deliver the event that woke it. Asserting column 0 is what
    makes that a test rather than a comment."""
    source = (EXTENSION_DIR / "background.js").read_text()
    assert re.search(
        r"^chrome\.runtime\.onMessage\.addListener\(", source, re.MULTILINE
    ), "onMessage listener must be registered at top level, unindented"
