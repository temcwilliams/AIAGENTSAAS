import os
os.environ['ENVIRONMENT']='test'
os.environ['AI_PROVIDER']='cloud'
os.environ['DATABASE_URL']='sqlite://'
os.environ['APP_ORIGIN']='http://testserver'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app
from app.models import Business, User
from app.security import hasher

@pytest.fixture()
def setup():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    from sqlalchemy import event
    event.listen(engine,'connect',lambda conn,_:conn.execute('PRAGMA foreign_keys=ON'))
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    with factory() as db:
        db.add_all([Business(id='a',name='Alpha'),Business(id='b',name='Beta')]);db.commit()
        for email,role,bid in [('admin@example.com','admin',None),('a@example.com','client','a'),('b@example.com','client','b')]:
            db.add(User(email=email,role=role,business_id=bid,password_hash=hasher.hash('Test-password-123!')))
        db.commit()
    def override():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app,headers={'Origin':'http://testserver'}) as client: yield client,factory
    app.dependency_overrides.clear();engine.dispose()

def login(client,email='admin@example.com'):
    return client.post('/auth/login',json={'email':email,'password':'Test-password-123!'})
