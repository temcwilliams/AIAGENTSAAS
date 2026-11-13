"""Installer tests use fake publisher responses; no binaries/models are downloaded."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import pytest

@pytest.fixture
def setup_module():
    path=Path(__file__).resolve().parents[2]/'scripts/setup_ollama.py'
    spec=importlib.util.spec_from_file_location('meadow_ollama_setup',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_token_is_private_reused_and_never_overwritten(setup_module,tmp_path):
    token_file=tmp_path/'bridge.token'
    token=setup_module.ensure_token(token_file)
    assert len(token)>=48
    assert token_file.stat().st_mode & 0o077==0
    assert setup_module.ensure_token(token_file)==token
    token_file.chmod(0o644)
    with pytest.raises(setup_module.SetupError):setup_module.ensure_token(token_file)
    assert token_file.read_text().strip()==token


def test_private_files_reject_symbolic_links(setup_module,tmp_path):
    original=tmp_path/'original';original.write_text('keep unchanged')
    link=tmp_path/'link';link.symlink_to(original)
    with pytest.raises(setup_module.SetupError):setup_module.private_file(link,'overwrite')
    with pytest.raises(setup_module.SetupError):setup_module.ensure_token(link)
    assert original.read_text()=='keep unchanged'
    safe=tmp_path/'safe';setup_module.private_file(safe,'first');setup_module.private_file(safe,'next')
    assert safe.read_text()=='next' and safe.stat().st_mode & 0o077==0


def test_render_configuration_only_accepts_https_tunnel(setup_module):
    url=setup_module.parse_tunnel_url('Tunnel ready: https://gentle-green-meadow.trycloudflare.com connection available')
    assert url=='https://gentle-green-meadow.trycloudflare.com'
    assert setup_module.parse_tunnel_url('https://trycloudflare.com') is None
    assert setup_module.render_configuration(url,'private-test-token').splitlines()==['AI_PROVIDER=bridge','OPENAI_BASE_URL='+url+'/v1','OPENAI_API_KEY=private-test-token']
    for bad in ['http://plain.trycloudflare.com','https://other.example','https://good.trycloudflare.com.evil.test','https://key@good.trycloudflare.com']:
        with pytest.raises(setup_module.SetupError):setup_module.render_configuration(bad,'private-test-token')


def test_publisher_download_verifies_digest(setup_module,tmp_path,monkeypatch):
    content=b'test-only-binary-not-executed'
    asset={'name':'cloudflared-linux-amd64','browser_download_url':'https://github.com/cloudflare/cloudflared/releases/download/test/cloudflared-linux-amd64','digest':'sha256:'+hashlib.sha256(content).hexdigest()}
    def response(request,**kwargs):
        url=request.full_url if hasattr(request,'full_url') else request
        return io.BytesIO(json.dumps({'assets':[asset]}).encode() if '/repos/' in url else content)
    monkeypatch.setattr(setup_module.urllib.request,'urlopen',response)
    target=tmp_path/'cloudflared'
    setup_module.release_asset('cloudflare/cloudflared',asset['name'],target)
    assert target.read_bytes()==content
    asset['digest']='sha256:'+'0'*64
    with pytest.raises(setup_module.SetupError):setup_module.release_asset('cloudflare/cloudflared',asset['name'],target)
    assert target.read_bytes()==content and not (tmp_path/'cloudflared.part').exists()
    asset['browser_download_url']='https://untrusted.example/binary'
    with pytest.raises(setup_module.SetupError):setup_module.release_asset('cloudflare/cloudflared',asset['name'],target)


def test_local_requests_do_not_use_environment_proxy(setup_module,monkeypatch):
    observed={}
    class Opener:
        def open(self,request,timeout):
            observed['url']=request.full_url;observed['authorization']=request.headers.get('Authorization')
            return io.BytesIO(b'{"data":[]}')
    def build(handler):
        assert handler.proxies=={}
        return Opener()
    monkeypatch.setattr(setup_module.urllib.request,'build_opener',build)
    assert setup_module.local_json(11435,'/v1/models',token='local-test-secret')=={'data':[]}
    assert observed=={'url':'http://127.0.0.1:11435/v1/models','authorization':'Bearer local-test-secret'}


def test_unsafe_archive_is_not_extracted(setup_module,tmp_path,monkeypatch):
    monkeypatch.setattr(setup_module.shutil,'which',lambda name:None if name=='ollama' else '/usr/bin/'+name)
    monkeypatch.setattr(setup_module,'release_asset',lambda repo,name,target:target.write_bytes(b'test'))
    monkeypatch.setattr(setup_module.subprocess,'check_output',lambda *args,**kwargs:'../outside-file\n')
    with pytest.raises(setup_module.SetupError):setup_module.install_ollama(tmp_path,'amd64')
    assert not (tmp_path.parent/'outside-file').exists()

def test_local_verification_requires_content_and_real_usage(setup_module):
    valid={'choices':[{'message':{'content':'Agent Meadow is ready.'}}],'usage':{'prompt_tokens':4,'completion_tokens':5}}
    assert setup_module.compatible_reply(valid)
    for invalid in [{},{'choices':[]},{**valid,'usage':{}},{**valid,'usage':{'prompt_tokens':-1,'completion_tokens':5}},{**valid,'usage':{'prompt_tokens':True,'completion_tokens':5}},{**valid,'choices':[{'message':{'content':''}}]}]:
        assert not setup_module.compatible_reply(invalid)
