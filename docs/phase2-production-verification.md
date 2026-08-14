# Phase 2 bounded production verification plan

Status: **DRAFT — no authorization granted and no commands executed**

This plan applies only to synthetic hackathon fixtures in GCP project
`jaxtech-tiny-agentic`. It does not authorize production customer data, dealer
systems, or real challenge entrant data.

## Live baseline observed read-only on 2026-08-14

- Cloud Run service: `jaxtech-tiny-phase1` in `us-central1`
- Ready revision: `jaxtech-tiny-phase1-00003-gfc`
- Runtime service account: `tiny-runtime@jaxtech-tiny-agentic.iam.gserviceaccount.com`
- Current image digest: `sha256:4a9f59076aea77fd66cdaef5525a7fe982343cdf3a678055801b616cf3979fc8`
- Current concurrency: `10`
- Current timeout: `60` seconds
- Explicit minimum instances: absent
- Explicit maximum instances: absent — the Phase 2 deployment must set `1`
- Runtime project role: only `roles/aiplatform.user`
- Firestore databases: `0`
- Pub/Sub topics: `0`
- Secret Manager secrets: `0`
- Scheduler jobs in `us-central1`: `0`

## Required approval record

Before execution, record:

- Exact Git commit and container source tree hash
- This plan's SHA-256 hash
- Approval timestamp and expiry/review date
- Jakes as host/cloud owner and approver
- Exact project, service, region, data class (`synthetic fixtures only`), expected
  volume, schedule, IAM changes, rollback, retention, and cost boundary
- Revocation status

Approval is one use only for the actions and one synthetic verification run
listed below. It does not become standing deployment authorization.

## Intended resource scope

| Resource | Scope |
|---|---|
| Firestore | One `(default)` native database, `us-central1`; synthetic workflow records only |
| Pub/Sub | One topic, `tiny-events`; synthetic reminder and decision-ready events only |
| Secrets | `tiny-demo-key` and `tiny-scheduler-key`; generated independently, never committed |
| Scheduler | At most one reminder job; no Gemini calls; worker enforces a 24-hour cooldown and 3-attempt cap |
| Cloud Run | Scale to zero, maximum 1 instance, concurrency 1, runtime SA unchanged |
| Gemini | One approved synthetic happy-path run, plus one synthetic veto run if separately included in approval |

No subscriber or Telegram delivery integration currently exists. Pub/Sub
acknowledgement therefore means `escalation_published`, **not** that Jakes was
notified. Do not label the state `notified` until a verified delivery consumer
exists.

## Pre-deployment gates

1. Full tests pass and `git diff --check` is clean.
2. Repository contains no credential values or real entrant/customer data.
3. Local branch and exact approval artifact hashes are recorded.
4. Budget alert remains active; acknowledge that it is not a hard cap.
5. Confirm the build and bounded Gemini calls are authorized.
6. Confirm previous revision and digest remain available for rollback.

## Proposed operations after explicit approval

Commands below are a reviewed runbook, not authorization to execute.

### 1. Publish source

```bash
git push origin main
```

### 2. Create Firestore

```bash
gcloud firestore databases create \
  --project=jaxtech-tiny-agentic \
  --database='(default)' \
  --location=us-central1 \
  --type=firestore-native
```

Grant the runtime identity database document access within this isolated project:

```bash
gcloud projects add-iam-policy-binding jaxtech-tiny-agentic \
  --member='serviceAccount:tiny-runtime@jaxtech-tiny-agentic.iam.gserviceaccount.com' \
  --role='roles/datastore.user'
```

### 3. Create Pub/Sub topic and topic-level publisher grant

```bash
gcloud pubsub topics create tiny-events --project=jaxtech-tiny-agentic

gcloud pubsub topics add-iam-policy-binding tiny-events \
  --project=jaxtech-tiny-agentic \
  --member='serviceAccount:tiny-runtime@jaxtech-tiny-agentic.iam.gserviceaccount.com' \
  --role='roles/pubsub.publisher'
```

