"""Vision extraction: job screenshots -> ExtractedJobFields (CAP-04).

The screenshot capture flow's counterpart to `extract_job_fields`. Where that
one parses pasted text with regexes and is fully deterministic, this one asks
Claude to read the posting off images.

WHY BOTH EXIST — AND WHY PASTE STAYS THE DEMO PATH
---------------------------------------------------
DEMO-02 requires the fixture set to produce identical verdicts across three
runs. A vision call cannot promise that, so this module is deliberately NOT on
the fixture/demo path: `POST /capture` and `/capture/text` still run the
deterministic regex extractor, and every determinism test goes through them.
Screenshots are the live-capture convenience, and the two paths converge on
the same `ExtractedJobFields` the moment extraction is done — so the gate, the
scorecard and the record are identical from there on.

MULTIPLE IMAGES ARE THE POINT
------------------------------
A job posting rarely fits one viewport, and the extension deliberately does
not scroll the page for the user (that would need DOM-injection permission and
reverse the project's no-scraping stance). Instead the user scrolls and
captures each section, and every frame is sent in ONE model call, in order, so
the model reads them as a single continuous posting rather than several
unrelated pictures.
"""
from __future__ import annotations

import base64
import binascii
import os
import re
from typing import Optional

from strands import Agent
from strands.models import BedrockModel

from models.triage import ExtractedJobFields

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Vision extraction is transcription, not judgement — temperature 0 so the
# same screenshots read back the same way as far as the model allows.
EXTRACTION_TEMPERATURE = 0.0

# Bounds. A posting needs a handful of viewports, not a hundred, and an
# unbounded list is both a cost and a payload-size problem.
MAX_SCREENSHOTS = 12
MAX_IMAGE_BYTES = 5 * 1024 * 1024

_DATA_URL_RE = re.compile(r"^data:image/(png|jpeg|jpg|gif|webp);base64,", re.IGNORECASE)
_FORMAT_ALIASES = {"jpg": "jpeg"}

EXTRACTION_SYSTEM_PROMPT = """\
You read freelance job postings out of screenshots and return their fields \
verbatim. The images are consecutive scrolled sections of ONE posting, in \
order — treat them as a single continuous page, and expect overlap between \
consecutive frames.

Rules:
- Transcribe, do not summarise. `description` should carry the posting's real \
requirements, not a précis of them.
- Copy numbers exactly as shown. Never estimate a budget that is not stated.
- budget_type is "hourly" only if the posting shows a rate per hour; "fixed" \
if it shows a project total; "unknown" if no pay is shown at all.
- hire_rate is a fraction: 89% becomes 0.89.
- Leave any field you cannot actually see as null. A missing value must stay \
missing — never guess one, and never substitute zero."""


class ScreenshotExtractionError(ValueError):
    """A readable failure in the screenshot path.

    Names the problem and never echoes image bytes or a raw AWS message
    (T-01-02, carried forward from Phase 1).
    """


def decode_screenshot(value: str) -> tuple[bytes, str]:
    """Turn one data URL or bare base64 string into (bytes, format).

    Returns:
        The raw image bytes and its Bedrock image format ("png", "jpeg", ...).

    Raises:
        ScreenshotExtractionError: empty, malformed, or oversized input.
    """
    if not isinstance(value, str) or not value.strip():
        raise ScreenshotExtractionError("a screenshot entry was empty")

    image_format = "png"
    if match := _DATA_URL_RE.match(value):
        image_format = match.group(1).lower()
        value = value[match.end() :]

    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ScreenshotExtractionError(
            "a screenshot was not valid base64 image data"
        ) from e

    if not raw:
        raise ScreenshotExtractionError("a screenshot decoded to zero bytes")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ScreenshotExtractionError(
            f"a screenshot is {len(raw) // 1024}KB, over the "
            f"{MAX_IMAGE_BYTES // 1024}KB limit"
        )

    return raw, _FORMAT_ALIASES.get(image_format, image_format)


def build_content_blocks(screenshots: list[str]) -> list[dict]:
    """Build the ordered image blocks, with a text block explaining the order.

    Order is load-bearing: the frames are scrolled sections of one page, and
    shuffling them would make the model read the posting out of sequence.
    """
    if not screenshots:
        raise ScreenshotExtractionError("no screenshots were supplied")
    if len(screenshots) > MAX_SCREENSHOTS:
        raise ScreenshotExtractionError(
            f"{len(screenshots)} screenshots supplied, over the "
            f"{MAX_SCREENSHOTS} limit"
        )

    blocks: list[dict] = [
        {
            "text": (
                f"These {len(screenshots)} images are consecutive scrolled "
                f"sections of one job posting, top to bottom. Read them as a "
                f"single page and extract its fields."
            )
        }
    ]
    for value in screenshots:
        raw, image_format = decode_screenshot(value)
        blocks.append({"image": {"format": image_format, "source": {"bytes": raw}}})
    return blocks


def extract_job_fields_from_screenshots(
    screenshots: list[str], agent: Optional[Agent] = None
) -> ExtractedJobFields:
    """Read a posting off one or more screenshots.

    Args:
        screenshots: Ordered data URLs or bare base64 PNG/JPEG strings.
        agent: Injected for tests. When omitted a Bedrock-backed Agent is
            constructed with the pinned model id and region (D-06).

    Returns:
        The same `ExtractedJobFields` the paste path produces, so everything
        downstream — gate, scorecard, record — is identical.

    Raises:
        ScreenshotExtractionError: on bad input or an unreadable model reply.
    """
    blocks = build_content_blocks(screenshots)

    if agent is None:
        agent = Agent(
            model=BedrockModel(
                model_id=MODEL_ID,
                region_name=REGION,
                temperature=EXTRACTION_TEMPERATURE,
            ),
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
        )

    fields = agent.structured_output(ExtractedJobFields, blocks)

    # The model can return a technically-valid but useless record if the
    # screenshots caught the wrong part of the page. Say so plainly rather
    # than letting an empty posting flow into the gate.
    if not fields.title.strip() or not fields.description.strip():
        raise ScreenshotExtractionError(
            "no job title or description was readable in those screenshots — "
            "capture the part of the page showing the posting itself"
        )
    return fields
