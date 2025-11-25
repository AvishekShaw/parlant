# Synthetic Conversation Generation - Session Actions & Context

**Date:** November 7, 2025
**Session:** Continuation of Phase 3 Implementation
**Goal:** Generate synthetic financial conversation data using Parlant agent + LLM-simulated personas

---

## 🎯 Current Status: BLOCKED ON TIMEOUTS

### Critical Issue
**Parlant agent is timing out even with Sonnet 3.5 and 120-second HTTP timeouts.**

All timeout attempts failed:
- ✗ 10s timeout: Failed (test_sonnet_1_conversation.log)
- ✗ 60s timeout: Failed (test_sonnet_retry.log)
- ✗ 120s timeout: Failed (test_sonnet_120s_timeout.log)

**Root Cause:** Parlant makes 4+ LLM calls per agent turn (journey selection, guideline matching, tool execution, response generation), EACH with retry logic (up to 3 attempts with exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s). If Anthropic API is slow or hitting rate limits, cumulative time easily exceeds 120 seconds.

**Current Configuration:**
- Parlant agent model: Claude Sonnet 3.5 (`claude-3-5-sonnet-20241022`)
- Persona simulation model: Claude Haiku (`claude-3-5-haiku-20241022`)
- HTTP GET timeout: 120s (parlant_inference_endpoint.py:205)
- HTTP POST timeout: 180s (lines 127, 160)
- Overall polling timeout: 300s (line 50)
- Composition mode: FLUID (main.py:106)

---

## 📁 Key Files and Their Current State

### 1. `parlant_inference_endpoint.py` (273 lines)
**Purpose:** Adapter bridging conversation generator to Parlant REST API

**Current Timeout Configuration:**
```python
Line 50:  timeout: int = 300                    # Overall polling timeout
Line 127: timeout=180                           # Session creation POST
Line 160: timeout=180                           # Customer message POST
Line 205: timeout=120                           # Event polling GET ⚠️ MOST RECENTLY CHANGED
```

**Key Methods:**
- `_create_session()`: Creates new Parlant session
- `_send_customer_message()`: POSTs customer message to `/sessions/{id}/events`
- `_poll_for_agent_response()`: Polls GET `/sessions/{id}/events` until agent responds
- `get_assistant_message()`: Main interface called by conversation generator

**Recent Changes:**
- Increased GET timeout from 10s → 60s → 120s trying to avoid timeouts
- Fixed event payload format (nested → top-level)
- Fixed role validation for enum comparison
- Fixed response parsing for string vs dict formats

### 2. `src/parlant/adapters/nlp/anthropic_service.py` (284 lines)
**Purpose:** Controls which Claude model Parlant agent uses

**Current Setting (Line 275):**
```python
async def get_schematic_generator(self, t: type[T]) -> AnthropicAISchematicGenerator[T]:
    # Temporarily using Sonnet 3.5 to test quality - Haiku was producing poor responses
    return Claude_Sonnet_3_5[t](self._logger, self._meter)  # type: ignore
```

**Available Models:**
- `Claude_Haiku_3_5` (lines 239-250): `claude-3-5-haiku-20241022` - Cheap but produces terrible quality
- `Claude_Sonnet_3_5` (lines 197-208): `claude-3-5-sonnet-20241022` - Testing now, timing out
- `Claude_Sonnet_4` (lines 211-222): `claude-sonnet-4-20250514` - Expensive
- `Claude_Opus_4_1` (lines 225-236): `claude-opus-4-1-20250805` - Very expensive, AVOID

**Retry Policy (Lines 96-107):**
```python
@policy([
    retry(
        exceptions=(
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIResponseValidationError,
        )
    ),
    retry(InternalServerError, max_exceptions=2, wait_times=(1.0, 5.0)),
])
```

**Issue:** Each LLM call retries up to 3 times with exponential backoff. With 4+ calls per turn, this compounds.

### 3. `main.py` (140 lines)
**Purpose:** Parlant server configuration

**Critical Setting (Line 106):**
```python
composition_mode=p.CompositionMode.FLUID,  # Changed from STRICT
```

**Composition Modes:**
- `STRICT`: Only canned responses → caused "Let me look into that" loop
- `FLUID`: Dynamic generation → allows real responses
- `COMPOSITED`: Mimics canned style

**Other Config:**
- Server: FastAPI on port 8800
- NLP Service: `p.NLPServices.anthropic`
- Journeys: dispute_transaction, lock_card, replace_card
- Tools: 6 mock implementations in tools.py

