from datetime import timezone
from anyio import from_thread
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session as DBSession
import httpx
from .db import get_db, locked_scalar
from .security import tenant, admin
from .models import Agent, Conversation, Usage, Message, KnowledgeDocument, now
from .schemas import KnowledgeInput, HandoffInput, HandoffStatus, HumanReply
from .config import settings
from .limits import consume

router=APIRouter(prefix='/businesses/{business_id}',dependencies=[Depends(tenant)])

def resource(db,model,business_id,id,lock=False):
    q=select(model).where(model.id==id,model.business_id==business_id)
    row=locked_scalar(db,q) if lock else db.scalar(q)
    if not row:raise HTTPException(404,'Resource not found')
    return row

@router.get('/knowledge')
def documents(business_id:str,db:DBSession=Depends(get_db)):
    return db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.business_id==business_id).order_by(KnowledgeDocument.created_at.desc()).limit(100)).all()

@router.post('/knowledge',status_code=201,dependencies=[Depends(admin)])
def add_document(business_id:str,data:KnowledgeInput,db:DBSession=Depends(get_db)):
    if db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.business_id==business_id))>=100:raise HTTPException(409,'Document limit reached; update an existing document')
    row=KnowledgeDocument(business_id=business_id,**data.model_dump());db.add(row);db.commit();return row

@router.put('/knowledge/{document_id}',dependencies=[Depends(admin)])
def update_document(business_id:str,document_id:str,data:KnowledgeInput,db:DBSession=Depends(get_db)):
    row=resource(db,KnowledgeDocument,business_id,document_id)
    for key,value in data.model_dump().items():setattr(row,key,value)
    db.commit();return row

@router.get('/handoffs')
def handoffs(business_id:str,db:DBSession=Depends(get_db)):
    return db.scalars(select(Conversation).where(Conversation.business_id==business_id,Conversation.status.in_(['requested','human'])).order_by(Conversation.handoff_requested_at).limit(100)).all()

@router.post('/conversations/{conversation_id}/handoff')
def request_handoff(business_id:str,conversation_id:str,data:HandoffInput,db:DBSession=Depends(get_db)):
    row=resource(db,Conversation,business_id,conversation_id,True)
    if row.status not in ('requested','human'):
        row.status='requested';row.handoff_reason=data.reason;row.handoff_requested_at=now()
    db.commit();return row

@router.post('/conversations/{conversation_id}/handoff/status',dependencies=[Depends(admin)])
def set_status(business_id:str,conversation_id:str,data:HandoffStatus,db:DBSession=Depends(get_db)):
    row=resource(db,Conversation,business_id,conversation_id,True)
    row.status=data.status;db.commit();return row

@router.post('/conversations/{conversation_id}/reply',status_code=201,dependencies=[Depends(admin)])
def human_reply(business_id:str,conversation_id:str,data:HumanReply,db:DBSession=Depends(get_db)):
    row=resource(db,Conversation,business_id,conversation_id,True)
    if row.status!='human':raise HTTPException(409,'Take over this conversation before replying')
    message=Message(business_id=business_id,conversation_id=conversation_id,role='human',content=data.content)
    db.add(message);db.commit();return message

@router.get('/floor')
def floor(business_id:str,db:DBSession=Depends(get_db)):
    agents=db.scalars(select(Agent).where(Agent.business_id==business_id).order_by(Agent.name).limit(100)).all()
    counts=dict(db.execute(select(Conversation.agent_id,func.count(Conversation.id)).where(Conversation.business_id==business_id).group_by(Conversation.agent_id)).all())
    alerts=dict(db.execute(select(Conversation.agent_id,func.count(Conversation.id)).where(Conversation.business_id==business_id,Conversation.status.in_(['requested','human'])).group_by(Conversation.agent_id)).all())
    usage={id:(requests,tokens) for id,requests,tokens in db.execute(select(Conversation.agent_id,func.count(Usage.id),func.coalesce(func.sum(Usage.prompt_tokens+Usage.completion_tokens),0)).join(Usage,and_(Usage.conversation_id==Conversation.id,Usage.business_id==Conversation.business_id)).where(Conversation.business_id==business_id).group_by(Conversation.agent_id)).all()}
    activity=dict(db.execute(select(Conversation.agent_id,func.max(Message.created_at)).join(Message,and_(Message.conversation_id==Conversation.id,Message.business_id==Conversation.business_id)).where(Conversation.business_id==business_id).group_by(Conversation.agent_id)).all())
    return {'updated_at':now(),'inference':settings.ai_provider,'agents':[{'id':a.id,'name':a.name,'model':a.model,'enabled':a.enabled,'status':'paused' if not a.enabled else 'attention' if alerts.get(a.id) else 'ready','conversations':counts.get(a.id,0),'handoffs':alerts.get(a.id,0),'requests':usage.get(a.id,(0,0))[0],'tokens':usage.get(a.id,(0,0))[1],'last_activity':activity.get(a.id)} for a in agents]}

@router.get('/inference')
def inference(business_id:str):
    return {'mode':settings.ai_provider,'configured':settings.ai_provider=='local' or settings.ai_provider in ('cloud','bridge') and bool(settings.openai_api_key),'local_model':'qwen2.5:1.5b'}

@router.post('/inference/check',dependencies=[Depends(admin)])
def check_inference(business_id:str,db:DBSession=Depends(get_db)):
    consume(db,f'inference-check:{business_id}',10,3600)
    return from_thread.run(fetch_inference_models)

async def fetch_inference_models():
    if settings.ai_provider=='disabled' or settings.ai_provider in ('cloud','bridge') and not settings.openai_api_key:raise HTTPException(503,'Inference is not configured')
    headers={'Authorization':f'Bearer {settings.openai_api_key}'} if settings.ai_provider in ('cloud','bridge') else {}
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False,trust_env=settings.ai_provider in ('cloud','bridge')) as client:
            response=await client.get(settings.openai_base_url.rstrip('/')+'/models',headers=headers);response.raise_for_status()
            data=response.json()['data']
            models=[str(item['id'])[:100] for item in data[:100]]
        return {'reachable':True,'models':models}
    except (httpx.HTTPError,KeyError,TypeError,ValueError):raise HTTPException(502,'Could not reach a compatible model server')
