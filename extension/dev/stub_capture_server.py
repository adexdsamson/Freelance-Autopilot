"""THROWAWAY dev stub of POST /capture, for exercising the extension only.

This is NOT Phase 3. Phase 3 builds the real endpoint in `backend/api.py`,
wires the Supervisor, and persists an Engagement Record. This file exists
solely so Phase 4's round-trip criterion can be verified before that endpoint
exists, and should be deleted once it does.

It deliberately mirrors the contract the extension expects, so swapping to the
real endpoint is a no-op for the extension:

    POST /capture  {"raw_text": "...", "source_url": "..."}
    ->  {"engagement_id": "...", "job": {...}, "triage": {...}}

Run:
    cd backend && .venv/bin/python ../extension/dev/stub_capture_server.py
    cd backend && .venv/bin/python ../extension/dev/stub_capture_server.py --canned

`--canned` returns a fixed apply-verdict response without calling Bedrock, so
the popup's apply path can be exercised with no AWS credentials. Without it,
the stub runs Phase 2's real `run_triage`: gate-rejected pastes work offline,
gate-passing ones need Bedrock.
"""
import argparse
import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Python puts THIS file's directory on sys.path, not the shell's cwd, so
# backend/ has to be added explicitly however the stub is launched.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from agents.gig_triage_agent import run_triage  # noqa: E402

CANNED = {
    "verdict": "apply",
    "score": 72.5,
    "reasoning": (
        "Clear scope, finalised designs and a well-established client. "
        "Scores — fit 8/10, competition 6/10, rate 7/10 → composite 72.5/100 "
        "(at or above the 60 apply threshold)."
    ),
    "extracted_fields": {
        "title": "Senior React Developer to Rebuild SaaS Analytics Dashboard",
        "description": "Rebuild 14 chart views in React 18 + TypeScript.",
        "budget": 8500.0,
        "budget_type": "fixed",
        "client_stats": {
            "total_spend": 142000.0,
            "hire_rate": 0.89,
            "hires": 45,
            "jobs_posted": 132,
            "payment_verified": True,
        },
    },
}


class Handler(BaseHTTPRequestHandler):
    canned = False

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        # The extension does not need CORS (its service worker bypasses it
        # under host_permissions), but the browser harness in dev/ does.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_POST(self):
        if self.path != "/capture":
            self._send(404, {"detail": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"detail": "body is not JSON"})
            return

        raw_text = (body.get("raw_text") or "").strip()
        if not raw_text:
            self._send(422, {"detail": "raw_text is required"})
            return

        if self.canned:
            result = dict(CANNED)
        else:
            try:
                result = run_triage(raw_text).model_dump()
            except Exception as e:  # noqa: BLE001 - stub: report, never crash
                self._send(502, {"detail": f"triage failed: {type(e).__name__}"})
                return

        extracted = result["extracted_fields"]
        self._send(
            200,
            {
                "engagement_id": str(uuid.uuid4()),
                "job": {
                    "title": extracted["title"],
                    "description": extracted["description"],
                    "budget": extracted["budget"],
                    "client_stats": extracted["client_stats"],
                },
                "triage": {
                    "verdict": result["verdict"],
                    "score": result["score"],
                    "reasoning": result["reasoning"],
                },
                "extracted_fields": extracted,
            },
        )

    def log_message(self, fmt, *args):
        sys.stderr.write("stub /capture: " + (fmt % args) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--canned",
        action="store_true",
        help="return a fixed apply verdict instead of calling Bedrock",
    )
    args = parser.parse_args()

    Handler.canned = args.canned
    mode = "canned" if args.canned else "live run_triage"
    print(f"stub /capture listening on http://localhost:{args.port} ({mode})")
    HTTPServer(("localhost", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
