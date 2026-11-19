from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from langchaingov.llm import make_chat_model
from langchaingov.settings import Settings


def test_make_chat_model_uses_settings() -> None:
    settings = Settings(
        base_url="http://example.test:4000/v1",
        model="fake-llama",
        api_key="sk-test",
        temperature=0.3,
    )
    model = make_chat_model(settings)
    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "http://example.test:4000/v1"
    assert model.model_name == "fake-llama"
    assert model.temperature == 0.3
    assert isinstance(model.openai_api_key, SecretStr)
    assert model.openai_api_key.get_secret_value() == "sk-test"


def test_make_chat_model_model_override() -> None:
    settings = Settings(model="fake-llama", api_key="sk-test")
    model = make_chat_model(settings, model="other-model")
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "other-model"


def test_make_chat_model_pins_request_params() -> None:
    settings = Settings(model="m", api_key="sk-test")
    model = make_chat_model(settings, max_tokens=1024, timeout=600, seed=7, max_retries=0)
    assert isinstance(model, ChatOpenAI)
    assert (model.max_tokens, model.request_timeout, model.seed, model.max_retries) == (
        1024,
        600,
        7,
        0,
    )


def test_make_chat_model_leaves_client_defaults_alone() -> None:
    model = make_chat_model(Settings(model="m", api_key="sk-test"))
    assert isinstance(model, ChatOpenAI)
    assert (model.max_tokens, model.request_timeout, model.seed) == (None, None, None)
