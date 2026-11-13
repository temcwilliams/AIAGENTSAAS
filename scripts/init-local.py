"""Generate local database secrets without printing them or overwriting files."""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    target = ROOT / '.env'
    if target.exists():
        raise SystemExit('.env already exists; leaving existing secrets unchanged.')
    password = secrets.token_hex(32)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as file:
        file.write(f'POSTGRES_USER=agent_studio\nPOSTGRES_DB=agent_studio\nPOSTGRES_PASSWORD={password}\nAPP_ORIGIN=http://localhost:3000\n')
    print('Created .env with a random local database password. Keep this file private.')

if __name__ == '__main__':
    main()
