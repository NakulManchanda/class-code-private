# Class 9b — Open WebUI Sample Sessions

**Your models in Open WebUI:**
- `Qwen/Qwen2.5-3B-Instruct` (text model) — GPU A (text-0)
- `Qwen/Qwen2.5-VL-3B-Instruct` (vision model) — GPU B (vision-0)

---

## 🎨 Open WebUI Interface

**URL:** `http://127.0.0.1:30030`

**Left sidebar:**
```
🏠 Home
💬 New Chat
🔍 Search
📝 Notes
🗂️ Workspace
  └─ Models (2 available)
  └─ Knowledge (0)
  └─ Prompts (0)
  └─ Skills (0)
  └─ Tools (0)
```

**Top bar:**
```
[Open WebUI Logo]
Models 2    Knowledge 0    Prompts 0    Skills 0    Tools 0
                          All ▼    Actions ▼
```

---

## 📊 Models Tab (Fixed Display)

**Current (broken):**
```
Search Models: [_______]

No models found
Try adjusting your search or filter to find what you are looking for.
```

**What it should show (with proper API formatting):**
```
Search Models: [_______]

Available Models (2)

┌─────────────────────────────────┐
│ 📄 Qwen2.5-3B-Instruct (text)   │
│ Type: Text Generation           │
│ Provider: Local                 │
│ Status: Ready                   │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 🖼️  Qwen2.5-VL-3B (vision)      │
│ Type: Vision + Text             │
│ Provider: Local                 │
│ Status: Ready                   │
└─────────────────────────────────┘
```

---

## 💬 Sample Session 1: Text Chat

**Screenshot flow:**

### Step 1: New Chat
```
┌──────────────────────────────────────────────────────┐
│ Open WebUI                               All ▼      │
├──────────────────────────────────────────────────────┤
│                                                       │
│ [Model Selector: Qwen2.5-3B-Instruct ▼]            │
│                                                       │
│ ┌────────────────────────────────────────────────┐  │
│ │ Hello! What can I help you with today?         │  │
│ │                                                 │  │
│ │ [Assistant message - waiting for user input]   │  │
│ └────────────────────────────────────────────────┘  │
│                                                       │
│ User: [Write a haiku about GPUs              ] [→] │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Step 2: Text Request Processing

**Behind the scenes (gateway flow):**
```
User types in Open WebUI
    ↓
Open WebUI sends: POST /v1/chat/completions
  {
    "model": "Qwen/Qwen2.5-3B-Instruct",
    "messages": [{"role": "user", "content": "Write a haiku about GPUs"}]
  }
    ↓
Gateway admission check
  - ADMIT ok (tokens available)
  - BIND text → text pool
  - PLACE text-0 (prefill pod)
    ↓
vLLM prefill generates KV cache
    ↓
Mooncake stores KV block
    ↓
Request routed to decode pod
    ↓
vLLM decode generates response
    ↓
Response streamed back to Open WebUI
```

### Step 3: AI Response

```
┌──────────────────────────────────────────────────────┐
│ Open WebUI                               All ▼      │
├──────────────────────────────────────────────────────┤
│                                                       │
│ [Model Selector: Qwen2.5-3B-Instruct ▼]            │
│                                                       │
│ User: Write a haiku about GPUs                       │
│                                                       │
│ ┌────────────────────────────────────────────────┐  │
│ │ Parallel pathways,                             │  │
│ │ Silicon rivers flow fast,                      │  │
│ │ Data dreams take flight.                       │  │
│ │                                                 │  │
│ │ [timestamp: 1.2s]                              │  │
│ └────────────────────────────────────────────────┘  │
│                                                       │
│ User: [Tell me about KV cache] [→]                  │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**What happened:**
- ✅ Gateway: ADMIT ok
- ✅ Router: PLACE text-0 (prefill) → text-0 (decode)
- ✅ KV Transfer: 16 tokens hopped via Mooncake
- ✅ Latency: 1.2s (gateway + pick + local)
- ✅ Status: 200 (success, local)

