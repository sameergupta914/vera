# Project Memory

Last updated: 2026-05-04

## 2026-05-04 Status Refresh

Current completion status review:

- the implementation and validation log through the two 2026-04-29 improvement passes is still accurate
- the project is close to submission-ready, but not fully ready for final submission
- the main blocking item remains unchanged:
  - the canonical evaluator pair list is still not present in the repo
  - final official `submission.jsonl` therefore cannot yet be generated

Repo-state corrections confirmed:

- `app_main.py` is the practical ASGI entrypoint for local runs
- `README.md` previously pointed to `uvicorn bot:app`, which was stale because of the `bot/` package name collision
- documentation has now been aligned to the `app_main.py` runtime path

Submission-readiness assessment as of 2026-05-04:

- ready for local testing and provisional seed-based artifact generation
- not yet ready for final challenge submission because the exact evaluator pair file is missing

Next required step for final submission:

- obtain the evaluator-provided pair list and run `generate_submission.py --pairs ...`

## Full Detailed Implementation Log

This section captures the actual step-by-step implementation and debugging path followed in this session.

### Step 1. Read Project Context And Prior Work

Actions taken:

- read `challenge-brief.md`
- read `claudechat.md`
- inspected current workspace contents

Reasoning:

- needed to separate the original challenge requirements from the previous incomplete implementation direction
- needed to determine whether the existing code was a usable base or a distraction

What was learned:

- the brief expects a relatively small submission surface: `compose()`, submission artifacts, optional multi-turn support
- previous Claude work had moved into a broader service architecture with multiple packages and a planned deployment/testing stack
- only a small portion of that prior scaffold was actually implemented

Decision:

- do not continue the large architecture as the primary path
- pivot to the actual submission-oriented deliverables first

### Step 2. Review Existing Context Layer

Files reviewed:

- `context/models.py`
- `context/store.py`
- sample dataset files from categories, merchants, triggers, and customers

Evaluation:

- `context/models.py`:
  - broad and dataset-compatible
  - not harmful, but too heavy relative to the minimum challenge needs
  - not the fastest way to deliver a working submission
- `context/store.py`:
  - useful and reusable
  - clean thread-safe in-memory versioned storage
  - maps directly onto judge `/v1/context` semantics

Decision:

- keep `context/store.py` as infrastructure support
- do not build the submission core around the Pydantic model layer

### Step 3. Inspect Dataset Shape Before Coding

Actions taken:

- opened one full category file
- opened seed merchant, trigger, and customer data
- checked actual field names and the kinds of trigger payloads present

Reasoning:

- the rule-based composer needed to be grounded in the real dataset fields, not just the challenge brief’s abstract schema

What this enabled:

- correct handling of real trigger names such as:
  - `research_digest`
  - `review_theme_emerged`
  - `active_planning_intent`
  - `supply_alert`
  - `chronic_refill_due`
- better mapping from real merchant/customer fields into composed copy

### Step 4. Choose Implementation Strategy

Options considered implicitly:

- continue service-oriented architecture first
- write an LLM-backed composer first
- write a deterministic rule-based submission composer first

Chosen path:

- deterministic rule-based composer first

Reasoning:

- the challenge requires deterministic output for the same inputs
- the repo did not yet have a stable minimal execution path
- rule-based composition is faster to validate, easier to debug, and enough to establish a working baseline
- HTTP harness support can wrap the deterministic core later

### Step 5. Build The Core Composer

Created:

- `submission_core.py`

What was implemented:

- a pure-Python `compose(category, merchant, trigger, customer)` function
- helper utilities for:
  - clipping to `<= 320` chars
  - formatting percentages and deltas
  - resolving active offers
  - resolving digest items
  - merchant naming
  - CTA selection
  - rationale generation

Trigger families added:

