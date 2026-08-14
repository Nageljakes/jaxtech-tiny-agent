# Jaxtech Tiny — Agentic Hackathon

Google-stack rebuild of Tiny, Jaxtech's autonomous scoping agent, for the **All Things Agentic Hackathon** Taskmaster track.

> Current state: Phase 1 production stack proof complete. Phase 2 autonomous scoping pipeline is next.

## Phase 1 stack

- Google Agent Development Kit (`google-adk`)
- Gemini `gemini-3.5-flash-lite`
- FastAPI HTTP adapter
- Cloud Run in `us-central1` (scale-to-zero, maximum one instance)
- Vertex AI global endpoint (Gemini 3.5 was not available to this project through the regional endpoint)
- [GitHub Pages presentation layer](https://nageljakes.github.io/Jaxtechweb/)

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

The live agent endpoint is `POST /api/agent/prove`. It uses the Cloud Run service identity; no API key is stored in the repository or service environment.

## Privacy and safety

- Tests and demos use synthetic data only.
- Never commit entrant or dealership/customer data.
- Never commit API keys or cloud credentials.
- Later risk-agent vetoes are binding; unsafe or unlawful automation stops.

## Deployment status

**Live service:** <https://jaxtech-tiny-phase1-360338025767.us-central1.run.app>

**Health check:** <https://jaxtech-tiny-phase1-360338025767.us-central1.run.app/health>

The deployed container is configured with:

- Runtime identity: dedicated service account with `roles/aiplatform.user`
- `GOOGLE_CLOUD_PROJECT=jaxtech-tiny-agentic`
- `GOOGLE_CLOUD_LOCATION=global`
- `GOOGLE_GENAI_USE_ENTERPRISE=true`
- 1 vCPU, 512 MiB, concurrency 10, 60-second timeout
- Minimum instances 0; maximum instances 1
- USD 10 monthly project-scoped budget with 50%, 90%, 100%, and forecast alerts

Production verification:

```bash
curl -fsS https://jaxtech-tiny-phase1-360338025767.us-central1.run.app/health

curl -fsS -X POST \
  https://jaxtech-tiny-phase1-360338025767.us-central1.run.app/api/agent/prove \
  -H 'Content-Type: application/json' \
  --data '{"message":"Synthetic verification: prove the Google stack."}'
```

The GitHub Pages frontend exposes a user-triggered **Prove Google stack** control. It does not call Gemini on ordinary page loads.
