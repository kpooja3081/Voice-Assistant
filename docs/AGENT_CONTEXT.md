# Agent Context — Lila Voice AI Project

> **Purpose:** This file gives AI coding agents full context to make changes without needing to explore the codebase first. Read this before modifying any code.

## What This Project Is

A **real-time voice AI agent** named **Lila** that makes outbound phone calls to cancer patients for periodic check-ins. Built on the **LiveKit Agents Framework v1.4.1**. The agent follows a structured 4-section protocol (symptoms → medications → wellbeing → closing) and never provides medical advice.

## Tech Stack (Exact Versions)

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | `livekit-agents` | 1.4.1 (installed), ~1.3.0 (pinned in requirements.txt) |
| STT | Sarvam AI (`saarika:v2.5`) | via `livekit-plugins-sarvam` |
| LLM | Google Gemini 2.5 Flash | via `livekit-plugins-google` |
| TTS | ElevenLabs (`eleven_turbo_v2`) | via `livekit-plugins-elevenlabs` |
| VAD | Silero | via `livekit-plugins-silero` |
| Telephony | Twilio Elastic SIP Trunk | via LiveKit SIP Bridge |
| Config | python-dotenv + dataclasses | `config.py` |
| Python | 3.13 | Windows 11 |

## Critical Files and Their Roles

### Entry Points

| File | Purpose | When to Modify |
|------|---------|---------------|
| `agent.py` | Main agent — creates pipeline, handles calls | Adding pipeline features, changing LLM, modifying session params |
| `make_call.py` | CLI to trigger outbound calls | Adding call parameters, changing dispatch logic |
| `config.py` | All environment configuration | Adding new providers or config options |

### Voice Pipeline

| File | Purpose | When to Modify |
|------|---------|---------------|
| `stt/factory.py` | STT provider factory (6 providers) | Adding new STT provider |
| `tts/factory.py` | TTS provider factory (6 providers) + ElevenLabs VoiceSettings | Adding TTS provider, tuning voice |
| `prompts/patient_support.py` | System prompt + greeting | Changing agent behavior, protocol, tone |

### Assessment Agents (NOT YET WIRED)

| File | Purpose | Status |
|------|---------|--------|
| `agents/orchestrator.py` | `AssessmentFunctions(llm.FunctionContext)` — LLM-callable tools | **Defined but NOT registered with AgentSession** |
| `agents/mental_health.py` | PHQ-2 depression screening (score 0-6) | Ready to use |
| `agents/sleep.py` | Sleep duration + quality assessment | Ready to use |
| `agents/appetite.py` | Appetite + weight loss tracking | Ready to use |
| `agents/side_effects.py` | 17 side effects × 3 severity levels + alias mapping | Ready to use |
| `agents/base.py` | `AssessmentResult`, `Severity` enum, base class | Stable |

**To wire assessment agents**, add to `agent.py`:
```python
from agents.orchestrator import AssessmentFunctions
fnc_ctx = AssessmentFunctions()
# Pass to AgentSession or register with PatientSupportAgent
```

### Data Layer

| File | Purpose |
|------|---------|
| `tools/patient_data.py` | `load_patient_context()` pre-call, `save_call_notes()` post-call |
| `data/patients/*.json` | Patient records — medications, conditions, call history |

### Unused but Present

| File | Status | Notes |
|------|--------|-------|
| `conversation/flow.py` | **Not active** | `ConversationState` machine. LLM follows prompt instead. |
| `llm/` directory | **Not active** | LLM abstraction layer. `agent.py` uses `google.LLM` directly. |

## Current agent.py Pipeline (Exact Code)

```python
# STT/TTS from factories (switchable via env)
stt = get_stt(config)      # → Sarvam STT by default
tts = get_tts(config)      # → ElevenLabs TTS with VoiceSettings
llm = google.LLM(model="gemini-2.5-flash", api_key=config.gemini.api_key)

# Session with interruption filtering
session = AgentSession(
    vad=silero.VAD.load(),
    stt=stt,
    llm=llm,
    tts=tts,
    min_interruption_duration=1.5,  # Filter coughs (<1.5s)
    min_interruption_words=3,        # Require 3+ words to interrupt
)

# Keyboard typing sound during thinking gap
background_audio = BackgroundAudioPlayer(
    thinking_sound=AudioConfig(
        source=BuiltinAudioClip.KEYBOARD_TYPING,
        volume=0.25,
    ),
)

# Session start + background audio
await session.start(room=ctx.room, agent=PatientSupportAgent(instructions=instructions))
await background_audio.start(room=ctx.room, agent_session=session)

# Greeting spoken directly (not via LLM)
await session.say(greeting)
```