- merchant-facing:
  - `research_digest`
  - `regulation_change`
  - `perf_dip`
  - `renewal_due`
  - `festival_upcoming`
  - `curious_ask_due`
  - `winback_eligible`
  - `ipl_match_today`
  - `review_theme_emerged`
  - `milestone_reached`
  - `active_planning_intent`
  - `seasonal_perf_dip`
  - `supply_alert`
  - `category_seasonal`
  - `gbp_unverified`
  - `competitor_opened`
  - `dormant_with_vera`
  - `perf_spike`
  - `cde_opportunity`
- customer-facing:
  - `recall_due`
  - `wedding_package_followup`
  - `customer_lapsed_hard`
  - `trial_followup`
  - `chronic_refill_due`

Design choice:

- each trigger family got a dedicated composition function instead of a single generic template

Expected advantage:

- better trigger relevance and better category fit than a one-template approach

### Step 6. Add Submission Generator

Created:

- `generate_submission.py`

Purpose:

- generate `submission.jsonl` from the available dataset
- support either:
  - all seed triggers, or
  - a future canonical test-pair file

Reasoning:

- the real submission format in the brief is artifact-based
- this keeps the output path aligned with what the challenge expects

### Step 7. Add Judge-Compatible HTTP Wrapper

Created initially:

- top-level `bot.py`

Implemented:

- `/v1/healthz`
- `/v1/metadata`
- `/v1/context`
- `/v1/tick`
- `/v1/reply`

Supporting behavior:

- in-memory context loading via `ContextStore`
- suppression tracking
- outbound conversation bookkeeping
- reply routing for:
  - auto-replies
  - explicit action intent
  - opt-out/hostile messages
  - simple deferral language

Reasoning:

- needed a live local bot endpoint for the judge simulator

### Step 8. Add Documentation

Created:

- `README.md`

Contents added:

- what the repo now optimizes for
- how to run the bot
- how to generate submission artifacts
- how the new path differs from the earlier scaffold

### Step 9. First Validation Attempt Failed On Python Availability

Problem:

- `python` was not on PATH in the local shell

Discovery:

- `py.exe` existed and could target installed Python versions

Adjustment:

- switched all validation commands to the `py` launcher

### Step 10. Second Validation Attempt Failed Under Sandbox / Interpreter Path

Problem:

- the sandboxed environment blocked direct use of the installed interpreter in the initial validation path

Adjustment:

- requested elevated execution where needed for Python-based validation commands

Reasoning:

- the code needed real execution checks, not just static inspection

### Step 11. FastAPI Dependency Block Led To A Design Split

Problem:

- runtime checks against the HTTP layer were blocked because `fastapi` was not yet installed

Response:

- separated the pure composition engine from the HTTP wrapper

Concrete outcome:

- moved the reusable deterministic composition logic into `submission_core.py`
- made the HTTP layer depend on the core instead of mixing both concerns together

Benefit:

- core submission behavior became testable even without the web stack

### Step 12. Clean Up Portability And Encoding Issues In The New Code

Problems found:

- some non-ASCII characters had slipped into new strings
- one import issue remained in the wrapper path

Fixes:

- normalized the new code toward ASCII where possible
- corrected missing imports

Reasoning:

- improves portability and avoids console-related surprises on Windows

### Step 13. Validate The Pure Composer And Submission Generator

Commands and outcomes:

- pure composer checks executed successfully
- `py -m py_compile` checks were later used to confirm syntax on all key modules
- generator output shape was validated

Observed sample outputs:

- merchant research-digest sample: 250 chars
- customer recall sample: 178 chars

Note:

- one console print failed when printing the rupee symbol under the Windows console encoding, but the actual composition data itself was valid

### Step 14. Install Dependencies For Real Runtime Testing

Initial attempt:

- install with Python `3.14`

Failure:

- `pydantic-core` had no convenient prebuilt path in this environment and fell back to native build
- native build failed because MSVC `link.exe` was unavailable

Follow-up investigation:

- checked installed Python versions using `py -0p`

