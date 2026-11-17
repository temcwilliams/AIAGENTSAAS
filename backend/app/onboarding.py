"""Versioned business drafts. Only owner approval/publication changes active configuration."""
from typing import Literal
from datetime import timezone
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .security import tenant, admin, current_user, permission
from .models import Business, Agent, KnowledgeDocument, OnboardingDraft, now
from .limits import consume

router=APIRouter(prefix='/businesses/{business_id}',dependencies=[Depends(tenant)])
TEMPLATES={
    'reception':{'version':1,'label':'General reception','prompt':'You are a business reception assistant. Answer practical questions using approved business facts, help visitors find the right service, and offer a human handoff when needed.'},
    'support':{'version':1,'label':'Customer support','prompt':'You are a customer support assistant. Use approved business facts to explain services and common solutions. Do not invent policies or commitments. Offer a human handoff for unresolved issues.'},
    'leads':{'version':1,'label':'Lead qualification','prompt':'You are a business inquiry assistant. Understand the visitor’s needs using approved business facts, ask concise relevant questions, and offer human assistance. Never pressure visitors to share contact details; saving contact details requires explicit consent.'},
}

class Profile(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    business_name:str=Field(default='',max_length=120)
    description:str=Field(default='',max_length=2000)
    contact_name:str=Field(default='',max_length=120)
    contact_email:str=Field(default='',max_length=254)
    phone:str=Field(default='',max_length=80)
    website:str=Field(default='',max_length=2048)
    services:str=Field(default='',max_length=4000)
    faqs:str=Field(default='',max_length=6000)
    hours:str=Field(default='',max_length=1000)
    handoff_preferences:str=Field(default='',max_length=2000)
    template:Literal['reception','support','leads']='reception'

    @field_validator('contact_email')
    @classmethod
    def email(cls,value):
        import re
        if value and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('Enter a valid contact email')
        return value

    @field_validator('website')
    @classmethod
    def website_url(cls,value):
        if value:
            parsed=urlsplit(value)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Use an HTTP or HTTPS website without credentials')
        return value

class VersionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=0)
class DraftInput(VersionInput):
    profile:Profile
class ReviewInput(VersionInput):
    decision:Literal['approved','changes_requested']
    notes:str=Field(default='',max_length=4000)
class PublishInput(VersionInput):
    model:str=Field(default='qwen2.5:1.5b',min_length=1,max_length=100,pattern=r'\S')
    enabled:bool=True

def output(row,business_id):
    if not row:
        return {'business_id':business_id,'version':0,'status':'draft','profile':Profile().model_dump(),
                'reviewer_notes':'','agent_id':None,'knowledge_id':None,'template_version':1,'published_at':None}
    return {'business_id':row.business_id,'version':row.version,'status':row.status,
            'profile':row.profile,'reviewer_notes':row.reviewer_notes,'agent_id':row.agent_id,
            'knowledge_id':row.knowledge_id,'template_version':row.template_version,
            'published_at':row.published_at.replace(tzinfo=timezone.utc) if row.published_at else None,
            'updated_at':row.updated_at.replace(tzinfo=timezone.utc)}

def lock_business(db,business_id):
    # Serializes initial draft creation too. These synchronous transactions never
    # await inference, mail or other network I/O while holding this lock.
    db.scalar(select(Business).where(Business.id==business_id).with_for_update())
    return db.scalar(select(OnboardingDraft).where(OnboardingDraft.business_id==business_id).with_for_update().execution_options(populate_existing=True))

def check_version(row,expected):
    if expected != (row.version if row else 0):
        raise HTTPException(409,'Setup changed in another session. Reload the latest version before saving.')

def complete(profile):
    missing=[label for field,label in [('business_name','business name'),('description','business description'),('contact_email','contact email'),('services','services'),('handoff_preferences','handoff preferences')] if not getattr(profile,field)]
    if missing: raise HTTPException(422,'Complete '+', '.join(missing)+' before submitting.')

def knowledge_text(profile):
    fields=[('Business','business_name'),('About','description'),('Contact name','contact_name'),('Contact email','contact_email'),('Phone','phone'),('Website','website'),('Opening hours','hours'),('Services','services'),('FAQs','faqs'),('Human handoff preferences','handoff_preferences')]
    return '\n\n'.join(label+':\n'+getattr(profile,key) for label,key in fields if getattr(profile,key))

@router.get('/onboarding')
def get_draft(business_id:str,db:DBSession=Depends(get_db)):
    return output(db.get(OnboardingDraft,business_id),business_id)

@router.get('/onboarding/templates')
def templates(business_id:str):
    return [{'id':key,'label':value['label'],'version':value['version']} for key,value in TEMPLATES.items()]