---

## 🖼️ Sample Session 2: Vision Chat

### Step 1: Attach Image + Send

```
┌──────────────────────────────────────────────────────┐
│ Open WebUI                               All ▼      │
├──────────────────────────────────────────────────────┤
│                                                       │
│ [Model Selector: Qwen2.5-VL-3B ▼]                  │
│                                                       │
│ User: [image preview: GPU_photo.jpg]                │
│       What's in this image?                          │
│                                                       │
│ ┌────────────────────────────────────────────────┐  │
│ │ This appears to be an NVIDIA GPU with...       │  │
│ │ [streaming response...]                         │  │
│ │                                                 │  │
│ │ [timestamp: 2.1s]                              │  │
│ └────────────────────────────────────────────────┘  │
│                                                       │
│ User: [Attach file...] [What else? ] [→]           │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**Behind the scenes:**
```
User attaches image + types prompt
    ↓
Open WebUI sends: POST /v1/chat/completions
  {
    "model": "Qwen/Qwen2.5-VL-3B-Instruct",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "image_url", "image_url": "data:image/png;base64,..."},
          {"type": "text", "text": "What's in this image?"}
        ]
      }
    ]
  }
    ↓
Gateway admission
  - ADMIT ok
  - BIND vision → vision pool
  - PLACE vision-0
    ↓
vLLM vision model processes image + text
    ↓
Response returned
    ↓
Open WebUI displays in chat
```

**What happened:**
- ✅ Gateway: ADMIT ok
- ✅ Router: PLACE vision-0 (vision-only pod)
- ✅ No KV hop (vision model handles both prefill + decode)
- ✅ Latency: 2.1s (vision processing is slower)
- ✅ Status: 200 (success, local)

---

## 🔄 Sample Session 3: Multi-Turn Conversation

```
┌──────────────────────────────────────────────────────┐
│ Open WebUI                               All ▼      │
├──────────────────────────────────────────────────────┤
│ [Model: Qwen2.5-3B-Instruct]                        │
│                                                       │
│ User:    What is a GPU?                             │
│ Bot:     A GPU is a graphics processor...           │
│          [1.2s] [200/local/text-0]                   │
│                                                       │
│ User:    What makes it different from a CPU?        │
│ Bot:     The key differences are...                 │
│          [1.1s] [200/local/text-0]                   │
│                                                       │
│ User:    Can GPUs be used for AI?                   │
│ Bot:     Absolutely! GPUs are excellent for...      │
│          [1.3s] [200/local/text-0]                   │
│          [kv_hop: prefill→decode]                    │
│                                                       │
│ User: [Follow-up question...] [→]                   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**What's happening:**
- Turn 1: Request 1 → text-0 (prefill) → text-0 (decode)
- Turn 2: Request 2 → text-0 (prefill) → text-0 (decode)
- Turn 3: Request 3 → text-0 (prefill) → text-0 (decode) + **KV HOP!**
  - Prefill generates new KV for "Can GPUs be used for AI?"
  - Mooncake stores the KV block
  - Decode pod retrieves and reuses previous context KV
  - Result: Faster response (reusing cached tokens)

---

## 📈 What Metrics Show During Session

**After text chat (3 messages):**
```
From REPL: lab> metrics

orch_requests_total 3
orch_completed_total 3
orch_pick_total 3
orch_place_total{capability="text"} 3
orch_kv_transfer_total 1            ← 1 KV hop (turn 3)
orch_kv_transfer_tokens 47          ← 47 tokens transferred
orch_request_duration_seconds_sum{stage="e2e"} 3.6s  ← 1.2s + 1.1s + 1.3s
```

**From Grafana Mooncake dashboard:**
```
Hops: 1
Hop tokens: 47
Blocks in store: 1
Router KV transfers: Activity spike visible
```

---

## 🎯 Typical Open WebUI Workflows

### Workflow 1: Text-Only Chat
```
1. Select "Qwen2.5-3B-Instruct" from model selector
2. Type prompt
3. Hit Enter or [→] button
4. Response streams into chat
5. Type follow-up (reuses KV cache with hop)
6. Repeat
```

