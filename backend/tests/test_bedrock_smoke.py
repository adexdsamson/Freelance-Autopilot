"""Covers ORC-03 (fail-fast half): the Bedrock connectivity smoke test must
never raise, must return 0 or 1, and must never leak the sandbox's
placeholder credential literal into its output (T-01-02). In this sandbox
(placeholder AWS credentials, no real Bedrock access) the fail-fast branch
returning 1 IS the designed PASS per D-08 — not a failure."""
import pytest

from scripts import smoke_test_bedrock_connectivity
from strands.types.exceptions import ModelThrottledException


def test_main_returns_int_in_0_or_1_and_never_raises_and_never_leaks_credentials(capsys):
    return_code = smoke_test_bedrock_connectivity.main()

    captured = capsys.readouterr()

    assert return_code in (0, 1)
    if return_code == 1:
        assert "FAIL:" in captured.err
    assert "proxy-injected" not in captured.out
    assert "proxy-injected" not in captured.err


@pytest.mark.parametrize(
    "raised",
    [
        ModelThrottledException("throttled"),  # strands re-raise (plain Exception subclass)
        RuntimeError("some entirely unexpected failure"),  # final safety net
    ],
)
def test_main_never_raises_on_throttling_or_unexpected_errors(monkeypatch, capsys, raised):
    """The blocking case: strands re-raises Bedrock throttling as its own
    (non-botocore) exception, and unknown failures must not escape either.
    main() must convert both into a readable exit-1, never a raw traceback."""

    class _FakeModel:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeAgent:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            raise raised

    monkeypatch.setattr(smoke_test_bedrock_connectivity, "BedrockModel", _FakeModel)
    monkeypatch.setattr(smoke_test_bedrock_connectivity, "Agent", _FakeAgent)

    # Must not raise.
    return_code = smoke_test_bedrock_connectivity.main()

    captured = capsys.readouterr()
    assert return_code == 1
    assert "FAIL:" in captured.err
