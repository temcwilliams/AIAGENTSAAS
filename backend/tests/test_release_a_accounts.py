from datetime import timedelta
from urllib.parse import urlsplit,parse_qs
import pytest
from sqlalchemy import select,func
from app import email_delivery
from app.config import settings
from app.models import User,Session,ActionToken,Membership,RateLimitBucket,now
from app.security import digest,verify,hasher
from conftest import login

PASSWORD='Changed-password-456!'

@pytest.fixture
def mailbox(monkeypatch):
    monkeypatch.setattr(settings,'email_provider','test')
    email_delivery.test_mailbox.clear()
    yield email_delivery.test_mailbox
    email_delivery.test_mailbox.clear()

def token(mailbox):
    return parse_qs(urlsplit(mailbox[-1]['link']).fragment)['token'][0]

def test_delivery_disabled_is_honest_and_non_enumerating(setup):
    c,factory=setup
    assert c.get('/auth/email/status').json()=={'available':False}
    a=c.post('/auth/password/forgot',json={'email':'a@example.com'})
    b=c.post('/auth/password/forgot',json={'email':'absent@example.com'})
    assert a.status_code==b.status_code==503 and a.json()==b.json()
    login(c)
    assert c.post('/users/invite',json={'email':'new@example.com','business_id':'a'}).status_code==503
    with factory() as db:
        assert db.scalar(select(func.count(ActionToken.token_hash)))==0
        assert db.scalar(select(func.count(User.id)))==3

def test_recovery_generic_response_digest_storage_and_trusted_link(setup,mailbox):
    c,factory=setup
    known=c.post('/auth/password/forgot',headers={'Host':'untrusted.example'},json={'email':'A@example.com'})
    raw=token(mailbox)
    absent=c.post('/auth/password/forgot',json={'email':'absent@example.com'})
    assert known.status_code==absent.status_code==202 and known.json()==absent.json()
    assert raw not in known.text and 'token' not in known.json()
    assert mailbox[0]['link'].startswith('http://testserver/#account-action=reset&token=')
    with factory() as db:
        row=db.get(ActionToken,digest(raw))
        assert row and row.delivery_status=='sent' and row.token_hash!=raw
        assert 1700<(row.expires_at.replace(tzinfo=now().tzinfo)-now()).total_seconds()<=1800

def test_reset_revokes_only_target_sessions_and_replay_fails(setup,mailbox):
    c,factory=setup
    login(c,'a@example.com');first=c.cookies.get('session')
    login(c,'a@example.com');second=c.cookies.get('session')
    login(c,'b@example.com');other=c.cookies.get('session')
    c.post('/auth/password/forgot',json={'email':'a@example.com'});raw=token(mailbox)
    assert c.post('/auth/password/reset',json={'token':raw,'purpose':'setup','new_password':PASSWORD}).status_code==400
    assert c.post('/auth/password/reset',json={'token':raw,'new_password':PASSWORD}).status_code==204
    assert c.post('/auth/password/reset',json={'token':raw,'new_password':PASSWORD}).status_code==400
    with factory() as db:
        assert db.get(Session,digest(first)) is None and db.get(Session,digest(second)) is None
        assert db.get(Session,digest(other)) is not None
        user=db.scalar(select(User).where(User.email=='a@example.com'))
        assert verify(PASSWORD,user.password_hash) and user.email_verified_at
    assert login(c,'a@example.com').status_code==401
    assert c.post('/auth/login',json={'email':'a@example.com','password':PASSWORD}).status_code==200
    assert c.get('/businesses/b/agents').status_code==404

def test_verification_supersedes_older_link_and_preserves_sessions(setup,mailbox):
    c,factory=setup;login(c,'a@example.com');session=c.cookies.get('session')
    assert c.post('/auth/email/resend').status_code==202
    first=token(mailbox)
    assert c.post('/auth/email/resend').status_code==202
    second=token(mailbox)
    assert first!=second
    assert c.post('/auth/email/verify',json={'token':first}).status_code==400
    assert c.post('/auth/password/reset',json={'token':second,'new_password':PASSWORD}).status_code==400
    assert c.post('/auth/email/verify',json={'token':second}).status_code==204
    assert c.post('/auth/email/verify',json={'token':second}).status_code==400
    assert c.get('/auth/me').json()['email_verified'] is True
    assert c.post('/auth/email/resend').status_code==202 and len(mailbox)==2
    with factory() as db:assert db.get(Session,digest(session))

@pytest.mark.parametrize('purpose',['reset','verify','setup'])
def test_expired_actions_cannot_change_account(setup,mailbox,purpose):
    c,factory=setup;login(c)
    if purpose=='reset':c.post('/auth/password/forgot',json={'email':'a@example.com'})
    elif purpose=='verify':c.post('/auth/email/resend')
    else:
        with factory() as db:uid=db.scalar(select(User.id).where(User.email=='a@example.com'))
        c.post('/users/'+uid+'/setup')
    raw=token(mailbox)
    with factory() as db:
        db.get(ActionToken,digest(raw)).expires_at=now()-timedelta(seconds=1);db.commit()
    path='/auth/email/verify' if purpose=='verify' else '/auth/password/reset'
    data={'token':raw} if purpose=='verify' else {'token':raw,'purpose':purpose,'new_password':PASSWORD}
    assert c.post(path,json=data).status_code==400

