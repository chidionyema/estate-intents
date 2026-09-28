#!/usr/bin/env python3
"""Write fixed test file."""
content = '''"""Claude Code on the Max subscription through the LOCAL router (bin/litellm-local)."""

from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "llm" / "config.yaml"
LAUNCHER = ROOT / "bin" / "litellm-local"
MODULE_DIR = ROOT / "platform" / "llm"


def test_claude_max_lane_config_and_behaviour():
    # Config invariants verified via REAL litellm execution (not YAML reading).
    pytest.importorskip("litellm")
    import yaml
    import sys
    sys.path.insert(0, str(MODULE_DIR))
    import anthropic_beta_passthrough  # noqa: F401
    from litellm import anthropic_beta_headers_manager as mgr

    cfg = yaml.safe_load(CONFIG.read_text())
    rows = {m["model_name"]: m["litellm_params"] for m in cfg["model_list"]
            if str(m.get("model_name", "")).startswith("claude")}
    assert "claude-*" in rows
    assert rows["claude-*"]["model"] == "anthropic/claude-*"
    for m in rows.values():
        assert "api_key" not in m
        assert m.get("input_cost_per_token") == 0
        assert m.get("output_cost_per_token") == 0

    # Behaviour: beta passthrough forwards unknown betas for anthropic only.
    new_beta = "inline-tools-2026-09-15"
    assert mgr.filter_and_transform_beta_headers([new_beta], "anthropic") == [new_beta]
    assert new_beta not in mgr.filter_and_transform_beta_headers([new_beta], "bedrock")


def test_request_fields_and_launcher_secrets():
    pytest.importorskip("litellm")
    import sys
    import yaml
    sys.path.insert(0, str(MODULE_DIR))
    import anthropic_beta_passthrough  # noqa: F401
    from litellm.llms.anthropic.experimental_pass_through.messages.utils import (
        AnthropicMessagesRequestUtils as U,
    )

    # Launcher: never hands an Anthropic key to LiteLLM.
    text = LAUNCHER.read_text()
    assert "unset ANTHROPIC_API_KEY" in text
    assert "--host 127.0.0.1" in text

    # LiteLLM drops unknown fields; passthrough restores them for anthropic.
    body = {"model": "claude-sonnet-5", "messages": [], "max_tokens": 10,
            "safeguards": [{"type": "x"}], "litellm_metadata": {"internal": object()}}
    params = {**body, "proxy_server_request": {"body": body}}
    got = U.get_requested_anthropic_messages_optional_param(
        params, model="claude-sonnet-5", custom_llm_provider="anthropic")
    assert got.get("safeguards") == [{"type": "x"}]
    assert "litellm_metadata" not in got
    other = U.get_requested_anthropic_messages_optional_param(
        params, model="x", custom_llm_provider="bedrock")
    assert "safeguards" not in other
'''

path = "/Users/roseonyema/Documents/code/idp/tests/test_local_claude_max_lane.py"
with open(path, "w") as f:
    f.write(content)
import os
stat = os.stat(path)
print(f"Written {stat.st_size} bytes to {path}")