### 4. `generate_synthetic_conversations.py` (471 lines)
**Purpose:** Main orchestration script for batch generation

**Current Test Settings:**
```python
Line 200: model_id: str = "claude-3-5-haiku-20241022"  # Persona simulation
Line 202: timeout: int = 300                           # Polling timeout
Line 238: return data['users'][:1]                     # TEMP: Only 1 persona for testing
```

**Full Pipeline:**
- Loads personas from `data/conversation_characters/financial_personas.yaml`
- Starts Parlant server (subprocess)
- Creates sessions for each persona
- Generates conversations (max 15 turns)
- Exports to JSON (sessions.json, events.json)
- Stops server

**Run Command:**
```bash
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee <logfile>
```

### 5. `data/conversation_characters/financial_personas.yaml`
**Purpose:** 25 financial dispute personas

**Distribution:**
- 7 Elder (tech scams, fraud)
- 7 Millennial (subscriptions, online fraud)
- 6 Small Business Owner (merchant disputes, B2B fraud)
- 5 Foreigner (international transactions, currency issues)

**Each persona has:**
```yaml
- name: Margaret Chen
  customer_type: Elder
  description: 72-year-old retired librarian...
  personality: Anxious and apologetic...
  scenario: "Margaret noticed a $299 charge..."
  dispute_reason: fraud
  summary: Elderly scam victim needs fraud help
```

### 6. `tools.py` (267 lines)
**Purpose:** Mock tool implementations for Chase Digital Assistant

**Available Tools:**
- `list_user_cards()`: Returns mock credit card data
- `fetch_recent_transactions()`: Returns mock transaction history
- `file_dispute()`: Files dispute, returns dispute ID
- `lock_card()`: Locks card temporarily
- `get_user_address()`: Returns mock address
- `process_card_replacement()`: Initiates card replacement

**Mock Data Structure:**
```python
MOCK_CARDS = {
    "Elder": [...],
    "Millennial": [...],
    "Small Business Owner": [...],
    "Foreigner": [...]
}
```

---

## 🔧 Timeline of Changes This Session

### 1. Investigation Phase
- Read `test_sonnet_retry.log` - found 60s timeout failure
- Read `parlant_inference_endpoint.py` - analyzed timeout settings
- Read `test_sonnet_1_conversation.log` - found 10s timeout failure
- Read `generate_synthetic_conversations.py` - understood pipeline
- Read `anthropic_service.py` - found Sonnet 3.5 configuration

### 2. Timeout Increase #1: 10s → 60s
**File:** `parlant_inference_endpoint.py:205`
```python
# Before:
response = requests.get(url, params=params, timeout=10)

# After:
response = requests.get(url, params=params, timeout=60)
```
**Result:** Still timed out ❌

### 3. Timeout Increase #2: 60s → 120s
**File:** `parlant_inference_endpoint.py:205`
```python
response = requests.get(url, params=params, timeout=120)  # Increased to 120s - agent may retry multiple LLM calls
```
**Result:** Still timed out ❌

### 4. Background Process Management
- Started test with 120s timeout: `3c0e40`
- Found port 8800 already in use (PID 96802)
- Killed existing server
- Process completed but still failed with timeout

---

## 🚨 Previous Issues (RESOLVED)

### Issue #1: Haiku Quality
**Problem:** With Haiku, agent only responded "Oh no." repeatedly
**Root Cause:** Haiku too weak for Parlant's complex reasoning
**Solution:** Switched to Sonnet 3.5
**Status:** Resolved, but introduced timeout issues

### Issue #2: STRICT Composition Mode
**Problem:** Agent only responded "Let me look into that."
**Root Cause:** STRICT mode only allows canned responses
**Solution:** Changed to FLUID mode
**Status:** Resolved (main.py:106)

### Issue #3: Cost Overruns ($50 burnt)
**Problem:** User burnt through $50 in one morning
**Root Cause:** Parlant agent was using Opus 4.1 / Sonnet 4 by default
**Solution:** Changed to Haiku, then Sonnet 3.5
**Cost Impact:** Dropped from ~$25-30 to ~$0.23 per 2 conversations
**Status:** Resolved

### Issue #4: Event Payload Format (422 Error)
**Problem:** Server rejected event creation
**Solution:** Changed payload from nested to top-level message format
**Status:** Resolved

### Issue #5: Role Validation Failure
**Problem:** Enum comparison failing
**Solution:** Enhanced role checking to handle both enum and string
**Status:** Resolved

---

## 📊 Test Results Summary

