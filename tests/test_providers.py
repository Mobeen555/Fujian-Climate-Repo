"""Offline adapter checks. Mock responses are not a claim of live provider access."""
import json
from types import SimpleNamespace
import pytest
from ai_providers import PROVIDERS, validate_connection
import crew_runtime as runtime


@pytest.mark.parametrize("provider", list(PROVIDERS))
def test_provider_request_is_minimal_and_audited(provider, monkeypatch):
    sent = []
    monkeypatch.setattr(runtime, "reserve_rate_slot", lambda *a, **k: None)
    def post(url, **kwargs):
        sent.append((url, kwargs))
        return SimpleNamespace(status_code=200, json=lambda: {
            "model": "returned-model-id", "choices": [{"message": {"content": "Final Answer: QA only"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8}})
    monkeypatch.setattr(runtime.requests, "post", post)
    budget=runtime.RunBudget();events=[]
    llm=runtime.ProviderEvidenceLLM("qa-private-key", PROVIDERS[provider]["model"], budget,
                                    events.append, provider=provider)
    llm.call([{"role":"system","content":"QA", "cache_breakpoint": True}])
    url, request=sent[0]
    assert url == PROVIDERS[provider]["base_url"] + "/chat/completions"
    assert request["json"]["messages"] == [{"role":"system","content":"QA"}]
    assert request["allow_redirects"] is False
    assert "tools" not in request["json"]
    token_field="max_completion_tokens" if provider=="groq" else "max_tokens"
    assert token_field in request["json"]
    if provider=="gemini": assert request["json"]["reasoning_effort"]=="low"
    assert budget.actual_models==["returned-model-id"]
    assert budget.prompt_tokens==12 and budget.completion_tokens==8
    assert "qa-private-key" not in llm.model_dump_json()
    assert "qa-private-key" not in json.dumps(events)


def test_paid_openrouter_and_untrusted_endpoints_are_rejected():
    with pytest.raises(ValueError, match=":free"):
        validate_connection("openrouter", "paid/model")
    for endpoint in ["http://remote.example/v1", "https://user:secret@example.com/v1", "https://example.com/v1?key=abc"]:
        with pytest.raises(ValueError):validate_connection("ollama", "model", endpoint)
    assert validate_connection("gemini","test-model","https://untrusted.example/v1")==PROVIDERS["gemini"]["base_url"]
    with pytest.raises(runtime.CrewRunError,match="API key"):
        runtime.ProviderEvidenceLLM("","model",provider="ollama",base_url="https://example.com/v1")
    assert runtime.ProviderEvidenceLLM("","model",provider="ollama")


def test_request_pacing_respects_selected_rpm(monkeypatch):
    clock=[100.]
    monkeypatch.setattr(runtime.time,"monotonic",lambda:clock[0])
    monkeypatch.setattr(runtime.time,"sleep",lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    runtime._RATE_BUCKETS.clear()
    budget=runtime.RunBudget(seconds=200)
    runtime.reserve_rate_slot("unique-qa",100,10000,budget,requests_per_minute=1)
    runtime.reserve_rate_slot("unique-qa",100,10000,budget,requests_per_minute=1)
    assert clock[0]>=161
    runtime._RATE_BUCKETS.clear()


@pytest.mark.parametrize("status",[401,402,403,404,429,503])
def test_provider_error_is_sanitized_and_not_retried(status, monkeypatch):
    count=[]
    monkeypatch.setattr(runtime,"reserve_rate_slot",lambda *a,**k:None)
    def post(*a,**k):
        count.append(1)
        return SimpleNamespace(status_code=status,json=lambda:{"secret":"provider-internal-body"})
    monkeypatch.setattr(runtime.requests,"post",post)
    llm=runtime.ProviderEvidenceLLM("qa-key",PROVIDERS["gemini"]["model"])
    with pytest.raises(runtime.CrewRunError) as error:llm.call("QA")
    assert len(count)==1
    assert "provider-internal-body" not in str(error.value)
    assert "qa-key" not in str(error.value)
