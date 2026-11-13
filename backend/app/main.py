import secrets
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from sqlalchemy import select, func, delete, case
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import get_db
from .models import Business, User, Session, LoginAttempt, Agent, Conversation, Message, Usage, Lead, now
from .schemas import Credentials, ClientCreate, BusinessInput, AgentInput, ChatInput, LeadInput, PasswordChange
from .security import current_user, admin, tenant, hasher, verify, digest, DUMMY_HASH
from . import ai
from .limits import consume

app = FastAPI(title="Agent Studio API", version="1.0.0")

@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("origin") != settings.app_origin:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Invalid origin"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.get("/health")
def health(db: DBSession=Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}

@app.post("/auth/login")
def login(data: Credentials, response: Response, db: DBSession=Depends(get_db)):
    email = data.email.lower().strip()
    key = digest(email)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    current = now()
    stmt = insert(LoginAttempt).values(key=key, count=1, reset_at=current+timedelta(minutes=15))
    expired = LoginAttempt.reset_at <= current
    stmt = stmt.on_conflict_do_update(index_elements=[LoginAttempt.key], set_={
        "count": case((expired, 1), else_=LoginAttempt.count+1),
        "reset_at": case((expired, current+timedelta(minutes=15)), else_=LoginAttempt.reset_at)
    }).returning(LoginAttempt.count)
    count = db.scalar(stmt)
    db.commit()
    if count > 10: raise HTTPException(429, "Try again in 15 minutes")
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    valid = verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid: raise HTTPException(401, "Invalid credentials")
    token = secrets.token_urlsafe(48)
    db.add(Session(token_hash=digest(token), user_id=user.id, expires_at=now()+timedelta(hours=settings.session_hours)))
    db.execute(delete(LoginAttempt).where(LoginAttempt.key == key)); db.commit()
    response.set_cookie("session", token, httponly=True, secure=settings.environment == "production", samesite="strict", max_age=settings.session_hours*3600, path="/")
    return {"id": user.id, "role": user.role, "business_id": user.business_id, "email": user.email}

@app.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DBSession=Depends(get_db)):
    db.execute(delete(Session).where(Session.token_hash == digest(request.cookies.get("session", ""))))
    db.commit(); response.delete_cookie("session", path="/")

