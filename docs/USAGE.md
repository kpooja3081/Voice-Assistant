# Technical Usage Guide — Lila Voice Agent

## Prerequisites

- Python 3.11+
- LiveKit Cloud account (or self-hosted LiveKit server)
- Twilio account with Elastic SIP Trunking (for phone calls)
- API keys for: Google Gemini, STT provider, TTS provider

## Installation

```bash
git clone <repo-url>
cd VOICE
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

**Note:** `requirements.txt` pins `livekit-agents~=1.3.0` but the actual installed version is **v1.4.1** (via dependency resolution). All code is tested against v1.4.1.

## Configuration

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | `wss://your-project.livekit.cloud` |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `GOOGLE_API_KEY` | Google Gemini API key |

### STT Provider (pick one)

| `STT_PROVIDER` | Variable Needed |
|----------------|-----------------|
| `sarvam` (Indian English) | `SARVAM_API_KEY` |
| `deepgram` (general) | `DEEPGRAM_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `google` | Google credentials |
| `azure` | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |
| `assemblyai` | `ASSEMBLYAI_API_KEY` |

### TTS Provider (pick one)

| `TTS_PROVIDER` | Variable Needed |
|----------------|-----------------|
| `elevenlabs` (recommended) | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| `deepgram` (low latency) | `DEEPGRAM_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `cartesia` (ultra low latency) | `CARTESIA_API_KEY` |
| `google` | Google credentials |
| `azure` | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |

### Phone Calls

| Variable | Description |
|----------|-------------|
| `SIP_OUTBOUND_TRUNK_ID` | LiveKit outbound SIP trunk ID (`ST_xxxx`) |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PATIENT_ID` | `P001` | Default patient to load |
| `AGENT_NAME` | `Lila` | Agent's spoken name |
| `LLM_PROVIDER` | `gemini` | `gemini` or `azure` |

## Running the Agent

### Development (hot reload)

```bash
python agent.py dev
```

The agent registers with LiveKit Cloud and watches for file changes. Any edits to `.py` files trigger automatic restart.

### Production

```bash
python agent.py start
```

## Making Calls

### Via WebRTC (no phone needed)

1. Start the agent: `python agent.py dev`
2. Open [LiveKit Playground](https://agents-playground.livekit.io/)
3. Enter your LiveKit URL + credentials
4. Talk to Lila through your browser microphone

### Via Phone (Twilio SIP)

**Terminal 1** — Start the agent:
```bash
python agent.py dev
```

**Terminal 2** — Dial a patient:
```bash
python make_call.py +919876543210
python make_call.py +919876543210 --patient P002
```

The agent dispatches itself to a new room, dials the phone via SIP, and starts the check-in protocol when the patient picks up.

## Twilio SIP Setup

### Step 1: Twilio Console

1. Buy a phone number (Phone Numbers > Buy a Number)
2. Create Elastic SIP Trunk (Elastic SIP Trunking > Trunks > Create)
3. Configure Termination:
   - Set termination URI: `your-trunk.pstn.twilio.com`
   - Create Credential List (Voice > Credential Lists) with username/password
   - Assign credentials to trunk's Termination > Authentication
4. Associate phone number with trunk (Numbers tab)

### Step 2: LiveKit SIP Trunk

Interactive setup:
```bash
python setup_sip_trunk.py
```

Or create via [LiveKit Cloud Dashboard](https://cloud.livekit.io/) > Telephony > SIP Trunks.

### Step 3: Add to `.env`

```bash
SIP_OUTBOUND_TRUNK_ID=ST_xxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
```

### Step 4: Verify

```bash
python test_twilio_sip.py
```

Expected:
```
[PASS] env          - All required env vars set
[PASS] livekit      - Connected to LiveKit Cloud
[PASS] sip_trunk    - Outbound trunk found
```

### Step 5: Test Real Call

```bash
python test_twilio_sip.py --call +919876543210
```

## Patient Data Management

### Add a New Patient

Create `data/patients/P002.json`:

```json
{
  "patient_id": "P002",
  "name": "Raj Kumar",
  "age": 52,
  "medications": [
    {"name": "Pembrolizumab", "dose": "200mg", "frequency": "every 3 weeks"}
  ],
  "conditions": ["Lung Cancer"],
  "allergies": ["None"],
  "provider": "Dr. Priya Sharma",
  "call_history": []
}
```

Call with:
```bash
python make_call.py +91XXXXXXXXXX --patient P002
```

### View Call History

Call transcripts are automatically saved to the patient's JSON under `call_history`. Each entry has a timestamp and full transcript.

## Switching Providers

All changes via `.env` — no code modification needed:

```bash
# Indian English optimized
STT_PROVIDER=sarvam
TTS_PROVIDER=elevenlabs