| Test | Model | Timeout | Result | Log File |
|------|-------|---------|--------|----------|
| Initial | Haiku | 10s | Poor quality (only "Oh no.") | test_2_conversations.log |
| Retry #1 | Sonnet | 10s | Timeout ❌ | test_sonnet_1_conversation.log |
| Retry #2 | Sonnet | 60s | Timeout ❌ | test_sonnet_retry.log |
| Retry #3 | Sonnet | 120s | Timeout ❌ | test_sonnet_120s_timeout.log |

**Estimated Time per Turn:** >120 seconds (exact time unknown, exceeded timeout)

**Projected Full Generation Time:**
- 25 personas × 15 turns = 375 turns
- At 120s+ per turn = 12.5+ hours minimum
- Likely 18-31 hours in practice

---

## 🎯 Options for Next Session

### Option 1: Increase Timeout Further ⚠️ RISKY
**Action:** Set GET timeout to 180s or 300s

**Changes:**
```python
# parlant_inference_endpoint.py:205
response = requests.get(url, params=params, timeout=300)
```

**Pros:**
- Might finally work
- No code changes needed beyond timeout

**Cons:**
- 5 minutes per turn = 31+ hours for 25 conversations
- Could still timeout if API issues persist
- Very expensive (Sonnet costs ~$3/1M input, $15/1M output)

**Recommended:** Try once more with 300s, but if it fails, move to Option 2 or 3

---

### Option 2: Reduce Retry Logic 🔧 MODERATE RISK
**Action:** Disable or reduce Parlant's retry policies

**Changes:**
```python
# src/parlant/adapters/nlp/anthropic_service.py:96-107
# Comment out retry policies OR reduce max_attempts

# BEFORE:
@policy([
    retry(
        exceptions=(
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIResponseValidationError,
        )
    ),
    retry(InternalServerError, max_exceptions=2, wait_times=(1.0, 5.0)),
])

# AFTER (Option A - Remove retries):
# @policy([...])  # Comment out entirely

# OR (Option B - Reduce attempts):
@policy([
    retry(
        exceptions=(
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIResponseValidationError,
        ),
        max_attempts=1,  # No retries, fail fast
        wait_times=(0.5,)
    ),
])
```

**Pros:**
- Much faster (fail within seconds instead of minutes)
- Still uses Parlant's journey/guideline features
- Cheaper (fewer API calls)

**Cons:**
- Lower reliability (might fail on transient API issues)
- Might need to manually retry failed conversations

**Recommended:** Good middle ground - try this with 60s timeout

---

### Option 3: Check Anthropic API Status 🔍 INVESTIGATION
**Action:** Verify if Anthropic API is having issues

**Steps:**
1. Check Anthropic status page: https://status.anthropic.com/
2. Test direct API call outside Parlant to measure latency
3. Check if hitting rate limits (check account dashboard)

**Test Script:**
```python
# test_anthropic_latency.py
import time
from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

start = time.time()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, how are you?"}]
)
end = time.time()

print(f"Response time: {end - start:.2f}s")
print(f"Response: {response.content[0].text}")
```

**Run:**
```bash
.venv/bin/python test_anthropic_latency.py
```

**Expected:** <5s response time
**If >10s:** API issues likely

---

### Option 4: Bypass Parlant (Simplify) ⚡ FAST BUT LOSES FEATURES
**Action:** Generate conversations using direct Anthropic API calls instead of Parlant agent

**Pros:**
- Much faster (1-2s per turn instead of 120s+)
- Much cheaper (only 2 LLM calls per turn: persona + assistant)
- Guaranteed to work
- Can generate all 25 conversations in <1 hour

**Cons:**
- Loses Parlant's journey/guideline intelligence
- Loses tool execution simulation
- Less realistic conversations (no journey state management)
- Would need to implement simple conversation logic

**Implementation Approach:**
```python
# Simple two-LLM conversation
for turn in range(max_turns):
    # Persona generates user message
    user_message = persona_llm.generate(
        context=conversation_history,
        persona=persona_card,
        scenario=scenario
    )

    # Assistant responds (direct Claude call, no Parlant)
    assistant_message = assistant_llm.generate(
        context=conversation_history + [user_message],
        system_prompt=chase_assistant_description
    )

    conversation_history.append(user_message)
    conversation_history.append(assistant_message)
```

**Recommended:** Last resort if Option 1-3 fail

---

### Option 5: Hybrid Approach (Generate Real Data from Real Parlant) 🎨 CREATIVE
**Action:** Use Parlant Sandbox UI to have real conversations, export those

