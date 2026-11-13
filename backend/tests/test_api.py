import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.models import Message, Usage, Agent, Conversation
from conftest import login

AGENT={'name':'Support','model':'test-model','system_prompt':'Help customers','temperature':0.5,'max_tokens':100}

def test_auth_and_revocation(setup):
    c,_=setup
    assert c.get('/businesses').status_code==401
    assert c.post('/auth/login',json={'email':'a@example.com','password':'wrong-password'}).status_code==401
    r=login(c);assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
    cookie=c.cookies.get('session')
    assert c.get('/auth/me').json()['role']=='admin'
    assert c.post('/auth/logout').status_code==204
    c.cookies.set('session',cookie)
    assert c.get('/auth/me').status_code==401

def test_csrf_and_rate_limit(setup):
    c,_=setup
    assert c.post('/auth/login',headers={'Origin':'https://evil.example'},json={}).status_code==403
    for _ in range(10):
        assert c.post('/auth/login',json={'email':'none@example.com','password':'wrong-password'}).status_code==401
    assert c.post('/auth/login',json={'email':'none@example.com','password':'wrong-password'}).status_code==429

def test_admin_and_validation(setup):
    c,_=setup;login(c)
    assert c.post('/businesses',json={'name':'New business'}).status_code==201
    assert c.put('/businesses/a',json={'name':'Renamed'}).status_code==200
    assert c.post('/users',json={'email':'new@example.com','password':'Strong-password-123','business_id':'a'}).status_code==201
    assert c.post('/users',json={'email':'new@example.com','password':'Strong-password-123','business_id':'a'}).status_code==409
    assert c.post('/businesses/a/agents',json={**AGENT,'max_tokens':99999}).status_code==422
    login(c,'a@example.com')
    assert c.post('/businesses',json={'name':'Forbidden'}).status_code==403
    assert c.post('/businesses/a/agents',json=AGENT).status_code==403
    assert [b['id'] for b in c.get('/businesses').json()]==['a']

@pytest.mark.parametrize('suffix',['agents','conversations','leads','usage'])
def test_tenant_list_isolation(setup,suffix):
    c,_=setup;login(c,'a@example.com')
    assert c.get('/businesses/b/'+suffix).status_code==404
    assert c.get('/businesses/a/'+suffix).status_code==200

def test_resource_isolation_and_chat_storage(setup,monkeypatch):
    c,factory=setup;login(c)
    aid=c.post('/businesses/b/agents',json=AGENT).json()['id']
    cid=c.post(f'/businesses/b/agents/{aid}/conversations').json()['id']
    login(c,'a@example.com')
    assert c.post(f'/businesses/a/agents/{aid}/conversations').status_code==404
    assert c.get(f'/businesses/a/conversations/{cid}/messages').status_code==404
    assert c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'secret'}).status_code==404
    login(c,'b@example.com')
    async def fake(agent,messages):
        assert messages[0]['role']=='system'
        return 'Hello!',12,3
    monkeypatch.setattr('app.ai.complete',fake)
    r=c.post(f'/businesses/b/conversations/{cid}/messages',json={'content':'Hi'})
    assert r.status_code==200
    assert len(c.get(f'/businesses/b/conversations/{cid}/messages').json())==2
    usage=c.get('/businesses/b/usage').json()
    assert usage['prompt_tokens']==12 and usage['completion_tokens']==3 and usage['requests']==1
    assert c.get('/businesses/a/usage').status_code==404
    async def fail(*args):
        from fastapi import HTTPException
        raise HTTPException(502,'Provider failed')
    monkeypatch.setattr('app.ai.complete',fail)
    assert c.post(f'/businesses/b/conversations/{cid}/messages',json={'content':'Fail'}).status_code==502
    with factory() as db:
        assert db.scalar(select(func.count(Message.id)))==2
        assert db.scalar(select(func.count(Usage.id)))==1

def test_database_rejects_mixed_tenant_reference(setup):
    _,factory=setup
    with factory() as db:
        db.add(Agent(id='agent',business_id='a',**AGENT));db.commit()
        db.add(Conversation(business_id='b',agent_id='agent'))
        with pytest.raises(IntegrityError):db.commit()

def test_leads_and_disabled_agent(setup):
    c,_=setup;login(c)
    assert c.post('/businesses/a/leads',json={'name':'Prospect','email':'lead@example.com'}).status_code==201
    assert len(c.get('/businesses/a/leads').json())==1
    aid=c.post('/businesses/a/agents',json={**AGENT,'enabled':False}).json()['id']
    cid=c.post(f'/businesses/a/agents/{aid}/conversations').json()['id']
    assert c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'Hi'}).status_code==409

def test_expired_and_forged_session(setup):
    from app.models import Session, now
    from datetime import timedelta
    c,factory=setup;login(c)
    with factory() as db:
        row=db.scalar(select(Session));row.expires_at=now()-timedelta(seconds=1);db.commit()
    assert c.get('/auth/me').status_code==401
    c.cookies.clear();c.cookies.set('session','forged')
    assert c.get('/auth/me').status_code==401