# Low latency setup
STT_PROVIDER=deepgram
TTS_PROVIDER=cartesia

# Budget setup
STT_PROVIDER=deepgram
TTS_PROVIDER=deepgram
```

## Customization

### Change Agent Name
```bash
AGENT_NAME=Maya  # in .env
```

### Change TTS Voice
Update `ELEVENLABS_VOICE_ID` in `.env`. Browse: [ElevenLabs Voice Library](https://elevenlabs.io/voice-library)

### Tune Voice Emotion
Edit `tts/factory.py` → `VoiceSettings`:
- `stability` (0-1): Lower = more emotional range. Current: `0.4`
- `similarity_boost` (0-1): Voice consistency. Current: `0.75`
- `style` (0-1): Expressiveness. Current: `0.35`
- `use_speaker_boost`: Clarity boost. Current: `True`

### Modify Check-In Protocol
Edit `prompts/patient_support.py`:
- `CALL PROTOCOL` section: Change questions and flow
- `RESPONSE PACING` section: Change filler phrases
- `GUARDRAILS` section: Adjust boundaries
- `TONE & STYLE` section: Adjust personality

### Tune Interruption Handling
Edit `agent.py` → `AgentSession(...)`:
- `min_interruption_duration`: Seconds of speech needed (default: `1.5`)
- `min_interruption_words`: Transcribed words needed (default: `3`)

### Tune Thinking Sound
Edit `agent.py` → `BackgroundAudioPlayer`:
- `volume`: `0.15` for WebRTC, `0.25-0.3` for phone calls
- `source`: `BuiltinAudioClip.KEYBOARD_TYPING` (only built-in option)

## Debug Logging

The agent logs pipeline events with `[PIPELINE]` prefix:

```
[PIPELINE] agent_state: listening -> thinking     # LLM processing
[PIPELINE] agent_state: thinking -> speaking      # TTS outputting
[PIPELINE] user_input_transcribed: ...            # What STT heard
[PIPELINE] ERROR from <source>: ...               # LLM/STT/TTS failure
[PIPELINE] false_interruption: resumed=True       # Noise filtered
```

To see full debug output:
```bash
python agent.py dev 2>&1 | findstr "[PIPELINE]"   # Windows
python agent.py dev 2>&1 | grep "[PIPELINE]"       # Linux/Mac
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent not responding after greeting | Gemini API hanging | Check `GOOGLE_API_KEY`, check Gemini quota |
| Voice cuts off mid-sentence | Too-sensitive interruption | Increase `min_interruption_duration` |
| Coughs interrupt agent | Interruption threshold too low | Increase `min_interruption_words` |
| Can't interrupt agent | Threshold too high | Lower `min_interruption_duration` to `1.0` |
| Call not ringing | SIP trunk misconfigured | Run `python test_twilio_sip.py` |
| High latency (>5s silence) | Gemini slow | Check network; Gemini Flash is already fastest |
| Typing sound too quiet on phone | Volume too low | Increase `volume` to `0.3` in BackgroundAudioPlayer |
| `AFC is enabled` log | Normal Gemini SDK message | Not an error — ignore |
| STT not understanding accent | Wrong provider | Try `sarvam` for Indian English |
| Hot reload errors on Windows | Normal IPC restart | Ignore `DuplexClosed` errors — agent re-registers |
