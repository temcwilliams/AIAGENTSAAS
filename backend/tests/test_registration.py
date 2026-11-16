"""Accounts are operator-provisioned; public and legacy owner signup are closed."""
import pytest
from sqlalchemy import select, func, delete
from app.db import get_db
from app.main import app
from app.models import User, Business, Session, OwnerSetup, RateLimitBucket
from app.security import digest
from app.config import settings
from conftest import login

DATA={'email':'new@example.com','password':'New-password-123!','business_name':'New Business'}


@pytest.mark.parametrize('payload',[
    DATA,
    {},
    {**DATA,'setup_token':'test-owner-code'},
    {**DATA,'role':'admin','business_id':'a'},
])
def test_registration_never_creates_accounts_or_sessions(setup,monkeypatch,payload):
    client,factory=setup
    monkeypatch.setattr(settings,'owner_setup_token_hash',digest('test-owner-code'))
    models=[User,Business,Session,OwnerSetup,RateLimitBucket]
    with factory() as db:
        before=[db.scalar(select(func.count()).select_from(model)) for model in models]
    def forbid_hash(*args,**kwargs):
        raise AssertionError('Disabled signup must not hash passwords')
    monkeypatch.setattr('app.security.hasher.hash',forbid_hash)
    response=client.post('/auth/register',json=payload)
    assert response.status_code==403
    assert 'disabled' in response.json()['detail']
    assert 'set-cookie' not in response.headers
    assert not client.cookies.get('session')
    with factory() as db:
        assert before==[db.scalar(select(func.count()).select_from(model)) for model in models]


def test_registration_stays_closed_without_an_administrator_or_database_access(setup,monkeypatch):
    client,factory=setup
    with factory() as db:
        db.execute(delete(User).where(User.role=='admin'));db.commit()
    monkeypatch.setattr(settings,'owner_setup_token_hash',digest('test-owner-code'))
    def forbid_db():
        raise AssertionError('Disabled signup must not open a database session')
    app.dependency_overrides[get_db]=forbid_db
    assert client.post('/auth/register',json={**DATA,'setup_token':'test-owner-code'}).status_code==403
    assert client.post('/auth/register',content=b'not JSON',headers={'Content-Type':'application/json'}).status_code==403


def test_operator_can_provision_a_client_who_can_sign_in(setup):
    client,_=setup
    assert login(client).status_code==200
    business=client.post('/businesses',json={'name':'Approved Business'})
    assert business.status_code==201
    bid=business.json()['id']
    response=client.post('/users',json={'email':DATA['email'],'password':DATA['password'],'business_id':bid})
    assert response.status_code==201
    assert client.post('/auth/logout').status_code==204
    assert client.post('/auth/login',json={'email':DATA['email'],'password':DATA['password']}).status_code==200
    me=client.get('/auth/me').json()
    assert me['role']=='client' and me['business_id']==bid
    assert [b['id'] for b in client.get('/businesses').json()]==[bid]
    assert client.get('/businesses/a/agents').status_code==404
    assert client.post('/users',json={'email':'other@example.com','password':DATA['password'],'business_id':bid}).status_code==403


def test_unauthenticated_users_cannot_provision_accounts(setup):
    client,_=setup
    assert client.post('/businesses',json={'name':'Bot Business'}).status_code==401
    assert client.post('/users',json={'email':DATA['email'],'password':DATA['password'],'business_id':'a'}).status_code==401
