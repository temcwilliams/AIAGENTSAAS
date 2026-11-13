"""Run Next.js + loopback-only FastAPI in one Render instance."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main():
    port = int(os.environ.get('PORT', '10000'))
    if not 1 <= port <= 65535 or port == 8123:
        raise SystemExit('PORT must be valid and different from internal port 8123')
    # Free Render instances do not provide pre-deploy commands. Deploying this
    # template authorizes this migration on every start (including cold starts).
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',check=True)
    children=[]
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8123'],cwd=ROOT/'backend'))
        children.append(subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port',str(port)],cwd=ROOT/'frontend',env={**os.environ,'BACKEND_URL':'http://127.0.0.1:8123'}))
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise SystemExit('A server exited; restarting the service is required')
            time.sleep(0.25)
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        deadline=time.monotonic()+10
        for child in children:
            try:child.wait(timeout=max(0.1,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:child.kill();child.wait()

if __name__=='__main__':main()
