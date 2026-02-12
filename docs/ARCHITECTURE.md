# Architecture — Lila Patient Support Voice Agent

## System Overview

Lila is a real-time voice AI agent that makes outbound phone calls to cancer patients for periodic check-ins. It uses a streaming pipeline where each component processes data as it arrives, minimizing end-to-end latency.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              LiveKit Cloud                                       │
│                                                                                  │
│   ┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│   │  Sarvam /   │     │   Google      │     │  ElevenLabs  │     │  Patient   │  │
│   │  Deepgram   │────>│   Gemini      │────>│   TTS        │────>│  (Phone/   │  │
│   │  STT        │<────│   2.5 Flash   │<────│              │<────│   WebRTC)  │  │
│   └─────────────┘     └──────────────┘     └──────────────┘     └────────────┘  │
│         ^                    ^                                        |          │
│         |                    |                                        v          │
│   ┌─────────────┐     ┌──────────────┐                        ┌────────────┐    │
│   │  Silero VAD │     │  Background  │                        │ Twilio SIP │    │
│   │  (activity  │     │  Audio Player│                        │ Trunk      │    │
│   │   detect)   │     │  (typing snd)│                        │ (PSTN)     │    │
│   └─────────────┘     └──────────────┘                        └────────────┘    │
│                                                                                  │
│   AgentSession: min_interruption_duration=1.5, min_interruption_words=3          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Outbound Call (Primary Use Case)

```
1. make_call.py
   ├── Creates LiveKit room via API
   └── Dispatches agent with metadata: {phone_number, patient_id}

2. LiveKit Cloud
   └── Assigns job to running agent.py worker

3. agent.py (entrypoint)
   ├── Parses job metadata → gets phone_number + patient_id
   ├── load_patient_context(patient_id) → injects into system prompt
   ├── Connects to LiveKit room
   ├── Dials phone via ctx.api.sip.create_sip_participant()
   │   └── LiveKit SIP Bridge → Twilio Elastic SIP Trunk → PSTN → Patient phone
   ├── Waits for participant to join (patient picks up)
   ├── Creates pipeline: VAD + STT + LLM + TTS
   ├── Starts AgentSession + BackgroundAudioPlayer
   └── Speaks initial greeting via session.say()

4. Real-time conversation loop (managed by AgentSession)
   ├── Patient speaks → Silero VAD detects speech
   ├── Audio → STT (Sarvam/Deepgram) → text transcript
   ├── Transcript → LLM (Gemini 2.5 Flash) → response text (streaming)
   ├── Response → TTS (ElevenLabs) → audio → Patient hears response
   └── During "thinking" gap: BackgroundAudioPlayer plays typing sound

5. Call ends (patient hangs up)
   ├── participant_disconnected event fires
   ├── save_call_notes() → appends transcript to patient JSON
   └── Session closes
```

### Inbound Call (WebRTC)

```
1. Patient opens LiveKit Playground in browser
2. LiveKit auto-dispatches agent (agent_name="patient-support-agent")
3. Same pipeline as outbound, minus the SIP dialing step
```

## Component Architecture

### Core Pipeline (`agent.py`)

The main orchestrator. Creates and wires all components:

| Component | Implementation | Role |
|-----------|---------------|------|
| `PatientSupportAgent` | Extends `livekit.agents.voice.Agent` | Holds system prompt (instructions) |
| `AgentSession` | LiveKit framework | Manages the VAD→STT→LLM→TTS loop |
| `BackgroundAudioPlayer` | LiveKit built-in | Plays typing sound during thinking state |

**AgentSession State Machine:**
```
initializing → listening → thinking → speaking → listening → ...
                                ↑                      |
                                └──────────────────────┘
```

**Interruption Handling:**
- `min_interruption_duration=1.5s` — ignores sounds shorter than 1.5s (coughs, "hmm")
- `min_interruption_words=3` — requires 3+ transcribed words to count as interruption
- If false interruption detected → agent resumes from where it left off

### Prompt System (`prompts/patient_support.py`)

Single system prompt with structured sections:

```
SYSTEM_PROMPT = f"""
  ## YOUR ROLE          ← Identity and boundaries
  ## TONE & STYLE       ← Voice personality
  ## RESPONSE PACING    ← Filler phrases for latency reduction
  ## TTS FORMATTING     ← Rules for spoken output (ellipses, no abbreviations)
  ## CALL PROTOCOL      ← 4-section check-in flow
    Section 1: Symptoms & Side Effects
    Section 2: Medication Adherence
    Section 3: Wellbeing (mood, sleep, appetite)
    Section 4: Closing & Next Steps
  ## EMERGENCY PROTOCOL ← Urgent care escalation
  ## GUARDRAILS         ← What agent must never do
"""
```

Patient context is appended at runtime:
```
instructions = SYSTEM_PROMPT + load_patient_context(patient_id)
```

### Provider Factories (`stt/factory.py`, `tts/factory.py`)

Factory pattern — switch providers via env vars without code changes:

| Factory | Providers | Default | Selection |
|---------|-----------|---------|-----------|
| `get_stt(config)` | Sarvam, Deepgram, OpenAI, Google, Azure, AssemblyAI | Deepgram | `STT_PROVIDER` env |
| `get_tts(config)` | ElevenLabs, Deepgram, OpenAI, Google, Azure, Cartesia | Deepgram | `TTS_PROVIDER` env |

**ElevenLabs Voice Settings** (tuned for warm, empathetic delivery):
```python
VoiceSettings(
    stability=0.4,           # More expressive emotional range
    similarity_boost=0.75,   # True to original voice
    style=0.35,              # Moderate warmth exaggeration
    use_speaker_boost=True,  # Clearer on phone
)
```

