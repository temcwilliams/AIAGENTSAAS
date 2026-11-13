"""Public tenant registration and one-time, token-authorized owner setup."""
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from .config import settings
from .db import get_db
from .limits import consume
from .models import Business, User, Session, OwnerSetup, now
from .schemas import Registration
from .security import digest, hasher

router = APIRouter(prefix='/auth')

@router.post('/register', status_code=201)
def register(data: Registration, response: Response, db: DBSession=Depends(get_db)):
    email=data.email.strip().lower()
    # Shared database limits do not trust client-supplied IP headers.
    consume(db,'registration:global',limit=50,seconds=3600)
    consume(db,f'registration:{email}',limit=5,seconds=3600)
    owner=bool(data.setup_token)
    if owner:
        expected=settings.owner_setup_token_hash
        if not expected or not secrets.compare_digest(digest(data.setup_token),expected):
            raise HTTPException(403,'Invalid owner setup code')
        if db.scalar(select(User.id).where(User.role=='admin').limit(1)):
            raise HTTPException(409,'Owner setup has already been completed')
    if db.scalar(select(User.id).where(User.email==email)):
        raise HTTPException(409,'An account with that email already exists. Sign in instead.')
    password_hash=hasher.hash(data.password)
    token=secrets.token_urlsafe(48)
    try:
        if owner:
            # A unique singleton claim serializes competing owner requests even
            # when different emails race. Claim, account, and session are atomic.
            db.add(OwnerSetup(id='platform-owner',completed_at=now()))
            db.flush()
        business=Business(name=data.business_name.strip())
        db.add(business);db.flush()
        user=User(email=email,password_hash=password_hash,role='admin' if owner else 'client',business_id=business.id)
        db.add(user);db.flush()
        db.add(Session(token_hash=digest(token),user_id=user.id,expires_at=now()+timedelta(hours=settings.session_hours)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Account or owner setup already exists. Sign in instead.')
    response.set_cookie('session',token,httponly=True,secure=settings.environment=='production',samesite='strict',max_age=settings.session_hours*3600,path='/')
    return {'id':user.id,'email':user.email,'role':user.role,'business_id':user.business_id}
