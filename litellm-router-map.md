# LITELLM ROUTER — 360° COMPLETE MAP

## WHAT THIS IS

The router is the estate's LLM proxy. Every AI call from every consumer passes through it.
It is the single chokepoint for:
  - Route selection (which model handles the request)
  - Cost control (token efficiency + per-request ceilings)
  - Auth enforcement (who can call which lane)
  - Audit (every call logged with model, latency, tokens, cost)
  - Telemetry (OTel traces to the collector)

There are TWO routers:
  - Laptop router: ~/.estate/litellm-local/ (local macOS, no cluster dependency)
  - Cluster router: llm.mumchimp.com (Kubernetes, fleet-wide)

Both share the same model registry (llm/config.yaml, platform/vendors/consoles.yaml).
The laptop router runs Claude Code's traffic so the founder's Max subscription works
even when the cluster is down (founder, 2026-09-26).

---

## ENTRY POINTS

### Laptop router: http://127.0.0.1:4000

Claude Code (founder's Mac):
  ~/.claude/settings.json → ANTHROPIC_BASE_URL=http://127.0.0.1:4000
  Claude Code sends: Authorization: Bearer sk-ant-oat01-... (Max OAuth token)
  No API key in settings.json.

Voice pipeline (founder's Mac):
  Same router, different lane (voice-asr, voice-tts).
  Groq API key held by router.

Agent workforce (founder's Mac):
  Same router, different lanes (default, fast, minimax, groq, etc.).

### Cluster router: https://llm.mumchimp.com

Otto gateway pod:
  Internal cluster traffic. Uses router's master key or virtual keys.

Prospector:
  The CLI that routes LLM calls for the crew. Reads llm/config.yaml to know lane names.

Holmes:
  The investigator agent. Same routing as prospector.

Any service in the cluster that calls an LLM:
  Goes through the cluster router, not the laptop router.

### How the two routers relate

The laptop router is the founder's private circuit breaker. If the cluster router
goes down, Claude Code still works. If the laptop router goes down, Claude Code
gets "connection refused" and nothing works.

Claude Code is explicitly routed to the laptop router, not the cluster one.
The cluster router handles everything else in the fleet.

---

## THE AUTH MODEL

### Laptop router: local_caller_auth.py

Runs as a LiteLLM custom_auth callback, BEFORE every other callback.

Two checks on every request:

1. BROWSER CHECK
   Refuses: requests with Origin header OR Host != 127.0.0.1:4000
   Why: Web pages in the founder's browser could otherwise call the router and spend
        the Groq/Cerebras lanes the router holds keys for.
   Result: Only local CLIs and services can reach the router.

2. KEYED-LANE CHECK
   Keyed lanes: model rows with api_key: os.environ/... (Groq, Cerebras, MiniMax, etc.)
   These lanes spend a key the router HOLDS.
   Requires: Caller must present the laptop router key (LITELLM_LAPTOP_KEY.yaml)
   Non-keyed lanes (claude-*, ollama-*): Open to any local caller.

The claude-* lane is NON-keyed. It has no api_key. It relays the caller's own
OAuth token upstream. No laptop key needed for it.

HOST MISMATCH BUG: If something occupies port 4000, the router binds 5606.
local_caller_auth then sees Host: 127.0.0.1:5606 and refuses it. Fix: kill
the squatter, restart on 4000.

### Cluster router

Uses LITELLM_MASTER_KEY for authentication.
Virtual keys for named consumers (Otto, Holmes, etc.).

---

## MODEL LANES

Each lane is a named model (or pool) the router knows how to call.

### Claude Code lanes (relay Max OAuth token)

  claude-* (wildcard)
    model: anthropic/claude-*
    auth: NO KEY — relays client's sk-ant-oat01-... OAuth token
    timeout: 600s
    cost: $0 (Max subscription, no per-token billing)
    fallback: none
    notes:
      - Wildcard carries whatever model ID Claude Code sends (claude-opus-5-5, etc.)
      - No alias may be set for claude-* (aliases outrank model rows silently)
      - pass_through_client_api_key: true forwards x-api-key to Anthropic
      - anthropic_beta_passthrough.py keeps beta headers + request fields intact

### General-purpose lanes

  default (pool: MiniMax + Groq + Cerebras + SambaNova)
    primary: openai/MiniMax-M3 via MiniMax API
    keys held: MINIMAX_API_KEY (router)
    pool members: MiniMax, Groq, Cerebras, SambaNova (cost-based-routing)
    fallback: [gemini, groq]
    timeout: 300s
    max_input_tokens: 512000

  fast (pool: MiniMax + Groq + Cerebras + SambaNova)
    Same as default, different lane name.
    fallback: [gemini, groq]
    timeout: 300s

### Direct vendor lanes

  minimax
    model: openai/MiniMax-M3
    api_base: https://api.minimax.io/v1
    key: MINIMAX_API_KEY
    timeout: 300s
    max_input_tokens: 512000
    input_cost: $0.30/M output_cost: $1.20/M
    fallback: [gemini, groq]

  minimax_m27
    model: openai/MiniMax-M2.7
    key: MINIMAX_API_KEY
    timeout: 300s
    max_input_tokens: 204800
    fallback: [gemini, groq]

  minimax_json
    model: openai/MiniMax-M3
    key: MINIMAX_API_KEY
    Forces JSON-only output (response_format: json_schema)
    max_input_tokens: 512000

  gemini
    model: gemini/gemini-2.5-flash
    key: GEMINI_API_KEY
    timeout: 300s
    tpm: 500000 (billed per-model-per-minute)
    fallback: [minimax, groq]
    notes:
      - Demoted 2026-09-08 (unbilled account, 95% failure rate)
      - Returns to front when Google account is billed (crew#920)

  deepseek
    model: deepseek/deepseek-chat
    key: DEEPSEEK_API_KEY
    timeout: 300s
    fallback: [gemini, minimax, groq]
    notes:
      - Revoked 2026-09-04, re-funded later
      - Answers 401 when key is bad

### Free floor lanes

  groq (pool of 3 keys: GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3)
    model: openai/gpt-oss-120b
    api_base: https://api.groq.com/openai/v1
    timeout: 60s
    max_input_tokens: 131072
    notes:
      - Pool: cost-based-routing picks cheapest healthy member
      - allowed_fails: 3, cooldown: 60s (self-healing)
    fallback: [cerebras, sambanova, nvidia, openrouter]

  cerebras (pool of 3 keys)
    model: openai/gpt-oss-120b
    api_base: https://api.cerebras.ai/v1
    timeout: 60s
    max_input_tokens: 65536
    fallback: [sambanova, nvidia, openrouter]

  sambanova (pool of 3 keys)
    model: openai/gpt-oss-120b
    api_base: https://api.sambanova.ai/v1
    timeout: 60s
    max_input_tokens: 131072
    fallback: [nvidia, openrouter]

  nvidia
    model: openai/nemotron-3.5-lightning-30b-a3b
    api_base: https://integrate.api.nvidia.com/v1
    key: NVIDIA_API_KEY
    timeout: 90s
    max_input_tokens: 131072

  openrouter
    model: openai/nemotron-3.5-lightning:free
    api_base: https://openrouter.ai/api/v1
    key: OPENROUTER_API_KEY
    timeout: 90s
    max_input_tokens: 131072

### Voice lanes

  voice-asr
    model: groq/whisper-large-v3-turbo
    mode: audio_transcription
    key: GROQ_API_KEY
    timeout: 20s

  voice-tts
    model: openai/canopylabs/orpheus-v1-english
    api_base: https://api.groq.com/openai/v1
    key: GROQ_API_KEY
    mode: audio_speech
    timeout: 20s

### Local lanes

  ollama
    model: ollama/qwen2.5-coder:7b
    api_base: http://host.docker.internal:11434
    timeout: 300s
    keep_alive: 24h

  ollama-vision
    model: openai/gemma3:4b
    api_base: http://host.docker.internal:11434/v1
    key: ollama
    timeout: 300s

  ollama-llama
    model: ollama/llama3.2:latest
    api_base: http://host.docker.internal:11434
    timeout: 300s
    keep_alive: 24h

### Aliases

  model_group_alias:
    kimi: moonshot/kimi-k3
    No claude-* alias, ever (silently turns sessions into wrong model)

---

## FALLBACK CHAINS

LiteLLM walks these when the primary model fails.

  deepseek → [gemini, minimax, groq]
  minimax → [gemini, groq]
  gemini → [minimax, groq]
  default → [gemini, groq]
  fast → [gemini, groq]

  groq → [cerebras, sambanova, nvidia, openrouter]
  cerebras → [sambanova, nvidia, openrouter]
  sambanova → [nvidia, openrouter]

Key properties:
  - groq/cerebras/sambanova: pools, not single keys. allowed_fails + cooldown_time
    do self-healing across the pool without any PR.
  - Gemini goes LAST on every chain it heads. Returns to front when billed.
  - DeepSeek heads a chain but has no floor — dead key = dead chain branch.

---

## CALLBACK CHAIN

### 1. local_caller_auth.py (custom_auth, runs first)

Purpose: Auth gate for laptop router.
What it does:
  - Refuses browser requests (Origin header or wrong Host)
  - Enforces laptop router key on keyed lanes
  - Tags callers (LOCAL_SERVICE vs OWN_CREDENTIAL)
Files:
  - Laptop: ~/.estate/litellm-local/modules/local_caller_auth.py
  - Cluster: platform/llm/local_caller_auth.py (different, uses master key)

### 2. request_ceiling.py (pre-call hook)

Purpose: Size gate — refuse oversized requests before they cost money.
What it does:
  - Measures estimated input tokens (message text + tool schemas)
  - Refuses if > MAX_INPUT_TOKENS (default 128k)
  - Never throttles or truncates — hard refusal with fix instructions
Key env: ESTATE_MAX_INPUT_TOKENS (default 128000)
Why: Measured 2026-09-13, one session sent 737k tokens × 439 calls in one hour.

### 3. efficiency_gateway.py (pre-call hook)

Purpose: 8 token-optimization mechanisms.
What it does (per mechanism):

For OpenAI-shaped lanes (MiniMax, Groq, etc.):
  [1] CacheGuardian — detects system-prompt drift that kills prefix caching
  [2] TokenKiller — deduplicates identical consecutive lines in tool_result text
  [3] MCPAdapter — truncates verbose tool descriptions to MAX_TOOL_DESC_CHARS
  [4] TokenBudgetOrchestrator — tracks cumulative spend per session
  [5] SoLPi — replaces exact-repeat large tool results with pointer (≥500 chars)
  [6] DynamicContextPruning — removes duplicate tool_result entries
  [7] CompactionManager — bounds history to MAX_HISTORY_MSGS, respects tool_call invariants
  [8] GistingSimulator — condenses old assistant turns beyond GIST_AFTER_MSGS
  [9] ToolPairValidator — drops orphaned tool messages (safety net, runs LAST)

For Anthropic Messages format (claude-* lane):
  All mechanisms are APPEND-STABLE (transform depends only on the message itself).
  [1] CacheGuardian — measures prefix stability per call
  [2] TokenKiller — adjacent runs only, inside tool_result text
  [3] MCPAdapter — SKIPPED (tool schemas in cached prefix at 0.1x cost)
  [5] SoLPi — exact repeats within same request, ≥500 chars
  [7] CompactionManager — SKIPPED (Claude Code compacts its own history)
  [9] ToolPairValidator — active (reports, never drops)

Key env vars:
  ESTATE_MAX_TOOL_DESC_CHARS (default 400)
  ESTATE_MAX_HISTORY_MSGS (default 60)
  ESTATE_MAX_HISTORY_BYTES (default 200000)
  ESTATE_GIST_AFTER_MSGS (default 40)
  ESTATE_RUN_MIN_LINES (default 3)
  ESTATE_EFFICIENCY_LEDGER (default ~/.estate/efficiency-ledger.jsonl)

### 4. anthropic_beta_passthrough.py (module-level, no hook)

Purpose: Fix two LiteLLM bugs on the Anthropic provider.
What it does:
  a) Beta headers: LiteLLM allow-lists beta values from BerriAI's GitHub.
     Claude Code ships betas faster than the map updates.
     This module makes provider=anthropic pass client beta values through unchanged.
  b) Request fields: LiteLLM silently drops unknown top-level fields.
     Claude Code sends `safeguards` — without this fix, the safety verdict never returns
     and Claude Code's own classifier gets called (then 429'd on Max token).

### 5. otel callback (OpenTelemetry)

Purpose: Traces to the estate's collector.
What it sends: model, latency, tokens, cost — NOT prompt/completion content.

---

## THE X-API-KEY BUG AND FIX

### The problem

LiteLLM strips incoming auth headers when custom_auth is enabled.
Claude Code sends: Authorization: Bearer sk-ant-oat01-... (Max OAuth token)
LiteLLM processes it for proxy auth, then DROPS x-api-key before forwarding.
Anthropic receives: empty x-api-key → 401 "missing authentication"

### The fix

llm/config.yaml → litellm_settings:
  pass_through_client_api_key: true

This tells LiteLLM to forward the client's x-api-key header to the upstream LLM.
Confirmed present in llm/config.yaml as of 2026-09-27.

### After fixing

Claude Code → local_caller_auth → LiteLLM
  → pass_through_client_api_key: true
  → x-api-key: Bearer sk-ant-oat01-... forwarded to Anthropic
  → Anthropic accepts Max OAuth token → 200 OK

---

## SECRET MANAGEMENT

### Where keys live

Source of truth: estate-secrets repo (SOPS/age encrypted)
  ~/Documents/code/estate-secrets/secrets/dev/

Laptop router: SOPS-decrypted at startup, never written to disk unencrypted
  ~/.estate/litellm-local/secrets/*.yaml (ciphertext)
  Decrypted into process environment only

Cluster router: Kubernetes Secrets, mounted from Secrets Manager

### Keys the laptop router holds

  MINIMAX_API_KEY
  GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3
  CEREBRAS_API_KEY, CEREBRAS_API_KEY_2, CEREBRAS_API_KEY_3
  SAMBANOVA_API_KEY, SAMBANOVA_API_KEY_2, SAMBANOVA_API_KEY_3
  GEMINI_API_KEY
  DEEPSEEK_API_KEY
  NVIDIA_API_KEY
  OPENROUTER_API_KEY
  LITELLM_LAPTOP_KEY (caller auth)
  OTEL_EXPORTER_OTLP_ENDPOINT

### Keys the laptop router does NOT hold

  ANTHROPIC_API_KEY — unset by design. Claude Code's OAuth token pays.
  LITELLM_MASTER_KEY — unset. local_caller_auth handles auth instead.

### Key filtering at startup

litellm-local generates config.runtime.yaml at startup:
  - Reads llm/config.yaml
  - Drops model rows whose api_key env var is not set
  - Adds custom_auth: local_caller_auth.user_api_key_auth
  - Prepends local_caller_auth.proxy_handler_instance to callbacks

---

## AUDIT AND LOGGING

### Efficiency ledger

Path: ~/.estate/efficiency-ledger.jsonl (ESTATE_EFFICIENCY_LEDGER env var)

Two row types per call:

  pre row:
    v: 2
    kind: pre
    mode: openai | anthropic
    call_id: litellm call ID
    session: Claude Code session ID
    at: ISO timestamp
    model: actual model called
    ms: hook execution time
    bytes_before: JSON size before optimization
    bytes_after: JSON size after optimization
    bytes_saved: difference
    steps: {m1: ..., m2: ..., ...}  per-mechanism deltas

  outcome row:
    v: 2
    kind: outcome
    mode: openai | anthropic
    call_id: litellm call ID
    session: Claude Code session ID
    at: ISO timestamp
    latency_ms: end-to-end call time
    ok: true | false
    usage: {prompt_tokens, cache_read, cache_write_5m, cache_write_1h, output_tokens,
            input_equiv_billed, input_equiv_no_cache, cache_saved_input_equiv,
            cache_hit_pct}

What it proves: Per-call savings vs. what would have been billed without optimization.

### Router access log

Every refused request logged by local_caller_auth:
  REFUSED <reason> on <path>

This is the proof the auth gate is running.

### OTEL traces

Span per call: model, latency, tokens, cost.
NO content (turn_off_message_logging: true).

---

## PLATFORM RELATIONSHIPS

### Router ↔ Claude Code

Claude Code reads ANTHROPIC_BASE_URL from ~/.claude/settings.json.
Setting it to http://127.0.0.1:4000 routes all Claude Code traffic through the router.
Claude Code brings its own Max OAuth token. Router has no Anthropic key.

### Router ↔ Prospector

Prospector reads llm/config.yaml to know lane names.
When a user asks for "cheap model", prospector routes to "groq".

### Router ↔ Otto Gateway

Otto is the customer-facing API gateway.
Its private brain config has its own free floor (separate from the router's).

### Router ↔ Voice Pipeline

voice-asr and voice-tts lanes route to Groq (Whisper + Orpheus).
The Groq API key is held by the router. Voice pipeline calls the router.

### Router ↔ Fleet Reactor

The reactor uses Claude Code for the board.
Claude Code routes through the laptop router.
The router's efficiency gateway measures and records every reactor call.

### Router ↔ Agent Workforce

Agents use the router for all LLM calls.
The router enforces token ceilings so one bad session can't spend the estate's budget.

---

## STARTUP AND LIFECYCLE

### Install (one-time)

~/.estate/litellm-local/litellm-local install

Does:
  1. Copy launcher + config + modules to ~/.estate/litellm-local/
  2. Decrypt vendor keys into secrets/ (SOPS/age)
  3. Decrypt LITELLM_LAPTOP_KEY into caller/
  4. Generate config.runtime.yaml (drops lanes with missing keys)
  5. Register com.estate.litellm-local with launchd
  6. Wait 90s for /health/liveliness — FAIL hard if not live

### Why staged outside ~/Documents

launchd agents cannot read ~/Documents (macOS TCC restriction).
install copies everything to ~/.estate/litellm-local/, launchd runs from there.
Branch switches don't affect the running router.

### Run (what launchd calls)

~/.estate/litellm-local/litellm-local run

Does:
  1. Unset ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, DATABASE_URL
  2. Set PYTHONPATH to modules/
  3. Decrypt secrets/*.yaml into environment
  4. Generate config.runtime.yaml
  5. exec litellm --config config.runtime.yaml --host 127.0.0.1 --port 4000

### Health check

curl http://127.0.0.1:4000/health/liveliness
Returns 200 if router is alive.
Returns 403 if local_caller_auth refuses (wrong Host, no key, etc.).

### Commands

  ~/.estate/litellm-local/litellm-local status
  ~/.estate/litellm-local/litellm-local uninstall
  tail -f ~/Library/Logs/litellm-local.log

---

## CONFIGURATION FILES

  llm/config.yaml               — Source of truth, edit here
  llm/config.base.yaml          — Base config (platform/llm/config.base.yaml)
  platform/vendors/consoles.yaml — Vendor lane declarations
  bin/idp-vendor-render        — Renders config.yaml from base + consoles

  platform/llm/local_caller_auth.py
  platform/llm/efficiency_gateway.py
  platform/llm/request_ceiling.py
  platform/llm/anthropic_beta_passthrough.py
  platform/llm/litellm.yml

  ~/.estate/litellm-local/litellm-local
  ~/.estate/litellm-local/config.yaml
  ~/.estate/litellm-local/config.runtime.yaml
  ~/.estate/litellm-local/modules/
  ~/.estate/litellm-local/secrets/
  ~/.estate/litellm-local/caller/
  ~/.estate/litellm-local/sops

---

## ENVIRONMENT VARIABLES

  LITELLM_MASTER_KEY           — NOT SET on laptop (local_caller_auth instead)
  ANTHROPIC_API_KEY            — UNSET (Claude Code uses OAuth token)
  DATABASE_URL                  — UNSET (no DB)
  PYTHONPATH                   — Set to modules/ directory
  ESTATE_MAX_INPUT_TOKENS       — Request ceiling (default 128000)
  ESTATE_MAX_TOOL_DESC_CHARS   — MCPAdapter limit (default 400)
  ESTATE_MAX_HISTORY_MSGS      — CompactionManager limit (default 60)
  ESTATE_MAX_HISTORY_BYTES     — CompactionManager limit (default 200000)
  ESTATE_GIST_AFTER_MSGS       — GistingSimulator threshold (default 40)
  ESTATE_RUN_MIN_LINES         — TokenKiller run length (default 3)
  ESTATE_EFFICIENCY_LEDGER     — Ledger path (default ~/.estate/efficiency-ledger.jsonl)
  ESTATE_LOCAL_CALLER_KEY      — Decrypted laptop router key
  ESTATE_ROUTER_CONFIG         — Runtime config path
  ESTATE_ROUTER_HOSTS          — Allowed Host values (default 127.0.0.1:4000,localhost:4000)
  OTEL_EXPORTER_OTLP_ENDPOINT  — Collector URL (default http://127.0.0.1:4318)
  OTEL_SERVICE_NAME            — litellm-local (laptop) or litellm (cluster)

---

## DIAGNOSIS GUIDE

### Router not responding

  1. Check port: lsof -i :4000
     If something else is there → kill it, restart router
  2. Check launchd: ~/.estate/litellm-local/litellm-local status
  3. Check logs: tail ~/Library/Logs/litellm-local.log
  4. Check health: curl http://127.0.0.1:4000/health/liveliness

### Auth failures (401 from router)

  1. Router not started → install and start
  2. Wrong port → router on 5606, local_caller_auth rejects Host mismatch
  3. Missing laptop key → check caller/LITELLM_LAPTOP_KEY.yaml decrypts

### Anthropic auth failures (401 from Anthropic)

  1. Check llm/config.yaml has pass_through_client_api_key: true
  2. Reinstall router: ~/.estate/litellm-local/litellm-local install

### Token ceiling firing (400 from router)

  1. Session context is too large
  2. Fix: compaction, not retries
  3. Check ledger: grep <session_id> ~/.estate/efficiency-ledger.jsonl

---

## RELATED INTENTS

  k8s.debug              — Diagnose cluster issues
  hypotheses.race         — Bayesian diagnosis for complex failures
