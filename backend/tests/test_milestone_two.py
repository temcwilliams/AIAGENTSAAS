from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
import pytest
from fastapi import HTTPException
from conftest import login
from test_api import AGENT
from app.models import Lead,Message,Usage,KnowledgeDocument
from app.config import settings


def conversation(c,business='a'):
    agent=c.post(f'/businesses/{business}/agents',json=AGENT).json()['id']
    conv=c.post(f'/businesses/{business}/agents/{agent}/conversations').json()['id']
    return agent,conv


def test_knowledge_citations_and_tenant_grounding(setup,monkeypatch):
    c,factory=setup;login(c)
    a=c.post('/businesses/a/knowledge',json={'title':'Hours','content':'We open Monday at 9 and close at 5.'}).json()
    b=c.post('/businesses/b/knowledge',json={'title':'Private secret','content':'Monday private secret BETA-ONLY'}).json()
    _,cid=conversation(c)
    login(c,'a@example.com')
    assert c.get('/businesses/b/knowledge').status_code==404
    assert c.post('/businesses/a/knowledge',json={'title':'No','content':'Denied'}).status_code==403
    async def complete(agent,messages):
        assert 'Monday at 9' in messages[0]['content']
        assert 'BETA-ONLY' not in str(messages)
        assert 'untrusted_business_reference' in messages[0]['content']
        return 'We open at 9.',10,3
    monkeypatch.setattr('app.ai.complete',complete)
    response=c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'When do you open Monday?'})
    assert response.status_code==200 and response.json()['sources']==[{'id':a['id'],'title':'Hours'}]
    assert c.get(f'/businesses/a/conversations/{cid}/messages').json()[-1]['sources'][0]['id']==a['id']
    login(c)
    assert c.put(f"/businesses/a/knowledge/{b['id']}",json={'title':'No','content':'No'}).status_code==404
    assert c.put(f"/businesses/a/knowledge/{a['id']}",json={'title':'Hours','content':'We open Monday at 9.','enabled':False}).status_code==200
    async def no_disabled(agent,messages):
        assert 'Monday at 9' not in messages[0]['content']
        return 'Please ask the team.',7,3
    monkeypatch.setattr('app.ai.complete',no_disabled)
    assert c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'Monday opening hours'}).json()['sources']==[]


def test_capture_requires_consent_and_deduplicates(setup,monkeypatch):
    c,factory=setup;login(c);_,cid=conversation(c)
    async def complete(*_):return 'Thanks',10,2
    monkeypatch.setattr('app.ai.complete',complete)
    route=f'/businesses/a/conversations/{cid}/messages'
    content='My name is Alice, please email alice@example.com.'
    assert not c.post(route,json={'content':content}).json()['lead_captured']
    assert c.post(route,json={'content':content,'capture_lead':True}).json()['lead_captured']
    assert c.post(route,json={'content':content,'capture_lead':True}).json()['lead_captured']
    rows=c.get('/businesses/a/leads').json()
    assert len(rows)==1 and rows[0]['name']=='Alice' and rows[0]['email']=='alice@example.com'
    assert rows[0]['conversation_id']==cid and rows[0]['source']=='chat'
    async def fail(*_):raise HTTPException(502,'Failed')
    monkeypatch.setattr('app.ai.complete',fail)
    assert c.post(route,json={'content':'contact new@example.com','capture_lead':True}).status_code==502
    assert len(c.get('/businesses/a/leads').json())==1
    with factory() as db:
        db.add(Lead(business_id='b',conversation_id=cid,name='Wrong',email='bad@example.com'))
        with pytest.raises(IntegrityError):db.commit()


def test_handoff_lifecycle_and_client_permissions(setup,monkeypatch):
    c,factory=setup;login(c);aid,cid=conversation(c);route=f'/businesses/a/conversations/{cid}'
    login(c,'a@example.com')
    assert c.post(route+'/handoff',json={'reason':'Please help with my booking'}).status_code==200
    def forbidden(*_):raise AssertionError('Must not call AI during human handoff')
    monkeypatch.setattr('app.ai.complete',forbidden)
    queued=c.post(route+'/messages',json={'content':'You can reach me at help@example.com','capture_lead':True})
    assert queued.status_code==200 and queued.json()['queued_for_human']
    assert c.post(route+'/reply',json={'content':'Not permitted'}).status_code==403
    assert c.post(route+'/handoff/status',json={'status':'human'}).status_code==403
    assert len(c.get('/businesses/a/handoffs').json())==1
    login(c,'b@example.com')
    assert c.get('/businesses/a/handoffs').status_code==404
    assert c.post(f'/businesses/b/conversations/{cid}/handoff',json={'reason':'Wrong tenant'}).status_code==404
    login(c)
    assert c.post(route+'/reply',json={'content':'Need to take over first'}).status_code==409
    assert c.post(route+'/handoff/status',json={'status':'human'}).status_code==200
    assert c.post(route+'/reply',json={'content':'A real person is here.'}).status_code==201
    assert c.get(route+'/messages').json()[-1]['role']=='human'
    assert c.post(route+'/handoff/status',json={'status':'resolved'}).status_code==200
    assert not c.get('/businesses/a/handoffs').json()
    assert c.post(route+'/messages',json={'content':'More'}).status_code==409
    assert c.post(route+'/handoff/status',json={'status':'ai'}).status_code==200
    async def resumed(agent,messages):
        assert any(m['role']=='assistant' and 'real person' in m['content'] for m in messages)
        return 'Resumed',12,3
    monkeypatch.setattr('app.ai.complete',resumed)
    assert c.post(route+'/messages',json={'content':'Continue'}).status_code==200
    with factory() as db:assert db.scalar(select(func.count(Usage.id)))==1


def test_floor_has_real_scoped_metrics(setup,monkeypatch):
    c,_=setup;login(c);aid,cid=conversation(c);conversation(c,'b')
    async def complete(*_):return 'Reply',12,3
    monkeypatch.setattr('app.ai.complete',complete)
    c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'Hi'})
    c.post(f'/businesses/a/conversations/{cid}/handoff',json={'reason':'Need help'})
    login(c,'a@example.com')
    floor=c.get('/businesses/a/floor').json()
    assert len(floor['agents'])==1
    agent=floor['agents'][0]
    assert agent['id']==aid and agent['tokens']==15 and agent['requests']==1 and agent['conversations']==1
    assert agent['status']=='attention' and agent['handoffs']==1 and agent['last_activity']
    assert c.get('/businesses/b/floor').status_code==404


def test_inference_status_is_safe_and_checks_require_admin(setup,monkeypatch):
    c,_=setup;login(c,'a@example.com')
    monkeypatch.setattr(settings,'ai_provider','disabled')
    monkeypatch.setattr(settings,'openai_api_key','must-not-leak')
    response=c.get('/businesses/a/inference')
    assert response.json()['configured'] is False and 'must-not-leak' not in response.text
    assert c.post('/businesses/a/inference/check').status_code==403
    login(c)
    assert c.post('/businesses/a/inference/check').status_code==503
