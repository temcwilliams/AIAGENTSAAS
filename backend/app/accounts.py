"""Digest-only action links, owner invitations, business permissions and account status."""
import secrets
from datetime import timedelta, timezone
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .models import User, Session, ActionToken, Membership, Business, now
from .security import current_user, admin, tenant, digest, hasher, business_role
from .config import settings
from .limits import consume
from . import email_delivery

router=APIRouter()
EMAIL_PATTERN=r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

class EmailInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str = Field(min_length=3,max_length=254,pattern=EMAIL_PATTERN)
class TokenInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    token: str = Field(min_length=32,max_length=256)
class ResetInput(TokenInput):
    purpose: Literal['reset','setup'] = 'reset'
    new_password: str = Field(min_length=12,max_length=128)
class InviteInput(EmailInput):
    business_id: str = Field(min_length=1,max_length=36)
    business_role: Literal['viewer','responder','manager'] = 'viewer'
class RoleInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    role: Literal['viewer','responder','manager']
class StatusInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    disabled: bool

def require_mail():
    if not email_delivery.available():
        raise HTTPException(503,'Email delivery is unavailable. Contact the platform owner; no email has been sent.')

def mail_limits(db,email):
    consume(db,'mail:minute',10,60)
    consume(db,'mail:day',settings.mail_requests_per_day,86400)
    consume(db,'mail:address:'+email.strip().lower(),3,3600)

def revoke_actions(db,user_id):
    db.execute(update(ActionToken).where(ActionToken.user_id==user_id,ActionToken.consumed_at.is_(None)).values(consumed_at=now()))

def issue(db,user,purpose):
    # Caller reserves rate limits first. Lock order is always User -> ActionToken.
    user=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not user or user.disabled: return False
    db.execute(update(ActionToken).where(ActionToken.user_id==user.id,ActionToken.purpose==purpose,ActionToken.consumed_at.is_(None)).values(consumed_at=now()))
    raw=secrets.token_urlsafe(48)
    hashed=digest(raw)
    row=ActionToken(token_hash=hashed,user_id=user.id,purpose=purpose,
                    expires_at=now()+timedelta(minutes=30) if purpose=='reset' else now()+timedelta(hours=24))
    db.add(row);db.commit()
    link=settings.app_origin.rstrip('/')+'/#'+urlencode({'account-action':purpose,'token':raw})
    sent=email_delivery.send(user.email,purpose,link)
    row.delivery_status='sent' if sent else 'failed'
    if not sent: row.consumed_at=now()
    db.commit()
    return sent

@router.get('/auth/email/status')
def mail_status():
    return {'available':email_delivery.available()}

@router.post('/auth/password/forgot',status_code=202)
def forgot(data:EmailInput,db:DBSession=Depends(get_db)):
    require_mail()
    email=data.email.strip().lower()
    mail_limits(db,email)
    user=db.scalar(select(User).where(User.email==email))
    if user and not user.disabled:
        issue(db,user,'reset')
    # Delivery failures are recorded privately; public responses never identify accounts.
    return {'message':'If an eligible account exists, a password recovery email has been requested. If it does not arrive, contact the platform owner.'}

@router.post('/auth/email/resend',status_code=202)
def resend(user=Depends(current_user),db:DBSession=Depends(get_db)):
    if user.email_verified_at: return {'message':'Your email is already verified.'}
    require_mail();mail_limits(db,user.email)
    if not issue(db,user,'verify'): raise HTTPException(502,'Email delivery failed. Try again later or contact the platform owner.')
    return {'message':'Verification email accepted by the delivery provider. Check your inbox.'}

def valid_action(db,raw,purpose):
    row=db.get(ActionToken,digest(raw))
    if not row or row.purpose!=purpose or row.consumed_at or row.delivery_status!='sent' or row.expires_at.replace(tzinfo=timezone.utc)<=now():
        raise HTTPException(400,'This link is invalid, expired, or already used. Request a new email.')
    user=db.scalar(select(User).where(User.id==row.user_id).with_for_update().execution_options(populate_existing=True))
    if not user or user.disabled: raise HTTPException(400,'This link is invalid, expired, or already used. Request a new email.')
    return row,user

def consume_action(db,row):
    claimed=db.scalar(update(ActionToken).where(ActionToken.token_hash==row.token_hash,
        ActionToken.consumed_at.is_(None),ActionToken.expires_at>now(),ActionToken.delivery_status=='sent').values(consumed_at=now()).execution_options(synchronize_session=False).returning(ActionToken.token_hash))
    if not claimed: raise HTTPException(400,'This link is invalid, expired, or already used. Request a new email.')

def action_limits(db,raw):
    """Bound invalid-link traffic without storing one bucket per guessed token."""
    consume(db,'action:global',60,60)
    hashed=digest(raw)
    if not db.get(ActionToken,hashed):
        raise HTTPException(400,'This link is invalid, expired, or already used. Request a new email.')
    consume(db,'action:'+hashed,5,60)

