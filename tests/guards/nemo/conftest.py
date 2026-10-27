"""NeMo tests run only with the extra installed, and strictly offline: the Hugging Face
hub is forced offline so the embedding model NeMo uses for intent examples must already
be cached, otherwise the module is skipped."""

import os

import pytest

pytest.importorskip("nemoguardrails", reason="needs: uv sync --extra nemo")

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