@app.get("/auth/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "business_id": user.business_id}

@app.post("/auth/password", status_code=204)
def change_password(data: PasswordChange, response: Response, user=Depends(current_user), db: DBSession=Depends(get_db)):
    consume(db, f"password:{user.id}", limit=5, seconds=900)
    locked = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not verify(data.current_password, locked.password_hash):
        raise HTTPException(401, "Current password is incorrect")
    if data.current_password == data.new_password:
        raise HTTPException(422, "Choose a different password")
    locked.password_hash = hasher.hash(data.new_password)
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.commit()
    response.delete_cookie("session", path="/")

@app.post("/auth/logout-all", status_code=204)
def logout_all(response: Response, user=Depends(current_user), db: DBSession=Depends(get_db)):
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.commit()
    response.delete_cookie("session", path="/")

@app.post("/users", status_code=201, dependencies=[Depends(admin)])
def create_user(data: ClientCreate, db: DBSession=Depends(get_db)):
    if not db.get(Business, data.business_id): raise HTTPException(404, "Business not found")
    user = User(email=data.email.lower().strip(), password_hash=hasher.hash(data.password), role="client", business_id=data.business_id)
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Email already exists")
    return {"id": user.id, "email": user.email}

@app.get("/businesses")
def businesses(user=Depends(current_user), db: DBSession=Depends(get_db), offset: int=0):
    q = select(Business)
    if user.role != "admin": q = q.where(Business.id == user.business_id)
    return db.scalars(q.order_by(Business.created_at).offset(max(offset,0)).limit(100)).all()

@app.post("/businesses", status_code=201, dependencies=[Depends(admin)])
def create_business(data: BusinessInput, db: DBSession=Depends(get_db)):
    row = Business(**data.model_dump()); db.add(row); db.commit(); return row

@app.put("/businesses/{business_id}", dependencies=[Depends(admin), Depends(tenant)])
def update_business(business_id: str, data: BusinessInput, db: DBSession=Depends(get_db)):
    row = db.get(Business, business_id); row.name = data.name; db.commit(); return row

@app.get("/businesses/{business_id}/agents", dependencies=[Depends(tenant)])
def agents(business_id: str, db: DBSession=Depends(get_db)):
    return db.scalars(select(Agent).where(Agent.business_id == business_id).limit(100)).all()

@app.post("/businesses/{business_id}/agents", status_code=201, dependencies=[Depends(admin), Depends(tenant)])
def create_agent(business_id: str, data: AgentInput, db: DBSession=Depends(get_db)):
    row = Agent(business_id=business_id, **data.model_dump()); db.add(row); db.commit(); return row

@app.put("/businesses/{business_id}/agents/{agent_id}", dependencies=[Depends(admin), Depends(tenant)])
def update_agent(business_id: str, agent_id: str, data: AgentInput, db: DBSession=Depends(get_db)):
    row = scoped(db, Agent, business_id, agent_id)
    for key,value in data.model_dump().items(): setattr(row,key,value)
    db.commit(); return row

def scoped(db, model, business_id, id):
    row = db.scalar(select(model).where(model.id == id, model.business_id == business_id))
    if not row: raise HTTPException(404, "Resource not found")
    return row

@app.post("/businesses/{business_id}/agents/{agent_id}/conversations", status_code=201, dependencies=[Depends(tenant)])
def new_conversation(business_id: str, agent_id: str, db: DBSession=Depends(get_db)):
    scoped(db, Agent, business_id, agent_id)
    row = Conversation(business_id=business_id, agent_id=agent_id); db.add(row); db.commit(); return row

@app.get("/businesses/{business_id}/conversations", dependencies=[Depends(tenant)])
def conversations(business_id: str, offset: int=0, db: DBSession=Depends(get_db)):
    return db.scalars(select(Conversation).where(Conversation.business_id == business_id).order_by(Conversation.created_at.desc()).offset(max(0,offset)).limit(100)).all()

@app.get("/businesses/{business_id}/conversations/{conversation_id}/messages", dependencies=[Depends(tenant)])
def messages(business_id: str, conversation_id: str, db: DBSession=Depends(get_db)):
    scoped(db, Conversation, business_id, conversation_id)
    return db.scalars(select(Message).where(Message.business_id == business_id, Message.conversation_id == conversation_id).order_by(Message.created_at).limit(200)).all()

@app.post("/businesses/{business_id}/conversations/{conversation_id}/messages", dependencies=[Depends(tenant)])
async def chat(business_id: str, conversation_id: str, data: ChatInput, db: DBSession=Depends(get_db)):
    # Validate resource ownership before reserving a business-wide attempt.
    initial = scoped(db, Conversation, business_id, conversation_id)
    initial_agent = scoped(db, Agent, business_id, initial.agent_id)
    if not initial_agent.enabled: raise HTTPException(409, "Agent is disabled")
    consume(db, f"chat:{business_id}", settings.chat_requests_per_hour, seconds=3600)
    # Row lock serializes turns for this conversation on PostgreSQL.
    conv = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.business_id == business_id).with_for_update())
    if not conv: raise HTTPException(404, "Resource not found")
    agent = scoped(db, Agent, business_id, conv.agent_id)
    if not agent.enabled: raise HTTPException(409, "Agent is disabled")
    history = db.scalars(select(Message).where(Message.conversation_id == conv.id, Message.business_id == business_id).order_by(Message.created_at.desc()).limit(40)).all()
    payload = [{"role":"system", "content":agent.system_prompt}] + [{"role":m.role,"content":m.content} for m in reversed(history)] + [{"role":"user","content":data.content}]
    if sum(len(m["content"]) for m in payload) > 60000: raise HTTPException(422, "Context too large; start a new conversation")
    content, prompt_tokens, completion_tokens = await ai.complete(agent, payload)
    for role,text in [("user", data.content), ("assistant",content)]:
        db.add(Message(business_id=business_id, conversation_id=conv.id, role=role, content=text))
    db.add(Usage(business_id=business_id, conversation_id=conv.id, model=agent.model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))
    db.commit()
    return {"content": content, "prompt_tokens":prompt_tokens, "completion_tokens":completion_tokens}

@app.get("/businesses/{business_id}/leads", dependencies=[Depends(tenant)])
def leads(business_id: str, db: DBSession=Depends(get_db)):
    return db.scalars(select(Lead).where(Lead.business_id == business_id).order_by(Lead.created_at.desc()).limit(100)).all()

@app.post("/businesses/{business_id}/leads", status_code=201, dependencies=[Depends(admin), Depends(tenant)])
def create_lead(business_id: str, data: LeadInput, db: DBSession=Depends(get_db)):
    row = Lead(business_id=business_id, **data.model_dump()); db.add(row); db.commit(); return row

@app.get("/businesses/{business_id}/usage", dependencies=[Depends(tenant)])
def usage(business_id: str, db: DBSession=Depends(get_db)):
    tokens = db.execute(select(func.coalesce(func.sum(Usage.prompt_tokens),0), func.coalesce(func.sum(Usage.completion_tokens),0),func.count(Usage.id)).where(Usage.business_id == business_id)).one()
    return {"prompt_tokens":tokens[0], "completion_tokens":tokens[1], "requests":tokens[2], "conversations":db.scalar(select(func.count(Conversation.id)).where(Conversation.business_id == business_id)), "leads":db.scalar(select(func.count(Lead.id)).where(Lead.business_id == business_id))}