Discovery:

- Python `3.11` was available locally

Fix:

- installed dependencies with Python `3.11`

Result:

- install succeeded

### Step 15. First Server Boot Failed Due To Import Collision

Attempt:

- ran `uvicorn bot:app`

Failure:

- startup log reported:
  - `Attribute "app" not found in module "bot"`

Root cause:

- the repo already contained a `bot/` package from the earlier scaffold
- `uvicorn` imported that package instead of the top-level `bot.py`

Fix:

- created `app_main.py` as the clean ASGI entrypoint

### Step 16. Move To Stable ASGI Entry Point

Created:

- `app_main.py`

What it contains:

- the working FastAPI app
- dataset preloading for local testing
- same reply-handling logic as the wrapper path

Result:

- local server booted successfully with:
  - `py -3.11 -m uvicorn app_main:app --host 127.0.0.1 --port 8080`

### Step 17. Run Live Health And Replay Checks

Verified:

- `/v1/healthz` returned success
- `/v1/metadata` returned success

Ran simulator-derived local scenarios:

- warmup
- auto reply
- intent transition
- hostile handling

Outcome:

- warmup passed
- intent transition passed
- hostile handling passed
- auto-reply exposed a real bug

### Step 18. Debug And Fix Auto-Reply Logic

Original behavior:

- auto-reply count was tracked only inside one conversation state

Why that failed:

- the simulator replay scenario reused the same merchant across fresh conversation IDs
- repeated canned replies were not being recognized as a cross-conversation pattern

Fix implemented:

- track normalized repeated auto-reply messages by merchant across conversations
- retain per-conversation handling as well

Files updated:

- `app_main.py`
- `bot.py`

Result:

- reran replay checks
- auto-reply scenario then passed

### Step 19. Run Full Local Judge With OpenAI

User later supplied an OpenAI key and requested a real run.

Initial handling:

- ran the local judge against the live bot using the key via process environment without writing it into code

Result:

- scenario suite `all` passed:
  - warmup
  - auto_reply
  - intent
  - hostile

### Step 20. Move Simulator Config To `.env`

User then requested:

- do not hardcode the API key
- fetch it through an env file

Changes made:

- updated `judge_simulator.py` to use `python-dotenv`
- load:
  - `OPENAI_API_KEY`
  - `LLM_PROVIDER`
  - `LLM_MODEL`
  - `BOT_URL`
  - `OLLAMA_URL`
  - `TEST_SCENARIO`
- added `.env.example`
- added `.gitignore`
- added local `.env`

Validation:

- confirmed that the simulator successfully loads config from `.env`

### Step 21. Run Full Evaluation For Real Scoring

First attempt:

- ran `full_evaluation`

Failure:

- simulator crashed while printing Unicode score bars in the default Windows console encoding

Cause:

- output encoding problem, not a bot/runtime logic problem

Fix:

- reran with `PYTHONUTF8=1`

### Step 22. Final Full Evaluation Result

Successful full evaluation outcome:

- average score: `38/50`
- rating: `GOOD`
- messages scored: `20`

Per-dimension averages:

- specificity: `7/10`
- category fit: `8/10`
- merchant fit: `8/10`
- trigger relevance: `8/10`
- engagement: `7/10`

Best observed families:

- pharmacy alert and refill messaging
- several operational restaurant/gym/salon nudges

Weakest observed families:

- dormant re-engagement
- festival messaging
- curious ask prompts
- planning prompts

Important runtime observation:

- one early full-evaluation batch returned `0 actions`
- this suggests current suppression/selection behavior may be too conservative for some scenarios

### Step 23. Create Persistent Project Memory

Created:

- `PROJECT_MEMORY.md`

Reason:

- user requested a running memory of all updates and context

Policy established:

- this file will be updated as future work continues
- it serves as the in-repo running state log

## Project Goal

