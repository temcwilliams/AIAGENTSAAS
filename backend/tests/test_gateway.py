import importlib.util
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv('MEADOW_BRIDGE_TOKEN','test-only-bridge-token-with-48-characters-at-least')
    path=Path(__file__).resolve().parents[2]/'scripts/ollama_gateway.py'
    spec=importlib.util.spec_from_file_location('test_gateway_module',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with TestClient(module.app) as client:yield client,module


def test_gateway_requires_auth_and_preserves_protocol(gateway,monkeypatch):
    c,module=gateway
    assert c.get('/v1/models').status_code==401
    assert c.get('/v1/models',headers={'Authorization':'Bearer wrong'}).status_code==401
    calls=[]
    async def fake(method,path,payload=None):
        calls.append((method,path,payload))
        return {'data':[{'id':'qwen2.5:1.5b'}]} if method=='GET' else {'choices':[{'message':{'content':'Hi'}}],'usage':{'prompt_tokens':4,'completion_tokens':2}}
    monkeypatch.setattr(module,'upstream',fake)
    headers={'Authorization':'Bearer '+module.secret}
    assert c.get('/v1/models',headers=headers).json()['data'][0]['id']=='qwen2.5:1.5b'
    payload={'model':'qwen2.5:1.5b','messages':[{'role':'user','content':'Hi'}]}
    assert c.post('/v1/chat/completions',headers=headers,json=payload).json()['usage']['prompt_tokens']==4
    assert c.post('/v1/chat/completions',headers=headers,json={**payload,'max_tokens':10000}).status_code==422
    assert c.post('/v1/chat/completions',headers=headers,json={**payload,'messages':[{'role':'user','content':'x'*60001}]}).status_code==422
    assert c.get('/unrestricted-proxy',headers=headers).status_code==404
    module.request_count=60
    assert c.post('/v1/chat/completions',headers=headers,json=payload).status_code==429
    assert len(calls)==2

def test_gateway_rejects_oversized_body_before_parsing(gateway):
    c,module=gateway
    assert c.post('/v1/chat/completions',headers={'Authorization':'Bearer '+module.secret},content='x'*256001).status_code==413
