"""Unit tests for the Anthropic provider. The SDK is replaced by fakes - no network, no key."""
import os
from types import SimpleNamespace

os.environ.setdefault("LLM_PROVIDER", "anthropic")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-not-a-real-key")

import anthropic
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.client import AnthropicLlmClient, LlmProviderError


def _response(text="Hello.", stop_reason="end_turn", model="claude-opus-5-5"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        model=model,
        usage=SimpleNamespace(
            input_tokens=120, output_tokens=30, cache_creation_input_tokens=0, cache_read_input_tokens=100
        ),
        _request_id="req_test",
    )


class _Recorder:
    """Stands in for anthropic.Anthropic and records the call it receives."""

    def __init__(self, response=None, error=None):
        self.calls = []
        self._response, self._error = response or _response(), error
        outer = self

        class _M:
            def create(self, **kw):
                outer.calls.append(("messages.create", kw))
                if outer._error:
                    raise outer._error
                return outer._response

        class _B:
            messages = _M()

        self.messages = _M()
        self.beta = _B()
        # beta.messages.create records under a different name
        outer_beta = outer

        def beta_create(**kw):
            outer_beta.calls.append(("beta.messages.create", kw))
            if outer_beta._error:
                raise outer_beta._error
            return outer_beta._response

        _B.messages = SimpleNamespace(create=beta_create)
        self.beta = _B()


def _client(rec, fallback=True, **kw):
    c = AnthropicLlmClient(model="claude-opus-5-5", api_key="dummy", refusal_fallback=fallback, **kw)
    c._client = rec
    return c


def _api_error(cls, status):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(status, request=req, headers={"retry-after": "7"})
    return cls("boom", response=resp, body=None)


# ---------------------------------------------------------------- request shape
def test_request_shape_system_effort_no_sampling_params():
    rec = _Recorder()
    out = _client(rec, fallback=False).complete_ex(
        [("system", "SYS"), ("user", "hi"), ("assistant", "yo"), ("user", "again")]
    )
    name, kw = rec.calls[0]
    assert name == "messages.create"
    assert kw["model"] == "claude-opus-5-5"
    assert kw["system"][0]["text"] == "SYS" and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert [m["role"] for m in kw["messages"]] == ["user", "assistant", "user"]
    assert kw["output_config"] == {"effort": "medium"}
    # claude-opus-5-5 rejects these with a 400, so they must never be sent
    for forbidden in ("temperature", "top_p", "top_k", "thinking", "tool_choice"):
        assert forbidden not in kw
    assert out.text == "Hello." and out.usage["cache_read_input_tokens"] == 100 and out.request_id == "req_test"


def test_per_request_overrides_and_invalid_effort_falls_back():
    rec = _Recorder()
    c = _client(rec, fallback=False)
    c.complete_ex([("user", "x")], max_tokens=600, effort="low")
    assert rec.calls[-1][1]["max_tokens"] == 600 and rec.calls[-1][1]["output_config"] == {"effort": "low"}
    c.complete_ex([("user", "x")], effort="bogus")
    assert rec.calls[-1][1]["output_config"] == {"effort": "medium"}


def test_refusal_fallback_uses_beta_endpoint():
    rec = _Recorder()
    _client(rec, fallback=True).complete_ex([("user", "x")])
    name, kw = rec.calls[0]
    assert name == "beta.messages.create"
    assert kw["betas"] == ["server-side-fallback-2026-07-01"] and kw["fallbacks"] == "default"


def test_conversation_must_start_with_user_and_blank_messages_dropped():
    rec = _Recorder()
    _client(rec, fallback=False).complete_ex([("assistant", "stray"), ("user", ""), ("user", "q")])
    assert [m["content"] for m in rec.calls[0][1]["messages"]] == ["q"]


def test_no_user_content_is_a_400():
    with pytest.raises(LlmProviderError) as e:
        _client(_Recorder(), fallback=False).complete_ex([("system", "only system")])
    assert e.value.status_code == 400