**Routing:** Text requests → text-0 (prefill) → text-0 (decode)

### Workflow 2: Vision Analysis
```
1. Select "Qwen2.5-VL-3B" from model selector
2. Click [📎 Attach] to upload image
3. Type question about image
4. Hit Enter
5. AI analyzes image + generates response
```

**Routing:** Vision requests → vision-0 (both prefill + decode)

### Workflow 3: Mixed Session
```
1. Chat about GPUs (text model)
2. Switch to vision model
3. Upload GPU photo
4. Ask "Is this the same GPU we discussed?"
5. Switch back to text
6. Continue text conversation
```

**Routing:** Switches between text-0 and vision-0 as model changes

---

## 🚨 Error Cases in Open WebUI

### Audio Request (Not Supported Locally)
```
User: [Attach audio.mp3] Transcribe this

⚠️  Open WebUI:
"This model doesn't support audio.
Please try a text or vision model."

Behind scenes:
- Gateway admits request ✓
- Router checks: vision model ≠ audio model
- Gateway: "503 no eligible pod"
- Overflow: Sends to Superlinked
- Superlinked: Returns transcription
- Open WebUI displays result
```

### Overload (Pod Saturated)
```
User types very fast, queue builds up

⚠️  Open WebUI:
"Server busy. Retrying... (429)"

Behind scenes:
- Too many tokens in flight
- Gateway: "429 admission cap"
- Open WebUI client waits/retries
- Once pod frees up, request goes through
```

### Pod Crash (Rare)
```
User sends request, pod dies

⚠️  Open WebUI:
"Connection failed. Trying backup service..."

Behind scenes:
- Local pod down: "503 no eligible pod"
- Gateway: Routes to Superlinked overflow
- Superlinked processes request
- Open WebUI receives response from backup
```

---

## 📊 Open WebUI → Gateway Request Format

**What Open WebUI actually sends:**

```json
POST http://127.0.0.1:8080/v1/chat/completions

{
  "model": "Qwen/Qwen2.5-3B-Instruct",
  "messages": [
    {
      "role": "user",
      "content": "Write a haiku about GPUs"
    }
  ],
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 100,
  "stream": true
}
```

**What gateway receives:**
```
Request {
  model: "Qwen/Qwen2.5-3B-Instruct"
  capability: "text"
  tokens: 37 (input + max_tokens estimate)
}
```

**Gateway processing:**
```
1. ADMIT: Check tenant tokens (OK)
2. BIND: Map to text capability
3. PLACE: Find text-0 pod
4. ROUTE: Send to vLLM
5. RESPONSE: Stream back to Open WebUI
```

---

## 🎓 Key Takeaways

| Layer | What Open WebUI Sees | What's Happening |
|-------|---------------------|------------------|
| **UI** | Chat interface | User types naturally |
| **Gateway** | /v1/chat/completions | Admission + routing |
| **Router** | Worker pools (text/vision) | Pod placement |
| **KV** | Transparent | Mooncake caching behind scenes |
| **Device** | Pod health | HAMi slicing GPU |
| **Scaling** | Response time | KEDA adjusts replicas |

**From user's perspective:** Just a ChatGPT-like chat.

**From system's perspective:** Five-plane architecture orchestrating everything!

---

## 🚀 How to Test This

**Terminal 1: Port forward Grafana**
```bash
kubectl port-forward svc/grafana 31495:80
```

**Terminal 2: Keep REPL open**
```bash
make repl
lab> metrics
# Watch metrics update as you use Open WebUI
```

**Browser:**
1. Open http://127.0.0.1:30030 (Open WebUI)
2. Chat naturally
3. In another tab: http://127.0.0.1:31495 (Grafana)
4. Watch Mooncake dashboard update in real-time!
5. Back to REPL: `lab> board` to see routing decisions

---

**Open WebUI is the friendly face on your distributed LLM system!** 🎨✨
