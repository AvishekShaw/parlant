# Quick Reference - Synthetic Conversation Generation

**Last Updated:** November 7, 2025
**Status:** ⚠️ BLOCKED ON TIMEOUTS (120s timeout still failing)

---

## 🚀 Most Common Commands

### Start Fresh Test
```bash
.venv/bin/python generate_synthetic_conversations.py 2>&1 | tee test_$(date +%Y%m%d_%H%M%S).log
```

### Monitor Progress
```bash
# In separate terminal
tail -f test_*.log | grep -E "(✓|✗|→|ℹ)"
```

### Check API Latency (FIRST THING TO TRY)
```bash
.venv/bin/python test_anthropic_latency.py
```

### Kill Zombie Servers
```bash
pkill -f "python.*main.py"
lsof -i:8800  # Verify port is free
```

### Check Latest Output
```bash
ls -lht output/synthetic_conversations/
cat output/synthetic_conversations/conversation_1_*.json | jq .
```

---

## 📁 Critical Files

| File | Purpose | Key Line(s) |
|------|---------|-------------|
| `parlant_inference_endpoint.py` | HTTP timeout settings | Line 205 (GET), 127/160 (POST) |
| `src/parlant/adapters/nlp/anthropic_service.py` | Model selection | Line 275 (Sonnet/Haiku) |
| `main.py` | Composition mode | Line 106 (FLUID/STRICT) |
| `generate_synthetic_conversations.py` | Generation config | Line 238 (persona count) |
| `ACTIONS.md` | Full context document | All options and details |

---

## ⚙️ Current Configuration

```
Parlant Agent Model:  Claude Sonnet 3.5
Persona Model:        Claude Haiku
HTTP GET Timeout:     120s  ⚠️ STILL FAILING
HTTP POST Timeout:    180s
Overall Timeout:      300s
Composition Mode:     FLUID
Test Personas:        1 (Margaret Chen)
```

---

## 🔧 Quick Fixes

### Change Timeout (parlant_inference_endpoint.py:205)
```python
response = requests.get(url, params=params, timeout=300)  # Try 300s
```

### Change Model (src/parlant/adapters/nlp/anthropic_service.py:275)
```python
# For Haiku (cheap but poor quality):
return Claude_Haiku_3_5[t](self._logger, self._meter)

# For Sonnet (expensive, slow, timing out):
return Claude_Sonnet_3_5[t](self._logger, self._meter)
```

### Change Persona Count (generate_synthetic_conversations.py:238)
```python
return data['users'][:1]   # Test with 1
return data['users'][:5]   # Test with 5
return data['users']       # Full 25
```

### Disable Retries (src/parlant/adapters/nlp/anthropic_service.py:96-107)
```python
# Comment out the @policy decorator:
# @policy([
#     retry(...),
#     retry(...),
# ])
async def do_generate(...):
```

---

## 📊 Test Results Tracker

| Date | Model | Timeout | Result | Log File |
|------|-------|---------|--------|----------|
| Nov 7 | Haiku | 10s | Poor quality | test_2_conversations.log |
| Nov 7 | Sonnet | 10s | Timeout ❌ | test_sonnet_1_conversation.log |
| Nov 7 | Sonnet | 60s | Timeout ❌ | test_sonnet_retry.log |
| Nov 7 | Sonnet | 120s | Timeout ❌ | test_sonnet_120s_timeout.log |
| _____ | ______ | _____ | _________ | _________________________ |

---

## 🎯 Decision Tree

```
START
  |
  └─> Run test_anthropic_latency.py
       |
       ├─> API fast (<5s)?
       |    └─> Reduce retry logic (Option 2 in ACTIONS.md)
       |
       ├─> API moderate (5-10s)?
       |    └─> Increase timeout to 180s-300s (Option 1)
       |
       └─> API slow (>10s)?
            └─> Check status.anthropic.com
                 └─> Wait 1-2 hours and retry
                      └─> If still slow, bypass Parlant (Option 4)
```

---

## 💡 Key Insights

1. **Parlant makes 4+ LLM calls per turn** (journey, guidelines, tools, response)
2. **Each call has 3-attempt retry** with exponential backoff (1s, 2s, 4s, 8s...)
3. **120s timeout is insufficient** for Sonnet with retries
4. **Haiku is too weak** - produces only "Oh no." responses
5. **FLUID mode required** - STRICT only gives canned responses
6. **Cost with Sonnet:** ~$2-5 per conversation = $50-125 for 25
7. **Time with Sonnet:** 120s+ per turn = 18-31 hours for 25 conversations

---

## 🆘 Emergency Contacts

- **Anthropic Status:** https://status.anthropic.com/
- **Parlant Docs:** https://docs.parlant.io/
- **This Project:** /Users/egregious/Code/parlant/

---

## 📝 Next Session Checklist

- [ ] Read ACTIONS.md for full context
- [ ] Run test_anthropic_latency.py
- [ ] Check if port 8800 is free
- [ ] Review latest log files
- [ ] Check git status (branch: synthetic)
- [ ] Decide on Option 1, 2, 3, or 4 from ACTIONS.md

---

**See ACTIONS.md for detailed options and implementation guides.**
