import pytest
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.models import User,Membership,OnboardingDraft,Agent,KnowledgeDocument
from conftest import login
from test_api import AGENT

PROFILE={'business_name':'Approved Alpha','description':'A local business.','contact_name':'Alex','contact_email':'contact@example.com','services':'Repairs and advice','faqs':'Q: Open weekends? A: Saturdays.','hours':'Monday to Saturday','handoff_preferences':'Ask a person for complex issues.','template':'support'}
BASE='/businesses/a/onboarding'

def manager(client,factory):
    login(client)
    with factory() as db:uid=db.scalar(select(User.id).where(User.email=='a@example.com'))
    assert client.put('/businesses/a/members/'+uid,json={'role':'manager'}).status_code==200
    login(client,'a@example.com')

def save(client,version=0,profile=None):
    result=client.put(BASE,json={'expected_version':version,'profile':profile or PROFILE})
    assert result.status_code==200,result.text
    return result.json()

def approved(client,factory):
    manager(client,factory);draft=save(client)
    submit=client.post(BASE+'/submit',json={'expected_version':draft['version']})
    assert submit.status_code==200
    login(client)
    result=client.post(BASE+'/review',json={'expected_version':submit.json()['version'],'decision':'approved'})
    assert result.status_code==200
    return result.json()

def test_viewers_preserved_but_cannot_edit_submit_review_or_publish(setup):
    c,_=setup;login(c,'a@example.com')
    assert c.get('/auth/me').json()['business_role']=='viewer'
    assert c.get(BASE).json()['version']==0
    assert c.put(BASE,json={'expected_version':0,'profile':PROFILE}).status_code==403
    for action,data in [('submit',{}),('review',{'decision':'approved'}),('publish',{})]:
        assert c.post(BASE+'/'+action,json={'expected_version':0,**data}).status_code==403
    assert c.get('/businesses/b/onboarding').status_code==404
    assert c.get('/businesses/b/onboarding/preview').status_code==404

def test_draft_resumes_and_never_changes_live_configuration_before_publish(setup):
    c,factory=setup;login(c)
    aid=c.post('/businesses/a/agents',json=AGENT).json()['id']
    doc=c.post('/businesses/a/knowledge',json={'title':'Internal','content':'Private facts','enabled':False}).json()['id']
    manager(c,factory);d=save(c)
    assert c.get('/businesses').json()[0]['name']=='Alpha'
    c.post('/auth/logout');login(c,'a@example.com')
    assert c.get(BASE).json()['profile']['services']==PROFILE['services']
    assert c.get('/businesses/a/agents').json()[0]['id']==aid
    assert c.get('/businesses/a/knowledge').json()[0]['id']==doc
    assert c.get(BASE+'/preview').json()['inference_called'] is False
    submitted=c.post(BASE+'/submit',json={'expected_version':d['version']}).json()
    assert c.put(BASE,json={'expected_version':submitted['version'],'profile':PROFILE}).status_code==409
    assert c.post(BASE+'/publish',json={'expected_version':submitted['version']}).status_code==403
    with factory() as db:
        assert db.get(Agent,aid).system_prompt==AGENT['system_prompt']
        assert db.get(KnowledgeDocument,doc).enabled is False

def test_review_changes_version_conflicts_and_idempotent_publication(setup):
    c,factory=setup;manager(c,factory);draft=save(c)
    stale=c.put(BASE,json={'expected_version':0,'profile':PROFILE})
    assert stale.status_code==409
    submitted=c.post(BASE+'/submit',json={'expected_version':draft['version']}).json()
    login(c)
    assert c.post(BASE+'/publish',json={'expected_version':submitted['version']}).status_code==409
    changed=c.post(BASE+'/review',json={'expected_version':submitted['version'],'decision':'changes_requested','notes':'Add your phone number.'}).json()
    login(c,'a@example.com')
    draft=save(c,changed['version'],{**PROFILE,'phone':'555-0100'})
    submitted=c.post(BASE+'/submit',json={'expected_version':draft['version']}).json()
    login(c)
    review=c.post(BASE+'/review',json={'expected_version':submitted['version'],'decision':'approved'}).json()
    payload={'expected_version':review['version'],'model':'owner-selected-model'}
    published=c.post(BASE+'/publish',json=payload)
    assert published.status_code==200
    first=published.json()
    assert c.post(BASE+'/publish',json=payload).json()==first
    assert c.get('/businesses').json()[0]['name']==PROFILE['business_name']
    with factory() as db:
        assert db.scalar(select(func.count(Agent.id)).where(Agent.business_id=='a'))==1
        assert db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.business_id=='a'))==1
        agent=db.get(Agent,first['agent_id'])
        assert agent.model=='owner-selected-model' and 'customer support' in agent.system_prompt
        assert db.get(KnowledgeDocument,first['knowledge_id']).content.find('555-0100')>=0
    # Later client edits start a draft; active approved configuration stays intact.
    login(c,'a@example.com')
    save(c,first['version'],{**PROFILE,'services':'A proposed new service'})
    with factory() as db:
        assert 'A proposed new service' not in db.get(KnowledgeDocument,first['knowledge_id']).content
        assert db.get(Agent,first['agent_id']).model=='owner-selected-model'

