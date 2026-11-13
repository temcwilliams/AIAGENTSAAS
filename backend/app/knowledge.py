"""Small, bounded lexical retrieval with no embedding provider or external fetch."""
import re
from sqlalchemy import select
from .models import KnowledgeDocument


def retrieve(db,business_id,query):
    terms=set(re.findall(r'[a-z0-9]{3,}',query.lower()))-{'the','and','are','you','your','can','what','how','does','for','with','this','that'}
    documents=db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.business_id==business_id,KnowledgeDocument.enabled==True).order_by(KnowledgeDocument.created_at.desc()).limit(100)).all()
    ranked=[]
    for document in documents:
        for offset in range(0,len(document.content),800):
            chunk=document.content[offset:offset+1000]
            words=set(re.findall(r'[a-z0-9]{3,}',(document.title+' '+chunk).lower()))
            score=len(terms & words)
            if score:ranked.append((score,document.id,offset,document.title,chunk))
    ranked.sort(key=lambda item:(-item[0],item[1],item[2]))
    selected=ranked[:4]
    sources=[]
    for _,id,_,title,_ in selected:
        if not any(source['id']==id for source in sources):sources.append({'id':id,'title':title})
    context='\n\n'.join(f'[Reference: {title}]\n{chunk}' for _,_,_,title,chunk in selected)
    return context,sources