**Steps:**
1. Start Parlant server: `.venv/bin/python main.py`
2. Open Sandbox UI: http://localhost:8800
3. Manually simulate 5-10 conversations using personas
4. Export session data via API: `GET /sessions` and `GET /sessions/{id}/events`
5. Use those as seed data
6. Generate variations using direct LLM calls for remaining personas

**Pros:**
- Real Parlant journey/guideline behavior
- High quality seed data
- No timeout issues
- Fast for remaining personas

**Cons:**
- Manual work for seed conversations
- Hybrid approach more complex

---

## 🔥 Recommended Action Plan

### Immediate Next Steps:

**1. Test API Latency (5 minutes)**
```bash
# Create and run test script
cat > test_anthropic_latency.py << 'EOF'
import time
from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

print("Testing Sonnet 3.5 latency...")
for i in range(3):
    start = time.time()
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Test {i+1}: Say hello"}]
    )
    end = time.time()
    print(f"  Request {i+1}: {end - start:.2f}s")

print("\nIf all requests >10s, API is likely slow/rate limited")
EOF

.venv/bin/python test_anthropic_latency.py
```

**2a. If API is fast (<5s per request):** Reduce retry logic (Option 2)
```python
# Edit src/parlant/adapters/nlp/anthropic_service.py:96-107
# Change max_attempts to 1, reduce wait_times

# Then test with 60s timeout:
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee test_fast_fail.log
```

**2b. If API is slow (>10s per request):** Wait or try later
- Check https://status.anthropic.com/
- Try again in 1-2 hours
- Consider using different API key (if rate limited)

**3. If still failing:** Increase to 300s timeout (Option 1) as last resort
```python
# parlant_inference_endpoint.py:205
response = requests.get(url, params=params, timeout=300)

# Then run:
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee test_300s_timeout.log
```

**4. If Option 1-3 all fail:** Implement Option 4 (bypass Parlant)
- Will require writing new generation script
- Can preserve Parlant format in output
- Estimate 2-3 hours to implement

---

## 🐛 Debugging Commands

### Check Parlant Server Status
```bash
# Is server running?
lsof -i:8800

# Kill zombie servers
pkill -f "python.*main.py"

# View server logs
tail -f parlant_server_debug.log
```

### Check Background Processes
```bash
# List all background generation processes
ps aux | grep generate_synthetic_conversations

# Check specific log file
tail -f test_sonnet_120s_timeout.log

# Check latest conversation output
ls -lht output/synthetic_conversations/
cat output/synthetic_conversations/conversation_1_Margaret_Chen.json
```

### Test Parlant API Directly
```bash
# Start server
.venv/bin/python main.py &

# Wait for startup
sleep 10

# Test session creation
curl -X POST http://localhost:8800/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "4QLbllmskD",
    "customer_id": "FDybuZlkyY",
    "mode": "auto"
  }'

# Send message (replace SESSION_ID)
curl -X POST http://localhost:8800/sessions/SESSION_ID/events \
  -H "Content-Type: application/json" \
  -d '{
    "source": "customer",
    "kind": "message",
    "message": "Hello, I need help with a fraudulent charge"
  }'

# Poll for response (replace SESSION_ID)
curl "http://localhost:8800/sessions/SESSION_ID/events?offset=0"
```

---

## 📝 Git Status

**Branch:** `synthetic` (from previous session)

**Uncommitted Changes:**
- `parlant_inference_endpoint.py` (timeout changes: 10s → 60s → 120s)
- Potentially other test files/logs

**Before Next Commit:**
```bash
# Review changes
git diff parlant_inference_endpoint.py

# Should commit when we have a working solution, not while debugging
# Commit message should include final timeout value that works
```

---

## 💰 Cost Estimates

### With Sonnet 3.5
**Pricing:**
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens

**Per Conversation (15 turns):**
- Parlant agent: 4 LLM calls per turn × 15 turns = 60 calls
- Persona simulation: 15 calls
- Estimated: ~$2-5 per conversation (depending on retries)

**Full 25 Conversations:**
- Total: $50-125 (optimistic to pessimistic)
- Time: 18-31 hours (if 120s+ per turn)

### With Haiku (if quality improves)
**Pricing:**
- Input: $0.80 per 1M tokens
- Output: $4 per 1M tokens

**Full 25 Conversations:**
- Total: ~$3-6
- Time: 6-10 hours
- Quality: ❌ Currently terrible (only "Oh no." responses)

---

## 📚 Key Learnings

### 1. Parlant Architecture
- Makes 4+ LLM calls per agent turn (journey selection, guideline matching, tool execution, response generation)
- Each call has retry logic (3 attempts, exponential backoff)
- STRICT mode = canned responses only
- FLUID mode = dynamic generation

