"""Offline operator command; never exposes public admin registration."""
import getpass
from sqlalchemy import select
from .db import SessionLocal
from .models import User
from .security import hasher
from .schemas import Credentials

def main():
    credentials = Credentials(email=input('Admin email: '), password=getpass.getpass('Password (12+ characters): '))
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == 'admin')):
            raise SystemExit('An administrator already exists; refusing bootstrap.')
        db.add(User(email=credentials.email.lower().strip(), password_hash=hasher.hash(credentials.password), role='admin'))
        db.commit()
    print('Administrator created.')
if __name__ == '__main__': main()