def test_manager_and_responder_roles_enforced_without_session_claims(setup):
    c,factory=setup;login(c)
    aid=c.post('/businesses/a/agents',json=AGENT).json()['id']
    cid=c.post('/businesses/a/agents/'+aid+'/conversations').json()['id']
    with factory() as db:uid=db.scalar(select(User.id).where(User.email=='a@example.com'))
    login(c,'a@example.com');cookie=c.cookies.get('session')
    route='/businesses/a/conversations/'+cid
    assert c.post(route+'/handoff/status',json={'status':'human'}).status_code==403
    login(c)
    c.put('/businesses/a/members/'+uid,json={'role':'responder'})
    c.cookies.clear();c.cookies.set('session',cookie)
    assert c.post(route+'/handoff/status',json={'status':'human'}).status_code==200
    assert c.post(route+'/reply',json={'content':'A real human reply'}).status_code==201
    assert c.put(BASE,json={'expected_version':0,'profile':PROFILE}).status_code==403
    assert c.post('/businesses/a/agents',json=AGENT).status_code==403
    login(c);c.put('/businesses/a/members/'+uid,json={'role':'viewer'})
    c.cookies.clear();c.cookies.set('session',cookie)
    assert c.post(route+'/reply',json={'content':'No longer permitted'}).status_code==403

def test_validation_incomplete_drafts_and_status_overposting(setup):
    c,factory=setup;manager(c,factory)
    draft=save(c,profile={'business_name':'Partial'})
    assert c.post(BASE+'/submit',json={'expected_version':draft['version']}).status_code==422
    assert c.put(BASE,json={'expected_version':draft['version'],'profile':PROFILE,'status':'approved'}).status_code==422
    assert c.put(BASE,json={'expected_version':draft['version'],'profile':{**PROFILE,'model':'client-injected'}}).status_code==422
    assert c.put(BASE,json={'expected_version':draft['version'],'profile':{**PROFILE,'website':'javascript:alert(1)'}}).status_code==422

def test_memberships_and_onboarding_have_database_tenant_constraints(setup):
    c,factory=setup;login(c)
    aid=c.post('/businesses/b/agents',json=AGENT).json()['id']
    doc=c.post('/businesses/b/knowledge',json={'title':'B','content':'B only'}).json()['id']
    with factory() as db:
        uid=db.scalar(select(User.id).where(User.email=='a@example.com'))
        db.add(Membership(user_id=uid,business_id='b',role='manager'))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        db.add(OnboardingDraft(business_id='a',profile=PROFILE,agent_id=aid))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        db.add(OnboardingDraft(business_id='a',profile=PROFILE,knowledge_id=doc))
        with pytest.raises(IntegrityError):db.commit()

def test_publication_capacity_failure_is_atomic(setup):
    c,factory=setup;review=approved(c,factory)
    with factory() as db:
        for i in range(100):db.add(KnowledgeDocument(business_id='a',title='Existing '+str(i),content='Existing',enabled=True))
        db.commit()
    assert c.post(BASE+'/publish',json={'expected_version':review['version']}).status_code==409
    with factory() as db:
        row=db.get(OnboardingDraft,'a')
        assert row.status=='approved' and row.agent_id is None and row.knowledge_id is None
        assert db.scalar(select(func.count(Agent.id)))==0

def test_republication_reuses_managed_agent_and_document(setup):
    c,factory=setup;review=approved(c,factory)
    first=c.post(BASE+'/publish',json={'expected_version':review['version']}).json()
    manager(c,factory)
    d=save(c,first['version'],{**PROFILE,'template':'leads','services':'New approved services'})
    submitted=c.post(BASE+'/submit',json={'expected_version':d['version']}).json()
    login(c)
    reviewed=c.post(BASE+'/review',json={'expected_version':submitted['version'],'decision':'approved'}).json()
    second=c.post(BASE+'/publish',json={'expected_version':reviewed['version'],'model':'new-model'}).json()
    assert first['agent_id']==second['agent_id'] and first['knowledge_id']==second['knowledge_id']
    assert second['template_version']==1
    with factory() as db:
        assert db.scalar(select(func.count(Agent.id)))==1
        assert db.scalar(select(func.count(KnowledgeDocument.id)))==1
        assert db.get(Agent,first['agent_id']).model=='new-model'
