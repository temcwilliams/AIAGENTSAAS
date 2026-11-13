from sqlalchemy import select, func, delete
from app.models import User, Business, Session, OwnerSetup
from app.security import digest, verify
from app.config import settings
from conftest import login

DATA={'email':'new@example.com','password':'New-password-123!','business_name':'New Business'}

def test_registration_signs_in_isolated_client(setup):
    c,factory=setup
    response=c.post('/auth/register',json=DATA)
    assert response.status_code==201
    account=response.json()
    assert account['role']=='client'
    assert 'HttpOnly' in response.headers['set-cookie']
    assert c.get('/auth/me').json()['email']==DATA['email']
    businesses=c.get('/businesses').json()
    assert len(businesses)==1 and businesses[0]['name']=='New Business'
    assert c.get('/businesses/a/agents').status_code==404
    assert c.post('/businesses',json={'name':'Forbidden'}).status_code==403
    with factory() as db:
        user=db.get(User,account['id'])
        assert user.password_hash!=DATA['password'] and verify(DATA['password'],user.password_hash)
        assert db.get(Session,digest(c.cookies.get('session'))).user_id==user.id

def test_duplicate_and_tampered_registration_do_not_create_businesses(setup):
    c,factory=setup
    assert c.post('/auth/register',json=DATA).status_code==201
    assert c.post('/auth/register',json={**DATA,'email':'NEW@example.com'}).status_code==409
    assert c.post('/auth/register',json={**DATA,'email':'other@example.com','role':'admin','business_id':'a'}).status_code==422
    with factory() as db:assert db.scalar(select(func.count(Business.id)))==3

def test_registration_validates_origin_password_and_business(setup):
    c,_=setup
    assert c.post('/auth/register',headers={'Origin':'https://evil.example'},json=DATA).status_code==403
    for override in [{'password':'short'},{'business_name':'   '},{'email':'invalid'}]:
        assert c.post('/auth/register',json={**DATA,**override}).status_code==422

def test_public_registration_cannot_claim_owner(setup,monkeypatch):
    c,_=setup
    monkeypatch.setattr(settings,'owner_setup_token_hash',digest('test-owner-code'))
    assert c.post('/auth/register',json={**DATA,'setup_token':'wrong-code'}).status_code==403
    assert c.post('/auth/register',json=DATA).json()['role']=='client'

def test_one_time_owner_setup(setup,monkeypatch):
    c,factory=setup
    monkeypatch.setattr(settings,'owner_setup_token_hash',digest('test-owner-code'))
    with factory() as db:
        db.execute(delete(User).where(User.role=='admin'));db.commit()
    response=c.post('/auth/register',json={**DATA,'setup_token':'test-owner-code'})
    assert response.status_code==201 and response.json()['role']=='admin'
    assert c.post('/businesses',json={'name':'Managed client'}).status_code==201
    assert c.post('/auth/register',json={**DATA,'email':'second@example.com','setup_token':'test-owner-code'}).status_code==409
    with factory() as db:
        assert db.scalar(select(func.count(OwnerSetup.id)))==1
        # Even if an admin is removed, the unique claim cannot be reused.
        db.execute(delete(Session));db.execute(delete(User).where(User.role=='admin'));db.commit()
    assert c.post('/auth/register',json={**DATA,'email':'third@example.com','setup_token':'test-owner-code'}).status_code==409

def test_owner_setup_disabled_or_existing_owner(setup,monkeypatch):
    c,_=setup
    monkeypatch.setattr(settings,'owner_setup_token_hash','')
    assert c.post('/auth/register',json={**DATA,'setup_token':'test-owner-code'}).status_code==403
    monkeypatch.setattr(settings,'owner_setup_token_hash',digest('test-owner-code'))
    assert c.post('/auth/register',json={**DATA,'setup_token':'test-owner-code'}).status_code==409

def test_registration_is_rate_limited(setup):
    c,_=setup
    for _ in range(5):
        assert c.post('/auth/register',json={**DATA,'setup_token':'invalid'}).status_code==403
    assert c.post('/auth/register',json=DATA).status_code==429
