# TradingView Autonomous Manager — Agent Notes

Read this first before editing code, docs, or configuration.

## What this repo does

Autonomous TradingView Desktop control and Pine Script strategy management that forwards signals to Sapphire for paper or live execution. Built for Raspberry Pi deployment with a FastAPI backend.

## Key directories and files

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI app entrypoint |
| `backend/app/core/` | TradingView Desktop controller + config loader |
| `backend/app/strategies/` | Strategy manager |
| `backend/app/watchlist/` | Watchlist manager |
| `backend/app/services/` | Community script tester |
| `backend/app/integrations/` | Sapphire bridge |
| `config/settings.yaml` | Runtime configuration |
| `deploy_to_pi.py` | Pi mesh deployment script |
| `pine_scripts/` | Pine Script strategies |
| `webhook_server.py` | Standalone webhook receiver |

## How to run the dev server

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8081
```

## Tests

There is no formal test suite yet. Validate by running:

```bash
python test_api.py
python test_system.py
```

## Safety boundaries

- **Never** hardcode webhook secrets or API keys in source.
- **Never** deploy to live Pi nodes without explicit confirmation.
- **Never** delete `config/settings.yaml` or `pine_scripts/` without backup.
- Do not change the Sapphire bridge signal format without coordinating with `~/Code/Sapphire`.

---

# AGENTS.md — Operating Charter

> Guiding principles for any AI agent (or human) working in this repo. Derived from the Andrej Karpathy engineering philosophy. Tool-neutral: applies whether you drive this repo with Claude Code, goose, or by hand.

## The four rules
1. **Simplicity first.** Write the minimum code that solves the task. No speculative abstractions, no unrequested features, no single-use platforms. Extract a shared module only when there are >= 2 real call-sites today.
2. **Surgical changes, one concern per PR.** Touch only what the task requires. Do not opportunistically reformat, bump unrelated deps, or fix adjacent dead code. Small, reviewable, independently revertable diffs.
3. **Evals are the spec.** Define and run the repo verification (tests, build, typecheck, smoke) BEFORE and AFTER a change. Nothing merges unless it stays green. Keep the generate->verify loop tight and reversible.
4. **Delete > add; fewer dependencies.** Removing code, repos, and dependencies is the highest-leverage move. Every dependency is attack surface you own. Pin and lock what remains. Humans stay in the loop for irreversible / outward-facing / production steps (deletes, credential rotation, infra teardown, deploys).

## Safety
- Never use `git add .` or `git add -A` — stage changed files by explicit path (avoids sweeping in WIP or secrets).
- Never commit secrets; `.env*` stays gitignored (except `.env.example`).
- Treat anything outward-facing or irreversible as draft-then-confirm.
