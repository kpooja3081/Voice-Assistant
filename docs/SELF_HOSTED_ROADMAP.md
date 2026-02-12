# Self-Hosted LiveKit Roadmap

## Current State: LiveKit Cloud

The project currently uses **LiveKit Cloud** (`wss://lila-cq2z59g7.livekit.cloud`, India South region). This means:
- Zero infrastructure management
- Automatic scaling
- Built-in SIP bridge for Twilio calls
- HIPAA-eligible
- Pay per-minute pricing

## Why Self-Host?

| Reason | Details |
|--------|---------|
| Data sovereignty | Full control over patient audio/transcripts (HIPAA on your terms) |
| Cost at scale | Per-minute Cloud pricing adds up with 1000+ daily calls |
| Latency control | Co-locate LiveKit with your STT/LLM/TTS providers |
| Offline/air-gapped | Hospital networks that can't reach external cloud |
| Custom SIP routing | Direct peering with telecom instead of going through Twilio |

## Architecture: Cloud vs Self-Hosted

### Current (Cloud)
```
Agent (your server) ←→ LiveKit Cloud ←→ Twilio SIP Trunk ←→ PSTN ←→ Patient
                           |
                    Built-in SIP Bridge
```

### Self-Hosted
```
Agent (your server) ←→ LiveKit Server ←→ LiveKit SIP ←→ Twilio/SIP Provider ←→ PSTN
                           |                  |
                         Redis            SIP Bridge
                       (required)       (separate service)
```

## Deployment Options

### Option 1: Single Server (Dev/Small Scale)

Good for: Development, testing, <50 concurrent calls.

```bash
# Install LiveKit CLI
# macOS
brew install livekit

# Windows
scoop bucket add livekit https://github.com/livekit/scoop-bucket
scoop install livekit

# Start local server
livekit-server --dev
```

`.env` changes:
```bash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

**Limitations:** No SIP support (need separate SIP service), no persistence, no scaling.

### Option 2: Docker Compose (Recommended for Testing SIP)

```yaml
# docker-compose.yml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"    # WebSocket (client connections)
      - "7881:7881"    # RTC (WebRTC media)
      - "7882:7882"    # TURN/TLS
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
    command: --config /etc/livekit.yaml
    depends_on:
      - redis

  sip:
    image: livekit/sip:latest
    network_mode: host          # SIP needs direct network access
    environment:
      - LIVEKIT_URL=ws://localhost:7880
      - LIVEKIT_API_KEY=devkey
      - LIVEKIT_API_SECRET=secret
    depends_on:
      - livekit
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
```

### Option 3: Production (Kubernetes / Multi-Node)

Components needed:
1. **LiveKit Server** — 1+ instances (horizontal scaling)
2. **LiveKit SIP** — 1+ instances (SIP bridge)
3. **Redis** — Required for multi-node coordination
4. **TURN Server** — For NAT traversal (or use LiveKit's built-in TURN)
5. **TLS Certificates** — Required for production WebRTC
6. **Load Balancer** — For WebSocket connections

## What Changes in Code

### Minimal Changes Required

The agent code is **almost entirely unchanged**. Only `.env` values change:

```bash
# Before (Cloud)
LIVEKIT_URL=wss://lila-cq2z59g7.livekit.cloud
LIVEKIT_API_KEY=<cloud-key>
LIVEKIT_API_SECRET=<cloud-secret>
SIP_OUTBOUND_TRUNK_ID=ST_xxxx

# After (Self-Hosted)
LIVEKIT_URL=wss://livekit.yourdomain.com    # or ws://localhost:7880 for dev
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
SIP_OUTBOUND_TRUNK_ID=ST_xxxx              # Create via API or dashboard
```

### SIP Trunk Setup Differences

**Cloud:** Use `setup_sip_trunk.py` or LiveKit Cloud Dashboard.

**Self-Hosted:** Create trunk via LiveKit API:

```python
from livekit import api

lk = api.LiveKitAPI("http://localhost:7880", "devkey", "secret")

# Create outbound SIP trunk pointing to Twilio
trunk = await lk.sip.create_sip_outbound_trunk(
    api.CreateSIPOutboundTrunkRequest(
        name="twilio-outbound",
        address="your-trunk.pstn.twilio.com",
        numbers=["+1XXXXXXXXXX"],
        auth_username="twilio-user",
        auth_password="twilio-pass",
    )
)
print(f"Trunk ID: {trunk.sip_trunk_id}")  # → SIP_OUTBOUND_TRUNK_ID
```

Or update `setup_sip_trunk.py` to point to your self-hosted URL instead of Cloud.

### Telephony Architecture (Self-Hosted)

```
                    Your Infrastructure
