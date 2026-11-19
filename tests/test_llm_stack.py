"""The local model stack's configs and scripts agree with each other. No network."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from langchaingov.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
MODELFILE = ROOT / "infra" / "ollama" / "llama3.2-3b-32k.Modelfile"
LITELLM_CONFIG = ROOT / "infra" / "litellm" / "config.yaml"
LIB = ROOT / "scripts" / "llm" / "lib.sh"
SCRIPTS = sorted((ROOT / "scripts" / "llm").glob("*.sh"))


def lib_default(name: str) -> str:
    """The default in a ``NAME="${NAME:-default}"`` line of lib.sh."""
    match = re.search(rf'^{name}="\$\{{{name}:-(.+)\}}"', LIB.read_text(), re.MULTILINE)
    assert match, f"{name} default not found in lib.sh"
    return match.group(1)


def modelfile_value(keyword: str) -> str:
    """``FROM`` takes one value; ``PARAMETER`` lines are looked up as ``PARAMETER <name>``."""
    for line in MODELFILE.read_text().splitlines():
        parts = line.split()
        if parts[:1] == [keyword] and len(parts) == 2:
            return parts[1]
        if parts[:2] == keyword.split() and len(parts) == 3:
            return parts[2]
    raise AssertionError(f"{keyword} not found in {MODELFILE.name}")


@pytest.fixture
def local_model() -> dict[str, Any]:
    config = yaml.safe_load(LITELLM_CONFIG.read_text())
    assert len(config["model_list"]) == 1
    entry: dict[str, Any] = config["model_list"][0]
    return entry


def test_served_context_matches_litellm_metadata(local_model: dict[str, Any]) -> None:
    num_ctx = int(modelfile_value("PARAMETER num_ctx"))
    assert num_ctx == local_model["model_info"]["max_input_tokens"]


def test_modelfile_builds_on_the_base_model_the_scripts_pull() -> None:
    assert modelfile_value("FROM") == lib_default("OLLAMA_BASE_MODEL")


def test_litellm_routes_to_the_tag_the_scripts_build(local_model: dict[str, Any]) -> None:
    params = local_model["litellm_params"]
    assert params["model"] == f"ollama_chat/{lib_default('OLLAMA_TAG')}"
    assert params["api_base"] == lib_default("OLLAMA_URL")
    assert local_model["model_name"] == lib_default("LLM_MODEL_NAME")


def test_env_example_defaults_to_the_local_model(local_model: dict[str, Any]) -> None:
    env_example = (ROOT / ".env.example").read_text()
    match = re.search(r"^LANGCHAINGOV_MODEL=(\S+)$", env_example, re.MULTILINE)
    assert match
    assert match.group(1) == local_model["model_name"]


def test_proxy_port_matches_the_default_base_url() -> None:
    assert f":{lib_default('LLM_PORT')}/" in Settings.model_fields["base_url"].default


def test_master_key_is_read_from_the_environment() -> None:
    config = yaml.safe_load(LITELLM_CONFIG.read_text())
    assert config["general_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_script_parses(script: Path) -> None:
    result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_all_stack_scripts_are_present() -> None:
    assert {p.name for p in SCRIPTS} == {"lib.sh", "up.sh", "down.sh", "status.sh", "smoke.sh"}