@router.post('/auth/password/reset',status_code=204)
def reset(data:ResetInput,response:Response,db:DBSession=Depends(get_db)):
    action_limits(db,data.token)
    row,user=valid_action(db,data.token,data.purpose)
    hashed=hasher.hash(data.new_password)
    consume_action(db,row)
    user.password_hash=hashed
    user.email_verified_at=user.email_verified_at or now()
    revoke_actions(db,user.id)
    db.execute(delete(Session).where(Session.user_id==user.id))
    db.commit();response.delete_cookie('session',path='/')

@router.post('/auth/email/verify',status_code=204)
def verify_email(data:TokenInput,db:DBSession=Depends(get_db)):
    action_limits(db,data.token)
    row,user=valid_action(db,data.token,'verify')
    consume_action(db,row);user.email_verified_at=now();db.commit()

def public_user(db,user):
    latest=db.scalar(select(ActionToken).where(ActionToken.user_id==user.id).order_by(ActionToken.created_at.desc()).limit(1))
    return {'id':user.id,'email':user.email,'role':user.role,'business_id':user.business_id,
            'business_role':business_role(db,user),'disabled':user.disabled,'email_verified':bool(user.email_verified_at),
            'last_delivery':{'purpose':latest.purpose,'status':latest.delivery_status,'at':latest.created_at} if latest else None}

@router.get('/users',dependencies=[Depends(admin)])
def list_users(business_id:str|None=None,offset:int=0,db:DBSession=Depends(get_db)):
    query=select(User)
    if business_id: query=query.where(User.business_id==business_id)
    return [public_user(db,u) for u in db.scalars(query.order_by(User.email).offset(max(offset,0)).limit(100))]

@router.post('/users/invite',status_code=201,dependencies=[Depends(admin)])
def invite(data:InviteInput,db:DBSession=Depends(get_db)):
    require_mail()
    if not db.get(Business,data.business_id): raise HTTPException(404,'Business not found')
    email=data.email.lower().strip()
    mail_limits(db,email)
    user=User(email=email,password_hash=hasher.hash(secrets.token_urlsafe(48)),role='client',business_id=data.business_id)
    try:
        db.add(user);db.flush()
        db.add(Membership(business_id=data.business_id,user_id=user.id,role=data.business_role))
        db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'An account with that email already exists')
    # The account/token commit precedes mail delivery. A failed invitation can be
    # retried through the admin setup action, without creating another account.
    sent=issue(db,user,'setup')
    return {'id':user.id,'email':user.email,'delivery':'sent' if sent else 'failed'}

@router.post('/users/{user_id}/setup',status_code=202,dependencies=[Depends(admin)])
def send_setup(user_id:str,db:DBSession=Depends(get_db)):
    require_mail()
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,'User not found')
    mail_limits(db,user.email)
    if not issue(db,user,'setup'): raise HTTPException(502,'Setup email delivery failed. The account remains; retry this action later.')
    return {'message':'Setup email accepted by the delivery provider.'}

@router.put('/users/{user_id}/status',dependencies=[Depends(admin)])
def set_account_status(user_id:str,data:StatusInput,db:DBSession=Depends(get_db)):
    # Lock all admins in deterministic order so concurrent disables cannot remove
    # the final active administrator. Existing administrators are never auto-verified.
    admins=db.scalars(select(User).where(User.role=='admin').order_by(User.id).with_for_update().execution_options(populate_existing=True)).all()
    user=db.scalar(select(User).where(User.id==user_id).with_for_update().execution_options(populate_existing=True))
    if not user: raise HTTPException(404,'User not found')
    if data.disabled and user.role=='admin' and not user.disabled and sum(not u.disabled for u in admins)<=1:
        raise HTTPException(409,'Cannot disable the final active platform administrator')
    user.disabled=data.disabled
    if data.disabled:
        db.execute(delete(Session).where(Session.user_id==user.id));revoke_actions(db,user.id)
    db.commit()
    return public_user(db,user)

@router.get('/businesses/{business_id}/members',dependencies=[Depends(admin),Depends(tenant)])
def members(business_id:str,db:DBSession=Depends(get_db)):
    return [public_user(db,u) for u in db.scalars(select(User).where(User.business_id==business_id,User.role=='client').order_by(User.email).limit(100))]

@router.put('/businesses/{business_id}/members/{user_id}',dependencies=[Depends(admin),Depends(tenant)])
def set_membership(business_id:str,user_id:str,data:RoleInput,db:DBSession=Depends(get_db)):
    user=db.scalar(select(User).where(User.id==user_id,User.business_id==business_id,User.role=='client').with_for_update())
    if not user: raise HTTPException(404,'Client account not found in this business')
    row=db.get(Membership,(business_id,user_id))
    if row: row.role=data.role
    else: db.add(Membership(business_id=business_id,user_id=user_id,role=data.role))
    db.commit();return public_user(db,user)
