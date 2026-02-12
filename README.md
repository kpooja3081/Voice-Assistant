# Lila - Patient Support Voice Agent

An AI-powered voice agent built with LiveKit that makes outbound phone calls to cancer patients for periodic check-ins — covering medication adherence, side effect reporting, and general well-being.

## How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LiveKit Voice Pipeline                             │
│                                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Sarvam/  │    │   Gemini     │    │  ElevenLabs  │    │   Patient    │  │
│  │ Deepgram │───>│   2.5 Flash  │───>│   TTS        │───>│  (Phone/    │  │
│  │   STT    │<───│   LLM        │<───│              │<───│   WebRTC)   │  │
│  └──────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                                             │
│  Silero VAD handles: Interruption, Turn-taking, Silence detection           │
│  BackgroundAudioPlayer: Thinking sound fills silence during LLM generation  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │  Twilio SIP Trunk   │
                          │  (PSTN Gateway)     │
                          └─────────┬──────────┘
                                    │
                              Patient Phone
```

## Features

- **Outbound phone calls** via Twilio Elastic SIP Trunking
- **Inbound calls** via WebRTC (LiveKit Playground)
- **Modular STT/TTS** — 6+ providers each, switchable via env vars
- **Patient context pre-loading** — zero latency impact on calls
- **Low-latency responses** — three-layer approach: background thinking sound, LLM filler phrases, and preemptive generation
- **Smart interruption handling** — filters coughs/noise (requires 1.5s + 3 words), resumes on false interruptions
- **Assessment agents** — PHQ-2 mental health, sleep, appetite, side effects with severity scoring
- **Auto-save transcripts** — conversation saved to patient JSON on disconnect
- **Strict guardrails** — agent never provides medical advice or discusses unrelated topics

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Voice Pipeline | LiveKit Agents v1.3+ | Handles VAD, turn-taking, interruption |
| STT | Sarvam / Deepgram / OpenAI / Google / Azure / AssemblyAI | Switchable via `STT_PROVIDER` |
| TTS | ElevenLabs / Deepgram / OpenAI / Google / Azure / Cartesia | Switchable via `TTS_PROVIDER` |
| LLM | Google Gemini 2.5 Flash | Via LiveKit plugin |
| VAD | Silero | Voice Activity Detection |
| Telephony | Twilio Elastic SIP Trunk + LiveKit SIP Bridge | Outbound PSTN calls |

## Project Structure

```
VOICE/
├── agent.py                  # Main agent — handles inbound + outbound calls
├── make_call.py              # Trigger outbound call to a phone number
├── setup_sip_trunk.py        # Interactive: create LiveKit outbound SIP trunk
├── test_twilio_sip.py        # Test suite: env, LiveKit, SIP trunk, real call
├── config.py                 # Environment config via dataclasses
│
├── prompts/
│   └── patient_support.py    # System prompt with 4-section check-in protocol
│
├── conversation/
│   └── flow.py               # Conversation state machine (stages, tracking)
│
├── agents/                   # Assessment agents (tool functions for LLM)
│   ├── orchestrator.py       # Registers agents as LLM-callable tools
│   ├── mental_health.py      # PHQ-2 depression screening
│   ├── sleep.py              # Sleep quality + duration assessment
│   ├── appetite.py           # Appetite + weight loss tracking
│   └── side_effects.py       # 17 side effects with severity matrix
│
├── tools/
│   └── patient_data.py       # Pre-load patient context, save transcripts
│
├── stt/
│   └── factory.py            # STT provider factory (6 providers)
│
├── tts/
│   └── factory.py            # TTS provider factory (6 providers)
│
├── llm/                      # LLM abstraction (Azure/Gemini) — not active
│   ├── base.py
│   ├── azure_openai.py
│   ├── gemini.py
│   └── factory.py
│
├── data/patients/
│   └── sample_patient.json   # Patient records + call history
│
├── .env                      # Your credentials (DO NOT commit)
├── .env.example              # Template for env vars
└── requirements.txt          # Python dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Fill in your API keys in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `LIVEKIT_URL` | Yes | LiveKit server URL (`wss://...livekit.cloud`) |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret |
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `DEEPGRAM_API_KEY` | Yes (if STT=deepgram) | Deepgram API key |
| `ELEVENLABS_API_KEY` | Yes (if TTS=elevenlabs) | ElevenLabs API key |
| `SARVAM_API_KEY` | Yes (if STT=sarvam) | Sarvam AI API key |
| `STT_PROVIDER` | No | `deepgram` (default), `sarvam`, `openai`, `google`, `azure`, `assemblyai` |
| `TTS_PROVIDER` | No | `deepgram` (default), `elevenlabs`, `openai`, `google`, `azure`, `cartesia` |
| `LLM_PROVIDER` | No | `gemini` (default) or `azure` |
| `PATIENT_ID` | No | Patient to load (default: `P001`) |