## AgentSession Events (v1.4.1)

These are the CORRECT event names. Do NOT use names from older versions.

```python
EventTypes = Literal[
    "user_state_changed",        # UserStateChangedEvent(old_state, new_state)
    "agent_state_changed",       # AgentStateChangedEvent(old_state, new_state)
    "user_input_transcribed",    # UserInputTranscribedEvent
    "conversation_item_added",   # ConversationItemAddedEvent(item)
    "agent_false_interruption",  # AgentFalseInterruptionEvent(resumed)
    "function_tools_executed",   # FunctionToolsExecutedEvent
    "metrics_collected",         # MetricsCollectedEvent(metrics)
    "speech_created",            # SpeechCreatedEvent(speech_handle, user_initiated, source)
    "error",                     # ErrorEvent(error, source)
    "close",                     # CloseEvent(error, reason)
]

UserState = Literal["speaking", "listening", "away"]
AgentState = Literal["initializing", "idle", "listening", "thinking", "speaking"]
```

## ElevenLabs VoiceSettings (Current)

```python
VoiceSettings(
    stability=0.4,           # Lower = more expressive/emotional
    similarity_boost=0.75,   # Closeness to original voice
    style=0.35,              # Style exaggeration (warmth)
    use_speaker_boost=True,  # Clarity on phone audio
)
```

Parameters available: `stability`, `similarity_boost`, `style`, `speed`, `use_speaker_boost`.

## System Prompt Structure

```
SYSTEM_PROMPT = f"""
## YOUR ROLE                    ← "You are {AGENT_NAME}, a virtual patient navigator..."
## TONE & STYLE                 ← Soft, warm, one question at a time
## RESPONSE PACING (CRITICAL)   ← Always start with filler: "I see...", "Got it..."
## TTS FORMATTING               ← Ellipses for pauses, spell out acronyms
## CALL PROTOCOL
  Section 1: Symptoms & Side Effects
  Section 2: Medication Adherence
  Section 3: Wellbeing (mood, sleep, appetite)
  Section 4: Closing
## EMERGENCY PROTOCOL           ← Alert care team, end gracefully
## GUARDRAILS                   ← No medical advice, no diagnosis
## EXAMPLE RESPONSES
"""
+ load_patient_context(patient_id)  # Appended at runtime
```

## Patient Data Schema

```json
{
  "patient_id": "P001",
  "name": "Sarah Johnson",
  "age": 45,
  "medications": [
    {"name": "Toripalimab", "dose": "500mg", "frequency": "twice daily"}
  ],
  "conditions": ["Cancer"],
  "allergies": ["Penicillin"],
  "provider": "Dr. Emily Carter",
  "last_call": "2026-02-12T13:06:29.944",
  "call_history": [
    {
      "date": "2026-02-12T...",
      "transcript": ["assistant: Hello...", "user: Yes, I can talk."]
    }
  ]
}
```

## Known Issues and Gotchas

### Gemini Latency
- TTFT (time to first token) varies **7-20 seconds**
- The `AFC is enabled with max remote calls: 10` log is normal (Google GenAI SDK)
- `preemptive_generation=True` causes Gemini to **hang and never respond** — DO NOT USE
- `false_interruption_timeout` and `resume_false_interruption` parameters may cause issues — currently not set (framework uses defaults)

### Windows Dev
- Hot reload (`python agent.py dev`) produces `DuplexClosed` errors on restart — these are harmless
- IPC errors during reload are normal on Windows with `IocpProactor`

### Sarvam STT
- Transcribes Hindi-English code-switching well
- Sometimes produces empty transcripts for very short utterances
- WebSocket connection can close after ~2-3 minutes of silence (reconnects automatically)

### ElevenLabs TTS
- `eleven_turbo_v2` model is fast but lower quality than `eleven_multilingual_v2`
- Voice ID `21m00Tcm4TlvDq8ikWAM` is "Rachel" — warm, professional
- VoiceSettings with low stability can produce inconsistent output at sentence boundaries

### Interruption Handling
- `min_interruption_duration=1.5` works well for phone calls
- Without it, phone line noise/coughs constantly interrupt the agent
- The agent uses default `false_interruption_timeout=2.0` and resumes automatically

## Project File Tree

