import pytest
import httpx
from fastapi import HTTPException
from app import ai
from types import SimpleNamespace

@pytest.mark.anyio
async def test_missing_key():
    old=ai.settings.openai_api_key;ai.settings.openai_api_key=''
    try:
        with pytest.raises(HTTPException) as e: await ai.complete(None,[])
        assert e.value.status_code==503
    finally:ai.settings.openai_api_key=old

@pytest.fixture
def anyio_backend(): return 'asyncio'

@pytest.mark.anyio
@pytest.mark.parametrize('payload,status',[
    ({'choices':[{'message':{'content':'Hello'}}],'usage':{'prompt_tokens':10,'completion_tokens':2}},200),
    ({'choices':[]},502),
    ({'choices':[{'message':{'content':'Hello'}}],'usage':{'prompt_tokens':-1,'completion_tokens':2}},502)])
async def test_provider_protocol(monkeypatch,payload,status):
    monkeypatch.setattr(ai.settings,'openai_api_key','test-only-key')
    real_client=httpx.AsyncClient
    def handler(request):
        assert request.url.path.endswith('/chat/completions')
        assert request.headers['authorization']=='Bearer test-only-key'
        return httpx.Response(200,json=payload)
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    agent=SimpleNamespace(model='model',temperature=0.5,max_tokens=10)
    if status==200: assert await ai.complete(agent,[])==('Hello',10,2)
    else:
        with pytest.raises(HTTPException) as e: await ai.complete(agent,[])
        assert e.value.status_code==status

@pytest.mark.anyio
async def test_local_ollama_needs_no_key_and_sends_no_credentials(monkeypatch):
    monkeypatch.setattr(ai.settings,'ai_provider','local')
    monkeypatch.setattr(ai.settings,'openai_base_url','http://ollama:11434/v1')
    # Even an accidentally retained cloud key must never be sent to a local model.
    monkeypatch.setattr(ai.settings,'openai_api_key','must-not-be-forwarded')
    real_client=httpx.AsyncClient
    def handler(request):
        assert str(request.url)=='http://ollama:11434/v1/chat/completions'
        assert 'authorization' not in request.headers
        return httpx.Response(200,json={'choices':[{'message':{'content':'Local reply'}}],'usage':{'prompt_tokens':8,'completion_tokens':2}})
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    agent=SimpleNamespace(model='qwen2.5:1.5b',temperature=0.5,max_tokens=10)
    assert await ai.complete(agent,[{'role':'user','content':'Hi'}])==('Local reply',8,2)
    monkeypatch.setattr(ai.settings,'openai_api_key','')
    assert await ai.complete(agent,[])==('Local reply',8,2)

@pytest.mark.anyio
async def test_disabled_ai_never_calls_provider(monkeypatch):
    monkeypatch.setattr(ai.settings,'ai_provider','disabled')
    def forbidden(**kwargs):raise AssertionError('Disabled AI must never make a request')
    monkeypatch.setattr(ai.httpx,'AsyncClient',forbidden)
    with pytest.raises(HTTPException) as error:await ai.complete(None,[])
    assert error.value.status_code==503