@router.put('/onboarding',dependencies=[Depends(permission('manager'))])
def save_draft(business_id:str,data:DraftInput,db:DBSession=Depends(get_db)):
    consume(db,'onboarding-write:'+business_id,120,3600)
    row=lock_business(db,business_id);check_version(row,data.expected_version)
    if row and row.status in ('submitted','approved'):
        raise HTTPException(409,'This setup is under review. Request changes before editing.')
    if not row:
        row=OnboardingDraft(business_id=business_id,version=1)
        db.add(row)
    else: row.version+=1
    row.profile=data.profile.model_dump();row.status='draft';row.reviewer_notes=''
    row.reviewed_by=None;row.updated_at=now()
    db.commit();return output(row,business_id)

@router.post('/onboarding/submit',dependencies=[Depends(permission('manager'))])
def submit(business_id:str,data:VersionInput,db:DBSession=Depends(get_db)):
    consume(db,'onboarding-write:'+business_id,120,3600)
    row=lock_business(db,business_id);check_version(row,data.expected_version)
    if not row or row.status not in ('draft','changes_requested'):
        raise HTTPException(409,'Save a draft before submitting it.')
    complete(Profile(**row.profile))
    row.status='submitted';row.submitted_at=now();row.updated_at=now();row.version+=1
    db.commit();return output(row,business_id)

@router.post('/onboarding/review',dependencies=[Depends(admin)])
def review(business_id:str,data:ReviewInput,user=Depends(current_user),db:DBSession=Depends(get_db)):
    row=lock_business(db,business_id);check_version(row,data.expected_version)
    if not row or row.status not in ('submitted','approved'):
        raise HTTPException(409,'Only submitted or approved setups can be reviewed.')
    if data.decision=='changes_requested' and not data.notes.strip():raise HTTPException(422,'Describe the changes the client should make.')
    if data.decision=='approved':complete(Profile(**row.profile))
    row.status=data.decision;row.reviewer_notes=data.notes.strip();row.reviewed_by=user.id
    row.updated_at=now();row.version+=1
    db.commit();return output(row,business_id)

@router.get('/onboarding/preview')
def preview(business_id:str,db:DBSession=Depends(get_db)):
    row=db.get(OnboardingDraft,business_id)
    profile=Profile(**row.profile) if row else Profile()
    template=TEMPLATES[profile.template]
    return {'preview_only':True,'template':template['label'],'template_version':template['version'],
            'system_prompt':template['prompt'],'knowledge':knowledge_text(profile),
            'inference_called':False}

@router.post('/onboarding/publish',dependencies=[Depends(admin)])
def publish(business_id:str,data:PublishInput,user=Depends(current_user),db:DBSession=Depends(get_db)):
    row=lock_business(db,business_id)
    if row and row.status=='published' and data.expected_version in (row.version,row.published_source_version):
        return output(row,business_id)
    check_version(row,data.expected_version)
    if not row or row.status!='approved':raise HTTPException(409,'An administrator must approve this setup before publication.')
    profile=Profile(**row.profile);complete(profile);template=TEMPLATES[profile.template]
    if not row.knowledge_id and db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.business_id==business_id))>=100:
        raise HTTPException(409,'Knowledge limit reached. Publication needs space for its managed onboarding document.')
    agent=db.scalar(select(Agent).where(Agent.id==row.agent_id,Agent.business_id==business_id)) if row.agent_id else None
    document=db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id==row.knowledge_id,KnowledgeDocument.business_id==business_id)) if row.knowledge_id else None
    if row.agent_id and not agent or row.knowledge_id and not document:raise HTTPException(409,'Published configuration is missing; ask the owner to restore it.')
    if not agent:
        agent=Agent(business_id=business_id,name='',model=data.model,system_prompt='')
        db.add(agent)
    if not document:
        document=KnowledgeDocument(business_id=business_id,title='',content='',enabled=True)
        db.add(document)
    agent.name=(profile.business_name+' assistant')[:120];agent.model=data.model
    agent.system_prompt=template['prompt'];agent.temperature=0.5;agent.max_tokens=512;agent.enabled=data.enabled
    document.title=('Approved onboarding · '+profile.business_name)[:200]
    document.content=knowledge_text(profile);document.enabled=True
    db.flush()
    row.agent_id=agent.id;row.knowledge_id=document.id;row.template_version=template['version']
    row.published_source_version=row.version;row.version+=1;row.status='published'
    row.published_at=now();row.updated_at=now();row.published_by=user.id
    db.get(Business,business_id).name=profile.business_name
    db.commit();return output(row,business_id)
