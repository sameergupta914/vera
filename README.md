# magicpin AI Challenge Bot

This repo is now aligned to the actual challenge deliverables first:

- `submission_core.py`: deterministic `compose()` engine
- `app_main.py`: judge-compatible FastAPI entrypoint for local runs
- `bot.py`: duplicate wrapper logic kept for compatibility/reference
- `generate_submission.py`: creates `submission.jsonl` from either the provided trigger seeds or a canonical test-pairs file
- existing `context/` package: kept as support code, not as the primary submission surface

## Approach

The bot uses trigger-specific composition rules instead of a generic one-template prompt. Each message is grounded in:

- category voice and digest items
- merchant performance, offers, and signals
- trigger payload facts
- optional customer relationship/preferences

The composer aims to preserve the challenge constraints:

- `<= 320` characters
- no URLs
- one primary CTA
- specific numbers / dates / offers where available
- customer-facing sends attributed as `merchant_on_behalf`

Reply handling is deliberately simple but targeted at the two major replay risks from the brief:

- repeated auto-reply detection with graceful exit
- explicit merchant commitment routed into action mode instead of more qualification

## Local usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the bot:

```bash
py -3.11 -m uvicorn app_main:app --host 127.0.0.1 --port 8080
```

## Deployment

This repo is now prepared for public bot hosting in either of these common ways:

- `Dockerfile`: for any platform that deploys containers
- `Procfile`: for Procfile-style web hosts

Expected web process:

```bash
uvicorn app_main:app --host 0.0.0.0 --port $PORT
```

The public base URL you submit must expose:

- `POST /v1/context`
- `POST /v1/tick`
- `POST /v1/reply`
- `GET /v1/healthz`
- `GET /v1/metadata`

Generate a submission from all seed triggers:

```bash
py -3.11 generate_submission.py
```

Generate a submission from the canonical 30-pair file once available:

```bash
py -3.11 generate_submission.py --pairs test_pairs.jsonl --output submission.jsonl
```

## Notes

The repo still contains an earlier scaffold under `context/`, `composer/`, `conversation/`, and `trigger/`. That was moving toward a larger service architecture. The challenge deliverable is narrower, so the active runtime path is `app_main.py` + `submission_core.py`.

The only missing final submission artifact is the real evaluator-provided pair list. Until that file is available, any generated `submission.jsonl` is only a seed-based practice artifact, not the canonical final deliverable.
