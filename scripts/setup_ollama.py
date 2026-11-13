#!/usr/bin/env python3
"""Rootless Linux setup for Ollama + the authenticated Agent Meadow bridge."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
MODELS=('qwen2.5:1.5b','qwen2.5:0.5b')
GIB=1024**3
class SetupError(Exception):pass

def state_directory():
    return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share'))).expanduser()/'agent-meadow'

def architecture():
    value=platform.machine().lower()
    if value in ('x86_64','amd64'):return 'amd64'
    if value in ('aarch64','arm64'):return 'arm64'
    raise SetupError('Supported Linux architectures: x86_64 and arm64.')

def private_file(path,text):
    path=Path(path)
    if path.is_symlink():raise SetupError('Refusing a symbolic link for a private configuration file.')
    flags=os.O_WRONLY|os.O_CREAT|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path,flags,0o600)
    try:
        if os.fstat(fd).st_uid!=os.getuid():raise SetupError('Private configuration must be owned by your Linux user.')
        os.fchmod(fd,0o600)
        os.ftruncate(fd,0)
        with os.fdopen(fd,'w',closefd=False) as file:file.write(text)
    finally:os.close(fd)

def ensure_token(path):
    path=Path(path)
    if path.is_symlink():raise SetupError('Refusing a symbolic link for the bridge token.')
    if path.exists():
        mode=path.stat()
        if mode.st_uid!=os.getuid() or stat.S_IMODE(mode.st_mode)&0o077:raise SetupError('Existing token must be owned by you with permissions 600.')
        token=path.read_text().strip()
        if not 32<=len(token)<=256 or not token.isascii():raise SetupError('Existing bridge token is invalid; it was not overwritten.')
        return token
    token=secrets.token_urlsafe(48)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w') as file:file.write(token+'\n')
    return token

def local_json(port,path,body=None,token=None,timeout=10):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    request=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=json.dumps(body).encode() if body is not None else None,headers=headers,method='POST' if body is not None else 'GET')
    # Local credentials and model requests must never use an environment proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=timeout) as response:return json.load(response)

def release_asset(repo,name,destination):
    request=urllib.request.Request('https://api.github.com/repos/'+repo+'/releases/latest',headers={'User-Agent':'Agent-Meadow-Linux-Setup','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=30) as response:release=json.load(response)
    asset=next((item for item in release['assets'] if item['name']==name),None)
    if not asset:raise SetupError('Publisher release does not include '+name+'; install it using the official instructions.')
    url=asset['browser_download_url']
    if not url.startswith('https://github.com/'+repo+'/releases/download/'):raise SetupError('Unexpected publisher download URL.')
    expected=asset.get('digest','')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',expected):raise SetupError('Publisher checksum is unavailable; install this tool manually using official instructions.')
    temporary=Path(str(destination)+'.part');digest=hashlib.sha256()
    print('Downloading '+name+' from its official publisher…',flush=True)
    try:
        with urllib.request.urlopen(url,timeout=120) as response,temporary.open('wb') as file:
            while chunk:=response.read(1024*1024):digest.update(chunk);file.write(chunk)
        if digest.hexdigest()!=expected.split(':',1)[1]:raise SetupError('Download checksum verification failed.')
        temporary.replace(destination)
    finally:
        if temporary.exists():temporary.unlink()

def install_ollama(state,arch):
    existing=shutil.which('ollama')
    if existing:return existing
    destination=state/'ollama';binary=destination/'bin/ollama'
    if binary.exists() and (destination/'.installed').exists():return str(binary)
    if not shutil.which('zstd') or not shutil.which('tar'):raise SetupError('Install zstd and tar first (Ubuntu/Debian: sudo apt-get install zstd tar).')
    archive=state/'ollama.tar.zst'
    release_asset('ollama/ollama','ollama-linux-'+arch+'.tar.zst',archive)
    listing=subprocess.check_output(['tar','--zstd','-tf',str(archive)],text=True)
    if any(PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts for name in listing.splitlines()):raise SetupError('Unsafe archive path; extraction cancelled.')
    destination.mkdir(exist_ok=True)
    subprocess.run(['tar','--zstd','-xf',str(archive),'--no-same-owner','--no-same-permissions','-C',str(destination)],check=True)
    archive.unlink()
    if not binary.exists():raise SetupError('Ollama binary missing after extraction.')
    (destination/'.installed').write_text('Official archive extracted successfully.\n')
    return str(binary)

def wait_ready(check,child,seconds=60):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if child is not None and child.poll() is not None:raise SetupError('A local service exited; check the private log directory.')
        try:return check()
        except (OSError,ValueError):time.sleep(0.5)
    raise SetupError('Local service did not become ready in time; inspect its log.')

def port_in_use(port):
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(('127.0.0.1',port))==0

def pull_model(model):
    print('Pulling local model '+model+' (first download can take several minutes)…',flush=True)
    request=urllib.request.Request('http://127.0.0.1:11434/api/pull',data=json.dumps({'model':model,'stream':True}).encode(),headers={'Content-Type':'application/json'})
    previous=None
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=1800) as response:
        for line in response:
            event=json.loads(line)
            if event.get('error'):raise SetupError('Ollama could not pull the selected model; see its local log.')
            status=event.get('status','Downloading')
            if event.get('total'):status+=f" {100*event.get('completed',0)//event['total']}%"
            if status!=previous:print(status,flush=True);previous=status

def parse_tunnel_url(text):
    match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com\b',text)
    return match.group(0) if match else None

def render_configuration(url,token):
    if not re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com',url):raise SetupError('Unexpected HTTPS tunnel URL.')
    return f'AI_PROVIDER=bridge\nOPENAI_BASE_URL={url}/v1\nOPENAI_API_KEY={token}\n'

def compatible_reply(data):
    if not isinstance(data,dict):return False
    choices=data.get('choices');usage=data.get('usage')
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):return False
    message=choices[0].get('message',{})
    if not isinstance(message,dict) or not isinstance(message.get('content'),str) or not message['content'].strip():return False
    return isinstance(usage,dict) and all(type(usage.get(key)) is int and usage[key]>=0 for key in ('prompt_tokens','completion_tokens'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=MODELS,default=MODELS[0])
    parser.add_argument('--doctor',action='store_true',help='Read-only machine checks; installs or starts nothing')
    parser.add_argument('--no-tunnel',action='store_true',help='Start a local bridge only; use your own HTTPS reverse proxy')
    args=parser.parse_args()
    if platform.system()!='Linux':raise SetupError('Run this command on the Linux machine that will host Ollama.')
    if sys.version_info<(3,10):raise SetupError('Python 3.10 or later is required; Python 3.12 is recommended.')
    arch=architecture();state=state_directory()
    parent=state
    while not parent.exists():parent=parent.parent
    free=shutil.disk_usage(parent).free
    if args.doctor:
        print(json.dumps({'linux_architecture':arch,'free_gib':round(free/GIB,2),'recommended_free_gib':6,'ollama_installed':bool(shutil.which('ollama')),'cloudflared_installed':bool(shutil.which('cloudflared')),'private_state_directory':str(state),'root_required':False},indent=2));return
    if os.getuid()==0:raise SetupError('Run as your normal Linux user, not root or sudo.')
    if free<6*GIB:raise SetupError('Allow at least 6 GiB free disk space for Ollama, downloads, and model weights. No downloads were started.')
    if port_in_use(11435):raise SetupError('Port 11435 is already in use. Stop the previous bridge before restarting setup.')
    if state.is_symlink():raise SetupError('Private state directory must not be a symbolic link.')
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    if state.stat().st_uid!=os.getuid():raise SetupError('Private state directory must be owned by your Linux user.')
    state.chmod(0o700)
    token=ensure_token(state/'bridge.token')
    python=state/'venv/bin/python'
    if not python.exists():subprocess.run([sys.executable,'-m','venv',str(state/'venv')],check=True)
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'backend/requirements.txt')],check=True)
    children=[];logs=[]
    def start(command,name,env=None):
        file=open(state/(name+'.log'),'a');logs.append(file)
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=file,stderr=subprocess.STDOUT);children.append(child);return child
    def interrupt(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupt)
    try:
        try:local_json(11434,'/api/version');ollama=None
        except OSError:
            binary=install_ollama(state,arch)
            ollama=start([binary,'serve'],'ollama',{**os.environ,'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_MODELS':str(state/'models'),'OLLAMA_DEBUG':'0'})
            wait_ready(lambda:local_json(11434,'/api/version'),ollama)
        pull_model(args.model)
        gateway=start([str(python),'-m','uvicorn','scripts.ollama_gateway:app','--host','127.0.0.1','--port','11435','--workers','1'],'gateway',{**os.environ,'MEADOW_BRIDGE_TOKEN':token})
        wait_ready(lambda:local_json(11435,'/v1/models',token=token),gateway)
        answer=local_json(11435,'/v1/chat/completions',{'model':args.model,'messages':[{'role':'user','content':'Reply briefly: Agent Meadow is ready.'}],'max_tokens':32,'temperature':0},token,180)
        if not compatible_reply(answer):raise SetupError('Local inference did not return a compatible response and token usage.')
        print('Local Ollama inference verified. No paid model API was used.',flush=True)
        if not args.no_tunnel:
            cloudflared=shutil.which('cloudflared') or str(state/'cloudflared')
            if not Path(cloudflared).exists():release_asset('cloudflare/cloudflared','cloudflared-linux-'+arch,Path(cloudflared));Path(cloudflared).chmod(0o700)
            tunnel_log=state/'tunnel.log'
            # Start a fresh tunnel log so a previous run's URL cannot be reused.
            private_file(tunnel_log,'')
            tunnel=start([cloudflared,'tunnel','--url','http://127.0.0.1:11435'],'tunnel')
            deadline=time.monotonic()+90;url=None
            while time.monotonic()<deadline and tunnel.poll() is None:
                url=parse_tunnel_url(tunnel_log.read_text())
                if url:break
                time.sleep(0.5)
            if not url:raise SetupError('HTTPS tunnel did not start; inspect tunnel.log. Quick Tunnels can be unavailable or restricted.')
            config=state/'render-environment.txt';private_file(config,render_configuration(url,token))
            print('HTTPS bridge URL: '+url+'/v1',flush=True)
            print('Copy the three settings from '+str(config)+' into your Render service Environment page, then deploy.',flush=True)
            print('That file contains a private token. Do not paste it in chat or commit it.',flush=True)
        else:print('Local bridge is listening on 127.0.0.1:11435. Add your own HTTPS reverse proxy before connecting Render.',flush=True)
        print('Selected agent model: '+args.model,flush=True)
        print('Keep this terminal and Linux machine running. Ctrl+C stops only services started by this command.',flush=True)
        while True:
            if any(child.poll() is not None for child in children):raise SetupError('A managed service stopped; check the private log directory.')
            time.sleep(1)
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        for file in logs:file.close()

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nAgent Meadow local services stopped.')
    except SetupError as error:
        print('Setup: '+str(error),file=sys.stderr);sys.exit(1)
    except (subprocess.SubprocessError,OSError,ValueError):
        # Avoid echoing arbitrary exception text that might include private data.
        print('Setup could not complete. Check prerequisites and the private log directory; no tokens were printed.',file=sys.stderr)
        sys.exit(1)