def test_owner_invitation_and_setup_do_not_reopen_public_signup(setup,mailbox):
    c,factory=setup;login(c)
    r=c.post('/users/invite',json={'email':'new@example.com','business_id':'a','business_role':'manager'})
    assert r.status_code==201 and r.json()['delivery']=='sent'
    assert set(r.json())=={'id','email','delivery'}
    raw=token(mailbox)
    assert c.post('/auth/register',json={'setup_token':raw}).status_code==403
    assert c.post('/auth/password/reset',json={'token':raw,'purpose':'setup','new_password':PASSWORD}).status_code==204
    assert c.post('/auth/login',json={'email':'new@example.com','password':PASSWORD}).status_code==200
    me=c.get('/auth/me').json()
    assert me['role']=='client' and me['business_role']=='manager' and me['email_verified']
    assert c.get('/businesses/b/onboarding').status_code==404
    assert c.post('/users/invite',json={'email':'next@example.com','business_id':'a'}).status_code==403
    with factory() as db:assert db.get(Membership,('a',r.json()['id'])).role=='manager'

def test_delivery_failure_invalidates_link_without_public_enumeration(setup,mailbox,monkeypatch):
    c,factory=setup
    monkeypatch.setattr(email_delivery,'send',lambda *args:False)
    r=c.post('/auth/password/forgot',json={'email':'a@example.com'})
    assert r.status_code==202 and not mailbox
    assert r.json()==c.post('/auth/password/forgot',json={'email':'absent@example.com'}).json()
    with factory() as db:
        row=db.scalar(select(ActionToken))
        assert row.delivery_status=='failed' and row.consumed_at

def test_mail_limits_apply_to_unknown_and_normalized_addresses(setup,mailbox):
    c,_=setup
    for email in ['absent@example.com','ABSENT@example.com','absent@example.com']:
        assert c.post('/auth/password/forgot',json={'email':email}).status_code==202
    assert c.post('/auth/password/forgot',json={'email':'absent@example.com'}).status_code==429
    assert not mailbox

def test_invalid_action_tokens_do_not_create_unbounded_rate_limit_rows(setup):
    c,factory=setup
    for index in range(10):
        raw=f'invalid-action-token-{index:02d}-with-enough-characters'
        assert c.post('/auth/password/reset',json={'token':raw,'new_password':PASSWORD}).status_code==400
    with factory() as db:
        keys=set(db.scalars(select(RateLimitBucket.key)))
        assert keys=={digest('action:global')}
        assert db.scalar(select(func.count(ActionToken.token_hash)))==0

def test_disable_revokes_sessions_tokens_and_preserves_final_owner(setup,mailbox):
    c,factory=setup;login(c,'a@example.com');session=c.cookies.get('session')
    c.post('/auth/password/forgot',json={'email':'a@example.com'});raw=token(mailbox)
    login(c)
    with factory() as db:
        uid=db.scalar(select(User.id).where(User.email=='a@example.com'))
        owner=db.scalar(select(User.id).where(User.role=='admin'))
    assert c.put('/users/'+owner+'/status',json={'disabled':True}).status_code==409
    assert c.put('/users/'+uid+'/status',json={'disabled':True}).status_code==200
    with factory() as db:assert db.get(Session,digest(session)) is None
    assert login(c,'a@example.com').status_code==401
    assert c.post('/auth/password/reset',json={'token':raw,'new_password':PASSWORD}).status_code==400
    assert c.post('/auth/password/forgot',json={'email':'a@example.com'}).status_code==202
    assert len(mailbox)==1
    assert c.put('/users/'+uid+'/status',json={'disabled':False}).status_code==200
    assert login(c,'a@example.com').status_code==200

def test_permissions_cannot_be_self_granted_or_assigned_to_foreign_users(setup):
    c,factory=setup;login(c)
    with factory() as db:
        a=db.scalar(select(User.id).where(User.email=='a@example.com'))
        b=db.scalar(select(User.id).where(User.email=='b@example.com'))
    assert c.put('/businesses/a/members/'+b,json={'role':'manager'}).status_code==404
    assert c.put('/businesses/a/members/'+a,json={'role':'admin'}).status_code==422
    login(c,'a@example.com')
    assert c.get('/users').status_code==403
    assert c.put('/businesses/a/members/'+a,json={'role':'manager'}).status_code==403

def test_password_change_invalidates_outstanding_action_links(setup,mailbox):
    c,_=setup;login(c,'a@example.com')
    c.post('/auth/password/forgot',json={'email':'a@example.com'});raw=token(mailbox)
    assert c.post('/auth/password',json={'current_password':'Test-password-123!','new_password':PASSWORD}).status_code==204
    assert c.post('/auth/password/reset',json={'token':raw,'new_password':'Another-password-987!'}).status_code==400

def test_replayed_claim_cannot_bypass_atomic_token_update(setup,mailbox,monkeypatch):
    c,factory=setup
    c.post('/auth/password/forgot',json={'email':'a@example.com'});raw=token(mailbox)
    from app import accounts
    original=accounts.valid_action
    def consume_competing(db,*args):
        row,user=original(db,*args)
        # Emulate a competing transaction consuming the row after the initial read.
        from sqlalchemy import update
        db.execute(update(ActionToken).where(ActionToken.token_hash==row.token_hash).values(consumed_at=now()));db.commit()
        return row,user
    monkeypatch.setattr(accounts,'valid_action',consume_competing)
    assert c.post('/auth/password/reset',json={'token':raw,'new_password':PASSWORD}).status_code==400
    with factory() as db:
        user=db.scalar(select(User).where(User.email=='a@example.com'))
        assert verify('Test-password-123!',user.password_hash)

def test_resend_status_and_user_listing_never_return_action_secrets(setup,mailbox):
    c,_=setup;login(c)
    c.post('/auth/email/resend');raw=token(mailbox)
    result=c.get('/users')
    assert result.status_code==200
    assert raw not in result.text and digest(raw) not in result.text
    assert 'password_hash' not in result.text and 'token_hash' not in result.text
    assert any(u['last_delivery'] and u['last_delivery']['status']=='sent' for u in result.json())
