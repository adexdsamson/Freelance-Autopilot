"""Throwaway spike: prove Bedrock connectivity works, or fail fast with a
readable diagnosis. Standalone script — never imported by api.py (D-08).

D-06: BedrockModel(model_id=..., region_name=...) is constructed explicitly
(never a bare model-id string passed to Agent(model=...)), so the model id
and region are visible in code and env-driven.

Construction alone proves nothing (Pitfall 2, RESEARCH.md) — credential and
model-access errors only surface on the first real invoke_model call, so
main() always makes one real (cheap) call before declaring success.

main() must NEVER raise: it returns 0 (reachable) or 1 (a readable failure).
strands' BedrockModel re-raises Bedrock throttling / context-overflow as its
own exception types (plain Exception subclasses), and botocore network
timeouts are siblings of EndpointConnectionError under BotoCoreError, so we
branch on those explicitly for good diagnostics AND keep a final catch-all so
no unexpected exception type can ever escape as a raw traceback. Failure
messages print only the error *type/Code* and a static remediation string —
never the raw AWS Message text (which can echo request context / secrets).
"""
import os
import sys

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)
from strands import Agent
from strands.models import BedrockModel
from strands.types.exceptions import (
    ContextWindowOverflowException,
    ModelThrottledException,
)

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def _fail(message: str) -> int:
    """Print a readable, secret-free diagnostic to stderr and return 1."""
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
        agent = Agent(model=model)
        result = agent("Reply with exactly: PONG")
        print(f"PASS: Bedrock reachable in {REGION} with model {MODEL_ID}")
        print(f"Response: {result}")
        return 0
    except NoCredentialsError:
        return _fail(
            "no AWS credentials found. Run `aws configure` or export "
            "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN."
        )
    except ClientError as e:
        # Only the error Code (never the raw Message) is surfaced.
        code = e.response.get("Error", {}).get("Code", "Unknown")
        if code == "AccessDeniedException":
            return _fail(
                f"credentials valid but no Bedrock model access for {MODEL_ID} "
                f"in {REGION}. Enable it in the Bedrock console's 'Model access' "
                f"page for this account/region."
            )
        if code == "UnrecognizedClientException":
            return _fail(
                "AWS credentials present but invalid/expired "
                "(UnrecognizedClientException). Check AWS_ACCESS_KEY_ID/"
                "AWS_SECRET_ACCESS_KEY are current."
            )
        if code == "ValidationException":
            return _fail(
                f"ValidationException — likely a wrong model id format for "
                f"{REGION} (bare foundation-model id vs. required "
                f"inference-profile id, e.g. 'us.anthropic...'). Check "
                f"BEDROCK_MODEL_ID."
            )
        if code in ("ThrottlingException", "TooManyRequestsException"):
            return _fail(
                f"Bedrock throttled the request ({code}) in {REGION}. Retry "
                f"with backoff or request a quota increase."
            )
        return _fail(f"Bedrock ClientError [{code}]. See the Bedrock console.")
    except (ConnectTimeoutError, ReadTimeoutError):
        return _fail(
            f"timed out talking to the Bedrock endpoint in {REGION} "
            f"(slow/blocked network)."
        )
    except EndpointConnectionError:
        return _fail(
            f"could not reach the Bedrock endpoint in {REGION} "
            f"(network/DNS issue, or the region has no Bedrock endpoint)."
        )
    except ModelThrottledException:
        return _fail(
            f"Bedrock throttled the model invocation in {REGION} "
            f"(ModelThrottledException). Retry with backoff."
        )
    except ContextWindowOverflowException:
        return _fail(
            "the prompt exceeded the model's context window "
            "(ContextWindowOverflowException) — unexpected for a PONG probe; "
            "check the model id."
        )
    except BotoCoreError as e:
        # Any other botocore-layer error (config, endpoint resolution, etc.).
        return _fail(f"AWS SDK error ({type(e).__name__}) talking to Bedrock.")
    except Exception as e:  # noqa: BLE001 — final safety net: main() must never raise
        # Unknown/unexpected failure type. Surface the class name only (never
        # the message, which could echo credentials or request context).
        return _fail(
            f"unexpected error contacting Bedrock ({type(e).__name__}). "
            f"This is a diagnosable failure, not a crash."
        )


if __name__ == "__main__":
    sys.exit(main())
