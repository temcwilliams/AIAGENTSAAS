"""Free setup must neither require cloud secrets nor accept remote local-mode URLs."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]


def test_secret_generator_is_private_and_preserves_existing_file(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('init_local',ROOT/'scripts/init-local.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    module.main()
    target=tmp_path/'.env'
    content=target.read_text()
    assert 'POSTGRES_PASSWORD=' in content
    password=content.split('POSTGRES_PASSWORD=')[1].splitlines()[0]
    assert len(password)==64
    assert target.stat().st_mode & 0o077==0
    with pytest.raises(SystemExit):module.main()
    assert target.read_text()==content


@pytest.mark.parametrize('endpoint,accepted',[
    ('http://127.0.0.1:11434/v1',True),
    ('http://ollama:11434/v1',True),
    ('https://paid-provider.example/v1',False),
    ('http://secret@localhost:11434/v1',False),
])
def test_local_endpoint_is_explicitly_local(endpoint,accepted):
    env={**os.environ,'AI_PROVIDER':'local','OPENAI_BASE_URL':endpoint,'OPENAI_API_KEY':''}
    result=subprocess.run([sys.executable,'-c','from app.config import settings; assert settings.ai_provider == "local"'],env=env,capture_output=True,text=True)
    assert (result.returncode==0)==accepted