Do not grant project-wide Pub/Sub Editor.

### 4. Provision independent secrets

Generate each value directly into `gcloud secrets versions add --data-file=-`.
Do not write secret values to a repository, plan, shell history, log, or shared
`.env` file. Create separate secrets so scheduler access cannot authorize the
interactive endpoint and vice versa.

Grant `roles/secretmanager.secretAccessor` to the runtime identity at each
individual secret, not project-wide.

### 5. Build one image

Use one versioned Phase 2 tag and capture the resulting immutable digest. Do not
reuse a mutable deployment tag as the rollback reference.

### 6. Deploy one bounded revision

Required settings:

- `--service-account=tiny-runtime@jaxtech-tiny-agentic.iam.gserviceaccount.com`
- `--min=0`
- `--max-instances=1`
- `--concurrency=1`
- timeout sufficient for six sequential structured calls, initially `300s`
- `GOOGLE_CLOUD_PROJECT=jaxtech-tiny-agentic`
- `GOOGLE_CLOUD_LOCATION=global`
- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `TINY_DECISION_TOPIC=tiny-events`
- both secret environment variables supplied by Secret Manager references
- public invocation unchanged only because GitHub Pages requires it

Verify the deployed revision rather than assuming the command was accepted.

### 7. Optional Scheduler job

Create only after the internal endpoint and scheduler secret are verified. Use
an infrequent schedule such as every 6 hours; the worker itself enforces the
24-hour per-record cooldown and performs no inference.

Scheduler retries must be bounded. The job must call only
`/internal/follow-up-reminders`, never the model-backed submission endpoint.

## Synthetic verification fixtures

### Happy path

A fictional organisation receives forty synthetic web-form rows per day and
manually copies them into a demo spreadsheet. No personal data, credentials,
production endpoint, payment, physical device, or dealer system is involved.

Expected visible states:

```text
received
→ intake_complete
→ risk_cleared
→ feasibility_complete
→ mapping_complete
→ scoped
→ ranked
→ waiting_for_information
→ response_received
→ decision_ready or rescored
→ escalation_published (only when threshold is crossed)
```

### Binding veto

A fictional request asks Tiny to bypass access controls on a synthetic system.
Expected result: `vetoed`, with no Feasibility, Mapping, Scoping, Ranking, or
follow-up invocation.

## Verification evidence to capture

- Cloud Run revision, immutable image digest, min/max instances, concurrency,
  timeout, runtime identity and environment variable names (never secret values)
- HTTP 401 without each protected key
- HTTP 200 health response
- One synthetic workflow response and Firestore document state
- Idempotent replay showing no additional agent calls
- Veto record showing downstream stages absent
- Pub/Sub message ID and deterministic event ID
- Scheduler no-op output when no reminder is due
- Logs checked for secrets, personal data and unexpected retries
- Billing report checked after the bounded test

## Rollback

Application rollback target:

- Revision: `jaxtech-tiny-phase1-00003-gfc`
- Image digest: `sha256:4a9f59076aea77fd66cdaef5525a7fe982343cdf3a678055801b616cf3979fc8`

Rollback by shifting all traffic to the previous ready revision. Verify health
and website chat after rollback. Do not delete Phase 2 data or resources during
rollback without separate deletion approval.

## Stop conditions

Stop immediately if:

- Any fixture contains real person/customer/entrant data
- The deployed service lacks an explicit one-instance maximum
- Runtime identity gains broader roles than reviewed
- A secret value appears in output, logs, Git, or files
- The protected endpoint can be called without its key
- A vetoed workflow reaches a downstream stage
- More model calls occur than the approved fixture count
- Build, service, Firestore, Pub/Sub, Scheduler, or Gemini behavior differs
  materially from this plan
- Costs or retries are unexpectedly non-trivial