### Assessment Agents (`agents/`)

Tool functions that the LLM can invoke via function calling (not yet wired into AgentSession):

| Agent | What It Does | Trigger |
|-------|-------------|---------|
| `assess_mental_health` | PHQ-2 depression screening (score 0-6, flag ≥3) | After both PHQ-2 questions answered |
| `assess_sleep` | Sleep duration + quality + problem type | After sleep questions answered |
| `assess_appetite` | Appetite + weight loss % (flag >5%) | After appetite questions answered |
| `assess_side_effect` | 17 side effects × 3 severity levels | For each reported side effect |

Architecture:
```
agents/
├── base.py           ← AssessmentResult, Severity enum
├── mental_health.py  ← PHQ-2 scoring
├── sleep.py          ← Duration + quality assessment
├── appetite.py       ← Weight loss flagging
├── side_effects.py   ← 17 side effects × severity matrix + aliases
└── orchestrator.py   ← AssessmentFunctions (llm.FunctionContext)
                        Registers all agents as LLM-callable tools
```

### Patient Data (`tools/patient_data.py`, `data/patients/`)

**Pre-call:** `load_patient_context()` reads patient JSON and formats it for the system prompt. Includes name, medications, conditions, allergies, provider, and last 3 call summaries.

**Post-call:** `save_call_notes()` extracts the conversation transcript from `session.history` and appends it to the patient's `call_history` array.

```json
{
  "patient_id": "P001",
  "name": "Sarah Johnson",
  "medications": [{"name": "Toripalimab", "dose": "500mg", "frequency": "twice daily"}],
  "conditions": ["Cancer"],
  "call_history": [
    {"date": "2026-02-12T...", "transcript": ["assistant: ...", "user: ..."]}
  ]
}
```

### Configuration (`config.py`)

Dataclass-based config loaded from env vars at startup:

```python
config = Config.from_env()  # Global singleton
```

Key config groups: `LiveKitConfig`, `ElevenLabsConfig`, `DeepgramConfig`, `GeminiConfig`, `SarvamConfig`, etc.

### Conversation Flow (`conversation/flow.py`)

Defines a `ConversationState` machine with stages (GREETING → IDENTITY_VERIFICATION → MEDICATION_ADHERENCE → ... → CLOSING). Currently **not wired** into agent.py — the LLM follows the protocol from the system prompt instead.

### Latency Reduction

Three layers work together:

| Layer | Where | Latency Saved |
|-------|-------|--------------|
| Background typing sound | `BackgroundAudioPlayer` in agent.py | Fills silence immediately (~0ms) |
| Filler phrases | Prompt instructs "always start with 'I see...'" | LLM first tokens in ~100ms, TTS synthesis ~300ms |
| Short responses | Prompt says "1-3 sentences max" | Less generation time from LLM |

### Debug Logging

Pipeline events (v1.4.1 event names):
```
agent_state_changed    → tracks: listening → thinking → speaking
user_state_changed     → tracks: listening → speaking → away
user_input_transcribed → raw STT output
speech_created         → agent starting to speak (source: say/generate_reply)
conversation_item_added → committed messages (role + text)
error                  → LLM/STT/TTS errors
agent_false_interruption → noise that was correctly filtered
close                  → session teardown reason
```

## File Map

```
VOICE/
├── agent.py                  # Main entrypoint — pipeline wiring + call handling
├── make_call.py              # CLI: dispatch agent + dial phone number
├── config.py                 # Env-based configuration (all providers)
├── setup_sip_trunk.py        # Interactive: create LiveKit outbound SIP trunk
├── test_twilio_sip.py        # Test suite: env, LiveKit, SIP, real call
├── test_elevenlabs.py        # ElevenLabs TTS test
├── requirements.txt          # Python dependencies
│
├── prompts/
│   ├── __init__.py
│   └── patient_support.py    # System prompt + greeting function
│
├── stt/
│   ├── __init__.py
│   └── factory.py            # STT provider factory (6 providers)
│
├── tts/
│   ├── __init__.py
│   └── factory.py            # TTS provider factory (6 providers) + ElevenLabs voice settings
│
├── agents/
│   ├── __init__.py
│   ├── base.py               # AssessmentResult, Severity, base class
│   ├── orchestrator.py       # LLM-callable tool functions (FunctionContext)
│   ├── mental_health.py      # PHQ-2 depression screening
│   ├── sleep.py              # Sleep assessment
│   ├── appetite.py           # Appetite + weight loss
│   └── side_effects.py       # 17 side effects × severity matrix
│
├── tools/
│   ├── __init__.py
│   └── patient_data.py       # Load patient context / save transcripts
│
├── conversation/
│   ├── __init__.py
│   └── flow.py               # ConversationState machine (not active)
│
├── llm/
│   ├── __init__.py
│   ├── base.py               # LLM abstraction base
│   ├── azure_openai.py       # Azure OpenAI wrapper
│   ├── gemini.py             # Gemini wrapper
│   └── factory.py            # LLM factory (not active — agent.py uses plugin directly)
│
├── data/patients/
│   └── sample_patient.json   # Patient records + call history
│
└── docs/
    ├── ARCHITECTURE.md        # This file
    ├── USAGE.md               # Technical usage guide
    ├── SELF_HOSTED_ROADMAP.md # Self-hosted LiveKit roadmap
    └── AGENT_CONTEXT.md       # Full context for AI agents
```
