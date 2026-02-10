# Patient Support Voice Agent

A Voice AI agent built with LiveKit that calls patients for medication adherence follow-up and side effect reporting.

## Features

- **LiveKit Voice Pipeline**: Best-in-class interruption handling with Voice Activity Detection (VAD)
- **Gemini TTS**: High-quality, real-time text-to-speech from Google
- **Deepgram STT**: Low-latency, accurate speech-to-text
- **Switchable LLMs**: Support for Azure OpenAI and Google Gemini Flash
- **Strict Boundaries**: Agent only discusses medication adherence and side effects

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LiveKit Voice Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐ │
│  │ Deepgram │───▶│   LLM    │───▶│ Gemini   │───▶│  Patient  │ │
│  │   STT    │    │ (Gemini) │    │   TTS    │    │  (Phone)  │ │
│  │          │◀───│          │◀───│          │◀───│           │ │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘ │
│                                                                  │
│  LiveKit handles: Interruption, VAD, Turn-taking, Audio routing │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- LiveKit Cloud account (or self-hosted LiveKit server)
- Deepgram API key
- ElevenLabs API key
- Azure OpenAI OR Google Gemini API credentials

## Setup

### 1. Clone and Install Dependencies

```bash
cd voice
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|----------|-------------|
| `LIVEKIT_URL` | Your LiveKit server URL |
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `DEEPGRAM_API_KEY` | Deepgram API key |
| `LLM_PROVIDER` | `azure` or `gemini` |

For Azure OpenAI:
| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`) |

For Gemini:
| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI API key |
| `GEMINI_MODEL` | Model name (default: `gemini-1.5-flash`) |

### 3. Get LiveKit Credentials

1. Sign up at [LiveKit Cloud](https://cloud.livekit.io/)
2. Create a new project
3. Copy the URL, API Key, and API Secret

### 4. Get Deepgram Credentials

1. Sign up at [Deepgram](https://deepgram.com/)
2. Create an API key

## Running the Agent

### Development Mode

```bash
python agent.py dev
```

This starts the agent in development mode with hot reloading.

### Production Mode

```bash
python agent.py start
```

## Switching LLM Providers

To switch between Azure OpenAI and Gemini, update the `LLM_PROVIDER` environment variable:

```bash
# Use Azure OpenAI
LLM_PROVIDER=azure

# Use Gemini Flash
LLM_PROVIDER=gemini
```

## Testing

### Using LiveKit Playground

1. Go to [LiveKit Playground](https://agents-playground.livekit.io/)
2. Enter your LiveKit credentials
3. Connect to test the voice agent

### Using SIP (Phone Calls)

To enable phone calls, configure LiveKit SIP:

1. Set up a SIP trunk provider (Twilio, etc.)
2. Configure LiveKit SIP settings
3. Assign a phone number to your agent

## Conversation Boundaries

The agent is strictly limited to discussing:
- Medication adherence (taking medicine as prescribed)
- Side effects (type, severity, frequency)
- General well-being related to medication
- Scheduling callbacks with healthcare providers

The agent will NOT:
- Provide medical advice
- Diagnose conditions
- Recommend treatment changes
- Discuss unrelated topics

## Project Structure

```
voice/
├── agent.py                 # Main LiveKit agent entry point
├── config.py                # Configuration management
├── llm/
│   ├── __init__.py
│   ├── base.py              # Base LLM interface
│   ├── azure_openai.py      # Azure OpenAI implementation
│   ├── gemini.py            # Gemini implementation
│   └── factory.py           # LLM factory function
├── prompts/
│   ├── __init__.py
│   └── patient_support.py   # System prompts & boundaries
├── conversation/
│   ├── __init__.py
│   └── flow.py              # Conversation state management
├── .env.example             # Environment template
├── requirements.txt         # Dependencies
└── README.md
```

## Customization

### Changing the TTS Voice

Update `ELEVENLABS_VOICE_ID` in your `.env` file. Find voice IDs at [ElevenLabs Voice Library](https://elevenlabs.io/voice-library).

Popular voices:
- `21m00Tcm4TlvDq8ikWAM` - Rachel (default, warm professional)
- `EXAVITQu4vr4xnSDxMaL` - Sarah (soft, friendly)
- `pNInz6obpgDQGcFmaJgB` - Adam (deep, authoritative)

### Modifying Conversation Flow

Edit `prompts/patient_support.py` to adjust:
- System prompt and boundaries
- Conversation style
- Response templates

Edit `conversation/flow.py` to adjust:
- Conversation stages
- Data collection fields
- State machine logic

## Troubleshooting

### Agent not responding
- Check LiveKit connection credentials
- Verify the agent is running (`python agent.py dev`)
- Check console logs for errors

### Poor audio quality
- Ensure stable internet connection
- Try different ElevenLabs voice model (`eleven_turbo_v2` for lower latency)

### High latency
- Switch to Gemini Flash for faster responses
- Use `eleven_turbo_v2` model for ElevenLabs
- Check network latency to service endpoints

## License

Private - All rights reserved.
