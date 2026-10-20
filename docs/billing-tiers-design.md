# Billing & Tiers Design — Pwanimate Spark

**Status:** design (2026-10-20) — nothing implemented yet beyond what §"Build sequence" marks as done.
**Owner:** Pwanimate. **Stack:** M-Pesa Daraja (STK push), fee-per-transaction, no recurring infrastructure.

---

## 1. Goals and hard constraints

1. **$0 recurring cost for the free tier.** The free tier must cost us nothing in API spend. Every rung reachable by a free-tier student must be a genuinely free model (§4).
2. **The free tier is never denied service.** Caps *degrade* (queue + notify), they never block or 402. A student mid-assignment is never told "upgrade".
3. **Model locks are enforced server-side** (D8). The client can POST any model name today — that hole is closed at the gateway, not in the UI.
4. **Retrieval is tier-invisible** (D7): local `spark-vector` embeddings for every tier, so a paid tier buys *answer quality*, not search.
5. **No fixed infrastructure per tier.** Everything scales on the box we already run (2 vCPU, 7.7 GiB) plus per-call API cost paid out of revenue.
6. **The UI renders from the API.** No hardcoded model cards, no hardcoded prices (§7).

## 2. The cost model (this decides the prices)

**Measured token shape of one real turn** (from our own logs): prompt ≈ 8–12k tokens (our RAG context is *large* — the page-scoped attachment block alone is ~37k characters), output ≈ 1–2k tokens.

**Cost per call** (list prices, Oct 2026 — re-verify monthly, they drift):

| Class | Example | Input $/M | Output $/M | **Cost per turn** |
|---|---|---|---|---|
| `FREE_ROUTE` | Gemini free tier, Groq free tier, OpenRouter `:free` | 0 | 0 | **$0.00** (rate-limited, not billed) |
| `PAID_FLASH` | paid Gemini Flash tier, cheap OpenRouter models | ~0.075 | ~0.30 | **~$0.0014** |
| `FRONTIER` | frontier/pro-class models (e.g. `gemini-pro-latest`) | ~1.50 | ~6.00 | **~$0.030** |
| `VISION_EXTERNAL` | external VL per image | — | — | **~$0.005 / image** |

**What one price can afford** (1 USD ≈ 130 KSh):

| Price | USD | Frontier turns affordable/month | `PAID_FLASH` turns affordable/month |
|---|---|---|---|
| 30 KSh | $0.23 | ~7 | ~160 |
| 50 KSh | $0.38 | ~12 | ~270 |
| 300 KSh | $2.31 | ~77 | ~1,650 |
| 900 KSh | $6.92 | ~230 | ~4,900 |

*(less the ~1% + KSh 0.40 Daraja fee, and assuming a frontier turn costs $0.03)*

### 2.1 The answer to "day pass 30, monthly 50?"

**Not 50 for the month — 50 is priced for a *different product*.**

- **50 KSh/month ($0.38)** only breaks even if the customer uses ~12 frontier turns a month. Sell it as "a month of the premium model" and the heavy user (the one who actually wants to pay) costs us 3–5× what they paid. That is the classic mistake: your best customers subsidise your worst margin.
- **900 KSh/month (30 × 30)** is a different market entirely (~$6.90/month) — priced for institutions/teams, not for a student comparing it to a $2 data bundle.

**Recommendation:**

| Tier | Price | Duration | Frontier allowance | Why it holds |
|---|---|---|---|---|
| **Day Pass** | **30 KSh** | 24 h | 20 frontier turns/day | Worst case 20 × $0.03 = $0.60 vs $0.23 revenue… **so cap it at 10/day** ($0.30, ≈$0.38 gross) |
| **Pro Monthly** | **300 KSh** | 30 d | 5 frontier turns/day (150/mo = $4.50)… **cap at 3/day** (90/mo = $2.70 vs $2.31 + margin from flash) | Profitable at heavy use, attractive at light use |
| **Pro Lite** *(optional 5th)* | **50 KSh** | 30 d | **no frontier** — paid-flash + priority + external vision | 270 flash turns = $0.38 ⇒ break-even, never loses |
| **Teams** | **1,200 KSh/seat** (min 5) | 30 d | same as Pro | Negotiated, shared, admin |

