"""Covers the screenshot capture path (CAP-04) and `/capture/text`.

The Bedrock vision call is stubbed throughout. That is not avoidance — it is
the only way to assert the parts that must hold regardless of what a model
answers: that multiple screenshots reach the model in order and in one call,
that bad input fails readably rather than as a 500, and that the screenshot
path converges on exactly the same gate/merge/store path as paste.

Determinism note: `/capture/screenshots` is deliberately NOT on the fixture or
demo path (DEMO-02) precisely because a vision call cannot be deterministic.
`/capture/text` is, and keeps using the regex extractor.
"""
import base64

import pytest
from fastapi.testclient import TestClient

import api
from models.triage import ClientStats, ExtractedJobFields
from tools import extract_from_screenshots as vision
from tools.extract_from_screenshots import (
    MAX_SCREENSHOTS,
    ScreenshotExtractionError,
    build_content_blocks,
    decode_screenshot,
    extract_job_fields_from_screenshots,
)

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n fake image bytes").decode()
DATA_URL = f"data:image/png;base64,{PNG}"

GOOD_FIELDS = ExtractedJobFields(
    title="Senior React Developer",
    description="Rebuild 14 chart views in React 18 with a clear checklist.",
    budget=8500.0,
    budget_type="fixed",
    client_stats=ClientStats(total_spend=142000.0, hire_rate=0.89, payment_verified=True),
)


class FakeVisionAgent:
    """Records what it was asked; answers with a fixed extraction."""

    def __init__(self, fields=GOOD_FIELDS):
        self.fields = fields
        self.calls = []

    def structured_output(self, output_model, prompt):
        self.calls.append((output_model, prompt))
        return self.fields


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGAGEMENT_DATA_DIR", str(tmp_path))
    api._store = None  # rebuild the store against tmp_path
    yield TestClient(api.app)
    api._store = None


# --- decoding -------------------------------------------------------------


def test_bare_base64_and_data_urls_both_decode():
    assert decode_screenshot(PNG)[1] == "png"
    assert decode_screenshot(DATA_URL)[1] == "png"


def test_jpeg_data_url_reports_jpeg_and_jpg_is_normalised():
    assert decode_screenshot(f"data:image/jpeg;base64,{PNG}")[1] == "jpeg"
    assert decode_screenshot(f"data:image/jpg;base64,{PNG}")[1] == "jpeg"


@pytest.mark.parametrize("bad", ["", "   ", "not base64!!!", None])
def test_unusable_screenshot_input_is_a_named_error(bad):
    with pytest.raises(ScreenshotExtractionError):
        decode_screenshot(bad)


def test_an_oversized_screenshot_is_rejected_with_its_size(monkeypatch):
    monkeypatch.setattr(vision, "MAX_IMAGE_BYTES", 10)
    with pytest.raises(ScreenshotExtractionError, match="over the"):
        decode_screenshot(PNG)


# --- multi-image assembly: the heart of "capture the whole page" ----------


def test_every_screenshot_becomes_its_own_image_block_in_order():
    a = base64.b64encode(b"first").decode()
    b = base64.b64encode(b"second").decode()
    blocks = build_content_blocks([a, b])
    assert list(blocks[0]) == ["text"]  # the ordering instruction
    assert blocks[1]["image"]["source"]["bytes"] == b"first"
    assert blocks[2]["image"]["source"]["bytes"] == b"second"


def test_the_lead_text_block_tells_the_model_the_frames_are_one_page():
    text = build_content_blocks([PNG, PNG, PNG])[0]["text"]
    assert "3 images" in text
    assert "one job posting" in text


def test_no_screenshots_is_a_named_error():
    with pytest.raises(ScreenshotExtractionError, match="no screenshots"):
        build_content_blocks([])


def test_too_many_screenshots_is_refused_rather_than_silently_truncated():
    with pytest.raises(ScreenshotExtractionError, match="over the"):
        build_content_blocks([PNG] * (MAX_SCREENSHOTS + 1))