Build a magicpin Vera-like merchant/customer WhatsApp assistant for the `magicpin AI Challenge`.

Primary challenge deliverables:

- `bot.py` with deterministic `compose(category, merchant, trigger, customer)` behavior
- judge-compatible HTTP endpoints for local evaluation
- `submission.jsonl`
- short `README.md`

Key product constraints from the brief:

- message body must be `<= 320` chars
- no URLs
- strong specificity
- category-correct tone
- merchant personalization
- clear trigger relevance
- good engagement compulsion
- strong auto-reply detection
- immediate action-mode transition when merchant shows commitment

## Source Context Read

Read and summarized:

- `challenge-brief.md`
- `claudechat.md`

Key conclusion from those files:

- previous work by Claude was mostly architecture planning plus early scaffold creation
- that work drifted toward a larger FastAPI service architecture
- the actual brief expects a smaller submission-oriented path first

## What Existed Before This Session

Existing repo state when reviewed:

- `requirements.txt`
- `context/models.py`
- `context/store.py`
- package directories: `bot/`, `composer/`, `conversation/`, `trigger/`, `tests/`
- challenge docs and dataset

Assessment:

- `context/models.py` is broad enough for dataset parsing, but overbuilt for the minimal challenge deliverable
- `context/store.py` is reusable and aligns well with context versioning for `/v1/context`
- the old package scaffold was incomplete and not the fastest route to a working submission

## Changes Made In This Session

### Submission / Composition Path

Added:

- `submission_core.py`
- `generate_submission.py`
- `README.md`

Purpose:

- `submission_core.py` contains the deterministic rule-based `compose()` implementation
- `generate_submission.py` creates `submission.jsonl` from the dataset or from canonical test pairs once available
- `README.md` now reflects the real challenge deliverables and usage

### HTTP / Judge Path

Added:

- `app_main.py`

Updated:

- `bot.py`

Purpose:

- `app_main.py` is the clean ASGI entrypoint for the local bot server
- this avoids the namespace collision caused by the existing `bot/` package when trying to run `uvicorn bot:app`
- `bot.py` still contains a judge-compatible wrapper path and mirrors the core reply logic

### Environment / Secret Handling

Added:

- `.env`
- `.env.example`
- `.gitignore`

Updated:

- `judge_simulator.py`

Purpose:

- simulator config now loads from `.env`
- `OPENAI_API_KEY` is no longer intended to be hardcoded into the simulator file
- `.gitignore` ignores `.env`, `.env.local`, and log files

## Implemented Behavior

### Composition Coverage

Implemented rule-based message handling for trigger families including:

- `research_digest`
- `regulation_change`
- `perf_dip`
- `renewal_due`
- `festival_upcoming`
- `curious_ask_due`
- `winback_eligible`
- `ipl_match_today`
- `review_theme_emerged`
- `milestone_reached`
- `active_planning_intent`
- `seasonal_perf_dip`
- `supply_alert`
- `category_seasonal`
- `gbp_unverified`
- `competitor_opened`
- `dormant_with_vera`
- `perf_spike`
- `cde_opportunity`

Customer-facing flows implemented for:

- `recall_due`
- `wedding_package_followup`
- `customer_lapsed_hard`
- `trial_followup`
- `chronic_refill_due`

### Reply Handling

Implemented replay-relevant behavior:

- repeated auto-reply detection
- hostile / opt-out detection with end action
- intent transition into action mode
- simple wait behavior for “later” / “tomorrow”

## Bugs Found And Fixed

### 1. Python Environment Issue

Issue:

- dependency install failed under Python `3.14`
- `pydantic-core` attempted a source build and failed because MSVC `link.exe` was unavailable

Fix:

- switched project runtime/install to local Python `3.11`

### 2. ASGI Import Collision

Issue:

- `uvicorn bot:app` imported the old `bot/` package instead of the top-level `bot.py`

Fix:

- added `app_main.py`
- started server via `uvicorn app_main:app`