### 3. Test via WebRTC (No Phone Required)

```bash
python agent.py dev
```

Then open [LiveKit Playground](https://agents-playground.livekit.io/), enter your LiveKit credentials, and talk to Lila.

## Phone Calls via Twilio

### Prerequisites

- [Twilio account](https://www.twilio.com/) with Elastic SIP Trunking
- A Twilio phone number with voice capability
- LiveKit Cloud project with SIP enabled

### Step 1: Set Up Twilio Elastic SIP Trunk

1. **Buy a phone number** in Twilio Console (Phone Numbers > Buy a Number)
2. **Create an Elastic SIP Trunk** (Elastic SIP Trunking > Trunks > Create)
3. **Configure Termination**:
   - Set a termination URI (e.g., `your-trunk.pstn.twilio.com`)
   - Create a **Credential List** (Voice > Credential Lists) with a username/password
   - Assign the credential list to the trunk's Termination > Authentication
4. **Associate your phone number** with the trunk (trunk > Numbers tab)

### Step 2: Create LiveKit Outbound SIP Trunk

Run the interactive setup script:

```bash
python setup_sip_trunk.py
```

It will ask for:
- Twilio termination URI (`your-trunk.pstn.twilio.com`)
- Phone number (`+1XXXXXXXXXX`)
- Credential username/password

Or create it via the [LiveKit Cloud Dashboard](https://cloud.livekit.io/) under Telephony > SIP Trunks.

### Step 3: Add Trunk ID to `.env`

```bash
SIP_OUTBOUND_TRUNK_ID=ST_xxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
```

### Step 4: Verify Setup

```bash
python test_twilio_sip.py
```

Expected output:
```
[PASS] env          - All required env vars set
[PASS] livekit      - Connected to LiveKit Cloud
[PASS] sip_trunk    - Outbound trunk found
```

### Step 5: Make a Phone Call

**Terminal 1** — Start the agent:
```bash
python agent.py dev
```

**Terminal 2** — Dial a patient:
```bash
python make_call.py +919876543210
python make_call.py +919876543210 --patient P001
```

### Step 6: Test with a Real Call

```bash
# Test SIP trunk only (phone rings, no agent — just verifies Twilio works)
python test_twilio_sip.py --call +919876543210

# Full call with agent
python agent.py dev                       # Terminal 1
python make_call.py +919876543210         # Terminal 2
```

## Call Flow (Outbound)

```
1. make_call.py           →  Creates LiveKit room + dispatches agent
2. LiveKit                →  Assigns job to agent.py
3. agent.py               →  Connects to room, reads phone_number from metadata
4. agent.py               →  Calls ctx.api.sip.create_sip_participant()
5. LiveKit SIP Bridge     →  Sends SIP INVITE to Twilio
6. Twilio SIP Trunk       →  Routes call to PSTN
7. Patient phone rings    →  Patient answers
8. Voice pipeline starts  →  STT ↔ LLM ↔ TTS (bidirectional audio)
9. Patient hangs up       →  Transcript auto-saved to patient JSON
```

## Check-In Protocol

Lila follows a structured 4-section protocol:

| Section | What Lila Does |
|---------|---------------|
| **1. Symptoms & Side Effects** | Asks about physical symptoms, severity, duration |
| **2. Medication Adherence** | Checks if all doses were taken, counsels on missed doses |
| **3. Well-being** | Asks about mood, sleep, appetite, daily functioning |
| **4. Closing** | Summarizes, offers care team callback, thanks patient |

### Emergency Protocol
If the patient reports something urgent, Lila stops the normal flow and offers to alert the care team immediately.

### Guardrails
Lila will **never**:
- Provide medical advice or diagnose conditions
- Recommend treatment changes
- Discuss unrelated topics (politely redirects)
- Misrepresent herself as a nurse or doctor

## Patient Data

Patient records live in `data/patients/*.json`:

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
  "call_history": [
    {"date": "2026-02-11T...", "transcript": ["assistant: ...", "user: ..."]}
  ]
}
```

Transcripts are automatically appended to `call_history` when the patient disconnects.

## Switching Providers

```bash
# STT (Speech-to-Text)
STT_PROVIDER=sarvam      # Indian English (default)
STT_PROVIDER=deepgram    # Fast, accurate
STT_PROVIDER=openai      # Whisper
STT_PROVIDER=google      # Google Cloud

# TTS (Text-to-Speech)
TTS_PROVIDER=elevenlabs  # High quality (default)
TTS_PROVIDER=deepgram    # Low latency
TTS_PROVIDER=cartesia    # Ultra low latency
TTS_PROVIDER=openai      # OpenAI TTS

# LLM
LLM_PROVIDER=gemini      # Gemini 2.5 Flash (default)
LLM_PROVIDER=azure       # Azure OpenAI GPT-4o
```

## Customization

### Change Agent Name
```bash
AGENT_NAME=Maya   # in .env (default: Lila)
```

### Change TTS Voice
Update `ELEVENLABS_VOICE_ID` in `.env`. Browse voices at [ElevenLabs Voice Library](https://elevenlabs.io/voice-library).

### Modify Check-In Protocol
Edit `prompts/patient_support.py` to change:
- Conversation sections and questions
- Tone and style guidelines
- Response pacing (filler phrases for low-latency feel)
- Guardrails and boundaries

### Add Patient Records
Create a new JSON file in `data/patients/` following the schema above, then call with:
```bash
python make_call.py +91XXXXXXXXXX --patient P002
```

## Next Steps: Self-Hosted LiveKit (Local Setup)

Currently this project uses **LiveKit Cloud**. To run LiveKit locally for development, testing, or on-premise deployment:

### Option 1: LiveKit CLI (Quickest for Dev)

```bash
# Install LiveKit CLI
# macOS
brew install livekit

# Windows (via scoop)
scoop bucket add livekit https://github.com/livekit/scoop-bucket
scoop install livekit

# Start a local LiveKit server
livekit-server --dev
```

This starts LiveKit at `ws://localhost:7880` with test credentials:
- API Key: `devkey`
- API Secret: `secret`

Update your `.env`:
```bash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

### Option 2: Docker (Recommended for Local SIP)

```bash
docker run --rm -p 7880:7880 -p 7881:7881 -p 5060:5060/udp \
  -e LIVEKIT_KEYS="devkey: secret" \
  livekit/livekit-server --dev
```

Port `5060/udp` is the SIP port — required for phone call testing.

### Option 3: Full Self-Hosted (Production)

For production self-hosting with SIP support, you need:

1. **LiveKit Server** — Core media server
2. **LiveKit SIP** — SIP bridge (separate service)
3. **Redis** — Required for multi-node deployments
4. **TURN Server** — For NAT traversal (or use LiveKit's built-in TURN)

```yaml
# docker-compose.yml
version: "3.9"
services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"    # WebSocket
      - "7881:7881"    # RTC (WebRTC)
      - "7882:7882"    # TURN/TLS
    environment:
      - LIVEKIT_KEYS=devkey: secret
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    command: --config /etc/livekit.yaml

  livekit-sip:
    image: livekit/sip:latest
    network_mode: host
    ports:
      - "5060:5060/udp"  # SIP signaling
    environment:
      - LIVEKIT_URL=ws://livekit:7880
      - LIVEKIT_API_KEY=devkey
      - LIVEKIT_API_SECRET=secret
    depends_on:
      - livekit

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```yaml
# livekit.yaml
port: 7880
rtc:
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: true
redis:
  address: redis:6379
keys:
  devkey: secret
sip:
  enabled: true
```

### Local SIP Testing (Without Twilio)

For local development without Twilio costs, you can use **FreeSWITCH** or **Opal** as a local SIP server:

```bash
# Install FreeSWITCH (local SIP PBX)
# Then configure LiveKit SIP trunk to point to localhost:5060
# Use a softphone (Opal, Opal, Zoiper) to make/receive calls locally
```

Or use a **SIP softphone** (Opal, Opal, Zoiper, Opal) connected directly to LiveKit SIP:

1. Start LiveKit locally with SIP enabled
2. Create an inbound SIP trunk in LiveKit
3. Point your softphone to `localhost:5060`
4. Call in — LiveKit dispatches the agent

### Deployment Considerations

| Concern | Cloud | Self-Hosted |
|---------|-------|-------------|
| Setup complexity | None | High (networking, TURN, TLS) |
| SIP support | Built-in | Deploy `livekit/sip` separately |
| Scaling | Automatic | Manual (add nodes + Redis) |
| Latency | Depends on region | Controlled (your infra) |
| Cost | Per-minute | Server costs only |
| Data privacy | Data on LiveKit servers | Full control |
| HIPAA compliance | LiveKit Cloud is HIPAA-eligible | You manage compliance |

## Latency Reduction & Interruption Handling

The agent uses a three-layer approach to minimize perceived response latency:

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| **Background audio** | `BackgroundAudioPlayer` plays subtle keyboard typing during thinking | Fills dead silence immediately (~0ms) |
| **Filler phrases** | LLM instructed to start every response with "I see...", "Got it...", etc. | First tokens stream fast (~100ms), TTS synthesizes quickly (~300ms) |
| **Preemptive generation** | `preemptive_generation=True` on `AgentSession` | LLM starts generating on partial transcript before user finishes |

Interruption handling prevents noise from cutting off the agent:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `min_interruption_duration` | `1.5s` | Filters coughs (<0.5s) and "hmm" (~0.8s) |
| `min_interruption_words` | `3` | Requires 3+ transcribed words, not just noise |
| `false_interruption_timeout` | `2.0s` | If user goes silent after triggering interruption, agent resumes |
| `resume_false_interruption` | `True` | Agent resumes from where it left off (doesn't restart) |

### Tuning Tips

- **Phone calls**: Increase thinking sound volume from `0.15` to `0.2-0.3` in `agent.py` (phone audio is compressed)
- **Too aggressive filtering**: Lower `min_interruption_duration` to `1.0` if legitimate interruptions are being ignored
- **Too sensitive**: Raise `min_interruption_words` to `4` if short phrases still interrupt

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent not responding | Check `python agent.py dev` is running, verify LiveKit credentials |
| Call not ringing | Verify `SIP_OUTBOUND_TRUNK_ID` in `.env`, run `python test_twilio_sip.py` |
| Poor audio quality | Check internet connection, try `TTS_PROVIDER=deepgram` for lower latency |
| High latency | Preemptive generation + filler phrases should help; also try `elevenlabs` with `eleven_turbo_v2`, ensure Gemini Flash (not Pro) |
| Coughs/noise interrupting agent | Increase `min_interruption_duration` or `min_interruption_words` in `agent.py` |
| Can't interrupt agent | Lower `min_interruption_duration` (default 1.5s) — legitimate speech is ~2s+ |
| Thinking sound too quiet on phone | Increase `volume` from `0.15` to `0.2-0.3` in `BackgroundAudioPlayer` config |
| STT not understanding | Try switching `STT_PROVIDER` (sarvam for Indian English, deepgram for general) |
| Call drops immediately | Check Twilio trunk credentials, verify phone number is associated with trunk |
| "Trunk not found" error | Run `python setup_sip_trunk.py --list` to verify trunk exists |

## License

Private - All rights reserved.