# ---------------------------------------------------------------- response handling
def test_refusal_stop_reason_becomes_422():
    rec = _Recorder(_response(text="", stop_reason="refusal"))
    with pytest.raises(LlmProviderError) as e:
        _client(rec, fallback=False).complete_ex([("user", "x")])
    assert e.value.status_code == 422 and e.value.category == "refused"


def test_empty_text_is_502():
    rec = _Recorder(_response(text="   "))
    with pytest.raises(LlmProviderError) as e:
        _client(rec, fallback=False).complete_ex([("user", "x")])
    assert e.value.status_code == 502


def test_max_tokens_truncation_is_returned_not_raised():
    rec = _Recorder(_response(text="partial", stop_reason="max_tokens"))
    out = _client(rec, fallback=False).complete_ex([("user", "x")])
    assert out.text == "partial" and out.stop_reason == "max_tokens"


# ---------------------------------------------------------------- error translation
@pytest.mark.parametrize(
    "cls,status,expect_status,expect_cat",
    [
        (anthropic.RateLimitError, 429, 429, "rate_limited"),
        (anthropic.AuthenticationError, 401, 502, "provider_auth"),
        (anthropic.PermissionDeniedError, 403, 502, "provider_auth"),
        (anthropic.NotFoundError, 404, 502, "model_unavailable"),
        (anthropic.BadRequestError, 400, 400, "bad_request"),
        (anthropic.InternalServerError, 529, 503, "overloaded"),
    ],
)
def test_error_translation(cls, status, expect_status, expect_cat):
    rec = _Recorder(error=_api_error(cls, status))
    with pytest.raises(LlmProviderError) as e:
        _client(rec, fallback=False).complete_ex([("user", "x")])
    assert (e.value.status_code, e.value.category) == (expect_status, expect_cat)
    # no secrets / internals in the user-facing message
    assert "dummy" not in e.value.message and "boom" not in e.value.message


def test_rate_limit_carries_retry_after():
    rec = _Recorder(error=_api_error(anthropic.RateLimitError, 429))
    with pytest.raises(LlmProviderError) as e:
        _client(rec, fallback=False).complete_ex([("user", "x")])
    assert e.value.retry_after == 7


def test_timeout_and_connection_errors():
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    with pytest.raises(LlmProviderError) as e:
        _client(_Recorder(error=anthropic.APITimeoutError(request=req)), fallback=False).complete_ex([("user", "x")])
    assert e.value.status_code == 504
    with pytest.raises(LlmProviderError) as e:
        _client(_Recorder(error=anthropic.APIConnectionError(request=req)), fallback=False).complete_ex([("user", "x")])
    assert e.value.status_code == 503


# ---------------------------------------------------------------- HTTP layer / provider switch
def test_http_complete_contract_is_backward_compatible(monkeypatch):
    monkeypatch.setattr(main, "_client", _client(_Recorder(), fallback=False))
    r = TestClient(main.app).post("/complete", json={"messages": [{"role": "user", "content": "hi"}]})
    body = r.json()
    assert r.status_code == 200 and body["text"] == "Hello."          # original contract
    assert body["provider"] == "anthropic" and body["usage"]["output_tokens"] == 30  # additive metadata


def test_http_error_never_leaks_credentials(monkeypatch):
    monkeypatch.setattr(main, "_client", _client(_Recorder(error=_api_error(anthropic.AuthenticationError, 401)), fallback=False))
    r = TestClient(main.app).post("/complete", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 502 and "dummy" not in r.text and "sk-ant" not in r.text


def test_http_rate_limit_sets_retry_after_header(monkeypatch):
    monkeypatch.setattr(main, "_client", _client(_Recorder(error=_api_error(anthropic.RateLimitError, 429)), fallback=False))
    r = TestClient(main.app).post("/complete", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 429 and r.headers["retry-after"] == "7"


def test_provider_switch(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    c = main.build_client()
    assert isinstance(c, AnthropicLlmClient) and c._model == "claude-sonnet-5-5"
    monkeypatch.setenv("LLM_PROVIDER", "nonsense")
    with pytest.raises(RuntimeError):
        main.build_client()