### 3. Auto-Reply Replay Bug

Issue:

- auto-reply detection originally counted repeats only within one conversation
- simulator replay reused the same merchant across fresh conversation IDs

Fix:

- track repeated canned auto-replies by merchant across conversations

### 4. Simulator Console Encoding Issue

Issue:

- full evaluation initially crashed when printing Unicode score bars in a Windows cp1252 console

Fix:

- reran with `PYTHONUTF8=1`

## Validation Completed

### Syntax / Static Checks

Passed:

- `py -3.11 -m py_compile bot.py`
- `py -3.11 -m py_compile app_main.py`
- `py -3.11 -m py_compile submission_core.py`
- `py -3.11 -m py_compile generate_submission.py`
- `py -3.11 -m py_compile context\store.py`

### Runtime Checks

Verified:

- local bot server starts successfully via `uvicorn app_main:app --host 127.0.0.1 --port 8080`
- `/v1/healthz` responds
- `/v1/metadata` responds

### Simulator Results

Basic / replay scenarios:

- warmup: passed
- auto_reply: passed
- intent_transition: passed
- hostile: passed

Full evaluation:

- average score: `38/50`
- rating: `GOOD`
- messages scored: `20`

Average dimension scores:

- specificity: `7/10`
- category fit: `8/10`
- merchant fit: `8/10`
- trigger relevance: `8/10`
- engagement: `7/10`

Observed score pattern:

- strongest families: pharmacy alerts/refills/seasonal prompts, several operational nudges
- weakest families: dormant re-engagement, festival prompts, curious asks, planning prompts

## Current Known Limitations

- the current composer is solid but still somewhat generic on engagement compulsion in weaker trigger families
- some trigger batches in full evaluation returned `0 actions`, which may reduce opportunity in stricter evaluations
- the real evaluator-provided 30-pair list is still not present, so final `submission.jsonl` for official submission is not yet generated against that canonical set
- `.env` now exists locally for simulator execution, but the API key that was exposed in chat should still be rotated

## How To Run Now

### Start Bot

```bash
py -3.11 -m uvicorn app_main:app --host 127.0.0.1 --port 8080
```

### Run Simulator

Configured via `.env`, then run:

```bash
py -3.11 judge_simulator.py
```

### Run Full Evaluation Explicitly

```bash
$env:TEST_SCENARIO='full_evaluation'
$env:PYTHONUTF8='1'
py -3.11 judge_simulator.py
```

## Next Best Improvement Areas

Highest-value areas to improve score from current `38/50`:

1. `dormant_with_vera`
2. `festival_upcoming`
3. `curious_ask_due`
4. `active_planning_intent`
5. `cde_opportunity`

Goal for next pass:

- increase specificity and engagement compulsion
- preserve current reliability on replay behaviors

## Latest Improvement Focus

Based on the current full-evaluation average of `38/50`, the next improvement pass should prioritize:

1. raise specificity in weaker trigger families by grounding copy in more payload facts, dates, counts, and merchant-state details
2. raise engagement compulsion by replacing generic “Want the draft?” endings with stronger curiosity, loss-aversion, or effort-externalization hooks
3. improve trigger families currently scoring lowest:
   - `dormant_with_vera`
   - `festival_upcoming`
   - `curious_ask_due`
   - `active_planning_intent`
   - `cde_opportunity`
4. review why one full-evaluation batch returned `0 actions` and reduce over-conservative suppression behavior
5. keep current strengths unchanged:
   - auto-reply handling
   - intent transition
   - hostile handling
   - pharmacy alert / refill quality

## Latest Change Log

### 2026-04-29 - Improvement Pass 1: Specificity Upgrade For Weak Trigger Families

Goal:

- address the first major scoring issue: low specificity in weaker trigger families

Files changed:

- `submission_core.py`

What was improved:

