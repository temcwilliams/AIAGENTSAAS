"""Authenticated local-model bridge. Run behind HTTPS, never expose Ollama itself."""
import asyncio
import os
import secrets
import time
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, model_validator
import httpx

secret=os.environ.get('MEADOW_BRIDGE_TOKEN','')
if len(secret)<32:raise RuntimeError('Set MEADOW_BRIDGE_TOKEN to a random secret of at least 32 characters')
app=FastAPI(title='Agent Meadow local inference bridge',docs_url=None,redoc_url=None,openapi_url=None)
security=HTTPBearer(auto_error=False)
semaphore=asyncio.Semaphore(1)
window_start=time.monotonic()
request_count=0

@app.middleware('http')
async def protect_body(request:Request,call_next):
    authorization=request.headers.get('authorization','')
    scheme,_,token=authorization.partition(' ')
    if scheme.lower()!='bearer' or not secrets.compare_digest(token,secret):
        return JSONResponse({'detail':'Authentication required'},status_code=401)
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>256000:return JSONResponse({'detail':'Request too large'},status_code=413)
        chunks.append(chunk)
    request._body=b''.join(chunks)
    return await call_next(request)

def authorized(credentials:HTTPAuthorizationCredentials=Depends(security)):
    if not credentials or not secrets.compare_digest(credentials.credentials,secret):raise HTTPException(401,'Authentication required')

class Turn(BaseModel):
    role:Literal['system','user','assistant']
    content:str=Field(max_length=60000)
class Completion(BaseModel):
    model:str=Field(min_length=1,max_length=100)
    messages:list[Turn]=Field(min_length=1,max_length=42)
    temperature:float=Field(default=0.7,ge=0,le=2)
    max_tokens:int=Field(default=512,ge=1,le=4096)
    @model_validator(mode='after')
    def context_limit(self):
        if sum(len(turn.content) for turn in self.messages)>60000:raise ValueError('Context too large')
        return self

async def upstream(method,path,payload=None):
    try:
        async with httpx.AsyncClient(timeout=180,trust_env=False,follow_redirects=False) as client:
            response=await client.request(method,'http://127.0.0.1:11434/v1/'+path,json=payload)
            response.raise_for_status();return response.json()
    except (httpx.HTTPError,ValueError):raise HTTPException(502,'Local Ollama request failed')

@app.get('/v1/models',dependencies=[Depends(authorized)])
async def models():return await upstream('GET','models')

@app.post('/v1/chat/completions',dependencies=[Depends(authorized)])
async def complete(data:Completion):
    global window_start,request_count
    current=time.monotonic()
    if current-window_start>=3600:window_start=current;request_count=0
    if request_count>=60:raise HTTPException(429,'Bridge hourly request limit reached')
    request_count+=1
    if semaphore.locked():raise HTTPException(429,'Local model is busy; try again shortly')
    async with semaphore:return await upstream('POST','chat/completions',data.model_dump())