┌─────────────────────────────────────────────────┐
│                                                   │
│  agent.py ←→ LiveKit Server ←→ LiveKit SIP       │
│                    |                |              │
│                  Redis          SIP INVITE         │
│                                    |              │
└────────────────────────────────────|──────────────┘
                                     |
                              ┌──────┴──────┐
                              │   Options   │
                              └──────┬──────┘
                                     |
                    ┌────────────────┼────────────────┐
                    |                |                 |
             Twilio SIP        Direct SIP         FreeSWITCH
             Trunk             Provider           (Local PBX)
                    |                |                 |
                  PSTN            PSTN            Softphones
```

**Option A: Keep Twilio** (Easiest migration)
- LiveKit SIP sends SIP INVITE to Twilio's termination URI
- Twilio routes to PSTN
- Same Twilio credentials, same phone numbers
- Only change: LiveKit SIP runs on your server instead of Cloud

**Option B: Direct SIP Provider** (Lower cost)
- Replace Twilio with a direct SIP trunking provider (e.g., Telnyx, Vonage, Bandwidth)
- Configure LiveKit SIP trunk with provider's SIP address
- Potentially lower per-minute rates

**Option C: FreeSWITCH / Local PBX** (Full control, no PSTN costs for testing)
- Run FreeSWITCH locally as a SIP PBX
- Use softphones (Opal, Zoiper) to simulate calls
- Great for development without Twilio costs
- Configure LiveKit SIP trunk to point to `localhost:5060`

## Migration Checklist

### Phase 1: Local Development (1-2 days)
- [ ] Install Docker and docker-compose
- [ ] Deploy LiveKit Server + Redis locally
- [ ] Update `.env` to point to `ws://localhost:7880`
- [ ] Verify `python agent.py dev` connects to local LiveKit
- [ ] Test inbound calls via WebRTC (LiveKit Playground → local server)

### Phase 2: SIP Integration (1-2 days)
- [ ] Deploy LiveKit SIP service alongside LiveKit Server
- [ ] Create outbound SIP trunk via API
- [ ] Configure trunk with Twilio credentials
- [ ] Test outbound call: `python make_call.py +91XXXXXXXXXX`
- [ ] Verify call quality matches Cloud

### Phase 3: Production Hardening (1-2 weeks)
- [ ] Set up TLS certificates for LiveKit Server
- [ ] Configure TURN server for NAT traversal
- [ ] Set up Redis for persistence
- [ ] Configure proper API keys (not devkey)
- [ ] Set up monitoring/alerting
- [ ] Load test: concurrent calls
- [ ] Set up log aggregation

### Phase 4: Scaling (Ongoing)
- [ ] Add multiple LiveKit Server nodes
- [ ] Configure load balancer
- [ ] Set up auto-scaling rules
- [ ] Monitor Redis memory usage
- [ ] Set up backup SIP trunks (failover)

## Network Requirements

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 7880 | TCP | LiveKit WebSocket | Client connections |
| 7881 | UDP | LiveKit RTC | WebRTC media |
| 7882 | TCP | TURN/TLS | NAT traversal |
| 5060 | UDP | SIP Signaling | LiveKit SIP service |
| 10000-20000 | UDP | RTP Media | SIP audio (configurable range) |
| 6379 | TCP | Redis | Internal only |
| 443 | TCP | HTTPS | TLS termination |

## Cost Comparison

| Aspect | LiveKit Cloud | Self-Hosted |
|--------|--------------|-------------|
| LiveKit | ~$0.01-0.04/min | Server cost only |
| SIP Bridge | Included | Free (self-hosted) |
| Twilio | ~$0.013/min (India) | Same (or switch provider) |
| STT/TTS/LLM | Same (external APIs) | Same (or self-host models) |
| Maintenance | Zero | Your team manages |
| Scaling | Automatic | Manual (or K8s auto-scale) |

**Break-even point:** Roughly 50,000-100,000 call minutes/month, depending on Cloud tier and server costs.

## Future: Self-Hosted AI Models

For maximum control and lowest latency, you could also self-host:

| Component | Self-Hosted Option | Notes |
|-----------|-------------------|-------|
| STT | Whisper (local GPU) | Eliminates Sarvam/Deepgram API calls |
| LLM | Llama 3 / Mistral (vLLM) | Eliminates Gemini API dependency |
| TTS | Coqui TTS / XTTS | Eliminates ElevenLabs API calls |

This would make the entire pipeline run on-premises with zero external API calls — ideal for air-gapped hospital environments.
