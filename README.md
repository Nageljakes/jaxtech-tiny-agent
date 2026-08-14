# Jaxtech Tiny — Agentic Hackathon

Google-stack rebuild of Tiny, Jaxtech's autonomous scoping agent, for the **All Things Agentic Hackathon** Taskmaster track.

> Current state: Phase 1 stack-proof scaffold. Feature implementation intentionally starts only after the production stack is proven.

## Phase 1 stack

- Google Agent Development Kit (`google-adk`)
- Gemini `gemini-3.5-flash-lite`
- FastAPI HTTP adapter
- Cloud Run target (scale-to-zero)
- GitHub Pages presentation layer

## Local verification

Prerequisites: Python 3.11 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
curl http://127.0.0.1:8080/health
```

Expected health response:

```json
{"status":"ok","framework":"google-adk","model":"gemini-3.5-flash-lite","phase":1}
```

The live agent endpoint is `POST /api/agent/prove`. It needs Google credentials at runtime; no key belongs in this repository.

## Privacy and safety

- Tests and demos use synthetic data only.
- Never commit entrant or dealership/customer data.
- Never commit API keys or cloud credentials.
- Later risk-agent vetoes are binding; unsafe or unlawful automation stops.

## Deployment status

Cloud deployment instructions and the public URL will be added only after the Phase 1 production deployment has been exercised successfully.
