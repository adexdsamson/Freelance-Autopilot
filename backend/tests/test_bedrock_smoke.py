"""Covers ORC-03 (fail-fast half): the Bedrock connectivity smoke test must
never raise, must return 0 or 1, and must never leak the sandbox's
placeholder credential literal into its output (T-01-02). In this sandbox
(placeholder AWS credentials, no real Bedrock access) the fail-fast branch
returning 1 IS the designed PASS per D-08 — not a failure."""
from scripts import smoke_test_bedrock_connectivity


def test_main_returns_int_in_0_or_1_and_never_raises_and_never_leaks_credentials(capsys):
    return_code = smoke_test_bedrock_connectivity.main()

    captured = capsys.readouterr()

    assert return_code in (0, 1)
    if return_code == 1:
        assert "FAIL:" in captured.err
    assert "proxy-injected" not in captured.out
    assert "proxy-injected" not in captured.err