**The rule underneath:** sell *model class and capability*, never "unlimited frontier". Every tier's worst case must be under its price.

## 3. Tier catalogue

| | **Ember** (free) | **Day Pass** | **Pro Monthly** | **Teams** |
|---|---|---|---|---|
| Price | KSh 0 | KSh 30 | KSh 300 | KSh 1,200/seat (min 5) |
| Duration | — | 24 h | 30 d | 30 d, renews as a group |
| Engines visible | all 4 | all 4 | all 4 | all 4 |
| Model class | `FREE_ROUTE` only | + `PAID_FLASH` | + `FRONTIER` (3/day) | + `FRONTIER` (10/day) |
| Chats/day | 20 (then queue + notify) | 60 | 200 | 500/seat-pool |
| Images/day | 5 (local VLM, queued) | 20 (external VL, immediate) | 60 (external VL) | 200 (external VL) |
| Chat priority | queue | priority | priority | priority |
| Embeddings/retrieval | local (identical) | local | local | local |
| Study Mode | ✓ | ✓ | ✓ | ✓ |
| Collections | personal | personal | personal | **shared + admin** |
| Receipts / VAT | — | ✓ | ✓ | ✓ + company |

*(Chats/day caps are **soft**: over the cap the request queues and notifies — never a block.)*

## 4. The $0 guarantee: every free-tier rung must be free

**Rule:** a `FREE_ROUTE` offering may only be served on a provider's *free* allowance (Gemini free tier, Groq free tier, OpenRouter `:free` ids).

**Verified 2026-10-20 against OpenRouter's live catalog:** `google/gemini-3.8-flash` has **no `:free` variant** — it is a *paid* model, and it sat in the 2nd–3rd rung of **every** engine ladder. Any free-tier chat falling past Gemini and Groq would have been **billed**. Replaced with `nvidia/nemotron-3-ultra-550b-a55b:free` (a 550B-class free flagship; the catalog has 17 free ids including `nemotron-3.5-super-vl:free` for vision).

Other free ids available for future rungs: `minimax/minimax-m3.1-flash:free`, `thinkingmachines/inkling:free`, `google/gemma-4-31b-it:free`, `cohere/north-mini-code:free` (code), `poolside/laguna-s-2.1:free` (code), `nvidia/nemotron-3-5-lightning:free`.

> **Operational rule:** any new ladder rung must be added to the registry with a cost class, and the CI check (§9) fails if a `FREE_ROUTE` offering points at a non-`:free` OpenRouter id or a paid Gemini/Groq model.

## 5. Which models in which tier (the matrix)

**Registry rows** (seeded from the current ladders; `min_tier` = the lowest tier allowed to reach it):

| Offering key | Provider / model | Class | min_tier | Notes |
|---|---|---|---|---|
| `gemini-flash-38` | gemini `gemini-3.8-flash` | FREE_ROUTE | Ember | identity primary for Speed/Scholar |
| `gemini-flash-36` | gemini `gemini-3.6-flash` | FREE_ROUTE | Ember | |
| `gemini-flash-lite-35` | gemini `gemini-3.5-flash-lite` | FREE_ROUTE | Ember | |
| `groq-gpt-oss-120b` | groq `openai/gpt-oss-120b` | FREE_ROUTE | Ember | Coda identity primary |
| `groq-gpt-oss-20b` | groq `openai/gpt-oss-20b` | FREE_ROUTE | Ember | |
| `groq-qwen-38-27b` | groq `qwen/qwen3.8-27b` | FREE_ROUTE | Ember | also the vision backup |
| `or-nemotron-ultra` | openrouter `nvidia/nemotron-3-ultra-550b-a55b:free` | FREE_ROUTE | Ember | replaced the paid gemini rung |
| `or-nemotron-super` | openrouter `nvidia/nemotron-3-super-120b-a12b:free` | FREE_ROUTE | Ember | |
| `or-nemotron-lightning` | openrouter `nvidia/nemotron-3.5-lightning:free` | FREE_ROUTE | Ember | |
| `or-liquid-lfm` | openrouter `liquid/lfm-2.5-2.6b:free` | FREE_ROUTE | Ember | |
| `or-super-vl` | openrouter `nvidia/nemotron-3.5-super-vl:free` | FREE_ROUTE | Ember | free vision backup (local VLM era) |
| `gemini-flash-paid` | gemini paid tier | PAID_FLASH | Day Pass | ~$0.0014/turn |
| `vision-external` | external VL (per image) | VISION_EXTERNAL | Day Pass | ~$0.005/image, immediate |
| `frontier-pro` | frontier/pro-class (e.g. `gemini-pro-latest`) | FRONTIER | Pro Monthly | **3 turns/day** on Pro, 10 on Teams |

