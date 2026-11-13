from datetime import timedelta
from sqlalchemy import select, func
from fastapi import HTTPException
from conftest import login
from app.models import Session, User, RateLimitBucket, now
from app.security import verify, digest
from app.config import settings
from app.limits import consume
from test_api import AGENT
import pytest


def test_password_change_revokes_all_sessions(setup):
    c,factory=setup
    login(c,'a@example.com');first=c.cookies.get('session')
    login(c,'a@example.com');second=c.cookies.get('session')
    login(c,'b@example.com');other=c.cookies.get('session')
    c.cookies.clear();c.cookies.set('session',second)
    r=c.post('/auth/password',json={'current_password':'Test-password-123!','new_password':'Changed-password-456!'})
    assert r.status_code==204
    with factory() as db:
        assert db.get(Session,digest(first)) is None
        assert db.get(Session,digest(second)) is None
        assert db.get(Session,digest(other)) is not None
        user=db.scalar(select(User).where(User.email=='a@example.com'))
        assert verify('Changed-password-456!',user.password_hash)
    c.cookies.clear();c.cookies.set('session',first)
    assert c.get('/auth/me').status_code==401
    assert login(c,'a@example.com').status_code==401
    assert c.post('/auth/login',json={'email':'a@example.com','password':'Changed-password-456!'}).status_code==200


def test_password_failure_preserves_session_and_is_throttled(setup):
    c,_=setup;login(c)
    assert c.post('/auth/password',json={'current_password':'Test-password-123!','new_password':'short'}).status_code==422
    assert c.post('/auth/password',json={'current_password':'Test-password-123!','new_password':'Test-password-123!'}).status_code==422
    for _ in range(4):
        assert c.post('/auth/password',json={'current_password':'wrong','new_password':'Different-password-123!'}).status_code==401
    assert c.post('/auth/password',json={'current_password':'wrong','new_password':'Different-password-123!'}).status_code==429
    assert c.get('/auth/me').status_code==200


def test_logout_all_revokes_every_session(setup):
    c,factory=setup;login(c);first=c.cookies.get('session');login(c)
    assert c.post('/auth/logout-all').status_code==204
    c.cookies.clear();c.cookies.set('session',first)
    assert c.get('/auth/me').status_code==401
    with factory() as db: assert db.scalar(select(func.count(Session.token_hash)))==0


def test_security_writes_require_auth_and_origin(setup):
    c,_=setup
    assert c.post('/auth/logout-all').status_code==401
    assert c.post('/auth/password',json={'current_password':'x','new_password':'New-password-123!'}).status_code==401
    login(c)
    assert c.post('/auth/logout-all',headers={'Origin':'https://evil.example'}).status_code==403


def test_chat_attempt_limit_shared_by_business_and_failed_requests(setup,monkeypatch):
    c,factory=setup;login(c)
    monkeypatch.setattr(settings,'chat_requests_per_hour',1)
    a=c.post('/businesses/a/agents',json=AGENT).json()['id']
    b=c.post('/businesses/b/agents',json=AGENT).json()['id']
    cid=c.post(f'/businesses/a/agents/{a}/conversations').json()['id']
    cid2=c.post(f'/businesses/a/agents/{a}/conversations').json()['id']
    bid=c.post(f'/businesses/b/agents/{b}/conversations').json()['id']
    calls=[]
    async def fail(*args):
        calls.append(True)
        raise HTTPException(502,'Provider failed')
    monkeypatch.setattr('app.ai.complete',fail)
    assert c.post(f'/businesses/a/conversations/{cid}/messages',json={'content':'Hi'}).status_code==502
    login(c,'a@example.com')
    denied=c.post(f'/businesses/a/conversations/{cid2}/messages',json={'content':'Hi'})
    assert denied.status_code==429 and denied.headers['retry-after']=='3600'
    assert len(calls)==1
    assert c.post(f'/businesses/b/conversations/{bid}/messages',json={'content':'Hi'}).status_code==404
    login(c,'b@example.com')
    assert c.post(f'/businesses/b/conversations/{bid}/messages',json={'content':'Hi'}).status_code==502
    assert len(calls)==2
    with factory() as db:
        assert db.get(RateLimitBucket,digest('chat:a')).count==1
        assert db.get(RateLimitBucket,digest('chat:b')).count==1


def test_limit_window_resets(setup):
    _,factory=setup
    with factory() as db:
        consume(db,'test-window',1,3600)
        with pytest.raises(HTTPException):consume(db,'test-window',1,3600)
        bucket=db.get(RateLimitBucket,digest('test-window'))
        bucket.reset_at=now()-timedelta(seconds=1);db.commit()
        consume(db,'test-window',1,3600)
        db.expire_all()
        assert db.get(RateLimitBucket,digest('test-window')).count==1
