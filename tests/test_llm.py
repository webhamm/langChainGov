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