### 2. Timeout Considerations
- HTTP timeout ≠ Polling timeout
- Need to account for cumulative time of all LLM calls + retries
- 120s timeout is reasonable for single LLM call, but not for 4+ calls with retries
- Parlant can take 2-5+ minutes per turn with Sonnet + retries

### 3. Cost vs Quality Tradeoff
- Haiku: Cheap (~$0.12/conversation) but terrible quality
- Sonnet: Expensive (~$2-5/conversation) and slow
- Opus: Very expensive (~$10-20/conversation), explicitly avoided

### 4. Model Selection in Parlant
- Controlled by `src/parlant/adapters/nlp/anthropic_service.py:get_schematic_generator()`
- Affects ALL Parlant agent calls (journey, guidelines, tools, response)
- Cannot mix models (e.g., Haiku for journey selection, Sonnet for response)

### 5. Polling Pattern
- Client polls GET `/sessions/{id}/events?offset=N`
- Server processes async in background
- Events arrive incrementally (customer message, then agent message)
- Need to track `last_event_offset` to avoid re-reading events

---

## 🔍 Files to Review Next Session

**High Priority:**
1. `parlant_inference_endpoint.py:168-233` - Polling logic
2. `src/parlant/adapters/nlp/anthropic_service.py:96-194` - Retry policies and generation
3. `src/parlant/core/nlp/policies.py` - Retry implementation details
4. `generate_synthetic_conversations.py:240-332` - Generation loop

**Medium Priority:**
5. `src/parlant/core/engines/alpha/` - Journey/guideline matching (to understand what's taking so long)
6. `main.py:80-130` - Agent configuration
7. `data/conversation_characters/financial_personas.yaml` - Persona details

**Low Priority:**
8. `tools.py` - Mock tool implementations (already working)
9. Test output files in `output/synthetic_conversations/`

---

## 🎬 Quick Start Commands for Next Session

### Test if Issue is Resolved
```bash
# 1. Start fresh generation with current settings
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee test_new_session.log

# 2. In another terminal, monitor progress
tail -f test_new_session.log

# 3. After 3-5 minutes, check if it succeeded
cat output/synthetic_conversations/conversation_1_Margaret_Chen.json
```

### If Still Broken - Test API Latency
```bash
# Check if Anthropic API is slow
.venv/bin/python test_anthropic_latency.py
```

### If API is Fast - Reduce Retries
```bash
# Edit retry policy
vim src/parlant/adapters/nlp/anthropic_service.py
# Change line 99: max_attempts=1

# Test again
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee test_no_retry.log
```

### If Still Failing - Nuclear Option (Bypass Parlant)
```bash
# Would need to implement new generation script
# Ask Claude to implement Option 4 from above
```

---

## 📞 Questions for User

Before starting next session, clarify:

1. **Timeout tolerance:** Are you willing to wait 5-10 minutes per conversation turn? (18-31 hours total)
2. **Quality requirements:** Is Parlant's journey/guideline intelligence critical, or can we simplify?
3. **Budget:** What's the max budget for this generation? ($50-125 for Sonnet, $3-6 for Haiku if we can fix quality)
4. **Timeline:** When do you need the 25 conversations completed?
5. **Reliability:** Is it okay to disable retries for faster generation, even if some conversations might fail?

---

## 🏁 Session Summary

**What Worked:**
- ✅ Identified timeout as critical issue
- ✅ Understood Parlant's multi-LLM-call architecture
- ✅ Tested multiple timeout values systematically
- ✅ Switched from Haiku to Sonnet for quality
- ✅ FLUID mode enables dynamic responses
- ✅ Cost reduced from $50/morning to ~$0.23/2 conversations

**What Didn't Work:**
- ❌ 10s timeout: Too short
- ❌ 60s timeout: Too short
- ❌ 120s timeout: Still too short
- ❌ Haiku quality: Only "Oh no." responses
- ❌ Sonnet with current retry logic: Takes >120s per turn

**What's Unknown:**
- ❓ Is 180s or 300s timeout sufficient?
- ❓ Is Anthropic API currently slow/rate limited?
- ❓ Can we reduce retries without breaking reliability?
- ❓ How long does Parlant actually take per turn? (exceeded all timeouts, exact time unknown)

**Next Session Priority:**
1. Test API latency to rule out API issues
2. Try reducing retry logic (Option 2)
3. If that fails, increase timeout to 300s (Option 1)
4. If that fails, consider bypassing Parlant (Option 4)

---

**End of Actions Document**
