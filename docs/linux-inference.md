# Free Linux inference for Agent Meadow

Render hosts the PWA/API; your Linux machine runs Ollama. No paid model API is needed. The Linux machine must stay on and connected. The `scripts/ollama_gateway.py` bridge requires a long random bearer secret, limits context/output/concurrency/requests, binds to loopback, and forwards only model-list and chat requests to local Ollama. It does not expose your filesystem or an arbitrary proxy target.

## Guided setup (recommended for a free pilot)

Run this **on your own Linux computer/server**, not inside the Render web service. Use a normal Linux user, Python 3.10+ (3.12 recommended), at least 6 GiB free disk space, and preferably 8 GB RAM. A GPU is optional. On Ubuntu/Debian, install prerequisites if needed:

```sh
sudo apt-get update
sudo apt-get install -y git python3 python3-venv tar zstd
```

Then:

```sh
git clone https://github.com/temcwilliams/AIAGENTSAAS.git
cd AIAGENTSAAS
python3 scripts/setup_ollama.py
```

If the repository is already cloned, update it with your normal Git workflow and run the last command from its root. No sudo is needed for the setup script itself. It will:

1. Reuse a running local Ollama service, or install the official Linux distribution under your private user data directory and start it on loopback.
2. Pull **`qwen2.5:1.5b`**, install the bridge's Python dependencies in a private virtual environment, and start the authenticated bridge.
3. Verify a real local reply **and its token usage** before reporting local inference ready.
4. Download the official Cloudflare connector, start a free temporary HTTPS tunnel, and display its public bridge URL.
5. Write a private `render-environment.txt` containing the three Render settings. The token is generated randomly, reused on restart, stored with mode 0600, and never printed. Downloads are restricted to official publisher release URLs and require matching published SHA-256 checksums.

By default, files and model weights live in `~/.local/share/agent-meadow/` (or your `XDG_DATA_HOME` equivalent). Logs are there too. The script uses no paid model API and creates no paid hosting resources. It does not upload credentials or change Render automatically.

Open the generated `render-environment.txt` **privately on your Linux machine** and copy its three settings into the [Render service Environment page](https://dashboard.render.com/web/srv-dbriv0l6e07s73bs7p7g/env). Save/deploy the settings, then use **Inference → Check connection** in Agent Meadow. Configure agents with the exact installed model name. You can share the HTTPS bridge URL here for help; do **not** paste the token or configuration file in chat.

Keep the terminal and machine running. Ctrl+C stops processes started by this run; an existing Ollama service is left running. Quick Tunnel URLs may change on restart, requiring the Render URL setting to be updated. The setup is for a pilot, not an always-on hosting guarantee. Use a supervised service and stable HTTPS endpoint for a sustained client deployment.

Useful options:

```sh
python3 scripts/setup_ollama.py --doctor
python3 scripts/setup_ollama.py --model qwen2.5:0.5b
python3 scripts/setup_ollama.py --no-tunnel
```

`--doctor` is read-only. The smaller 0.5b model reduces resource needs at the cost of answer quality. `--no-tunnel` leaves the bridge on loopback for your own HTTPS reverse proxy. Do not expose unauthenticated port 11434 publicly.

## Manual setup

1. Install Ollama using its official Linux installation instructions. Pull `qwen2.5:1.5b` (Apache 2.0 weights) using `ollama pull qwen2.5:1.5b`. Check the model license if you choose another model. CPU operation is supported; speed depends on hardware.
2. Clone your Agent Meadow repository onto the Linux machine. Create a Python virtual environment and install `backend/requirements.txt`.
3. Generate a private token in your own terminal: `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Store it securely; do not paste it in chat or commit it. Set it as `MEADOW_BRIDGE_TOKEN` in the Linux process environment.
4. Start the bridge from the project root: `.venv/bin/uvicorn scripts.ollama_gateway:app --host 127.0.0.1 --port 11435 --workers 1`. The token is intentionally not forwarded to Ollama. Use one worker for the built-in single-machine limits. A token-authenticated request to `/v1/models` should list your installed model.
5. Put an HTTPS tunnel/reverse proxy in front of **11435**, never the unauthenticated Ollama port 11434. For a free temporary pilot, a Cloudflare Quick Tunnel can forward to `http://127.0.0.1:11435` after installing the official `cloudflared` binary: `cloudflared tunnel --url http://127.0.0.1:11435`. Follow current Cloudflare limits/terms; quick-tunnel URLs can change and are not production hosting. A persistent HTTPS endpoint requires your own infrastructure/domain configuration.
6. In Render's service Environment page, set `AI_PROVIDER=bridge`, `OPENAI_BASE_URL=https://YOUR-TUNNEL-HOST/v1`, and `OPENAI_API_KEY` to the same bridge token. Keep these as server-side secrets. Deploy the changed configuration. No connection is enabled automatically; the Linux endpoint and secret must exist first.
7. Open **Inference** in Agent Meadow and choose **Check connection**, then configure an agent with `qwen2.5:1.5b` and send an approved test message. Tokens are stored from actual responses; failures never produce fake replies.

The app already has per-business request limits. The bridge also limits 60 attempts/hour across its single process, so account for all connected businesses. It has no distributed queue, multi-host load balancing, or GPU provisioning. Restarting the bridge resets its process-local limits. Keep token access limited to your deployment, rotate it if exposed, and use stable supervised services/TLS for a real client pilot. A sleeping/disconnected Linux machine makes AI unavailable; business dashboards remain available.

We cannot activate this connection from the development workspace until you run the bridge on your Linux machine and configure its endpoint and token in Render. Never use the dashboard to publish the token to frontend code.