- `festival_upcoming`
  - now includes city and `days_until`
  - uses the merchant's active offer directly when available
  - CTA tightened to a direct "Reply YES"
- `curious_ask_due`
  - now references merchant locality
  - now anchors the ask against the merchant's active offer when possible
  - makes the response burden lower and the output clearer
- `active_planning_intent`
  - now references the merchant's last message
  - now promises an exact draft instead of vague planning help
- `dormant_with_vera`
  - now references days since last reply
  - now references last topic
  - now surfaces one concrete current hook such as stale posts or no active offers
- `cde_opportunity`
  - now includes the event date explicitly when available
  - keeps the credit/source grounding in the body

Validation run after this pass:

- syntax checks passed
- local bot server restarted successfully
- full evaluation rerun completed successfully

Observed evaluation impact:

- full evaluation now scored `25` messages instead of `20`
- Batch 1 no longer returned `0 actions`
- several improved messages moved into the `41-42/50` range
- some earlier weak families improved:
  - `festival_upcoming`: `41/50`
  - `curious_ask_due`: `39/50`
  - `active_planning_intent` example improved to `41/50`
  - `dormant_with_vera`: `39/50`
- however the rounded overall average remained `38/50`

Interpretation:

- specificity improvements helped locally and reduced skipped-action behavior
- the overall average did not move because engagement compulsion remains the next main bottleneck

Next issue to fix:

- strengthen engagement compulsion and CTA design, especially for:
  - `cde_opportunity`
  - `milestone_reached`
  - remaining planning-style prompts

### 2026-04-29 - Improvement Pass 2: Engagement Compulsion And CTA Upgrade

Goal:

- address the second major scoring issue: weak engagement compulsion caused by repetitive low-energy endings like "Want the draft?"

Files changed:

- `submission_core.py`

What was improved:

- rewrote many soft CTA endings into more concrete reply-driven actions
- replaced generic asks with stronger effort-externalization language such as:
  - "Reply YES and I'll send..."
  - "I already have..."
  - "I'll send the exact line..."
- touched CTA style across multiple merchant-facing families, including:
  - `research_digest`
  - `regulation_change`
  - `perf_dip`
  - `renewal_due`
  - `winback_eligible`
  - `ipl_match_today`
  - `review_theme_emerged`
  - `milestone_reached`
  - `seasonal_perf_dip`
  - `supply_alert`
  - `category_seasonal`
  - `gbp_unverified`
  - `competitor_opened`
  - `dormant_with_vera`
  - `perf_spike`
  - `cde_opportunity`
  - `default` merchant fallback

Validation run after this pass:

- syntax checks passed
- local bot server restarted successfully
- full evaluation rerun completed successfully

Observed evaluation impact:

- full evaluation average increased from `38/50` to `39/50`
- full evaluation still scored `25` messages
- category fit average improved to `9/10`
- some messages improved materially:
  - `regulation_change`: `46/50`
  - `festival_upcoming`: held at strong `41/50`
  - `milestone_reached`: improved to `41/50`
  - `cde_opportunity`: improved slightly to `39/50`
- several pharmacy/operational messages remained strong at `41-46/50`

Interpretation:

- stronger CTA language produced a measurable improvement
- however, the gain is modest because several messages still need more nuanced compulsion, not just firmer phrasing

What still looks weak:

- some curiosity-style prompts still underperform
- some planning-style prompts still feel templated
- dormant messaging is still uneven and can regress depending on wording
- engagement is no longer blocked by generic "Want the draft?" phrasing alone; it now needs better trigger-specific persuasion design

Suggested next issue:

- redesign low-performing families using explicit compulsion patterns per trigger:
  - curiosity
  - loss aversion
  - effort externalization
  - social proof where grounded

## Memory Policy For This Repo

This file is the working memory for the project.

Going forward:

- after each meaningful user/assistant exchange, update this file with new context, changes, validation results, blockers, and decisions
- treat this file as the authoritative running log inside the repo