**How a tier maps onto an engine:** the *engine* (Speed/Coda/Scholar/Vision) stays visible to everyone (§3). What a tier changes is **which rung of the ladder may be used**:
- Ember → the ladder is filtered to `FREE_ROUTE` rungs only.
- Day Pass+ → `PAID_FLASH` rungs become eligible (inserted after the free ones, so the free route still leads when it's healthy).
- Pro/Teams → `FRONTIER` rungs become eligible but are **allowance-gated** (3/day), and are only reached *after* the free/flash rungs fail — they are never the default path.

**The `gemini-pro-latest` question is now answered** (it was §12's open item): it is **Pro/Teams only**, and it must **leave the global Auto chain** (`PWANIMATE_LLM_FALLBACK_CHAIN`) — otherwise every free student reaches a frontier model by failover. It becomes a registry row with `min_tier = Pro Monthly`, reachable only when the chain filter admits it.

## 6. Enforcement (server-side)

**Tier resolution** (per request, cached in the request): `Subscription` (active, unexpired) → `Tier.rank`; no subscription or expired → `Ember` (rank 0).

**Chain filtering — the important one.** `LLMRouter.resolve_fallback_chain()` currently returns the engine ladder (or the global Auto chain). The filter runs *after* resolution and *before* the first attempt:

```
for candidate in resolved_chain:
    offering = registry.lookup(candidate.provider, candidate.model)
    if offering.min_tier.rank > user_tier.rank:  -> drop the candidate
```

Consequences:
- A free student's ladder contains **only** `FREE_ROUTE` rungs ⇒ the $0 guarantee is structural, not a convention.
- The frontier model is unreachable via failover for free students ⇒ no "one unlucky chain" leak.
- Providers without keys are still skipped silently, as today.

**Explicit requests.** Today the chat API accepts `provider`/`model` from the client (`views.py:450-451`). After the registry lands, a request naming an offering above the user's tier returns **403** with a machine-readable body:

```json
{"error": "model_locked", "required_tier": "pro_monthly",
 "offering": "frontier-pro", "upgrade_url": "/api/pwanimate/billing/mpesa/stk/"}
```
The UI turns that into a lock badge + upgrade CTA. A free-tier user is never *denied* — they are offered the path to unlock.

**Caps → degrade, never block.** Over-cap chats enter the existing queue + notify path (the same mechanism the free vision tier uses). No 402, no "upgrade to continue" wall.

**Cost accounting.** Every turn records `offering_id`, `cost_class`, `tokens` → `UsageCounter` (per user per day) and a `UsageRecord` for margin reporting (cost per tier, per day). This is what tells us whether 300 KSh is right.

## 7. API surface (the UI renders only from this)

| Endpoint | Purpose |
|---|---|
| `GET /api/pwanimate/billing/tiers/` | tiers + prices + the caller's tier + per-offering lock state + entitlement counters + upgrade copy |
| `GET /api/pwanimate/billing/subscription/` | current subscription, expiry, usage counters (chats/images today) |
| `POST /api/pwanimate/billing/mpesa/stk/` | start a payment: `{phone, tier_code}` → `{checkout_id, message, expires_in}` |
| `POST /api/pwanimate/billing/mpesa/callback/` | Daraja webhook (public, rate-limited, idempotent) |
| `POST /api/pwanimate/billing/manage/cancel/` | cancel auto-renew (no auto-renew in v1 → 501 until then) |

**UI behaviour:** the engine cards and the "premium" chips render their lock state from `tiers/`. A locked chip is visibly locked with the required tier and price; tapping it opens the payment sheet (phone → STK). No prices or tier names are hardcoded in JS (there is an existing settings-UI test asserting no pricing text — it will be updated *deliberately* when the billing UI lands, not silently).

## 8. M-Pesa Daraja flow (STK push)

1. Client posts `{phone, tier_code}` → server validates the tier, creates a `Payment` row (`status=pending`, `reference=<uuid>` as the Daraja account reference, amount from the tier price — **never from the client**).
2. Server calls Daraja's STK-push endpoint (business paybill + LNM) with `Amount`, `AccountReference=<payment.reference>`, `TransactionDesc="<tier> (<days>d)"`, `PhoneNumber=<254…>`.
3. Daraja pushes the STK prompt to the phone; the customer enters their PIN.
4. Daraja calls back `/billing/mpesa/callback/` with `ResultCode` (0 = success) and the transaction code.
5. Server: **idempotent** (unique constraint on the Daraja transaction code) → on success, create/extend the `Subscription` (`tier`, `starts_at`, `ends_at = starts_at + duration_days`), mark the payment `paid`, notify the user (the `notifications` app already exists ✓).
6. On failure/timeout → `Payment.status = failed|expired`; the tier never activates.

**Verification caveat (important):** Daraja's basic callback is **not cryptographically signed** — anyone who learns the URL can post a fake "success". Mitigations, in order of cost:
- Only accept a callback whose `AccountReference` matches an existing **pending** `Payment` row *and* whose `Amount` equals that row's amount (both server-side facts a forger cannot know).
- Reconcile daily against Daraja's transaction-query API for the business paybill; quarantine mismatches.
- Rotate the paybill credentials if a forgery ever lands.

**Fees:** ~1% + KSh 0.40 per transaction ⇒ ~2.3% at 30 KSh, ~1.1% at 300 KSh. No fixed cost ✓ ($0-budget constraint holds).

**No auto-renew in v1.** A Day Pass/Monthly is a single payment; renewal is a second STK push the user initiates (recurring Daraja mandates need extra paperwork and dispute handling — out of scope for v1).

## 9. Build sequence (ordered, each independently shippable)

1. **Registry + models, no behaviour change.** `Tier`, `ModelOffering`, `Subscription`, `Payment`, `UsageCounter`; `manage.py seed_model_registry` (seeds tiers + offerings from the ladders). Tests: schema, seeding, ordering. *Nothing changes for users yet.*
2. **Tier resolution + chain filtering.** Resolve the caller's tier; filter resolved chains by `min_tier`; **remove `gemini-pro-latest` from the global Auto chain**; add the CI check that a `FREE_ROUTE` offering is a genuinely free id (§4). *Effect: the $0 guarantee becomes structural.*
3. **Entitlements + caps.** Daily counters (20 chats, 5 images) with the queue+notify degradation; `tiers/` API.
4. **UI: locks + upgrade CTA.** Engine cards render lock state from the API; the upgrade sheet starts an STK push. *(Update the settings-UI pricing test deliberately here.)*
5. **Daraja: STK + callback + activation.** Sandbox first, then live; idempotent callbacks; receipts; activation notification.
6. **Teams**: seats, admin, shared collections, company receipts.
7. **Margin reporting**: cost per tier per day (from `UsageRecord`) — the number that tells us when to adjust 300 KSh.

## 10. Open questions

- **Teams commercials**: who pays (student or institution), min seats, seat reassignment, VAT/invoicing for Kenyan institutions.
- **Pro Lite (50 KSh)**: ship it as a 5th tier or use it to make Pro Monthly feel expensive?
- **Refund policy**: within 24 h? proportional?
- **Price drift**: provider list prices change monthly; the break-even table must be re-verified (and the allowance caps adjusted) — a 2× price rise on frontier models turns Pro Monthly from profitable to loss-making.
- **Free-route extinction**: if Gemini/Groq/OpenRouter free tiers disappear, Ember becomes $0-cost-impossible; the fallback is to fund Ember from Pro revenue (§9.7 margin reporting would show it) or to move Ember to `PAID_FLASH` with a hard cap and shrink the free tier's promise.
- **Vision allowance for paid tiers**: priced per image (~$0.005) — is 20/day the right number, or should external vision be metered by credits instead of a cap?
- **Student verification**: is a phone number enough to hold a paid tier, or do we need a verified student ID (institutional fraud risk)?
