"""Real populated SQLite migrations; PostgreSQL is validated separately."""
import os, sqlite3, subprocess, sys
from pathlib import Path

def test_populated_release_a_upgrade_backfill_and_round_trip(tmp_path):
    database=tmp_path/'release-a.db'
    backend=Path(__file__).resolve().parents[1]
    env={**os.environ,'ENVIRONMENT':'test','DATABASE_URL':'sqlite:///'+str(database),'DATABASE_URL_UNPOOLED':'','AI_PROVIDER':'disabled','EMAIL_PROVIDER':'disabled'}
    def migrate(*args):
        subprocess.run([sys.executable,'-m','alembic',*args],cwd=backend,env=env,check=True,capture_output=True,text=True)
    migrate('upgrade','0004')
    with sqlite3.connect(database) as db:
        db.executescript("""
INSERT INTO businesses (id,name,created_at) VALUES ('tenant','Existing business','2026-01-01');
INSERT INTO users (id,email,password_hash,role,business_id) VALUES ('owner','owner@example.com','old-owner-hash','admin',NULL),('client','client@example.com','old-client-hash','client','tenant');
INSERT INTO sessions (token_hash,user_id,expires_at) VALUES ('existing-session','client','2030-01-01');
INSERT INTO agents (id,business_id,name,model,system_prompt,temperature,max_tokens,enabled) VALUES ('agent','tenant','Existing agent','old-model','Approved existing prompt',0.5,512,1);
INSERT INTO conversations (id,business_id,agent_id,status,handoff_reason,created_at) VALUES ('conversation','tenant','agent','human','Existing reason','2026-01-01');
INSERT INTO messages (id,business_id,conversation_id,role,content,sources,created_at) VALUES ('message','tenant','conversation','user','Existing transcript','[]','2026-01-01');
INSERT INTO usage (id,business_id,conversation_id,model,prompt_tokens,completion_tokens,created_at) VALUES ('usage','tenant','conversation','old-model',7,8,'2026-01-01');
INSERT INTO leads (id,business_id,name,email,notes,source,created_at) VALUES ('lead','tenant','Lead','lead@example.com','Existing notes','manual','2026-01-01');
INSERT INTO knowledge_documents (id,business_id,title,content,enabled,created_at) VALUES ('document','tenant','Existing knowledge','Existing facts',1,'2026-01-01');
""")
    migrate('upgrade','head')
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()==('0006',)
        assert db.execute('SELECT business_id,user_id,role FROM memberships').fetchall()==[('tenant','client','viewer')]
        assert db.execute('SELECT email_verified_at,disabled FROM users ORDER BY id').fetchall()==[(None,0),(None,0)]
        assert db.execute('SELECT password_hash FROM users ORDER BY id').fetchall()==[('old-client-hash',),('old-owner-hash',)]
        assert db.execute('SELECT token_hash FROM sessions').fetchall()==[('existing-session',)]
        assert db.execute('SELECT content FROM messages').fetchall()==[('Existing transcript',)]
        assert db.execute('SELECT prompt_tokens,completion_tokens FROM usage').fetchall()==[(7,8)]
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    migrate('downgrade','0004');migrate('upgrade','head')
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT role FROM memberships').fetchall()==[('viewer',)]
        assert db.execute('SELECT system_prompt FROM agents').fetchall()==[('Approved existing prompt',)]
        assert db.execute('SELECT content FROM knowledge_documents').fetchall()==[('Existing facts',)]
        assert db.execute('SELECT notes FROM leads').fetchall()==[('Existing notes',)]
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    migrate('downgrade','base');migrate('upgrade','head')
