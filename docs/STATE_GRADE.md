# State-Grade Operations Guide

This document explains how Global Intelligence enforces data
sovereignty, classification handling and need-to-know access. It is
the reference for operators deploying the platform in a sensitive
context (government, defense, critical-infrastructure).

> **Status:** Foundation P1 implemented. MFA (P2) and report signing
> (P3) are still placeholders — see "Roadmap" at the bottom.

---

## 1. Why classification + RLS + local LLMs?

A classical multi-tenant SaaS leaks data through three vectors:

1. **The LLM provider.** Every prompt sent to an external API leaves
   the operator's perimeter. For intelligence work that is
   unacceptable.
2. **Application-level filtering.** A bug in the API can return rows
   the caller should not see. A second layer of defense at the
   database is required.
3. **Shared session state.** Long-lived connections must carry the
   caller's clearance into the database for every query.

We address those three vectors with:

| Layer | Mechanism |
| --- | --- |
| LLM sovereignty | `app.services.llm.router.LLMRouter`, primary provider is Ollama |
| Defense in depth | PostgreSQL Row Level Security on classified tables |
| Session context | `app.set_user_context(clearance, org_id)` called per-request |

---

## 2. Classification taxonomy

`app.core.classification` defines the canonical labels used across
the platform.

| Level | Int | Handling |
| --- | --- | --- |
| `PUBLIC` | 0 | Freely shareable. OSINT, press, public datasets. |
| `RESTRICTED` | 1 | OUO / FOUO equivalent. Need-to-know inside an org. |
| `CONFIDENTIAL` | 2 | Local infra only. RLS enforced. |
| `SECRET` | 3 | Local infra only. RLS enforced. Audit recommended. |

`TOP_SECRET` is intentionally not modeled — it requires physically
isolated infrastructure that is out of scope.

Auxiliary taxonomies:

* **TLP v2.0** (`TLP.CLEAR` ... `TLP.RED`) carries the sharing caveat
  with every output.
* **NATO Admiralty (STANAG 2511)** rates the source reliability
  (A-F) and the credibility of the information (1-6) separately.

---

## 3. Access matrix — clearance vs. LLM provider

Rule of thumb: a row whose classification is *C* may only be read by
a caller whose clearance is *>= C*, and may only be processed by an
LLM provider that is allowed at *C*.

| Classification | Ollama (local) | vLLM (local) | OpenRouter (external) |
| --- | --- | --- | --- |
| PUBLIC | yes | yes | yes, only if `ENABLE_OPENROUTER_FALLBACK=true` |
| RESTRICTED | yes | yes | **forbidden** |
| CONFIDENTIAL | yes | yes | **forbidden** |
| SECRET | yes | yes | **forbidden** |

When `STATE_GRADE_MODE=true` (default), the router additionally
*fails closed* for CONFIDENTIAL+ tasks if no local provider is
reachable — it will not silently downgrade.

---

## 4. Postgres Row Level Security

Migration `0001_state_grade_classification.py` installs:

* A helper schema `app` with the function
  `app.set_user_context(p_clearance int, p_org_id uuid)` that uses
  `SET LOCAL` to push request-scoped session variables.
* `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on
  `intelligence_items`, `daily_reports`, `premium_reports`.
* A single policy per table that checks:
  * `classification <= current_setting('app.user_clearance')::int`
  * `org_id IS NULL OR org_id = current_setting('app.user_org_id')::uuid`

The application MUST call `app.set_user_context(...)` at the start
of every authenticated request. The dependency
`app.api.deps_classified.get_db_with_context` does this
automatically — use it instead of the raw `get_db` for any endpoint
that touches classified tables.

---

## 5. Bringing up Ollama

```bash
docker compose up -d ollama
# pull the default model (about 4.7GB on disk)
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
# sanity check
docker compose exec ollama ollama list
```

To use a different model:

```env
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M
```

GPU acceleration: uncomment the `deploy.resources.reservations`
block under the `ollama` service in `docker-compose.yml` and install
the NVIDIA Container Toolkit on the host.

---

## 6. Assigning a clearance level

Until a dedicated admin endpoint ships (P2), clearance is set
directly in the database:

```sql
UPDATE users
SET clearance_level = 2,        -- CONFIDENTIAL
    org_id = '<uuid-of-org>'    -- NULL for global users
WHERE email = 'analyst@agency.gov';
```

The corresponding Python constants are in
`app.core.classification.ClassificationLevel`.

A user who has not been granted a clearance defaults to PUBLIC and
will only see rows with `classification = 0`.

---

## 7. State-grade activation checklist

1. Set in `.env`:
   ```env
   STATE_GRADE_MODE=true
   ENABLE_OPENROUTER_FALLBACK=false
   OPENROUTER_API_KEY=          # leave empty
   ```
2. `docker compose up -d`.
3. `docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M`.
4. Assign clearance levels to operators (see section 6).
5. Reach the platform through `/api/v1/classified/*`. Calls to the
   legacy `/api/v1/*` aggregate router will be removed before GA.

---

## 8. Roadmap and disclaimers

The following items are **not** implemented yet and MUST be
addressed before going live with real classified data:

* **MFA (P2).** `require_mfa_verified_user` currently accepts the
  `two_factor_enabled` flag without verifying a TOTP code. Replace
  with a real WebAuthn / TOTP exchange step that issues an access
  token carrying `mfa_verified=true`.
* **Report signing (P3).** The `signature` columns on
  `daily_reports` and `premium_reports` are populated as NULL.
  A detached-signature scheme (Ed25519 or PQC hybrid) should be
  wired in.
* **Real OSINT providers (P3).** `OSINTAgent.execute` raises
  `NotImplementedError`. Plug providers under
  `app.agents.providers.osint.*` (NewsAPI, RSS, GDELT, ...).

### Compliance references

This codebase is designed to **support** compliance with:

* Esquema Nacional de Seguridad (ENS, Spain) — Real Decreto 311/2022.
* ISO/IEC 27001:2022.
* NIST SP 800-53 Rev. 5 (relevant control families: AC, AU, SC).

It is NOT certified. Certification requires organizational controls
(personnel screening, physical security, incident response, ...)
that are outside this repository.
