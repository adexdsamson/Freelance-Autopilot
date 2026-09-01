"""Throwaway spike: prove Bedrock connectivity works, or fail fast with a
readable diagnosis. Standalone script — never imported by api.py (D-08).

D-06: BedrockModel(model_id=..., region_name=...) is constructed explicitly
(never a bare model-id string passed to Agent(model=...)), so the model id
and region are visible in code and env-driven.

Construction alone proves nothing (Pitfall 2, RESEARCH.md) — credential and
model-access errors only surface on the first real invoke_model call, so
main() always makes one real (cheap) call before declaring success.
"""
import os
import sys

from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
from strands import Agent
from strands.models import BedrockModel

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def main() -> int:
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(model=model)
    try:
        result = agent("Reply with exactly: PONG")
        print(f"PASS: Bedrock reachable in {REGION} with model {MODEL_ID}")
        print(f"Response: {result}")
        return 0
    except NoCredentialsError:
        print(
            "FAIL: no AWS credentials found. Run `aws configure` or export "
            "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN.",
            file=sys.stderr,
        )
        return 1
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", str(e))
        if code == "AccessDeniedException":
            print(
                f"FAIL: credentials valid but no Bedrock model access for "
                f"{MODEL_ID} in {REGION}. Enable it in the Bedrock console's "
                f"'Model access' page for this account/region.",
                file=sys.stderr,
            )
        elif code == "UnrecognizedClientException":
            print(
                "FAIL: AWS credentials present but invalid/expired "
                "(UnrecognizedClientException). Check AWS_ACCESS_KEY_ID/"
                "AWS_SECRET_ACCESS_KEY are current.",
                file=sys.stderr,
            )
        elif code == "ValidationException":
            print(
                f"FAIL: ValidationException — likely wrong model id format "
                f"for {REGION} (bare foundation-model id vs. required "
                f"inference-profile id, e.g. 'us.anthropic...'). Message: {msg}",
                file=sys.stderr,
            )
        else:
            print(f"FAIL: Bedrock ClientError [{code}]: {msg}", file=sys.stderr)
        return 1
    except EndpointConnectionError as e:
        print(
            f"FAIL: could not reach the Bedrock endpoint in {REGION} "
            f"(network/DNS issue): {e}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
