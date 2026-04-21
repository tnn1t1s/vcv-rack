from agent.doctor import describe_environment, render_environment


def test_describe_environment_exposes_repo_runtime_basics():
    info = describe_environment()
    assert info["repo_root"].endswith("vcv-rack")
    assert info["env_path"].endswith("agent/.env")
    assert info["supported_module_count"] > 0
    assert "doctor" in info["commands"]
    assert "agent" in info["commands"]


def test_render_environment_mentions_canonical_commands():
    rendered = render_environment(describe_environment())
    assert "uv run vcv-agent-doctor" in rendered
    assert "uv run vcv-agent" in rendered
    assert "Start from the repo root" in rendered