```
VOICE/
├── agent.py                   # MAIN: Pipeline wiring, call handling, event logging
├── make_call.py               # CLI: Dispatch agent + dial phone
├── config.py                  # Config from env vars (dataclasses)
├── setup_sip_trunk.py         # Interactive SIP trunk setup
├── test_twilio_sip.py         # SIP integration tests
├── test_elevenlabs.py         # ElevenLabs TTS test
├── requirements.txt           # Dependencies (livekit-agents~=1.3.0)
│
├── prompts/
│   ├── __init__.py            # Exports: SYSTEM_PROMPT, get_initial_greeting
│   └── patient_support.py     # Full system prompt + greeting function
│
├── stt/
│   ├── __init__.py            # Exports: get_stt
│   └── factory.py             # STT factory: sarvam|deepgram|openai|google|azure|assemblyai
│
├── tts/
│   ├── __init__.py            # Exports: get_tts
│   └── factory.py             # TTS factory: elevenlabs|deepgram|openai|google|azure|cartesia
│                              #   + ElevenLabs VoiceSettings (stability, style, etc.)
│
├── agents/
│   ├── __init__.py
│   ├── base.py                # AssessmentResult, Severity, AssessmentAgent base
│   ├── orchestrator.py        # AssessmentFunctions(llm.FunctionContext) — NOT WIRED YET
│   ├── mental_health.py       # PHQ-2 (score 0-6, flag ≥3)
│   ├── sleep.py               # Duration + quality + problem type
│   ├── appetite.py            # Appetite + weight loss % (flag >5%)
│   └── side_effects.py        # 17 effects × severity matrix + 46 aliases
│
├── tools/
│   ├── __init__.py            # Exports: load_patient_context, save_call_notes
│   └── patient_data.py        # Pre-load patient JSON, save transcripts post-call
│
├── conversation/
│   ├── __init__.py
│   └── flow.py                # ConversationState machine — NOT ACTIVE
│
├── llm/                       # LLM abstraction — NOT ACTIVE (agent.py uses plugin directly)
│   ├── __init__.py
│   ├── base.py
│   ├── azure_openai.py
│   ├── gemini.py
│   └── factory.py
│
├── data/patients/
│   └── sample_patient.json    # P001 — Sarah Johnson
│
└── docs/
    ├── ARCHITECTURE.md         # System architecture deep-dive
    ├── USAGE.md                # Technical how-to guide
    ├── SELF_HOSTED_ROADMAP.md  # Self-hosted LiveKit migration plan
    └── AGENT_CONTEXT.md        # THIS FILE — AI agent context
```

## Common Tasks for Future Agents

### "Add a new assessment agent"
1. Create `agents/new_agent.py` extending `AssessmentAgent`
2. Add tool function in `agents/orchestrator.py`
3. Wire `AssessmentFunctions` into `agent.py` AgentSession

### "Switch LLM to GPT-4o"
1. In `agent.py`, replace `google.LLM(...)` with `openai.LLM(model="gpt-4o", ...)`
2. Update imports: `from livekit.plugins import openai`
3. Ensure `OPENAI_API_KEY` is set in `.env`

### "Add a new STT/TTS provider"
1. Add enum value in `config.py` (`STTProvider` or `TTSProvider`)
2. Add config dataclass if needed
3. Add case in `stt/factory.py` or `tts/factory.py`
4. Add env vars in `.env.example`

### "Change the conversation protocol"
1. Edit `prompts/patient_support.py` → `CALL PROTOCOL` section
2. No code changes needed — the LLM follows the prompt

### "Wire assessment agents into the session"
1. In `agent.py`, import `AssessmentFunctions` from `agents.orchestrator`
2. Create instance: `fnc_ctx = AssessmentFunctions()`
3. Pass to Agent or AgentSession (check v1.4.1 API for exact parameter)
4. The LLM will automatically call tool functions when it has enough info

### "Add multilingual support"
1. Change `SARVAM_LANGUAGE` env var for STT
2. Add language param to ElevenLabs TTS in `tts/factory.py`
3. Optionally translate the system prompt in `prompts/patient_support.py`

### "Reduce latency"
1. Switch TTS to `cartesia` (ultra low latency) or `deepgram`
2. Strengthen filler phrases in prompt (RESPONSE PACING section)
3. Increase BackgroundAudioPlayer volume for better perceived fill
4. DO NOT enable `preemptive_generation=True` — it breaks Gemini
5. Consider switching LLM to a faster provider if Gemini TTFT is too high

### "Deploy to production"
1. See `docs/SELF_HOSTED_ROADMAP.md` for full migration plan
2. Change `python agent.py dev` → `python agent.py start`
3. Remove debug `[PIPELINE]` event listeners from `agent.py` if not needed
4. Set proper `LIVEKIT_API_KEY`/`SECRET` (not devkey)