def test_all_frames_go_in_a_single_model_call():
    """One call, not one per image — otherwise the model never sees the
    posting as a continuous page."""
    agent = FakeVisionAgent()
    extract_job_fields_from_screenshots([PNG, PNG, PNG], agent=agent)
    assert len(agent.calls) == 1
    _, prompt = agent.calls[0]
    assert sum(1 for block in prompt if "image" in block) == 3


def test_extraction_returns_the_same_type_the_paste_path_produces():
    """Both routes converge on ExtractedJobFields, so the gate and scorecard
    downstream cannot tell them apart."""
    fields = extract_job_fields_from_screenshots([PNG], agent=FakeVisionAgent())
    assert isinstance(fields, ExtractedJobFields)
    assert fields.title == "Senior React Developer"


def test_screenshots_of_the_wrong_part_of_the_page_fail_with_advice():
    blank = ExtractedJobFields(title="   ", description="")
    with pytest.raises(ScreenshotExtractionError, match="capture the part of the page"):
        extract_job_fields_from_screenshots([PNG], agent=FakeVisionAgent(blank))


# --- endpoints ------------------------------------------------------------


def test_capture_screenshots_returns_a_verdict(client, monkeypatch):
    monkeypatch.setattr(
        vision, "extract_job_fields_from_screenshots", lambda s: GOOD_FIELDS
    )
    monkeypatch.setattr(api, "extract_job_fields_from_screenshots", lambda s: GOOD_FIELDS)
    response = client.post("/capture/screenshots", json={"screenshots": [DATA_URL]})
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] in ("apply", "skip")
    assert body["engagement_id"]


def test_captured_record_is_persisted_and_readable(client, monkeypatch):
    monkeypatch.setattr(api, "extract_job_fields_from_screenshots", lambda s: GOOD_FIELDS)
    captured = client.post("/capture/screenshots", json={"screenshots": [DATA_URL]}).json()
    fetched = client.get(f"/engagements/{captured['engagement_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["job"]["title"] == "Senior React Developer"


def test_an_unreadable_screenshot_is_a_422_not_a_500(client):
    response = client.post("/capture/screenshots", json={"screenshots": ["not base64!!!"]})
    assert response.status_code == 422


def test_an_empty_screenshot_list_is_rejected_by_validation(client):
    assert client.post("/capture/screenshots", json={"screenshots": []}).status_code == 422


def test_a_bedrock_failure_becomes_a_readable_503(client, monkeypatch):
    def explode(_screenshots):
        raise RuntimeError("boom AKIA-secret")

    monkeypatch.setattr(api, "extract_job_fields_from_screenshots", explode)
    response = client.post("/capture/screenshots", json={"screenshots": [DATA_URL]})
    assert response.status_code == 503
    assert "AKIA-secret" not in response.text


def test_capture_text_accepts_what_the_extension_actually_sends(client):
    """Regression: the extension posted {raw_text} at /capture, which expects a
    JobSlice, so every paste capture 422'd after the Phase 2/4 merge."""
    response = client.post(
        "/capture/text",
        json={
            "raw_text": (
                "Senior React Developer\nEst. Budget: $8,500\nRebuild the dashboard.\n"
                "About the client\n$142K total spent\n89% hire rate"
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["verdict"] in ("apply", "skip")


def test_capture_text_extracts_the_budget_deterministically(client):
    """The paste route keeps the regex extractor, which is what lets DEMO-02
    promise identical runs."""
    body = {"raw_text": "A Job\nEst. Budget: $4,200\nWork to do."}
    first = client.post("/capture/text", json=body).json()
    second = client.post("/capture/text", json=body).json()
    assert first["verdict"] == second["verdict"]
    assert first["score"] == second["score"]
    assert first["reasoning"] == second["reasoning"]


def test_empty_paste_is_rejected(client):
    assert client.post("/capture/text", json={"raw_text": "   "}).status_code == 422
